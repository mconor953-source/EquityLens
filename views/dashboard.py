"""EquityLens — Dashboard: a 10-second read on markets and research.

Visual layer only — every computation on this page is unchanged from
before; only presentation changed (KPI strip, a genuine two-column grid,
components.data_table). Sections fetch-then-render one at a time, in the
order they appear on screen, instead of computing everything up front —
that "compute everything, then render everything" ordering was tried in an
earlier pass and caused a real regression: with ~30 network fetches across
this page (market data, six Research Highlights stocks, watchlist, six
Market Structure Watch tickers each needing three intraday timeframes),
nothing at all appeared on screen — not even the page title — until every
fetch finished, 40-50+ seconds on a cold cache. Fetching and rendering each
section together means the page title, KPI strip, and Market Overview all
appear within a few seconds, and the more expensive sections lower on the
page load progressively underneath real, already-visible content.

Market Overview (Global Markets, Major Assets, Market Movers, Market Pulse)
is real, live data, derived from one fetch per tracked asset (see the loop
below) and reused across every section so the page makes exactly one pass
over the network per load for that data. Research Highlights / Watchlist /
Assets to Review / Financial Health Snapshot reuse idea_engine.py and
scoring.py against the app's predefined Stocks universe and the user's
saved Long-Term Investing watchlist — no separate fetch logic, no generated
signals. This is EquityLens's automated research, clearly separate from the
user's own Investment Ideas register (views/investment_ideas.py) — it
informs a decision, it never makes one. Market Pulse / Key Market Signals
are computed by dashboard_content.py the same rule-based way as scoring.py's
Financial Health Score and technicals.py's Technical Rating — real numbers
run through fixed thresholds, never generated text and never AI.
"""

from datetime import datetime

import streamlit as st

from theme import apply_theme, INK_PRIMARY, INK_SECONDARY, INK_MUTED, BORDER, RATING_COLORS, STRUCTURE_COLORS, IMPACT_COLORS
from components import section_header, page_header, market_table, data_table, render_html, stance_badge_html, price_change_html
from assets import GLOBAL_MARKETS, MAJOR_ASSETS, PREDEFINED_ASSETS, STRUCTURE_WATCH_DEFAULT
from data_fetcher import get_price_history, get_ticker_info, is_valid_ticker, format_market_price
from technicals import relative_strength_index, fifty_two_week_range
from dashboard_content import get_market_pulse, get_notable_signals, get_52_week_extremes
from idea_engine import build_investment_idea, stance_for_universe
from structure_engine import build_market_structure
from news_calendar import get_relevant_events
from watchlist_store import load_watchlists

st.set_page_config(page_title="EquityLens — Dashboard", layout="wide")
apply_theme()

# ---------- Page header renders immediately, before any network call ----------
page_header(
    "Dashboard",
    subtitle="Markets, research, and structure at a glance.",
    meta=datetime.now().strftime("%A, %B %d, %Y") + " &middot; Yahoo Finance, delayed",
)


def _build_idea_for_ticker(ticker: str):
    try:
        history = get_price_history(ticker, period="1y")
    except Exception:
        history = None
    if history is None or history.empty:
        return None
    info = get_ticker_info(ticker)
    if not (is_valid_ticker(info) and info.get("quoteType") == "EQUITY"):
        info = None
    price = history["Close"].iloc[-1]
    return build_investment_idea(ticker, ticker, "Stock" if info else "Other", price, history, info)


# =====================================================================
# Tracked assets + this week's events: the two data sources fast enough
# to compute before the KPI strip / Market Overview / What Matters Today
# row, so that row appears within a few seconds rather than after every
# other section on the page has also finished loading.
# =====================================================================
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
advancing = [d for d in movable if d["pct_change"] > 0]
gainers = sorted(movable, key=lambda d: d["pct_change"], reverse=True)[:3]
losers = sorted(movable, key=lambda d: d["pct_change"])[:3]
gainer_rows = [(d["label"], d["price"], d["pct_change"]) for d in gainers]
loser_rows = [(d["label"], d["price"], d["pct_change"]) for d in losers]

pulse = get_market_pulse(market_data)
notable_signals = get_notable_signals(market_data)

watchlist_tickers = load_watchlists().get("Long-Term Investing", [])

seen_titles = set()
all_relevant = []
calendar_available = False
for currency_proxy_ticker, cls in (("^GSPC", "Indices"), ("^FTSE", "Indices"), ("EURUSD=X", "Forex"), ("USDJPY=X", "Forex")):
    r = get_relevant_events(currency_proxy_ticker, cls, max_events=10)
    if r["available"]:
        calendar_available = True
        all_relevant.extend(r["events"])
all_relevant.sort(key=lambda e: e["time"])
deduped_events = []
for e in all_relevant:
    key = (e["title"], e["currency"], e["time"])
    if key not in seen_titles:
        seen_titles.add(key)
        deduped_events.append(e)
deduped_events = deduped_events[:6]

# ---------- KPI strip ----------
kpi_cols = st.columns(4)
with kpi_cols[0]:
    st.metric("Market Breadth", f"{len(advancing)} / {len(movable)}", help="Assets advancing vs. total tracked with a computable change.")
with kpi_cols[1]:
    if gainers:
        st.metric("Biggest Mover", gainers[0]["label"], f"{gainers[0]['pct_change']:+.2f}%")
    else:
        st.metric("Biggest Mover", "N/A")
with kpi_cols[2]:
    if not calendar_available:
        st.metric("Event Risk", "N/A", help="Economic calendar unavailable right now.")
    else:
        st.metric("Event Risk", "HIGH" if deduped_events else "Low", help=f"{len(deduped_events)} high-impact event(s) scheduled this week.")
with kpi_cols[3]:
    st.metric("Watchlist Size", str(len(watchlist_tickers)), help="Tickers saved to Long-Term Investing.")

st.write("")

# ---------- Market Overview (left, wide) | What Matters Today (right) ----------
overview_col, matters_col = st.columns([1.7, 1])

with overview_col:
    section_header("Market Overview")
    with st.container(border=True):
        ov_tabs = st.tabs(["Global Markets", "Major Assets", "Movers"])
        with ov_tabs[0]:
            market_table(global_rows)
        with ov_tabs[1]:
            market_table(asset_rows)
        with ov_tabs[2]:
            mv1, mv2 = st.columns(2)
            with mv1:
                st.markdown("###### Gainers")
                market_table(gainer_rows) if gainer_rows else st.caption("No data available.")
            with mv2:
                st.markdown("###### Losers")
                market_table(loser_rows) if loser_rows else st.caption("No data available.")

with matters_col:
    section_header("What Matters Today")
    with st.container(border=True):
        render_html(f'<div style="font-size:1.05rem; font-weight:700; color:{INK_PRIMARY}; line-height:1.35; margin-bottom:10px;">{pulse["headline"]}</div>')
        for paragraph in pulse["summary"]:
            render_html(f'<p style="color:{INK_SECONDARY}; font-size:0.85rem; line-height:1.55; margin-bottom:8px;">{paragraph}</p>')
        if notable_signals:
            render_html(f'<hr style="margin:10px 0; border-color:{BORDER};">')
            render_html(f'<div class="el-section-label">Momentum Extremes</div>')
            for i, item in enumerate(notable_signals[:3]):
                render_html(
                    f'<div style="padding:3px 0; font-size:0.82rem;"><b style="color:{INK_PRIMARY};">{item["asset"]}</b>'
                    f'<span style="color:{INK_SECONDARY};"> — {item["note"]}</span></div>'
                )

st.write("")

# =====================================================================
# Watchlist — fetched and rendered together, right where it appears.
# =====================================================================
section_header("Watchlist", subtitle="Live price and automated research read on your saved Long-Term Investing watchlist — reference only.")
if not watchlist_tickers:
    st.info("No tickers saved yet — add some on the Watchlists page.")
else:
    with st.spinner("Loading watchlist..."):
        watchlist_rows = []
        for ticker in watchlist_tickers:
            idea = _build_idea_for_ticker(ticker)
            price, pct_change = None, None
            try:
                hist = get_price_history(ticker, period="5d")
                if hist is not None and not hist.empty:
                    price = hist["Close"].iloc[-1]
                    if len(hist) > 1:
                        prev = hist["Close"].iloc[-2]
                        pct_change = (price - prev) / prev * 100 if prev else None
            except Exception:
                pass
            watchlist_rows.append({"ticker": ticker, "price": price, "pct_change": pct_change, "idea": idea})

    table_rows = []
    for row in watchlist_rows:
        idea = row["idea"]
        stance_cell = stance_badge_html(idea["stance"]) if idea else '<span style="color:' + INK_MUTED + ';">N/A</span>'
        conviction_cell = f"{idea['conviction']}/100" if idea else "—"
        horizon_cell = idea["horizon"] if idea else "—"
        table_rows.append([
            f"<b>{row['ticker']}</b>",
            format_market_price(row["price"]),
            price_change_html(row["pct_change"]),
            stance_cell,
            conviction_cell,
            horizon_cell,
        ])
    data_table(["Asset", "Price", "1D", "Stance", "Conviction", "Horizon"], table_rows, right_align_cols={1})

st.write("")

# =====================================================================
# Research Highlights | Market Structure Watch — the two most expensive
# sections (six stocks' worth of analysis each), fetched together right
# before they render, with everything above already visible by this point.
# =====================================================================
stock_universe = list(PREDEFINED_ASSETS["US Stocks"].items())  # [(display_name, ticker), ...]
research_col, structure_col = st.columns(2)

with research_col:
    section_header("Research Highlights", subtitle="Automated Conviction Score, ranked highest to lowest — reference only.")
    with st.container(border=True):
        with st.spinner("Building investment ideas..."):
            ideas = []
            for display_name, ticker in stock_universe:
                idea = _build_idea_for_ticker(ticker)
                if idea:
                    idea["display_name"] = display_name
                    ideas.append(idea)
            ranked_ideas = stance_for_universe(ideas)

        top_ideas = ranked_ideas[:5]
        if not top_ideas:
            st.caption("Not enough data to rank research highlights right now.")
        for i, idea in enumerate(top_ideas):
            reason = idea["positives"][0] if idea["positives"] else (idea["risks"][0] if idea["risks"] else "No standout drivers identified.")
            cols = st.columns([0.9, 1, 0.9, 2.6])
            cols[0].markdown(f"**{idea['ticker']}**")
            with cols[1]:
                render_html(stance_badge_html(idea["stance"]))
            cols[2].markdown(f"{idea['conviction']}/100")
            with cols[3]:
                render_html(f'<span style="color:{INK_SECONDARY}; font-size:0.82rem;">{reason}</span>')
            if i < len(top_ideas) - 1:
                render_html(f'<hr style="margin:5px 0; border-color:{BORDER};">')

with structure_col:
    section_header("Market Structure Watch", subtitle="Price structure across a curated, intraday-active watchlist.")
    with st.container(border=True):
        with st.spinner("Analyzing structure..."):
            structure_watch_results = []
            for label, watch_ticker in STRUCTURE_WATCH_DEFAULT:
                try:
                    structure_watch_results.append((label, build_market_structure(watch_ticker)))
                except Exception:
                    structure_watch_results.append((label, None))

        for i, (label, struct_result) in enumerate(structure_watch_results):
            if struct_result is None:
                render_html(
                    f'<div style="display:flex; justify-content:space-between; padding:5px 0;">'
                    f'<b style="color:{INK_PRIMARY};">{label}</b><span style="color:{INK_MUTED};">Unavailable</span></div>'
                )
            else:
                direction = struct_result["direction"]
                color = STRUCTURE_COLORS.get(direction, STRUCTURE_COLORS["neutral"]) if direction else STRUCTURE_COLORS["neutral"]
                render_html(
                    f'<div style="display:flex; justify-content:space-between; align-items:baseline; padding:5px 0;">'
                    f'<b style="color:{INK_PRIMARY};">{label}</b>'
                    f'<span style="color:{color}; font-weight:600; font-size:0.85rem;">{struct_result["state_label"]}</span></div>'
                )
            if i < len(structure_watch_results) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')

to_review = [i for i in ranked_ideas if i["stance"] in ("REDUCE", "AVOID")]
healthy = [i for i in ranked_ideas if i["financial_health"] is not None]

st.write("")

# ---------- Assets to Review | Financial Health Snapshot ----------
review_col, health_col = st.columns(2)

with review_col:
    section_header("Assets to Review", subtitle="Lowest-conviction names — REDUCE or AVOID stance.")
    with st.container(border=True):
        if not to_review:
            st.caption("No tracked stocks currently carry a REDUCE or AVOID stance.")
        for i, idea in enumerate(to_review):
            key_risk = idea["risks"][0] if idea["risks"] else "No specific risk flagged."
            render_html(
                f"""
                <div style="padding:6px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:baseline;">
                        <b style="color:{INK_PRIMARY};">{idea['ticker']}</b>
                        {stance_badge_html(idea['stance'])}
                    </div>
                    <div style="color:{INK_SECONDARY}; font-size:0.82rem; margin-top:2px;">{key_risk}</div>
                </div>
                """
            )
            if i < len(to_review) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')

with health_col:
    section_header("Financial Health Snapshot", subtitle="Financial Health Score for each tracked stock.")
    with st.container(border=True):
        if not healthy:
            st.caption("Fundamental data unavailable.")
        for i, idea in enumerate(healthy):
            health = idea["financial_health"]
            fh_color = RATING_COLORS.get(health["rating"], INK_SECONDARY)
            render_html(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0;">
                    <b style="color:{INK_PRIMARY};">{idea['ticker']}</b>
                    <span style="color:{fh_color}; font-size:0.85rem; font-weight:600;">{health['total_score']}/100 &middot; {health['rating']}</span>
                </div>
                """
            )
            if i < len(healthy) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')

st.write("")

# ---------- Upcoming Events | 52-Week Extremes ----------
extremes_52w = get_52_week_extremes(market_data)
events_col, extremes_col = st.columns(2)

with events_col:
    section_header("Upcoming High-Impact Events", subtitle="USD, GBP, EUR and JPY events scheduled this week.")
    with st.container(border=True):
        if not calendar_available:
            st.caption("Economic calendar unavailable right now.")
        elif not deduped_events:
            st.caption("No high-impact events scheduled this week.")
        else:
            for i, event in enumerate(deduped_events):
                impact_color = IMPACT_COLORS.get(event["impact"], INK_MUTED)
                render_html(
                    f"""
                    <div style="padding:5px 0;">
                        <span style="color:{impact_color}; font-weight:700; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em;">{event['impact']}</span>
                        <span style="color:{INK_PRIMARY}; font-weight:600; margin-left:6px;">{event['title']}</span>
                        <span style="color:{INK_MUTED}; font-size:0.8rem; margin-left:6px;">({event['currency']}) in {event['time_until']}</span>
                    </div>
                    """
                )
                if i < len(deduped_events) - 1:
                    render_html(f'<hr style="margin:2px 0; border-color:{BORDER};">')

with extremes_col:
    section_header("52-Week Extremes", subtitle="Assets trading within 3% of their trailing 52-week high or low.")
    with st.container(border=True):
        if not extremes_52w:
            st.caption("No tracked assets are currently near a 52-week high or low.")
        for i, item in enumerate(extremes_52w):
            is_high = item["flag"] == "Near High"
            flag_color = INK_PRIMARY if is_high else INK_SECONDARY
            render_html(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0;">
                    <div>
                        <div style="color:{INK_PRIMARY}; font-weight:600; font-size:0.85rem;">{item['asset']}</div>
                        <div style="color:{INK_MUTED}; font-size:0.74rem;">{item['note']}</div>
                    </div>
                    <span style="color:{flag_color}; font-weight:700; font-size:0.74rem;
                                text-transform:uppercase; letter-spacing:0.03em;">{item['flag']}</span>
                </div>
                """
            )
            if i < len(extremes_52w) - 1:
                render_html(f'<hr style="margin:4px 0; border-color:{BORDER};">')
