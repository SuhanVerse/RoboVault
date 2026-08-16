"""Loan routes — thin handlers that delegate to the lending service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser
from app.db.session import get_db
from app.models.loan import Loan
from app.schemas.loan import LoanRead, LoanRequest
from app.services.lending import (
    ConflictError,
    NotFoundError,
    approve_loan,
    flag_overdue,
    reject_loan,
    request_loan,
    return_loan,
)

router = APIRouter(prefix="/api/v1/loans", tags=["loans"])


def _get_loan_or_404(loan_id: int, db: Annotated[Session, Depends(get_db)]) -> Loan:
    """Fetch a loan by id — flagging overdue first so status is always fresh."""
    flag_overdue(db)
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.post("/request", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def create_loan_request(
    payload: LoanRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> Loan:
    """Request to borrow an item (any authenticated user)."""
    try:
        return request_loan(
            db, payload.item_id, current_user, payload.quantity, payload.due_date
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{loan_id}/approve", response_model=LoanRead)
def approve_loan_request(
    loan: Annotated[Loan, Depends(_get_loan_or_404)],
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Loan:
    """Approve a request (ADMIN only) — stock goes down, or auto-reject if too low."""
    try:
        return approve_loan(db, loan, admin)
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{loan_id}/reject", response_model=LoanRead)
def reject_loan_request(
    loan: Annotated[Loan, Depends(_get_loan_or_404)],
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Loan:
    """Reject a request (ADMIN only): REQUESTED → REJECTED."""
    try:
        return reject_loan(db, loan)
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{loan_id}/return", response_model=LoanRead)
def return_loan_request(
    loan: Annotated[Loan, Depends(_get_loan_or_404)],
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Loan:
    """Return an approved loan (ADMIN only) — stock comes back."""
    try:
        return return_loan(db, loan)
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
