"""Multiple and annual valuation context builders for ui_main.render_main_page."""

from ui_common import *


def cap_float(value, default=None):
    try:
        return float(value) if value is not None else default
    except Exception:
        return default


def valuation_num(value):
    try:
        if value is None:
            return None
        value = float(value)
        if pd.isna(value) or value <= 0:
            return None
        return value
    except Exception:
        return None


def valuation_price(eps, cap):
    eps_value = valuation_num(eps)
    cap_value = valuation_num(cap)
    return eps_value * cap_value if eps_value is not None and cap_value is not None else None


def build_current_eps_valuation(
    *,
    ai_latest_quarter_eps=None,
    sys_latest_quarter_eps=None,
    eff_t_eps=None,
    formula_pe_cap=None,
    raw_ai_period=None,
):
    """Build current realized EPS valuation, preferring latest-quarter annualized EPS."""
    latest_quarter_eps = valuation_num(ai_latest_quarter_eps)
    source = "最新單季 EPS 年化"
    source_detail = "AI 最新單季 EPS"
    if latest_quarter_eps is None:
        latest_quarter_eps = valuation_num(sys_latest_quarter_eps)
        source_detail = "系統最新單季 EPS"

    if latest_quarter_eps is not None:
        current_eps_for_valuation = latest_quarter_eps * 4
        current_eps_raw = latest_quarter_eps
        period = raw_ai_period or "最新已抓取季度"
    else:
        current_eps_for_valuation = valuation_num(eff_t_eps)
        current_eps_raw = current_eps_for_valuation
        source = "TTM EPS"
        source_detail = "近四季已實現 EPS"
        period = "近四季 / 系統反推" if current_eps_for_valuation is not None else "未取得"

    return {
        "current_eps_raw": current_eps_raw,
        "current_eps_for_valuation": current_eps_for_valuation,
        "current_eps_source": source,
        "current_eps_source_detail": source_detail,
        "current_eps_period": period,
        "current_target_price_est": valuation_price(current_eps_for_valuation, formula_pe_cap),
    }


def fmt_price(value):
    value = valuation_num(value)
    return f"{value:.1f}元" if value is not None else "N/A"


def fmt_eps(value):
    value = valuation_num(value)
    return f"{value:.2f}" if value is not None else "N/A"


def fmt_cap(value):
    value = valuation_num(value)
    return f"{value:.1f}x" if value is not None else "N/A"


def build_multiple_context(
    *,
    target_pe_cap,
    suggested_cap,
    dynamic_cap_pack,
    industry_profile,
    eff_f_eps,
    has_ai_fin_fetch,
    ai_f_eps_calc,
    ai_forward_eps_fy1,
    ai_forward_eps_fy2,
    ai_forward_eps_fy3,
    cap_adopted_forward_eps,
    sys_latest_quarter_eps=None,
    ai_latest_quarter_eps=None,
    eff_t_eps=None,
    raw_ai_period=None,
):
    """Build multiple caps, formula prices, manual scenario, and FY tiers."""
    dynamic_cap_pack = dynamic_cap_pack if isinstance(dynamic_cap_pack, dict) else {}
    industry_profile = industry_profile if isinstance(industry_profile, dict) else {}

    operable_pe_cap = cap_float(target_pe_cap, suggested_cap)
    base_pe_cap_for_calc = cap_float(dynamic_cap_pack.get("base_multiple"), None)
    if base_pe_cap_for_calc is None:
        base_pe_cap_for_calc = cap_float(industry_profile.get("base_pe"), None)
    if base_pe_cap_for_calc is None:
        base_pe_cap_for_calc = cap_float(industry_profile.get("cap_hint"), None)

    formula_pe_cap = cap_float(dynamic_cap_pack.get("formula_cap"), None)
    if formula_pe_cap is None:
        formula_pe_cap = cap_float(dynamic_cap_pack.get("raw_cap"), base_pe_cap_for_calc if base_pe_cap_for_calc is not None else operable_pe_cap)
    if base_pe_cap_for_calc is None:
        base_pe_cap_for_calc = formula_pe_cap

    soft_pe_cap = cap_float(dynamic_cap_pack.get("optimistic_cap"), None)
    if soft_pe_cap is None:
        soft_pe_cap = cap_float(dynamic_cap_pack.get("soft_ceiling_cap"), formula_pe_cap)
    hard_pe_cap = cap_float(dynamic_cap_pack.get("hard_ceiling_cap"), cap_float(dynamic_cap_pack.get("ceiling_cap"), soft_pe_cap))

    if soft_pe_cap is not None and base_pe_cap_for_calc is not None:
        soft_pe_cap = max(soft_pe_cap, base_pe_cap_for_calc)
    if hard_pe_cap is not None and soft_pe_cap is not None:
        hard_pe_cap = max(hard_pe_cap, soft_pe_cap)

    soft_pe_cap_for_calc = soft_pe_cap
    hard_pe_cap_for_calc = hard_pe_cap
    if formula_pe_cap is not None and soft_pe_cap is not None:
        formula_pe_cap = min(formula_pe_cap, soft_pe_cap)
    extreme_pe_cap_for_calc = soft_pe_cap if soft_pe_cap is not None else operable_pe_cap

    forward_eps_period_mismatch = detect_forward_eps_period_mismatch(
        system_forward_eps=eff_f_eps,
        fy1_eps=ai_forward_eps_fy1,
        fy2_eps=ai_forward_eps_fy2,
    )
    formula_eps_for_calc = forward_eps_period_mismatch.get("recommended_eps")
    formula_eps_source = forward_eps_period_mismatch.get("recommended_eps_source")
    sys_target_price_raw = valuation_price(eff_f_eps, formula_pe_cap)
    sys_target_price_est = valuation_price(formula_eps_for_calc, formula_pe_cap)
    is_capped = False
    extreme_target_price_raw = valuation_price(eff_f_eps, extreme_pe_cap_for_calc)
    extreme_target_price = valuation_price(formula_eps_for_calc, extreme_pe_cap_for_calc)
    current_eps_valuation = build_current_eps_valuation(
        ai_latest_quarter_eps=ai_latest_quarter_eps,
        sys_latest_quarter_eps=sys_latest_quarter_eps,
        eff_t_eps=eff_t_eps,
        formula_pe_cap=formula_pe_cap,
        raw_ai_period=raw_ai_period,
    )

    try:
        manual_cap_user_adjusted = (
            target_pe_cap is not None
            and suggested_cap is not None
            and abs(float(target_pe_cap) - float(suggested_cap)) > 1e-6
        )
    except Exception:
        manual_cap_user_adjusted = False
    manual_cap_input = operable_pe_cap if manual_cap_user_adjusted else base_pe_cap_for_calc
    manual_cap_source_text = "使用者手動 Cap" if manual_cap_user_adjusted else "未手動調整，採 FY1 base"
    manual_cap_for_calc = manual_cap_input
    manual_cap_hit_hard = False
    if manual_cap_input is not None and hard_pe_cap is not None and manual_cap_input > hard_pe_cap:
        manual_cap_for_calc = hard_pe_cap
        manual_cap_hit_hard = True
    manual_target_price = eff_f_eps * manual_cap_for_calc if eff_f_eps is not None and eff_f_eps > 0 and manual_cap_for_calc is not None else None

    ai_target_price_est = ai_f_eps_calc * formula_pe_cap if has_ai_fin_fetch and ai_f_eps_calc is not None and ai_f_eps_calc > 0 and formula_pe_cap is not None else None
    ai_is_capped = False
    ai_extreme_target_price = ai_f_eps_calc * extreme_pe_cap_for_calc if has_ai_fin_fetch and ai_f_eps_calc is not None and ai_f_eps_calc > 0 and extreme_pe_cap_for_calc is not None else None
    ai_manual_target_price = ai_f_eps_calc * manual_cap_for_calc if has_ai_fin_fetch and ai_f_eps_calc is not None and ai_f_eps_calc > 0 and manual_cap_for_calc is not None else None

    fy1_eps_for_annual = ai_forward_eps_fy1 if ai_forward_eps_fy1 is not None else cap_adopted_forward_eps
    fy1_formula_target_price = valuation_price(ai_forward_eps_fy1, formula_pe_cap)
    fy2_formula_target_price = valuation_price(ai_forward_eps_fy2, formula_pe_cap)
    fy3_formula_target_price = valuation_price(ai_forward_eps_fy3, formula_pe_cap)
    fy1_base_target_price = valuation_price(ai_forward_eps_fy1, base_pe_cap_for_calc)
    fy1_soft_target_price = valuation_price(ai_forward_eps_fy1, soft_pe_cap_for_calc)
    fy1_hard_target_price = valuation_price(ai_forward_eps_fy1, hard_pe_cap_for_calc)
    fy2_base_target_price = valuation_price(ai_forward_eps_fy2, base_pe_cap_for_calc)
    fy2_soft_target_price = valuation_price(ai_forward_eps_fy2, soft_pe_cap_for_calc)
    fy2_hard_target_price = valuation_price(ai_forward_eps_fy2, hard_pe_cap_for_calc)
    fy3_base_target_price = valuation_price(ai_forward_eps_fy3, base_pe_cap_for_calc)
    fy3_soft_target_price = valuation_price(ai_forward_eps_fy3, soft_pe_cap_for_calc)
    fy3_hard_target_price = valuation_price(ai_forward_eps_fy3, hard_pe_cap_for_calc)
    fy1_manual_target_price = valuation_price(fy1_eps_for_annual, manual_cap_for_calc)

    return {
        "operable_pe_cap": operable_pe_cap,
        "base_pe_cap_for_calc": base_pe_cap_for_calc,
        "formula_pe_cap": formula_pe_cap,
        "soft_pe_cap": soft_pe_cap,
        "hard_pe_cap": hard_pe_cap,
        "soft_pe_cap_for_calc": soft_pe_cap_for_calc,
        "hard_pe_cap_for_calc": hard_pe_cap_for_calc,
        "extreme_pe_cap_for_calc": extreme_pe_cap_for_calc,
        "sys_target_price_est": sys_target_price_est,
        "sys_target_price_raw": sys_target_price_raw,
        "formula_eps_for_calc": formula_eps_for_calc,
        "formula_eps_source": formula_eps_source,
        "forward_eps_period_mismatch": forward_eps_period_mismatch,
        "current_eps_raw": current_eps_valuation["current_eps_raw"],
        "current_eps_for_valuation": current_eps_valuation["current_eps_for_valuation"],
        "current_eps_source": current_eps_valuation["current_eps_source"],
        "current_eps_source_detail": current_eps_valuation["current_eps_source_detail"],
        "current_eps_period": current_eps_valuation["current_eps_period"],
        "current_target_price_est": current_eps_valuation["current_target_price_est"],
        "is_capped": is_capped,
        "extreme_target_price": extreme_target_price,
        "extreme_target_price_raw": extreme_target_price_raw,
        "manual_cap_user_adjusted": manual_cap_user_adjusted,
        "manual_cap_input": manual_cap_input,
        "manual_cap_source_text": manual_cap_source_text,
        "manual_cap_for_calc": manual_cap_for_calc,
        "manual_cap_hit_hard": manual_cap_hit_hard,
        "manual_target_price": manual_target_price,
        "ai_target_price_est": ai_target_price_est,
        "ai_is_capped": ai_is_capped,
        "ai_extreme_target_price": ai_extreme_target_price,
        "ai_manual_target_price": ai_manual_target_price,
        "fy1_eps_for_annual": fy1_eps_for_annual,
        "fy1_formula_target_price": fy1_formula_target_price,
        "fy2_formula_target_price": fy2_formula_target_price,
        "fy3_formula_target_price": fy3_formula_target_price,
        "fy1_base_target_price": fy1_base_target_price,
        "fy1_soft_target_price": fy1_soft_target_price,
        "fy1_hard_target_price": fy1_hard_target_price,
        "fy2_base_target_price": fy2_base_target_price,
        "fy2_soft_target_price": fy2_soft_target_price,
        "fy2_hard_target_price": fy2_hard_target_price,
        "fy3_base_target_price": fy3_base_target_price,
        "fy3_soft_target_price": fy3_soft_target_price,
        "fy3_hard_target_price": fy3_hard_target_price,
        "fy1_manual_target_price": fy1_manual_target_price,
    }
