"""AI Gateway helpers for V3 market reasoning analysis."""

from __future__ import annotations

import json
import re
from copy import deepcopy

from market_reasoning import build_market_reasoning_api_payload


MARKET_AI_GATEWAY_VERSION = "V3-AI-Gateway-Phase5b-20260715"

MARKET_AI_RESPONSE_REQUIRED_FIELDS = {
    "summary": str,
    "market_bias": str,
    "short_interpretation": dict,
    "key_evidence": list,
    "counter_evidence": list,
    "scenarios": dict,
    "risk_alerts": list,
    "watch_next": list,
    "confidence": (int, float),
    "disclaimer": str,
}

MARKET_AI_BIAS_VALUES = {"BULLISH", "NEUTRAL", "BEARISH"}
MARKET_AI_SCENARIO_KEYS = {"bull", "base", "bear"}


def _json_safe(value):
    """Return a JSON-serializable deep copy."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _compact_evidence(records, limit=8):
    out = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        out.append({
            "signal_code": record.get("signal_code"),
            "direction": record.get("direction"),
            "evidence_text": record.get("evidence_text"),
            "source": record.get("source"),
        })
        if len(out) >= limit:
            break
    return out


def build_market_ai_input(reasoning_pack, stock_id=None, stock_name=None, trade_date=None):
    """Build the fixed JSON input sent to the AI analysis gateway."""
    payload = deepcopy(reasoning_pack.get("api_payload") or build_market_reasoning_api_payload(reasoning_pack, trade_date=trade_date))
    payload = _json_safe(payload)
    payload["evidence"] = _compact_evidence(payload.get("evidence"), limit=10)
    ai_input = {
        "gateway_version": MARKET_AI_GATEWAY_VERSION,
        "task": "market_reasoning_ai_analysis",
        "language": "zh-TW",
        "analysis_scope": {
            "target": "TAIWAN_EQUITY_MARKET",
            "description": "分析標的是整體台股市場，不是目前 UI 查詢的單一股票。",
            "current_ui_stock_id": str(stock_id or ""),
            "current_ui_stock_name": str(stock_name or ""),
        },
        "stock": {
            "stock_id": str(stock_id or ""),
            "stock_name": str(stock_name or ""),
            "note": "保留相容欄位；AI 市場分析不得針對此單一股票下結論。",
        },
        "rules": {
            "data_boundary": "只能根據 INPUT_JSON 分析，不得自行補資料或上網查詢。",
            "market_scope": "本任務只分析整體台股市場。即使 stock 欄位有值，也只能視為 UI 當時查詢脈絡，不得寫成針對該股票的市場判斷。",
            "must_distinguish": "請區分客觀資料、規則引擎結果、AI 推論與不確定性。",
            "no_guarantee": "不得輸出保證式語言，不得把單一訊號當成確定預測。",
            "missing_data": "缺少資料時，必須降低 confidence 並在 risk_alerts 說明。",
        },
        "output_schema": {
            "summary": "string, 100~250 Chinese chars",
            "market_bias": "BULLISH | NEUTRAL | BEARISH",
            "short_interpretation": {
                "top_class": "string",
                "explanation": "string",
                "probabilities": "object",
            },
            "key_evidence": ["string"],
            "counter_evidence": ["string"],
            "scenarios": {
                "bull": "string",
                "base": "string",
                "bear": "string",
            },
            "risk_alerts": ["string"],
            "watch_next": ["string"],
            "confidence": "number 0~100",
            "disclaimer": "string",
        },
        "input_json": payload,
    }
    return ai_input


def build_market_ai_prompt(ai_input):
    """Build a stable prompt pair for Gemini / ChatGPT style model calls."""
    system_instruction = (
        "你是台股整體市場分析助理。你只能根據使用者提供的 INPUT_JSON 分析整體台股市場。"
        "即使 INPUT_JSON 內有 stock 或 current_ui_stock 欄位，也不得把結論寫成針對單一股票。"
        "你必須回傳完全符合 output_schema 的 JSON，不得增加欄位，不得輸出 Markdown。"
        "你不得自行上網、不得補缺漏數據、不得把單日訊號視為確定預測。"
    )
    user_prompt = (
        "請分析以下市場推理引擎輸出，並回傳單一 JSON 物件。\n"
        "請務必保留不確定性，並用繁體中文回答。\n"
        "INPUT_JSON:\n"
        f"{json.dumps(ai_input, ensure_ascii=False, indent=2)}"
    )
    return {
        "gateway_version": MARKET_AI_GATEWAY_VERSION,
        "system_instruction": system_instruction,
        "user_prompt": user_prompt,
    }


def extract_json_object(text):
    """Extract and parse the first JSON object from model text."""
    if isinstance(text, dict):
        return text
    raw = str(text or "").strip()
    raw = re.sub(r"```json\s*|```", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end + 1]
    return json.loads(raw)


def _normalize_string_list(value, max_items=8):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return [str(value)]
    return [str(item) for item in value if str(item).strip()][:max_items]


def _normalize_confidence(value):
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(100.0, num))


def validate_market_ai_response(payload):
    """Validate and normalize AI output against the phase-5 schema."""
    issues = []
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "issues": ["AI 回覆不是 JSON object"],
            "normalized": None,
        }

    normalized = {}
    for field, expected_type in MARKET_AI_RESPONSE_REQUIRED_FIELDS.items():
        value = payload.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"{field} 型別錯誤或缺漏")
            continue
        normalized[field] = value

    market_bias = str(payload.get("market_bias") or "").upper()
    if market_bias not in MARKET_AI_BIAS_VALUES:
        issues.append("market_bias 必須為 BULLISH / NEUTRAL / BEARISH")
    normalized["market_bias"] = market_bias if market_bias in MARKET_AI_BIAS_VALUES else "NEUTRAL"

    normalized["summary"] = str(payload.get("summary") or "").strip()
    normalized["key_evidence"] = _normalize_string_list(payload.get("key_evidence"))
    normalized["counter_evidence"] = _normalize_string_list(payload.get("counter_evidence"))
    normalized["risk_alerts"] = _normalize_string_list(payload.get("risk_alerts"))
    normalized["watch_next"] = _normalize_string_list(payload.get("watch_next"))
    normalized["disclaimer"] = str(payload.get("disclaimer") or "").strip()

    confidence = _normalize_confidence(payload.get("confidence"))
    if confidence is None:
        issues.append("confidence 必須為 0~100 數字")
        confidence = 0.0
    normalized["confidence"] = confidence

    scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), dict) else {}
    missing_scenarios = MARKET_AI_SCENARIO_KEYS - set(scenarios)
    if missing_scenarios:
        issues.append("scenarios 缺少 bull/base/bear")
    normalized["scenarios"] = {
        key: str(scenarios.get(key) or "").strip()
        for key in ("bull", "base", "bear")
    }

    short_interpretation = payload.get("short_interpretation") if isinstance(payload.get("short_interpretation"), dict) else {}
    normalized["short_interpretation"] = {
        "top_class": str(short_interpretation.get("top_class") or "資料不足"),
        "explanation": str(short_interpretation.get("explanation") or ""),
        "probabilities": short_interpretation.get("probabilities") if isinstance(short_interpretation.get("probabilities"), dict) else {},
    }

    if not normalized["summary"]:
        issues.append("summary 不可為空")
    if not normalized["disclaimer"]:
        issues.append("disclaimer 不可為空")

    return {
        "ok": not issues,
        "issues": issues,
        "normalized": normalized,
    }


def _market_bias_from_scores(direction_score):
    try:
        score = float(direction_score)
    except (TypeError, ValueError):
        return "NEUTRAL"
    if score >= 20:
        return "BULLISH"
    if score <= -20:
        return "BEARISH"
    return "NEUTRAL"


def build_market_ai_fallback_response(ai_input, reason="AI Gateway fallback"):
    """Build a deterministic fallback response from rule-engine data."""
    payload = ai_input.get("input_json") or {}
    direction_score = payload.get("direction_score")
    risk_score = payload.get("risk_score")
    confidence_score = payload.get("confidence_score") or 0
    regime_label = payload.get("regime_label") or "資料不足"
    short_position = payload.get("short_position") if isinstance(payload.get("short_position"), dict) else {}
    scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), dict) else {}
    evidence = payload.get("evidence") or []
    warnings = payload.get("warnings") or []

    def scenario_summary(key):
        scenario = scenarios.get(key) if isinstance(scenarios.get(key), dict) else {}
        label = scenario.get("label") or key
        prob = scenario.get("probability")
        summary = scenario.get("summary") or ""
        if isinstance(prob, (int, float)):
            return f"{label} 機率 {prob:.0%}。{summary}"
        return f"{label}。{summary}"

    key_evidence = [
        str(item.get("evidence_text") or item)
        for item in evidence
        if not isinstance(item, dict) or item.get("direction") in {"support", "neutral"}
    ][:5]
    counter_evidence = [
        str(item.get("evidence_text") or item)
        for item in evidence
        if isinstance(item, dict) and item.get("direction") in {"counter", "warning"}
    ][:5]

    fallback = {
        "summary": (
            f"規則引擎目前判定市場狀態為{regime_label}，方向分數 {direction_score}，"
            f"風險分數 {risk_score}，信心分數 {confidence_score}。"
            "此為 AI Gateway 降級摘要，只根據系統結構化資料生成。"
        ),
        "market_bias": _market_bias_from_scores(direction_score),
        "short_interpretation": {
            "top_class": short_position.get("display_label") or short_position.get("top_label", "資料不足"),
            "explanation": short_position.get("interpretation") or short_position.get("message", "依系統空單分類結果或缺值狀態呈現。"),
            "probabilities": short_position.get("probabilities") if isinstance(short_position.get("probabilities"), dict) else {},
        },
        "key_evidence": key_evidence or ["系統尚未累積足夠支持證據。"],
        "counter_evidence": counter_evidence or ["請檢查資料缺漏與反向訊號。"],
        "scenarios": {
            "bull": scenario_summary("bull"),
            "base": scenario_summary("base"),
            "bear": scenario_summary("bear"),
        },
        "risk_alerts": _normalize_string_list(warnings + [reason]),
        "watch_next": [
            "SOX 與 TSM ADR 是否延續同向",
            "法人近10日買賣超是否轉折",
            "融資使用率與5日融資變化是否升溫",
            "若補進台指期資料，需重新檢查空單分類",
        ],
        "confidence": min(float(confidence_score or 0), 70.0),
        "disclaimer": "本分析只供研究與風險檢查，不構成投資建議或報酬保證。",
        "_fallback": True,
        "_fallback_reason": reason,
        "_gateway_version": MARKET_AI_GATEWAY_VERSION,
    }
    return fallback


def parse_and_validate_market_ai_response(text, ai_input=None):
    """Parse model text and return normalized output, with fallback on failure."""
    ai_input = ai_input or {"input_json": {}}
    try:
        parsed = extract_json_object(text)
    except Exception as exc:
        fallback = build_market_ai_fallback_response(ai_input, reason=f"AI 回覆 JSON 解析失敗：{str(exc)[:120]}")
        return {
            "ok": False,
            "issues": [fallback["_fallback_reason"]],
            "data": fallback,
        }

    validation = validate_market_ai_response(parsed)
    if validation["ok"]:
        data = validation["normalized"]
        data["_fallback"] = False
        data["_gateway_version"] = MARKET_AI_GATEWAY_VERSION
        return {
            "ok": True,
            "issues": [],
            "data": data,
        }

    fallback = build_market_ai_fallback_response(
        ai_input,
        reason="AI 回覆未通過 Schema 驗證：" + "；".join(validation["issues"]),
    )
    return {
        "ok": False,
        "issues": validation["issues"],
        "data": fallback,
    }
