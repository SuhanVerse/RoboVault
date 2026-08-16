"""Lending business rules — the heart of RoboVault.

Routes never touch the database directly; they call these functions.
"""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.loan import Loan, LoanStatus
from app.models.user import User


class NotFoundError(Exception):
    """Raised when a requested record does not exist."""


class ConflictError(Exception):
    """Raised when a business rule forbids the operation."""


def request_loan(
    db: Session, item_id: int, borrower: User, quantity: int, due_date: date | None
) -> Loan:
    """Create a REQUESTED loan for an item with enough stock."""
    item = db.get(Item, item_id)
    if item is None:
        raise NotFoundError("Item not found")
    if item.quantity_available < quantity:
        raise ConflictError("Not enough items available")
    loan = Loan(
        item_id=item_id,
        borrower_id=borrower.id,
        quantity=quantity,
        status=LoanStatus.REQUESTED,
        due_date=due_date,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def approve_loan(db: Session, loan: Loan, approver: User) -> Loan:
    """Approve a REQUESTED loan, or reject it if stock ran out (never below zero)."""
    if loan.status is not LoanStatus.REQUESTED:
        raise ConflictError("Only requested loans can be approved")
    if loan.item.quantity_available < loan.quantity:
        loan.status = LoanStatus.REJECTED  # rule: never go below zero
        db.commit()
        raise ConflictError("Not enough stock to approve this loan")
    loan.status = LoanStatus.APPROVED
    loan.approved_by = approver.id
    loan.item.quantity_available -= loan.quantity  # stock goes down
    db.commit()
    db.refresh(loan)
    return loan


def reject_loan(db: Session, loan: Loan) -> Loan:
    """Reject a REQUESTED loan."""
    if loan.status is not LoanStatus.REQUESTED:
        raise ConflictError("Only requested loans can be rejected")
    loan.status = LoanStatus.REJECTED
    db.commit()
    db.refresh(loan)
    return loan


def return_loan(db: Session, loan: Loan) -> Loan:
    """Return an APPROVED/OVERDUE loan and restore the stock."""
    if loan.status not in (LoanStatus.APPROVED, LoanStatus.OVERDUE):
        raise ConflictError("Only approved loans can be returned")
    loan.status = LoanStatus.RETURNED
    loan.returned_at = datetime.now(UTC)
    loan.item.quantity_available += loan.quantity  # stock comes back
    db.commit()
    db.refresh(loan)
    return loan


def flag_overdue(db: Session) -> int:
    """Flip every approved loan past its due date to OVERDUE. Returns the count."""
    today = datetime.now(UTC).date()
    overdue = db.scalars(
        select(Loan).where(
            Loan.status == LoanStatus.APPROVED,
            Loan.due_date.is_not(None),
            Loan.due_date < today,
        )
    ).all()
    for loan in overdue:
        loan.status = LoanStatus.OVERDUE
    db.commit()
    return len(overdue)
