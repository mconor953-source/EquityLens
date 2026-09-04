"""Market Structure — deterministic multi-timeframe price-structure engine.

Deliberately not named market_structure.py — views/market_structure.py is
the page that imports this module, and Streamlit's per-page script
execution puts each page's own directory on sys.path, so a same-named
module there would shadow this one (the same reason idea_engine.py isn't
named investment_ideas.py, and dashboard_content.py isn't named dashboard.py).

Public naming vs internal naming: this implements an Indication / Correction
/ Continuation (ICC) sequence, but that vocabulary never reaches the UI.
Internally: INDICATION -> "break"/"indication" fields, CORRECTION ->
"correction" fields, CONTINUATION -> "continuation" fields. Externally
(views/market_structure.py) these render as "Breakout/Breakdown",
"Pullback/Correction", and "Continuation" — see PUBLIC_STATE_LABELS below.

Pipeline (deterministic, no AI, no screenshot recognition):

    OHLC history (4H / 1H / 15m / 5m)
        -> detect_swings()            per-timeframe fractal pivots
        -> alternate_swings()         reduce to a strict high/low zigzag
        -> classify_structure()       label each swing HH / HL / LH / LL
        -> structure_bias()           read the last two labels as a trend
        -> get_key_levels()           most recent un-broken swing high/low
        -> detect_close_break()       has a CLOSE crossed the level (never a wick)
        -> lower-timeframe bias       used to detect correction / continuation
        -> determine_state()          one fixed state from Part 31's list
        -> generate_explanation()     a plain paragraph built from the above

Nothing here computes a probability, a trade recommendation, an entry, a
stop, or a position size (see views/market_structure.py's own guarantees).
Every field in the result dict traces back to a real number pulled from
real OHLC data — if a timeframe's data can't be fetched, that timeframe's
entry is None and every downstream step treats it as "insufficient data"
rather than guessing.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration — internal defaults; not exposed to the normal user (Part 46
# lets an advanced settings panel override these, see views/market_structure.py).
# ---------------------------------------------------------------------------
TIMEFRAMES = ("4H", "1H", "15m", "5m")

# yfinance (period, interval) per timeframe. 4H has no native yfinance
# interval, so it's built by resampling 1H bars (see resample_to_4h). These
# windows are deliberately "recent structure" sized (weeks, not years) —
# "the most recent swing high/low" should mean recent, and a huge fetch
# window mostly just adds latency and stale, irrelevant swing points.
FETCH_PARAMS = {
    "1H": {"period": "60d", "interval": "1h"},
    "15m": {"period": "30d", "interval": "15m"},
    "5m": {"period": "10d", "interval": "5m"},
}

# Fractal swing sensitivity per timeframe — a swing point must be the most
# extreme candle among this many neighbors on BOTH sides. Calibrated
# against real data (see market_structure design notes) so each timeframe
# yields on the order of 1-2 swings per trading day rather than a swing
# every few candles — the "avoid marking every tiny movement" requirement.
# Higher = fewer, more significant swings; lower = more, noisier swings.
DEFAULT_SENSITIVITY = {"4H": 3, "1H": 6, "15m": 6, "5m": 6}

REQUIRE_CANDLE_CLOSE = True  # Part 27/28 — a wick through a level is never a break

MIN_CANDLES_FOR_SWINGS = 20  # below this, a timeframe is "insufficient data"

PUBLIC_STATE_LABELS = {
    "no_clear_structure": "No Clear Structure",
    "watching_seller_level": "Watching Seller Level",
    "watching_buyer_level": "Watching Buyer Level",
    "bullish_breakout_confirmed": "Bullish Breakout Confirmed",
    "bearish_breakdown_confirmed": "Bearish Breakdown Confirmed",
    "bullish_pullback_in_progress": "Bullish Pullback In Progress",
    "bearish_correction_in_progress": "Bearish Correction In Progress",
    "bullish_continuation_developing": "Bullish Continuation Developing",
    "bearish_continuation_developing": "Bearish Continuation Developing",
    "bullish_continuation_confirmed": "Bullish Continuation Confirmed",
    "bearish_continuation_confirmed": "Bearish Continuation Confirmed",
    "invalidated": "Invalidated",
}


# ---------------------------------------------------------------------------
# Step 1 — swing detection (fractal / pivot pattern)
# ---------------------------------------------------------------------------
def detect_swings(history: pd.DataFrame, sensitivity: int) -> list:
    """A candle is a swing HIGH if its High is strictly greater than the
    High of `sensitivity` candles immediately before AND after it (and the
    mirror for swing LOW). This is the classic "fractal" pivot definition —
    simple, deterministic, and it naturally ignores single-candle noise
    once sensitivity >= 2, since a real swing needs several candles on
    each side to actually be more extreme than.

    Returns a chronological list of {"time", "price", "type": "high"|"low"}.
    """
    if history is None or len(history) < sensitivity * 2 + 1:
        return []

    highs = history["High"]
    lows = history["Low"]
    n = len(history)
    swings = []

    for i in range(sensitivity, n - sensitivity):
        left_high = highs.iloc[i - sensitivity:i]
        right_high = highs.iloc[i + 1:i + 1 + sensitivity]
        if highs.iloc[i] > left_high.max() and highs.iloc[i] > right_high.max():
            swings.append({"time": history.index[i], "price": float(highs.iloc[i]), "type": "high"})

        left_low = lows.iloc[i - sensitivity:i]
        right_low = lows.iloc[i + 1:i + 1 + sensitivity]
        if lows.iloc[i] < left_low.min() and lows.iloc[i] < right_low.min():
            swings.append({"time": history.index[i], "price": float(lows.iloc[i]), "type": "low"})

    swings.sort(key=lambda s: s["time"])
    return swings


def alternate_swings(swings: list) -> list:
    """Reduce a raw swing list to a strict high/low zigzag: when two swings
    of the same type occur back-to-back with no opposite-type swing between
    them, only the more extreme one survives. Real structure analysis reads
    an alternating sequence of highs and lows — this is the step that
    guarantees one."""
    if not swings:
        return []
    reduced = [swings[0]]
    for s in swings[1:]:
        last = reduced[-1]
        if s["type"] == last["type"]:
            if (s["type"] == "high" and s["price"] > last["price"]) or (s["type"] == "low" and s["price"] < last["price"]):
                reduced[-1] = s
        else:
            reduced.append(s)
    return reduced


# ---------------------------------------------------------------------------
# Step 2 — HH / HL / LH / LL classification and trend bias
# ---------------------------------------------------------------------------
def classify_structure(alt_swings: list) -> list:
    """Label each swing relative to the previous swing of the *same* type:
    a high above the prior high is HH, below is LH; a low above the prior
    low is HL, below is LL. The first high and first low in the sequence
    have nothing to compare to and are labeled "H"/"L"."""
    labeled = []
    last_high = None
    last_low = None
    for s in alt_swings:
        if s["type"] == "high":
            label = "H" if last_high is None else ("HH" if s["price"] > last_high["price"] else "LH")
            last_high = s
        else:
            label = "L" if last_low is None else ("HL" if s["price"] > last_low["price"] else "LL")
            last_low = s
        labeled.append({**s, "label": label})
    return labeled


def structure_bias(labeled_swings: list) -> str:
    """Read overall bias from the most recent classified high and low:
    HH+HL together -> bullish, LH+LL together -> bearish, anything mixed
    (e.g. a fresh HH but still HL pending, or one LH against an HL) ->
    "developing" — not yet a clean trend in either direction."""
    highs = [s for s in labeled_swings if s["type"] == "high" and s["label"] in ("HH", "LH")]
    lows = [s for s in labeled_swings if s["type"] == "low" and s["label"] in ("HL", "LL")]
    if not highs or not lows:
        return "neutral"
    last_high_label = highs[-1]["label"]
    last_low_label = lows[-1]["label"]
    if last_high_label == "HH" and last_low_label == "HL":
        return "bullish"
    if last_high_label == "LH" and last_low_label == "LL":
        return "bearish"
    return "developing"


# ---------------------------------------------------------------------------
# Step 3 — key levels (Part 27/28: most recent un-broken swing high/low)
# ---------------------------------------------------------------------------
def get_key_levels(labeled_swings: list) -> dict:
    """The seller level is the most recent swing high (an area sellers
    previously took control); the buyer level is the most recent swing low
    (an area buyers previously took control). Whether either has since been
    broken is a separate question — see detect_close_break()."""
    highs = [s for s in labeled_swings if s["type"] == "high"]
    lows = [s for s in labeled_swings if s["type"] == "low"]
    return {
        "seller_level": highs[-1] if highs else None,
        "buyer_level": lows[-1] if lows else None,
    }


# ---------------------------------------------------------------------------
# Step 4 — candle-close break detection (Part 27/28 — a wick never counts)
# ---------------------------------------------------------------------------
def detect_close_break(history: pd.DataFrame, level: dict, direction: str) -> dict:
    """First candle whose CLOSE crossed beyond `level`, among candles after
    the level itself formed. direction="bullish" requires a close above a
    seller level; direction="bearish" requires a close below a buyer level.
    A high/low wick beyond the level with the close still on the near side
    does not count — this function only ever looks at Close.
    """
    if level is None or history is None or history.empty:
        return {"broken": False}

    after_level = history[history.index > level["time"]]
    if after_level.empty:
        return {"broken": False}

    if direction == "bullish":
        crossed = after_level[after_level["Close"] > level["price"]]
    else:
        crossed = after_level[after_level["Close"] < level["price"]]

    if crossed.empty:
        return {"broken": False}

    break_time = crossed.index[0]
    return {"broken": True, "time": break_time, "close": float(crossed["Close"].iloc[0])}


# ---------------------------------------------------------------------------
# Per-timeframe bundle
# ---------------------------------------------------------------------------
def analyze_timeframe(history: pd.DataFrame, sensitivity: int) -> dict:
    """Bundle swings/labels/bias/levels for one timeframe's OHLC data.
    Returns None if there isn't enough history to say anything — callers
    must treat that as "insufficient data," never as a bearish/bullish
    read."""
    if history is None or len(history) < MIN_CANDLES_FOR_SWINGS:
        return None
    swings = alternate_swings(detect_swings(history, sensitivity))
    labeled = classify_structure(swings)
    return {
        "swings": labeled,
        "bias": structure_bias(labeled),
        "levels": get_key_levels(labeled),
        "candle_count": len(history),
        "last_time": history.index[-1],
    }


def resample_to_4h(history_1h: pd.DataFrame) -> pd.DataFrame:
    """Build 4H bars from 1H data — yfinance has no native 4h interval.
    Anchored to 00:00 so bars land on consistent 4-hour boundaries rather
    than wherever the data happens to start."""
    if history_1h is None or history_1h.empty:
        return history_1h
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in history_1h.columns:
        agg["Volume"] = "sum"
    resampled = history_1h.resample("4h", origin="start_day").agg(agg).dropna(subset=["Open"])
    return resampled


# ---------------------------------------------------------------------------
# Step 5 — the state machine (Part 29-31)
# ---------------------------------------------------------------------------
def determine_state(tf: dict) -> dict:
    """The core ICC/structure decision, driven primarily by 1H (with 4H as
    context) for bias and levels, and 15m/5m for correction/continuation
    confirmation — exactly the "4H/1H lead, 15m/5m confirm" split Part 24
    asks for. `tf` is {"4H": bundle_or_None, "1H": ..., "15m": ..., "5m": ...}
    from analyze_timeframe(). Returns {"state": <key>, "direction":
    "bullish"|"bearish"|None, "break": {...}, "quality_factors": {...}}.
    """
    htf, primary, ltf1, ltf2 = tf.get("4H"), tf.get("1H"), tf.get("15m"), tf.get("5m")

    if primary is None:
        return {"state": "no_clear_structure", "direction": None, "break": None, "quality_factors": {}}

    primary_bias = primary["bias"]
    htf_bias = htf["bias"] if htf else None

    # Overall directional lean: 1H bias, but "developing" on 1H falls back
    # to 4H context if 4H has a clean read — matches "4H and 1H are the
    # most important" without letting a noisy 1H alone decide everything.
    if primary_bias in ("bullish", "bearish"):
        direction = primary_bias
    elif htf_bias in ("bullish", "bearish"):
        direction = htf_bias
    else:
        return {"state": "no_clear_structure", "direction": None, "break": None, "quality_factors": {}}

    level_key = "seller_level" if direction == "bullish" else "buyer_level"
    level = primary["levels"].get(level_key)
    if level is None:
        return {"state": "no_clear_structure", "direction": direction, "break": None, "quality_factors": {}}

    # We need the raw 1H history to test candle closes against the level;
    # analyze_timeframe doesn't keep it, so the caller (build_market_structure)
    # passes it in via tf["_history"]["1H"] rather than re-fetching here.
    history_1h = tf.get("_history", {}).get("1H")
    break_info = detect_close_break(history_1h, level, direction) if REQUIRE_CANDLE_CLOSE else {"broken": True, "time": level["time"], "close": level["price"]}

    quality_factors = {
        "4h_aligned": bool(htf and htf_bias == direction),
        "1h_bias_clean": primary_bias in ("bullish", "bearish"),
        "close_confirmed_break": bool(break_info.get("broken")),
    }

    if not break_info.get("broken"):
        state = "watching_seller_level" if direction == "bullish" else "watching_buyer_level"
        return {"state": state, "direction": direction, "break": break_info, "quality_factors": quality_factors}

    # Broken — now read lower-timeframe structure formed *after* the break
    # to tell correction from continuation. Part 24: 15m/5m only confirm,
    # they never override the higher-timeframe idea by themselves.
    ltf1_after = _bias_after(ltf1, break_info["time"])
    ltf2_after = _bias_after(ltf2, break_info["time"])
    quality_factors["15m_confirms"] = ltf1_after == direction
    quality_factors["5m_confirms"] = ltf2_after == direction

    opposite = "bearish" if direction == "bullish" else "bullish"
    correcting = ltf1_after == opposite or ltf2_after == opposite
    continuation_signal = (ltf1_after == direction) or (ltf2_after == direction)

    # Invalidation: price closes back through the *opposite* level (the
    # level that would confirm the trend has failed), after having broken
    # the original level.
    invalidation_level = primary["levels"].get("buyer_level" if direction == "bullish" else "seller_level")
    invalidated = False
    if invalidation_level is not None and history_1h is not None:
        inv_direction = "bearish" if direction == "bullish" else "bullish"
        inv_break = detect_close_break(history_1h, invalidation_level, inv_direction)
        if inv_break.get("broken") and inv_break["time"] > break_info["time"]:
            invalidated = True

    if invalidated:
        state = "invalidated"
    elif not correcting and not continuation_signal:
        state = "bullish_breakout_confirmed" if direction == "bullish" else "bearish_breakdown_confirmed"
    elif correcting and not continuation_signal:
        state = "bullish_pullback_in_progress" if direction == "bullish" else "bearish_correction_in_progress"
    elif continuation_signal and not (quality_factors["15m_confirms"] and quality_factors["5m_confirms"]):
        state = "bullish_continuation_developing" if direction == "bullish" else "bearish_continuation_developing"
    else:
        state = "bullish_continuation_confirmed" if direction == "bullish" else "bearish_continuation_confirmed"

    return {"state": state, "direction": direction, "break": break_info, "quality_factors": quality_factors}


def _bias_after(tf_bundle: dict, cutoff_time) -> str:
    """Re-read a timeframe's bias using only swings formed at/after
    `cutoff_time` — used to judge lower-timeframe structure *since the
    break*, not its structure over its whole fetch window."""
    if tf_bundle is None:
        return "neutral"
    recent = [s for s in tf_bundle["swings"] if s["time"] >= cutoff_time]
    if len(recent) < 2:
        return tf_bundle["bias"]  # not enough post-break swings yet — fall back to full-window bias
    return structure_bias(classify_structure(recent))


# ---------------------------------------------------------------------------
# Step 6 — structure quality (Part 38 — explainable factors, never a
# fake win probability)
# ---------------------------------------------------------------------------
def structure_quality(quality_factors: dict) -> str:
    if not quality_factors:
        return "N/A"
    score = sum(1 for v in quality_factors.values() if v)
    total = len(quality_factors)
    ratio = score / total if total else 0
    if ratio >= 0.8:
        return "Strong"
    if ratio >= 0.5:
        return "Moderate"
    return "Weak"


# ---------------------------------------------------------------------------
# Step 7 — human-readable explanation (Part 35 — generated, not an LLM)
# ---------------------------------------------------------------------------
def generate_explanation(ticker: str, tf: dict, decision: dict) -> str:
    state = decision["state"]
    direction = decision["direction"]
    lines = []

    htf, primary = tf.get("4H"), tf.get("1H")
    if htf:
        lines.append(f"4H structure is currently {htf['bias']}.")
    if primary:
        lines.append(f"1H structure is currently {primary['bias']}.")

    break_info = decision.get("break")
    level_word = "seller" if direction == "bullish" else "buyer"
    if break_info and break_info.get("broken") and primary:
        level = primary["levels"].get(f"{level_word}_level")
        if level:
            verb = "closed above" if direction == "bullish" else "closed below"
            lines.append(f"Price {verb} the 1H {level_word} level at {level['price']:.4f}, confirming the break.")
    elif primary:
        level = primary["levels"].get(f"{level_word}_level")
        if level:
            lines.append(f"Price has not yet closed beyond the 1H {level_word} level at {level['price']:.4f}.")

    if state in ("bullish_pullback_in_progress", "bearish_correction_in_progress"):
        lines.append("Lower-timeframe (15m/5m) structure currently shows the opposite short-term bias — consistent with a correction after the break, not an invalidation of the higher-timeframe idea.")
    elif state in ("bullish_continuation_developing", "bearish_continuation_developing"):
        lines.append("Lower-timeframe structure is starting to shift back in the original direction, but 15m and 5m aren't both confirming yet.")
    elif state in ("bullish_continuation_confirmed", "bearish_continuation_confirmed"):
        lines.append("Both 15m and 5m structure have shifted back in line with the higher-timeframe direction.")
    elif state == "invalidated":
        lines.append("Price has since closed back through the opposite key level, invalidating this structure read.")
    elif state in ("watching_seller_level", "watching_buyer_level"):
        lines.append("No confirmed break yet — this level is being watched.")

    if not lines:
        return f"Not enough clear structure on {ticker} across the analyzed timeframes to describe a setup."

    return " ".join(lines)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------
def build_market_structure(ticker: str, sensitivity: dict = None) -> dict:
    """Fetch 4H/1H/15m/5m history, run the full pipeline, and return one
    result dict. Never raises — a timeframe that can't be fetched is simply
    None everywhere downstream, and the state machine degrades to
    "no_clear_structure" rather than crashing the page. Import
    data_fetcher's fetchers lazily inside the function so this module has
    zero import-time dependency on Streamlit's cache decorator running in a
    live app context (keeps it testable from plain Python, same as
    technicals.py/scoring.py).
    """
    from data_fetcher import get_intraday_history

    sensitivity = sensitivity or DEFAULT_SENSITIVITY

    raw_history = {}
    for label in ("1H", "15m", "5m"):
        params = FETCH_PARAMS[label]
        try:
            raw_history[label] = get_intraday_history(ticker, params["period"], params["interval"])
        except Exception:
            raw_history[label] = None
    raw_history["4H"] = resample_to_4h(raw_history.get("1H"))

    tf = {"_history": raw_history}
    for label in TIMEFRAMES:
        tf[label] = analyze_timeframe(raw_history.get(label), sensitivity.get(label, 2))

    decision = determine_state(tf)
    explanation = generate_explanation(ticker, tf, decision)
    quality = structure_quality(decision.get("quality_factors", {}))

    return {
        "ticker": ticker,
        "state": decision["state"],
        "state_label": PUBLIC_STATE_LABELS[decision["state"]],
        "direction": decision["direction"],
        "break": decision.get("break"),
        "quality": quality,
        "quality_factors": decision.get("quality_factors", {}),
        "explanation": explanation,
        "timeframes": {label: tf.get(label) for label in TIMEFRAMES},
        "history": raw_history,
        "data_available": {label: raw_history.get(label) is not None for label in TIMEFRAMES},
    }
