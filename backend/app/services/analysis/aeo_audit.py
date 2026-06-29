"""Module 6 — AEO Audit (site + page scope, with competitor_delta).

Scores presence/readiness across the AI answer surfaces — AI Overview, People
Also Ask, Knowledge Panel, Voice search — plus answer-paragraph and content-
structure readiness derived from the crawled content. PAA coverage is measured
against the PAA queries persisted in Phase 3 (``serp_queries``).
"""

from __future__ import annotations

import re

from app.models.crawl import Page
from app.models.serp import QUERY_PAA, SerpQuery
from app.schemas.contract import Layer, Priority, Recommendation, Status
from app.services.analysis.aeo_features import features_for_page
from app.services.analysis.base import (
    Check,
    build_competitor_delta,
    build_result,
    maybe_enrich_recommendations,
)
from app.services.analysis.signals import ratio
from app.services.benchmarks import get_benchmark

MODULE = "aeo_audit"
DELTA_SIGNALS = [
    "concise_answer_rate", "question_heading_rate", "faq_schema_rate", "org_schema_rate",
]

_STOP = {"the", "a", "an", "to", "of", "for", "and", "or", "in", "on", "is", "are",
         "do", "does", "how", "what", "why", "when", "where", "who", "which", "can"}


def _readiness_status(rate: float) -> Status:
    if rate >= 0.6:
        return Status.passing
    return Status.warn if rate >= 0.3 else Status.fail


def _metrics(pages: list[Page]) -> dict[str, float]:
    feats = [features_for_page(p) for p in pages]
    schema_answer = [
        f["has_faq_schema"] or f["has_howto_schema"] or f["has_article_schema"] for f in feats
    ]
    return {
        "concise_answer_rate": ratio([f["has_concise_answer"] for f in feats]),
        "question_heading_rate": ratio([f["question_headings"] >= 1 for f in feats]),
        "faq_schema_rate": ratio([f["has_faq_schema"] for f in feats]),
        "howto_schema_rate": ratio([f["has_howto_schema"] for f in feats]),
        "article_schema_rate": ratio([f["has_article_schema"] for f in feats]),
        "schema_answer_rate": ratio(schema_answer),
        "org_schema_rate": ratio([f["has_org_schema"] for f in feats]),
        "speakable_rate": ratio([f["has_speakable"] for f in feats]),
        "structure_rate": ratio([(f["lists"] + f["tables"]) >= 1 for f in feats]),
    }


def _paa_coverage(db, project_id: int | None, pages: list[Page]) -> tuple[float | None, int, int]:
    """Share of tracked PAA queries addressed by the client content."""
    if project_id is None:
        return None, 0, 0
    queries = (
        db.query(SerpQuery)
        .filter(SerpQuery.project_id == project_id, SerpQuery.query_type == QUERY_PAA)
        .all()
    )
    if not queries:
        return None, 0, 0
    corpus = " ".join((p.cleaned_text or "").lower() for p in pages)
    addressed = 0
    for q in queries:
        tokens = [t for t in re.findall(r"\w+", q.query.lower()) if t not in _STOP and len(t) > 2]
        if not tokens:
            continue
        hits = sum(1 for t in tokens if t in corpus)
        if hits / len(tokens) >= 0.6:
            addressed += 1
    return round(addressed / len(queries), 4), addressed, len(queries)


def _mean(*vals: float) -> float:
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    m = _metrics(ctx.client_pages)
    paa_cov, paa_hit, paa_total = _paa_coverage(db, ctx.project_id, ctx.client_pages)

    b_answer = get_benchmark(db, "aeo_answer_length")
    b_faq = get_benchmark(db, "aeo_faq_schema")
    b_qh = get_benchmark(db, "aeo_question_headings")
    b_org = get_benchmark(db, "aeo_org_schema")
    b_speak = get_benchmark(db, "aeo_speakable")
    b_struct = get_benchmark(db, "aeo_structure")

    ai_overview = _mean(
        m["concise_answer_rate"], m["question_heading_rate"], m["schema_answer_rate"]
    )
    paa_ready = _mean(m["question_heading_rate"], m["faq_schema_rate"], paa_cov)
    voice = _mean(m["concise_answer_rate"], m["speakable_rate"], m["question_heading_rate"])

    checks = [
        Check(signal="ai_overview_readiness", status=_readiness_status(ai_overview), weight=1.5,
              value=ai_overview, benchmark=b_faq.value if b_faq else 1.0,
              source=b_faq.source if b_faq else None,
              evidence=f"concise answers {int(m['concise_answer_rate']*100)}%, "
                       f"answer schema {int(m['schema_answer_rate']*100)}%"),
        Check(signal="people_also_ask_readiness", status=_readiness_status(paa_ready), weight=1.5,
              value=paa_ready, benchmark=b_qh.value if b_qh else 0.3,
              source=b_qh.source if b_qh else None,
              evidence=(
                  f"PAA coverage {int(paa_cov*100)}% ({paa_hit}/{paa_total})"
                  if paa_cov is not None
                  else f"question headings on {int(m['question_heading_rate']*100)}% of pages"
              )),
        Check(signal="knowledge_panel_readiness", status=_readiness_status(m["org_schema_rate"]),
              weight=1.0, value=m["org_schema_rate"], benchmark=b_org.value if b_org else 1.0,
              source=b_org.source if b_org else None,
              evidence=f"Organization schema on {int(m['org_schema_rate']*100)}% of pages"),
        Check(signal="voice_search_readiness", status=_readiness_status(voice), weight=1.0,
              value=voice, benchmark=b_speak.value if b_speak else 1.0,
              source=b_speak.source if b_speak else None,
              evidence=f"speakable {int(m['speakable_rate']*100)}%, "
                       f"concise answers {int(m['concise_answer_rate']*100)}%"),
        Check(signal="answer_paragraph_readiness",
              status=_readiness_status(m["concise_answer_rate"]), weight=1.5,
              value=m["concise_answer_rate"], benchmark=b_answer.value if b_answer else 54,
              source=b_answer.source if b_answer else None,
              evidence=f"{int(m['concise_answer_rate']*100)}% of pages lead with a concise answer"),
        Check(signal="content_structure_readiness",
              status=_readiness_status(m["structure_rate"]), weight=1.0,
              value=m["structure_rate"], benchmark=b_struct.value if b_struct else 1.0,
              source=b_struct.source if b_struct else None,
              evidence=f"{int(m['structure_rate']*100)}% of pages use lists/tables"),
    ]

    _RECS = {
        "ai_overview_readiness": (
            "Make pages AI-Overview-ready", Priority.high,
            "Lead with a concise answer and add FAQ/HowTo/Article schema so engines can cite you."),
        "people_also_ask_readiness": (
            "Target People Also Ask", Priority.high,
            "Add question-led H2/H3 with concise answers and FAQPage schema for PAA queries."),
        "knowledge_panel_readiness": (
            "Strengthen Knowledge Panel signals", Priority.med,
            "Add Organization schema with sameAs links, logo and a complete About page."),
        "voice_search_readiness": (
            "Improve voice-search readiness", Priority.med,
            "Add Speakable schema and conversational, concise (~40-60 word) answers."),
        "answer_paragraph_readiness": (
            "Add lead answer paragraphs", Priority.high,
            "Open key pages with a direct 40-60 word answer to the page's core question."),
        "content_structure_readiness": (
            "Improve answer extractability", Priority.med,
            "Use bulleted/numbered lists and comparison tables with clear question headings."),
    }
    recs: list[Recommendation] = []
    for c in checks:
        if c.status == Status.passing or c.signal not in _RECS:
            continue
        action, prio, how_to = _RECS[c.signal]
        recs.append(Recommendation(
            priority=prio if c.status == Status.fail else Priority.med,
            layer=Layer.aeo, action=action, how_to=how_to,
            effort="med", impact="high" if prio == Priority.high else "med"))
    recs = maybe_enrich_recommendations(ctx.llm, recs)

    competitor_metrics = {name: _metrics(pages) for name, pages in ctx.competitor_pages.items()}
    delta = build_competitor_delta(m, competitor_metrics, DELTA_SIGNALS)

    return build_result(
        module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=checks,
        recommendations=recs, competitor_delta=delta, generated_at=ctx.generated_at,
    )
