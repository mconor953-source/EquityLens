"""Local, file-backed storage for user watchlists.

Two named watchlists live in data/watchlists.json, created with sensible
defaults on first run. This is genuinely persisted state, not
st.session_state that resets on refresh — a "workspace" page should
remember what you put in it across restarts.

No Streamlit dependency here on purpose: this is plain file I/O,
independently testable, same "no UI here" separation as scoring.py and
idea_engine.py.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STORE_PATH = DATA_DIR / "watchlists.json"

DEFAULT_WATCHLISTS = {
    "Long-Term Investing": ["AAPL", "MSFT", "GOOGL", "JNJ", "KO"],
    "Momentum Watchlist": ["TSLA", "NVDA", "AMD"],
}


def load_watchlists() -> dict:
    """Return the saved watchlists, creating the file with defaults on first run."""
    if not STORE_PATH.exists():
        save_watchlists(DEFAULT_WATCHLISTS)
        return {name: list(tickers) for name, tickers in DEFAULT_WATCHLISTS.items()}

    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_watchlists(watchlists: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(watchlists, f, indent=2)


def add_ticker(watchlist_name: str, ticker: str) -> dict:
    """Add a ticker to a watchlist (normalized, deduplicated) and persist."""
    watchlists = load_watchlists()
    ticker = ticker.strip().upper()
    tickers = watchlists.setdefault(watchlist_name, [])
    if ticker and ticker not in tickers:
        tickers.append(ticker)
        save_watchlists(watchlists)
    return watchlists


def remove_ticker(watchlist_name: str, ticker: str) -> dict:
    """Remove a ticker from a watchlist and persist."""
    watchlists = load_watchlists()
    tickers = watchlists.get(watchlist_name, [])
    if ticker in tickers:
        tickers.remove(ticker)
        save_watchlists(watchlists)
    return watchlists
