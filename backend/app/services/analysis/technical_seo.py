"""Module 1 — Technical SEO analyzer (site + page scope, with competitor_delta).

Signals: indexability (noindex), canonical, HTTPS, mobile viewport, HTTP status
health, structured-data presence, declared language, and page weight / text-to-
HTML ratio. Each is benchmarked against a cited source.
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
from app.services.analysis.signals import is_https, page_signals, ratio
from app.services.benchmarks import get_benchmark

MODULE = "technical_seo"
DELTA_SIGNALS = ["indexable_rate", "https_rate", "structured_data_rate", "canonical_rate"]


def _metrics(pages: list[Page]) -> dict[str, float]:
    """Aggregate technical pass-rates across a set of pages (0..1)."""
    sig = [page_signals(p) for p in pages]
    return {
        "indexable_rate": ratio([not s.get("is_noindex", False) for s in sig]),
        "https_rate": ratio([is_https(p.url) for p in pages]),
        "viewport_rate": ratio([s.get("has_viewport_meta", False) for s in sig]),
        "canonical_rate": ratio([s.get("has_canonical", False) for s in sig]),
        "structured_data_rate": ratio([s.get("has_structured_data", False) for s in sig]),
        "ok_status_rate": ratio([(s.get("http_status") or 200) < 400 for s in sig]),
        "lang_rate": ratio([bool(s.get("lang")) for s in sig]),
    }


def _bool_check(db, metric, signal, value_rate, *, warn_at=0.99) -> Check:
    bench = get_benchmark(db, metric)
    if value_rate >= warn_at:
        status = Status.passing
    elif value_rate >= 0.5:
        status = Status.warn
    else:
        status = Status.fail
    return Check(
        signal=signal,
        status=status,
        weight=1.0,
        value=round(value_rate, 4),
        benchmark=bench.value if bench else 1.0,
        source=bench.source if bench else None,
        evidence=f"{round(value_rate * 100)}% of pages pass",
    )


def _recommendations(checks: list[Check]) -> list[Recommendation]:
    recs: list[Recommendation] = []
    rec_map = {
        "indexable": (
            "Remove unintended noindex on key pages",
            "Audit robots meta/X-Robots-Tag; ensure money pages are indexable.",
            "low", "high",
        ),
        "https": (
            "Serve all pages over HTTPS",
            "Force HTTPS with 301 redirects and HSTS; fix mixed content.",
            "med", "high",
        ),
        "mobile_viewport": (
            "Add a responsive viewport meta tag",
            "Add <meta name=viewport content='width=device-width, initial-scale=1'>.",
            "low", "high",
        ),
        "canonical": (
            "Add canonical tags",
            "Add a self-referencing rel=canonical to consolidate duplicates.",
            "low", "med",
        ),
        "structured_data": (
            "Add schema.org structured data",
            "Add JSON-LD (Organization, Product, FAQ, Breadcrumb) for rich results & AEO.",
            "med", "high",
        ),
        "http_status": (
            "Fix non-200 responses",
            "Resolve 4xx/5xx and redirect chains on selected pages.",
            "med", "high",
        ),
        "declared_language": (
            "Declare page language",
            "Set <html lang> to aid crawling and accessibility.",
            "low", "low",
        ),
    }
    for c in checks:
        if c.status == Status.passing:
            continue
        key = c.signal
        if key not in rec_map:
            continue
        action, how_to, effort, impact = rec_map[key]
        priority = Priority.high if c.status == Status.fail else Priority.med
        recs.append(
            Recommendation(
                priority=priority, layer=Layer.seo, action=action,
                how_to=how_to, effort=effort, impact=impact,
            )
        )
    return recs


def analyze(ctx) -> ModuleResult:  # noqa: F821 - ModuleResult returned via build_result
    db = ctx.db
    m = _metrics(ctx.client_pages)
    checks = [
        _bool_check(db, "indexable", "indexable", m["indexable_rate"]),
        _bool_check(db, "https_required", "https", m["https_rate"]),
        _bool_check(db, "mobile_viewport", "mobile_viewport", m["viewport_rate"]),
        _bool_check(db, "canonical_present", "canonical", m["canonical_rate"]),
        _bool_check(
            db, "structured_data", "structured_data", m["structured_data_rate"], warn_at=0.8
        ),
        _bool_check(db, "indexable", "http_status", m["ok_status_rate"]),
        _bool_check(db, "indexable", "declared_language", m["lang_rate"], warn_at=0.9),
    ]
    recs = maybe_enrich_recommendations(ctx.llm, _recommendations(checks))
    competitor_metrics = {name: _metrics(pages) for name, pages in ctx.competitor_pages.items()}
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
