# 產業估值模型建議調整表 - 第三批 AI伺服器/電子零組件主鏈

- 查核基準日：2026-06-05
- 產出日期：2026-06-07
- 查核來源：`valuation_external_audit_batch3.md`
- 本表只提供調整建議，尚未改 `industry_taxonomy.py` / `dynamic_cap_model.py` / `stock_mapping.py`。

## 調整原則

1. 第三批不是所有 AI 伺服器供應鏈都該上修；ODM 多數 PE 並未超過 hard ceiling，真正過熱集中在 ABF/CCL、機構件、電源、部分 PCB 與連接器。
2. 高 PB 高 PE 的材料/零組件股應標示「市場重估 / 動能區」，不直接把 base_pe 抬高。
3. AI 純度差異大的分類應拆成「高能見度核心」與「一般/低純度」。
4. 代工/ODM 應以 AI server 營收占比、毛利率改善與 hybrid 權重處理，不宜全部套純 AI server 倍率。

## 分類層級建議

| 現行 taxon | 現行 base/soft/hard | 外部查核現象 | 建議處理 | 建議新倍率或規則 |
|---|---:|---|---|---|
| `ABF_SUBSTRATE` | 30 / 45 / 55 | 3 檔全高於 hard，PE 137-201、PB 8.7-13.1 | 不上修整體；改成 ABF 循環復甦/動能區 | 維持 30 / 45 / 55；PE > hard 標示動能區，PB > 8 高檔警示 |
| `CCL_HIGH_SPEED_MATERIALS` | 24 / 35 / 42 | 台光電/台燿 PE > 100、PB > 25，聯茂也高於 hard | 拆成高階 AI CCL 與一般 CCL | 高階 AI CCL 36 / 60 / 80；一般 CCL 22 / 35 / 45 |
| `SERVER_CHASSIS_RAIL` | 26 / 38 / 45 | 8 檔中 5 檔高於 hard；川湖/富世達/南俊 PB 極高 | 拆成高階滑軌/折疊機構件、AI機殼、一般機殼 | 高階機構 38 / 60 / 80；AI機殼 30 / 45 / 58；一般機殼 18 / 30 / 40 |
| `POWER_BBU` | 26 / 38 / 46 | 台達電、康舒 PE 高於 hard；旭隼/光寶/群電/全漢差異大 | 拆成電源龍頭/資料中心電源、UPS/高毛利電源、一般電源 | 電源龍頭 34 / 55 / 70；UPS高毛利 28 / 42 / 55；一般電源 18 / 30 / 40 |
| `SERVER_PCB_BOARD` | 28 / 42 / 52 | 金像電、定穎高於 hard；華通偏熱，健鼎較合理 | 拆成 AI Server PCB 高能見度與一般 PCB | AI Server PCB 34 / 55 / 70；一般 PCB 22 / 35 / 45 |
| `CONNECTOR_CABLE` | 30 / 45 / 55 | 嘉基 PE 205；貿聯/佳必琪 PB 偏高；一般線材差距大 | 拆成高速連接器與一般連接/線材 | 高速連接器 34 / 55 / 70；一般線材 18 / 30 / 40 |
| `NETWORK_SWITCH` | 28 / 42 / 52 | 智邦、啟碁偏熱；其餘多為一般網通 | 拆出 AI Data Center switch | AI DC switch 36 / 58 / 75；一般網通 20 / 32 / 42 |
| `PC_NB_ODM` | 16 / 24 / 32 | 廣達/緯創/英業達/仁寶 AI 純度差異大，但 PE 未整體過熱 | 不拆大分類，改強化 hybrid 權重 | 純 NB ODM 維持 16 / 24 / 32；AI 權重依純度給 0.15-0.45 |
| `EMS_PLATFORM_CONTRACT_MANUFACTURING` | 14 / 24 / 32 | 鴻海 PE 20.2，未過熱 | 維持，AI server/EV 只透過 hybrid | 維持 14 / 24 / 32 |
| `AI_SERVER_ODM` | 24 / 34 / 42 | 緯穎/神達 PE 未過熱 | 暫維持 | 維持 24 / 34 / 42 |
| `AI_SERVER_BOARD_SYSTEM` | 26 / 36 / 45 | 技嘉/微星 PE 未過熱 | 暫維持，避免過度上修 | 維持 26 / 36 / 45 |
| `IPC_EDGE_AI` | 22 / 34 / 42 | 研華偏熱，但樺漢/振樺較正常 | 不拆；研華可加高品質龍頭註記 | 維持 22 / 34 / 42 |

## 個股調整建議

| 股票 | 現行 taxon | 外部資料初判 | 建議處理 | 優先度 |
|---|---|---|---|---|
| 3037 欣興 | `ABF_SUBSTRATE` | PE 137.2、PB 13.07、法人同向偏賣 | 保留 ABF，但加 PB 高檔與動能區警示 | 高 |
| 3189 景碩 | `ABF_SUBSTRATE` | PE 200.6、PB 8.69 | 保留 ABF，PE 極端防護，不上修 base | 高 |
| 8046 南電 | `ABF_SUBSTRATE` | PE 179.0、PB 11.69、投信賣 | 保留 ABF，標示高估值動能區 | 高 |
| 2383 台光電 | `CCL_HIGH_SPEED_MATERIALS` | PE 106.0、PB 36.51 | 建議 `AI_CCL_HIGH_VISIBILITY`，但 PE > hard 仍動能區 | 高 |
| 6274 台燿 | `CCL_HIGH_SPEED_MATERIALS` | PE 116.3、PB 25.74 | 建議 `AI_CCL_HIGH_VISIBILITY`，需高估值警示 | 高 |
| 6213 聯茂 | `CCL_HIGH_SPEED_MATERIALS` | PE 62.2、PB 4.39 | 一般/高階 CCL 中間層，保守給高階低權重 | 中 |
| 2059 川湖 | `SERVER_CHASSIS_RAIL` | PE 49.5、PB 16.99 | 高階滑軌核心，建議 `SERVER_RAIL_HIGH_VISIBILITY` | 高 |
| 6805 富世達 | `SERVER_CHASSIS_RAIL` | PE 49.8、PB 18.01 | 高階機構件，建議高能見度分類，但 PB 動能區警示 | 高 |
| 6584 南俊國際 | `SERVER_CHASSIS_RAIL` | PE 85.1、PB 12.87 | 高階滑軌/機構件，但 PE > hard，需動能區 | 高 |
| 8210 勤誠 | `SERVER_CHASSIS_RAIL` | PE 40.6、PB 13.61 | AI 機殼，建議 `AI_SERVER_CHASSIS_CORE` | 高 |
| 5426 振發 | `SERVER_CHASSIS_RAIL` | PE 76.8、PB 1.86 | EPS 分母偏低，若 AI 純度不足不應吃高階滑軌倍率 | 中 |
| 3693 營邦 | `SERVER_CHASSIS_RAIL` | PE 66.1、PB 4.62 | AI 機殼/伺服器機殼題材，需動能區或一般機殼 | 中 |
| 2308 台達電 | `POWER_BBU` | PE 84.8、PB 19.94 | 建議 `DATACENTER_POWER_LEADER`，但列動能區 | 高 |
| 6282 康舒 | `POWER_BBU` | PE 127.6、外資大賣 | EPS 分母失真/一般電源防護，不應上修整體 POWER_BBU | 高 |
| 6409 旭隼 | `POWER_BBU` | PE 26.6、PB 7.88 | UPS 高毛利電源，建議獨立 `UPS_POWER_QUALITY` | 中 |
| 2301 光寶科 | `POWER_BBU` | PE 33.8、PB 5.92 | 資料中心電源/光電混合，保留或低權重電源龍頭 | 中 |
| 6412 群電 | `POWER_BBU` | PE 18.8、投信賣 | 一般電源，不套資料中心高倍率 | 中 |
| 2368 金像電 | `SERVER_PCB_BOARD` | PE 59.4、PB 19.28 | 建議 `AI_SERVER_PCB_HIGH_VISIBILITY`，動能區警示 | 高 |
| 3715 定穎投控 | `SERVER_PCB_BOARD` | PE 175.3、PB 4.48 | PE 分母失真/題材化，需動能區，不上修整體 PCB | 高 |
| 2313 華通 | `SERVER_PCB_BOARD` | PE 45.7、外資大賣 | AI Server PCB/低軌混合，偏熱但未超 hard | 中 |
| 3044 健鼎 | `SERVER_PCB_BOARD` | PE 24.2、PB 4.49 | 一般 PCB/伺服器板，維持一般層 | 低 |
| 6715 嘉基 | `CONNECTOR_CABLE` | PE 205.7、PB 7.97 | EPS 分母失真，若高速占比不足需事件/PB 輔助 | 高 |
| 3533 嘉澤 | `CONNECTOR_CABLE` | PE 33.2、PB 6.33 | 高速連接器核心，建議 `HIGH_SPEED_CONNECTOR_CORE` | 高 |
| 3665 貿聯-KY | `CONNECTOR_CABLE` | PE 44.4、PB 9.20，法人偏買 | 高速線束/車用/AI 混合，建議核心連接分類 | 高 |
| 6197 佳必琪 | `CONNECTOR_CABLE` | PE 31.7、PB 8.69 | 高速連接/線材偏熱，核心連接分類或 PB 警示 | 中 |
| 6290 良維 | `CONNECTOR_CABLE` | PE 40.9、PB 7.87 | 高階線材，偏熱，需分類權重 | 中 |
| 2392 正崴 | `CONNECTOR_CABLE` | 無 PE、PB 0.85 | 一般連接器/集團股，不套高速高倍率 | 中 |
| 2345 智邦 | `NETWORK_SWITCH` | PE 47.1、PB 21.31 | 建議 `AI_DATACENTER_SWITCH`，但 PB 高檔警示 | 高 |
| 6285 啟碁 | `NETWORK_SWITCH` | PE 43.1、PB 4.04 | 一般網通/低軌混合，偏熱，不直接升高能見度 | 中 |
| 3596 智易 | `NETWORK_SWITCH` | PE 15.1、PB 2.67 | 一般網通，維持一般層 | 低 |
| 3704 合勤控 | `NETWORK_SWITCH` | PE 41.5、PB 1.65 | 一般網通偏熱，維持一般層 | 低 |
| 2382 廣達 | `PC_NB_ODM` | PE 19.6、PB 7.25，外資賣投信買 | 保留 PC_NB_ODM + AI_SERVER_ODM hybrid，不升純 AI | 高 |
| 3231 緯創 | `PC_NB_ODM` | PE 17.1、PB 2.86 | 保留 hybrid，AI 純度較高但 PE 未過熱 | 高 |
| 2356 英業達 | `PC_NB_ODM` | PE 29.2、外資買投信賣 | AI server 權重低於廣達/緯創，維持 hybrid | 中 |
| 2324 仁寶 | `PC_NB_ODM` | PE 31.1、PB 1.38 | AI 純度低，不上修；若 EPS 未落地維持 NB ODM | 中 |
| 2317 鴻海 | `EMS_PLATFORM_CONTRACT_MANUFACTURING` | PE 20.2、PB 2.24 | 維持 EMS 平台，AI/EV 用 hybrid 權重 | 中 |
| 6669 緯穎 | `AI_SERVER_ODM` | PE 19.0、PB 7.50 | 純 AI server ODM 但未過熱，維持現倍率 | 中 |
| 3706 神達 | `AI_SERVER_ODM` | PE 17.6、PB 1.85 | 維持現倍率 | 低 |
| 2395 研華 | `IPC_EDGE_AI` | PE 38.5、PB 8.68 | IPC 龍頭品質溢價，偏熱但不拆 | 中 |

## 建議新增 / 調整 taxon

| 建議 taxon | 用途 | base | soft | hard | 適用公司候選 |
|---|---|---:|---:|---:|---|
| `AI_CCL_HIGH_VISIBILITY` | AI Server 高階 CCL / 高速材料 | 36 | 60 | 80 | 2383、6274 |
| `CCL_STANDARD_CYCLE` | 一般 CCL / 高階材料但 AI 純度較低 | 22 | 35 | 45 | 6213 |
| `SERVER_RAIL_HIGH_VISIBILITY` | 高階滑軌/高毛利機構件 | 38 | 60 | 80 | 2059、6584、6805 |
| `AI_SERVER_CHASSIS_CORE` | AI 機殼/伺服器機構件 | 30 | 45 | 58 | 8210、3693、3013 |
| `SERVER_CHASSIS_STANDARD` | 一般伺服器機殼/低純度機構件 | 18 | 30 | 40 | 5426、6117 |
| `DATACENTER_POWER_LEADER` | 資料中心電源/電源龍頭 | 34 | 55 | 70 | 2308、2301 部分 hybrid |
| `UPS_POWER_QUALITY` | UPS / 高毛利穩定電源 | 28 | 42 | 55 | 6409 |
| `POWER_SUPPLY_STANDARD` | 一般電源供應器 | 18 | 30 | 40 | 3015、3078、6282、6412 |
| `AI_SERVER_PCB_HIGH_VISIBILITY` | AI Server 高階 PCB | 34 | 55 | 70 | 2368、3715、2313 部分 |
| `PCB_STANDARD_BOARD` | 一般 PCB / 伺服器板 | 22 | 35 | 45 | 2367、3044、2313 部分 |
| `HIGH_SPEED_CONNECTOR_CORE` | 高速連接器/高速線束核心 | 34 | 55 | 70 | 3533、3665、6197、6290、6715 |
| `CONNECTOR_STANDARD` | 一般連接器/線材 | 18 | 30 | 40 | 2392、3605、8103 |
| `AI_DATACENTER_SWITCH` | AI Data Center switch / 高速交換器 | 36 | 58 | 75 | 2345 |
| `NETWORK_EQUIPMENT_STANDARD` | 一般網通設備 | 20 | 32 | 42 | 3025、3380、3596、3704、4906、5388、6285 |

## 不建議調高的項目

| 項目 | 理由 |
|---|---|
| `PC_NB_ODM` 不建議整體上修 | 廣達/緯創 AI 純度高，但仁寶/和碩/英業達差異大，應用 hybrid 權重。 |
| `AI_SERVER_ODM` 暫不調高 | 緯穎/神達 PE 未過熱，現有 24 / 34 / 42 仍可用。 |
| `ABF_SUBSTRATE` 不建議整體上修 | 三檔官方 PE/PB 都處高檔，應列動能區，不把 100x+ 視為常態。 |
| `CCL_HIGH_SPEED_MATERIALS` 不建議整體上修 | 台光電/台燿與聯茂差異大，需拆高能見度與一般層。 |
| `POWER_BBU` 不建議整體上修 | 台達電、旭隼、康舒、群電、全漢商業模式差異大。 |

## 實作順序建議

1. 先拆 `CCL_HIGH_SPEED_MATERIALS`、`SERVER_CHASSIS_RAIL`、`POWER_BBU`，因為外部 PE/PB 差異最大。
2. 再拆 `SERVER_PCB_BOARD`、`CONNECTOR_CABLE`、`NETWORK_SWITCH`。
3. `PC_NB_ODM`、`EMS_PLATFORM_CONTRACT_MANUFACTURING` 先不拆，改檢查 hybrid 權重是否合理。
4. `ABF_SUBSTRATE` 先加 PB 高檔與動能區警示，不急著拆。
5. 第三批若要實作，優先搬移高確定性個股：台光電、台燿、川湖、富世達、南俊、台達電、旭隼、金像電、智邦。

