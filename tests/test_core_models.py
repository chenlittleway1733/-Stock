import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


if "plotly" not in sys.modules:
    sys.modules["plotly"] = types.ModuleType("plotly")
    sys.modules["plotly.graph_objects"] = types.ModuleType("plotly.graph_objects")
    plotly_subplots = types.ModuleType("plotly.subplots")
    plotly_subplots.make_subplots = lambda *args, **kwargs: None
    sys.modules["plotly.subplots"] = plotly_subplots

if "streamlit" not in sys.modules:
    def _identity_decorator(*dargs, **dkwargs):
        if dargs and callable(dargs[0]) and len(dargs) == 1 and not dkwargs:
            return dargs[0]
        return lambda fn: fn

    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = _SessionState()
    streamlit_stub.cache_data = _identity_decorator
    sys.modules["streamlit"] = streamlit_stub
    sys.modules["streamlit.components"] = types.ModuleType("streamlit.components")
    sys.modules["streamlit.components.v1"] = types.ModuleType("streamlit.components.v1")

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: types.SimpleNamespace(status_code=599, json=lambda: {})
    requests_stub.post = lambda *args, **kwargs: types.SimpleNamespace(status_code=599, json=lambda: {})
    sys.modules["requests"] = requests_stub

if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = types.ModuleType("yfinance")

if "google" not in sys.modules:
    google_stub = types.ModuleType("google")
    genai_stub = types.ModuleType("google.genai")
    genai_types_stub = types.ModuleType("google.genai.types")
    genai_types_stub.Tool = lambda *args, **kwargs: {"tool": kwargs}
    genai_types_stub.GoogleSearch = lambda *args, **kwargs: {"google_search": kwargs}
    genai_stub.types = genai_types_stub
    google_stub.genai = genai_stub
    sys.modules["google"] = google_stub
    sys.modules["google.genai"] = genai_stub
    sys.modules["google.genai.types"] = genai_types_stub


import stock_mapping
import industry_taxonomy
import services
import ui_context.financial_context as financial_context
from ai_services.financial_filler import postprocess_financial_ai_payload
from ai_services.financial_schema import normalize_ai_source_metadata
from ai_services.market_gateway import (
    MARKET_AI_GATEWAY_VERSION,
    build_market_ai_fallback_response,
    build_market_ai_input,
    build_market_ai_prompt,
    parse_and_validate_market_ai_response,
    validate_market_ai_response,
)
from market_backtest import (
    MARKET_BACKTEST_VERSION,
    build_backtest_samples,
    evaluate_market_backtest,
    normalize_weight_config,
    optimize_market_weights,
)
from market_reports import (
    MARKET_REPORT_VERSION,
    build_market_alert_report,
    build_market_alerts,
    build_market_auto_report,
    build_market_report_frame,
    build_market_report_text,
)
from dynamic_cap_model import (
    CALIBRATION_DEFAULTS,
    build_m10_margin_benchmark_summary,
    calculate_dynamic_cap_v2,
    get_dynamic_cap_version_info,
    quality_factor_relative,
)
from industry_model import get_industry_valuation_profile
from market_reasoning import (
    append_market_reasoning_history,
    build_market_reasoning_api_payload,
    build_market_history_frame,
    build_market_reasoning_report,
    build_market_scenario_report,
    classify_short_position,
    calculate_market_reasoning,
    format_market_reasoning_prompt_summary,
)
from model_data_loader import (
    build_margin_benchmark_profile,
    get_stock_model_margin_by_stock_id,
    validate_m10_model_data,
)
from services import (
    build_margin_credit_summary,
    build_taifex_foreign_futures_snapshot,
    merge_mops_latest_revenue,
    parse_taifex_futures_contracts_html,
    parse_mops_monthly_revenue_csv,
    parse_mops_monthly_revenue_html,
    reconcile_price_history_with_reference,
)
from ui_context.prompt_context import (
    prompt_chip_panel_summary,
    prompt_dynamic_cap_core,
    prompt_etf_panel_summary,
    prompt_eps_adoption_sync_summary,
    prompt_m10_margin_benchmark_summary,
    prompt_model_gap_trigger_conditions,
    prompt_model_library_feedback_request,
    prompt_peg_valuation_layers,
    prompt_technical_suffix,
)
from ui_context.multiple_context import build_multiple_context
from ui_panels.market_reasoning import (
    MARKET_AI_ANALYSIS_KEY,
    MARKET_AI_BUTTON_KEY,
    MARKET_AUTO_REPORT_TEXT_KEY,
    MARKET_AUTO_REPORT_TYPE_KEY,
    MARKET_REASONING_HISTORY_KEY,
    build_market_reasoning_calculation_kwargs,
)
from validators.candidate_review import build_financial_candidate_data as modular_build_financial_candidate_data
from validators.financial_validation import validate_ai_financial_json as modular_validate_ai_financial_json
from validators.stock_dataset_validation import (
    expected_yahoo_symbol,
    normalize_stock_code,
    validate_stock_dataset,
    validate_stock_record,
    validation_status_from_issues,
)
from validators.stock_dataset_batch import (
    normalize_stock_dataset_dataframe,
    validate_stock_dataset_file,
    validate_stock_dataset_frame,
)
from utils import (
    build_field_source_priority_report,
    build_candidate_data_report,
    build_financial_candidate_data,
    build_financial_quality_report,
    build_forward_eps_calendar_notice,
    build_ttm_eps_adoption,
    build_forward_eps_tiered_valuation_report,
    build_divergence_warnings,
    build_divergence_warning_report,
    build_final_operation_signal,
    calculate_future_evidence_score,
    calc_monthly_revenue_growth,
    detect_forward_eps_period_mismatch,
    format_field_source_priority_for_prompt,
    infer_pricing_horizon,
    summarize_data_quality_levels,
    apply_financial_candidate_reviews,
    load_financial_candidate_review_cache,
    normalize_candidate_review_status,
    source_priority_summary_for_field,
    update_financial_candidate_review,
    validate_ai_financial_json,
    validate_and_correct_financial_metrics,
)


def _parse_stocklist():
    rows = []
    current_category = "未分類"
    for line_no, raw in enumerate((ROOT / "stocklist.txt").read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if "," not in line:
            current_category = line
            continue
        code, name = [x.strip() for x in line.split(",", 1)]
        rows.append({"code": code, "name": name, "category": current_category, "line": line_no})
    return rows


class StockMappingConsistencyTests(unittest.TestCase):
    def test_stocklist_mapping_and_taxonomy_are_in_sync(self):
        rows = _parse_stocklist()
        stocklist_codes = [r["code"] for r in rows]
        mapping_codes = set(stock_mapping.STOCK_MAPPING)
        taxonomy_codes = set(industry_taxonomy.INDUSTRY_TAXONOMY)

        self.assertGreater(len(rows), 0)
        self.assertEqual(len(stocklist_codes), len(set(stocklist_codes)), "stocklist.txt has duplicate stock codes")
        self.assertEqual(set(stocklist_codes), mapping_codes, "stocklist.txt and stock_mapping.py stock codes differ")

        for row in rows:
            self.assertRegex(row["code"], r"^\d{4}$", f"invalid stock code at line {row['line']}")
            self.assertTrue(row["name"], f"missing stock name at line {row['line']}")

        for code, entry in stock_mapping.STOCK_MAPPING.items():
            primary = entry.get("primary_taxon")
            self.assertIn(primary, taxonomy_codes, f"{code} primary_taxon not found in taxonomy: {primary}")

            total_weight = 0.0
            for hybrid in entry.get("hybrid_taxons") or []:
                taxon = hybrid.get("taxon")
                weight = float(hybrid.get("weight", 0) or 0)
                self.assertIn(taxon, taxonomy_codes, f"{code} hybrid taxon not found in taxonomy: {taxon}")
                self.assertGreaterEqual(weight, 0.0, f"{code} hybrid weight below zero")
                self.assertLessEqual(weight, 0.50, f"{code} hybrid weight exceeds 50%")
                total_weight += weight
            self.assertLessEqual(total_weight, 0.50 + 1e-9, f"{code} total hybrid weight exceeds 50%")

    def test_7828_innovation_service_uses_semiconductor_test_model(self):
        rows = {r["code"]: r for r in _parse_stocklist()}
        self.assertIn("7828", rows)
        self.assertEqual(rows["7828"]["name"], "創新服務")
        self.assertIn("測試 / AOI / 自動化檢測設備", rows["7828"]["category"])

        profile = get_industry_valuation_profile("7828", "創新服務")
        self.assertEqual(profile["primary_taxon"], "TEST_AUTOMATION_EQUIPMENT")
        self.assertEqual(profile["model_label"], "測試 / AOI / 自動化檢測設備")
        self.assertEqual(profile["classification_source"], "stock_mapping.py")
        self.assertEqual(profile["m10_margin_status"], "stock_not_valuation_ready")

    def test_2454_cloud_ai_asic_re_rating_keeps_platform_primary_and_hard_cap_locked(self):
        profile = get_industry_valuation_profile("2454", "聯發科")

        self.assertEqual(profile["primary_taxon"], "PLATFORM_IC_LEADER")
        self.assertEqual(profile["re_rating_status"], "CLOUD_AI_ASIC_RE_RATING")
        self.assertIn("IC_DESIGN_ASIC_HIGH_VISIBILITY 35%（hard 0%）", profile["hybrid_taxons_text"])
        self.assertTrue(profile["disable_market_hard_overlay"])
        self.assertIn("FY2_SOFT_PRICED", profile["pricing_horizon_policy"])
        self.assertAlmostEqual(profile["hybrid_cap_display"]["mixed_hard_ceiling_pe"], 60.0)
        self.assertGreater(profile["hybrid_cap_display"]["mixed_soft_ceiling_pe"], 45.0)

        cap_pack = calculate_dynamic_cap_v2(
            stock_id="2454",
            stock_name="聯發科",
            current_price=5000,
            industry_profile=profile,
            ttm_eps=100,
            system_forward_eps=100,
            revenue_yoy=0.80,
            gross_margin=0.50,
            operating_margin=0.25,
            roe=0.25,
            divergence_warnings=[],
            dq_warnings=[],
        )
        self.assertEqual(cap_pack["model_version"], "Dynamic Cap 2.0 calibration 17-C-23")
        self.assertAlmostEqual(cap_pack["structural_hard_ceiling_cap"], 60.0)
        self.assertAlmostEqual(cap_pack["hard_ceiling_cap"], 60.0)
        self.assertFalse(cap_pack["market_condition_hard_adjustment"]["adjusted"])
        self.assertIn("關閉市場 hard overlay", cap_pack["market_condition_hard_adjustment"]["reason"])

    def test_taxonomy_pe_caps_are_ordered_when_present(self):
        for taxon, profile in industry_taxonomy.INDUSTRY_TAXONOMY.items():
            base = profile.get("base_pe")
            floor = profile.get("floor_pe")
            soft = profile.get("soft_ceiling_pe")
            hard = profile.get("hard_ceiling_pe")
            if base is None or floor is None or soft is None or hard is None:
                continue
            self.assertLessEqual(float(floor), float(base), f"{taxon} floor > base")
            self.assertLessEqual(float(base), float(soft), f"{taxon} base > soft")
            self.assertLessEqual(float(soft), float(hard), f"{taxon} soft > hard")

    def test_industry_profile_exposes_primary_taxon_for_prompt_context(self):
        profile = get_industry_valuation_profile("3017", "奇鋐", "科技業", "散熱")

        self.assertEqual(profile.get("primary_taxon"), "THERMAL_LIQUID_CORE")
        self.assertEqual(profile.get("model_key"), "THERMAL_LIQUID_CORE")
        self.assertEqual(profile.get("taxon_key"), "THERMAL_LIQUID_CORE")
        self.assertEqual(profile.get("model_build_version"), "17-C-22")


class MarketReasoningEngineTests(unittest.TestCase):
    def test_bullish_global_tech_inputs_produce_risk_on_regime(self):
        pack = calculate_market_reasoning({
            "sox": 1.8,
            "tsm": 1.4,
            "ewt": 1.0,
            "nq": 0.8,
            "target_day": "今日",
        })

        self.assertTrue(pack["available"])
        self.assertEqual(pack["regime"], "RISK_ON")
        self.assertGreater(pack["direction_score"], 35)
        self.assertLess(pack["risk_score"], 55)
        self.assertGreater(pack["confidence_score"], 90)
        self.assertIn("SOX", " ".join(pack["evidence"]))

    def test_bearish_global_inputs_raise_risk_warning(self):
        pack = calculate_market_reasoning({
            "sox": -2.2,
            "tsm": -1.8,
            "ewt": -1.2,
            "nq": -1.0,
        })

        self.assertTrue(pack["available"])
        self.assertEqual(pack["regime"], "RISK_OFF")
        self.assertLess(pack["direction_score"], -35)
        self.assertGreater(pack["risk_score"], 55)
        self.assertGreaterEqual(len(pack["counter_evidence"]), 4)

    def test_missing_market_inputs_are_not_marked_available(self):
        pack = calculate_market_reasoning({})

        self.assertFalse(pack["available"])
        self.assertEqual(pack["regime"], "DATA_INSUFFICIENT")
        self.assertEqual(pack["data_quality"]["status"], "INSUFFICIENT")
        self.assertTrue(pack["warnings"])

    def test_market_reasoning_report_and_prompt_are_stable(self):
        pack = calculate_market_reasoning({
            "sox": 0.4,
            "tsm": -0.2,
            "ewt": 0.1,
            "nq": 0.2,
        })

        report = build_market_reasoning_report(pack)
        prompt = format_market_reasoning_prompt_summary(pack)

        self.assertIn("市場方向分數", set(report["項目"]))
        self.assertIn("資料品質", set(report["項目"]))
        self.assertIn("市場推理模型=", prompt)
        self.assertIn("資料品質=OK", prompt)

    def test_phase2_institutional_and_margin_features_affect_scores(self):
        chip_state = {
            "has_institutional_data": True,
            "f_10d": 1800,
            "t_10d": 900,
            "margin_credit": {
                "available": True,
                "risk_label": "偏熱",
                "risk_score": 4,
                "margin_usage_ratio": 0.62,
                "margin_to_shares_ratio": 0.08,
                "margin_change_5d_pct": 0.22,
                "source": "FinMind TaiwanStockMarginPurchaseShortSale",
            },
        }
        pack = calculate_market_reasoning(
            trend_data={"sox": 0.7, "tsm": 0.5, "ewt": 0.2, "nq": 0.4},
            chip_state=chip_state,
        )
        report = build_market_reasoning_report(pack)

        self.assertTrue(pack["available"])
        self.assertEqual(pack["data_quality"]["status"], "OK")
        self.assertIn("institutional_flow", pack["data_quality"]["available_groups"])
        self.assertIn("margin_credit", pack["data_quality"]["available_groups"])
        self.assertGreater(pack["risk_score"], 40)
        self.assertTrue(any("法人近10日" == item for item in report["項目"]))
        self.assertTrue(any("信用交易風險" == item for item in report["項目"]))
        self.assertIn("信用交易風險", " ".join(pack["counter_evidence"]))

    def test_phase2_missing_chip_inputs_downgrades_quality_but_keeps_global_signal(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": 1.0, "tsm": 0.8, "ewt": 0.6, "nq": 0.4},
            chip_state={},
        )

        self.assertTrue(pack["available"])
        self.assertEqual(pack["data_quality"]["status"], "PARTIAL")
        self.assertIn("institutional_flow", pack["data_quality"]["missing_fields"])
        self.assertIn("margin_credit", pack["data_quality"]["missing_fields"])

    def test_market_reasoning_ui_defaults_to_global_scope_keys_and_ignores_stock_chip_state(self):
        self.assertEqual(MARKET_REASONING_HISTORY_KEY, "market_reasoning_history_global")
        self.assertEqual(MARKET_AI_ANALYSIS_KEY, "market_ai_analysis_global")
        self.assertEqual(MARKET_AI_BUTTON_KEY, "market_ai_analysis_btn_global")
        self.assertEqual(MARKET_AUTO_REPORT_TYPE_KEY, "market_auto_report_type_global")
        self.assertEqual(MARKET_AUTO_REPORT_TEXT_KEY, "market_auto_report_text_global")

        trend = {"sox": 0.6, "tsm": 0.4, "ewt": 0.2, "nq": 0.3}
        futures = {"available": True, "foreign_futures_short_change": 4000, "price_change_pct": 0.2}
        stock_chip_a = {"f_10d": 5000, "t_10d": 1000, "margin_credit": {"available": True, "risk_score": 80}}
        stock_chip_b = {"f_10d": -5000, "t_10d": -1000, "margin_credit": {"available": True, "risk_score": 10}}

        kwargs_a = build_market_reasoning_calculation_kwargs(trend, stock_chip_a, futures)
        kwargs_b = build_market_reasoning_calculation_kwargs(trend, stock_chip_b, futures)
        self.assertIsNone(kwargs_a["chip_state"])
        self.assertIsNone(kwargs_b["chip_state"])

        pack_a = calculate_market_reasoning(**kwargs_a)
        pack_b = calculate_market_reasoning(**kwargs_b)
        self.assertEqual(round(pack_a["direction_score"], 4), round(pack_b["direction_score"], 4))
        self.assertEqual(round(pack_a["risk_score"], 4), round(pack_b["risk_score"], 4))
        self.assertIn("futures_snapshot", pack_a["data_quality"]["available_groups"])

    def test_market_reasoning_uses_taifex_short_position_in_scores(self):
        trend = {"sox": 0.4, "tsm": 0.3, "ewt": 0.2, "nq": 0.2}
        base = calculate_market_reasoning(trend_data=trend)
        bearish_short = calculate_market_reasoning(
            trend_data=trend,
            futures_snapshot={
                "available": True,
                "foreign_futures_short_change": 9000,
                "foreign_futures_net_oi_lots": -85000,
                "price_change_pct": -0.8,
            },
            institutional_flow={"f_10d": -6000},
        )

        self.assertTrue(bearish_short["short_position"]["available"])
        self.assertEqual(bearish_short["short_position"]["top_class"], "directional_bear")
        self.assertLess(bearish_short["direction_score"], base["direction_score"])
        self.assertGreater(bearish_short["risk_score"], base["risk_score"])

    def test_short_position_classifier_identifies_hedge_when_cash_buys_and_futures_shorts_rise(self):
        result = classify_short_position(
            institutional_flow={"cash_net": 6200},
            futures_snapshot={"foreign_futures_short_change": 14000, "price_change_pct": 0.2},
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["top_class"], "hedge")
        self.assertGreater(result["probabilities"]["hedge"], result["probabilities"]["directional_bear"])

    def test_short_position_classifier_requires_futures_data(self):
        result = classify_short_position(institutional_flow={"cash_net": -3000})

        self.assertFalse(result["available"])
        self.assertIsNone(result["top_class"])
        self.assertIn("台指期", result["message"])

    def test_taifex_foreign_futures_snapshot_parses_tx_foreign_row(self):
        html = """
        <html><body>日期2026/07/15
        <table>
        <tr><th>序號</th><th>商品名稱</th><th>身份別</th><th>多方口數</th><th>多方金額</th><th>空方口數</th><th>空方金額</th><th>多空淨額口數</th><th>多空淨額金額</th><th>未平倉多方口數</th><th>未平倉多方金額</th><th>未平倉空方口數</th><th>未平倉空方金額</th><th>未平倉淨額口數</th><th>未平倉淨額金額</th></tr>
        <tr><td>1</td><td>臺股期貨</td><td>自營商</td><td>8,774</td><td>79,913,086</td><td>10,717</td><td>97,646,365</td><td>-1,943</td><td>-17,733,279</td><td>3,941</td><td>36,404,678</td><td>4,605</td><td>42,508,599</td><td>-664</td><td>-6,103,921</td></tr>
        <tr><td>投信</td><td>6,242</td><td>57,219,234</td><td>4,469</td><td>40,853,445</td><td>1,773</td><td>16,365,789</td><td>81,601</td><td>751,806,333</td><td>5,955</td><td>54,864,606</td><td>75,646</td><td>696,941,727</td></tr>
        <tr><td>外資</td><td>61,727</td><td>561,690,489</td><td>60,535</td><td>551,182,103</td><td>1,192</td><td>10,508,385</td><td>7,319</td><td>67,433,521</td><td>86,876</td><td>800,498,844</td><td>-79,557</td><td>-733,065,323</td></tr>
        </table></body></html>
        """

        row = parse_taifex_futures_contracts_html(html)
        snapshot = build_taifex_foreign_futures_snapshot(row, price_change_pct=-0.8)

        self.assertTrue(row["available"])
        self.assertEqual(row["data_date"], "2026-07-15")
        self.assertEqual(row["product_name"], "臺股期貨")
        self.assertEqual(row["investor_name"], "外資")
        self.assertEqual(snapshot["foreign_futures_net_change"], 1192)
        self.assertEqual(snapshot["foreign_futures_short_change"], -1192)
        self.assertEqual(snapshot["foreign_futures_short_oi_lots"], 86876)
        self.assertEqual(snapshot["foreign_futures_net_oi_lots"], -79557)
        self.assertIn("未平倉偏空", snapshot["net_oi_bias"])

        classified = classify_short_position(futures_snapshot=snapshot)
        self.assertEqual(classified["top_class"], "covering")
        self.assertEqual(classified["position_label"], "未平倉重度偏空")
        self.assertEqual(classified["flow_label"], "當日小幅回補")
        self.assertIn("未平倉重度偏空 / 當日小幅回補", classified["display_label"])
        self.assertIn("不代表既有空單已消失", classified["interpretation"])

    def test_short_position_classifier_uses_open_interest_bias_for_hedge_or_bearish_read(self):
        hedge = classify_short_position(
            institutional_flow={"cash_net": 6200},
            futures_snapshot={
                "foreign_futures_short_change": -1200,
                "foreign_futures_net_oi_lots": -79557,
                "foreign_futures_long_oi_lots": 7319,
                "foreign_futures_short_oi_lots": 86876,
                "price_change_pct": -0.2,
            },
        )
        bear = classify_short_position(
            institutional_flow={"cash_net": -6200},
            futures_snapshot={
                "foreign_futures_short_change": 5200,
                "foreign_futures_net_oi_lots": -79557,
                "foreign_futures_long_oi_lots": 7319,
                "foreign_futures_short_oi_lots": 86876,
                "price_change_pct": -1.0,
            },
        )

        self.assertTrue(hedge["available"])
        self.assertEqual(hedge["top_class"], "hedge")
        self.assertIn("期貨未平倉淨額", "；".join(hedge["evidence"]))
        self.assertEqual(bear["top_class"], "directional_bear")

    def test_phase3_scenarios_and_evidence_records_are_generated(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": 1.2, "tsm": 0.9, "ewt": 0.5, "nq": 0.7},
            chip_state={
                "has_institutional_data": True,
                "f_10d": 2500,
                "t_10d": 700,
                "margin_credit": {
                    "available": True,
                    "risk_label": "正常",
                    "risk_score": 1,
                    "margin_usage_ratio": 0.28,
                    "margin_to_shares_ratio": 0.02,
                    "margin_change_5d_pct": -0.05,
                },
            },
        )

        self.assertEqual(pack["model_version"], "V3-MR-Phase7c-20260715")
        self.assertEqual(set(pack["scenarios"]), {"bull", "base", "bear"})
        self.assertAlmostEqual(sum(s["probability"] for s in pack["scenarios"].values()), 1.0)
        self.assertTrue(pack["reasoning_evidence"])
        self.assertTrue({"signal_code", "direction", "evidence_text"}.issubset(pack["reasoning_evidence"][0]))

        scenario_report = build_market_scenario_report(pack)
        self.assertEqual(set(scenario_report["情境"]), {"多方情境", "基準情境", "空方情境"})
        self.assertIn("觸發條件", scenario_report.columns)

    def test_phase3_api_payload_matches_expected_schema(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": -1.5, "tsm": -1.1, "ewt": -0.7, "nq": -0.8},
            futures_snapshot={"foreign_futures_short_change": 12000, "price_change_pct": -0.9},
            institutional_flow={"cash_net": -5200},
            margin_credit={
                "available": True,
                "risk_label": "偏熱",
                "risk_score": 4,
                "margin_usage_ratio": 0.66,
            },
        )
        payload = build_market_reasoning_api_payload(pack, trade_date="2026-07-15", analysis_id="unit-test")
        prompt = format_market_reasoning_prompt_summary(pack)
        report = build_market_reasoning_report(pack)

        self.assertEqual(payload["analysis_id"], "unit-test")
        self.assertEqual(payload["trade_date"], "2026-07-15")
        self.assertEqual(payload["model_version"], "V3-MR-Phase7c-20260715")
        self.assertIn("scenarios", payload)
        self.assertIn("evidence", payload)
        self.assertIn("source_snapshot", payload)
        self.assertEqual(payload["short_position"]["top_class"], "directional_bear")
        self.assertIn("情境=", prompt)
        self.assertTrue(any("情境機率" == item for item in report["項目"]))

    def test_phase4_dashboard_history_deduplicates_and_builds_frame(self):
        base_pack = calculate_market_reasoning(
            trend_data={"sox": 0.4, "tsm": 0.3, "ewt": 0.2, "nq": 0.1},
            chip_state={
                "f_10d": 1000,
                "t_10d": 300,
                "margin_credit": {"available": True, "risk_label": "正常", "risk_score": 1},
            },
        )
        changed_pack = calculate_market_reasoning(
            trend_data={"sox": -1.8, "tsm": -1.2, "ewt": -0.9, "nq": -1.0},
            chip_state={
                "f_10d": -1500,
                "t_10d": -500,
                "margin_credit": {"available": True, "risk_label": "偏熱", "risk_score": 4},
            },
        )

        history = append_market_reasoning_history([], base_pack, stock_id="2330", stock_name="台積電")
        history = append_market_reasoning_history(history, base_pack, stock_id="2330", stock_name="台積電")
        history = append_market_reasoning_history(history, changed_pack, stock_id="2330", stock_name="台積電")
        frame = build_market_history_frame(history)

        self.assertEqual(len(history), 2)
        self.assertFalse(frame.empty)
        self.assertIn("方向", frame.columns)
        self.assertIn("Bull", frame.columns)
        self.assertEqual(frame.iloc[-1]["股票"], "台積電 2330")

    def test_phase5_ai_gateway_builds_fixed_prompt_input(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": 0.9, "tsm": 0.6, "ewt": 0.4, "nq": 0.5},
            chip_state={
                "f_10d": 1200,
                "t_10d": 500,
                "margin_credit": {"available": True, "risk_label": "正常", "risk_score": 1},
            },
        )

        ai_input = build_market_ai_input(pack, stock_id="2330", stock_name="台積電")
        prompt = build_market_ai_prompt(ai_input)

        self.assertEqual(ai_input["gateway_version"], MARKET_AI_GATEWAY_VERSION)
        self.assertEqual(ai_input["analysis_scope"]["target"], "TAIWAN_EQUITY_MARKET")
        self.assertEqual(ai_input["stock"]["stock_id"], "2330")
        self.assertIn("整體台股市場", ai_input["analysis_scope"]["description"])
        self.assertIn("不得針對此單一股票", ai_input["stock"]["note"])
        self.assertIn("整體台股市場", ai_input["rules"]["market_scope"])
        self.assertIn("只能根據 INPUT_JSON", ai_input["rules"]["data_boundary"])
        self.assertIn("output_schema", ai_input)
        self.assertIn("INPUT_JSON", prompt["user_prompt"])
        self.assertIn("不得把結論寫成針對單一股票", prompt["system_instruction"])
        self.assertIn("不得自行上網", prompt["system_instruction"])

    def test_phase5_ai_gateway_validates_good_json_response(self):
        payload = {
            "summary": "市場狀態偏中性但科技股外部訊號略有支撐，仍需等待法人與信用交易延續確認。",
            "market_bias": "NEUTRAL",
            "short_interpretation": {"top_class": "資料不足", "explanation": "缺少台指期資料", "probabilities": {}},
            "key_evidence": ["SOX 上漲", "法人買超"],
            "counter_evidence": ["信用交易略升溫"],
            "scenarios": {"bull": "多方需 SOX 延續", "base": "維持震盪", "bear": "風險升高轉弱"},
            "risk_alerts": ["期貨資料缺漏"],
            "watch_next": ["SOX", "法人買賣超"],
            "confidence": 68,
            "disclaimer": "僅供研究，不構成投資建議。",
        }

        validation = validate_market_ai_response(payload)
        parsed = parse_and_validate_market_ai_response(json.dumps(payload, ensure_ascii=False))

        self.assertTrue(validation["ok"], validation["issues"])
        self.assertTrue(parsed["ok"], parsed["issues"])
        self.assertFalse(parsed["data"]["_fallback"])
        self.assertEqual(parsed["data"]["market_bias"], "NEUTRAL")

    def test_phase5_ai_gateway_invalid_response_falls_back_to_rule_summary(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": -1.2, "tsm": -0.8, "ewt": -0.5, "nq": -0.6},
            chip_state={"margin_credit": {"available": True, "risk_label": "偏熱", "risk_score": 4}},
        )
        ai_input = build_market_ai_input(pack, stock_id="2330", stock_name="台積電")

        parsed = parse_and_validate_market_ai_response("不是 JSON", ai_input=ai_input)
        fallback = build_market_ai_fallback_response(ai_input, reason="unit test fallback")

        self.assertFalse(parsed["ok"])
        self.assertTrue(parsed["data"]["_fallback"])
        self.assertIn("JSON", parsed["issues"][0])
        self.assertEqual(fallback["_gateway_version"], MARKET_AI_GATEWAY_VERSION)
        self.assertIn(fallback["market_bias"], {"BULLISH", "NEUTRAL", "BEARISH"})

    def test_phase6_backtest_requires_future_return_labels(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": 0.5, "tsm": 0.4, "ewt": 0.2, "nq": 0.3},
            chip_state={"f_10d": 800, "t_10d": 200, "margin_credit": {"available": True, "risk_label": "正常", "risk_score": 1}},
        )
        history = append_market_reasoning_history([], pack, stock_id="2330", stock_name="台積電")

        result = evaluate_market_backtest(history, min_samples=3)

        self.assertFalse(result["available"])
        self.assertEqual(result["version"], MARKET_BACKTEST_VERSION)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertEqual(result["sample_count"], 0)
        self.assertIn("future_return", result["message"])

    def test_phase6_backtest_evaluates_direction_hit_rate_and_returns(self):
        rows = [
            {"direction_score": 35, "future_return_5d": 0.020, "bull_probability": 0.70},
            {"direction_score": 25, "future_return_5d": 0.015, "bull_probability": 0.65},
            {"direction_score": -30, "future_return_5d": -0.018, "bull_probability": 0.20},
            {"direction_score": -25, "future_return_5d": -0.012, "bull_probability": 0.25},
            {"direction_score": 5, "future_return_5d": 0.0005, "bull_probability": 0.45},
        ]

        samples = build_backtest_samples(rows)
        result = evaluate_market_backtest(rows, min_samples=5)

        self.assertEqual(len(samples), 5)
        self.assertTrue(result["available"])
        self.assertEqual(result["sample_count"], 5)
        self.assertAlmostEqual(result["hit_rate"], 1.0)
        self.assertGreater(result["avg_strategy_return"], 0)
        self.assertLessEqual(result["max_drawdown"], 0)
        self.assertFalse(result["report"].empty)

    def test_phase6_weight_optimization_compares_candidates(self):
        rows = [
            {"global_direction_score": -35, "institutional_direction_score": 60, "margin_direction_score": 0, "future_return_5d": 0.020},
            {"global_direction_score": -25, "institutional_direction_score": 55, "margin_direction_score": 0, "future_return_5d": 0.018},
            {"global_direction_score": 40, "institutional_direction_score": -60, "margin_direction_score": -20, "future_return_5d": -0.022},
            {"global_direction_score": 30, "institutional_direction_score": -50, "margin_direction_score": -15, "future_return_5d": -0.015},
            {"global_direction_score": 5, "institutional_direction_score": 0, "margin_direction_score": 0, "future_return_5d": 0.0002},
        ]

        normalized = normalize_weight_config({"global": 2, "institutional": 1, "margin": 1})
        result = optimize_market_weights(rows, min_samples=5)

        self.assertAlmostEqual(sum(normalized.values()), 1.0)
        self.assertTrue(result["available"])
        self.assertEqual(result["version"], MARKET_BACKTEST_VERSION)
        self.assertIsNotNone(result["best_config"])
        self.assertIn(result["best_config"]["config_name"], {"phase6_default", "global_heavy", "chip_heavy", "risk_control"})
        self.assertFalse(result["report"].empty)

    def test_phase7_alerts_detect_risk_off_and_data_quality(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": -3.0, "tsm": -3.0, "ewt": -2.8, "nq": -2.6},
            chip_state={},
        )

        alerts = build_market_alerts(pack)
        alert_codes = {item["code"] for item in alerts}
        report = build_market_alert_report(alerts)

        self.assertIn("DATA_PARTIAL", alert_codes)
        self.assertIn("HIGH_MARKET_RISK", alert_codes)
        self.assertIn("RISK_OFF_REGIME", alert_codes)
        self.assertEqual(alerts[0]["severity"], "danger")
        self.assertIn("嚴重度", report.columns)
        self.assertIn("建議", report.columns)

    def test_phase7_auto_report_contains_markdown_and_watchlist(self):
        pack = calculate_market_reasoning(
            trend_data={"sox": 1.1, "tsm": 0.8, "ewt": 0.4, "nq": 0.6},
            chip_state={
                "f_10d": 1800,
                "t_10d": 500,
                "margin_credit": {"available": True, "risk_label": "正常", "risk_score": 1, "margin_usage_ratio": 0.25},
            },
            futures_snapshot={"foreign_futures_short_change": 4000, "price_change_pct": 0.2},
        )
        backtest = evaluate_market_backtest([], min_samples=5)

        report = build_market_auto_report(
            pack,
            report_type="pre_market",
            stock_id="2330",
            stock_name="台積電",
            backtest_result=backtest,
        )
        frame = build_market_report_frame(report)
        text = build_market_report_text(report)

        self.assertEqual(report["version"], MARKET_REPORT_VERSION)
        self.assertEqual(report["report_type_label"], "盤前報告")
        self.assertEqual(report["stock"]["stock_id"], "2330")
        self.assertTrue(report["alerts"])
        self.assertTrue(report["watch_next"])
        self.assertFalse(frame.empty)
        self.assertIn("## 市場摘要", text)
        self.assertIn("## 告警", text)
        self.assertIn("台積電", text)


class ModelVersionTableTests(unittest.TestCase):
    def test_taxonomy_and_dynamic_cap_version_tables_are_current_and_ordered(self):
        tax_info = industry_taxonomy.get_taxonomy_version_info()
        cap_info = get_dynamic_cap_version_info()
        expected_taxonomy_stages = [
            "17-B-2",
            "17-C",
            "17-C-4",
            "17-C-6",
            "17-C-7B",
            "17-C-10",
            "17-C-11",
            "17-C-12",
            "17-C-13",
            "17-C-14",
            "17-C-15",
            "17-C-16",
            "17-C-17",
            "17-C-18",
            "17-C-19",
            "17-C-20",
            "17-C-21",
            "17-C-22",
        ]
        expected_dynamic_cap_stages = [
            "17-C-4",
            "17-C-5",
            "17-C-6",
            "17-C-7A",
            "17-C-9",
            "17-C-10",
            "17-C-11",
            "17-C-11B",
            "17-C-12",
            "17-C-13",
            "17-C-14",
            "17-C-15",
            "17-C-16",
            "17-C-17",
            "17-C-18",
            "17-C-19",
            "17-C-20",
            "17-C-21",
            "17-C-22",
            "17-C-23",
        ]

        for info in (tax_info,):
            table = info["version_table"]
            orders = [row["order"] for row in table]
            self.assertGreaterEqual(len(table), 5)
            self.assertEqual(info["version"], "17-C-22")
            self.assertEqual(info["latest_stage"], "17-C-22")
            self.assertEqual(info["build_date"], "2026-06-20")
            self.assertEqual(table[-1]["stage"], info["latest_stage"])
            self.assertEqual(orders, sorted(orders))

        table = cap_info["version_table"]
        orders = [row["order"] for row in table]
        self.assertGreaterEqual(len(table), 5)
        self.assertEqual(cap_info["version"], "17-C-23")
        self.assertEqual(cap_info["latest_stage"], "17-C-23")
        self.assertEqual(cap_info["build_date"], "2026-06-23")
        self.assertEqual(table[-1]["stage"], cap_info["latest_stage"])
        self.assertEqual(orders, sorted(orders))

        self.assertEqual([row["stage"] for row in tax_info["version_table"]], expected_taxonomy_stages)
        self.assertEqual([row["stage"] for row in cap_info["version_table"]], expected_dynamic_cap_stages)
        self.assertEqual(cap_info["engine_version"], "Dynamic Cap 2.0 calibration 17-C-23")

    def test_multiplier_tightening_stage_keeps_taxonomy_and_dynamic_cap_in_sync(self):
        expected_caps = {
            "IC_DESIGN_IP_ROYALTY": (45.0, 68.0, 82.0),
            "IC_DESIGN_ASIC_HIGH_VISIBILITY": (45.0, 65.0, 80.0),
            "OPTICAL_COMM_CPO_HIGH_VISIBILITY": (42.0, 65.0, 82.0),
            "IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY": (40.0, 62.0, 78.0),
            "SEMICAP_ADV_PACKAGING_CORE": (38.0, 60.0, 82.0),
            "THERMAL_LIQUID_CORE": (40.0, 60.0, 78.0),
            "TEST_AUTOMATION_EQUIPMENT": (34.0, 55.0, 65.0),
            "INDUSTRIAL_AUTOMATION_CORE": (24.0, 40.0, 55.0),
            "SERVER_RAIL_HIGH_VISIBILITY": (36.0, 55.0, 70.0),
            "AI_CCL_HIGH_VISIBILITY": (36.0, 55.0, 70.0),
            "MEMORY_IP_AI": (30.0, 48.0, 60.0),
            "AI_SERVER_PCB_HIGH_VISIBILITY": (32.0, 48.0, 62.0),
            "HIGH_SPEED_CONNECTOR_CORE": (32.0, 48.0, 62.0),
            "SEMIMAT_ADVANCED_CONSUMABLES": (32.0, 48.0, 60.0),
            "POWER_MANAGEMENT_IC_DESIGN": (24.0, 36.0, 48.0),
            "OSAT_AI_HPC_TESTING": (30.0, 40.0, 52.0),
            "AI_DATACENTER_SWITCH": (34.0, 52.0, 68.0),
            "CONSUMER_TOURISM": (22.0, 32.0, 38.0),
            "ABF_SUBSTRATE": (24.0, 55.0, 82.0),
            "PROBE_AI_ASIC": (50.0, 85.0, 115.0),
            "AI_SERVER_ODM": (20.0, 30.0, 38.0),
            "AI_SERVER_BOARD_SYSTEM": (22.0, 32.0, 40.0),
        }
        user_fy2026_source = "17-C-20 使用者收集 FY2026E / 目標價倍率校準"
        expected_sources = {
            "SEMICAP_ADV_PACKAGING_CORE": user_fy2026_source,
            "THERMAL_LIQUID_CORE": user_fy2026_source,
            "TEST_AUTOMATION_EQUIPMENT": user_fy2026_source,
            "INDUSTRIAL_AUTOMATION_CORE": user_fy2026_source,
            "AI_CCL_HIGH_VISIBILITY": user_fy2026_source,
            "OSAT_AI_HPC_TESTING": user_fy2026_source,
            "ABF_SUBSTRATE": user_fy2026_source,
            "PROBE_AI_ASIC": user_fy2026_source,
            "AI_SERVER_ODM": user_fy2026_source,
            "AI_SERVER_BOARD_SYSTEM": user_fy2026_source,
        }

        for taxon, expected in expected_caps.items():
            tax_profile = industry_taxonomy.INDUSTRY_TAXONOMY[taxon]
            dyn_profile = CALIBRATION_DEFAULTS[taxon]
            tax_caps = (
                float(tax_profile["base_pe"]),
                float(tax_profile["soft_ceiling_pe"]),
                float(tax_profile["hard_ceiling_pe"]),
            )
            dyn_caps = (
                float(dyn_profile["base_pe"]),
                float(dyn_profile["soft_ceiling_pe"]),
                float(dyn_profile["hard_ceiling_pe"]),
            )
            self.assertEqual(tax_caps, expected, taxon)
            self.assertEqual(dyn_caps, expected, taxon)
            self.assertEqual(tax_profile.get("calibration_source"), expected_sources.get(taxon, "17-C-17 倍率寬鬆度收斂"), taxon)

        high_hard_taxons = {
            taxon
            for taxon, profile in industry_taxonomy.INDUSTRY_TAXONOMY.items()
            if profile.get("hard_ceiling_pe") is not None and float(profile["hard_ceiling_pe"]) > 82.0
        }
        high_hard_dyn_taxons = {
            taxon
            for taxon, profile in CALIBRATION_DEFAULTS.items()
            if profile.get("hard_ceiling_pe") is not None and float(profile["hard_ceiling_pe"]) > 82.0
        }
        self.assertEqual(high_hard_taxons, {"PROBE_AI_ASIC"})
        self.assertEqual(high_hard_dyn_taxons, {"PROBE_AI_ASIC"})


class M10ModelDataLoaderTests(unittest.TestCase):
    def test_m10_model_data_loader_validates_expected_counts(self):
        summary = validate_m10_model_data()

        self.assertTrue(summary["ok"], summary["issues"])
        self.assertEqual(summary["industry_category_count"], 90)
        self.assertEqual(summary["stock_model_count"], 276)
        self.assertEqual(summary["valuation_universe_count"], 157)
        self.assertEqual(summary["margin_quality_counts"], {"A": 37, "B": 35, "C": 15, "N/A": 3})

    def test_m10_stock_margin_profiles_apply_usage_guards(self):
        tsmc = build_margin_benchmark_profile("2330")
        bank = build_margin_benchmark_profile("2884")
        biotech_mismatch = build_margin_benchmark_profile("4128")

        self.assertTrue(tsmc["m10_margin_available"])
        self.assertEqual(tsmc["m10_task_id"], "T01")
        self.assertEqual(tsmc["base_gross_margin_pct"], 45)
        self.assertAlmostEqual(tsmc["base_gross_margin_ratio"], 0.45)
        self.assertEqual(tsmc["base_operating_margin_pct"], 35)
        self.assertTrue(tsmc["margin_model_applicable"])
        self.assertTrue(tsmc["margin_can_affect_valuation"])

        self.assertEqual(bank["margin_rule"], "margin_not_applicable")
        self.assertEqual(bank["margin_quality"], "N/A")
        self.assertFalse(bank["margin_model_applicable"])
        self.assertFalse(bank["margin_can_affect_valuation"])

        self.assertEqual(biotech_mismatch["margin_quality"], "C")
        self.assertEqual(biotech_mismatch["m10_data_quality_grade"], "C")
        self.assertEqual(biotech_mismatch["m10_margin_status"], "stock_not_valuation_ready")
        self.assertFalse(biotech_mismatch["margin_can_affect_valuation"])

    def test_industry_profile_attaches_m10_margin_without_replacing_taxon(self):
        profile = get_industry_valuation_profile("2330", "台積電", "科技業", "半導體")

        self.assertEqual(profile["primary_taxon"], "FOUNDRY_ADVANCED")
        self.assertEqual(profile["m10_task_id"], "T01")
        self.assertEqual(profile["m10_category_name"], "半導體｜晶圓代工 / HPC / 先進製程")
        self.assertEqual(profile["base_gross_margin_pct"], 45)
        self.assertEqual(profile["base_operating_margin_pct"], 35)
        self.assertEqual(profile["margin_quality"], "A")
        self.assertEqual(profile["margin_rule"], "high_operating_margin_cap")
        self.assertTrue(profile["margin_can_affect_valuation"])

    def test_m10_old_code_rows_are_available_but_not_valuation_uplift(self):
        old_code = get_stock_model_margin_by_stock_id("1701")
        margin = build_margin_benchmark_profile("1701")

        self.assertEqual(old_code["data_quality_grade"], "D")
        self.assertEqual(old_code["valuation_ready_flag"], "not_ready")
        self.assertEqual(margin["m10_margin_status"], "stock_not_valuation_ready")
        self.assertFalse(margin["margin_can_affect_valuation"])


class StockDatasetValidationTests(unittest.TestCase):
    def test_stock_dataset_validation_accepts_clean_record(self):
        record = {
            "stock_code": "2330",
            "stock_name": "台積電",
            "market_suffix": "TW",
            "yahoo_symbol": "2330.TW",
            "data_quality_grade": "A",
            "include_in_valuation_model": "納入估值模型（高權重）",
            "valuation_ready_flag": "ready",
            "current_price": 100.0,
            "analyst_target_avg": 120.0,
            "fy_eps": 5.0,
            "upside_pct": 0.20,
            "forward_pe": 20.0,
            "target_date": "2026-06-19",
            "price_date": "2026-06-19",
            "eps_year": "FY2026E",
            "source_price_url": "https://example.test/price",
            "source_target_url": "https://example.test/target",
            "source_eps_url": "https://example.test/eps",
        }

        issues = validate_stock_record(record)
        dataset = validate_stock_dataset([record])

        self.assertEqual(normalize_stock_code("2330.0"), "2330")
        self.assertEqual(expected_yahoo_symbol("2330", "TW"), "2330.TW")
        self.assertEqual(issues, [])
        self.assertEqual(validation_status_from_issues(issues), "PASS")
        self.assertEqual(dataset["pass_count"], 1)
        self.assertEqual(dataset["issue_count"], 0)

    def test_stock_dataset_validation_flags_known_code_name_mismatch(self):
        record = {
            "stock_code": "4128",
            "stock_name": "中裕",
            "market_suffix": "TWO",
            "yahoo_symbol": "4128.TWO",
            "data_quality_grade": "C",
            "include_in_valuation_model": "僅分類/題材追蹤",
        }

        issues = validate_stock_record(record)
        dataset = validate_stock_dataset([record])

        self.assertEqual({issue["rule_code"] for issue in issues}, {"V015"})
        self.assertEqual(issues[0]["replacement_code"], "4147")
        self.assertEqual(validation_status_from_issues(issues), "EXCLUDE_OR_MAPPING")
        self.assertEqual(dataset["reports"][0]["validation_status"], "EXCLUDE_OR_MAPPING")
        self.assertEqual(dataset["rule_counts"]["V015"], 1)

    def test_stock_dataset_validation_catches_symbol_and_formula_mismatch(self):
        record = {
            "stock_code": "3017",
            "stock_name": "奇鋐",
            "market_suffix": "TW",
            "yahoo_symbol": "9999.TW",
            "data_quality_grade": "B",
            "include_in_valuation_model": "納入估值模型",
            "valuation_ready_flag": "ready",
            "current_price": 100.0,
            "analyst_target_avg": 150.0,
            "fy_eps": 10.0,
            "upside_pct": 0.10,
            "forward_pe": 11.0,
            "target_date": "2026-06-19",
            "price_date": "2026-06-19",
            "eps_year": "FY2026E",
            "source_price_url": "https://example.test/price",
            "source_target_url": "https://example.test/target",
            "source_eps_url": "https://example.test/eps",
        }

        issues = validate_stock_record(record)
        codes = {issue["rule_code"] for issue in issues}

        self.assertEqual(codes, {"V004", "V010", "V011"})
        self.assertEqual(validation_status_from_issues(issues), "FIX_REQUIRED")

    def test_stock_dataset_validation_warns_extreme_forward_pe(self):
        record = {
            "stock_code": "3661",
            "stock_name": "世芯-KY",
            "market_suffix": "TW",
            "yahoo_symbol": "3661.TW",
            "data_quality_grade": "A",
            "include_in_valuation_model": "納入估值模型（高權重）",
            "valuation_ready_flag": "ready",
            "current_price": 1500.0,
            "analyst_target_avg": 1650.0,
            "fy_eps": 10.0,
            "upside_pct": 0.10,
            "forward_pe": 150.0,
            "target_date": "2026-06-19",
            "price_date": "2026-06-19",
            "eps_year": "FY2026E",
            "source_price_url": "https://example.test/price",
            "source_target_url": "https://example.test/target",
            "source_eps_url": "https://example.test/eps",
        }

        issues = validate_stock_record(record)

        self.assertEqual([issue["rule_code"] for issue in issues], ["V020"])
        self.assertEqual(validation_status_from_issues(issues), "WARN_REVIEW")

    def test_stock_dataset_batch_normalizes_chinese_columns(self):
        df = pd.DataFrame([{
            "任務ID": "T01",
            "分類": "半導體｜晶圓代工",
            "代號": 2330,
            "名稱": "台積電",
            "市場別/尾碼": "TW",
            "現價": 100.0,
            "價格日期": "2026-06-19",
            "法人平均目標價": 120.0,
            "目標價日期": "2026-06-19",
            "FY EPS": 5.0,
            "EPS年度": "FY2026E",
            "上行空間%": "20%",
            "Forward P/E": "20x",
            "現價來源URL": "https://example.test/price",
            "目標價來源URL": "https://example.test/target",
            "EPS來源URL": "https://example.test/eps",
            "資料品質等級": "A",
            "是否納入估值模型": "納入估值模型（高權重）",
            "valuation_ready_flag": "ready",
        }])

        normalized = normalize_stock_dataset_dataframe(df)
        result = validate_stock_dataset_frame(df, source_meta={"sheet_name": "股票明細"})

        self.assertEqual(normalized.iloc[0]["stock_code"], "2330")
        self.assertEqual(normalized.iloc[0]["yahoo_symbol"], "2330.TW")
        self.assertEqual(result["summary"]["status_counts"]["PASS"], 1)
        self.assertEqual(result["summary"]["issue_count"], 0)

    def test_stock_dataset_file_writes_validation_artifacts_from_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "model_input.csv"
            out_dir = Path(tmpdir) / "validation"
            pd.DataFrame([{
                "stock_code": "3017",
                "stock_name": "奇鋐",
                "market_suffix": "TW",
                "yahoo_symbol": "9999.TW",
                "data_quality_grade": "B",
                "include_in_valuation_model": "納入估值模型",
                "valuation_ready_flag": "ready",
                "current_price": 100.0,
                "price_date": "2026-06-19",
                "analyst_target_avg": 150.0,
                "target_date": "2026-06-19",
                "fy_eps": 10.0,
                "eps_year": "FY2026E",
                "upside_pct": 0.10,
                "forward_pe": 11.0,
                "price_source_url": "https://example.test/price",
                "target_source_url": "https://example.test/target",
                "eps_source_url": "https://example.test/eps",
            }]).to_csv(csv_path, index=False)

            result = validate_stock_dataset_file(csv_path, output_dir=out_dir)
            paths = result["artifact_paths"]

            self.assertEqual(result["summary"]["status_counts"]["FIX_REQUIRED"], 1)
            self.assertTrue(Path(paths["report_csv"]).exists())
            self.assertTrue(Path(paths["issues_csv"]).exists())
            self.assertTrue(Path(paths["summary_json"]).exists())
            issues = pd.read_csv(paths["issues_csv"])
            self.assertEqual(set(issues["rule_code"]), {"V004", "V010", "V011"})


class FieldSourcePriorityTests(unittest.TestCase):
    def test_price_history_cross_check_flags_large_source_divergence_without_replacing(self):
        dates = pd.to_datetime(["2026-06-17", "2026-06-18"])
        primary = pd.DataFrame({
            "Open": [960.0, 965.0],
            "High": [970.0, 975.0],
            "Low": [950.0, 960.0],
            "Close": [960.0, 968.0],
            "Volume": [1000, 1200],
        }, index=dates)
        reference = pd.DataFrame({
            "Open": [162.0, 164.0],
            "High": [166.0, 167.0],
            "Low": [160.0, 163.0],
            "Close": [163.0, 165.0],
            "Volume": [3000, 3500],
        }, index=dates)

        checked, note = reconcile_price_history_with_reference(
            primary,
            reference,
            stock_id="3037",
            primary_source="Yahoo Finance",
            reference_source="FinMind",
            divergence_threshold=0.35,
        )

        self.assertIs(checked, primary)
        self.assertEqual(float(checked["Close"].iloc[-1]), 968.0)
        self.assertIn("3037", note)
        self.assertIn("不自動覆蓋現價", note)

    def test_price_history_cross_check_keeps_close_sources(self):
        dates = pd.to_datetime(["2026-06-17", "2026-06-18"])
        primary = pd.DataFrame({"Close": [160.0, 168.0]}, index=dates)
        reference = pd.DataFrame({"Close": [159.0, 165.0]}, index=dates)

        checked, note = reconcile_price_history_with_reference(primary, reference)

        self.assertIs(checked, primary)
        self.assertIsNone(note)

    def test_field_source_priority_report_contains_core_adoption_rules(self):
        report = build_field_source_priority_report(["營收 YoY", "Forward EPS－FY1", "TTM EPS", "D/E"])

        self.assertEqual(len(report), 4)
        revenue = report[report["資料欄位"] == "營收 YoY"].iloc[0]
        fy1 = report[report["資料欄位"] == "Forward EPS－FY1"].iloc[0]
        ttm = report[report["資料欄位"] == "TTM EPS"].iloc[0]
        de = report[report["資料欄位"] == "D/E"].iloc[0]

        self.assertIn("FinMind TaiwanStockMonthRevenue", revenue["來源優先序"])
        self.assertIn("yfinance revenueGrowth 只作診斷備註", revenue["採用規則"])
        self.assertIn("法人 FY1 年度共識 EPS", fy1["來源優先序"])
        self.assertIn("FY1 是前瞻 PEG 年度估值", fy1["採用規則"])
        ttm_priority = str(ttm["來源優先序"])
        self.assertLess(ttm_priority.find("近四季財報 EPS 合計"), ttm_priority.find("yfinance trailingEps"))
        self.assertIn("yfinance trailingEps 僅作備援", ttm["採用規則"])
        self.assertIn("標準化成倍數", de["採用規則"])
        self.assertIn("D/E > 8", de["校驗/降權規則"])

    def test_forward_eps_calendar_notice_flags_h2_and_q4_without_changing_fy_sequence(self):
        june = build_forward_eps_calendar_notice(
            current_date="2026-06-15",
            fy1_year="2026",
            fy2_year="2027",
            fy3_year="2028",
        )
        july = build_forward_eps_calendar_notice(
            current_date="2026-07-15",
            fy1_year="2026",
            fy2_year="2027",
            fy3_year="2028",
        )
        october = build_forward_eps_calendar_notice(
            current_date="2026-10-15",
            fy1_year="2026",
            fy2_year="2027",
            fy3_year="2028",
        )

        self.assertEqual(june["phase"], "h1_fy1_primary")
        self.assertEqual(june["ui_notice"], "")
        self.assertEqual(july["fy_sequence_text"], "FY1=2026E / FY2=2027E / FY3=2028E")
        self.assertIn("同步參考 FY2", july["ui_notice"])
        self.assertEqual(october["phase"], "q4_fy2_primary_reference")
        self.assertIn("FY2 作主要前瞻參考", october["ui_notice"])
        self.assertIn("FY1/FY2/FY3 EPS 計算方式不變", october["prompt_notice"])

    def test_financial_base_context_uses_monthly_yoy_not_yfinance_revenue_growth(self):
        old_monthly = financial_context.get_monthly_revenue
        old_pepb = financial_context.get_pe_pb_data
        old_health = financial_context.get_finmind_financial_health
        try:
            financial_context.get_monthly_revenue = lambda *args, **kwargs: pd.DataFrame({
                "Month": ["2026/05"],
                "YoY": [42.67],
                "MoM": [3.2],
                "revenue_source": ["FinMind TaiwanStockMonthRevenue"],
                "source_url": ["https://example.test/monthly-revenue"],
                "source_rule": ["monthly revenue only; not yfinance revenueGrowth"],
                "announce_month": ["2026/06"],
                "revenue_month": ["2026/05"],
            })
            financial_context.get_pe_pb_data = lambda *args, **kwargs: pd.DataFrame()
            financial_context.get_finmind_financial_health = lambda *args, **kwargs: {}

            context = financial_context.build_financial_base_context(
                stock_id="3008",
                info={"revenueGrowth": 0.2257},
                current_price=2500,
                finmind_key="",
            )
        finally:
            financial_context.get_monthly_revenue = old_monthly
            financial_context.get_pe_pb_data = old_pepb
            financial_context.get_finmind_financial_health = old_health

        self.assertAlmostEqual(context["rev_growth"], 0.4267)
        self.assertEqual(context["latest_rev_display_label"], "公告月份：2026/05")
        self.assertEqual(context["latest_rev_source_url"], "https://example.test/monthly-revenue")
        self.assertEqual(context["latest_rev_source_rule"], "monthly revenue only; not yfinance revenueGrowth")
        self.assertEqual(context["latest_rev_announce_month"], "2026/06")
        self.assertEqual(context["latest_rev_revenue_month"], "2026/05")

    def test_ttm_eps_adoption_prefers_traced_four_quarter_sum_over_yfinance(self):
        result = build_ttm_eps_adoption(
            system_ttm_eps=6.51,
            ai_ttm_eps=7.37,
            system_source="yfinance trailingEps",
            ai_source="AI/外部校對近四季 EPS 合計",
            ai_has_trace=True,
        )

        self.assertEqual(result["adopted_value"], 7.37)
        self.assertIn("近四季", result["adopted_source"])
        self.assertTrue(result["warnings"])
        self.assertIn("可能過舊", result["warnings"][0])

    def test_ttm_eps_adoption_marks_price_pe_inference_as_backup(self):
        result = build_ttm_eps_adoption(
            system_ttm_eps=None,
            ai_ttm_eps=None,
            current_price=120,
            pe_ratio=20,
        )

        self.assertEqual(result["adopted_value"], 6.0)
        self.assertEqual(result["adopted_source"], "現價 / P/E 反推")
        self.assertTrue(result["system_is_inferred"])
        self.assertIn("反推", "；".join(result["notes"]))

    def test_ai_financial_context_derives_last_two_quarter_eps(self):
        context = financial_context.build_ai_financial_context(
            stock_id="2330",
            info={},
            ai_financial_store={
                "2330": {
                    "_stock_id": "2330",
                    "latest_month_eps": 1.1,
                    "latest_quarter_eps": 3.2,
                    "previous_quarter_eps": 2.8,
                }
            },
        )

        self.assertEqual(context["ai_latest_month_eps"], 1.1)
        self.assertEqual(context["ai_latest_quarter_eps"], 3.2)
        self.assertEqual(context["ai_previous_quarter_eps"], 2.8)
        self.assertEqual(context["ai_last_two_quarter_eps"], 6.0)

    def test_get_monthly_revenue_finmind_fallback_has_source_meta(self):
        class FakeResponse:
            def __init__(self, status_code, payload=None, text=""):
                self.status_code = status_code
                self._payload = payload or {}
                self.text = text
                self.content = text.encode("utf-8")

            def json(self):
                return self._payload

        old_mops = services.get_mops_monthly_revenue
        old_get = services.requests.get
        try:
            services.get_mops_monthly_revenue = lambda *args, **kwargs: pd.DataFrame()

            def fake_get(url, *args, **kwargs):
                if "tw.stock.yahoo.com" in url:
                    return FakeResponse(404, text="")
                self.assertIn("TaiwanStockMonthRevenue", url)
                return FakeResponse(200, {
                    "status": 200,
                    "data": [
                        {"date": "2025-05-01", "revenue": 700880000},
                        {"date": "2026-04-01", "revenue": 773500000},
                        {"date": "2026-05-01", "revenue": 814000000},
                    ],
                })

            services.requests.get = fake_get
            df = services.get_monthly_revenue("6789", "")
        finally:
            services.get_mops_monthly_revenue = old_mops
            services.requests.get = old_get

        self.assertFalse(df.empty)
        latest = df.iloc[-1]
        self.assertEqual(latest["revenue_source"], "FinMind TaiwanStockMonthRevenue")
        self.assertIn("api.finmindtrade.com", latest["source_url"])
        self.assertEqual(latest["source_rule"], "FinMind TaiwanStockMonthRevenue; same-month YoY/MoM; not yfinance revenueGrowth")
        self.assertEqual(latest["announce_date"], "來源未提供")
        self.assertEqual(latest["announce_month"], "來源未提供")
        self.assertEqual(latest["revenue_month"], "2026/05")

    def test_calc_monthly_revenue_growth_uses_same_month_last_year(self):
        df = pd.DataFrame([
            {"date": "2025-05-01", "revenue": 700_880_000},
            {"date": "2026-04-01", "revenue": 773_500_000},
            {"date": "2026-05-01", "revenue": 814_000_000},
        ])

        result = calc_monthly_revenue_growth(df)

        self.assertEqual(result["revenue_month"], "2026/05")
        self.assertAlmostEqual(result["monthly_revenue_yoy"], 16.14, places=2)
        self.assertAlmostEqual(result["monthly_revenue_mom"], 5.24, places=2)
        self.assertEqual(result["source_rule"], "monthly revenue only; not yfinance revenueGrowth")

    def test_parse_mops_monthly_revenue_html_calculates_yoy_and_mom(self):
        html = """
        <table>
          <tr>
            <th>公司代號</th><th>公司名稱</th><th>當月營收</th><th>上月營收</th>
            <th>去年當月營收</th><th>上月比較增減(%)</th><th>去年同月增減(%)</th>
          </tr>
          <tr><td>6789</td><td>采鈺</td><td>814000</td><td>773500</td><td>700880</td><td>5.23</td><td>16.14</td></tr>
        </table>
        """

        df = parse_mops_monthly_revenue_html(html, "6789", "2026/05")

        self.assertFalse(df.empty)
        self.assertEqual(df.iloc[0]["Month"], "2026/05")
        self.assertAlmostEqual(df.iloc[0]["monthly_revenue_yoy"], 16.14, places=2)
        self.assertAlmostEqual(df.iloc[0]["monthly_revenue_mom"], 5.24, places=2)
        self.assertEqual(df.iloc[0]["revenue_source"], "MOPS 公開資訊觀測站月營收")

    def test_parse_mops_monthly_revenue_csv_calculates_yoy_and_source_meta(self):
        csv_text = """出表日期,資料年月,公司代號,公司名稱,產業別,營業收入-當月營收,營業收入-上月營收,營業收入-去年當月營收,營業收入-上月比較增減(%),營業收入-去年同月增減(%)
"1150617","11505","6789","采鈺","半導體業","814000","773500","700880","5.23594","16.14094"
"""

        df = parse_mops_monthly_revenue_csv(csv_text, "6789", "上市", "https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv")

        self.assertFalse(df.empty)
        self.assertEqual(df.iloc[0]["Month"], "2026/05")
        self.assertAlmostEqual(df.iloc[0]["monthly_revenue_yoy"], 16.14, places=2)
        self.assertAlmostEqual(df.iloc[0]["monthly_revenue_mom"], 5.24, places=2)
        self.assertEqual(df.iloc[0]["revenue_source"], "MOPS 開放資料月營收(上市)")
        self.assertEqual(df.iloc[0]["source_rule"], "MOPS OpenData monthly revenue; same-month YoY/MoM")
        self.assertEqual(df.iloc[0]["announce_date"], "2026/06/17")
        self.assertEqual(df.iloc[0]["announce_month"], "2026/06")
        self.assertEqual(df.iloc[0]["source_url"], "https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv")

    def test_mops_latest_revenue_overrides_same_month_history_row(self):
        history = pd.DataFrame([
            {"Month": "2026/04", "Revenue": 7.735, "YoY": 2.0, "MoM": 1.0, "revenue_source": "FinMind TaiwanStockMonthRevenue"},
            {"Month": "2026/05", "Revenue": 8.14, "YoY": -0.62, "MoM": 5.23, "revenue_source": "FinMind TaiwanStockMonthRevenue"},
        ])
        mops = pd.DataFrame([
            {
                "Month": "2026/05",
                "Revenue": 8.14,
                "YoY": 16.14,
                "MoM": 5.24,
                "monthly_revenue_yoy": 16.14,
                "monthly_revenue_mom": 5.24,
                "revenue_source": "MOPS 公開資訊觀測站月營收(上市)",
            }
        ])

        merged = merge_mops_latest_revenue(history, mops)

        self.assertEqual(len(merged), 2)
        latest = merged[merged["Month"] == "2026/05"].iloc[0]
        self.assertEqual(latest["revenue_source"], "MOPS 公開資訊觀測站月營收(上市)")
        self.assertAlmostEqual(latest["monthly_revenue_yoy"], 16.14)

    def test_financial_quality_report_includes_source_priority_column(self):
        report = build_financial_quality_report([
            {
                "field": "營收 YoY",
                "system_source": "MOPS/FinMind/Yahoo 月營收",
                "system_source_url": "https://mops.twse.com.tw/nas/t21/sii/t21sc03_115_5_0.html",
                "source_rule": "MOPS monthly revenue; same-month YoY/MoM",
                "announce_date": "2026/06/10",
                "announce_month": "2026/06",
                "revenue_month": "2026/05",
                "system_value": 0.71,
                "ai_source": "AI補齊",
                "ai_value": 0.69,
                "adopted_value": 0.71,
                "adopted_source": "FinMind/yfinance",
                "period": "公告月份：2026/05",
                "fmt": "pct",
            }
        ])

        self.assertIn("來源優先序", report.columns)
        self.assertIn("系統來源網址", report.columns)
        self.assertIn("來源規則", report.columns)
        self.assertIn("公告日", report.columns)
        self.assertIn("公告月份", report.columns)
        self.assertIn("營收所屬月份", report.columns)
        self.assertIn("FinMind TaiwanStockMonthRevenue", report.iloc[0]["來源優先序"])
        self.assertEqual(report.iloc[0]["系統來源網址"], "https://mops.twse.com.tw/nas/t21/sii/t21sc03_115_5_0.html")
        self.assertEqual(report.iloc[0]["來源規則"], "MOPS monthly revenue; same-month YoY/MoM")
        self.assertEqual(report.iloc[0]["公告月份"], "2026/06")
        self.assertEqual(report.iloc[0]["營收所屬月份"], "2026/05")
        self.assertIn("系統+AI交叉", report.iloc[0]["品質狀態"])

    def test_prompt_source_priority_summary_is_compact_and_includes_critical_fields(self):
        prompt = format_field_source_priority_for_prompt(["營收 YoY", "Forward EPS－FY2", "D/E"], max_rows=5)

        self.assertIn("欄位=營收 YoY", prompt)
        self.assertIn("yfinance revenueGrowth", prompt)
        self.assertIn("欄位=Forward EPS－FY2", prompt)
        self.assertIn("FY2 只作市場先行定價", prompt)
        self.assertIn("欄位=D/E", prompt)

    def test_source_priority_summary_handles_aliases(self):
        summary = source_priority_summary_for_field("forward_eps_fy1")

        self.assertIn("法人 FY1 年度共識 EPS", summary)
        self.assertIn("FY1 是前瞻 PEG 年度估值", summary)

    def test_financial_candidate_data_standardizes_review_status_and_source_tier(self):
        ai_fin = {
            "_stock_id": "3008",
            "_stock_name": "大立光",
            "ttm_eps": 48.12,
            "yoy": 0.4267,
            "target_price_avg": 3200,
            "data_period": "2026Q1",
            "_ai_source_trace": {
                "ttm_eps": {
                    "source": "公開資訊觀測站公司財報",
                    "published_date": "2026Q1",
                    "source_url": "https://mops.example.test",
                    "note": "近四季 EPS 合計",
                    "confidence": "high",
                },
                "yoy": {
                    "source": "AI依成長率推估",
                    "published_date": "2026/05",
                    "note": "非公告單月 YoY",
                },
            },
        }

        candidates = build_financial_candidate_data(
            ai_fin,
            system_values={"ttm_eps": 48.12, "yoy": 0.2257},
            stock_id="3008",
            stock_name="大立光",
            retrieved_at="2026-06-18T15:00:00",
        )

        by_field = {row["field_name"]: row for row in candidates}
        self.assertEqual(by_field["ttm_eps"]["review_status"], "pending")
        self.assertEqual(by_field["ttm_eps"]["source_tier"], 1)
        self.assertEqual(by_field["ttm_eps"]["conflict_status"], "same_as_system")
        self.assertEqual(by_field["ttm_eps"]["unit"], "NTD/share")
        self.assertEqual(by_field["yoy"]["source_tier"], 5)
        self.assertEqual(by_field["yoy"]["unit"], "ratio_decimal")
        self.assertEqual(by_field["yoy"]["conflict_status"], "different_from_system")
        self.assertAlmostEqual(by_field["yoy"]["difference_pct"], (0.4267 - 0.2257) / 0.2257)
        self.assertEqual(by_field["target_price_avg"]["conflict_status"], "not_compared")
        self.assertTrue(by_field["target_price_avg"]["candidate_id"].startswith("fin:3008:target_price_avg:"))

    def test_candidate_data_report_exposes_review_status(self):
        candidates = build_financial_candidate_data(
            {
                "forward_eps_fy1": 120.5,
                "_ai_source_trace": {
                    "forward_eps_fy1": {
                        "source": "券商報告摘要",
                        "published_date": "2026/06/10",
                        "review_status": "needs_followup",
                    }
                },
            },
            stock_id="2330",
            stock_name="台積電",
            retrieved_at="2026-06-18T15:00:00",
        )

        report = build_candidate_data_report(candidates)

        self.assertIn("審核狀態", report.columns)
        self.assertIn("來源層級", report.columns)
        self.assertEqual(report.iloc[0]["審核狀態"], "需追查")
        self.assertEqual(report.iloc[0]["來源層級"], "Level 4")
        self.assertEqual(normalize_candidate_review_status("保留原值"), "kept_original")

    def test_candidate_review_cache_persists_and_applies_status(self):
        candidates = build_financial_candidate_data(
            {"ttm_eps": 10.5, "_ai_source_trace": {"ttm_eps": {"source": "公開資訊觀測站"}}},
            stock_id="3008",
            stock_name="大立光",
            retrieved_at="2026-06-18T15:00:00",
        )
        candidate = candidates[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "candidate_reviews.json"
            record = update_financial_candidate_review(
                stock_id="3008",
                candidate_id=candidate["candidate_id"],
                review_status="accepted",
                decision_note="unit test accept",
                candidate_snapshot=candidate,
                cache_path=cache_path,
            )
            loaded = load_financial_candidate_review_cache(cache_path)
            applied = apply_financial_candidate_reviews(candidates, loaded, stock_id="3008")

        self.assertEqual(record["review_status"], "accepted")
        self.assertIn("reviews", loaded)
        self.assertEqual(applied[0]["review_status"], "accepted")
        self.assertEqual(applied[0]["decision_note"], "unit test accept")

    def test_modular_validator_boundaries_reexport_financial_helpers(self):
        payload = {"gross_margin": "25.5", "operating_margin": "12.0"}

        validated = modular_validate_ai_financial_json(payload, stock_id="TEST", stock_name="測試股")
        candidates = modular_build_financial_candidate_data(
            {"ttm_eps": 10.0, "_ai_source_trace": {"ttm_eps": {"source": "公開資訊觀測站"}}},
            stock_id="TEST",
            stock_name="測試股",
            retrieved_at="2026-06-18T15:00:00",
        )

        self.assertAlmostEqual(validated["gross_margin"], 0.255)
        self.assertAlmostEqual(validated["operating_margin"], 0.12)
        self.assertEqual(candidates[0]["field_name"], "ttm_eps")
        self.assertEqual(candidates[0]["source_tier"], 1)

    def test_ai_financial_postprocess_module_adds_sources_candidates_and_query_payload(self):
        parsed = {
            "ttm_eps": 5.4,
            "target_price_high": 90,
            "target_price_avg": 120,
            "target_price_low": 150,
            "data_period": "2026Q1",
            "_sources": {
                "ttm_eps": {
                    "source": "公開資訊觀測站",
                    "published_date": "2026Q1",
                    "source_url": "https://mops.example.test",
                    "note": "近四季合計",
                }
            },
        }

        result = postprocess_financial_ai_payload(
            parsed,
            marker_data={"target_price_avg": 130},
            stock_id="3008",
            stock_name="大立光",
            target_year=2026,
            used_model="gemini-3.1-pro-preview",
            used_search=True,
            attempts=[{"ok": True}],
            prompt_text="PROMPT",
            system_prompt="SYSTEM",
        )

        self.assertIn("_ai_source_trace", result)
        self.assertEqual(result["_ai_source_trace"]["ttm_eps"]["source"], "公開資訊觀測站")
        self.assertEqual(result["target_price_high"], 150)
        self.assertEqual(result["target_price_avg"], 120)
        self.assertEqual(result["target_price_low"], 90)
        self.assertTrue(result["_candidate_data"])
        self.assertIn("pending_review_candidates=", result["_candidate_data_status"])
        self.assertIn('"target_year": 2026', result["query_payload"])

    def test_ai_financial_schema_normalizes_source_metadata(self):
        result = normalize_ai_source_metadata({
            "ttm_eps": 12.3,
            "data_period": "2026Q1",
            "_sources": {"ttm_eps": "公開資訊觀測站"},
        })

        self.assertEqual(result["_ai_source_trace"]["ttm_eps"]["source"], "公開資訊觀測站")
        self.assertEqual(result["_ai_source_trace"]["ttm_eps"]["published_date"], "2026Q1")


class ValuationLogicTests(unittest.TestCase):
    def test_m10_margin_not_applicable_skips_margin_uplift_and_guard(self):
        result = quality_factor_relative(
            gross_margin=0.80,
            operating_margin=0.60,
            roe=0.20,
            calibration={
                "margin_quality": "N/A",
                "margin_rule": "margin_not_applicable",
                "margin_model_applicable": False,
                "margin_can_affect_valuation": False,
                "max_quality_factor": 1.30,
            },
        )

        self.assertAlmostEqual(result["factor"], 1.03, places=4)
        self.assertIn("不適用製造業毛利率 / 營益率模型", result["reason"])
        self.assertIn("跳過營益率防呆", result["reason"])

    def test_m10_tracking_only_zeroes_positive_margin_uplift(self):
        result = quality_factor_relative(
            gross_margin=0.70,
            operating_margin=0.45,
            roe=None,
            calibration={
                "gross_margin_baseline": 0.30,
                "gross_margin_good": 0.40,
                "gross_margin_excellent": 0.50,
                "base_operating_margin_ratio": 0.10,
                "operating_margin_low_ratio": 0.00,
                "operating_margin_high_ratio": 0.20,
                "margin_quality": "C",
                "margin_rule": "event_or_cycle_tracking_only",
                "margin_model_applicable": True,
                "margin_can_affect_valuation": False,
                "m10_margin_status": "tracking_only",
                "max_quality_factor": 1.30,
            },
        )

        self.assertAlmostEqual(result["factor"], 1.00, places=4)
        self.assertIn("正向 margin 加分歸零", result["reason"])

    def test_m10_operating_margin_benchmark_adds_small_adjustment(self):
        result = quality_factor_relative(
            gross_margin=0.45,
            operating_margin=0.30,
            roe=None,
            calibration={
                "gross_margin_baseline": 0.40,
                "gross_margin_good": 0.45,
                "gross_margin_excellent": 0.55,
                "base_operating_margin_ratio": 0.20,
                "operating_margin_low_ratio": 0.08,
                "operating_margin_high_ratio": 0.28,
                "margin_quality": "A",
                "margin_rule": "standard_margin_benchmark",
                "margin_model_applicable": True,
                "margin_can_affect_valuation": True,
                "max_quality_factor": 1.30,
            },
        )

        self.assertGreater(result["factor"], 1.00)
        self.assertIn("M10 分類", result["reason"])

    def test_dynamic_cap_pack_exposes_m10_margin_benchmark_for_ui_and_prompt(self):
        profile = {
            "model_key": "FOUNDRY",
            "model_label": "晶圓代工測試分類",
            "primary_valuation": "forward_pe",
            "pe_applicable": True,
            "themes": ["HPC"],
            "classification_confidence_factor": 1.0,
            "classification_source": "unit_test",
            "m10_margin_available": True,
            "m10_margin_status": "usable",
            "m10_task_id": "T01",
            "m10_category_name": "半導體｜晶圓代工 / HPC / 先進製程",
            "base_gross_margin_pct": 45,
            "gross_margin_low_pct": 35,
            "gross_margin_high_pct": 60,
            "base_operating_margin_pct": 35,
            "operating_margin_low_pct": 20,
            "operating_margin_high_pct": 50,
            "margin_quality": "A",
            "margin_rule": "high_operating_margin_cap",
            "margin_model_applicable": True,
            "margin_can_affect_valuation": True,
            "margin_reference_stocks": "2330 台積電；2303 聯電",
        }

        summary = build_m10_margin_benchmark_summary(profile)
        self.assertEqual(summary["status"], "usable")
        self.assertEqual(summary["base_gross_margin_pct"], 45.0)
        self.assertTrue(summary["can_affect_valuation"])

        pack = calculate_dynamic_cap_v2(
            stock_id="TEST",
            stock_name="M10測試股",
            current_price=120,
            info={"marketCap": 300_000_000_000},
            industry_profile=profile,
            gross_margin=0.50,
            operating_margin=0.38,
            roe=0.22,
            debt_to_equity=0.30,
            revenue_yoy=0.18,
            free_cash_flow=1_000_000_000,
            ttm_eps=5.0,
            system_forward_eps=6.0,
            consensus_forward_eps=6.2,
        )

        self.assertEqual(pack["m10_margin_benchmark"]["status"], "usable")
        report_text = " ".join(str(x) for x in pack["report"]["項目"].tolist())
        self.assertIn("M10 margin benchmark", report_text)
        prompt_text = prompt_dynamic_cap_core(pack, mode="research")
        self.assertIn("M10 margin benchmark", prompt_text)
        self.assertIn("晶圓代工 / HPC", prompt_text)
        self.assertIn("2330 台積電", prompt_text)

    def test_prompt_m10_margin_benchmark_summary_marks_not_applicable(self):
        text = prompt_m10_margin_benchmark_summary({
            "m10_margin_benchmark": {
                "available": True,
                "status": "not_applicable",
                "status_label": "不適用 margin 模型",
                "category_name": "金融業｜金控",
                "margin_quality": "N/A",
                "margin_rule_label": "不適用 margin 模型",
                "model_applicable": False,
                "can_affect_valuation": False,
                "usage_label": "不適用製造業毛利率 / 營益率模型；品質係數只採 ROE 與財務風險",
            }
        })

        self.assertIn("不適用 margin 模型", text)
        self.assertIn("品質係數只採 ROE", text)

    def test_dynamic_cap_returns_bounded_forward_pe_pack(self):
        profile = dict(industry_taxonomy.get_taxonomy("AI_SERVER_ODM"))
        profile.update({
            "model_key": "AI_SERVER_ODM",
            "model_label": profile.get("display_name", "AI Server ODM"),
            "themes": ["AI伺服器"],
            "classification_confidence_factor": 1.0,
            "classification_source": "unit_test",
        })

        pack = calculate_dynamic_cap_v2(
            stock_id="TEST",
            stock_name="測試股",
            current_price=300,
            info={"marketCap": 300_000_000_000},
            industry_profile=profile,
            gross_margin=0.22,
            operating_margin=0.09,
            roe=0.18,
            debt_to_equity=0.45,
            revenue_yoy=0.30,
            free_cash_flow=1_000_000_000,
            ttm_eps=8.0,
            system_forward_eps=10.0,
            consensus_forward_eps=10.5,
            pb_ratio=3.0,
        )

        self.assertTrue(pack.get("available"))
        self.assertEqual(pack.get("valuation_mode"), profile.get("primary_valuation"))
        self.assertGreater(pack.get("final_cap"), 0)
        self.assertGreaterEqual(pack.get("final_cap"), pack.get("floor_cap"))
        self.assertLessEqual(pack.get("final_cap"), pack.get("hard_ceiling_cap"))
        self.assertEqual(pack.get("model_version"), "Dynamic Cap 2.0 calibration 17-C-23")
        self.assertFalse(pack.get("report").empty)

    def test_dynamic_cap_market_condition_can_expand_hard_ceiling(self):
        profile = dict(industry_taxonomy.get_taxonomy("PROBE_AI_ASIC"))
        profile.update({
            "model_key": "PROBE_AI_ASIC",
            "model_label": profile.get("display_name", "AI ASIC 探針卡"),
            "themes": ["AI ASIC", "探針卡"],
            "classification_confidence_factor": 1.0,
            "classification_source": "unit_test",
        })

        pack = calculate_dynamic_cap_v2(
            stock_id="TEST",
            stock_name="測試探針卡",
            current_price=1600,
            info={"marketCap": 250_000_000_000, "averageVolume": 8_000_000},
            industry_profile=profile,
            gross_margin=0.56,
            operating_margin=0.34,
            roe=0.32,
            debt_to_equity=0.20,
            revenue_yoy=0.70,
            free_cash_flow=2_000_000_000,
            ttm_eps=4.0,
            consensus_forward_eps=10.0,
            pb_ratio=12.0,
        )

        adjustment = pack.get("market_condition_hard_adjustment") or {}
        self.assertTrue(adjustment.get("adjusted"))
        self.assertEqual(pack.get("structural_hard_ceiling_cap"), 115.0)
        self.assertGreater(pack.get("hard_ceiling_cap"), pack.get("structural_hard_ceiling_cap"))
        self.assertLessEqual(pack.get("final_cap"), pack.get("hard_ceiling_cap"))

    def test_dynamic_cap_market_condition_does_not_expand_hard_ceiling_when_data_is_weak(self):
        profile = dict(industry_taxonomy.get_taxonomy("PROBE_AI_ASIC"))
        profile.update({
            "model_key": "PROBE_AI_ASIC",
            "model_label": profile.get("display_name", "AI ASIC 探針卡"),
            "themes": ["AI ASIC", "探針卡"],
            "classification_confidence_factor": 1.0,
            "classification_source": "unit_test",
        })

        warnings = [
            {"規則": "EPS 分歧", "嚴重度": "warning", "警告文字": "EPS 差距過大"},
            {"規則": "Forward P/E 分歧", "嚴重度": "warning", "警告文字": "倍率差距過大"},
            {"規則": "YoY 分歧", "嚴重度": "warning", "警告文字": "營收口徑不同"},
        ]
        pack = calculate_dynamic_cap_v2(
            stock_id="TEST",
            stock_name="測試探針卡",
            current_price=1600,
            info={"marketCap": 250_000_000_000, "averageVolume": 8_000_000},
            industry_profile=profile,
            gross_margin=0.56,
            operating_margin=0.34,
            roe=0.32,
            debt_to_equity=0.20,
            revenue_yoy=0.70,
            free_cash_flow=2_000_000_000,
            ttm_eps=4.0,
            consensus_forward_eps=10.0,
            pb_ratio=12.0,
            divergence_warnings=warnings,
        )

        adjustment = pack.get("market_condition_hard_adjustment") or {}
        self.assertFalse(adjustment.get("adjusted"))
        self.assertEqual(pack.get("structural_hard_ceiling_cap"), 115.0)
        self.assertEqual(pack.get("hard_ceiling_cap"), 115.0)

    def test_forward_eps_tiered_valuation_calculates_base_soft_hard(self):
        result = build_forward_eps_tiered_valuation_report(
            current_price=100,
            broker_target_avg=120,
            broker_target_high=150,
            broker_target_low=90,
            ttm_eps=4,
            fy1_eps=5,
            fy2_eps=6,
            fy3_eps=7,
            fy1_year=2026,
            fy2_year=2027,
            fy3_year=2028,
            base_cap=18,
            soft_ceiling=22,
            hard_ceiling=28,
            current_date="2026-10-15",
        )
        report = result["report"]

        self.assertEqual(len(report), 4)
        fy1 = report[report["EPS口徑"] == "FY1 EPS"].iloc[0]
        self.assertEqual(fy1["基礎估值"], 90)
        self.assertEqual(fy1["樂觀估值"], 110)
        self.assertEqual(fy1["極限估值"], 140)
        self.assertEqual(result["summary"]["base_cap"], 18)
        self.assertEqual(result["summary"]["soft_cap"], 22)
        self.assertEqual(result["summary"]["hard_cap"], 28)
        self.assertEqual(result["summary"]["fy_sequence_text"], "FY1=2026E / FY2=2027E / FY3=2028E")
        self.assertIn("FY2 作主要前瞻參考", result["summary"]["fy_calendar_ui_notice"])

    def test_infer_pricing_horizon_detects_fy2_pricing(self):
        result = infer_pricing_horizon(
            price=150,
            ttm_eps=3,
            fy1_eps=5,
            fy2_eps=9,
            fy3_eps=10,
            base_pe=18,
            soft_pe=22,
            hard_pe=28,
        )

        self.assertEqual(result["code"], "FY2_PRICED")
        self.assertTrue(result["is_future_priced"])
        self.assertIn("新買", result["decision_rule"])

    def test_infer_pricing_horizon_detects_fy2_soft_pricing(self):
        result = infer_pricing_horizon(
            price=1000,
            ttm_eps=13.12,
            fy1_eps=14.29,
            fy2_eps=28.24,
            fy3_eps=None,
            base_pe=24,
            soft_pe=42,
            hard_pe=55,
        )

        self.assertEqual(result["code"], "FY2_SOFT_PRICED")
        self.assertEqual(result["rank"], 2)
        self.assertIn("soft", result["explanation"])
        self.assertIn("降權", result["decision_rule"])

    def test_infer_pricing_horizon_keeps_fy1_soft_separate_from_fy2(self):
        result = infer_pricing_horizon(
            price=3040,
            ttm_eps=39.59,
            fy1_eps=68.29,
            fy2_eps=100.0,
            fy3_eps=None,
            base_pe=38,
            soft_pe=60,
            hard_pe=60,
        )

        self.assertEqual(result["code"], "FY1_SOFT_PRICED")
        self.assertEqual(result["rank"], 1)
        self.assertFalse(result["is_future_priced"])
        self.assertIn("不代表必須用 FY2", result["explanation"])

    def test_future_evidence_score_rewards_landing_but_penalizes_data_risk(self):
        strong = calculate_future_evidence_score(
            revenue_yoy=0.52,
            revenue_mom=0.08,
            gross_margin=0.42,
            operating_margin=0.22,
            roe=0.25,
            fy1_eps=5,
            fy2_eps=7,
            analyst_count=12,
            target_confidence={"rank": 5, "label": "高可信"},
        )
        weak = calculate_future_evidence_score(
            revenue_yoy=-0.05,
            revenue_mom=-0.12,
            gross_margin=0.12,
            operating_margin=0.03,
            roe=0.04,
            fy1_eps=5,
            fy2_eps=4,
            analyst_count=1,
            target_confidence={"rank": 1, "label": "低可信"},
            divergence_warnings=[{"嚴重度": "danger"}],
        )

        self.assertGreaterEqual(strong["score"], 80)
        self.assertEqual(strong["label"], "未來高度落地")
        self.assertLess(weak["score"], 40)
        self.assertEqual(weak["label"], "純題材或證據反轉")

    def test_forward_eps_tiered_summary_includes_pricing_horizon_and_future_evidence(self):
        result = build_forward_eps_tiered_valuation_report(
            current_price=150,
            ttm_eps=3,
            fy1_eps=5,
            fy2_eps=9,
            fy3_eps=10,
            base_cap=18,
            soft_ceiling=22,
            hard_ceiling=28,
            revenue_yoy=0.30,
            revenue_mom=0.05,
            gross_margin=0.35,
            operating_margin=0.18,
            roe=0.20,
            analyst_count=8,
            target_confidence={"rank": 4, "label": "中高可信"},
        )

        summary = result["summary"]
        self.assertEqual(summary["pricing_horizon_code"], "FY2_PRICED")
        self.assertIn("FY2", summary["pricing_horizon_label"])
        self.assertGreaterEqual(summary["future_evidence_score"], 60)
        self.assertIn("future_evidence", summary)

    def test_current_eps_valuation_prefers_latest_month_annualized_eps(self):
        result = build_multiple_context(
            target_pe_cap=20,
            suggested_cap=20,
            dynamic_cap_pack={
                "formula_cap": 18,
                "base_multiple": 18,
                "optimistic_cap": 22,
                "hard_ceiling_cap": 28,
            },
            industry_profile={},
            eff_f_eps=5,
            has_ai_fin_fetch=True,
            ai_f_eps_calc=5.5,
            ai_forward_eps_fy1=6,
            ai_forward_eps_fy2=7,
            ai_forward_eps_fy3=8,
            cap_adopted_forward_eps=6,
            sys_latest_quarter_eps=None,
            ai_latest_month_eps=1.5,
            ai_latest_quarter_eps=2.5,
            eff_t_eps=8,
            raw_ai_period="2026/04",
        )

        self.assertEqual(result["current_eps_raw"], 1.5)
        self.assertEqual(result["current_eps_for_valuation"], 18.0)
        self.assertEqual(result["current_target_price_est"], 324.0)
        self.assertEqual(result["current_eps_source"], "最新單月 EPS 年化")
        self.assertIn("×12 年化值", result["current_eps_source_detail"])
        self.assertIn("原始單月 EPS=1.50", result["current_eps_formula_note"])
        self.assertIn("年化 EPS=18.00", result["current_eps_formula_note"])

    def test_current_eps_valuation_prefers_latest_quarter_annualized_eps(self):
        result = build_multiple_context(
            target_pe_cap=20,
            suggested_cap=20,
            dynamic_cap_pack={
                "formula_cap": 18,
                "base_multiple": 18,
                "optimistic_cap": 22,
                "hard_ceiling_cap": 28,
            },
            industry_profile={},
            eff_f_eps=5,
            has_ai_fin_fetch=True,
            ai_f_eps_calc=5.5,
            ai_forward_eps_fy1=6,
            ai_forward_eps_fy2=7,
            ai_forward_eps_fy3=8,
            cap_adopted_forward_eps=6,
            sys_latest_quarter_eps=None,
            ai_latest_quarter_eps=2.5,
            eff_t_eps=8,
            raw_ai_period="2026Q1",
        )

        self.assertEqual(result["current_eps_raw"], 2.5)
        self.assertEqual(result["current_eps_for_valuation"], 10.0)
        self.assertEqual(result["current_target_price_est"], 180.0)
        self.assertEqual(result["current_eps_source"], "最新單季 EPS 年化")
        self.assertIn("×4 年化值", result["current_eps_source_detail"])
        self.assertIn("原始單季 EPS=2.50", result["current_eps_formula_note"])
        self.assertIn("年化 EPS=10.00", result["current_eps_formula_note"])
        self.assertEqual(result["current_eps_period"], "2026Q1")

    def test_run_rate_eps_uses_latest_two_quarters_without_replacing_current_eps(self):
        result = build_multiple_context(
            target_pe_cap=20,
            suggested_cap=20,
            dynamic_cap_pack={
                "formula_cap": 18,
                "base_multiple": 18,
                "optimistic_cap": 22,
                "hard_ceiling_cap": 28,
            },
            industry_profile={},
            eff_f_eps=10,
            has_ai_fin_fetch=True,
            ai_f_eps_calc=10,
            ai_forward_eps_fy1=12,
            ai_forward_eps_fy2=14,
            ai_forward_eps_fy3=16,
            cap_adopted_forward_eps=12,
            ai_latest_quarter_eps=2.5,
            ai_previous_quarter_eps=2.3,
            eff_t_eps=7,
            raw_ai_period="2026Q1",
        )

        self.assertEqual(result["current_eps_for_valuation"], 10.0)
        self.assertAlmostEqual(result["run_rate_2q_eps_annualized"], 9.6)
        self.assertAlmostEqual(result["run_rate_reference_eps"], 9.6)
        self.assertAlmostEqual(result["run_rate_2q_target_price"], 172.8)
        self.assertEqual(result["run_rate_label"], "獲利動能加速")

    def test_run_rate_eps_flags_single_quarter_overheat(self):
        result = build_multiple_context(
            target_pe_cap=20,
            suggested_cap=20,
            dynamic_cap_pack={"formula_cap": 18, "base_multiple": 18},
            industry_profile={},
            eff_f_eps=10,
            has_ai_fin_fetch=True,
            ai_f_eps_calc=10,
            ai_forward_eps_fy1=10,
            ai_forward_eps_fy2=None,
            ai_forward_eps_fy3=None,
            cap_adopted_forward_eps=10,
            ai_latest_quarter_eps=4,
            ai_previous_quarter_eps=2,
            eff_t_eps=8,
            raw_ai_period="2026Q1",
        )

        self.assertEqual(result["run_rate_label"], "單季過熱需確認")
        self.assertIn("一次性因素", result["run_rate_action"])

    def test_current_eps_valuation_falls_back_to_ttm_eps(self):
        result = build_multiple_context(
            target_pe_cap=20,
            suggested_cap=20,
            dynamic_cap_pack={"formula_cap": 18, "base_multiple": 18},
            industry_profile={},
            eff_f_eps=5,
            has_ai_fin_fetch=False,
            ai_f_eps_calc=None,
            ai_forward_eps_fy1=None,
            ai_forward_eps_fy2=None,
            ai_forward_eps_fy3=None,
            cap_adopted_forward_eps=5,
            sys_latest_quarter_eps=None,
            ai_latest_quarter_eps=None,
            eff_t_eps=8,
        )

        self.assertEqual(result["current_eps_raw"], 8.0)
        self.assertEqual(result["current_eps_for_valuation"], 8.0)
        self.assertEqual(result["current_target_price_est"], 144.0)
        self.assertEqual(result["current_eps_source"], "TTM EPS")
        self.assertIn("直接採 TTM EPS", result["current_eps_formula_note"])

    def test_forward_eps_period_mismatch_detects_system_eps_closer_to_fy2(self):
        result = detect_forward_eps_period_mismatch(
            system_forward_eps=135.21,
            fy1_eps=93.75,
            fy2_eps=131.10,
        )

        self.assertTrue(result["has_mismatch"])
        self.assertEqual(result["recommended_eps"], 93.75)
        self.assertIn("更接近 FY2", result["note"])

    def test_divergence_report_adds_l1_l5_data_quality_levels(self):
        warnings = [
            {"規則": "Forward EPS 年期錯位", "嚴重度": "warning", "警告文字": "系統 Forward EPS 更接近 FY2"},
            {"規則": "EPS 分歧", "嚴重度": "danger", "警告文字": "EPS 差距過大"},
            {"規則": "合理價分歧", "嚴重度": "danger", "警告文字": "合理價差距過大"},
        ]

        report = build_divergence_warning_report(warnings)
        summary = summarize_data_quality_levels(warnings)

        self.assertIn("資料等級", report.columns)
        self.assertEqual(report.iloc[0]["資料等級"], "L3")
        self.assertEqual(report.iloc[1]["資料等級"], "L4")
        self.assertEqual(summary["level"], "L5")

    def test_formula_valuation_is_downgraded_when_forward_eps_matches_fy2(self):
        result = build_multiple_context(
            target_pe_cap=36,
            suggested_cap=36,
            dynamic_cap_pack={
                "formula_cap": 36,
                "base_multiple": 36,
                "optimistic_cap": 55,
                "hard_ceiling_cap": 70,
            },
            industry_profile={},
            eff_f_eps=135.21,
            has_ai_fin_fetch=True,
            ai_f_eps_calc=93.75,
            ai_forward_eps_fy1=93.75,
            ai_forward_eps_fy2=131.10,
            ai_forward_eps_fy3=150.0,
            cap_adopted_forward_eps=93.75,
        )

        self.assertTrue(result["forward_eps_period_mismatch"]["has_mismatch"])
        self.assertAlmostEqual(result["sys_target_price_raw"], 4867.56)
        self.assertAlmostEqual(result["sys_target_price_est"], 3375.0)
        self.assertEqual(result["formula_eps_for_calc"], 93.75)
        self.assertIn("FY1 EPS", result["formula_eps_source"])

    def test_final_signal_uses_unjudgeable_grade_only_for_critical_data_breaks(self):
        result = build_final_operation_signal(
            current_price=100,
            valuation_separation={"warning_count": 0, "danger_count": 0},
            divergence_warnings=[],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=18,
            peg=1.1,
            gross_margin=0.20,
            operating_margin=0.35,
        )

        self.assertEqual(result["signal"], "資料異常-不可判斷")
        self.assertEqual(result["data_grade_label"], "資料異常-不可判斷")
        self.assertIn("營益率高於毛利率", "；".join(result["reasons"]))

    def test_final_signal_downgrades_divergent_data_without_hard_stopping(self):
        result = build_final_operation_signal(
            current_price=100,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 1, "danger_count": 1},
            divergence_warnings=[{"嚴重度": "danger", "規則": "EPS 分歧"}],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=24,
            peg=1.2,
            roe=0.20,
            revenue_yoy=0.20,
            gross_margin=0.30,
            operating_margin=0.20,
        )

        self.assertEqual(result["signal"], "資料分歧-降權判斷")
        self.assertEqual(result["data_grade_label"], "資料分歧-降權判斷")
        self.assertEqual(result["data_quality_level"]["level"], "L4")
        self.assertIn("保守估值", result["advice"])

    def test_yoy_divergence_over_ten_points_blocks_buy_signal(self):
        warnings = build_divergence_warnings(
            system_yoy=0.1614,
            ai_yoy=-0.0062,
            stock_id="6789",
            stock_name="采鈺",
        )

        self.assertEqual(warnings[0]["規則"], "YoY 分歧")
        self.assertEqual(warnings[0]["嚴重度"], "danger")

        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 1, "danger_count": 1},
            divergence_warnings=warnings,
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=16,
            peg=0.9,
            roe=0.20,
            revenue_yoy=0.1614,
            gross_margin=0.30,
            operating_margin=0.20,
        )

        self.assertEqual(result["signal"], "資料分歧-降權判斷")
        self.assertNotEqual(result["signal"], "可買-小量分批")

    def test_final_signal_can_remain_small_batch_buy_with_light_data_warnings(self):
        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 1, "danger_count": 0},
            divergence_warnings=[{"嚴重度": "warning", "規則": "YoY 分歧"}],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=16,
            peg=0.9,
            roe=0.20,
            revenue_yoy=0.20,
            gross_margin=0.30,
            operating_margin=0.20,
        )

        self.assertEqual(result["signal"], "可買-小量分批")
        self.assertEqual(result["data_grade_label"], "觀望-資料待確認")
        self.assertIn("不可一次買滿", result["advice"])

    def test_final_signal_blocks_buy_when_fy2_priced_with_weak_evidence(self):
        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 0, "danger_count": 0},
            divergence_warnings=[],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=16,
            peg=0.9,
            roe=0.20,
            revenue_yoy=0.20,
            gross_margin=0.30,
            operating_margin=0.20,
            pricing_horizon={"code": "FY2_PRICED", "label": "FY2 先行定價", "explanation": "需 FY2 EPS 才能解釋", "decision_rule": "新買需降權"},
            future_evidence={"score": 35, "label": "純題材或證據反轉", "action": "不可用 FY2 支撐買進"},
        )

        self.assertEqual(result["signal"], "不建議")
        self.assertIn("未來證據不足", result["advice"])
        self.assertEqual(result["pricing_horizon_code"], "FY2_PRICED")

    def test_final_signal_downgrades_fy2_priced_buy_even_with_strong_evidence(self):
        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 0, "danger_count": 0},
            divergence_warnings=[],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=16,
            peg=0.9,
            roe=0.25,
            revenue_yoy=0.50,
            gross_margin=0.45,
            operating_margin=0.25,
            pricing_horizon={"code": "FY2_PRICED", "label": "FY2 先行定價", "explanation": "需 FY2 EPS 才能解釋", "decision_rule": "新買需降權"},
            future_evidence={"score": 85, "label": "未來高度落地", "action": "只可小部位或既有續抱"},
        )

        self.assertEqual(result["signal"], "資料分歧-降權判斷")
        self.assertIn("小部位", result["advice"])
        self.assertEqual(result["future_evidence_score"], 85)

    def test_final_signal_does_not_treat_fy1_soft_as_fy2_future_pricing(self):
        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 0, "danger_count": 0},
            divergence_warnings=[],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=24,
            peg=0.9,
            roe=0.20,
            revenue_yoy=0.20,
            gross_margin=0.30,
            operating_margin=0.20,
            pricing_horizon={"code": "FY1_SOFT_PRICED", "label": "FY1 樂觀定價", "explanation": "FY1 soft 可解釋", "decision_rule": "安全邊際不足"},
            future_evidence={"score": 35, "label": "證據不足", "action": "不可追價"},
        )

        self.assertEqual(result["pricing_horizon_code"], "FY1_SOFT_PRICED")
        self.assertNotIn("需 FY2", result["advice"])
        self.assertNotIn("FY2", "；".join(result["reasons"]))
        self.assertIn("FY1 樂觀區", "；".join(result["reasons"]))

    def test_final_signal_normalizes_legacy_fy1_soft_or_fy2_watch_code(self):
        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 0, "danger_count": 0},
            divergence_warnings=[],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=24,
            peg=0.9,
            roe=0.20,
            revenue_yoy=0.20,
            gross_margin=0.30,
            operating_margin=0.20,
            pricing_horizon={"code": "FY1_SOFT_OR_FY2_WATCH", "label": "FY1 樂觀 / FY2 觀察", "explanation": "舊版 code", "decision_rule": "舊版規則"},
            future_evidence={"score": 35, "label": "證據不足", "action": "不可追價"},
        )

        self.assertEqual(result["pricing_horizon_code"], "FY1_SOFT_PRICED")
        self.assertIn("FY1 樂觀定價", result["pricing_horizon_label"])
        self.assertNotIn("需 FY2", result["advice"])
        self.assertNotIn("FY2", "；".join(result["reasons"]))

    def test_final_signal_never_upgrades_buy_for_fy2_soft_priced(self):
        result = build_final_operation_signal(
            current_price=85,
            valuation_separation={"operable_low": 90, "operable_mid": 105, "operable_high": 120, "warning_count": 0, "danger_count": 0},
            divergence_warnings=[],
            target_confidence={"rank": 5},
            industry_profile={"pe_model_suitable": True},
            forward_pe=16,
            peg=0.9,
            roe=0.25,
            revenue_yoy=0.50,
            gross_margin=0.45,
            operating_margin=0.25,
            pricing_horizon={"code": "FY2_SOFT_PRICED", "label": "FY2 樂觀先行定價", "explanation": "需 FY2 soft 才能解釋", "decision_rule": "不得升級買進"},
            future_evidence={"score": 90, "label": "未來高度落地", "action": "續抱或回檔小量"},
        )

        self.assertNotEqual(result["signal"], "可買-小量分批")
        self.assertEqual(result["signal"], "資料分歧-降權判斷")
        self.assertIn("不得直接升級", result["advice"])
        self.assertIn("回檔小量", result["advice"])

    def test_margin_credit_summary_calculates_ratios_and_risk(self):
        df = pd.DataFrame({
            "date": pd.date_range("2026-05-01", periods=6, freq="B"),
            "stock_id": ["2330"] * 6,
            "MarginPurchaseBuy": [100, 120, 130, 140, 150, 160],
            "MarginPurchaseCashRepayment": [0, 0, 0, 0, 0, 0],
            "MarginPurchaseLimit": [5000] * 6,
            "MarginPurchaseSell": [50, 60, 70, 80, 90, 100],
            "MarginPurchaseTodayBalance": [1000, 1120, 1250, 1400, 1600, 1800],
            "MarginPurchaseYesterdayBalance": [950, 1000, 1120, 1250, 1400, 1600],
            "OffsetLoanAndShort": [0] * 6,
            "ShortSaleBuy": [0] * 6,
            "ShortSaleCashRepayment": [0] * 6,
            "ShortSaleLimit": [5000] * 6,
            "ShortSaleSell": [10, 20, 20, 30, 40, 50],
            "ShortSaleTodayBalance": [80, 90, 100, 120, 150, 180],
            "ShortSaleYesterdayBalance": [70, 80, 90, 100, 120, 150],
        })

        summary = build_margin_credit_summary(df, shares_outstanding=20_000_000)

        self.assertTrue(summary["available"])
        self.assertAlmostEqual(summary["margin_usage_ratio"], 0.36)
        self.assertAlmostEqual(summary["margin_to_shares_ratio"], 0.09)
        self.assertEqual(summary["margin_change_1d"], 200)
        self.assertEqual(summary["margin_change_5d"], 800)
        self.assertAlmostEqual(summary["short_margin_ratio"], 0.10)
        self.assertEqual(summary["risk_label"], "偏熱")
        self.assertFalse(summary["report"].empty)

    def test_monthly_revenue_yoy_replaces_yfinance_without_warning(self):
        monthly_rev_df = pd.DataFrame({
            "Month": ["2026-05"],
            "YoY": [71.62],
        })

        corrected_sys, corrected_ai, warnings = validate_and_correct_financial_metrics(
            {"rev_growth": 1.102, "gross_margin": 0.26, "operating_margin": 0.20, "debt_to_equity": 0.3},
            {"rev_growth": None},
            monthly_rev_df=monthly_rev_df,
            stock_id="3017",
            stock_name="奇鋐",
        )

        self.assertAlmostEqual(corrected_sys["rev_growth"], 0.7162)
        self.assertAlmostEqual(corrected_sys["revenue_yoy"], 0.7162)
        self.assertEqual(warnings, [])

    def test_ai_financial_json_validation_normalizes_and_blocks_bad_values(self):
        payload = {
            "forward_eps_fy1": "6.2",
            "forward_eps_fy2": "7.4",
            "forward_eps_fy3": "8.6",
            "gross_margin": "25.5",
            "operating_margin": "12.3",
            "roe": "18.0",
            "target_price_high": 90,
            "target_price_avg": 120,
            "target_price_low": 150,
            "industry_classification": {
                "suggested_primary_taxon": "NOT_A_REAL_TAXON",
                "confidence": "medium",
                "suggested_themes": "AI伺服器",
            },
        }

        result = validate_ai_financial_json(payload, stock_id="TEST", stock_name="測試股")

        self.assertEqual(result["forward_eps_fy1"], 6.2)
        self.assertAlmostEqual(result["gross_margin"], 0.255)
        self.assertAlmostEqual(result["operating_margin"], 0.123)
        self.assertAlmostEqual(result["roe"], 0.18)
        self.assertEqual(result["target_price_high"], 150)
        self.assertEqual(result["target_price_avg"], 120)
        self.assertEqual(result["target_price_low"], 90)
        self.assertEqual(result["industry_classification"]["suggested_primary_taxon"], "GENERAL")
        self.assertTrue(result.get("_ai_validation_warnings"))


class PromptContextTests(unittest.TestCase):
    def test_etf_prompt_summary_includes_fast_and_ai_rows(self):
        summary = prompt_etf_panel_summary(
            etf_holders=[
                {"etf_code": "00999", "etf_name": "測試ETF", "weight": 3.456, "data_date": "2026-06-01", "source": "unit"},
            ],
            ai_etf_data={
                "etf_holders_ai": [
                    {"etf_code": "00888", "etf_name": "AI補查ETF", "weight": 1.2, "data_date": "2026-06-02", "source": "ai"},
                ],
                "summary": "AI 補查摘要",
            },
        )

        self.assertIn("快速ETF｜00999 測試ETF", summary)
        self.assertIn("持股=3.46%", summary)
        self.assertIn("AI ETF｜00888 AI補查ETF", summary)
        self.assertIn("AI ETF 摘要｜AI 補查摘要", summary)

    def test_chip_prompt_summary_uses_panel_state(self):
        summary = prompt_chip_panel_summary({
            "has_institutional_data": True,
            "f_10d": 1200,
            "t_10d": -300,
            "f_status": "連買",
            "t_status": "連賣",
            "trap_warning": "<div>籌碼警示文字</div>",
            "inst_str": "22.0%",
            "inst_eval": "穩定認可",
            "insider_str": "18.0%",
            "in_eval": "相對穩健",
            "share_capital": 2_500_000_000,
            "cap_type": "中小型",
            "driver": "投信主導",
            "driver_desc": "股本輕",
            "margin_credit": {
                "available": True,
                "risk_label": "偏熱",
                "latest_date": "2026-06-08",
                "margin_balance": 1800,
                "margin_usage_ratio": 0.36,
                "margin_to_shares_ratio": 0.09,
                "margin_change_5d": 800,
                "margin_change_5d_pct": 0.80,
                "margin_change_20d": 1000,
                "margin_change_20d_pct": 1.25,
                "short_margin_ratio": 0.10,
                "risk_note": "融資籌碼已有升溫跡象",
            },
        })

        self.assertIn("外資近10日淨買賣: 1200", summary)
        self.assertIn("投信近10日淨買賣: -300", summary)
        self.assertIn("外資+投信近10日合計: 900", summary)
        self.assertIn("籌碼警示文字", summary)
        self.assertIn("融資融券風險: 等級=偏熱", summary)
        self.assertIn("融資使用率=36.00%", summary)
        self.assertIn("融資占股本=9.00%", summary)
        self.assertIn("股本/控盤類型: 25.0 億｜中小型｜投信主導", summary)

    def test_model_library_feedback_prompt_includes_profile_context(self):
        summary = prompt_model_library_feedback_request({
            "primary_taxon": "AI_TEST_EQUIPMENT",
            "model_label": "AI 測試設備",
            "hybrid_taxons_text": "ADVANCED_PACKAGING 20%",
            "hybrid_mixed_caps_text": "base 25 / floor 18 / soft 35 / hard 45",
            "classification_source": "stock_mapping.py",
            "classification_confidence": "high",
            "soft_ceiling_pe": 35,
            "hard_ceiling_pe": 45,
        })
        gap_rules = prompt_model_gap_trigger_conditions()

        self.assertIn("目前 primary_taxon: AI_TEST_EQUIPMENT", summary)
        self.assertIn("目前 hybrid_taxons / 權重: ADVANCED_PACKAGING 20%", summary)
        self.assertIn("主模型 soft / hard ceiling: 35 / 45", summary)
        self.assertIn("primary_taxon_review", summary)
        self.assertIn("不可因單次股價上漲就建議調高模型", summary)
        self.assertIn("啟動模型落差診斷", gap_rules)

    def test_prompt_peg_layers_include_current_eps_valuation(self):
        summary = prompt_peg_valuation_layers(
            system_eps=5,
            system_eps_raw=7,
            system_raw_price=126,
            formula_eps_source="FY1 EPS（系統 Forward EPS 疑似 FY2，已降權）",
            forward_eps_mismatch_note="系統 Forward EPS 更接近 FY2",
            current_eps=10,
            current_eps_raw=2.5,
            current_eps_source="最新單季 EPS 年化",
            current_eps_formula_note="原始單季 EPS=2.50；年化 EPS=10.00",
            current_eps_period="2026Q1",
            current_price=180,
            run_rate_1q_eps=10,
            run_rate_2q_eps=9.6,
            run_rate_reference_eps=9.6,
            run_rate_1q_price=180,
            run_rate_2q_price=172.8,
            run_rate_reference_price=172.8,
            run_rate_label="獲利動能加速",
            run_rate_action="近二季年化高於 TTM",
            fy1_eps=6,
            fy1_year="2026",
            fy2_year="2027",
            fy3_year="2028",
            formula_cap=18,
            base_cap=18,
            soft_cap=22,
            hard_cap=28,
            system_price=90,
            fy1_base_price=108,
            fy1_soft_price=132,
            fy1_hard_price=168,
            current_date="2026-10-15",
        )

        self.assertIn("1-1. 目前估值", summary)
        self.assertIn("1-2. Run-rate EPS 動能估值", summary)
        self.assertIn("近二季年化EPS=9.60", summary)
        self.assertIn("不取代 TTM", summary)
        self.assertIn("最新單季 EPS 年化", summary)
        self.assertIn("原始EPS=2.50", summary)
        self.assertIn("計算=原始單季 EPS=2.50；年化 EPS=10.00", summary)
        self.assertIn("目前實際獲利支撐度", summary)
        self.assertIn("系統原始公式價=126.0元", summary)
        self.assertIn("系統 Forward EPS 更接近 FY2", summary)
        self.assertIn("目前台北時間月份=10月", summary)
        self.assertIn("FY1=2026E / FY2=2027E / FY3=2028E", summary)
        self.assertIn("FY2 可作主要前瞻參考", summary)

    def test_eps_adoption_summary_includes_current_valuation_price(self):
        summary = prompt_eps_adoption_sync_summary(
            sys_forward_eps_system_val=5,
            eff_f_eps_val=5,
            current_eps_for_valuation_val=10,
            current_eps_raw_val=2.5,
            current_eps_source_val="最新單季 EPS 年化",
            current_eps_formula_note_val="原始單季 EPS=2.50；年化 EPS=10.00",
            current_eps_period_val="2026Q1",
            formula_pe_cap_val=18,
            sys_target_price_est_val=90,
            current_target_price_est_val=180,
            run_rate_1q_eps_val=10,
            run_rate_2q_eps_val=9.6,
            run_rate_reference_eps_val=9.6,
            run_rate_1q_target_price_val=180,
            run_rate_2q_target_price_val=172.8,
            run_rate_reference_target_price_val=172.8,
            run_rate_label_val="獲利動能加速",
            run_rate_action_val="近二季年化高於 TTM",
        )

        self.assertIn("目前估值 EPS", summary)
        self.assertIn("計算=原始單季 EPS=2.50；年化 EPS=10.00", summary)
        self.assertIn("Run-rate EPS 動能", summary)
        self.assertIn("Run-rate參考=172.8元", summary)
        self.assertIn("目前估值=180.0元", summary)
        self.assertIn("最新單季 EPS 年化", summary)

    def test_technical_suffix_respects_mode_and_builds_summary(self):
        hist = pd.DataFrame({
            "Open": [100 + i for i in range(80)],
            "High": [102 + i for i in range(80)],
            "Low": [98 + i for i in range(80)],
            "Close": [101 + i for i in range(80)],
            "Volume": [1000 + i * 10 for i in range(80)],
        })

        self.assertEqual(prompt_technical_suffix("不加入技術面", hist=hist, curr_p=180), "")

        summary = prompt_technical_suffix("加入技術面摘要與線圖輔助規則", hist=hist, curr_p=180)
        self.assertIn("技術面與進出場節奏", summary)
        self.assertIn("收盤價與均線", summary)
        self.assertIn("KD 狀態", summary)
        self.assertIn("技術線圖輔助規則", summary)
        self.assertIn("不可覆蓋", summary)


class _FakePanelContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakePromptPackStreamlit:
    def __init__(self, radio_values):
        self.radio_values = radio_values
        self.expander_calls = []
        self.radio_calls = []
        self.caption_calls = []
        self.text_area_calls = []

    def expander(self, label, expanded=False):
        self.expander_calls.append({"label": label, "expanded": expanded})
        return _FakePanelContext()

    def radio(self, label, options, horizontal=False, key=None):
        self.radio_calls.append({"label": label, "options": list(options), "horizontal": horizontal, "key": key})
        return self.radio_values.get(label, options[0])

    def caption(self, text):
        self.caption_calls.append(text)

    def text_area(self, label, value, height=None, label_visibility=None, key=None):
        self.text_area_calls.append({
            "label": label,
            "value": value,
            "height": height,
            "label_visibility": label_visibility,
            "key": key,
        })


class _FakePromptPackComponents:
    def __init__(self):
        self.html_calls = []

    def html(self, body, height=None):
        self.html_calls.append({"body": body, "height": height})


class _FakePanelStreamlit:
    def __init__(self, *, session_state=None, button_values=None):
        self.session_state = _SessionState(session_state or {})
        self.button_values = button_values or {}
        self.columns_calls = []
        self.expander_calls = []
        self.markdown_calls = []
        self.caption_calls = []
        self.warning_calls = []
        self.info_calls = []
        self.error_calls = []
        self.success_calls = []
        self.write_calls = []
        self.dataframe_calls = []
        self.button_calls = []
        self.spinner_calls = []
        self.json_calls = []
        self.code_calls = []
        self.rerun_called = False
        self.stop_called = False

    def columns(self, spec):
        self.columns_calls.append(spec)
        count = spec if isinstance(spec, int) else len(spec)
        return [_FakePanelContext() for _ in range(count)]

    def expander(self, label, expanded=False):
        self.expander_calls.append({"label": label, "expanded": expanded})
        return _FakePanelContext()

    def spinner(self, text):
        self.spinner_calls.append(text)
        return _FakePanelContext()

    def button(self, label, **kwargs):
        self.button_calls.append({"label": label, **kwargs})
        if kwargs.get("disabled"):
            return False
        key = kwargs.get("key")
        return bool(self.button_values.get(key, self.button_values.get(label, False)))

    def markdown(self, text, **kwargs):
        self.markdown_calls.append({"text": text, **kwargs})

    def caption(self, text):
        self.caption_calls.append(text)

    def warning(self, text):
        self.warning_calls.append(text)

    def info(self, text):
        self.info_calls.append(text)

    def error(self, text):
        self.error_calls.append(text)

    def success(self, text):
        self.success_calls.append(text)

    def write(self, value):
        self.write_calls.append(value)

    def dataframe(self, data, **kwargs):
        self.dataframe_calls.append({"data": data, **kwargs})

    def json(self, value):
        self.json_calls.append(value)

    def code(self, body, language=None):
        self.code_calls.append({"body": body, "language": language})

    def rerun(self):
        self.rerun_called = True

    def stop(self):
        self.stop_called = True
        raise RuntimeError("streamlit stop called")


class UIRegressionTests(unittest.TestCase):
    def _render_prompt_pack_with_fakes(self, *, prompt_mode, technical_mode, suffix_text):
        from ui_panels import prompt_pack

        fake_st = _FakePromptPackStreamlit({
            "提示詞版本": prompt_mode,
            "技術面打包選項": technical_mode,
        })
        fake_components = _FakePromptPackComponents()
        suffix_calls = []

        def build_suffix(mode):
            suffix_calls.append(mode)
            return suffix_text

        original_st = prompt_pack.st
        original_components = prompt_pack.components
        try:
            prompt_pack.st = fake_st
            prompt_pack.components = fake_components
            prompt_pack.render_prompt_pack_panel(
                curr_id="2330",
                buy_decision_prompt="BUY_PROMPT",
                research_prompt="RESEARCH_PROMPT",
                build_technical_suffix=build_suffix,
            )
        finally:
            prompt_pack.st = original_st
            prompt_pack.components = original_components

        return fake_st, fake_components, suffix_calls

    def test_prompt_pack_panel_renders_buy_prompt_without_technical_suffix(self):
        fake_st, fake_components, suffix_calls = self._render_prompt_pack_with_fakes(
            prompt_mode="買進決策版（精簡，建議平常使用）",
            technical_mode="不加入技術面",
            suffix_text="",
        )

        self.assertEqual(suffix_calls, ["不加入技術面"])
        self.assertEqual(fake_st.expander_calls[0]["label"], "📋 點此複製【打包提示詞】至 Gemini Advanced 或 ChatGPT 發問")
        self.assertEqual(fake_st.text_area_calls[0]["value"], "BUY_PROMPT")
        self.assertIn("copy_prompt_textarea_2330_buy_", fake_st.text_area_calls[0]["key"])
        self.assertIn(json.dumps("BUY_PROMPT", ensure_ascii=False), fake_components.html_calls[0]["body"])
        self.assertEqual(fake_components.html_calls[0]["height"], 105)

    def test_prompt_pack_panel_appends_technical_suffix_to_research_prompt(self):
        fake_st, fake_components, suffix_calls = self._render_prompt_pack_with_fakes(
            prompt_mode="研究完整版（完整，適合深度分析）",
            technical_mode="加入技術面摘要 + 技術線圖輔助規則",
            suffix_text="TECH_SUFFIX",
        )

        selected_prompt = "RESEARCH_PROMPT\n\nTECH_SUFFIX"
        self.assertEqual(suffix_calls, ["加入技術面摘要 + 技術線圖輔助規則"])
        self.assertEqual(fake_st.text_area_calls[0]["value"], selected_prompt)
        self.assertIn("copy_prompt_textarea_2330_research_", fake_st.text_area_calls[0]["key"])
        self.assertIn(json.dumps(selected_prompt, ensure_ascii=False), fake_components.html_calls[0]["body"])
        self.assertNotIn("BUY_PROMPT", fake_st.text_area_calls[0]["value"])

    def test_financial_panel_m10_margin_summary_renders_with_fake_streamlit(self):
        from ui_panels import financials

        fake_st = _FakePanelStreamlit()
        summary = {
            "available": True,
            "status": "usable",
            "status_label": "可納入品質係數",
            "category_name": "半導體｜晶圓代工 / HPC / 先進製程",
            "margin_quality": "A",
            "margin_rule_label": "高營益率 cap",
            "base_gross_margin_pct": 45,
            "gross_margin_low_pct": 35,
            "gross_margin_high_pct": 60,
            "base_operating_margin_pct": 35,
            "operating_margin_low_pct": 20,
            "operating_margin_high_pct": 50,
            "usage_label": "可納入 Dynamic Cap 品質係數",
        }

        original_st = financials.st
        try:
            financials.st = fake_st
            financials._render_m10_margin_benchmark_summary(summary)
            report = financials._build_m10_margin_benchmark_report(summary)
        finally:
            financials.st = original_st

        markdown_text = "\n".join(call["text"] for call in fake_st.markdown_calls)
        self.assertIn("M10 margin benchmark", markdown_text)
        self.assertIn("可納入品質係數", markdown_text)
        self.assertFalse(report.empty)
        self.assertIn("營益率 base / low / high", report["項目"].tolist())

    def test_stock_header_panel_renders_title_classification_and_summary(self):
        from ui_panels import stock_header

        fake_st = _FakePanelStreamlit(session_state={
            "ai_fetched_financials": {
                "2330": {"_stock_id": "2330", "forward_eps": 45.0},
            },
        })
        captured = {}
        profile = {
            "model_label": "晶圓代工 / HPC",
            "themes_text": "AI, HPC",
            "classification_source": "stock_mapping.py",
            "classification_needs_manual_review": False,
            "pe_trap_warning": False,
            "pe_model_suitable": True,
        }

        def fake_get_industry_profile(curr_id, stock_name, sector_disp, industry, ai_financials=None):
            captured.update({
                "curr_id": curr_id,
                "stock_name": stock_name,
                "sector_disp": sector_disp,
                "industry": industry,
                "ai_financials": ai_financials,
            })
            return profile

        original_st = stock_header.st
        original_get_watchlist = stock_header.get_watchlist
        original_toggle_watchlist = stock_header.toggle_watchlist
        original_get_industry_profile = stock_header.get_industry_valuation_profile
        original_translate = stock_header.translate_to_zh
        try:
            stock_header.st = fake_st
            stock_header.get_watchlist = lambda: []
            stock_header.toggle_watchlist = lambda *args, **kwargs: None
            stock_header.get_industry_valuation_profile = fake_get_industry_profile
            stock_header.translate_to_zh = lambda text: "中文公司簡介"
            sector_disp, rendered_profile = stock_header.render_stock_header_panel(
                curr_id="2330",
                stock_name="台積電",
                info={
                    "sector": "科技業",
                    "industry": "半導體",
                    "longBusinessSummary": "English business summary",
                },
            )
        finally:
            stock_header.st = original_st
            stock_header.get_watchlist = original_get_watchlist
            stock_header.toggle_watchlist = original_toggle_watchlist
            stock_header.get_industry_valuation_profile = original_get_industry_profile
            stock_header.translate_to_zh = original_translate

        markdown_text = "\n".join(call["text"] for call in fake_st.markdown_calls)
        self.assertEqual(sector_disp, "科技業")
        self.assertIs(rendered_profile, profile)
        self.assertEqual(captured["ai_financials"]["forward_eps"], 45.0)
        self.assertEqual(fake_st.button_calls[0]["label"], "☆ 加入自選")
        self.assertIn("台積電 (2330)", markdown_text)
        self.assertIn("估值模型：晶圓代工 / HPC", markdown_text)
        self.assertIn("題材標籤：AI, HPC", markdown_text)
        self.assertIn("分類來源：stock_mapping.py", markdown_text)
        self.assertEqual(fake_st.expander_calls[0]["label"], "📖 查看公司詳細營業項目簡介 (自動英翻中)")
        self.assertEqual(fake_st.write_calls, ["中文公司簡介"])

    def test_etf_panel_renders_fast_and_ai_holder_tables(self):
        from ui_panels import etf

        fast_rows = [{
            "etf_name": "元大台灣50",
            "etf_code": "0050",
            "weight": 7.123,
            "data_date": "2026-06-09",
            "source": "Yahoo",
        }]
        ai_rows = [{
            "etf_name": "主動統一台股增長",
            "etf_code": "00981A",
            "weight": 1.5,
            "data_date": "2026-06-09",
            "source": "投信公告",
            "data_type": "AI交叉補查",
        }]
        fake_st = _FakePanelStreamlit(session_state={
            "api_key": "TEST_KEY",
            "ai_etf_holders": {
                "2330": {
                    "etf_holders_ai": ai_rows,
                    "summary": "已交叉查詢主動式 ETF。",
                },
            },
        })

        original_st = etf.st
        original_get_stock_etf_holders = etf.get_stock_etf_holders
        try:
            etf.st = fake_st
            etf.get_stock_etf_holders = lambda curr_id, stock_name: fast_rows
            returned_rows = etf.render_etf_exposure_panel(curr_id="2330", stock_name="台積電")
        finally:
            etf.st = original_st
            etf.get_stock_etf_holders = original_get_stock_etf_holders

        self.assertEqual(returned_rows, fast_rows)
        self.assertEqual(len(fake_st.dataframe_calls), 2)
        fast_df = fake_st.dataframe_calls[0]["data"]
        ai_df = fake_st.dataframe_calls[1]["data"]
        self.assertEqual(fast_df.iloc[0]["ETF名稱"], "元大台灣50")
        self.assertEqual(fast_df.iloc[0]["持股比例"], "7.12%")
        self.assertEqual(ai_df.iloc[0]["代號"], "00981A")
        self.assertEqual(ai_df.iloc[0]["資料性質"], "AI交叉補查")
        self.assertEqual(fake_st.button_calls[0]["key"], "ai_etf_lookup_2330")
        self.assertFalse(fake_st.button_calls[0]["disabled"])
        self.assertTrue(any("AI 摘要：已交叉查詢主動式 ETF。" == text for text in fake_st.caption_calls))

    def test_chip_panel_renders_margin_credit_summary(self):
        from ui_panels import chips

        dates = pd.date_range("2026-05-01", periods=6, freq="B")
        inst_df = pd.DataFrame(
            {"Foreign": [100, 120, 80, 90, 110, 130], "Trust": [10, 20, 30, 40, 50, 60]},
            index=dates,
        )
        margin_df = pd.DataFrame({
            "date": dates,
            "stock_id": ["2330"] * 6,
            "MarginPurchaseBuy": [100, 120, 130, 140, 150, 160],
            "MarginPurchaseCashRepayment": [0, 0, 0, 0, 0, 0],
            "MarginPurchaseLimit": [5000] * 6,
            "MarginPurchaseSell": [50, 60, 70, 80, 90, 100],
            "MarginPurchaseTodayBalance": [1000, 1120, 1250, 1400, 1600, 1800],
            "MarginPurchaseYesterdayBalance": [950, 1000, 1120, 1250, 1400, 1600],
            "OffsetLoanAndShort": [0] * 6,
            "ShortSaleBuy": [0] * 6,
            "ShortSaleCashRepayment": [0] * 6,
            "ShortSaleLimit": [5000] * 6,
            "ShortSaleSell": [10, 20, 20, 30, 40, 50],
            "ShortSaleTodayBalance": [80, 90, 100, 120, 150, 180],
            "ShortSaleYesterdayBalance": [70, 80, 90, 100, 120, 150],
        })
        fake_st = _FakePanelStreamlit(session_state={"finmind_key": "TEST_TOKEN"})

        original_st = chips.st
        original_get_inst_data = chips.get_inst_data
        original_get_margin_credit_data = chips.get_margin_credit_data
        try:
            chips.st = fake_st
            chips.get_inst_data = lambda curr_id, fm_key="": inst_df
            chips.get_margin_credit_data = lambda curr_id, fm_key="": margin_df
            result = chips.render_chip_panels(
                curr_id="2330",
                info={"sharesOutstanding": 20_000_000, "heldPercentInsiders": 0.18, "heldPercentInstitutions": 0.22},
                ai_shares=None,
                eff_eg=0.20,
            )
        finally:
            chips.st = original_st
            chips.get_inst_data = original_get_inst_data
            chips.get_margin_credit_data = original_get_margin_credit_data

        markdown_text = "\n".join(call["text"] for call in fake_st.markdown_calls)
        self.assertTrue(result["margin_credit"]["available"])
        self.assertEqual(result["margin_credit"]["risk_label"], "偏熱")
        self.assertIn("信用交易風險", markdown_text)
        self.assertIn("融資使用率", markdown_text)
        self.assertEqual(len(fake_st.dataframe_calls), 1)

    def test_financial_audit_control_renders_existing_ai_snapshot(self):
        from ui_panels import financials

        ai_snapshot = {
            "_stock_id": "2330",
            "_stock_name": "台積電",
            "model_used": "Gemini 3.1 Pro Preview (付費版)",
            "forward_eps": 45.0,
            "_ai_validation_warnings": ["target_price_low 已自動排序"],
            "_ai_validation_status": "AI 欄位已校正",
        }
        fake_st = _FakePanelStreamlit(session_state={
            "api_key": "",
            "ai_fetched_financials": {"2330": dict(ai_snapshot)},
        })

        original_st = financials.st
        try:
            financials.st = fake_st
            temp_ai_fin, has_ai_fin_fetch = financials.render_ai_financial_audit_control(
                curr_id="2330",
                stock_name="台積電",
            )
        finally:
            financials.st = original_st

        markdown_text = "\n".join(call["text"] for call in fake_st.markdown_calls)
        self.assertTrue(has_ai_fin_fetch)
        self.assertEqual(temp_ai_fin["forward_eps"], 45.0)
        self.assertEqual(fake_st.button_calls[0]["label"], "🪄 啟動 AI 全方位校對與補齊財報")
        self.assertTrue(fake_st.button_calls[0]["disabled"])
        self.assertEqual(fake_st.button_calls[1]["key"], "toggle_ai_raw_btn_2330")
        self.assertFalse(fake_st.session_state["show_ai_raw_panel_2330"])
        self.assertIn("驅動核心", markdown_text)
        self.assertIn("Gemini 3.1 Pro Preview", markdown_text)
        self.assertTrue(any("AI 財報 JSON 已觸發合理性校驗" in text for text in fake_st.warning_calls))

    def test_financial_candidate_review_panel_updates_status(self):
        from ui_panels import financials

        candidates = build_financial_candidate_data(
            {"ttm_eps": 42.0, "_ai_source_trace": {"ttm_eps": {"source": "公開資訊觀測站"}}},
            stock_id="2330",
            stock_name="台積電",
            retrieved_at="2026-06-18T15:00:00",
        )
        candidate = candidates[0]
        safe_key = re.sub(r"[^A-Za-z0-9_]+", "_", candidate["candidate_id"])
        ai_snapshot = {
            "_stock_id": "2330",
            "_stock_name": "台積電",
            "model_used": "Gemini 3.1 Pro Preview (付費版)",
            "ttm_eps": 42.0,
            "_candidate_data": candidates,
        }
        fake_st = _FakePanelStreamlit(
            session_state={
                "api_key": "",
                "show_ai_raw_panel_2330": True,
                "ai_fetched_financials": {"2330": dict(ai_snapshot)},
                "financial_candidate_reviews": {},
            },
            button_values={
                f"candidate_review_2330_{safe_key}_accepted": True,
            },
        )
        updates = []

        def fake_update(**kwargs):
            updates.append(kwargs)
            return {
                "stock_id": kwargs["stock_id"],
                "candidate_id": kwargs["candidate_id"],
                "review_status": kwargs["review_status"],
                "decision_note": kwargs["decision_note"],
            }

        original_st = financials.st
        original_load_cache = financials.load_financial_candidate_review_cache
        original_update = financials.update_financial_candidate_review
        try:
            financials.st = fake_st
            financials.load_financial_candidate_review_cache = lambda *args, **kwargs: {"version": "test", "updated_at": "", "reviews": {}}
            financials.update_financial_candidate_review = fake_update
            temp_ai_fin, has_ai_fin_fetch = financials.render_ai_financial_audit_control(
                curr_id="2330",
                stock_name="台積電",
            )
        finally:
            financials.st = original_st
            financials.load_financial_candidate_review_cache = original_load_cache
            financials.update_financial_candidate_review = original_update

        self.assertTrue(has_ai_fin_fetch)
        self.assertEqual(updates[0]["review_status"], "accepted")
        self.assertTrue(fake_st.rerun_called)
        self.assertIn("審核狀態", fake_st.dataframe_calls[0]["data"].columns)
        review_key = f"2330::{candidate['candidate_id']}"
        self.assertEqual(fake_st.session_state.financial_candidate_reviews[review_key]["review_status"], "accepted")
        self.assertEqual(temp_ai_fin["_candidate_data"][0]["review_status"], "accepted")


if __name__ == "__main__":
    unittest.main()
