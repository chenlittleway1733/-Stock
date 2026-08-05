# 產業估值模型 base / soft / hard 倍率寬鬆度查核

- 查核日期：2026-06-09
- 查核範圍：`industry_taxonomy.py`、`dynamic_cap_model.py`
- 查核時模型版本：17-C-16
- 後續執行版本：17-C-17
- 本次結論：已於 17-C-17 修改模型倍率，收斂高 hard ceiling 分類並同步 taxonomy / Dynamic Cap 實算口徑。

## 17-C-17 執行後摘要

| 項目 | 調整前 | 調整後 |
|---|---:|---:|
| taxonomy hard >= 70 分類數 | 19 | 13 |
| 全模型最高 hard ceiling | 90x | 82x |
| taxonomy / Dynamic Cap P/E 倍率不一致分類 | 22 | 7 |

剩餘 7 個不一致分類為 P/B 或 event 主模型：`MEMORY_CYCLE`、`DISPLAY_LED_CYCLE`、`PASSIVE_COMPONENT_CYCLE`、`FINANCIAL`、`SHIPPING_CYCLE`、`THEME_EVENT`、`ROBOTICS_THEME_EVENT`。taxonomy 對這些分類不提供 P/E cap，Dynamic Cap 僅保留 fallback / 事件模型輔助，因此不視為顯示與實算衝突。

## 外部基準摘要

1. 台股整體估值偏熱，不宜全面下修。
   - World PE Ratio 估計 2026-06-08 台灣股市 P/E 為 24.20，高於 5 年平均 16.20，評等為 Expensive。
   - Simply Wall St 2026-06-08 台灣市場 PE 為 31.3x，高於 3 年平均 22.5x，並估計未來盈餘年增約 26%。
2. 半導體估值已明顯高於過往平均，但仍有 AI 成長支撐。
   - Simply Wall St 2026-06-06 台灣半導體產業 PE 為 36.8x，高於 3 年平均 24.9x，預估盈餘年增約 25%。
   - 同頁代表股：台積電 PE 32.1x、南亞科 32.2x、瑞昱 23.1x、長華* 53.2x、華邦電 48.1x。
3. 官方產業基準顯示，多數傳統或電子零組件產業仍低於模型高階 hard。
   - TWSE Fact Book 2025 年底 2024：總市場 PER 21.29、半導體 26.20、通訊網路 32.12、電子零組件 24.39、資訊服務 22.77、其他電子 18.03。
   - 生技醫療 47.75、光電 79.24 的 PER 偏高，但常混有獲利低基期或虧損剔除效果，不宜直接當成買進倍率。

## 本地模型掃描摘要

| 指標 | 結果 |
|---|---:|
| taxonomy 中含 base/soft/hard 的分類 | 118 |
| Dynamic Cap defaults 中含 base/soft/hard 的分類 | 124 |
| taxonomy 與 Dynamic Cap base/soft/hard 不一致分類 | 22 |
| taxonomy hard >= 80 的分類 | 9 |
| taxonomy hard >= 70 的分類 | 19 |
| 週期股但 hard >= 55 的分類 | 14 |
| hard/base >= 2.1 的寬區間分類 | 29 |
| P/B / event / cycle 類但仍有 hard >= 45 的分類 | 19 |

## 優先風險清單

### A. 高倍率 hard 80-90，需要加嚴或小幅下修

| taxon | 目前 base/soft/hard | 判斷 | 建議方向 |
|---|---:|---|---|
| IC_DESIGN_IP_ROYALTY | 45 / 75 / 90 | IP/Royalty 高毛利合理，但 90x 只適合授權收入高度可見且 EPS 上修明確。 | soft/hard 建議降到 65-70 / 80-85，或保留 90 但新增高確定性條件。 |
| OPTICAL_COMM_CPO_HIGH_VISIBILITY | 42 / 70 / 90 | CPO/矽光子題材熱，外部市場也支持高估值，但個股 EPS 落地差異大。 | hard 90 可留作極限，不應作一般樂觀；若無 FY2/FY3 EPS 可見度，應退回 60-70。 |
| IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY | 42 / 70 / 90 | BMC/資料中心 IC 能見度高但分類較窄，90x 偏寬。 | 建議 40 / 62 / 78 或加入客戶/訂單能見度條件。 |
| IC_DESIGN_ASIC_HIGH_VISIBILITY | 45 / 70 / 85 | 高能見度 ASIC 可高估值，但目前 base 已高。 | 可接受，但 hard 應只給 confirmed ASIC revenue / EPS 上修。 |
| SEMICAP_ADV_PACKAGING_CORE | 38 / 60 / 80 | 先進封裝設備受資本支出循環影響，80x 過度接近題材股。 | 建議 36 / 55 / 72。 |
| THERMAL_LIQUID_CORE | 38 / 60 / 80 | 液冷高成長，但散熱零組件仍有競爭與毛利壓力。 | 建議 36 / 55 / 70。 |
| SERVER_RAIL_HIGH_VISIBILITY | 38 / 60 / 80 | 高階滑軌龍頭可享高估值，但 80x 對硬體零組件偏寬。 | 建議 36 / 55 / 70。 |
| AI_CCL_HIGH_VISIBILITY | 36 / 60 / 80 | CCL/材料有週期性，且已標記 cyclical。 | 建議 34 / 52 / 65，或加入 P/B/庫存週期防呆。 |

### B. 週期股 hard 偏高，應優先收斂

| taxon | 目前 base/soft/hard | 問題 |
|---|---:|---|
| MEMORY_IP_AI | 35 / 60 / 75 | primary 是 forward_pe_pb_cycle，且 pe_trap 為 secondary_only；75x 對記憶體題材偏鬆。 |
| SEMIMAT_ADVANCED_CONSUMABLES | 34 / 55 / 70 | 半導體材料/耗材仍受產能利用率與庫存週期影響。 |
| AI_SERVER_PCB_HIGH_VISIBILITY | 34 / 55 / 70 | PCB/載板屬週期型，70x 只有高階材料滲透率快速提升時合理。 |
| HIGH_SPEED_CONNECTOR_CORE | 34 / 55 / 70 | 高速連接器雖受 AI 拉動，但仍是零組件週期與客戶集中風險。 |
| POWER_MANAGEMENT_IC_DESIGN | 26 / 42 / 58 | PMIC/類比 IC 循環屬性強，hard/base 2.23 偏寬。 |
| OSAT_AI_HPC_TESTING | 28 / 45 / 58 | 封測仍有景氣循環，應避免用高 P/E 掩蓋稼動率下滑。 |

### C. Dynamic Cap 與 taxonomy 倍率不一致，需先同步

這是本次最實務的風險。`_calibration()` 以 `CALIBRATION_DEFAULTS` 為底，再讓 taxonomy 覆寫 floor/soft/hard，但 base 若 Dynamic defaults 已有值通常不被 taxonomy 覆寫。因此同一分類可能出現「UI/文件看一套，Dynamic Cap base 用另一套」。

| taxon | taxonomy | dynamic defaults | 建議 |
|---|---:|---:|---|
| PROBE_TEST_INTERFACE | 32 / 45 / 55 | 34 / 50 / 60 | 同步為較保守的 32 / 45 / 55。 |
| NETWORK_SWITCH | 26 / 36 / 45 | 28 / 42 / 52 | 建議降回 taxonomy 或拆成 AI switch / 一般 switch。 |
| ROBOTICS_AUTOMATION | 24 / 36 / 45 | 28 / 42 / 52 | taxonomy 已有 EPS 未落地事件模型；Dynamic defaults 偏寬。 |
| SPACE_LEO_SATELLITE | 28 / 34 / 45 | 30 / 45 / 55 | 題材/event 屬性強，Dynamic defaults 偏寬。 |
| SOFTWARE_SECURITY_CLOUD | 30 / 42 / 50 | 32 / 50 / 60 | 台股軟體資安規模與流動性有限，60x 偏寬。 |
| THERMAL_LIQUID_COOLING | 34 / 48 / 60 | 34 / 50 / 62 | 小差異，可同步 taxonomy。 |

完整不一致分類數：22。

## 判斷為可先保留的分類

| taxon | 理由 |
|---|---|
| FOUNDRY_ADVANCED 24 / 30 / 35 | 相對台積電與半導體產業現況偏保守，可維持。 |
| PLATFORM_IC_LEADER 28 / 42 / 55 | 聯發科/瑞昱差異大，但平台龍頭可用品質係數與 P/B 高檔警示控制。 |
| FINANCIAL_BANK_HOLDCO_QUALITY / FINANCIAL_LIFE_INSURANCE_HOLDCO | 金融分類倍率相對保守，符合 P/B/股利導向。 |
| DISPLAY_DRIVER_IC_CYCLE / MEMORY_MANUFACTURING_CYCLE | 已改週期/PB 防護，倍率不算寬鬆。 |
| PC_NB_ODM / EMS_PLATFORM_CONTRACT_MANUFACTURING | 代工與品牌硬體倍率維持中低水位，合理。 |

## 建議處理順序

1. 先同步 22 個 taxonomy / Dynamic Cap 不一致分類，避免顯示與實算不同。
2. 第一批調整高風險 8 類：`AI_CCL_HIGH_VISIBILITY`、`THERMAL_LIQUID_CORE`、`SERVER_RAIL_HIGH_VISIBILITY`、`SEMICAP_ADV_PACKAGING_CORE`、`MEMORY_IP_AI`、`AI_SERVER_PCB_HIGH_VISIBILITY`、`HIGH_SPEED_CONNECTOR_CORE`、`IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY`。
3. 第二批處理 19 個 P/B / event / cycle 但仍有高 P/E hard 的分類，將 P/E cap 標成輔助或改由 P/B/event 模型主導。
4. 保留 CPO/IP/ASIC 的高 hard，但新增條件：必須有 FY2/FY3 EPS 上修、客戶/訂單能見度、毛利率不下滑，否則自動降到 soft 以下。

## 資料來源

- TWSE Daily P/E ratio notes: https://www.twse.com.tw/en/trading/historical/bwibbu.html
- TWSE Fact Book 2025, PER / Dividend Yield / PBR by Industry Year-end 2024: https://wwwc.twse.com.tw/downloads/zh/about/company/factbook/2025/2.08.html
- World PE Ratio, Taiwan Stock Market P/E, 2026-06-08: https://worldperatio.com/area/taiwan/
- Simply Wall St, Taiwanese Market Analysis, updated 2026-06-08: https://simplywall.st/markets/tw
- Simply Wall St, Taiwanese Semiconductors Industry Analysis, updated 2026-06-06: https://simplywall.st/markets/tw/tech/semiconductors
