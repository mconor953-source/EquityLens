"""EquityLens — Dashboard: a 10-second read on global markets.

Global Markets, Major Assets, and Market Movers are all real, live data —
fetched once at the top of this script and reused across sections so the
page makes exactly one pass over the network per load. The AI Market Brief,
Today's Watchlist, and Economic Calendar are illustrative sample content
(see dashboard_content.py) — there is no news feed, calendar API, or AI
model behind them yet, and each is labeled "Sample data" for that reason.
"""

from datetime import datetime

import streamlit as st

from theme import apply_theme, INK_PRIMARY, INK_SECONDARY, INK_MUTED, BORDER
from components import section_header, market_table, render_html
from assets import GLOBAL_MARKETS, MAJOR_ASSETS
from data_fetcher import get_current_price_and_change
from dashboard_content import get_market_brief, get_todays_watchlist, get_economic_calendar

st.set_page_config(page_title="EquityLens — Dashboard", layout="wide")
apply_theme()

st.markdown("## Dashboard")
st.caption(datetime.now().strftime("%A, %B %d, %Y") + " · Market data via Yahoo Finance, delayed")

st.write("")

# ---------- Fetch every tracked asset once, reused across sections below ----------
tracked_assets = GLOBAL_MARKETS + MAJOR_ASSETS
market_data = []
for label, ticker in tracked_assets:
    price, pct_change = get_current_price_and_change(ticker)
    market_data.append({"label": label, "price": price, "pct_change": pct_change})

global_rows = [(d["label"], d["price"], d["pct_change"]) for d in market_data[: len(GLOBAL_MARKETS)]]
asset_rows = [(d["label"], d["price"], d["pct_change"]) for d in market_data[len(GLOBAL_MARKETS):]]

movable = [d for d in market_data if d["pct_change"] is not None]
gainers = sorted(movable, key=lambda d: d["pct_change"], reverse=True)[:3]
losers = sorted(movable, key=lambda d: d["pct_change"])[:3]
gainer_rows = [(d["label"], d["price"], d["pct_change"]) for d in gainers]
loser_rows = [(d["label"], d["price"], d["pct_change"]) for d in losers]

# ---------- AI Market Brief — the focal point ----------
brief = get_market_brief()
section_header("AI Market Brief", tag="Sample data")

with st.container(border=True):
    render_html(
        f"""
        <div style="font-size:1.4rem; font-weight:700; color:{INK_PRIMARY}; line-height:1.35; margin-bottom:16px;">
            {brief['headline']}
        </div>
        """
    )
    for paragraph in brief["summary"]:
        render_html(
            f'<p style="color:{INK_SECONDARY}; font-size:0.95rem; line-height:1.7; margin-bottom:12px;">{paragraph}</p>'
        )

    render_html(f'<hr style="margin:18px 0 16px 0; border-color:{BORDER};">')

    watch_cols = st.columns(len(brief["watch_items"]))
    for col, item in zip(watch_cols, brief["watch_items"]):
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

# ---------- Today's Watchlist | Economic Calendar ----------
tw_col, ec_col = st.columns(2)

with tw_col:
    section_header("Today's Watchlist", tag="Sample data")
    with st.container(border=True):
        items = get_todays_watchlist()
        for i, item in enumerate(items):
            render_html(
                f'<div style="padding:5px 0; font-size:0.88rem;">'
                f'<b style="color:{INK_PRIMARY};">{item["asset"]}</b>'
                f'<span style="color:{INK_SECONDARY};"> — {item["note"]}</span></div>'
            )
            if i < len(items) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')

with ec_col:
    section_header("Economic Calendar", tag="Sample data")
    with st.container(border=True):
        events = get_economic_calendar()
        for i, event in enumerate(events):
            is_high = event["impact"] == "High"
            impact_color = INK_PRIMARY if is_high else INK_SECONDARY
            impact_weight = "700" if is_high else "500"
            render_html(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0;">
                    <div>
                        <div style="color:{INK_PRIMARY}; font-weight:600; font-size:0.87rem;">{event['event']}</div>
                        <div style="color:{INK_MUTED}; font-size:0.76rem;">{event['when']}</div>
                    </div>
                    <span style="color:{impact_color}; font-weight:{impact_weight}; font-size:0.76rem;
                                text-transform:uppercase; letter-spacing:0.03em;">{event['impact']}</span>
                </div>
                """
            )
            if i < len(events) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')
