"""Data access layer: wraps yfinance calls and formats raw numbers for display."""

import yfinance as yf
import pandas as pd
import streamlit as st


@st.cache_data(ttl=300, show_spinner=False)
def get_ticker_info(ticker: str) -> dict:
    """Fetch company/financial info for a ticker. Cached for 5 minutes."""
    stock = yf.Ticker(ticker)
    return stock.info


@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical OHLCV price data for a ticker. Cached for 5 minutes.

    yfinance sometimes includes a trailing row for the current, still-open
    session with no data yet (all-NaN OHLC) — that row is dropped so charts
    and price calculations never end on an empty bar.
    """
    stock = yf.Ticker(ticker)
    history = stock.history(period=period)
    if "Close" in history.columns:
        history = history.dropna(subset=["Close"])
    return history


def get_current_price_and_change(ticker: str, period: str = "5d"):
    """Return (current_price, pct_change) from the last two daily closes.

    Works across every asset class (stocks, crypto, forex, metals, indices)
    since it reads directly from price history rather than the inconsistent
    `.info` fields those asset types don't all populate. Returns (None, None)
    if no data is available for the ticker.
    """
    try:
        history = get_price_history(ticker, period=period)
    except Exception:
        return None, None

    if history.empty or "Close" not in history.columns:
        return None, None

    current_price = history["Close"].iloc[-1]
    if len(history) < 2:
        return current_price, None

    previous_close = history["Close"].iloc[-2]
    pct_change = (current_price - previous_close) / previous_close * 100 if previous_close else None
    return current_price, pct_change


def is_valid_ticker(info: dict) -> bool:
    """A delisted/invalid ticker returns an info dict with no name and no price."""
    if not info:
        return False
    has_name = bool(info.get("longName") or info.get("shortName"))
    has_price = info.get("currentPrice") is not None or info.get("regularMarketPrice") is not None
    return has_name and has_price


def format_large_number(value, prefix: str = "$") -> str:
    """Convert a raw number into a readable scale, e.g. 3.51e12 -> '$3.51T'."""
    if value is None:
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1e12:
        scaled = f"{value / 1e12:.2f}T"
    elif abs_value >= 1e9:
        scaled = f"{value / 1e9:.2f}B"
    elif abs_value >= 1e6:
        scaled = f"{value / 1e6:.2f}M"
    else:
        scaled = f"{value:,.0f}"
    return f"{prefix}{scaled}"


def format_ratio(value) -> str:
    """Format a plain ratio like P/E to two decimal places."""
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def format_price(value) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_market_price(value) -> str:
    """Format a price with precision appropriate to its magnitude: more
    decimals for sub-$10 instruments (most forex pairs trade near 1.00-1.50
    and need that precision to show meaningful movement), standard cents
    otherwise. Same convention already used inline on Market Research."""
    if value is None:
        return "N/A"
    return f"${value:,.4f}" if value < 10 else f"${value:,.2f}"


def format_percentage(value) -> str:
    """Format a fractional ratio as a percentage, e.g. 0.166 -> '16.60%'."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def format_multiple(value) -> str:
    """Format a ratio as a multiple, e.g. 0.795 -> '0.80x'."""
    if value is None:
        return "N/A"
    return f"{value:.2f}x"


RECOMMENDATION_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "underperform": "Underperform",
    "sell": "Sell",
}


def get_analyst_consensus(info: dict) -> dict:
    """Extract Wall Street analyst coverage from the yfinance info dict —
    real sell-side data (recommendation, price targets, analyst count), not
    computed here. Returns raw values (None if uncovered); formatting is
    handled by the view."""
    key = (info.get("recommendationKey") or "").lower()
    return {
        "recommendation": RECOMMENDATION_LABELS.get(key, key.replace("_", " ").title() if key else None),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "target_mean": info.get("targetMeanPrice"),
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
    }


def get_extended_metrics(info: dict) -> dict:
    """Extract growth, profitability, financial position, and valuation figures
    from the yfinance info dict. Returns raw numeric values (None if unavailable);
    formatting is handled separately by the format_* helpers.

    Note: yfinance reports debtToEquity as a percentage-point figure (e.g. 79.5),
    not a raw ratio, so it is divided by 100 here to give a true multiple (0.795).
    """
    debt_to_equity = info.get("debtToEquity")
    return {
        "revenue_growth": info.get("revenueGrowth"),
        "net_profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "return_on_equity": info.get("returnOnEquity"),
        "free_cash_flow": info.get("freeCashflow"),
        "total_debt": info.get("totalDebt"),
        "debt_to_equity": (debt_to_equity / 100) if debt_to_equity is not None else None,
        "forward_pe": info.get("forwardPE"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
    }
