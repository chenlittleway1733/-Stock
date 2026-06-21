"""
側邊欄 UI 模組：
包含個股查詢、自選股管理器、策略漏斗掃描器。
"""
import io

from ui_common import *
from validators.stock_dataset_batch import read_stock_dataset_file, validate_stock_dataset_frame

def render_sidebar():
    """渲染左側欄，並回傳主畫面需要共用的 sidebar 狀態。"""
    # ==========================================
    # 4. 側邊欄：功能選單與策略漏斗
    # ==========================================
    with st.sidebar:
        st.markdown("### 🔍 個股查詢")
        st.text_input("輸入台股代號", value=st.session_state.selected_stock, key="stock_input_widget", on_change=on_stock_input_change)
        st.markdown("<div style='color:#ff8c00; font-size:0.8rem; margin-top:-10px; margin-bottom:10px;'>💡 提示：輸入完畢請務必按 <b>Enter 鍵</b> 確認送出</div>", unsafe_allow_html=True)
    
        options = ["-- 快速切換標的 --"]
        categories = {"未分類": []}
        current_cat = "未分類"
        if os.path.exists("stocklist.txt"):
            try:
                with open("stocklist.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        if "," in line:
                            p = line.split(",")
                            if len(p) >= 2:
                                options.append(f"　🔸 {p[0].strip()} {p[1].strip()}")
                                categories[current_cat].append((p[0].strip(), p[1].strip()))
                        else:
                            current_cat = line
                            options.append(f"🏷️ {line}")
                            categories[current_cat] = []
            except Exception as e:
                st.warning(f"⚠️ 快速選股名單讀取失敗，已改用最小模式。({str(e)[:80]})")
            
        st.selectbox("⚡ 快速選股名單", options, key="quick_select", on_change=on_quick_select_change)
        if st.button("🗂️ 自選股管理器", use_container_width=True):
            st.session_state.show_watchlist_manager = not st.session_state.get('show_watchlist_manager', False)

        if st.session_state.get('show_watchlist_manager', False):
            with st.container():
                st.markdown("#### 🛠️ 自選股管理器")
                cat_order, cat_map, parse_errors = load_stocklist_structure()
                if parse_errors:
                    st.warning("⚠️ 偵測到檔案格式問題：" + "；".join(parse_errors[:3]))

                issues = validate_stocklist_structure(cat_order, cat_map)
                if issues:
                    st.error("❌ 格式驗證未通過：" + "；".join(issues[:3]))
                else:
                    st.success("✅ 檔案格式驗證通過")

                with st.expander("➕ 新增分類", expanded=False):
                    new_cat = st.text_input("分類名稱", key="mgr_new_cat")
                    if st.button("新增分類", key="mgr_add_cat_btn", use_container_width=True):
                        ok, msg = add_category_to_stocklist(new_cat)
                        (st.success if ok else st.error)(msg)
                        if ok: st.rerun()

                with st.expander("➕ 新增股票", expanded=False):
                    mcol1, mcol2 = st.columns(2)
                    with mcol1:
                        new_code = st.text_input("股票代號", key="mgr_new_code")
                    with mcol2:
                        new_name = st.text_input("股票名稱", key="mgr_new_name")
                    cat_choices = cat_order if cat_order else ["未分類"]
                    new_cat_target = st.selectbox("加入到分類", cat_choices, key="mgr_target_cat")
                    if st.button("新增股票", key="mgr_add_stock_btn", use_container_width=True):
                        ok, msg = add_stock_to_category(new_code, new_name, new_cat_target)
                        (st.success if ok else st.error)(msg)
                        if ok: st.rerun()

                all_stocks = [(c, n, cat) for cat in cat_order for c, n in cat_map.get(cat, [])]
                if all_stocks:
                    with st.expander("🔀 搬移股票", expanded=False):
                        stock_labels = [f"{c} {n}（{cat}）" for c, n, cat in all_stocks]
                        picked = st.selectbox("選擇股票", stock_labels, key="mgr_move_pick")
                        target_cat = st.selectbox("目標分類", cat_order if cat_order else ["未分類"], key="mgr_move_target")
                        pick_code = picked.split(" ")[0]
                        if st.button("搬移到新分類", key="mgr_move_btn", use_container_width=True):
                            ok, msg = move_stock_to_category(pick_code, target_cat)
                            (st.success if ok else st.error)(msg)
                            if ok: st.rerun()

                    with st.expander("🧹 刪除股票", expanded=False):
                        del_pick = st.selectbox("選擇要刪除的股票", stock_labels, key="mgr_del_pick")
                        del_code = del_pick.split(" ")[0]
                        if st.button("刪除股票", key="mgr_del_btn", use_container_width=True):
                            ok, msg = remove_stock_from_stocklist(del_code)
                            (st.success if ok else st.error)(msg)
                            if ok: st.rerun()

                    with st.expander("↕️ 分類內排序（拖曳替代）", expanded=False):
                        sort_cat = st.selectbox("排序分類", cat_order, key="mgr_sort_cat")
                        sort_arr = cat_map.get(sort_cat, [])
                        for i, (sc, sn) in enumerate(sort_arr):
                            c1, c2, c3 = st.columns([0.64, 0.18, 0.18])
                            with c1:
                                st.caption(f"{i+1}. {sc} {sn}")
                            with c2:
                                if st.button("⬆️", key=f"mgr_up_{sort_cat}_{sc}_{i}", use_container_width=True):
                                    ok, msg = move_stock_order_within_category(sort_cat, sc, "up")
                                    (st.success if ok else st.warning)(msg)
                                    if ok: st.rerun()
                            with c3:
                                if st.button("⬇️", key=f"mgr_dn_{sort_cat}_{sc}_{i}", use_container_width=True):
                                    ok, msg = move_stock_order_within_category(sort_cat, sc, "down")
                                    (st.success if ok else st.warning)(msg)
                                    if ok: st.rerun()
                else:
                    st.info("目前尚無股票資料，可先新增分類或股票。")

        with st.expander("🧪 模型資料驗證閘門", expanded=False):
            st.caption("上傳 M03/M06/M07 類型 Excel 或 CSV；只產出驗證結果，不寫入 stock_mapping.py 或倍率檔。")
            uploaded_model_file = st.file_uploader(
                "上傳模型資料檔",
                type=["xlsx", "xlsm", "xls", "csv"],
                key="stock_dataset_validation_upload",
            )
            sheet_name = st.text_input(
                "指定工作表（可留空）",
                value="",
                key="stock_dataset_validation_sheet",
                placeholder="例如：M03模型主表_clean",
            )
            if uploaded_model_file is not None:
                try:
                    raw_df, source_meta = read_stock_dataset_file(
                        io.BytesIO(uploaded_model_file.getvalue()),
                        filename=uploaded_model_file.name,
                        preferred_sheet=sheet_name.strip() or None,
                    )
                    validation_result = validate_stock_dataset_frame(raw_df, source_meta=source_meta)
                    summary = validation_result["summary"]
                    report_df = validation_result["report"]
                    issues_df = validation_result["issues"]
                    status_counts = summary.get("status_counts", {})

                    st.caption(
                        f"讀取來源：{source_meta.get('file_name', '—')}"
                        f"{' / ' + source_meta.get('sheet_name') if source_meta.get('sheet_name') else ''}"
                    )
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("總筆數", int(summary.get("total", 0)))
                    with m2:
                        st.metric("PASS", int(status_counts.get("PASS", 0)))
                    with m3:
                        st.metric("需修正", int(status_counts.get("FIX_REQUIRED", 0)))
                    with m4:
                        st.metric("排除/映射", int(status_counts.get("EXCLUDE_OR_MAPPING", 0)))

                    if not issues_df.empty:
                        st.warning(f"偵測到 {len(issues_df)} 筆異常規則命中，請先處理 FIX_REQUIRED / EXCLUDE_OR_MAPPING。")
                        st_dataframe(issues_df.head(200), hide_index=True)
                    else:
                        st.success("驗證通過，沒有資料異常。")

                    with st.expander("完整驗證清單", expanded=False):
                        st_dataframe(report_df.head(300), hide_index=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button(
                            "下載驗證清單 CSV",
                            data=report_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="stock_dataset_validation_report.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    with c2:
                        st.download_button(
                            "下載異常清單 CSV",
                            data=issues_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="stock_dataset_validation_issues.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(f"模型資料驗證失敗：{str(e)[:180]}")
        st.markdown("---")
        st.markdown("### 🎯 策略漏斗掃描器")
        st.caption("多因子評分卡（可調權重）：估值 / 成長 / 籌碼 / 營收動能")
        wc1, wc2 = st.columns(2)
        with wc1:
            st.session_state.w_valuation = st.slider("估值", 0, 100, int(st.session_state.get('w_valuation', 35)), 5, key="slider_w_valuation")
            st.session_state.w_chip = st.slider("籌碼", 0, 100, int(st.session_state.get('w_chip', 20)), 5, key="slider_w_chip")
        with wc2:
            st.session_state.w_growth = st.slider("成長", 0, 100, int(st.session_state.get('w_growth', 30)), 5, key="slider_w_growth")
            st.session_state.w_revenue = st.slider("營收動能", 0, 100, int(st.session_state.get('w_revenue', 15)), 5, key="slider_w_revenue")

        screener_weights, used_weight_fallback = normalize_screener_weights(
            st.session_state.w_valuation,
            st.session_state.w_growth,
            st.session_state.w_chip,
            st.session_state.w_revenue,
        )
        if used_weight_fallback:
            st.warning("⚠️ 權重總和不可為 0，系統已暫時使用平均權重。")
        wv = screener_weights["valuation"]
        wg = screener_weights["growth"]
        wc = screener_weights["chip"]
        wr = screener_weights["revenue"]
        st.caption(f"權重占比：估值 {wv:.0%}｜成長 {wg:.0%}｜籌碼 {wc:.0%}｜營收動能 {wr:.0%}")

        if st.button("🔍 掃描同族群潛力股", use_container_width=True): st.session_state.run_screener = True
        
        if st.session_state.get('run_screener'):
            target_cat = None; target_stocks = []
            for cat, stocks in categories.items():
                for code, name in stocks:
                    if code == st.session_state.selected_stock: target_cat = cat; target_stocks = stocks; break
            if target_cat and target_stocks:
                with st.spinner(f"掃描 {target_cat} 財報中..."):
                    results = []
                    pbar = st.progress(0)
                    for i, (c, n) in enumerate(target_stocks):
                        hist_scan, inf = get_stock_data(c, st.session_state.fugle_key, st.session_state.finmind_key)
                        if inf:
                            # 月營收資料需每次先宣告，避免上一輪殘值或 NameError；營收動能以官方/月營收為優先。
                            df_rv = get_monthly_revenue(c, st.session_state.finmind_key)
                            score_pack = calculate_strategy_score(inf, df_rv, screener_weights)
                            r1m = backtest_return_from_hist(hist_scan, 30)
                            r3m = backtest_return_from_hist(hist_scan, 90)
                            r6m = backtest_return_from_hist(hist_scan, 180)
                            results.append({
                                'code': c,
                                'name': n,
                                'roe': score_pack.get('roe'),
                                'roe_str': to_pct(score_pack.get('roe')),
                                'peg_str': score_pack.get('peg_display', 'N/A'),
                                'score_total': score_pack.get('total_score', 50.0),
                                'score_val': score_pack.get('valuation_score', 50.0),
                                'score_growth': score_pack.get('growth_score', 50.0),
                                'score_chip': score_pack.get('chip_score', 50.0),
                                'score_revenue': score_pack.get('revenue_score', 50.0),
                                'yoy': score_pack.get('yoy_pct'),
                                'mom': score_pack.get('mom_pct'),
                                'warnings': score_pack.get('warnings', []),
                                'ret_1m': r1m,
                                'ret_3m': r3m,
                                'ret_6m': r6m,
                            })
 
                        time.sleep(0.5); pbar.progress((i+1)/len(target_stocks))
                    pbar.empty(); results.sort(key=lambda x: x['score_total'], reverse=True)             
                    st.markdown("<div style='background:#1e1e1e; padding:10px; border-radius:5px; border-left:4px solid #00bfff;'><b>🌟 掃描結果</b></div>", unsafe_allow_html=True)
                    
                    def avg_ret(key):
                        vals = [x.get(key) for x in results if x.get(key) is not None]
                        return (sum(vals) / len(vals)) if vals else None

                    a1, a3, a6 = avg_ret('ret_1m'), avg_ret('ret_3m'), avg_ret('ret_6m')
                    bt_parts = []
                    if a1 is not None: bt_parts.append(f"1M 平均: {a1:+.2f}%")
                    if a3 is not None: bt_parts.append(f"3M 平均: {a3:+.2f}%")
                    if a6 is not None: bt_parts.append(f"6M 平均: {a6:+.2f}%")
                    if bt_parts:
                        st.caption("🧪 最小回測/模擬（歷史報酬回看）｜" + " ｜ ".join(bt_parts))

                    for res in results:
                        icon = score_icon(res['score_total'])
                        r1_txt = f"{res['ret_1m']:+.1f}%" if res.get('ret_1m') is not None else "N/A"
                        r3_txt = f"{res['ret_3m']:+.1f}%" if res.get('ret_3m') is not None else "N/A"
                        r6_txt = f"{res['ret_6m']:+.1f}%" if res.get('ret_6m') is not None else "N/A"
                        st.button(
                            f"{icon} {res['name']} ({res['code']})\n"
                            f"總分: {res['score_total']:.1f} | PEG: {res['peg_str']} | ROE: {res['roe_str']}\n"
                            f"估值 {res['score_val']:.0f} / 成長 {res['score_growth']:.0f} / 籌碼 {res['score_chip']:.0f} / 營收 {res['score_revenue']:.0f}\n"
                            f"回測: 1M {r1_txt} | 3M {r3_txt} | 6M {r6_txt}",
                            key=f"s_{res['code']}",
                            on_click=reset_all_states_on_stock_change,
                            args=(res['code'],),
                            use_container_width=True
                        )

        st.markdown("---")
        st.markdown("### 🐳 籌碼集中度追蹤")
        if st.button("🔍 掃描籌碼增持名單", use_container_width=True):
            st.session_state.show_whale = True
            st.session_state.topic_results = None
            st.session_state.show_pk = False
            st.session_state.ai_industry_result = None
            st.session_state.run_screener = False
            st.rerun()

        st.markdown("---")
        st.markdown("### 🔐 一鍵匯入金鑰")
        uploaded_key_file = st.file_uploader("📂 上傳 key.txt 自動填入", type=["txt"], help="請上傳包含 GEMINI_KEY, FUGLE_KEY, FINMIND_KEY 的純文字檔")
        if uploaded_key_file is not None:
            content = uploaded_key_file.getvalue().decode("utf-8")
            clean_content = re.sub(r'\s+', '', content)
            keys_loaded = 0
            m_gemini = re.search(r'GEMINI_KEY=(.*?)(?:FUGLE_KEY|FINMIND_KEY|$)', clean_content, re.IGNORECASE)
            m_fugle = re.search(r'FUGLE_KEY=(.*?)(?:GEMINI_KEY|FINMIND_KEY|$)', clean_content, re.IGNORECASE)
            m_finmind = re.search(r'FINMIND_KEY=(.*?)(?:GEMINI_KEY|FUGLE_KEY|$)', clean_content, re.IGNORECASE)
        
            if m_gemini and m_gemini.group(1):
                st.session_state.api_key = m_gemini.group(1)
                keys_loaded += 1
            if m_fugle and m_fugle.group(1):
                st.session_state.fugle_key = m_fugle.group(1)
                keys_loaded += 1
            if m_finmind and m_finmind.group(1):
                st.session_state.finmind_key = m_finmind.group(1)
                keys_loaded += 1
            
            if keys_loaded > 0:
                st.success(f"✅ 成功載入 {keys_loaded} 組金鑰！密碼框已自動填滿，請點擊下方「🔄 重新整理快取」套用。")
            else:
                st.error("❌ 找不到有效的金鑰，請確認檔案格式是否正確。")

        if st.button("🔄 重新整理快取", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown("---")
        st.markdown("### 🧠 AI 聯網議題選股")
        topic_q = st.text_input("輸入議題 (如: 代理人AI、矽光子)")
    
        ai_model_option = st.radio("使用AI版本", [
            "Gemini 3.1 Pro Preview (付費版)"
        ], key="ai_model_radio")
        st.caption("🔒 已鎖定付費版高階模型；不自動降級到 2.5 Pro / 2.5 Flash，避免財報資料不準。")
    
        st.session_state.api_key = st.text_input("🔑 Gemini API Key", type="password", value=st.session_state.api_key)
    
        if st.button("AI 實時推演分析", type="primary", use_container_width=True):
            if topic_q and st.session_state.api_key:
                st.session_state.selected_model = get_selected_model_id()
                st.session_state.topic_results = "LOADING"
                st.session_state.ai_industry_result = None
                st.session_state.run_screener = False
                st.rerun()
            
        st.markdown("---")
        st.markdown("### ⚔️ 產業同業 PK")
        if st.button("🤖 尋找同業競爭對手並 PK", use_container_width=True):
            if not st.session_state.api_key: st.warning("請先輸入您的 API Key。")
            else: st.session_state.show_pk = True; st.rerun()

        st.markdown("---")
        st.markdown("### 📈 進階資料源設定")
        st.session_state.fugle_key = st.text_input("🔑 Fugle (富果) API Key (選填)", type="password", value=st.session_state.fugle_key)
        st.session_state.finmind_key = st.text_input("🔑 FinMind API Key (選填)", type="password", value=st.session_state.finmind_key)

        f_ok, m_ok = validate_api_keys(st.session_state.fugle_key, st.session_state.finmind_key)
    
        if st.session_state.fugle_key:
            if f_ok: st.success("✅ 富果 API 連線成功")
            else: st.error("❌ 富果金鑰無效或已過期")
        
        if st.session_state.finmind_key:
            if m_ok: st.success("✅ FinMind API 連線成功")
            else: st.error("❌ FinMind 金鑰無效")
        st.markdown("---")
        st.markdown("### 🩺 Data Health Panel")
        health = st.session_state.get("data_health_stats", {})
        def fmt_health_status(raw_status):
            rs = str(raw_status).upper() if raw_status is not None else "N/A"
            if rs == "N/A":
                return "— 尚未呼叫"
            if rs in ["200", "OK"]:
                return f"✅ 成功 ({raw_status})"
            if rs == "ERR":
                return "❌ 連線錯誤 (ERR)"
            return f"⚠️ 失敗 ({raw_status})"

        if health:
            for src in ["Yahoo", "Fugle", "FinMind", "Gemini"]:
                s = health.get(src, {"last_success": None, "error_count": 0, "last_status": "N/A"})
                last_ok = s.get("last_success") or "尚無"
                err_cnt = s.get("error_count", 0)
                last_st = s.get("last_status", "N/A")
                st.markdown(
                    f"- **{src}**｜最近狀態: `{fmt_health_status(last_st)}`｜錯誤次數: `{err_cnt}`\n"
                    f"  - 最後成功時間: `{last_ok}`"
                )
        else:
            st.info("尚無來源健康資料。")

        error_events = st.session_state.get("error_events", [])
        if error_events:
            with st.expander("🧯 最近非致命錯誤紀錄", expanded=False):
                for ev in reversed(error_events[-10:]):
                    st.markdown(
                        f"- `{ev.get('time', '')}` **{ev.get('source', '')}** / "
                        f"{ev.get('context', '')}：`{ev.get('error', '')}`"
                    )
        st.markdown("---")

    return {
        "topic_q": locals().get("topic_q", ""),
        "f_ok": locals().get("f_ok", None),
        "m_ok": locals().get("m_ok", None),
    }
