"""
Dynamic Cap 2.0 係數校準模型（第 17-B-1 階段）。

設計原則：
- 不再採用「產業基準 + 各項絕對倍數」加總，避免倍率連續堆高。
- 改為「產業基準 × 成長係數 × 品質係數 × 題材係數 × 規模係數 × 風險折扣」。
- 每一個係數有單項上限，最終倍率再套用產業 hard ceiling。
- 毛利率改採相對產業基準，缺少產業基準時保守處理。
- 台灣關鍵半導體供應鏈加入地緣政治折價，特別避免台積電類超大型晶圓代工龍頭被推到過高 P/E。
- P/B 週期股與題材 / 事件股仍不輸出 P/E 買進倍率。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pandas as pd


def _sf(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
            if x in {"", "None", "nan", "NULL", "N/A", "—"}:
                return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _pct01(x: Any) -> Optional[float]:
    """接受 0.25 或 25 兩種百分比口徑，統一轉成 0.25。"""
    v = _sf(x)
    if v is None:
        return None
    if abs(v) > 3:
        return v / 100.0
    return v


def _fmt_x(x: Any, digits: int = 1) -> str:
    v = _sf(x)
    return "NULL" if v is None else f"{v:.{digits}f}x"


def _fmt_pct(x: Any, digits: int = 1) -> str:
    v = _pct01(x)
    return "NULL" if v is None else f"{v*100:.{digits}f}%"


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _add_row(rows: List[Dict[str, Any]], kind: str, name: str, value: Any, reason: str) -> None:
    rows.append({"類型": kind, "項目": name, "倍率/係數": value, "說明": reason})


def _add_factor(rows: List[Dict[str, Any]], name: str, factor: float, reason: str) -> None:
    _add_row(rows, "係數項", name, f"×{factor:.3f}", reason)


def _add_discount(rows: List[Dict[str, Any]], name: str, factor: float, reason: str) -> None:
    _add_row(rows, "折扣項", name, f"×{factor:.3f}", reason)


# 未在 taxonomy.py 明確設定時，由此表提供保守校準。
# base_pe 以「可解釋公式倍率」為主，不是追價倍數；hard_ceiling 為強制截斷上限。
CALIBRATION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "FOUNDRY": {
        "base_pe": 24.0, "floor_pe": 16.0, "soft_ceiling_pe": 30.0, "hard_ceiling_pe": 35.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.10, "max_theme_factor": 1.06, "max_scale_factor": 1.00,
        "gross_margin_baseline": 0.54, "gross_margin_good": 0.58, "gross_margin_excellent": 0.62,
        "baked_in_themes": ["ai", "hpc", "cowos", "先進製程"],
        "geopolitical_factor": 0.92,
        "geopolitical_note": "台灣關鍵半導體供應鏈地緣政治折價；超大型晶圓代工龍頭不宜用 40x 以上作操作倍率。",
    },
    "IC_DESIGN_ASIC": {
        "base_pe": 35.0, "floor_pe": 22.0, "soft_ceiling_pe": 55.0, "hard_ceiling_pe": 70.0,
        "max_growth_factor": 1.25, "max_quality_factor": 1.22, "max_theme_factor": 1.18, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.42, "gross_margin_good": 0.48, "gross_margin_excellent": 0.55,
        "baked_in_themes": ["asic", "ai晶片", "ai asic"],
        "geopolitical_factor": 0.97,
    },
    "IP_EDA_DESIGN_SERVICE": {
        "base_pe": 42.0, "floor_pe": 25.0, "soft_ceiling_pe": 65.0, "hard_ceiling_pe": 80.0,
        "max_growth_factor": 1.25, "max_quality_factor": 1.25, "max_theme_factor": 1.15, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.55, "gross_margin_good": 0.65, "gross_margin_excellent": 0.75,
        "baked_in_themes": ["ip", "eda", "矽智財"],
        "geopolitical_factor": 0.97,
    },
    "OSAT_TESTING": {
        "base_pe": 24.0, "floor_pe": 15.0, "soft_ceiling_pe": 35.0, "hard_ceiling_pe": 42.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.12, "max_theme_factor": 1.10, "max_scale_factor": 1.04,
        "gross_margin_baseline": 0.22, "gross_margin_good": 0.28, "gross_margin_excellent": 0.35,
        "baked_in_themes": ["先進封裝", "cowos"], "geopolitical_factor": 0.96,
    },
    "PROBE_TEST_INTERFACE": {
        "base_pe": 34.0, "floor_pe": 22.0, "soft_ceiling_pe": 50.0, "hard_ceiling_pe": 60.0,
        "max_growth_factor": 1.22, "max_quality_factor": 1.20, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.38, "gross_margin_good": 0.45, "gross_margin_excellent": 0.52,
        "baked_in_themes": ["測試", "探針"], "geopolitical_factor": 0.97,
    },
    "SEMICAP_COWOS_EQUIPMENT": {
        "base_pe": 32.0, "floor_pe": 20.0, "soft_ceiling_pe": 48.0, "hard_ceiling_pe": 58.0,
        "max_growth_factor": 1.22, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.30, "gross_margin_good": 0.38, "gross_margin_excellent": 0.45,
        "baked_in_themes": ["cowos", "先進封裝", "設備"], "geopolitical_factor": 0.96,
    },
    "FAB_FACILITY_MATERIALS": {
        "base_pe": 26.0, "floor_pe": 16.0, "soft_ceiling_pe": 38.0, "hard_ceiling_pe": 45.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.12, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.24, "gross_margin_good": 0.30, "gross_margin_excellent": 0.36,
        "baked_in_themes": ["廠務", "材料"], "geopolitical_factor": 0.96,
    },
    "ABF_SUBSTRATE": {
        "base_pe": 30.0, "floor_pe": 18.0, "soft_ceiling_pe": 45.0, "hard_ceiling_pe": 55.0,
        "max_growth_factor": 1.20, "max_quality_factor": 1.16, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.23, "gross_margin_good": 0.30, "gross_margin_excellent": 0.38,
        "baked_in_themes": ["abf", "ai載板", "hpc", "載板"],
        "cyclical_low_base_cap": True,
    },
    "SERVER_PCB_BOARD": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 42.0, "hard_ceiling_pe": 52.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.14, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.18, "gross_margin_good": 0.24, "gross_margin_excellent": 0.30,
        "baked_in_themes": ["ai伺服器", "高階pcb"],
    },
    "AI_SERVER_ODM": {
        "base_pe": 24.0, "floor_pe": 14.0, "soft_ceiling_pe": 34.0, "hard_ceiling_pe": 42.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.15, "max_theme_factor": 1.08, "max_scale_factor": 1.03,
        "gross_margin_baseline": 0.06, "gross_margin_good": 0.09, "gross_margin_excellent": 0.12,
        "baked_in_themes": ["ai", "ai伺服器", "資料中心"],
    },
    "CONNECTOR_CABLE": {
        "base_pe": 30.0, "floor_pe": 18.0, "soft_ceiling_pe": 45.0, "hard_ceiling_pe": 55.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.16, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.25, "gross_margin_good": 0.32, "gross_margin_excellent": 0.40,
        "baked_in_themes": ["高速傳輸", "連接器"],
    },
    "SERVER_CHASSIS_RAIL": {
        "base_pe": 26.0, "floor_pe": 16.0, "soft_ceiling_pe": 38.0, "hard_ceiling_pe": 45.0,
        "max_growth_factor": 1.15, "max_quality_factor": 1.12, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.20, "gross_margin_good": 0.26, "gross_margin_excellent": 0.32,
        "baked_in_themes": ["機構件", "滑軌", "機殼"],
    },
    "POWER_BBU": {
        "base_pe": 26.0, "floor_pe": 16.0, "soft_ceiling_pe": 38.0, "hard_ceiling_pe": 46.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.12, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.18, "gross_margin_good": 0.24, "gross_margin_excellent": 0.30,
        "baked_in_themes": ["電源", "bbu"],
    },
    "THERMAL_LIQUID_COOLING": {
        "base_pe": 34.0, "floor_pe": 20.0, "soft_ceiling_pe": 50.0, "hard_ceiling_pe": 62.0,
        "max_growth_factor": 1.20, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.26, "gross_margin_good": 0.32, "gross_margin_excellent": 0.40,
        "baked_in_themes": ["水冷", "液冷", "散熱"],
    },
    "OPTICAL_COMM_SILICON_PHOTONICS": {
        "base_pe": 36.0, "floor_pe": 22.0, "soft_ceiling_pe": 55.0, "hard_ceiling_pe": 68.0,
        "max_growth_factor": 1.22, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.32, "gross_margin_good": 0.40, "gross_margin_excellent": 0.48,
        "baked_in_themes": ["矽光子", "cpo", "800g", "1.6t"],
    },
    "NETWORK_SWITCH": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 42.0, "hard_ceiling_pe": 52.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.14, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.24, "gross_margin_good": 0.32, "gross_margin_excellent": 0.40,
        "baked_in_themes": ["交換器", "網通"],
    },
    "OPTICS_LENS_MODULE": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 42.0, "hard_ceiling_pe": 52.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.20, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.38, "gross_margin_good": 0.48, "gross_margin_excellent": 0.58,
        "baked_in_themes": ["光學", "鏡頭"],
    },
    "ROBOTICS_AUTOMATION": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 42.0, "hard_ceiling_pe": 52.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.14, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.28, "gross_margin_good": 0.36, "gross_margin_excellent": 0.45,
        "baked_in_themes": ["機器人", "自動化"],
    },
    "SPACE_LEO_SATELLITE": {
        "base_pe": 30.0, "floor_pe": 16.0, "soft_ceiling_pe": 45.0, "hard_ceiling_pe": 55.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.14, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.25, "gross_margin_good": 0.33, "gross_margin_excellent": 0.42,
        "baked_in_themes": ["低軌", "衛星", "太空"],
    },
    "EV_AUTO_ELECTRONICS": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 42.0, "hard_ceiling_pe": 50.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.14, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.22, "gross_margin_good": 0.30, "gross_margin_excellent": 0.38,
        "baked_in_themes": ["車用", "電動車"],
    },
    "GRID_POWER_STORAGE": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 38.0, "hard_ceiling_pe": 46.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.15, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.18, "gross_margin_good": 0.24, "gross_margin_excellent": 0.30,
        "baked_in_themes": ["重電", "電網", "儲能"],
    },
    "SOFTWARE_SECURITY_CLOUD": {
        "base_pe": 32.0, "floor_pe": 18.0, "soft_ceiling_pe": 50.0, "hard_ceiling_pe": 60.0,
        "max_growth_factor": 1.20, "max_quality_factor": 1.20, "max_theme_factor": 1.08, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.45, "gross_margin_good": 0.55, "gross_margin_excellent": 0.65,
        "baked_in_themes": ["資安", "雲端", "軟體"],
    },
    "GENERAL": {
        "base_pe": 20.0, "floor_pe": 10.0, "soft_ceiling_pe": 28.0, "hard_ceiling_pe": 35.0,
        "max_growth_factor": 1.12, "max_quality_factor": 1.10, "max_theme_factor": 1.05, "max_scale_factor": 1.03,
        "gross_margin_baseline": None,
    },
}


def _calibration(industry_profile: Dict[str, Any]) -> Dict[str, Any]:
    key = str(industry_profile.get("model_key") or industry_profile.get("taxon_key") or "GENERAL")
    c = dict(CALIBRATION_DEFAULTS.get(key, CALIBRATION_DEFAULTS.get("GENERAL", {})))
    # 若 taxonomy 已明確設新欄位，允許覆寫；舊 base_pe/pe_range 不直接覆寫保守校準，避免舊表過度樂觀。
    for k in [
        "floor_pe", "soft_ceiling_pe", "hard_ceiling_pe",
        "max_growth_factor", "max_quality_factor", "max_theme_factor", "max_scale_factor",
        "gross_margin_baseline", "gross_margin_good", "gross_margin_excellent",
        "baked_in_themes", "geopolitical_factor", "geopolitical_note",
    ]:
        if industry_profile.get(k) is not None:
            c[k] = industry_profile.get(k)
    if c.get("base_pe") is None:
        c["base_pe"] = _sf(industry_profile.get("base_pe"), 20.0) or 20.0
    return c


def _growth_to_factor(growth: Optional[float]) -> float:
    if growth is None:
        return 1.00
    if growth < -0.20:
        return 0.85
    if growth < 0:
        return 0.92
    if growth < 0.10:
        return 1.00
    if growth < 0.20:
        return 1.05
    if growth < 0.35:
        return 1.10
    if growth < 0.60:
        return 1.15
    if growth < 1.00:
        return 1.20
    return 1.25


def growth_factor_hierarchical(
    *,
    system_forward_eps: Any = None,
    ai_forward_eps: Any = None,
    consensus_forward_eps: Any = None,
    ttm_eps: Any = None,
    ai_ttm_eps: Any = None,
    revenue_yoy: Any = None,
    revenue_yoy_3m: Any = None,
    industry_profile: Dict[str, Any] = None,
    calibration: Dict[str, Any] = None,
    roe: Any = None,
    gross_margin: Any = None,
) -> Dict[str, Any]:
    """成長係數只採一個最高優先資料源，避免重複加分。"""
    industry_profile = industry_profile or {}
    calibration = calibration or {}
    base_eps = _sf(ttm_eps) or _sf(ai_ttm_eps)
    consensus = _sf(consensus_forward_eps)
    system_f = _sf(system_forward_eps)
    ai_f = _sf(ai_forward_eps)

    src = None
    growth = None
    if base_eps and base_eps > 0 and consensus and consensus > 0:
        growth = (consensus - base_eps) / base_eps
        src = "法人共識 Forward EPS 成長"
    elif base_eps and base_eps > 0 and system_f and system_f > 0:
        growth = (system_f - base_eps) / base_eps
        src = "系統 Forward EPS 成長"
    elif base_eps and base_eps > 0 and ai_f and ai_f > 0:
        growth = (ai_f - base_eps) / base_eps
        src = "AI Forward EPS 成長"
    elif _pct01(revenue_yoy_3m) is not None:
        growth = _pct01(revenue_yoy_3m)
        src = "近三個月營收 YoY 平均"
    elif _pct01(revenue_yoy) is not None:
        growth = _pct01(revenue_yoy)
        src = "最新單月 / 最新可得營收 YoY"

    if growth is None:
        return {"factor": 1.00, "reason": "缺少 Forward EPS 或營收 YoY，成長係數 ×1.00", "source": "none", "growth": None}

    factor = _growth_to_factor(growth)
    reason = f"採用{src}：{_fmt_pct(growth)}；低優先級成長項不重複加分"

    # 循環股低基期修復：EPS 成長很高，但 ROE / 毛利未改善時不可視為長期結構成長。
    cyc = bool(industry_profile.get("cyclical"))
    r = _pct01(roe)
    gm = _pct01(gross_margin)
    gm_base = calibration.get("gross_margin_baseline")
    gm_base = _sf(gm_base)
    if cyc and growth is not None and growth > 1.0:
        cap = 1.18
        if (r is not None and r < 0.10) or (gm is not None and gm_base is not None and gm < gm_base):
            cap = 1.12
            reason += "；循環股高成長疑似低基期修復，且 ROE/毛利未同步改善，成長係數保守上限 ×1.12"
        else:
            reason += "；循環股高成長採低基期折扣，成長係數上限 ×1.18"
        factor = min(factor, cap)

    max_f = _sf(calibration.get("max_growth_factor"), 1.20) or 1.20
    clipped = min(factor, max_f)
    if clipped < factor:
        reason += f"；套用產業成長係數上限 ×{max_f:.2f}"
    return {"factor": round(clipped, 4), "reason": reason, "source": src, "growth": growth}


def quality_factor_relative(
    gross_margin: Any,
    roe: Any = None,
    revenue_yoy: Any = None,
    eps_positive: bool = True,
    debt_to_equity: Any = None,
    warning_count: int = 0,
    calibration: Dict[str, Any] = None,
) -> Dict[str, Any]:
    calibration = calibration or {}
    gm = _pct01(gross_margin)
    roev = _pct01(roe)
    de = _sf(debt_to_equity)
    max_q = _sf(calibration.get("max_quality_factor"), 1.12) or 1.12
    gm_base = _sf(calibration.get("gross_margin_baseline"))
    gm_good = _sf(calibration.get("gross_margin_good"))
    gm_excellent = _sf(calibration.get("gross_margin_excellent"))

    if not eps_positive:
        return {"factor": 1.00, "reason": "EPS 不穩或為負，不給品質係數溢價"}

    factor = 1.00
    notes = []

    if gm is None:
        notes.append("毛利率缺值")
    elif gm_base is None:
        # 缺產業基準時，只給非常保守的絕對毛利加分。
        if gm >= 0.45:
            factor *= 1.05
            notes.append(f"缺少產業毛利基準；毛利率 {_fmt_pct(gm)} 僅保守給 ×1.05")
        elif gm < 0.10:
            factor *= 0.90
            notes.append(f"缺少產業毛利基準；毛利率 {_fmt_pct(gm)} 偏低，品質折價")
        else:
            notes.append(f"缺少產業毛利基準；毛利率 {_fmt_pct(gm)} 不加分")
    else:
        if gm < gm_base - 0.08:
            factor *= 0.90
            notes.append(f"毛利率 {_fmt_pct(gm)} 明顯低於產業基準 {_fmt_pct(gm_base)}")
        elif gm < gm_base:
            factor *= 0.96
            notes.append(f"毛利率 {_fmt_pct(gm)} 略低於產業基準 {_fmt_pct(gm_base)}")
        elif gm_excellent is not None and gm >= gm_excellent:
            factor *= 1.16
            notes.append(f"毛利率 {_fmt_pct(gm)} 高於產業 excellent 門檻 {_fmt_pct(gm_excellent)}")
        elif gm_good is not None and gm >= gm_good:
            factor *= 1.10
            notes.append(f"毛利率 {_fmt_pct(gm)} 高於產業 good 門檻 {_fmt_pct(gm_good)}")
        elif gm >= gm_base:
            factor *= 1.04
            notes.append(f"毛利率 {_fmt_pct(gm)} 略高於產業基準 {_fmt_pct(gm_base)}")

    if roev is None:
        notes.append("ROE 缺值")
    elif roev < 0:
        factor *= 0.85
        notes.append(f"ROE {_fmt_pct(roev)} 為負")
    elif roev < 0.08:
        factor *= 0.94
        notes.append(f"ROE {_fmt_pct(roev)} 偏低")
    elif roev >= 0.35:
        factor *= 1.10
        notes.append(f"ROE {_fmt_pct(roev)} 極佳")
    elif roev >= 0.25:
        factor *= 1.07
        notes.append(f"ROE {_fmt_pct(roev)} 優良")
    elif roev >= 0.15:
        factor *= 1.04
        notes.append(f"ROE {_fmt_pct(roev)} 正常偏佳")

    rev = _pct01(revenue_yoy)
    if rev is not None and rev < 0 and factor > 1.0:
        factor = 1 + (factor - 1) * 0.5
        notes.append("營收 YoY 為負，品質溢價減半")
    if de is not None and de > 2 and factor > 1.0:
        factor = 1 + (factor - 1) * 0.5
        notes.append(f"D/E {de:.2f} 偏高，品質溢價減半")
    if warning_count > 0 and factor > 1.10:
        factor = min(factor, 1.10)
        notes.append("資料分歧存在，品質係數上限 ×1.10")

    if factor > max_q:
        factor = max_q
        notes.append(f"套用產業品質係數硬上限 ×{max_q:.2f}")
    return {"factor": round(factor, 4), "reason": "；".join(notes) or "品質資料中性，係數 ×1.00"}


def theme_order_factor(themes: List[str], industry_profile: Dict[str, Any], eps_positive: bool = True, data_warning_count: int = 0, calibration: Dict[str, Any] = None) -> Dict[str, Any]:
    calibration = calibration or {}
    if not industry_profile.get("theme_premium_allowed", False):
        return {"factor": 1.00, "reason": "此產業模型不建議額外給題材高倍率"}
    text = " ".join(str(x) for x in (themes or [])).lower()
    if not text.strip():
        return {"factor": 1.00, "reason": "未偵測到題材標籤，題材係數 ×1.00"}

    baked = [str(x).lower() for x in (calibration.get("baked_in_themes") or [])]
    baked_hits = [k for k in baked if k and k in text]

    rules = [
        (1.18, ["ai asic", "asic", "cpo", "矽光子"]),
        (1.15, ["hpc", "cowos", "ai載板", "abf", "水冷", "液冷", "資料中心"]),
        (1.10, ["ai", "低軌", "衛星", "電網", "重電", "儲能"]),
        (1.06, ["車用", "高速傳輸", "機器人", "自動化"]),
    ]
    factor = 1.00
    hit = []
    for score, keys in rules:
        matched = [k for k in keys if k.lower() in text]
        if matched:
            factor = max(factor, score)
            hit.extend(matched)

    if factor <= 1.00:
        return {"factor": 1.00, "reason": "題材標籤未命中可量化溢價，僅列為備註"}

    reason = f"題材標籤命中：{'、'.join(sorted(set(hit)))}"
    if baked_hits:
        factor = min(factor, 1.05)
        reason += f"；{'、'.join(sorted(set(baked_hits)))} 已包含在產業基準中，避免重複加分，題材係數上限 ×1.05"
    if not eps_positive:
        factor = 1 + (factor - 1) * 0.5
        reason += "；EPS 未落地，題材係數減半"
    if data_warning_count >= 2:
        factor = 1 + (factor - 1) * 0.5
        reason += "；資料分歧較多，題材係數減半"
    max_f = _sf(calibration.get("max_theme_factor"), 1.10) or 1.10
    if factor > max_f:
        factor = max_f
        reason += f"；套用產業題材係數上限 ×{max_f:.2f}"
    return {"factor": round(factor, 4), "reason": reason}


def scale_growth_flex_factor(market_cap: Any, eps_positive: bool = True, liquidity_ok: bool = True, calibration: Dict[str, Any] = None) -> Dict[str, Any]:
    calibration = calibration or {}
    mc = _sf(market_cap)
    max_scale = _sf(calibration.get("max_scale_factor"), 1.05) or 1.05
    if mc is None or mc <= 0:
        return {"factor": 1.00, "reason": "市值缺值，不做規模與成長彈性修正"}
    billion = mc / 100_000_000  # 億元
    if billion >= 50_000:
        f, msg = 0.94, "超大型權值股，成長彈性與本益比擴張受限制"
    elif billion >= 10_000:
        f, msg = 0.97, "大型龍頭，穩定性高但夢想倍率有限"
    elif billion >= 3_000:
        f, msg = 1.00, "大型成長股，規模修正中性"
    elif billion >= 500:
        f, msg = 1.04, "中型成長股，成長彈性較佳"
    elif billion >= 100 and eps_positive and liquidity_ok:
        f, msg = 1.06, "小型高成長且流動性尚可，給小幅彈性溢價"
    else:
        f, msg = 0.92, "市值小、EPS 或流動性條件不足，套用規模風險折扣"
    if f > max_scale:
        f = max_scale
        msg += f"；套用產業規模係數上限 ×{max_scale:.2f}"
    return {"factor": round(f, 4), "reason": f"市值約 {billion:,.0f} 億；{msg}"}


def geopolitical_factor(industry_profile: Dict[str, Any], calibration: Dict[str, Any]) -> Dict[str, Any]:
    f = _sf(calibration.get("geopolitical_factor"), 1.00) or 1.00
    if f >= 0.999:
        return {"factor": 1.00, "reason": "未套用特別地緣政治折價"}
    note = calibration.get("geopolitical_note") or "台灣供應鏈地緣政治與出口管制 / 客戶集中風險折價"
    return {"factor": round(f, 4), "reason": note}


def data_confidence_factor(warnings: List[Dict[str, Any]] = None, dq_warnings: List[str] = None) -> Dict[str, Any]:
    warnings = warnings or []
    dq_warnings = dq_warnings or []
    danger = sum(1 for w in warnings if str(w.get("嚴重度", "")).lower() == "danger")
    count = len(warnings) + len(dq_warnings)
    if danger >= 2 or count >= 5:
        f, label = 0.70, "低 / 資料異常"
    elif danger >= 1 or count >= 3:
        f, label = 0.80, "偏低"
    elif count == 2:
        f, label = 0.90, "中"
    elif count == 1:
        f, label = 0.95, "中高"
    else:
        f, label = 1.00, "高"
    return {"factor": f, "label": label, "reason": f"分歧警告 {len(warnings)} 項、資料校驗提醒 {len(dq_warnings)} 項"}


def valuation_risk_factor(current_price: Any = None, operable_low: Any = None, operable_high: Any = None) -> Dict[str, Any]:
    cp = _sf(current_price)
    lo = _sf(operable_low)
    hi = _sf(operable_high)
    if cp is None or lo is None or hi is None or hi <= 0:
        return {"factor": 0.95, "label": "保守預設", "reason": "可操作區間尚未建立，先套用保守估值折扣 ×0.95"}
    if cp <= lo:
        return {"factor": 1.00, "label": "低於區間", "reason": "現價低於或接近可操作區間下緣"}
    if cp <= hi:
        return {"factor": 0.95, "label": "區間內", "reason": "現價位於可操作區間內"}
    over = (cp / hi) - 1
    if over <= 0.10:
        f = 0.90
    elif over <= 0.30:
        f = 0.80
    else:
        f = 0.70
    return {"factor": f, "label": "高於區間", "reason": f"現價高於可操作區間上緣 {over*100:.1f}%"}


def liquidity_factor(hist_data: Any = None, info: Dict[str, Any] = None) -> Dict[str, Any]:
    avg_shares = None
    try:
        if hist_data is not None and hasattr(hist_data, "empty") and not hist_data.empty and "Volume" in hist_data.columns:
            avg_shares = float(hist_data["Volume"].tail(20).mean())
    except Exception:
        avg_shares = None
    if avg_shares is None and isinstance(info, dict):
        avg_shares = _sf(info.get("averageVolume") or info.get("averageVolume10days") or info.get("averageDailyVolume10Day"))
    if avg_shares is None or avg_shares <= 0:
        return {"factor": 1.00, "label": "未套用", "avg_lots": None, "reason": "近 20 日均量缺值，暫不套流動性折扣"}
    lots = avg_shares / 1000.0
    if lots >= 5000:
        f, label = 1.00, "佳"
    elif lots >= 2000:
        f, label = 0.95, "正常"
    elif lots >= 1000:
        f, label = 0.90, "稍低"
    elif lots >= 500:
        f, label = 0.85, "偏低"
    else:
        f, label = 0.78, "低"
    return {"factor": f, "label": label, "avg_lots": lots, "reason": f"近 20 日均量約 {lots:,.0f} 張"}


def pe_floor_ceiling(industry_profile: Dict[str, Any], calibration: Dict[str, Any]) -> Dict[str, Any]:
    floor = _sf(calibration.get("floor_pe"), 12.0) or 12.0
    soft = _sf(calibration.get("soft_ceiling_pe"), None)
    hard = _sf(calibration.get("hard_ceiling_pe"), None)
    if soft is None or hard is None:
        rng = industry_profile.get("pe_range")
        if isinstance(rng, (tuple, list)) and len(rng) == 2 and _sf(rng[0]) and _sf(rng[1]):
            floor = float(rng[0])
            soft = float(rng[1]) * 0.90
            hard = float(rng[1])
        else:
            soft, hard = 35.0, 45.0
    return {"floor": float(floor), "soft_ceiling": float(soft), "hard_ceiling": float(hard), "ceiling": float(hard)}


def build_pb_cycle_pack(current_price: Any, pb_ratio: Any, industry_profile: Dict[str, Any]) -> Dict[str, Any]:
    pb = _sf(pb_ratio)
    cp = _sf(current_price)
    pb_range = industry_profile.get("pb_range")
    rows = []
    if not (isinstance(pb_range, (tuple, list)) and len(pb_range) == 2):
        pb_range = (None, None)
    low_pb, high_pb = _sf(pb_range[0]), _sf(pb_range[1])
    bvps = cp / pb if cp is not None and pb and pb > 0 else None
    low_val = bvps * low_pb if bvps and low_pb else None
    high_val = bvps * high_pb if bvps and high_pb else None
    rows.append({"類型": "P/B 週期模型", "項目": "目前 P/B", "倍率/係數": _fmt_x(pb), "說明": "週期股優先看 P/B 與報價/運價/庫存週期"})
    rows.append({"類型": "P/B 週期模型", "項目": "參考 P/B 區間", "倍率/係數": f"{_fmt_x(low_pb)}～{_fmt_x(high_pb)}", "說明": industry_profile.get("warning_note", "低 P/E 不一定代表低估")})
    rows.append({"類型": "P/B 週期模型", "項目": "BVPS 推估", "倍率/係數": "NULL" if bvps is None else f"{bvps:.2f}", "說明": "以現價 ÷ P/B 反推；後續可改接 Yahoo BVPS"})
    return {
        "available": False,
        "valuation_mode": "pb_cycle",
        "final_cap": None,
        "raw_cap": None,
        "pb_ratio": pb,
        "bvps": bvps,
        "pb_low_price": low_val,
        "pb_high_price": high_val,
        "warnings": ["本產業優先使用 P/B 週期模型，P/E 僅作輔助"],
        "report": pd.DataFrame(rows),
    }


def build_event_theme_pack(industry_profile: Dict[str, Any]) -> Dict[str, Any]:
    rows = [
        {"類型": "題材 / 事件模型", "項目": "P/E Cap", "倍率/係數": "不輸出", "說明": "本分類 EPS 或訂單落地程度不足，不適合一般 P/E 買進倍率。"},
        {"類型": "題材 / 事件模型", "項目": "主要觀察", "倍率/係數": "—", "說明": "事件催化、訂單真實性、籌碼、成交量與財報落地程度。"},
        {"類型": "題材 / 事件模型", "項目": "風險提醒", "倍率/係數": "高", "說明": industry_profile.get("warning_note", industry_profile.get("note", "題材股不輸出公式買進倍率。"))},
    ]
    return {
        "available": False,
        "valuation_mode": "event_chip",
        "final_cap": None,
        "raw_cap": None,
        "warnings": ["題材 / 事件驅動股不輸出 P/E 買進倍率"],
        "report": pd.DataFrame(rows),
    }


def calculate_dynamic_cap_v2(
    *,
    stock_id: str = "",
    stock_name: str = "",
    current_price: Any = None,
    info: Dict[str, Any] = None,
    hist_data: Any = None,
    industry_profile: Dict[str, Any] = None,
    gross_margin: Any = None,
    roe: Any = None,
    debt_to_equity: Any = None,
    revenue_yoy: Any = None,
    ttm_eps: Any = None,
    system_forward_eps: Any = None,
    ai_forward_eps: Any = None,
    consensus_forward_eps: Any = None,
    ai_ttm_eps: Any = None,
    pb_ratio: Any = None,
    divergence_warnings: List[Dict[str, Any]] = None,
    dq_warnings: List[str] = None,
    operable_low: Any = None,
    operable_high: Any = None,
) -> Dict[str, Any]:
    info = info or {}
    p = industry_profile or {}
    c = _calibration(p)
    warnings: List[str] = []
    themes = list(p.get("themes") or [])
    primary_valuation = str(p.get("primary_valuation") or "forward_pe")
    pe_app = p.get("pe_applicable", True)
    eps_positive = any((_sf(x) or 0) > 0 for x in [consensus_forward_eps, system_forward_eps, ai_forward_eps, ttm_eps, ai_ttm_eps])
    warn_count = len(divergence_warnings or []) + len(dq_warnings or [])

    # 17-B-2：低軌衛星、機器人、生技等條件式 P/E 模型，若 EPS / 訂單未落地，直接切換事件模型。
    if p.get("event_model_if_eps_unstable") and not eps_positive:
        pack = build_event_theme_pack(p)
        note = p.get("event_switch_note") or "EPS / 訂單未落地，依 17-B-2 校準規則改用事件模型。"
        pack["warnings"] = list(pack.get("warnings") or []) + [note]
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p, "model_version": "Dynamic Cap 2.0 calibration 17-B-2"})
        return pack

    if pe_app is False or primary_valuation in {"event_chip", "theme_event"}:
        pack = build_event_theme_pack(p)
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p, "model_version": "Dynamic Cap 2.0 calibration 17-B-2"})
        return pack
    if primary_valuation.startswith("pb") or primary_valuation in {"pb", "pb_roe"}:
        pack = build_pb_cycle_pack(current_price, pb_ratio, p)
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p, "model_version": "Dynamic Cap 2.0 calibration 17-B-2"})
        return pack

    base = _sf(c.get("base_pe"), 20.0) or 20.0
    rows: List[Dict[str, Any]] = []
    _add_row(rows, "基準", "產業基準倍率", f"{base:.1f}x", f"{p.get('model_label', p.get('display_name', '一般產業'))} 17-B-2 校準後 base_pe；非買進追價倍率")

    liq = liquidity_factor(hist_data, info)
    g = growth_factor_hierarchical(
        system_forward_eps=system_forward_eps,
        ai_forward_eps=ai_forward_eps,
        consensus_forward_eps=consensus_forward_eps,
        ttm_eps=ttm_eps,
        ai_ttm_eps=ai_ttm_eps,
        revenue_yoy=revenue_yoy,
        industry_profile=p,
        calibration=c,
        roe=roe,
        gross_margin=gross_margin,
    )
    q = quality_factor_relative(
        gross_margin,
        roe=roe,
        revenue_yoy=revenue_yoy,
        eps_positive=eps_positive,
        debt_to_equity=debt_to_equity,
        warning_count=warn_count,
        calibration=c,
    )
    th = theme_order_factor(themes, p, eps_positive=eps_positive, data_warning_count=warn_count, calibration=c)
    sc = scale_growth_flex_factor(info.get("marketCap"), eps_positive=eps_positive, liquidity_ok=(liq.get("factor", 1) >= 0.85), calibration=c)
    geo = geopolitical_factor(p, c)

    for name, pack in [
        ("成長係數", g),
        ("品質係數（毛利率相對化 + ROE）", q),
        ("題材 / 訂單係數", th),
        ("規模與成長彈性係數", sc),
        ("地緣政治 / 供應鏈風險係數", geo),
    ]:
        _add_factor(rows, name, float(pack.get("factor", 1.0) or 1.0), pack.get("reason", ""))

    raw_cap = base * float(g.get("factor", 1) or 1) * float(q.get("factor", 1) or 1) * float(th.get("factor", 1) or 1) * float(sc.get("factor", 1) or 1) * float(geo.get("factor", 1) or 1)
    fc = pe_floor_ceiling(p, c)
    _add_row(rows, "小計", "原始建議倍率", f"{raw_cap:.1f}x", "產業基準 × 成長係數 × 品質係數 × 題材係數 × 規模係數 × 地緣政治折價")

    dc = data_confidence_factor(divergence_warnings, dq_warnings)
    vr = valuation_risk_factor(current_price, operable_low, operable_high)
    _add_discount(rows, "資料可信度折扣", dc["factor"], f"{dc['label']}；{dc['reason']}")
    _add_discount(rows, "估值風險折扣", vr["factor"], f"{vr['label']}；{vr['reason']}")
    _add_discount(rows, "流動性折扣", liq["factor"], f"{liq['label']}；{liq['reason']}")

    pre_clip_cap = raw_cap * dc["factor"] * vr["factor"] * liq["factor"]
    final_cap = _clip(pre_clip_cap, fc["floor"], fc["hard_ceiling"])
    hit_floor = final_cap <= fc["floor"] + 1e-9 and pre_clip_cap < fc["floor"]
    hit_hard_ceiling = final_cap >= fc["hard_ceiling"] - 1e-9 and pre_clip_cap > fc["hard_ceiling"]
    if pre_clip_cap > fc["soft_ceiling"]:
        warnings.append("Dynamic Cap 已高於產業 soft ceiling，模型輸入偏樂觀，請保守解讀")
    if hit_hard_ceiling:
        warnings.append("Dynamic Cap 已觸及產業 hard ceiling，已強制截斷；不可直接作為買進乘數")
    if hit_floor:
        warnings.append("Dynamic Cap 低於產業 floor，已套用最低樓地板避免倍率失真")

    _add_row(
        rows,
        "結果",
        "最終建議倍率",
        f"{final_cap:.1f}x",
        f"折扣前 {pre_clip_cap:.1f}x；floor {fc['floor']:.0f}x / soft ceiling {fc['soft_ceiling']:.0f}x / hard ceiling {fc['hard_ceiling']:.0f}x",
    )

    if p.get("pe_trap_warning"):
        warnings.append("本產業存在 P/E 陷阱，低 P/E 不一定代表低估")
    if warn_count >= 3:
        warnings.append("資料分歧或校驗提醒較多，Dynamic Cap 已折扣")
    if liq.get("factor", 1) < 0.9:
        warnings.append("流動性偏低，已套用流動性折扣")

    return {
        "available": True,
        "valuation_mode": primary_valuation,
        "model_version": "Dynamic Cap 2.0 calibration 17-B-2",
        "base_multiple": base,
        "growth_premium": g,  # 保留舊 key，實際為 growth factor pack
        "gross_margin_premium": q,  # 保留舊 key，實際為 quality factor pack
        "roe_quality_premium": q,
        "theme_premium": th,
        "market_cap_adjustment": sc,
        "geopolitical_factor": geo,
        "data_confidence_factor": dc,
        "valuation_risk_factor": vr,
        "liquidity_factor": liq,
        "raw_cap": raw_cap,
        "pre_clip_cap": pre_clip_cap,
        "final_cap": final_cap,
        "floor_cap": fc["floor"],
        "soft_ceiling_cap": fc["soft_ceiling"],
        "ceiling_cap": fc["hard_ceiling"],
        "hard_ceiling_cap": fc["hard_ceiling"],
        "hit_hard_ceiling": hit_hard_ceiling,
        "warnings": warnings,
        "industry_profile": p,
        "report": pd.DataFrame(rows),
        "explanation": "Dynamic Cap 2.0 17-B-2：已同步全產業校準表，產業基準 × 成長/品質/題材/規模/地緣係數，再乘資料、估值與流動性折扣，最後套用產業 hard ceiling。",
    }
