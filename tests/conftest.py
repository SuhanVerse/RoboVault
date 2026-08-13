"""Shared pytest fixtures: isolated Postgres test database and API client.

The test database defaults to the configured DATABASE_URL with a ``_test``
suffix (e.g. ``robovault`` -> ``robovault_test``). Override with the
``TEST_DATABASE_URL`` env var when needed (e.g. in CI).
"""

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command

# --- Point the app at the test database before any app module is imported. ---
# Settings and the engine in app.db.session are built at import time, so the
# env var must be set first.

_TEST_SUFFIX = "_test"


def _test_database_url() -> str:
    """Same server as the configured URL, database name suffixed with _test."""
    configured = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://robovault:robovault@localhost:5433/robovault",
    )
    parts = urlsplit(configured)
    db_name = parts.path.lstrip("/")
    if not db_name.endswith(_TEST_SUFFIX):
        db_name += _TEST_SUFFIX
    return urlunsplit(parts._replace(path=f"/{db_name}"))


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _test_database_url()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient

import app.models
from app.db.base import Base
from app.db.session import engine
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _create_test_database() -> None:
    """Create the test database if it does not exist yet."""
    parts = urlsplit(TEST_DATABASE_URL)
    db_name = parts.path.lstrip("/")
    admin_engine = create_engine(
        urlunsplit(parts._replace(path="/postgres")), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    """Ensure the test DB exists and its schema is up to date (once per run)."""
    _create_test_database()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def _clean_database(_prepare_database: None) -> None:
    """Start every test with empty tables (RESTART IDENTITY keeps ids stable)."""
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if not tables:
        return
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def client() -> TestClient:
    """TestClient wired to the test database via the app's real dependencies."""
    return TestClient(app)
