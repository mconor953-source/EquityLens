"""Deterministic Dashboard intelligence, derived from the same live price
snapshots as Global Markets / Major Assets / Market Movers — no AI/LLM, no
news feed, no economic calendar API. Every sentence and figure here is a
plain-English rendering of a real number (breadth, RSI, 52-week range),
computed the same way scoring.py and technicals.py compute everything else
in this app: fixed rules over real data, nothing generated or guessed.

Pure functions only, operating on a pre-fetched list of asset snapshots
(see views/dashboard.py) — no network calls in this module, same "no I/O
here" separation as scoring.py and idea_engine.py.
"""

RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
NEAR_EXTREME_PCT = 0.03  # within 3% of the trailing 52-week high/low

# Average absolute move across tracked assets -> a plain-English activity
# read, ordered best (most active) to worst (quietest) like scoring.py's bands.
ACTIVITY_BANDS = (
    (1.5, "unusually active, higher-volatility trading"),
    (0.5, "typical daily trading activity"),
    (0.0, "quiet, low-volatility trading"),
)

# Breadth ratio (advancing vs. declining) -> headline word.
BREADTH_RATIO = 1.5


def _activity_phrase(avg_abs_change: float) -> str:
    for minimum, phrase in ACTIVITY_BANDS:
        if avg_abs_change >= minimum:
            return phrase
    return ACTIVITY_BANDS[-1][1]


def get_market_pulse(snapshots: list) -> dict:
    """A rule-based market snapshot: breadth (advancing vs. declining),
    the largest mover, and an activity read from the average move size —
    one real sentence built from real numbers, not a generated narrative.

    Returns the same {headline, summary, watch_items} shape the Dashboard
    has always rendered, so the view code barely changes even though the
    content source did.
    """
    moved = [s for s in snapshots if s.get("pct_change") is not None]
    if not moved:
        return {
            "headline": "Market data is temporarily unavailable.",
            "summary": [
                "Yahoo Finance didn't return live prices for any tracked asset just now — usually a brief "
                "rate-limit or connectivity issue on their end, not a problem with your holdings or watchlists. "
                "Try refreshing in a moment."
            ],
            "watch_items": [],
        }

    advancing = [s for s in moved if s["pct_change"] > 0]
    declining = [s for s in moved if s["pct_change"] < 0]
    total = len(moved)

    if len(advancing) >= len(declining) * BREADTH_RATIO:
        breadth_word = "broadly higher"
    elif len(declining) >= len(advancing) * BREADTH_RATIO:
        breadth_word = "broadly lower"
    else:
        breadth_word = "mixed"

    headline = f"Markets are {breadth_word} today across the assets EquityLens tracks."

    biggest_gainer = max(moved, key=lambda s: s["pct_change"])
    biggest_decliner = min(moved, key=lambda s: s["pct_change"])
    avg_abs_change = sum(abs(s["pct_change"]) for s in moved) / total
    activity_phrase = _activity_phrase(avg_abs_change)

    summary = [
        f"{len(advancing)} of {total} tracked assets are advancing and {len(declining)} are declining, "
        f"consistent with {activity_phrase} (average move of {avg_abs_change:.2f}%).",
        f"{biggest_gainer['label']} leads gainers at {biggest_gainer['pct_change']:+.2f}%, while "
        f"{biggest_decliner['label']} is the weakest at {biggest_decliner['pct_change']:+.2f}%.",
    ]

    watch_items = [
        {"label": "Biggest Gainer", "detail": f"{biggest_gainer['label']} &middot; {biggest_gainer['pct_change']:+.2f}%"},
        {"label": "Biggest Decliner", "detail": f"{biggest_decliner['label']} &middot; {biggest_decliner['pct_change']:+.2f}%"},
        {"label": "Breadth", "detail": f"{len(advancing)} advancing &middot; {len(declining)} declining"},
    ]

    return {"headline": headline, "summary": summary, "watch_items": watch_items}


def get_notable_signals(snapshots: list) -> list:
    """Assets currently at a momentum extreme — RSI(14) <=30 (oversold) or
    >=70 (overbought) — using the same calculation as Market Research's
    Technical Rating. Real and deterministic; empty when nothing qualifies,
    never padded with filler."""
    signals = []
    for snap in snapshots:
        rsi = snap.get("rsi")
        if rsi is None:
            continue
        if rsi >= RSI_OVERBOUGHT:
            signals.append({"asset": snap["label"], "note": f"RSI at {rsi:.1f} — overbought after a strong run."})
        elif rsi <= RSI_OVERSOLD:
            signals.append({"asset": snap["label"], "note": f"RSI at {rsi:.1f} — oversold after a sharp pullback."})
    return signals


def get_52_week_extremes(snapshots: list) -> list:
    """Assets trading within 3% of their trailing 52-week high or low —
    the same range computation as Market Research's Price Statistics."""
    extremes = []
    for snap in snapshots:
        range_52w = snap.get("range_52w")
        price = snap.get("price")
        if not range_52w or price is None:
            continue
        high, low = range_52w["high"], range_52w["low"]
        if high == low:
            continue
        if price >= high * (1 - NEAR_EXTREME_PCT):
            distance = (high - price) / high * 100
            extremes.append({
                "asset": snap["label"],
                "note": f"Within {distance:.1f}% of its 52-week high.",
                "flag": "Near High",
            })
        elif price <= low * (1 + NEAR_EXTREME_PCT):
            distance = (price - low) / low * 100
            extremes.append({
                "asset": snap["label"],
                "note": f"Within {distance:.1f}% of its 52-week low.",
                "flag": "Near Low",
            })
    return extremes
