"""Local, file-backed storage for the Trade Studio notes field.

Same file-backed JSON pattern as watchlist_store.py and settings_store.py —
notes survive across restarts, not just st.session_state (which resets
when the browser tab closes).

No Streamlit dependency here on purpose: this is plain file I/O,
independently testable, same "no UI here" separation as scoring.py and
trade_calculator.py.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STORE_PATH = DATA_DIR / "trade_notes.json"


def load_trade_notes() -> str:
    """Return the saved notes text, or "" if nothing has been saved yet."""
    if not STORE_PATH.exists():
        return ""

    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("notes", "")


def save_trade_notes(notes: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump({"notes": notes}, f, indent=2)
