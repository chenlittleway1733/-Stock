"""Stock dataset validation boundary.

This module validates stock-level model input before valuation.  It is based on
the M07 validation package supplied on 2026-06-19, but kept as maintainable
first-party code instead of executing generated attachment code directly.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Optional


ALLOWED_MARKET_SUFFIX = {"TW", "TWO"}
VALID_DATA_QUALITY_GRADES = {"A", "B", "C", "D"}
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "ok": 0}

KNOWN_STOCK_CODE_RULES: Dict[str, Dict[str, Any]] = {
    "1701": {
        "type": "old_code",
        "rule_code": "V016",
        "severity": "critical",
        "action": "map_then_exclude_old_code",
        "replacement_code": "3716",
        "replacement_name": "中化控股",
        "reason": "舊代號終止上市；保留映射，不納入估值。",
    },
    "8078": {
        "type": "old_code",
        "rule_code": "V016",
        "severity": "critical",
        "action": "exclude_from_valuation",
        "replacement_code": None,
        "replacement_name": None,
        "reason": "舊資料 / 終止上市代號；不納入估值。",
    },
    "6806": {
        "type": "delist_risk",
        "rule_code": "V016",
        "severity": "high",
        "action": "exclude_from_valuation",
        "replacement_code": None,
        "replacement_name": None,
        "reason": "終止上市風險標記；僅保留分類與風險樣本。",
    },
    "4128": {
        "type": "code_name_mismatch",
        "rule_code": "V015",
        "severity": "critical",
        "action": "manual_review_or_map",
        "replacement_code": "4147",
        "replacement_name": "中裕",
        "reason": "清單出現「4128 中裕」；需人工確認是 4128 中天或 4147 中裕。",
    },
}


def _pick(record: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record and record.get(key) not in (None, ""):
            return record.get(key)
    return None


def _num(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            text = value.strip()
            if not text or text.upper() in {"N/A", "NA", "NULL", "NONE"} or text in {"-", "—", "–"}:
                return None
            is_percent = text.endswith("%")
            text = text.replace(",", "").replace("倍", "").replace("x", "").replace("X", "").replace("%", "").strip()
            if not text:
                return None
            f = float(text)
            if is_percent:
                f /= 100.0
        else:
            f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def normalize_stock_code(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", text):
        text = str(int(float(text)))
    return text.zfill(4) if text.isdigit() and len(text) <= 4 else text


def expected_yahoo_symbol(stock_code: Any, market_suffix: Any) -> str:
    code = normalize_stock_code(stock_code)
    suffix = str(market_suffix or "").strip()
    if not code or suffix not in ALLOWED_MARKET_SUFFIX:
        return ""
    return f"{code}.{suffix}"


def _is_valuation_included(include_text: str) -> bool:
    include_text = str(include_text or "").strip()
    if not include_text:
        return False
    return "納入估值" in include_text and "不納入" not in include_text


def _has_value_source(record: Mapping[str, Any], *keys: str) -> bool:
    return any(str(record.get(key) or "").strip() for key in keys)


def _max_severity(issues: List[Dict[str, Any]]) -> str:
    if not issues:
        return "ok"
    return max((str(i.get("severity") or "low") for i in issues), key=lambda x: SEVERITY_ORDER.get(x, 0))


def validation_status_from_issues(issues: List[Dict[str, Any]]) -> str:
    if not issues:
        return "PASS"
    codes = {str(i.get("rule_code") or i.get("code") or "") for i in issues}
    actions = " ".join(str(i.get("suggested_action") or "") for i in issues).lower()
    if codes & {"V015", "V016", "V018"} or "exclude" in actions or "map" in actions:
        return "EXCLUDE_OR_MAPPING"
    max_sev = _max_severity(issues)
    if max_sev in {"critical", "high", "medium"}:
        return "FIX_REQUIRED"
    return "WARN_REVIEW"


def validate_stock_record(
    record: Mapping[str, Any],
    *,
    duplicate_count: int = 1,
    known_stock_code_rules: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Validate one stock model-input record and return issue dictionaries."""
    rules = dict(known_stock_code_rules or KNOWN_STOCK_CODE_RULES)
    issues: List[Dict[str, Any]] = []

    def add(rule_code: str, severity: str, field: str, description: str, suggested_action: str, **extra: Any) -> None:
        issue = {
            "rule_code": rule_code,
            "severity": severity,
            "field": field,
            "description": description,
            "suggested_action": suggested_action,
        }
        issue.update(extra)
        issues.append(issue)

    stock_code = normalize_stock_code(_pick(record, "stock_code", "代號"))
    stock_name = str(_pick(record, "stock_name", "名稱") or "").strip()
    suffix = str(_pick(record, "market_suffix", "市場別/尾碼") or "").strip()
    yahoo_symbol = str(_pick(record, "yahoo_symbol", "Yahoo Symbol", "Yahoo") or "").strip()
    grade = str(_pick(record, "data_quality_grade", "資料品質等級") or "").strip()
    include = str(_pick(record, "include_in_valuation_model", "是否納入估值模型") or "").strip()
    ready = str(_pick(record, "valuation_ready_flag") or "").strip()
    current = _num(_pick(record, "current_price", "現價"))
    target = _num(_pick(record, "analyst_target_avg", "法人平均目標價"))
    eps = _num(_pick(record, "fy_eps", "FY EPS"))
    upside = _num(_pick(record, "upside_pct", "上行空間%"))
    forward_pe = _num(_pick(record, "forward_pe", "Forward P/E"))
    target_date = _pick(record, "target_date", "目標價日期")
    price_date = _pick(record, "price_date", "價格日期")
    eps_year = str(_pick(record, "eps_year", "EPS年度") or "").strip()

    if not re.fullmatch(r"\d{4}", stock_code):
        add("V001", "critical", "stock_code", "代號不是 4 位數字", "修正代號或排除")
    if not stock_name:
        add("V002", "critical", "stock_name", "股票名稱空白", "補名稱")
    if duplicate_count > 1:
        add("V005", "high", "stock_code", f"代號重複出現 {duplicate_count} 次", "檢查重複分類或映射")

    known = rules.get(stock_code)
    if known:
        add(
            str(known.get("rule_code") or "V016"),
            str(known.get("severity") or "high"),
            "stock_code/stock_name",
            f"已知映射/排除代號：{stock_code}；{known.get('reason') or ''}".strip(),
            str(known.get("action") or "manual_review"),
            replacement_code=known.get("replacement_code"),
            replacement_name=known.get("replacement_name"),
            mapping_type=known.get("type"),
        )

    if suffix in ALLOWED_MARKET_SUFFIX:
        expected = expected_yahoo_symbol(stock_code, suffix)
        if yahoo_symbol and yahoo_symbol != expected:
            add("V004", "high", "yahoo_symbol", f"Yahoo symbol 應為 {expected}", "修正 yahoo_symbol")
    elif grade != "D":
        add("V003", "high", "market_suffix", "非 TW/TWO 且非 D 級排除資料", "補 TW/TWO 或排除")

    if grade not in VALID_DATA_QUALITY_GRADES:
        add("V006", "high", "data_quality_grade", "資料品質等級不是 A/B/C/D", "補正等級")

    valuation_included = _is_valuation_included(include)
    if grade in {"A", "B"}:
        if not valuation_included:
            add("V006", "high", "include_in_valuation_model", "A/B 未標示納入估值模型", "修正納入旗標")
        if current is None or target is None or eps is None:
            add("V008", "high", "valuation_inputs", "A/B 缺估值必要欄位", "補資料或降級")
        if ready and ready != "ready":
            add("V007", "medium", "valuation_ready_flag", "A/B 但 valuation_ready_flag 不是 ready", "檢查或降級")
    if grade in {"C", "D"} and valuation_included:
        add("V009", "high", "include_in_valuation_model", "C/D 不應納入估值模型", "改為追蹤/排除")
    if grade == "D" and not known:
        add("V018", "medium", "data_quality_grade", "D 級資料應進排除/映射流程", "保留在排除清單，不納入估值")

    if current is not None and current > 0 and target is not None:
        expected_upside = target / current - 1
        if upside is None or abs(upside - expected_upside) > 0.0005:
            add("V010", "medium", "upside_pct", "上行空間公式不一致", "重算 target/current-1")
    if current is not None and current > 0 and eps is not None and eps > 0:
        expected_pe = current / eps
        tolerance = max(0.01, abs(expected_pe) * 0.001)
        if forward_pe is None or abs(forward_pe - expected_pe) > tolerance:
            add("V011", "medium", "forward_pe", "Forward P/E 公式不一致", "重算 current/eps")
    elif eps is not None and eps <= 0 and grade in {"A", "B"}:
        add("V012", "medium", "fy_eps", "EPS 為 0 或負值但仍在 A/B universe", "套用負 EPS 規則或降權")

    if target is not None and not target_date:
        add("V013", "low", "target_date", "有目標價但缺日期", "補日期")
    if current is not None and not price_date:
        add("V014", "low", "price_date", "有現價但缺日期", "補日期")
    eps_year_has_valid_year = bool(
        re.search(r"(?:FY)?20\d{2}E", eps_year)
        or re.search(r"FY20\d{2}[-/～~]20\d{2}", eps_year)
    )
    if eps is not None and eps_year and not eps_year_has_valid_year:
        add("V017", "medium", "eps_year", "有 FY EPS 但年度非 FYxxxxE 口徑", "補 EPS 年度")

    has_price_source = _has_value_source(record, "source_price_url", "price_source_url", "現價來源URL")
    has_target_source = _has_value_source(record, "source_target_url", "target_source_url", "目標價來源URL")
    has_eps_source = _has_value_source(record, "source_eps_url", "eps_source_url", "EPS來源URL")
    if current is not None and not has_price_source:
        add("V019", "low", "price_source_url", "有現價但缺來源 URL", "補來源")
    if target is not None and not has_target_source:
        add("V019", "low", "target_source_url", "有目標價但缺來源 URL", "補來源")
    if eps is not None and not has_eps_source:
        add("V019", "low", "eps_source_url", "有 FY EPS 但缺來源 URL", "補來源")

    if forward_pe is not None and forward_pe > 100 and grade in {"A", "B"}:
        add("V020", "low", "forward_pe", "Forward P/E > 100x", "套用 PE cap / 極端值規則")
    return issues


def summarize_record_validation(record: Mapping[str, Any], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    code = normalize_stock_code(_pick(record, "stock_code", "代號"))
    name = str(_pick(record, "stock_name", "名稱") or "").strip()
    max_sev = _max_severity(issues)
    return {
        "stock_code": code,
        "stock_name": name,
        "validation_status": validation_status_from_issues(issues),
        "max_severity": max_sev,
        "issue_count": len(issues),
        "issue_codes": ";".join(str(i.get("rule_code") or "") for i in issues if i.get("rule_code")),
        "suggested_action": "；".join(str(i.get("suggested_action") or "") for i in issues[:3]) if issues else "可直接使用",
        "issues": issues,
    }


def validate_stock_dataset(records: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = list(records or [])
    duplicate_counts = Counter(normalize_stock_code(_pick(row, "stock_code", "代號")) for row in rows)
    duplicate_counts.pop("", None)

    reports: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        code = normalize_stock_code(_pick(row, "stock_code", "代號"))
        row_issues = validate_stock_record(row, duplicate_count=duplicate_counts.get(code, 1))
        report = summarize_record_validation(row, row_issues)
        report["row_index"] = idx
        reports.append(report)
        for issue in row_issues:
            issue_row = dict(issue)
            issue_row.update({"row_index": idx, "stock_code": report["stock_code"], "stock_name": report["stock_name"]})
            issues.append(issue_row)

    status_counts = Counter(report["validation_status"] for report in reports)
    severity_counts = Counter(str(issue.get("severity") or "low") for issue in issues)
    rule_counts = Counter(str(issue.get("rule_code") or "") for issue in issues)
    return {
        "total": len(rows),
        "reports": reports,
        "issues": issues,
        "status_counts": dict(status_counts),
        "severity_counts": dict(severity_counts),
        "rule_counts": dict(rule_counts),
        "pass_count": status_counts.get("PASS", 0),
        "issue_count": len(issues),
    }


__all__ = [
    "ALLOWED_MARKET_SUFFIX",
    "KNOWN_STOCK_CODE_RULES",
    "VALID_DATA_QUALITY_GRADES",
    "expected_yahoo_symbol",
    "normalize_stock_code",
    "summarize_record_validation",
    "validate_stock_dataset",
    "validate_stock_record",
    "validation_status_from_issues",
]
