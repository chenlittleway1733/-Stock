"""
主畫面 UI 模組：
包含個股儀表板、AI 分析、財務資料、圖表、ETF 曝險等主要畫面。
"""
from ui_common import *

def render_main_page(sidebar_state=None):
    """渲染主畫面。"""
    hi_val = None
    me_val = None
    lo_val = None
    sidebar_state = sidebar_state or {}
    topic_q = sidebar_state.get("topic_q", "")
    f_ok = sidebar_state.get("f_ok", None)
    m_ok = sidebar_state.get("m_ok", None)

    # ==========================================
    # 5. 主畫面開始
    # ==========================================
    st.markdown("## 📈 WAY AI 投資戰情室 版本2.1")

    if st.session_state.fugle_key and not f_ok:
        st.error("🚨 **系統警報**：您輸入的「富果 (Fugle) API Key」驗證失敗！請至左側欄檢查金鑰是否輸入正確。")
    if st.session_state.finmind_key and not m_ok:
        st.error("🚨 **系統警報**：您輸入的「FinMind API Key」驗證失敗！請至左側欄檢查金鑰是否輸入正確。")

    if st.session_state.topic_results == "LOADING":
        with st.spinner(f"🤖 AI 正在連線推演「{topic_q}」..."):
            data, links = get_ai_analysis_final(topic_q, st.session_state.api_key, st.session_state.get('selected_model', 'gemini-3.1-pro-preview'))
            if isinstance(data, dict):
                st.session_state.topic_results = {"data": data, "links": links, "topic": topic_q}
                st.session_state.show_whale = False
                st.rerun()
            else:
                st.error(f"AI 解析失敗或逾時無回應。\n\n詳細原因：{data}")
                st.session_state.topic_results = None

    if isinstance(st.session_state.topic_results, dict):
        t = st.session_state.topic_results
        st.success("✅ AI 議題推演完成！系統已為您捕捉以下關聯受惠股，點擊按鈕即可一鍵切換至該檔股票的戰情室面板！")
    
        ai_topic_html = f"""
        <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #FFD700;'>
            <h3 style='color: white; margin-top: 0;'>💡 議題動態推演：【{t['topic']}】</h3>
            <div style='color: #e0e0e0; font-size: 1.05rem; line-height: 1.6;'>{t['data'].get('reasoning', '無分析內容')}</div>
        </div>
        """
        st.markdown(clean_html(ai_topic_html), unsafe_allow_html=True)
    
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🛡️ 潛力權值股 (點擊切換)")
            for s in [x for x in t['data'].get('stocks', []) if "權值" in x.get('type', '') or "潛力" in x.get('type', '')]:
                st.button(f"📌 {s.get('name', '未知')} ({s.get('id', '')})", on_click=reset_all_states_on_stock_change, args=(s.get('id', ''),), key=f"tp_{s.get('id', '')}", use_container_width=True)
                st.caption(f"理由：{s.get('why', '')}")
        with c2:
            st.markdown("#### 🚀 爆發中小型股 (點擊切換)")
            for s in [x for x in t['data'].get('stocks', []) if "中小" in x.get('type', '') or "爆發" in x.get('type', '')]:
                st.button(f"🔥 {s.get('name', '未知')} ({s.get('id', '')})", on_click=reset_all_states_on_stock_change, args=(s.get('id', ''),), key=f"ts_{s.get('id', '')}", use_container_width=True)
                st.caption(f"理由：{s.get('why', '')}")
            
        if t['links']:
            with st.expander("🔗 查看 AI 參考來源"):
                for link in t['links']: st.markdown(f"- [{link}]({link})")
        st.markdown("---")

    if st.session_state.show_whale:
        st.markdown("### 🐳 近兩周大戶持股比例顯著增加標的")
        whales = [("2317", "鴻海"), ("2382", "廣達"), ("1519", "華城"), ("6669", "緯穎"), ("3324", "雙鴻")]
        cols = st.columns(5)
        for idx, (code, name) in enumerate(whales):
            with cols[idx]: st.button(f"{name}\n({code})", on_click=reset_all_states_on_stock_change, args=(code,), key=f"w_{code}", use_container_width=True)
        st.markdown("---")

    curr_id = st.session_state.selected_stock
    if curr_id:
        # 🚀 絕對防呆宣告：避免因任何例外導致變數未定義而觸發 NameError
        ctx_pe, ctx_fpe, ctx_pb, ctx_peg = "N/A", "N/A", "N/A", "N/A"
        hi_str, me_str, lo_str, ai_tp_str = "N/A", "N/A", "N/A", ""
        latest_rev_month, latest_mom_str = "未知", "N/A"
        latest_rev_notice, latest_rev_display_label = "", "公告月份：未知"
        latest_rev_source = ""
        dy_str, fcf_str, cr_str, fs_str = "N/A", "N/A", "N/A", "N/A"
        ctx_eps, ctx_rg, ctx_eg, ctx_gm, ctx_om, ctx_roe, ctx_de = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
        tp_est_str, cap_warning_html = "無資料", ""

        with st.spinner('同步數據中...'):
            hist, info = get_stock_data(curr_id, st.session_state.fugle_key, st.session_state.finmind_key)
            if info is None: info = {}
            c_name = get_chinese_name(curr_id) or info.get('shortName', curr_id)
        fallback_notes = info.get('__fallback_notes', []) if isinstance(info, dict) else []
        price_source = info.get('__price_source') if isinstance(info, dict) else None
        info_source = info.get('__info_source') if isinstance(info, dict) else None
        if price_source or info_source:
            st.caption(f"🛰️ 資料來源｜股價: {price_source or '未知'}；財務: {info_source or '未知'}")
        if fallback_notes:
            for note in fallback_notes:
                st.info(f"💡 備援提示：{note}")

        if hist is not None and not hist.empty:
            col_title, col_star = st.columns([0.85, 0.15])
            with col_title: st.markdown(f"### 🏢 {c_name} ({curr_id})")
            with col_star:
                in_watch = curr_id in get_watchlist()
                btn_label = "⭐ 移除自選" if in_watch else "☆ 加入自選"
                if st.button(btn_label, use_container_width=True):
                    toggle_watchlist(curr_id, c_name)
                    st.rerun()

            sector_disp = SECTOR_MAP.get(info.get('sector', '未知'), info.get('sector', '未知'))
            industry_profile = get_industry_valuation_profile(curr_id, c_name, sector_disp, info.get('industry', '未知'))
            st.markdown(
                f"**🏷️ 產業分類：** {sector_disp} / {info.get('industry', '未知')}｜"
                f"估值模型：{industry_profile.get('model_label', '一般產業')}｜"
                f"題材標籤：{industry_profile.get('themes_text', '—')}"
            )
            if industry_profile.get('pe_trap_warning'):
                st.warning("⚠️ 本產業具有 P/E 陷阱風險：低 P/E 不一定代表低估，請優先檢查 P/B、週期位置、報價或訂單落地。")
            if industry_profile.get('pe_model_suitable') is False:
                st.warning("⚠️ 本分類不適合使用一般 P/E 公式估值作為買進依據，應以事件、訂單、籌碼與財報落地程度評估。")
            with st.expander("📖 查看公司詳細營業項目簡介 (自動英翻中)"):
                st.write(translate_to_zh(info.get('longBusinessSummary', '暫無簡介。')))

            # ==========================================
            # ⚡ 即時報價
            # ==========================================
            st.markdown("#### ⚡ 即時報價與交易資訊")
            today_data = hist.iloc[-1]
            prev_data = hist.iloc[-2] if len(hist) > 1 else today_data
        
            curr_p = s_float(today_data.get('Close'), 0)
            open_p = s_float(today_data.get('Open'), 0)
            high_p = s_float(today_data.get('High'), 0)
            low_p = s_float(today_data.get('Low'), 0)
            vol_shares = s_float(today_data.get('Volume'), 0)
        
            vol_lots = int(vol_shares // 1000) if vol_shares else 0
            prev_vol_lots = int(s_float(prev_data.get('Volume'), 0) // 1000) if len(hist) > 1 else 0
        
            prev_close = s_float(info.get('previousClose'), s_float(prev_data.get('Close'), 0))
            change = curr_p - prev_close if prev_close else 0
            change_pct = (change / prev_close) * 100 if prev_close else 0
            amp = ((high_p - low_p) / prev_close) * 100 if prev_close and prev_close > 0 else 0
            avg_price = (high_p + low_p + curr_p) / 3 if curr_p else 0
            turnover_100m = (vol_shares * avg_price) / 100000000
        
            def get_color(val, base):
                if val > base: return "#ff4d4d"
                elif val < base: return "#00cc66"
                return "#ffffff"
            
            c_curr = get_color(curr_p, prev_close)
            c_open = get_color(open_p, prev_close)
            c_high = get_color(high_p, prev_close)
            c_low = get_color(low_p, prev_close)
            c_change = get_color(change, 0)
            arrow = "▲" if change > 0 else ("▼" if change < 0 else "")
        
            quote_html = f"""
            <style>
            .q-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 30px; background: #1e1e1e; padding: 15px 20px; border-radius: 8px; font-family: sans-serif; margin-bottom: 20px; border: 1px solid #333; }}
            .q-item {{ display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 4px; }}
            .q-label {{ color: #aaa; font-size: 1rem; }}
            .q-val {{ font-weight: bold; font-size: 1.1rem; }}
            </style>
            <div class="q-container">
                <div class="q-item"><span class="q-label">成交</span><span class="q-val" style="color: {c_curr};">{curr_p:,.2f}</span></div>
                <div class="q-item"><span class="q-label">昨收</span><span class="q-val" style="color: #fff;">{prev_close:,.2f}</span></div>
                <div class="q-item"><span class="q-label">開盤</span><span class="q-val" style="color: {c_open};">{open_p:,.2f}</span></div>
                <div class="q-item"><span class="q-label">漲跌幅</span><span class="q-val" style="color: {c_change};">{arrow} {abs(change_pct):.2f}%</span></div>
                <div class="q-item"><span class="q-label">最高</span><span class="q-val" style="color: {c_high};">{high_p:,.2f}</span></div>
                <div class="q-item"><span class="q-label">漲跌</span><span class="q-val" style="color: {c_change};">{arrow} {abs(change):.2f}</span></div>
                <div class="q-item"><span class="q-label">最低</span><span class="q-val" style="color: {c_low};">{low_p:,.2f}</span></div>
                <div class="q-item"><span class="q-label">總量 (張)</span><span class="q-val" style="color: #ffd700;">{vol_lots:,}</span></div>
                <div class="q-item"><span class="q-label">均價</span><span class="q-val" style="color: #fff;">{avg_price:,.2f}</span></div>
                <div class="q-item"><span class="q-label">昨量 (張)</span><span class="q-val" style="color: #fff;">{prev_vol_lots:,}</span></div>
                <div class="q-item"><span class="q-label">成交金額(億)</span><span class="q-val" style="color: #fff;">{turnover_100m:,.2f}</span></div>
                <div class="q-item"><span class="q-label">振幅</span><span class="q-val" style="color: #fff;">{amp:.2f}%</span></div>
            </div>
            """
            st.markdown(clean_html(quote_html), unsafe_allow_html=True)

            # ==========================================
            # 📌 主要 ETF 持有概況 + 獨立 AI ETF 補查
            # ==========================================
            st.markdown("#### 📌 主要 ETF 持有概況")
            with st.expander(f"查看含有 {c_name} ({curr_id}) 的 ETF", expanded=False):
                st.caption("一般頁面僅做快速查詢，不使用 AI、不掃描 MoneyDJ / Pocket / CMoney 快取，避免等待過久。此區主要來自 Yahoo 個股 ETF 頁，可能只涵蓋主要 / 前十大 ETF，不代表完整 ETF 持股清單。")

                try:
                    etf_holders = get_stock_etf_holders(curr_id, c_name)
                except Exception as e:
                    etf_holders = []
                    st.warning(f"⚠️ ETF 快速資料源暫時無法取得：{str(e)[:120]}")

                def _render_etf_holder_table(rows, title, source_tag):
                    rows = rows or []
                    if not rows:
                        return False
                    table_rows = []
                    for r in rows:
                        if not isinstance(r, dict):
                            continue
                        weight = r.get("weight")
                        try:
                            weight_text = f"{float(weight):.2f}%" if weight is not None and str(weight).strip() != "" else "N/A"
                        except Exception:
                            weight_text = str(weight) if weight else "N/A"
                        table_rows.append({
                            "ETF名稱": r.get("etf_name") or "",
                            "代號": r.get("etf_code") or "",
                            "持股比例": weight_text,
                            "資料日期": r.get("data_date") or "來源未揭露",
                            "來源": r.get("source") or source_tag,
                            "資料性質": r.get("data_type") or source_tag,
                        })
                    if not table_rows:
                        return False
                    st.markdown(title)
                    df_etf = pd.DataFrame(table_rows)
                    st.dataframe(df_etf, use_container_width=True, hide_index=True)
                    return True

                has_system_etf = _render_etf_holder_table(etf_holders, "**主要 / 前十大 ETF 快速查詢**", "主要/前十大快速查詢")
                if not has_system_etf:
                    st.info("目前快速資料源查無 ETF 持有資料，或網站版面暫時無法解析。")

                st.caption("⚠️ 此區不保證完整。像 00981A 這類主動式 ETF 可能因 Yahoo 個股頁只列主要/前十大而未出現；需要完整交叉檢查時，請按下方 AI 按鈕。")

                st.markdown("---")
                st.markdown("#### 🤖 AI 查完整 ETF 持有狀況")
                st.caption("此按鈕與『AI 全方位校對與補齊財報』分開執行；只有按下時才會使用 AI + 搜尋補查 ETF，不會拖慢財報校對。")

                if "ai_etf_holders" not in st.session_state:
                    st.session_state.ai_etf_holders = {}

                if st.button("🤖 AI 查完整 ETF 持有狀況", disabled=not st.session_state.api_key, key=f"ai_etf_lookup_{curr_id}", use_container_width=True, help="獨立查詢 ETF 持股；會特別檢查主動式 ETF，例如 00981A、00987A、00988A、00400A、00403A。"):
                    with st.spinner("AI 正在獨立查詢 ETF 持有狀況，請稍候...（不會執行財報校對）"):
                        ai_etf_data = get_etf_holders_from_ai(curr_id, c_name, st.session_state.api_key, get_selected_model_id())
                        st.session_state.ai_etf_holders[curr_id] = ai_etf_data
                    st.rerun()

                ai_etf_data = st.session_state.ai_etf_holders.get(curr_id) if isinstance(st.session_state.get("ai_etf_holders"), dict) else None
                if isinstance(ai_etf_data, dict) and ai_etf_data.get("error"):
                    st.error(f"AI ETF 查詢失敗：{ai_etf_data.get('error')}")
                elif isinstance(ai_etf_data, dict):
                    ai_etf_rows = ai_etf_data.get("etf_holders_ai", [])
                    if ai_etf_rows:
                        _render_etf_holder_table(ai_etf_rows, "**🤖 AI 完整 ETF 補查結果**", "AI完整ETF補查")
                        st.caption("⚠️ AI ETF 資料為獨立聯網補查結果，只作交叉比對；正式持股仍請以投信公告、PCF 或 ETF 官方持股明細為準。")
                    else:
                        st.info("AI 已查詢，但沒有回傳可用的 ETF 持股清單。")
                    if ai_etf_data.get("summary"):
                        st.caption(f"AI 摘要：{ai_etf_data.get('summary')}")
                else:
                    st.caption("尚未執行 AI ETF 補查。")

            st.markdown("---")

            # ==========================================
            # 🌍 國際連動與動態時間趨勢推估
            # ==========================================
            st.markdown("<br>", unsafe_allow_html=True)
            trend_data = get_global_market_trend()
            if trend_data:
                target_day_text = trend_data.get('target_day', '明日')
                time_status_text = trend_data.get('time_status', '')
                st.markdown(f"#### 🌍 國際連動與{target_day_text}趨勢推估 {time_status_text}", unsafe_allow_html=True)
            
                def c_color(v): return "#ff4d4d" if v > 0 else "#00cc66" if v < 0 else "#fff"
                trend_html = f"""
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {trend_data['color']}; margin-bottom: 20px; border-top:1px solid #333; border-right:1px solid #333; border-bottom:1px solid #333;'>
                    <div style='font-size:1.15rem; font-weight:bold; color:{trend_data['color']}; margin-bottom:10px;'>{trend_data['trend']}</div>
                    <div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;'>
                        <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>費城半導體 (^SOX)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["sox_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["sox"])};'>({trend_data["sox"]:+.2f}%)</span></div>
                        <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>台積電 ADR (TSM)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["tsm_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["tsm"])};'>({trend_data["tsm"]:+.2f}%)</span></div>
                        <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>納斯達克期貨 (NQ=F)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["nq_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["nq"])};'>({trend_data["nq"]:+.2f}%)</span></div>
                        <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>台股 ETF (EWT)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["ewt_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["ewt"])};'>({trend_data["ewt"]:+.2f}%)</span></div>
                    </div>
                </div>
                """
                st.markdown(clean_html(trend_html), unsafe_allow_html=True)

            # ==========================================
            # 📰 近期財報與法說會新聞
            # ==========================================
            st.markdown("#### 📰 近期財報與法說會新聞")
            news_list = get_stock_news(curr_id)
            if news_list:
                for n in news_list[:5]:
                    publish_time = datetime.datetime.fromtimestamp(n['timestamp']).strftime('%Y-%m-%d %H:%M') if n['timestamp'] else "未知時間"
                    st.markdown(f"🔸 [{n['title']}]({n['link']}) <span style='color:gray; font-size:0.8rem;'>- {n['publisher']} ({publish_time})</span>", unsafe_allow_html=True)
            else:
                st.caption("目前無符合條件的基本面或財報新聞。")
            st.markdown("---")

            # ==========================================
            # 💼 財務基本面與獲利基準微調
            # ==========================================
            col_fin_title, col_fin_btn = st.columns([0.6, 0.4])
            with col_fin_title:
                st.markdown("#### 💼 財務基本面與獲利基準微調")
            with col_fin_btn:
                if st.button("🪄 啟動 AI 全方位校對與補齊財報", disabled=not st.session_state.api_key, use_container_width=True, help="點此讓 AI 上網搜尋最新財報與估值指標，並與現有資料進行比對"):
                    with st.spinner("AI 正在聯網為您強行抓取最新財報數據，請稍候...（Pro Only 最多重試 3 次，約需 30-90 秒）"):
                        selected_model = get_selected_model_id()
                        fetched_data = get_financials_from_ai(c_name, curr_id, st.session_state.api_key, selected_model)
                    
                        if isinstance(fetched_data, dict) and "error" not in fetched_data:
                            core_fin_keys = ["pe", "trailing_eps", "ttm_eps", "latest_quarter_eps", "forward_eps", "forward_eps_ai", "forward_eps_consensus", "pb", "gross_margin", "operating_margin", "roe", "yoy", "target_price", "mom", "dividend_yield"]
                            has_effective_fin_data = any(fetched_data.get(k) not in (None, "", "null") for k in core_fin_keys)
                            if not has_effective_fin_data:
                                st.warning("⚠️ AI 本次有回應，但未抓到可用財報欄位（可能是來源暫無資料或回傳皆為 null）。請稍後重試或切換標的。")
                                st.session_state.ai_fetched_financials.pop(curr_id, None)
                                st.stop()

                            model_label_map = {
                                "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview (付費版)",
                            }
                            model_id = fetched_data.get('model_used', selected_model)
                            model_label = model_label_map.get(model_id, model_id)
                            fallback_reason = fetched_data.get('fallback_reason') or ""
                            search_enabled = fetched_data.get('ai_search_enabled', True)
                            if fallback_reason:
                                model_label = f"{model_label}｜{fallback_reason}"
                            fetched_data['model_used'] = model_label
                            # 綁定本次 AI 財報資料所屬標的，避免切換股票後舊資料被誤套用。
                            fetched_data['_stock_id'] = str(curr_id)
                            fetched_data['_stock_name'] = str(c_name)
                            if not search_enabled:
                                st.warning("⚠️ 本次 AI 財報補齊未啟用 Google Search，資料不得納入公式極限價。")
                            elif fallback_reason:
                                st.warning(f"⚠️ {fallback_reason}")
                            st.session_state.ai_fetched_financials[curr_id] = fetched_data
                            st.rerun()
                        elif isinstance(fetched_data, dict) and "error" in fetched_data:
                            st.error(f"🚨 AI 抓取失敗：{fetched_data['error']}")
                            if fetched_data.get("last_error"):
                                st.caption(f"最後錯誤：{fetched_data.get('last_error')}")
                            if fetched_data.get("attempts"):
                                with st.expander("🧾 查看 Pro Only 同模型重試紀錄", expanded=False):
                                    st.json(fetched_data.get("attempts"))
                        else:
                            st.error("🚨 AI 暫時無法找到確切數據，或請求遭拒。")

                temp_ai_fin = st.session_state.ai_fetched_financials.get(curr_id, {})
                # 防止舊版 session 或切換股票後殘留的 AI 財報資料誤套到目前標的。
                if isinstance(temp_ai_fin, dict) and temp_ai_fin:
                    bound_stock_id = str(temp_ai_fin.get('_stock_id') or curr_id)
                    if bound_stock_id != str(curr_id):
                        st.session_state.ai_fetched_financials.pop(curr_id, None)
                        temp_ai_fin = {}
                has_ai_fin_fetch = bool(temp_ai_fin)
                if temp_ai_fin.get('model_used'):
                    st.markdown(f"<div style='text-align:right; color:#FFD700; font-size:0.85rem; margin-top:5px;'>🤖 驅動核心: <b>{temp_ai_fin['model_used']}</b></div>", unsafe_allow_html=True)
                    if temp_ai_fin.get("_ai_validation_warnings"):
                        st.warning("🧪 AI 財報 JSON 已觸發合理性校驗；部分欄位已自動校正或設為 NULL，詳情可展開原始回報面板查看。")
                    raw_state_key = f"show_ai_raw_panel_{curr_id}"
                    if raw_state_key not in st.session_state:
                        st.session_state[raw_state_key] = False

                    btn_label = "🧾 隱藏本次 AI 查詢與回報資料" if st.session_state[raw_state_key] else "🧾 顯示本次 AI 查詢與回報資料"
                    if st.button(btn_label, key=f"toggle_ai_raw_btn_{curr_id}", use_container_width=True):
                        st.session_state[raw_state_key] = not st.session_state[raw_state_key]

                    if st.session_state[raw_state_key]:
                        st.caption("以下為本次 AI 全方位校對與補齊財報的查詢內容與原始回報：")
                        query_preview = temp_ai_fin.get("query_payload")
                        if query_preview:
                            st.code(query_preview, language="json")
                        ai_source_df = build_ai_source_trace_report(temp_ai_fin)
                        if ai_source_df is not None and not ai_source_df.empty:
                            st.markdown("##### 🔗 AI 逐欄來源追蹤")
                            st.dataframe(ai_source_df, use_container_width=True, hide_index=True)
                        ai_validation_warnings = temp_ai_fin.get("_ai_validation_warnings") or []
                        if ai_validation_warnings:
                            st.markdown("##### 🧪 AI JSON 合理性驗證")
                            st.warning(temp_ai_fin.get("_ai_validation_status", "⚠️ AI 欄位已校正"))
                            for w in ai_validation_warnings[:20]:
                                st.caption(f"- {w}")
                        elif temp_ai_fin.get("_ai_validation_status"):
                            st.success(temp_ai_fin.get("_ai_validation_status"))
                        st.json(temp_ai_fin)    
            df_rev_bk = get_monthly_revenue(curr_id, st.session_state.finmind_key)
            df_per_bk = get_pe_pb_data(curr_id, st.session_state.finmind_key)
            fm_health = get_finmind_financial_health(curr_id, st.session_state.finmind_key)
        
            if df_rev_bk is not None and not df_rev_bk.empty:
                if 'actual_revenue_month' in df_rev_bk.columns:
                    latest_rev_month = normalize_revenue_month(df_rev_bk['actual_revenue_month'].iloc[-1])
                else:
                    latest_rev_month = normalize_revenue_month(df_rev_bk['Month'].iloc[-1])
                latest_mom_val = s_float(df_rev_bk['MoM'].iloc[-1])
                latest_rev_source = str(df_rev_bk['revenue_source'].iloc[-1]) if 'revenue_source' in df_rev_bk.columns else "月營收資料源"
                rev_notice_pack = build_revenue_month_notice(latest_rev_month)
                latest_rev_notice = rev_notice_pack.get('notice', '')
                latest_rev_display_label = rev_notice_pack.get('display_label', f"公告月份：{latest_rev_month}")
            else:
                latest_rev_month = "無資料"
                latest_mom_val = None
                latest_rev_notice = "未取得月營收資料，營收 YoY / MoM 將改用其他資料源或顯示 N/A。"
                latest_rev_display_label = "公告月份：未取得"
                latest_rev_source = ""
        
            if latest_rev_notice:
                st.info(f"📅 月營收公告月份提示：{latest_rev_notice}")

            pe_ratio = s_float(info.get('trailingPE'))
            if (pe_ratio is None or pe_ratio > 1000) and df_per_bk is not None and not df_per_bk.empty:
                if (pd.Timestamp.today() - df_per_bk.iloc[-1]['date']).days < 30: pe_ratio = s_float(df_per_bk['PER'].iloc[-1])
            pb_ratio = s_float(info.get('priceToBook'))
            if (pb_ratio is None or pb_ratio > 500) and df_per_bk is not None and not df_per_bk.empty and 'PBR' in df_per_bk.columns:
                pb_ratio = s_float(df_per_bk['PBR'].iloc[-1])
            
            roe = s_float(info.get('returnOnEquity'))
            sys_de = s_float(info.get('debtToEquity'))
            if sys_de is not None: sys_de = sys_de / 100.0  
        
            gross_margin = s_float(info.get('grossMargins'))
            op_margin = s_float(info.get('operatingMargins'))
        
            if gross_margin is None: gross_margin = fm_health.get('grossMargins')
            if op_margin is None: op_margin = fm_health.get('operatingMargins')
            if sys_de is None: sys_de = fm_health.get('debtToEquity')
        
            rev_growth = s_float(info.get('revenueGrowth'))
            if rev_growth is None and df_rev_bk is not None and not df_rev_bk.empty:
                rev_growth = s_float(df_rev_bk['YoY'].iloc[-1]) / 100.0
            earn_growth = s_float(info.get('earningsGrowth'))
        
            t_eps = s_float(info.get('trailingEps'))
            if t_eps is None and pe_ratio is not None and pe_ratio > 0 and curr_p > 0:
                t_eps = curr_p / pe_ratio
            
            sys_f_eps_calc = s_float(info.get('forwardEps'))
            # EPS 拆欄：yfinance 多數只提供 trailingEps / forwardEps；最新單季與完整年度 EPS 先保留 NULL，避免誤標口徑。
            sys_latest_quarter_eps = None
            sys_ttm_eps = t_eps
            sys_fiscal_year_eps = None
            sys_forward_eps_system = sys_f_eps_calc

            if pe_ratio is None and t_eps is None and not st.session_state.ai_fetched_financials.get(curr_id):
                st.warning("⚠️ **全球連線受阻**：目前免費資料庫限制了部分股票的抓取。👉 **解決方案**：請點擊上方【🪄 啟動 AI 全方位校對與補齊財報】讓 AI 強制為您抓回最新數據！")
        
            ai_fin = st.session_state.ai_fetched_financials.get(curr_id, {})
            if isinstance(ai_fin, dict) and ai_fin:
                bound_stock_id = str(ai_fin.get('_stock_id') or curr_id)
                if bound_stock_id != str(curr_id):
                    ai_fin = {}
                    st.session_state.ai_fetched_financials.pop(curr_id, None)
            has_ai_fin_fetch = bool(ai_fin)
            ai_pe = s_float(ai_fin.get('pe')) if has_ai_fin_fetch else None
            ai_pb = s_float(ai_fin.get('pb')) if has_ai_fin_fetch else None
            # EPS 拆欄：避免最新單季、TTM、年度、Forward EPS 混用。
            ai_latest_quarter_eps = pick_first_number(ai_fin.get('latest_quarter_eps')) if has_ai_fin_fetch else None
            ai_ttm_eps = pick_first_number(ai_fin.get('ttm_eps'), ai_fin.get('trailing_eps')) if has_ai_fin_fetch else None
            ai_fiscal_year_eps = pick_first_number(ai_fin.get('fiscal_year_eps')) if has_ai_fin_fetch else None
            ai_forward_eps_ai = pick_first_number(ai_fin.get('forward_eps_ai'), ai_fin.get('forward_eps')) if has_ai_fin_fetch else None
            ai_forward_eps_consensus = pick_first_number(ai_fin.get('forward_eps_consensus')) if has_ai_fin_fetch else None
            ai_t_eps = ai_ttm_eps
            ai_f_eps_calc = pick_first_number(ai_forward_eps_consensus, ai_forward_eps_ai) if has_ai_fin_fetch else None
            ai_yoy = s_float(ai_fin.get('yoy')) if has_ai_fin_fetch else None
            ai_gm = s_float(ai_fin.get('gross_margin')) if has_ai_fin_fetch else None
            ai_om = s_float(ai_fin.get('operating_margin')) if has_ai_fin_fetch else None
            ai_roe = s_float(ai_fin.get('roe')) if has_ai_fin_fetch else None
            ai_de = s_float(ai_fin.get('debt_to_equity')) if has_ai_fin_fetch else None
            ai_dy = s_float(ai_fin.get('dividend_yield')) if has_ai_fin_fetch else None
            
            # 接取剛增加的三項防禦/主力籌碼指標
            ai_fcf = s_float(ai_fin.get('free_cash_flow')) if has_ai_fin_fetch else None
            ai_cr = s_float(ai_fin.get('current_ratio')) if has_ai_fin_fetch else None
            ai_shares = s_float(ai_fin.get('shares_outstanding')) if has_ai_fin_fetch else None
        
            # 🚀 接收 AI 抓到的目標價、MoM 與 Dividend Yield，並覆蓋錯誤資料
            ai_target_price = s_float(ai_fin.get('target_price')) if has_ai_fin_fetch else None
            ai_hi_val = s_float(ai_fin.get('target_price_high')) if has_ai_fin_fetch else None
            ai_me_val = (s_float(ai_fin.get('target_price_avg')) or ai_target_price) if has_ai_fin_fetch else None
            ai_lo_val = s_float(ai_fin.get('target_price_low')) if has_ai_fin_fetch else None
            ai_analyst_count = ai_fin.get('target_price_analyst_count') if has_ai_fin_fetch else None
            ai_target_rationale = str(ai_fin.get('target_price_rationale') or "").strip() if has_ai_fin_fetch else ""
            ai_mom = normalize_financial_ratio(ai_fin.get('mom')) if has_ai_fin_fetch else None
            if ai_mom is not None: 
                latest_mom_val = ai_mom * 100

            # ==========================================
            # 🧯 資料品質閘門：避免欄位錯位直接進估值模型
            # ==========================================
            sys_vals_for_check = {
                "gross_margin": gross_margin,
                "operating_margin": op_margin,
                "rev_growth": rev_growth,
                "debt_to_equity": sys_de,
            }
            ai_vals_for_check = {
                "gross_margin": ai_gm,
                "operating_margin": ai_om,
                "rev_growth": ai_yoy,
                "debt_to_equity": ai_de,
            }
            corrected_sys, corrected_ai, dq_warnings = validate_and_correct_financial_metrics(
                sys_vals_for_check,
                ai_vals_for_check,
                monthly_rev_df=df_rev_bk,
                stock_id=curr_id,
                stock_name=c_name,
            )
            # ✅ 重要：從這一行開始，所有估值、Markdown 顯示與 AI prompt 都只使用「校正後」資料。
            # 不再讓校驗前的 gross_margin / op_margin / rev_growth / sys_de 進入畫面或公式極限價演算法。
            gross_margin = corrected_sys.get("gross_margin")
            op_margin = corrected_sys.get("operating_margin")
            rev_growth = corrected_sys.get("rev_growth")
            sys_de = corrected_sys.get("debt_to_equity")
            ai_gm = corrected_ai.get("gross_margin")
            ai_om = corrected_ai.get("operating_margin")
            ai_yoy = corrected_ai.get("rev_growth")
            ai_de = corrected_ai.get("debt_to_equity")

            # 明確宣告「顯示層專用」變數，避免日後維護時誤拿校驗前欄位組 Markdown。
            display_rev_growth = rev_growth
            display_ai_yoy = ai_yoy
            display_gross_margin = gross_margin
            display_operating_margin = op_margin
            display_ai_gross_margin = ai_gm
            display_ai_operating_margin = ai_om
            display_debt_to_equity = sys_de
            display_ai_debt_to_equity = ai_de

            if dq_warnings:
                # 右下角短提示：讓操盤手知道資料已被校正，不是靜默改值
                toast_key = f"dq_toast_{curr_id}_{hash(tuple(dq_warnings))}"
                if not st.session_state.get(toast_key, False):
                    try:
                        st.toast(f"🩺 目前標的 {c_name} ({curr_id}) 觸發資料品質校驗，已啟動自動校正／NULL 防護。", icon="🩺")
                    except Exception:
                        pass
                    st.session_state[toast_key] = True

                with st.expander("🩺 資料品質校驗提醒", expanded=True):
                    for w in dq_warnings:
                        st.warning(w)
        
            if latest_mom_val is not None:
                latest_mom_str = f"{latest_mom_val:.2f}%"
            else:
                latest_mom_str = "N/A"
        
            # 設定 AI 標籤與時間後綴
            raw_ai_period = str(ai_fin.get('data_period', '')).replace('None', '').strip() if has_ai_fin_fetch else ""
            ai_label = "AI捉取"
            ai_period_val = f"({raw_ai_period})" if raw_ai_period else ""
        
            # 🚀 在目標價 html 生成前，先宣告給 prompt 用的純文字變數，絕對防禦 NameError
            ai_tp_str = f"{ai_target_price:.1f}" if ai_target_price is not None else "未捕捉到"
            target_price_html = ""
            cap_warning_html = ""

            eff_pe = pe_ratio if pe_ratio is not None else ai_pe
            eff_pb = pb_ratio if pb_ratio is not None else ai_pb
            eff_t_eps = t_eps if t_eps is not None else ai_t_eps
            eff_rg = rev_growth if rev_growth is not None else ai_yoy
            eff_eg = earn_growth if earn_growth is not None else ai_yoy
            eff_gm = gross_margin if gross_margin is not None else ai_gm
            eff_om = op_margin if op_margin is not None else ai_om
            eff_roe = roe if roe is not None else ai_roe
            eff_de = sys_de if sys_de is not None else ai_de

            if eff_pe and eff_pe > 0 and eff_pb and eff_pb > 0:
                eff_roe = eff_pb / eff_pe
                roe = eff_roe 
            
            if ai_pe and ai_pe > 0 and ai_pb and ai_pb > 0:
                ai_roe = ai_pb / ai_pe
        
            # 只有已按下 AI 財報補齊且 AI 有基礎欄位時，才推算 AI Forward EPS。
            # 未按 AI 按鈕時，不得把系統值包裝成「AI推估」。
            if has_ai_fin_fetch and ai_f_eps_calc is None and ai_t_eps is not None and ai_yoy is not None and -1 <= ai_yoy <= 5:
                ai_f_eps_calc = ai_t_eps * (1 + ai_yoy)
                # 這是 AI TTM EPS × AI 成長率推估，不是法人共識。
                ai_forward_eps_ai = ai_f_eps_calc
            
            if sys_f_eps_calc is None and t_eps is not None and earn_growth is not None and -1 <= earn_growth <= 5:
                sys_f_eps_calc = t_eps * (1 + earn_growth)
            sys_forward_eps_system = sys_f_eps_calc

            # EPS 拆欄報告：顯示每一種 EPS 口徑，不再用「目前 EPS」混稱。
            eps_rows = [
                {"field": "最新單季 EPS", "definition": "最新已公告季度 EPS；用來判斷短期獲利動能", "system_value": sys_latest_quarter_eps, "ai_value": ai_latest_quarter_eps, "adopted_value": ai_latest_quarter_eps, "source": "AI補齊" if ai_latest_quarter_eps is not None else "未取得", "period": ai_period_val or raw_ai_period or "需查最新財報", "notes": "系統資料源未穩定提供單季 EPS，避免用 TTM 代替。"},
                {"field": "TTM EPS", "definition": "近四季 EPS 合計；用於歷史 P/E", "system_value": sys_ttm_eps, "ai_value": ai_ttm_eps, "adopted_value": sys_ttm_eps if sys_ttm_eps is not None else ai_ttm_eps, "source": "系統優先" if sys_ttm_eps is not None else ("AI補齊" if ai_ttm_eps is not None else "未取得"), "period": "yfinance trailingEps / 現價÷P/E 反推" if sys_ttm_eps is not None else (raw_ai_period or "AI未揭露"), "notes": "原 trailing_eps 口徑統一視為 TTM EPS。"},
                {"field": "完整年度 EPS", "definition": "最近完整會計年度 EPS；用來看年度基準", "system_value": sys_fiscal_year_eps, "ai_value": ai_fiscal_year_eps, "adopted_value": ai_fiscal_year_eps, "source": "AI補齊" if ai_fiscal_year_eps is not None else "未取得", "period": raw_ai_period or "需查年報", "notes": "不得用 TTM EPS 直接冒充完整年度 EPS。"},
                {"field": "Forward EPS－系統", "definition": "yfinance forwardEps；缺值時由 TTM EPS × 成長率推估", "system_value": sys_forward_eps_system, "ai_value": None, "adopted_value": sys_forward_eps_system, "source": "系統/反推" if sys_forward_eps_system is not None else "未取得", "period": "forwardEps 或 earningsGrowth 推估", "notes": "用於系統 Forward P/E 與公式估值。"},
                {"field": "Forward EPS－AI", "definition": "AI 從新聞/券商報告抓取或推估的 Forward EPS", "system_value": None, "ai_value": ai_forward_eps_ai, "adopted_value": ai_forward_eps_ai, "source": "AI補齊" if ai_forward_eps_ai is not None else "未取得", "period": raw_ai_period or "AI未揭露", "notes": "與法人共識 EPS 分開，避免單一來源誤當共識。"},
                {"field": "Forward EPS－法人共識", "definition": "多家法人共識 EPS；若無明確樣本則為 NULL", "system_value": None, "ai_value": ai_forward_eps_consensus, "adopted_value": ai_forward_eps_consensus, "source": "AI/法人共識" if ai_forward_eps_consensus is not None else "未取得", "period": raw_ai_period or "AI未揭露", "notes": "後續可操作估值應優先考慮此欄；無共識不可視為強共識。"},
            ]
            eps_report_df = build_eps_breakdown_report(eps_rows)
            with st.expander("🧾 EPS 口徑拆欄（單季 / TTM / 年度 / Forward）", expanded=False):
                st.caption("避免把最新單季 EPS、TTM EPS、完整年度 EPS、Forward EPS 混稱為『目前 EPS』。目前估值仍以系統 Forward EPS 優先，AI EPS 作為補齊與交叉校對。")
                st.dataframe(eps_report_df, use_container_width=True, hide_index=True)

            # ==========================================
            # 🚀 財務儀表板 (乾淨版)
            # ==========================================
            col_eps1, col_eps2 = st.columns([1, 1])
            with col_eps1:
                target_peg_adj = st.selectbox(
                    "🎯 估值情境 (目標 PEG)", 
                    [1.0, 1.2, 1.5], 
                    format_func=lambda x: "保守 (1.0x)" if x==1.0 else ("穩健 (1.2x)" if x==1.2 else "樂觀高空 (1.5x)"),
                    index=0,
                    help="教練密技：目標價逆推公式的乘數。大盤熱度高或作夢空間大時可調升至 1.5。"
                )
            with col_eps2:
                # ⚙️ 第 17-B 階段：Dynamic Cap 2.0 初算。
                # 此處使用已取得的 EPS / 毛利率 / ROE / 題材 / 流動性資料建立可解釋倍率。
                try:
                    dynamic_cap_pack = calculate_dynamic_cap_v2(
                        stock_id=curr_id,
                        stock_name=c_name,
                        current_price=curr_p,
                        info=info,
                        hist_data=hist,
                        industry_profile=industry_profile,
                        gross_margin=eff_gm,
                        roe=eff_roe,
                        debt_to_equity=eff_de,
                        revenue_yoy=eff_rg,
                        ttm_eps=eff_t_eps,
                        system_forward_eps=sys_forward_eps_system,
                        ai_forward_eps=ai_forward_eps_ai,
                        consensus_forward_eps=ai_forward_eps_consensus,
                        ai_ttm_eps=ai_t_eps,
                        pb_ratio=eff_pb,
                        divergence_warnings=[],
                        dq_warnings=dq_warnings,
                    )
                except Exception as e:
                    log_exception("DynamicCapV2", "ui_main:calculate_dynamic_cap_v2", e)
                    dynamic_cap_pack = {"available": False, "valuation_mode": "fallback", "final_cap": industry_profile.get('cap_hint') or 30.0, "report": pd.DataFrame()}

                if dynamic_cap_pack.get("available") and dynamic_cap_pack.get("final_cap") is not None:
                    suggested_cap = float(dynamic_cap_pack.get("final_cap"))
                    cap_reason = f"Dynamic Cap 2.0 最終建議倍率：{suggested_cap:.1f}x。已採 17-B-2 全產業校準同步：產業基準 × 成長/品質/題材/規模/地緣係數，再乘資料、估值與流動性折扣，並套用產業 hard ceiling。"
                else:
                    suggested_cap = float(industry_profile.get('cap_hint') or 30.0)
                    cap_reason = f"此產業主要估值模式為 {dynamic_cap_pack.get('valuation_mode', industry_profile.get('primary_valuation', 'N/A'))}，P/E Cap 僅作輔助；後續請優先看 P/B / 週期 / 題材落地。"

                target_pe_cap = st.number_input("⚙️ 動態本益比天花板 (Dynamic Cap 2.0)", value=float(suggested_cap), step=5.0, help="第 17-B-2 階段：使用全產業校準表，產業基準 × 成長/品質/題材/規模/地緣係數，再乘資料可信度、估值風險與流動性折扣。")
                if dynamic_cap_pack.get("available"):
                    # 使用者仍可手動覆寫 Cap；若覆寫，估值公式採手動值，拆解表仍保留系統建議值。
                    dynamic_cap_pack["user_selected_cap"] = target_pe_cap
                st.markdown(f"<div style='color:#00bfff; font-size:0.75rem; margin-top:-10px; line-height:1.2;'>💡 {cap_reason}</div>", unsafe_allow_html=True)

            is_base_normalized = False 

            eff_f_eps = sys_f_eps_calc
            eps_source_text = f"海外系統或反推 ({eff_f_eps:.2f}元)" if eff_f_eps is not None else "系統預估 (無資料)"
            
            # 使用新的排版函數呼叫
            f_eps_display = build_cmp_dual_str(t_eps, sys_f_eps_calc, ai_t_eps, ai_f_eps_calc, 'num', 'num', 'AI推估', show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
    
            sys_forward_pe = s_float(info.get('forwardPE'))
            if sys_forward_pe is None and eff_f_eps is not None and eff_f_eps > 0: sys_forward_pe = curr_p / eff_f_eps
        
            ai_fpe = curr_p / ai_f_eps_calc if has_ai_fin_fetch and ai_f_eps_calc and ai_f_eps_calc > 0 else None
            eff_forward_pe = sys_forward_pe if sys_forward_pe is not None else ai_fpe
        
            if eff_f_eps is not None and t_eps is not None and t_eps > 0:
                if t_eps < 0.5:
                    safe_base_eps = 0.5
                    is_base_normalized = True
                else: safe_base_eps = t_eps
                real_cg = (eff_f_eps - safe_base_eps) / safe_base_eps
            else: real_cg = earn_growth
        
            orig_peg = sys_forward_pe / (real_cg * 100) if sys_forward_pe is not None and real_cg is not None and real_cg > 0 else None
        
            ai_cg = None
            if has_ai_fin_fetch:
                if ai_f_eps_calc is not None and ai_t_eps is not None and ai_t_eps > 0:
                    safe_base_eps_ai = 0.5 if ai_t_eps < 0.5 else ai_t_eps
                    ai_cg = (ai_f_eps_calc - safe_base_eps_ai) / safe_base_eps_ai
                else:
                    ai_cg = ai_yoy
            
            ai_peg = ai_fpe / (ai_cg * 100) if has_ai_fin_fetch and ai_fpe is not None and ai_cg is not None and ai_cg > 0 else None
        
            eff_peg = orig_peg if orig_peg is not None else ai_peg
            if real_cg is not None and real_cg <= 0: eff_peg = -999

            # ==========================================
            # 🩺 統一資料品質報告：把系統/AI/採用值與期間集中呈現
            # ==========================================
            dq_note_text = "；".join(dq_warnings) if dq_warnings else ""
            ai_period_text = raw_ai_period if raw_ai_period else "AI未啟動或未揭露期間"

            def _ai_src(field_key, fallback_label="AI補齊"):
                return format_ai_source_detail(ai_fin, field_key, ai_period_text, fallback_label) if has_ai_fin_fetch else "AI未啟動"

            def _ai_url(field_key):
                return get_ai_source_url(ai_fin, field_key) if has_ai_fin_fetch else ""

            latest_rev_period = latest_rev_display_label if latest_rev_month and latest_rev_month != "無資料" else "未取得月營收"
            rev_is_stale = revenue_month_is_older(latest_rev_month) if latest_rev_month and latest_rev_month != "無資料" else False

            def _adopt_src(sys_val, ai_val, sys_label="系統", ai_label_text="AI補齊"):
                return sys_label if sys_val is not None else (ai_label_text if ai_val is not None else "無可用資料")

            quality_rows = [
                {"field": "現價", "system_source": "Yahoo/yfinance 即時或延遲行情", "system_value": curr_p, "ai_source": "不使用AI", "ai_value": None, "adopted_value": curr_p, "adopted_source": "系統行情", "period": "即時/延遲", "fmt": "price"},
                {"field": "P/E", "system_source": "yfinance；異常時 FinMind PER 備援", "system_value": pe_ratio, "ai_source": _ai_src("pe"), "ai_source_url": _ai_url("pe"), "ai_value": ai_pe, "adopted_value": eff_pe, "adopted_source": _adopt_src(pe_ratio, ai_pe), "period": ai_period_text if pe_ratio is None and ai_pe is not None else "系統最新可得", "fmt": "x"},
                {"field": "Forward P/E", "system_source": "yfinance forwardPE 或 EPS 反推", "system_value": sys_forward_pe, "ai_source": _ai_src("forward_eps"), "ai_source_url": _ai_url("forward_eps"), "ai_value": ai_fpe, "adopted_value": eff_forward_pe, "adopted_source": _adopt_src(sys_forward_pe, ai_fpe), "period": ai_period_text if sys_forward_pe is None and ai_fpe is not None else "系統/反推", "fmt": "x"},
                {"field": "PEG", "system_source": "Forward P/E ÷ 預估成長率", "system_value": orig_peg, "ai_source": _ai_src("yoy"), "ai_source_url": _ai_url("yoy"), "ai_value": ai_peg, "adopted_value": None if eff_peg == -999 else eff_peg, "adopted_source": "系統優先/AI備援", "period": "推估值", "fmt": "x", "notes": "成長率為負時 PEG 無意義" if eff_peg == -999 else ""},
                {"field": "P/B", "system_source": "yfinance；異常時 FinMind PBR 備援", "system_value": pb_ratio, "ai_source": _ai_src("pb"), "ai_source_url": _ai_url("pb"), "ai_value": ai_pb, "adopted_value": eff_pb, "adopted_source": _adopt_src(pb_ratio, ai_pb), "period": ai_period_text if pb_ratio is None and ai_pb is not None else "系統最新可得", "fmt": "x"},
                {"field": "最新單季 EPS", "system_source": "系統未穩定提供，避免用 TTM 冒充", "system_value": sys_latest_quarter_eps, "ai_source": _ai_src("latest_quarter_eps"), "ai_source_url": _ai_url("latest_quarter_eps"), "ai_value": ai_latest_quarter_eps, "adopted_value": ai_latest_quarter_eps, "adopted_source": "AI補齊" if ai_latest_quarter_eps is not None else "無可用資料", "period": ai_period_text, "fmt": "num", "notes": "判斷最新獲利動能"},
                {"field": "TTM EPS", "system_source": "yfinance trailingEps；必要時用 現價÷P/E 反推", "system_value": sys_ttm_eps, "ai_source": _ai_src("ttm_eps"), "ai_source_url": _ai_url("ttm_eps"), "ai_value": ai_ttm_eps, "adopted_value": eff_t_eps, "adopted_source": _adopt_src(sys_ttm_eps, ai_ttm_eps), "period": ai_period_text if sys_ttm_eps is None and ai_ttm_eps is not None else "系統/反推", "fmt": "num", "notes": "用於歷史 P/E"},
                {"field": "完整年度 EPS", "system_source": "未穩定提供，需 AI/年報補齊", "system_value": sys_fiscal_year_eps, "ai_source": _ai_src("fiscal_year_eps"), "ai_source_url": _ai_url("fiscal_year_eps"), "ai_value": ai_fiscal_year_eps, "adopted_value": ai_fiscal_year_eps, "adopted_source": "AI補齊" if ai_fiscal_year_eps is not None else "無可用資料", "period": ai_period_text, "fmt": "num", "notes": "年度基準，不與 TTM 混用"},
                {"field": "Forward EPS－系統", "system_source": "yfinance forwardEps；必要時由 TTM EPS×成長率推估", "system_value": sys_forward_eps_system, "ai_source": "不使用AI", "ai_source_url": "", "ai_value": None, "adopted_value": sys_forward_eps_system, "adopted_source": "系統/推估" if sys_forward_eps_system is not None else "無可用資料", "period": "系統/推估", "fmt": "num"},
                {"field": "Forward EPS－AI/共識", "system_source": "不使用系統", "system_value": None, "ai_source": _ai_src("forward_eps_consensus") if ai_forward_eps_consensus is not None else _ai_src("forward_eps_ai"), "ai_source_url": _ai_url("forward_eps_consensus") if ai_forward_eps_consensus is not None else _ai_url("forward_eps_ai"), "ai_value": ai_f_eps_calc, "adopted_value": ai_f_eps_calc, "adopted_source": "法人共識" if ai_forward_eps_consensus is not None else ("AI補齊" if ai_forward_eps_ai is not None else "無可用資料"), "period": ai_period_text, "fmt": "num", "notes": "與系統 Forward EPS 分開比較"},
                {"field": "營收 YoY", "system_source": "FinMind 月營收優先；yfinance 備援", "system_value": rev_growth, "ai_source": _ai_src("yoy"), "ai_source_url": _ai_url("yoy"), "ai_value": ai_yoy, "adopted_value": eff_rg, "adopted_source": _adopt_src(rev_growth, ai_yoy, "FinMind/yfinance", "AI補齊"), "period": latest_rev_period, "fmt": "pct", "is_stale": rev_is_stale, "notes": latest_rev_notice or ("月營收可能不是最新公告月份" if rev_is_stale else "")},
                {"field": "營收 MoM", "system_source": "FinMind 月營收", "system_value": (latest_mom_val / 100.0) if latest_mom_val is not None else None, "ai_source": _ai_src("mom"), "ai_source_url": _ai_url("mom"), "ai_value": ai_mom, "adopted_value": (latest_mom_val / 100.0) if latest_mom_val is not None else ai_mom, "adopted_source": "FinMind 月營收/AI覆蓋", "period": latest_rev_period, "fmt": "pct", "is_stale": rev_is_stale},
                {"field": "毛利率", "system_source": "yfinance；缺值時 FinMind 財報健康度", "system_value": gross_margin, "ai_source": _ai_src("gross_margin"), "ai_source_url": _ai_url("gross_margin"), "ai_value": ai_gm, "adopted_value": eff_gm, "adopted_source": _adopt_src(gross_margin, ai_gm), "period": ai_period_text if gross_margin is None and ai_gm is not None else "系統最新可得", "fmt": "pct", "notes": dq_note_text if "毛利率" in dq_note_text else ""},
                {"field": "營益率", "system_source": "yfinance；缺值時 FinMind 財報健康度", "system_value": op_margin, "ai_source": _ai_src("operating_margin"), "ai_source_url": _ai_url("operating_margin"), "ai_value": ai_om, "adopted_value": eff_om, "adopted_source": _adopt_src(op_margin, ai_om), "period": ai_period_text if op_margin is None and ai_om is not None else "系統最新可得", "fmt": "pct", "notes": dq_note_text if "營益率" in dq_note_text else ""},
                {"field": "ROE", "system_source": "yfinance；或用 P/B÷P/E 校正", "system_value": roe, "ai_source": _ai_src("roe"), "ai_source_url": _ai_url("roe"), "ai_value": ai_roe, "adopted_value": eff_roe, "adopted_source": _adopt_src(roe, ai_roe, "系統/恆等式校正", "AI補齊"), "period": ai_period_text if roe is None and ai_roe is not None else "系統/校正", "fmt": "pct"},
                {"field": "D/E", "system_source": "yfinance；缺值時 FinMind 財報健康度", "system_value": sys_de, "ai_source": _ai_src("debt_to_equity"), "ai_source_url": _ai_url("debt_to_equity"), "ai_value": ai_de, "adopted_value": eff_de, "adopted_source": _adopt_src(sys_de, ai_de), "period": ai_period_text if sys_de is None and ai_de is not None else "系統最新可得", "fmt": "x", "notes": dq_note_text if "D/E" in dq_note_text or "債" in dq_note_text else ""},
            ]
            dq_report_df = build_financial_quality_report(quality_rows)
            with st.expander("🩺 統一資料品質報告（系統 / AI / 採用值）", expanded=False):
                st.caption("此表用來檢查每個估值欄位的來源、採用值、期間、AI來源網址與品質狀態。估值模型仍採系統值優先、AI 作為補齊與交叉校對。")
                st.dataframe(dq_report_df, use_container_width=True, hide_index=True)
        
            if eff_f_eps is not None and real_cg is not None and real_cg > 0:
                raw_mult = (real_cg * 100) * target_peg_adj
                capped_mult = min(raw_mult, target_pe_cap)
                sys_target_price_est = eff_f_eps * capped_mult
                is_capped = raw_mult > target_pe_cap
            else:
                sys_target_price_est = None; is_capped = False
            
            extreme_target_price = eff_f_eps * target_pe_cap if eff_f_eps is not None else None

            if has_ai_fin_fetch and ai_f_eps_calc is not None and ai_cg is not None and ai_cg > 0:
                ai_raw_mult = (ai_cg * 100) * target_peg_adj
                ai_capped_mult = min(ai_raw_mult, target_pe_cap)
                ai_target_price_est = ai_f_eps_calc * ai_capped_mult
                ai_is_capped = ai_raw_mult > target_pe_cap
            else:
                ai_target_price_est = None; ai_is_capped = False

            ai_extreme_target_price = ai_f_eps_calc * target_pe_cap if has_ai_fin_fetch and ai_f_eps_calc is not None else None

            # ==========================================
            # ⚠️ 系統 / AI 分歧警告：EPS / YoY / PEG / 合理價 / D/E
            # ==========================================
            divergence_warnings = build_divergence_warnings(
                system_forward_eps=sys_forward_eps_system,
                ai_forward_eps=ai_f_eps_calc,
                system_yoy=rev_growth,
                ai_yoy=ai_yoy,
                system_peg=orig_peg,
                ai_peg=ai_peg,
                system_fair_value=sys_target_price_est,
                ai_fair_value=ai_target_price_est,
                system_de=sys_de,
                ai_de=ai_de,
                stock_id=curr_id,
                stock_name=c_name,
            )
            if divergence_warnings:
                danger_count = sum(1 for w in divergence_warnings if w.get("嚴重度") == "danger")
                with st.expander(f"⚠️ 系統 / AI 分歧警告（{len(divergence_warnings)} 項）", expanded=True):
                    if danger_count:
                        st.error("偵測到重大估值分歧：請先確認 EPS、YoY、PEG、合理價或 D/E 口徑，再使用買賣結論。")
                    else:
                        st.warning("偵測到資料口徑分歧：建議先檢查來源與期間，再解讀估值。")
                    for w in divergence_warnings:
                        msg = (
                            f"**{w.get('規則', '分歧警告')}**：{w.get('警告文字', '')}  \n"
                            f"系統值：`{w.get('系統值', 'NULL')}`｜AI值：`{w.get('AI值', 'NULL')}`｜差距：`{w.get('差距', 'N/A')}`  \n"
                            f"建議：{w.get('建議處理', '')}"
                        )
                        if w.get("嚴重度") == "danger":
                            st.error(msg)
                        else:
                            st.warning(msg)
                    st.dataframe(build_divergence_warning_report(divergence_warnings), use_container_width=True, hide_index=True)
        
            # 手動組合區域
            time_str = f", {ai_period_val}" if ai_period_val else ""

            # 1. 預估獲利成長 (YoY)
            eg_str_disp = build_cmp_str(real_cg, ai_cg, 'pct', 'AI推估', show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
            if is_base_normalized: eg_str_disp += "<br><span style='color:#FFD700; font-size:0.75rem; font-weight:normal;'>⚠️ 啟動低基期防護(分母=0.5)</span>"
            eg_color = "#ff4d4d" if real_cg and real_cg > 0 else ("#00cc66" if real_cg and real_cg < 0 else "#fff")
        
            # 2. 前瞻 PEG
            orig_peg_str = f"{orig_peg:.2f}" if orig_peg is not None else ("分母為負" if real_cg is not None and real_cg <= 0 else "N/A")
            peg_str_disp = f"{orig_peg_str}<br><span style='color:#FFD700; font-size:0.85rem;'>(AI推估: {ai_peg:.2f}{time_str})</span>" if ai_peg is not None else orig_peg_str
        
            # 3. 前瞻 P/E
            orig_fpe_str = f"{sys_forward_pe:.1f}x" if sys_forward_pe is not None else "N/A"
            fpe_str = f"{orig_fpe_str}<br><span style='color:#FFD700; font-size:0.85rem;'>(AI推估: {ai_fpe:.1f}x{time_str})</span>" if ai_fpe is not None else orig_fpe_str
        
            pe_str = build_cmp_str(pe_ratio, ai_pe, 'x', ai_label, show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
            # ✅ 顯示字串只吃 validate_and_correct_financial_metrics() 校正後的 display_* 變數。
            rg_str = build_cmp_str(display_rev_growth, display_ai_yoy, 'pct', ai_label, show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
            gm_om_str = build_cmp_dual_str(display_gross_margin, display_operating_margin, display_ai_gross_margin, display_ai_operating_margin, 'pct', 'pct', ai_label, show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
            roe_str = build_cmp_str(roe, ai_roe, 'pct', ai_label, show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
            de_str = build_cmp_str(display_debt_to_equity, display_ai_debt_to_equity, 'pct', ai_label, show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
            pb_str = build_cmp_str(pb_ratio, ai_pb, 'x', ai_label, show_ai_missing=has_ai_fin_fetch, period=ai_period_val)
        
            rg_color = "#ff4d4d" if eff_rg and eff_rg > 0 else ("#00cc66" if eff_rg and eff_rg < 0 else "#fff")
            roe_eval = " <span style='color:#00cc66; font-size:0.8rem; margin-left:5px;' title='大於15%視為資金運用效率極佳 (已透過恆等式校正)'>⭐ 優質</span>" if eff_roe is not None and eff_roe >= 0.15 else ""
        
            if eff_de is None: de_eval = ""
            elif eff_de < 0.5: de_eval = " <span style='color:#00cc66; font-size:0.8rem; margin-left:5px;' title='小於50%財務極度穩健'>⭐ 優質</span>"
            elif eff_de > 1.0: de_eval = " <span style='color:#ff4d4d; font-size:0.8rem; margin-left:5px;' title='大於100%視為高槓桿風險'>⚠️ 高槓桿</span>"
            else: de_eval = " <span style='color:#FFD700; font-size:0.8rem; margin-left:5px;' title='50%~100%為資本密集產業常見合理區間'>🆗 合理</span>"

            if eff_pe is None: pe_color, pe_text = "gray", "數據不足"
            elif eff_pe > 25: pe_color, pe_text = "#ff4d4d", "高成長溢價"
            elif eff_pe < 15: pe_color, pe_text = "#00cc66", "相對便宜"
            else: pe_color, pe_text = "#FFD700", "合理區間"

            if eff_pb is None: pb_color, pb_text = "gray", "數據不足"
            elif eff_pb > 3: pb_color, pb_text = "#ff4d4d", "偏高溢價"
            elif eff_pb < 1.5: pb_color, pb_text = "#00cc66", "具資產保護"
            else: pb_color, pb_text = "#FFD700", "合理區間"

            if eff_forward_pe is None: fpe_color, fpe_text = "gray", "數據不足"
            else:
                if eff_forward_pe > 25: fpe_color, fpe_text = "#ff4d4d", "高成長期望"
                elif eff_forward_pe < 15: fpe_color, fpe_text = "#00cc66", "相對便宜"
                else: fpe_color, fpe_text = "#FFD700", "合理區間"

            if eff_peg == -999: peg_color, peg_text = "gray", "分母為負，無意義"
            elif eff_peg is None: peg_color, peg_text = "gray", "衰退或無數據"
            else: 
                if eff_forward_pe is not None and target_pe_cap is not None and eff_forward_pe > target_pe_cap:
                    peg_color, peg_text = "#ff8c00", "估值過熱(超越Cap)" 
                elif eff_peg > 2: peg_color, peg_text = "#ff4d4d", "透支未來成長"
                elif eff_peg <= 1: peg_color, peg_text = "#00cc66", "低估 (成長性支撐)"
                else: peg_color, peg_text = "#FFD700", "合理區間"
            if sys_target_price_est or ai_target_price_est:
                if is_capped or ai_is_capped:
                    cap_msg = f"🚨 觸發封頂防護 ({target_pe_cap:.0f}x)"
                    if (extreme_target_price and curr_p > extreme_target_price) or (ai_extreme_target_price and curr_p > ai_extreme_target_price):
                        cap_warning_html = f"<br><span style='color:#ff4d4d; font-weight:bold;'>{cap_msg}，追高風險極大！</span>"
                    else: 
                        cap_warning_html = f"<br><span style='color:#ff4d4d; font-weight:bold;'>{cap_msg}</span>"
                sys_tp_str = f"{sys_target_price_est:.1f}元" if sys_target_price_est else "N/A"
                ai_tp_est_html = f"<span style='color:#FFD700; font-size:0.95rem;'>(AI推估: {ai_target_price_est:.1f}元{time_str})</span>" if ai_target_price_est else ""            
                sys_ext_str = f"{extreme_target_price:.1f}元" if extreme_target_price else "N/A"
                ai_ext_str = f"<span style='color:#FFD700; font-size:0.95rem;'>(AI推估: {ai_extreme_target_price:.1f}元{time_str})</span>" if ai_extreme_target_price else ""   
                debug_eps = eff_f_eps if eff_f_eps else 0
                # 🚀 修正處：將計算出來的結果回填給純文字變數 tp_est_str，讓提示詞抓得到
                ai_tp_txt = f"{ai_target_price_est:.1f}元" if ai_target_price_est else "N/A"
                ai_ext_txt = f"{ai_extreme_target_price:.1f}元" if ai_extreme_target_price else "N/A"
                if has_ai_fin_fetch:
                    tp_est_str = f"公式合理估值: {sys_tp_str} (AI公式合理估值: {ai_tp_txt}) | 公式極限價: {sys_ext_str} (AI公式極限價: {ai_ext_txt}) | 帶入 Cap: {target_pe_cap:.0f}x"
                else:
                    tp_est_str = f"公式合理估值: {sys_tp_str} | 公式極限價: {sys_ext_str} | 帶入 Cap: {target_pe_cap:.0f}x"
                target_price_html = f"<div style='color:#aaa; font-size:0.85rem; border-top:1px solid #444; padding-top:8px; margin-top:8px;'>🎯 公式合理估值 (PEG 推算，非買賣目標): <b style='color:#fff; font-size:1.1rem;'>{sys_tp_str}</b> <br>{ai_tp_est_html}<br>🚀 <span style='color:#ff4d4d; font-weight:bold;'>公式極限價 (Forward EPS × Cap，高風險情境): <span style='font-size:1.2rem;'>{sys_ext_str}</span> <br>{ai_ext_str}</span><br><div style='background:#2c2c2c; padding:4px 8px; border-radius:4px; margin-top:4px;'><small style='color:#00bfff;'>🐛 [底層運算除錯] 帶入 EPS: {debug_eps:.2f} | 帶入 Cap: {target_pe_cap:.0f}x</small></div>{cap_warning_html}</div>"

            # ==========================================
            # 🧭 法人目標價可信度 + 公式估值 / 可操作估值分離
            # ==========================================
            valuation_separation = build_valuation_separation_report(
                current_price=curr_p,
                system_formula_fair_value=sys_target_price_est,
                ai_formula_fair_value=ai_target_price_est,
                system_formula_extreme_value=extreme_target_price,
                ai_formula_extreme_value=ai_extreme_target_price,
                broker_target_avg=ai_me_val,
                broker_target_low=ai_lo_val,
                analyst_count=ai_analyst_count,
                system_forward_eps=sys_forward_eps_system,
                ai_forward_eps=ai_forward_eps_ai,
                consensus_forward_eps=ai_forward_eps_consensus,
                target_pe_cap=target_pe_cap,
                divergence_warnings=divergence_warnings,
                industry_profile=industry_profile,
                dynamic_cap_pack=dynamic_cap_pack,
                pb_ratio=eff_pb,
            )
            target_confidence = valuation_separation.get('target_confidence', classify_target_price_confidence(ai_analyst_count))
            val_html = f"""
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom:20px;'>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {pe_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>📊 歷史本益比 (Trailing P/E)</div>
                        <div style='background:{pe_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{pe_text}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff; margin-bottom:10px;'>{pe_str}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {fpe_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>🚀 前瞻本益比 (Forward P/E)</div>
                        <div style='background:{fpe_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{fpe_text}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff; margin-bottom:5px;'>{fpe_str}</div>
                    <div style='color:#ffd700; font-size:0.85rem; font-weight:bold;'>基準：{eps_source_text}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {peg_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>📈 前瞻 PEG (Forward PEG)</div>
                        <div style='background:{peg_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{peg_text}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff; margin-bottom:5px;'>{peg_str_disp}</div>
                    {target_price_html}
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {pb_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>🏦 股價淨值比 (P/B Ratio)</div>
                        <div style='background:{pb_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{pb_text}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff; margin-bottom:10px;'>{pb_str}</div>
                </div>
            </div>
            """
            st.markdown(clean_html(val_html), unsafe_allow_html=True)

            with st.expander("🧭 法人目標價可信度 + 公式估值 / 可操作估值分離", expanded=True):
                tc = target_confidence
                st.markdown(
                    f"<div style='background:#111827;color:#F3F4F6;border-left:5px solid {tc.get('color', '#FFD700')};padding:12px 14px;border-radius:8px;margin-bottom:10px;line-height:1.7;'>"
                    f"<div style='color:#F3F4F6;'><b>法人目標價可信度：</b><span style='color:{tc.get('color', '#FFD700')};font-weight:bold;'>{tc.get('label', '低可信')}</span>｜<span style='color:#D1D5DB;'>{tc.get('message', '')}</span></div>"
                    f"<div style='margin-top:4px;color:#F3F4F6;'><b>可操作估值提示：</b><span style='color:#E5E7EB;'>{valuation_separation.get('action_hint', '觀望 / 資料不足')}</span></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.caption("公式合理估值與公式極限價只顯示模型輸出；可操作估值區間會額外考慮保守 EPS、法人樣本數、系統/AI 分歧警告與產業估值模型。")
                st.dataframe(valuation_separation.get('report'), use_container_width=True, hide_index=True)
                with st.expander("🏭 產業估值模型明細", expanded=False):
                    st.dataframe(build_industry_valuation_model_report(industry_profile), use_container_width=True, hide_index=True)
                if isinstance(dynamic_cap_pack, dict) and dynamic_cap_pack.get("report") is not None:
                    with st.expander("⚙️ Dynamic Cap 2.0 倍率拆解", expanded=True):
                        if dynamic_cap_pack.get("valuation_mode") == "pb_cycle":
                            st.warning("本分類採 P/B 週期模型：P/E Cap 僅作輔助，不直接作買進倍率。")
                        else:
                            st.caption("17-B-2 已同步全產業校準表：產業基準 × 成長係數 × 品質係數 × 題材係數 × 規模係數 × 地緣政治係數，再乘資料、估值與流動性折扣，最後套用產業 hard ceiling。")
                        st.dataframe(dynamic_cap_pack.get("report"), use_container_width=True, hide_index=True)
                        dc_warnings = dynamic_cap_pack.get("warnings") or []
                        if dc_warnings:
                            st.warning("Dynamic Cap 模型提醒：" + "；".join(str(x) for x in dc_warnings))
                with st.expander("法人目標價可信度明細", expanded=False):
                    st.dataframe(build_target_price_confidence_report(ai_analyst_count, ai_hi_val, ai_me_val, ai_lo_val, ai_target_rationale), use_container_width=True, hide_index=True)

            # ==========================================
            # 🚦 最終操作燈號：可買 / 觀望 / 不建議 / 資料異常
            # ==========================================
            final_signal = build_final_operation_signal(
                current_price=curr_p,
                valuation_separation=valuation_separation,
                divergence_warnings=divergence_warnings,
                target_confidence=target_confidence,
                industry_profile=industry_profile,
                pe=pe_ratio,
                forward_pe=eff_forward_pe,
                peg=orig_peg,
                pb=pb_ratio,
                roe=eff_roe,
                debt_to_equity=display_debt_to_equity,
                revenue_yoy=display_rev_growth,
                gross_margin=display_gross_margin,
                operating_margin=display_operating_margin,
                has_ai_fin_fetch=has_ai_fin_fetch,
            )
            with st.expander("🚦 最終操作燈號", expanded=True):
                st.markdown(
                    f"<div style='background:#1e1e1e;border-left:7px solid {final_signal.get('color', '#FFD700')};padding:14px;border-radius:10px;margin-bottom:10px;'>"
                    f"<div style='font-size:1.35rem;font-weight:bold;color:{final_signal.get('color', '#FFD700')};'>"
                    f"{final_signal.get('signal', '觀望')}</div>"
                    f"<div style='color:#ddd;margin-top:6px;'><b>操作含義：</b>{final_signal.get('advice', '')}</div>"
                    f"<div style='color:#aaa;margin-top:6px;font-size:0.9rem;'>"
                    f"資料可信度：{final_signal.get('data_confidence')}｜估值可信度：{final_signal.get('valuation_confidence')}｜操作可信度：{final_signal.get('operation_confidence')}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                st.caption("燈號會綜合資料分歧、可操作估值區間、法人樣本數、產業估值模型與基本面防呆；資料異常時優先停用買賣判斷。")
                st.dataframe(final_signal.get("report"), use_container_width=True, hide_index=True)
        
            mom_color = "#ff4d4d" if latest_mom_val is not None and latest_mom_val > 0 else ("#00cc66" if latest_mom_val is not None and latest_mom_val < 0 else "#fff")
            mom_str_disp = f"<br><span style='font-size:1rem; color:{mom_color};'>MoM: {latest_mom_str}</span>" if latest_mom_str != "N/A" else ""

            fund_html = f"""
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px;'>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>歷史本益比 (P/E)</div><div style='font-size:1.3rem; font-weight:bold; color:#fff;'>{pe_str}</div></div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>EPS (TTM / Forward)</div><div style='font-size:1.3rem; font-weight:bold; color:#FFD700;'>{f_eps_display}</div></div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>營收成長率<br><span style='font-size:0.75rem; color:#888;'>({latest_rev_display_label})</span></div><div style='font-size:1.3rem; font-weight:bold; color:{rg_color};'>{rg_str}{mom_str_disp}</div></div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>預估獲利成長 (YoY)</div><div style='font-size:1.3rem; font-weight:bold; color:{eg_color};'>{eg_str_disp}</div></div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>毛利率 / 營益率</div><div style='font-size:1.3rem; font-weight:bold; color:#fff;'>{gm_om_str}</div></div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>ROE (恆等式校正)</div><div style='font-size:1.3rem; font-weight:bold; color:#00bfff;'>{roe_str}{roe_eval}</div></div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; text-align:center;'><div style='color:#aaa; font-size:0.9rem; margin-bottom:5px;'>負債權益比 (D/E)</div><div style='font-size:1.3rem; font-weight:bold; color:#fff;'>{de_str}{de_eval}</div></div>
            </div>
            """
            st.markdown(clean_html(fund_html), unsafe_allow_html=True)
            st.markdown("---")
        
            # 🚀 極端風險 (Anomaly) 警示燈號
            st.markdown("#### 🚨 系統異常風險偵測 (Anomaly Detection)", unsafe_allow_html=True)
            anomaly_html = ""

            if eff_pb is not None and eff_pb > 10:
                anomaly_html += f"<div style='background:linear-gradient(90deg, #8b0000 0%, #ff4d4d 100%); color:white; padding:12px; border-radius:8px; margin-bottom:10px; font-weight:bold;'>🔥【極度溢價警示】 股價淨值比 (P/B) 高達 {eff_pb:.1f} 倍，已脫離台股歷史常態評價，隨時有均值回歸的暴跌風險！</div>"

            if df_rev_bk is not None and len(df_rev_bk) >= 2:
                last_mom = df_rev_bk['MoM'].iloc[-1]
                prev_mom = df_rev_bk['MoM'].iloc[-2]
                recent_high_120 = hist['High'].tail(120).max() if len(hist) >= 120 else hist['High'].max()
                price_near_high = curr_p >= (recent_high_120 * 0.9)
                if last_mom < 0 and prev_mom < 0 and price_near_high:
                     anomaly_html += f"<div style='background:linear-gradient(90deg, #b8860b 0%, #ff8c00 100%); color:white; padding:12px; border-radius:8px; margin-bottom:10px; font-weight:bold;'>🚸【量價背離風險】 近兩月營收連續衰退 (最新 MoM: {last_mom:.2f}%)，但股價仍高掛在近半年高檔區，請嚴防主力拉高出貨！</div>"

            if anomaly_html == "":
                anomaly_html = "<div style='background:#1e1e1e; color:#00cc66; padding:12px; border-radius:8px; border:1px solid #333;'>✅ 目前未偵測到極端高估 (P/B>10) 或營收背離風險，數據處於相對常態範圍。</div>"

            st.markdown(clean_html(anomaly_html), unsafe_allow_html=True)
            st.markdown("---")

            st.markdown("#### 🛡️ 防禦力與財務健康檢測 (長線/存股必看)", unsafe_allow_html=True)
            div_yield = s_float(info.get('dividendYield')) or s_float(info.get('trailingAnnualDividendYield'))
        
            if ai_dy is not None:
                div_yield = ai_dy
            elif div_yield is not None and div_yield > 1.0: 
                div_yield = div_yield / 100.0

            fcf = s_float(info.get('freeCashflow'))
            if fcf is None and fm_health.get('cfo_l'): fcf = fm_health.get('cfo_l')
            if ai_fcf is not None: fcf = ai_fcf
            
            current_ratio = s_float(info.get('currentRatio'))
            if ai_cr is not None: current_ratio = ai_cr

            dy_str = to_pct(div_yield)
            if div_yield is None: dy_color, dy_eval = "gray", "無資料"
            elif div_yield >= 0.05: dy_color, dy_eval = "#ff4d4d", "高息護體(>5%)"
            elif div_yield >= 0.03: dy_color, dy_eval = "#FFD700", "穩健配息"
            else: dy_color, dy_eval = "#00cc66", "殖利率偏低"

            if fcf is None: fcf_str, fcf_color, fcf_eval = "無資料", "gray", "無資料"
            elif fcf > 0: fcf_str, fcf_color, fcf_eval = f"{fcf/100000000:,.0f} 億", "#ff4d4d", "現金流健康"
            else: fcf_str, fcf_color, fcf_eval = f"{fcf/100000000:,.0f} 億", "#00cc66", "⚠️ 留意燒錢風險"

            if current_ratio is None: cr_str, cr_color, cr_eval = "無資料", "gray", "無資料"
            elif current_ratio >= 1.5: cr_str, cr_color, cr_eval = f"{current_ratio:.2f}", "#ff4d4d", "短期無債務風險"
            elif current_ratio >= 1.0: cr_str, cr_color, cr_eval = f"{current_ratio:.2f}", "#FFD700", "流動性及格"
            else: cr_str, cr_color, cr_eval = f"{current_ratio:.2f}", "#00cc66", "⚠️ 流動性吃緊"
        
            f_score_val = fm_health.get('f_score')
            if f_score_val is None: 
                fs_str, fs_color, fs_eval = "無資料", "gray", "資料不足"
            elif f_score_val >= 7: 
                fs_str, fs_color, fs_eval = f"{f_score_val} 分", "#ff4d4d", "⭐ 體質極優"
            elif f_score_val >= 5: 
                fs_str, fs_color, fs_eval = f"{f_score_val} 分", "#FFD700", "🆗 體質及格"
            else: 
                fs_str, fs_color, fs_eval = f"{f_score_val} 分", "#00cc66", "🚨 孱弱/高風險"

            dfens_html = f"""
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom:20px;'>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {dy_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>💰 預估殖利率</div><div style='background:{dy_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{dy_eval}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff;'>{dy_str}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {fcf_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>💵 自由/營業現金流</div><div style='background:{fcf_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{fcf_eval}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff;'>{fcf_str}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {cr_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>⚖️ 流動比率</div><div style='background:{cr_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{cr_eval}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff;'>{cr_str}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {fs_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>🩺 F-Score 健康跑分</div><div style='background:{fs_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{fs_eval}</div>
                    </div>
                    <div style='font-size:1.6rem; font-weight:bold; color:#fff;'>{fs_str}</div>
                </div>
            </div>
            """
            st.markdown(clean_html(dfens_html), unsafe_allow_html=True)
            st.markdown("---")

            analyst_count_display = ai_analyst_count if ai_analyst_count not in (None, "", "null") else "無"
            target_confidence = locals().get("target_confidence", classify_target_price_confidence(ai_analyst_count))
            conf_color = target_confidence.get("color", "#FFD700")
            conf_label = target_confidence.get("label", "低可信")
            st.markdown(f"#### 🎯 法人預估目標價 (分析師統計：{analyst_count_display} 位｜可信度：<span style='color:{conf_color};'>{conf_label}</span>)", unsafe_allow_html=True)
            st.caption(target_confidence.get("message", "分析師樣本數不足時，不宜視為強共識。"))
        
            if ai_hi_val is not None and ai_me_val is not None and ai_lo_val is not None:
                v1, v2, v3 = st.columns(3)
                v1.markdown(f"<div style='background:#ffebee;padding:12px;border-radius:8px;text-align:center;color:#000;'><small>最高價</small><br><b>{ai_hi_val:.1f}</b></div>", unsafe_allow_html=True)
                upside = ((ai_me_val / curr_p) - 1) * 100 if curr_p else 0
                v2.markdown(f"<div style='background:#fff3e0;padding:12px;border-radius:8px;text-align:center;color:#000;'><small>平均價</small><br><b>{ai_me_val:.1f}</b><br><small>空間: {upside:+.1f}%</small></div>", unsafe_allow_html=True)
                v3.markdown(f"<div style='background:#e8f5e9;padding:12px;border-radius:8px;text-align:center;color:#000;'><small>最低價</small><br><b>{ai_lo_val:.1f}</b></div>", unsafe_allow_html=True)
                if ai_target_rationale:
                    st.caption(f"📌 法人目標價核心理由：{ai_target_rationale}")
                st.markdown("---")
            elif ai_me_val is not None:
                 upside_ai = ((ai_me_val / curr_p) - 1) * 100 if curr_p else 0
                 st.markdown(f"<div style='background:#fff3e0;padding:12px;border-radius:8px;text-align:center;color:#000;'><small>🤖 AI 聯網捕捉平均目標價 ({ai_label} {ai_period_val})</small><br><b>{ai_me_val:.1f}</b><br><small>潛在空間: {upside_ai:+.1f}%</small></div>", unsafe_allow_html=True)
                 if ai_target_rationale:
                    st.caption(f"📌 法人目標價核心理由：{ai_target_rationale}")
                 st.markdown("---")
            else:
                 st.markdown("<span style='color:gray;'>AI 目前尚未捕捉到法人目標價資料。</span>", unsafe_allow_html=True)
                 st.markdown("---")

            # 🚀 主力籌碼追蹤雷達
            st.markdown("#### 📡 主力籌碼追蹤雷達 (聰明錢動向與背離陷阱)", unsafe_allow_html=True)
            inst_df = get_inst_data(curr_id, st.session_state.finmind_key)
        
            if not inst_df.empty:
                f_streak = get_streak(inst_df['Foreign'])
                t_streak = get_streak(inst_df['Trust'])
                f_10d = inst_df['Foreign'].tail(10).sum()
                t_10d = inst_df['Trust'].tail(10).sum()
            
                f_status = f"連買 {f_streak} 天 🔥" if f_streak > 0 else (f"連賣 {-f_streak} 天 ⚠️" if f_streak < 0 else "無連續動向")
                t_status = f"連買 {t_streak} 天 🔥" if t_streak > 0 else (f"連賣 {-t_streak} 天 ⚠️" if t_streak < 0 else "無連續動向")
            
                f_color = "#ff4d4d" if f_10d > 0 else "#00cc66"
                t_color = "#ff4d4d" if t_10d > 0 else "#00cc66"
            
                trap_warning = ""
                if (eff_eg is not None and eff_eg > 0) and ((f_10d + t_10d) < -1000):
                    trap_warning = "<div style='background:linear-gradient(90deg, #8b0000 0%, #ff4d4d 100%); color:white; padding:12px; border-radius:8px; margin-top:10px; font-weight:bold;'>🚨 【高危陷阱警示】基本面看似亮眼，但外資/投信近 10 日聯手倒貨超過千張！請提防主力趁利多逢高出貨！</div>"
                elif (f_streak >= 3 or t_streak >= 3) and ((f_10d + t_10d) > 1000):
                    trap_warning = "<div style='background:linear-gradient(90deg, #006400 0%, #00cc66 100%); color:white; padding:12px; border-radius:8px; margin-top:10px; font-weight:bold;'>🚀 【聰明錢上車】三大法人近期連買且大幅建倉，籌碼動能強勁，極具波段上攻潛力！</div>"
                else:
                    trap_warning = "<div style='background:#1e1e1e; color:#aaa; padding:12px; border-radius:8px; border:1px solid #333; margin-top:10px;'>目前三大法人買賣超動向無極端異常訊號。</div>"

                radar_html = f"""
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom:10px;'>
                    <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {f_color};'>
                        <div style='color:#aaa; font-size:0.9rem;'>外資近 10 日淨買賣</div>
                        <div style='font-size:1.6rem; font-weight:bold; color:{f_color};'>{f_10d:,.0f} 張</div>
                        <div style='font-size:1rem; font-weight:bold; color:#fff; margin-top:5px;'>動向: {f_status}</div>
                    </div>
                    <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {t_color};'>
                        <div style='color:#aaa; font-size:0.9rem;'>投信近 10 日淨買賣</div>
                        <div style='font-size:1.6rem; font-weight:bold; color:{t_color};'>{t_10d:,.0f} 張</div>
                        <div style='font-size:1rem; font-weight:bold; color:#fff; margin-top:5px;'>動向: {t_status}</div>
                    </div>
                </div>
                {trap_warning}
                """
                st.markdown(clean_html(radar_html), unsafe_allow_html=True)
            else:
                if not st.session_state.finmind_key:
                    st.warning("⚠️ 系統無法獲取主力籌碼雷達。請至左側上傳 `key.txt` 匯入 FinMind 金鑰以解除限制。")
                else:
                    st.warning("⚠️ 此檔股票近期無三大法人買賣超數據，無法啟動籌碼雷達。")
            st.markdown("---")

            # 🚀 籌碼面與股權結構分析
            st.markdown("#### 🐳 內部人與控盤主力推估", unsafe_allow_html=True)
            insider_pct = s_float(info.get('heldPercentInsiders'))
            inst_pct = s_float(info.get('heldPercentInstitutions'))
            shares_out = s_float(info.get('sharesOutstanding'))
            if ai_shares is not None: shares_out = ai_shares
            share_capital = shares_out * 10 if shares_out is not None else None

            if share_capital is not None:
                if share_capital >= 10_000_000_000:
                    cap_type, driver, cap_color, driver_desc = "大型權值股", "🌍 外資主導", "#4169E1", f"股本約 {share_capital/100000000:.0f} 億。籌碼龐大，走勢受外資資金影響大。"
                elif share_capital <= 3_000_000_000:
                    cap_type, driver, cap_color, driver_desc = "中小型飆股", "🔥 投信/內資主力", "#ff8c00", f"股本約 {share_capital/100000000:.0f} 億。籌碼輕薄，易受投信作帳帶動。"
                else:
                    cap_type, driver, cap_color, driver_desc = "中型中堅股", "🤝 土洋共議", "#9370DB", f"股本約 {share_capital/100000000:.0f} 億。出現土洋合作易有波段行情。"
            else:
                cap_type, driver, cap_color, driver_desc = "無資料", "未知", "gray", "無法獲取股本資料"

            inst_str = to_pct(inst_pct)
            inst_color, inst_eval = ("#ff4d4d", "高度集中 (留意結帳)") if inst_pct is not None and inst_pct > 0.40 else ("#FFD700", "穩定認可") if inst_pct is not None and inst_pct > 0.15 else ("#00bfff", "內資/散戶主導") if inst_pct is not None else ("gray", "數據不足")

            insider_str = to_pct(insider_pct)
            in_color, in_eval = ("#ff4d4d", "籌碼極度安定") if insider_pct is not None and insider_pct > 0.40 else ("#FFD700", "相對穩健") if insider_pct is not None and insider_pct > 0.20 else ("#00cc66", "籌碼較渙散 (警戒)") if insider_pct is not None else ("gray", "數據不足")

            chip_html = f"""
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top:10px;'>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {inst_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>🏦 外資/機構總持股率</div>
                        <div style='background:{inst_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{inst_eval}</div>
                    </div>
                    <div style='font-size:1.8rem; font-weight:bold; color:#fff; margin-bottom:5px;'>{inst_str}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {in_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>🏢 內部人與大股東持股</div>
                        <div style='background:{in_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{in_eval}</div>
                    </div>
                    <div style='font-size:1.8rem; font-weight:bold; color:#fff; margin-bottom:5px;'>{insider_str}</div>
                </div>
                <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {cap_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='font-size:1.1rem; font-weight:bold; color:#fff;'>🎯 控盤主力推估</div>
                        <div style='background:{cap_color}; color:#fff; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{cap_type}</div>
                    </div>
                    <div style='font-size:1.3rem; font-weight:bold; color:{cap_color}; margin-bottom:10px;'>{driver}</div>
                    <div style='color:#aaa; font-size:0.85rem; line-height:1.5;'>{driver_desc}</div>
                </div>
            </div>
            """
            st.markdown(clean_html(chip_html), unsafe_allow_html=True)
            st.markdown("---")
            
            def _nullize_text(s):
                s = str(s) if s is not None else ""
                import re
                s = re.sub(r'<[^>]+>', ' ', s)
                s = s.replace("N/A", "NULL").replace("無資料", "NULL").replace("未捕捉到", "NULL")
                s = re.sub(r'\s+', ' ', s)
                return s.strip() if s.strip() else "NULL"

            def _prompt_df(df, max_rows=20):
                """將 Streamlit 表格壓成可貼給外部 AI 的純文字，避免 2.0 面板資訊沒被打包。"""
                try:
                    if df is None or getattr(df, "empty", True):
                        return "NULL"
                    rows = []
                    for i, row in df.head(max_rows).iterrows():
                        parts = []
                        for col in df.columns:
                            val = row.get(col, "")
                            val = _nullize_text(val)
                            if val != "NULL":
                                parts.append(f"{col}={val}")
                        if parts:
                            rows.append(f"- " + "；".join(parts))
                    return "\n".join(rows) if rows else "NULL"
                except Exception as e:
                    try:
                        log_exception("PromptPack", "_prompt_df", e)
                    except Exception:
                        pass
                    return "NULL"

            def _prompt_warnings(warnings):
                try:
                    if not warnings:
                        return "NULL"
                    rows = []
                    for w in warnings[:12]:
                        rows.append(
                            "- "
                            f"規則={_nullize_text(w.get('規則'))}；"
                            f"嚴重度={_nullize_text(w.get('嚴重度'))}；"
                            f"警告={_nullize_text(w.get('警告文字'))}；"
                            f"系統值={_nullize_text(w.get('系統值'))}；"
                            f"AI值={_nullize_text(w.get('AI值'))}；"
                            f"差距={_nullize_text(w.get('差距'))}；"
                            f"建議={_nullize_text(w.get('建議處理'))}"
                        )
                    return "\n".join(rows)
                except Exception as e:
                    try:
                        log_exception("PromptPack", "_prompt_warnings", e)
                    except Exception:
                        pass
                    return "NULL"

            # 面板核心數值（系統/AI/推估）
            ctx_tp_est = _nullize_text(tp_est_str)
            panel_pe = _nullize_text(pe_str)
            panel_fpe = _nullize_text(fpe_str)
            panel_pb = _nullize_text(pb_str)
            panel_peg = _nullize_text(peg_str_disp)
            panel_eps = _nullize_text(f_eps_display)
            # ✅ AI prompt / 戰情面板也沿用已校正後的 Markdown 字串，避免 prompt 吃到舊值。
            panel_rg = _nullize_text(rg_str)
            panel_eg = _nullize_text(eg_str_disp)
            panel_gmom = _nullize_text(gm_om_str)
            panel_roe = _nullize_text(roe_str)
            panel_de = _nullize_text(de_str)

            # 🚀 修正處：正確讀取系統目標價與 AI 目標價的判斷邏輯
            sys_hi = s_float(info.get('targetHighPrice'))
            sys_me = s_float(info.get('targetMeanPrice'))
            sys_lo = s_float(info.get('targetLowPrice'))
            hi_str = f"{sys_hi:.1f}" if sys_hi is not None else "N/A"
            me_str = f"{sys_me:.1f}" if sys_me is not None else "N/A"
            lo_str = f"{sys_lo:.1f}" if sys_lo is not None else "N/A"

            prompt_hi_str = f"{ai_hi_val:.1f}" if ai_hi_val is not None else hi_str
            prompt_me_str = f"{ai_me_val:.1f}" if ai_me_val is not None else me_str
            prompt_lo_str = f"{ai_lo_val:.1f}" if ai_lo_val is not None else lo_str
            
            if ai_target_price is not None:
                if prompt_hi_str == "N/A": prompt_hi_str = f"{ai_target_price:.1f} (AI回填)"
                if prompt_me_str == "N/A": prompt_me_str = f"{ai_target_price:.1f} (AI回填)"
                if prompt_lo_str == "N/A": prompt_lo_str = f"{ai_target_price:.1f} (AI回填)"
            ai_source_trace_df_for_prompt = build_ai_source_trace_report(temp_ai_fin) if isinstance(temp_ai_fin, dict) else pd.DataFrame()
            ai_validation_warnings_for_prompt = temp_ai_fin.get("_ai_validation_warnings", []) if isinstance(temp_ai_fin, dict) else []
            ai_validation_status_for_prompt = temp_ai_fin.get("_ai_validation_status", "") if isinstance(temp_ai_fin, dict) else ""
            final_signal_report_for_prompt = final_signal.get("report") if isinstance(final_signal, dict) else None
            valuation_report_for_prompt = valuation_separation.get("report") if isinstance(valuation_separation, dict) else None
            target_confidence_report_for_prompt = build_target_price_confidence_report(ai_analyst_count, ai_hi_val, ai_me_val, ai_lo_val, ai_target_rationale)
            industry_report_for_prompt = build_industry_valuation_model_report(industry_profile)
            dynamic_cap_report_for_prompt = dynamic_cap_pack.get("report") if isinstance(dynamic_cap_pack, dict) else None

            context_str = f"""
【0. WAY AI 投資戰情室 2.1 判讀總覽】
- 股票: {c_name} ({curr_id})
- 最新收盤價: {_nullize_text(curr_p)} 元
- 系統版本: 2.1
- 最終操作燈號: {_nullize_text(final_signal.get('signal') if isinstance(final_signal, dict) else 'NULL')}
- 操作含義: {_nullize_text(final_signal.get('advice') if isinstance(final_signal, dict) else 'NULL')}
- 資料可信度: {_nullize_text(final_signal.get('data_confidence') if isinstance(final_signal, dict) else 'NULL')}
- 估值可信度: {_nullize_text(final_signal.get('valuation_confidence') if isinstance(final_signal, dict) else 'NULL')}
- 操作可信度: {_nullize_text(final_signal.get('operation_confidence') if isinstance(final_signal, dict) else 'NULL')}
- 法人目標價可信度: {_nullize_text(target_confidence.get('label') if isinstance(target_confidence, dict) else 'NULL')}｜{_nullize_text(target_confidence.get('message') if isinstance(target_confidence, dict) else 'NULL')}

【1. 月營收公告月份與營收動能】
- 營收公告月份標籤: {_nullize_text(latest_rev_display_label)}
- 最新單月營收 YoY [{latest_rev_display_label}]: {panel_rg}
- 最新單月營收 MoM [{latest_rev_display_label}]: {_nullize_text(latest_mom_str)}
- 月營收資料源: {_nullize_text(latest_rev_source)}
- 月營收月份提示: {_nullize_text(latest_rev_notice)}
- 注意: 若查詢當月尚未公告，不可把查詢月份誤當最新公告月份。

【2. EPS 口徑拆欄（不可混用）】
{_prompt_df(eps_report_df, max_rows=10)}

【3. 盤面與基礎估值（系統/AI整合值）】
- 歷史本益比 Trailing P/E: {panel_pe}
- 前瞻本益比 Forward P/E: {panel_fpe}
- 股價淨值比 P/B: {panel_pb}
- 前瞻 PEG: {panel_peg}
- EPS（TTM / Forward 顯示值）: {panel_eps}
- 預估獲利成長 YoY: {panel_eg}
- 毛利率 / 營益率: {panel_gmom}
- ROE（恆等式校正）: {panel_roe}
- 負債權益比 D/E: {panel_de}
- 預估殖利率: {_nullize_text(dy_str)}
- 自由現金流 FCF: {_nullize_text(fcf_str)}
- 流動比率: {_nullize_text(cr_str)}
- Piotroski F-Score: {_nullize_text(fs_str)}（滿分 9 分）

【4. 系統 / AI 分歧警告（2.1 風險層）】
{_prompt_warnings(divergence_warnings)}

【5. 統一資料品質報告（系統 / AI / 採用值）】
{_prompt_df(dq_report_df, max_rows=30)}

【6. 法人目標價與可信度】
- 最高目標價: {_nullize_text(prompt_hi_str)}
- 平均目標價: {_nullize_text(prompt_me_str)}
- 最低保底價: {_nullize_text(prompt_lo_str)}
- AI 最新聯網目標價({ai_label}): {_nullize_text(ai_tp_str)}
- 目標價分析師人數: {_nullize_text(ai_analyst_count)}
- 目標價可信度: {_nullize_text(target_confidence.get('label') if isinstance(target_confidence, dict) else 'NULL')}
- 目標價核心理由: {_nullize_text(ai_target_rationale)}
- 可信度明細:
{_prompt_df(target_confidence_report_for_prompt, max_rows=5)}

【7. 公式估值 / 可操作估值分離】
- 系統逆向推算估值摘要: {ctx_tp_est}
- 可操作估值提示: {_nullize_text(valuation_separation.get('action_hint') if isinstance(valuation_separation, dict) else 'NULL')}
- 可操作估值區間低/中/高: {_nullize_text(valuation_separation.get('operable_low') if isinstance(valuation_separation, dict) else 'NULL')} / {_nullize_text(valuation_separation.get('operable_mid') if isinstance(valuation_separation, dict) else 'NULL')} / {_nullize_text(valuation_separation.get('operable_high') if isinstance(valuation_separation, dict) else 'NULL')}
- 警告數: {_nullize_text(valuation_separation.get('warning_count') if isinstance(valuation_separation, dict) else 'NULL')}；重大警告數: {_nullize_text(valuation_separation.get('danger_count') if isinstance(valuation_separation, dict) else 'NULL')}
- 估值分離表:
{_prompt_df(valuation_report_for_prompt, max_rows=20)}

【8. 產業估值模型】
- 匹配模型: {_nullize_text(industry_profile.get('model_label') if isinstance(industry_profile, dict) else 'NULL')}
- 主分類: {_nullize_text(industry_profile.get('parent_category') if isinstance(industry_profile, dict) else 'NULL')}
- stocklist 分類: {_nullize_text(industry_profile.get('stocklist_category') if isinstance(industry_profile, dict) else 'NULL')}
- 股票對應來源: {_nullize_text(industry_profile.get('mapping_source') if isinstance(industry_profile, dict) else 'NULL')}
- 題材標籤: {_nullize_text(industry_profile.get('themes_text') if isinstance(industry_profile, dict) else 'NULL')}
- 主要估值方式: {_nullize_text(industry_profile.get('primary_valuation') if isinstance(industry_profile, dict) else 'NULL')}
- 次要估值方式: {_nullize_text(industry_profile.get('secondary_valuation') if isinstance(industry_profile, dict) else 'NULL')}
- P/E 模型適用性: {_nullize_text(industry_profile.get('pe_applicability_text') if isinstance(industry_profile, dict) else 'NULL')}
- 校準來源: {_nullize_text(industry_profile.get('calibration_source') if isinstance(industry_profile, dict) else 'NULL')}
- Dynamic Cap floor / soft / hard: {_nullize_text(industry_profile.get('floor_pe') if isinstance(industry_profile, dict) else 'NULL')} / {_nullize_text(industry_profile.get('soft_ceiling_pe') if isinstance(industry_profile, dict) else 'NULL')} / {_nullize_text(industry_profile.get('hard_ceiling_pe') if isinstance(industry_profile, dict) else 'NULL')}
- 事件模型切換: {_nullize_text(industry_profile.get('event_switch_note') if isinstance(industry_profile, dict) else 'NULL')}
- 是否循環股: {_nullize_text(industry_profile.get('cyclical') if isinstance(industry_profile, dict) else 'NULL')}
- 是否有 P/E 陷阱: {_nullize_text(industry_profile.get('pe_trap_warning') if isinstance(industry_profile, dict) else 'NULL')}
- P/B 參考區間: {_nullize_text(industry_profile.get('pb_range') if isinstance(industry_profile, dict) else 'NULL')}
- 風險旗標: {_nullize_text(industry_profile.get('risk_flags') if isinstance(industry_profile, dict) else 'NULL')}
- 產業模型明細:
{_prompt_df(industry_report_for_prompt, max_rows=25)}

【9. Dynamic Cap 2.0 動態本益比 / P/B 模型】
- 使用模型: {_nullize_text(dynamic_cap_pack.get('valuation_mode') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 產業基準倍率: {_nullize_text(dynamic_cap_pack.get('base_multiple') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 原始建議倍率: {_nullize_text(dynamic_cap_pack.get('raw_cap') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 最終建議倍率: {_nullize_text(dynamic_cap_pack.get('final_cap') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 使用者帶入 Cap: {_nullize_text(target_pe_cap)}
- 樓地板 / soft ceiling / hard ceiling: {_nullize_text(dynamic_cap_pack.get('floor_cap') if isinstance(dynamic_cap_pack, dict) else 'NULL')} / {_nullize_text(dynamic_cap_pack.get('soft_ceiling_cap') if isinstance(dynamic_cap_pack, dict) else 'NULL')} / {_nullize_text(dynamic_cap_pack.get('hard_ceiling_cap') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 模型版本: {_nullize_text(dynamic_cap_pack.get('model_version') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- P/B 週期模型 BVPS: {_nullize_text(dynamic_cap_pack.get('bvps') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- P/B 週期估值區間: {_nullize_text(dynamic_cap_pack.get('pb_low_price') if isinstance(dynamic_cap_pack, dict) else 'NULL')} ～ {_nullize_text(dynamic_cap_pack.get('pb_high_price') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 模型提醒: {_nullize_text(dynamic_cap_pack.get('warnings') if isinstance(dynamic_cap_pack, dict) else 'NULL')}
- 倍率拆解表:
{_prompt_df(dynamic_cap_report_for_prompt, max_rows=30)}

【10. 最終操作燈號明細】
{_prompt_df(final_signal_report_for_prompt, max_rows=20)}

【11. AI 逐欄來源追蹤與 JSON 驗證】
- AI 模型/資料期間: {_nullize_text(temp_ai_fin.get('model_used') if isinstance(temp_ai_fin, dict) else 'NULL')}｜{_nullize_text(raw_ai_period)}
- AI JSON 驗證狀態: {_nullize_text(ai_validation_status_for_prompt)}
- AI JSON 驗證警告: {_nullize_text('；'.join([str(x) for x in ai_validation_warnings_for_prompt[:20]]) if ai_validation_warnings_for_prompt else 'NULL')}
- AI 逐欄來源追蹤:
{_prompt_df(ai_source_trace_df_for_prompt, max_rows=30)}
"""

            full_prompt_for_copy = f"""你是台股研究總監 + 交易策略專家。請用繁體中文、條列、可執行結論，並嚴格使用下方 WAY AI 投資戰情室 2.1 數據。

重要原則：
1) 請優先尊重系統 2.1 已產出的「月營收公告月份、EPS 拆欄、分歧警告、資料品質報告、法人目標價可信度、公式估值/可操作估值分離、產業估值模型、Dynamic Cap 2.0、最終操作燈號」。
2) 公式合理估值與公式極限價只代表模型輸出，不可直接當作買進目標；真正操作請以「可操作估值區間」與最終燈號為主。
3) 若系統 / AI 分歧警告存在，必須先說明分歧對估值可信度與操作可信度的影響，不可直接給樂觀目標價。
4) EPS 必須分清楚最新單季 EPS、TTM EPS、完整年度 EPS、系統 Forward EPS、AI Forward EPS、法人共識 Forward EPS，不可混用。
5) 月營收必須以公告月份為準，不可用查詢當月推定最新月營收。
6) 若關鍵欄位為 NULL，需提出替代判斷法；若資料異常，請明確說「暫不適合做買賣判斷」。

任務要求：
1) 先做「2.1 資料品質盤點」：逐項說明哪些欄位是系統/AI/推估/NULL，並指出最影響結論的 3 個資料風險。
2) 解讀「分歧警告」：EPS / YoY / PEG / 合理價 / D/E 若有警告，請說明是否會讓估值降級。
3) 解讀「產業估值模型」：說明這檔股票適合用哪些估值指標，不適合用哪些指標。
4) 解讀「公式估值 vs 可操作估值」：請分開說明公式合理價、公式極限價、可操作估值區間，不可混成同一個目標價。
5) 交易決策：
   - 先引用系統最終燈號，再判斷是否同意。
   - 給「可買 / 觀望 / 不建議 / 資料異常」之一。
   - 買點：給 2~3 個分批區間與理由。
   - 賣點：給 2~3 個減碼 / 停利 / 停損條件。
   - 倉位建議：保守 / 中性 / 積極三種配置比例。
6) 三情境目標價：牛市 / 基準 / 熊市，各列目標價區間、假設前提、觸發條件。
7) 下月追蹤清單：列出 8 個要追蹤的指標與警戒閾值，必須包含月營收 YoY、MoM、毛利率、EPS、法人目標價或 EPS 預估調整。

輸出格式（必須照做）：
- [投資結論一句話]
- [2.1 資料品質與分歧警告]
- [產業估值模型解讀]
- [公式估值 vs 可操作估值]
- [公司優缺點]
- [買點 / 賣點 / 停損停利]
- [三情境目標價]
- [風險與反證]
- [下月追蹤清單]

以下是系統面板完整數據（含網路抓取 / AI 抓取 / 推估 / 2.1 風險判斷；無資料為 NULL）。若出現數據不合理，可上網查詢並說明不合理原因，但不可忽略系統已標示的分歧與資料品質警告：
{context_str}
"""
            
            # 將原本的 AI 按鈕移除，並將提示詞區塊設為展開且全寬度顯示
            with st.expander("📋 點此複製【打包提示詞】至 Gemini Advanced 或 ChatGPT 發問", expanded=True):
                st.markdown(
                    "<small style='color:gray;'>*手機版可直接按下方按鈕複製；電腦版也可在文字框內全選 (Ctrl+A / ⌘+A) 並複製。*</small>",
                    unsafe_allow_html=True
                )

                # 用 json.dumps 包裝提示詞，避免換行、引號或特殊符號造成 JavaScript 失效。
                safe_prompt_js = json.dumps(full_prompt_for_copy, ensure_ascii=False)
                components.html(
                    f"""
                    <div style="margin: 10px 0 12px 0; font-family: sans-serif;">
                        <button
                            onclick="copyPromptToClipboard()"
                            style="
                                width: 100%;
                                padding: 13px 14px;
                                border-radius: 10px;
                                border: 1px solid #4b5563;
                                background: #2563eb;
                                color: white;
                                font-size: 16px;
                                font-weight: 700;
                                cursor: pointer;
                            "
                        >
                            📋 一鍵複製完整提示詞
                        </button>
                        <div id="copyStatus" style="margin-top: 8px; color: #16a34a; font-size: 14px;"></div>
                    </div>

                    <script>
                    async function copyPromptToClipboard() {{
                        const text = {safe_prompt_js};
                        const status = document.getElementById("copyStatus");

                        try {{
                            await navigator.clipboard.writeText(text);
                            status.innerText = "✅ 已複製完整提示詞，可直接貼到 Gemini Advanced 或 ChatGPT。";
                        }} catch (err) {{
                            const textarea = document.createElement("textarea");
                            textarea.value = text;
                            textarea.style.position = "fixed";
                            textarea.style.left = "-9999px";
                            textarea.style.top = "0";
                            document.body.appendChild(textarea);
                            textarea.focus();
                            textarea.select();

                            try {{
                                document.execCommand("copy");
                                status.innerText = "✅ 已複製完整提示詞，可直接貼上使用。";
                            }} catch (fallbackErr) {{
                                status.style.color = "#dc2626";
                                status.innerText = "⚠️ 手機瀏覽器限制自動複製，請改用下方文字框長按複製。";
                            }}

                            document.body.removeChild(textarea);
                        }}
                    }}
                    </script>
                    """,
                    height=105,
                )

                st.text_area(
                    "提示詞內容",
                    value=full_prompt_for_copy,
                    height=300,
                    label_visibility="collapsed",
                    key=f"copy_prompt_textarea_{curr_id}"
                )
            
            st.markdown("---")

            # ⚔️ 產業同業 PK
            if st.session_state.show_pk:
                st.markdown("#### ⚔️ 產業橫向對比 (同業估值與利潤率 PK)")
                st.markdown("<small style='color:gray;'>*註：透過 AI 動態檢索業務相近的競爭對手，並抓取最新財報數據進行橫向比較。*</small>", unsafe_allow_html=True)
                with st.spinner("AI 正在深度檢索產業鏈與競爭對手，並同步抓取最新財報數據..."):
                    peers = get_peers_from_ai(c_name, curr_id, st.session_state.api_key)
                    if peers:
                        compare_list = [curr_id] + [p for p in peers if p != curr_id]
                        compare_data = []
                        for code in compare_list:
                            _, p_info = get_stock_data(code, st.session_state.fugle_key, st.session_state.finmind_key)
                            p_name = get_chinese_name(code) or code
                            if p_info:
                                pe_val = s_float(p_info.get("trailingPE"))
                                pe_fmt = f"{pe_val:.2f}x" if pe_val is not None else "N/A"
                                gm_fmt = to_pct(s_float(p_info.get('grossMargins')))
                                om_fmt = to_pct(s_float(p_info.get('operatingMargins')))
                                roe_fmt = to_pct(s_float(p_info.get('returnOnEquity')))
                                prev_close_val = s_float(p_info.get("previousClose"))
                                prev_close_fmt = f"{prev_close_val:.2f}" if prev_close_val is not None else "N/A"
                                t_eps_p = s_float(p_info.get('trailingEps'))
                                f_eps_p = s_float(p_info.get('forwardEps'))
                                t_eps_p_str = f"{t_eps_p:.2f}" if t_eps_p is not None else "N/A"
                                f_eps_p_str = f"{f_eps_p:.2f}" if f_eps_p is not None else "N/A"
                                eps_display = f"{t_eps_p_str} / <span style='color:#00bfff;'>{f_eps_p_str}</span>"
                                if prev_close_val is not None and f_eps_p is not None and f_eps_p > 0: fpe_fmt = f"<b style='color:#FFD700;'>{prev_close_val / f_eps_p:.1f}x</b>"
                                else: fpe_fmt = "<span style='color:gray;'>N/A</span>"
                                target_mean_p = s_float(p_info.get('targetMeanPrice'))
                                if target_mean_p is not None and prev_close_val is not None and prev_close_val > 0:
                                    upside = ((target_mean_p - prev_close_val) / prev_close_val) * 100
                                    if upside >= 25: upside_fmt = f"<span style='color:#ff4d4d; font-weight:bold;'>+{upside:.1f}%</span>"
                                    elif upside > 0: upside_fmt = f"<span style='color:#00cc66;'>+{upside:.1f}%</span>"
                                    else: upside_fmt = f"<span style='color:#aaa;'>{upside:.1f}%</span>"
                                    target_display = f"{target_mean_p:.1f} ({upside_fmt})"
                                else: target_display = "<span style='color:gray;'>無資料</span>"
                                compare_data.append({"代號": f"{p_name} ({code})", "股價": prev_close_fmt, "前瞻 P/E": fpe_fmt, "預估 EPS": eps_display, "目標價": target_display, "毛利率": gm_fmt, "營益率": om_fmt, "ROE": roe_fmt})
                        if compare_data:
                            table_html = "<table style='width:100%; text-align:center; border-collapse: collapse; margin-top: 10px; font-size: 1.05rem; color: #e0e0e0;'><tr style='background-color:#333; color:#fff; border-bottom: 2px solid #555;'><th style='padding:12px;'>公司名稱</th><th>最新收盤價</th><th>前瞻 P/E</th><th>預估 EPS (今/明)</th><th>目標價 (潛在空間)</th><th>毛利率</th><th>營益率</th><th>ROE</th></tr>"
                            for d in compare_data:
                                row_bg = "#2c3e50" if str(curr_id) in d['代號'] else "#1e1e1e" 
                                table_html += f"<tr style='background-color:{row_bg}; border-bottom:1px solid #444;'><td style='padding:12px; color:#ffffff;'><b>{d['代號']}</b></td><td>{d['股價']}</td><td>{d['前瞻 P/E']}</td><td>{d['預估 EPS']}</td><td>{d['目標價']}</td><td>{d['毛利率']}</td><td>{d['營益率']}</td><td style='color:#00bfff;'><b>{d['ROE']}</b></td></tr>"
                            table_html += "</table>"
                            st.markdown(table_html, unsafe_allow_html=True)
                    else: st.error("AI 暫時找不到明確的同業數據，或請檢查您的 API Key 額度。")
                st.markdown("---")

            # 🌊 雙河流圖 (Tabs) 
            if df_per_bk is not None and not df_per_bk.empty:
                st.markdown("### 🌊 估值位階雙河流圖 (P/E & P/B River)")
                st.markdown("<small style='color:gray;'>*實戰密技：『成長股』看本益比判斷潛力；『景氣循環股』(航運/鋼鐵/面板) 獲利不穩定，必須看淨值比(P/B)河流圖抄底！*</small>", unsafe_allow_html=True)
            
                h_reset = hist.copy()
                h_reset.index.name = 'Date'
                h_reset = h_reset.reset_index()
            
                if h_reset['Date'].dt.tz is not None: h_reset['Date'] = h_reset['Date'].dt.tz_localize(None)
                h_reset['Date_only'] = h_reset['Date'].dt.date
            
                d_per = df_per_bk.drop_duplicates(subset=['date'], keep='last').copy()
                d_per['date_only'] = d_per['date'].dt.date
                h_reset = h_reset.drop_duplicates(subset=['Date_only'], keep='last')

                merged = pd.merge(h_reset, d_per, left_on='Date_only', right_on='date_only', how='inner').sort_values('Date_only')

                if not merged.empty: 
                    tab_pe, tab_pb = st.tabs(["🌊 本益比河流圖 (P/E River)", "⚓ 股價淨值比河流圖 (P/B River - 循環股剋星)"])
                
                    with tab_pe:
                        merged_pe = merged[merged['PER'] > 0].copy()
                        if len(merged_pe) > 60:
                            merged_pe['EPS_calc'] = merged_pe['Close'] / merged_pe['PER']
                            pe_quantiles = merged_pe['PER'].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).values

                            fig_river = go.Figure()
                            b1 = merged_pe['EPS_calc'] * pe_quantiles[0]
                            b2 = merged_pe['EPS_calc'] * pe_quantiles[1]
                            b3 = merged_pe['EPS_calc'] * pe_quantiles[2]
                            b4 = merged_pe['EPS_calc'] * pe_quantiles[3]
                            b5 = merged_pe['EPS_calc'] * pe_quantiles[4]

                            fig_river.add_trace(go.Scatter(x=merged_pe['Date'], y=b1, mode='lines', line=dict(color='#00cc66', width=1), name=f'悲觀區 ({pe_quantiles[0]:.1f}x)'))
                            fig_river.add_trace(go.Scatter(x=merged_pe['Date'], y=b2, mode='lines', fill='tonexty', fillcolor='rgba(0, 204, 102, 0.2)', line=dict(color='#00cc66', width=1), name=f'低估區 ({pe_quantiles[1]:.1f}x)'))
                            fig_river.add_trace(go.Scatter(x=merged_pe['Date'], y=b3, mode='lines', fill='tonexty', fillcolor='rgba(255, 215, 0, 0.2)', line=dict(color='#FFD700', width=1), name=f'合理區 ({pe_quantiles[2]:.1f}x)'))
                            fig_river.add_trace(go.Scatter(x=merged_pe['Date'], y=b4, mode='lines', fill='tonexty', fillcolor='rgba(255, 140, 0, 0.2)', line=dict(color='#ff8c00', width=1), name=f'高估區 ({pe_quantiles[3]:.1f}x)'))
                            fig_river.add_trace(go.Scatter(x=merged_pe['Date'], y=b5, mode='lines', fill='tonexty', fillcolor='rgba(255, 77, 77, 0.2)', line=dict(color='#ff4d4d', width=1), name=f'瘋狂區 ({pe_quantiles[4]:.1f}x)'))
                            fig_river.add_trace(go.Scatter(x=merged_pe['Date'], y=merged_pe['Close'], mode='lines', line=dict(color='#0033cc', width=3), name='實際股價'))

                            current_pe = merged_pe['PER'].iloc[-1]
                            current_price = merged_pe['Close'].iloc[-1]
                        
                            if current_price <= b2.iloc[-1]: pe_status, status_color = "🔥 處於歷史低估區間！(潛在買點)", "#00cc66"
                            elif current_price >= b5.iloc[-1]: pe_status, status_color = "🚨 突破歷史瘋狂區間！(極度高估)", "#ff4d4d"
                            elif current_price >= b4.iloc[-1]: pe_status, status_color = "⚠️ 處於歷史高估區間！(留意風險)", "#ff8c00"
                            else: pe_status, status_color = "⚖️ 處於歷史合理區間", "#FFD700"

                            fig_river.update_layout(height=450, margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), hovermode="x unified")
                            fig_river.update_yaxes(title_text="股價 (元)", showgrid=True, gridcolor='#e0e0e0')

                            st.markdown(f"<div style='background:#f8f9fa; border-left:4px solid {status_color}; padding:10px; border-radius:5px; margin-bottom:10px; color:#333;'>目前位階推估：<b><span style='color:{status_color};'>{pe_status}</span></b> (最新本益比約 {current_pe:.1f}x)</div>", unsafe_allow_html=True)
                            st.plotly_chart(fig_river, use_container_width=True)
                        else:
                            st.info("⚠️ 缺乏足夠的有效本益比數據 (通常因為過去常處於虧損狀態)，建議切換查看「股價淨值比河流圖」。")

                    with tab_pb:
                        merged_pb = merged[merged['PBR'] > 0].copy()
                        if len(merged_pb) > 60:
                            merged_pb['BVPS_calc'] = merged_pb['Close'] / merged_pb['PBR']
                            pb_quantiles = merged_pb['PBR'].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).values

                            fig_pb = go.Figure()
                            pb1 = merged_pb['BVPS_calc'] * pb_quantiles[0]
                            pb2 = merged_pb['BVPS_calc'] * pb_quantiles[1]
                            pb3 = merged_pb['BVPS_calc'] * pb_quantiles[2]
                            pb4 = merged_pb['BVPS_calc'] * pb_quantiles[3]
                            pb5 = merged_pb['BVPS_calc'] * pb_quantiles[4]

                            fig_pb.add_trace(go.Scatter(x=merged_pb['Date'], y=pb1, mode='lines', line=dict(color='#00cc66', width=1), name=f'悲觀區 ({pb_quantiles[0]:.2f}x)'))
                            fig_pb.add_trace(go.Scatter(x=merged_pb['Date'], y=pb2, mode='lines', fill='tonexty', fillcolor='rgba(0, 204, 102, 0.2)', line=dict(color='#00cc66', width=1), name=f'低估區 ({pb_quantiles[1]:.2f}x)'))
                            fig_pb.add_trace(go.Scatter(x=merged_pb['Date'], y=pb3, mode='lines', fill='tonexty', fillcolor='rgba(255, 215, 0, 0.2)', line=dict(color='#FFD700', width=1), name=f'合理區 ({pb_quantiles[2]:.2f}x)'))
                            fig_pb.add_trace(go.Scatter(x=merged_pb['Date'], y=pb4, mode='lines', fill='tonexty', fillcolor='rgba(255, 140, 0, 0.2)', line=dict(color='#ff8c00', width=1), name=f'高估區 ({pb_quantiles[3]:.2f}x)'))
                            fig_pb.add_trace(go.Scatter(x=merged_pb['Date'], y=pb5, mode='lines', fill='tonexty', fillcolor='rgba(255, 77, 77, 0.2)', line=dict(color='#ff4d4d', width=1), name=f'瘋狂區 ({pb_quantiles[4]:.2f}x)'))
                            fig_pb.add_trace(go.Scatter(x=merged_pb['Date'], y=merged_pb['Close'], mode='lines', line=dict(color='#0033cc', width=3), name='實際股價'))

                            current_pb = merged_pb['PBR'].iloc[-1]
                            current_price_pb = merged_pb['Close'].iloc[-1]
                        
                            if current_price_pb <= pb2.iloc[-1]: pb_status, status_color_pb = "⚓ 跌入歷史低估淨值區！(循環股潛買點)", "#00cc66"
                            elif current_price_pb >= pb5.iloc[-1]: pb_status, status_color_pb = "🚨 突破歷史瘋狂淨值區！(極度高估)", "#ff4d4d"
                            elif current_price_pb >= pb4.iloc[-1]: pb_status, status_color_pb = "⚠️ 處於歷史高估淨值區！(留意風險)", "#ff8c00"
                            else: pb_status, status_color_pb = "⚖️ 處於歷史合理淨值區", "#FFD700"

                            fig_pb.update_layout(height=450, margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), hovermode="x unified")
                            fig_pb.update_yaxes(title_text="股價 (元)", showgrid=True, gridcolor='#e0e0e0')

                            st.markdown(f"<div style='background:#f8f9fa; border-left:4px solid {status_color_pb}; padding:10px; border-radius:5px; margin-bottom:10px; color:#333;'>目前位階推估：<b><span style='color:{status_color_pb};'>{pb_status}</span></b> (最新淨值比約 {current_pb:.2f}x)</div>", unsafe_allow_html=True)
                            st.plotly_chart(fig_pb, use_container_width=True)
                        else:
                            st.info("缺乏足夠的淨值比數據。")
            st.markdown("---")

            # ==========================================
            # 🚀 專業技術線圖與 KD 指標
            # ==========================================
            st.markdown("### 🤖 專業技術線圖與量化型態分析")
        
            chart_tf = st.radio("切換 K 線週期：", ["60分線", "日線", "週線", "月線"], index=1, horizontal=True)
        
            if chart_tf == "日線":
                chart_df = hist.copy()
            else:
                with st.spinner(f"載入 {chart_tf} 數據中..."):
                    chart_df = get_chart_data(curr_id, chart_tf, st.session_state.fugle_key)
            
            if chart_df.empty: full_df = hist.copy() 
            else: full_df = chart_df.copy()

            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col not in full_df.columns: full_df[col] = 0.0
            
            full_df['MA5'] = full_df['Close'].rolling(5).mean()
            full_df['MA10'] = full_df['Close'].rolling(10).mean()
            full_df['MA20'] = full_df['Close'].rolling(20).mean()
            full_df['MA60'] = full_df['Close'].rolling(60).mean()
            full_df['Vol_MA20'] = full_df['Volume'].rolling(20).mean()
        
            h9, l9 = full_df['High'].rolling(9).max(), full_df['Low'].rolling(9).min()
            h9_l9_diff = h9 - l9
            h9_l9_diff[h9_l9_diff == 0] = 1e-9 
            rsv = (full_df['Close'] - l9) / h9_l9_diff * 100
        
            K, D = [50], [50]
            for v in rsv.fillna(50):
                K.append(K[-1]*(2/3) + v*(1/3))
                D.append(D[-1]*(2/3) + K[-1]*(1/3))
            full_df['K'], full_df['D'] = K[1:], D[1:]
        
            plot_df = full_df.tail(120).copy()
        
            if not inst_df.empty:
                # 🛠️ 修復時區問題：強制移除 K 線圖日期的時區，才能跟 FinMind 的日期精準對齊
                temp_dates = pd.to_datetime(plot_df.index)
                if temp_dates.tz is not None:
                    temp_dates = temp_dates.tz_localize(None)
                temp_dates = temp_dates.normalize()
            
                inst_df_aligned = inst_df.copy()
                inst_df_aligned.index = pd.to_datetime(inst_df_aligned.index).normalize()
            
                plot_df['Foreign'] = temp_dates.map(inst_df_aligned['Foreign']).fillna(0)
                plot_df['Trust'] = temp_dates.map(inst_df_aligned['Trust']).fillna(0)
                plot_df['Dealer'] = temp_dates.map(inst_df_aligned['Dealer']).fillna(0)
            else:
                plot_df['Foreign'] = 0; plot_df['Trust'] = 0; plot_df['Dealer'] = 0

            def safe_val(series, fallback=0):
                if len(series) == 0: return fallback
                val = series.iloc[-1]
                return val if not pd.isna(val) else fallback

            last_close = safe_val(plot_df['Close'])
            ma5_last = safe_val(plot_df['MA5'], last_close)
            ma20_last = safe_val(plot_df['MA20'], last_close)
            ma60_last = safe_val(plot_df['MA60'], ma20_last)
            k_last = safe_val(plot_df['K'], 50)
            d_last = safe_val(plot_df['D'], 50)
        
            recent_20 = plot_df.tail(20)
            recent_high = recent_20['High'].max() if not recent_20.empty else last_close
            recent_low = recent_20['Low'].min() if not recent_20.empty else last_close
        
            if not recent_20.empty and 'Volume' in recent_20.columns and recent_20['Volume'].sum() > 0:
                max_vol_idx = recent_20['Volume'].idxmax()
                max_vol_day = recent_20.loc[max_vol_idx]
                is_high_vol = max_vol_day['Volume'] > (max_vol_day['Vol_MA20'] * 2)
                is_at_high = max_vol_day['High'] >= (recent_high * 0.95)
                is_dropping = last_close < max_vol_day['Low']
                high_vol_warning = is_high_vol and is_at_high and is_dropping
                vol_escape_price = max_vol_day['High']
            else:
                high_vol_warning = False
                vol_escape_price = last_close
        
            support_price = max(recent_low, ma60_last) if last_close > ma60_last else recent_low
            resist_price = recent_high if last_close > ma20_last else min(recent_high, ma20_last)

            if last_close < ma60_last: trend_status, trend_color = "⚠️ 跌破長線支撐 (趨勢轉弱)", "#00cc66"
            elif last_close > ma20_last and ma5_last > ma20_last: trend_status, trend_color = "📈 多頭強勢 (站上短中均線)", "#ff4d4d"
            elif last_close < ma20_last and ma5_last < ma20_last: trend_status, trend_color = "📉 空頭弱勢 (跌破中線)", "#00cc66"
            else: trend_status, trend_color = "↔️ 區間震盪 (方向未明)", "#ffd700"
            
            if high_vol_warning: adv_text, buy_rec, sell_rec = "🚨 【量價警訊】高檔爆出天量且跌破低點，切勿盲目接刀！", "強烈觀望", f"反彈至 {vol_escape_price:.2f} 逃命"
            elif last_close < ma60_last: adv_text, buy_rec, sell_rec = "📉 【趨勢轉弱】跌破長期均線，應耐心等待底部確立。", "等待站回均線", f"{ma60_last:.2f} (長線壓力)"
            elif k_last < 25 and k_last > d_last: adv_text, buy_rec, sell_rec = "📈 【技術反彈】KD 低檔黃金交叉，可嘗試逢低少量佈局。", f"現價~{support_price:.2f} 附近", f"{resist_price:.2f} (上檔壓力)"
            elif k_last > 80 and k_last < d_last: adv_text, buy_rec, sell_rec = "⚠️ 【動能轉弱】KD 高檔死亡交叉，建議適度獲利了結保住利潤。", "暫時觀望", f"現價~{resist_price:.2f} 附近"
            elif last_close > ma20_last: adv_text, buy_rec, sell_rec = "🔥 【多方格局】量價配合良好，拉回中線(20MA)有守可伺機介入。", f"{ma20_last:.2f} (中線支撐)", f"{resist_price:.2f} (近期前高)"
            else: adv_text, buy_rec, sell_rec = "❄️ 【空方格局】短線均線反壓，反彈至均線壓力區可考慮減碼。", "等待技術面打底", f"{ma20_last:.2f} (中線壓力)"

            st.markdown(f"""
            <div style='background:#1e1e1e; padding:15px; border-radius:8px; border:1px solid #333; margin-bottom:20px;'>
                <h4 style='margin-top:0; color:#fff;'>🎯 演算法量化交易策略</h4>
                <div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;'>
                    <div style='flex:1; min-width:120px;'><div style='color:#aaa; font-size:0.9rem;'>目前趨勢</div><div style='font-size:1.1rem; font-weight:bold; color:{trend_color};'>{trend_status}</div></div>
                    <div style='flex:1; min-width:120px;'><div style='color:#aaa; font-size:0.9rem;'>下檔支撐</div><div style='font-size:1.1rem; font-weight:bold; color:#00bfff;'>{support_price:.2f}</div></div>
                    <div style='flex:1; min-width:120px;'><div style='color:#aaa; font-size:0.9rem;'>上檔壓力</div><div style='font-size:1.1rem; font-weight:bold; color:#ab82ff;'>{resist_price:.2f}</div></div>
                    <div style='flex:1; min-width:120px;'><div style='color:#aaa; font-size:0.9rem;'>建議買點</div><div style='font-size:1.1rem; font-weight:bold; color:#ff4d4d;'>{buy_rec}</div></div>
                    <div style='flex:1; min-width:120px;'><div style='color:#aaa; font-size:0.9rem;'>建議賣點</div><div style='font-size:1.1rem; font-weight:bold; color:#00cc66;'>{sell_rec}</div></div>
                </div>
                <div style='margin-top:15px; padding-top:10px; border-top:1px dashed #444;'><span style='color:#aaa; font-size:0.9rem;'>💡 策略解析：</span><span style='color:#ffd700; font-weight:bold;'>{adv_text}</span></div>
            </div>
            """.replace('\n', ''), unsafe_allow_html=True)
        
            def get_ma_trend(ma_series):
                if len(ma_series) < 2 or pd.isna(ma_series.iloc[-1]): return 0.0, "-", "#aaa"
                last_val = ma_series.iloc[-1]
                prev_val = ma_series.iloc[-2]
                if pd.isna(prev_val): return last_val, "-", "#aaa"
                if last_val > prev_val: return last_val, "▲", "#ff4d4d"
                elif last_val < prev_val: return last_val, "▼", "#00cc66"
                return last_val, "-", "#aaa"
            
            m5_v, m5_d, m5_c = get_ma_trend(plot_df['MA5'])
            m10_v, m10_d, m10_c = get_ma_trend(plot_df['MA10'])
            m20_v, m20_d, m20_c = get_ma_trend(plot_df['MA20'])
            m60_v, m60_d, m60_c = get_ma_trend(plot_df['MA60'])

            ma_html = f"""
            <div style='display: flex; gap: 20px; font-size: 1.05rem; padding: 10px 15px; background: #1e1e1e; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px; flex-wrap: wrap; align-items: center;'>
                <div style='color: #fff;'><span style='color: #00bfff; font-size:1.2rem; vertical-align:middle;'>■</span> <b>MA5</b> {m5_v:.2f} <span style='color:{m5_c}; font-size:0.9rem;'>{m5_d}</span></div>
                <div style='color: #fff;'><span style='color: #ab82ff; font-size:1.2rem; vertical-align:middle;'>■</span> <b>MA10</b> {m10_v:.2f} <span style='color:{m10_c}; font-size:0.9rem;'>{m10_d}</span></div>
                <div style='color: #fff;'><span style='color: #ff8c00; font-size:1.2rem; vertical-align:middle;'>■</span> <b>MA20</b> {m20_v:.2f} <span style='color:{m20_c}; font-size:0.9rem;'>{m20_d}</span></div>
                <div style='color: #fff;'><span style='color: #ffd700; font-size:1.2rem; vertical-align:middle;'>■</span> <b>MA60</b> {m60_v:.2f} <span style='color:{m60_c}; font-size:0.9rem;'>{m60_d}</span></div>
            </div>
            """
            st.markdown(clean_html(ma_html), unsafe_allow_html=True)
        
            fig_k = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25], vertical_spacing=0.05, specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}]])
        
            fig_k.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='K線', increasing_line_color='#ff4d4d', decreasing_line_color='#00cc66'), row=1, col=1, secondary_y=False)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA5'], mode='lines', name='5MA', line=dict(color='#00bfff', width=2.5)), row=1, col=1, secondary_y=False)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA10'], mode='lines', name='10MA', line=dict(color='#ab82ff', width=1.8)), row=1, col=1, secondary_y=False)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA20'], mode='lines', name='20MA', line=dict(color='#ff8c00', width=1.8)), row=1, col=1, secondary_y=False)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA60'], mode='lines', name='60MA', line=dict(color='#ffd700', width=1.8)), row=1, col=1, secondary_y=False)
        
            vol_colors = ['#ff4d4d' if c >= o else '#00cc66' for c, o in zip(plot_df['Close'], plot_df['Open'])]
            fig_k.add_trace(go.Bar(x=plot_df.index, y=plot_df['Volume']/1000, marker_color=vol_colors, name='成交量(張)', opacity=0.5), row=1, col=1, secondary_y=True)
        
            f_colors = ['#ff4d4d' if v > 0 else '#00cc66' for v in plot_df['Foreign']]
            t_colors = ['#ff4d4d' if v > 0 else '#00cc66' for v in plot_df['Trust']]
            d_colors = ['#ff4d4d' if v > 0 else '#00cc66' for v in plot_df['Dealer']]
            fig_k.add_trace(go.Bar(x=plot_df.index, y=plot_df['Foreign'], name='外資', marker_color=f_colors, opacity=0.8), row=2, col=1)
            fig_k.add_trace(go.Bar(x=plot_df.index, y=plot_df['Trust'], name='投信', marker_color=t_colors, opacity=0.8), row=2, col=1)
            fig_k.add_trace(go.Bar(x=plot_df.index, y=plot_df['Dealer'], name='自營商', marker_color=d_colors, opacity=0.8), row=2, col=1)

            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['K'], mode='lines', name='K9', line=dict(color='#00bfff', width=1.5)), row=3, col=1, secondary_y=False)
            fig_k.add_trace(go.Scatter(x=plot_df.index, y=plot_df['D'], mode='lines', name='D9', line=dict(color='#ff8c00', width=1.5)), row=3, col=1, secondary_y=False)
        
            max_vol = plot_df['Volume'].max() / 1000 if not plot_df['Volume'].empty else 100
            fig_k.update_yaxes(side="left", showgrid=False, showticklabels=False, range=[0, max_vol * 3.5], secondary_y=True, row=1, col=1)
            fig_k.update_yaxes(side="right", mirror=True, showline=True, linecolor='#555', secondary_y=False, row=1, col=1)
            fig_k.update_yaxes(title_text="買賣超(張)", side="right", mirror=True, showline=True, linecolor='#555', row=2, col=1)
            fig_k.update_yaxes(range=[0, 100], dtick=20, side="right", mirror=True, showline=True, linecolor='#555', row=3, col=1)
        
            if not plot_df.empty and chart_tf == "日線":
                idx_norm = plot_df.index.normalize()
                dt_all = pd.date_range(start=idx_norm[0], end=idx_norm[-1])
                dt_obs = [d.strftime("%Y-%m-%d") for d in idx_norm]
                dt_breaks = [d.strftime("%Y-%m-%d") for d in dt_all if d.strftime("%Y-%m-%d") not in dt_obs]
            else:
                dt_breaks = []

            if chart_tf == "60分線":
                x_fmt = "%m/%d %H:%M"
                rb = [dict(bounds=["sat", "mon"]), dict(bounds=[13.5, 9], pattern="hour")]
            elif chart_tf == "月線":
                x_fmt = "%Y/%m"
                rb = [] 
            elif chart_tf == "週線":
                x_fmt = "%Y/%m/%d"
                rb = [] 
            else: 
                x_fmt = "%m/%d"
                rb = [dict(bounds=["sat", "mon"])] 
                if dt_breaks:
                    rb.append(dict(values=dt_breaks)) 

            fig_k.update_xaxes(rangebreaks=rb, tickformat=x_fmt, showgrid=True, gridcolor='#333', mirror=True, showline=True, linecolor='#555')
            fig_k.update_layout(height=750, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=10,b=10), template="plotly_dark", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            st.plotly_chart(fig_k, use_container_width=True)
        else:
            st.error(f"找不到代號 {curr_id} 的資料，請確認代號是否正確或重新整理。")
