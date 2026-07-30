"""Technical analysis: moving averages, oscillators, and a rule-based
Technical Rating. Deterministic and fully rule-based — no AI/ML, no
predictive model — same philosophy as scoring.py (Financial Health Score).

Pure functions only, operating on a price-history DataFrame as returned by
data_fetcher.get_price_history. No UI, no network calls.

The Technical Rating mirrors the "signal count" approach used by real
charting platforms: a fixed basket of moving averages and momentum
oscillators are each independently classified Buy / Sell / Neutral, and the
overall rating is the balance across all of them. Any signal that can't be
computed (not enough history) is simply omitted rather than guessed.
"""

import pandas as pd

MA_WINDOWS = (20, 50, 100, 200)
RSI_PERIOD = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
ROC_PERIOD = 10
VOLUME_WINDOW = 20
TRADING_DAYS_PER_YEAR = 252

# Overall rating bands: (minimum buy/sell balance, label), scanned best to
# worst. Balance is (buy_count - sell_count) / total_signals, so it ranges
# from -1.0 (all sell) to +1.0 (all buy).
RATING_BANDS = (
    (0.5, "Strong Buy"),
    (0.15, "Buy"),
    (-0.15, "Neutral"),
    (-0.5, "Sell"),
    (float("-inf"), "Strong Sell"),
)


def simple_moving_average(closes: pd.Series, window: int):
    """Rolling SMA, or None if there isn't enough history to seed it."""
    if closes is None or len(closes) < window:
        return None
    return closes.rolling(window=window).mean()


def relative_strength_index(closes: pd.Series, period: int = RSI_PERIOD):
    """Wilder's RSI via an exponential moving average of gains/losses."""
    if closes is None or len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.where(avg_loss != 0, 100)  # no losses in the lookback -> RSI 100


def macd(closes: pd.Series, fast: int = MACD_FAST, slow: int = MACD_SLOW, signal: int = MACD_SIGNAL):
    """Standard MACD: fast/slow EMA spread, plus its own signal-line EMA."""
    if closes is None or len(closes) < slow + signal:
        return None
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return {"macd_line": macd_line, "signal_line": signal_line, "histogram": macd_line - signal_line}


def rate_of_change(closes: pd.Series, period: int = ROC_PERIOD):
    """% price change over `period` bars — a simple momentum oscillator."""
    if closes is None or len(closes) < period + 1:
        return None
    return (closes - closes.shift(period)) / closes.shift(period) * 100


def annualized_volatility(closes: pd.Series, trading_days: int = TRADING_DAYS_PER_YEAR):
    """Standard deviation of daily returns, annualized. Returns a fraction
    (0.35 == 35%), consistent with the other ratio metrics in this app."""
    if closes is None or len(closes) < 2:
        return None
    daily_returns = closes.pct_change().dropna()
    if daily_returns.empty:
        return None
    return daily_returns.std() * (trading_days ** 0.5)


def fifty_two_week_range(history: pd.DataFrame):
    """High/low over the trailing ~252 trading days (or all available
    history if shorter, e.g. a recently listed ticker)."""
    if history is None or history.empty:
        return None
    window = history.tail(TRADING_DAYS_PER_YEAR) if len(history) > TRADING_DAYS_PER_YEAR else history
    return {"high": window["High"].max(), "low": window["Low"].min()}


def volume_ratio(history: pd.DataFrame, window: int = VOLUME_WINDOW):
    """Latest volume vs. its trailing `window`-day average. None for
    instruments yfinance doesn't report meaningful volume for (most forex
    pairs and indices report an all-zero volume column)."""
    if history is None or "Volume" not in history.columns:
        return None
    volume = history["Volume"]
    if volume.fillna(0).sum() == 0 or len(volume) < window + 1:
        return None
    average_volume = volume.iloc[-(window + 1):-1].mean()
    latest_volume = volume.iloc[-1]
    if not average_volume:
        return None
    return {"latest": latest_volume, "average": average_volume, "ratio": latest_volume / average_volume}


def _signal_price_vs_ma(price, ma_value):
    if ma_value is None or pd.isna(ma_value):
        return None
    return "Buy" if price > ma_value else "Sell"


def _signal_ma_cross(short_ma, long_ma):
    if short_ma is None or long_ma is None or pd.isna(short_ma) or pd.isna(long_ma):
        return None
    return "Buy" if short_ma > long_ma else "Sell"


def _signal_rsi(rsi_value):
    if rsi_value is None or pd.isna(rsi_value):
        return None
    if rsi_value < 30:
        return "Buy"       # oversold — standard oscillator convention
    if rsi_value > 70:
        return "Sell"      # overbought
    return "Neutral"


def _signal_macd(macd_line_value, signal_line_value):
    if macd_line_value is None or signal_line_value is None or pd.isna(macd_line_value) or pd.isna(signal_line_value):
        return None
    return "Buy" if macd_line_value > signal_line_value else "Sell"


def _signal_roc(roc_value):
    if roc_value is None or pd.isna(roc_value):
        return None
    return "Buy" if roc_value > 0 else "Sell"


def _rating_for_balance(balance):
    for minimum, label in RATING_BANDS:
        if balance >= minimum:
            return label
    return RATING_BANDS[-1][1]


def compute_technical_rating(history: pd.DataFrame) -> dict:
    """Compute a signal-count Technical Rating from price history alone —
    works for every asset class (stocks, crypto, forex, metals, indices),
    since it needs only OHLC data, not fundamentals.

    Basket: price vs. SMA 20/50/100/200, the 50/200-day cross, RSI(14),
    MACD(12,26,9), and 10-day Rate of Change — 7 signals when full history
    is available. Each is independently Buy / Sell / Neutral; the overall
    rating is the buy/sell balance across whichever signals could be
    computed. Returns None if there isn't enough history to compute any of
    them (fewer than ~15 bars).
    """
    if history is None or history.empty or "Close" not in history.columns:
        return None

    closes = history["Close"]
    if len(closes) < 15:
        return None
    price = closes.iloc[-1]

    sma_values = {window: simple_moving_average(closes, window) for window in MA_WINDOWS}
    rsi_series = relative_strength_index(closes)
    macd_data = macd(closes)
    roc_series = rate_of_change(closes)

    signals = []

    for window in MA_WINDOWS:
        sma = sma_values[window]
        current = sma.iloc[-1] if sma is not None else None
        sig = _signal_price_vs_ma(price, current)
        if sig:
            signals.append({
                "name": f"SMA {window}",
                "signal": sig,
                "detail": f"Price is {'above' if sig == 'Buy' else 'below'} the {window}-day simple moving average.",
            })

    sma50 = sma_values[50]
    sma200 = sma_values[200]
    cross_sig = _signal_ma_cross(
        sma50.iloc[-1] if sma50 is not None else None,
        sma200.iloc[-1] if sma200 is not None else None,
    )
    if cross_sig:
        label = "Golden Cross — 50-day is above the 200-day." if cross_sig == "Buy" else "Death Cross — 50-day is below the 200-day."
        signals.append({"name": "MA Cross (50/200)", "signal": cross_sig, "detail": label})

    rsi_val = rsi_series.iloc[-1] if rsi_series is not None else None
    rsi_sig = _signal_rsi(rsi_val)
    if rsi_sig:
        signals.append({
            "name": "RSI (14)",
            "signal": rsi_sig,
            "detail": f"RSI at {rsi_val:.1f}"
            + (" — oversold." if rsi_sig == "Buy" else " — overbought." if rsi_sig == "Sell" else " — neutral zone."),
        })

    macd_line_val = macd_data["macd_line"].iloc[-1] if macd_data is not None else None
    signal_line_val = macd_data["signal_line"].iloc[-1] if macd_data is not None else None
    macd_sig = _signal_macd(macd_line_val, signal_line_val)
    if macd_sig:
        signals.append({
            "name": "MACD (12,26,9)",
            "signal": macd_sig,
            "detail": f"MACD line is {'above' if macd_sig == 'Buy' else 'below'} its signal line.",
        })

    roc_val = roc_series.iloc[-1] if roc_series is not None else None
    roc_sig = _signal_roc(roc_val)
    if roc_sig:
        signals.append({
            "name": "Rate of Change (10D)",
            "signal": roc_sig,
            "detail": f"Price is {roc_val:+.1f}% over the last 10 trading days.",
        })

    if not signals:
        return None

    buy_count = sum(1 for s in signals if s["signal"] == "Buy")
    sell_count = sum(1 for s in signals if s["signal"] == "Sell")
    neutral_count = sum(1 for s in signals if s["signal"] == "Neutral")
    total = len(signals)
    balance = (buy_count - sell_count) / total

    return {
        "rating": _rating_for_balance(balance),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "neutral_count": neutral_count,
        "total_signals": total,
        "signals": signals,
        "rsi": rsi_val,
    }
