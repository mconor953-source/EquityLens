"""Research orchestration: composes data_fetcher.py, technicals.py,
scoring.py, and news_calendar.py into the same "Research Summary" content
views/market_research.py already displays, as one reusable payload the
FastAPI backend can call. No UI, no new calculations — every figure here
is produced by a function that already existed; this module only calls
them in the same order the Streamlit page does and returns the result as
one dict instead of rendering it.

Pure functions and orchestration only — no Streamlit import, same "no UI
here" separation as scoring.py/technicals.py/idea_engine.py.
"""

from data_fetcher import (
    get_price_history,
    get_ticker_info,
    is_valid_ticker,
    classify_asset_class,
    get_extended_metrics,
    get_analyst_consensus,
)
from scoring import calculate_financial_health
from technicals import (
    compute_technical_rating,
    fifty_two_week_range,
    annualized_volatility,
    volume_ratio,
)
from news_calendar import get_relevant_events, get_earnings_info
from cache_utils import ttl_cache
EQUITY_CLASSES = ("US Stocks", "UK Stocks", "Stock")


def event_risk_summary(relevant_events: dict) -> dict:
    """{"available", "label" ("HIGH"/"None scheduled"), "events"} from
    news_calendar.get_relevant_events()'s result — the same Event Risk read
    Market Research and Market Structure both show, extracted here so
    there's exactly one place that decides what "HIGH" means."""
    events = relevant_events["events"] if relevant_events["available"] else []
    return {
        "available": relevant_events["available"],
        "label": "HIGH" if events else "None scheduled",
        "events": events,
    }


def build_research_summary_sentence(technical: dict, health: dict, high_impact_events: list) -> str:
    """The same one-sentence recap Market Research's Research Summary panel
    shows — a factual, deterministic composition of whichever of the three
    lenses (technical / financial health / event risk) are available. Every
    clause quotes an already-computed figure; nothing is generated."""
    parts = []
    if technical:
        parts.append(f"Technical indicators are currently reading {technical['rating'].upper()}")
    else:
        parts.append("Technical indicators can't be read yet (insufficient price history)")
    if health:
        parts.append(f"financial health is {health['rating'].lower()} at {health['total_score']}/100")
    if high_impact_events:
        soonest = high_impact_events[0]
        parts.append(
            f"a high-impact {soonest['currency']} event ({soonest['title']}) is scheduled in "
            f"{soonest['time_until']}, which may increase near-term volatility"
        )
    sentence = ", and ".join(parts) if len(parts) <= 2 else ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return sentence[0].upper() + sentence[1:] + "."


@ttl_cache(1800)
def build_research_payload(ticker: str, period: str = "1y") -> dict:
    """Full Research payload for one ticker — technical rating, price
    statistics, equity fundamentals + Financial Health Score (when the
    ticker is an equity), analyst consensus, event risk, and the same
    summary sentence Market Research shows. Every figure comes from the
    same functions views/market_research.py calls; this is the same
    computation, packaged for an API response instead of a page render.

    Raises ValueError if there's no price data for the ticker.
    """
    history = get_price_history(ticker, period=period)
    if history is None or history.empty or "Close" not in history.columns:
        raise ValueError(f"No price data for '{ticker}'.")

    current_price = history["Close"].iloc[-1]
    previous_close = history["Close"].iloc[-2] if len(history) > 1 else None
    pct_change = ((current_price - previous_close) / previous_close * 100) if previous_close else None

    info = get_ticker_info(ticker)
    resolved_asset_class = classify_asset_class(info)
    is_equity = resolved_asset_class in EQUITY_CLASSES and is_valid_ticker(info)

    technical = compute_technical_rating(history)

    health = None
    fundamentals = None
    consensus = None
    if is_equity:
        metrics = get_extended_metrics(info)
        health = calculate_financial_health(info, metrics)
        fundamentals = {
            "name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange"),
            "market_cap": info.get("marketCap"),
            "revenue_ttm": info.get("totalRevenue"),
            "net_income_ttm": info.get("netIncomeToCommon"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "metrics": metrics,
        }
        consensus = get_analyst_consensus(info)

    relevant_events = get_relevant_events(ticker, resolved_asset_class)
    event_risk = event_risk_summary(relevant_events)

    range_52w = fifty_two_week_range(history)
    volatility = annualized_volatility(history["Close"])
    vol_ratio = volume_ratio(history)

    earnings = get_earnings_info(ticker) if is_equity else {}

    summary_sentence = build_research_summary_sentence(technical, health, event_risk["events"])

    return {
        "symbol": ticker,
        "name": (info.get("longName") or info.get("shortName") or ticker) if info else ticker,
        "asset_class": resolved_asset_class,
        "price": current_price,
        "daily_change_pct": pct_change,
        "data_status": "delayed",
        "price_statistics": {
            "52w_high": range_52w["high"] if range_52w else None,
            "52w_low": range_52w["low"] if range_52w else None,
            "annualized_volatility": volatility,
            "volume_ratio": vol_ratio["ratio"] if vol_ratio else None,
        },
        "technical": technical,
        "financial_health": health,
        "fundamentals": fundamentals,
        "analyst_consensus": consensus,
        "event_risk": event_risk,
        "earnings": earnings or None,
        "summary": summary_sentence,
    }
