"""Pydantic schemas for items — one model per operation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.item import ItemSource


class ItemCreate(BaseModel):
    """Payload for POST /items — quantity_available is NOT settable here."""

    name: str = Field(..., min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    quantity_total: int = Field(default=0, ge=0)
    condition: str | None = Field(default=None, max_length=100)
    unit_price: float | None = None
    source: ItemSource = ItemSource.MANUAL


class ItemUpdate(BaseModel):
    """All fields optional for PUT /items/{id}."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = None
    description: str | None = None
    quantity_total: int | None = Field(default=None, ge=0)
    condition: str | None = None
    unit_price: float | None = None
    source: ItemSource | None = None


class ItemRead(BaseModel):
    """Item as returned by the API."""

    id: int
    name: str
    category: str | None
    description: str | None
    quantity_total: int
    quantity_available: int
    condition: str | None
    photo_url: str | None
    unit_price: float | None
    source: ItemSource
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
