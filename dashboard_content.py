"""Sample/illustrative content for the Dashboard's editorial sections.

Everything in this file is placeholder content — there is no news feed,
economic calendar API, or AI model behind it yet. It exists so the Dashboard
can demonstrate its intended layout and information hierarchy today, and so
a future AI/news/calendar integration has an obvious, single place to plug
in: replace the functions below with real data sources and nothing in
views/dashboard.py needs to change, since it only consumes this shape.

Every section built from this data is labeled "Sample data" in the UI —
never presented as live analysis.
"""


def get_market_brief() -> dict:
    """A sample morning market brief, structured the way a real one would be:
    a headline, a short narrative (what happened / why / macro context), and
    a set of scannable watch items (central bank, earnings, data)."""
    return {
        "headline": "Markets consolidate near recent highs as investors weigh the rate outlook",
        "summary": [
            "Global equities traded in a narrow range, with major indices holding close to "
            "recent highs as investors digested a mixed batch of economic data. Technology "
            "shares outperformed, while defensive sectors lagged the broader market.",
            "Treasury yields firmed after data reinforced expectations that the Federal Reserve "
            "will hold rates steady at its next meeting. The dollar strengthened against most "
            "major currencies, weighing on gold and other dollar-denominated assets.",
            "In commodities, oil eased on demand concerns, while Bitcoin remained range-bound "
            "as investors await clearer macro catalysts.",
        ],
        "watch_items": [
            {
                "label": "Central Bank Watch",
                "detail": "A Federal Reserve rate decision is due this week — markets are "
                "pricing in a high probability of no change.",
            },
            {
                "label": "Earnings Focus",
                "detail": "Several large-cap technology names report this week, with "
                "AI-related capital expenditure guidance in focus.",
            },
            {
                "label": "Data Watch",
                "detail": "The US jobs report and ISM manufacturing data, both due later "
                "this week, could shift rate-cut expectations.",
            },
        ],
    }


def get_todays_watchlist() -> list:
    """Sample list of assets/events approaching a notable technical or macro
    trigger — the kind of thing a trader would want flagged at a glance."""
    return [
        {"asset": "Gold", "note": "Approaching key resistance near recent highs"},
        {"asset": "GBP/JPY", "note": "Testing an important support zone"},
        {"asset": "NVIDIA", "note": "Earnings due later this week"},
        {"asset": "Federal Reserve", "note": "Policy meeting scheduled this week"},
    ]


def get_economic_calendar() -> list:
    """Sample upcoming high-impact macro events."""
    return [
        {"event": "Federal Reserve Interest Rate Decision", "when": "This week", "impact": "High"},
        {"event": "US Non-Farm Payrolls", "when": "Friday", "impact": "High"},
        {"event": "Eurozone Flash CPI", "when": "This week", "impact": "Medium"},
        {"event": "ISM Manufacturing PMI", "when": "This week", "impact": "Medium"},
    ]
