"""Investment stance/conviction engine behind the Investment Ideas page.

Deliberately not named investment_ideas.py — views/investment_ideas.py is
the page that imports this module, and Streamlit's per-page script
execution puts each page's own directory on sys.path, so a same-named
module there would shadow this one (the same reason the existing codebase
already used dashboard_content.py rather than dashboard.py for
views/dashboard.py's logic).

This is the longer-term counterpart to scoring.py (Financial Health, pure
fundamentals) and technicals.py (Technical Rating, pure price action): it
blends the two into a single 0-100 Conviction Score, then maps that score
onto a plain-English investment stance (BUY / HOLD / REDUCE / AVOID) and a
suggested time horizon. Nothing here is a second scoring model — it is a
weighted combination of numbers scoring.py and technicals.py already
computed, so retuning either of those automatically flows through here.

Weighted for research over timing: when fundamentals are available
(equities), Financial Health carries half the weight, long-term trend
structure (price vs. the 100/200-day moving averages and the 50/200 cross)
a bit over a third, and short-term momentum oscillators (RSI, MACD, 10-day
Rate of Change) only a small remainder — deliberately the opposite emphasis
of a day-trading signal. Asset classes without fundamentals (crypto, FX,
metals, indices) fall back to trend-plus-momentum only, with trend still
dominant.

The score represents current investment attractiveness based on the data
available today — not a probability or a prediction of future price. Every
sentence this module produces quotes a real, already-computed figure or
signal detail; nothing is invented. Where fundamentals are unavailable
(non-equity asset classes, or an equity yfinance has no info for) the module
says so explicitly rather than guessing a reason.

Pure functions only — no UI, no network calls — same separation as
scoring.py and technicals.py.
"""

import math

from data_fetcher import get_extended_metrics, is_valid_ticker, format_market_price
from scoring import calculate_financial_health
from technicals import compute_technical_rating, fifty_two_week_range, simple_moving_average

# Signals from technicals.compute_technical_rating's basket that reflect
# long-term trend structure rather than short-term momentum.
TREND_SIGNAL_NAMES = {"SMA 100", "SMA 200", "MA Cross (50/200)"}

FUNDAMENTAL_WEIGHTS = {"financial_health": 0.50, "trend": 0.35, "momentum": 0.15}
TECHNICAL_ONLY_WEIGHTS = {"trend": 0.70, "momentum": 0.30}

FUNDAMENTALS_UNAVAILABLE_NOTE = (
    "Fundamental data unavailable for this asset class — the view above is based on price trend and momentum only."
)

STANCE_BANDS = (
    (70, "BUY"),
    (50, "HOLD"),
    (30, "REDUCE"),
    (float("-inf"), "AVOID"),
)

HORIZON_BANDS = (
    (75, "1–3 years"),
    (55, "6–12 months"),
    (float("-inf"), "3–6 months"),
)

# Financial Health category name -> (what would strengthen the idea if this
# category is currently a weakness, what would weaken it if currently a
# strength). Generic, deterministic, and tied to a real computed category —
# not a fabricated reason.
CATEGORY_WATCH = {
    "Growth": (
        "A return to positive revenue growth",
        "A further slowdown or decline in revenue growth",
    ),
    "Profitability": (
        "Improving margins or return on equity",
        "Margin compression or a decline in return on equity",
    ),
    "Balance Sheet": (
        "Continued deleveraging of the balance sheet",
        "A material increase in debt-to-equity",
    ),
    "Cash Flow": (
        "Stronger free cash flow conversion",
        "Deteriorating free cash flow generation",
    ),
    "Valuation": (
        "Valuation multiples becoming more reasonable relative to earnings — via a price pullback or continued earnings growth",
        "Multiple expansion running ahead of earnings growth, eroding today's valuation cushion",
    ),
}


def _weighted_average(components: dict, weights: dict):
    """Weighted mean over whichever components are not None, renormalized
    over just the available ones so missing data never silently drags the
    score toward zero."""
    available = [(components[k], w) for k, w in weights.items() if components.get(k) is not None]
    if not available:
        return None
    total_weight = sum(w for _, w in available)
    return sum(s * w for s, w in available) / total_weight


def _signal_balance_score(signals: list):
    """(buy - sell) / total across a signal list, rescaled from [-1, 1] to
    [0, 100]. None if there are no signals to read."""
    if not signals:
        return None
    buy = sum(1 for s in signals if s["signal"] == "Buy")
    sell = sum(1 for s in signals if s["signal"] == "Sell")
    balance = (buy - sell) / len(signals)
    return (balance + 1) / 2 * 100


def _band_lookup(value, bands):
    for minimum, label in bands:
        if value >= minimum:
            return label
    return bands[-1][1]


def _article(word: str) -> str:
    return "an" if word[0] in "AEIOU" else "a"


def build_investment_idea(
    ticker: str, display_name: str, asset_class: str, current_price, history, info: dict = None
) -> dict:
    """Compute a full Investment Idea for one asset.

    `info` is the yfinance info dict (Stocks only — pass None for other
    asset classes, which have no income statement or valuation multiples).
    `history` is price history (>= ~1y) as returned by
    data_fetcher.get_price_history, used for the Technical Rating and the
    long-term trend read. Returns None only if there isn't enough data
    (price or fundamentals) to form any view at all.
    """
    technical = compute_technical_rating(history) if history is not None else None
    all_signals = technical["signals"] if technical else []
    trend_signals = [s for s in all_signals if s["name"] in TREND_SIGNAL_NAMES]
    momentum_signals = [s for s in all_signals if s["name"] not in TREND_SIGNAL_NAMES]

    trend_score = _signal_balance_score(trend_signals)
    momentum_score = _signal_balance_score(momentum_signals)

    health = None
    fundamentals_available = False
    if info is not None and is_valid_ticker(info):
        fundamentals_available = True
        metrics = get_extended_metrics(info)
        health = calculate_financial_health(info, metrics)

    components = {
        "financial_health": health["total_score"] if health else None,
        "trend": trend_score,
        "momentum": momentum_score,
    }
    weights = FUNDAMENTAL_WEIGHTS if fundamentals_available else TECHNICAL_ONLY_WEIGHTS
    conviction = _weighted_average(components, weights)

    if conviction is None:
        return None

    conviction = round(conviction)
    stance = _band_lookup(conviction, STANCE_BANDS)
    horizon = _band_lookup(conviction, HORIZON_BANDS)

    positives, risks, strengthen, weaken = [], [], [], []

    if health:
        positives.extend(health["strengths"])
        risks.extend(health["weaknesses"])
        for cat in health["categories"]:
            watch = CATEGORY_WATCH.get(cat["name"])
            if not watch:
                continue
            if cat["tag"] == "weakness":
                strengthen.append(watch[0])
            elif cat["tag"] == "strength":
                weaken.append(watch[1])

    trend_label = "N/A"
    if trend_signals:
        buy_trend = [s for s in trend_signals if s["signal"] == "Buy"]
        detail = "; ".join(s["detail"] for s in trend_signals)
        if len(buy_trend) > len(trend_signals) / 2:
            trend_label = "Uptrend"
            positives.append(f"Long-term trend structure is constructive: {detail}.")
        elif len(buy_trend) < len(trend_signals) / 2:
            trend_label = "Downtrend"
            risks.append(f"Long-term trend structure is unfavorable: {detail}.")
        else:
            trend_label = "Mixed"

    if momentum_signals:
        buy_mom = sum(1 for s in momentum_signals if s["signal"] == "Buy")
        sell_mom = sum(1 for s in momentum_signals if s["signal"] == "Sell")
        if buy_mom > sell_mom:
            positives.append("Shorter-term momentum is currently supportive of the long-term view.")
        elif sell_mom > buy_mom:
            risks.append("Shorter-term momentum is currently working against the long-term view.")

    range_52w = fifty_two_week_range(history) if history is not None else None
    sma200_series = simple_moving_average(history["Close"], 200) if history is not None and "Close" in history.columns else None
    sma200 = sma200_series.iloc[-1] if sma200_series is not None and not sma200_series.empty else None
    if sma200 is not None and math.isnan(sma200):
        sma200 = None

    key_levels = {
        "52w_high": range_52w["high"] if range_52w else None,
        "52w_low": range_52w["low"] if range_52w else None,
        "sma200": sma200,
    }

    if key_levels["52w_high"] is not None:
        strengthen.append(f"A confirmed breakout above the 52-week high ({format_market_price(key_levels['52w_high'])})")
    if key_levels["52w_low"] is not None:
        weaken.append(f"A breakdown below the 52-week low ({format_market_price(key_levels['52w_low'])})")

    if not fundamentals_available:
        risks.insert(0, FUNDAMENTALS_UNAVAILABLE_NOTE)

    thesis = _build_thesis(display_name, stance, conviction, horizon, positives, risks, fundamentals_available)

    return {
        "ticker": ticker,
        "display_name": display_name,
        "asset_class": asset_class,
        "current_price": current_price,
        "conviction": conviction,
        "stance": stance,
        "horizon": horizon,
        "trend_label": trend_label,
        "thesis": thesis,
        "positives": positives,
        "risks": risks,
        "strengthen": strengthen,
        "weaken": weaken,
        "fundamentals_available": fundamentals_available,
        "financial_health": health,
        "technical": technical,
        "key_levels": key_levels,
    }


def _build_thesis(display_name, stance, conviction, horizon, positives, risks, fundamentals_available) -> str:
    lead = (
        f"{display_name} currently screens as {_article(stance)} {stance} on a {horizon} view, "
        f"with a conviction score of {conviction}/100 based on the data available today."
    )
    parts = [lead]
    if not fundamentals_available:
        parts.append("Fundamental data unavailable for this asset class — this reflects price trend and momentum only.")
    if positives:
        parts.append(positives[0])
    concrete_risks = [r for r in risks if r != FUNDAMENTALS_UNAVAILABLE_NOTE]
    if concrete_risks:
        parts.append(f"The main offsetting risk: {concrete_risks[0]}")
    return " ".join(parts)


def stance_for_universe(assets: list) -> list:
    """Sort a list of already-built investment-idea dicts by conviction,
    descending, dropping any that came back None (not enough data)."""
    return sorted((a for a in assets if a is not None), key=lambda a: a["conviction"], reverse=True)
