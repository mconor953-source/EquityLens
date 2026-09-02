"""Data access layer: wraps yfinance calls and formats raw numbers for display.

Root cause of the "everything shows N/A at once" failure mode: by default,
yfinance sets `yf.config.debug.hide_exceptions = True`, which makes it
silently swallow real fetch errors (HTTP errors, rate limits, timeouts) and
just return an empty DataFrame — no exception raised, nothing logged
anywhere. When Yahoo has a momentary hiccup, every ticker in a batch fails
the same silent way at once, and there's no diagnostic trail to tell "Yahoo
rate-limited us" apart from "these are somehow all invalid tickers." That
flag is flipped off below so failures actually raise and can be logged.

Yahoo Finance occasionally rate-limits or momentarily rejects a request —
not a code bug, just the reality of a free, unofficial data source. Every
network call in this module goes through _with_retries() so a single
transient blip (one dropped connection, one 429) doesn't have to fail the
whole Dashboard: it's retried a couple of times with a short backoff before
the caller ever sees an exception. Failures (transient or final) are logged
to the terminal via the standard `logging` module so they're diagnosable —
never as a raw traceback shown to the user, who instead sees a plain "N/A"
or "data unavailable" from the calling view.
"""

import logging
import time

import yfinance as yf
import pandas as pd
from yfinance.exceptions import YFTickerMissingError, YFPricesMissingError

from cache_utils import ttl_cache

yf.config.debug.hide_exceptions = False

logger = logging.getLogger("equitylens.data_fetcher")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

MAX_ATTEMPTS = 3            # 1 initial try + 2 retries
RETRY_BACKOFF_SECONDS = 0.6  # multiplied by attempt number between tries


def _is_permanent_failure(exc: Exception) -> bool:
    """True for a genuinely invalid/delisted ticker — retrying a 404 or a
    "no data for this symbol" error just wastes time, since Yahoo will say
    the same thing every attempt. Everything else (rate limits, timeouts,
    connection resets, 5xx) is treated as possibly transient and retried —
    that's the failure mode this module exists to absorb."""
    if isinstance(exc, (YFTickerMissingError, YFPricesMissingError)):
        return True
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    return status_code == 404


def _with_retries(description: str, fetch):
    """Call the no-arg `fetch` callable, retrying transient failures with a
    short backoff. Logs every attempt; re-raises the last exception once
    attempts are exhausted (or immediately, for a permanent failure) so
    existing callers' try/except (they all already have one — see
    get_current_price_and_change and every view) keeps working exactly as
    before, just with real transient failures now self-healing instead of
    surfacing on the first hiccup."""
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch()
        except Exception as exc:
            last_exc = exc
            permanent = _is_permanent_failure(exc)
            logger.warning(
                "%s failed (attempt %d/%d, %s): %s: %s",
                description, attempt, MAX_ATTEMPTS,
                "not retrying — no data for this ticker" if permanent else "will retry",
                type(exc).__name__, exc,
            )
            if permanent:
                raise
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    logger.error("%s failed after %d attempts — giving up.", description, MAX_ATTEMPTS)
    raise last_exc


@ttl_cache(300)
def get_ticker_info(ticker: str) -> dict:
    """Fetch company/financial info for a ticker. Cached for 5 minutes.

    Every caller in this app relies on this never raising — they check
    is_valid_ticker(info) on the result rather than wrapping the call in
    try/except. That contract is preserved here: retries happen internally,
    and a final failure (invalid ticker, or Yahoo still down after retries)
    is logged and returned as {} — which is_valid_ticker() already reads as
    "no data" — rather than propagating an exception nothing upstream
    expects.
    """
    try:
        return _with_retries(f"get_ticker_info({ticker})", lambda: yf.Ticker(ticker).info)
    except Exception:
        return {}


@ttl_cache(300)
def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical OHLCV price data for a ticker. Cached for 5 minutes.

    yfinance sometimes includes a trailing row for the current, still-open
    session with no data yet (all-NaN OHLC) — that row is dropped so charts
    and price calculations never end on an empty bar.

    An empty result is treated as a retryable failure too (not just a raised
    exception): Yahoo occasionally returns a 200 with no rows for a
    known-good ticker during a rate-limited window, which looks identical to
    "no data" but usually clears up within a retry or two.
    """
    def _fetch():
        history = yf.Ticker(ticker).history(period=period)
        if history is None or history.empty:
            raise ValueError(f"empty price history returned for '{ticker}' (period={period})")
        if "Close" in history.columns:
            history = history.dropna(subset=["Close"])
        return history

    return _with_retries(f"get_price_history({ticker}, period={period})", _fetch)


@ttl_cache(300)
def get_intraday_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Fetch intraday OHLC data at a specific interval (e.g. "1h", "15m",
    "5m") — used by market_structure.py for multi-timeframe analysis.
    Separate from get_price_history because Yahoo's intraday endpoint has
    real limits get_price_history's daily-only callers never hit: 1h data
    only goes back ~730 days, 15m/5m only ~60 days. Same retry/logging
    behavior as get_price_history — an empty result is retried, then
    raised, and every caller is expected to catch it (market_structure.py
    treats a failed timeframe as "insufficient data" for that timeframe,
    never a whole-page crash).

    Yahoo has no native 4-hour interval; market_structure.py builds 4H bars
    by resampling 1h data itself (see resample_to_4h there) rather than
    this function pretending interval="4h" is a real yfinance option.
    """
    def _fetch():
        history = yf.Ticker(ticker).history(period=period, interval=interval)
        if history is None or history.empty:
            raise ValueError(f"empty intraday history returned for '{ticker}' (period={period}, interval={interval})")
        if "Close" in history.columns:
            history = history.dropna(subset=["Close"])
        return history

    return _with_retries(f"get_intraday_history({ticker}, period={period}, interval={interval})", _fetch)


def get_current_price_and_change(ticker: str, period: str = "5d"):
    """Return (current_price, pct_change) from the last two daily closes.

    Works across every asset class (stocks, crypto, forex, metals, indices)
    since it reads directly from price history rather than the inconsistent
    `.info` fields those asset types don't all populate. Returns (None, None)
    if no data is available for the ticker.
    """
    try:
        history = get_price_history(ticker, period=period)
    except Exception:
        return None, None

    if history.empty or "Close" not in history.columns:
        return None, None

    current_price = history["Close"].iloc[-1]
    if len(history) < 2:
        return current_price, None

    previous_close = history["Close"].iloc[-2]
    pct_change = (current_price - previous_close) / previous_close * 100 if previous_close else None
    return current_price, pct_change


def is_valid_ticker(info: dict) -> bool:
    """A delisted/invalid ticker returns an info dict with no name and no price."""
    if not info:
        return False
    has_name = bool(info.get("longName") or info.get("shortName"))
    has_price = info.get("currentPrice") is not None or info.get("regularMarketPrice") is not None
    return has_name and has_price


def format_large_number(value, prefix: str = "$") -> str:
    """Convert a raw number into a readable scale, e.g. 3.51e12 -> '$3.51T'."""
    if value is None:
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1e12:
        scaled = f"{value / 1e12:.2f}T"
    elif abs_value >= 1e9:
        scaled = f"{value / 1e9:.2f}B"
    elif abs_value >= 1e6:
        scaled = f"{value / 1e6:.2f}M"
    else:
        scaled = f"{value:,.0f}"
    return f"{prefix}{scaled}"


def format_ratio(value) -> str:
    """Format a plain ratio like P/E to two decimal places."""
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def format_price(value) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_market_price(value) -> str:
    """Format a price with precision appropriate to its magnitude: more
    decimals for sub-$10 instruments (most forex pairs trade near 1.00-1.50
    and need that precision to show meaningful movement), standard cents
    otherwise. Same convention already used inline on Market Research."""
    if value is None:
        return "N/A"
    return f"${value:,.4f}" if value < 10 else f"${value:,.2f}"


def format_percentage(value) -> str:
    """Format a fractional ratio as a percentage, e.g. 0.166 -> '16.60%'."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def format_multiple(value) -> str:
    """Format a ratio as a multiple, e.g. 0.795 -> '0.80x'."""
    if value is None:
        return "N/A"
    return f"{value:.2f}x"


RECOMMENDATION_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "underperform": "Underperform",
    "sell": "Sell",
}


def get_analyst_consensus(info: dict) -> dict:
    """Extract Wall Street analyst coverage from the yfinance info dict —
    real sell-side data (recommendation, price targets, analyst count), not
    computed here. Returns raw values (None if uncovered); formatting is
    handled by the view."""
    key = (info.get("recommendationKey") or "").lower()
    return {
        "recommendation": RECOMMENDATION_LABELS.get(key, key.replace("_", " ").title() if key else None),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "target_mean": info.get("targetMeanPrice"),
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
    }


QUOTE_TYPE_TO_ASSET_CLASS = {
    "EQUITY": "Stock",
    "ETF": "ETF",
    "INDEX": "Index",
    "CURRENCY": "Forex",
    "CRYPTOCURRENCY": "Crypto",
    "FUTURE": "Commodity",
    "COMMODITY": "Commodity",
}


def classify_asset_class(info: dict) -> str:
    """Classify an asset using Yahoo quoteType first, then safe fallbacks."""
    info = info or {}

    quote_type = str(info.get("quoteType", "")).strip().upper()
    mapped = QUOTE_TYPE_TO_ASSET_CLASS.get(quote_type)
    if mapped:
        return mapped

    symbol = str(info.get("symbol", "")).strip().upper()

    if symbol.startswith("^"):
        return "Index"

    if symbol.endswith("=X"):
        return "Forex"

    if symbol.endswith("=F"):
        return "Commodity"

    if symbol.endswith("-USD") or symbol.endswith("-GBP") or symbol.endswith("-EUR"):
        return "Crypto"

    if info.get("fundFamily") or info.get("category"):
        return "ETF"

    if (
        info.get("sector")
        or info.get("industry")
        or info.get("marketCap") is not None
        or info.get("enterpriseValue") is not None
    ):
        return "Stock"

    return "Other"
    

def get_extended_metrics(info: dict) -> dict:
    """Extract growth, profitability, financial position, and valuation figures
    from the yfinance info dict. Returns raw numeric values (None if unavailable);
    formatting is handled separately by the format_* helpers.

    Note: yfinance reports debtToEquity as a percentage-point figure (e.g. 79.5),
    not a raw ratio, so it is divided by 100 here to give a true multiple (0.795).
    """
    debt_to_equity = info.get("debtToEquity")
    return {
        "revenue_growth": info.get("revenueGrowth"),
        "net_profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "return_on_equity": info.get("returnOnEquity"),
        "free_cash_flow": info.get("freeCashflow"),
        "total_debt": info.get("totalDebt"),
        "debt_to_equity": (debt_to_equity / 100) if debt_to_equity is not None else None,
        "forward_pe": info.get("forwardPE"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
    }
