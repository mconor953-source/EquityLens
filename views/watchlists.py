"""EquityLens — Watchlists: two persistent, workspace-style ticker lists."""

import streamlit as st

from theme import apply_theme
from components import price_change_html, rating_badge_html, render_html
from data_fetcher import get_current_price_and_change, get_ticker_info, get_extended_metrics, is_valid_ticker
from scoring import calculate_financial_health
from watchlist_store import load_watchlists, add_ticker, remove_ticker

st.set_page_config(page_title="EquityLens — Watchlists", layout="wide")
apply_theme()

st.markdown("## Watchlists")
st.caption("Two persistent, purpose-built lists — not just a table of tickers.")

watchlists = load_watchlists()


def add_remove_row(watchlist_name: str) -> None:
    add_col, button_col = st.columns([3, 1])
    new_ticker = add_col.text_input(
        "Add ticker", placeholder="e.g. AAPL", key=f"add_input_{watchlist_name}", label_visibility="collapsed"
    )
    if button_col.button("Add", key=f"add_button_{watchlist_name}", use_container_width=True):
        if new_ticker.strip():
            add_ticker(watchlist_name, new_ticker)
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

        score_html = '<span style="color:#5B6B82;">N/A</span>'
        if is_valid_ticker(info):
            metrics = get_extended_metrics(info)
            health = calculate_financial_health(info, metrics)
            score_html = f"{health['total_score']}/100 &nbsp;{rating_badge_html(health['rating'])}"

        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1.2, 1.3, 1.3, 2, 0.8])
        row_col1.markdown(f"**{ticker}**")
        row_col2.markdown(f"${price:,.2f}" if price is not None else "N/A")
        row_col3.markdown(price_change_html(pct_change), unsafe_allow_html=True)
        row_col4.markdown(score_html, unsafe_allow_html=True)
        if row_col5.button("Remove", key=f"remove_Long-Term Investing_{ticker}"):
            remove_ticker("Long-Term Investing", ticker)
            st.rerun()
        st.markdown('<hr style="margin:4px 0; border-color:#E2E8F0;">', unsafe_allow_html=True)

# ---------- Swing Trade Watchlist ----------
with swing_tab:
    st.caption(
        "Live price only for now — trend, status, and alerting are planned for a future stage."
    )
    add_remove_row("Swing Trade Watchlist")
    st.write("")

    tickers = watchlists.get("Swing Trade Watchlist", [])
    if not tickers:
        st.info("No tickers yet — add one above.")

    swing_cols = st.columns(2)
    for i, ticker in enumerate(tickers):
        price, pct_change = get_current_price_and_change(ticker)
        with swing_cols[i % 2]:
            render_html(
                f"""
                <div class="el-card">
                    <div style="display:flex; justify-content:space-between; align-items:baseline;">
                        <span class="el-card-title">{ticker}</span>
                        <span style="font-weight:700;">{f"${price:,.2f}" if price is not None else "N/A"}</span>
                    </div>
                    <div style="margin-bottom:10px;">{price_change_html(pct_change)}</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px 14px; font-size:0.85rem; color:#5B6B82;">
                        <div>Current Trend: <b>—</b></div>
                        <div>Status: <b>—</b></div>
                        <div>Distance to Entry: <b>—</b></div>
                        <div>Support: <b>—</b></div>
                        <div>Resistance: <b>—</b></div>
                        <div>Alert Status: <b>—</b></div>
                    </div>
                    <div style="display:inline-block; margin-top:12px; padding:3px 12px; border-radius:999px;
                                background-color:#F4F7FB; color:#5B6B82; font-size:0.7rem; font-weight:700;
                                letter-spacing:0.03em; text-transform:uppercase;">Planned feature</div>
                </div>
                """
            )
            if st.button("Remove", key=f"remove_Swing Trade Watchlist_{ticker}"):
                remove_ticker("Swing Trade Watchlist", ticker)
                st.rerun()
