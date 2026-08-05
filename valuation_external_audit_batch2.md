# 外部法人與估值現況查核 - 第二批半導體中游/週期分類

- 資料日期：2026-06-05（最近交易日）
- 查核範圍：75 檔，8 個分類
- 資料來源：TWSE T86 三大法人日報、TWSE BWIBBU_ALL 本益比/PB、TPEx 三大法人 OpenAPI、TPEx 本益比/PB OpenAPI
- 本報告只列查核與建議，不直接改模型參數。

## 分類結論摘要
| taxon | 檔數 | 模型 base/soft/hard | 官方 PE 中位數 | 官方 PB 中位數 | 高於 soft | 高於 hard | 法人同向偏空 | 初步建議 |
|---|---:|---|---:|---:|---:|---:|---:|---|
| COMPOUND_SEMICONDUCTOR_OPTO | 2 | 22.0/34.0/45.0 | 65.0 | 3.54 | 1 | 1 | 1 | 需拆分類或加入 PE 失真/動能區防護 |
| IC_DESIGN_CONSUMER | 18 | 18.0/26.0/32.0 | 21.2 | 2.45 | 5 | 5 | 2 | 需拆分類或加入 PE 失真/動能區防護 |
| IC_DESIGN_PLATFORM_AI_EDGE | 10 | 24.0/38.0/50.0 | 38.3 | 4.78 | 5 | 3 | 0 | 需拆分類或加入 PE 失真/動能區防護 |
| MEMORY_CYCLE | 9 | 12.0/18.0/24.0 | 13.5 | 5.29 | 3 | 3 | 5 | 週期/PB模型優先，補報價與庫存循環 |
| OSAT_TESTING | 12 | 24.0/35.0/42.0 | 34.8 | 3.40 | 5 | 2 | 4 | 需拆分類或加入 PE 失真/動能區防護 |
| POWER_ANALOG_IC | 11 | 22.0/36.0/48.0 | 31.2 | 3.07 | 4 | 3 | 1 | 需拆分類或加入 PE 失真/動能區防護 |
| SEMICONDUCTOR_MATERIALS_CONSUMABLES | 7 | 26.0/38.0/45.0 | 68.8 | 4.45 | 5 | 4 | 0 | 需拆分類或加入 PE 失真/動能區防護 |
| SILICON_WAFER_CYCLE | 6 | 18.0/28.0/36.0 | 263.4 | 3.68 | 4 | 4 | 0 | 週期/PB模型優先，補報價與庫存循環 |

## 個股查核表
| code | name | market | taxon | valuation | model base/soft/hard | PE | PB | 外資(張) | 投信(張) | 合計(張) | 初判 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| 2340 | 台亞 | 上市 | COMPOUND_SEMICONDUCTOR_OPTO | forward_pe_pb_cycle | 22.0/34.0/45.0 | NA | 2.47 | -1013 | 0 | -1146 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 5222 | 全訊 | 上市 | COMPOUND_SEMICONDUCTOR_OPTO | forward_pe_pb_cycle | 22.0/34.0/45.0 | 65.0 | 4.60 | -88 | -1 | -94 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 2363 | 矽統 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 36.8 | 1.58 | 555 | 0 | 494 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 2401 | 凌陽 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | NA | 1.97 | 638 | 0 | 213 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2436 | 偉詮電 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 21.2 | 3.24 | -340 | 0 | -434 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2458 | 義隆 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 17.5 | 4.69 | -9 | -16 | -61 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 3034 | 聯詠 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 20.2 | 4.16 | 349 | -75 | 73 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 3041 | 揚智 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | NA | 2.44 | -366 | 0 | -365 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 3094 | 聯傑 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 122.5 | 2.62 | 32 | 0 | 33 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 3227 | 原相 | 上櫃 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 20.4 | 2.98 | 31 | NA | -46 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 3545 | 敦泰 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | NA | 1.39 | 244 | 0 | 207 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 3592 | 瑞鼎 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 17.0 | 1.91 | -25 | -6 | -29 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 4919 | 新唐 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | NA | 5.65 | 9 | 0 | -112 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 4952 | 凌通 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 44.5 | 2.46 | -92 | 0 | -97 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 4961 | 天鈺 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 20.2 | 1.15 | 56 | 21 | 60 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 5471 | 松翰 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 52.8 | 2.42 | 43 | 0 | 44 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 6202 | 盛群 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 83.3 | 3.14 | -605 | 0 | -646 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 6243 | 迅杰 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | NA | 1.91 | -201 | 0 | -200 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 6962 | 奕力-KY | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 24.7 | 0.87 | -525 | 0 | -565 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 8016 | 矽創 | 上市 | IC_DESIGN_CONSUMER | forward_pe_pb_cycle | 18.0/26.0/32.0 | 19.1 | 3.12 | 609 | 24 | 624 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2379 | 瑞昱 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 23.1 | 7.33 | -2833 | 2817 | -6 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2454 | 聯發科 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 68.5 | 17.59 | 415 | -108 | -51 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 3014 | 聯陽 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 16.4 | 4.07 | 981 | -10 | 965 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 4966 | 譜瑞-KY | 上櫃 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 22.7 | 2.54 | 1049 | NA | 304 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 4968 | 立積 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 38.3 | 3.73 | -188 | 0 | -197 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 5274 | 信驊 | 上櫃 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 148.5 | 111.02 | -41 | NA | -56 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 6526 | 達發 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 38.4 | 6.25 | 21 | 1 | 12 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 6695 | 芯鼎 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | NA | 3.41 | -77 | 0 | -80 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 6756 | 威鋒電子 | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 62.7 | 2.28 | -29 | 0 | -30 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 7749 | 意騰-KY | 上市 | IC_DESIGN_PLATFORM_AI_EDGE | forward_pe_pb_cycle | 24.0/38.0/50.0 | 37.3 | 5.49 | -123 | 0 | -134 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2337 | 旺宏 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | NA | 5.86 | -1238 | -89 | -4153 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 2344 | 華邦電 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 48.1 | 6.25 | -33721 | -9514 | -44929 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 2408 | 南亞科 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 32.2 | 5.78 | -11331 | -332 | -12676 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 2451 | 創見 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 10.4 | 5.29 | -5063 | -1152 | -6323 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 3006 | 晶豪科 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 26.5 | 4.85 | -644 | -1 | -862 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 3135 | 凌航 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 16.1 | 6.26 | -585 | 0 | -584 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 3260 | 威剛 | 上櫃 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 8.4 | 4.85 | -2591 | NA | -3120 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 4967 | 十銓 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 7.1 | 3.34 | -3741 | 0 | -3795 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 8271 | 宇瞻 | 上市 | MEMORY_CYCLE | pb_cycle | 12.0/18.0/24.0 | 10.8 | 4.50 | -2185 | 0 | -2205 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 2329 | 華泰 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 25.5 | 3.24 | -1768 | 0 | -2432 | 中性：先維持，進入分類/財報細查 |
| 2369 | 菱生 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | NA | 2.70 | 227 | 0 | 312 | 資料不足：無官方 PE，需用 PB/事件或 Forward EPS 查核 |
| 2441 | 超豐 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 28.2 | 2.96 | 271 | -363 | -364 | 中性：先維持，進入分類/財報細查 |
| 2449 | 京元電子 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 42.0 | 6.95 | -6619 | -412 | -7537 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 3264 | 欣銓 | 上櫃 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 35.4 | 5.35 | -1440 | NA | -1545 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 3711 | 日月光投控 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 53.6 | 7.22 | -851 | -707 | -1379 | 偏高：官方 PE 高於 hard ceiling，需查 EPS 是否落地或拆分類 |
| 6239 | 力成 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 40.2 | 4.28 | 2688 | -4640 | -4015 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 6257 | 矽格 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 33.3 | 4.94 | -605 | -171 | -894 | 法人同向偏空：倍率需保守檢討 |
| 6525 | 捷敏-KY | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 19.9 | 3.56 | -583 | -10 | -599 | 法人同向偏空：倍率需保守檢討 |
| 8110 | 華東 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 20.7 | 2.31 | 83 | 0 | -57 | 中性：先維持，進入分類/財報細查 |
| 8131 | 福懋科 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 34.8 | 2.42 | -1640 | 0 | -1816 | 中性：先維持，進入分類/財報細查 |
| 8150 | 南茂 | 上市 | OSAT_TESTING | forward_pe | 24.0/35.0/42.0 | 82.0 | 2.75 | 1710 | -12 | 641 | 偏高：官方 PE 高於 hard ceiling，需查 EPS 是否落地或拆分類 |
| 2302 | 麗正 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 42.8 | 3.15 | 240 | 0 | 264 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2434 | 統懋 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | NA | 2.78 | 3 | 0 | 3 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 2481 | 強茂 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 52.4 | 4.35 | 8380 | -3807 | 5361 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 3257 | 虹冠電 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 20.4 | 3.07 | -10 | 0 | -11 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 3588 | 通嘉 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 98.2 | 2.03 | -56 | 0 | -56 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 6415 | 矽力*-KY | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 78.2 | 5.93 | 114 | -56 | 45 | 週期分類：PE 高於 hard，應用 PB/報價循環為主 |
| 6573 | 虹揚-KY | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 12.3 | 2.14 | 104 | 0 | 100 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 6719 | 力智 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 33.2 | 1.76 | -162 | 0 | -147 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 6799 | 來頡 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 26.7 | 2.65 | -28 | 0 | -58 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 8081 | 致新 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 16.0 | 3.32 | 60 | -1 | 56 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 8261 | 富鼎 | 上市 | POWER_ANALOG_IC | forward_pe_pb_cycle | 22.0/36.0/48.0 | 29.3 | 3.32 | -59 | -30 | -151 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 1560 | 中砂 | 上市 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | 68.8 | 12.62 | 23 | 1 | -1 | 偏高：官方 PE 高於 hard ceiling，需查 EPS 是否落地或拆分類 |
| 2338 | 光罩 | 上市 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | NA | 2.78 | -283 | 0 | -585 | 資料不足：無官方 PE，需用 PB/事件或 Forward EPS 查核 |
| 2351 | 順德 | 上市 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | 88.7 | 5.04 | -148 | 4 | -165 | 偏高：官方 PE 高於 hard ceiling，需查 EPS 是否落地或拆分類 |
| 3680 | 家登 | 上櫃 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | 53.2 | 4.45 | -443 | NA | -497 | 偏高：官方 PE 高於 hard ceiling，需查 EPS 是否落地或拆分類 |
| 5285 | 界霖 | 上市 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | 43.7 | 3.15 | -75 | 40 | -39 | 偏熱：官方 PE 高於 soft ceiling，需法人/EPS 支撐 |
| 6552 | 易華電 | 上市 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | NA | 1.63 | -5 | 0 | -11 | 資料不足：無官方 PE，需用 PB/事件或 Forward EPS 查核 |
| 7768 | 頌勝科技 | 上市 | SEMICONDUCTOR_MATERIALS_CONSUMABLES | forward_pe | 26.0/38.0/45.0 | 132.4 | 13.00 | 7 | 0 | 7 | 偏高：官方 PE 高於 hard ceiling，需查 EPS 是否落地或拆分類 |
| 3016 | 嘉晶 | 上市 | SILICON_WAFER_CYCLE | forward_pe_pb_cycle | 18.0/28.0/36.0 | 263.4 | 6.36 | 647 | 0 | 674 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 3532 | 台勝科 | 上市 | SILICON_WAFER_CYCLE | forward_pe_pb_cycle | 18.0/28.0/36.0 | 367.1 | 4.64 | 30 | -1 | 112 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 3686 | 達能 | 上市 | SILICON_WAFER_CYCLE | forward_pe_pb_cycle | 18.0/28.0/36.0 | NA | 1.96 | -109 | 0 | -109 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 5483 | 中美晶 | 上櫃 | SILICON_WAFER_CYCLE | forward_pe_pb_cycle | 18.0/28.0/36.0 | 21.7 | 1.90 | 335 | NA | -3720 | 週期分類：倍率先維持，重點查 PB/庫存/報價 |
| 6182 | 合晶 | 上櫃 | SILICON_WAFER_CYCLE | forward_pe_pb_cycle | 18.0/28.0/36.0 | 2137.5 | 3.21 | -1908 | NA | -1581 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |
| 6488 | 環球晶 | 上櫃 | SILICON_WAFER_CYCLE | forward_pe_pb_cycle | 18.0/28.0/36.0 | 50.0 | 4.15 | -155 | NA | -429 | 週期分類：PB 偏高，避免用低 PE 誤判便宜 |

## 資料源
- TWSE T86：https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date=20260605&selectType=ALL
- TWSE BWIBBU_ALL：https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL
- TPEx 三大法人：https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading
- TPEx 本益比/PB：https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis
