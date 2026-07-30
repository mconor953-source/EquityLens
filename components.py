"""Reusable UI building blocks shared across every EquityLens view.

Centralizing markup here (rather than each view hand-rolling its own card
HTML) is what makes five separate pages read as one product.
"""

import textwrap

import streamlit as st

from theme import RATING_COLORS, UP_COLOR, DOWN_COLOR, INK_SECONDARY, INK_PRIMARY, INK_MUTED, BORDER, RADIUS_SM
from assets import PREDEFINED_ASSETS
from data_fetcher import format_market_price

CUSTOM_OPTION = "Custom ticker..."


def render_html(html: str) -> None:
    """Render a multi-line HTML string safely.

    st.markdown runs content through a CommonMark parser even with
    unsafe_allow_html=True — a block indented 4+ spaces (which any HTML
    written to match surrounding Python indentation will be) gets parsed as
    an indented code block and shown as literal text instead of HTML. Every
    HTML block in this app must go through this helper instead of calling
    st.markdown directly, so that can't happen.
    """
    st.markdown(textwrap.dedent(html).strip(), unsafe_allow_html=True)


def section_header(title: str, subtitle: str = None) -> None:
    """A section title with an optional caption beneath it."""
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def rating_badge_html(rating: str) -> str:
    """Inline HTML for a Financial Health rating indicator — a small colored
    dot plus neutral text, in the style of a status chip rather than a
    filled colored pill. Embeddable inside a larger
    st.markdown(..., unsafe_allow_html=True) call."""
    color = RATING_COLORS.get(rating, INK_SECONDARY)
    return (
        f'<span style="display:inline-flex; align-items:center; gap:6px; '
        f'font-weight:600; font-size:0.85rem; color:{INK_PRIMARY};">'
        f'<span style="width:7px; height:7px; border-radius:50%; background-color:{color}; '
        f'display:inline-block; flex-shrink:0;"></span>{rating}</span>'
    )


def render_rating_badge(rating: str) -> None:
    st.markdown(rating_badge_html(rating), unsafe_allow_html=True)


def price_change_html(pct_change) -> str:
    """Colored, arrowed % change span. Never color-only — always paired with
    the numeric value and an arrow glyph."""
    if pct_change is None:
        return f'<span style="color:{INK_SECONDARY};">N/A</span>'
    color = UP_COLOR if pct_change >= 0 else DOWN_COLOR
    arrow = "▲" if pct_change >= 0 else "▼"
    return f'<span style="color:{color}; font-weight:700;">{arrow} {pct_change:+.2f}%</span>'


def market_row(label: str, price, pct_change) -> None:
    """One dense row of a market-data table: label | price | change.

    This is what replaces one-card-per-asset with a single scannable table
    inside one card — the pattern that makes market data read like a
    terminal rather than a grid of separate widgets.
    """
    label_col, price_col, change_col = st.columns([2, 1.3, 1.3])
    label_col.markdown(f"**{label}**")
    price_col.markdown(format_market_price(price))
    with change_col:
        render_html(price_change_html(pct_change))


def market_table(rows) -> None:
    """Render a list of (label, price, pct_change) tuples as a dense table
    with hairline dividers between rows — used for Global Markets, Major
    Assets, and Market Movers so each is one scannable table, not several
    separate cards."""
    for i, (label, price, pct_change) in enumerate(rows):
        market_row(label, price, pct_change)
        if i < len(rows) - 1:
            render_html(f'<hr style="margin:6px 0; border-color:{BORDER};">')


def signal_tag_html(signal: str) -> str:
    """Small colored tag for a Buy/Sell/Neutral technical signal — a lighter,
    denser variant of rating_badge_html sized for inline use in a signal
    list rather than as a standalone headline badge."""
    colors = {"Buy": UP_COLOR, "Sell": DOWN_COLOR, "Neutral": INK_MUTED}
    color = colors.get(signal, INK_SECONDARY)
    return (
        f'<span style="display:inline-block; padding:2px 8px; border-radius:{RADIUS_SM}; '
        f'background-color:{color}1A; color:{color}; font-size:0.7rem; font-weight:700; '
        f'text-transform:uppercase; letter-spacing:0.03em; white-space:nowrap;">{signal}</span>'
    )


def signal_row(name: str, detail: str, signal: str) -> None:
    """One row of a Technical Rating signal breakdown: indicator name |
    plain-English detail | colored Buy/Sell/Neutral tag."""
    name_col, detail_col, tag_col = st.columns([1.3, 2.7, 1])
    name_col.markdown(f"**{name}**")
    with detail_col:
        render_html(f'<span style="color:{INK_SECONDARY}; font-size:0.85rem;">{detail}</span>')
    with tag_col:
        render_html(signal_tag_html(signal))


def signal_list(signals) -> None:
    """Render a list of {name, detail, signal} dicts (as produced by
    technicals.compute_technical_rating) as dense rows with hairline
    dividers — the Technical Analysis equivalent of market_table."""
    for i, sig in enumerate(signals):
        signal_row(sig["name"], sig["detail"], sig["signal"])
        if i < len(signals) - 1:
            render_html(f'<hr style="margin:6px 0; border-color:{BORDER};">')


def asset_picker(key_prefix: str, default_class: str = "Stocks", default_asset: str = None):
    """Shared asset-class + asset + custom-ticker selector.

    Used by both Market Research and Trade Studio so ticker selection looks
    and behaves identically everywhere. Returns (ticker, display_name,
    asset_class); ticker is None/empty if the user hasn't typed a custom
    ticker yet.

    `default_class`/`default_asset` (from Settings, see settings_store.py)
    only seed the *initial* widget value — like any Streamlit widget, once
    the user has picked something in this session that choice sticks, even
    if Settings changes afterward. They take effect the next time the page
    is opened fresh.
    """
    classes = list(PREDEFINED_ASSETS.keys())
    default_index = classes.index(default_class) if default_class in classes else 0

    class_col, asset_col = st.columns(2)
    with class_col:
        asset_class = st.selectbox(
            "Asset class", classes, index=default_index, key=f"{key_prefix}_class"
        )
    with asset_col:
        options = list(PREDEFINED_ASSETS[asset_class].keys()) + [CUSTOM_OPTION]
        asset_index = options.index(default_asset) if default_asset in options else 0
        selected_asset = st.selectbox("Asset", options, index=asset_index, key=f"{key_prefix}_asset")

    if selected_asset == CUSTOM_OPTION:
        ticker = st.text_input(
            "Yahoo Finance ticker",
            placeholder="e.g. AAPL, BTC-USD, EURUSD=X, GC=F, ^GSPC",
            key=f"{key_prefix}_custom_ticker",
        ).strip().upper()
        display_name = ticker
    else:
        ticker = PREDEFINED_ASSETS[asset_class][selected_asset]
        display_name = selected_asset

    return (ticker or None), display_name, asset_class
