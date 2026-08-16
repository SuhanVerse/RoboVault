"""Pydantic schemas for loans."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.loan import LoanStatus


class LoanRequest(BaseModel):
    """Payload for POST /loans/request."""

    item_id: int
    quantity: int = Field(..., ge=1)
    due_date: date | None = None


class LoanRead(BaseModel):
    """Loan as returned by the API."""

    id: int
    item_id: int
    borrower_id: int
    quantity: int
    status: LoanStatus
    requested_at: datetime
    due_date: date | None
    returned_at: datetime | None
    approved_by: int | None

    model_config = ConfigDict(from_attributes=True)
