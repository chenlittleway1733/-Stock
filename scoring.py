"""
投資評分模型模組：
把策略漏斗掃描器的多因子評分邏輯從 UI 層拆出，方便日後調整權重、回測與批次掃描。

設計原則：
1. UI 只負責顯示與按鈕互動。
2. scoring.py 負責分數計算、權重正規化、最小回測。
3. 不直接呼叫外部 API，避免與 services.py 耦合過深。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd


def safe_float(value: Any) -> Optional[float]:
    """安全轉成 float；失敗、NaN、空字串都回傳 None。"""
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
            if value == "" or value.upper() in {"N/A", "NA", "NULL", "NONE"}:
                return None
        v = float(value)
        if pd.isna(v):
            return None
        return v
    except Exception:
        return None


def clamp_score(value: Any, low: float = 0.0, high: float = 100.0) -> float:
    """把分數限制在 0~100。"""
    v = safe_float(value)
    if v is None:
        return 50.0
    return max(low, min(high, v))


def pct_score(x: Any, center: float = 0.0, scale: float = 2.0) -> Optional[float]:
    """
    將百分比型因子轉為 0~100 分。
    x 使用小數格式，例如 0.1 = 10%。
    """
    v = safe_float(x)
    if v is None:
        return None
    return clamp_score(50.0 + (v - center) * 100.0 * scale)


def normalize_screener_weights(
    valuation: Any,
    growth: Any,
    chip: Any,
    revenue: Any,
) -> Tuple[Dict[str, float], bool]:
    """
    將 UI 的 0~100 權重正規化為總和 1。
    回傳：(weights, used_fallback)。
    """
    raw = {
        "valuation": safe_float(valuation) or 0.0,
        "growth": safe_float(growth) or 0.0,
        "chip": safe_float(chip) or 0.0,
        "revenue": safe_float(revenue) or 0.0,
    }
    total = sum(raw.values())
    if total <= 0:
        return {"valuation": 0.25, "growth": 0.25, "chip": 0.25, "revenue": 0.25}, True
    return {k: v / total for k, v in raw.items()}, False


def _latest_revenue_values(monthly_revenue_df: Any) -> Dict[str, Optional[float]]:
    """從月營收 DataFrame 取最近一筆 YoY/MoM。YoY/MoM 在原系統中是百分比數字，例如 25.3。"""
    out = {"yoy_pct": None, "mom_pct": None}
    try:
        if monthly_revenue_df is None or monthly_revenue_df.empty:
            return out
        if "YoY" in monthly_revenue_df.columns:
            out["yoy_pct"] = safe_float(monthly_revenue_df["YoY"].iloc[-1])
        if "MoM" in monthly_revenue_df.columns:
            out["mom_pct"] = safe_float(monthly_revenue_df["MoM"].iloc[-1])
    except Exception:
        pass
    return out


def calculate_strategy_score(
    info: Dict[str, Any],
    monthly_revenue_df: Any = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    計算策略漏斗掃描器分數。

    Parameters
    ----------
    info:
        get_stock_data() 回傳的 yfinance/info 類資料。
    monthly_revenue_df:
        get_monthly_revenue() 回傳的月營收資料；若有資料，營收成長優先使用官方月營收 YoY。
    weights:
        已正規化權重，keys: valuation/growth/chip/revenue。

    Returns
    -------
    dict:
        total_score 與各子分數、PEG 顯示、YoY/MoM 等。
    """
    info = info or {}
    weights = weights or {"valuation": 0.35, "growth": 0.30, "chip": 0.20, "revenue": 0.15}

    pe = safe_float(info.get("trailingPE"))
    roe = safe_float(info.get("returnOnEquity"))
    earnings_growth = safe_float(info.get("earningsGrowth"))
    revenue_growth = safe_float(info.get("revenueGrowth"))
    sys_peg = safe_float(info.get("pegRatio"))

    latest_rv = _latest_revenue_values(monthly_revenue_df)
    yoy_pct = latest_rv["yoy_pct"]
    mom_pct = latest_rv["mom_pct"]

    # 若 EPS 成長缺值，以月營收 YoY 粗略代理；原 UI 邏輯即採此做法。
    if earnings_growth is None and yoy_pct is not None:
        earnings_growth = yoy_pct / 100.0

    # 營收成長以官方月營收 YoY 優先。
    if yoy_pct is not None:
        revenue_growth = yoy_pct / 100.0

    peg_is_neg = earnings_growth is not None and earnings_growth <= 0
    if (sys_peg is None) and pe and earnings_growth and earnings_growth > 0:
        sys_peg = pe / (earnings_growth * 100.0)

    # 1) 估值分數：PEG 越低越好，PE 過高扣分。
    peg_score = None
    if sys_peg is not None and sys_peg > 0 and not peg_is_neg:
        peg_score = clamp_score(100.0 - sys_peg * 30.0)
    pe_score = clamp_score(100.0 - pe * 2.0) if pe is not None and pe > 0 else None
    val_components = [v for v in [peg_score, pe_score] if v is not None]
    valuation_score = sum(val_components) / len(val_components) if val_components else 50.0

    # 2) 成長分數：EPS/營收成長。
    growth_components = []
    eg_score = pct_score(earnings_growth, center=0.0, scale=2.5)
    rg_score = pct_score(revenue_growth, center=0.0, scale=2.0)
    if eg_score is not None:
        growth_components.append(eg_score)
    if rg_score is not None:
        growth_components.append(rg_score)
    growth_score = sum(growth_components) / len(growth_components) if growth_components else 50.0

    # 3) 籌碼分數：機構/內部人持股。
    held_inst = safe_float(info.get("heldPercentInstitutions"))
    held_inside = safe_float(info.get("heldPercentInsiders"))
    chip_components = []
    if held_inst is not None:
        chip_components.append(clamp_score(held_inst * 200.0))
    if held_inside is not None:
        chip_components.append(clamp_score(held_inside * 250.0))
    chip_score = sum(chip_components) / len(chip_components) if chip_components else 50.0

    # 4) 營收動能分數：YoY 70% + MoM 30%。YoY/MoM 是百分比數字。
    revenue_score = 50.0
    if yoy_pct is not None or mom_pct is not None:
        yoy_score = clamp_score(50.0 + ((yoy_pct or 0.0) * 1.5))
        mom_score = clamp_score(50.0 + ((mom_pct or 0.0) * 2.0))
        revenue_score = yoy_score * 0.7 + mom_score * 0.3

    total_score = (
        valuation_score * weights.get("valuation", 0.35)
        + growth_score * weights.get("growth", 0.30)
        + chip_score * weights.get("chip", 0.20)
        + revenue_score * weights.get("revenue", 0.15)
    )

    peg_display = "分母為負" if peg_is_neg else (f"{sys_peg:.2f}" if sys_peg is not None else "N/A")

    warnings = []
    if pe is None:
        warnings.append("P/E 缺值")
    if sys_peg is None and not peg_is_neg:
        warnings.append("PEG 缺值")
    if yoy_pct is None:
        warnings.append("月營收 YoY 缺值")
    if held_inst is None and held_inside is None:
        warnings.append("籌碼持股資料缺值")

    return {
        "total_score": total_score,
        "valuation_score": valuation_score,
        "growth_score": growth_score,
        "chip_score": chip_score,
        "revenue_score": revenue_score,
        "pe": pe,
        "roe": roe,
        "peg": sys_peg,
        "peg_is_negative_growth": peg_is_neg,
        "peg_display": peg_display,
        "yoy_pct": yoy_pct,
        "mom_pct": mom_pct,
        "warnings": warnings,
    }


def backtest_return_from_hist(hist_df: Any, days: int) -> Optional[float]:
    """最小回測：用最近收盤 vs N 天前最近可用收盤計算報酬率(%)。"""
    try:
        if hist_df is None or hist_df.empty or "Close" not in hist_df.columns:
            return None
        h = hist_df[["Close"]].dropna().sort_index()
        if len(h) < 2:
            return None
        end_idx = h.index[-1]
        end_close = float(h["Close"].iloc[-1])
        target_dt = end_idx - pd.Timedelta(days=days)
        past = h[h.index <= target_dt]
        if past.empty:
            return None
        start_close = float(past["Close"].iloc[-1])
        if start_close <= 0:
            return None
        return (end_close / start_close - 1.0) * 100.0
    except Exception:
        return None


def score_icon(total_score: Any) -> str:
    """依總分回傳 UI icon。"""
    score = safe_float(total_score) or 0.0
    if score >= 70:
        return "🔥"
    if score >= 60:
        return "⭐"
    return "🔸"
