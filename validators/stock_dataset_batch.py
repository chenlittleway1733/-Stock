"""Batch import helpers for stock dataset validation.

This module turns model-data spreadsheets or CSV files into the canonical
record format consumed by stock_dataset_validation.  It is intentionally a
pre-write gate: it produces validation reports and never mutates model files.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import pandas as pd

from .stock_dataset_validation import expected_yahoo_symbol, normalize_stock_code, validate_stock_dataset


PREFERRED_SHEETS = (
    "M03模型主表_clean",
    "股票明細",
    "M06估值AB_scored",
    "M07資料驗證清單",
)

COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "task_id": ("task_id", "任務ID"),
    "category_name": ("category_name", "分類"),
    "stock_code": ("stock_code", "代號", "股票代號"),
    "stock_name": ("stock_name", "名稱", "股票名稱"),
    "market_suffix": ("market_suffix", "市場別/尾碼", "市場", "市場別"),
    "yahoo_symbol": ("yahoo_symbol", "Yahoo Symbol", "Yahoo"),
    "current_price": ("current_price", "現價", "收盤價"),
    "price_date": ("price_date", "價格日期", "現價日期"),
    "price_change_pct": ("price_change_pct", "漲跌幅%"),
    "analyst_target_avg": ("analyst_target_avg", "法人平均目標價", "目標價", "平均目標價"),
    "target_date": ("target_date", "目標價日期"),
    "fy_eps": ("fy_eps", "FY EPS", "Forward EPS", "預估EPS"),
    "eps_year": ("eps_year", "EPS年度", "EPS 年度"),
    "upside_pct": ("upside_pct", "上行空間%", "上行空間"),
    "forward_pe": ("forward_pe", "Forward P/E", "Forward PE", "前瞻本益比"),
    "data_quality_grade": ("data_quality_grade", "資料品質等級", "資料品質"),
    "include_in_valuation_model": ("include_in_valuation_model", "是否納入估值模型"),
    "discount_factor": ("discount_factor", "資料降權係數", "降權係數"),
    "weighted_upside_pct": ("weighted_upside_pct", "加權上行空間%"),
    "valuation_ready_flag": ("valuation_ready_flag",),
    "pe_cap_rule": ("pe_cap_rule",),
    "model_risk_tags": ("model_risk_tags", "模型風險標籤", "風險標籤"),
    "model_usage_advice": ("model_usage_advice", "模型使用建議"),
    "review_priority": ("review_priority", "優先複核等級", "優先複核"),
    "training_sample_use": ("training_sample_use", "訓練樣本用途"),
    "status": ("status", "狀態"),
    "remarks": ("remarks", "備註", "缺值/備註"),
    "price_source_url": ("price_source_url", "現價來源URL", "來源URL"),
    "target_source_url": ("target_source_url", "目標價來源URL"),
    "eps_source_url": ("eps_source_url", "EPS來源URL"),
}


def _clean_column_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s_\-／/（）()]+", "", text)


def _source_from_bytes(source: Any) -> Any:
    if isinstance(source, (bytes, bytearray)):
        return io.BytesIO(source)
    return source


def _column_score(columns: Any) -> int:
    normalized = {_clean_column_name(c) for c in columns}
    score = 0
    for canonical, weight in {
        "stock_code": 4,
        "stock_name": 4,
        "data_quality_grade": 2,
        "current_price": 1,
        "analyst_target_avg": 1,
        "fy_eps": 1,
    }.items():
        aliases = {_clean_column_name(alias) for alias in COLUMN_ALIASES.get(canonical, ())}
        if normalized & aliases:
            score += weight
    return score


def _choose_excel_sheet(excel: pd.ExcelFile, preferred_sheet: Optional[str] = None) -> str:
    if preferred_sheet:
        if preferred_sheet not in excel.sheet_names:
            raise ValueError(f"找不到指定工作表：{preferred_sheet}")
        return preferred_sheet

    for sheet in PREFERRED_SHEETS:
        if sheet in excel.sheet_names:
            return sheet

    best_sheet = excel.sheet_names[0]
    best_score = -1
    for sheet in excel.sheet_names:
        try:
            preview = pd.read_excel(excel, sheet_name=sheet, nrows=8)
        except Exception:
            continue
        score = _column_score(preview.columns)
        if score > best_score:
            best_sheet = sheet
            best_score = score
    return best_sheet


def read_stock_dataset_file(
    source: Any,
    *,
    filename: str = "",
    preferred_sheet: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Read a stock dataset CSV/XLSX and return raw DataFrame plus metadata."""
    source = _source_from_bytes(source)
    file_name = filename or str(source)
    ext = Path(file_name).suffix.lower()

    if ext in {".csv", ".txt"}:
        df = pd.read_csv(source)
        return df, {"file_name": file_name, "file_type": "csv", "sheet_name": None, "available_sheets": []}

    if ext in {".xlsx", ".xlsm", ".xls"}:
        try:
            excel = pd.ExcelFile(source)
        except ImportError as exc:
            raise RuntimeError("讀取 Excel 需要 openpyxl，請確認 requirements.txt 已安裝 openpyxl。") from exc
        sheet_name = _choose_excel_sheet(excel, preferred_sheet)
        df = pd.read_excel(excel, sheet_name=sheet_name)
        return df, {
            "file_name": file_name,
            "file_type": "excel",
            "sheet_name": sheet_name,
            "available_sheets": list(excel.sheet_names),
        }

    raise ValueError(f"不支援的檔案格式：{ext or file_name}")


def normalize_stock_dataset_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Map English/Chinese spreadsheet columns into validation canonical fields."""
    df = df.copy()
    clean_to_source = {_clean_column_name(col): col for col in df.columns if not str(col).startswith("Unnamed:")}
    output = pd.DataFrame(index=df.index)

    for canonical, aliases in COLUMN_ALIASES.items():
        source_col = None
        for alias in aliases:
            source_col = clean_to_source.get(_clean_column_name(alias))
            if source_col is not None:
                break
        if source_col is not None:
            output[canonical] = df[source_col]

    if "stock_code" not in output.columns:
        output["stock_code"] = ""
    if "stock_name" not in output.columns:
        output["stock_name"] = ""

    output.insert(0, "source_row_number", [int(i) + 2 for i in range(len(output))])
    output["stock_code"] = output["stock_code"].map(normalize_stock_code)
    output["stock_name"] = output["stock_name"].fillna("").astype(str).str.strip()

    if "market_suffix" not in output.columns:
        output["market_suffix"] = ""
    output["market_suffix"] = output["market_suffix"].fillna("").astype(str).str.strip()

    if "yahoo_symbol" not in output.columns:
        output["yahoo_symbol"] = ""
    output["yahoo_symbol"] = output["yahoo_symbol"].fillna("").astype(str).str.strip()

    def infer_suffix(row: Mapping[str, Any]) -> str:
        suffix = str(row.get("market_suffix") or "").strip()
        if suffix:
            return suffix
        symbol = str(row.get("yahoo_symbol") or "").strip()
        if symbol.endswith(".TW"):
            return "TW"
        if symbol.endswith(".TWO"):
            return "TWO"
        return ""

    output["market_suffix"] = output.apply(infer_suffix, axis=1)

    missing_symbol = output["yahoo_symbol"].eq("") & output["stock_code"].ne("") & output["market_suffix"].ne("")
    output.loc[missing_symbol, "yahoo_symbol"] = output.loc[missing_symbol].apply(
        lambda row: expected_yahoo_symbol(row.get("stock_code"), row.get("market_suffix")),
        axis=1,
    )

    keep_mask = output["stock_code"].astype(str).str.strip().ne("") | output["stock_name"].astype(str).str.strip().ne("")
    return output.loc[keep_mask].reset_index(drop=True)


def validate_stock_dataset_frame(
    df: pd.DataFrame,
    *,
    source_meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    normalized = normalize_stock_dataset_dataframe(df)
    dataset = validate_stock_dataset(normalized.to_dict("records"))
    report = pd.DataFrame(dataset["reports"]).drop(columns=["issues"], errors="ignore")

    base_cols = [
        "source_row_number",
        "task_id",
        "category_name",
        "stock_code",
        "stock_name",
        "market_suffix",
        "yahoo_symbol",
        "data_quality_grade",
        "include_in_valuation_model",
        "valuation_ready_flag",
    ]
    present_base_cols = [c for c in base_cols if c in normalized.columns]
    if not report.empty:
        report = pd.concat(
            [
                normalized[present_base_cols].reset_index(drop=True),
                report.drop(columns=[c for c in ("stock_code", "stock_name") if c in report.columns], errors="ignore").reset_index(drop=True),
            ],
            axis=1,
        )

    issues = pd.DataFrame(dataset["issues"])
    if not issues.empty:
        lookup_cols = [c for c in ("source_row_number", "task_id", "category_name", "data_quality_grade") if c in normalized.columns]
        lookup = normalized.reset_index(names="row_index")[["row_index", *lookup_cols]]
        issues = issues.merge(lookup, on="row_index", how="left")
        front = ["source_row_number", "task_id", "category_name", "stock_code", "stock_name", "data_quality_grade"]
        ordered = [c for c in front if c in issues.columns] + [c for c in issues.columns if c not in front]
        issues = issues[ordered]

    summary = {
        "source": dict(source_meta or {}),
        "total": dataset["total"],
        "pass_count": dataset["pass_count"],
        "issue_count": dataset["issue_count"],
        "status_counts": dataset["status_counts"],
        "severity_counts": dataset["severity_counts"],
        "rule_counts": dataset["rule_counts"],
    }
    return {
        "summary": summary,
        "normalized_records": normalized,
        "report": report,
        "issues": issues,
        "raw_dataset": dataset,
    }


def _safe_stem(name: str) -> str:
    stem = Path(name or "stock_dataset").stem
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", stem)
    return stem.strip("._") or "stock_dataset"


def write_stock_dataset_validation_artifacts(
    result: Mapping[str, Any],
    *,
    output_dir: str | Path = "output/validation",
    source_name: str = "stock_dataset",
) -> Dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(source_name)

    report_path = out_dir / f"{stem}_validation_report.csv"
    issues_path = out_dir / f"{stem}_validation_issues.csv"
    summary_path = out_dir / f"{stem}_validation_summary.json"

    result["report"].to_csv(report_path, index=False, encoding="utf-8-sig")
    result["issues"].to_csv(issues_path, index=False, encoding="utf-8-sig")
    summary_path.write_text(json.dumps(result["summary"], ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "report_csv": str(report_path),
        "issues_csv": str(issues_path),
        "summary_json": str(summary_path),
    }


def validate_stock_dataset_file(
    source: Any,
    *,
    filename: str = "",
    preferred_sheet: Optional[str] = None,
    output_dir: str | Path = "output/validation",
) -> Dict[str, Any]:
    raw_df, meta = read_stock_dataset_file(source, filename=filename or str(source), preferred_sheet=preferred_sheet)
    result = validate_stock_dataset_frame(raw_df, source_meta=meta)
    result["artifact_paths"] = write_stock_dataset_validation_artifacts(
        result,
        output_dir=output_dir,
        source_name=meta.get("file_name") or filename or str(source),
    )
    return result


__all__ = [
    "COLUMN_ALIASES",
    "PREFERRED_SHEETS",
    "normalize_stock_dataset_dataframe",
    "read_stock_dataset_file",
    "validate_stock_dataset_file",
    "validate_stock_dataset_frame",
    "write_stock_dataset_validation_artifacts",
]
