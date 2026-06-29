"""AEO (Answer Engine Optimization) feature extraction from crawled HTML.

Computes the page-level signals AI answer engines reward: question-led
subheadings, a concise lead answer paragraph, extractable structure (lists/
tables), and answer-oriented structured data (FAQ/HowTo/Organization/Speakable).

Re-parses raw HTML from disk (like the internal-link graph). Falls back to the
signals captured at crawl time when raw HTML is unavailable.
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from app.models.crawl import Page
from app.services.analysis.internal_graph import load_html
from app.services.analysis.signals import page_signals

_QUESTION_RE = re.compile(
    r"^(how|what|why|when|where|who|whose|whom|which|can|could|should|would|"
    r"do|does|did|is|are|will|may)\b",
    re.IGNORECASE,
)

# Concise answer passages (snippet/voice friendly) sit ~20-60 words.
ANSWER_MIN, ANSWER_MAX = 20, 60


def is_question(text: str) -> bool:
    text = (text or "").strip()
    return text.endswith("?") or bool(_QUESTION_RE.match(text))


def _ld_types(soup: BeautifulSoup) -> list[str]:
    types: list[str] = []
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type"):
                t = item["@type"]
                types.extend(t if isinstance(t, list) else [t])
    return [str(t).lower() for t in types]


def extract_aeo_features(html: str) -> dict:
    soup = BeautifulSoup(html or "", "lxml")

    subheads = [h.get_text(strip=True) for h in soup.find_all(["h2", "h3", "h4"])]
    question_headings = sum(1 for h in subheads if is_question(h))

    # Lead answer paragraph: first substantive <p>, ideally a concise answer.
    first_words = 0
    has_concise_answer = False
    for p in soup.find_all("p")[:5]:
        words = len(p.get_text(" ", strip=True).split())
        if words >= 10 and first_words == 0:
            first_words = words
        if ANSWER_MIN <= words <= ANSWER_MAX:
            has_concise_answer = True
            break

    types = _ld_types(soup)

    def has(*needles: str) -> bool:
        return any(any(n in t for n in needles) for t in types)

    return {
        "subheadings": len(subheads),
        "question_headings": question_headings,
        "question_heading_ratio": round(question_headings / len(subheads), 4) if subheads else 0.0,
        "first_paragraph_words": first_words,
        "has_concise_answer": has_concise_answer,
        "lists": len(soup.find_all(["ul", "ol"])),
        "tables": len(soup.find_all("table")),
        "schema_types": sorted(set(types)),
        "has_faq_schema": has("faqpage", "qapage", "question"),
        "has_howto_schema": has("howto"),
        "has_article_schema": has("article", "blogposting", "newsarticle"),
        "has_org_schema": has("organization", "localbusiness", "corporation"),
        "has_speakable": has("speakable"),
        "has_breadcrumb": has("breadcrumb"),
    }


def features_for_page(page: Page) -> dict:
    """AEO features for a page; degrades to crawl-time signals if raw HTML is gone."""
    html = load_html(page)
    if html:
        return extract_aeo_features(html)
    # Fallback: use the signals captured during the crawl.
    sig = page_signals(page)
    types = [str(t).lower() for t in sig.get("structured_data_types", [])]

    def has(*needles: str) -> bool:
        return any(any(n in t for n in needles) for t in types)

    h1 = sig.get("h1") or []
    return {
        "subheadings": sig.get("h2_count", 0),
        "question_headings": sum(1 for h in h1 if is_question(h)),
        "question_heading_ratio": 0.0,
        "first_paragraph_words": 0,
        "has_concise_answer": False,
        "lists": 0,
        "tables": 0,
        "schema_types": sorted(set(types)),
        "has_faq_schema": has("faqpage", "qapage", "question"),
        "has_howto_schema": has("howto"),
        "has_article_schema": has("article", "blogposting", "newsarticle"),
        "has_org_schema": has("organization", "localbusiness", "corporation"),
        "has_speakable": has("speakable"),
        "has_breadcrumb": has("breadcrumb"),
    }
