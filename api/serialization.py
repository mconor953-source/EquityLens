"""JSON-safe conversion for API responses.

The core engine (data_fetcher.py, technicals.py, structure_engine.py, ...)
works natively with pandas/numpy — Timestamps, numpy scalar types, NaN,
Infinity, DataFrames. None of that is valid JSON. `json_safe()` walks any
value returned by the engine and converts it into plain Python types a
frontend can actually consume, without changing any of the numbers
themselves.
"""

import math
from datetime import date, datetime

import numpy as np
import pandas as pd


def json_safe(value):
    """Recursively convert `value` into something json.dumps (and
    FastAPI's JSONResponse) can serialize directly."""
    if value is None:
        return None

    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value

    if isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        as_float = float(value)
        return None if (math.isnan(as_float) or math.isinf(as_float)) else as_float

    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]

    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()

    if isinstance(value, pd.Timedelta):
        return None if pd.isna(value) else value.isoformat()

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, pd.DataFrame):
        records = value.reset_index().to_dict(orient="records")
        return [json_safe(record) for record in records]

    if isinstance(value, pd.Series):
        return [json_safe(item) for item in value.tolist()]

    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    # pandas NA / NaT and anything else pandas considers "missing"
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value
