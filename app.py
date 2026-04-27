"""Main Streamlit entrypoint for the modularized stock application."""

from __future__ import annotations

import streamlit as st

from data_fetch import add_technical_indicators, compute_valuation, fetch_stock_data
from ui_sections import (
    render_kd_chart,
    render_news_placeholder,
    render_price_chart,
    render_top_bar,
    render_valuation,
)


stock_symbol, yf_symbol = render_top_bar()

if stock_symbol:
    try:
        hist, info = fetch_stock_data(yf_symbol)

        if hist.empty:
            st.error("找不到該股票的資料，請確認台股代號是否正確。")
        else:
            stock_name = info.get("shortName", stock_symbol)
            current_price = hist["Close"].iloc[-1]

            valuation = compute_valuation(info, current_price)
            hist_with_indicators = add_technical_indicators(hist)

            render_valuation(stock_name, stock_symbol, current_price, valuation)
            render_price_chart(hist_with_indicators)
            render_kd_chart(hist_with_indicators)
            render_news_placeholder()

    except Exception as exc:
        st.error(f"系統分析時發生錯誤: {exc}")
