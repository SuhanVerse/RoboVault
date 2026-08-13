"""Tests for the auth endpoints and the security helpers."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core import security
from app.core.config import settings

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def _register(client, email: str = "ada@example.com") -> None:
    """Helper: register the default test user."""
    response = client.post(
        REGISTER_URL,
        json={"name": "Ada", "email": email, "password": "hunter22"},
    )
    assert response.status_code == 201


def test_register_creates_guest_user(client) -> None:
    """POST /auth/register returns 201 with the new user, never the hash."""
    response = client.post(
        REGISTER_URL,
        json={"name": "Ada", "email": "ada@example.com", "password": "hunter22"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada"
    assert body["email"] == "ada@example.com"
    assert body["role"] == "GUEST"
    assert body["id"] > 0
    assert "created_at" in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(client) -> None:
    """Registering the same email twice returns 409."""
    _register(client)
    response = client.post(
        REGISTER_URL,
        json={"name": "Ada", "email": "ada@example.com", "password": "hunter22"},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


def test_login_returns_working_bearer_token(client) -> None:
    """Login with valid credentials returns a JWT that decodes to the user id."""
    _register(client)
    response = client.post(
        LOGIN_URL, json={"email": "ada@example.com", "password": "hunter22"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert security.decode_access_token(body["access_token"]) is not None


def test_login_rejects_wrong_password(client) -> None:
    """A wrong password for a real account returns 401."""
    _register(client)
    response = client.post(
        LOGIN_URL, json={"email": "ada@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login_rejects_unknown_email(client) -> None:
    """An email that was never registered returns 401."""
    response = client.post(
        LOGIN_URL, json={"email": "ghost@example.com", "password": "hunter22"}
    )
    assert response.status_code == 401


def test_hash_and_verify_password() -> None:
    """Passwords hash to a different string and verify correctly."""
    hashed = security.hash_password("hunter22")
    assert hashed != "hunter22"
    assert security.verify_password("hunter22", hashed)
    assert not security.verify_password("wrong-password", hashed)


def test_access_token_round_trip() -> None:
    """create_access_token stores the subject; decode returns it."""
    token = security.create_access_token("42")
    assert security.decode_access_token(token) == "42"


def test_decode_rejects_invalid_token() -> None:
    """Garbage input decodes to None instead of raising."""
    assert security.decode_access_token("not-a-jwt") is None


def test_decode_rejects_expired_token() -> None:
    """An expired token decodes to None instead of raising."""
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert security.decode_access_token(expired) is None
