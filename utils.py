"""
共用常數、格式化工具、自選股與 Streamlit Session State 管理。
由原始 app(1).py 拆分而來。
"""

import os
import re
import math

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

def build_cmp_str(orig, ai_val, fmt="pct", suffix="AI推估"):
    s = to_val_str(orig, fmt)
    if ai_val is not None and not pd.isna(ai_val):
        s += f"<br><span style='color:#FFD700; font-size:0.85rem;'>({to_val_str(float(ai_val), fmt)}, {suffix})</span>"
    return s

def build_cmp_dual_str(o1, o2, a1, a2, fmt1="num", fmt2="num", suffix="AI推估"):
    s1 = to_val_str(o1, fmt1)
    s2 = to_val_str(o2, fmt2)
    s = f"{s1} / <span style='color:#00bfff;'>{s2}</span>" if (fmt1=="num" and fmt2=="num") else f"{s1} / {s2}"
    if (a1 is not None and not pd.isna(a1)) or (a2 is not None and not pd.isna(a2)):
        sa1 = to_val_str(float(a1) if a1 is not None else None, fmt1)
        sa2 = to_val_str(float(a2) if a2 is not None else None, fmt2)
        s += f"<br><span style='color:#FFD700; font-size:0.85rem;'>({sa1} / {sa2}, {suffix})</span>"
    return s

def clean_html(html_str):
    return re.sub(r'[\r\n\t]+', ' ', html_str).strip()

def get_watchlist():
    watchlist = []
    if os.path.exists("stocklist.txt"):
        try:
            with open("stocklist.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if "," in line: watchlist.append(line.split(",")[0].strip())
        except: pass
    return watchlist

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

def reset_all_states_on_stock_change(stock_code):
    st.session_state.selected_stock = stock_code
    st.session_state.quick_select = "-- 快速切換標的 --"
    st.session_state.show_pk = False
    st.session_state.ai_industry_result = None
    st.session_state.run_screener = False

def on_stock_input_change():
    new_stock = st.session_state.stock_input_widget
    if new_stock != st.session_state.selected_stock: reset_all_states_on_stock_change(new_stock)

def on_quick_select_change():
    selected = st.session_state.quick_select
    if selected != "-- 快速切換標的 --":
        if not selected.startswith("🏷️"):
            q_code = selected.replace("　🔸 ", "").split(" ")[0].strip()
            if q_code != st.session_state.selected_stock: reset_all_states_on_stock_change(q_code)
        st.session_state.quick_select = "-- 快速切換標的 --"

def get_selected_model_id():
    opt = st.session_state.get('ai_model_radio', 'Gemini 2.5 Flash')
    if "3.1 Pro" in opt: return "gemini-3.1-pro-preview"
    elif "3.1 Flash-Lite" in opt: return "gemini-3.1-flash-lite-preview"
    elif "3 Flash" in opt: return "gemini-3-flash-preview"
    elif "2.5 Pro" in opt: return "gemini-2.5-pro"
    else: return "gemini-2.5-flash"
