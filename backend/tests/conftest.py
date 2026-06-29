"""Test fixtures: isolated in-memory-ish SQLite DB + FastAPI TestClient."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest

# Configure env BEFORE importing the app so settings pick a throwaway DB + key.
_tmp_db = os.path.join(tempfile.gettempdir(), "eclerx_test.db")
_tmp_html = os.path.join(tempfile.gettempdir(), "eclerx_test_html")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["SECRET_KEY"] = "test-secret-key-deterministic"
os.environ["RAW_HTML_DIR"] = _tmp_html
os.environ["INGEST_INLINE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ingest.fetcher import FetchResult  # noqa: E402


class FakeFetcher:
    """Deterministic fetcher for tests — no network, no firecrawl/playwright."""

    def __init__(self, html_by_url: dict[str, str] | None = None, default_html: str | None = None):
        self.html_by_url = html_by_url or {}
        self.default_html = default_html
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        html = self.html_by_url.get(url, self.default_html)
        if html is None:
            html = (
                f"<html lang='en'><head><title>{url}</title>"
                "<meta name='description' content='sample page'>"
                "<meta name='viewport' content='width=device-width'>"
                f"<link rel='canonical' href='{url}'></head>"
                "<body><h1>Heading</h1><p>" + ("word " * 60) + "</p>"
                "<a href='/about'>about</a></body></html>"
            )
        return FetchResult(url=url, method="fake", success=True, status_code=200, html=html)


@pytest.fixture
def fake_fetcher() -> FakeFetcher:
    return FakeFetcher()


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
