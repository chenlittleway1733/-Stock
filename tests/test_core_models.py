import json
import re
import sys
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
import ui_context.financial_context as financial_context
from dynamic_cap_model import CALIBRATION_DEFAULTS, calculate_dynamic_cap_v2, get_dynamic_cap_version_info
from industry_model import get_industry_valuation_profile
from services import build_margin_credit_summary
from ui_context.prompt_context import (
    prompt_chip_panel_summary,
    prompt_etf_panel_summary,
    prompt_eps_adoption_sync_summary,
    prompt_model_gap_trigger_conditions,
    prompt_model_library_feedback_request,
    prompt_peg_valuation_layers,
    prompt_technical_suffix,
)
from ui_context.multiple_context import build_multiple_context
from utils import (
    build_field_source_priority_report,
    build_financial_quality_report,
    build_forward_eps_tiered_valuation_report,
    build_final_operation_signal,
    detect_forward_eps_period_mismatch,
    format_field_source_priority_for_prompt,
    source_priority_summary_for_field,
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
        self.assertEqual(profile.get("model_build_version"), "17-C-17")


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
        ]

        for info in (tax_info, cap_info):
            table = info["version_table"]
            orders = [row["order"] for row in table]
            self.assertGreaterEqual(len(table), 5)
            self.assertEqual(info["version"], "17-C-17")
            self.assertEqual(info["latest_stage"], "17-C-17")
            self.assertEqual(info["build_date"], "2026-06-09")
            self.assertEqual(table[-1]["stage"], info["latest_stage"])
            self.assertEqual(orders, sorted(orders))

        self.assertEqual([row["stage"] for row in tax_info["version_table"]], expected_taxonomy_stages)
        self.assertEqual([row["stage"] for row in cap_info["version_table"]], expected_dynamic_cap_stages)
        self.assertEqual(cap_info["engine_version"], "Dynamic Cap 2.0 calibration 17-C-17")

    def test_multiplier_tightening_stage_keeps_taxonomy_and_dynamic_cap_in_sync(self):
        expected_caps = {
            "IC_DESIGN_IP_ROYALTY": (45.0, 68.0, 82.0),
            "IC_DESIGN_ASIC_HIGH_VISIBILITY": (45.0, 65.0, 80.0),
            "OPTICAL_COMM_CPO_HIGH_VISIBILITY": (42.0, 65.0, 82.0),
            "IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY": (40.0, 62.0, 78.0),
            "SEMICAP_ADV_PACKAGING_CORE": (36.0, 55.0, 72.0),
            "THERMAL_LIQUID_CORE": (36.0, 55.0, 70.0),
            "SERVER_RAIL_HIGH_VISIBILITY": (36.0, 55.0, 70.0),
            "AI_CCL_HIGH_VISIBILITY": (34.0, 52.0, 65.0),
            "MEMORY_IP_AI": (30.0, 48.0, 60.0),
            "AI_SERVER_PCB_HIGH_VISIBILITY": (32.0, 48.0, 62.0),
            "HIGH_SPEED_CONNECTOR_CORE": (32.0, 48.0, 62.0),
            "SEMIMAT_ADVANCED_CONSUMABLES": (32.0, 48.0, 60.0),
            "POWER_MANAGEMENT_IC_DESIGN": (24.0, 36.0, 48.0),
            "OSAT_AI_HPC_TESTING": (26.0, 40.0, 52.0),
            "AI_DATACENTER_SWITCH": (34.0, 52.0, 68.0),
            "CONSUMER_TOURISM": (22.0, 32.0, 38.0),
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
            self.assertEqual(tax_profile.get("calibration_source"), "17-C-17 倍率寬鬆度收斂", taxon)

        max_tax_hard = max(
            float(profile["hard_ceiling_pe"])
            for profile in industry_taxonomy.INDUSTRY_TAXONOMY.values()
            if profile.get("hard_ceiling_pe") is not None
        )
        max_dyn_hard = max(
            float(profile["hard_ceiling_pe"])
            for profile in CALIBRATION_DEFAULTS.values()
            if profile.get("hard_ceiling_pe") is not None
        )
        self.assertLessEqual(max_tax_hard, 82.0)
        self.assertLessEqual(max_dyn_hard, 82.0)


class FieldSourcePriorityTests(unittest.TestCase):
    def test_field_source_priority_report_contains_core_adoption_rules(self):
        report = build_field_source_priority_report(["營收 YoY", "Forward EPS－FY1", "D/E"])

        self.assertEqual(len(report), 3)
        revenue = report[report["資料欄位"] == "營收 YoY"].iloc[0]
        fy1 = report[report["資料欄位"] == "Forward EPS－FY1"].iloc[0]
        de = report[report["資料欄位"] == "D/E"].iloc[0]

        self.assertIn("FinMind TaiwanStockMonthRevenue", revenue["來源優先序"])
        self.assertIn("yfinance revenueGrowth 只作診斷備註", revenue["採用規則"])
        self.assertIn("法人 FY1 年度共識 EPS", fy1["來源優先序"])
        self.assertIn("FY1 是前瞻 PEG 年度估值", fy1["採用規則"])
        self.assertIn("標準化成倍數", de["採用規則"])
        self.assertIn("D/E > 8", de["校驗/降權規則"])

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

    def test_financial_quality_report_includes_source_priority_column(self):
        report = build_financial_quality_report([
            {
                "field": "營收 YoY",
                "system_source": "FinMind 月營收優先；yfinance 備援",
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
        self.assertIn("FinMind TaiwanStockMonthRevenue", report.iloc[0]["來源優先序"])
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


class ValuationLogicTests(unittest.TestCase):
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
        self.assertEqual(pack.get("model_version"), "Dynamic Cap 2.0 calibration 17-C-17")
        self.assertFalse(pack.get("report").empty)

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
        self.assertEqual(result["current_eps_period"], "2026Q1")

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

    def test_forward_eps_period_mismatch_detects_system_eps_closer_to_fy2(self):
        result = detect_forward_eps_period_mismatch(
            system_forward_eps=135.21,
            fy1_eps=93.75,
            fy2_eps=131.10,
        )

        self.assertTrue(result["has_mismatch"])
        self.assertEqual(result["recommended_eps"], 93.75)
        self.assertIn("更接近 FY2", result["note"])

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
        self.assertIn("保守估值", result["advice"])

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
            current_eps_period="2026Q1",
            current_price=180,
            fy1_eps=6,
            formula_cap=18,
            base_cap=18,
            soft_cap=22,
            hard_cap=28,
            system_price=90,
            fy1_base_price=108,
            fy1_soft_price=132,
            fy1_hard_price=168,
        )

        self.assertIn("1-1. 目前估值", summary)
        self.assertIn("最新單季 EPS 年化", summary)
        self.assertIn("原始EPS=2.50", summary)
        self.assertIn("目前實際獲利支撐度", summary)
        self.assertIn("系統原始公式價=126.0元", summary)
        self.assertIn("系統 Forward EPS 更接近 FY2", summary)

    def test_eps_adoption_summary_includes_current_valuation_price(self):
        summary = prompt_eps_adoption_sync_summary(
            sys_forward_eps_system_val=5,
            eff_f_eps_val=5,
            current_eps_for_valuation_val=10,
            current_eps_raw_val=2.5,
            current_eps_source_val="最新單季 EPS 年化",
            current_eps_period_val="2026Q1",
            formula_pe_cap_val=18,
            sys_target_price_est_val=90,
            current_target_price_est_val=180,
        )

        self.assertIn("目前估值 EPS", summary)
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


if __name__ == "__main__":
    unittest.main()
