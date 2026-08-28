"""Local, file-backed storage for the user's manual Investment Ideas register.

Same file-backed JSON pattern as watchlist_store.py and settings_store.py —
ideas survive across restarts, not just st.session_state. Every idea here
is a manual decision the user typed in (stance, conviction, thesis, ...);
nothing in this module computes or infers any of that — see idea_engine.py
for the separate, automated Conviction Score used elsewhere in the app.

No Streamlit dependency here on purpose: this is plain file I/O,
independently testable, same "no UI here" separation as scoring.py and
idea_engine.py.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STORE_PATH = DATA_DIR / "investment_ideas.json"

IDEA_FIELDS = (
    "asset_class", "ticker", "title", "stance", "horizon", "conviction", "status",
    "entry_date", "entry_price", "target_price", "invalidation_price",
    "thesis", "drivers", "risks", "strengthen", "weaken", "notes",
    "exit_date", "exit_price", "closing_notes",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_ideas() -> list:
    """Return all saved ideas, creating an empty store on first run."""
    if not STORE_PATH.exists():
        save_ideas([])
        return []

    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_ideas(ideas: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(ideas, f, indent=2)


def get_idea(idea_id: str) -> dict | None:
    for idea in load_ideas():
        if idea["id"] == idea_id:
            return idea
    return None


def add_idea(fields: dict) -> str:
    """Create a new idea from a dict of IDEA_FIELDS values, stamp it with a
    fresh id and created/updated timestamps, persist it, and return its id."""
    ideas = load_ideas()
    idea_id = uuid.uuid4().hex
    now = _now()
    idea = {"id": idea_id, "created_at": now, "updated_at": now}
    for field in IDEA_FIELDS:
        idea[field] = fields.get(field)
    ideas.append(idea)
    save_ideas(ideas)
    return idea_id


def update_idea(idea_id: str, updates: dict) -> bool:
    """Apply `updates` (any subset of IDEA_FIELDS) to an existing idea and
    bump its updated_at timestamp. Returns False if the id doesn't exist."""
    ideas = load_ideas()
    for idea in ideas:
        if idea["id"] == idea_id:
            for field in IDEA_FIELDS:
                if field in updates:
                    idea[field] = updates[field]
            idea["updated_at"] = _now()
            save_ideas(ideas)
            return True
    return False


def delete_idea(idea_id: str) -> bool:
    ideas = load_ideas()
    remaining = [i for i in ideas if i["id"] != idea_id]
    if len(remaining) == len(ideas):
        return False
    save_ideas(remaining)
    return True
