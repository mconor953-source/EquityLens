"""Curated asset universe, grouped by class.

This is a *starting point* for browsing, not the limit of what EquityLens
can look up — components.asset_picker also accepts any free-typed Yahoo
Finance ticker (validated live against real data, "Asset not found" if it
isn't one), so the real asset universe is "whatever Yahoo Finance covers,"
not just what's listed here. This file exists so a new user has something
to click through — Market Research, Market Structure, and Dashboard all
import from here so ticker symbols stay defined in exactly one place.
"""

PREDEFINED_ASSETS = {
    "US Stocks": {
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "NVIDIA (NVDA)": "NVDA",
        "Meta Platforms (META)": "META",
        "Amazon (AMZN)": "AMZN",
        "Alphabet (GOOGL)": "GOOGL",
        "JPMorgan Chase (JPM)": "JPM",
        "Goldman Sachs (GS)": "GS",
        "Morgan Stanley (MS)": "MS",
        "Bank of America (BAC)": "BAC",
        "Tesla (TSLA)": "TSLA",
        "AMD (AMD)": "AMD",
        "Netflix (NFLX)": "NFLX",
        "Coca-Cola (KO)": "KO",
        "Walt Disney (DIS)": "DIS",
    },
    "UK Stocks": {
        "Lloyds Banking Group (LLOY.L)": "LLOY.L",
        "Barclays (BARC.L)": "BARC.L",
        "BP (BP.L)": "BP.L",
        "Shell (SHEL.L)": "SHEL.L",
        "HSBC (HSBA.L)": "HSBA.L",
        "AstraZeneca (AZN.L)": "AZN.L",
        "Unilever (ULVR.L)": "ULVR.L",
    },
    "ETFs": {
        "S&P 500 (SPY)": "SPY",
        "Nasdaq 100 (QQQ)": "QQQ",
        "Dow Jones (DIA)": "DIA",
        "Russell 2000 (IWM)": "IWM",
        "FTSE 100 (ISF.L)": "ISF.L",
    },
    "Indices": {
        "S&P 500": "^GSPC",
        "Nasdaq Composite": "^IXIC",
        "Dow Jones Industrial Average": "^DJI",
        "FTSE 100": "^FTSE",
        "DAX": "^GDAXI",
        "Nikkei 225": "^N225",
    },
    "Commodities": {
        "Gold (Futures)": "GC=F",
        "Silver (Futures)": "SI=F",
        "Oil — WTI (Futures)": "CL=F",
        "Platinum (Futures)": "PL=F",
        "Copper (Futures)": "HG=F",
        "Natural Gas (Futures)": "NG=F",
    },
    "Forex": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "GBP/JPY": "GBPJPY=X",
        "USD/JPY": "USDJPY=X",
        "EUR/JPY": "EURJPY=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CAD": "USDCAD=X",
        "USD/CHF": "USDCHF=X",
    },
    "Crypto": {
        "Bitcoin (BTC-USD)": "BTC-USD",
        "Ethereum (ETH-USD)": "ETH-USD",
        "Solana (SOL-USD)": "SOL-USD",
        "XRP (XRP-USD)": "XRP-USD",
        "Dogecoin (DOGE-USD)": "DOGE-USD",
    },
}

# Cross-class quick-select shown first in the asset picker ("Popular"),
# pulled from the curated lists above rather than duplicated.
POPULAR_ASSETS = [
    ("Apple (AAPL)", "AAPL", "US Stocks"),
    ("NVIDIA (NVDA)", "NVDA", "US Stocks"),
    ("Microsoft (MSFT)", "MSFT", "US Stocks"),
    ("S&P 500", "^GSPC", "Indices"),
    ("Nasdaq Composite", "^IXIC", "Indices"),
    ("Gold (Futures)", "GC=F", "Commodities"),
    ("EUR/USD", "EURUSD=X", "Forex"),
    ("GBP/USD", "GBPUSD=X", "Forex"),
    ("GBP/JPY", "GBPJPY=X", "Forex"),
    ("Bitcoin (BTC-USD)", "BTC-USD", "Crypto"),
]

# Dashboard "Market Snapshot" — major world indices.
GLOBAL_MARKETS = [
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
    ("Dow Jones", "^DJI"),
    ("FTSE 100", "^FTSE"),
    ("DAX", "^GDAXI"),
    ("Nikkei 225", "^N225"),
]

# Dashboard "Market Snapshot" — commodities, crypto, and FX majors.
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

# Market Structure is intraday-driven (4H/1H/15m/5m) and most useful on
# liquid, always-trading instruments — this is the default "Watch" universe
# for Dashboard's Market Structure Watch section, not a restriction on what
# Market Structure itself can analyze (any ticker with intraday history
# works there).
STRUCTURE_WATCH_DEFAULT = [
    ("Gold", "GC=F"),
    ("GBP/JPY", "GBPJPY=X"),
    ("EUR/USD", "EURUSD=X"),
    ("NASDAQ", "^IXIC"),
    ("S&P 500", "^GSPC"),
    ("Bitcoin", "BTC-USD"),
]
