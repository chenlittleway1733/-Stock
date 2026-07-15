產業估值模型說明文件
版本：taxonomy 17-C-22 / Dynamic Cap 17-C-23
模型建立日期：2026-06-23
狀態：已完成 M10 margin benchmark 導入，並新增 hybrid 欄位級權重。base/soft 可反映副成長曲線，但 hard ceiling 可獨立鎖住；聯發科 2454 已加入 Cloud AI ASIC 重評價觀察，且不因股價先漲而上調 hard ceiling。

一、模型目的

本系統的產業估值模型用來把台股個股對應到較合適的估值框架，避免所有公司共用同一套 P/E 或 PEG 判斷。

核心原則：
1. 股票正式估值分類以 stock_mapping.py 為準。
2. stocklist.txt 只作 UI 分類、快速選股與人工閱讀，不承載正式估值規則。
3. 產業倍率以 industry_taxonomy.py 與 dynamic_cap_model.py 為主。
4. AI 財報校對可輔助補資料與建議分類，但不會自動覆蓋 stock_mapping.py。
5. 單次快照不直接更新模型；若要調整 primary_taxon、hybrid 權重或 base/soft/hard，需人工確認。
6. M10 margin benchmark 只作毛利率 / 營益率同業基準與品質係數守門，不直接改寫產業 base/soft/hard 倍率。

二、目前資料盤點

截至 2026-06-23：
- stocklist.txt 股票數：276
- stock_mapping.py 股票數：276
- industry_taxonomy.py 產業分類數：127
- hybrid_taxons 條目數：24
- 目前檢查結果：stocklist 與 stock_mapping 無缺碼、無重複碼；primary_taxon 與 hybrid taxon 皆可在 taxonomy 中找到。

三、主要檔案關聯

| 檔案 | 功能 |
| --- | --- |
| stocklist.txt | UI 快速選股分類、自選股管理器使用；不作正式估值分類來源 |
| stock_mapping.py | 股票代號對應 primary_taxon、themes、hybrid_taxons；正式估值分類入口 |
| industry_taxonomy.py | 各產業分類的估值框架、base/floor/soft/hard、P/B 區間、風險旗標；內建版本表與建立日期 |
| model_data/*.json | M10 / M12 外部模型資料匯入層；目前包含 90 類 margin taxonomy、275 檔個股 margin metadata、157 檔估值 universe 與 margin 規則 |
| model_data_loader.py | 讀取 M10 margin benchmark，轉換百分比口徑，輸出可掛載到 industry_profile 的 metadata |
| industry_model.py | 整合個股分類、產業參數與 M10 margin benchmark，產生 industry_profile，並輸出模型建立日期與維護提醒 |
| dynamic_cap_model.py | Dynamic Cap 2.0 核心計算：成長、品質、題材、規模、資料可信度與風險折扣；17-C-22 起會讀取 M10 margin benchmark 作為品質係數守門，17-C-23 起支援 hybrid 欄位級權重與個股市場 hard overlay 關閉 |
| utils.py | EPS 拆欄、Forward EPS 分層估值、公式估值/可操作估值分離、快照稽核、AI JSON 驗證 |
| ui_main.py | Streamlit 主流程；負責資料取得、估值計算串接與各面板呼叫 |
| ui_panels/quote.py / market_trend.py | 即時報價與交易資訊、國際連動與隔日趨勢推估面板 |
| ui_context/financial_context.py | 系統/FinMind/Yahoo 財務基礎資料與 AI 財報快照解析 context |
| ui_context/valuation_context.py / quality_context.py | Dynamic Cap 採用值、分歧警告前置資料與資料品質報告 rows 組裝 |
| ui_context/multiple_context.py / implied_context.py | 倍率分層、公式價、手動年度情境、FY1/FY2/FY3 估值矩陣與市場/法人隱含 Forward P/E 組裝 |
| ui_context/prompt_context.py | 打包提示詞用表格/警告/來源摘要、法人目標價 fallback、Dynamic Cap/EPS/PEG/snapshot audit prompt core、M10 margin benchmark 摘要、ETF/防禦力/籌碼/panel sync prompt summary、模型落差/買進風險/模型庫回饋 prompt 規則、技術面 prompt suffix |
| ui_panels/financials.py | 財報 AI 校對控制列、EPS 拆欄、資料品質、估值明細、Dynamic Cap 與 M10 margin benchmark 顯示、燈號、財務卡片、防禦力與法人目標價面板 |
| ui_panels/etf.py | ETF 快速持有概況、AI ETF 補查與提示詞同步用 ETF 快照 |
| ui_panels/chips.py | 外資/投信籌碼雷達、內部人/機構持股與控盤主力推估 |
| ui_panels/news.py / peer_compare.py | 近期財報與法說新聞、AI 同業估值與利潤率橫向比較 |
| ui_panels/river_charts.py / technical.py | P/E / P/B 估值河流圖、K 線 / 均線 / KD / 法人買賣超技術圖表 |
| ui_panels/overview.py / stock_header.py / prompt_pack.py | 總覽/空白提示、股票標題/產業分類、打包提示詞面板 |
| services.py | 外部資料與 Gemini 3.1 Pro Preview AI 財報補齊 |

四、資料流

1. 使用者選擇股票。
2. ui_main.py 呼叫 get_industry_valuation_profile。
3. industry_model.py 先查 stock_mapping.py：
   - 找到 mapping：使用正式 primary_taxon、themes、hybrid_taxons。
   - 找不到 mapping：用 stocklist/關鍵字 fallback；若 AI 有建議分類，先標示待人工確認並套折扣。
4. industry_model.py 從 industry_taxonomy.py 取得產業估值參數。
5. industry_model.py 呼叫 model_data_loader.py，把該股 M10 margin benchmark 掛載到 industry_profile。
6. 若該股有 hybrid_taxons，計算混合後 base/floor/soft/hard 顯示值；若設定 hard_weight，hard ceiling 可使用不同權重。
7. dynamic_cap_model.py 用財務資料、產業參數與 M10 margin benchmark 計算 Dynamic Cap 2.0。
8. utils.py 建立估值分層、可操作區間、分歧警告與快照稽核表。
9. ui_main.py 顯示模型建立日期、分類、倍率、Forward EPS 三情境、M10 margin 狀態與打包提示詞。

五、分類規則

stock_mapping.py 欄位：
- name：股票名稱。
- primary_taxon：主要估值分類，決定主要模型。
- themes：題材標籤，只作顯示與輔助判讀，不取代主分類。
- hybrid_taxons：混合型企業的副分類與權重。
- re_rating_status / re_rating_status_label：個股重評價觀察狀態。
- pricing_horizon_policy：若市場定價年期已進入 FY2 soft 等遠期情境，對買進燈號的限制。
- hard_ceiling_policy / disable_market_hard_overlay：個股是否鎖住 hard ceiling，避免因市場先漲而反向調高模型。

分類優先順序：
1. stock_mapping.py 正式分類。
2. AI 建議分類，但只限未正式 mapping 或 fallback 明顯不足時，且標示待人工確認。
3. stocklist/關鍵字 fallback。
4. GENERAL 防禦型兜底。

注意：
- themes 不可直接當作估值分類。
- AI 建議分類不可直接寫回 stock_mapping.py。
- GENERAL 只作防守，不應長期停留；新增股票後需補正式 mapping。

六、產業倍率欄位

industry_taxonomy.py 與 dynamic_cap_model.py 主要使用以下欄位：
- base_pe：產業基礎倍率。
- floor_pe：產業低檔/保守下緣。
- soft_ceiling_pe：樂觀倍率上緣。
- hard_ceiling_pe：極限倍率上限。
- base_pb / pb_range：P/B 週期模型用欄位。
- primary_valuation：主要估值法，例如 forward_pe、pb_cycle、event 等。
- pe_applicable：是否適合使用 P/E。
- pe_trap_warning：是否有 P/E 陷阱。
- event_model_if_eps_unstable：EPS 不穩時是否切換事件模型。
- operable_discount_factor：可操作估值折扣。
- risk_flags：主要風險提示。

base / soft / hard 定義：
- base：基礎倍率，代表目前產業正常情境的估值中樞。
- soft：樂觀倍率，代表可觀察的高估值區，但不是買進目標。
- hard：極限倍率，代表風控上限；不可因股價上漲或單次法人目標價偏高就直接上修。

七、混合型企業 hybrid_taxons

混合型企業用來處理「本業仍是 A，但已有 B 成長曲線」的公司。

範例：
- 鴻海：EMS 平台為主，AI Server 與 EV 為副成長線。
- 廣達：PC/NB ODM 為主，AI Server ODM 權重較高。
- 欣興：ABF 載板為主，AI/HPC 高階載板題材影響估值。
- 鴻勁：測試設備為主，AI 晶片測試/先進封裝為副分類。

權重規則：
1. primary_taxon 永遠是主分類。
2. hybrid_taxons 的單一權重會被限制在 0%～50%。
3. hybrid_taxons 總權重最多 50%。
4. 主分類權重 = 1 - hybrid 總權重。
5. 混合後倍率會以主分類與副分類加權計算 base/floor/soft/hard。
6. 17-C-23 起允許 base/floor/soft/hard 使用欄位級權重，例如 hard_weight=0 表示副分類可影響 base/soft，但不推高 hard ceiling。
7. hybrid 權重只反映已能影響估值的成長曲線，不等於題材熱度。

聯發科 2454 範例：
- primary_taxon 保留 PLATFORM_IC_LEADER。
- hybrid_taxons 加入 IC_DESIGN_ASIC_HIGH_VISIBILITY 35%，但 hard_weight=0。
- re_rating_status 為 CLOUD_AI_ASIC_RE_RATING。
- 混合後顯示為 base 35.25x / floor 21.50x / soft 52.00x / hard 60.00x。
- 若 pricing_horizon=FY2_SOFT_PRICED，買進燈號不得直接升級，只允許既有部位續抱或回檔小量。
- disable_market_hard_overlay=True，市場 hard overlay 不會因現價隱含 P/E 高於 hard 而調高 hard ceiling。

八、Dynamic Cap 2.0 計算概念

Dynamic Cap 2.0 不是單純取產業 hard ceiling，而是用多個係數修正產業基準倍率。

主要輸入：
- industry_profile：產業分類與倍率。
- Forward EPS / TTM EPS / FY1 EPS。
- gross_margin：毛利率。
- operating_margin：營益率。
- m10_margin_benchmark：M10 分類毛利率 / 營益率 base、low、high 與使用狀態。
- roe：ROE。
- debt_to_equity：負債權益比。
- revenue_yoy：營收年增率。
- free_cash_flow：自由現金流。
- pb_ratio：P/B。
- divergence_warnings：系統值與 AI 值分歧警告。
- dq_warnings：資料品質校驗警告。

主要修正項：
- growth_factor：成長係數。
- quality_factor：品質係數，已納入毛利率、營益率、M10 同業 benchmark 與 ROE，不再只看毛利率。
- theme_factor：題材係數。
- scale_factor：規模/龍頭係數。
- data_confidence_factor：資料可信度折扣。
- valuation_risk_factor：估值風險折扣。
- liquidity_factor：流動性折扣。
- classification_factor：分類可信度折扣。

限制：
- 若 EPS 尚未穩定轉正，P/E 模型會停用或降級成事件/轉機模型。
- 若現價隱含 Forward P/E 超過 hard ceiling，只列為市場重估/題材動能區，不自動上修買進倍率。
- P/B 週期股、金融、記憶體、面板、航運等類型不可只看 P/E。

八之一、M10 margin benchmark 規則

M10 margin benchmark 是外部整理的分類毛利率 / 營益率基準，用來改善品質係數是否過度加分或錯誤扣分。

資料來源：
- model_data/industry_taxonomy_with_margin.json：90 類產業 margin benchmark。
- model_data/stock_model_data_with_margin.json：275 檔股票對應 margin metadata。
- model_data/valuation_universe_with_margin.json：157 檔 A/B 估值 universe。
- model_data/margin_benchmark_rules.json：margin_quality 與 margin_rule 定義。

主要欄位：
- margin_quality：A / B / C / N/A。
- margin_rule：standard_margin_benchmark、high_operating_margin_cap、high_gross_margin_profile、low_operating_margin_cap、cycle_margin_sensitive、event_or_cycle_tracking_only、margin_not_applicable。
- m10_margin_status：usable、tracking_only、stock_not_valuation_ready、not_applicable、missing_stock_model_data。
- base_gross_margin_pct / gross_margin_low_pct / gross_margin_high_pct。
- base_operating_margin_pct / operating_margin_low_pct / operating_margin_high_pct。
- margin_model_applicable：是否適合套用製造業毛利率 / 營益率模型。
- margin_can_affect_valuation：是否允許正向影響品質係數。

Dynamic Cap 使用規則：
1. usable：可納入品質係數，但仍受 max_quality_factor 與 hard ceiling 限制。
2. tracking_only 或 margin_quality=C：正向 margin 加分歸零，只保留負向風險折扣。
3. stock_not_valuation_ready：只作背景參考，不當作估值正向加分來源。
4. not_applicable 或 margin_not_applicable：不套毛利率 / 營益率模型，品質係數只採 ROE 與財務風險，並跳過營益率防呆。
5. missing_stock_model_data：沿用既有產業品質係數設定，畫面與提示詞標示未建立。

限制：
- M10 margin benchmark 不直接改 base/soft/hard。
- M10 margin benchmark 不取代 stock_mapping.py 的 primary_taxon。
- 金融、事件型、循環敏感或 margin 不適用分類，不可因毛利率/營益率數字漂亮而拿到正向品質加分。
- UI 與打包提示詞會顯示 M10 狀態、品質、規則與 benchmark，方便外部 AI 判斷是否應保守解讀。

九、Forward EPS 與 PEG 面板規則

EPS 口徑必須拆開：
- 最新單季 EPS：只看短期獲利動能。
- TTM EPS：近四季 EPS 合計，用於歷史 P/E。
- 完整年度 EPS：最近完整會計年度 EPS。
- Forward EPS：預估年度 EPS，不可與單季 EPS 混用。
- FY1 EPS：一年預估 EPS。
- FY2 EPS：第二年預估 EPS。
- FY3 EPS：第三年預估 EPS或長期高風險情境 EPS。

Forward PEG 面板規則：
1. FY1 / FY2 / FY3 都要分別計算 base / soft / hard。
2. base 顯示為基礎估值。
3. soft 顯示為樂觀估值。
4. hard 顯示為極限估值。
5. 樂觀年度情境已取消，避免與 soft/hard 重複。
6. 手動年度情境若使用者未調整，倍率預設使用 FY1 base。
7. AI估值不再獨立重複顯示為另一個與 FY1 相同的估值；AI/法人 FY1 已併入年度分層表。

十、公式估值與可操作估值分離

utils.py 的 build_valuation_separation_report 會把公式估值與可操作區間分開。

原則：
- 系統公式合理估值：純公式輸出。
- 系統公式極限價：風控與壓力測試用。
- 法人目標價：依分析師人數與高低區間判斷可信度。
- 可操作估值區間：經資料分歧、產業折扣、法人可信度與風險因子折減後產生。

目前規則：
- AI公式合理估值 / AI公式極限價不再作為獨立列進入可操作估值。
- AI/法人 FY1 已在 Forward EPS 年度三情境中呈現。
- 可操作區間不是買進建議，只是風險調整後的估值參考。

十一、AI 財報校對與 Gemini 提示詞

按鈕：
「啟動 AI 全方位校對與補齊財報」

模型：
- gemini-3.1-pro-preview
- Pro Only，同模型最多重試 3 次。
- 不自動降級到 2.5 Pro / 2.5 Flash。
- 啟用 Google Search grounding。

提示詞要求：
- 查詢最新財報、營收、P/E、P/B、毛利率、營益率、ROE、D/E、FCF、流動比率、法人目標價。
- 必須回傳 FY1/FY2/FY3 EPS 與對應年度。
- 必須回傳 _sources，逐欄標示來源、發布日期、source_url、note。
- 必須回傳 industry_classification，但只作建議分類。
- 不查 ETF 持股；ETF 持股由獨立按鈕處理。
- 嚴格回傳 JSON，不輸出 markdown。
- 打包提示詞會同步帶入 M10 margin benchmark；外部 AI 應解讀 margin 狀態，但不可直接建議修改 base/soft/hard。

AI 回傳後處理：
- validate_ai_financial_json 會檢查數值範圍。
- 百分比會統一轉小數。
- EPS 極端值會被檢查。
- 毛利率/營益率若邏輯不合理會設為 NULL。
- 分歧警告會同步進資料品質與 Dynamic Cap 折扣。

十二、模型稽核與維護規則

模型建立資訊目前由 industry_model.py 輸出：
- model_build_version：taxonomy 17-C-22 / Dynamic Cap 17-C-23
- model_built_at：2026-06-20
- model_build_note：17-C-22 導入 M10 margin benchmark metadata；17-C-23 支援 hybrid 欄位級權重與個股市場 hard overlay 關閉。
- model_maintenance_note：建議每月做 mapping/hybrid 小檢查，每季檢查產業 base/soft/hard。

建議維護節奏：
1. 每次新增 stocklist 股票後，檢查是否也要補 stock_mapping.py。
2. 每月檢查 primary_taxon 與 hybrid_taxons。
3. 每季檢查 industry_taxonomy.py 的 base/soft/hard 是否符合市場現況。
4. 對 P/B 週期、事件股、EPS 不穩股，不因短線股價或單一法人目標價直接上修模型。
5. 若 AI 建議調整模型，必須說明是 primary_taxon、hybrid 權重，還是 base/soft/hard 的問題。

十三、目前仍需完善之處

1. stocklist 管理器只會修改 stocklist.txt，不會自動同步 stock_mapping.py。
2. 產業模型已建立最小自動化測試，並開始覆蓋 M10 loader、Dynamic Cap、prompt context 與提示詞面板 UI contract；但尚未擴充到完整瀏覽器 UI、外部 API 與端到端情境回歸測試。
3. ui_main.py 已完成第十三階段資料組裝模組化，並補上第一批 UI 回歸測試：已抽出總覽/空白提示、股票標題/產業分類、即時報價、國際連動、打包提示詞面板、財報 AI 校對控制列、EPS/資料品質、估值明細、最終燈號、財務卡片、防禦力、法人目標價、ETF、籌碼、新聞、產業比較、估值河流圖與技術圖表面板，並新增 financial / valuation / quality / multiple / implied / prompt context，統一整理系統/FinMind/Yahoo 基礎財務資料、AI 財報快照、Dynamic Cap 採用值、分歧警告前置資料、資料品質報告 rows、倍率分層、年度估值矩陣、市場/法人隱含 Forward P/E，以及提示詞用表格/警告/來源摘要、法人目標價 fallback、Dynamic Cap/EPS/PEG/snapshot audit prompt core、ETF/防禦力/籌碼/panel sync prompt summary、模型落差/買進風險/模型庫回饋 prompt 規則與技術面 prompt suffix；後續重點改為擴充更多 UI 面板 contract與完整瀏覽器回歸測試。
4. industry_taxonomy.py 與 dynamic_cap_model.py 已補上可讀取版本表；目前 taxonomy 為 17-C-22、Dynamic Cap 為 17-C-23。長期仍可把多段 update 覆寫整理為資料檔或單一建表流程。
5. 歷史紀錄資料庫尚未啟用，因此快照稽核不能判斷連續幾次偏離。
6. AI 建議分類仍需人工確認，不可自動覆蓋正式模型。

十四、自動化測試

測試檔：
- tests/test_core_models.py

目前覆蓋：
1. stocklist.txt、stock_mapping.py、industry_taxonomy.py 一致性。
2. primary_taxon / hybrid_taxons 是否存在於 taxonomy。
3. hybrid 權重是否落在 0%～50%，總權重是否不超過 50%。
4. taxonomy 中 P/E 類倍率是否符合 floor <= base <= soft <= hard。
5. industry_taxonomy.py / dynamic_cap_model.py 版本表是否存在、完整階段清單與排序是否正確；taxonomy 最新版本為 17-C-22，Dynamic Cap 最新版本為 17-C-23。
6. 17-C-17 高風險倍率收斂分類是否與 Dynamic Cap 實算口徑一致，且全模型 hard ceiling 是否不再超過 82x。
7. Dynamic Cap 2.0 是否輸出合理且受 floor/hard 約束的 forward_pe pack，並回傳最新 engine version。
8. Forward EPS 分層是否正確計算 FY1/FY2/FY3 的 base/soft/hard 估值。
9. AI 財報 JSON 驗證是否能轉換百分比、排序目標價、阻擋無效 taxonomy。
10. ETF prompt summary 是否同步快速查詢與 AI ETF 補查資料。
11. 籌碼 prompt summary 是否同步外資/投信、股權結構與控盤資訊。
12. 模型庫回饋 prompt 是否同步 primary_taxon、hybrid 權重與 soft/hard ceiling。
13. 技術面 prompt suffix 是否依模式輸出日線摘要與線圖輔助規則。
14. 提示詞面板 UI 回歸：買進/研究版本切換、技術面 suffix 附加、複製 HTML 與文字框內容是否同步。
15. 股票標題面板 UI 回歸：股票名稱/代號、產業分類摘要、watchlist 按鈕、AI 財報快照與公司簡介是否正常串接。
16. ETF 面板 UI 回歸：快速 ETF 持股表、AI ETF 補查表、按鈕狀態與 AI 摘要是否正常呈現。
17. 財報面板 UI 回歸：AI 全方位校對控制列、既有 AI 財報快照、JSON 校驗警示與原始回報切換按鈕是否正常呈現。
18. M10 margin benchmark 回歸：資料匯入 count、個股 profile 掛載、Dynamic Cap 品質係數守門、UI 顯示與打包提示詞同步。
19. 聯發科 2454 Cloud AI ASIC 重評價回歸：primary_taxon 保留 PLATFORM_IC_LEADER、hybrid 權重 35% 但 hard_weight=0、Dynamic Cap hard ceiling 不被市場 overlay 上調、FY2_SOFT_PRICED 不升級買進燈號。

執行方式：
python -m unittest discover -s tests -v

十五、修改產業估值模型時的標準流程

新增股票：
1. 先加入 stocklist.txt。
2. 再補 stock_mapping.py 的 primary_taxon 與 themes。
3. 若現有分類不足，新增 industry_taxonomy.py 分類。
4. 同步 dynamic_cap_model.py 的校準參數。
5. 跑 stocklist / mapping / taxonomy 一致性檢查。
6. 更新本說明文件。

調整倍率：
1. 先查外部資料、法人目標價、投信/法人持股或產業報價資料。
2. 判斷是市場過熱、EPS 上修、產業結構改變，還是分類錯誤。
3. 只在有結構性理由時調整 base/soft/hard。
4. hard ceiling 只作極限上限，不因股價突破就機械調高。
5. 調整後用代表股驗證，例如聯發科、欣興、鴻勁等。

調整 hybrid 權重：
1. 確認副成長曲線已實際影響營收、EPS、毛利率、營益率或法人目標價。
2. 權重不可只根據市場題材熱度。
3. 單一與總權重需遵守 50% 上限。
4. 若副成長線只應影響 base/soft，不應影響極限天花板，需設定 hard_weight=0 或較低 hard 權重。
5. 調整後檢查混合後 base/floor/soft/hard 是否仍合理，並確認 Dynamic Cap 與提示詞同步。

調整 M10 margin benchmark：
1. 先確認分類是否適用製造業毛利率 / 營益率模型。
2. 金融、事件型、循環敏感或 margin 不適用分類，應標示 not_applicable 或 tracking_only。
3. usable 類別才允許正向品質係數加分；tracking_only 僅保留負向折扣。
4. 調整後需檢查 Dynamic Cap 拆解表、M10 UI 卡片與打包提示詞是否同步。
5. 不得只因單家公司毛利率高於同業就直接調整 base/soft/hard，應先檢查 ROE、營益率、FCF、EPS 年期與法人目標價可信度。

十五、重要提醒

本系統是投資研究與估值輔助工具，不是自動下單或保證報酬系統。
產業估值模型的輸出應搭配：
- 最新財報與月營收。
- 法人目標價可信度。
- 籌碼與流動性。
- 產業週期位置。
- P/B 或事件模型適用性。
- 資料來源與發布日期。

若資料不足、AI/系統分歧過大、EPS 尚未穩定轉正，應優先降低模型可信度，而不是提高估值倍率。
