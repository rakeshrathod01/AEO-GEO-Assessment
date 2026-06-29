"""Test fixtures: isolated in-memory-ish SQLite DB + FastAPI TestClient."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest

# Configure env BEFORE importing the app so settings pick a throwaway DB + key.
_tmp_db = os.path.join(tempfile.gettempdir(), "eclerx_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["SECRET_KEY"] = "test-secret-key-deterministic"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
