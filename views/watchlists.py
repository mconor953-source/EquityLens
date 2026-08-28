"""EquityLens — Watchlists: two persistent, workspace-style ticker lists.

Long-Term Investing shows idea_engine.py's automated stance/conviction read
for each holding — reference research, not a decision — so a glance at the
list tells you which names currently look attractive, neutral, or weak.
Momentum Watchlist keeps the existing rule-based Technical Rating, Market
Structure read, and Event Risk flag for shorter-lookback monitoring. Either
tab can hand a ticker off to the user's own Investment Ideas register via
the "Create Idea" action, which prefills the asset only — never the stance
or conviction.
"""

from datetime import datetime

import streamlit as st

from theme import apply_theme, INK_SECONDARY, INK_MUTED, TECHNICAL_RATING_COLORS, STRUCTURE_COLORS, IMPACT_COLORS
from components import price_change_html, stance_badge_html, page_header, data_table
from data_fetcher import (
    get_current_price_and_change,
    get_ticker_info,
    get_price_history,
    is_valid_ticker,
    format_market_price,
    classify_asset_class,
)
from idea_engine import build_investment_idea
from technicals import compute_technical_rating
from structure_engine import build_market_structure
from news_calendar import get_relevant_events
from watchlist_store import load_watchlists, add_ticker, remove_ticker


def _create_idea_from_ticker(ticker: str, asset_class_label: str) -> None:
    """Hand off to Investment Ideas with the asset/ticker/class prefilled —
    the BUY/HOLD/SELL decision, conviction, and thesis stay manual."""
    st.session_state["idea_prefill"] = {"ticker": ticker, "asset_class": asset_class_label}
    st.switch_page("views/investment_ideas.py")


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
    if button_col.button("Add", key=f"add_button_{watchlist_name}", use_container_width=True, type="primary"):
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


def manage_row(watchlist_name: str, tickers: list) -> None:
    """A compact 'act on one ticker' row below the read-only table — the
    table itself (components.data_table) is plain styled HTML with no
    interactive cells, so Create Idea / Remove live here instead of as
    per-row buttons."""
    if not tickers:
        return
    m1, m2, m3 = st.columns([2, 1, 1])
    chosen = m1.selectbox("Manage a ticker", tickers, key=f"manage_select_{watchlist_name}", label_visibility="collapsed")
    if m2.button("Create Idea", key=f"manage_idea_{watchlist_name}", use_container_width=True):
        asset_class_label = classify_asset_class(get_ticker_info(chosen))
        _create_idea_from_ticker(chosen, asset_class_label)
    if m3.button("Remove", key=f"manage_remove_{watchlist_name}", use_container_width=True):
        remove_ticker(watchlist_name, chosen)
        st.rerun()


st.set_page_config(page_title="EquityLens — Watchlists", layout="wide")
apply_theme()

page_header("Watchlists", subtitle="Two persistent, purpose-built lists for ongoing monitoring.")

watchlists = load_watchlists()
last_updated = datetime.now().strftime("%H:%M:%S")

long_term_tab, momentum_tab = st.tabs(["Long-Term Investing", "Momentum Watchlist"])

# ---------- Long-Term Investing ----------
with long_term_tab:
    st.caption(
        "Live price and EquityLens's automated research read (stance, conviction) for each holding — "
        "reference only, not your decision. Fundamentals are used where the ticker is an equity; "
        "otherwise the view is price trend and momentum only."
    )
    add_remove_row("Long-Term Investing")
    st.write("")

    tickers = watchlists.get("Long-Term Investing", [])
    if not tickers:
        st.info("No tickers yet — add one above.")
    else:
        rows = []
        for ticker in tickers:
            price, pct_change = get_current_price_and_change(ticker)
            try:
                history = get_price_history(ticker, period="1y")
            except Exception:
                history = None

            raw_info = get_ticker_info(ticker)
            asset_class_label = classify_asset_class(raw_info)
            info = raw_info if (is_valid_ticker(raw_info) and raw_info.get("quoteType") == "EQUITY") else None

            idea = build_investment_idea(ticker, ticker, asset_class_label, price, history, info) if history is not None else None

            if idea:
                stance_cell = stance_badge_html(idea["stance"])
                conviction_cell = f"{idea['conviction']}/100"
                trend_cell = idea["trend_label"]
                key_risk = idea["risks"][0] if idea["risks"] else "No material risk flagged"
                risk_cell = f'<span title="{key_risk}" style="display:inline-block; max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; vertical-align:bottom;">{key_risk}</span>'
            else:
                na = f'<span style="color:{INK_MUTED};">N/A</span>'
                stance_cell = conviction_cell = trend_cell = risk_cell = na

            rows.append([
                f"<b>{ticker}</b>", format_market_price(price), price_change_html(pct_change),
                stance_cell, conviction_cell, trend_cell, risk_cell, last_updated,
            ])
        data_table(["Asset", "Price", "1D", "Stance", "Conviction", "Trend", "Key Risk", "Updated"], rows, right_align_cols={1})
        st.write("")
        manage_row("Long-Term Investing", tickers)

# ---------- Momentum Watchlist ----------
with momentum_tab:
    st.caption(
        "Live price, rule-based Technical Rating, Market Structure read, and event risk for each ticker — "
        "the same models used on Market Research and Market Structure."
    )
    add_remove_row("Momentum Watchlist")
    st.write("")

    tickers = watchlists.get("Momentum Watchlist", [])
    if not tickers:
        st.info("No tickers yet — add one above.")
    else:
        rows = []
        for ticker in tickers:
            price, pct_change = get_current_price_and_change(ticker)
            try:
                history = get_price_history(ticker, period="1y")
            except Exception:
                history = None
            technical = compute_technical_rating(history) if history is not None else None
            asset_class_label = classify_asset_class(get_ticker_info(ticker))

            if technical:
                rating_color = TECHNICAL_RATING_COLORS.get(technical["rating"], INK_SECONDARY)
                technical_cell = f'<b style="color:{rating_color};">{technical["rating"]}</b>'
            else:
                technical_cell = f'<span style="color:{INK_MUTED};">N/A</span>'

            try:
                structure = build_market_structure(ticker)
            except Exception:
                structure = None
            if structure:
                struct_color = STRUCTURE_COLORS.get(structure["direction"], STRUCTURE_COLORS["neutral"]) if structure["direction"] else STRUCTURE_COLORS["neutral"]
                structure_cell = f'<b style="color:{struct_color};">{structure["state_label"]}</b>'
            else:
                structure_cell = f'<span style="color:{INK_MUTED};">Unavailable</span>'

            events = get_relevant_events(ticker, asset_class_label)
            if not events["available"]:
                event_cell = f'<span style="color:{INK_MUTED};">N/A</span>'
            elif events["events"]:
                event_cell = f'<b style="color:{IMPACT_COLORS["High"]};">HIGH</b>'
            else:
                event_cell = f'<span style="color:{INK_MUTED};">Low</span>'

            rows.append([
                f"<b>{ticker}</b>", format_market_price(price), price_change_html(pct_change),
                technical_cell, structure_cell, event_cell, last_updated,
            ])
        data_table(["Asset", "Price", "1D", "Technical", "Structure", "Event Risk", "Updated"], rows, right_align_cols={1})
        st.write("")
        manage_row("Momentum Watchlist", tickers)
