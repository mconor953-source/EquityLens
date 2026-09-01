"""FastAPI backend for EquityLens — exposes the exact same engine
(data_fetcher.py, technicals.py, scoring.py, structure_engine.py,
idea_engine.py, research_service.py, news_calendar.py, and the *_store.py
files) that views/*.py already renders, over HTTP, for a future
React/Next.js frontend.

No calculations happen in this file. Every endpoint calls an existing
engine function (or the small orchestration wrappers in research_service.py
and structure_engine.build_structure_payload/phase_status) and reshapes the
result into a JSON-safe response via api.serialization.json_safe. Run with:
    python -m uvicorn api.main:app --reload --port 8000
from the repository root (see README / final report for both run commands).
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how uvicorn is invoked (bare
# `uvicorn api.main:app` does not add the CWD to sys.path the way
# `python -m uvicorn ...` does) — data_fetcher.py, scoring.py, etc. all
# live one directory up from this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from yfinance.exceptions import YFTickerMissingError, YFPricesMissingError

from api.schemas import IdeaCreateRequest, IdeaUpdateRequest, WatchlistAddRequest
from api.serialization import json_safe

from data_fetcher import (
    get_price_history,
    get_ticker_info,
    is_valid_ticker,
    classify_asset_class,
    get_extended_metrics,
    get_current_price_and_change,
)
from scoring import calculate_financial_health
from technicals import compute_technical_rating
from structure_engine import build_structure_payload
from news_calendar import get_relevant_events, get_company_news, get_earnings_info
from research_service import build_research_payload
from watchlist_store import load_watchlists, add_ticker, remove_ticker
from ideas_store import load_ideas, add_idea, update_idea, delete_idea, get_idea

EQUITY_CLASSES = ("US Stocks", "UK Stocks", "Stock")

app = FastAPI(title="EquityLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://id-preview--4aa6bb48-0623-4daa-bd99-25fdeb167b42.lovable.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Last-resort safety net — an endpoint should already have translated
    a known failure (invalid ticker, unreachable data source) into a 404 or
    502 below. Anything that still reaches here is unexpected, but the API
    still returns structured JSON instead of crashing or leaking a raw
    traceback."""
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})


def api_response(data, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=json_safe(data), status_code=status_code)


def _shape_technical(technical: dict | None) -> dict | None:
    if technical is None:
        return None
    return {
        "signal": technical["rating"],
        "buy_count": technical["buy_count"],
        "neutral_count": technical["neutral_count"],
        "sell_count": technical["sell_count"],
        "total_signals": technical["total_signals"],
        "rsi": technical.get("rsi"),
        "indicators": technical["signals"],
    }


def _shape_financial_health(health: dict | None) -> dict | None:
    if health is None:
        return None
    return {
        "score": health["total_score"],
        "classification": health["rating"],
        "categories": health["categories"],
        "strengths": health["strengths"],
        "weaknesses": health["weaknesses"],
    }


def _resolve_asset_class(ticker: str) -> str:
    return classify_asset_class(get_ticker_info(ticker))


def _map_fetch_error(ticker: str, exc: Exception) -> HTTPException:
    """Map a data-fetch failure to the right HTTP status: a genuinely
    invalid/delisted ticker is a 404 (the resource doesn't exist); anything
    else (rate limit, timeout, Yahoo outage) is a 502 (the upstream data
    source failed) — mirrors data_fetcher._is_permanent_failure's own
    permanent/transient distinction."""
    if isinstance(exc, (YFTickerMissingError, YFPricesMissingError)):
        return HTTPException(status_code=404, detail=f"'{ticker}' is not a valid ticker.")
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    if status_code == 404:
        return HTTPException(status_code=404, detail=f"'{ticker}' is not a valid ticker.")
    return HTTPException(status_code=502, detail=f"Failed to fetch data for '{ticker}': {exc}")


# =====================================================================
# Health
# =====================================================================
@app.get("/api/health")
def health():
    return api_response({"status": "ok"})


# =====================================================================
# Asset / Research / Technical / Fundamentals / Market Structure / Events
# =====================================================================
@app.get("/api/asset/{ticker}")
def get_asset(ticker: str):
    ticker = ticker.strip().upper()
    try:
        research = build_research_payload(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise _map_fetch_error(ticker, exc)

    try:
        structure = build_structure_payload(ticker)
        market_structure = {
            "status": structure["structure_status"],
            "direction": structure["direction"],
            "quality": structure["quality"],
        }
    except Exception:
        market_structure = None

    payload = {
        "symbol": research["symbol"],
        "name": research["name"],
        "asset_class": research["asset_class"],
        "price": research["price"],
        "daily_change_pct": research["daily_change_pct"],
        "data_status": research["data_status"],
        "technical": _shape_technical(research["technical"]),
        "financial_health": _shape_financial_health(research["financial_health"]),
        "event_risk": research["event_risk"],
        "market_structure": market_structure,
    }
    return api_response(payload)


@app.get("/api/research/{ticker}")
def get_research(ticker: str):
    ticker = ticker.strip().upper()
    try:
        research = build_research_payload(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise _map_fetch_error(ticker, exc)
    return api_response(research)


@app.get("/api/technical/{ticker}")
def get_technical(ticker: str):
    ticker = ticker.strip().upper()
    try:
        history = get_price_history(ticker, period="1y")
    except Exception as exc:
        raise _map_fetch_error(ticker, exc)

    if history is None or history.empty or "Close" not in history.columns:
        raise HTTPException(status_code=404, detail=f"No price data for '{ticker}'.")

    technical = compute_technical_rating(history)
    if technical is None:
        raise HTTPException(
            status_code=404,
            detail=f"Not enough price history to compute technical signals for '{ticker}'.",
        )

    return api_response({"symbol": ticker, "technical": _shape_technical(technical)})


@app.get("/api/fundamentals/{ticker}")
def get_fundamentals(ticker: str):
    ticker = ticker.strip().upper()
    info = get_ticker_info(ticker)
    resolved_asset_class = classify_asset_class(info)

    if resolved_asset_class not in EQUITY_CLASSES or not is_valid_ticker(info):
        raise HTTPException(
            status_code=404,
            detail=f"No equity fundamentals available for '{ticker}' (asset class: {resolved_asset_class}).",
        )

    metrics = get_extended_metrics(info)
    health = calculate_financial_health(info, metrics)

    payload = {
        "symbol": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "exchange": info.get("exchange"),
        "market_cap": info.get("marketCap"),
        "revenue_ttm": info.get("totalRevenue"),
        "net_income_ttm": info.get("netIncomeToCommon"),
        "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
        "metrics": metrics,
        "financial_health": _shape_financial_health(health),
    }
    return api_response(payload)


@app.get("/api/market-structure/{ticker}")
def get_market_structure(ticker: str):
    ticker = ticker.strip().upper()
    try:
        payload = build_structure_payload(ticker)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to build market structure for '{ticker}': {exc}")
    return api_response(payload)


@app.get("/api/events/{ticker}")
def get_events(ticker: str, asset_class: str = Query(default=None)):
    ticker = ticker.strip().upper()
    resolved_asset_class = asset_class or _resolve_asset_class(ticker)

    economic = get_relevant_events(ticker, resolved_asset_class)
    news = get_company_news(ticker)
    earnings = get_earnings_info(ticker)

    return api_response({
        "symbol": ticker,
        "asset_class": resolved_asset_class,
        "economic_events": economic,
        "company_news": news,
        "earnings": earnings or None,
    })


# =====================================================================
# Watchlist — same data/watchlists.json Streamlit's Watchlists page uses
# =====================================================================
@app.get("/api/watchlist")
def get_watchlist():
    return api_response(load_watchlists())


@app.post("/api/watchlist")
def post_watchlist(body: WatchlistAddRequest):
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required.")

    price, _ = get_current_price_and_change(ticker)
    if price is None:
        raise HTTPException(status_code=404, detail=f"No data found for '{ticker}'.")

    watchlists = add_ticker(body.watchlist_name, ticker)
    return api_response(watchlists)


@app.delete("/api/watchlist/{ticker}")
def delete_watchlist_ticker(ticker: str, watchlist_name: str = Query(...)):
    ticker = ticker.strip().upper()
    watchlists = remove_ticker(watchlist_name, ticker)
    return api_response(watchlists)


# =====================================================================
# Investment Ideas — same data/investment_ideas.json Streamlit's
# Investment Ideas page uses
# =====================================================================
@app.get("/api/investment-ideas")
def get_investment_ideas():
    return api_response(load_ideas())


@app.post("/api/investment-ideas")
def post_investment_idea(body: IdeaCreateRequest):
    fields = body.to_fields()
    fields["ticker"] = (fields.get("ticker") or "").strip().upper()
    if not fields["ticker"]:
        raise HTTPException(status_code=400, detail="ticker is required.")

    idea_id = add_idea(fields)
    return api_response(get_idea(idea_id), status_code=201)


@app.put("/api/investment-ideas/{idea_id}")
def put_investment_idea(idea_id: str, body: IdeaUpdateRequest):
    updates = body.to_updates()
    if not update_idea(idea_id, updates):
        raise HTTPException(status_code=404, detail=f"Investment idea '{idea_id}' not found.")
    return api_response(get_idea(idea_id))


@app.delete("/api/investment-ideas/{idea_id}")
def delete_investment_idea(idea_id: str):
    if not delete_idea(idea_id):
        raise HTTPException(status_code=404, detail=f"Investment idea '{idea_id}' not found.")
    return api_response({"deleted": idea_id})
