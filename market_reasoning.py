"""
V3 市場推理引擎。

第一階段使用既有國際連動資料，不新增外部 API：
- SOX
- TSM ADR
- NASDAQ futures
- EWT

第二階段加入特徵與規則引擎：
- 法人現貨買賣超特徵
- 信用交易風險特徵
- 空單分類框架（有期貨資料才輸出機率）

第三階段加入推理輸出層：
- Bull/Base/Bear 三情境
- 可追溯證據紀錄
- 可供未來 REST API 直接回傳的穩定 payload

第四階段加入 Dashboard 輔助：
- 市場推理快照摘要
- Session 內歷史紀錄
- 歷史分數表格

第五階段加入 AI Gateway：
- 固定 JSON prompt input
- AI 回覆 Schema 驗證
- 失敗時降級規則引擎摘要

第六階段加入回測與權重優化框架：
- 方向命中率與策略報酬
- 權重候選組合比較
- 樣本不足時明確降級

第七階段加入自動報告與告警：
- 盤前/盤後結構化報告
- 資料品質、風險、空單、信用交易分級告警
- 可複製 Markdown 報告文字

輸出為穩定 dict，供 Streamlit 面板與後續提示詞打包使用。
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd


MARKET_REASONING_VERSION = "V3-MR-Phase7c-20260715"

SHORT_POSITION_CLASSES = (
    "hedge",
    "directional_bear",
    "arbitrage",
    "covering",
)

MARKET_COMPONENTS = (
    {
        "key": "sox",
        "price_key": "sox_p",
        "label": "費城半導體 SOX",
        "weight": 0.35,
        "role": "半導體景氣與 AI 硬體風險偏好",
    },
    {
        "key": "tsm",
        "price_key": "tsm_p",
        "label": "台積電 ADR",
        "weight": 0.30,
        "role": "台股權值與先進製程定價參考",
    },
    {
        "key": "ewt",
        "price_key": "ewt_p",
        "label": "EWT 台股 ETF",
        "weight": 0.20,
        "role": "海外資金對台股整體風險偏好",
    },
    {
        "key": "nq",
        "price_key": "nq_p",
        "label": "NASDAQ futures",
        "weight": 0.15,
        "role": "美股科技股短線風險偏好",
    },
)


def _to_float(value):
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    return num


def _clamp(value, low, high):
    return max(low, min(high, value))


def _pct_to_component_score(change_pct):
    """Map daily percent change to a -100..100 component score."""
    if change_pct is None:
        return None
    return _clamp(change_pct / 3.0 * 100.0, -100.0, 100.0)


def _fmt_pct(value):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def _first_present(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _streak_from_series(series):
    values = []
    try:
        values = list(series.dropna())
    except Exception:
        values = list(series or [])
    streak = 0
    for value in reversed(values):
        num = _to_float(value)
        if num is None or abs(num) < 1e-9:
            break
        sign = 1 if num > 0 else -1
        if streak == 0:
            streak = sign
        elif streak * sign > 0:
            streak += sign
        else:
            break
    return streak


def _lots_to_score(value, scale=3000.0):
    num = _to_float(value)
    if num is None:
        return None
    return _clamp(num / scale * 100.0, -100.0, 100.0)


def _softmax(scores):
    max_score = max(scores.values()) if scores else 0.0
    exp_scores = {key: math.exp(value - max_score) for key, value in scores.items()}
    total = sum(exp_scores.values())
    if total <= 0:
        return {key: 0.0 for key in scores}
    return {key: value / total for key, value in exp_scores.items()}


def build_institutional_flow_feature(institutional_flow=None):
    """Normalize stock-level institutional flow into phase-2 rule features."""
    if institutional_flow is None:
        return {
            "available": False,
            "group": "institutional_flow",
            "message": "未提供法人現貨資料",
            "evidence": [],
            "counter_evidence": [],
        }

    f_10d = t_10d = d_10d = None
    f_streak = t_streak = None
    source = "ui_chip_panel"

    if isinstance(institutional_flow, pd.DataFrame):
        if institutional_flow.empty:
            return {
                "available": False,
                "group": "institutional_flow",
                "message": "法人現貨資料為空",
                "evidence": [],
                "counter_evidence": [],
            }
        source = "FinMind TaiwanStockInstitutionalInvestorsBuySell"
        if "Foreign" in institutional_flow.columns:
            f_10d = _to_float(institutional_flow["Foreign"].tail(10).sum())
            f_streak = _streak_from_series(institutional_flow["Foreign"])
        if "Trust" in institutional_flow.columns:
            t_10d = _to_float(institutional_flow["Trust"].tail(10).sum())
            t_streak = _streak_from_series(institutional_flow["Trust"])
        if "Dealer" in institutional_flow.columns:
            d_10d = _to_float(institutional_flow["Dealer"].tail(10).sum())
    elif isinstance(institutional_flow, dict):
        f_10d = _to_float(_first_present(institutional_flow.get("f_10d"), institutional_flow.get("foreign_10d")))
        t_10d = _to_float(_first_present(institutional_flow.get("t_10d"), institutional_flow.get("trust_10d")))
        d_10d = _to_float(_first_present(institutional_flow.get("d_10d"), institutional_flow.get("dealer_10d")))
        f_streak = _to_float(institutional_flow.get("f_streak"))
        t_streak = _to_float(institutional_flow.get("t_streak"))
    else:
        return {
            "available": False,
            "group": "institutional_flow",
            "message": "法人現貨資料格式不支援",
            "evidence": [],
            "counter_evidence": [],
        }

    if f_10d is None and t_10d is None and d_10d is None:
        return {
            "available": False,
            "group": "institutional_flow",
            "message": "法人現貨資料缺少外資/投信/自營商買賣超",
            "evidence": [],
            "counter_evidence": [],
        }

    f_10d = f_10d or 0.0
    t_10d = t_10d or 0.0
    d_10d = d_10d or 0.0
    combined_10d = f_10d + t_10d + d_10d
    direction_raw = f_10d * 0.55 + t_10d * 0.35 + d_10d * 0.10
    direction_score = _lots_to_score(direction_raw)

    divergence_risk = 0.0
    if abs(f_10d) >= 500 and abs(t_10d) >= 500 and f_10d * t_10d < 0:
        divergence_risk = 25.0
    selling_pressure = _clamp(abs(min(combined_10d, 0.0)) / 3000.0 * 45.0, 0.0, 45.0)
    crowding_pressure = _clamp(max(combined_10d - 5000.0, 0.0) / 5000.0 * 20.0, 0.0, 20.0)
    risk_score = _clamp(30.0 + selling_pressure + divergence_risk + crowding_pressure, 0.0, 100.0)

    evidence = []
    counter_evidence = []
    if combined_10d > 300:
        evidence.append(f"法人近10日合計買超 {combined_10d:,.0f} 張")
    elif combined_10d < -300:
        counter_evidence.append(f"法人近10日合計賣超 {abs(combined_10d):,.0f} 張")
    if f_10d > 300:
        evidence.append(f"外資近10日買超 {f_10d:,.0f} 張")
    elif f_10d < -300:
        counter_evidence.append(f"外資近10日賣超 {abs(f_10d):,.0f} 張")
    if t_10d > 300:
        evidence.append(f"投信近10日買超 {t_10d:,.0f} 張")
    elif t_10d < -300:
        counter_evidence.append(f"投信近10日賣超 {abs(t_10d):,.0f} 張")
    if divergence_risk:
        counter_evidence.append("外資與投信方向相反，籌碼一致性下降")

    return {
        "available": True,
        "group": "institutional_flow",
        "source": source,
        "f_10d": f_10d,
        "t_10d": t_10d,
        "d_10d": d_10d,
        "combined_10d": combined_10d,
        "f_streak": f_streak,
        "t_streak": t_streak,
        "direction_score": direction_score,
        "risk_score": risk_score,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
    }


def build_margin_credit_feature(margin_credit=None):
    """Normalize margin/short-sale summary into phase-2 rule features."""
    if not isinstance(margin_credit, dict) or not margin_credit.get("available"):
        return {
            "available": False,
            "group": "margin_credit",
            "message": "未提供可用信用交易資料",
            "evidence": [],
            "counter_evidence": [],
        }

    label = str(margin_credit.get("risk_label") or "資料不足")
    label_score = {
        "低": 20.0,
        "正常": 40.0,
        "偏熱": 65.0,
        "過熱": 85.0,
        "資料不足": None,
    }.get(label)
    raw_risk = _to_float(margin_credit.get("risk_score"))
    risk_score = label_score if label_score is not None else (None if raw_risk is None else _clamp(raw_risk * 15.0, 0.0, 100.0))
    margin_change_5d_pct = _to_float(margin_credit.get("margin_change_5d_pct"))
    margin_usage_ratio = _to_float(margin_credit.get("margin_usage_ratio"))
    margin_to_shares_ratio = _to_float(margin_credit.get("margin_to_shares_ratio"))

    direction_score = 0.0
    if risk_score is not None and risk_score >= 60 and (margin_change_5d_pct is None or margin_change_5d_pct > 0):
        direction_score = -_clamp((risk_score - 50.0) * 1.2, 0.0, 45.0)
    elif risk_score is not None and risk_score <= 25:
        direction_score = 8.0

    evidence = []
    counter_evidence = []
    if risk_score is not None and risk_score <= 30:
        evidence.append("信用交易槓桿壓力低")
    if risk_score is not None and risk_score >= 60:
        counter_evidence.append(f"信用交易風險 {label}")
    if margin_usage_ratio is not None:
        target = counter_evidence if margin_usage_ratio >= 0.60 else evidence
        target.append(f"融資使用率 {margin_usage_ratio:.2%}")
    if margin_to_shares_ratio is not None and margin_to_shares_ratio >= 0.05:
        counter_evidence.append(f"融資占股本 {margin_to_shares_ratio:.2%}")
    if margin_change_5d_pct is not None and margin_change_5d_pct >= 0.15:
        counter_evidence.append(f"5日融資增幅 {margin_change_5d_pct:.2%}")

    return {
        "available": True,
        "group": "margin_credit",
        "source": margin_credit.get("source", "FinMind TaiwanStockMarginPurchaseShortSale"),
        "risk_label": label,
        "risk_score": risk_score,
        "direction_score": direction_score,
        "margin_usage_ratio": margin_usage_ratio,
        "margin_to_shares_ratio": margin_to_shares_ratio,
        "margin_change_5d_pct": margin_change_5d_pct,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
    }


def classify_short_position(
    institutional_flow=None,
    futures_snapshot=None,
    margin_credit=None,
    price_change_pct=None,
    fx_change_pct=None,
):
    """
    Classify foreign futures short-position nature.

    Without futures data, the function intentionally returns unavailable.
    """
    if not futures_snapshot or (isinstance(futures_snapshot, dict) and futures_snapshot.get("available") is False):
        missing_message = "缺少外資台指期淨部位或空單變化，暫不分類空單性質。"
        if isinstance(futures_snapshot, dict):
            missing_message = futures_snapshot.get("message") or missing_message
        return {
            "available": False,
            "message": missing_message,
            "probabilities": {key: None for key in SHORT_POSITION_CLASSES},
            "top_class": None,
            "top_label": "資料不足",
            "evidence": [],
        }

    institutional_flow = institutional_flow or {}
    margin_credit = margin_credit or {}

    cash_net = _to_float(_first_present(
        institutional_flow.get("cash_net"),
        institutional_flow.get("combined_10d"),
        institutional_flow.get("foreign_cash_net"),
    )) or 0.0
    futures_net_change = _to_float(_first_present(
        futures_snapshot.get("foreign_futures_net_change"),
        futures_snapshot.get("futures_net_change"),
        futures_snapshot.get("net_change"),
    )) or 0.0
    futures_short_change = _to_float(_first_present(
        futures_snapshot.get("foreign_futures_short_change"),
        futures_snapshot.get("futures_short_change"),
        futures_snapshot.get("short_change"),
    ))
    if futures_short_change is None:
        futures_short_change = -futures_net_change

    price_change_pct = _to_float(_first_present(
        price_change_pct,
        futures_snapshot.get("price_change_pct"),
        futures_snapshot.get("taiex_change_pct"),
    )) or 0.0
    futures_net_oi = _to_float(_first_present(
        futures_snapshot.get("foreign_futures_net_oi_lots"),
        futures_snapshot.get("futures_net_oi"),
        futures_snapshot.get("net_oi"),
    ))
    futures_short_oi = _to_float(_first_present(
        futures_snapshot.get("foreign_futures_short_oi_lots"),
        futures_snapshot.get("futures_short_oi"),
        futures_snapshot.get("short_oi"),
    ))
    futures_long_oi = _to_float(_first_present(
        futures_snapshot.get("foreign_futures_long_oi_lots"),
        futures_snapshot.get("futures_long_oi"),
        futures_snapshot.get("long_oi"),
    ))
    fx_change_pct = _to_float(_first_present(
        fx_change_pct,
        futures_snapshot.get("usd_twd_change_pct"),
        futures_snapshot.get("fx_change_pct"),
    )) or 0.0
    basis_abnormal = bool(futures_snapshot.get("basis_abnormal") or futures_snapshot.get("arbitrage_signal"))
    margin_risk = _to_float(margin_credit.get("risk_score")) or 0.0

    cash_score = _clamp(cash_net / 5000.0, -2.0, 2.0)
    short_score = _clamp(futures_short_change / 10000.0, -2.0, 2.0)
    price_score = _clamp(price_change_pct / 2.5, -2.0, 2.0)
    fx_stress = _clamp(fx_change_pct / 1.0, -2.0, 2.0)
    oi_short_pressure = 0.0
    if futures_net_oi is not None:
        oi_short_pressure = _clamp((-futures_net_oi) / 50000.0, -2.0, 2.0)

    position_bias = "unknown"
    position_label = "未平倉資料不足"
    if futures_net_oi is not None:
        if futures_net_oi <= -60000:
            position_bias = "heavy_short"
            position_label = "未平倉重度偏空"
        elif futures_net_oi <= -30000:
            position_bias = "short"
            position_label = "未平倉偏空"
        elif futures_net_oi >= 30000:
            position_bias = "long"
            position_label = "未平倉偏多"
        else:
            position_bias = "neutral"
            position_label = "未平倉中性"

    flow_bias = "neutral"
    flow_label = "當日交易中性"
    if futures_short_change >= 3000:
        flow_bias = "short_build"
        flow_label = "當日偏加空"
    elif futures_short_change > 0:
        flow_bias = "slight_short_build"
        flow_label = "當日略偏加空"
    elif futures_short_change <= -3000:
        flow_bias = "short_covering"
        flow_label = "當日明顯回補"
    elif futures_short_change < 0:
        flow_bias = "slight_short_covering"
        flow_label = "當日小幅回補"

    scores = {key: 0.0 for key in SHORT_POSITION_CLASSES}
    if short_score > 0:
        if cash_score > 0:
            scores["hedge"] += 1.20 + min(cash_score, 1.0) * 0.45 + max(-fx_stress, 0.0) * 0.20
            scores["arbitrage"] += 0.40
        if cash_score < 0:
            scores["directional_bear"] += 1.30 + min(abs(cash_score), 1.0) * 0.55 + max(fx_stress, 0.0) * 0.30
        if basis_abnormal:
            scores["arbitrage"] += 1.10
    if short_score < 0:
        scores["covering"] += 1.25 + max(price_score, 0.0) * 0.45
    if oi_short_pressure > 0.6:
        if cash_score > 0:
            scores["hedge"] += 0.85 + min(oi_short_pressure, 1.2) * 0.35
        elif cash_score < 0:
            scores["directional_bear"] += 0.45 + min(oi_short_pressure, 1.2) * 0.30
        else:
            scores["directional_bear"] += min(oi_short_pressure, 1.2) * 0.15
    if price_score < -0.4 and short_score > 0:
        scores["directional_bear"] += 0.35
    if margin_risk >= 65 and price_score < 0:
        scores["directional_bear"] += 0.20

    probabilities = _softmax(scores)
    top_class = max(probabilities, key=probabilities.get)
    labels = {
        "hedge": "避險 Hedge",
        "directional_bear": "方向性看空",
        "arbitrage": "套利 Arbitrage",
        "covering": "空單回補 Covering",
    }
    behavior_label = labels.get(top_class, top_class)
    if position_bias in {"heavy_short", "short"}:
        display_label = f"{position_label} / {flow_label}"
        if flow_bias in {"short_covering", "slight_short_covering"}:
            interpretation = (
                f"{position_label}，但當日交易流量偏回補；這只代表空方當日減壓，"
                "不代表既有空單已消失。"
            )
        elif flow_bias in {"short_build", "slight_short_build"}:
            interpretation = f"{position_label}，且當日交易仍偏加空，市場風險需提高。"
        else:
            interpretation = f"{position_label}，當日交易流量中性，仍需以未平倉存量控風險。"
    else:
        display_label = f"{position_label} / {flow_label}" if position_bias != "unknown" else behavior_label
        interpretation = f"{position_label}；{flow_label}。"
    evidence = [
        f"現貨/法人淨額 {cash_net:,.0f}",
        f"期貨空單變化 {futures_short_change:,.0f}",
        f"價格變動 {price_change_pct:+.2f}%",
    ]
    if futures_net_oi is not None:
        evidence.append(f"期貨未平倉淨額 {futures_net_oi:,.0f}")
    if futures_short_oi is not None or futures_long_oi is not None:
        evidence.append(f"期貨未平倉多/空 {futures_long_oi or 0:,.0f}/{futures_short_oi or 0:,.0f}")
    if basis_abnormal:
        evidence.append("期現價差/套利訊號異常")

    return {
        "available": True,
        "probabilities": probabilities,
        "top_class": top_class,
        "top_label": behavior_label,
        "behavior_label": behavior_label,
        "position_bias": position_bias,
        "position_label": position_label,
        "flow_bias": flow_bias,
        "flow_label": flow_label,
        "display_label": display_label,
        "interpretation": interpretation,
        "scores": scores,
        "evidence": evidence,
        "source": futures_snapshot.get("source"),
        "data_date": futures_snapshot.get("data_date"),
        "daily_bias": futures_snapshot.get("daily_bias"),
        "net_oi_bias": futures_snapshot.get("net_oi_bias"),
    }


def _short_position_direction_score(short_position):
    """Convert market-level futures short-position classification into a small direction score."""
    if not isinstance(short_position, dict) or not short_position.get("available"):
        return None
    probabilities = short_position.get("probabilities") or {}
    directional_bear = _to_float(probabilities.get("directional_bear")) or 0.0
    hedge = _to_float(probabilities.get("hedge")) or 0.0
    covering = _to_float(probabilities.get("covering")) or 0.0
    arbitrage = _to_float(probabilities.get("arbitrage")) or 0.0
    score = covering * 35.0 + hedge * 12.0 - directional_bear * 55.0 - arbitrage * 6.0
    position_bias = short_position.get("position_bias")
    if position_bias == "heavy_short":
        score -= 12.0
    elif position_bias == "short":
        score -= 6.0
    elif position_bias == "long":
        score += 4.0
    return _clamp(score, -45.0, 35.0)


def _short_position_risk_score(short_position):
    """Convert market-level futures short-position classification into a risk score."""
    if not isinstance(short_position, dict) or not short_position.get("available"):
        return None
    probabilities = short_position.get("probabilities") or {}
    directional_bear = _to_float(probabilities.get("directional_bear")) or 0.0
    hedge = _to_float(probabilities.get("hedge")) or 0.0
    covering = _to_float(probabilities.get("covering")) or 0.0
    arbitrage = _to_float(probabilities.get("arbitrage")) or 0.0
    risk = 42.0 + directional_bear * 34.0 + hedge * 8.0 + arbitrage * 12.0 - covering * 14.0
    position_bias = short_position.get("position_bias")
    if position_bias == "heavy_short":
        risk += 14.0
    elif position_bias == "short":
        risk += 8.0
    elif position_bias == "long":
        risk -= 4.0
    return _clamp(risk, 20.0, 85.0)


def build_phase2_rule_features(
    institutional_flow=None,
    margin_credit=None,
    futures_snapshot=None,
    price_change_pct=None,
    fx_change_pct=None,
):
    inst_feature = build_institutional_flow_feature(institutional_flow)
    margin_feature = build_margin_credit_feature(margin_credit)
    short_position = classify_short_position(
        institutional_flow=inst_feature if inst_feature.get("available") else None,
        futures_snapshot=futures_snapshot,
        margin_credit=margin_feature if margin_feature.get("available") else None,
        price_change_pct=price_change_pct,
        fx_change_pct=fx_change_pct,
    )
    return {
        "institutional_flow": inst_feature,
        "margin_credit": margin_feature,
        "short_position": short_position,
    }


def build_market_snapshot(
    trend_data=None,
    chip_state=None,
    institutional_flow=None,
    margin_credit=None,
    futures_snapshot=None,
    options_snapshot=None,
    fx_snapshot=None,
    metadata=None,
):
    """
    Normalize available market inputs into a versioned snapshot.

    chip_state is the existing return value from render_chip_panels().
    """
    trend_data = trend_data or {}
    metadata = metadata or {}
    if chip_state is not None:
        institutional_flow = institutional_flow if institutional_flow is not None else chip_state
        if isinstance(chip_state, dict):
            margin_credit = margin_credit if margin_credit is not None else chip_state.get("margin_credit")

    components = []
    for spec in MARKET_COMPONENTS:
        change_pct = _to_float(trend_data.get(spec["key"]))
        price = _to_float(trend_data.get(spec["price_key"]))
        score = _pct_to_component_score(change_pct)
        components.append({
            "key": spec["key"],
            "label": spec["label"],
            "role": spec["role"],
            "weight": float(spec["weight"]),
            "price": price,
            "change_pct": change_pct,
            "score": score,
            "available": change_pct is not None,
        })

    phase2_features = build_phase2_rule_features(
        institutional_flow=institutional_flow,
        margin_credit=margin_credit,
        futures_snapshot=futures_snapshot,
        price_change_pct=trend_data.get("ewt"),
        fx_change_pct=(fx_snapshot or {}).get("usd_twd_change_pct") if isinstance(fx_snapshot, dict) else None,
    )

    extension_groups = {
        "institutional_flow": institutional_flow,
        "margin_credit": margin_credit,
        "futures_snapshot": futures_snapshot,
        "options_snapshot": options_snapshot,
        "fx_snapshot": fx_snapshot,
    }

    extension_available = {
        "institutional_flow": phase2_features["institutional_flow"].get("available", False),
        "margin_credit": phase2_features["margin_credit"].get("available", False),
        "futures_snapshot": phase2_features["short_position"].get("available", False),
        "options_snapshot": bool(options_snapshot),
        "fx_snapshot": bool(fx_snapshot),
    }
    expected_extensions = []
    if chip_state is not None:
        expected_extensions.append("institutional_flow")
        expected_extensions.append("margin_credit")
    if chip_state is None and institutional_flow is not None:
        expected_extensions.append("institutional_flow")
    if chip_state is None and margin_credit is not None:
        expected_extensions.append("margin_credit")
    if futures_snapshot is not None:
        expected_extensions.append("futures_snapshot")
    if options_snapshot is not None:
        expected_extensions.append("options_snapshot")
    if fx_snapshot is not None:
        expected_extensions.append("fx_snapshot")
    expected_extensions = list(dict.fromkeys(expected_extensions))
    missing_extensions = [name for name, available in extension_available.items() if not available]
    available_extensions = [name for name, available in extension_available.items() if available]

    return {
        "version": MARKET_REASONING_VERSION,
        "built_at": metadata.get("built_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "get_global_market_trend",
        "phase2_expected": any(value is not None for value in (chip_state, institutional_flow, margin_credit, futures_snapshot, options_snapshot, fx_snapshot)),
        "expected_extensions": expected_extensions,
        "target_day": trend_data.get("target_day", "今日"),
        "time_status": trend_data.get("time_status", ""),
        "legacy_trend_text": trend_data.get("trend", ""),
        "legacy_trend_color": trend_data.get("color", ""),
        "components": components,
        "phase2_features": phase2_features,
        "extensions": extension_groups,
        "missing_extensions": missing_extensions,
        "available_extensions": available_extensions,
    }


def _calculate_global_direction_score(components):
    weighted_sum = 0.0
    total_weight = 0.0
    for component in components:
        score = component.get("score")
        if score is None:
            continue
        weighted_sum += score * float(component.get("weight", 0.0) or 0.0)
        total_weight += float(component.get("weight", 0.0) or 0.0)
    if total_weight <= 0:
        return None
    return _clamp(weighted_sum / total_weight, -100.0, 100.0)


def _calculate_direction_score(components, phase2_features=None):
    global_score = _calculate_global_direction_score(components)
    phase2_features = phase2_features or {}
    inst_score = (phase2_features.get("institutional_flow") or {}).get("direction_score")
    margin_score = (phase2_features.get("margin_credit") or {}).get("direction_score")
    short_score = _short_position_direction_score(phase2_features.get("short_position"))

    weighted = []
    if global_score is not None:
        weighted.append((global_score, 0.65))
    if inst_score is not None:
        weighted.append((inst_score, 0.25))
    if margin_score is not None:
        weighted.append((margin_score, 0.10))
    if short_score is not None:
        weighted.append((short_score, 0.12))
    if not weighted:
        return None
    total_weight = sum(weight for _, weight in weighted)
    return _clamp(sum(score * weight for score, weight in weighted) / total_weight, -100.0, 100.0)


def _calculate_global_risk_score(components, direction_score):
    values = [c["change_pct"] for c in components if c.get("change_pct") is not None]
    if not values:
        return None

    downside = [abs(min(v, 0.0)) / 3.0 * 100.0 for v in values]
    downside_score = sum(downside) / len(downside)
    dispersion = max(values) - min(values) if len(values) >= 2 else 0.0
    dispersion_score = _clamp(dispersion / 4.0 * 100.0, 0.0, 100.0)
    direction_relief = max(direction_score or 0.0, 0.0) * 0.10

    risk = 35.0 + downside_score * 0.45 + dispersion_score * 0.25 - direction_relief
    return _clamp(risk, 0.0, 100.0)


def _calculate_risk_score(components, direction_score, phase2_features=None):
    global_risk = _calculate_global_risk_score(components, direction_score)
    phase2_features = phase2_features or {}
    inst_risk = (phase2_features.get("institutional_flow") or {}).get("risk_score")
    margin_risk = (phase2_features.get("margin_credit") or {}).get("risk_score")
    short_risk = _short_position_risk_score(phase2_features.get("short_position"))

    weighted = []
    if global_risk is not None:
        weighted.append((global_risk, 0.55))
    if inst_risk is not None:
        weighted.append((inst_risk, 0.15))
    if margin_risk is not None:
        weighted.append((margin_risk, 0.30))
    if short_risk is not None:
        weighted.append((short_risk, 0.15))
    if not weighted:
        return None
    total_weight = sum(weight for _, weight in weighted)
    return _clamp(sum(score * weight for score, weight in weighted) / total_weight, 0.0, 100.0)


def _calculate_confidence_score(components, phase2_features=None, phase2_expected=False, expected_features=None):
    available = [c for c in components if c.get("available")]
    global_ratio = len(available) / len(components) if components else 0.0
    phase2_features = phase2_features or {}
    feature_key_map = {"futures_snapshot": "short_position"}
    if expected_features is not None:
        phase2_required = [feature_key_map.get(name, name) for name in expected_features]
    else:
        phase2_required = ["institutional_flow", "margin_credit"] if phase2_expected else []
    phase2_available = [
        name for name in phase2_required
        if (phase2_features.get(name) or {}).get("available")
    ]
    if phase2_required:
        completeness_score = (global_ratio * 0.60 + len(phase2_available) / len(phase2_required) * 0.40) * 100.0
    else:
        completeness_score = global_ratio * 100.0

    signs = []
    for component in available:
        value = component.get("change_pct")
        if value is None or abs(value) < 0.05:
            continue
        signs.append(1 if value > 0 else -1)
    inst_score = (phase2_features.get("institutional_flow") or {}).get("direction_score")
    if inst_score is not None and abs(inst_score) >= 5:
        signs.append(1 if inst_score > 0 else -1)
    margin_score = (phase2_features.get("margin_credit") or {}).get("direction_score")
    if margin_score is not None and abs(margin_score) >= 5:
        signs.append(1 if margin_score > 0 else -1)
    short_score = _short_position_direction_score(phase2_features.get("short_position"))
    if short_score is not None and abs(short_score) >= 5:
        signs.append(1 if short_score > 0 else -1)

    if not signs:
        agreement_score = 45.0 if available else 0.0
    else:
        positive = signs.count(1)
        negative = signs.count(-1)
        agreement_score = max(positive, negative) / len(signs) * 100.0

    return _clamp(completeness_score * 0.60 + agreement_score * 0.40, 0.0, 100.0)


def _judge_regime(direction_score, risk_score, confidence_score, phase2_features=None):
    if direction_score is None or risk_score is None or confidence_score < 35:
        return "DATA_INSUFFICIENT", "資料不足"
    phase2_features = phase2_features or {}
    inst = phase2_features.get("institutional_flow") or {}
    margin = phase2_features.get("margin_credit") or {}
    short_position = phase2_features.get("short_position") or {}
    if short_position.get("available") and short_position.get("top_class") == "hedge" and direction_score >= 10 and risk_score >= 50:
        return "HEDGED_BULL", "避險型多頭"
    if direction_score >= 20 and (margin.get("risk_score") or 0) >= 70:
        return "LEVERAGE_RISK_ON", "多頭但槓桿偏熱"
    if direction_score >= 20 and (inst.get("direction_score") or 0) >= 35 and risk_score < 65:
        return "CHIP_ACCUMULATION", "法人偏多承接"
    if direction_score >= 35 and risk_score < 55:
        return "RISK_ON", "風險偏好多頭"
    if direction_score <= -35 and risk_score >= 55:
        return "RISK_OFF", "風險偏好轉弱"
    if direction_score >= 20:
        return "GLOBAL_TECH_TAILWIND", "科技股順風"
    if direction_score <= -20:
        return "GLOBAL_RISK_ALERT", "全球風險警戒"
    return "RANGE_NEUTRAL", "區間震盪"


def _build_evidence(components, phase2_features=None):
    evidence = []
    counter_evidence = []
    for component in components:
        change_pct = component.get("change_pct")
        if change_pct is None:
            continue
        text = f"{component['label']} {_fmt_pct(change_pct)}"
        if change_pct >= 0.05:
            evidence.append(text)
        elif change_pct <= -0.05:
            counter_evidence.append(text)
    phase2_features = phase2_features or {}
    for feature in phase2_features.values():
        if not isinstance(feature, dict) or not feature.get("available"):
            continue
        evidence.extend(feature.get("evidence") or [])
        counter_evidence.extend(feature.get("counter_evidence") or [])
    return evidence, counter_evidence


def _build_data_quality(components, snapshot):
    missing_fields = [c["label"] for c in components if not c.get("available")]
    available_count = len(components) - len(missing_fields)
    phase2_features = snapshot.get("phase2_features", {})
    phase2_expected = bool(snapshot.get("phase2_expected"))
    expected_extensions = list(snapshot.get("expected_extensions") or [])
    available_groups = ["international_linkage"] if available_count else []
    required_groups = ["international_linkage"]

    if phase2_expected:
        feature_key_map = {"futures_snapshot": "short_position"}
        required_groups.extend(expected_extensions)
        for extension_name in expected_extensions:
            feature_name = feature_key_map.get(extension_name, extension_name)
            feature = phase2_features.get(feature_name) or {}
            if feature.get("available"):
                available_groups.append(extension_name)
            else:
                missing_fields.append(extension_name)

    if set(required_groups).issubset(set(available_groups)):
        status = "OK"
    elif available_count >= 2 or len(available_groups) >= 1:
        status = "PARTIAL"
    else:
        status = "INSUFFICIENT"

    return {
        "status": status,
        "available_count": available_count,
        "required_count": len(components),
        "missing_fields": missing_fields,
        "available_groups": available_groups,
        "required_groups": required_groups,
        "missing_extension_groups": snapshot.get("missing_extensions", []),
        "note": "市場推理以國際連動為主，已接入資料才納入法人、信用交易、台指期外資空單、選擇權或匯率；未接入資料只標示缺值。",
    }


def _scenario_probabilities(direction_score, risk_score, confidence_score, available=True):
    if not available or direction_score is None or risk_score is None:
        return {"bull": 0.20, "base": 0.60, "bear": 0.20}
    confidence_score = confidence_score or 0.0
    scores = {
        "bull": direction_score / 35.0 - max(risk_score - 55.0, 0.0) / 35.0 + confidence_score / 120.0,
        "base": 1.00 - abs(direction_score) / 45.0 - abs(risk_score - 50.0) / 70.0 + confidence_score / 150.0,
        "bear": -direction_score / 35.0 + max(risk_score - 50.0, 0.0) / 35.0 + (100.0 - confidence_score) / 160.0,
    }
    return _softmax(scores)


def build_market_scenarios(reasoning_pack):
    """Build Bull/Base/Bear scenarios with explicit triggers and invalidations."""
    direction_score = reasoning_pack.get("direction_score")
    risk_score = reasoning_pack.get("risk_score")
    confidence_score = reasoning_pack.get("confidence_score")
    available = bool(reasoning_pack.get("available"))
    probabilities = _scenario_probabilities(direction_score, risk_score, confidence_score, available)
    features = reasoning_pack.get("phase2_features", {})
    inst = features.get("institutional_flow") or {}
    margin = features.get("margin_credit") or {}
    short_position = reasoning_pack.get("short_position") or {}
    data_quality = reasoning_pack.get("data_quality", {})

    if not available:
        bull_triggers = ["補齊國際連動、法人與信用交易資料後再判斷多方情境"]
        base_triggers = ["資料不足，維持中性觀察"]
        bear_triggers = ["若資料缺口同時伴隨價格轉弱，先提高風險控管"]
    else:
        bull_triggers = [
            "市場方向分數站上 +35 且風險分數低於 55",
            "SOX / TSM ADR 維持正報酬",
        ]
        base_triggers = [
            "市場方向分數維持在 -20 至 +20 區間",
            "國際連動、法人或信用交易訊號互相抵銷",
        ]
        bear_triggers = [
            "市場方向分數跌破 -35 或風險分數升高至 70 以上",
            "SOX / TSM ADR 同步轉弱",
        ]

        if inst.get("available"):
            if (inst.get("direction_score") or 0) > 0:
                bull_triggers.append("法人近10日買超延續")
                base_triggers.append("法人買超縮小或外資/投信轉為分歧")
            else:
                bull_triggers.append("法人賣超停止並轉為買超")
                bear_triggers.append("外資與投信賣超延續")
        else:
            base_triggers.append("法人現貨資料未補齊，降低方向信心")

        if margin.get("available"):
            if (margin.get("risk_score") or 0) >= 60:
                bull_triggers.append("融資使用率與5日融資增幅停止升溫")
                bear_triggers.append("融資偏熱且價格轉弱，槓桿賣壓風險升高")
            else:
                bull_triggers.append("信用交易維持正常或低風險")
        else:
            base_triggers.append("信用交易資料未補齊，維持基準情境")

        if short_position.get("available"):
            if short_position.get("top_class") == "hedge":
                bull_triggers.append("期貨空單維持避險性質，而非方向性放空")
            elif short_position.get("top_class") == "directional_bear":
                bear_triggers.append("空單分類偏方向性看空")
            elif short_position.get("top_class") == "covering":
                bull_triggers.append("空單回補帶動短線動能")
        else:
            base_triggers.append("台指期空單資料未接入，不強行判斷空單性質")

    if data_quality.get("status") != "OK":
        base_triggers.append("資料品質未達 OK，信心分數需降權")

    bull_summary = "多方情境成立時，市場風險偏好改善，個股估值可提高解讀彈性。"
    base_summary = "基準情境下，訊號仍需等待法人、信用交易或國際市場確認。"
    bear_summary = "空方情境成立時，優先降低曝險並避免用遠期樂觀估值追價。"
    if direction_score is not None and direction_score >= 35 and risk_score is not None and risk_score < 55:
        bull_summary = "目前多方條件較完整，但仍需追蹤信用交易是否升溫。"
    if risk_score is not None and risk_score >= 65:
        bear_summary = "風險分數偏高，若價格轉弱，空方情境會快速取得主導。"

    return {
        "bull": {
            "label": "多方情境",
            "probability": probabilities["bull"],
            "summary": bull_summary,
            "trigger_conditions": bull_triggers,
            "invalidations": ["方向分數跌回 0 以下", "風險分數升破 70", "法人轉為連續賣超"],
            "action_bias": "提高觀察名單優先度，但仍需個股估值與資料品質配合。",
        },
        "base": {
            "label": "基準情境",
            "probability": probabilities["base"],
            "summary": base_summary,
            "trigger_conditions": base_triggers,
            "invalidations": ["方向分數明確突破 +35 或跌破 -35", "資料品質升至 OK 且訊號一致"],
            "action_bias": "維持分批與等待確認，避免單一訊號決策。",
        },
        "bear": {
            "label": "空方情境",
            "probability": probabilities["bear"],
            "summary": bear_summary,
            "trigger_conditions": bear_triggers,
            "invalidations": ["風險分數回落至 45 以下", "SOX/TSM ADR 與法人同步轉強"],
            "action_bias": "降低追價，優先檢查槓桿、分歧與遠期估值風險。",
        },
    }


def build_reasoning_evidence_records(reasoning_pack):
    """Return auditable evidence records for UI, prompt, and future API usage."""
    records = []
    snapshot = reasoning_pack.get("snapshot", {})
    for component in snapshot.get("components", []):
        change_pct = component.get("change_pct")
        if change_pct is None:
            continue
        if change_pct > 0.05:
            direction = "support"
        elif change_pct < -0.05:
            direction = "counter"
        else:
            direction = "neutral"
        records.append({
            "signal_code": f"GLOBAL_{str(component.get('key', '')).upper()}",
            "direction": direction,
            "weight": component.get("weight", 0.0),
            "value": change_pct,
            "evidence_text": f"{component.get('label')} {_fmt_pct(change_pct)}",
            "source": snapshot.get("source", "get_global_market_trend"),
        })

    features = reasoning_pack.get("phase2_features", {})
    inst = features.get("institutional_flow") or {}
    if inst.get("available"):
        direction = "support" if (inst.get("direction_score") or 0) >= 0 else "counter"
        records.append({
            "signal_code": "INSTITUTIONAL_FLOW_10D",
            "direction": direction,
            "weight": 0.25,
            "value": inst.get("combined_10d"),
            "evidence_text": f"法人近10日合計 {inst.get('combined_10d', 0):,.0f} 張",
            "source": inst.get("source", "ui_chip_panel"),
        })

    margin = features.get("margin_credit") or {}
    if margin.get("available"):
        direction = "counter" if (margin.get("risk_score") or 0) >= 60 else "support"
        records.append({
            "signal_code": "MARGIN_CREDIT_RISK",
            "direction": direction,
            "weight": 0.30,
            "value": margin.get("risk_score"),
            "evidence_text": f"信用交易風險 {margin.get('risk_label', 'N/A')}",
            "source": margin.get("source", "FinMind TaiwanStockMarginPurchaseShortSale"),
        })

    short_position = reasoning_pack.get("short_position") or {}
    if short_position.get("available"):
        top_class = short_position.get("top_class")
        direction = "support" if top_class in {"hedge", "covering"} else "counter" if top_class == "directional_bear" else "neutral"
        records.append({
            "signal_code": "SHORT_POSITION_CLASSIFICATION",
            "direction": direction,
            "weight": 0.20,
            "value": top_class,
            "evidence_text": f"空單分類：{short_position.get('display_label') or short_position.get('top_label', 'N/A')}",
            "source": "market_reasoning.classify_short_position",
        })

    for warning in reasoning_pack.get("warnings", []):
        records.append({
            "signal_code": "DATA_OR_MODEL_WARNING",
            "direction": "warning",
            "weight": 0.0,
            "value": None,
            "evidence_text": warning,
            "source": "market_reasoning",
        })

    for idx, record in enumerate(records, 1):
        record["rank"] = idx
    return records


def _compact_snapshot_for_payload(snapshot):
    return {
        "version": snapshot.get("version"),
        "built_at": snapshot.get("built_at"),
        "target_day": snapshot.get("target_day"),
        "source": snapshot.get("source"),
        "available_extensions": snapshot.get("available_extensions", []),
        "expected_extensions": snapshot.get("expected_extensions", []),
        "missing_extensions": snapshot.get("missing_extensions", []),
        "components": [
            {
                "key": component.get("key"),
                "label": component.get("label"),
                "change_pct": component.get("change_pct"),
                "score": component.get("score"),
                "weight": component.get("weight"),
                "available": component.get("available"),
            }
            for component in snapshot.get("components", [])
        ],
    }


def build_market_reasoning_api_payload(reasoning_pack, trade_date=None, analysis_id=None):
    """Build a stable API-style payload without requiring a web framework."""
    snapshot = reasoning_pack.get("snapshot", {})
    built_at = snapshot.get("built_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    default_trade_date = str(built_at)[:10]
    payload = {
        "analysis_id": analysis_id or f"market-{str(built_at).replace(' ', 'T')}",
        "trade_date": trade_date or default_trade_date,
        "generated_at": built_at,
        "model_version": reasoning_pack.get("model_version", MARKET_REASONING_VERSION),
        "direction_score": reasoning_pack.get("direction_score"),
        "risk_score": reasoning_pack.get("risk_score"),
        "confidence_score": reasoning_pack.get("confidence_score"),
        "regime": reasoning_pack.get("regime"),
        "regime_label": reasoning_pack.get("regime_label"),
        "short_position": reasoning_pack.get("short_position", {}),
        "evidence": reasoning_pack.get("reasoning_evidence") or build_reasoning_evidence_records(reasoning_pack),
        "counter_evidence": reasoning_pack.get("counter_evidence", []),
        "scenarios": reasoning_pack.get("scenarios") or build_market_scenarios(reasoning_pack),
        "data_quality": reasoning_pack.get("data_quality", {}),
        "warnings": reasoning_pack.get("warnings", []),
        "source_snapshot": _compact_snapshot_for_payload(snapshot),
    }
    return payload


def build_market_dashboard_snapshot(reasoning_pack, stock_id=None, stock_name=None):
    """Build one compact dashboard/history row from a reasoning pack."""
    scenarios = reasoning_pack.get("scenarios") or {}
    snapshot = reasoning_pack.get("snapshot", {})
    built_at = snapshot.get("built_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "stock_id": stock_id or "",
        "stock_name": stock_name or "",
        "generated_at": built_at,
        "model_version": reasoning_pack.get("model_version", MARKET_REASONING_VERSION),
        "regime": reasoning_pack.get("regime"),
        "regime_label": reasoning_pack.get("regime_label"),
        "direction_score": reasoning_pack.get("direction_score"),
        "risk_score": reasoning_pack.get("risk_score"),
        "confidence_score": reasoning_pack.get("confidence_score"),
        "data_quality": (reasoning_pack.get("data_quality") or {}).get("status"),
        "bull_probability": (scenarios.get("bull") or {}).get("probability"),
        "base_probability": (scenarios.get("base") or {}).get("probability"),
        "bear_probability": (scenarios.get("bear") or {}).get("probability"),
        "short_position_label": (reasoning_pack.get("short_position") or {}).get("top_label", "資料不足"),
        "short_position_display_label": (reasoning_pack.get("short_position") or {}).get("display_label"),
    }
    row["signature"] = "|".join([
        str(row["stock_id"]),
        str(row["model_version"]),
        str(row["regime"]),
        str(round(row["direction_score"], 1)) if row["direction_score"] is not None else "N/A",
        str(round(row["risk_score"], 1)) if row["risk_score"] is not None else "N/A",
        str(round(row["confidence_score"], 1)) if row["confidence_score"] is not None else "N/A",
        str(row["data_quality"]),
    ])
    return row


def append_market_reasoning_history(history, reasoning_pack, stock_id=None, stock_name=None, max_rows=80):
    """
    Append a dashboard snapshot while avoiding duplicate rerun spam.

    If the latest row has the same signature, replace it with the newer timestamp
    instead of growing the history.
    """
    history = list(history or [])
    row = build_market_dashboard_snapshot(reasoning_pack, stock_id=stock_id, stock_name=stock_name)
    if history and history[-1].get("signature") == row.get("signature"):
        history[-1] = row
    else:
        history.append(row)
    return history[-max_rows:]


def build_market_history_frame(history):
    """Return a display-ready DataFrame for market dashboard history."""
    rows = []
    for item in history or []:
        rows.append({
            "時間": item.get("generated_at"),
            "股票": f"{item.get('stock_name') or ''} {item.get('stock_id') or ''}".strip(),
            "狀態": item.get("regime_label"),
            "方向": item.get("direction_score"),
            "風險": item.get("risk_score"),
            "信心": item.get("confidence_score"),
            "Bull": item.get("bull_probability"),
            "Base": item.get("base_probability"),
            "Bear": item.get("bear_probability"),
            "資料品質": item.get("data_quality"),
            "空單分類": item.get("short_position_display_label") or item.get("short_position_label"),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("方向", "風險", "信心"):
        df[col] = pd.to_numeric(df[col], errors="coerce").round(1)
    for col in ("Bull", "Base", "Bear"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def calculate_market_reasoning(
    snapshot_or_trend_data=None,
    *,
    trend_data=None,
    chip_state=None,
    institutional_flow=None,
    margin_credit=None,
    futures_snapshot=None,
    options_snapshot=None,
    fx_snapshot=None,
):
    """Calculate V3 market reasoning output from a normalized snapshot or raw trend_data."""
    raw = trend_data if trend_data is not None else (snapshot_or_trend_data or {})
    if raw.get("components") is not None and raw.get("version"):
        snapshot = raw
    else:
        snapshot = build_market_snapshot(
            raw,
            chip_state=chip_state,
            institutional_flow=institutional_flow,
            margin_credit=margin_credit,
            futures_snapshot=futures_snapshot,
            options_snapshot=options_snapshot,
            fx_snapshot=fx_snapshot,
        )

    components = snapshot.get("components", [])
    phase2_features = snapshot.get("phase2_features", {})
    data_quality = _build_data_quality(components, snapshot)
    direction_score = _calculate_direction_score(components, phase2_features)
    risk_score = _calculate_risk_score(components, direction_score, phase2_features)
    confidence_score = _calculate_confidence_score(
        components,
        phase2_features,
        phase2_expected=bool(snapshot.get("phase2_expected")),
        expected_features=snapshot.get("expected_extensions"),
    )
    regime, regime_label = _judge_regime(direction_score, risk_score, confidence_score, phase2_features)
    evidence, counter_evidence = _build_evidence(components, phase2_features)

    warnings = []
    if data_quality["status"] == "INSUFFICIENT":
        warnings.append("市場推理資料不足，結果不可作為買賣判斷。")
    elif data_quality["status"] == "PARTIAL":
        warnings.append("部分市場推理資料缺漏，信心分數已降權。")
    if direction_score is not None and abs(direction_score) >= 60 and confidence_score < 70:
        warnings.append("方向分數偏強但一致性不足，需等待台股開盤量價確認。")
    short_position = phase2_features.get("short_position") or {}
    if not short_position.get("available"):
        warnings.append(short_position.get("message", "期貨空單分類資料不足。"))

    available = data_quality["status"] != "INSUFFICIENT"
    summary = "市場資料不足，暫不輸出方向判斷。"
    if available:
        direction_text = "偏多" if direction_score > 15 else "偏空" if direction_score < -15 else "中性"
        summary = (
            f"{regime_label}；方向 {direction_text} "
            f"({direction_score:.1f})，風險 {risk_score:.1f}，信心 {confidence_score:.1f}。"
        )

    result = {
        "available": available,
        "model_version": MARKET_REASONING_VERSION,
        "snapshot": snapshot,
        "direction_score": direction_score,
        "risk_score": risk_score,
        "confidence_score": confidence_score,
        "regime": regime,
        "regime_label": regime_label,
        "phase2_features": phase2_features,
        "short_position": short_position,
        "data_quality": data_quality,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
        "warnings": warnings,
        "component_scores": {
            component["key"]: component.get("score")
            for component in components
            if component.get("score") is not None
        },
        "summary": summary,
    }
    result["scenarios"] = build_market_scenarios(result)
    result["reasoning_evidence"] = build_reasoning_evidence_records(result)
    result["api_payload"] = build_market_reasoning_api_payload(result)
    return result


def build_market_reasoning_report(reasoning_pack):
    """Return a compact DataFrame for UI display and tests."""
    rows = [
        {"項目": "模型版本", "結果": reasoning_pack.get("model_version", MARKET_REASONING_VERSION), "說明": "V3 市場推理第七階段"},
        {"項目": "市場狀態", "結果": reasoning_pack.get("regime_label", "資料不足"), "說明": reasoning_pack.get("regime", "")},
        {"項目": "市場方向分數", "結果": _format_score(reasoning_pack.get("direction_score")), "說明": "SOX/TSM ADR/EWT/NQ 為主，台指期外資空單小權重調整"},
        {"項目": "風險分數", "結果": _format_score(reasoning_pack.get("risk_score")), "說明": "國際連動與已接入市場資料綜合；個股籌碼不應混入全市場分數"},
        {"項目": "信心分數", "結果": _format_score(reasoning_pack.get("confidence_score")), "說明": "資料完整度、方向一致性與台指期空單資料可用性"},
        {
            "項目": "資料品質",
            "結果": reasoning_pack.get("data_quality", {}).get("status", "INSUFFICIENT"),
            "說明": reasoning_pack.get("data_quality", {}).get("note", ""),
        },
    ]

    snapshot = reasoning_pack.get("snapshot", {})
    for component in snapshot.get("components", []):
        rows.append({
            "項目": component.get("label", component.get("key", "")),
            "結果": _fmt_pct(component.get("change_pct")),
            "說明": f"權重 {component.get('weight', 0) * 100:.0f}%｜{component.get('role', '')}",
        })

    features = reasoning_pack.get("phase2_features", {})
    inst = features.get("institutional_flow") or {}
    if inst.get("available"):
        rows.append({
            "項目": "法人近10日",
            "結果": f"{inst.get('combined_10d', 0):,.0f} 張",
            "說明": f"外資 {inst.get('f_10d', 0):,.0f}｜投信 {inst.get('t_10d', 0):,.0f}｜方向分數 {_format_score(inst.get('direction_score'))}",
        })
    else:
        rows.append({"項目": "法人近10日", "結果": "N/A", "說明": inst.get("message", "未接入")})

    margin = features.get("margin_credit") or {}
    if margin.get("available"):
        rows.append({
            "項目": "信用交易風險",
            "結果": margin.get("risk_label", "N/A"),
            "說明": f"風險分數 {_format_score(margin.get('risk_score'))}｜融資使用率 {_fmt_ratio(margin.get('margin_usage_ratio'))}",
        })
    else:
        rows.append({"項目": "信用交易風險", "結果": "N/A", "說明": margin.get("message", "未接入")})

    short_position = features.get("short_position") or reasoning_pack.get("short_position") or {}
    if short_position.get("available"):
        probabilities = short_position.get("probabilities") or {}
        rows.append({
            "項目": "空單分類",
            "結果": short_position.get("display_label") or short_position.get("top_label", "N/A"),
            "說明": " / ".join(f"{key}:{value:.0%}" for key, value in probabilities.items() if value is not None),
        })
    else:
        rows.append({"項目": "空單分類", "結果": "資料不足", "說明": short_position.get("message", "缺少期貨資料")})

    scenarios = reasoning_pack.get("scenarios") or {}
    if scenarios:
        rows.append({
            "項目": "情境機率",
            "結果": " / ".join(
                f"{scenario.get('label')} {_fmt_ratio(scenario.get('probability'))}"
                for scenario in scenarios.values()
            ),
            "說明": "Bull/Base/Bear 三情境推理輸出",
        })

    return pd.DataFrame(rows)


def build_market_scenario_report(reasoning_pack):
    """Return Bull/Base/Bear scenarios as a compact DataFrame."""
    rows = []
    for key, scenario in (reasoning_pack.get("scenarios") or {}).items():
        rows.append({
            "情境": scenario.get("label", key),
            "機率": _fmt_ratio(scenario.get("probability")),
            "摘要": scenario.get("summary", ""),
            "觸發條件": "；".join(scenario.get("trigger_conditions") or []),
            "失效條件": "；".join(scenario.get("invalidations") or []),
            "操作偏向": scenario.get("action_bias", ""),
        })
    return pd.DataFrame(rows)


def _format_score(value):
    if value is None:
        return "N/A"
    return f"{value:.1f}/100"


def _fmt_ratio(value):
    if value is None:
        return "N/A"
    return f"{value:.2%}"


def format_market_reasoning_prompt_summary(reasoning_pack):
    """Compact text block for future AI prompt packaging."""
    quality = reasoning_pack.get("data_quality", {})
    short_position = reasoning_pack.get("short_position") or {}
    evidence = "、".join(reasoning_pack.get("evidence") or []) or "無"
    counter = "、".join(reasoning_pack.get("counter_evidence") or []) or "無"
    warnings = "；".join(reasoning_pack.get("warnings") or []) or "無"
    scenarios = reasoning_pack.get("scenarios") or {}
    scenario_text = "、".join(
        f"{scenario.get('label')}={_fmt_ratio(scenario.get('probability'))}"
        for scenario in scenarios.values()
    ) or "無"
    return (
        f"市場推理模型={reasoning_pack.get('model_version')}; "
        f"狀態={reasoning_pack.get('regime_label')}({reasoning_pack.get('regime')}); "
        f"方向={_format_score(reasoning_pack.get('direction_score'))}; "
        f"風險={_format_score(reasoning_pack.get('risk_score'))}; "
        f"信心={_format_score(reasoning_pack.get('confidence_score'))}; "
        f"資料品質={quality.get('status')}; "
        f"空單分類={short_position.get('display_label') or short_position.get('top_label', '資料不足')}; "
        f"情境={scenario_text}; "
        f"支持證據={evidence}; 反向證據={counter}; 警示={warnings}"
    )
