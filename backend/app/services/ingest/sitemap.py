"""Sitemap fetching + parsing (handles sitemap index files recursively).

Parsing is pure (operates on XML text) so it is unit-testable without network;
fetching is a thin httpx wrapper used by the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from app.services.ingest.urls import normalize_url

_SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@dataclass
class SitemapEntry:
    url: str
    lastmod: str | None = None
    priority: float | None = None


@dataclass
class ParsedSitemap:
    entries: list[SitemapEntry] = field(default_factory=list)
    # Nested sitemap URLs (when the document is a <sitemapindex>).
    child_sitemaps: list[str] = field(default_factory=list)


def parse_sitemap_xml(xml_text: str) -> ParsedSitemap:
    """Parse a urlset or sitemapindex document."""
    result = ParsedSitemap()
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return result

    tag = root.tag.lower()
    if tag.endswith("sitemapindex"):
        for sm in root.findall(f"{_SM_NS}sitemap"):
            loc = sm.findtext(f"{_SM_NS}loc")
            n = normalize_url(loc) if loc else None
            if n:
                result.child_sitemaps.append(n)
        return result

    # urlset
    for url_el in root.findall(f"{_SM_NS}url"):
        loc = url_el.findtext(f"{_SM_NS}loc")
        n = normalize_url(loc) if loc else None
        if not n:
            continue
        prio_text = url_el.findtext(f"{_SM_NS}priority")
        try:
            priority = float(prio_text) if prio_text is not None else None
        except ValueError:
            priority = None
        result.entries.append(
            SitemapEntry(
                url=n,
                lastmod=url_el.findtext(f"{_SM_NS}lastmod"),
                priority=priority,
            )
        )
    return result


def fetch_sitemap_entries(
    sitemap_url: str,
    *,
    fetch_text=None,
    max_sitemaps: int = 50,
    max_urls: int = 5000,
) -> list[SitemapEntry]:
    """Fetch a sitemap (following index children) and return flat entries.

    ``fetch_text(url) -> str`` is injectable for tests; defaults to httpx GET.
    """
    if fetch_text is None:
        import httpx

        def fetch_text(url: str) -> str:  # type: ignore[misc]
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            return resp.text

    seen_sitemaps: set[str] = set()
    queue = [normalize_url(sitemap_url) or sitemap_url]
    entries: dict[str, SitemapEntry] = {}

    while queue and len(seen_sitemaps) < max_sitemaps and len(entries) < max_urls:
        current = queue.pop(0)
        if current in seen_sitemaps:
            continue
        seen_sitemaps.add(current)
        try:
            xml_text = fetch_text(current)
        except Exception:
            continue
        parsed = parse_sitemap_xml(xml_text)
        for child in parsed.child_sitemaps:
            if child not in seen_sitemaps:
                queue.append(child)
        for entry in parsed.entries:
            entries.setdefault(entry.url, entry)

    return list(entries.values())
