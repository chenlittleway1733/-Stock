"""
台股聯網 AI 投資戰情室 - Streamlit 入口檔
執行方式：
    streamlit run app.py
""" 

import streamlit as st

from ui import render_main_page, render_sidebar
from utils import init_session_state

# ==========================================
# 0. 網頁基本設定
# ==========================================
st.set_page_config(page_title="way投資戰情室1.1", layout="wide")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

init_session_state()

sidebar_state = render_sidebar()
render_main_page(sidebar_state)
