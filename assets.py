"""Predefined tradable assets, grouped by class.

Shared between views/market_research.py (full selector) and
views/dashboard.py (Markets Today strip pulls a handful of these directly)
so ticker symbols are defined in exactly one place.
"""

PREDEFINED_ASSETS = {
    "Stocks": {
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "Alphabet (GOOGL)": "GOOGL",
        "Amazon (AMZN)": "AMZN",
        "NVIDIA (NVDA)": "NVDA",
        "Tesla (TSLA)": "TSLA",
    },
    "Crypto": {
        "Bitcoin (BTC-USD)": "BTC-USD",
        "Ethereum (ETH-USD)": "ETH-USD",
        "Solana (SOL-USD)": "SOL-USD",
        "XRP (XRP-USD)": "XRP-USD",
        "Dogecoin (DOGE-USD)": "DOGE-USD",
    },
    "Forex": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "USDJPY=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CHF": "USDCHF=X",
    },
    "Metals": {
        "Gold (Futures)": "GC=F",
        "Silver (Futures)": "SI=F",
        "Platinum (Futures)": "PL=F",
        "Copper (Futures)": "HG=F",
    },
    "Indices": {
        "S&P 500": "^GSPC",
        "Dow Jones Industrial Average": "^DJI",
        "Nasdaq Composite": "^IXIC",
        "FTSE 100": "^FTSE",
        "Nikkei 225": "^N225",
    },
}

# Curated picks for the Dashboard's "Markets Today" strip — one representative
# asset per class, referencing the same dict above (no duplicated tickers).
MARKETS_TODAY = [
    ("S&P 500", PREDEFINED_ASSETS["Indices"]["S&P 500"]),
    ("Nasdaq Composite", PREDEFINED_ASSETS["Indices"]["Nasdaq Composite"]),
    ("Dow Jones", PREDEFINED_ASSETS["Indices"]["Dow Jones Industrial Average"]),
    ("Bitcoin", PREDEFINED_ASSETS["Crypto"]["Bitcoin (BTC-USD)"]),
    ("Gold", PREDEFINED_ASSETS["Metals"]["Gold (Futures)"]),
    ("EUR/USD", PREDEFINED_ASSETS["Forex"]["EUR/USD"]),
]
