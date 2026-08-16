"""Role-based access control tests for the protected endpoints.

The items routes require an authenticated user for reads and an ADMIN for
writes (Steps 15-16). These tests create real users directly in the test
database (the conftest truncates tables before every test) and mint JWT
tokens for them.
"""

from sqlalchemy.orm import Session

from app.core import security
from app.db.session import SessionLocal
from app.models.user import User, UserRole

ITEMS_URL = "/api/v1/items"


def _create_user(role: UserRole, email: str) -> dict[str, str]:
    """Create a user with the given role and return an auth header for them."""
    db: Session = SessionLocal()
    try:
        user = User(
            name=email.split("@")[0].capitalize(),
            email=email,
            password_hash=security.hash_password("password123"),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = security.create_access_token(str(user.id))
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def test_protected_route_without_token(client) -> None:
    """Listing items without a token returns 401."""
    response = client.get(ITEMS_URL)
    assert response.status_code == 401


def test_write_route_without_token(client) -> None:
    """Creating an item without a token returns 401."""
    response = client.post(ITEMS_URL, data={"name": "Widget"})
    assert response.status_code == 401


def test_member_can_list_items(client) -> None:
    """Any authenticated user (here: MEMBER) can read inventory."""
    headers = _create_user(UserRole.MEMBER, "member@club.edu")
    response = client.get(ITEMS_URL, headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_admin_only_route_with_member_role(client) -> None:
    """A MEMBER token on an ADMIN-only write returns 403."""
    headers = _create_user(UserRole.MEMBER, "member@club.edu")
    response = client.post(ITEMS_URL, data={"name": "Widget"}, headers=headers)
    assert response.status_code == 403
