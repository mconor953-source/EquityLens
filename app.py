"""EquityLens — Version 1: core fundamentals + price chart."""

import streamlit as st
import plotly.graph_objects as go

from data_fetcher import (
    get_ticker_info,
    get_price_history,
    is_valid_ticker,
    format_large_number,
    format_ratio,
    format_price,
    format_percentage,
    format_multiple,
    get_extended_metrics,
)
from scoring import calculate_financial_health

st.set_page_config(
    page_title="EquityLens",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Styling ----------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            max-width: 1100px;
        }
        div[data-testid="stMetric"] {
            background-color: #F4F6F8;
            border: 1px solid #E3E7EB;
            border-radius: 10px;
            padding: 16px 18px;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.85rem;
            color: #5A6472;
        }
        .company-header {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1A1A1A;
            margin-bottom: 0;
        }
        .company-subtext {
            color: #5A6472;
            font-size: 0.95rem;
            margin-top: 2px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header ----------
st.markdown("## 📈 EquityLens")
st.caption("AI-Powered Equity Research & Risk Intelligence")

ticker_input = st.text_input(
    "Ticker symbol",
    value="AAPL",
    placeholder="e.g. AAPL, MSFT, TSLA",
    label_visibility="collapsed",
).strip().upper()

if not ticker_input:
    st.stop()

# ---------- Fetch data ----------
with st.spinner(f"Fetching data for {ticker_input}..."):
    info = get_ticker_info(ticker_input)

if not is_valid_ticker(info):
    st.error(f"Couldn't find data for '{ticker_input}'. Check the ticker symbol and try again.")
    st.stop()

# ---------- Company header ----------
company_name = info.get("longName") or info.get("shortName") or ticker_input
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")
exchange = info.get("exchange", "N/A")

st.markdown(f'<p class="company-header">{company_name} ({ticker_input})</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="company-subtext">{sector} · {industry} · {exchange}</p>',
    unsafe_allow_html=True,
)
st.write("")

# ---------- Key metrics ----------
current_price = info.get("currentPrice") or info.get("regularMarketPrice")
prev_close = info.get("previousClose")
day_change_pct = None
if current_price is not None and prev_close:
    day_change_pct = (current_price - prev_close) / prev_close * 100

market_cap = info.get("marketCap")
revenue = info.get("totalRevenue")
net_income = info.get("netIncomeToCommon")
pe_ratio = info.get("trailingPE") or info.get("forwardPE")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(
    "Share Price",
    format_price(current_price),
    f"{day_change_pct:+.2f}%" if day_change_pct is not None else None,
)
col2.metric("Market Cap", format_large_number(market_cap))
col3.metric("Revenue (TTM)", format_large_number(revenue))
col4.metric("Net Income (TTM)", format_large_number(net_income))
col5.metric("P/E Ratio", format_ratio(pe_ratio))

st.write("")

# ---------- Extended financial analysis ----------
st.markdown("#### Financial Analysis")

metrics = get_extended_metrics(info)

st.markdown("###### Growth")
st.metric(
    "Revenue Growth (YoY)",
    format_percentage(metrics["revenue_growth"]),
    help="Year-over-year growth in total revenue.",
)

st.markdown("###### Profitability")
prof1, prof2, prof3 = st.columns(3)
prof1.metric(
    "Net Profit Margin",
    format_percentage(metrics["net_profit_margin"]),
    help="Net income as a percentage of total revenue.",
)
prof2.metric(
    "Operating Margin",
    format_percentage(metrics["operating_margin"]),
    help="Operating income as a percentage of total revenue, before interest and tax.",
)
prof3.metric(
    "Return on Equity",
    format_percentage(metrics["return_on_equity"]),
    help="Net income as a percentage of shareholder equity — how efficiently the company generates profit from equity capital.",
)

st.markdown("###### Financial Position")
pos1, pos2, pos3 = st.columns(3)
pos1.metric(
    "Free Cash Flow",
    format_large_number(metrics["free_cash_flow"]),
    help="Cash generated from operations after capital expenditures.",
)
pos2.metric(
    "Total Debt",
    format_large_number(metrics["total_debt"]),
    help="Total short-term and long-term debt outstanding.",
)
pos3.metric(
    "Debt-to-Equity",
    format_multiple(metrics["debt_to_equity"]),
    help="Total debt divided by shareholder equity. Higher values indicate greater reliance on borrowed capital.",
)

st.markdown("###### Valuation")
val1, val2 = st.columns(2)
val1.metric(
    "Forward P/E",
    format_ratio(metrics["forward_pe"]),
    help="Share price divided by analysts' expected earnings per share over the next 12 months.",
)
val2.metric(
    "Price-to-Sales",
    format_ratio(metrics["price_to_sales"]),
    help="Market capitalization divided by trailing twelve-month revenue.",
)

st.write("")

# ---------- Financial Health Score ----------
st.markdown("#### Financial Health Score")

health = calculate_financial_health(info, metrics)

RATING_COLORS = {
    "Excellent": "#1E7A46",
    "Good": "#1F4E79",
    "Average": "#B8860B",
    "Weak": "#B23B3B",
}
rating_color = RATING_COLORS.get(health["rating"], "#5A6472")

score_col, breakdown_col = st.columns([1, 3])
with score_col:
    st.markdown(
        f"""
        <div style="text-align:center; padding: 8px 0 16px 0;">
            <div style="font-size:3rem; font-weight:800; line-height:1; color:{rating_color};">
                {health['total_score']}
            </div>
            <div style="font-size:0.85rem; color:#5A6472; margin-top:4px;">out of 100</div>
            <div style="display:inline-block; margin-top:10px; padding:4px 14px; border-radius:999px;
                        background-color:{rating_color}1A; color:{rating_color}; font-weight:600; font-size:0.9rem;">
                {health['rating']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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
            st.markdown(f"✅ {strength}")
    else:
        st.markdown("_No standout strengths identified._")

with weakness_col:
    st.markdown("###### Weaknesses")
    if health["weaknesses"]:
        for weakness in health["weaknesses"]:
            st.markdown(f"⚠️ {weakness}")
    else:
        st.markdown("_No significant weaknesses identified._")

st.caption(
    "The Financial Health Score is a rule-based heuristic built from the metrics above "
    "(not AI-generated) — it is not investment advice."
)

st.write("")

# ---------- Price chart ----------
st.markdown("#### Price History")

period_labels = {
    "1M": "1mo",
    "6M": "6mo",
    "YTD": "ytd",
    "1Y": "1y",
    "5Y": "5y",
    "MAX": "max",
}
selected_label = st.radio(
    "Period",
    list(period_labels.keys()),
    index=3,
    horizontal=True,
    label_visibility="collapsed",
)
period = period_labels[selected_label]

with st.spinner("Loading price history..."):
    history = get_price_history(ticker_input, period=period)

if history.empty:
    st.warning("No price history available for this period.")
else:
    is_positive = history["Close"].iloc[-1] >= history["Close"].iloc[0]
    line_color = "#1F4E79" if is_positive else "#B23B3B"
    fill_color = "rgba(31, 78, 121, 0.08)" if is_positive else "rgba(178, 59, 59, 0.08)"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["Close"],
            mode="lines",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="%{x|%b %d, %Y}<br>$%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor="#EDEFF2", tickprefix="$"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Data source: Yahoo Finance via yfinance. For research purposes only — not investment advice.")
