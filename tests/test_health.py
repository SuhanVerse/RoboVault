"""Smoke tests: the application boots and the health endpoint responds."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    """The /health endpoint reports that the API is up."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
