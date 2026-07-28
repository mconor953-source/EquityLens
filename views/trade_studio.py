"""EquityLens — Trade Studio: a trade-planning workspace.

No automatic technical analysis here — support/resistance and bias are the
trader's own read of the chart. What IS real and computed: the risk/reward
math and position sizing (trade_calculator.py), driven entirely by the
numbers the trader enters.
"""

import streamlit as st

from theme import apply_theme
from components import asset_picker, compact_placeholder
from data_fetcher import get_current_price_and_change
from trade_calculator import plan_trade

st.set_page_config(page_title="EquityLens — Trade Studio", layout="wide")
apply_theme()

st.markdown("## Trade Studio")
st.caption("Plan a trade with real risk/reward math — support, resistance, and bias are your call.")

# ---------- Asset Overview ----------
with st.container(border=True):
    st.markdown("##### Asset Overview")
    ticker, display_name, asset_class = asset_picker("trade_studio", default_class="Stocks")

    if not ticker:
        st.info("Enter a ticker symbol to continue.")
        st.stop()

    current_price, pct_change = get_current_price_and_change(ticker)
    reference_price = float(current_price) if current_price is not None else 100.0

    name_col, price_col, change_col, bias_col = st.columns([1.6, 1, 1, 1.2])
    with name_col:
        st.markdown(f"**{display_name}**")
        st.caption(f"{ticker} · {asset_class}")
    price_col.metric("Current Price", f"${current_price:,.2f}" if current_price is not None else "N/A")
    change_col.metric("Daily Change", f"{pct_change:+.2f}%" if pct_change is not None else "N/A")
    with bias_col:
        bias = st.selectbox("Market Bias", ["Bullish", "Neutral", "Bearish"], key="bias")

st.write("")

# ---------- Key Levels ----------
with st.container(border=True):
    st.markdown("##### Key Levels")
    st.caption("Your own read of the chart — these seed the planner below (still editable there).")
    lvl_col1, lvl_col2 = st.columns(2)
    support = lvl_col1.number_input("Support", value=round(reference_price * 0.95, 2), step=0.01, format="%.2f")
    resistance = lvl_col2.number_input("Resistance", value=round(reference_price * 1.05, 2), step=0.01, format="%.2f")

st.write("")

# ---------- Trade Planner Inputs ----------
with st.container(border=True):
    st.markdown("##### Trade Planner Inputs")
    in_col1, in_col2, in_col3 = st.columns(3)
    direction = in_col1.selectbox("Direction", ["Long", "Short"], key="direction")
    default_stop = support if direction == "Long" else resistance
    default_target = resistance if direction == "Long" else support
    entry = in_col2.number_input("Entry Price", value=round(reference_price, 2), step=0.01, format="%.2f")
    stop_loss = in_col3.number_input("Stop Loss", value=round(default_stop, 2), step=0.01, format="%.2f")

    in_col4, in_col5, in_col6 = st.columns(3)
    target = in_col4.number_input("Take Profit", value=round(default_target, 2), step=0.01, format="%.2f")
    account_size = in_col5.number_input("Account Size ($)", value=10000.0, min_value=0.0, step=100.0, format="%.2f")
    risk_pct = in_col6.number_input("Risk Percentage", value=1.0, min_value=0.0, max_value=100.0, step=0.1, format="%.1f")

trade = plan_trade(
    direction=direction, entry=entry, stop_loss=stop_loss, target=target,
    account_size=account_size, risk_pct=risk_pct,
)

for warning in trade.warnings:
    st.warning(warning)

st.write("")

# ---------- Calculated Results ----------
with st.container(border=True):
    st.markdown("##### Calculated Results")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Risk Amount", f"${trade.risk_amount:,.2f}")
    res_col2.metric("Position Size", f"{trade.position_size:,.2f} units" if trade.position_size is not None else "N/A")
    res_col3.metric("Risk-to-Reward Ratio", f"{trade.risk_reward_ratio:.2f} : 1" if trade.risk_reward_ratio is not None else "N/A")

    res_col4, res_col5, res_col6 = st.columns(3)
    res_col4.metric("Potential Profit", f"${trade.potential_profit:,.2f}" if trade.potential_profit is not None else "N/A")
    res_col5.metric("Distance to Stop", f"${trade.risk_per_unit:,.2f}")
    res_col6.metric("Distance to Target", f"${trade.reward_per_unit:,.2f}")

st.write("")

# ---------- Trade Notes ----------
with st.container(border=True):
    st.markdown("##### Trade Notes")
    st.text_area(
        "Notes",
        placeholder="Why this trade, what invalidates the thesis, anything to remember...",
        label_visibility="collapsed",
        key="trade_notes",
        height=100,
    )
    st.caption("Notes are kept for this session only (not saved across restarts yet).")

st.write("")
compact_placeholder("AI Technical Brief")
compact_placeholder("Automatic Levels")

st.caption("Trade Studio performs the risk/reward and position-size arithmetic only — it does not recommend trades.")
