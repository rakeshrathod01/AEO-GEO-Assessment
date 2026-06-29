"""Generate ~60-70 target prompts grouped into intent buckets.

Seeds come from Ahrefs PAA/featured-snippet queries (``serp_queries``) and crawled
content (page titles), combined with brand/industry/competitor templates. Works
deterministically with no API key; an Anthropic key lets Sonnet diversify further.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.crawl import STATUS_DONE, CrawlJob, Page
from app.models.project import Competitor, Project
from app.models.prompt import (
    INTENT_COMMERCIAL,
    INTENT_COMPARISON,
    INTENT_INFORMATIONAL,
    INTENT_NAVIGATIONAL,
    INTENT_TRANSACTIONAL,
    Prompt,
)
from app.models.serp import SerpQuery

_COMPARISON_RE = re.compile(r"\b(vs|versus|alternative|compare|comparison)\b", re.IGNORECASE)
_TRANSACTIONAL_RE = re.compile(
    r"\b(pricing|price|cost|buy|purchase|trial|demo|sign ?up|quote|subscribe)\b", re.IGNORECASE
)
_COMMERCIAL_RE = re.compile(
    r"\b(best|top|review|reviews|tools?|software|solutions?|vendors?|providers?|platform|"
    r"for enterprise|services?)\b",
    re.IGNORECASE,
)
_NAV_RE = re.compile(r"\b(login|log in|sign in|contact|careers|support|account)\b", re.IGNORECASE)
_QUESTION_RE = re.compile(r"^(how|what|why|when|where|who|which|can|does|is|are)\b", re.IGNORECASE)


def classify_intent(text: str, brand: str | None = None) -> str:
    t = (text or "").strip().lower()
    if _COMPARISON_RE.search(t):
        return INTENT_COMPARISON
    if _TRANSACTIONAL_RE.search(t):
        return INTENT_TRANSACTIONAL
    if _NAV_RE.search(t) or (brand and t == brand.lower()):
        return INTENT_NAVIGATIONAL
    if _COMMERCIAL_RE.search(t):
        return INTENT_COMMERCIAL
    if _QUESTION_RE.match(t) or t.endswith("?"):
        return INTENT_INFORMATIONAL
    return INTENT_INFORMATIONAL


def _domain(url: str) -> str:
    net = urlparse(url if "//" in url else "https://" + url).netloc.lower()
    return net[4:] if net.startswith("www.") else net


def _topics(db: Session, project: Project) -> list[str]:
    """Derive a handful of topic phrases from crawl titles + SERP seed keywords."""
    topics: list[str] = []
    if project.industry:
        topics.append(project.industry.lower())

    job = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id, CrawlJob.status == STATUS_DONE)
        .order_by(CrawlJob.created_at.desc())
        .first()
    )
    if job:
        titles = (
            db.query(Page.title)
            .filter(Page.crawl_job_id == job.id, Page.is_competitor.is_(False))
            .all()
        )
        for (title,) in titles:
            if not title:
                continue
            # Use the leading phrase of the title (before a separator).
            phrase = re.split(r"[|\-–:]", title)[0].strip().lower()
            # Skip URL/scheme-like junk (e.g. "https://...").
            if "http" in phrase or "//" in phrase or "www." in phrase:
                continue
            if 3 <= len(phrase) <= 40:
                topics.append(phrase)

    for (kw,) in db.query(SerpQuery.seed_keyword).filter(SerpQuery.project_id == project.id).all():
        if kw and len(kw) <= 40:
            topics.append(kw.lower())

    # Dedup, keep order, cap.
    seen, out = set(), []
    for t in topics:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:10] or ["the industry"]


def _candidates(project: Project, competitors: list[str], topics: list[str], serp: list[str]):
    """Yield (text, bucket, source) candidates."""
    brand = project.name
    ind = (project.industry or topics[0]).lower()

    # Informational — from real PAA/snippet questions first, then templates.
    for q in serp:
        yield q, classify_intent(q, brand), "paa"
    for t in topics:
        yield f"what is {t}", INTENT_INFORMATIONAL, "template"
        yield f"how does {t} work", INTENT_INFORMATIONAL, "template"
        yield f"how to choose {t}", INTENT_INFORMATIONAL, "template"
        yield f"how to implement {t}", INTENT_INFORMATIONAL, "template"
        yield f"benefits of {t}", INTENT_INFORMATIONAL, "template"
        yield f"{t} best practices", INTENT_INFORMATIONAL, "template"
        yield f"common {t} mistakes", INTENT_INFORMATIONAL, "template"
        yield f"{t} for beginners", INTENT_INFORMATIONAL, "template"

    # Commercial investigation.
    for t in topics[:6]:
        yield f"best {t} tools", INTENT_COMMERCIAL, "template"
        yield f"top {t} providers", INTENT_COMMERCIAL, "template"
        yield f"{t} software comparison", INTENT_COMMERCIAL, "template"
        yield f"enterprise {t} platforms", INTENT_COMMERCIAL, "template"
        yield f"{t} solutions for business", INTENT_COMMERCIAL, "template"
    yield f"is {brand} a good {ind} solution", INTENT_COMMERCIAL, "template"
    yield f"{brand} reviews", INTENT_COMMERCIAL, "template"
    yield f"{brand} ratings", INTENT_COMMERCIAL, "template"

    # Transactional.
    for tmpl in ("{b} pricing", "{b} cost", "{b} free trial", "{b} demo",
                 "{b} discount", "get started with {b}"):
        yield tmpl.format(b=brand), INTENT_TRANSACTIONAL, "template"
    for t in topics[:4]:
        yield f"buy {t} software", INTENT_TRANSACTIONAL, "template"

    # Navigational.
    for tmpl in ("{b}", "{b} login", "{b} contact", "{b} support",
                 "{b} careers", "{b} documentation"):
        yield tmpl.format(b=brand), INTENT_NAVIGATIONAL, "template"

    # Comparison — vs each competitor + alternatives.
    for c in competitors:
        yield f"{brand} vs {c}", INTENT_COMPARISON, "template"
        yield f"{c} vs {brand}", INTENT_COMPARISON, "template"
    yield f"{brand} alternatives", INTENT_COMPARISON, "template"
    yield f"best alternatives to {brand}", INTENT_COMPARISON, "template"
    yield f"{brand} competitors", INTENT_COMPARISON, "template"
    yield f"top {ind} companies", INTENT_COMPARISON, "template"


def generate_prompts(db: Session, project_id: int, target: int | None = None) -> list[Prompt]:
    """Build, persist (replacing prior) and return the target prompt set."""
    target = target or settings.PROMPT_TARGET_COUNT
    project = db.get(Project, project_id)
    if project is None:
        return []
    competitors = [c.name for c in db.query(Competitor).filter(Competitor.project_id == project_id)]
    topics = _topics(db, project)
    serp = [
        q for (q,) in db.query(SerpQuery.query).filter(SerpQuery.project_id == project_id).all()
    ]

    # Dedup by normalized text, preserve first-seen.
    seen: set[str] = set()
    chosen: list[tuple[str, str, str]] = []
    for text, bucket, source in _candidates(project, competitors, topics, serp):
        text = text.strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        chosen.append((text, bucket, source))

    # Cap to target, round-robin across buckets so every bucket is represented.
    by_bucket: dict[str, list[tuple[str, str, str]]] = {}
    for item in chosen:
        by_bucket.setdefault(item[1], []).append(item)
    selected: list[tuple[str, str, str]] = []
    while len(selected) < target and any(by_bucket.values()):
        for bucket in list(by_bucket):
            if by_bucket[bucket]:
                selected.append(by_bucket[bucket].pop(0))
                if len(selected) >= target:
                    break

    # Persist (replace existing for this project).
    db.query(Prompt).filter(Prompt.project_id == project_id).delete()
    rows = [
        Prompt(project_id=project_id, text=text, intent_bucket=bucket, source=source)
        for text, bucket, source in selected
    ]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


def prompts_by_bucket(prompts: list[Prompt]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in prompts:
        out.setdefault(p.intent_bucket, []).append(p.text)
    return out


def export_payload(prompts: list[Prompt]) -> str:
    return json.dumps(prompts_by_bucket(prompts))
