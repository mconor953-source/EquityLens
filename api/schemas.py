"""Request body models for the endpoints that accept one (POST/PUT).

Field set mirrors ideas_store.IDEA_FIELDS exactly — this is a thin
validation layer in front of that store, not a new data model.
"""

from typing import Optional

from pydantic import BaseModel

from ideas_store import IDEA_FIELDS


class WatchlistAddRequest(BaseModel):
    watchlist_name: str
    ticker: str


class IdeaCreateRequest(BaseModel):
    asset_class: str
    ticker: str
    title: Optional[str] = None
    stance: str
    horizon: str
    conviction: int
    status: str = "Watching"
    entry_date: Optional[str] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    invalidation_price: Optional[float] = None
    thesis: Optional[str] = None
    drivers: Optional[str] = None
    risks: Optional[str] = None
    strengthen: Optional[str] = None
    weaken: Optional[str] = None
    notes: Optional[str] = None

    def to_fields(self) -> dict:
        data = self.model_dump()
        return {field: data.get(field) for field in IDEA_FIELDS}


class IdeaUpdateRequest(BaseModel):
    asset_class: Optional[str] = None
    ticker: Optional[str] = None
    title: Optional[str] = None
    stance: Optional[str] = None
    horizon: Optional[str] = None
    conviction: Optional[int] = None
    status: Optional[str] = None
    entry_date: Optional[str] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    invalidation_price: Optional[float] = None
    thesis: Optional[str] = None
    drivers: Optional[str] = None
    risks: Optional[str] = None
    strengthen: Optional[str] = None
    weaken: Optional[str] = None
    notes: Optional[str] = None
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    closing_notes: Optional[str] = None

    def to_updates(self) -> dict:
        return self.model_dump(exclude_unset=True)
