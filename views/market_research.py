"""EquityLens — Market Research: multi-asset price research + equity fundamentals.

Every asset class gets price/change + an interactive candlestick chart.
Company fundamentals and the Financial Health Score only apply to equities,
so that section is shown for the Stocks asset class only — crypto, forex,
metals, and indices don't have income statements or a P/E ratio.
"""

import streamlit as st
import plotly.graph_objects as go

from theme import apply_theme, UP_COLOR, DOWN_COLOR, INK_PRIMARY, INK_SECONDARY, BORDER
from components import asset_picker, compact_placeholder, render_html, rating_badge_html
from data_fetcher import (
    get_price_history,
    get_ticker_info,
    is_valid_ticker,
    get_extended_metrics,
    format_large_number,
    format_ratio,
    format_price,
    format_percentage,
    format_multiple,
)
from scoring import calculate_financial_health

st.set_page_config(page_title="EquityLens — Market Research", layout="wide")
apply_theme()

st.markdown("## Market Research")
st.caption("What you need to know about this asset in the next 30 seconds.")

ticker, display_name, asset_class = asset_picker("market_research")

if not ticker:
    st.info("Enter a ticker symbol to continue.")
    st.stop()

PERIOD_LABELS = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
selected_period_label = st.radio(
    "Period", list(PERIOD_LABELS.keys()), index=3, horizontal=True, label_visibility="collapsed"
)
period = PERIOD_LABELS[selected_period_label]

with st.spinner(f"Fetching data for {ticker}..."):
    try:
        history = get_price_history(ticker, period=period)
    except Exception:
        history = None

if history is None or history.empty or "Close" not in history.columns:
    st.error(
        f"No data found for '{ticker}'. Check the symbol and try again — "
        "e.g. 'AAPL' for stocks, 'BTC-USD' for crypto, 'EURUSD=X' for forex, "
        "'GC=F' for metals futures, '^GSPC' for indices."
    )
    st.stop()

current_price = history["Close"].iloc[-1]
previous_close = history["Close"].iloc[-2] if len(history) > 1 else None
pct_change = ((current_price - previous_close) / previous_close * 100) if previous_close else None

render_html(f'<p class="el-header">{display_name}</p>')
render_html(f'<p class="el-subtext">{ticker} · {asset_class}</p>')
st.write("")

price_col, change_col = st.columns(2)
price_col.metric("Current Price", f"${current_price:,.4f}" if current_price < 10 else f"${current_price:,.2f}")
change_col.metric("Change (1D)", f"{pct_change:+.2f}%" if pct_change is not None else "N/A")

st.write("")
st.markdown("#### Price Chart")

fig = go.Figure(
    data=[
        go.Candlestick(
            x=history.index,
            open=history["Open"],
            high=history["High"],
            low=history["Low"],
            close=history["Close"],
            increasing_line_color=UP_COLOR,
            decreasing_line_color=DOWN_COLOR,
            name=ticker,
        )
    ]
)
fig.update_layout(
    height=440,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
    yaxis=dict(showgrid=True, gridcolor=BORDER, tickprefix="$"),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.write("")

# ---------- Equity fundamentals (Stocks only) ----------
if asset_class == "Stocks":
    info = get_ticker_info(ticker)
    if is_valid_ticker(info):
        company_name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        exchange = info.get("exchange", "N/A")

        st.markdown("#### Company Fundamentals")
        render_html(f'<p class="el-subtext">{company_name} · {sector} · {industry} · {exchange}</p>')

        market_cap = info.get("marketCap")
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")
        pe_ratio = info.get("trailingPE") or info.get("forwardPE")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Market Cap", format_large_number(market_cap))
        col2.metric("Revenue (TTM)", format_large_number(revenue))
        col3.metric("Net Income (TTM)", format_large_number(net_income))
        col4.metric("P/E Ratio", format_ratio(pe_ratio))

        st.write("")
        metrics = get_extended_metrics(info)

        st.markdown("###### Growth")
        st.metric(
            "Revenue Growth (YoY)",
            format_percentage(metrics["revenue_growth"]),
            help="Year-over-year growth in total revenue.",
        )

        st.markdown("###### Profitability")
        prof1, prof2, prof3 = st.columns(3)
        prof1.metric("Net Profit Margin", format_percentage(metrics["net_profit_margin"]),
                     help="Net income as a percentage of total revenue.")
        prof2.metric("Operating Margin", format_percentage(metrics["operating_margin"]),
                     help="Operating income as a percentage of total revenue, before interest and tax.")
        prof3.metric("Return on Equity", format_percentage(metrics["return_on_equity"]),
                     help="Net income as a percentage of shareholder equity.")

        st.markdown("###### Financial Position")
        pos1, pos2, pos3 = st.columns(3)
        pos1.metric("Free Cash Flow", format_large_number(metrics["free_cash_flow"]),
                    help="Cash generated from operations after capital expenditures.")
        pos2.metric("Total Debt", format_large_number(metrics["total_debt"]),
                    help="Total short-term and long-term debt outstanding.")
        pos3.metric("Debt-to-Equity", format_multiple(metrics["debt_to_equity"]),
                    help="Total debt divided by shareholder equity.")

        st.markdown("###### Valuation")
        val1, val2 = st.columns(2)
        val1.metric("Forward P/E", format_ratio(metrics["forward_pe"]),
                    help="Share price divided by expected earnings per share over the next 12 months.")
        val2.metric("Price-to-Sales", format_ratio(metrics["price_to_sales"]),
                    help="Market capitalization divided by trailing twelve-month revenue.")

        st.write("")

        # ---------- Financial Health Score ----------
        st.markdown("#### Financial Health Score")
        health = calculate_financial_health(info, metrics)

        score_col, breakdown_col = st.columns([1, 3])
        with score_col:
            render_html(
                f"""
                <div style="text-align:center; padding: 8px 0 16px 0;">
                    <div style="font-size:2.75rem; font-weight:800; line-height:1; color:{INK_PRIMARY}; font-variant-numeric:tabular-nums;">
                        {health['total_score']}
                    </div>
                    <div style="font-size:0.82rem; color:{INK_SECONDARY}; margin-top:4px;">out of 100</div>
                    <div style="margin-top:10px;">{rating_badge_html(health['rating'])}</div>
                </div>
                """
            )
        with breakdown_col:
            cat_cols = st.columns(5)
            for col, category in zip(cat_cols, health["categories"]):
                col.metric(category["name"], f"{category['score']:.0f}/20", help=category["detail"])

        st.write("")
        strength_col, weakness_col = st.columns(2)
        with strength_col:
            st.markdown("###### Strengths")
            if health["strengths"]:
                for strength in health["strengths"]:
                    st.markdown(f"- {strength}")
            else:
                st.markdown("_No standout strengths identified._")
        with weakness_col:
            st.markdown("###### Weaknesses")
            if health["weaknesses"]:
                for weakness in health["weaknesses"]:
                    st.markdown(f"- {weakness}")
            else:
                st.markdown("_No significant weaknesses identified._")

        st.caption(
            "The Financial Health Score is a rule-based heuristic built from the metrics above "
            "(not AI-generated) — it is not investment advice."
        )
    else:
        st.info(f"No equity fundamentals found for '{ticker}'.")
else:
    st.info(f"Company fundamentals are available for the Stocks asset class only — '{asset_class}' assets don't have an income statement or P/E ratio.")

st.write("")
st.markdown("#### Planned Intelligence Features")
compact_placeholder("AI Company Brief")
compact_placeholder("AI Financial Summary")
compact_placeholder("Technical Summary")
compact_placeholder("Overall Rating")

st.caption("Data source: Yahoo Finance via yfinance. For research purposes only — not investment advice.")
