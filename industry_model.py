"""
產業估值模型模組（第 17-A 階段）。

資料流：
1. stock_mapping.py 明確指定：股票 → primary_taxon + themes
2. industry_taxonomy.py 取得主要估值模型、P/E/P/B 適用性、循環股警示
3. stocklist.txt 只作 UI 分類輔助與人工可讀，不承載估值規則
"""
import os
import re
import pandas as pd

from industry_taxonomy import INDUSTRY_TAXONOMY, get_taxonomy
from stock_mapping import STOCK_MAPPING


def _safe_str(x):
    return "" if x is None else str(x)


def _read_stocklist_category(stock_id):
    """從 stocklist.txt 找出股票所在分類。找不到回傳空字串。"""
    sid = _safe_str(stock_id).strip()
    if not sid:
        return ""
    paths = ["stocklist.txt", os.path.join(os.getcwd(), "stocklist.txt")]
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            current_cat = ""
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    if "【" in line and "】" in line:
                        m = re.search(r"【(.+?)】", line)
                        current_cat = m.group(1).strip() if m else line.strip("★ ")
                        continue
                    if line.startswith(sid + ","):
                        return current_cat
        except Exception:
            continue
    return ""


def _infer_taxon_from_text(stock_id, stock_name="", category="", sector="", industry=""):
    """找不到 stock_mapping 時的保守關鍵字備援。"""
    text = " ".join([_safe_str(stock_id), _safe_str(stock_name), _safe_str(category), _safe_str(sector), _safe_str(industry)]).lower()
    sid = _safe_str(stock_id).strip()
    if sid in {"8033"} or any(k.lower() in text for k in ["題材", "軍工", "無人機", "drone"]):
        return "THEME_EVENT"
    keyword_map = [
        ("FOUNDRY", ["晶圓代工", "foundry"]),
        ("IC_DESIGN_ASIC", ["ic設計", "ic 設計", "asic", "晶片", "semiconductor"]),
        ("IP_EDA_DESIGN_SERVICE", ["矽智財", "ip", "eda"]),
        ("OSAT_TESTING", ["封測", "測試", "osat"]),
        ("PROBE_TEST_INTERFACE", ["探針", "測試介面", "檢測"]),
        ("SEMICAP_COWOS_EQUIPMENT", ["cowos", "先進封裝", "半導體設備", "設備"]),
        ("FAB_FACILITY_MATERIALS", ["廠務", "無塵室", "耗材", "材料"]),
        ("ABF_SUBSTRATE", ["abf", "載板"]),
        ("SERVER_PCB_BOARD", ["pcb", "主板", "ccl"]),
        ("AI_SERVER_ODM", ["伺服器代工", "組裝", "ai伺服器", "ai 伺服器", "server"]),
        ("CONNECTOR_CABLE", ["連接器", "線材", "高速傳輸"]),
        ("SERVER_CHASSIS_RAIL", ["機殼", "滑軌", "機構件"]),
        ("POWER_BBU", ["電源", "bbu", "power"]),
        ("THERMAL_LIQUID_COOLING", ["散熱", "水冷", "thermal", "heat"]),
        ("OPTICAL_COMM_SILICON_PHOTONICS", ["矽光子", "光通訊", "cpo", "optical communication"]),
        ("NETWORK_SWITCH", ["網通", "交換器", "network"]),
        ("OPTICS_LENS_MODULE", ["鏡頭", "光學", "lens", "optics"]),
        ("ROBOTICS_AUTOMATION", ["機器人", "自動化", "robot"]),
        ("SPACE_LEO_SATELLITE", ["低軌", "衛星", "太空", "satellite"]),
        ("EV_AUTO_ELECTRONICS", ["車用", "電動車", "ev", "automotive"]),
        ("GRID_POWER_STORAGE", ["重電", "電網", "儲能", "綠能", "grid"]),
        ("SOFTWARE_SECURITY_CLOUD", ["軟體", "資安", "雲端", "系統整合", "software"]),
        ("MEMORY_CYCLE", ["記憶體", "dram", "nand", "memory"]),
        ("DISPLAY_LED_CYCLE", ["面板", "led", "display"]),
        ("PASSIVE_COMPONENT_CYCLE", ["被動元件", "電容", "電阻", "電感"]),
        ("FINANCIAL", ["金融", "金控", "銀行", "保險"]),
        ("TRADITIONAL_CYCLE", ["化工", "塑化", "鋼鐵", "水泥", "橡膠"]),
        ("SHIPPING_CYCLE", ["航運", "海運", "物流"]),
        ("BIOTECH_MEDICAL", ["生技", "醫療", "藥", "medical", "biotech"]),
        ("CONSUMER_TOURISM", ["觀光", "餐飲", "消費", "tourism"]),
    ]
    for taxon, keywords in keyword_map:
        if any(k.lower() in text for k in keywords):
            return taxon
    return "GENERAL"


def _format_valuation_framework(tax):
    primary = tax.get("primary_valuation") or "—"
    secondary = tax.get("secondary_valuation") or []
    if isinstance(secondary, (list, tuple)):
        secondary_text = "、".join(str(x) for x in secondary) if secondary else "—"
    else:
        secondary_text = str(secondary)
    return f"主要：{primary}；次要：{secondary_text}"


def _pe_suitability_text(value):
    if value is True:
        return "適用"
    if value is False:
        return "不適用"
    if value == "secondary_only":
        return "僅輔助，優先 P/B / 週期"
    if value == "conditional":
        return "條件式適用，需確認 EPS/訂單落地"
    return str(value)


def get_industry_valuation_profile(stock_id, stock_name="", sector="", industry=""):
    """回傳產業估值模型 profile。"""
    sid = _safe_str(stock_id).strip()
    category = _read_stocklist_category(sid)
    mapping = STOCK_MAPPING.get(sid)
    if mapping:
        taxon_key = mapping.get("primary_taxon", "GENERAL")
        themes = list(mapping.get("themes", []))
        mapping_source = "stock_mapping.py"
        mapped_name = mapping.get("name", stock_name)
    else:
        taxon_key = _infer_taxon_from_text(sid, stock_name, category, sector, industry)
        themes = []
        mapping_source = "keyword_fallback"
        mapped_name = stock_name

    tax = dict(get_taxonomy(taxon_key))
    profile = dict(tax)
    profile.update({
        "model_key": taxon_key,
        "taxon_key": taxon_key,
        "model_label": tax.get("display_name", "一般產業 / 尚未分類"),
        "parent_category": tax.get("parent", "未分類"),
        "stock_id": sid,
        "stock_name": _safe_str(mapped_name),
        "themes": themes,
        "themes_text": "、".join(themes) if themes else "—",
        "matched_category": category or "未在 stocklist.txt 找到分類",
        "stocklist_category": category or "未在 stocklist.txt 找到分類",
        "mapping_source": mapping_source,
        "valuation_framework": _format_valuation_framework(tax),
        "valuation_method": _format_valuation_framework(tax),
        "primary_metrics": "、".join(tax.get("valuation_focus", [])) or "—",
        "caution_points": "、".join(tax.get("risk_flags", [])) or "—",
        "cap_hint": tax.get("base_pe"),
        "cap_adjust": 0.0,
        "pe_model_suitable": False if tax.get("pe_applicable") is False else True,
        "pe_applicability_text": _pe_suitability_text(tax.get("pe_applicable")),
        "warning_note": tax.get("note", "—"),
        "operable_discount_factor": tax.get("operable_discount_factor", 0.95),
    })
    return profile


def build_industry_valuation_model_report(profile):
    """產業估值模型說明表。"""
    p = profile or get_industry_valuation_profile("")
    pe_range = p.get("pe_range")
    pb_range = p.get("pb_range")
    pe_range_text = f"{pe_range[0]}x～{pe_range[1]}x" if isinstance(pe_range, (tuple, list)) and len(pe_range) == 2 else "不以 P/E 為主"
    pb_range_text = f"{pb_range[0]}x～{pb_range[1]}x" if isinstance(pb_range, (tuple, list)) and len(pb_range) == 2 else "—"
    rows = [
        {"項目": "匹配產業模型", "內容": p.get("model_label", "一般產業")},
        {"項目": "主分類", "內容": p.get("parent_category", "—")},
        {"項目": "股票對應來源", "內容": p.get("mapping_source", "—")},
        {"項目": "stocklist 分類", "內容": p.get("matched_category", "—")},
        {"項目": "題材標籤", "內容": p.get("themes_text", "—")},
        {"項目": "主要估值方式", "內容": p.get("primary_valuation", "—")},
        {"項目": "次要估值方式", "內容": "、".join(p.get("secondary_valuation", [])) if isinstance(p.get("secondary_valuation"), list) else p.get("secondary_valuation", "—")},
        {"項目": "優先觀察指標", "內容": p.get("primary_metrics", "—")},
        {"項目": "P/E 參考區間", "內容": pe_range_text},
        {"項目": "P/B 參考區間", "內容": pb_range_text},
        {"項目": "P/E 模型適用性", "內容": p.get("pe_applicability_text", "—")},
        {"項目": "是否循環股", "內容": "是" if p.get("cyclical") else "否"},
        {"項目": "P/E 陷阱提醒", "內容": "是，低 P/E 不一定代表低估" if p.get("pe_trap_warning") else "否"},
        {"項目": "題材溢價", "內容": "允許，但需驗證財報落地" if p.get("theme_premium_allowed") else "不建議額外給題材高倍率"},
        {"項目": "流動性敏感", "內容": "是，後續需納入 20 日均量折扣" if p.get("liquidity_sensitive") else "較低"},
        {"項目": "可操作估值折減", "內容": f"{p.get('operable_discount_factor', 1.0):.2f} 倍"},
        {"項目": "風險旗標", "內容": p.get("caution_points", "—")},
        {"項目": "模型提醒", "內容": p.get("warning_note", "—")},
    ]
    return pd.DataFrame(rows)
