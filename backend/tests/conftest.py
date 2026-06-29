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
os.environ["EXTERNAL_RATE_LIMIT_PER_SEC"] = "0"  # no throttling in tests

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


class FakeAhrefs:
    """Deterministic Ahrefs client for tests — no network/MCP."""

    enabled = True

    def __init__(self, dr=55):
        self.dr = dr

    def backlinks_stats(self, target: str) -> dict:
        # Competitors get a slightly stronger profile to produce a delta.
        boost = 0 if "acme" in target else 10
        return {
            "domain_rating": self.dr + boost,
            "referring_domains": 120 + boost,
            "backlinks": 5000 + boost * 100,
            "dofollow_ratio": 0.7,
        }

    def organic_keywords(self, target: str, limit: int = 1000) -> list[dict]:
        base = [
            {"keyword": "how to optimize seo", "volume": 1200, "position": 4,
             "traffic": 300, "url": f"{target}/guide", "difficulty": 30,
             "serp_features": ["people_also_ask", "featured_snippet"]},
            {"keyword": "best seo tools", "volume": 800, "position": 8,
             "traffic": 120, "url": f"{target}/tools", "difficulty": 40,
             "serp_features": ["paa"]},
            {"keyword": "seo pricing", "volume": 500, "position": 2,
             "traffic": 250, "url": f"{target}/pricing", "difficulty": 25,
             "serp_features": []},
        ]
        if "acme" not in target:
            base.append(
                {"keyword": "enterprise seo platform", "volume": 600, "position": 5,
                 "traffic": 90, "url": f"{target}/platform", "difficulty": 50,
                 "serp_features": ["featured_snippet"]}
            )
        return base

    def referring_domains(self, target: str, limit: int = 100) -> list[dict]:
        return []

    def anchors(self, target: str, limit: int = 50) -> list[dict]:
        return []

    def best_by_internal_links(self, target: str, limit: int = 100) -> list[dict]:
        return []


@pytest.fixture
def fake_ahrefs() -> FakeAhrefs:
    return FakeAhrefs()


from app.services.geo.providers import GeoResponse  # noqa: E402


class FakeGeoProvider:
    """Deterministic GEO provider for tests — no network."""

    def __init__(self, name="chatgpt", source_kind="api", text="Acme is a leading option.",
                 domains=("acme.com", "rival.com")):
        self.name = name
        self.source_kind = source_kind
        self.text = text
        self.domains = list(domains)

    @property
    def enabled(self) -> bool:
        return True

    def query(self, prompt: str) -> GeoResponse:
        return GeoResponse(
            provider=self.name, source_kind=self.source_kind, ok=True,
            text=self.text, citations=[], domains=self.domains,
        )


def fake_geo_providers():
    return [
        FakeGeoProvider("chatgpt", "api"),
        FakeGeoProvider("ai_overview", "serp", text="See acme.com for details.",
                        domains=["acme.com"]),
    ]


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
