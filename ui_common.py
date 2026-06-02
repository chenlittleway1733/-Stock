"""
UI 模組共用匯入。
此檔案保留原 ui.py 需要的外部依賴，避免各模組重複維護 import。
"""
import datetime
import math
import os
import re
import time
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components
from services import *
from utils import *
from scoring import calculate_strategy_score, normalize_screener_weights, backtest_return_from_hist, score_icon

from industry_model import get_industry_valuation_profile, build_industry_valuation_model_report

from dynamic_cap_model import calculate_dynamic_cap_v2
