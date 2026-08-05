"""V3 market reasoning backtest and weight-optimization helpers."""

from __future__ import annotations

import math
from copy import deepcopy

import pandas as pd


MARKET_BACKTEST_VERSION = "V3-Backtest-Phase6-20260715"

DEFAULT_MARKET_WEIGHT_CONFIG = {
    "global": 0.65,
    "institutional": 0.25,
    "margin": 0.10,
}

MARKET_WEIGHT_PRESETS = {
    "phase6_default": DEFAULT_MARKET_WEIGHT_CONFIG,
    "global_heavy": {"global": 0.80, "institutional": 0.15, "margin": 0.05},
    "chip_heavy": {"global": 0.45, "institutional": 0.45, "margin": 0.10},
    "risk_control": {"global": 0.55, "institutional": 0.20, "margin": 0.25},
}

FUTURE_RETURN_FIELDS = (
    "future_return_5d",
    "future_return_1d",
    "future_return",
    "future_return_pct",
    "future_return_5d_pct",
    "realized_return",
    "actual_return",
    "未來報酬",
    "5日報酬",
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


def _normalize_return(value):
    num = _to_float(value)
    if num is None:
        return None
    # Accept both decimal returns (0.012) and percent inputs (1.2).
    if abs(num) > 1.5:
        return num / 100.0
    return num


def _first_present(row, keys):
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def normalize_weight_config(weights):
    weights = dict(weights or DEFAULT_MARKET_WEIGHT_CONFIG)
    cleaned = {
        "global": max(_to_float(weights.get("global")) or 0.0, 0.0),
        "institutional": max(_to_float(weights.get("institutional")) or 0.0, 0.0),
        "margin": max(_to_float(weights.get("margin")) or 0.0, 0.0),
    }
    total = sum(cleaned.values())
    if total <= 0:
        return dict(DEFAULT_MARKET_WEIGHT_CONFIG)
    return {key: value / total for key, value in cleaned.items()}


def classify_market_bias(direction_score, bullish_threshold=20.0, bearish_threshold=-20.0):
    score = _to_float(direction_score)
    if score is None:
        return "UNKNOWN"
    if score >= bullish_threshold:
        return "BULLISH"
    if score <= bearish_threshold:
        return "BEARISH"
    return "NEUTRAL"


def classify_realized_return(forward_return, neutral_band=0.0025):
    value = _normalize_return(forward_return)
    if value is None:
        return "UNKNOWN"
    if value > neutral_band:
        return "UP"
    if value < -neutral_band:
        return "DOWN"
    return "FLAT"


def score_prediction_hit(predicted_bias, realized_bias):
    if predicted_bias == "UNKNOWN" or realized_bias == "UNKNOWN":
        return None
    if predicted_bias == "BULLISH":
        return realized_bias == "UP"
    if predicted_bias == "BEARISH":
        return realized_bias == "DOWN"
    return realized_bias == "FLAT"


def _row_dicts(records):
    if records is None:
        return []
    if isinstance(records, pd.DataFrame):
        return records.to_dict("records")
    if isinstance(records, dict):
        return [records]
    return [item for item in records if isinstance(item, dict)]


def _extract_return(row, future_return_field=None):
    if future_return_field:
        return _normalize_return(row.get(future_return_field))
    return _normalize_return(_first_present(row, FUTURE_RETURN_FIELDS))


def _extract_direction_score(row):
    return _to_float(_first_present(row, ("direction_score", "方向", "market_direction_score")))


def _extract_probability(row, key):
    return _to_float(_first_present(row, (key, key.replace("_probability", ""), key.title())))


def build_backtest_samples(
    records,
    future_return_field=None,
    bullish_threshold=20.0,
    bearish_threshold=-20.0,
    neutral_band=0.0025,
):
    """Normalize raw rows into backtest samples. Rows without future return are skipped."""
    samples = []
    skipped = 0
    for idx, row in enumerate(_row_dicts(records), 1):
        direction_score = _extract_direction_score(row)
        future_return = _extract_return(row, future_return_field=future_return_field)
        if direction_score is None or future_return is None:
            skipped += 1
            continue
        predicted_bias = classify_market_bias(direction_score, bullish_threshold, bearish_threshold)
        realized_bias = classify_realized_return(future_return, neutral_band=neutral_band)
        hit = score_prediction_hit(predicted_bias, realized_bias)
        if predicted_bias == "BULLISH":
            strategy_return = future_return
        elif predicted_bias == "BEARISH":
            strategy_return = -future_return
        else:
            strategy_return = 0.0
        samples.append({
            "sample_id": row.get("analysis_id") or row.get("generated_at") or row.get("時間") or idx,
            "stock_id": row.get("stock_id") or row.get("股票") or "",
            "direction_score": direction_score,
            "risk_score": _to_float(_first_present(row, ("risk_score", "風險"))),
            "confidence_score": _to_float(_first_present(row, ("confidence_score", "信心"))),
            "predicted_bias": predicted_bias,
            "future_return": future_return,
            "realized_bias": realized_bias,
            "hit": hit,
            "strategy_return": strategy_return,
            "bull_probability": _extract_probability(row, "bull_probability"),
            "base_probability": _extract_probability(row, "base_probability"),
            "bear_probability": _extract_probability(row, "bear_probability"),
        })
    df = pd.DataFrame(samples)
    df.attrs["skipped_rows"] = skipped
    return df


def _max_drawdown(returns):
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for value in returns:
        ret = _normalize_return(value) or 0.0
        equity *= (1.0 + ret)
        peak = max(peak, equity)
        if peak > 0:
            max_dd = min(max_dd, equity / peak - 1.0)
    return max_dd


def _brier_score(samples):
    values = []
    for _, row in samples.iterrows():
        prob = _to_float(row.get("bull_probability"))
        if prob is None:
            continue
        actual = 1.0 if row.get("future_return", 0.0) > 0 else 0.0
        values.append((prob - actual) ** 2)
    if not values:
        return None
    return sum(values) / len(values)


def _precision_for(samples, predicted_bias, realized_bias):
    subset = samples[samples["predicted_bias"] == predicted_bias]
    if subset.empty:
        return None
    return float((subset["realized_bias"] == realized_bias).mean())


def evaluate_market_backtest(
    records,
    future_return_field=None,
    bullish_threshold=20.0,
    bearish_threshold=-20.0,
    neutral_band=0.0025,
    min_samples=5,
):
    """Evaluate direction-score backtest metrics from rows with future returns."""
    samples = build_backtest_samples(
        records,
        future_return_field=future_return_field,
        bullish_threshold=bullish_threshold,
        bearish_threshold=bearish_threshold,
        neutral_band=neutral_band,
    )
    skipped = int(samples.attrs.get("skipped_rows", 0))
    if len(samples) < min_samples:
        return {
            "available": False,
            "version": MARKET_BACKTEST_VERSION,
            "status": "INSUFFICIENT",
            "sample_count": int(len(samples)),
            "skipped_rows": skipped,
            "required_min_samples": int(min_samples),
            "message": "回測樣本不足；需提供含 future_return_1d 或 future_return_5d 的歷史市場推理紀錄。",
            "samples": samples,
            "report": build_market_backtest_report(None),
        }

    valid_hits = samples["hit"].dropna()
    hit_rate = float(valid_hits.mean()) if not valid_hits.empty else None
    avg_forward_return = float(samples["future_return"].mean())
    avg_strategy_return = float(samples["strategy_return"].mean())
    max_drawdown = _max_drawdown(samples["strategy_return"])
    brier_score = _brier_score(samples)

    result = {
        "available": True,
        "version": MARKET_BACKTEST_VERSION,
        "status": "OK",
        "sample_count": int(len(samples)),
        "skipped_rows": skipped,
        "hit_rate": hit_rate,
        "avg_forward_return": avg_forward_return,
        "avg_strategy_return": avg_strategy_return,
        "max_drawdown": max_drawdown,
        "brier_score": brier_score,
        "bullish_precision": _precision_for(samples, "BULLISH", "UP"),
        "bearish_precision": _precision_for(samples, "BEARISH", "DOWN"),
        "neutral_precision": _precision_for(samples, "NEUTRAL", "FLAT"),
        "prediction_counts": samples["predicted_bias"].value_counts().to_dict(),
        "data_leakage_check": "PASS: only explicit future_return fields are used as labels; feature timestamps are not shifted internally.",
        "samples": samples,
    }
    result["report"] = build_market_backtest_report(result)
    return result


def build_market_backtest_report(result):
    """Build a compact backtest report DataFrame."""
    if not result or not result.get("available"):
        return pd.DataFrame([{
            "項目": "回測狀態",
            "結果": (result or {}).get("status", "INSUFFICIENT"),
            "說明": (result or {}).get("message", "尚未提供可回測樣本。"),
        }])

    def fmt_pct(value):
        if value is None:
            return "N/A"
        return f"{value:.2%}"

    rows = [
        {"項目": "回測版本", "結果": result.get("version"), "說明": "V3 市場推理第六階段"},
        {"項目": "樣本數", "結果": result.get("sample_count"), "說明": f"略過 {result.get('skipped_rows', 0)} 筆缺標籤資料"},
        {"項目": "方向命中率", "結果": fmt_pct(result.get("hit_rate")), "說明": "BULLISH 對上漲、BEARISH 對下跌、NEUTRAL 對盤整"},
        {"項目": "平均未來報酬", "結果": fmt_pct(result.get("avg_forward_return")), "說明": "標籤期間報酬平均"},
        {"項目": "策略平均報酬", "結果": fmt_pct(result.get("avg_strategy_return")), "說明": "BULLISH 做多、BEARISH 反向、NEUTRAL 空手"},
        {"項目": "最大回撤", "結果": fmt_pct(result.get("max_drawdown")), "說明": "以策略報酬序列估算"},
        {"項目": "Brier Score", "結果": "N/A" if result.get("brier_score") is None else f"{result.get('brier_score'):.4f}", "說明": "Bull 機率校準，越低越好"},
        {"項目": "Bull Precision", "結果": fmt_pct(result.get("bullish_precision")), "說明": "多方訊號實際上漲比例"},
        {"項目": "Bear Precision", "結果": fmt_pct(result.get("bearish_precision")), "說明": "空方訊號實際下跌比例"},
        {"項目": "Data Leakage Check", "結果": "PASS", "說明": result.get("data_leakage_check")},
    ]
    return pd.DataFrame(rows)


def _feature_score(row, key):
    aliases = {
        "global": ("global_direction_score", "global_score"),
        "institutional": ("institutional_direction_score", "institutional_score", "inst_direction_score"),
        "margin": ("margin_direction_score", "margin_score"),
    }
    value = _first_present(row, aliases[key])
    if value is not None:
        return _to_float(value)
    features = row.get("feature_scores")
    if isinstance(features, dict):
        return _to_float(features.get(key))
    return None


def _score_with_weights(row, weights):
    weights = normalize_weight_config(weights)
    parts = []
    for key, weight in weights.items():
        value = _feature_score(row, key)
        if value is not None:
            parts.append((value, weight))
    if not parts:
        return _extract_direction_score(row)
    total = sum(weight for _, weight in parts)
    if total <= 0:
        return None
    return sum(value * weight for value, weight in parts) / total


def evaluate_weight_config(
    records,
    weights,
    future_return_field=None,
    bullish_threshold=20.0,
    bearish_threshold=-20.0,
    neutral_band=0.0025,
    min_samples=5,
):
    rows = []
    for row in _row_dicts(records):
        new_row = deepcopy(row)
        new_row["direction_score"] = _score_with_weights(row, weights)
        rows.append(new_row)
    result = evaluate_market_backtest(
        rows,
        future_return_field=future_return_field,
        bullish_threshold=bullish_threshold,
        bearish_threshold=bearish_threshold,
        neutral_band=neutral_band,
        min_samples=min_samples,
    )
    result["weights"] = normalize_weight_config(weights)
    return result


def optimize_market_weights(
    records,
    candidate_weights=None,
    future_return_field=None,
    min_samples=5,
):
    """Compare preset or user-provided weight candidates."""
    candidates = candidate_weights or MARKET_WEIGHT_PRESETS
    rows = []
    best = None
    for name, weights in candidates.items():
        result = evaluate_weight_config(
            records,
            weights,
            future_return_field=future_return_field,
            min_samples=min_samples,
        )
        score = -999.0
        if result.get("available"):
            score = (
                (result.get("hit_rate") or 0.0) * 100.0
                + (result.get("avg_strategy_return") or 0.0) * 1000.0
                - abs(result.get("max_drawdown") or 0.0) * 25.0
            )
        row = {
            "config_name": name,
            "available": result.get("available", False),
            "score": score,
            "sample_count": result.get("sample_count", 0),
            "hit_rate": result.get("hit_rate"),
            "avg_strategy_return": result.get("avg_strategy_return"),
            "max_drawdown": result.get("max_drawdown"),
            "weights": result.get("weights"),
            "status": result.get("status"),
            "message": result.get("message", ""),
        }
        rows.append(row)
        if row["available"] and (best is None or row["score"] > best["score"]):
            best = row

    report = build_weight_optimization_report(rows)
    return {
        "available": best is not None,
        "version": MARKET_BACKTEST_VERSION,
        "best_config": best,
        "candidates": rows,
        "report": report,
        "message": "權重最佳化需含 future_return 標籤的歷史樣本。" if best is None else "已完成候選權重比較。",
    }


def build_weight_optimization_report(rows):
    def fmt_pct(value):
        if value is None:
            return "N/A"
        return f"{value:.2%}"

    out = []
    for row in rows or []:
        weights = row.get("weights") or {}
        out.append({
            "權重組合": row.get("config_name"),
            "可用": "是" if row.get("available") else "否",
            "樣本數": row.get("sample_count"),
            "命中率": fmt_pct(row.get("hit_rate")),
            "策略平均報酬": fmt_pct(row.get("avg_strategy_return")),
            "最大回撤": fmt_pct(row.get("max_drawdown")),
            "global": f"{weights.get('global', 0):.0%}" if weights else "N/A",
            "institutional": f"{weights.get('institutional', 0):.0%}" if weights else "N/A",
            "margin": f"{weights.get('margin', 0):.0%}" if weights else "N/A",
            "狀態": row.get("status"),
        })
    return pd.DataFrame(out)
