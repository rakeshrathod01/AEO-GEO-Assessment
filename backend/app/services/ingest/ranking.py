"""Heuristic ranking of sitemap URLs to select the top-N business-critical pages.

Signals (no live link graph needed pre-crawl):
  1. URL depth        — shallower paths are more business-critical.
  2. Money-page match — /pricing, /demo, /contact, /solutions, ... get a boost.
  3. Link prominence  — approximated structurally: a page that is the prefix of
                        many other URLs is a hub/section page (high prominence).
  4. Sitemap priority — <priority> from the sitemap, when present.
Plus penalties for clearly non-business URLs (blog tails, tags, paginated,
legal, asset files, locale duplicates).

Pure + deterministic so it's fully unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

# Money / conversion-intent path patterns.
MONEY_PATTERNS = [
    r"/pricing", r"/plans?", r"/buy", r"/checkout", r"/cart", r"/quote",
    r"/demo", r"/free-trial", r"/trial", r"/sign-?up", r"/get-started",
    r"/contact", r"/sales", r"/book", r"/schedule",
    r"/product", r"/products", r"/solutions?", r"/services?", r"/features?",
    r"/platform", r"/use-cases?", r"/industries", r"/enterprise",
]
_MONEY_RE = re.compile("|".join(MONEY_PATTERNS), re.IGNORECASE)

# Low-value / non-business path patterns (penalized).
PENALTY_PATTERNS = [
    r"/tag/", r"/tags/", r"/category/", r"/categories/", r"/author/",
    r"/page/\d+", r"/\d{4}/\d{2}/", r"/archive", r"/feed",
    r"/privacy", r"/terms", r"/cookie", r"/legal", r"/sitemap",
    r"/login", r"/logout", r"/account", r"/cart/", r"/wp-",
]
_PENALTY_RE = re.compile("|".join(PENALTY_PATTERNS), re.IGNORECASE)

_ASSET_RE = re.compile(r"\.(pdf|jpg|jpeg|png|gif|svg|zip|xml|css|js|ico|webp)$", re.IGNORECASE)

# Common locale prefixes (/en/, /en-us/, /fr/, ...) — duplicate-content alternates.
_LOCALE_RE = re.compile(r"^/[a-z]{2}(-[a-z]{2})?(/|$)", re.IGNORECASE)


@dataclass
class RankedUrl:
    url: str
    score: float
    depth: int
    reasons: dict[str, float] = field(default_factory=dict)
    is_money_page: bool = False
    is_homepage: bool = False


def _path_segments(path: str) -> list[str]:
    return [seg for seg in path.split("/") if seg]


def rank_urls(
    urls: list[str],
    priority_by_url: dict[str, float] | None = None,
) -> list[RankedUrl]:
    """Score every URL and return them sorted best-first (deterministic)."""
    priority_by_url = priority_by_url or {}
    parsed = [(u, urlparse(u)) for u in urls]

    # Prominence: how many URLs are descendants of each URL's path prefix.
    paths = [p.path or "/" for _, p in parsed]
    descendant_counts: dict[str, int] = {}
    for u, p in parsed:
        base = (p.path or "/").rstrip("/")
        prefix = base + "/" if base else "/"
        count = sum(1 for other in paths if other != (p.path or "/") and other.startswith(prefix))
        descendant_counts[u] = count
    max_desc = max(descendant_counts.values(), default=0)

    ranked: list[RankedUrl] = []
    for u, p in parsed:
        path = p.path or "/"
        segs = _path_segments(path)
        depth = len(segs)
        reasons: dict[str, float] = {}

        is_home = depth == 0
        # 1. Depth — shallower is better.
        depth_score = max(0.0, 1.0 - depth * 0.18)
        reasons["depth"] = round(depth_score, 4)

        # 2. Money-page boost.
        is_money = bool(_MONEY_RE.search(path))
        money_score = 0.6 if is_money else 0.0
        if is_money:
            reasons["money_page"] = money_score

        # 3. Prominence (hub pages with many descendants).
        prominence = (descendant_counts[u] / max_desc) if max_desc else 0.0
        prominence_score = round(prominence * 0.5, 4)
        if prominence_score:
            reasons["prominence"] = prominence_score

        # 4. Sitemap <priority>.
        prio = priority_by_url.get(u)
        prio_score = round((prio or 0.0) * 0.3, 4)
        if prio_score:
            reasons["sitemap_priority"] = prio_score

        # Homepage is always the most business-critical page.
        home_bonus = 1.0 if is_home else 0.0
        if home_bonus:
            reasons["homepage"] = home_bonus

        # Penalties.
        penalty = 0.0
        if _PENALTY_RE.search(path):
            penalty += 0.5
            reasons["low_value_penalty"] = -0.5
        if _ASSET_RE.search(path):
            penalty += 1.0
            reasons["asset_penalty"] = -1.0
        if p.query:
            penalty += 0.15
            reasons["query_penalty"] = -0.15
        if depth > 0 and _LOCALE_RE.match(path) and depth > 1:
            penalty += 0.1
            reasons["locale_penalty"] = -0.1

        score = depth_score + money_score + prominence_score + prio_score + home_bonus - penalty
        ranked.append(
            RankedUrl(
                url=u,
                score=round(score, 4),
                depth=depth,
                reasons=reasons,
                is_money_page=is_money,
                is_homepage=is_home,
            )
        )

    # Sort by score desc, then shallower depth, then URL for stable ties.
    ranked.sort(key=lambda r: (-r.score, r.depth, r.url))
    return ranked


def select_top(urls, n: int = 50, priority_by_url: dict[str, float] | None = None):
    """Rank and return the top-N RankedUrl entries."""
    ranked = rank_urls(list(urls), priority_by_url=priority_by_url)
    return ranked[:n]
