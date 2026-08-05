# 產業估值模型查核底稿

## 摘要
- 股票數：274
- 使用產業分類數：95

## 分類分布與倍率
| taxon | 檔數 | base | soft | hard | valuation | display |
|---|---:|---:|---:|---:|---|---|
| IT_SERVICES_SYSTEM_INTEGRATION | 8 | 18.0 | 26.0 | 32.0 | pe_fcf_dividend | 系統整合 / 資訊服務 |
| CONSUMER_MCU_CONTROL_IC | 7 | 18.0 | 28.0 | 36.0 | forward_pe_pb_cycle | 消費 MCU / 控制 IC |
| NETWORK_EQUIPMENT_STANDARD | 7 | 20.0 | 32.0 | 42.0 | forward_pe_pb_cycle | 一般網通設備 |
| OPTICAL_COMM_CPO_HIGH_VISIBILITY | 7 | 42.0 | 70.0 | 90.0 | forward_pe | 高能見度 CPO / 矽光子 / 800G 光通訊 |
| DISPLAY_DRIVER_IC_CYCLE | 6 | 16.0 | 24.0 | 32.0 | forward_pe_pb_cycle | Display Driver / TDDI / 顯示 IC |
| POWER_MANAGEMENT_IC_DESIGN | 6 | 26.0 | 42.0 | 58.0 | forward_pe_pb_cycle | PMIC / 類比 IC 設計 |
| SEMICAP_ADV_PACKAGING_CORE | 6 | 38.0 | 60.0 | 80.0 | forward_pe | CoWoS / 先進封裝核心設備 |
| SILICON_WAFER_CYCLE | 6 | 18.0 | 28.0 | 36.0 | forward_pe_pb_cycle | 半導體矽晶圓 / 上游材料循環 |
| GENERAL_OSAT_TEST_LEADFRAME | 5 | 18.0 | 28.0 | 38.0 | forward_pe_pb_cycle | 一般成熟封測 / 導線架測試 |
| HIGH_SPEED_CONNECTOR_CORE | 5 | 34.0 | 55.0 | 70.0 | forward_pe | 高速連接器 / 高速線束核心 |
| IC_DESIGN_ASIC | 5 | 35.0 | 55.0 | 70.0 | forward_pe | IC 設計 / ASIC / AI 晶片 |
| MEMORY_MODULE_STORAGE_BRAND | 5 | 12.0 | 20.0 | 28.0 | pe_cashflow_cycle | 記憶體模組 / 工控儲存品牌 |
| OPTICS_MODULE_CYCLE | 5 | 16.0 | 26.0 | 32.0 | forward_pe_pb_cycle | 一般光學模組 / 鏡頭循環 |
| PC_NB_ODM | 5 | 16.0 | 24.0 | 32.0 | pe_cashflow_cycle | PC / NB ODM / EMS 代工 |
| POWER_DISCRETE_COMPONENT_CYCLE | 5 | 18.0 | 30.0 | 42.0 | forward_pe_pb_cycle | 功率離散元件 / MOSFET / 二極體 |
| SEMICAP_GENERAL_EQUIPMENT | 5 | 28.0 | 42.0 | 55.0 | forward_pe_pb_cycle | 一般半導體 / PCB / 自動化設備 |
| TEST_AUTOMATION_EQUIPMENT | 5 | 30.0 | 42.0 | 50.0 | forward_pe | 測試 / AOI / 自動化檢測設備 |
| THERMAL_AIR | 5 | 18.0 | 28.0 | 35.0 | forward_pe | 傳統氣冷 / 風扇 / 常態散熱 |
| FAB_FACILITY_MATERIALS | 4 | 26.0 | 38.0 | 45.0 | pe_fcf | 半導體廠務 / 材料 / 製程耗材 |
| FINANCIAL_BANK_HOLDCO_QUALITY | 4 | 13.0 | 18.0 | 24.0 | pb_roe_dividend | 銀行型金控 / 官股銀行防禦 |
| FOUNDRY_MATURE | 4 | 12.0 | 18.0 | 22.0 | forward_pe_pb_cycle | 成熟晶圓代工 |
| INDUSTRIAL_AUTOMATION_CORE | 4 | 22.0 | 34.0 | 42.0 | forward_pe_pb_cycle | 工業自動化核心元件 |
| MEMORY_MANUFACTURING_CYCLE | 4 | 10.0 | 16.0 | 22.0 | pb_cycle | 記憶體製造 / DRAM / Flash 週期 |
| MEMORY_OSAT_CYCLE | 4 | 16.0 | 26.0 | 35.0 | forward_pe_pb_cycle | 記憶體封測週期 |
| POWER_SUPPLY_STANDARD | 4 | 18.0 | 30.0 | 40.0 | forward_pe_pb_cycle | 一般電源供應器 |
| SEMIMAT_ADVANCED_CONSUMABLES | 4 | 34.0 | 55.0 | 70.0 | forward_pe | 先進製程耗材 / EUV載具 / CMP耗材 |
| THERMAL_AI_COMPONENTS | 4 | 30.0 | 45.0 | 58.0 | forward_pe_pb_cycle | AI 散熱零組件 / 非液冷核心 |
| ABF_SUBSTRATE | 3 | 30.0 | 45.0 | 55.0 | forward_pe | PCB / ABF / 高階載板 |
| AI_SERVER_CHASSIS_CORE | 3 | 30.0 | 45.0 | 58.0 | forward_pe_pb_cycle | AI 機殼 / 伺服器機構件 |
| AI_SERVER_PCB_HIGH_VISIBILITY | 3 | 34.0 | 55.0 | 70.0 | forward_pe | AI Server 高階 PCB |
| CIS_SEMICONDUCTOR_OPTICS | 3 | 28.0 | 40.0 | 50.0 | forward_pe | CIS / 半導體光學 / 影像感測 |
| CONNECTOR_STANDARD | 3 | 18.0 | 30.0 | 40.0 | forward_pe_pb_cycle | 一般連接器 / 線材 |
| DISPLAY_LED_CYCLE | 3 | 10.0 | 16.0 | 22.0 | pb_cycle | 面板 / LED / 光電循環 |
| GRID_EQUIPMENT_CORE | 3 | 24.0 | 36.0 | 45.0 | forward_pe_orders | 重電 / 電網設備核心 |
| HIGH_SPEED_INTERFACE_IC | 3 | 26.0 | 40.0 | 50.0 | forward_pe_pb_cycle | 高速介面 / USB 控制 IC |
| IC_DESIGN_IP_ROYALTY | 3 | 45.0 | 75.0 | 90.0 | forward_pe | IP / 矽智財 / Royalty 授權 |
| IPC_EDGE_AI | 3 | 22.0 | 34.0 | 42.0 | forward_pe | 工業電腦 / IPC / Edge AI |
| LEGACY_CONSUMER_IC_TURNAROUND | 3 | 10.0 | 16.0 | 24.0 | theme_event_pb_guard | Legacy 消費 IC / 轉機型 |
| OPTICAL_COMM_STANDARD | 3 | 30.0 | 45.0 | 58.0 | forward_pe_pb_cycle | 一般光通訊 / 光收發模組 |
| OSAT_AI_HPC_TESTING | 3 | 28.0 | 45.0 | 58.0 | forward_pe | AI/HPC 測試 / 先進封測服務 |
| PASSIVE_COMPONENT_CYCLE | 3 | 14.0 | 22.0 | 30.0 | pb_cycle | 被動元件 / 電容電阻電感 |
| PHARMA_CDMO_PROFIT | 3 | 24.0 | 36.0 | 45.0 | forward_pe_fcf | 獲利型藥廠 / CDMO |
| PROBE_AI_ASIC | 3 | 45.0 | 65.0 | 75.0 | forward_pe | 高階 AI ASIC / CPO 探針卡與測試介面 |
| ROBOTICS_THEME_EVENT | 3 | 12.0 | 20.0 | 28.0 | theme_event | 機器人純題材 / EPS 未落地 |
| SERVER_RAIL_HIGH_VISIBILITY | 3 | 38.0 | 60.0 | 80.0 | forward_pe | 高階滑軌 / 高毛利機構件 |
| SHIPPING_CYCLE | 3 | 8.0 | 14.0 | 20.0 | pb_cycle_freight | 航運 / 空運 / 物流循環 |
| TELECOM_DEFENSIVE | 3 | 16.0 | 22.0 | 26.0 | dividend_pe_pb_defensive | 電信 / 基礎網路 / 高殖利率防禦型 |
| THERMAL_LIQUID_CORE | 3 | 38.0 | 60.0 | 80.0 | forward_pe | 液冷核心 / 高階 AI 散熱 |
| AI_CCL_HIGH_VISIBILITY | 2 | 36.0 | 60.0 | 80.0 | forward_pe | AI Server 高階 CCL / 高速材料 |
| AI_SERVER_BOARD_SYSTEM | 2 | 26.0 | 36.0 | 45.0 | forward_pe | AI 伺服器主板 / 板卡 / 系統品牌 |
| AI_SERVER_ODM | 2 | 24.0 | 34.0 | 42.0 | forward_pe | AI 伺服器 ODM / 組裝 |
| AUTO_PARTS_AM | 2 | 16.0 | 24.0 | 30.0 | pe_cashflow_cycle | 汽車零件 / AM 售後市場 |
| BIOTECH_CELL_THERAPY_BIOSIMILAR | 2 | 18.0 | 28.0 | 35.0 | milestone_revenue_transition | 細胞治療 / 生物相似藥事件型 |
| BIOTECH_NEW_DRUG_EVENT | 2 | 8.0 | 12.0 | 18.0 | milestone_event | 新藥 / 里程碑事件型生技 |
| CLOUD_SECURITY_SERVICES | 2 | 26.0 | 38.0 | 45.0 | pe_fcf_growth | 雲端 / 資安服務 |
| COMPOUND_SEMICONDUCTOR_OPTO | 2 | 22.0 | 34.0 | 45.0 | forward_pe_pb_cycle | 化合物半導體 / RF PA / 光電半導體 |
| CONSUMER_INTERFACE_SENSOR_IC | 2 | 20.0 | 32.0 | 40.0 | forward_pe_pb_cycle | 消費介面 / 感測 IC |
| DATACENTER_POWER_LEADER | 2 | 34.0 | 55.0 | 70.0 | forward_pe | 資料中心電源 / 電源龍頭 |
| EDGE_AI_SENSOR_SOC | 2 | 24.0 | 38.0 | 48.0 | forward_pe_event_guard | Edge AI / 影像音訊 SoC |
| EV_AUTO_ELECTRONICS | 2 | 28.0 | 42.0 | 50.0 | forward_pe | 車用電子 / 電動車零組件 |
| FINANCIAL_LIFE_INSURANCE_HOLDCO | 2 | 11.0 | 16.0 | 22.0 | pb_roe_dividend | 壽險型金控 / 保險金控 |
| IC_DESIGN_ASIC_SERVICE | 2 | 35.0 | 55.0 | 70.0 | forward_pe | ASIC 設計服務 / 客製化晶片設計 |
| MACHINE_TOOL_CYCLE | 2 | 14.0 | 22.0 | 30.0 | pb_cycle_orders | 工具機 / 工業機械循環 |
| OPTICS_LENS_LEADER | 2 | 24.0 | 34.0 | 42.0 | forward_pe_quality | 高階鏡頭龍頭 / 光學品質股 |
| PCB_STANDARD_BOARD | 2 | 22.0 | 35.0 | 45.0 | forward_pe_pb_cycle | 一般 PCB / 伺服器板 |
| PC_BRAND_AI_PC | 2 | 18.0 | 28.0 | 35.0 | pe_cashflow_cycle | PC 品牌 / AI PC / 消費電子品牌 |
| PLATFORM_IC_LEADER | 2 | 28.0 | 42.0 | 55.0 | forward_pe_quality | 平台型 IC 龍頭 |
| RF_CONNECTIVITY_IC | 2 | 22.0 | 34.0 | 45.0 | forward_pe_pb_cycle | RF / Connectivity IC |
| SEMIMAT_POWER_LEADFRAME | 2 | 22.0 | 35.0 | 45.0 | forward_pe_pb_cycle | 導線架 / 功率元件材料 |
| SERVER_CHASSIS_STANDARD | 2 | 18.0 | 30.0 | 40.0 | forward_pe_pb_cycle | 一般伺服器機殼 / 低純度機構件 |
| SPACE_LEO_SATELLITE | 2 | 30.0 | 45.0 | 55.0 | forward_pe_or_event | 太空科技 / 低軌衛星 / 無人載具 |
| SPECIALTY_CHEM_ELECTRONIC_MATERIALS | 2 | 17.0 | 24.0 | 30.0 | pe_pb_cycle_crosscheck | 特用化學 / 電子材料 / PCB材料 |
| WIND_POWER_INFRA | 2 | 18.0 | 28.0 | 34.0 | pe_cashflow_orders | 風電材料 / 風電基建 |
| AI_DATACENTER_SWITCH | 1 | 36.0 | 58.0 | 75.0 | forward_pe | AI Data Center Switch / 高速交換器 |
| AUTO_OEM_CYCLE | 1 | 12.0 | 18.0 | 24.0 | pb_cycle_cashflow | 整車 / 汽車集團 / 車市循環 |
| AUTO_PARTS_EV | 1 | 22.0 | 32.0 | 40.0 | forward_pe_orders | 電動車 / 傳動 / 車用零組件 |
| CCL_STANDARD_CYCLE | 1 | 22.0 | 35.0 | 45.0 | forward_pe_pb_cycle | 一般 CCL / PCB 材料循環 |
| DEFENSE_DRONE_EVENT | 1 | 8.0 | 14.0 | 24.0 | defense_event_pb_guard | 軍工 / 無人機事件型 |
| DISPLAY_COF_MATERIALS | 1 | 18.0 | 30.0 | 40.0 | forward_pe_pb_cycle | COF / 顯示驅動 IC 材料 |
| EMS_PLATFORM_CONTRACT_MANUFACTURING | 1 | 14.0 | 24.0 | 32.0 | forward_pe_pb_cycle | 大型 EMS / 平台型電子製造服務 |
| FOUNDRY_ADVANCED | 1 | 24.0 | 30.0 | 35.0 | forward_pe | 先進晶圓代工 / HPC / AI |
| GREEN_ENERGY_PROJECT_EPC | 1 | 12.0 | 20.0 | 28.0 | project_cashflow_pb_guard | 綠能工程 / 儲能 EPC |
| GRID_ASSET_TURNAROUND | 1 | 10.0 | 16.0 | 24.0 | pb_asset_turnaround | 重電資產 / 轉機型 |
| GRID_TRANSFORMER_HIGH_VISIBILITY | 1 | 30.0 | 45.0 | 60.0 | forward_pe_orders | 高能見度變壓器 / 電網龍頭 |
| IC_DESIGN_ASIC_HIGH_VISIBILITY | 1 | 45.0 | 70.0 | 85.0 | forward_pe | 高能見度 AI ASIC / Custom Silicon |
| IC_DESIGN_SERVER_BMC_HIGH_VISIBILITY | 1 | 42.0 | 70.0 | 90.0 | forward_pe | Server BMC / 高能見度資料中心 IC |
| LEGACY_TECH_REVIEW | 1 | 8.0 | 14.0 | 22.0 | review_only_pb_guard | 舊資料 / 待確認科技股 |
| MEMORY_CONTROLLER_CYCLE | 1 | 24.0 | 35.0 | 45.0 | forward_pe_pb_cycle | NAND 控制 IC / 記憶體控制與模組 |
| MEMORY_IP_AI | 1 | 35.0 | 60.0 | 75.0 | forward_pe_pb_cycle | AI Memory / 記憶體 IP / 高毛利記憶體題材 |
| PHARMA_DEFENSIVE_GENERIC | 1 | 16.0 | 24.0 | 28.0 | pe_dividend_defensive | 成熟製藥 / 防禦型藥廠 |
| PROBE_TEST_INTERFACE | 1 | 34.0 | 50.0 | 60.0 | forward_pe | 探針卡 / 測試介面 / 半導體檢測 |
| RF_MODULE_PACKAGING | 1 | 24.0 | 34.0 | 42.0 | forward_pe | RF / 高頻模組 / 特殊封裝 |
| TURNAROUND_PROBE_TEST_THEME | 1 | None | None | None | theme_event | 轉機 / 虧損探針與測試題材 |
| UPS_POWER_QUALITY | 1 | 28.0 | 42.0 | 55.0 | forward_pe | UPS / 高毛利穩定電源 |
| WAFER_RECLAIM_THINNING | 1 | 26.0 | 40.0 | 50.0 | forward_pe | 晶圓再生 / 晶圓薄化 / 先進封裝周邊 |

## 需優先人工查核類型

### A. 未分類 / 事件 / 題材型
| code | name | taxon | themes |
|---|---|---|---|
| 6589 | 台康生技 | BIOTECH_CELL_THERAPY_BIOSIMILAR | 生物相似藥 / 里程碑 / 事件型 |
| 6712 | 長聖 | BIOTECH_CELL_THERAPY_BIOSIMILAR | 細胞治療 / 再生醫療 / 事件型 |
| 4128 | 中裕 | BIOTECH_NEW_DRUG_EVENT | 新藥 / 里程碑 / 事件型 |
| 4743 | 合一 | BIOTECH_NEW_DRUG_EVENT | 新藥 / 里程碑 / 事件型 |
| 3374 | 精材 | CIS_SEMICONDUCTOR_OPTICS | CIS封裝 / 晶圓級封裝 / 台積電轉投資 / 封測 |
| 3530 | 晶相光 | CIS_SEMICONDUCTOR_OPTICS | CIS / 影像感測 / IC設計 |
| 6789 | 采鈺 | CIS_SEMICONDUCTOR_OPTICS | CIS / 影像感測 / 半導體光學 / 先進封裝 |
| 8033 | 雷虎 | DEFENSE_DRONE_EVENT | 軍工 / 無人機 / 事件驅動 / 題材 |
| 6695 | 芯鼎 | EDGE_AI_SENSOR_SOC | AI影像IC / 影像處理 / Edge AI |
| 7749 | 意騰-KY | EDGE_AI_SENSOR_SOC | AI聲學處理 / Edge AI / AI晶片 |
| 3661 | 世芯-KY | IC_DESIGN_ASIC_HIGH_VISIBILITY | AI ASIC / HPC / 客製化晶片 / 高能見度ASIC |
| 3529 | 力旺 | IC_DESIGN_IP_ROYALTY | 矽智財 / IP授權 / Royalty |
| 6533 | 晶心科 | IC_DESIGN_IP_ROYALTY | RISC-V / IP / Royalty |
| 6643 | M31 | IC_DESIGN_IP_ROYALTY | 矽智財 / IP授權 / Royalty |
| 2363 | 矽統 | LEGACY_CONSUMER_IC_TURNAROUND | 晶片組 / 消費性IC / 轉機題材 |
| 3041 | 揚智 | LEGACY_CONSUMER_IC_TURNAROUND | 多媒體IC / 機上盒晶片 / 轉機題材 |
| 3094 | 聯傑 | LEGACY_CONSUMER_IC_TURNAROUND | 網通IC / 通訊IC / 轉機題材 |
| 8078 | 華寶 | LEGACY_TECH_REVIEW | 待確認 / 舊資料保留 / 低可信度分類 |
| 3081 | 聯亞 | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 光通訊 / CPO / 矽光子 / 高能見度 |
| 3163 | 波若威 | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 光通訊 / AI data center / 800G/CPO題材 / 高能見度 |
| 3363 | 上詮 | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 光通訊 / CPO題材 / 矽光子 |
| 3450 | 聯鈞 | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 光通訊 / CPO題材 / AI data center |
| 4979 | 華星光 | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 光通訊 / AI data center / 800G/CPO題材 |
| 6442 | 光聖 | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 光通訊 / 矽光子 / CPO / AI data center |
| 6451 | 訊芯-KY | OPTICAL_COMM_CPO_HIGH_VISIBILITY | 矽光子 / 封裝 / CPO題材 |
| 2353 | 宏碁 | PC_BRAND_AI_PC | PC品牌 / AI PC |
| 2357 | 華碩 | PC_BRAND_AI_PC | PC品牌 / 主板 / AI PC / 伺服器系統 |
| 2359 | 所羅門 | ROBOTICS_THEME_EVENT | 機器人 / AI視覺 / 題材型 |
| 6125 | 廣運 | ROBOTICS_THEME_EVENT | 自動化 / 物流設備 / 機器人題材 / AI應用 |
| 6188 | 廣明 | ROBOTICS_THEME_EVENT | 機器人題材 / 自動化 / 低毛利硬體 |
| 2467 | 志聖 | SEMICAP_ADV_PACKAGING_CORE | 設備 / PCB設備 / 先進封裝題材 |
| 3131 | 弘塑 | SEMICAP_ADV_PACKAGING_CORE | CoWoS / 濕製程 / 先進封裝設備 |
| 3583 | 辛耘 | SEMICAP_ADV_PACKAGING_CORE | CoWoS / 半導體設備 / 先進封裝 |
| 6187 | 萬潤 | SEMICAP_ADV_PACKAGING_CORE | CoWoS / 設備 / 先進封裝 |
| 6640 | 均華 | SEMICAP_ADV_PACKAGING_CORE | 先進封裝設備 / CoWoS |
| 6937 | 天虹 | SEMICAP_ADV_PACKAGING_CORE | 半導體設備 / 先進封裝 / 設備 |
| 2314 | 台揚 | SPACE_LEO_SATELLITE | 低軌衛星 / 通訊 |
| 3491 | 昇達科 | SPACE_LEO_SATELLITE | 毫米波 / 低軌衛星 |
| 2360 | 致茂 | TEST_AUTOMATION_EQUIPMENT | 測試設備 / 自動化測試 / 電源測試 / AI伺服器測試 |
| 3455 | 由田 | TEST_AUTOMATION_EQUIPMENT | AOI / 檢測設備 / PCB/半導體檢測 / AI伺服器檢測 |
| 5443 | 均豪 | TEST_AUTOMATION_EQUIPMENT | AOI / 設備 / 自動化檢測 / 半導體設備 |
| 7769 | 鴻勁 | TEST_AUTOMATION_EQUIPMENT | 測試設備 / AI晶片測試 / 自動化測試 |
| 7822 | 倍利科 | TEST_AUTOMATION_EQUIPMENT | 半導體檢測 / 設備 / AOI |
| 6217 | 中探針 | TURNAROUND_PROBE_TEST_THEME | 測試針 / 探針 / 車用測試 / 轉機題材 |

### B. P/B 或 P/E 輔助型週期分類
| taxon | 檔數 | base | hard | valuation | 公司 |
|---|---:|---:|---:|---|---|
| ABF_SUBSTRATE | 3 | 30.0 | 55.0 | forward_pe | 3037 欣興、3189 景碩、8046 南電 |
| AI_CCL_HIGH_VISIBILITY | 2 | 36.0 | 80.0 | forward_pe | 2383 台光電、6274 台燿 |
| AI_SERVER_BOARD_SYSTEM | 2 | 26.0 | 45.0 | forward_pe | 2376 技嘉、2377 微星 |
| AI_SERVER_CHASSIS_CORE | 3 | 30.0 | 58.0 | forward_pe_pb_cycle | 3013 晟銘電、3693 營邦、8210 勤誠 |
| AI_SERVER_PCB_HIGH_VISIBILITY | 3 | 34.0 | 70.0 | forward_pe | 2313 華通、2368 金像電、3715 定穎投控 |
| AUTO_OEM_CYCLE | 1 | 12.0 | 24.0 | pb_cycle_cashflow | 2201 裕隆 |
| AUTO_PARTS_AM | 2 | 16.0 | 30.0 | pe_cashflow_cycle | 1319 東陽、1522 堤維西 |
| AUTO_PARTS_EV | 1 | 22.0 | 40.0 | forward_pe_orders | 1536 和大 |
| BIOTECH_CELL_THERAPY_BIOSIMILAR | 2 | 18.0 | 35.0 | milestone_revenue_transition | 6589 台康生技、6712 長聖 |
| BIOTECH_NEW_DRUG_EVENT | 2 | 8.0 | 18.0 | milestone_event | 4128 中裕、4743 合一 |
| CCL_STANDARD_CYCLE | 1 | 22.0 | 45.0 | forward_pe_pb_cycle | 6213 聯茂 |
| CIS_SEMICONDUCTOR_OPTICS | 3 | 28.0 | 50.0 | forward_pe | 3374 精材、3530 晶相光、6789 采鈺 |
| COMPOUND_SEMICONDUCTOR_OPTO | 2 | 22.0 | 45.0 | forward_pe_pb_cycle | 2340 台亞、5222 全訊 |
| CONNECTOR_STANDARD | 3 | 18.0 | 40.0 | forward_pe_pb_cycle | 2392 正崴、3605 宏致、8103 瀚荃 |
| CONSUMER_INTERFACE_SENSOR_IC | 2 | 20.0 | 40.0 | forward_pe_pb_cycle | 2458 義隆、3227 原相 |
| CONSUMER_MCU_CONTROL_IC | 7 | 18.0 | 36.0 | forward_pe_pb_cycle | 2401 凌陽、2436 偉詮電、4919 新唐、4952 凌通、5471 松翰、6202 盛群、6243 迅杰 |
| DEFENSE_DRONE_EVENT | 1 | 8.0 | 24.0 | defense_event_pb_guard | 8033 雷虎 |
| DISPLAY_COF_MATERIALS | 1 | 18.0 | 40.0 | forward_pe_pb_cycle | 6552 易華電 |
| DISPLAY_DRIVER_IC_CYCLE | 6 | 16.0 | 32.0 | forward_pe_pb_cycle | 3034 聯詠、3545 敦泰、3592 瑞鼎、4961 天鈺、6962 奕力-KY、8016 矽創 |
| DISPLAY_LED_CYCLE | 3 | 10.0 | 22.0 | pb_cycle | 2409 友達、3481 群創、3714 富采 |
| EDGE_AI_SENSOR_SOC | 2 | 24.0 | 48.0 | forward_pe_event_guard | 6695 芯鼎、7749 意騰-KY |
| EMS_PLATFORM_CONTRACT_MANUFACTURING | 1 | 14.0 | 32.0 | forward_pe_pb_cycle | 2317 鴻海 |
| FAB_FACILITY_MATERIALS | 4 | 26.0 | 45.0 | pe_fcf | 2404 漢唐、6139 亞翔、6196 帆宣、6909 創控 |
| FINANCIAL_BANK_HOLDCO_QUALITY | 4 | 13.0 | 24.0 | pb_roe_dividend | 2884 玉山金、2886 兆豐金、2891 中信金、2892 第一金 |
| FINANCIAL_LIFE_INSURANCE_HOLDCO | 2 | 11.0 | 22.0 | pb_roe_dividend | 2881 富邦金、2882 國泰金 |
| FOUNDRY_ADVANCED | 1 | 24.0 | 35.0 | forward_pe | 2330 台積電 |
| FOUNDRY_MATURE | 4 | 12.0 | 22.0 | forward_pe_pb_cycle | 2303 聯電、2342 茂矽、5347 世界、6770 力積電 |
| GENERAL_OSAT_TEST_LEADFRAME | 5 | 18.0 | 38.0 | forward_pe_pb_cycle | 2369 菱生、2441 超豐、6257 矽格、6525 捷敏-KY、8150 南茂 |
| GREEN_ENERGY_PROJECT_EPC | 1 | 12.0 | 28.0 | project_cashflow_pb_guard | 6806 森崴能源 |
| GRID_ASSET_TURNAROUND | 1 | 10.0 | 24.0 | pb_asset_turnaround | 2371 大同 |
| GRID_EQUIPMENT_CORE | 3 | 24.0 | 45.0 | forward_pe_orders | 1503 士電、1513 中興電、1514 亞力 |
| GRID_TRANSFORMER_HIGH_VISIBILITY | 1 | 30.0 | 60.0 | forward_pe_orders | 1519 華城 |
| HIGH_SPEED_CONNECTOR_CORE | 5 | 34.0 | 70.0 | forward_pe | 3533 嘉澤、3665 貿聯-KY、6197 佳必琪、6290 良維、6715 嘉基 |
| HIGH_SPEED_INTERFACE_IC | 3 | 26.0 | 50.0 | forward_pe_pb_cycle | 3014 聯陽、4966 譜瑞-KY、6756 威鋒電子 |
| IC_DESIGN_ASIC_HIGH_VISIBILITY | 1 | 45.0 | 85.0 | forward_pe | 3661 世芯-KY |
| IC_DESIGN_IP_ROYALTY | 3 | 45.0 | 90.0 | forward_pe | 3529 力旺、6533 晶心科、6643 M31 |
| INDUSTRIAL_AUTOMATION_CORE | 4 | 22.0 | 42.0 | forward_pe_pb_cycle | 1590 亞德客-KY、2049 上銀、2464 盟立、8374 羅昇 |
| LEGACY_CONSUMER_IC_TURNAROUND | 3 | 10.0 | 24.0 | theme_event_pb_guard | 2363 矽統、3041 揚智、3094 聯傑 |
| LEGACY_TECH_REVIEW | 1 | 8.0 | 22.0 | review_only_pb_guard | 8078 華寶 |
| MACHINE_TOOL_CYCLE | 2 | 14.0 | 30.0 | pb_cycle_orders | 4510 高鋒、4526 東台 |
| MEMORY_CONTROLLER_CYCLE | 1 | 24.0 | 45.0 | forward_pe_pb_cycle | 8299 群聯 |
| MEMORY_IP_AI | 1 | 35.0 | 75.0 | forward_pe_pb_cycle | 6531 愛普* |
| MEMORY_MANUFACTURING_CYCLE | 4 | 10.0 | 22.0 | pb_cycle | 2337 旺宏、2344 華邦電、2408 南亞科、3006 晶豪科 |
| MEMORY_MODULE_STORAGE_BRAND | 5 | 12.0 | 28.0 | pe_cashflow_cycle | 2451 創見、3135 凌航、3260 威剛、4967 十銓、8271 宇瞻 |
| MEMORY_OSAT_CYCLE | 4 | 16.0 | 35.0 | forward_pe_pb_cycle | 2329 華泰、6239 力成、8110 華東、8131 福懋科 |
| NETWORK_EQUIPMENT_STANDARD | 7 | 20.0 | 42.0 | forward_pe_pb_cycle | 3025 星通、3380 明泰、3596 智易、3704 合勤控、4906 正文、5388 中磊、6285 啟碁 |
| OPTICAL_COMM_CPO_HIGH_VISIBILITY | 7 | 42.0 | 90.0 | forward_pe | 3081 聯亞、3163 波若威、3363 上詮、3450 聯鈞、4979 華星光、6442 光聖、6451 訊芯-KY |
| OPTICAL_COMM_STANDARD | 3 | 30.0 | 58.0 | forward_pe_pb_cycle | 4908 前鼎、4977 眾達-KY、6530 創威 |
| OPTICS_LENS_LEADER | 2 | 24.0 | 42.0 | forward_pe_quality | 3008 大立光、3406 玉晶光 |
| OPTICS_MODULE_CYCLE | 5 | 16.0 | 32.0 | forward_pe_pb_cycle | 3019 亞光、3362 先進光、3630 新鉅科、4976 佳凌、6209 今國光 |
| OSAT_AI_HPC_TESTING | 3 | 28.0 | 58.0 | forward_pe | 2449 京元電子、3264 欣銓、3711 日月光投控 |
| PASSIVE_COMPONENT_CYCLE | 3 | 14.0 | 30.0 | pb_cycle | 2327 國巨、2492 華新科、3026 禾伸堂 |
| PCB_STANDARD_BOARD | 2 | 22.0 | 45.0 | forward_pe_pb_cycle | 2367 燿華、3044 健鼎 |
| PC_BRAND_AI_PC | 2 | 18.0 | 35.0 | pe_cashflow_cycle | 2353 宏碁、2357 華碩 |
| PC_NB_ODM | 5 | 16.0 | 32.0 | pe_cashflow_cycle | 2324 仁寶、2356 英業達、2382 廣達、3231 緯創、4938 和碩 |
| PLATFORM_IC_LEADER | 2 | 28.0 | 55.0 | forward_pe_quality | 2379 瑞昱、2454 聯發科 |
| POWER_DISCRETE_COMPONENT_CYCLE | 5 | 18.0 | 42.0 | forward_pe_pb_cycle | 2302 麗正、2434 統懋、2481 強茂、6573 虹揚-KY、8261 富鼎 |
| POWER_MANAGEMENT_IC_DESIGN | 6 | 26.0 | 58.0 | forward_pe_pb_cycle | 3257 虹冠電、3588 通嘉、6415 矽力*-KY、6719 力智、6799 來頡、8081 致新 |
| POWER_SUPPLY_STANDARD | 4 | 18.0 | 40.0 | forward_pe_pb_cycle | 3015 全漢、3078 僑威、6282 康舒、6412 群電 |
| RF_CONNECTIVITY_IC | 2 | 22.0 | 45.0 | forward_pe_pb_cycle | 4968 立積、6526 達發 |
| RF_MODULE_PACKAGING | 1 | 24.0 | 42.0 | forward_pe | 6271 同欣電 |
| ROBOTICS_THEME_EVENT | 3 | 12.0 | 28.0 | theme_event | 2359 所羅門、6125 廣運、6188 廣明 |
| SEMICAP_ADV_PACKAGING_CORE | 6 | 38.0 | 80.0 | forward_pe | 2467 志聖、3131 弘塑、3583 辛耘、6187 萬潤、6640 均華、6937 天虹 |
| SEMICAP_GENERAL_EQUIPMENT | 5 | 28.0 | 55.0 | forward_pe_pb_cycle | 3413 京鼎、6438 迅得、6664 群翊、8027 鈦昇、8064 東捷 |
| SEMIMAT_ADVANCED_CONSUMABLES | 4 | 34.0 | 70.0 | forward_pe | 1560 中砂、2338 光罩、3680 家登、7768 頌勝科技 |
| SEMIMAT_POWER_LEADFRAME | 2 | 22.0 | 45.0 | forward_pe_pb_cycle | 2351 順德、5285 界霖 |
| SERVER_CHASSIS_STANDARD | 2 | 18.0 | 40.0 | forward_pe_pb_cycle | 5426 振發、6117 迎廣 |
| SHIPPING_CYCLE | 3 | 8.0 | 20.0 | pb_cycle_freight | 2603 長榮、2609 陽明、2615 萬海 |
| SILICON_WAFER_CYCLE | 6 | 18.0 | 36.0 | forward_pe_pb_cycle | 3016 嘉晶、3532 台勝科、3686 達能、5483 中美晶、6182 合晶、6488 環球晶 |
| SPACE_LEO_SATELLITE | 2 | 30.0 | 55.0 | forward_pe_or_event | 2314 台揚、3491 昇達科 |
| SPECIALTY_CHEM_ELECTRONIC_MATERIALS | 2 | 17.0 | 30.0 | pe_pb_cycle_crosscheck | 1717 長興、8039 台虹 |
| TELECOM_DEFENSIVE | 3 | 16.0 | 26.0 | dividend_pe_pb_defensive | 2412 中華電、3045 台灣大、4904 遠傳 |
| TEST_AUTOMATION_EQUIPMENT | 5 | 30.0 | 50.0 | forward_pe | 2360 致茂、3455 由田、5443 均豪、7769 鴻勁、7822 倍利科 |
| THERMAL_AIR | 5 | 18.0 | 35.0 | forward_pe | 2421 建準、2486 一詮、6230 尼得科超眾、6275 元山、6591 動力-KY |
| THERMAL_AI_COMPONENTS | 4 | 30.0 | 58.0 | forward_pe_pb_cycle | 3324 雙鴻、3338 泰碩、3483 力致、4543 萬在 |
| TURNAROUND_PROBE_TEST_THEME | 1 | None | None | theme_event | 6217 中探針 |
| WAFER_RECLAIM_THINNING | 1 | 26.0 | 50.0 | forward_pe | 8028 昇陽半導體 |
| WIND_POWER_INFRA | 2 | 18.0 | 34.0 | pe_cashflow_orders | 3708 上緯投控、9958 世紀鋼 |
