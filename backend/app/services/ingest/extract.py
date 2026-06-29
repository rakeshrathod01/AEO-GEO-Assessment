"""Clean HTML -> text and extract on-page + technical SEO signals.

Pure function of (html, url): given raw HTML it returns cleaned text plus a
structured signal bundle. No network. The cleaned text (never raw HTML) is what
later phases send to the LLM.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

_WS_RE = re.compile(r"\s+")
# Tags whose text is not page content.
_NON_CONTENT_TAGS = ["script", "style", "noscript", "template", "svg"]


@dataclass
class Extraction:
    cleaned_text: str
    title: str | None
    meta_description: str | None
    word_count: int
    signals: dict = field(default_factory=dict)


def _clean_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(_NON_CONTENT_TAGS):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return _WS_RE.sub(" ", text).strip()


def extract(html: str, url: str, http_status: int | None = None) -> Extraction:
    soup = BeautifulSoup(html or "", "lxml")
    host = urlparse(url).netloc.lower()

    title = (soup.title.string.strip() if soup.title and soup.title.string else None)

    def meta(name=None, prop=None) -> str | None:
        if name:
            el = soup.find("meta", attrs={"name": re.compile(f"^{name}$", re.I)})
        else:
            el = soup.find("meta", attrs={"property": re.compile(f"^{re.escape(prop)}$", re.I)})
        if el and el.get("content"):
            return el["content"].strip()
        return None

    meta_description = meta(name="description")
    meta_robots = meta(name="robots")

    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3_count = len(soup.find_all("h3"))

    canonical_el = soup.find("link", rel=lambda v: v and "canonical" in v)
    canonical = canonical_el.get("href") if canonical_el else None

    html_el = soup.find("html")
    lang = html_el.get("lang") if html_el else None
    has_viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}) is not None

    # Links: internal vs external.
    internal, external = 0, 0
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        abs_url = urljoin(url, href)
        netloc = urlparse(abs_url).netloc.lower()
        if not netloc or netloc == host:
            internal += 1
        else:
            external += 1

    # Images / alt coverage.
    imgs = soup.find_all("img")
    imgs_missing_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())

    # Structured data (JSON-LD).
    ld_types: list[str] = []
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type"):
                t = item["@type"]
                ld_types.extend(t if isinstance(t, list) else [t])

    # Open Graph / Twitter presence.
    og_title = meta(prop="og:title")
    og_desc = meta(prop="og:description")

    cleaned_text = _clean_text(soup)
    word_count = len(cleaned_text.split())
    html_size = len(html or "")

    signals = {
        # --- on-page ---
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": meta_description,
        "meta_description_length": len(meta_description) if meta_description else 0,
        "h1": h1s,
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": h3_count,
        "word_count": word_count,
        "images_count": len(imgs),
        "images_missing_alt": imgs_missing_alt,
        "internal_links": internal,
        "external_links": external,
        "og_title": og_title,
        "og_description": og_desc,
        # --- technical ---
        "http_status": http_status,
        "canonical": canonical,
        "has_canonical": canonical is not None,
        "meta_robots": meta_robots,
        "is_noindex": bool(meta_robots and "noindex" in meta_robots.lower()),
        "lang": lang,
        "has_viewport_meta": has_viewport,
        "structured_data_types": sorted(set(ld_types)),
        "has_structured_data": bool(ld_types),
        "html_size_bytes": html_size,
        "text_to_html_ratio": round(len(cleaned_text) / html_size, 4) if html_size else 0.0,
    }

    return Extraction(
        cleaned_text=cleaned_text,
        title=title,
        meta_description=meta_description,
        word_count=word_count,
        signals=signals,
    )
