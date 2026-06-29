"""Build an internal-link graph from crawled raw HTML.

Internal linking is an on-site concern, so the graph is derived from our own
crawl (raw HTML on disk) rather than Ahrefs. Computes inbound/outbound counts
among the selected page set, orphan pages, and links into money pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models.crawl import Page
from app.services.ingest.ranking import _MONEY_RE
from app.services.ingest.urls import normalize_url


@dataclass
class GraphStats:
    inbound: dict[str, int] = field(default_factory=dict)
    outbound: dict[str, int] = field(default_factory=dict)
    orphans: list[str] = field(default_factory=list)
    money_pages: list[str] = field(default_factory=list)
    money_pages_orphaned: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.inbound)

    @property
    def orphan_rate(self) -> float:
        return round(len(self.orphans) / self.page_count, 4) if self.page_count else 0.0

    @property
    def avg_inbound(self) -> float:
        return round(sum(self.inbound.values()) / self.page_count, 2) if self.page_count else 0.0

    @property
    def avg_outbound(self) -> float:
        return round(sum(self.outbound.values()) / self.page_count, 2) if self.page_count else 0.0


def _internal_targets(html: str, page_url: str, in_set: set[str]) -> set[str]:
    """Normalized internal link targets from a page that point inside the set."""
    soup = BeautifulSoup(html or "", "lxml")
    targets: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        norm = normalize_url(urljoin(page_url, href))
        if norm and norm != page_url and norm in in_set:
            targets.add(norm)
    return targets


def build_graph(pages: list[tuple[str, str]]) -> GraphStats:
    """pages = list of (url, html). Returns inbound/outbound + orphan stats."""
    urls = [u for u, _ in pages]
    in_set = set(urls)
    stats = GraphStats(inbound={u: 0 for u in urls}, outbound={u: 0 for u in urls})
    for url, html in pages:
        targets = _internal_targets(html, url, in_set)
        stats.outbound[url] = len(targets)
        for t in targets:
            stats.inbound[t] += 1

    for url in urls:
        if stats.inbound[url] == 0:
            stats.orphans.append(url)
        if _MONEY_RE.search(url):
            stats.money_pages.append(url)
            if stats.inbound[url] == 0:
                stats.money_pages_orphaned.append(url)
    return stats


def load_html(page: Page) -> str | None:
    if not page.raw_html_path:
        return None
    try:
        return Path(page.raw_html_path).read_text(encoding="utf-8")
    except OSError:
        return None


def build_graph_from_pages(pages: list[Page]) -> GraphStats:
    pairs = [(p.url, load_html(p) or "") for p in pages]
    return build_graph(pairs)
