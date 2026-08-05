"""Top-level overview panels for ui_main.render_main_page."""

from ui_common import (
    clean_html,
    get_ai_analysis_final,
    reset_all_states_on_stock_change,
    st,
)


def render_topic_loading_panel(topic_q):
    """Resolve a pending topic-search request and update session state."""
    if st.session_state.topic_results != "LOADING":
        return
    with st.spinner(f"🤖 AI 正在連線推演「{topic_q}」..."):
        data, links = get_ai_analysis_final(
            topic_q,
            st.session_state.api_key,
            st.session_state.get("selected_model", "gemini-3.1-pro-preview"),
        )
        if isinstance(data, dict):
            st.session_state.topic_results = {"data": data, "links": links, "topic": topic_q}
            st.session_state.show_whale = False
            st.rerun()
        else:
            st.error(f"AI 解析失敗或逾時無回應。\n\n詳細原因：{data}")
            st.session_state.topic_results = None


def render_topic_results_panel(topic_results):
    """Render the AI topic stock-picking result panel."""
    if not isinstance(topic_results, dict):
        return

    st.success("✅ AI 議題推演完成！系統已為您捕捉以下關聯受惠股，點擊按鈕即可一鍵切換至該檔股票的戰情室面板！")
    data = topic_results.get("data", {}) or {}
    topic = topic_results.get("topic", "")
    stocks = data.get("stocks", []) or []

    ai_topic_html = f"""
    <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #FFD700;'>
        <h3 style='color: white; margin-top: 0;'>💡 議題動態推演：【{topic}】</h3>
        <div style='color: #e0e0e0; font-size: 1.05rem; line-height: 1.6;'>{data.get('reasoning', '無分析內容')}</div>
    </div>
    """
    st.markdown(clean_html(ai_topic_html), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🛡️ 潛力權值股 (點擊切換)")
        for item in [x for x in stocks if "權值" in x.get("type", "") or "潛力" in x.get("type", "")]:
            st.button(
                f"📌 {item.get('name', '未知')} ({item.get('id', '')})",
                on_click=reset_all_states_on_stock_change,
                args=(item.get("id", ""),),
                key=f"tp_{item.get('id', '')}",
                use_container_width=True,
            )
            st.caption(f"理由：{item.get('why', '')}")
    with c2:
        st.markdown("#### 🚀 爆發中小型股 (點擊切換)")
        for item in [x for x in stocks if "中小" in x.get("type", "") or "爆發" in x.get("type", "")]:
            st.button(
                f"🔥 {item.get('name', '未知')} ({item.get('id', '')})",
                on_click=reset_all_states_on_stock_change,
                args=(item.get("id", ""),),
                key=f"ts_{item.get('id', '')}",
                use_container_width=True,
            )
            st.caption(f"理由：{item.get('why', '')}")

    links = topic_results.get("links", []) or []
    if links:
        with st.expander("🔗 查看 AI 參考來源"):
            for link in links:
                st.markdown(f"- [{link}]({link})")
    st.markdown("---")


def render_whale_panel():
    """Render the quick whale-watch shortcut panel."""
    st.markdown("### 🐳 近兩周大戶持股比例顯著增加標的")
    whales = [("2317", "鴻海"), ("2382", "廣達"), ("1519", "華城"), ("6669", "緯穎"), ("3324", "雙鴻")]
    cols = st.columns(5)
    for idx, (code, name) in enumerate(whales):
        with cols[idx]:
            st.button(
                f"{name}\n({code})",
                on_click=reset_all_states_on_stock_change,
                args=(code,),
                key=f"w_{code}",
                use_container_width=True,
            )
    st.markdown("---")


def render_empty_stock_prompt():
    """Render first-load guidance when no stock is selected."""
    st.markdown(
        """
        <div style="
            margin-top: 2.5rem;
            padding: 1.4rem 1.6rem;
            border: 1px solid rgba(0,0,0,0.10);
            border-radius: 14px;
            background: rgba(127,127,127,0.07);
            max-width: 820px;
        ">
            <div style="font-size:1.35rem; font-weight:800; margin-bottom:0.55rem;">
                🔎 請先輸入股票代號或使用左側下拉選股查詢
            </div>
            <div style="font-size:1.02rem; line-height:1.8; color:rgba(120,120,120,0.95);">
                可在左側「輸入台股代號」欄位輸入，例如 <b>2330</b>、<b>3037</b>、<b>2454</b>，
                輸入後請按 <b style="color:#ff8c00;">Enter</b> 確認送出；也可以從「快速選股名單」下拉選擇股票。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
