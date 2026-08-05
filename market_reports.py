"""Automatic reports and alerts for V3 market reasoning phase 7."""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd


MARKET_REPORT_VERSION = "V3-Report-Phase7-20260715"

SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "danger": 2,
}


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


def _fmt_score(value):
    num = _to_float(value)
    if num is None:
        return "N/A"
    return f"{num:.1f}"


def _fmt_ratio(value):
    num = _to_float(value)
    if num is None:
        return "N/A"
    return f"{num:.1%}"


def _alert(severity, code, title, message, source, action):
    return {
        "severity": severity,
        "code": code,
        "title": title,
        "message": message,
        "source": source,
        "action": action,
    }


def _append_alert(alerts, seen_codes, severity, code, title, message, source, action):
    if code in seen_codes:
        return
    seen_codes.add(code)
    alerts.append(_alert(severity, code, title, message, source, action))


def _sort_alerts(alerts):
    return sorted(
        alerts,
        key=lambda item: (
            -SEVERITY_ORDER.get(item.get("severity"), 0),
            str(item.get("code") or ""),
        ),
    )


def build_market_alerts(reasoning_pack, backtest_result=None, ai_result=None):
    """Build deterministic warning cards from market reasoning outputs."""
    reasoning_pack = reasoning_pack or {}
    alerts = []
    seen_codes = set()
    quality = reasoning_pack.get("data_quality") or {}
    status = quality.get("status", "INSUFFICIENT")

    if status == "INSUFFICIENT":
        _append_alert(
            alerts,
            seen_codes,
            "danger",
            "DATA_INSUFFICIENT",
            "市場推理資料不足",
            "核心資料不足，市場方向、風險與情境機率不可作為操作判斷。",
            "market_reasoning.data_quality",
            "先補齊國際連動、法人現貨與信用交易資料後再解讀。",
        )
    elif status == "PARTIAL":
        missing = "、".join(quality.get("missing_fields") or []) or "部分欄位"
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            "DATA_PARTIAL",
            "市場資料未完整",
            f"缺少 {missing}，信心分數已被降權。",
            "market_reasoning.data_quality",
            "使用報告時保留折扣，等待缺漏資料補齊。",
        )

    risk_score = _to_float(reasoning_pack.get("risk_score"))
    if risk_score is not None and risk_score >= 70:
        _append_alert(
            alerts,
            seen_codes,
            "danger",
            "HIGH_MARKET_RISK",
            "市場風險偏高",
            f"風險分數 {_fmt_score(risk_score)}，空方情境可能快速取得主導。",
            "market_reasoning.risk_score",
            "避免用遠期樂觀估值追價，先檢查曝險與停損條件。",
        )
    elif risk_score is not None and risk_score >= 55:
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            "ELEVATED_MARKET_RISK",
            "市場風險升溫",
            f"風險分數 {_fmt_score(risk_score)}，需確認價格與籌碼是否同步轉弱。",
            "market_reasoning.risk_score",
            "降低單一訊號權重，等待 SOX/TSM ADR 與法人資料確認。",
        )

    confidence_score = _to_float(reasoning_pack.get("confidence_score"))
    if confidence_score is not None and confidence_score < 35:
        _append_alert(
            alerts,
            seen_codes,
            "danger",
            "LOW_CONFIDENCE",
            "市場推理信心過低",
            f"信心分數 {_fmt_score(confidence_score)}，目前判斷可靠度不足。",
            "market_reasoning.confidence_score",
            "暫不升級買進燈號，只保留觀察或資料補齊。",
        )
    elif confidence_score is not None and confidence_score < 55:
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            "MID_LOW_CONFIDENCE",
            "市場推理信心偏低",
            f"信心分數 {_fmt_score(confidence_score)}，訊號可能受到資料缺口或方向分歧影響。",
            "market_reasoning.confidence_score",
            "把市場推理當作輔助權重，不單獨改變操作結論。",
        )

    regime = reasoning_pack.get("regime")
    regime_label = reasoning_pack.get("regime_label") or regime or "資料不足"
    if regime == "RISK_OFF":
        _append_alert(
            alerts,
            seen_codes,
            "danger",
            "RISK_OFF_REGIME",
            "市場進入風險偏好轉弱",
            f"目前狀態為 {regime_label}。",
            "market_reasoning.regime",
            "優先檢查持股風險，避免新增高波動部位。",
        )
    elif regime == "GLOBAL_RISK_ALERT":
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            "GLOBAL_RISK_ALERT",
            "全球科技風險警戒",
            f"目前狀態為 {regime_label}。",
            "market_reasoning.regime",
            "等待國際連動訊號止穩，再評估估值折扣是否解除。",
        )

    direction_score = _to_float(reasoning_pack.get("direction_score"))
    if direction_score is not None and direction_score <= -35:
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            "NEGATIVE_DIRECTION",
            "市場方向明顯偏空",
            f"方向分數 {_fmt_score(direction_score)}，外部風險偏好對台股不利。",
            "market_reasoning.direction_score",
            "先看台股開盤量價是否抵抗，不直接使用樂觀情境。",
        )

    short_position = reasoning_pack.get("short_position") or {}
    if short_position.get("available") and short_position.get("top_class") == "directional_bear":
        probabilities = short_position.get("probabilities") or {}
        prob = _to_float(probabilities.get("directional_bear"))
        severity = "danger" if prob is not None and prob >= 0.45 else "warning"
        _append_alert(
            alerts,
            seen_codes,
            severity,
            "DIRECTIONAL_BEAR_SHORT",
            "空單分類偏方向性看空",
            f"期貨空單分類為 {short_position.get('display_label') or short_position.get('top_label', '方向性看空')}，機率 {_fmt_ratio(prob)}。",
            "market_reasoning.short_position",
            "需確認外資現貨是否同步賣超，若同步轉弱應降低追價。",
        )
    elif not short_position.get("available"):
        _append_alert(
            alerts,
            seen_codes,
            "info",
            "SHORT_POSITION_MISSING",
            "尚未分類空單性質",
            short_position.get("message", "缺少台指期資料，無法判斷避險或方向性放空。"),
            "market_reasoning.short_position",
            "補進台指期外資空單資料後再重新產生報告。",
        )

    features = reasoning_pack.get("phase2_features") or {}
    margin = features.get("margin_credit") or {}
    margin_risk = _to_float(margin.get("risk_score"))
    if margin.get("available") and margin_risk is not None:
        if margin_risk >= 70:
            _append_alert(
                alerts,
                seen_codes,
                "danger",
                "MARGIN_OVERHEAT",
                "信用交易槓桿偏熱",
                f"信用交易風險 {_fmt_score(margin_risk)}，融資槓桿可能放大跌勢。",
                "market_reasoning.margin_credit",
                "不要只用估值便宜判斷買進，需確認融資降溫或價格轉強。",
            )
        elif margin_risk >= 60:
            _append_alert(
                alerts,
                seen_codes,
                "warning",
                "MARGIN_ELEVATED",
                "信用交易風險升溫",
                f"信用交易風險 {_fmt_score(margin_risk)}。",
                "market_reasoning.margin_credit",
                "觀察融資使用率、5日融資變化與股價是否背離。",
            )

    inst = features.get("institutional_flow") or {}
    inst_net = _to_float(inst.get("combined_10d"))
    if inst.get("available") and inst_net is not None and inst_net <= -7000:
        _append_alert(
            alerts,
            seen_codes,
            "danger",
            "INSTITUTIONAL_SELLING_HEAVY",
            "法人賣壓偏重",
            f"法人近10日合計賣超 {abs(inst_net):,.0f} 張。",
            "market_reasoning.institutional_flow",
            "需等待外資或投信賣壓收斂，避免逆勢放大部位。",
        )
    elif inst.get("available") and inst_net is not None and inst_net <= -3000:
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            "INSTITUTIONAL_SELLING",
            "法人偏賣超",
            f"法人近10日合計賣超 {abs(inst_net):,.0f} 張。",
            "market_reasoning.institutional_flow",
            "確認賣超是否與國際連動同步轉弱。",
        )

    for idx, warning in enumerate(reasoning_pack.get("warnings") or [], 1):
        _append_alert(
            alerts,
            seen_codes,
            "warning",
            f"SYSTEM_WARNING_{idx}",
            "系統推理提醒",
            str(warning),
            "market_reasoning.warnings",
            "依提醒檢查資料口徑與缺漏項目。",
        )

    if isinstance(backtest_result, dict):
        if backtest_result.get("available"):
            hit_rate = _to_float(backtest_result.get("hit_rate"))
            max_drawdown = _to_float(backtest_result.get("max_drawdown"))
            if hit_rate is not None and hit_rate < 0.45:
                _append_alert(
                    alerts,
                    seen_codes,
                    "warning",
                    "BACKTEST_LOW_HIT_RATE",
                    "市場推理歷史命中率偏低",
                    f"回測方向命中率 {hit_rate:.1%}。",
                    "market_backtest.evaluate_market_backtest",
                    "不要調高市場推理權重，先檢查樣本期間與標籤品質。",
                )
            if max_drawdown is not None and max_drawdown <= -0.10:
                _append_alert(
                    alerts,
                    seen_codes,
                    "warning",
                    "BACKTEST_DRAWDOWN",
                    "市場推理策略回撤偏大",
                    f"策略最大回撤 {max_drawdown:.1%}。",
                    "market_backtest.evaluate_market_backtest",
                    "把回測結果列為模型調權前置條件。",
                )
        else:
            _append_alert(
                alerts,
                seen_codes,
                "info",
                "BACKTEST_SAMPLE_INSUFFICIENT",
                "回測樣本不足",
                backtest_result.get("message", "尚未提供 future_return 標籤，無法評估歷史命中率。"),
                "market_backtest.evaluate_market_backtest",
                "累積含未來報酬標籤的市場推理歷史後再啟用權重調整。",
            )

    if isinstance(ai_result, dict):
        data = ai_result.get("data") or {}
        if not ai_result.get("ok") or data.get("_fallback"):
            _append_alert(
                alerts,
                seen_codes,
                "warning",
                "AI_GATEWAY_FALLBACK",
                "AI Gateway 已降級",
                "AI 回覆未通過或呼叫失敗，目前使用規則引擎摘要。",
                "ai_services.market_gateway",
                "不要把 AI 摘要當成新增資料，仍以結構化欄位為準。",
            )
        for idx, message in enumerate(data.get("risk_alerts") or [], 1):
            _append_alert(
                alerts,
                seen_codes,
                "info",
                f"AI_RISK_ALERT_{idx}",
                "AI 風險補充",
                str(message),
                "ai_services.market_gateway",
                "僅作語意摘要參考，不取代系統告警。",
            )

    if not any(SEVERITY_ORDER.get(item.get("severity"), 0) >= 1 for item in alerts):
        _append_alert(
            alerts,
            seen_codes,
            "info",
            "NORMAL_MONITORING",
            "未偵測重大告警",
            "目前沒有 danger 或 warning 級別告警；仍需依個股估值與資料品質判斷。",
            "market_reports.build_market_alerts",
            "維持例行追蹤，不因市場輔助訊號單獨升級買進。",
        )

    return _sort_alerts(alerts)


def build_market_alert_report(alerts):
    """Return alert rows for Streamlit display and regression tests."""
    severity_label = {
        "danger": "重大",
        "warning": "警示",
        "info": "提醒",
    }
    rows = []
    for alert in alerts or []:
        rows.append({
            "嚴重度": severity_label.get(alert.get("severity"), alert.get("severity")),
            "代碼": alert.get("code"),
            "標題": alert.get("title"),
            "說明": alert.get("message"),
            "建議": alert.get("action"),
            "來源": alert.get("source"),
        })
    return pd.DataFrame(rows)


def _build_watch_next(reasoning_pack, alerts, ai_result=None):
    watch = []

    def add(item):
        if item and item not in watch:
            watch.append(item)

    alert_codes = {item.get("code") for item in alerts or []}
    if {"HIGH_MARKET_RISK", "ELEVATED_MARKET_RISK", "RISK_OFF_REGIME", "GLOBAL_RISK_ALERT"} & alert_codes:
        add("SOX、TSM ADR、NASDAQ futures 是否止跌或續弱")
    if {"INSTITUTIONAL_SELLING", "INSTITUTIONAL_SELLING_HEAVY"} & alert_codes:
        add("外資與投信近10日買賣超是否同步轉向")
    if {"MARGIN_OVERHEAT", "MARGIN_ELEVATED"} & alert_codes:
        add("融資使用率、融資占股本與5日融資變化")
    if "DIRECTIONAL_BEAR_SHORT" in alert_codes or "SHORT_POSITION_MISSING" in alert_codes:
        add("台指期外資空單與期現價差資料")

    quality = reasoning_pack.get("data_quality") or {}
    missing_extensions = quality.get("missing_extension_groups") or []
    for group in missing_extensions:
        label = {
            "institutional_flow": "法人現貨買賣超",
            "margin_credit": "信用交易",
            "futures_snapshot": "台指期外資空單",
            "options_snapshot": "選擇權波動與避險訊號",
            "fx_snapshot": "美元台幣匯率壓力",
        }.get(group, group)
        add(label)

    if isinstance(ai_result, dict):
        data = ai_result.get("data") or {}
        for item in data.get("watch_next") or []:
            add(str(item))

    add("台股開盤後個股量價是否確認市場推理方向")
    add("個股估值層級、資料品質與法人目標價是否同步")
    return watch[:8]


def _report_type_label(report_type):
    return "盤後報告" if report_type == "post_market" else "盤前報告"


def build_market_auto_report(
    reasoning_pack,
    report_type="pre_market",
    stock_id=None,
    stock_name=None,
    backtest_result=None,
    ai_result=None,
):
    """Build a structured pre-market or post-market report payload."""
    reasoning_pack = reasoning_pack or {}
    snapshot = reasoning_pack.get("snapshot") or {}
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alerts = build_market_alerts(
        reasoning_pack,
        backtest_result=backtest_result,
        ai_result=ai_result,
    )
    label = _report_type_label(report_type)
    stock_label = " ".join(str(x) for x in (stock_name, stock_id) if x)
    title_target = stock_label or "全市場"

    ai_data = (ai_result or {}).get("data") if isinstance(ai_result, dict) else None
    report = {
        "version": MARKET_REPORT_VERSION,
        "report_id": f"{report_type}-{generated_at[:10]}-{stock_id or 'market'}",
        "generated_at": generated_at,
        "report_type": report_type,
        "report_type_label": label,
        "title": f"{title_target} V3 市場推理{label}",
        "stock": {
            "stock_id": str(stock_id or ""),
            "stock_name": str(stock_name or ""),
        },
        "market_summary": reasoning_pack.get("summary", "市場資料不足。"),
        "scores": {
            "direction": reasoning_pack.get("direction_score"),
            "risk": reasoning_pack.get("risk_score"),
            "confidence": reasoning_pack.get("confidence_score"),
        },
        "regime": reasoning_pack.get("regime"),
        "regime_label": reasoning_pack.get("regime_label"),
        "data_quality": reasoning_pack.get("data_quality") or {},
        "scenarios": reasoning_pack.get("scenarios") or {},
        "alerts": alerts,
        "watch_next": _build_watch_next(reasoning_pack, alerts, ai_result=ai_result),
        "ai_summary": {
            "available": isinstance(ai_data, dict),
            "ok": bool((ai_result or {}).get("ok")) if isinstance(ai_result, dict) else False,
            "fallback": bool(ai_data.get("_fallback")) if isinstance(ai_data, dict) else False,
            "market_bias": ai_data.get("market_bias") if isinstance(ai_data, dict) else None,
            "summary": ai_data.get("summary") if isinstance(ai_data, dict) else "",
        },
        "backtest_status": {
            "available": bool(backtest_result.get("available")) if isinstance(backtest_result, dict) else False,
            "status": backtest_result.get("status") if isinstance(backtest_result, dict) else "NOT_PROVIDED",
            "sample_count": backtest_result.get("sample_count") if isinstance(backtest_result, dict) else 0,
            "hit_rate": backtest_result.get("hit_rate") if isinstance(backtest_result, dict) else None,
        },
        "source_snapshot": {
            "built_at": snapshot.get("built_at"),
            "target_day": snapshot.get("target_day"),
            "source": snapshot.get("source"),
        },
        "disclaimer": "本報告只供研究與風險檢查，不構成投資建議或報酬保證。",
    }
    return report


def build_market_report_frame(report):
    """Return a compact one-report summary table."""
    scores = report.get("scores") or {}
    quality = report.get("data_quality") or {}
    backtest = report.get("backtest_status") or {}
    rows = [
        {"項目": "報告版本", "結果": report.get("version"), "說明": report.get("report_type_label")},
        {"項目": "產生時間", "結果": report.get("generated_at"), "說明": report.get("report_id")},
        {"項目": "市場狀態", "結果": report.get("regime_label"), "說明": report.get("regime")},
        {"項目": "方向 / 風險 / 信心", "結果": f"{_fmt_score(scores.get('direction'))} / {_fmt_score(scores.get('risk'))} / {_fmt_score(scores.get('confidence'))}", "說明": "市場推理三核心分數"},
        {"項目": "資料品質", "結果": quality.get("status"), "說明": "、".join(quality.get("missing_fields") or [])},
        {"項目": "告警數", "結果": len(report.get("alerts") or []), "說明": "danger / warning / info 分級"},
        {"項目": "回測狀態", "結果": backtest.get("status"), "說明": f"樣本數 {backtest.get('sample_count', 0)}"},
    ]
    return pd.DataFrame(rows)


def build_market_report_text(report):
    """Render a concise Markdown report for copy/paste and archives."""
    report = report or {}
    scores = report.get("scores") or {}
    lines = [
        f"# {report.get('title', 'V3 市場推理報告')}",
        "",
        f"- 報告版本：{report.get('version', MARKET_REPORT_VERSION)}",
        f"- 產生時間：{report.get('generated_at', 'N/A')}",
        f"- 市場狀態：{report.get('regime_label', '資料不足')} ({report.get('regime', 'N/A')})",
        f"- 分數：方向 {_fmt_score(scores.get('direction'))} / 風險 {_fmt_score(scores.get('risk'))} / 信心 {_fmt_score(scores.get('confidence'))}",
        "",
        "## 市場摘要",
        str(report.get("market_summary") or "N/A"),
        "",
        "## 告警",
    ]

    for alert in report.get("alerts") or []:
        lines.append(
            f"- [{str(alert.get('severity')).upper()}] {alert.get('title')}："
            f"{alert.get('message')} 建議：{alert.get('action')}"
        )

    lines.extend(["", "## 情境"])
    for key, scenario in (report.get("scenarios") or {}).items():
        lines.append(
            f"- {scenario.get('label', key)} {_fmt_ratio(scenario.get('probability'))}："
            f"{scenario.get('summary', '')}"
        )

    lines.extend(["", "## 下一步追蹤"])
    for item in report.get("watch_next") or []:
        lines.append(f"- {item}")

    ai_summary = report.get("ai_summary") or {}
    if ai_summary.get("available"):
        lines.extend([
            "",
            "## AI Gateway 摘要",
            f"- 狀態：{'通過' if ai_summary.get('ok') else '降級'}；市場傾向：{ai_summary.get('market_bias') or 'N/A'}",
            f"- 摘要：{ai_summary.get('summary') or 'N/A'}",
        ])

    lines.extend([
        "",
        "## 限制",
        report.get("disclaimer", "本報告只供研究與風險檢查。"),
    ])
    return "\n".join(lines)
