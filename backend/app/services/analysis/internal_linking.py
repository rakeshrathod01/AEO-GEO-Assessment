"""Module 3 — Internal Linking analyzer (site + page scope, with competitor_delta).

Derives an internal-link graph from the crawl (raw HTML) to assess orphan pages,
inbound/outbound link distribution, click depth, and links into money pages.
Competitor delta compares average internal links per page (from crawl signals).
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
from app.services.analysis.internal_graph import build_graph_from_pages
from app.services.analysis.signals import avg, page_signals
from app.services.benchmarks import get_benchmark

MODULE = "internal_linking"
DELTA_SIGNALS = ["avg_internal_links", "orphan_rate"]


def _avg_outbound_from_signals(pages: list[Page]) -> float:
    return avg([page_signals(p).get("internal_links") for p in pages])


def _max_depth(pages: list[Page]) -> int:
    depths = []
    for p in pages:
        path = p.url.split("//", 1)[-1]
        depths.append(path.count("/") - 1 if "/" in path else 0)
    return max(depths) if depths else 0


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    stats = build_graph_from_pages(ctx.client_pages)
    avg_internal = stats.avg_outbound or _avg_outbound_from_signals(ctx.client_pages)
    max_depth = _max_depth(ctx.client_pages)

    b_links = get_benchmark(db, "internal_links_per_page_min")
    b_orphan = get_benchmark(db, "orphan_rate_max")
    b_depth = get_benchmark(db, "max_click_depth")

    def status_min(value, minimum):
        if value >= minimum:
            return Status.passing
        return Status.warn if value >= minimum * 0.5 else Status.fail

    checks = [
        Check(
            signal="avg_internal_links", status=status_min(avg_internal, 10), weight=1.0,
            value=avg_internal, benchmark=b_links.value if b_links else 10,
            source=b_links.source if b_links else None,
            evidence=f"avg {avg_internal} internal links/page",
        ),
        Check(
            signal="orphan_pages",
            status=Status.passing if stats.orphan_rate == 0 else (
                Status.warn if stats.orphan_rate <= 0.1 else Status.fail
            ),
            weight=1.5, value=stats.orphan_rate, benchmark=b_orphan.value if b_orphan else 0.0,
            source=b_orphan.source if b_orphan else None,
            evidence=f"{len(stats.orphans)} orphan pages of {stats.page_count}",
        ),
        Check(
            signal="click_depth",
            status=Status.passing if max_depth <= 3 else (
                Status.warn if max_depth <= 5 else Status.fail
            ),
            weight=1.0, value=max_depth, benchmark=b_depth.value if b_depth else 3,
            source=b_depth.source if b_depth else None,
            evidence=f"max click depth {max_depth}",
        ),
        Check(
            signal="money_page_links",
            status=Status.passing if not stats.money_pages_orphaned else Status.fail,
            weight=1.5, value=len(stats.money_pages_orphaned),
            benchmark=0, source=b_orphan.source if b_orphan else None,
            evidence=f"{len(stats.money_pages_orphaned)} money pages with no internal links",
        ),
    ]

    recs: list[Recommendation] = []
    for c in checks:
        if c.status == Status.passing:
            continue
        if c.signal == "orphan_pages":
            recs.append(Recommendation(
                priority=Priority.high, layer=Layer.seo,
                action="Link to orphan pages",
                how_to="Add contextual internal links from relevant hubs to every orphan page.",
                effort="med", impact="high"))
        elif c.signal == "avg_internal_links":
            recs.append(Recommendation(
                priority=Priority.med, layer=Layer.seo,
                action="Increase internal linking density",
                how_to="Add contextual links so key pages have 10+ relevant internal links.",
                effort="med", impact="med"))
        elif c.signal == "click_depth":
            recs.append(Recommendation(
                priority=Priority.med, layer=Layer.seo,
                action="Reduce click depth of key pages",
                how_to="Surface deep pages via navigation/hub links to within ~3 clicks.",
                effort="med", impact="med"))
        elif c.signal == "money_page_links":
            recs.append(Recommendation(
                priority=Priority.high, layer=Layer.seo,
                action="Internally link to money pages",
                how_to="Add internal links to conversion pages from high-authority pages.",
                effort="low", impact="high"))
    recs = maybe_enrich_recommendations(ctx.llm, recs)

    client_metrics = {"avg_internal_links": avg_internal, "orphan_rate": stats.orphan_rate}
    competitor_metrics = {
        name: {
            "avg_internal_links": _avg_outbound_from_signals(pages),
            "orphan_rate": build_graph_from_pages(pages).orphan_rate,
        }
        for name, pages in ctx.competitor_pages.items()
    }
    delta = build_competitor_delta(client_metrics, competitor_metrics, DELTA_SIGNALS)

    return build_result(
        module=MODULE, scope=ctx.scope, target_url=ctx.target_url,
        checks=checks, recommendations=recs, competitor_delta=delta,
        generated_at=ctx.generated_at,
    )
