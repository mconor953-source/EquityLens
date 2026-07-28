"""EquityLens — Dashboard: the 30-second view of the day."""

from datetime import datetime

import streamlit as st

from theme import apply_theme
from components import compact_placeholder, price_pill, render_html, rating_badge_html
from assets import MARKETS_TODAY
from data_fetcher import get_current_price_and_change, get_ticker_info, get_extended_metrics
from scoring import calculate_financial_health
from watchlist_store import load_watchlists

st.set_page_config(page_title="EquityLens — Dashboard", layout="wide")
apply_theme()

# ---------- Welcome ----------
hour = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
st.markdown(f"## {greeting}, welcome to EquityLens")
st.caption(datetime.now().strftime("%A, %B %d, %Y") + " · What you need to know in the next 30 seconds.")

st.write("")

# ---------- Markets Today ----------
st.markdown("#### Markets Today")
cols = st.columns(len(MARKETS_TODAY))
for col, (label, ticker) in zip(cols, MARKETS_TODAY):
    price, pct_change = get_current_price_and_change(ticker)
    with col:
        price_pill(label, price, pct_change, align="center")

st.write("")

# ---------- AI Market Brief + Quick Navigation ----------
brief_col, nav_col = st.columns([1.3, 1])

with brief_col:
    st.markdown("#### AI Market Brief")
    compact_placeholder("Daily AI market summary")

with nav_col:
    st.markdown("#### Quick Navigation")
    nav_items = [
        ("Market Research", "views/market_research.py"),
        ("Trade Studio", "views/trade_studio.py"),
        ("Watchlists", "views/watchlists.py"),
        ("Settings", "views/settings.py"),
    ]
    for label, target in nav_items:
        st.page_link(target, label=label, use_container_width=True)

st.write("")

# ---------- Watchlist Preview + Recent News ----------
preview_col, news_col = st.columns([1.3, 1])

with preview_col:
    st.markdown("#### Watchlist Preview — Long-Term Investing")
    watchlist_tickers = load_watchlists().get("Long-Term Investing", [])[:5]
    if not watchlist_tickers:
        st.caption("Your Long-Term Investing watchlist is empty. Add tickers on the Watchlists page.")
    else:
        preview_cols = st.columns(len(watchlist_tickers))
        for col, ticker in zip(preview_cols, watchlist_tickers):
            price, pct_change = get_current_price_and_change(ticker)
            with col:
                price_pill(ticker, price, pct_change, align="center")

with news_col:
    st.markdown("#### Recent News")
    compact_placeholder("Headlines for your watchlists")

st.write("")

# ---------- Financial Health Leaderboard + Market Sentiment ----------
leaderboard_col, sentiment_col = st.columns([1.3, 1])

with leaderboard_col:
    st.markdown("#### Financial Health Leaderboard")
    st.caption("Ranked by the same rule-based Financial Health Score used on Market Research.")

    LEADERBOARD_TICKERS = ["AAPL", "MSFT", "TSLA", "JNJ", "KO", "NVDA"]
    rows = []
    for ticker in LEADERBOARD_TICKERS:
        info = get_ticker_info(ticker)
        if not info or info.get("currentPrice") is None:
            continue
        metrics = get_extended_metrics(info)
        health = calculate_financial_health(info, metrics)
        name = info.get("longName") or info.get("shortName") or ticker
        rows.append((ticker, name, health["total_score"], health["rating"]))

    rows.sort(key=lambda r: r[2], reverse=True)

    if not rows:
        st.info("No leaderboard data available right now.")
    else:
        header_cols = st.columns([0.5, 1, 2.2, 1, 1.1])
        header_cols[0].markdown("**Rank**")
        header_cols[1].markdown("**Ticker**")
        header_cols[2].markdown("**Company**")
        header_cols[3].markdown("**Score**")
        header_cols[4].markdown("**Rating**")
        st.divider()

        for rank, (ticker, name, score, rating) in enumerate(rows, start=1):
            row_cols = st.columns([0.5, 1, 2.2, 1, 1.1])
            row_cols[0].markdown(f"#{rank}")
            row_cols[1].markdown(f"**{ticker}**")
            row_cols[2].markdown(name)
            row_cols[3].markdown(f"{score}/100")
            with row_cols[4]:
                render_html(rating_badge_html(rating))

with sentiment_col:
    st.markdown("#### Market Sentiment")
    compact_placeholder("Bullish vs. bearish positioning")
