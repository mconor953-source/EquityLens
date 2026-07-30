"""EquityLens — Watchlists: two persistent, workspace-style ticker lists."""

import streamlit as st

from theme import apply_theme, INK_SECONDARY, INK_MUTED, BORDER, TECHNICAL_RATING_COLORS
from components import price_change_html, rating_badge_html, render_html
from data_fetcher import (
    get_current_price_and_change,
    get_ticker_info,
    get_extended_metrics,
    get_price_history,
    is_valid_ticker,
    format_market_price,
)
from scoring import calculate_financial_health
from technicals import compute_technical_rating
from watchlist_store import load_watchlists, add_ticker, remove_ticker

st.set_page_config(page_title="EquityLens — Watchlists", layout="wide")
apply_theme()

st.markdown("## Watchlists")
st.caption("Two persistent, purpose-built lists — not just a table of tickers.")

watchlists = load_watchlists()


def add_remove_row(watchlist_name: str) -> None:
    """Add-ticker row: validates against real market data before persisting
    (so a typo can't silently sit in the list forever showing N/A), and
    clears the input on a successful add."""
    input_key = f"add_input_{watchlist_name}"
    add_col, button_col = st.columns([3, 1])
    new_ticker = add_col.text_input(
        "Add ticker", placeholder="e.g. AAPL, BTC-USD, EURUSD=X, GC=F, ^GSPC",
        key=input_key, label_visibility="collapsed",
    )
    if button_col.button("Add", key=f"add_button_{watchlist_name}", use_container_width=True):
        candidate = new_ticker.strip().upper()
        if not candidate:
            st.warning("Enter a ticker symbol first.")
        else:
            price, _ = get_current_price_and_change(candidate)
            if price is None:
                st.error(f"No data found for '{candidate}'. Check the symbol and try again.")
            else:
                if candidate in load_watchlists().get(watchlist_name, []):
                    st.toast(f"{candidate} is already in {watchlist_name}.")
                else:
                    add_ticker(watchlist_name, candidate)
                    st.toast(f"Added {candidate} to {watchlist_name}.")
                del st.session_state[input_key]
                st.rerun()


long_term_tab, swing_tab = st.tabs(["Long-Term Investing", "Swing Trade Watchlist"])

# ---------- Long-Term Investing ----------
with long_term_tab:
    st.caption("Live price, change, and Financial Health Score for each holding.")
    add_remove_row("Long-Term Investing")
    st.write("")

    tickers = watchlists.get("Long-Term Investing", [])
    if not tickers:
        st.info("No tickers yet — add one above.")
    for ticker in tickers:
        price, pct_change = get_current_price_and_change(ticker)
        info = get_ticker_info(ticker)

        score_html = f'<span style="color:{INK_SECONDARY};">N/A</span>'
        if is_valid_ticker(info):
            metrics = get_extended_metrics(info)
            health = calculate_financial_health(info, metrics)
            score_html = f"{health['total_score']}/100 &nbsp;{rating_badge_html(health['rating'])}"

        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1.2, 1.3, 1.3, 2, 0.8])
        row_col1.markdown(f"**{ticker}**")
        row_col2.markdown(format_market_price(price))
        row_col3.markdown(price_change_html(pct_change), unsafe_allow_html=True)
        row_col4.markdown(score_html, unsafe_allow_html=True)
        if row_col5.button("Remove", key=f"remove_Long-Term Investing_{ticker}"):
            remove_ticker("Long-Term Investing", ticker)
            st.rerun()
        st.markdown(f'<hr style="margin:4px 0; border-color:{BORDER};">', unsafe_allow_html=True)

# ---------- Swing Trade Watchlist ----------
with swing_tab:
    st.caption(
        "Live price and a rule-based Technical Rating for each ticker — the same signal-count "
        "model used on Market Research."
    )
    add_remove_row("Swing Trade Watchlist")
    st.write("")

    tickers = watchlists.get("Swing Trade Watchlist", [])
    if not tickers:
        st.info("No tickers yet — add one above.")

    swing_cols = st.columns(2)
    for i, ticker in enumerate(tickers):
        price, pct_change = get_current_price_and_change(ticker)
        try:
            history = get_price_history(ticker, period="1y")
        except Exception:
            history = None
        technical = compute_technical_rating(history) if history is not None else None

        if technical:
            rating_color = TECHNICAL_RATING_COLORS.get(technical["rating"], INK_SECONDARY)
            rating_html = (
                f'<b style="color:{rating_color};">{technical["rating"]}</b>'
                f'<span style="color:{INK_MUTED};"> &middot; {technical["buy_count"]}B / '
                f'{technical["neutral_count"]}N / {technical["sell_count"]}S</span>'
            )
            rsi_value = technical.get("rsi")
            rsi_html = f"{rsi_value:.1f}" if rsi_value is not None else "N/A"
        else:
            rating_html = f'<span style="color:{INK_MUTED};">Not enough price history</span>'
            rsi_html = "N/A"

        with swing_cols[i % 2]:
            render_html(
                f"""
                <div class="el-card">
                    <div style="display:flex; justify-content:space-between; align-items:baseline;">
                        <span class="el-card-title">{ticker}</span>
                        <span style="font-weight:700;">{format_market_price(price)}</span>
                    </div>
                    <div style="margin-bottom:10px;">{price_change_html(pct_change)}</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px 14px; font-size:0.85rem; color:{INK_SECONDARY};">
                        <div style="grid-column: 1 / -1;">Technical Rating: {rating_html}</div>
                        <div>RSI (14): <b>{rsi_html}</b></div>
                    </div>
                </div>
                """
            )
            if st.button("Remove", key=f"remove_Swing Trade Watchlist_{ticker}"):
                remove_ticker("Swing Trade Watchlist", ticker)
                st.rerun()
