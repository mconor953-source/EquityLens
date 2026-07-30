"""EquityLens — Dashboard: a 10-second read on global markets.

Every section here — Global Markets, Major Assets, Market Movers, Market
Pulse, Momentum Signals, and 52-Week Extremes — is real, live data, derived
from one fetch per tracked asset (see the loop below) and reused across
every section so the page makes exactly one pass over the network per
load. Market Pulse / Momentum Signals / 52-Week Extremes are computed by
dashboard_content.py using the same rule-based approach as scoring.py's
Financial Health Score and technicals.py's Technical Rating — real numbers
run through fixed thresholds, never generated text and never AI.
"""

from datetime import datetime

import streamlit as st

from theme import apply_theme, INK_PRIMARY, INK_SECONDARY, INK_MUTED, BORDER
from components import section_header, market_table, render_html
from assets import GLOBAL_MARKETS, MAJOR_ASSETS
from data_fetcher import get_price_history
from technicals import relative_strength_index, fifty_two_week_range
from dashboard_content import get_market_pulse, get_notable_signals, get_52_week_extremes

st.set_page_config(page_title="EquityLens — Dashboard", layout="wide")
apply_theme()

st.markdown("## Dashboard")
st.caption(datetime.now().strftime("%A, %B %d, %Y") + " · Market data via Yahoo Finance, delayed")

st.write("")

# ---------- Fetch every tracked asset once, reused across every section below ----------
# One year of history per asset (rather than a handful of days) so the same
# fetch can serve price/change, RSI(14), and the 52-week range — Market
# Pulse, Momentum Signals, and 52-Week Extremes all read from this list
# instead of hitting the network again.
tracked_assets = GLOBAL_MARKETS + MAJOR_ASSETS
market_data = []
with st.spinner("Loading market data..."):
    for label, ticker in tracked_assets:
        try:
            history = get_price_history(ticker, period="1y")
        except Exception:
            history = None

        price = pct_change = rsi = range_52w = None
        if history is not None and not history.empty and "Close" in history.columns:
            closes = history["Close"]
            price = closes.iloc[-1]
            previous_close = closes.iloc[-2] if len(closes) > 1 else None
            pct_change = ((price - previous_close) / previous_close * 100) if previous_close else None
            rsi_series = relative_strength_index(closes)
            rsi = rsi_series.iloc[-1] if rsi_series is not None else None
            range_52w = fifty_two_week_range(history)

        market_data.append({
            "label": label, "price": price, "pct_change": pct_change, "rsi": rsi, "range_52w": range_52w,
        })

global_rows = [(d["label"], d["price"], d["pct_change"]) for d in market_data[: len(GLOBAL_MARKETS)]]
asset_rows = [(d["label"], d["price"], d["pct_change"]) for d in market_data[len(GLOBAL_MARKETS):]]

movable = [d for d in market_data if d["pct_change"] is not None]
gainers = sorted(movable, key=lambda d: d["pct_change"], reverse=True)[:3]
losers = sorted(movable, key=lambda d: d["pct_change"])[:3]
gainer_rows = [(d["label"], d["price"], d["pct_change"]) for d in gainers]
loser_rows = [(d["label"], d["price"], d["pct_change"]) for d in losers]

# ---------- Market Pulse — the focal point ----------
pulse = get_market_pulse(market_data)
section_header("Market Pulse")

with st.container(border=True):
    render_html(
        f"""
        <div style="font-size:1.4rem; font-weight:700; color:{INK_PRIMARY}; line-height:1.35; margin-bottom:16px;">
            {pulse['headline']}
        </div>
        """
    )
    for paragraph in pulse["summary"]:
        render_html(
            f'<p style="color:{INK_SECONDARY}; font-size:0.95rem; line-height:1.7; margin-bottom:12px;">{paragraph}</p>'
        )

    if pulse["watch_items"]:
        render_html(f'<hr style="margin:18px 0 16px 0; border-color:{BORDER};">')

        watch_cols = st.columns(len(pulse["watch_items"]))
        for col, item in zip(watch_cols, pulse["watch_items"]):
            with col:
                render_html(
                    f"""
                    <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase;
                                letter-spacing:0.05em; color:{INK_MUTED}; margin-bottom:6px;">
                        {item['label']}
                    </div>
                    <div style="font-size:0.86rem; color:{INK_PRIMARY}; line-height:1.55;">
                        {item['detail']}
                    </div>
                    """
                )

st.write("")

# ---------- Global Markets | Major Assets ----------
gm_col, ma_col = st.columns(2)

with gm_col:
    st.markdown("#### Global Markets")
    with st.container(border=True):
        market_table(global_rows)

with ma_col:
    st.markdown("#### Major Assets")
    with st.container(border=True):
        market_table(asset_rows)

st.write("")

# ---------- Market Movers ----------
st.markdown("#### Market Movers")
st.caption("Biggest gainers and losers across all tracked global markets and major assets.")

mv_col1, mv_col2 = st.columns(2)
with mv_col1:
    st.markdown("###### Gainers")
    with st.container(border=True):
        if gainer_rows:
            market_table(gainer_rows)
        else:
            st.caption("No data available.")
with mv_col2:
    st.markdown("###### Losers")
    with st.container(border=True):
        if loser_rows:
            market_table(loser_rows)
        else:
            st.caption("No data available.")

st.write("")

# ---------- Momentum Signals | 52-Week Extremes ----------
ms_col, we_col = st.columns(2)

with ms_col:
    section_header("Momentum Signals", subtitle="Assets at an RSI(14) extreme — overbought above 70, oversold below 30.")
    with st.container(border=True):
        signals = get_notable_signals(market_data)
        if not signals:
            st.caption("No tracked assets are currently at a momentum extreme.")
        for i, item in enumerate(signals):
            render_html(
                f'<div style="padding:5px 0; font-size:0.88rem;">'
                f'<b style="color:{INK_PRIMARY};">{item["asset"]}</b>'
                f'<span style="color:{INK_SECONDARY};"> — {item["note"]}</span></div>'
            )
            if i < len(signals) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')

with we_col:
    section_header("52-Week Extremes", subtitle="Assets trading within 3% of their trailing 52-week high or low.")
    with st.container(border=True):
        extremes = get_52_week_extremes(market_data)
        if not extremes:
            st.caption("No tracked assets are currently near a 52-week high or low.")
        for i, item in enumerate(extremes):
            is_high = item["flag"] == "Near High"
            flag_color = INK_PRIMARY if is_high else INK_SECONDARY
            render_html(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0;">
                    <div>
                        <div style="color:{INK_PRIMARY}; font-weight:600; font-size:0.87rem;">{item['asset']}</div>
                        <div style="color:{INK_MUTED}; font-size:0.76rem;">{item['note']}</div>
                    </div>
                    <span style="color:{flag_color}; font-weight:700; font-size:0.76rem;
                                text-transform:uppercase; letter-spacing:0.03em;">{item['flag']}</span>
                </div>
                """
            )
            if i < len(extremes) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')
