"""
Dynamic Cap 2.0 係數校準模型（第 17-C-7A 階段）。

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
        "recovery_sensitive": True,
    },
    "PROBE_TEST_INTERFACE": {
        "base_pe": 34.0, "floor_pe": 22.0, "soft_ceiling_pe": 50.0, "hard_ceiling_pe": 60.0,
        "max_growth_factor": 1.22, "max_quality_factor": 1.20, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.38, "gross_margin_good": 0.45, "gross_margin_excellent": 0.52,
        "baked_in_themes": ["測試", "探針"], "geopolitical_factor": 0.97,
        "recovery_sensitive": True,
    },
    "SEMICAP_COWOS_EQUIPMENT": {
        "base_pe": 32.0, "floor_pe": 20.0, "soft_ceiling_pe": 48.0, "hard_ceiling_pe": 58.0,
        "max_growth_factor": 1.22, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.30, "gross_margin_good": 0.38, "gross_margin_excellent": 0.45,
        "baked_in_themes": ["cowos", "先進封裝", "設備"], "geopolitical_factor": 0.96,
        "recovery_sensitive": True,
    },
    "FAB_FACILITY_MATERIALS": {
        "base_pe": 26.0, "floor_pe": 16.0, "soft_ceiling_pe": 38.0, "hard_ceiling_pe": 45.0,
        "max_growth_factor": 1.16, "max_quality_factor": 1.12, "max_theme_factor": 1.08, "max_scale_factor": 1.05,
        "gross_margin_baseline": 0.24, "gross_margin_good": 0.30, "gross_margin_excellent": 0.36,
        "baked_in_themes": ["廠務", "材料"], "geopolitical_factor": 0.96,
        "recovery_sensitive": True,
    },
    "ABF_SUBSTRATE": {
        "base_pe": 30.0, "floor_pe": 18.0, "soft_ceiling_pe": 45.0, "hard_ceiling_pe": 55.0,
        "max_growth_factor": 1.20, "max_quality_factor": 1.16, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.23, "gross_margin_good": 0.30, "gross_margin_excellent": 0.38,
        "baked_in_themes": ["abf", "ai載板", "hpc", "載板"],
        "cyclical_low_base_cap": True,
        "recovery_sensitive": True,
    },
    "SERVER_PCB_BOARD": {
        "base_pe": 28.0, "floor_pe": 16.0, "soft_ceiling_pe": 42.0, "hard_ceiling_pe": 52.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.14, "max_theme_factor": 1.10, "max_scale_factor": 1.06,
        "gross_margin_baseline": 0.18, "gross_margin_good": 0.24, "gross_margin_excellent": 0.30,
        "baked_in_themes": ["ai伺服器", "高階pcb"],
        "recovery_sensitive": True,
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
        "recovery_sensitive": "partial",
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
        "recovery_sensitive": True,
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
        "recovery_sensitive": "partial",
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
    "SPECIALTY_CHEM_ELECTRONIC_MATERIALS": {'base_pe': 17.0,
     'floor_pe': 10.0,
     'soft_ceiling_pe': 24.0,
     'hard_ceiling_pe': 30.0,
     'max_growth_factor': 1.1,
     'max_quality_factor': 1.12,
     'max_theme_factor': 1.05,
     'max_scale_factor': 1.03,
     'gross_margin_baseline': 0.22,
     'gross_margin_good': 0.28,
     'gross_margin_excellent': 0.35,
     'baked_in_themes': ['電子材料', 'PCB材料', '特用化學'],
     'recovery_sensitive': True},
    "CCL_HIGH_SPEED_MATERIALS": {'base_pe': 24.0,
     'floor_pe': 14.0,
     'soft_ceiling_pe': 35.0,
     'hard_ceiling_pe': 42.0,
     'max_growth_factor': 1.15,
     'max_quality_factor': 1.15,
     'max_theme_factor': 1.08,
     'max_scale_factor': 1.05,
     'gross_margin_baseline': 0.25,
     'gross_margin_good': 0.32,
     'gross_margin_excellent': 0.4,
     'baked_in_themes': ['ccl', '高速材料', 'ai伺服器材料'],
     'recovery_sensitive': True},
    "SEMICONDUCTOR_MATERIALS_CONSUMABLES": {'base_pe': 26.0,
     'floor_pe': 15.0,
     'soft_ceiling_pe': 38.0,
     'hard_ceiling_pe': 45.0,
     'max_growth_factor': 1.15,
     'max_quality_factor': 1.15,
     'max_theme_factor': 1.08,
     'max_scale_factor': 1.05,
     'gross_margin_baseline': 0.3,
     'gross_margin_good': 0.38,
     'gross_margin_excellent': 0.45,
     'baked_in_themes': ['半導體材料', '耗材', 'euv', '再生晶圓'],
     'recovery_sensitive': True},
    "CIS_SEMICONDUCTOR_OPTICS": {'base_pe': 28.0,
     'floor_pe': 15.0,
     'soft_ceiling_pe': 40.0,
     'hard_ceiling_pe': 50.0,
     'max_growth_factor': 1.18,
     'max_quality_factor': 1.18,
     'max_theme_factor': 1.1,
     'max_scale_factor': 1.05,
     'gross_margin_baseline': 0.32,
     'gross_margin_good': 0.42,
     'gross_margin_excellent': 0.5,
     'baked_in_themes': ['cis', '影像感測', '半導體光學'],
     'recovery_sensitive': True},
    "TEST_AUTOMATION_EQUIPMENT": {'base_pe': 30.0,
     'floor_pe': 18.0,
     'soft_ceiling_pe': 42.0,
     'hard_ceiling_pe': 50.0,
     'max_growth_factor': 1.18,
     'max_quality_factor': 1.16,
     'max_theme_factor': 1.1,
     'max_scale_factor': 1.06,
     'gross_margin_baseline': 0.28,
     'gross_margin_good': 0.36,
     'gross_margin_excellent': 0.45,
     'baked_in_themes': ['aoi', '檢測設備', '自動化設備'],
     'recovery_sensitive': True},
    "GREEN_ENERGY_INFRA": {'base_pe': 22.0,
     'floor_pe': 10.0,
     'soft_ceiling_pe': 30.0,
     'hard_ceiling_pe': 38.0,
     'max_growth_factor': 1.12,
     'max_quality_factor': 1.1,
     'max_theme_factor': 1.03,
     'max_scale_factor': 1.03,
     'gross_margin_baseline': 0.15,
     'gross_margin_good': 0.22,
     'gross_margin_excellent': 0.28,
     'baked_in_themes': ['綠能', '風電', '儲能'],
     'recovery_sensitive': True},
    "AUTO_PARTS_AM": {'base_pe': 16.0,
     'floor_pe': 8.0,
     'soft_ceiling_pe': 24.0,
     'hard_ceiling_pe': 30.0,
     'max_growth_factor': 1.1,
     'max_quality_factor': 1.1,
     'max_theme_factor': 1.02,
     'max_scale_factor': 1.03,
     'gross_margin_baseline': 0.22,
     'gross_margin_good': 0.3,
     'gross_margin_excellent': 0.38,
     'baked_in_themes': ['am汽車零件'],
     'recovery_sensitive': True},
    "AUTO_PARTS_EV": {'base_pe': 22.0,
     'floor_pe': 12.0,
     'soft_ceiling_pe': 32.0,
     'hard_ceiling_pe': 40.0,
     'max_growth_factor': 1.14,
     'max_quality_factor': 1.12,
     'max_theme_factor': 1.06,
     'max_scale_factor': 1.04,
     'gross_margin_baseline': 0.2,
     'gross_margin_good': 0.28,
     'gross_margin_excellent': 0.35,
     'baked_in_themes': ['ev零組件', '車用零件'],
     'recovery_sensitive': True},
    "AUTO_OEM_CYCLE": {'base_pe': 12.0,
     'floor_pe': 6.0,
     'soft_ceiling_pe': 18.0,
     'hard_ceiling_pe': 24.0,
     'max_growth_factor': 1.08,
     'max_quality_factor': 1.05,
     'max_theme_factor': 1.0,
     'max_scale_factor': 1.02,
     'gross_margin_baseline': 0.12,
     'gross_margin_good': 0.18,
     'gross_margin_excellent': 0.25,
     'baked_in_themes': ['整車', '汽車集團'],
     'recovery_sensitive': True},
    "AI_SERVER_BOARD_SYSTEM": {'base_pe': 26.0,
     'floor_pe': 14.0,
     'soft_ceiling_pe': 36.0,
     'hard_ceiling_pe': 45.0,
     'max_growth_factor': 1.16,
     'max_quality_factor': 1.14,
     'max_theme_factor': 1.08,
     'max_scale_factor': 1.04,
     'gross_margin_baseline': 0.12,
     'gross_margin_good': 0.18,
     'gross_margin_excellent': 0.25,
     'baked_in_themes': ['主板', '板卡', 'ai伺服器系統'],
     'recovery_sensitive': True},
    "PC_BRAND_AI_PC": {'base_pe': 18.0,
     'floor_pe': 10.0,
     'soft_ceiling_pe': 28.0,
     'hard_ceiling_pe': 35.0,
     'max_growth_factor': 1.12,
     'max_quality_factor': 1.12,
     'max_theme_factor': 1.05,
     'max_scale_factor': 1.03,
     'gross_margin_baseline': 0.1,
     'gross_margin_good': 0.16,
     'gross_margin_excellent': 0.24,
     'baked_in_themes': ['ai pc', 'pc品牌'],
     'recovery_sensitive': True},
    "PC_NB_ODM": {'base_pe': 16.0,
     'floor_pe': 8.0,
     'soft_ceiling_pe': 24.0,
     'hard_ceiling_pe': 32.0,
     'max_growth_factor': 1.1,
     'max_quality_factor': 1.08,
     'max_theme_factor': 1.03,
     'max_scale_factor': 1.02,
     'gross_margin_baseline': 0.04,
     'gross_margin_good': 0.07,
     'gross_margin_excellent': 0.1,
     'baked_in_themes': ['nb odm', 'ems'],
     'recovery_sensitive': True},
    "MACHINE_TOOL_CYCLE": {'base_pe': 14.0,
     'floor_pe': 8.0,
     'soft_ceiling_pe': 22.0,
     'hard_ceiling_pe': 30.0,
     'max_growth_factor': 1.1,
     'max_quality_factor': 1.08,
     'max_theme_factor': 1.02,
     'max_scale_factor': 1.02,
     'gross_margin_baseline': 0.18,
     'gross_margin_good': 0.25,
     'gross_margin_excellent': 0.32,
     'baked_in_themes': ['工具機', '工業機械'],
     'recovery_sensitive': True},
    "MEMORY_CONTROLLER_CYCLE": {'base_pe': 24.0,
     'floor_pe': 12.0,
     'soft_ceiling_pe': 35.0,
     'hard_ceiling_pe': 45.0,
     'max_growth_factor': 1.15,
     'max_quality_factor': 1.14,
     'max_theme_factor': 1.06,
     'max_scale_factor': 1.04,
     'gross_margin_baseline': 0.25,
     'gross_margin_good': 0.35,
     'gross_margin_excellent': 0.45,
     'baked_in_themes': ['nand控制ic', '記憶體'],
     'recovery_sensitive': True},
    "RF_MODULE_PACKAGING": {'base_pe': 24.0,
     'floor_pe': 12.0,
     'soft_ceiling_pe': 34.0,
     'hard_ceiling_pe': 42.0,
     'max_growth_factor': 1.14,
     'max_quality_factor': 1.12,
     'max_theme_factor': 1.06,
     'max_scale_factor': 1.03,
     'gross_margin_baseline': 0.22,
     'gross_margin_good': 0.3,
     'gross_margin_excellent': 0.38,
     'baked_in_themes': ['rf', '高頻', '特殊封裝'],
     'recovery_sensitive': True},
    "GENERAL": {
        "base_pe": 20.0, "floor_pe": 10.0, "soft_ceiling_pe": 28.0, "hard_ceiling_pe": 35.0,
        "max_growth_factor": 1.12, "max_quality_factor": 1.10, "max_theme_factor": 1.05, "max_scale_factor": 1.03,
        "gross_margin_baseline": None,
    },
}



# ===== 第 17-C-6：IC 設計 / ASIC / IP 分層預設校準 =====
CALIBRATION_DEFAULTS.update({
    "IC_DESIGN_ASIC_SERVICE": {
        "base_pe": 35.0, "floor_pe": 22.0, "soft_ceiling_pe": 55.0, "hard_ceiling_pe": 70.0,
        "max_growth_factor": 1.25, "max_quality_factor": 1.20, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.42, "gross_margin_good": 0.50, "gross_margin_excellent": 0.60,
        "baked_in_themes": ["asic", "設計服務", "nre"],
        "geopolitical_factor": 0.97,
    },
    "IC_DESIGN_ASIC_HIGH_VISIBILITY": {
        "base_pe": 45.0, "floor_pe": 28.0, "soft_ceiling_pe": 70.0, "hard_ceiling_pe": 85.0,
        "max_growth_factor": 1.30, "max_quality_factor": 1.22, "max_theme_factor": 1.12, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.45, "gross_margin_good": 0.55, "gross_margin_excellent": 0.65,
        "baked_in_themes": ["ai asic", "custom silicon", "hyperscaler", "hpc"],
        "geopolitical_factor": 0.97,
    },
    "IC_DESIGN_IP_ROYALTY": {
        "base_pe": 45.0, "floor_pe": 28.0, "soft_ceiling_pe": 75.0, "hard_ceiling_pe": 90.0,
        "max_growth_factor": 1.28, "max_quality_factor": 1.25, "max_theme_factor": 1.10, "max_scale_factor": 1.08,
        "gross_margin_baseline": 0.55, "gross_margin_good": 0.65, "gross_margin_excellent": 0.75,
        "baked_in_themes": ["ip", "矽智財", "royalty", "eda"],
        "geopolitical_factor": 0.98,
    },
    "IC_DESIGN_PLATFORM_AI_EDGE": {
        "base_pe": 24.0, "floor_pe": 14.0, "soft_ceiling_pe": 38.0, "hard_ceiling_pe": 50.0,
        "max_growth_factor": 1.18, "max_quality_factor": 1.14, "max_theme_factor": 1.08, "max_scale_factor": 1.03,
        "gross_margin_baseline": 0.42, "gross_margin_good": 0.48, "gross_margin_excellent": 0.55,
        "baked_in_themes": ["ai edge", "手機晶片", "平台型 ic"],
        "geopolitical_factor": 0.97,
    },
})




# ===== 第 17-C-7C-1：第一批 AI 混合股補充預設校準 =====
CALIBRATION_DEFAULTS.update({
    "EMS_PLATFORM_CONTRACT_MANUFACTURING": {
        "base_pe": 14.0, "floor_pe": 8.0, "soft_ceiling_pe": 24.0, "hard_ceiling_pe": 32.0,
        "max_growth_factor": 1.10, "max_quality_factor": 1.08, "max_theme_factor": 1.05, "max_scale_factor": 1.02,
        "gross_margin_baseline": 0.06, "gross_margin_good": 0.09, "gross_margin_excellent": 0.12,
        "baked_in_themes": ["ems", "電子製造服務", "平台型製造"],
        "geopolitical_factor": 0.97,
        "recovery_sensitive": True,
    },
})

# ===== 第 17-C-7A：混合產業權重估值引擎 =====
def _safe_weight(x: Any) -> float:
    v = _sf(x, 0.0) or 0.0
    return max(0.0, min(float(v), 0.50))


def _weighted_value(primary: Any, hybrids: List[Dict[str, Any]], key: str, primary_weight: float) -> Optional[float]:
    base = _sf(primary)
    if base is None:
        return None
    total = base * primary_weight
    for h in hybrids:
        hv = _sf(h.get(key))
        if hv is not None:
            total += hv * float(h.get("effective_weight", h.get("weight", 0)) or 0)
    return total


def _build_hybrid_calibration(industry_profile: Dict[str, Any], primary_calibration: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """建立混合產業權重後的校準參數。

    原則：
    - hybrid_taxons 必須由 stock_mapping.py 人工指定，不由 AI 自動亂加。
    - total_weight 硬上限 0.50。
    - 若 classification 非 confirmed 或 Forward EPS 缺值/有嚴重分歧，後續可在此擴充折半；17-C-7A 先建立引擎。
    - 若 hybrid taxon 與 primary 相同，或已明顯內含 baked_in_themes，跳過避免重複加分。
    """
    p = industry_profile or {}
    hybrids_raw = p.get("hybrid_taxons") or []
    if not isinstance(hybrids_raw, list) or not hybrids_raw:
        return dict(primary_calibration), {"enabled": False, "reason": "未設定混合產業權重", "hybrids": []}

    primary_key = str(p.get("model_key") or p.get("taxon_key") or "").strip().upper()
    primary_baked = {str(x).lower() for x in (primary_calibration.get("baked_in_themes") or [])}
    valid = []
    total_weight = 0.0
    reasons = []

    for h in hybrids_raw:
        if not isinstance(h, dict):
            continue
        taxon = str(h.get("taxon") or "").strip().upper()
        weight = _safe_weight(h.get("weight"))
        if not taxon or weight <= 0:
            continue
        if taxon == primary_key:
            reasons.append(f"{taxon} 與主分類相同，跳過避免重複加分")
            continue
        hc = dict(CALIBRATION_DEFAULTS.get(taxon, {}))
        # 若 DEFAULTS 沒有，仍可用 taxonomy 參數；避免 import 循環，使用 dynamic defaults 為主。
        if not hc:
            reasons.append(f"{taxon} 找不到校準參數，跳過")
            continue
        # 內含題材防重複：若 hybrid taxon baked themes 已全部包含在 primary baked，降低至 0。
        hybrid_baked = {str(x).lower() for x in (hc.get("baked_in_themes") or [])}
        if hybrid_baked and primary_baked and hybrid_baked.issubset(primary_baked):
            reasons.append(f"{taxon} 題材已內含於主分類，跳過")
            continue
        if total_weight + weight > 0.50:
            weight = max(0.0, 0.50 - total_weight)
        if weight <= 0:
            continue
        hc["taxon"] = taxon
        hc["weight"] = weight
        hc["effective_weight"] = weight
        hc["reason"] = str(h.get("reason") or "")
        valid.append(hc)
        total_weight += weight
        if total_weight >= 0.50:
            break

    if not valid:
        return dict(primary_calibration), {"enabled": False, "reason": "混合產業權重全部被跳過；" + "；".join(reasons), "hybrids": []}

    primary_weight = max(0.50, 1.0 - total_weight)
    c = dict(primary_calibration)

    for key in ["base_pe", "floor_pe", "soft_ceiling_pe", "hard_ceiling_pe",
                "gross_margin_baseline", "gross_margin_good", "gross_margin_excellent",
                "max_growth_factor", "max_quality_factor", "max_theme_factor", "max_scale_factor"]:
        v = _weighted_value(primary_calibration.get(key), valid, key, primary_weight)
        if v is not None:
            c[key] = round(v, 4)

    # 風險與 baked theme 合併，避免題材係數再次過度加分。
    baked = list(primary_calibration.get("baked_in_themes") or [])
    for h in valid:
        baked.extend(h.get("baked_in_themes") or [])
    if baked:
        c["baked_in_themes"] = sorted(set(str(x) for x in baked if str(x).strip()))

    note_parts = [
        f"主分類權重 {primary_weight:.0%}",
        *[f"{h.get('taxon')} {float(h.get('effective_weight', 0)):.0%}" + (f"（{h.get('reason')}）" if h.get("reason") else "") for h in valid],
    ]
    summary = {
        "enabled": True,
        "primary_weight": primary_weight,
        "total_hybrid_weight": total_weight,
        "hybrids": [{"taxon": h.get("taxon"), "weight": h.get("effective_weight"), "reason": h.get("reason", "")} for h in valid],
        "reason": "；".join(note_parts + reasons),
        "mixed_base_pe": c.get("base_pe"),
        "mixed_soft_ceiling_pe": c.get("soft_ceiling_pe"),
        "mixed_hard_ceiling_pe": c.get("hard_ceiling_pe"),
    }
    return c, summary

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

    # 17-C-7A：若 stock_mapping.py 有人工指定 hybrid_taxons，混合 base/soft/hard 與係數上限。
    mixed, summary = _build_hybrid_calibration(industry_profile, c)
    mixed["hybrid_summary"] = summary
    return mixed


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


def _linear_score(value: float, left: float, right: float, out_left: float, out_right: float) -> float:
    """線性插值工具：value 在 left~right 間，輸出 out_left~out_right。"""
    if right == left:
        return out_right
    ratio = (value - left) / (right - left)
    ratio = max(0.0, min(1.0, ratio))
    return out_left + (out_right - out_left) * ratio


def _absolute_margin_adjustment(gm: Optional[float]) -> tuple[float, str]:
    """第 17-C-5：絕對毛利率水準調整，不同毛利率區間給漸進式加減分。"""
    if gm is None:
        return 0.0, "絕對毛利率缺值"
    if gm < 0.10:
        return -0.06, f"絕對毛利率 {_fmt_pct(gm)} 低於 10%，品質扣分 -0.06"
    if gm < 0.20:
        return _linear_score(gm, 0.10, 0.20, -0.02, 0.00), f"絕對毛利率 {_fmt_pct(gm)} 位於 10%～20%，偏低至中性"
    if gm < 0.30:
        return _linear_score(gm, 0.20, 0.30, 0.00, 0.02), f"絕對毛利率 {_fmt_pct(gm)} 位於 20%～30%，中性略佳"
    if gm < 0.40:
        return _linear_score(gm, 0.30, 0.40, 0.02, 0.04), f"絕對毛利率 {_fmt_pct(gm)} 位於 30%～40%，品質加分"
    if gm < 0.50:
        return _linear_score(gm, 0.40, 0.50, 0.04, 0.06), f"絕對毛利率 {_fmt_pct(gm)} 位於 40%～50%，高毛利加分"
    if gm < 0.60:
        return _linear_score(gm, 0.50, 0.60, 0.06, 0.08), f"絕對毛利率 {_fmt_pct(gm)} 位於 50%～60%，高毛利加分"
    return 0.10, f"絕對毛利率 {_fmt_pct(gm)} 高於 60%，絕對毛利加分上限 +0.10"


def _relative_margin_adjustment(
    gm: Optional[float],
    gm_base: Optional[float],
    gm_good: Optional[float],
    gm_excellent: Optional[float],
) -> tuple[float, str]:
    """第 17-C-5：相對產業毛利門檻調整，包含低於同業的扣分。"""
    if gm is None:
        return 0.0, "相對產業毛利無法判斷"
    if gm_base is None:
        if gm < 0.10:
            return -0.04, f"缺少產業毛利基準；毛利率 {_fmt_pct(gm)} 偏低，保守扣分"
        if gm >= 0.45:
            return 0.02, f"缺少產業毛利基準；毛利率 {_fmt_pct(gm)} 偏高，但僅小幅加分"
        return 0.0, f"缺少產業毛利基準；毛利率 {_fmt_pct(gm)} 不做相對加分"

    # 低於同業：分層扣分，不再只粗略扣 0.96/0.90。
    if gm < gm_base:
        gap = gm_base - gm
        if gap >= 0.10:
            return -0.10, f"毛利率 {_fmt_pct(gm)} 較產業基準 {_fmt_pct(gm_base)} 低超過 10 個百分點，明顯低於同業"
        if gap >= 0.05:
            return -0.07, f"毛利率 {_fmt_pct(gm)} 較產業基準 {_fmt_pct(gm_base)} 低 5～10 個百分點，低於同業"
        return -0.03, f"毛利率 {_fmt_pct(gm)} 略低於產業基準 {_fmt_pct(gm_base)}"

    # 高於同業：採漸進式，不再只要高於 good 就碰上限。
    if gm_good is None or gm_excellent is None or gm_excellent <= gm_good:
        if gm >= gm_base + 0.10:
            return 0.05, f"毛利率 {_fmt_pct(gm)} 明顯高於產業基準 {_fmt_pct(gm_base)}"
        if gm >= gm_base + 0.05:
            return 0.03, f"毛利率 {_fmt_pct(gm)} 高於產業基準 {_fmt_pct(gm_base)}"
        return 0.01, f"毛利率 {_fmt_pct(gm)} 略高於產業基準 {_fmt_pct(gm_base)}"

    if gm < gm_good:
        adj = _linear_score(gm, gm_base, gm_good, 0.01, 0.03)
        return adj, f"毛利率 {_fmt_pct(gm)} 位於產業基準～good 區間，僅小幅加分"
    if gm < gm_excellent:
        adj = _linear_score(gm, gm_good, gm_excellent, 0.04, 0.08)
        return adj, f"毛利率 {_fmt_pct(gm)} 位於 good～excellent 區間，漸進式加分"
    # 超過 excellent 才給較高相對加分，但仍交由產業 max_quality_factor 截斷。
    extra = min(0.04, max(0.0, gm - gm_excellent) * 0.5)
    return 0.09 + extra, f"毛利率 {_fmt_pct(gm)} 高於產業 excellent 門檻 {_fmt_pct(gm_excellent)}，相對同業優勢明確"


def _roe_adjustment(roev: Optional[float]) -> tuple[float, str]:
    """第 17-C-5：ROE 漸進式調整，不直接把品質推到上限。"""
    if roev is None:
        return 0.0, "ROE 缺值"
    if roev < 0:
        return -0.08, f"ROE {_fmt_pct(roev)} 為負"
    if roev < 0.08:
        return -0.04, f"ROE {_fmt_pct(roev)} 偏低"
    if roev < 0.15:
        return 0.0, f"ROE {_fmt_pct(roev)} 中性"
    if roev < 0.25:
        return _linear_score(roev, 0.15, 0.25, 0.02, 0.04), f"ROE {_fmt_pct(roev)} 正常偏佳，小幅加分"
    if roev < 0.35:
        return _linear_score(roev, 0.25, 0.35, 0.05, 0.07), f"ROE {_fmt_pct(roev)} 優良"
    return 0.09, f"ROE {_fmt_pct(roev)} 極佳"


def _operating_margin_guard(
    opm: Optional[float],
    gm: Optional[float],
    factor: float,
    notes: List[str],
) -> float:
    """第 17-C-5：營益率輔助判斷，避免高毛利但費用率吃掉獲利仍拿高品質分。"""
    if opm is None:
        return factor
    if opm < 0:
        notes.append(f"營益率 {_fmt_pct(opm)} 為負，品質折價")
        return min(factor, 0.94)
    if gm is not None and gm >= 0.30 and opm < 0.05 and factor > 1.0:
        notes.append(f"毛利率 {_fmt_pct(gm)} 不低，但營益率僅 {_fmt_pct(opm)}，費用率/營運槓桿壓力，品質溢價減半")
        return 1.0 + (factor - 1.0) * 0.5
    if opm < 0.03 and factor > 1.0:
        notes.append(f"營益率 {_fmt_pct(opm)} 偏低，品質溢價折半")
        return 1.0 + (factor - 1.0) * 0.5
    return factor


def quality_factor_relative(
    gross_margin: Any,
    roe: Any = None,
    revenue_yoy: Any = None,
    eps_positive: bool = True,
    debt_to_equity: Any = None,
    warning_count: int = 0,
    calibration: Dict[str, Any] = None,
    operating_margin: Any = None,
    free_cash_flow: Any = None,
) -> Dict[str, Any]:
    """第 17-C-5：品質係數細緻化。

    不再採用「高於 good 門檻就直接套 max_quality_factor」。
    改為：
    1) 絕對毛利率水準
    2) 相對產業毛利位置，含低於同業分層扣分
    3) ROE 漸進式加減分
    4) 營益率、D/E、FCF 與資料分歧防呆
    5) 最後才套產業 max_quality_factor
    """
    calibration = calibration or {}
    gm = _pct01(gross_margin)
    roev = _pct01(roe)
    opm = _pct01(operating_margin)
    de = _sf(debt_to_equity)
    fcf = _sf(free_cash_flow)
    max_q = _sf(calibration.get("max_quality_factor"), 1.12) or 1.12
    min_q = _sf(calibration.get("min_quality_factor"), 0.86) or 0.86
    gm_base = _sf(calibration.get("gross_margin_baseline"))
    gm_good = _sf(calibration.get("gross_margin_good"))
    gm_excellent = _sf(calibration.get("gross_margin_excellent"))

    if not eps_positive:
        return {"factor": 1.00, "reason": "EPS 不穩或為負，不給品質係數溢價"}

    notes: List[str] = []
    adjustment = 0.0

    abs_adj, abs_note = _absolute_margin_adjustment(gm)
    rel_adj, rel_note = _relative_margin_adjustment(gm, gm_base, gm_good, gm_excellent)
    roe_adj, roe_note = _roe_adjustment(roev)

    adjustment += abs_adj + rel_adj + roe_adj
    notes.extend([abs_note, rel_note, roe_note])

    factor = 1.0 + adjustment

    # 營益率輔助判斷。
    before_op = factor
    factor = _operating_margin_guard(opm, gm, factor, notes)
    if opm is not None and before_op == factor:
        notes.append(f"營益率 {_fmt_pct(opm)} 未觸發品質折扣")

    # 營收、負債、FCF、防呆。
    rev = _pct01(revenue_yoy)
    if rev is not None and rev < 0 and factor > 1.0:
        factor = 1 + (factor - 1) * 0.5
        notes.append("營收 YoY 為負，品質溢價減半")
    if de is not None:
        if de > 4 and factor > 1.0:
            factor = 1.0
            notes.append(f"D/E {de:.2f} 過高，品質溢價歸零")
        elif de > 2 and factor > 1.0:
            factor = 1 + (factor - 1) * 0.5
            notes.append(f"D/E {de:.2f} 偏高，品質溢價減半")
    if fcf is not None and fcf < 0 and factor > 1.08:
        factor = min(factor, 1.08)
        notes.append("FCF 為負，品質係數上限 ×1.08")
    if warning_count > 0 and factor > 1.10:
        factor = min(factor, 1.10)
        notes.append("資料分歧存在，品質係數上限 ×1.10")

    # 套上下限；max_quality_factor 只是硬上限，不是一般加分。
    if factor > max_q:
        factor = max_q
        notes.append(f"套用產業品質係數硬上限 ×{max_q:.2f}")
    if factor < min_q:
        factor = min_q
        notes.append(f"套用產業品質係數下限 ×{min_q:.2f}")

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
    # 17-B-4：一項重大分歧不再直接打到 ×0.80，避免從過度樂觀修成過度保守。
    if danger >= 2 or count >= 5:
        f, label = 0.70, "低 / 資料異常"
    elif count >= 3:
        f, label = 0.82, "偏低"
    elif danger >= 1:
        f, label = 0.90, "中 / 重大分歧"
    elif count == 2:
        f, label = 0.90, "中"
    elif count == 1:
        f, label = 0.95, "中高"
    else:
        f, label = 1.00, "高"
    return {"factor": f, "label": label, "reason": f"分歧警告 {len(warnings)} 項、資料校驗提醒 {len(dq_warnings)} 項"}


def detect_cycle_recovery_state(
    industry_profile: Dict[str, Any],
    calibration: Dict[str, Any],
    growth_pack: Dict[str, Any],
    gross_margin: Any = None,
    roe: Any = None,
    revenue_yoy: Any = None,
) -> Dict[str, Any]:
    """判斷是否屬於循環復甦 / 訂單週期復甦。避免低基期股被成長與品質雙重誤判。"""
    p = industry_profile or {}
    key = str(p.get("model_key") or p.get("taxon_key") or "")
    recovery_keys = {
        "ABF_SUBSTRATE", "SERVER_PCB_BOARD", "OSAT_TESTING", "PROBE_TEST_INTERFACE",
        "SEMICAP_COWOS_EQUIPMENT", "FAB_FACILITY_MATERIALS", "THERMAL_LIQUID_COOLING",
        "EV_AUTO_ELECTRONICS", "ROBOTICS_AUTOMATION",
    }
    sensitive = p.get("recovery_sensitive") or calibration.get("recovery_sensitive") or bool(p.get("cyclical")) or key in recovery_keys
    if not sensitive:
        return {"state": "normal_growth", "label": "一般成長", "quality_floor": None, "growth_cap": None, "reason": "非循環復甦敏感產業"}

    growth = growth_pack.get("growth") if isinstance(growth_pack, dict) else None
    gm = _pct01(gross_margin)
    roev = _pct01(roe)
    rev = _pct01(revenue_yoy)
    gm_base = _sf(calibration.get("gross_margin_baseline"))

    weak_quality = False
    weak_notes = []
    if gm is not None and gm_base is not None and gm < gm_base:
        weak_quality = True
        weak_notes.append(f"毛利率 {_fmt_pct(gm)} 低於產業基準 {_fmt_pct(gm_base)}")
    if roev is not None and roev < 0.10:
        weak_quality = True
        weak_notes.append(f"ROE {_fmt_pct(roev)} 尚未恢復")

    rev_ok = rev is None or rev >= -0.05
    if growth is not None and growth >= 0.50 and weak_quality and rev_ok:
        return {
            "state": "cycle_recovery",
            "label": "循環復甦",
            "quality_floor": 0.93,
            "growth_cap": 1.15,
            "reason": "Forward EPS / 營收顯示復甦，但當期品質指標尚未完全恢復；" + "、".join(weak_notes),
        }
    if growth is not None and growth >= 1.00 and bool(p.get("cyclical")):
        return {
            "state": "low_base_recovery",
            "label": "低基期修復",
            "quality_floor": 0.92,
            "growth_cap": 1.12,
            "reason": "循環產業 Forward EPS 高成長，疑似低基期修復，成長係數與品質扣分同時保守化。",
        }
    if bool(p.get("cyclical")):
        return {"state": "cyclical_normal", "label": "循環一般", "quality_floor": None, "growth_cap": 1.12, "reason": "循環產業，避免把單期 EPS 當長期結構性成長。"}
    return {"state": "normal_growth", "label": "一般成長", "quality_floor": None, "growth_cap": None, "reason": "未偵測到明確復甦狀態"}

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



def build_turnaround_event_pack(industry_profile: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """17-C-4：EPS 尚未穩定轉正時停用 P/E 估值，改用轉機 / 事件模型。"""
    rows = [
        {"類型": "轉機 / 事件模型", "項目": "P/E 公式估值", "倍率/係數": "停用", "說明": "Forward EPS、TTM EPS 或年度 EPS 尚未穩定轉正，不適合使用 P/E 公式合理價。"},
        {"類型": "轉機 / 事件模型", "項目": "主要觀察", "倍率/係數": "—", "說明": "連續單季 EPS 轉正、營益率改善、月營收連續成長、訂單落地、法人開始提供明確 Forward EPS。"},
        {"類型": "轉機 / 事件模型", "項目": "替代估值", "倍率/係數": "P/B / 事件", "說明": "可輔助觀察 P/B、淨值、現金流與籌碼；不可輸出負的公式合理價或負的極限價。"},
    ]
    warnings = ["Forward EPS / TTM EPS 未穩定轉正，已停用 P/E Dynamic Cap 買進估值", "此類標的應改用轉機事件模型，不輸出公式合理價 / 公式極限價"]
    if reason:
        warnings.append(reason)
    return {
        "available": False,
        "valuation_mode": "turnaround_event",
        "final_cap": None,
        "raw_cap": None,
        "formula_cap": None,
        "optimistic_cap": None,
        "hard_cap": None,
        "operable_cap_low": None,
        "operable_cap_high": None,
        "warnings": warnings,
        "industry_profile": industry_profile,
        "report": pd.DataFrame(rows),
        "explanation": "17-C-4：負 EPS / 轉機股防呆；停用 P/E 估值，避免出現負目標價。",
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
    operating_margin: Any = None,
    roe: Any = None,
    debt_to_equity: Any = None,
    revenue_yoy: Any = None,
    free_cash_flow: Any = None,
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
    positive_forward_eps = any((_sf(x) or 0) > 0 for x in [consensus_forward_eps, system_forward_eps, ai_forward_eps])
    positive_profit_eps = any((_sf(x) or 0) > 0 for x in [consensus_forward_eps, system_forward_eps, ai_forward_eps, ttm_eps, ai_ttm_eps])
    eps_positive = positive_profit_eps
    warn_count = len(divergence_warnings or []) + len(dq_warnings or [])

    # 17-C-4：只要主要模型是 P/E / Forward P/E，但 Forward EPS 與 TTM EPS 尚未穩定轉正，
    # 不應再輸出 P/E 公式估值，避免出現負合理價、負極限價。
    adopted_forward_eps = _sf(consensus_forward_eps) or _sf(system_forward_eps) or _sf(ai_forward_eps)
    adopted_ttm_eps = _sf(ttm_eps) if _sf(ttm_eps) is not None else _sf(ai_ttm_eps)
    # 17-C-4：負 EPS / 無 Forward EPS 防呆。
    # 若 TTM 與 Forward 都尚未穩定轉正，全面停用 P/E 估值；若 TTM 為負但有明確正 Forward EPS，可保留 Forward P/E 但列高風險。
    if primary_valuation in {"forward_pe", "pe_pb_crosscheck", "forward_pe_pb_cycle"} and ((adopted_forward_eps is None or adopted_forward_eps <= 0) and (adopted_ttm_eps is None or adopted_ttm_eps <= 0)):
        pack = build_turnaround_event_pack(p, "EPS 尚未穩定轉正，Dynamic Cap 停用 P/E 估值，改用轉機 / 事件模型。")
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "model_version": "Dynamic Cap 2.0 calibration 17-C-7C-1"})
        return pack

    # 17-B-4：低軌衛星、機器人、生技等條件式 P/E 模型，若 EPS / 訂單未落地，直接切換事件模型。
    if p.get("event_model_if_eps_unstable") and not positive_forward_eps:
        pack = build_event_theme_pack(p)
        note = p.get("event_switch_note") or "EPS / 訂單未落地，依 17-B-4 校準規則改用事件模型。"
        pack["warnings"] = list(pack.get("warnings") or []) + [note]
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p, "model_version": "Dynamic Cap 2.0 calibration 17-C-7C-1"})
        return pack

    if pe_app is False or primary_valuation in {"event_chip", "theme_event"}:
        pack = build_event_theme_pack(p)
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p, "model_version": "Dynamic Cap 2.0 calibration 17-C-7C-1"})
        return pack
    if primary_valuation.startswith("pb") or primary_valuation in {"pb", "pb_roe"}:
        pack = build_pb_cycle_pack(current_price, pb_ratio, p)
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p, "model_version": "Dynamic Cap 2.0 calibration 17-C-7C-1"})
        return pack

    base = _sf(c.get("base_pe"), 20.0) or 20.0
    rows: List[Dict[str, Any]] = []
    _add_row(rows, "基準", "產業基準倍率", f"{base:.1f}x", f"{p.get('model_label', p.get('display_name', '一般產業'))} 17-C-7C-1 校準後 base_pe；非買進追價倍率")
    hybrid_summary = c.get("hybrid_summary") or {}
    if hybrid_summary.get("enabled"):
        _add_row(rows, "基準", "混合產業權重", f"base {hybrid_summary.get('mixed_base_pe'):.1f}x / soft {hybrid_summary.get('mixed_soft_ceiling_pe'):.1f}x / hard {hybrid_summary.get('mixed_hard_ceiling_pe'):.1f}x", hybrid_summary.get("reason", ""))
    elif p.get("hybrid_taxons"):
        _add_row(rows, "基準", "混合產業權重", "未啟用", hybrid_summary.get("reason", "混合分類未通過防呆"))

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
        operating_margin=operating_margin,
        free_cash_flow=free_cash_flow,
    )
    # 17-B-4：循環復甦股通用判斷，避免「未來 EPS 加分」與「當期低 ROE/毛利重扣」雙殺。
    recovery = detect_cycle_recovery_state(p, c, g, gross_margin=gross_margin, roe=roe, revenue_yoy=revenue_yoy)
    if recovery.get("growth_cap") is not None and float(g.get("factor", 1) or 1) > float(recovery.get("growth_cap")):
        g = dict(g)
        g["factor"] = float(recovery.get("growth_cap"))
        g["reason"] = str(g.get("reason", "")) + f"；17-B-4 {recovery.get('label')} 狀態，成長係數上限 ×{float(recovery.get('growth_cap')):.2f}"
    if recovery.get("quality_floor") is not None and float(q.get("factor", 1) or 1) < float(recovery.get("quality_floor")):
        q = dict(q)
        q["factor"] = float(recovery.get("quality_floor"))
        q["reason"] = str(q.get("reason", "")) + f"；17-B-4 {recovery.get('label')} 狀態，避免復甦股被當期低毛利/低ROE雙殺，品質係數下限 ×{float(recovery.get('quality_floor')):.2f}"

    th = theme_order_factor(themes, p, eps_positive=eps_positive, data_warning_count=warn_count, calibration=c)
    sc = scale_growth_flex_factor(info.get("marketCap"), eps_positive=eps_positive, liquidity_ok=(liq.get("factor", 1) >= 0.85), calibration=c)
    geo = geopolitical_factor(p, c)
    cls_factor = float(p.get("classification_confidence_factor", 1.0) or 1.0)
    if cls_factor < 1.0:
        cls_reason = f"產業分類來源：{p.get('classification_source', p.get('mapping_source', '—'))}；可信度 {p.get('classification_confidence', 'low')}；待人工確認，Dynamic Cap 先套分類可信度折扣。"
    else:
        cls_reason = f"產業分類來源：{p.get('classification_source', p.get('mapping_source', '—'))}；不套分類折扣。"
    cls = {"factor": cls_factor, "reason": cls_reason}

    for name, pack in [
        ("成長係數", g),
        ("品質係數（毛利率相對化 + ROE）", q),
        ("題材 / 訂單係數", th),
        ("規模與成長彈性係數", sc),
        ("地緣政治 / 供應鏈風險係數", geo),
        ("產業分類可信度係數", cls),
    ]:
        _add_factor(rows, name, float(pack.get("factor", 1.0) or 1.0), pack.get("reason", ""))

    _add_row(rows, "復甦判斷", "循環 / 訂單復甦狀態", recovery.get("label", "一般成長"), recovery.get("reason", ""))

    raw_cap = base * float(g.get("factor", 1) or 1) * float(q.get("factor", 1) or 1) * float(th.get("factor", 1) or 1) * float(sc.get("factor", 1) or 1) * float(geo.get("factor", 1) or 1) * cls_factor
    fc = pe_floor_ceiling(p, c)
    _add_row(rows, "小計", "原始建議倍率", f"{raw_cap:.1f}x", "產業基準 × 成長係數 × 品質係數 × 題材係數 × 規模係數 × 地緣政治折價 × 分類可信度係數")

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

    # 17-B-4：倍率分層。final_cap 是可操作中性倍率；raw/soft/hard 分別作公式合理、樂觀與極限參考。
    formula_cap = min(raw_cap, fc["soft_ceiling"])
    optimistic_cap = fc["soft_ceiling"]
    hard_cap = fc["hard_ceiling"]
    operable_cap_low = max(fc["floor"], final_cap * 0.95)
    if recovery.get("state") in {"cycle_recovery", "low_base_recovery", "cyclical_normal"}:
        operable_cap_high = min(formula_cap, final_cap * 1.18, fc["soft_ceiling"])
    else:
        operable_cap_high = min(formula_cap, final_cap * 1.12, fc["soft_ceiling"])
    if operable_cap_high < operable_cap_low:
        operable_cap_high = operable_cap_low

    if recovery.get("state") in {"cycle_recovery", "low_base_recovery"}:
        warnings.append("循環復甦股：請同時看保守/中性/樂觀倍率區間，不宜只用單點 Cap 判斷。")

    if p.get("pe_trap_warning"):
        warnings.append("本產業存在 P/E 陷阱，低 P/E 不一定代表低估")
    if warn_count >= 3:
        warnings.append("資料分歧或校驗提醒較多，Dynamic Cap 已折扣")
    if liq.get("factor", 1) < 0.9:
        warnings.append("流動性偏低，已套用流動性折扣")

    # 17-C-4：市場隱含倍率。這不是買進倍率，而是用來解釋「現價為何高於系統估值」。
    adopted_forward_eps_for_implied = _sf(consensus_forward_eps) or _sf(system_forward_eps) or _sf(ai_forward_eps)
    market_implied_forward_pe = None
    market_implied_status = "Forward EPS 缺值或 <= 0，無法反推現價隱含 Forward P/E。"
    cp_for_implied = _sf(current_price)
    if adopted_forward_eps_for_implied is not None and adopted_forward_eps_for_implied > 0 and cp_for_implied is not None and cp_for_implied > 0:
        market_implied_forward_pe = cp_for_implied / adopted_forward_eps_for_implied
        if market_implied_forward_pe > fc["hard_ceiling"]:
            market_implied_status = "現價隱含 Forward P/E 已高於系統 hard ceiling，屬市場重估 / 題材動能區，不可直接當可操作買點。"
        elif market_implied_forward_pe > fc["soft_ceiling"]:
            market_implied_status = "現價隱含 Forward P/E 高於 soft ceiling，屬偏樂觀估值區。"
        elif market_implied_forward_pe > final_cap:
            market_implied_status = "現價隱含 Forward P/E 高於可操作倍率，但仍低於產業硬上限。"
        else:
            market_implied_status = "現價隱含 Forward P/E 未高於可操作倍率。"

    return {
        "available": True,
        "valuation_mode": primary_valuation,
        "model_version": "Dynamic Cap 2.0 calibration 17-C-7C-1",
        "base_multiple": base,
        "growth_premium": g,  # 保留舊 key，實際為 growth factor pack
        "gross_margin_premium": q,  # 保留舊 key，實際為 quality factor pack
        "roe_quality_premium": q,
        "theme_premium": th,
        "market_cap_adjustment": sc,
        "geopolitical_factor": geo,
        "classification_confidence_factor": cls,
        "data_confidence_factor": dc,
        "valuation_risk_factor": vr,
        "liquidity_factor": liq,
        "raw_cap": raw_cap,
        "formula_cap": formula_cap,
        "optimistic_cap": optimistic_cap,
        "hard_cap": hard_cap,
        "operable_cap_low": operable_cap_low,
        "operable_cap_high": operable_cap_high,
        "cycle_recovery_state": recovery,
        "pre_clip_cap": pre_clip_cap,
        "final_cap": final_cap,
        "floor_cap": fc["floor"],
        "soft_ceiling_cap": fc["soft_ceiling"],
        "ceiling_cap": fc["hard_ceiling"],
        "hard_ceiling_cap": fc["hard_ceiling"],
        "adopted_forward_eps_for_implied": adopted_forward_eps_for_implied,
        "market_implied_forward_pe": market_implied_forward_pe,
        "market_implied_status": market_implied_status,
        "hit_hard_ceiling": hit_hard_ceiling,
        "warnings": warnings,
        "industry_profile": p,
        "report": pd.DataFrame(rows),
        "explanation": "Dynamic Cap 2.0 17-B-4：已加入循環復甦判斷、分歧折扣校準、公式/可操作/極限倍率分離與 hard ceiling 顯示修正。",
    }

# ===== 第 17-C-4：Dynamic Cap 校準覆寫 =====
CALIBRATION_DEFAULTS.update({
    "FOUNDRY_ADVANCED": {"base_pe": 24.0, "floor_pe": 18.0, "soft_ceiling_pe": 30.0, "hard_ceiling_pe": 35.0, "max_growth_factor": 1.14, "max_quality_factor": 1.10, "max_theme_factor": 1.05, "max_scale_factor": 1.00, "gross_margin_baseline": 0.54, "gross_margin_good": 0.58, "gross_margin_excellent": 0.62, "baked_in_themes": ["ai", "hpc", "cowos", "先進製程"], "geopolitical_factor": 0.92},
    "FOUNDRY_MATURE": {"base_pe": 12.0, "floor_pe": 8.0, "soft_ceiling_pe": 18.0, "hard_ceiling_pe": 22.0, "max_growth_factor": 1.10, "max_quality_factor": 1.08, "max_theme_factor": 1.00, "max_scale_factor": 1.00, "gross_margin_baseline": 0.24, "gross_margin_good": 0.32, "gross_margin_excellent": 0.40, "recovery_sensitive": True},
    "IC_DESIGN_ASIC_IP": {"base_pe": 35.0, "floor_pe": 22.0, "soft_ceiling_pe": 55.0, "hard_ceiling_pe": 70.0, "max_growth_factor": 1.25, "max_quality_factor": 1.22, "max_theme_factor": 1.18, "max_scale_factor": 1.08, "gross_margin_baseline": 0.45, "gross_margin_good": 0.55, "gross_margin_excellent": 0.65, "baked_in_themes": ["ai asic", "asic", "ip", "矽智財"], "geopolitical_factor": 0.97},
    "IC_DESIGN_CONSUMER": {"base_pe": 18.0, "floor_pe": 10.0, "soft_ceiling_pe": 26.0, "hard_ceiling_pe": 32.0, "max_growth_factor": 1.12, "max_quality_factor": 1.10, "max_theme_factor": 1.02, "max_scale_factor": 1.03, "gross_margin_baseline": 0.32, "gross_margin_good": 0.40, "gross_margin_excellent": 0.48, "recovery_sensitive": True},
    "PROBE_AI_ASIC": {"base_pe": 45.0, "floor_pe": 24.0, "soft_ceiling_pe": 65.0, "hard_ceiling_pe": 75.0, "max_growth_factor": 1.25, "max_quality_factor": 1.20, "max_theme_factor": 1.10, "max_scale_factor": 1.08, "gross_margin_baseline": 0.45, "gross_margin_good": 0.52, "gross_margin_excellent": 0.58, "baked_in_themes": ["ai asic", "cpo", "mems", "探針卡", "測試介面"], "geopolitical_factor": 0.97},
    "PROBE_STANDARD": {"base_pe": 18.0, "floor_pe": 10.0, "soft_ceiling_pe": 28.0, "hard_ceiling_pe": 35.0, "max_growth_factor": 1.12, "max_quality_factor": 1.10, "max_theme_factor": 1.05, "max_scale_factor": 1.03, "gross_margin_baseline": 0.25, "gross_margin_good": 0.35, "gross_margin_excellent": 0.45, "baked_in_themes": ["探針", "測試"], "recovery_sensitive": True},
    "TURNAROUND_PROBE_TEST_THEME": {"base_pe": None, "floor_pe": None, "soft_ceiling_pe": None, "hard_ceiling_pe": None, "pb_range": (0.8, 2.5)},
    "THERMAL_LIQUID": {"base_pe": 34.0, "floor_pe": 20.0, "soft_ceiling_pe": 48.0, "hard_ceiling_pe": 60.0, "max_growth_factor": 1.20, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08, "gross_margin_baseline": 0.26, "gross_margin_good": 0.32, "gross_margin_excellent": 0.40, "baked_in_themes": ["水冷", "液冷", "ai伺服器"]},
    "THERMAL_AIR": {"base_pe": 18.0, "floor_pe": 10.0, "soft_ceiling_pe": 28.0, "hard_ceiling_pe": 35.0, "max_growth_factor": 1.12, "max_quality_factor": 1.10, "max_theme_factor": 1.03, "max_scale_factor": 1.03, "gross_margin_baseline": 0.20, "gross_margin_good": 0.26, "gross_margin_excellent": 0.32, "recovery_sensitive": True},
    "SEMICAP_COWOS_EQUIPMENT": {"base_pe": 32.0, "floor_pe": 20.0, "soft_ceiling_pe": 50.0, "hard_ceiling_pe": 65.0, "max_growth_factor": 1.22, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08, "gross_margin_baseline": 0.30, "gross_margin_good": 0.38, "gross_margin_excellent": 0.45, "baked_in_themes": ["cowos", "先進封裝", "設備"], "geopolitical_factor": 0.96, "recovery_sensitive": True},
    "GRID_POWER_STORAGE": {"base_pe": 18.0, "floor_pe": 12.0, "soft_ceiling_pe": 30.0, "hard_ceiling_pe": 38.0, "max_growth_factor": 1.14, "max_quality_factor": 1.12, "max_theme_factor": 1.06, "max_scale_factor": 1.04, "gross_margin_baseline": 0.18, "gross_margin_good": 0.24, "gross_margin_excellent": 0.30},
    "OPTICAL_COMM_SILICON_PHOTONICS": {"base_pe": 36.0, "floor_pe": 22.0, "soft_ceiling_pe": 54.0, "hard_ceiling_pe": 68.0, "max_growth_factor": 1.22, "max_quality_factor": 1.18, "max_theme_factor": 1.12, "max_scale_factor": 1.08, "gross_margin_baseline": 0.32, "gross_margin_good": 0.40, "gross_margin_excellent": 0.48, "baked_in_themes": ["矽光子", "cpo", "800g", "1.6t"]},
    "GENERAL": {"base_pe": 15.0, "floor_pe": 8.0, "soft_ceiling_pe": 24.0, "hard_ceiling_pe": 30.0, "max_growth_factor": 1.10, "max_quality_factor": 1.08, "max_theme_factor": 1.02, "max_scale_factor": 1.00, "gross_margin_baseline": None}
})
