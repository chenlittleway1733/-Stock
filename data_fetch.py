"""Data fetching and financial computations."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from utils_format import s_float


@st.cache_data(ttl=3600)
def fetch_stock_data(symbol: str) -> tuple[pd.DataFrame, dict]:
    """Fetch one year of historical prices and metadata for a stock symbol."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1y")
    info = ticker.info
    return hist, info


def compute_valuation(info: dict, current_price: float) -> dict:
    """Compute valuation ranges based on EPS and PE."""
    eps = s_float(info.get("trailingEps", 0))
    pe_ratio = s_float(info.get("trailingPE", 0))

    if pe_ratio == 0 and eps > 0:
        pe_ratio = current_price / eps

    cheap_price = eps * 15
    fair_price = eps * 20
    expensive_price = eps * 30

    evaluation = "合理"
    if current_price <= cheap_price:
        evaluation = "便宜區間"
    elif current_price >= expensive_price:
        evaluation = "昂貴區間"

    return {
        "eps": eps,
        "pe_ratio": pe_ratio,
        "cheap_price": cheap_price,
        "fair_price": fair_price,
        "expensive_price": expensive_price,
        "evaluation": evaluation,
    }


def add_technical_indicators(hist: pd.DataFrame) -> pd.DataFrame:
    """Add MA and KD indicators while preserving the original DataFrame structure."""
    df = hist.copy()
    df["5MA"] = df["Close"].rolling(window=5).mean()
    df["10MA"] = df["Close"].rolling(window=10).mean()
    df["60MA"] = df["Close"].rolling(window=60).mean()

    low_min = df["Low"].rolling(window=9).min()
    high_max = df["High"].rolling(window=9).max()
    denominator = (high_max - low_min).replace(0, pd.NA)
    df["RSV"] = 100 * (df["Close"] - low_min) / denominator
    df["K"] = df["RSV"].ewm(com=2, adjust=False).mean()
    df["D"] = df["K"].ewm(com=2, adjust=False).mean()

    return df
