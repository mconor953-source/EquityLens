"""Local, file-backed storage for user preferences (Settings page).

Same "no UI here" separation and file-backed persistence pattern as
watchlist_store.py — preferences survive across restarts, not just
st.session_state (which resets when the browser tab closes).
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STORE_PATH = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "default_asset_class": "Stocks",
    "default_asset": "Apple (AAPL)",
    "default_period_label": "1Y",
}


def load_settings() -> dict:
    """Return saved preferences, creating the file with defaults on first
    run. Missing keys (e.g. after an app update adds a new preference) fall
    back to DEFAULT_SETTINGS rather than raising a KeyError."""
    if not STORE_PATH.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    with open(STORE_PATH, "r", encoding="utf-8") as f:
        saved = json.load(f)

    settings = dict(DEFAULT_SETTINGS)
    settings.update(saved)
    return settings


def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
