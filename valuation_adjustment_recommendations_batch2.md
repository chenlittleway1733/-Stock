# 產業估值模型建議調整表 - 第二批半導體中游/週期分類

- 查核基準日：2026-06-05
- 產出日期：2026-06-07
- 查核來源：`valuation_external_audit_batch2.md`
- 本表只提供調整建議，尚未改 `industry_taxonomy.py` / `dynamic_cap_model.py` / `stock_mapping.py`。

## 調整原則

1. 第二批多數分類屬成熟/週期/庫存循環，不能因官方 PE 偏高就上修 hard ceiling。
2. 記憶體、矽晶圓、一般消費 IC、功率半導體應以 P/B、庫存、報價、毛利率為主，P/E 只作輔助。
3. 同分類中若同時存在「AI/高能見度」與「成熟週期」公司，優先拆分類。
4. 官方 PE 極端值多半代表 EPS 分母過低，不代表可操作倍率應提高。

## 分類層級建議

| 現行 taxon | 現行 base/soft/hard | 外部查核現象 | 建議處理 | 建議新倍率或規則 |
|---|---:|---|---|---|
| `MEMORY_CYCLE` | 12 / 18 / 24 | 9 檔 PB 幾乎都偏高，且三大法人多數偏賣 | 不上修 PE；強化 P/B 週期模型與法人偏空警示 | 維持 12 / 18 / 24；加入 PB > 3.0 高檔週期警示 |
| `SILICON_WAFER_CYCLE` | 18 / 28 / 36 | PE 極端失真，合晶/台勝科/嘉晶 PE 遠高於 hard；PB 多數偏高 | 不上修；改以 P/B/報價/稼動率優先 | 維持 18 / 28 / 36；PB > 3.0 需標示週期高檔 |
| `IC_DESIGN_CONSUMER` | 18 / 26 / 32 | 大多數落在合理區，但聯傑、盛群、松翰、凌通等 PE 高於 hard | 不整體上修；加入 EPS 失真/週期防護 | 維持 18 / 26 / 32；PE > 50 且 PB 不高者列 EPS 分母失真 |
| `IC_DESIGN_PLATFORM_AI_EDGE` | 24 / 38 / 50 | 信驊、聯發科、威鋒 PE 高於 hard，分類內差異大 | 拆出 Server BMC / 高速介面 / 大型平台 IC | 大型平台維持 24 / 38 / 50；Server BMC 可獨立高能見度分類 |
| `OSAT_TESTING` | 24 / 35 / 42 | 日月光、南茂高於 hard；京元電、力成、欣銓偏熱；成熟封測差異大 | 拆成 AI/HPC測試封測與成熟/記憶體封測 | AI/HPC OSAT 28 / 45 / 58；成熟封測 18 / 30 / 40 |
| `POWER_ANALOG_IC` | 22 / 36 / 48 | 矽力、通嘉、強茂高於 hard；離散功率與 PMIC 混在一起 | 拆成功率離散元件與 PMIC/類比 IC 設計 | PMIC/類比 26 / 42 / 58；功率離散 18 / 30 / 42 |
| `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | 26 / 38 / 45 | 中砂、順德、家登、頌勝 PE/PB 明顯分歧 | 拆成先進製程耗材/載具、功率導線架、COF/顯示材料 | 先進耗材 34 / 55 / 70；功率材料 22 / 35 / 45；COF 18 / 30 / 40 |
| `COMPOUND_SEMICONDUCTOR_OPTO` | 22 / 34 / 45 | 全訊 PE 高於 hard，台亞無 PE 且外資偏賣 | 暫不拆，但加入 PE 高於 hard 時 PB/事件輔助 | 維持 22 / 34 / 45；全訊需查 RF/GaAs 訂單能見度 |

## 個股調整建議

| 股票 | 現行 taxon | 外部資料初判 | 建議處理 | 優先度 |
|---|---|---|---|---|
| 2337 旺宏 | `MEMORY_CYCLE` | 無 PE、PB 5.86、法人偏賣 | 保留 P/B 週期；加 PB 高檔與法人偏空警示 | 高 |
| 2344 華邦電 | `MEMORY_CYCLE` | PE 48.1、PB 6.25、外資/投信大賣 | 保留 P/B 週期；不因 PE 上修 | 高 |
| 2408 南亞科 | `MEMORY_CYCLE` | PE 32.2、PB 5.78、法人偏賣 | 保留 P/B 週期；加報價循環/庫存警示 | 高 |
| 3260 威剛 | `MEMORY_CYCLE` | PE 8.4 但 PB 4.85、外資偏賣 | 防止低 PE 誤判便宜；P/B 高檔警示 | 高 |
| 3016 嘉晶 | `SILICON_WAFER_CYCLE` | PE 263.4、PB 6.36 | PE 失真；保留矽晶圓週期模型 | 高 |
| 3532 台勝科 | `SILICON_WAFER_CYCLE` | PE 367.1、PB 4.64 | PE 失真；保留 P/B 週期 | 高 |
| 6182 合晶 | `SILICON_WAFER_CYCLE` | PE 2137.5、PB 3.21 | 強制 EPS 分母失真防護 | 高 |
| 6488 環球晶 | `SILICON_WAFER_CYCLE` | PE 50.0、PB 4.15 | 保留週期模型；避免用 PE 追價 | 中 |
| 5274 信驊 | `IC_DESIGN_PLATFORM_AI_EDGE` | PE 148.5、PB 111.0 | 建議拆出 `IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY`，但 PE > hard 仍列動能區 | 高 |
| 2454 聯發科 | `IC_DESIGN_PLATFORM_AI_EDGE` | PE 68.5、PB 17.6，仍是大型平台股 | 保留平台 IC；AI ASIC 用 hybrid，不直接升成純 ASIC | 高 |
| 6756 威鋒電子 | `IC_DESIGN_PLATFORM_AI_EDGE` | PE 62.7，高於 hard | 改列高速介面/USB 控制 IC，暫不享大型平台高倍率 | 中 |
| 2379 瑞昱 | `IC_DESIGN_PLATFORM_AI_EDGE` | PE 23.1，外資賣、投信買 | 保留平台 IC；籌碼分歧提示 | 低 |
| 3094 聯傑 | `IC_DESIGN_CONSUMER` | PE 122.5、PB 2.62 | EPS 分母失真/轉機防護，不上修分類倍率 | 高 |
| 6202 盛群 | `IC_DESIGN_CONSUMER` | PE 83.3、PB 3.14、外資偏賣 | EPS 失真/消費 IC 庫存循環警示 | 高 |
| 5471 松翰 | `IC_DESIGN_CONSUMER` | PE 52.8、PB 2.42 | 不上修；列偏熱/低 EPS 分母 | 中 |
| 4952 凌通 | `IC_DESIGN_CONSUMER` | PE 44.5、PB 2.46 | 不上修；維持一般 IC 設計 | 中 |
| 6962 奕力-KY | `IC_DESIGN_CONSUMER` | PE 24.7、PB 0.87，外資偏賣 | 顯示驅動 IC 低 PB，保留週期模型 | 中 |
| 3711 日月光投控 | `OSAT_TESTING` | PE 53.6、PB 7.22、法人偏賣 | 大型 OSAT/先進封裝 hybrid，需拆出 AI/HPC OSAT | 高 |
| 2449 京元電子 | `OSAT_TESTING` | PE 42.0、PB 6.95、法人偏賣 | AI/HPC 測試占比高，建議 `OSAT_AI_HPC_TESTING` | 高 |
| 3264 欣銓 | `OSAT_TESTING` | PE 35.4、PB 5.35 | 測試/車用 OSAT，偏熱但未超 hard | 中 |
| 6239 力成 | `OSAT_TESTING` | PE 40.2、外資買投信賣 | 記憶體封測，保留 OSAT 但加記憶體循環風險 | 中 |
| 8150 南茂 | `OSAT_TESTING` | PE 82.0、PB 2.75 | 驅動 IC/記憶體封測，PE 失真防護 | 高 |
| 6415 矽力*-KY | `POWER_ANALOG_IC` | PE 78.2、PB 5.93 | 拆入 `POWER_MANAGEMENT_IC_DESIGN`，但高於 hard 時動能區 | 高 |
| 3588 通嘉 | `POWER_ANALOG_IC` | PE 98.2、PB 2.03 | PMIC 類，但 PE 明顯失真，需事件/PB 輔助 | 高 |
| 2481 強茂 | `POWER_ANALOG_IC` | PE 52.4、PB 4.35、外資大買投信賣 | 功率離散元件，建議 `POWER_DISCRETE_COMPONENT_CYCLE` | 高 |
| 8261 富鼎 | `POWER_ANALOG_IC` | PE 29.3、PB 3.32、法人偏賣 | MOSFET/功率離散，建議功率離散分類 | 中 |
| 1560 中砂 | `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | PE 68.8、PB 12.62 | 先進製程耗材/鑽石碟，建議拆出高能見度材料 | 高 |
| 3680 家登 | `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | PE 53.2、PB 4.45 | EUV/載具，建議先進耗材分類 | 高 |
| 7768 頌勝科技 | `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | PE 132.4、PB 13.0 | CMP耗材新上市，需高估值動能區/失真防護 | 高 |
| 2351 順德 | `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | PE 88.7、PB 5.04 | 導線架/功率材料，不宜吃先進耗材高倍率 | 高 |
| 5285 界霖 | `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | PE 43.7、PB 3.15 | 導線架/功率材料，分類應獨立 | 中 |
| 6552 易華電 | `SEMICONDUCTOR_MATERIALS_CONSUMABLES` | 無 PE、PB 1.63 | COF/顯示材料，應與半導體耗材拆開 | 中 |
| 5222 全訊 | `COMPOUND_SEMICONDUCTOR_OPTO` | PE 65.0、PB 4.60、法人偏賣 | 若 RF/GaAs 訂單無高能見度，維持週期/PB，不上修 | 中 |
| 2340 台亞 | `COMPOUND_SEMICONDUCTOR_OPTO` | 無 PE、PB 2.47、外資偏賣 | 保留事件/PB 輔助，等待 EPS 穩定 | 中 |

## 建議新增 / 調整 taxon

| 建議 taxon | 用途 | base | soft | hard | 適用公司候選 |
|---|---|---:|---:|---:|---|
| `OSAT_AI_HPC_TESTING` | AI/HPC 測試、先進封測能見度較高 | 28 | 45 | 58 | 2449、3264、3711 部分 hybrid |
| `OSAT_MEMORY_DISPLAY_MATURE` | 記憶體/驅動 IC/成熟封測 | 18 | 30 | 40 | 2329、2369、2441、6239、6525、8110、8131、8150 |
| `POWER_MANAGEMENT_IC_DESIGN` | PMIC/類比 IC 設計 | 26 | 42 | 58 | 3257、3588、6415、6719、6799、8081 |
| `POWER_DISCRETE_COMPONENT_CYCLE` | 二極體/MOSFET/整流器等功率離散元件 | 18 | 30 | 42 | 2302、2434、2481、6573、8261 |
| `SEMIMAT_ADVANCED_CONSUMABLES` | 先進製程耗材、EUV載具、CMP耗材 | 34 | 55 | 70 | 1560、3680、7768、2338 視 EPS |
| `SEMIMAT_POWER_LEADFRAME` | 導線架、功率元件材料 | 22 | 35 | 45 | 2351、5285 |
| `DISPLAY_COF_MATERIALS` | COF/顯示驅動 IC 材料 | 18 | 30 | 40 | 6552 |
| `IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY` | Server BMC/資料中心高毛利 IC | 42 | 70 | 90 | 5274 |

## 不建議調高的項目

| 項目 | 理由 |
|---|---|
| `MEMORY_CYCLE` 不建議上修 | PB 普遍偏高且法人偏空，低 PE 反而可能是景氣高峰/報價循環陷阱。 |
| `SILICON_WAFER_CYCLE` 不建議上修 | PE 大量極端失真，矽晶圓應以 P/B、報價與稼動率為主。 |
| `IC_DESIGN_CONSUMER` 不建議整體上修 | 中位 PE 約 21.2，只有部分 EPS 分母失真股高於 hard。 |
| `POWER_ANALOG_IC` 不建議整體上修 | PMIC 與功率離散元件混在一起，應拆分類，不是調高整體 hard。 |
| `SEMICONDUCTOR_MATERIALS_CONSUMABLES` 不建議整體上修 | 中砂/家登/頌勝與順德/界霖/易華電產業邏輯不同，需拆分。 |

## 實作順序建議

1. 先補週期防護：`MEMORY_CYCLE`、`SILICON_WAFER_CYCLE` 加 PB 高檔警示與 PE 極端值防護。
2. 拆 `POWER_ANALOG_IC`：PMIC/類比 IC 與功率離散元件分開。
3. 拆 `SEMICONDUCTOR_MATERIALS_CONSUMABLES`：先進耗材、導線架/功率材料、COF/顯示材料分開。
4. 拆 `OSAT_TESTING`：AI/HPC 測試與成熟/記憶體/驅動 IC 封測分開。
5. 單獨處理 `5274 信驊`：建立 Server BMC 高能見度分類，保留動能區警示。

