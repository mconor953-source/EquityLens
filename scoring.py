"""Financial Health Score — rule-based, fully deterministic. No AI/ML.

The score is out of 100, split evenly across five categories worth 20
points each: Growth, Profitability, Balance Sheet, Cash Flow, Valuation.
Every rule below is a plain threshold comparison against metrics already
computed by data_fetcher.py. To retune the score, edit the *_BANDS tuples
in this file — nothing elsewhere needs to change.

Each category's rating bands are ordered best-to-worst as
(minimum_value, points, phrase_template) — the first band whose minimum
the value clears wins. If a metric is unavailable, the category is given
a neutral default score instead of being penalised or rewarded.
"""

CATEGORY_MAX = 20
NEUTRAL_DEFAULT = CATEGORY_MAX / 2  # 10/20 — awarded when data is missing

STRENGTH_RATIO = 0.75  # category scoring >= 75% of its points -> strength
WEAKNESS_RATIO = 0.40  # category scoring <= 40% of its points -> weakness

RATING_BANDS = (
    (80, "Excellent"),
    (60, "Good"),
    (40, "Average"),
    (0, "Weak"),
)

NEG_INF = float("-inf")

GROWTH_BANDS = (
    (0.15, 20, "Revenue grew {value:.1%} year-over-year — strong growth momentum."),
    (0.08, 15, "Revenue grew {value:.1%} year-over-year — solid, steady growth."),
    (0.00, 10, "Revenue grew {value:.1%} year-over-year — modest growth."),
    (NEG_INF, 3, "Revenue declined {value:.1%} year-over-year — a growth concern."),
)

MARGIN_BANDS = (
    (0.20, 20, "excellent at {value:.1%}"),
    (0.10, 15, "healthy at {value:.1%}"),
    (0.00, 8, "thin at {value:.1%}"),
    (NEG_INF, 2, "negative at {value:.1%} (unprofitable)"),
)

ROE_BANDS = (
    (0.20, 20, "excellent at {value:.1%}"),
    (0.10, 15, "solid at {value:.1%}"),
    (0.00, 8, "weak at {value:.1%}"),
    (NEG_INF, 2, "negative at {value:.1%} (eroding shareholder value)"),
)

# Debt-to-equity is a "lower is better" metric, so bands are evaluated as
# value <= threshold rather than value >= threshold (see _rate_lower_is_better).
DEBT_TO_EQUITY_BANDS = (
    (0.3, 20, "very low at {value:.2f}x — a conservative, low-risk balance sheet."),
    (0.7, 16, "manageable at {value:.2f}x."),
    (1.5, 10, "moderate-to-high at {value:.2f}x — some leverage risk."),
    (3.0, 5, "high at {value:.2f}x — elevated financial risk."),
    (float("inf"), 2, "very high at {value:.2f}x — significant leverage risk."),
)

FCF_MARGIN_BANDS = (
    (0.20, 20, "excellent at {value:.1%} of revenue converted to free cash."),
    (0.10, 15, "strong at {value:.1%} of revenue converted to free cash."),
    (0.00, 8, "modest at {value:.1%} of revenue converted to free cash."),
    (NEG_INF, 2, "negative at {value:.1%} — the company is burning cash."),
)

# "Lower is better" — evaluated as value <= threshold.
FORWARD_PE_BANDS = (
    (15, 20, "attractive at {value:.1f}x forward earnings."),
    (25, 15, "reasonable at {value:.1f}x forward earnings."),
    (40, 8, "rich at {value:.1f}x forward earnings."),
    (float("inf"), 3, "very expensive at {value:.1f}x forward earnings."),
)

# "Lower is better" — evaluated as value <= threshold.
PRICE_TO_SALES_BANDS = (
    (2, 20, "attractive at {value:.1f}x sales."),
    (5, 15, "reasonable at {value:.1f}x sales."),
    (10, 8, "rich at {value:.1f}x sales."),
    (float("inf"), 3, "very expensive at {value:.1f}x sales."),
)


def _rate_higher_is_better(value, bands):
    """First band whose minimum the value clears (scanning best to worst)."""
    if value is None:
        return None, None
    for minimum, points, phrase in bands:
        if value >= minimum:
            return points, phrase.format(value=value)
    return None, None


def _rate_lower_is_better(value, bands):
    """First band whose maximum the value stays under (scanning best to worst)."""
    if value is None:
        return None, None
    for maximum, points, phrase in bands:
        if value <= maximum:
            return points, phrase.format(value=value)
    return None, None


def _tag(points):
    ratio = points / CATEGORY_MAX
    if ratio >= STRENGTH_RATIO:
        return "strength"
    if ratio <= WEAKNESS_RATIO:
        return "weakness"
    return "neutral"


def _category(name, points, detail):
    if points is None:
        points = NEUTRAL_DEFAULT
        detail = f"{detail} Data unavailable — scored neutral."
        tag = "neutral"
    else:
        tag = _tag(points)
    return {"name": name, "score": round(points, 1), "max_score": CATEGORY_MAX, "detail": detail, "tag": tag}


def _score_growth(metrics):
    points, phrase = _rate_higher_is_better(metrics.get("revenue_growth"), GROWTH_BANDS)
    return _category("Growth", points, phrase or "Revenue growth")


def _score_profitability(metrics):
    net_points, net_phrase = _rate_higher_is_better(metrics.get("net_profit_margin"), MARGIN_BANDS)
    op_points, op_phrase = _rate_higher_is_better(metrics.get("operating_margin"), MARGIN_BANDS)
    roe_points, roe_phrase = _rate_higher_is_better(metrics.get("return_on_equity"), ROE_BANDS)

    available = [p for p in (net_points, op_points, roe_points) if p is not None]
    points = sum(available) / len(available) if available else None

    parts = []
    parts.append(f"net margin {net_phrase}" if net_phrase else "net margin n/a")
    parts.append(f"operating margin {op_phrase}" if op_phrase else "operating margin n/a")
    parts.append(f"return on equity {roe_phrase}" if roe_phrase else "return on equity n/a")
    detail = "Profitability is " + ", ".join(parts) + "."

    return _category("Profitability", points, detail)


def _score_balance_sheet(metrics):
    points, phrase = _rate_lower_is_better(metrics.get("debt_to_equity"), DEBT_TO_EQUITY_BANDS)
    detail = f"Debt-to-equity is {phrase}" if phrase else "Debt-to-equity"
    return _category("Balance Sheet", points, detail)


def _score_cash_flow(info, metrics):
    fcf = metrics.get("free_cash_flow")
    revenue = info.get("totalRevenue")
    fcf_margin = fcf / revenue if fcf is not None and revenue else None

    points, phrase = _rate_higher_is_better(fcf_margin, FCF_MARGIN_BANDS)
    detail = f"Free cash flow generation is {phrase}" if phrase else "Free cash flow"
    return _category("Cash Flow", points, detail)


def _score_valuation(metrics):
    pe = metrics.get("forward_pe")
    ps = metrics.get("price_to_sales")
    # A non-positive forward P/E means negative expected earnings, which is
    # already penalised under Profitability — treat as unavailable here
    # rather than double-counting it as "cheap".
    if pe is not None and pe <= 0:
        pe = None

    pe_points, pe_phrase = _rate_lower_is_better(pe, FORWARD_PE_BANDS)
    ps_points, ps_phrase = _rate_lower_is_better(ps, PRICE_TO_SALES_BANDS)

    available = [p for p in (pe_points, ps_points) if p is not None]
    points = sum(available) / len(available) if available else None

    parts = []
    parts.append(f"forward P/E is {pe_phrase}" if pe_phrase else "forward P/E is n/a")
    parts.append(f"price-to-sales is {ps_phrase}" if ps_phrase else "price-to-sales is n/a")
    detail = "Valuation: " + " ".join(parts) + " Lower valuation multiples score higher here."

    return _category("Valuation", points, detail)


def _rating_for_score(total_score):
    for minimum, label in RATING_BANDS:
        if total_score >= minimum:
            return label
    return RATING_BANDS[-1][1]


def calculate_financial_health(info: dict, metrics: dict) -> dict:
    """Compute the Financial Health Score for a company.

    `info` is the raw yfinance info dict (used only for totalRevenue, to
    compute the FCF margin). `metrics` is the dict returned by
    data_fetcher.get_extended_metrics(info). No network calls happen here.
    """
    categories = [
        _score_growth(metrics),
        _score_profitability(metrics),
        _score_balance_sheet(metrics),
        _score_cash_flow(info, metrics),
        _score_valuation(metrics),
    ]

    total_score = round(sum(c["score"] for c in categories))
    rating = _rating_for_score(total_score)

    strengths = [c["detail"] for c in categories if c["tag"] == "strength"]
    weaknesses = [c["detail"] for c in categories if c["tag"] == "weakness"]

    return {
        "total_score": total_score,
        "rating": rating,
        "categories": categories,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }
