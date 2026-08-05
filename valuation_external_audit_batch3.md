# 外部法人與估值現況查核 - 第三批 AI伺服器/電子零組件主鏈

- 資料日期：2026-06-05（最近交易日）
- 查核範圍：55 檔，12 個分類
- 資料來源：TWSE T86 三大法人日報、TWSE BWIBBU_ALL 本益比/PB、TPEx 三大法人 OpenAPI、TPEx 本益比/PB OpenAPI
- 本報告只列查核與建議，不直接改模型參數。

## 分類結論摘要
| taxon | 檔數 | 模型 base/soft/hard | 官方 PE 中位數 | 官方 PB 中位數 | 高於 soft | 高於 hard | 法人同向偏空 | 初步建議 |
|---|---:|---|---:|---:|---:|---:|---:|---|
| ABF_SUBSTRATE | 3 | 30.0/45.0/55.0 | 179.0 | 11.69 | 3 | 3 | 1 | 需拆分類或加入動能區防護 |
| AI_SERVER_BOARD_SYSTEM | 2 | 26.0/36.0/45.0 | 16.0 | 3.00 | 0 | 0 | 0 | 暫維持，進入個股純度查核 |
| AI_SERVER_ODM | 2 | 24.0/34.0/42.0 | 18.3 | 4.67 | 0 | 0 | 0 | 暫維持，進入個股純度查核 |
| CCL_HIGH_SPEED_MATERIALS | 3 | 24.0/35.0/42.0 | 106.0 | 25.74 | 3 | 3 | 0 | 需拆分類或加入動能區防護 |
| CONNECTOR_CABLE | 8 | 30.0/45.0/55.0 | 33.2 | 7.10 | 1 | 1 | 0 | 分類過寬，需拆高能見度與一般零組件 |
| EMS_PLATFORM_CONTRACT_MANUFACTURING | 1 | 14.0/24.0/32.0 | 20.2 | 2.24 | 0 | 0 | 0 | AI純度差異大，建議用 hybrid/權重分層 |
| IPC_EDGE_AI | 3 | 22.0/34.0/42.0 | 17.8 | 2.30 | 1 | 0 | 0 | 偏熱，需查 EPS/訂單能見度 |
| NETWORK_SWITCH | 8 | 28.0/42.0/52.0 | 31.9 | 2.45 | 2 | 0 | 0 | 偏熱，需查 EPS/訂單能見度 |
| PC_NB_ODM | 5 | 16.0/24.0/32.0 | 22.3 | 2.86 | 2 | 0 | 0 | AI純度差異大，建議用 hybrid/權重分層 |
| POWER_BBU | 7 | 26.0/38.0/46.0 | 33.8 | 2.71 | 2 | 2 | 1 | 分類過寬，需拆高能見度與一般零組件 |
| SERVER_CHASSIS_RAIL | 8 | 26.0/38.0/45.0 | 49.7 | 8.74 | 6 | 5 | 1 | 分類過寬，需拆高能見度與一般零組件 |
| SERVER_PCB_BOARD | 5 | 28.0/42.0/52.0 | 52.5 | 4.49 | 3 | 2 | 0 | 需拆分類或加入動能區防護 |

## 個股查核表
| code | name | market | taxon | valuation | model base/soft/hard | PE | PB | 外資(張) | 投信(張) | 合計(張) | 初判 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| 3037 | 欣興 | 上市 | ABF_SUBSTRATE | forward_pe | 30.0/45.0/55.0 | 137.2 | 13.07 | -834 | -1480 | -2533 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 3189 | 景碩 | 上市 | ABF_SUBSTRATE | forward_pe | 30.0/45.0/55.0 | 200.6 | 8.69 | 2328 | -517 | 1003 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 8046 | 南電 | 上市 | ABF_SUBSTRATE | forward_pe | 30.0/45.0/55.0 | 179.0 | 11.69 | 1571 | -2475 | -911 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 2376 | 技嘉 | 上市 | AI_SERVER_BOARD_SYSTEM | forward_pe | 26.0/36.0/45.0 | 17.2 | 3.83 | 5346 | -768 | 4452 | 中性：先維持，進入分類/純度細查 |
| 2377 | 微星 | 上市 | AI_SERVER_BOARD_SYSTEM | forward_pe | 26.0/36.0/45.0 | 14.8 | 2.18 | -643 | 22 | -827 | 偏低：可能景氣/毛利疑慮或模型倍率偏高 |
| 3706 | 神達 | 上市 | AI_SERVER_ODM | forward_pe | 24.0/34.0/42.0 | 17.6 | 1.85 | 516 | -18 | -1227 | 中性：先維持，進入分類/純度細查 |
| 6669 | 緯穎 | 上市 | AI_SERVER_ODM | forward_pe | 24.0/34.0/42.0 | 19.0 | 7.50 | -138 | 58 | -83 | 中性：先維持，進入分類/純度細查 |
| 2383 | 台光電 | 上市 | CCL_HIGH_SPEED_MATERIALS | forward_pe_pb_cycle | 24.0/35.0/42.0 | 106.0 | 36.51 | 18 | 105 | 105 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 6213 | 聯茂 | 上市 | CCL_HIGH_SPEED_MATERIALS | forward_pe_pb_cycle | 24.0/35.0/42.0 | 62.2 | 4.39 | 435 | 0 | 51 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 6274 | 台燿 | 上櫃 | CCL_HIGH_SPEED_MATERIALS | forward_pe_pb_cycle | 24.0/35.0/42.0 | 116.3 | 25.74 | -382 | NA | -419 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 2392 | 正崴 | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | NA | 0.85 | 86 | -1 | 72 | 資料不足：無官方 PE，需用 PB/Forward EPS/訂單能見度查核 |
| 3533 | 嘉澤 | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 33.2 | 6.33 | 578 | -174 | 371 | 中性：先維持，進入分類/純度細查 |
| 3605 | 宏致 | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 21.7 | 1.54 | 204 | 0 | 145 | 中性：先維持，進入分類/純度細查 |
| 3665 | 貿聯-KY | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 44.4 | 9.20 | 141 | 188 | 311 | PB 偏高：需查 AI 純度、毛利率與訂單能見度 |
| 6197 | 佳必琪 | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 31.7 | 8.69 | 340 | 0 | 228 | PB 偏高：需查 AI 純度、毛利率與訂單能見度 |
| 6290 | 良維 | 上櫃 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 40.9 | 7.87 | 247 | NA | 100 | 中性：先維持，進入分類/純度細查 |
| 6715 | 嘉基 | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 205.7 | 7.97 | -10 | 0 | -11 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 8103 | 瀚荃 | 上市 | CONNECTOR_CABLE | forward_pe | 30.0/45.0/55.0 | 21.8 | 2.04 | -53 | 0 | -56 | 中性：先維持，進入分類/純度細查 |
| 2317 | 鴻海 | 上市 | EMS_PLATFORM_CONTRACT_MANUFACTURING | forward_pe_pb_cycle | 14.0/24.0/32.0 | 20.2 | 2.24 | -3319 | 263 | -5379 | 中性：先維持，進入分類/純度細查 |
| 2395 | 研華 | 上市 | IPC_EDGE_AI | forward_pe | 22.0/34.0/42.0 | 38.5 | 8.68 | -885 | 5 | -927 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 6414 | 樺漢 | 上市 | IPC_EDGE_AI | forward_pe | 22.0/34.0/42.0 | 17.8 | 2.13 | 111 | -17 | -15 | 中性：先維持，進入分類/純度細查 |
| 8114 | 振樺電 | 上市 | IPC_EDGE_AI | forward_pe | 22.0/34.0/42.0 | 15.3 | 2.30 | 253 | 0 | 240 | 中性：先維持，進入分類/純度細查 |
| 2345 | 智邦 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | 47.1 | 21.31 | -230 | 191 | -141 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 3025 | 星通 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | 17.6 | 4.35 | -123 | 0 | -121 | 偏低：可能景氣/毛利疑慮或模型倍率偏高 |
| 3380 | 明泰 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | NA | 2.23 | 417 | -1 | 374 | 資料不足：無官方 PE，需用 PB/Forward EPS/訂單能見度查核 |
| 3596 | 智易 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | 15.1 | 2.67 | 654 | 0 | 660 | 偏低：可能景氣/毛利疑慮或模型倍率偏高 |
| 3704 | 合勤控 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | 41.5 | 1.65 | 286 | 0 | 280 | 中性：先維持，進入分類/純度細查 |
| 4906 | 正文 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | NA | 1.90 | 1964 | 0 | 1563 | 資料不足：無官方 PE，需用 PB/Forward EPS/訂單能見度查核 |
| 5388 | 中磊 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | 22.4 | 1.71 | 120 | 0 | 11 | 中性：先維持，進入分類/純度細查 |
| 6285 | 啟碁 | 上市 | NETWORK_SWITCH | forward_pe | 28.0/42.0/52.0 | 43.1 | 4.04 | 518 | 51 | 447 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 2324 | 仁寶 | 上市 | PC_NB_ODM | pe_cashflow_cycle | 16.0/24.0/32.0 | 31.1 | 1.38 | -996 | 50 | -712 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 2356 | 英業達 | 上市 | PC_NB_ODM | pe_cashflow_cycle | 16.0/24.0/32.0 | 29.2 | 3.75 | 9678 | -96 | 8363 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 2382 | 廣達 | 上市 | PC_NB_ODM | pe_cashflow_cycle | 16.0/24.0/32.0 | 19.6 | 7.25 | -21411 | 19825 | -1496 | 中性：先維持，進入分類/純度細查 |
| 3231 | 緯創 | 上市 | PC_NB_ODM | pe_cashflow_cycle | 16.0/24.0/32.0 | 17.1 | 2.86 | 4080 | 138 | 3708 | 中性：先維持，進入分類/純度細查 |
| 4938 | 和碩 | 上市 | PC_NB_ODM | pe_cashflow_cycle | 16.0/24.0/32.0 | 22.3 | 1.28 | -14168 | 14532 | -197 | 中性：先維持，進入分類/純度細查 |
| 2301 | 光寶科 | 上市 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 33.8 | 5.92 | 651 | 72 | 282 | 中性：先維持，進入分類/純度細查 |
| 2308 | 台達電 | 上市 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 84.8 | 19.94 | -2361 | -66 | -2372 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 3015 | 全漢 | 上市 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 33.9 | 1.09 | -755 | 26 | -576 | 中性：先維持，進入分類/純度細查 |
| 3078 | 僑威 | 上櫃 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 11.7 | 1.94 | -269 | NA | -282 | 偏低：可能景氣/毛利疑慮或模型倍率偏高 |
| 6282 | 康舒 | 上市 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 127.6 | 2.43 | -31907 | 121 | -34980 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 6409 | 旭隼 | 上市 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 26.6 | 7.88 | 401 | -1 | 404 | 中性：先維持，進入分類/純度細查 |
| 6412 | 群電 | 上市 | POWER_BBU | forward_pe | 26.0/38.0/46.0 | 18.8 | 2.71 | 810 | -2283 | -1547 | 中性：先維持，進入分類/純度細查 |
| 2059 | 川湖 | 上市 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 49.5 | 16.99 | -192 | -6 | -183 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 3013 | 晟銘電 | 上市 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 26.8 | 4.55 | 111 | 0 | -104 | 中性：先維持，進入分類/純度細查 |
| 3693 | 營邦 | 上櫃 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 66.1 | 4.62 | -31 | NA | -30 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 5426 | 振發 | 上櫃 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 76.8 | 1.86 | 465 | NA | 197 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 6117 | 迎廣 | 上市 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 18.0 | 3.26 | 82 | 0 | 52 | 中性：先維持，進入分類/純度細查 |
| 6584 | 南俊國際 | 上櫃 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 85.1 | 12.87 | -111 | NA | -117 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 6805 | 富世達 | 上市 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 49.8 | 18.01 | -219 | 89 | -128 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 8210 | 勤誠 | 上市 | SERVER_CHASSIS_RAIL | forward_pe | 26.0/38.0/45.0 | 40.6 | 13.61 | -498 | 15 | -513 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 2313 | 華通 | 上市 | SERVER_PCB_BOARD | forward_pe | 28.0/42.0/52.0 | 45.7 | 6.59 | -11629 | 46 | -11894 | 偏熱：官方 PE 高於 soft ceiling，需 EPS/訂單支撐 |
| 2367 | 燿華 | 上市 | SERVER_PCB_BOARD | forward_pe | 28.0/42.0/52.0 | NA | 3.51 | -2697 | 0 | -4093 | 資料不足：無官方 PE，需用 PB/Forward EPS/訂單能見度查核 |
| 2368 | 金像電 | 上市 | SERVER_PCB_BOARD | forward_pe | 28.0/42.0/52.0 | 59.4 | 19.28 | 306 | -186 | 140 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |
| 3044 | 健鼎 | 上市 | SERVER_PCB_BOARD | forward_pe | 28.0/42.0/52.0 | 24.2 | 4.49 | -638 | 333 | -319 | 中性：先維持，進入分類/純度細查 |
| 3715 | 定穎投控 | 上市 | SERVER_PCB_BOARD | forward_pe | 28.0/42.0/52.0 | 175.3 | 4.48 | -170 | 0 | -199 | 偏高：官方 PE 高於 hard ceiling，需拆分類或標示動能區 |

## 資料源
- TWSE T86：https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date=20260605&selectType=ALL
- TWSE BWIBBU_ALL：https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL
- TPEx 三大法人：https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading
- TPEx 本益比/PB：https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis
