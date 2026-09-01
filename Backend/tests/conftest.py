"""
Shared test fixtures.

Tests run against a real Postgres database (set TEST_DATABASE_URL, or they
fall back to DATABASE_URL with a `_test` suffix) — Phase 1 uses Postgres-
specific features (ON CONFLICT, etc.) that SQLite can't emulate, so a real
Postgres instance is what these tests are written against, matching what
Docker Compose provides in dev/CI.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401 - registers models on Base.metadata


def _test_db_url() -> str:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    base_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://flyvora:flyvora_dev_password@localhost:5432/flyvora")
    return base_url.rsplit("/", 1)[0] + "/flyvora_test"


TEST_DATABASE_URL = _test_db_url()
engine = create_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate everything between tests so each test starts from empty."""
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE fare_observations, ingestion_jobs, data_sources, routes, airlines, airports "
            "RESTART IDENTITY CASCADE"
        ))
    yield


@pytest.fixture
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
