"""Page fetching: Firecrawl primary, Playwright-stealth fallback.

The fetch backends are dependency-injected behind a small protocol so the
pipeline is fully testable without network or the heavy firecrawl/playwright
packages (which are imported lazily inside the concrete fetchers).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings

# Markers that indicate a bot challenge / interstitial rather than real content.
_CHALLENGE_MARKERS = re.compile(
    r"(just a moment|checking your browser|attention required|cf-browser-verification|"
    r"captcha|are you a human|enable javascript|please wait while we verify)",
    re.IGNORECASE,
)
_BLOCK_STATUSES = {401, 403, 429, 503}


@dataclass
class FetchResult:
    url: str
    method: str  # firecrawl | playwright | fake
    success: bool
    status_code: int | None = None
    html: str = ""
    text: str | None = None  # provider-supplied text/markdown, if any
    error: str | None = None


class Fetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


def needs_fallback(result: FetchResult, min_chars: int | None = None) -> bool:
    """Decide whether a Firecrawl result warrants the Playwright-stealth fallback.

    Triggers: failure, a block/challenge HTTP status, challenge markers in the
    HTML, or near-empty rendered content (JS-heavy page Firecrawl couldn't render).
    """
    min_chars = settings.MIN_CONTENT_CHARS if min_chars is None else min_chars
    if not result.success:
        return True
    if result.status_code in _BLOCK_STATUSES:
        return True
    body = (result.text or result.html or "")
    if _CHALLENGE_MARKERS.search(body):
        return True
    # Strip tags cheaply to gauge visible text length.
    visible = re.sub(r"<[^>]+>", " ", result.html or "")
    visible_len = len((result.text or visible).strip())
    if visible_len < min_chars:
        return True
    return False


class FirecrawlFetcher:
    """Primary fetcher using Firecrawl. Key is the tenant's BYO Firecrawl key."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self, url: str) -> FetchResult:
        try:
            from firecrawl import FirecrawlApp  # lazy import

            app = FirecrawlApp(api_key=self.api_key)
            resp = app.scrape_url(url, params={"formats": ["html", "markdown"]})
            data = resp.get("data", resp) if isinstance(resp, dict) else {}
            html = data.get("html") or data.get("rawHtml") or ""
            text = data.get("markdown")
            status = (data.get("metadata") or {}).get("statusCode")
            return FetchResult(
                url=url,
                method="firecrawl",
                success=bool(html or text),
                status_code=status,
                html=html,
                text=text,
            )
        except Exception as exc:  # noqa: BLE001 - surface as a failed fetch, trigger fallback
            return FetchResult(url=url, method="firecrawl", success=False, error=str(exc))


class PlaywrightStealthFetcher:
    """Fallback fetcher: headless Chromium with stealth tweaks for JS-heavy/bot-gated pages."""

    def __init__(self, timeout_seconds: int | None = None):
        self.timeout = (timeout_seconds or settings.FETCH_TIMEOUT_SECONDS) * 1000

    def fetch(self, url: str) -> FetchResult:
        try:
            from playwright.sync_api import sync_playwright  # lazy import

            try:
                from playwright_stealth import stealth_sync
            except Exception:  # noqa: BLE001
                stealth_sync = None

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                    )
                )
                if stealth_sync:
                    stealth_sync(page)
                resp = page.goto(url, timeout=self.timeout, wait_until="networkidle")
                html = page.content()
                status = resp.status if resp else None
                browser.close()
                return FetchResult(
                    url=url,
                    method="playwright",
                    success=bool(html),
                    status_code=status,
                    html=html,
                )
        except Exception as exc:  # noqa: BLE001
            return FetchResult(url=url, method="playwright", success=False, error=str(exc))


class CompositeFetcher:
    """Firecrawl first; fall back to Playwright-stealth when needed."""

    def __init__(self, primary: Fetcher, fallback: Fetcher | None = None):
        self.primary = primary
        self.fallback = fallback

    def fetch(self, url: str) -> FetchResult:
        result = self.primary.fetch(url)
        if self.fallback is not None and needs_fallback(result):
            fb = self.fallback.fetch(url)
            # Keep the fallback result if it actually produced usable content.
            if fb.success and not needs_fallback(fb):
                return fb
            # Otherwise prefer whichever succeeded at all.
            return fb if (fb.success and not result.success) else result
        return result


def build_default_fetcher(firecrawl_key: str | None) -> Fetcher:
    """Wire the production fetcher. Playwright fallback is always available."""
    fallback = PlaywrightStealthFetcher()
    if firecrawl_key:
        return CompositeFetcher(FirecrawlFetcher(firecrawl_key), fallback)
    # No Firecrawl key configured — use Playwright directly.
    return fallback
