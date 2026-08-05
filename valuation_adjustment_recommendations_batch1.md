# 產業估值模型建議調整表 - 第一批高倍率分類

- 查核基準日：2026-06-05
- 產出日期：2026-06-07
- 查核來源：`valuation_external_audit_batch1.md`
- 本表只提供調整建議，尚未改 `industry_taxonomy.py` / `dynamic_cap_model.py` / `stock_mapping.py`。

## 調整原則

1. 官方 PE 高於 hard ceiling 不等於應上修模型天花板；若 EPS/訂單未充分落地，應標示為「市場重估 / 動能區」。
2. 同分類內 PE/PB 差距過大時，優先拆分類，不用單一 taxon 硬套所有公司。
3. base_pe 是可解釋的產業中樞，不是追價倍率；soft/hard 是可操作上緣與風控上限。
4. 法人單日買賣超只作籌碼溫度，不能取代 EPS、法說、訂單能見度。

## 分類層級建議

| 現行 taxon | 現行 base/soft/hard | 外部查核現象 | 建議處理 | 建議新倍率或規則 |
|---|---:|---|---|---|
| `PROBE_AI_ASIC` | 45 / 65 / 75 | 3 檔全高於 hard，PE 約 96.8-172.6，PB 約 11.0-46.7 | 不直接上修 base；新增「市場重估/動能區」判斷 | 維持 45 / 65 / 75；若 PE > 75，輸出「高估值動能區，需 EPS 上修驗證」 |
| `IC_DESIGN_IP_ROYALTY` | 45 / 75 / 90 | 力旺、愛普*、M31 高於 hard；M31 官方 PE 極端值，晶心科無 PE | 拆成純 IP/Royalty 與 EPS 未穩/記憶體 IP 題材 | 純 IP 維持 45 / 75 / 90；EPS 極端或無 PE 者切事件/PB 輔助 |
| `OPTICAL_COMM_SILICON_PHOTONICS` | 36 / 54 / 68 | 10 檔中 6 檔高於 hard，PE 中位數約 111.1；CPO/800G 題材溢價差異很大 | 拆成高能見度 CPO/矽光子與一般光通訊 | 高能見度層 42 / 70 / 90；一般層 30 / 45 / 58 |
| `SEMICAP_COWOS_EQUIPMENT` | 32 / 50 / 65 | 11 檔中 5 檔高於 hard；京鼎、群翊、迅得等 PE 明顯較低 | 拆成 CoWoS/先進封裝核心設備與一般半導體/PCB設備 | 核心設備 38 / 60 / 80；一般設備 28 / 42 / 55 |
| `THERMAL_LIQUID_COOLING` | 34 / 50 / 62 | 分類內差距極大：一詮 PE 548、健策/高力高於 hard，但建準/元山/動力偏低 | 拆成液冷核心、AI散熱零組件、傳統風扇/散熱 | 液冷核心 38 / 60 / 80；AI散熱零組件 30 / 45 / 58；傳統散熱 18 / 28 / 35 |
| `IC_DESIGN_ASIC_HIGH_VISIBILITY` | 45 / 70 / 85 | 世芯-KY PE 62.8，仍在 soft/hard 內，但外資與投信同日偏賣 | 暫不調整，保留逐季 EPS/客戶集中風險檢查 | 維持 45 / 70 / 85；若法人 EPS 下修則降回 ASIC_SERVICE |

## 個股遷移建議

| 股票 | 現行 taxon | 外部資料初判 | 建議 taxon / 規則 | 優先度 |
|---|---|---|---|---|
| 6223 旺矽 | `PROBE_AI_ASIC` | PE 153.5、PB 35.85，超過 hard | 保留 `PROBE_AI_ASIC`，但 PE > hard 時標示動能區，不上修 base | 高 |
| 6510 精測 | `PROBE_AI_ASIC` | PE 96.8、PB 11.03，超過 hard | 保留 `PROBE_AI_ASIC`，需查 EPS 上修與 AI ASIC 測試占比 | 高 |
| 6515 穎崴 | `PROBE_AI_ASIC` | PE 172.6、PB 46.73，外資/投信同向偏賣 | 保留 `PROBE_AI_ASIC`，強制高估值警示 | 高 |
| 3529 力旺 | `IC_DESIGN_IP_ROYALTY` | PE 125.4、PB 57.8，超過 hard | 保留純 IP/Royalty，但 PE > hard 時列市場重估區 | 高 |
| 6643 M31 | `IC_DESIGN_IP_ROYALTY` | 官方 PE 13900，疑似 EPS 分母極低造成失真 | 加入 EPS 失真防護：PE 極端值時改事件/PB 輔助，不提高 hard | 高 |
| 6531 愛普* | `IC_DESIGN_IP_ROYALTY` | PE 102.6，外資買、投信賣，且具記憶體循環屬性 | 建議新分類或 hybrid：`MEMORY_IP_AI` / `MEMORY_CYCLE` 權重提高 | 中 |
| 6533 晶心科 | `IC_DESIGN_IP_ROYALTY` | 無官方 PE，PB 2.58，外資偏賣 | EPS 未落地時改事件模型，不套 IP 高倍率 | 中 |
| 3081 聯亞 | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 348.9、PB 57.94，極高估值 | 遷入高能見度 CPO/矽光子，但 PE > hard 仍只列動能區 | 高 |
| 3163 波若威 | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 118.1、PB 25.73，超過 hard | 高能見度 CPO/光通訊；需查 EPS 與 800G/CPO 比重 | 高 |
| 3450 聯鈞 | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 149.1，外資大賣 | 高能見度 CPO/光通訊，但加法人偏空警示 | 高 |
| 4979 華星光 | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 107.8、PB 20.53 | 高能見度 CPO/光通訊；PE > hard 標示動能區 | 高 |
| 6442 光聖 | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 77.5，高於現 hard 68 | 高能見度 CPO/矽光子；若新 hard 90 內可列偏熱而非極高 | 高 |
| 3363 上詮 | `OPTICAL_COMM_SILICON_PHOTONICS` | 無官方 PE，PB 17.99，三大法人偏買 | EPS 未穩時事件/PB 輔助，不用純 PE 買進倍率 | 中 |
| 6451 訊芯-KY | `OPTICAL_COMM_SILICON_PHOTONICS` | 無官方 PE，外資偏賣 | 暫保留，需查矽光子封裝營收落地；EPS 未穩改事件模型 | 中 |
| 4977 眾達-KY | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 44.5，在現 soft 內 | 保留一般光通訊或高能見度低權重，不需上修 | 低 |
| 6530 創威 | `OPTICAL_COMM_SILICON_PHOTONICS` | PE 51.2，接近現 soft | 保留一般光通訊，不需上修 | 低 |
| 2467 志聖 | `SEMICAP_COWOS_EQUIPMENT` | PE 77.1，外資偏賣 | 若 CoWoS 訂單占比不足，降至一般設備；若落地則核心設備 | 高 |
| 3131 弘塑 | `SEMICAP_COWOS_EQUIPMENT` | PE 60.0，高於 soft 但未超 hard | 遷入核心先進封裝/濕製程設備 | 高 |
| 3583 辛耘 | `SEMICAP_COWOS_EQUIPMENT` | PE 58.9，高於 soft | 遷入核心先進封裝設備 | 高 |
| 6187 萬潤 | `SEMICAP_COWOS_EQUIPMENT` | PE 74.2，高於 hard，三大法人偏買 | 遷入核心先進封裝設備，但列偏高 | 高 |
| 6640 均華 | `SEMICAP_COWOS_EQUIPMENT` | PE 73.9，高於 hard | 遷入核心先進封裝設備，需查 EPS/訂單 | 高 |
| 6937 天虹 | `SEMICAP_COWOS_EQUIPMENT` | PE 86.9，外資/投信同向偏賣 | 若設備訂單能見度不足，保守列一般設備或動能區 | 高 |
| 8064 東捷 | `SEMICAP_COWOS_EQUIPMENT` | PE 78.7，外資大賣 | 建議降至一般設備/FOPLP題材，不宜吃核心 CoWoS 高倍率 | 高 |
| 3413 京鼎 | `SEMICAP_COWOS_EQUIPMENT` | PE 16.8、PB 2.21，低於 base | 建議降至一般半導體設備/設備零組件，不用 CoWoS 高倍率 | 中 |
| 6438 迅得 | `SEMICAP_COWOS_EQUIPMENT` | PE 28.9、PB 2.30 | 建議一般設備/自動化設備，不用核心 CoWoS 高倍率 | 中 |
| 6664 群翊 | `SEMICAP_COWOS_EQUIPMENT` | PE 28.1、PB 6.43 | 建議一般設備/PCB設備，不用核心 CoWoS 高倍率 | 中 |
| 8027 鈦昇 | `SEMICAP_COWOS_EQUIPMENT` | 無官方 PE，PB 11.24，外資偏賣 | EPS 未穩時事件/PB 輔助，暫不套高 PE | 中 |
| 3653 健策 | `THERMAL_LIQUID_COOLING` | PE 100.1、PB 25.08 | 遷入液冷/高階散熱核心，PE > 80 標示動能區 | 高 |
| 8996 高力 | `THERMAL_LIQUID_COOLING` | PE 80.2、PB 22.53，投信買但外資賣 | 遷入液冷核心，需加籌碼分歧警示 | 高 |
| 3017 奇鋐 | `THERMAL_LIQUID_COOLING` | PE 42.7、PB 22.60，外資/投信偏賣 | 遷入液冷核心，但法人偏空時降低可操作倍率 | 高 |
| 3324 雙鴻 | `THERMAL_LIQUID_COOLING` | PE 32.0、PB 7.70 | AI散熱零組件，現倍率可維持 | 中 |
| 2486 一詮 | `THERMAL_LIQUID_COOLING` | PE 548.0，外資偏賣，疑似 EPS 分母失真 | 不應用液冷核心 PE；改事件/PB 輔助或一般散熱題材 | 高 |
| 3338 泰碩 | `THERMAL_LIQUID_COOLING` | PE 53.8，PB 3.34 | AI散熱零組件，接近偏熱 | 中 |
| 2421 建準 | `THERMAL_LIQUID_COOLING` | PE 19.7，外資/投信偏賣 | 傳統風扇/散熱，建議降至 `THERMAL_AIR` | 中 |
| 3483 力致 | `THERMAL_LIQUID_COOLING` | PE 25.4，外資偏賣 | 傳統/一般散熱，建議降至 `THERMAL_AIR` 或 AI散熱零組件低權重 | 中 |
| 4543 萬在 | `THERMAL_LIQUID_COOLING` | PE 42.3、PB 1.37 | 暫列 AI散熱零組件，不用液冷核心倍率 | 中 |
| 6230 尼得科超眾 | `THERMAL_LIQUID_COOLING` | 無官方 PE，PB 2.07 | 傳統散熱，建議降至 `THERMAL_AIR` | 中 |
| 6275 元山 | `THERMAL_LIQUID_COOLING` | PE 18.2、PB 2.47 | 傳統風扇/散熱，建議降至 `THERMAL_AIR` | 中 |
| 6591 動力-KY | `THERMAL_LIQUID_COOLING` | PE 13.5、PB 1.10 | 傳統風扇/散熱，建議降至 `THERMAL_AIR` | 中 |
| 3661 世芯-KY | `IC_DESIGN_ASIC_HIGH_VISIBILITY` | PE 62.8，仍在模型 soft/hard 內，但法人同向偏賣 | 暫維持，加入法人偏空時不得再加 AI 題材倍率 | 中 |

## 建議新增 / 調整 taxon

| 建議 taxon | 用途 | base | soft | hard | 適用公司候選 |
|---|---|---:|---:|---:|---|
| `OPTICAL_COMM_CPO_HIGH_VISIBILITY` | CPO/矽光子/800G 營收與 EPS 已落地者 | 42 | 70 | 90 | 3081、3163、3450、4979、6442、3363、6451 |
| `OPTICAL_COMM_STANDARD` | 一般光通訊或題材尚未完全落地 | 30 | 45 | 58 | 4977、6530、4908 視 EPS 重新確認 |
| `SEMICAP_ADV_PACKAGING_CORE` | CoWoS/先進封裝核心設備、濕製程、測試自動化 | 38 | 60 | 80 | 3131、3583、6187、6640、部分 2467/6937 |
| `SEMICAP_GENERAL_EQUIPMENT` | 一般半導體設備、PCB設備、自動化設備 | 28 | 42 | 55 | 3413、6438、6664、8064、8027 |
| `THERMAL_LIQUID_CORE` | 液冷核心、高階均熱/散熱模組且 EPS 落地 | 38 | 60 | 80 | 3017、3653、8996 |
| `THERMAL_AI_COMPONENTS` | AI散熱零組件，但非液冷核心 | 30 | 45 | 58 | 3324、3338、4543、部分 3483 |
| `MEMORY_IP_AI` | 愛普* 類記憶體 IP/AI memory，兼具高毛利與記憶體循環 | 35 | 60 | 75 | 6531 |

## 不建議調高的項目

| 項目 | 理由 |
|---|---|
| `PROBE_AI_ASIC` hard ceiling 不建議超過 75 | 三檔官方 PE 都已高於 hard，若跟著上修會把買進模型變成追價模型；應用動能區提示取代上修。 |
| `IC_DESIGN_IP_ROYALTY` hard ceiling 不建議超過 90 | 力旺/M31 類高 PB、高 PE 本來就屬市場重估；模型應提醒風險，不應把 100x+ 當可操作常態。 |
| `THERMAL_LIQUID_COOLING` 不應一體上修 | 分類內從 PE 13.5 到 548 都有，表示分類過寬，應拆分類，不是整體抬倍率。 |
| `SEMICAP_COWOS_EQUIPMENT` 不應一體上修 | 京鼎、群翊、迅得等低 PE 公司與弘塑/萬潤/均華不同，應拆核心與一般設備。 |

## 實作順序建議

1. 先新增 taxon：`THERMAL_LIQUID_CORE`、`THERMAL_AI_COMPONENTS`、`SEMICAP_ADV_PACKAGING_CORE`、`SEMICAP_GENERAL_EQUIPMENT`、`OPTICAL_COMM_CPO_HIGH_VISIBILITY`、`OPTICAL_COMM_STANDARD`。
2. 移動明顯錯層公司：建準、元山、動力-KY、尼得科超眾降出液冷核心；京鼎、迅得、群翊、東捷降出 CoWoS 核心。
3. 高 PE 但題材明確者保留高能見度分類，同時在 Dynamic Cap 報告中加「PE > hard ceiling = 市場重估/動能區，不產生買進倍率」提示。
4. 對 M31、上詮、訊芯-KY、鈦昇等無 PE 或 PE 極端值個股加入 EPS 失真防護，切換事件/PB 輔助。
5. 第二輪再查：第二批新增半導體分類 `POWER_ANALOG_IC`、`COMPOUND_SEMICONDUCTOR_OPTO`、`IC_DESIGN_CONSUMER`、`OSAT_TESTING`。

