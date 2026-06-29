"""Match competitor pages to the client's selected pages ("comparable pages").

Two strategies:
  * mirror_client_paths  — when only a competitor domain is known, mirror each
    client page's path onto the competitor domain (client /pricing ->
    competitor.com/pricing). Guarantees a 1:1 comparable set.
  * match_by_similarity  — when a competitor sitemap is available, pick the
    competitor URL whose path is most similar to each client page.

Both are pure + deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse


@dataclass
class CompetitorMatch:
    client_url: str
    competitor_url: str
    score: float  # 1.0 for a mirrored path; similarity ratio otherwise


def _base(competitor_base_url: str) -> tuple[str, str]:
    raw = competitor_base_url if "//" in competitor_base_url else "https://" + competitor_base_url
    p = urlparse(raw)
    scheme = p.scheme or "https"
    netloc = p.netloc.lower() or p.path.lower()
    return scheme, netloc


def mirror_client_paths(client_urls: list[str], competitor_base_url: str) -> list[CompetitorMatch]:
    """Project each client URL's path/query onto the competitor domain."""
    scheme, netloc = _base(competitor_base_url)
    matches: list[CompetitorMatch] = []
    for cu in client_urls:
        cp = urlparse(cu)
        mirrored = urlunparse((scheme, netloc, cp.path or "/", "", cp.query, ""))
        matches.append(CompetitorMatch(client_url=cu, competitor_url=mirrored, score=1.0))
    return matches


def _path_key(url: str) -> str:
    return (urlparse(url).path or "/").lower()


def match_by_similarity(
    client_urls: list[str],
    competitor_urls: list[str],
    min_score: float = 0.45,
) -> list[CompetitorMatch]:
    """For each client URL, choose the most path-similar competitor URL.

    A competitor URL is used at most once. Falls back to nothing for a client
    page if no candidate clears ``min_score``.
    """
    remaining = list(competitor_urls)
    matches: list[CompetitorMatch] = []
    for cu in client_urls:
        ck = _path_key(cu)
        best_url: str | None = None
        best_score = 0.0
        for comp in remaining:
            score = SequenceMatcher(None, ck, _path_key(comp)).ratio()
            # Exact path match wins outright.
            if _path_key(comp) == ck:
                score = 1.0
            if score > best_score:
                best_score, best_url = score, comp
        if best_url is not None and best_score >= min_score:
            remaining.remove(best_url)
            matches.append(
                CompetitorMatch(
                    client_url=cu, competitor_url=best_url, score=round(best_score, 4)
                )
            )
    return matches
