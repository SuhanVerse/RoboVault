"""Smoke tests: the application boots and the health endpoint responds."""


def test_health_check_returns_ok(client) -> None:
    """The /health endpoint reports that the API is up."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
