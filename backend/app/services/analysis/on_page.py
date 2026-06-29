"""Module 2 — On-Page SEO analyzer (site + page scope, with competitor_delta).

Covers titles, meta descriptions, heading structure, content depth, image alt
coverage, Open Graph, schema/structured-data, and E-E-A-T signals. Benchmarks
are cited; E-E-A-T uses heuristics (+ optional Haiku refinement at page scope).
"""

from __future__ import annotations

from app.models.crawl import Page
from app.schemas.contract import Layer, Priority, Recommendation, Status
from app.services.analysis.base import (
    Check,
    build_competitor_delta,
    build_result,
    maybe_enrich_recommendations,
)
from app.services.analysis.eeat import detect_eeat
from app.services.analysis.signals import avg, page_signals, ratio
from app.services.benchmarks import get_benchmark

MODULE = "on_page"
DELTA_SIGNALS = [
    "title_ok_rate", "meta_ok_rate", "content_depth_rate", "schema_rate", "eeat_score"
]


def _alt_coverage(s: dict) -> float:
    total = s.get("images_count", 0)
    if not total:
        return 1.0  # no images -> nothing to caption
    missing = s.get("images_missing_alt", 0)
    return (total - missing) / total


def _metrics(pages: list[Page], llm=None) -> dict[str, float]:
    sig = [page_signals(p) for p in pages]
    eeat_scores = [
        detect_eeat(p.cleaned_text or "", s, llm=llm)["score"]
        for p, s in zip(pages, sig, strict=False)
    ]
    return {
        "title_present_rate": ratio([bool(s.get("title")) for s in sig]),
        "title_ok_rate": ratio([30 <= s.get("title_length", 0) <= 60 for s in sig]),
        "meta_present_rate": ratio([bool(s.get("meta_description")) for s in sig]),
        "meta_ok_rate": ratio([70 <= s.get("meta_description_length", 0) <= 160 for s in sig]),
        "single_h1_rate": ratio([s.get("h1_count", 0) == 1 for s in sig]),
        "structure_rate": ratio(
            [s.get("h1_count", 0) == 1 and s.get("h2_count", 0) >= 1 for s in sig]
        ),
        "content_depth_rate": ratio([s.get("word_count", 0) >= 600 for s in sig]),
        "alt_coverage": avg([_alt_coverage(s) for s in sig]),
        "og_rate": ratio([bool(s.get("og_title")) for s in sig]),
        "schema_rate": ratio([s.get("has_structured_data", False) for s in sig]),
        "eeat_score": round(sum(eeat_scores) / len(eeat_scores), 4) if eeat_scores else 0.0,
    }


def _rate_check(db, metric, signal, rate, *, warn_at=0.9, weight=1.0) -> Check:
    bench = get_benchmark(db, metric)
    if rate >= warn_at:
        status = Status.passing
    elif rate >= 0.5:
        status = Status.warn
    else:
        status = Status.fail
    return Check(
        signal=signal, status=status, weight=weight, value=round(rate, 4),
        benchmark=bench.value if bench else None,
        source=bench.source if bench else None,
        evidence=f"{round(rate * 100)}% of pages",
    )


_REC_MAP = {
    "title_optimized": (
        "Optimize title tags to 30–60 chars",
        "Front-load the primary keyword; keep titles 30–60 chars and unique.",
        "low", "high",
    ),
    "meta_description": (
        "Write meta descriptions (70–160 chars)",
        "Add compelling, unique descriptions with a CTA in 70–160 chars.",
        "low", "med",
    ),
    "single_h1": (
        "Use exactly one H1 per page",
        "Ensure a single descriptive H1 that matches search intent.",
        "low", "med",
    ),
    "heading_structure": (
        "Improve heading hierarchy",
        "Use one H1 then logical H2/H3 sections to structure content.",
        "low", "med",
    ),
    "content_depth": (
        "Increase content depth",
        "Expand thin pages toward 600+ words covering the topic comprehensively.",
        "med", "high",
    ),
    "image_alt": (
        "Add alt text to images",
        "Add descriptive alt attributes to all meaningful images.",
        "low", "med",
    ),
    "open_graph": (
        "Add Open Graph tags",
        "Add og:title/og:description/og:image for better social/AEO previews.",
        "low", "low",
    ),
    "schema_markup": (
        "Add schema.org structured data",
        "Add JSON-LD relevant to each template (Product, FAQ, Article, Breadcrumb).",
        "med", "high",
    ),
    "eeat": (
        "Strengthen E-E-A-T signals",
        "Add author bylines + credentials, cite sources, show dates and trust signals.",
        "med", "high",
    ),
}


def _recommendations(checks: list[Check]) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for c in checks:
        if c.status == Status.passing or c.signal not in _REC_MAP:
            continue
        action, how_to, effort, impact = _REC_MAP[c.signal]
        priority = Priority.high if c.status == Status.fail else Priority.med
        recs.append(
            Recommendation(
                priority=priority, layer=Layer.seo, action=action,
                how_to=how_to, effort=effort, impact=impact,
            )
        )
    return recs


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    eeat_llm = ctx.llm if ctx.scope == "page" else None  # cost control: LLM only at page scope
    m = _metrics(ctx.client_pages, llm=eeat_llm)

    checks = [
        _rate_check(db, "title_length_max", "title_optimized", m["title_ok_rate"], weight=1.5),
        _rate_check(db, "meta_description_max", "meta_description", m["meta_ok_rate"]),
        _rate_check(db, "h1_count", "single_h1", m["single_h1_rate"]),
        _rate_check(db, "h1_count", "heading_structure", m["structure_rate"]),
        _rate_check(db, "word_count_min", "content_depth", m["content_depth_rate"], weight=1.5),
        _rate_check(db, "image_alt_coverage", "image_alt", m["alt_coverage"]),
        _rate_check(db, "structured_data", "open_graph", m["og_rate"], warn_at=0.8),
        _rate_check(
            db, "structured_data", "schema_markup", m["schema_rate"], warn_at=0.8, weight=1.5
        ),
        _rate_check(db, "structured_data", "eeat", m["eeat_score"], warn_at=0.8, weight=1.5),
    ]
    recs = maybe_enrich_recommendations(ctx.llm, _recommendations(checks))
    competitor_metrics = {
        name: _metrics(pages) for name, pages in ctx.competitor_pages.items()
    }
    delta = build_competitor_delta(m, competitor_metrics, DELTA_SIGNALS)

    return build_result(
        module=MODULE,
        scope=ctx.scope,
        target_url=ctx.target_url,
        checks=checks,
        recommendations=recs,
        competitor_delta=delta,
        generated_at=ctx.generated_at,
    )
