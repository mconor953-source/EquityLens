"""EquityLens — Market Research: multi-asset price research + equity fundamentals.

Every asset class gets price/change, price statistics, an interactive
candlestick chart with moving averages and volume, and a rule-based
Technical Rating — all computed from price history alone, so it works the
same for stocks, crypto, forex, metals, and indices. Company fundamentals,
Analyst Consensus, and the Financial Health Score only apply to equities,
so that section is shown for the Stocks asset class only — crypto, forex,
metals, and indices don't have income statements, analyst coverage, or a
P/E ratio.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from theme import (
    apply_theme, UP_COLOR, DOWN_COLOR, INK_PRIMARY, INK_SECONDARY, INK_MUTED, BORDER,
    TECHNICAL_RATING_COLORS,
)
from components import asset_picker, render_html, rating_badge_html, signal_list
from data_fetcher import (
    get_price_history,
    get_ticker_info,
    is_valid_ticker,
    get_extended_metrics,
    get_analyst_consensus,
    format_large_number,
    format_ratio,
    format_price,
    format_market_price,
    format_percentage,
    format_multiple,
)
from scoring import calculate_financial_health
from settings_store import load_settings
from technicals import (
    simple_moving_average,
    annualized_volatility,
    fifty_two_week_range,
    volume_ratio,
    compute_technical_rating,
)

st.set_page_config(page_title="EquityLens — Market Research", layout="wide")
apply_theme()

st.markdown("## Market Research")
st.caption("What you need to know about this asset in the next 30 seconds.")

settings = load_settings()
ticker, display_name, asset_class = asset_picker(
    "market_research",
    default_class=settings.get("default_asset_class", "Stocks"),
    default_asset=settings.get("default_asset"),
)

if not ticker:
    st.info("Enter a ticker symbol to continue.")
    st.stop()

PERIOD_LABELS = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
period_keys = list(PERIOD_LABELS.keys())
saved_period_label = settings.get("default_period_label", "1Y")
default_period_index = period_keys.index(saved_period_label) if saved_period_label in period_keys else 3
selected_period_label = st.radio(
    "Period", period_keys, index=default_period_index, horizontal=True, label_visibility="collapsed"
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

# Indicators (moving averages, RSI, 52-week range, ...) need at least a
# year of history to be meaningful regardless of what chart period is
# selected. Reuse `history` directly when it already covers >= 1y; only
# fetch again for the shorter chart periods (1M/3M/6M).
if period in ("1mo", "3mo", "6mo"):
    with st.spinner(f"Loading indicators for {ticker}..."):
        try:
            indicator_history = get_price_history(ticker, period="1y")
        except Exception:
            indicator_history = history
    if indicator_history is None or indicator_history.empty:
        indicator_history = history
else:
    indicator_history = history

current_price = history["Close"].iloc[-1]
previous_close = history["Close"].iloc[-2] if len(history) > 1 else None
pct_change = ((current_price - previous_close) / previous_close * 100) if previous_close else None

render_html(f'<p class="el-header">{display_name}</p>')
render_html(f'<p class="el-subtext">{ticker} · {asset_class}</p>')
st.write("")

price_col, change_col = st.columns(2)
price_col.metric("Current Price", f"${current_price:,.4f}" if current_price < 10 else f"${current_price:,.2f}")
change_col.metric("Change (1D)", f"{pct_change:+.2f}%" if pct_change is not None else "N/A")

# ---------- Price Statistics (every asset class — price-derived only) ----------
st.write("")
st.markdown("#### Price Statistics")
st.caption(
    "Computed on a trailing 1-year (or longer) price history, independent of the "
    "chart period selected above — so these figures don't change when you switch to 1M or 3M."
)

range_52w = fifty_two_week_range(indicator_history)
volatility = annualized_volatility(indicator_history["Close"])
vol_ratio = volume_ratio(indicator_history)

stat1, stat2, stat3, stat4 = st.columns(4)
stat1.metric("52-Week High", format_market_price(range_52w["high"]) if range_52w else "N/A")
stat2.metric("52-Week Low", format_market_price(range_52w["low"]) if range_52w else "N/A")
stat3.metric(
    "Annualized Volatility",
    format_percentage(volatility) if volatility is not None else "N/A",
    help="Standard deviation of daily returns, annualized over 252 trading days.",
)
stat4.metric(
    "Volume (vs. 20D Avg)",
    format_multiple(vol_ratio["ratio"]) if vol_ratio else "N/A",
    help="Latest session volume divided by its trailing 20-day average.",
)

if range_52w and range_52w["high"] != range_52w["low"]:
    position_pct = max(0.0, min(100.0, (current_price - range_52w["low"]) / (range_52w["high"] - range_52w["low"]) * 100))
    render_html(
        f"""
        <div style="margin-top:4px; margin-bottom:8px;">
            <div style="position:relative; height:6px; background-color:{BORDER}; border-radius:3px;">
                <div style="position:absolute; left:{position_pct:.1f}%; top:-3px; width:2px; height:12px;
                            background-color:{INK_PRIMARY}; border-radius:1px; transform:translateX(-1px);"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:4px; font-size:0.72rem; color:{INK_MUTED};">
                <span>{format_market_price(range_52w['low'])}</span>
                <span>52-week range — current price at the {position_pct:.0f}th percentile</span>
                <span>{format_market_price(range_52w['high'])}</span>
            </div>
        </div>
        """
    )

st.write("")
st.markdown("#### Price Chart")

sma50_series = simple_moving_average(indicator_history["Close"], 50)
sma200_series = simple_moving_average(indicator_history["Close"], 200)
has_volume = "Volume" in history.columns and history["Volume"].fillna(0).sum() > 0

fig = make_subplots(
    rows=2 if has_volume else 1,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.72, 0.28] if has_volume else [1.0],
    vertical_spacing=0.03,
)

fig.add_trace(
    go.Candlestick(
        x=history.index,
        open=history["Open"],
        high=history["High"],
        low=history["Low"],
        close=history["Close"],
        increasing_line_color=UP_COLOR,
        decreasing_line_color=DOWN_COLOR,
        name=ticker,
    ),
    row=1, col=1,
)

if sma50_series is not None:
    sma50_plot = sma50_series.reindex(history.index).dropna()
    if not sma50_plot.empty:
        fig.add_trace(
            go.Scatter(
                x=sma50_plot.index, y=sma50_plot.values, mode="lines", name="SMA 50",
                line=dict(color=INK_SECONDARY, width=1.3),
            ),
            row=1, col=1,
        )

if sma200_series is not None:
    sma200_plot = sma200_series.reindex(history.index).dropna()
    if not sma200_plot.empty:
        fig.add_trace(
            go.Scatter(
                x=sma200_plot.index, y=sma200_plot.values, mode="lines", name="SMA 200",
                line=dict(color=INK_MUTED, width=1.3, dash="dot"),
            ),
            row=1, col=1,
        )

if has_volume:
    volume_colors = [
        UP_COLOR if c >= o else DOWN_COLOR
        for o, c in zip(history["Open"], history["Close"])
    ]
    fig.add_trace(
        go.Bar(x=history.index, y=history["Volume"], marker_color=volume_colors, name="Volume", opacity=0.55),
        row=2, col=1,
    )

fig.update_layout(
    height=520 if has_volume else 440,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    paper_bgcolor="white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
)
fig.update_xaxes(showgrid=False, rangeslider_visible=False, row=1, col=1)
fig.update_yaxes(showgrid=True, gridcolor=BORDER, tickprefix="$", row=1, col=1)
if has_volume:
    fig.update_xaxes(showgrid=False, row=2, col=1)
    fig.update_yaxes(showgrid=False, row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# ---------- Technical Analysis (every asset class — price-derived only) ----------
st.write("")
st.markdown("#### Technical Analysis")

technical = compute_technical_rating(indicator_history)

if technical is None:
    st.info("Not enough price history to compute technical signals for this ticker.")
else:
    rating_col, counts_col = st.columns([1, 3])
    with rating_col:
        rating_color = TECHNICAL_RATING_COLORS.get(technical["rating"], INK_SECONDARY)
        render_html(
            f"""
            <div style="text-align:center; padding: 8px 0 16px 0;">
                <div style="font-size:1.55rem; font-weight:800; color:{rating_color}; line-height:1.2;">
                    {technical['rating']}
                </div>
                <div style="font-size:0.78rem; color:{INK_SECONDARY}; margin-top:8px;">
                    {technical['total_signals']} signals evaluated
                </div>
            </div>
            """
        )
    with counts_col:
        c1, c2, c3 = st.columns(3)
        c1.metric("Buy Signals", technical["buy_count"])
        c2.metric("Neutral Signals", technical["neutral_count"])
        c3.metric("Sell Signals", technical["sell_count"])

    st.write("")
    st.markdown("###### Signal Breakdown")
    signal_list(technical["signals"])

    st.caption(
        "Technical Rating counts Buy/Sell/Neutral signals across four moving averages "
        "(20/50/100/200-day) plus the 50/200-day cross, and three momentum oscillators "
        "(RSI-14, MACD, 10-day Rate of Change) — a rule-based signal count, not a "
        "prediction. Not investment advice."
    )

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

        # ---------- Analyst Consensus ----------
        st.markdown("#### Analyst Consensus")
        consensus = get_analyst_consensus(info)

        if consensus["num_analysts"] and consensus["target_mean"]:
            upside = (consensus["target_mean"] - current_price) / current_price * 100
            ac1, ac2, ac3, ac4 = st.columns(4)
            ac1.metric("Recommendation", consensus["recommendation"] or "N/A")
            ac2.metric("Analysts Covering", consensus["num_analysts"])
            ac3.metric("Mean Price Target", format_price(consensus["target_mean"]))
            ac4.metric(
                "Implied Upside",
                f"{upside:+.1f}%",
                help="Mean analyst price target vs. the current price.",
            )
            st.caption(
                f"Analyst target range: {format_price(consensus['target_low'])} – {format_price(consensus['target_high'])}. "
                "Source: Yahoo Finance sell-side consensus."
            )
        else:
            st.info(f"No analyst coverage data available for '{ticker}'.")

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
st.caption("Data source: Yahoo Finance via yfinance. For research purposes only — not investment advice.")
