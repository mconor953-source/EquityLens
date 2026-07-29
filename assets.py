"""Predefined tradable assets, grouped by class.

Shared between views/market_research.py (full selector) and
views/dashboard.py (Global Markets / Major Assets sections pull tickers
directly from here) so ticker symbols are defined in exactly one place.
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

# Dashboard "Global Markets" section — major world indices.
GLOBAL_MARKETS = [
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
    ("Dow Jones", "^DJI"),
    ("FTSE 100", "^FTSE"),
    ("DAX", "^GDAXI"),
    ("Nikkei 225", "^N225"),
]

# Dashboard "Major Assets" section — commodities, crypto, and FX majors.
MAJOR_ASSETS = [
    ("Gold", "GC=F"),
    ("Silver", "SI=F"),
    ("Oil (WTI)", "CL=F"),
    ("Bitcoin", "BTC-USD"),
    ("Ethereum", "ETH-USD"),
    ("EUR/USD", "EURUSD=X"),
    ("GBP/USD", "GBPUSD=X"),
    ("USD/JPY", "USDJPY=X"),
]
