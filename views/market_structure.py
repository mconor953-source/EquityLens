"""EquityLens — Market Structure: multi-timeframe price-structure analysis.

Answers a different question than Market Research: not "what do indicators
and fundamentals say," but "what is price doing across 4H/1H/15m/5m, and is
a break -> correction -> continuation sequence developing." Powered by
market_structure.py's deterministic engine — no AI, no screenshot
recognition, no fake win probabilities, and no trade execution/entry/
stop/size recommendations anywhere on this page (see the caption at the
bottom). This is a completely separate, optional page: a long-term investor
never needs to open it, and nothing here feeds into Investment Ideas
automatically — see views/investment_ideas.py, which stays entirely manual.
"""

import streamlit as st
import plotly.graph_objects as go

from theme import (
    apply_theme, INK_PRIMARY, INK_SECONDARY, INK_MUTED, BORDER, CARD_BG, RADIUS,
    STRUCTURE_COLORS, IMPACT_COLORS, ACCENT_TEAL, RED, AMBER,
)
from components import asset_picker, render_html, price_change_html, page_header, status_line_html
from data_fetcher import get_current_price_and_change, format_market_price
from structure_engine import build_market_structure, phase_status, DEFAULT_SENSITIVITY, REQUIRE_CANDLE_CLOSE
from news_calendar import get_relevant_events
from settings_store import load_settings

st.set_page_config(page_title="EquityLens — Market Structure", layout="wide")
apply_theme()

MAJOR_SWING_COUNT = 8  # chart display only — how many of the most recent swings render as full-size, labeled markers

page_header(
    "Market Structure",
    subtitle="Multi-timeframe price structure and key levels — identifies structure only, never trades, sizes, or sets stops.",
)

settings = load_settings()
ticker, display_name, asset_class = asset_picker(
    "market_structure",
    default_class=settings.get("default_asset_class", "US Stocks"),
    default_asset=settings.get("default_asset"),
)

if not ticker:
    st.info("Enter a ticker symbol to continue.")
    st.stop()

with st.spinner(f"Analyzing structure for {ticker} across 4H / 1H / 15m / 5m..."):
    result = build_market_structure(ticker)

current_price, pct_change = get_current_price_and_change(ticker)

direction = result["direction"]
struct_color = STRUCTURE_COLORS["neutral"]
if direction == "bullish":
    struct_color = STRUCTURE_COLORS["bullish"] if "confirmed" in result["state"] or "breakout" in result["state"] or "breakdown" in result["state"] else STRUCTURE_COLORS["developing"]
elif direction == "bearish":
    struct_color = STRUCTURE_COLORS["bearish"] if "confirmed" in result["state"] or "breakdown" in result["state"] else STRUCTURE_COLORS["developing"]
if result["state"] == "invalidated":
    struct_color = STRUCTURE_COLORS["neutral"]

# =====================================================================
# HEADER — asset, price, structure status
# =====================================================================
render_html(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end;
                border-bottom:1px solid {BORDER}; padding-bottom:14px; margin-bottom:18px;">
        <div>
            <div class="el-header">{display_name}</div>
            <div class="el-subtext">{ticker} &middot; {asset_class}</div>
        </div>
        <div style="display:flex; gap:28px; align-items:flex-end;">
            <div style="text-align:right;">
                <div style="font-size:1.4rem; font-weight:700; color:{INK_PRIMARY}; font-variant-numeric:tabular-nums;">
                    {format_market_price(current_price) if current_price is not None else "N/A"}
                </div>
                <div style="font-size:0.86rem; margin-top:1px;">{price_change_html(pct_change)}</div>
            </div>
            {status_line_html("Market Structure Status", result["state_label"], struct_color)}
        </div>
    </div>
    """
)

# =====================================================================
# MULTI-TIMEFRAME STRUCTURE — four compact panels
# =====================================================================
st.markdown("#### Multi-Timeframe Structure")
tf_cols = st.columns(4)
for col, label in zip(tf_cols, ("4H", "1H", "15m", "5m")):
    bundle = result["timeframes"][label]
    with col:
        if bundle is None:
            render_html(
                f'<div class="el-panel" style="text-align:center;">'
                f'<div class="el-section-label" style="margin-bottom:6px;">{label}</div>'
                f'<div style="font-size:0.95rem; font-weight:600; color:{INK_MUTED};">Insufficient Data</div></div>'
            )
        else:
            bias_color = STRUCTURE_COLORS.get(bundle["bias"], STRUCTURE_COLORS["neutral"])
            render_html(
                f'<div class="el-panel" style="text-align:center;">'
                f'<div class="el-section-label" style="margin-bottom:6px;">{label}</div>'
                f'<div style="font-size:1.05rem; font-weight:700; color:{bias_color}; text-transform:uppercase; letter-spacing:0.02em;">{bundle["bias"]}</div></div>'
            )
st.caption("4H and 1H set higher-timeframe direction. 15m and 5m confirm corrections and continuations — they never override 4H/1H alone.")

st.write("")

# =====================================================================
# STRUCTURE CHART (70%) | KEY LEVELS + CURRENT PHASE (30%)
# =====================================================================
chart_col, side_col = st.columns([2.3, 1])

primary_tf = result["timeframes"]["1H"]
with side_col:
    st.markdown("#### Key Levels")
    with st.container(border=True):
        if primary_tf:
            seller = primary_tf["levels"].get("seller_level")
            buyer = primary_tf["levels"].get("buyer_level")
            render_html('<div class="el-section-label">Seller (1H)</div>')
            render_html(f'<div style="font-size:1.15rem; font-weight:700; color:{RED};">{seller["price"]:.4f}</div>' if seller else f'<div style="color:{INK_MUTED};">N/A</div>')
            render_html('<div class="el-section-label" style="margin-top:12px;">Buyer (1H)</div>')
            render_html(f'<div style="font-size:1.15rem; font-weight:700; color:{ACCENT_TEAL};">{buyer["price"]:.4f}</div>' if buyer else f'<div style="color:{INK_MUTED};">N/A</div>')
        else:
            st.caption("Insufficient 1H data to identify key levels.")

    st.markdown("#### Current Phase")
    with st.container(border=True):
        phases = phase_status(result)

        for phase_name, status in [
            ("Breakout / Breakdown", phases["indication_status"]),
            ("Pullback / Correction", phases["correction_status"]),
            ("Continuation", phases["continuation_status"]),
        ]:
            render_html(
                f'<div style="display:flex; justify-content:space-between; padding:4px 0;">'
                f'<span style="color:{INK_SECONDARY}; font-size:0.85rem;">{phase_name}</span>'
                f'<span style="color:{INK_PRIMARY}; font-weight:600; font-size:0.85rem;">{status}</span></div>'
            )
        render_html(f'<hr style="margin:8px 0; border-color:{BORDER};">')
        render_html(
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<span style="color:{INK_SECONDARY}; font-size:0.85rem;">Structure Quality</span>'
            f'<span style="color:{INK_PRIMARY}; font-weight:700; font-size:0.85rem;">{result["quality"]}</span></div>'
        )

with chart_col:
    st.markdown("#### Structure Chart")
    chart_tf_choice = st.radio("Chart timeframe", ("1H", "4H", "15m", "5m"), horizontal=True, label_visibility="collapsed")
    toggle_cols = st.columns(3)
    show_swings = toggle_cols[0].checkbox("Show Structure", value=True)
    show_levels = toggle_cols[1].checkbox("Show Buyer/Seller Levels", value=True)
    show_labels = toggle_cols[2].checkbox("Show HH/HL/LH/LL Labels", value=True)

    chart_history = result["history"].get(chart_tf_choice)
    chart_bundle = result["timeframes"].get(chart_tf_choice)

    if chart_history is None or chart_history.empty:
        st.info(f"No {chart_tf_choice} data available to chart.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=chart_history.index, open=chart_history["Open"], high=chart_history["High"],
            low=chart_history["Low"], close=chart_history["Close"],
            increasing_line_color=ACCENT_TEAL, decreasing_line_color=RED, name=ticker,
        ))

        if chart_bundle and show_swings:
            # Visual hierarchy only — the underlying swing list (and every
            # structure/level/state computation from it) is unchanged.
            # "Major" = the most recent MAJOR_SWING_COUNT swings, which are
            # what current structure/levels actually reference; older
            # swings still plot, but small and unlabeled by default, so
            # the chart isn't wall-to-wall HH/HL/LH/LL text.
            highs = [s for s in chart_bundle["swings"] if s["type"] == "high"]
            lows = [s for s in chart_bundle["swings"] if s["type"] == "low"]
            major_cutoff_time = chart_bundle["swings"][-MAJOR_SWING_COUNT]["time"] if len(chart_bundle["swings"]) > MAJOR_SWING_COUNT else None

            for swing_list, symbol, color, textpos in ((highs, "triangle-down", RED, "top center"), (lows, "triangle-up", ACCENT_TEAL, "bottom center")):
                major = [s for s in swing_list if major_cutoff_time is None or s["time"] >= major_cutoff_time]
                minor = [s for s in swing_list if major_cutoff_time is not None and s["time"] < major_cutoff_time]
                if minor:
                    fig.add_trace(go.Scatter(
                        x=[s["time"] for s in minor], y=[s["price"] for s in minor], mode="markers",
                        marker=dict(symbol=symbol, size=4, color=color, opacity=0.35), showlegend=False, hoverinfo="skip",
                    ))
                if major:
                    fig.add_trace(go.Scatter(
                        x=[s["time"] for s in major], y=[s["price"] for s in major],
                        mode="markers+text" if show_labels else "markers",
                        text=[s["label"] for s in major] if show_labels else None, textposition=textpos,
                        marker=dict(symbol=symbol, size=9, color=color), showlegend=False,
                        textfont=dict(size=10, color=color, family="Inter"),
                    ))

        if chart_bundle and show_levels:
            seller = chart_bundle["levels"].get("seller_level")
            buyer = chart_bundle["levels"].get("buyer_level")
            if seller:
                fig.add_hline(y=seller["price"], line=dict(color=RED, width=1, dash="dot"), annotation_text="Seller Level", annotation_font_color=RED)
            if buyer:
                fig.add_hline(y=buyer["price"], line=dict(color=ACCENT_TEAL, width=1, dash="dot"), annotation_text="Buyer Level", annotation_font_color=ACCENT_TEAL)

        if result.get("break") and result["break"].get("broken"):
            fig.add_vline(x=result["break"]["time"], line=dict(color=AMBER, width=1, dash="dash"))

        fig.update_layout(
            height=480, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white", paper_bgcolor="white",
            hovermode="x unified", showlegend=False,
            xaxis_rangeslider_visible=False,
        )
        fig.update_yaxes(showgrid=True, gridcolor=BORDER)
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Amber dashed line marks the confirmed candle-close break, where applicable. Faded markers are older/minor swings — solid, labeled markers are the most recent structure the levels above are based on.")

st.write("")

# =====================================================================
# OUTLOOK — the deterministic, generated-from-computed-structure explanation
# =====================================================================
st.markdown("#### Outlook")
with st.container(border=True):
    render_html(f'<p style="color:{INK_SECONDARY}; font-size:0.9rem; line-height:1.6; margin:0;">{result["explanation"]}</p>')

st.write("")

# =====================================================================
# ADVANCED STRUCTURE DETAILS
# =====================================================================
with st.expander("Advanced Structure Details"):
    break_info = result.get("break")
    phases = phase_status(result)
    adv1, adv2, adv3 = st.columns(3)
    adv1.metric("Indication", phases["indication_status"])
    adv2.metric("Correction", phases["correction_status"])
    adv3.metric("Continuation", phases["continuation_status"])

    st.write("")
    st.markdown("###### Evidence")
    evidence_lines = []
    if break_info and break_info.get("broken"):
        evidence_lines.append(f"Indication: 1H candle closed at {break_info['close']:.4f} beyond the key level at {break_info['time']}.")
    else:
        evidence_lines.append("Indication: no confirmed candle-close break yet.")
    for tf_label in ("15m", "5m"):
        bundle = result["timeframes"][tf_label]
        if bundle:
            evidence_lines.append(f"{tf_label} structure: currently {bundle['bias']} ({len(bundle['swings'])} swings detected in the analysis window).")
        else:
            evidence_lines.append(f"{tf_label} structure: insufficient data.")
    for line in evidence_lines:
        st.markdown(f"- {line}")

    st.write("")
    st.markdown("###### Structure Quality Factors")
    if result["quality_factors"]:
        for factor, met in result["quality_factors"].items():
            icon = "✓" if met else "✗"
            color = ACCENT_TEAL if met else INK_MUTED
            render_html(f'<span style="color:{color}; font-weight:600;">{icon}</span> <span style="color:{INK_SECONDARY};">{factor.replace("_", " ")}</span><br>')
    else:
        st.caption("Not enough confirmed structure yet to score quality factors.")

    st.caption(
        "Structure Quality is a count of explainable factors (timeframe alignment, confirmed break, lower-timeframe "
        "confirmation) — never a statistical win probability."
    )

st.write("")

# =====================================================================
# EVENT RISK — warning only, never changes the structure read
# =====================================================================
st.markdown("#### Event Risk")
relevant = get_relevant_events(ticker, asset_class)
if not relevant["available"]:
    st.caption("Economic calendar unavailable right now.")
elif not relevant["events"]:
    st.caption(f"No high-impact events scheduled for {ticker} this week.")
else:
    for event in relevant["events"]:
        impact_color = IMPACT_COLORS.get(event["impact"], INK_MUTED)
        render_html(
            f"""
            <div style="padding:6px 0;">
                <span style="color:{impact_color}; font-weight:700; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em;">{event['impact']} Impact</span>
                <span style="color:{INK_PRIMARY}; font-weight:600; margin-left:8px;">{event['title']}</span>
                <span style="color:{INK_MUTED}; font-size:0.82rem; margin-left:6px;">({event['currency']}) in {event['time_until']}</span>
                <div style="color:{INK_SECONDARY}; font-size:0.82rem; margin-top:2px;">{event['relevance']}</div>
            </div>
            """
        )
    st.caption("This is a warning only — it does not change the Market Structure status above, and structure analysis continues regardless of upcoming events.")

st.write("")

# =====================================================================
# DEBUG / VALIDATION MODE
# =====================================================================
with st.expander("Debug / Validation Mode"):
    st.caption("Raw detected structure for the chosen timeframe — for checking the engine's read against your own chart analysis.")
    debug_tf = st.selectbox("Timeframe", ("4H", "1H", "15m", "5m"), key="ms_debug_tf")
    debug_bundle = result["timeframes"].get(debug_tf)
    if debug_bundle is None:
        st.caption("Insufficient data for this timeframe.")
    else:
        st.markdown(f"**{len(debug_bundle['swings'])} swings detected** (sensitivity={DEFAULT_SENSITIVITY.get(debug_tf)}, candle-close required for breaks: {REQUIRE_CANDLE_CLOSE})")
        debug_rows = [
            {"Time": str(s["time"]), "Type": s["type"], "Price": round(s["price"], 4), "Label": s["label"]}
            for s in debug_bundle["swings"][-30:]
        ]
        st.dataframe(debug_rows, hide_index=True, use_container_width=True)
        st.caption("Showing the most recent 30 detected swings. Bias, key levels, and the break/correction/continuation read above are all derived directly from this list.")

st.write("")
st.caption(
    "Market Structure identifies price structure only — it does not recommend an entry, stop, target, or position "
    "size, and it never executes trades. You make the decision; log it manually on Investment Ideas if you choose to."
)
