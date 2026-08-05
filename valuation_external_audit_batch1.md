# 外部法人與估值現況查核 - 第一批高倍率分類

- 資料日期：2026-06-05（最近交易日）
- 查核範圍：41 檔，6 個高倍率/高敏感分類
- 資料來源：TWSE T86 三大法人日報、TWSE BWIBBU_ALL 本益比/PB、TPEx 三大法人 OpenAPI、TPEx 本益比/PB OpenAPI
- 本報告只列建議，不直接改模型參數。

## 分類結論摘要
| taxon | 檔數 | 模型倍率 base/soft/hard | 官方 PE 中位數 | 高於 soft | 高於 hard | 法人同向偏空 | 初步建議 |
|---|---:|---|---:|---:|---:|---:|---|
| IC_DESIGN_ASIC_HIGH_VISIBILITY | 1 | 45.0/70.0/85.0 | 62.8 | 0 | 0 | 1 | 暫維持，進入逐檔 EPS 查核 |
| IC_DESIGN_IP_ROYALTY | 4 | 45.0/75.0/90.0 | 125.4 | 3 | 3 | 0 | 需下修/拆分或標示動能區 |
| OPTICAL_COMM_SILICON_PHOTONICS | 10 | 36.0/54.0/68.0 | 111.1 | 6 | 6 | 0 | 需下修/拆分或標示動能區 |
| PROBE_AI_ASIC | 3 | 45.0/65.0/75.0 | 153.5 | 3 | 3 | 1 | 需下修/拆分或標示動能區 |
| SEMICAP_COWOS_EQUIPMENT | 11 | 32.0/50.0/65.0 | 66.9 | 7 | 5 | 1 | 需下修/拆分或標示動能區 |
| THERMAL_LIQUID_COOLING | 12 | 34.0/50.0/62.0 | 42.3 | 4 | 3 | 2 | 需下修/拆分或標示動能區 |

## 個股查核表
| code | name | market | taxon | model base/soft/hard | PE | PB | 外資買賣超(張) | 投信買賣超(張) | 三大法人合計(張) | 初判 |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| 3661 | 世芯-KY | 上市 | IC_DESIGN_ASIC_HIGH_VISIBILITY | 45.0/70.0/85.0 | 62.8 | 8.10 | -53 | -110 | -181 | 中性：先維持，需查近期 EPS/法說 |
| 3529 | 力旺 | 上櫃 | IC_DESIGN_IP_ROYALTY | 45.0/75.0/90.0 | 125.4 | 57.80 | 24 | NA | 13 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6531 | 愛普* | 上市 | IC_DESIGN_IP_ROYALTY | 45.0/75.0/90.0 | 102.6 | 13.92 | 1496 | -512 | 934 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6533 | 晶心科 | 上市 | IC_DESIGN_IP_ROYALTY | 45.0/75.0/90.0 | NA | 2.58 | -136 | 0 | -140 | 資料不足：無官方 PE，需用 P/B 或事件模型 |
| 6643 | M31 | 上櫃 | IC_DESIGN_IP_ROYALTY | 45.0/75.0/90.0 | 13900.0 | 12.89 | 20 | NA | 16 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 3081 | 聯亞 | 上櫃 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 348.9 | 57.94 | -129 | NA | -116 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 3163 | 波若威 | 上櫃 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 118.1 | 25.73 | -68 | NA | 154 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 3363 | 上詮 | 上櫃 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | NA | 17.99 | 1418 | NA | 1401 | 資料不足：無官方 PE，需用 P/B 或事件模型 |
| 3450 | 聯鈞 | 上市 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 149.1 | 13.99 | -1679 | 39 | -1696 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 4908 | 前鼎 | 上櫃 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 114.4 | 9.93 | 218 | NA | 212 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 4977 | 眾達-KY | 上市 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 44.5 | 4.13 | 155 | 0 | 76 | 中性：先維持，需查近期 EPS/法說 |
| 4979 | 華星光 | 上櫃 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 107.8 | 20.53 | 198 | NA | 231 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6442 | 光聖 | 上市 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 77.5 | 22.70 | 138 | -73 | 82 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6451 | 訊芯-KY | 上市 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | NA | 10.09 | -354 | 0 | -370 | 資料不足：無官方 PE，需用 P/B 或事件模型 |
| 6530 | 創威 | 上櫃 | OPTICAL_COMM_SILICON_PHOTONICS | 36.0/54.0/68.0 | 51.2 | 7.28 | -10 | NA | -9 | 中性：先維持，需查近期 EPS/法說 |
| 6223 | 旺矽 | 上櫃 | PROBE_AI_ASIC | 45.0/65.0/75.0 | 153.5 | 35.85 | -79 | NA | 24 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6510 | 精測 | 上櫃 | PROBE_AI_ASIC | 45.0/65.0/75.0 | 96.8 | 11.03 | -59 | NA | -288 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6515 | 穎崴 | 上市 | PROBE_AI_ASIC | 45.0/65.0/75.0 | 172.6 | 46.73 | -65 | -14 | -79 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 2467 | 志聖 | 上市 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 77.1 | 10.88 | -721 | 0 | -740 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 3131 | 弘塑 | 上櫃 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 60.0 | 22.96 | 12 | NA | -60 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 3413 | 京鼎 | 上市 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 16.8 | 2.21 | 56 | 0 | 24 | 偏低或景氣/EPS疑慮：需查 EPS 是否在高峰/下修 |
| 3583 | 辛耘 | 上市 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 58.9 | 9.13 | 196 | 0 | 189 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 6187 | 萬潤 | 上櫃 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 74.2 | 15.87 | 87 | NA | 529 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6438 | 迅得 | 上市 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 28.9 | 2.30 | -231 | 0 | -253 | 中性：先維持，需查近期 EPS/法說 |
| 6640 | 均華 | 上櫃 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 73.9 | 10.39 | -5 | NA | -8 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 6664 | 群翊 | 上櫃 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 28.1 | 6.43 | 3 | NA | -9 | 中性：先維持，需查近期 EPS/法說 |
| 6937 | 天虹 | 上市 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 86.9 | 5.53 | -133 | -58 | -214 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 8027 | 鈦昇 | 上櫃 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | NA | 11.24 | -190 | NA | -203 | 資料不足：無官方 PE，需用 P/B 或事件模型 |
| 8064 | 東捷 | 上櫃 | SEMICAP_COWOS_EQUIPMENT | 32.0/50.0/65.0 | 78.7 | 7.09 | -1052 | NA | -1133 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 2421 | 建準 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 19.7 | 4.08 | -491 | -5 | -770 | 偏低或景氣/EPS疑慮：需查 EPS 是否在高峰/下修 |
| 2486 | 一詮 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 548.0 | 12.40 | -831 | 0 | -1018 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 3017 | 奇鋐 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 42.7 | 22.60 | -504 | -193 | -805 | 中性：先維持，需查近期 EPS/法說 |
| 3324 | 雙鴻 | 上櫃 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 32.0 | 7.70 | -342 | NA | -439 | 中性：先維持，需查近期 EPS/法說 |
| 3338 | 泰碩 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 53.8 | 3.34 | -9 | 0 | -11 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 3483 | 力致 | 上櫃 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 25.4 | 2.01 | -879 | NA | -918 | 中性：先維持，需查近期 EPS/法說 |
| 3653 | 健策 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 100.1 | 25.08 | 4 | -0 | -14 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |
| 4543 | 萬在 | 上櫃 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 42.3 | 1.37 | 32 | NA | 31 | 中性：先維持，需查近期 EPS/法說 |
| 6230 | 尼得科超眾 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | NA | 2.07 | -16 | 0 | -16 | 資料不足：無官方 PE，需用 P/B 或事件模型 |
| 6275 | 元山 | 上櫃 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 18.2 | 2.47 | 54 | NA | 27 | 偏低或景氣/EPS疑慮：需查 EPS 是否在高峰/下修 |
| 6591 | 動力-KY | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 13.5 | 1.10 | -144 | 0 | -143 | 偏低或景氣/EPS疑慮：需查 EPS 是否在高峰/下修 |
| 8996 | 高力 | 上市 | THERMAL_LIQUID_COOLING | 34.0/50.0/62.0 | 80.2 | 22.53 | -335 | 374 | 116 | 偏高：官方 PE 高於 hard ceiling，需下修可操作區或標示動能區 |

## 資料源
- TWSE T86：https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date=20260605&selectType=ALL
- TWSE BWIBBU_ALL：https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL
- TPEx 三大法人：https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading
- TPEx 本益比/PB：https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis
