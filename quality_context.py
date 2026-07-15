"""Financial data context builders for ui_main.render_main_page."""

from ui_common import *


def _row_text(row, key, default=""):
    try:
        value = row.get(key, default)
    except Exception:
        return default
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "null"} else text


def build_financial_base_context(*, stock_id, info, current_price, finmind_key, has_ai_financial_snapshot=False):
    """Collect system/FinMind financial inputs before valuation calculations."""
    info = info or {}
    df_rev_bk = get_monthly_revenue(stock_id, finmind_key)
    df_per_bk = get_pe_pb_data(stock_id, finmind_key)
    fm_health = get_finmind_financial_health(stock_id, finmind_key)

    if df_rev_bk is not None and not df_rev_bk.empty:
        latest_rev_row = df_rev_bk.iloc[-1]
        if "actual_revenue_month" in df_rev_bk.columns:
            latest_rev_month = normalize_revenue_month(df_rev_bk["actual_revenue_month"].iloc[-1])
        else:
            latest_rev_month = normalize_revenue_month(df_rev_bk["Month"].iloc[-1])
        latest_mom_val = s_float(df_rev_bk["monthly_revenue_mom"].iloc[-1]) if "monthly_revenue_mom" in df_rev_bk.columns else s_float(df_rev_bk["MoM"].iloc[-1])
        latest_yoy_val = s_float(df_rev_bk["monthly_revenue_yoy"].iloc[-1]) if "monthly_revenue_yoy" in df_rev_bk.columns else (s_float(df_rev_bk["YoY"].iloc[-1]) if "YoY" in df_rev_bk.columns else None)
        latest_monthly_yoy = latest_yoy_val / 100.0 if latest_yoy_val is not None else None
        latest_rev_source = _row_text(latest_rev_row, "revenue_source", "月營收資料源") or "月營收資料源"
        latest_rev_source_url = _row_text(latest_rev_row, "source_url")
        latest_rev_source_rule = _row_text(latest_rev_row, "source_rule")
        latest_rev_announce_date = _row_text(latest_rev_row, "announce_date")
        latest_rev_announce_month = normalize_revenue_month(_row_text(latest_rev_row, "announce_month"))
        latest_rev_revenue_month = normalize_revenue_month(
            _row_text(latest_rev_row, "revenue_month")
            or _row_text(latest_rev_row, "actual_revenue_month")
            or _row_text(latest_rev_row, "Month")
            or latest_rev_month
        )
        rev_notice_pack = build_revenue_month_notice(latest_rev_month)
        latest_rev_notice = rev_notice_pack.get("notice", "")
        latest_rev_display_label = rev_notice_pack.get("display_label", f"公告月份：{latest_rev_month}")
    else:
        latest_rev_month = "無資料"
        latest_mom_val = None
        latest_monthly_yoy = None
        latest_rev_notice = "未取得月營收資料，營收 YoY / MoM 將改用其他資料源或顯示 N/A。"
        latest_rev_display_label = "公告月份：未取得"
        latest_rev_source = ""
        latest_rev_source_url = ""
        latest_rev_source_rule = ""
        latest_rev_announce_date = ""
        latest_rev_announce_month = ""
        latest_rev_revenue_month = ""

    pe_ratio = s_float(info.get("trailingPE"))
    if (pe_ratio is None or pe_ratio > 1000) and df_per_bk is not None and not df_per_bk.empty:
        if (pd.Timestamp.today() - df_per_bk.iloc[-1]["date"]).days < 30:
            pe_ratio = s_float(df_per_bk["PER"].iloc[-1])

    pb_ratio = s_float(info.get("priceToBook"))
    if (pb_ratio is None or pb_ratio > 500) and df_per_bk is not None and not df_per_bk.empty and "PBR" in df_per_bk.columns:
        pb_ratio = s_float(df_per_bk["PBR"].iloc[-1])

    roe = s_float(info.get("returnOnEquity"))
    sys_de = s_float(info.get("debtToEquity"))
    if sys_de is not None:
        sys_de = sys_de / 100.0

    gross_margin = s_float(info.get("grossMargins"))
    op_margin = s_float(info.get("operatingMargins"))

    if gross_margin is None:
        gross_margin = fm_health.get("grossMargins")
    if op_margin is None:
        op_margin = fm_health.get("operatingMargins")
    if sys_de is None:
        sys_de = fm_health.get("debtToEquity")

    # yfinance revenueGrowth 常是季度/TTM 口徑，不等於台股最新單月營收 YoY。
    # 系統「營收 YoY」只採公告月份的月營收資料；缺值時留空，後續可由 AI 單月 YoY 補齊。
    rev_growth = latest_monthly_yoy
    earn_growth = s_float(info.get("earningsGrowth"))

    t_eps = s_float(info.get("trailingEps"))
    sys_ttm_eps_source = "yfinance trailingEps"
    sys_ttm_eps_is_inferred = False
    if t_eps is None and pe_ratio is not None and pe_ratio > 0 and current_price > 0:
        t_eps = current_price / pe_ratio
        sys_ttm_eps_source = "現價 / P/E 反推"
        sys_ttm_eps_is_inferred = True

    sys_f_eps_calc = s_float(info.get("forwardEps"))

    return {
        "df_rev_bk": df_rev_bk,
        "df_per_bk": df_per_bk,
        "fm_health": fm_health,
        "latest_rev_month": latest_rev_month,
        "latest_mom_val": latest_mom_val,
        "latest_rev_notice": latest_rev_notice,
        "latest_rev_display_label": latest_rev_display_label,
        "latest_rev_source": latest_rev_source,
        "latest_rev_source_url": latest_rev_source_url,
        "latest_rev_source_rule": latest_rev_source_rule,
        "latest_rev_announce_date": latest_rev_announce_date,
        "latest_rev_announce_month": latest_rev_announce_month,
        "latest_rev_revenue_month": latest_rev_revenue_month,
        "pe_ratio": pe_ratio,
        "pb_ratio": pb_ratio,
        "roe": roe,
        "sys_de": sys_de,
        "gross_margin": gross_margin,
        "op_margin": op_margin,
        "rev_growth": rev_growth,
        "earn_growth": earn_growth,
        "t_eps": t_eps,
        "sys_ttm_eps_source": sys_ttm_eps_source if t_eps is not None else "",
        "sys_ttm_eps_is_inferred": sys_ttm_eps_is_inferred,
        "sys_f_eps_calc": sys_f_eps_calc,
        "sys_latest_quarter_eps": None,
        "sys_ttm_eps": t_eps,
        "sys_fiscal_year_eps": None,
        "sys_forward_eps_system": sys_f_eps_calc,
        "show_ai_financial_warning": pe_ratio is None and t_eps is None and not has_ai_financial_snapshot,
    }


def first_valid_analyst_count(*vals):
    for value in vals:
        float_value = s_float(value)
        if float_value is not None and float_value > 0:
            return int(float_value)
    return None


def build_ai_financial_context(*, stock_id, info, ai_financial_store):
    """Normalize an existing AI financial snapshot into variables used by ui_main."""
    info = info or {}
    ai_financial_store = ai_financial_store if isinstance(ai_financial_store, dict) else {}
    ai_fin = ai_financial_store.get(stock_id, {})
    if isinstance(ai_fin, dict) and ai_fin:
        bound_stock_id = str(ai_fin.get("_stock_id") or stock_id)
        if bound_stock_id != str(stock_id):
            ai_fin = {}
            ai_financial_store.pop(stock_id, None)
    if not isinstance(ai_fin, dict):
        ai_fin = {}

    has_ai_fin_fetch = bool(ai_fin)
    ai_pe = s_float(ai_fin.get("pe")) if has_ai_fin_fetch else None
    ai_pb = s_float(ai_fin.get("pb")) if has_ai_fin_fetch else None
    ai_latest_month_eps = pick_first_number(ai_fin.get("latest_month_eps")) if has_ai_fin_fetch else None
    ai_latest_quarter_eps = pick_first_number(ai_fin.get("latest_quarter_eps")) if has_ai_fin_fetch else None
    ai_previous_quarter_eps = pick_first_number(ai_fin.get("previous_quarter_eps")) if has_ai_fin_fetch else None
    ai_last_two_quarter_eps = pick_first_number(ai_fin.get("last_two_quarter_eps")) if has_ai_fin_fetch else None
    if ai_last_two_quarter_eps is None and ai_latest_quarter_eps is not None and ai_previous_quarter_eps is not None:
        ai_last_two_quarter_eps = ai_latest_quarter_eps + ai_previous_quarter_eps
    ai_ttm_eps = pick_first_number(ai_fin.get("ttm_eps"), ai_fin.get("trailing_eps")) if has_ai_fin_fetch else None
    ai_fiscal_year_eps = pick_first_number(ai_fin.get("fiscal_year_eps")) if has_ai_fin_fetch else None
    ai_forward_eps_ai = pick_first_number(ai_fin.get("forward_eps_ai"), ai_fin.get("forward_eps")) if has_ai_fin_fetch else None
    ai_forward_eps_consensus = pick_first_number(ai_fin.get("forward_eps_consensus")) if has_ai_fin_fetch else None
    ai_forward_eps_fy1 = pick_first_number(ai_fin.get("forward_eps_fy1"), ai_forward_eps_consensus, ai_forward_eps_ai) if has_ai_fin_fetch else None
    ai_forward_eps_fy2 = pick_first_number(ai_fin.get("forward_eps_fy2")) if has_ai_fin_fetch else None
    ai_forward_eps_fy3 = pick_first_number(ai_fin.get("forward_eps_fy3")) if has_ai_fin_fetch else None
    ai_forward_eps_fy1_year = ai_fin.get("forward_eps_fy1_year") if has_ai_fin_fetch else None
    ai_forward_eps_fy2_year = ai_fin.get("forward_eps_fy2_year") if has_ai_fin_fetch else None
    ai_forward_eps_fy3_year = ai_fin.get("forward_eps_fy3_year") if has_ai_fin_fetch else None
    ai_forward_eps_fy_source_note = ai_fin.get("forward_eps_fy_source_note") if has_ai_fin_fetch else None
    ai_forward_eps_fy_basis = ai_fin.get("forward_eps_fy_basis") if has_ai_fin_fetch else None
    ai_t_eps = ai_ttm_eps
    ai_f_eps_calc = pick_first_number(ai_forward_eps_fy1, ai_forward_eps_consensus, ai_forward_eps_ai) if has_ai_fin_fetch else None
    ai_yoy = s_float(ai_fin.get("yoy")) if has_ai_fin_fetch else None
    ai_gm = s_float(ai_fin.get("gross_margin")) if has_ai_fin_fetch else None
    ai_om = s_float(ai_fin.get("operating_margin")) if has_ai_fin_fetch else None
    ai_roe = s_float(ai_fin.get("roe")) if has_ai_fin_fetch else None
    ai_de = s_float(ai_fin.get("debt_to_equity")) if has_ai_fin_fetch else None
    ai_dy = s_float(ai_fin.get("dividend_yield")) if has_ai_fin_fetch else None
    ai_fcf = s_float(ai_fin.get("free_cash_flow")) if has_ai_fin_fetch else None
    ai_cr = s_float(ai_fin.get("current_ratio")) if has_ai_fin_fetch else None
    ai_shares = s_float(ai_fin.get("shares_outstanding")) if has_ai_fin_fetch else None
    ai_target_price = s_float(ai_fin.get("target_price")) if has_ai_fin_fetch else None
    ai_hi_val = s_float(ai_fin.get("target_price_high")) if has_ai_fin_fetch else None
    ai_me_val = (s_float(ai_fin.get("target_price_avg")) or ai_target_price) if has_ai_fin_fetch else None
    ai_lo_val = s_float(ai_fin.get("target_price_low")) if has_ai_fin_fetch else None
    ai_analyst_count = ai_fin.get("target_price_analyst_count") if has_ai_fin_fetch else None
    ai_target_rationale = str(ai_fin.get("target_price_rationale") or "").strip() if has_ai_fin_fetch else ""
    sys_analyst_count = info.get("numberOfAnalystOpinions")
    ai_analyst_count = first_valid_analyst_count(
        ai_analyst_count,
        ai_fin.get("analyst_count") if has_ai_fin_fetch else None,
        ai_fin.get("target_analyst_count") if has_ai_fin_fetch else None,
        sys_analyst_count,
    )
    ai_mom = normalize_financial_ratio(ai_fin.get("mom")) if has_ai_fin_fetch else None

    return {
        "ai_fin": ai_fin,
        "has_ai_fin_fetch": has_ai_fin_fetch,
        "ai_pe": ai_pe,
        "ai_pb": ai_pb,
        "ai_latest_month_eps": ai_latest_month_eps,
        "ai_latest_quarter_eps": ai_latest_quarter_eps,
        "ai_previous_quarter_eps": ai_previous_quarter_eps,
        "ai_last_two_quarter_eps": ai_last_two_quarter_eps,
        "ai_ttm_eps": ai_ttm_eps,
        "ai_fiscal_year_eps": ai_fiscal_year_eps,
        "ai_forward_eps_ai": ai_forward_eps_ai,
        "ai_forward_eps_consensus": ai_forward_eps_consensus,
        "ai_forward_eps_fy1": ai_forward_eps_fy1,
        "ai_forward_eps_fy2": ai_forward_eps_fy2,
        "ai_forward_eps_fy3": ai_forward_eps_fy3,
        "ai_forward_eps_fy1_year": ai_forward_eps_fy1_year,
        "ai_forward_eps_fy2_year": ai_forward_eps_fy2_year,
        "ai_forward_eps_fy3_year": ai_forward_eps_fy3_year,
        "ai_forward_eps_fy_source_note": ai_forward_eps_fy_source_note,
        "ai_forward_eps_fy_basis": ai_forward_eps_fy_basis,
        "ai_t_eps": ai_t_eps,
        "ai_f_eps_calc": ai_f_eps_calc,
        "ai_yoy": ai_yoy,
        "ai_gm": ai_gm,
        "ai_om": ai_om,
        "ai_roe": ai_roe,
        "ai_de": ai_de,
        "ai_dy": ai_dy,
        "ai_fcf": ai_fcf,
        "ai_cr": ai_cr,
        "ai_shares": ai_shares,
        "ai_target_price": ai_target_price,
        "ai_hi_val": ai_hi_val,
        "ai_me_val": ai_me_val,
        "ai_lo_val": ai_lo_val,
        "ai_analyst_count": ai_analyst_count,
        "ai_target_rationale": ai_target_rationale,
        "ai_mom": ai_mom,
    }
