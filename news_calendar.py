"""News & economic-event context: a real structured economic calendar plus
real company news, mapped to the currently-viewed asset by explainable
rules. No AI, no invented headlines, no sentiment scoring — every fact here
traces back to a real API/feed response.

ECONOMIC CALENDAR — sourced from https://nfs.faireconomy.media, the same
structured JSON feed that powers most of the free "Forex Factory calendar"
widgets found across the web. It mirrors Forex Factory's calendar data
(event name, country/currency, impact tier, scheduled time, forecast,
previous) as plain JSON rather than an HTML page — a legitimate structured
source, not a scraper, and free with no API key. If the feed is ever
unreachable, get_economic_calendar() returns an explicit unavailable flag
rather than silently returning an empty list that looks like "no events."

COMPANY NEWS / EARNINGS — sourced from yfinance's own Ticker.news and
Ticker.calendar, the same free data source (and dependency) the rest of
EquityLens already uses. No separate API, no new paid service.

EVENT RELEVANCE — a fixed, explainable rule table (see _relevant_currencies
and RELEVANCE_NOTES below): every asset maps to one or two currency codes
(FX pairs to both legs, indices/equities/commodities/crypto to the currency
they're priced or headquartered in), and only High-impact events for those
currencies are surfaced. This never overrides a Technical Rating or a
Market Structure read — see views/market_research.py, which displays event
risk as separate context, never as a signal.
"""

import logging
import re
from datetime import datetime, timezone

import requests
import streamlit as st
import yfinance as yf

from data_fetcher import _with_retries

logger = logging.getLogger("equitylens.news_calendar")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CALENDAR_TIMEOUT_SECONDS = 8

# Ticker pattern -> currency this asset is most exposed to. Order matters —
# first match wins. Kept as a simple, auditable table rather than a model:
# every mapping here is something a person could read and agree/disagree
# with, which is the point (Part 17 — "sensible explainable rules").
INDEX_CURRENCY = {
    "^GSPC": "USD", "^IXIC": "USD", "^DJI": "USD",
    "^FTSE": "GBP", "^GDAXI": "EUR", "^N225": "JPY",
}
ETF_CURRENCY = {"SPY": "USD", "QQQ": "USD", "DIA": "USD", "IWM": "USD", "ISF.L": "GBP"}
COMMODITY_CURRENCY = {"GC=F": "USD", "SI=F": "USD", "CL=F": "USD", "PL=F": "USD", "HG=F": "USD", "NG=F": "USD"}

FX_PATTERN = re.compile(r"^([A-Z]{3})([A-Z]{3})=X$")


def _relevant_currencies(ticker: str, asset_class: str) -> set:
    """Which currency codes' events matter for this asset. FX pairs get
    both legs; everything else gets the single currency it's priced or
    domiciled in. UK-listed instruments (.L suffix) get GBP; anything else
    defaults to USD, since most of EquityLens's non-FX universe (US
    equities, commodities priced in USD, USD-denominated crypto) is
    genuinely USD-exposed — an explicit, if broad, rule rather than a
    guess."""
    ticker = ticker.upper()

    fx_match = FX_PATTERN.match(ticker)
    if fx_match:
        return {fx_match.group(1), fx_match.group(2)}

    if ticker in INDEX_CURRENCY:
        return {INDEX_CURRENCY[ticker]}
    if ticker in ETF_CURRENCY:
        return {ETF_CURRENCY[ticker]}
    if ticker in COMMODITY_CURRENCY:
        return {COMMODITY_CURRENCY[ticker]}
    if ticker.endswith(".L"):
        return {"GBP"}
    if asset_class == "Crypto" or ticker.endswith("-USD"):
        return {"USD"}
    return {"USD"}


def _relevance_note(ticker: str, currencies: set) -> str:
    if FX_PATTERN.match(ticker.upper()):
        return f"Directly affects {ticker.upper().replace('=X', '')} — both currencies in the pair."
    if ticker.upper().endswith("-USD") or ticker.upper() in COMMODITY_CURRENCY:
        return "USD-denominated — major USD events can move price via the dollar."
    if ticker.upper() in INDEX_CURRENCY or ticker.upper() in ETF_CURRENCY or ticker.upper().endswith(".L"):
        return f"{', '.join(sorted(currencies))} macro events can move broad market risk sentiment for this index/market."
    return f"{', '.join(sorted(currencies))} macro events can affect broad risk sentiment for this asset."


@st.cache_data(ttl=1800, show_spinner=False)
def get_economic_calendar() -> dict:
    """Fetch this week's economic calendar. Returns
    {"available": bool, "events": [...], "fetched_at": iso str}. Never
    raises — a fetch failure is reported as available=False so the UI can
    say so honestly, rather than an empty events list that would read as
    "nothing scheduled this week," which is a materially different (and
    false) claim.
    """
    def _fetch():
        response = requests.get(CALENDAR_URL, timeout=CALENDAR_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    try:
        raw_events = _with_retries("get_economic_calendar()", _fetch)
    except Exception as exc:
        logger.error("Economic calendar unavailable: %s: %s", type(exc).__name__, exc)
        return {"available": False, "events": [], "fetched_at": None}

    events = []
    for item in raw_events:
        try:
            event_time = datetime.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue
        events.append({
            "title": item.get("title", "Untitled event"),
            "currency": item.get("country", ""),
            "impact": item.get("impact", "Low"),
            "time": event_time,
            "forecast": item.get("forecast") or None,
            "previous": item.get("previous") or None,
        })
    events.sort(key=lambda e: e["time"])
    return {"available": True, "events": events, "fetched_at": datetime.now(timezone.utc).isoformat()}


def get_relevant_events(ticker: str, asset_class: str, impact_levels=("High",), max_events: int = 6) -> dict:
    """Upcoming (not-yet-occurred) events relevant to `ticker`, filtered to
    the given impact tiers (High only by default — Part 17: "prioritise
    high-impact events"). Returns
    {"available": bool, "events": [{..., "time_until": str, "relevance": str}], ...}.
    """
    calendar = get_economic_calendar()
    if not calendar["available"]:
        return {"available": False, "events": []}

    currencies = _relevant_currencies(ticker, asset_class)
    note = _relevance_note(ticker, currencies)
    now = datetime.now(timezone.utc)

    upcoming = [
        e for e in calendar["events"]
        if e["currency"] in currencies and e["impact"] in impact_levels and e["time"] > now
    ]
    upcoming = upcoming[:max_events]

    result = []
    for e in upcoming:
        result.append({**e, "time_until": _format_time_until(e["time"], now), "relevance": note})
    return {"available": True, "events": result}


def _format_time_until(event_time: datetime, now: datetime) -> str:
    delta = event_time - now
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 60:
        return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"
    total_hours = total_minutes // 60
    if total_hours < 48:
        return f"{total_hours} hour{'s' if total_hours != 1 else ''}"
    total_days = total_hours // 24
    return f"{total_days} day{'s' if total_days != 1 else ''}"


@st.cache_data(ttl=1800, show_spinner=False)
def get_company_news(ticker: str, limit: int = 5) -> list:
    """Recent real headlines for an equity via yfinance's Ticker.news.
    Returns [] for asset classes without article-style news (forex,
    commodities, most indices) or if the fetch fails — never fabricated.
    Each item: {title, publisher, published, url}.
    """
    try:
        raw = yf.Ticker(ticker).news
    except Exception as exc:
        logger.warning("get_company_news(%s) failed: %s: %s", ticker, type(exc).__name__, exc)
        return []

    articles = []
    for item in raw or []:
        content = item.get("content", item)  # newer yfinance nests fields under "content"
        title = content.get("title")
        if not title:
            continue
        published = content.get("pubDate") or content.get("displayTime")
        provider = (content.get("provider") or {}).get("displayName", "Unknown source")
        url = (content.get("canonicalUrl") or content.get("clickThroughUrl") or {}).get("url")
        articles.append({"title": title, "publisher": provider, "published": published, "url": url})
        if len(articles) >= limit:
            break
    return articles


@st.cache_data(ttl=1800, show_spinner=False)
def get_earnings_info(ticker: str) -> dict:
    """Next scheduled earnings date and consensus EPS estimate, straight
    from yfinance's Ticker.calendar. Returns {} if unavailable (non-equity
    asset classes, or Yahoo has nothing scheduled)."""
    try:
        calendar = yf.Ticker(ticker).calendar
    except Exception as exc:
        logger.warning("get_earnings_info(%s) failed: %s: %s", ticker, type(exc).__name__, exc)
        return {}

    if not calendar or "Earnings Date" not in calendar:
        return {}
    dates = calendar["Earnings Date"]
    next_date = dates[0] if isinstance(dates, list) and dates else dates
    return {
        "next_date": next_date,
        "eps_estimate": calendar.get("Earnings Average"),
        "revenue_estimate": calendar.get("Revenue Average"),
    }
