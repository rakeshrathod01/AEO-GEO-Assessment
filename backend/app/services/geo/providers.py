"""Swappable GEO data-source providers.

Each provider answers a prompt and returns text + cited URLs, tagged with a
``source_kind``: ``api`` (the assistant's own API) or ``serp`` (captured from a
search-engine results page, e.g. Google AI Overview). Adding/removing a provider
is just editing :func:`build_providers`; the GEO analyzer is provider-agnostic.

All providers: read BYO keys from Settings, cache every call in ``api_cache``,
and degrade to ``ok=False`` when unconfigured or on error (so runs/tests never
fail for a missing key).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from app.services.cache import get_or_set
from app.services.keys import get_api_key

SOURCE_API = "api"
SOURCE_SERP = "serp"

_URL_RE = re.compile(r"https?://[^\s)>\]\"']+", re.IGNORECASE)


def extract_domains(text: str, citations: list[str]) -> list[str]:
    """Ordered, de-duplicated domains from explicit citations + inline URLs."""
    urls = list(citations or []) + _URL_RE.findall(text or "")
    out: list[str] = []
    for u in urls:
        m = re.search(r"https?://([^/\s]+)", u if "//" in u else "https://" + u)
        host = (m.group(1) if m else u).lower()
        if host.startswith("www."):
            host = host[4:]
        if host and host not in out:
            out.append(host)
    return out


@dataclass
class GeoResponse:
    provider: str
    source_kind: str
    ok: bool
    text: str = ""
    citations: list[str] = field(default_factory=list)  # explicit cited URLs
    domains: list[str] = field(default_factory=list)  # ordered cited/mentioned domains
    error: str | None = None


class GeoProvider(Protocol):
    name: str
    source_kind: str
    @property
    def enabled(self) -> bool: ...
    def query(self, prompt: str) -> GeoResponse: ...


def _key(db: Session, provider: str, tenant_id: int | None = None) -> str | None:
    return get_api_key(db, provider, tenant_id)


class _BaseProvider:
    name = "base"
    source_kind = SOURCE_API

    def __init__(self, db: Session, api_key: str | None):
        self.db = db
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _raw(self, prompt: str) -> dict:
        """Return {'text': str, 'citations': [url, ...]}. Override per provider."""
        raise NotImplementedError

    def query(self, prompt: str) -> GeoResponse:
        if not self.enabled:
            return GeoResponse(self.name, self.source_kind, ok=False, error="not configured")
        try:
            data = get_or_set(
                self.db, provider=f"geo:{self.name}", endpoint=self.name,
                params={"prompt": prompt}, fetch=lambda: self._raw(prompt),
            )
        except Exception as exc:  # noqa: BLE001
            return GeoResponse(self.name, self.source_kind, ok=False, error=str(exc))
        text = data.get("text", "")
        citations = data.get("citations", [])
        return GeoResponse(
            self.name, self.source_kind, ok=True, text=text, citations=citations,
            domains=extract_domains(text, citations),
        )


class OpenAIProvider(_BaseProvider):
    name = "chatgpt"
    source_kind = SOURCE_API

    def _raw(self, prompt: str) -> dict:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        r = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        return {"text": r.choices[0].message.content or "", "citations": []}


class GeminiProvider(_BaseProvider):
    name = "gemini"
    source_kind = SOURCE_API

    def _raw(self, prompt: str) -> dict:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        r = model.generate_content(prompt)
        return {"text": getattr(r, "text", "") or "", "citations": []}


class ClaudeProvider(_BaseProvider):
    name = "claude"
    source_kind = SOURCE_API

    def _raw(self, prompt: str) -> dict:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return {"text": text, "citations": []}


class PerplexityProvider(_BaseProvider):
    name = "perplexity"
    source_kind = SOURCE_API

    def _raw(self, prompt: str) -> dict:
        import httpx

        resp = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "sonar", "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        text = body["choices"][0]["message"]["content"]
        return {"text": text, "citations": body.get("citations", [])}


class SerpAIOverviewProvider(_BaseProvider):
    """SERP capture (not an API): fetches the Google SERP and extracts cited domains.

    Uses the Firecrawl key for capture. Clearly flagged source_kind='serp'.
    """

    name = "ai_overview"
    source_kind = SOURCE_SERP

    def _raw(self, prompt: str) -> dict:
        from urllib.parse import quote_plus

        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=self.api_key)
        url = f"https://www.google.com/search?q={quote_plus(prompt)}"
        resp = app.scrape_url(url, params={"formats": ["markdown", "html"]})
        data = resp.get("data", resp) if isinstance(resp, dict) else {}
        text = data.get("markdown") or data.get("html") or ""
        return {"text": text, "citations": _URL_RE.findall(text)}


def build_providers(db: Session, tenant_id: int | None = None) -> list[GeoProvider]:
    """Instantiate the configured providers (swap by editing this list)."""
    candidates: list[GeoProvider] = [
        OpenAIProvider(db, _key(db, "openai", tenant_id)),
        GeminiProvider(db, _key(db, "gemini", tenant_id)),
        ClaudeProvider(db, _key(db, "anthropic", tenant_id)),
        PerplexityProvider(db, _key(db, "perplexity", tenant_id)),
        SerpAIOverviewProvider(db, _key(db, "firecrawl", tenant_id)),
    ]
    return [p for p in candidates if p.enabled]
