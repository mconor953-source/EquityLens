"""Reusable UI building blocks shared across every EquityLens view.

Centralizing markup here (rather than each view hand-rolling its own card
HTML) is what makes five separate pages read as one product.
"""

import textwrap

import streamlit as st

from theme import (
    RATING_COLORS, STANCE_COLORS, UP_COLOR, DOWN_COLOR, INK_SECONDARY, INK_PRIMARY, INK_MUTED,
    BORDER, RADIUS_SM, TECHNICAL_RATING_COLORS, TECHNICAL_RATING_ORDER,
)
from assets import PREDEFINED_ASSETS, POPULAR_ASSETS
from data_fetcher import format_market_price

POPULAR_LABEL = "Popular"


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


def page_header(title: str, subtitle: str = None, meta: str = None) -> None:
    """The compact research-terminal header every page opens with: a page
    title, a one-line description, and an optional right-aligned metadata
    string (e.g. "Last updated 15:26") — replacing the old pattern of a
    bare st.markdown("## Title") + st.caption(...) floating against empty
    page background."""
    meta_html = f'<div class="el-page-meta">{meta}</div>' if meta else ""
    subtitle_html = f'<div class="el-page-subtitle">{subtitle}</div>' if subtitle else ""
    render_html(
        f"""
        <div class="el-page-header">
            <div>
                <div class="el-page-title">{title}</div>
                {subtitle_html}
            </div>
            {meta_html}
        </div>
        """
    )


def data_table(headers: list, rows: list, right_align_cols: set = frozenset()) -> None:
    """A real, CSS-styled HTML <table> — soft blue-grey header, white rows,
    subtle separators, tabular numerals, hover state. Used in place of
    st.dataframe wherever the table is read-only display (st.dataframe's
    canvas-rendered grid can't be restyled with CSS at all, so it's kept
    only where its native row-selection behavior is actually used —
    Investment Ideas' saved-ideas register).

    `rows` is a list of lists/tuples of already-formatted cell strings
    (plain text or a small HTML fragment like a colored badge — this
    function does not escape cell content, so callers control exactly
    what's safe to embed, same convention as the rest of this module).
    `right_align_cols` is a set of column indices to right-align (for
    price/number columns).
    """
    head_cells = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            cls = ' class="el-num"' if i in right_align_cols else ""
            cells.append(f"<td{cls}>{value}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    render_html(
        f"""
        <div class="el-table-wrap">
        <table class="el-table">
            <thead><tr>{head_cells}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
        </table>
        </div>
        """
    )


def status_line_html(label: str, value: str, color: str) -> str:
    """A compact structured status readout — small uppercase label, a thin
    colored left accent bar, and a strong value underneath. Deliberately
    not a filled colored pill/badge: research-terminal software leans on
    typography and a restrained accent line for a headline state (Technical
    View, Market Structure status, Research Summary) rather than a bright
    box of color."""
    return (
        f'<div class="el-status" style="border-left-color:{color};">'
        f'<div class="el-status-label">{label}</div>'
        f'<div class="el-status-value" style="color:{color};">{value}</div>'
        f'</div>'
    )


def sentiment_meter_html(current_label: str, order: tuple = TECHNICAL_RATING_ORDER, colors: dict = TECHNICAL_RATING_COLORS) -> str:
    """A restrained horizontal 5-segment meter (Strong Sell | Sell | Neutral
    | Buy | Strong Buy) with the current state's segment highlighted —
    reads as a real financial sentiment indicator rather than a bare label.
    Segments are always shown in the same fixed order regardless of which
    one is active, so the meter's shape never changes, only which segment
    lights up."""
    segments = []
    for label in order:
        active = label == current_label
        color = colors.get(label, INK_MUTED)
        opacity = "1" if active else "0.18"
        segments.append(f'<div style="background-color:{color}; opacity:{opacity};" title="{label}"></div>')
    labels_row = "".join(
        f'<span style="flex:1; text-align:center; font-size:0.62rem; font-weight:{700 if l == current_label else 500}; '
        f'color:{colors.get(l, INK_MUTED) if l == current_label else INK_MUTED}; text-transform:uppercase; letter-spacing:0.02em;">{l}</span>'
        for l in order
    )
    return (
        f'<div class="el-sentiment-track">{"".join(segments)}</div>'
        f'<div style="display:flex; margin-top:4px;">{labels_row}</div>'
    )


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


def stance_badge_html(stance: str) -> str:
    """Inline HTML for a stance chip — BUY/HOLD/REDUCE/AVOID from
    idea_engine.py's automated Conviction Score (Dashboard, Watchlists) or
    BUY/HOLD/SELL from the user's manual Investment Ideas register — same
    status-chip style as rating_badge_html, colored per theme.STANCE_COLORS."""
    color = STANCE_COLORS.get(stance, INK_SECONDARY)
    return (
        f'<span style="display:inline-flex; align-items:center; gap:6px; '
        f'font-weight:700; font-size:0.85rem; color:{color}; text-transform:uppercase; letter-spacing:0.03em;">'
        f'<span style="width:7px; height:7px; border-radius:50%; background-color:{color}; '
        f'display:inline-block; flex-shrink:0;"></span>{stance}</span>'
    )


def render_stance_badge(stance: str) -> None:
    st.markdown(stance_badge_html(stance), unsafe_allow_html=True)


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


def asset_picker(key_prefix: str, default_class: str = "US Stocks", default_asset: str = None):
    """Search-first asset selector: a free-text ticker search up top (any
    Yahoo Finance symbol — NVDA, GBPJPY=X, BTC-USD, ^GSPC, ...), with a
    curated "Popular" + per-class browser underneath for anyone who'd
    rather click than type. Returns (ticker, display_name, asset_class);
    ticker is None if nothing has been chosen or typed yet.

    The curated list in assets.py is a starting point for browsing, not a
    restriction — a typed symbol Yahoo Finance doesn't recognize is caught
    downstream by the calling view (get_price_history fails, the view shows
    "No data found") exactly like a bad symbol picked from the list would
    be, so there's no separate validation path to keep in sync here.

    Investment Ideas does not use this — it takes a free-typed ticker in
    its own Add Idea form, since the user is logging a specific asset they
    already have in mind rather than browsing a predefined list.

    `default_class`/`default_asset` (from Settings, see settings_store.py)
    only seed the *initial* widget value — like any Streamlit widget, once
    the user has picked something in this session that choice sticks, even
    if Settings changes afterward. They take effect the next time the page
    is opened fresh.
    """
    search_query = st.text_input(
        "Search ticker or asset",
        placeholder="e.g. NVDA, AAPL, GBPJPY=X, BTC-USD, ^GSPC — any Yahoo Finance symbol",
        key=f"{key_prefix}_search",
    ).strip().upper()

    if search_query:
        return search_query, search_query, "Search"

    st.caption("Or browse popular assets:")
    classes = [POPULAR_LABEL] + list(PREDEFINED_ASSETS.keys())
    default_index = classes.index(default_class) if default_class in classes else 0

    class_col, asset_col = st.columns(2)
    with class_col:
        asset_class = st.selectbox(
            "Asset class", classes, index=default_index, key=f"{key_prefix}_class"
        )
    with asset_col:
        if asset_class == POPULAR_LABEL:
            catalog = {name: (ticker, cls) for name, ticker, cls in POPULAR_ASSETS}
        else:
            catalog = {name: (ticker, asset_class) for name, ticker in PREDEFINED_ASSETS[asset_class].items()}
        options = list(catalog.keys())
        asset_index = options.index(default_asset) if default_asset in options else 0
        selected_asset = st.selectbox("Asset", options, index=asset_index, key=f"{key_prefix}_asset")

    ticker, resolved_class = catalog[selected_asset]
    return ticker, selected_asset, resolved_class
