"""V3 market reasoning panel."""

from ui_common import *
from market_backtest import evaluate_market_backtest, optimize_market_weights
from market_reports import (
    build_market_alert_report,
    build_market_auto_report,
    build_market_report_frame,
    build_market_report_text,
)
from market_reasoning import (
    append_market_reasoning_history,
    calculate_market_reasoning,
    build_market_history_frame,
    build_market_reasoning_report,
    build_market_scenario_report,
)


MARKET_REASONING_SCOPE = "global_taiwan_market"
MARKET_REASONING_HISTORY_KEY = "market_reasoning_history_global"
MARKET_AI_ANALYSIS_KEY = "market_ai_analysis_global"
MARKET_AI_BUTTON_KEY = "market_ai_analysis_btn_global"
MARKET_AUTO_REPORT_TYPE_KEY = "market_auto_report_type_global"
MARKET_AUTO_REPORT_TEXT_KEY = "market_auto_report_text_global"


def build_market_reasoning_calculation_kwargs(trend_data=None, chip_state=None, futures_snapshot=None, use_stock_chip_state=False):
    """Build calculation kwargs for the UI; market mode ignores current stock chip data by default."""
    return {
        "trend_data": trend_data,
        "chip_state": chip_state if use_stock_chip_state else None,
        "futures_snapshot": futures_snapshot,
    }


def _score_color(score, *, inverse=False):
    if score is None:
        return "#aaaaaa"
    if inverse:
        if score >= 70:
            return "#ff6b6b"
        if score >= 45:
            return "#ffd166"
        return "#3ddc84"
    if score >= 35:
        return "#ff6b6b"
    if score <= -35:
        return "#3ddc84"
    return "#ffd166"


def _fmt_score(score):
    if score is None:
        return "N/A"
    return f"{score:.1f}"


def _taipei_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)


def _market_session_info(now=None):
    now = now or _taipei_now()
    minutes = now.hour * 60 + now.minute
    if 5 * 60 <= minutes <= 8 * 60 + 59:
        label = "台股盤前"
    elif 9 * 60 <= minutes <= 13 * 60 + 30:
        label = "台股盤中"
    elif 13 * 60 + 31 <= minutes <= 20 * 60 + 59:
        label = "台股盤後"
    else:
        label = "美股 / 夜盤"
    return {
        "label": label,
        "key": f"{now.strftime('%Y-%m-%d')}::{label}",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "display_time": now.strftime("%H時%M分"),
    }


def _attach_ai_cache_meta(ai_result, session_info):
    if isinstance(ai_result, dict):
        ai_result["_ui_cache"] = {
            "market_session": session_info["label"],
            "market_session_key": session_info["key"],
            "generated_at": session_info["generated_at"],
            "display_time": session_info["display_time"],
        }
    return ai_result


def render_market_reasoning_panel(
    trend_data=None,
    chip_state=None,
    stock_id=None,
    stock_name=None,
    futures_snapshot=None,
    use_stock_chip_state=False,
):
    """Render V3 market reasoning result and return the reasoning pack."""
    if futures_snapshot is None:
        futures_snapshot = get_taifex_foreign_futures_snapshot(
            price_change_pct=(trend_data or {}).get("ewt"),
        )
    reasoning = calculate_market_reasoning(**build_market_reasoning_calculation_kwargs(
        trend_data=trend_data,
        chip_state=chip_state,
        futures_snapshot=futures_snapshot,
        use_stock_chip_state=use_stock_chip_state,
    ))
    quality = reasoning.get("data_quality", {})
    phase_label = "第七階段｜全市場模式"

    history = append_market_reasoning_history(
        st.session_state.get(MARKET_REASONING_HISTORY_KEY, []),
        reasoning,
        stock_id=None,
        stock_name=None,
    )
    st.session_state[MARKET_REASONING_HISTORY_KEY] = history
    backtest = evaluate_market_backtest(history, min_samples=5)
    weight_result = optimize_market_weights(history, min_samples=5)

    st.markdown(f"#### 🧭 V3 市場推理引擎（{phase_label}）")

    direction = reasoning.get("direction_score")
    risk = reasoning.get("risk_score")
    confidence = reasoning.get("confidence_score")
    regime_label = reasoning.get("regime_label", "資料不足")

    header_html = f"""
    <div style='background:#1e1e1e; border:1px solid #333; border-left:5px solid {_score_color(direction)};
        border-radius:8px; padding:14px 16px; margin-bottom:10px;'>
        <div style='display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; align-items:flex-start;'>
            <div>
                <div style='color:#cccccc; font-size:0.9rem;'>市場狀態</div>
                <div style='font-size:1.25rem; font-weight:700; color:#ffffff;'>{regime_label}</div>
                <div style='color:#cccccc; font-size:0.9rem; margin-top:4px;'>{reasoning.get("summary", "")}</div>
            </div>
            <div style='text-align:right; color:#cccccc; font-size:0.85rem;'>
                <div>{reasoning.get("model_version", "")}</div>
                <div>資料品質：{quality.get("status", "INSUFFICIENT")}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(clean_html(header_html), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("市場方向分數", _fmt_score(direction), help="SOX、TSM ADR、EWT、NASDAQ futures 加權後的方向分數。")
    with c2:
        st.metric("風險分數", _fmt_score(risk), help="跌幅、指標分歧與方向強度綜合後的環境風險。")
    with c3:
        st.metric("信心分數", _fmt_score(confidence), help="資料完整度與方向一致性合成。")

    for warning in reasoning.get("warnings", []):
        st.warning(warning)
    if chip_state is not None and not use_stock_chip_state:
        st.caption("本區為全市場推理：不納入目前查詢個股的法人/融資籌碼，因此切換股票時市場分數應維持一致；個股籌碼請看下方籌碼面板。")

    short_position = reasoning.get("short_position") or {}
    futures_data = ((reasoning.get("snapshot") or {}).get("extensions") or {}).get("futures_snapshot") or {}
    with st.expander("台指期外資空單分類", expanded=False):
        if futures_data.get("available"):
            def _fmt_lots(value):
                value = s_float(value)
                return "N/A" if value is None else f"{value:,.0f} 口"

            rows = [
                {"項目": "資料日期", "數值": futures_data.get("data_date") or "N/A", "說明": futures_data.get("source", "TAIFEX")},
                {"項目": "商品 / 身份", "數值": f"{futures_data.get('product_name', 'N/A')} / {futures_data.get('investor_name', 'N/A')}", "說明": "期交所三大法人區分各期貨契約"},
                {"項目": "當日多方交易", "數值": _fmt_lots(futures_data.get("foreign_futures_trade_long_lots")), "說明": "外資買進期貨口數"},
                {"項目": "當日空方交易", "數值": _fmt_lots(futures_data.get("foreign_futures_trade_short_lots")), "說明": "外資賣出期貨口數"},
                {"項目": "當日交易淨流量推估", "數值": _fmt_lots(futures_data.get("foreign_futures_short_change")), "說明": f"{futures_data.get('daily_bias', '')}；這是交易流量，不等於未平倉變化"},
                {"項目": "未平倉多方", "數值": _fmt_lots(futures_data.get("foreign_futures_long_oi_lots")), "說明": "外資未平倉多方口數"},
                {"項目": "未平倉空方", "數值": _fmt_lots(futures_data.get("foreign_futures_short_oi_lots")), "說明": "外資未平倉空方口數"},
                {"項目": "未平倉淨額", "數值": _fmt_lots(futures_data.get("foreign_futures_net_oi_lots")), "說明": futures_data.get("net_oi_bias", "")},
                {"項目": "存量判讀", "數值": short_position.get("position_label", "資料不足"), "說明": "依外資台指期未平倉淨額判斷"},
                {"項目": "當日流量判讀", "數值": short_position.get("flow_label", "資料不足"), "說明": "依當日多方/空方交易口數推估"},
                {"項目": "分類結果", "數值": short_position.get("display_label") or short_position.get("top_label", "資料不足"), "說明": short_position.get("interpretation") or "看空 / 避險 / 套利 / 回補為規則推估"},
            ]
            st_dataframe(pd.DataFrame(rows), hide_index=True)
            probabilities = short_position.get("probabilities") or {}
            if probabilities:
                st.caption("下表機率描述的是當日行為型態；未平倉空單存量請以上方「存量判讀」為準。")
                prob_rows = [
                    {"分類": "避險 / 風控", "機率": f"{probabilities.get('hedge', 0):.1%}"},
                    {"分類": "方向性看空", "機率": f"{probabilities.get('directional_bear', 0):.1%}"},
                    {"分類": "套利", "機率": f"{probabilities.get('arbitrage', 0):.1%}"},
                    {"分類": "空單回補", "機率": f"{probabilities.get('covering', 0):.1%}"},
                ]
                st_dataframe(pd.DataFrame(prob_rows), hide_index=True)
            st.caption("限制：期交所資料為市場層級台指期外資部位；當日交易流量與未平倉存量需分開解讀，分類只作風控推估。")
        else:
            st.info(futures_data.get("message", "尚未取得台指期外資空單資料。"))

    evidence = reasoning.get("evidence") or []
    counter_evidence = reasoning.get("counter_evidence") or []
    if evidence or counter_evidence:
        with st.expander("市場推理證據", expanded=False):
            if evidence:
                st.caption("支持證據")
                st.write("；".join(evidence))
            if counter_evidence:
                st.caption("反向證據")
                st.write("；".join(counter_evidence))

    with st.expander("Bull / Base / Bear 三情境", expanded=False):
        scenario_report = build_market_scenario_report(reasoning)
        if not scenario_report.empty:
            st_dataframe(scenario_report, hide_index=True)
        else:
            st.caption("尚未產生情境資料。")

    evidence_records = reasoning.get("reasoning_evidence") or []
    if evidence_records:
        with st.expander("可追溯證據紀錄", expanded=False):
            evidence_df = pd.DataFrame(evidence_records)
            display_cols = ["rank", "signal_code", "direction", "weight", "value", "evidence_text", "source"]
            st_dataframe(evidence_df[[c for c in display_cols if c in evidence_df.columns]], hide_index=True)

    with st.expander("市場推理歷史趨勢", expanded=False):
        history_df = build_market_history_frame(history)
        if history_df.empty:
            st.caption("尚未累積市場推理快照。")
        else:
            display_history = history_df.copy()
            for col in ("Bull", "Base", "Bear"):
                if col in display_history.columns:
                    display_history[col] = display_history[col].apply(lambda v: "N/A" if pd.isna(v) else f"{v:.2%}")
            st_dataframe(display_history.tail(20), hide_index=True)
            if len(history_df) >= 2:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=history_df["時間"], y=history_df["方向"], mode="lines+markers", name="方向"))
                fig.add_trace(go.Scatter(x=history_df["時間"], y=history_df["風險"], mode="lines+markers", name="風險"))
                fig.add_trace(go.Scatter(x=history_df["時間"], y=history_df["信心"], mode="lines+markers", name="信心"))
                fig.update_layout(
                    height=280,
                    margin=dict(l=10, r=10, t=25, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(range=[0, 100]),
                    legend=dict(orientation="h"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("累積兩筆以上快照後顯示走勢圖。")

    with st.expander("回測與權重優化（第六階段）", expanded=False):
        if not backtest.get("available"):
            st.info(backtest.get("message", "回測樣本不足。"))
            st.caption("需要歷史紀錄含 `future_return_1d` 或 `future_return_5d` 欄位；目前 session 快照只保存推理輸出，不會自行產生未來報酬。")
            st_dataframe(backtest.get("report"), hide_index=True)
        else:
            st.success("回測樣本足夠，已產生方向命中率與策略報酬。")
            st_dataframe(backtest.get("report"), hide_index=True)

        if weight_result.get("available"):
            best = weight_result.get("best_config") or {}
            st.caption(f"目前最佳候選權重：{best.get('config_name')}。注意：需用足夠歷史樣本再納入正式模型。")
        else:
            st.caption(weight_result.get("message", "權重優化樣本不足。"))
        if weight_result.get("report") is not None:
            st_dataframe(weight_result.get("report"), hide_index=True)

    st.markdown("##### 🤖 AI Gateway 市場深度分析")
    ai_key = MARKET_AI_ANALYSIS_KEY
    button_key = MARKET_AI_BUTTON_KEY
    current_session = _market_session_info()
    if st.button(
        "啟動 AI 市場深度分析",
        key=button_key,
        disabled=not st.session_state.get("api_key"),
        use_container_width=True,
        help="只會送出系統市場推理 JSON，不允許 AI 自行補資料。",
    ):
        with st.spinner("AI Gateway 分析市場推理資料中..."):
            st.session_state[ai_key] = _attach_ai_cache_meta(get_market_ai_analysis(
                reasoning,
                st.session_state.get("api_key", ""),
                stock_id=None,
                stock_name=None,
                model_name=get_selected_model_id(),
            ), current_session)

    if not st.session_state.get("api_key"):
        st.caption("尚未輸入 Gemini API Key；AI Gateway 按鈕停用。")

    ai_result = st.session_state.get(ai_key)
    if isinstance(ai_result, dict):
        if not isinstance(ai_result.get("_ui_cache"), dict):
            ai_result = _attach_ai_cache_meta(ai_result, current_session)
            st.session_state[ai_key] = ai_result
        cache_meta = ai_result.get("_ui_cache") or {}
        if cache_meta.get("market_session_key") == current_session["key"]:
            st.info(
                f"本時段（{cache_meta.get('display_time', '時間未記錄')}）已有 AI 市場分析結果，預設沿用；"
                "再次按下「啟動 AI 市場深度分析」會重新分析。"
            )
        else:
            st.caption(
                f"上一時段（{cache_meta.get('market_session', '未知時段')} "
                f"{cache_meta.get('display_time', '時間未記錄')}）已有 AI 市場分析結果；"
                "若市場資料已更新，可按下按鈕重新分析。"
            )
        data = ai_result.get("data") or {}
        if ai_result.get("ok"):
            st.success("AI Gateway 回覆已通過 JSON Schema 驗證。")
        else:
            st.warning("AI Gateway 已使用規則引擎降級摘要。")
            issues = ai_result.get("issues") or []
            if issues:
                st.caption("；".join(str(item) for item in issues))

        st.markdown(f"**市場傾向**：`{data.get('market_bias', 'NEUTRAL')}`｜**信心**：`{data.get('confidence', 'N/A')}`")
        if data.get("summary"):
            st.write(data.get("summary"))
        with st.expander("AI Gateway JSON 結果", expanded=False):
            st.json(data)
        with st.expander("AI Gateway Prompt / Input", expanded=False):
            st.json({
                "prompt": ai_result.get("prompt"),
                "input": ai_result.get("input"),
                "model_used": ai_result.get("model_used"),
            })

    with st.expander("自動報告與告警（第七階段）", expanded=False):
        report_choice = st.radio(
            "報告類型",
            ["盤前報告", "盤後報告"],
            horizontal=True,
            key=MARKET_AUTO_REPORT_TYPE_KEY,
        )
        report_type = "post_market" if report_choice == "盤後報告" else "pre_market"
        auto_report = build_market_auto_report(
            reasoning,
            report_type=report_type,
            stock_id=None,
            stock_name=None,
            backtest_result=backtest,
            ai_result=ai_result,
        )
        st_dataframe(build_market_report_frame(auto_report), hide_index=True)

        alerts = auto_report.get("alerts") or []
        for alert in alerts:
            message = f"{alert.get('title')}：{alert.get('message')}｜建議：{alert.get('action')}"
            if alert.get("severity") == "danger":
                st.error(message)
            elif alert.get("severity") == "warning":
                st.warning(message)
            else:
                st.info(message)
        st_dataframe(build_market_alert_report(alerts), hide_index=True)

        st.text_area(
            "報告內容",
            value=build_market_report_text(auto_report),
            height=300,
            key=MARKET_AUTO_REPORT_TEXT_KEY,
        )

    with st.expander("市場推理資料品質與權重", expanded=False):
        report = build_market_reasoning_report(reasoning)
        st_dataframe(report, hide_index=True)
        missing = quality.get("missing_extension_groups") or []
        if missing:
            st.caption("後續階段待接資料：" + "、".join(missing))

    with st.expander("API Payload 預覽", expanded=False):
        st.json(reasoning.get("api_payload", {}))

    return reasoning
