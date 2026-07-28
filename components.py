"""Reusable UI building blocks shared across every EquityLens view.

Centralizing markup here (rather than each view hand-rolling its own card
HTML) is what makes five separate pages read as one product.
"""

import textwrap

import streamlit as st

from theme import RATING_COLORS, UP_COLOR, DOWN_COLOR, INK_SECONDARY, INK_PRIMARY
from assets import PREDEFINED_ASSETS

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
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def compact_placeholder(label: str, tag: str = "Planned feature") -> None:
    """A single-line, low-visual-weight marker for a not-yet-built feature.

    Deliberately small — a label plus a muted tag, not a large empty panel —
    so a page with several planned features doesn't read as unfinished.
    """
    render_html(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;
                    background-color:#F4F7FB; border:1px solid #E2E8F0; border-radius:10px;
                    padding:10px 14px; margin-bottom:8px;">
            <span style="font-weight:600; color:{INK_PRIMARY}; font-size:0.88rem;">{label}</span>
            <span style="color:{INK_SECONDARY}; font-size:0.72rem; font-weight:700;
                        text-transform:uppercase; letter-spacing:0.03em;">{tag}</span>
        </div>
        """
    )


def rating_badge_html(rating: str) -> str:
    """Inline HTML for a Financial Health rating badge, embeddable inside a
    larger st.markdown(..., unsafe_allow_html=True) call."""
    color = RATING_COLORS.get(rating, INK_SECONDARY)
    return f'<span class="el-badge" style="background-color:{color}22; color:{color};">{rating}</span>'


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


def price_pill(label: str, price, pct_change, align: str = "left") -> None:
    """A compact price + % change stat card, used in dense strips like
    Markets Today and watchlist rows."""
    price_str = f"${price:,.2f}" if price is not None else "N/A"
    render_html(
        f"""
        <div class="el-card" style="padding:14px 16px; margin-bottom:10px; text-align:{align};">
            <div class="el-card-subtext">{label}</div>
            <div style="font-size:1.1rem; font-weight:700; color:{INK_PRIMARY};">{price_str}</div>
            <div style="font-size:0.82rem;">{price_change_html(pct_change)}</div>
        </div>
        """
    )


def asset_picker(key_prefix: str, default_class: str = "Stocks"):
    """Shared asset-class + asset + custom-ticker selector.

    Used by both Market Research and Trade Studio so ticker selection looks
    and behaves identically everywhere. Returns (ticker, display_name,
    asset_class); ticker is None/empty if the user hasn't typed a custom
    ticker yet.
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
        selected_asset = st.selectbox("Asset", options, key=f"{key_prefix}_asset")

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
