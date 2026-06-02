"""
動態 Cap 2.0 全加總倍率模型（第 17-B 階段）。

設計原則：
- P/E 與 P/B 分流：若產業屬 pb_cycle 或 P/E 不適用，不輸出 P/E 買進倍率。
- 成長溢價採階層式優先級，避免 Forward EPS 與營收 YoY 重複加分。
- 先加總形成 raw_cap，再乘上資料可信度、估值風險與流動性折扣。
- 最終倍率套用產業 floor / ceiling，避免扣到 0 或負數。
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


def _add_factor(rows: List[Dict[str, Any]], name: str, value: float, reason: str) -> None:
    rows.append({"類型": "加減項", "項目": name, "倍率/係數": f"{value:+.1f}x", "說明": reason})


def _add_discount(rows: List[Dict[str, Any]], name: str, factor: float, reason: str) -> None:
    rows.append({"類型": "折扣項", "項目": name, "倍率/係數": f"×{factor:.2f}", "說明": reason})


def gross_margin_premium(gross_margin: Any, revenue_yoy: Any = None, eps_positive: bool = True, roe: Any = None) -> Dict[str, Any]:
    gm = _pct01(gross_margin)
    if gm is None:
        return {"value": 0.0, "reason": "毛利率缺值，不給毛利率溢價"}
    if not eps_positive:
        return {"value": 0.0, "reason": f"毛利率 {_fmt_pct(gm)}，但 EPS 不穩或為負，不給毛利率溢價"}
    if gm < 0.10:
        val = -8.0
    elif gm < 0.15:
        val = -4.0
    elif gm < 0.25:
        val = 0.0
    elif gm < 0.35:
        val = 4.0
    elif gm < 0.45:
        val = 8.0
    elif gm < 0.55:
        val = 12.0
    else:
        val = 15.0
    rev = _pct01(revenue_yoy)
    r = f"毛利率 {_fmt_pct(gm)}"
    if rev is not None and rev < 0 and val > 0:
        val *= 0.5
        r += "；營收 YoY 為負，毛利率加分減半"
    roev = _pct01(roe)
    if roev is not None and roev < 0.08 and val > 0:
        val *= 0.6
        r += "；ROE 偏低，高毛利加分打折"
    return {"value": round(val, 2), "reason": r}


def roe_quality_premium(roe: Any, debt_to_equity: Any = None, warning_count: int = 0) -> Dict[str, Any]:
    r = _pct01(roe)
    if r is None:
        return {"value": 0.0, "reason": "ROE 缺值，不給財務品質溢價"}
    if r < 0:
        val = -8.0
    elif r < 0.08:
        val = -4.0
    elif r < 0.15:
        val = 0.0
    elif r < 0.25:
        val = 4.0
    elif r < 0.35:
        val = 7.0
    else:
        val = 10.0
    de = _sf(debt_to_equity)
    reason = f"ROE {_fmt_pct(r)}"
    if de is not None and de > 2 and val > 0:
        val *= 0.5
        reason += f"；D/E {de:.2f} 偏高，ROE 加分減半"
    if warning_count > 0 and val > 3:
        val = min(val, 3.0)
        reason += "；資料分歧存在，ROE 加分上限 3x"
    return {"value": round(val, 2), "reason": reason}


def growth_premium_hierarchical(
    *,
    system_forward_eps: Any = None,
    ai_forward_eps: Any = None,
    consensus_forward_eps: Any = None,
    ttm_eps: Any = None,
    ai_ttm_eps: Any = None,
    revenue_yoy: Any = None,
    revenue_yoy_3m: Any = None,
) -> Dict[str, Any]:
    """成長溢價只採一個最高優先資料源，避免重複加分。"""
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
        return {"value": 0.0, "reason": "缺少 Forward EPS 或營收 YoY，成長溢價 0x", "source": "none", "growth": None}

    if growth < -0.20:
        val = -8.0
    elif growth < 0:
        val = -4.0
    elif growth < 0.10:
        val = 0.0
    elif growth < 0.20:
        val = 4.0
    elif growth < 0.35:
        val = 8.0
    elif growth < 0.60:
        val = 12.0
    else:
        val = 15.0
    return {"value": float(val), "reason": f"採用{src}：{_fmt_pct(growth)}；低優先級成長項不重複加分", "source": src, "growth": growth}


def theme_order_premium(themes: List[str], industry_profile: Dict[str, Any], eps_positive: bool = True, data_warning_count: int = 0) -> Dict[str, Any]:
    if not industry_profile.get("theme_premium_allowed", False):
        return {"value": 0.0, "reason": "此產業模型不建議額外給題材高倍率"}
    text = " ".join(str(x) for x in (themes or [])).lower()
    rules = [
        (12.0, ["ai asic", "asic", "hpc", "cowos", "cpo", "矽光子"]),
        (10.0, ["ai載板", "abf", "水冷", "液冷", "資料中心"]),
        (8.0, ["ai", "低軌", "衛星", "電網", "重電", "儲能"]),
        (6.0, ["車用", "高速傳輸", "機器人", "自動化"]),
    ]
    val = 0.0
    hit = []
    for score, keys in rules:
        matched = [k for k in keys if k.lower() in text]
        if matched:
            val = max(val, score)
            hit.extend(matched)
    if val <= 0:
        return {"value": 0.0, "reason": "未偵測到可量化題材溢價，題材僅列為備註"}
    reason = f"題材標籤命中：{'、'.join(sorted(set(hit)))}"
    if not eps_positive:
        val *= 0.5
        reason += "；EPS 未落地，題材溢價減半"
    if data_warning_count >= 2:
        val *= 0.5
        reason += "；資料分歧較多，題材溢價減半"
    return {"value": round(val, 2), "reason": reason}


def market_cap_adjustment(market_cap: Any, eps_positive: bool = True, liquidity_ok: bool = True) -> Dict[str, Any]:
    mc = _sf(market_cap)
    if mc is None or mc <= 0:
        return {"value": 0.0, "reason": "市值缺值，不做股本 / 市值修正"}
    # yfinance marketCap usually in TWD for .TW tickers.
    billion = mc / 100_000_000
    if billion >= 10_000:
        val, msg = 3.0, "大型龍頭，估值穩定度較高"
    elif billion >= 3_000:
        val, msg = 2.0, "大型權值股，估值穩定度正常"
    elif billion >= 500:
        val, msg = 3.0, "中型成長股，可給小幅成長溢價"
    elif billion >= 100 and eps_positive and liquidity_ok:
        val, msg = 4.0, "小型高成長且流動性尚可，小幅加分但需注意波動"
    else:
        val, msg = 0.0, "市值小或條件不足，不給小股本夢想溢價"
    return {"value": val, "reason": f"市值約 {billion:,.0f} 億；{msg}"}


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
        return {"factor": 1.00, "label": "未套用", "reason": "可操作區間尚未建立，暫不套估值位置折扣"}
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


def pe_floor_ceiling(industry_profile: Dict[str, Any], themes: List[str]) -> Dict[str, Any]:
    rng = industry_profile.get("pe_range")
    if isinstance(rng, (tuple, list)) and len(rng) == 2 and _sf(rng[0]) and _sf(rng[1]):
        floor, ceiling = float(rng[0]), float(rng[1])
    else:
        floor, ceiling = 12.0, 50.0
    key = str(industry_profile.get("model_key") or "")
    text = " ".join(str(x) for x in (themes or [])).lower()
    if any(k in key for k in ["IC_DESIGN", "IP_EDA"]):
        floor, ceiling = max(floor, 25.0), min(max(ceiling, 75.0), 85.0)
    elif any(k in text for k in ["ai", "hpc", "asic", "cowos", "abf", "矽光子", "水冷", "液冷"]):
        floor, ceiling = max(floor, 20.0), min(max(ceiling, 65.0), 75.0)
    return {"floor": floor, "ceiling": ceiling}


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
    warnings = []
    themes = list(p.get("themes") or [])
    primary_valuation = str(p.get("primary_valuation") or "forward_pe")
    pe_app = p.get("pe_applicable", True)

    if pe_app is False or primary_valuation in {"event_chip", "theme_event"}:
        pack = build_event_theme_pack(p)
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p})
        return pack
    if primary_valuation.startswith("pb_cycle") or primary_valuation in {"pb", "pb_roe"}:
        pack = build_pb_cycle_pack(current_price, pb_ratio, p)
        pack.update({"stock_id": stock_id, "stock_name": stock_name, "industry_profile": p})
        return pack

    base = _sf(p.get("base_pe"), 30.0) or 30.0
    rows: List[Dict[str, Any]] = []
    rows.append({"類型": "基準", "項目": "產業基準倍率", "倍率/係數": f"{base:.1f}x", "說明": f"{p.get('model_label', p.get('display_name', '一般產業'))} 的 base_pe"})

    eps_positive = any((_sf(x) or 0) > 0 for x in [consensus_forward_eps, system_forward_eps, ai_forward_eps, ttm_eps, ai_ttm_eps])
    warn_count = len(divergence_warnings or []) + len(dq_warnings or [])

    g = growth_premium_hierarchical(
        system_forward_eps=system_forward_eps,
        ai_forward_eps=ai_forward_eps,
        consensus_forward_eps=consensus_forward_eps,
        ttm_eps=ttm_eps,
        ai_ttm_eps=ai_ttm_eps,
        revenue_yoy=revenue_yoy,
    )
    gm = gross_margin_premium(gross_margin, revenue_yoy, eps_positive=eps_positive, roe=roe)
    rq = roe_quality_premium(roe, debt_to_equity, warning_count=warn_count)
    th = theme_order_premium(themes, p, eps_positive=eps_positive, data_warning_count=warn_count)
    liq = liquidity_factor(hist_data, info)
    mc = market_cap_adjustment(info.get("marketCap"), eps_positive=eps_positive, liquidity_ok=(liq.get("factor", 1) >= 0.85))

    for name, pack in [("成長溢價", g), ("毛利率溢價", gm), ("ROE / 財務品質溢價", rq), ("AI / 題材 / 訂單溢價", th), ("股本 / 市值修正", mc)]:
        _add_factor(rows, name, float(pack.get("value", 0) or 0), pack.get("reason", ""))

    raw_cap = base + float(g.get("value", 0) or 0) + float(gm.get("value", 0) or 0) + float(rq.get("value", 0) or 0) + float(th.get("value", 0) or 0) + float(mc.get("value", 0) or 0)
    rows.append({"類型": "小計", "項目": "原始建議倍率", "倍率/係數": f"{raw_cap:.1f}x", "說明": "產業基準 + 成長 + 毛利 + ROE + 題材 + 市值修正"})

    dc = data_confidence_factor(divergence_warnings, dq_warnings)
    vr = valuation_risk_factor(current_price, operable_low, operable_high)
    _add_discount(rows, "資料可信度折扣", dc["factor"], f"{dc['label']}；{dc['reason']}")
    _add_discount(rows, "估值風險折扣", vr["factor"], f"{vr['label']}；{vr['reason']}")
    _add_discount(rows, "流動性折扣", liq["factor"], f"{liq['label']}；{liq['reason']}")

    fc = pe_floor_ceiling(p, themes)
    final_cap = raw_cap * dc["factor"] * vr["factor"] * liq["factor"]
    final_cap = min(max(final_cap, fc["floor"]), fc["ceiling"])
    rows.append({"類型": "結果", "項目": "最終建議倍率", "倍率/係數": f"{final_cap:.1f}x", "說明": f"已套用樓地板 {fc['floor']:.0f}x 與天花板 {fc['ceiling']:.0f}x"})

    if p.get("pe_trap_warning"):
        warnings.append("本產業存在 P/E 陷阱，低 P/E 不一定代表低估")
    if warn_count >= 3:
        warnings.append("資料分歧或校驗提醒較多，Dynamic Cap 已折扣")
    if liq.get("factor", 1) < 0.9:
        warnings.append("流動性偏低，已套用流動性折扣")

    return {
        "available": True,
        "valuation_mode": primary_valuation,
        "base_multiple": base,
        "growth_premium": g,
        "gross_margin_premium": gm,
        "roe_quality_premium": rq,
        "theme_premium": th,
        "market_cap_adjustment": mc,
        "data_confidence_factor": dc,
        "valuation_risk_factor": vr,
        "liquidity_factor": liq,
        "raw_cap": raw_cap,
        "final_cap": final_cap,
        "floor_cap": fc["floor"],
        "ceiling_cap": fc["ceiling"],
        "warnings": warnings,
        "industry_profile": p,
        "report": pd.DataFrame(rows),
        "explanation": "Dynamic Cap 2.0：先加總基本溢價，再乘上資料、估值與流動性折扣。",
    }
