"""Read-only loader for M10/M12 model data exports.

The M10 files are an auxiliary model-data layer.  They should not replace the
existing 17-C semantic taxonomy; callers merge the returned margin benchmark
metadata into profiles when needed.
"""

from __future__ import annotations

import copy
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


MODEL_DATA_DIR = Path(__file__).resolve().parent / "model_data"
INDUSTRY_MARGIN_FILE = "industry_taxonomy_with_margin.json"
STOCK_MODEL_MARGIN_FILE = "stock_model_data_with_margin.json"
VALUATION_UNIVERSE_MARGIN_FILE = "valuation_universe_with_margin.json"
MARGIN_RULES_FILE = "margin_benchmark_rules.json"

EXPECTED_INDUSTRY_CATEGORY_COUNT = 90
EXPECTED_STOCK_MODEL_COUNT = 275
EXPECTED_VALUATION_UNIVERSE_COUNT = 157
EXPECTED_MARGIN_QUALITY_COUNTS = {"A": 37, "B": 35, "C": 15, "N/A": 3}


def _normalize_stock_id(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", text):
        text = str(int(float(text)))
    return text.zfill(4) if text.isdigit() and len(text) <= 4 else text


def _json_safe_copy(value: Any) -> Any:
    return copy.deepcopy(value)


@lru_cache(maxsize=8)
def _load_json_cached(file_name: str) -> Any:
    path = MODEL_DATA_DIR / file_name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_json(file_name: str) -> Any:
    return _json_safe_copy(_load_json_cached(file_name))


def _pct_to_ratio(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v / 100.0


def load_industry_margin_taxonomy() -> List[Dict[str, Any]]:
    """Return the 90-category M10 margin taxonomy as dictionaries."""
    data = _load_json(INDUSTRY_MARGIN_FILE)
    return data if isinstance(data, list) else []


def load_stock_model_data_with_margin() -> List[Dict[str, Any]]:
    """Return all 275 stock model rows with attached M10 margin metadata."""
    data = _load_json(STOCK_MODEL_MARGIN_FILE)
    return data if isinstance(data, list) else []


def load_valuation_universe_with_margin() -> List[Dict[str, Any]]:
    """Return the A/B valuation universe rows with attached margin metadata."""
    data = _load_json(VALUATION_UNIVERSE_MARGIN_FILE)
    return data if isinstance(data, list) else []


def load_margin_benchmark_rules() -> Dict[str, Any]:
    """Return M10 margin benchmark rule definitions."""
    data = _load_json(MARGIN_RULES_FILE)
    return data if isinstance(data, dict) else {}


def get_industry_margin_by_task_id(task_id: Any) -> Optional[Dict[str, Any]]:
    tid = str(task_id or "").strip()
    if not tid:
        return None
    for row in load_industry_margin_taxonomy():
        if str(row.get("task_id") or "").strip() == tid:
            return row
    return None


def get_stock_model_margin_by_stock_id(stock_id: Any) -> Optional[Dict[str, Any]]:
    sid = _normalize_stock_id(stock_id)
    if not sid:
        return None
    for row in load_stock_model_data_with_margin():
        if _normalize_stock_id(row.get("stock_code")) == sid:
            return row
    return None


def get_valuation_universe_margin_by_stock_id(stock_id: Any) -> Optional[Dict[str, Any]]:
    sid = _normalize_stock_id(stock_id)
    if not sid:
        return None
    for row in load_valuation_universe_with_margin():
        if _normalize_stock_id(row.get("stock_code")) == sid:
            return row
    return None


def _margin_can_affect_valuation(margin_quality: Any, margin_rule: Any) -> bool:
    quality = str(margin_quality or "").strip().upper()
    rule = str(margin_rule or "").strip()
    if quality not in {"A", "B"}:
        return False
    if rule in {"margin_not_applicable", "event_or_cycle_tracking_only"}:
        return False
    return True


def _margin_applicable(margin_quality: Any, margin_rule: Any) -> bool:
    quality = str(margin_quality or "").strip().upper()
    rule = str(margin_rule or "").strip()
    return quality != "N/A" and rule != "margin_not_applicable"


def build_margin_benchmark_profile(stock_id: Any) -> Dict[str, Any]:
    """Build non-invasive M10 margin metadata for one stock.

    Values ending in ``_pct`` are percentage points from the source data.  Ratio
    mirrors are supplied for code that needs 0.xx percentages.
    """
    row = get_stock_model_margin_by_stock_id(stock_id)
    if not row:
        return {
            "m10_margin_available": False,
            "m10_margin_status": "missing_stock_model_data",
            "m10_margin_warning": "M10 margin benchmark row not found.",
        }

    task = get_industry_margin_by_task_id(row.get("task_id")) or {}
    source = {**task, **row}
    quality = str(source.get("margin_quality") or "").strip() or "N/A"
    rule = str(source.get("margin_rule") or "").strip()
    stock_quality = str(row.get("data_quality_grade") or "").strip().upper()
    valuation_ready = str(row.get("valuation_ready_flag") or "").strip()
    applicable = _margin_applicable(quality, rule)
    can_affect = _margin_can_affect_valuation(quality, rule)
    if stock_quality not in {"A", "B"} or valuation_ready != "ready":
        can_affect = False

    if not applicable:
        status = "not_applicable"
        warning = "M10 margin benchmark is not applicable; do not use manufacturing gross/operating margin model."
    elif stock_quality not in {"A", "B"} or valuation_ready != "ready":
        status = "stock_not_valuation_ready"
        warning = "Stock is not in A/B ready universe; show margin benchmark as background only."
    elif not can_affect:
        status = "tracking_only"
        warning = "M10 margin benchmark is tracking-only; show as risk context, not valuation uplift."
    else:
        status = "usable"
        warning = ""

    gross_base = source.get("base_gross_margin_pct")
    gross_low = source.get("gross_margin_low_pct")
    gross_high = source.get("gross_margin_high_pct")
    op_base = source.get("base_operating_margin_pct")
    op_low = source.get("operating_margin_low_pct")
    op_high = source.get("operating_margin_high_pct")

    return {
        "m10_margin_available": True,
        "m10_margin_status": status,
        "m10_margin_warning": warning,
        "m10_task_id": source.get("task_id"),
        "m10_category_name": source.get("category_name"),
        "m10_taxonomy_key": source.get("taxonomy_key"),
        "base_gross_margin_pct": gross_base,
        "gross_margin_low_pct": gross_low,
        "gross_margin_high_pct": gross_high,
        "base_operating_margin_pct": op_base,
        "operating_margin_low_pct": op_low,
        "operating_margin_high_pct": op_high,
        "base_gross_margin_ratio": _pct_to_ratio(gross_base),
        "gross_margin_low_ratio": _pct_to_ratio(gross_low),
        "gross_margin_high_ratio": _pct_to_ratio(gross_high),
        "base_operating_margin_ratio": _pct_to_ratio(op_base),
        "operating_margin_low_ratio": _pct_to_ratio(op_low),
        "operating_margin_high_ratio": _pct_to_ratio(op_high),
        "margin_quality": quality,
        "margin_rule": rule,
        "margin_profile": source.get("margin_profile"),
        "margin_model_usage": source.get("margin_model_usage"),
        "margin_reference_stocks": source.get("margin_reference_stocks"),
        "margin_notes": source.get("margin_notes"),
        "margin_source_urls": source.get("margin_source_urls"),
        "margin_model_applicable": applicable,
        "margin_can_affect_valuation": can_affect,
        "m10_data_quality_grade": row.get("data_quality_grade"),
        "m10_valuation_ready_flag": row.get("valuation_ready_flag"),
        "m10_discount_factor": row.get("discount_factor"),
    }


def merge_margin_benchmark_into_profile(profile: Dict[str, Any], stock_id: Any) -> Dict[str, Any]:
    """Return a profile copy with M10 margin metadata attached."""
    merged = dict(profile or {})
    margin = build_margin_benchmark_profile(stock_id)
    merged.update(margin)
    return merged


def validate_m10_model_data() -> Dict[str, Any]:
    """Validate the imported M10 data package counts and key constraints."""
    taxonomy = load_industry_margin_taxonomy()
    stocks = load_stock_model_data_with_margin()
    universe = load_valuation_universe_with_margin()
    rules = load_margin_benchmark_rules()

    quality_counts: Dict[str, int] = {}
    for row in taxonomy:
        q = str(row.get("margin_quality") or "N/A")
        quality_counts[q] = quality_counts.get(q, 0) + 1

    issues: List[str] = []
    if len(taxonomy) != EXPECTED_INDUSTRY_CATEGORY_COUNT:
        issues.append(f"industry_margin_taxonomy_count={len(taxonomy)}")
    if len(stocks) != EXPECTED_STOCK_MODEL_COUNT:
        issues.append(f"stock_model_data_count={len(stocks)}")
    if len(universe) != EXPECTED_VALUATION_UNIVERSE_COUNT:
        issues.append(f"valuation_universe_count={len(universe)}")
    if quality_counts != EXPECTED_MARGIN_QUALITY_COUNTS:
        issues.append(f"margin_quality_counts={quality_counts}")

    task_ids = [str(row.get("task_id") or "") for row in taxonomy]
    stock_ids = [_normalize_stock_id(row.get("stock_code")) for row in stocks]
    if len(task_ids) != len(set(task_ids)):
        issues.append("duplicate_task_id")
    if len(stock_ids) != len(set(stock_ids)):
        issues.append("duplicate_stock_code")

    for code in ["1701", "6806", "8078", "4128"]:
        if not get_stock_model_margin_by_stock_id(code):
            issues.append(f"missing_required_validation_sample_{code}")

    return {
        "ok": not issues,
        "issues": issues,
        "industry_category_count": len(taxonomy),
        "stock_model_count": len(stocks),
        "valuation_universe_count": len(universe),
        "margin_quality_counts": quality_counts,
        "margin_rule_counts": rules.get("margin_rule_counts", {}),
        "data_dir": str(MODEL_DATA_DIR),
    }


__all__ = [
    "MODEL_DATA_DIR",
    "build_margin_benchmark_profile",
    "get_industry_margin_by_task_id",
    "get_stock_model_margin_by_stock_id",
    "get_valuation_universe_margin_by_stock_id",
    "load_industry_margin_taxonomy",
    "load_margin_benchmark_rules",
    "load_stock_model_data_with_margin",
    "load_valuation_universe_with_margin",
    "merge_margin_benchmark_into_profile",
    "validate_m10_model_data",
]
