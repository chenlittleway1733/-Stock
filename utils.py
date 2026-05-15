"""
共用常數、格式化工具、自選股與 Streamlit Session State 管理。
由原始 app(1).py 拆分而來。
"""
import os
import re
import math
import datetime
import pandas as pd
import streamlit as st

# --- 產業對照表 ---
SECTOR_MAP = {
    "Technology": "科技產業", "Semiconductors": "半導體業", "Consumer Electronics": "消費性電子",
    "Electronic Components": "電子零組件", "Computer Hardware": "電腦及週邊設備",
    "Communication Equipment": "通信網路業", "Software—Infrastructure": "軟體服務業",
    "Financials": "金融保險業", "Banks—Regional": "銀行業", "Life Insurance": "人壽保險",
    "Industrials": "工業", "Marine Shipping": "航運業", "Airlines": "航空業",
    "Auto Parts": "汽車零組件", "Healthcare": "生技醫療業", "Real Estate": "建材營造業",
    "Basic Materials": "原物料/塑化", "Energy": "能源產業", "Utilities": "公用事業"
}

# ==========================================
# 1. 全局安全轉換與排版函數
# ==========================================
def s_float(val, default=None):
    try:
        if val is None: return default
        v = float(val)
        if math.isnan(v) or math.isinf(v): return default
        return v
    except:
        return default

def to_pct(val):
    try:
        if val is None or pd.isna(val): return "N/A"
        return f"{val * 100:.2f}%"
    except:
        return "N/A"

def to_val_str(v, fmt="pct"):
    if v is None or pd.isna(v): return "N/A"
    if fmt == "pct": return f"{v * 100:.2f}%"
    if fmt == "x": return f"{v:.1f}x"
    return f"{v:.2f}"

def p_fmt(orig, ai_val, fmt="pct", suffix="AI捉取"):
    s = to_val_str(orig, fmt)
    if ai_val is not None and not pd.isna(ai_val):
        s += f" ({to_val_str(float(ai_val), fmt)}, {suffix})"
    return s

def p_dual(o1, o2, a1, a2, suffix="AI捉取"):
    s = f"{to_val_str(o1, 'num')} / {to_val_str(o2, 'num')}"
    if (a1 is not None and not pd.isna(a1)) or (a2 is not None and not pd.isna(a2)):
        sa1 = to_val_str(float(a1) if a1 is not None else None, 'num')
        sa2 = to_val_str(float(a2) if a2 is not None else None, 'num')
        s += f" ({sa1} / {sa2}, {suffix})"
    return s

def build_cmp_str(orig, ai_val, fmt="pct", suffix="AI推估", show_ai_missing=False, period=""):
    s = to_val_str(orig, fmt)
    if ai_val is not None and not pd.isna(ai_val):
        ai_text = to_val_str(float(ai_val), fmt)
    elif show_ai_missing:
        ai_text = "AI找不到數據"
    else:
        return s
    
    time_str = f", {period}" if period else ""
    s += f"<br><span style='color:#FFD700; font-size:0.85rem;'>({suffix}: {ai_text}{time_str})</span>"
    return s

def build_cmp_dual_str(o1, o2, a1, a2, fmt1="num", fmt2="num", suffix="AI推估", show_ai_missing=False, period=""):
    s1 = to_val_str(o1, fmt1)
    s2 = to_val_str(o2, fmt2)
    s = f"{s1} / <span style='color:#00bfff;'>{s2}</span>" if (fmt1=="num" and fmt2=="num") else f"{s1} / {s2}"
    has_ai = ((a1 is not None and not pd.isna(a1)) or (a2 is not None and not pd.isna(a2)))
    if not has_ai and not show_ai_missing:
        return s
    sa1 = to_val_str(float(a1) if a1 is not None and not pd.isna(a1) else None, fmt1)
    sa2 = to_val_str(float(a2) if a2 is not None and not pd.isna(a2) else None, fmt2)
    if sa1 == "N/A":
        sa1 = "AI找不到數據"
    if sa2 == "N/A":
        sa2 = "AI找不到數據"
        
    time_str = f", {period}" if period else ""
    s += f"<br><span style='color:#FFD700; font-size:0.85rem;'>({suffix}: {sa1} / {sa2}{time_str})</span>"
    return s

def clean_html(html_str):
    return re.sub(r'[\r\n\t]+', ' ', html_str).strip()


# ==========================================
# 1.1 財務資料合理性校驗 / 欄位錯位防呆
# ==========================================
def normalize_financial_ratio(val, default=None):
    """將百分比欄位統一成小數格式：31.5 -> 0.315；0.315 -> 0.315。"""
    v = s_float(val, default)
    if v is None:
        return default
    # Yahoo / AI / 不同 API 有時會把百分比以 31.5 而非 0.315 回傳
    if abs(v) > 1.5 and abs(v) <= 100:
        return v / 100.0
    return v


def validate_and_correct_financial_metrics(system_vals, ai_vals=None, monthly_rev_df=None, stock_id="", stock_name=""):
    """
    財務資料品質閘門：
    1) 營益率不可高於毛利率；
    2) 最新單月 YoY 優先採用月營收資料，不直接吃 yfinance revenueGrowth；
    3) D/E 若疑似單位錯置或與 AI/財報校對差距過大，先剔除系統值；
    4) AI 交叉校對值也必須通過合理區間，否則設為 NULL，避免幻覺進入估值模型。

    回傳：corrected_system, normalized_ai, warnings
    """
    ai_vals = ai_vals or {}
    corrected = dict(system_vals or {})
    ai_norm = dict(ai_vals or {})
    warnings = []
    label = f"{stock_name} ({stock_id})" if stock_name and stock_id else (stock_name or stock_id or "目前標的")

    # 統一百分比欄位尺度
    for key in ["gross_margin", "operating_margin", "rev_growth", "debt_to_equity"]:
        corrected[key] = normalize_financial_ratio(corrected.get(key))
        ai_norm[key] = normalize_financial_ratio(ai_norm.get(key))

    def is_reasonable_ratio(v, lo=-1.0, hi=1.0):
        return v is None or (lo <= v <= hi)

    def margin_pair_is_valid(gm, om):
        if not is_reasonable_ratio(gm, -1.0, 1.0) or not is_reasonable_ratio(om, -1.0, 1.0):
            return False
        if gm is None or om is None:
            return True
        # 營益率理論上不得高於毛利率；0.3% 容許極小四捨五入誤差
        return om <= gm + 0.003

    sys_gm = corrected.get("gross_margin")
    sys_om = corrected.get("operating_margin")
    ai_gm = ai_norm.get("gross_margin")
    ai_om = ai_norm.get("operating_margin")

    if not margin_pair_is_valid(sys_gm, sys_om):
        warnings.append(
            f"{label} 的毛利率/營益率校驗失敗：系統值 {to_val_str(sys_gm, 'pct')} / {to_val_str(sys_om, 'pct')} 不合理，已排除系統毛利率與營益率。"
        )
        corrected["gross_margin"] = None
        corrected["operating_margin"] = None

    if not margin_pair_is_valid(ai_gm, ai_om):
        warnings.append(
            f"{label} 的 AI 毛利率/營益率也未通過校驗：{to_val_str(ai_gm, 'pct')} / {to_val_str(ai_om, 'pct')}，已設為 NULL，避免 AI 幻覺進入估值。"
        )
        ai_norm["gross_margin"] = None
        ai_norm["operating_margin"] = None

    # 最新單月 YoY：優先用月營收表，不用 yfinance info 的 revenueGrowth 當月 YoY
    try:
        if monthly_rev_df is not None and not monthly_rev_df.empty and "YoY" in monthly_rev_df.columns:
            monthly_yoy_pct = s_float(monthly_rev_df["YoY"].iloc[-1])
            monthly_yoy = monthly_yoy_pct / 100.0 if monthly_yoy_pct is not None else None
            if monthly_yoy is not None and -1.0 <= monthly_yoy <= 10.0:
                old_sys_yoy = corrected.get("rev_growth")
                if old_sys_yoy is not None and abs(old_sys_yoy - monthly_yoy) >= 0.10:
                    warnings.append(
                        f"{label} 的營收 YoY 已改用月營收資料：原 yfinance revenueGrowth={to_val_str(old_sys_yoy, 'pct')}，月營收 YoY={to_val_str(monthly_yoy, 'pct')}。"
                    )
                corrected["rev_growth"] = monthly_yoy
    except Exception:
        pass

    # AI YoY 也做合理範圍防呆；極端值多半是抓到錯欄或摘要幻覺
    ai_yoy = ai_norm.get("rev_growth")
    if ai_yoy is not None and not (-1.0 <= ai_yoy <= 10.0):
        warnings.append(
            f"{label} 的 AI 營收 YoY={to_val_str(ai_yoy, 'pct')} 超出合理範圍，已設為 NULL。"
        )
        ai_norm["rev_growth"] = None

    # D/E：系統值與 AI 值雙層防呆。D/E > 800% 直接視為高風險異常值，不進估值模型。
    def debt_to_equity_is_valid(v):
        return v is None or (0 <= v <= 8.0)

    sys_de = corrected.get("debt_to_equity")
    ai_de = ai_norm.get("debt_to_equity")

    if not debt_to_equity_is_valid(ai_de):
        warnings.append(
            f"{label} 的 AI D/E={to_val_str(ai_de, 'pct')} 超出 800% 安全上限，已設為 NULL，避免 AI 幻覺污染模型。"
        )
        ai_norm["debt_to_equity"] = None
        ai_de = None

    if sys_de is not None:
        if not debt_to_equity_is_valid(sys_de):
            warnings.append(f"{label} 的 D/E 系統值 {to_val_str(sys_de, 'pct')} 超出合理範圍，已排除。")
            corrected["debt_to_equity"] = None
        elif ai_de is not None:
            # 例如系統 0.76% vs AI 31.53%，極可能是單位或欄位錯位
            if sys_de < 0.02 and ai_de >= 0.10:
                warnings.append(
                    f"{label} 的 D/E 疑似單位/欄位錯位：系統 {to_val_str(sys_de, 'pct')} vs AI {to_val_str(ai_de, 'pct')}，已排除系統 D/E。"
                )
                corrected["debt_to_equity"] = None
            elif abs(sys_de - ai_de) >= max(0.15, abs(ai_de) * 0.80):
                warnings.append(
                    f"{label} 的 D/E 與交叉校對差距過大：系統 {to_val_str(sys_de, 'pct')} vs AI {to_val_str(ai_de, 'pct')}，已排除系統 D/E。"
                )
                corrected["debt_to_equity"] = None

    # 最終防線：系統值被排除時，如果 AI 也不可用，後續 eff_de 會自然維持 None/NULL。
    return corrected, ai_norm, warnings

def get_watchlist():
    watchlist = []
    if os.path.exists("stocklist.txt"):
        try:
            with open("stocklist.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if "," in line: watchlist.append(line.split(",")[0].strip())
        except: pass
    return watchlist

def load_stocklist_structure():
    """解析 stocklist.txt 為 (分類順序, 分類->[(code,name)], 錯誤訊息)。"""
    cat_order = []
    cat_map = {}
    errors = []
    current_cat = None

    if not os.path.exists("stocklist.txt"):
        return [], {}, []

    try:
        with open("stocklist.txt", "r", encoding="utf-8") as f:
            for ln, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                if "," in line:
                    parts = [p.strip() for p in line.split(",", 1)]
                    if len(parts) != 2 or not parts[0] or not parts[1]:
                        errors.append(f"第 {ln} 行格式錯誤：{line}")
                        continue
                    if current_cat is None:
                        current_cat = "未分類"
                        cat_order.append(current_cat)
                        cat_map[current_cat] = []
                    cat_map[current_cat].append((parts[0], parts[1]))
                else:
                    current_cat = line
                    if current_cat not in cat_map:
                        cat_order.append(current_cat)
                        cat_map[current_cat] = []
    except Exception as e:
        errors.append(f"讀取失敗：{str(e)}")

    return cat_order, cat_map, errors

def save_stocklist_structure(cat_order, cat_map):
    lines = []
    for cat in cat_order:
        lines.append(f"{cat}\n")
        for code, name in cat_map.get(cat, []):
            lines.append(f"{code},{name}\n")
        lines.append("\n")
    with open("stocklist.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)

def validate_stocklist_structure(cat_order, cat_map):
    issues = []
    seen = set()
    for cat in cat_order:
        if not cat or "," in cat:
            issues.append(f"分類名稱不合法：{cat}")
        for code, name in cat_map.get(cat, []):
            if not code.isdigit():
                issues.append(f"代號非純數字：{code} ({name})")
            if code in seen:
                issues.append(f"重複代號：{code}")
            seen.add(code)
    return issues

def add_category_to_stocklist(category_name):
    cat = category_name.strip()
    if not cat:
        return False, "分類名稱不可空白。"
    if "," in cat:
        return False, "分類名稱不可包含逗號。"
    cat_order, cat_map, _ = load_stocklist_structure()
    if cat in cat_map:
        return False, "分類已存在。"
    cat_order.append(cat)
    cat_map[cat] = []
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已新增分類：{cat}"

def add_stock_to_category(code, name, category):
    sc = str(code).strip()
    sn = str(name).strip()
    if not sc or not sn:
        return False, "股票代號與名稱皆不可空白。"
    if not sc.isdigit():
        return False, "股票代號必須為純數字。"
    cat_order, cat_map, _ = load_stocklist_structure()
    if category not in cat_map:
        cat_order.append(category)
        cat_map[category] = []
    for c in cat_order:
        for ec, _ in cat_map.get(c, []):
            if ec == sc:
                return False, f"代號 {sc} 已存在於分類「{c}」。"
    cat_map[category].append((sc, sn))
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已加入 {sc} {sn} 到「{category}」。"

def remove_stock_from_stocklist(code):
    sc = str(code).strip()
    cat_order, cat_map, _ = load_stocklist_structure()
    removed = False
    for c in cat_order:
        old_len = len(cat_map.get(c, []))
        cat_map[c] = [(ec, en) for ec, en in cat_map.get(c, []) if ec != sc]
        if len(cat_map[c]) != old_len:
            removed = True
    if not removed:
        return False, f"找不到代號 {sc}。"
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已刪除代號 {sc}。"

def move_stock_to_category(code, target_category):
    sc = str(code).strip()
    target = str(target_category).strip()
    if not target:
        return False, "目標分類不可空白。"
    cat_order, cat_map, _ = load_stocklist_structure()
    found = None
    for c in cat_order:
        for i, (ec, en) in enumerate(cat_map.get(c, [])):
            if ec == sc:
                found = (c, i, en)
                break
        if found:
            break
    if not found:
        return False, f"找不到代號 {sc}。"
    from_cat, idx, name = found
    if target not in cat_map:
        cat_order.append(target)
        cat_map[target] = []
    if from_cat == target:
        return False, "已在同一分類。"
    cat_map[from_cat].pop(idx)
    cat_map[target].append((sc, name))
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已將 {sc} 移動至「{target}」。"

def move_stock_order_within_category(category, code, direction="up"):
    cat_order, cat_map, _ = load_stocklist_structure()
    if category not in cat_map:
        return False, "分類不存在。"
    arr = cat_map[category]
    idx = next((i for i, (c, _) in enumerate(arr) if c == str(code).strip()), -1)
    if idx == -1:
        return False, "找不到該代號。"
    if direction == "up" and idx > 0:
        arr[idx-1], arr[idx] = arr[idx], arr[idx-1]
    elif direction == "down" and idx < len(arr)-1:
        arr[idx+1], arr[idx] = arr[idx], arr[idx+1]
    else:
        return False, "已在邊界，無法移動。"
    cat_map[category] = arr
    save_stocklist_structure(cat_order, cat_map)
    return True, "排序已更新。"

def toggle_watchlist(code, name):
    lines = []
    if os.path.exists("stocklist.txt"):
        try:
            with open("stocklist.txt", "r", encoding="utf-8") as f: lines = f.readlines()
        except: pass
    new_lines = []
    is_removed = False
    for line in lines:
        if "," in line and line.split(",")[0].strip() == str(code):
            is_removed = True
            continue
        new_lines.append(line)
    if not is_removed:
        if new_lines and not new_lines[-1].endswith("\n"): new_lines[-1] = new_lines[-1] + "\n"
        new_lines.append(f"{code},{name}\n")
    with open("stocklist.txt", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def get_streak(series):
    streak = 0
    for val in reversed(series.tolist()):
        if val > 0:
            if streak >= 0: streak += 1
            else: break
        elif val < 0:
            if streak <= 0: streak -= 1
            else: break
        else:
            break
    return streak

# ==========================================
# 2. Session State 初始化 & 狀態管理
# ==========================================
def init_session_state():
    if 'selected_stock' not in st.session_state: st.session_state.selected_stock = "2330"
    if 'topic_results' not in st.session_state: st.session_state.topic_results = None
    if 'show_whale' not in st.session_state: st.session_state.show_whale = False
    if 'api_key' not in st.session_state: st.session_state.api_key = ""
    if 'fugle_key' not in st.session_state: st.session_state.fugle_key = "" 
    if 'finmind_key' not in st.session_state: st.session_state.finmind_key = "" 
    if 'ai_fetched_financials' not in st.session_state: st.session_state.ai_fetched_financials = {}
    if 'show_pk' not in st.session_state: st.session_state.show_pk = False
    if 'ai_industry_result' not in st.session_state: st.session_state.ai_industry_result = None
    if 'run_screener' not in st.session_state: st.session_state.run_screener = False
    if 'quick_select' not in st.session_state: st.session_state.quick_select = "-- 快速切換標的 --"
    if 'stock_input_widget' not in st.session_state: st.session_state.stock_input_widget = "2330"
    if 'show_watchlist_manager' not in st.session_state: st.session_state.show_watchlist_manager = False
    if 'w_valuation' not in st.session_state: st.session_state.w_valuation = 35
    if 'w_growth' not in st.session_state: st.session_state.w_growth = 30
    if 'w_chip' not in st.session_state: st.session_state.w_chip = 20
    if 'w_revenue' not in st.session_state: st.session_state.w_revenue = 15
    if 'data_health_stats' not in st.session_state:
        st.session_state.data_health_stats = {
            "Yahoo": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            "Fugle": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            "FinMind": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            "Gemini": {"last_success": None, "error_count": 0, "last_status": "N/A"},
        }

def log_data_health(source, ok, status_code=None):
    src = str(source).strip()
    if not src:
        return
    if 'data_health_stats' not in st.session_state:
        init_session_state()
    stats = st.session_state.data_health_stats
    if src not in stats:
        stats[src] = {"last_success": None, "error_count": 0, "last_status": "N/A"}

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s = stats[src]
    s["last_status"] = str(status_code) if status_code is not None else ("OK" if ok else "ERR")
    if ok:
        s["last_success"] = now_str
    else:
        s["error_count"] = int(s.get("error_count", 0)) + 1
    stats[src] = s
    st.session_state.data_health_stats = stats

def reset_all_states_on_stock_change(stock_code):
    st.session_state.selected_stock = stock_code
    st.session_state.quick_select = "-- 快速切換標的 --"
    st.session_state.show_pk = False
    st.session_state.ai_industry_result = None
    st.session_state.run_screener = False

# ==========================================
# 🌟 這裡就是修正的部分：加入 .get() 安全讀取機制
# ==========================================
def on_stock_input_change():
    new_stock = st.session_state.get('stock_input_widget', '2330')
    selected_stock = st.session_state.get('selected_stock', '2330')
    
    if new_stock != selected_stock: 
        reset_all_states_on_stock_change(new_stock)

def on_quick_select_change():
    selected = st.session_state.get('quick_select', '-- 快速切換標的 --')
    selected_stock = st.session_state.get('selected_stock', '2330')
    
    if selected != "-- 快速切換標的 --":
        if not selected.startswith("🏷️"):
            q_code = selected.replace("　🔸 ", "").split(" ")[0].strip()
            if q_code != selected_stock: 
                reset_all_states_on_stock_change(q_code)
        st.session_state.quick_select = "-- 快速切換標的 --"

def get_selected_model_id():
    """AI 財報/分析模型鎖定付費版高階模型，避免自動降級造成資料失真。"""
    return "gemini-3.1-pro-preview"
