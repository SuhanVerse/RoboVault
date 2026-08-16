"""Lending business-rule tests — the mandatory evidence for the report."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.loan import Loan, LoanStatus
from app.models.user import User
from app.services.lending import flag_overdue


def test_cannot_borrow_item_with_zero_available(
    client: TestClient,
    db: Session,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """The single most important rule: no borrowing when quantity_available == 0."""
    item = Item(name="ESP32-CAM", quantity_total=0, quantity_available=0)
    db.add(item)
    db.commit()

    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 409
    assert "available" in response.json()["detail"].lower()


def test_stock_integrity_across_the_lending_cycle(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Create 3, lend 2 → 1 left; return the loan → 3 left (fully restored)."""
    item = Item(name="Sensor Kit", quantity_total=3, quantity_available=3)
    db.add(item)
    db.commit()

    # a member requests 2 units
    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 2},
        headers=auth_header(member_user),
    )
    assert response.status_code == 201
    loan_id = response.json()["id"]

    # admin approves → stock drops 3 → 1
    response = client.put(
        f"/api/v1/loans/{loan_id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["status"] == LoanStatus.APPROVED.value
    db.refresh(item)
    assert item.quantity_available == 1

    # admin registers the return → the loan's 2 units come back: 1 → 3
    response = client.put(
        f"/api/v1/loans/{loan_id}/return",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["status"] == LoanStatus.RETURNED.value
    db.refresh(item)
    assert item.quantity_available == 3


def test_request_loan_for_missing_item_returns_404(
    client: TestClient,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Requesting a loan for an item that does not exist returns 404."""
    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": 999999, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}


def test_approve_missing_loan_returns_404(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Approving a loan that does not exist returns 404."""
    response = client.put(
        "/api/v1/loans/999999/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Loan not found"}


def test_member_cannot_approve_loan(
    client: TestClient,
    db: Session,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """A MEMBER token on the ADMIN-only approve route returns 403."""
    item = Item(name="Drone Kit", quantity_total=2, quantity_available=2)
    db.add(item)
    db.commit()

    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 201
    loan_id = response.json()["id"]

    response = client.put(
        f"/api/v1/loans/{loan_id}/approve",
        headers=auth_header(member_user),
    )
    assert response.status_code == 403


def test_approving_twice_returns_409(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Approving an already-approved loan is a conflict (409)."""
    item = Item(name="Robot Arm", quantity_total=2, quantity_available=2)
    db.add(item)
    db.commit()

    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 201
    loan_id = response.json()["id"]

    response = client.put(
        f"/api/v1/loans/{loan_id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200

    response = client.put(
        f"/api/v1/loans/{loan_id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Only requested loans can be approved"}


def test_flag_overdue_marks_past_due_approved_loans(
    db: Session, member_user: User
) -> None:
    """flag_overdue flips APPROVED loans past their due date to OVERDUE."""
    item = Item(name="Rover", quantity_total=2, quantity_available=2)
    db.add(item)
    db.commit()

    past_due = Loan(
        item_id=item.id,
        borrower_id=member_user.id,
        quantity=1,
        status=LoanStatus.APPROVED,
        due_date=datetime.now(UTC).date() - timedelta(days=1),
    )
    on_time = Loan(
        item_id=item.id,
        borrower_id=member_user.id,
        quantity=1,
        status=LoanStatus.APPROVED,
        due_date=datetime.now(UTC).date() + timedelta(days=7),
    )
    db.add_all([past_due, on_time])
    db.commit()

    changed = flag_overdue(db)
    assert changed == 1
    db.refresh(past_due)
    db.refresh(on_time)
    assert past_due.status == LoanStatus.OVERDUE
    assert on_time.status == LoanStatus.APPROVED


def test_approve_route_flags_overdue_before_reading(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """The approve route flags overdue loans first, so a past-due APPROVED loan
    becomes OVERDUE before the business rule rejects re-approval."""
    item = Item(name="Older Rover", quantity_total=1, quantity_available=1)
    db.add(item)
    db.commit()

    past_due = Loan(
        item_id=item.id,
        borrower_id=member_user.id,
        quantity=1,
        status=LoanStatus.APPROVED,
        due_date=datetime.now(UTC).date() - timedelta(days=1),
    )
    db.add(past_due)
    db.commit()

    response = client.put(
        f"/api/v1/loans/{past_due.id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 409
    db.refresh(past_due)
    assert past_due.status == LoanStatus.OVERDUE


def test_reject_requested_loan(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Rejecting a REQUESTED loan returns 200 and flips it to REJECTED."""
    item = Item(name="GPS Shield", quantity_total=1, quantity_available=1)
    db.add(item)
    db.commit()

    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 201
    loan_id = response.json()["id"]

    response = client.put(
        f"/api/v1/loans/{loan_id}/reject",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["status"] == LoanStatus.REJECTED.value


def test_reject_approved_loan_returns_409(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Only REQUESTED loans can be rejected."""
    item = Item(name="Motor Shield", quantity_total=2, quantity_available=2)
    db.add(item)
    db.commit()

    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 201
    loan_id = response.json()["id"]
    response = client.put(
        f"/api/v1/loans/{loan_id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200

    response = client.put(
        f"/api/v1/loans/{loan_id}/reject",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Only requested loans can be rejected"}


def test_return_requested_loan_returns_409(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Only APPROVED/OVERDUE loans can be returned."""
    item = Item(name="Battery Pack", quantity_total=1, quantity_available=1)
    db.add(item)
    db.commit()

    response = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 1},
        headers=auth_header(member_user),
    )
    assert response.status_code == 201
    loan_id = response.json()["id"]

    response = client.put(
        f"/api/v1/loans/{loan_id}/return",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Only approved loans can be returned"}


def test_approve_with_insufficient_stock_auto_rejects(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Approving when stock ran out rejects the loan and never goes below zero."""
    item = Item(name="Robot Arm", quantity_total=2, quantity_available=2)
    db.add(item)
    db.commit()

    first = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 2},
        headers=auth_header(member_user),
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post(
        "/api/v1/loans/request",
        json={"item_id": item.id, "quantity": 2},
        headers=auth_header(member_user),
    )
    assert second.status_code == 201
    second_id = second.json()["id"]

    # first approval takes all the stock: 2 → 0
    response = client.put(
        f"/api/v1/loans/{first_id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200

    # second approval finds no stock → auto-rejected with a conflict
    response = client.put(
        f"/api/v1/loans/{second_id}/approve",
        headers=auth_header(admin_user),
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Not enough stock to approve this loan"}

    second_loan = db.get(Loan, second_id)
    assert second_loan is not None
    assert second_loan.status == LoanStatus.REJECTED
    db.refresh(second_loan.item)  # the session's identity map is stale here
    assert second_loan.item.quantity_available == 0  # never below zero
