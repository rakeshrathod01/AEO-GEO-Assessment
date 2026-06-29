"""Industry benchmarks with cited sources.

Defaults are seeded once into ``benchmark_sources`` and reused everywhere — never
re-derived. Every benchmark carries a source so it is defensible in client decks.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.benchmark_source import BenchmarkSource

# metric -> (value, unit, source_name, source_url, year, notes)
DEFAULT_BENCHMARKS: dict[str, tuple] = {
    # On-page
    "title_length_max": (60, "chars", "Moz — Title Tag SEO Best Practices",
                          "https://moz.com/learn/seo/title-tag", 2024,
                          "Titles over ~60 chars are truncated in SERPs."),
    "title_length_min": (30, "chars", "Moz — Title Tag SEO Best Practices",
                         "https://moz.com/learn/seo/title-tag", 2024, None),
    "meta_description_max": (160, "chars", "Moz — Meta Description",
                             "https://moz.com/learn/seo/meta-description", 2024,
                             "Descriptions over ~155-160 chars are truncated."),
    "meta_description_min": (70, "chars", "Moz — Meta Description",
                             "https://moz.com/learn/seo/meta-description", 2024, None),
    "h1_count": (1, "count", "Google Search Central — Headings",
                 "https://developers.google.com/search/docs/appearance/structured-data", 2024,
                 "One primary H1 per page."),
    "word_count_min": (600, "words", "Backlinko — Content Length Study",
                       "https://backlinko.com/content-study", 2023,
                       "Longer, comprehensive content tends to rank better."),
    "image_alt_coverage": (1.0, "ratio", "W3C / Google — Image best practices",
                           "https://developers.google.com/search/docs/appearance/google-images",
                           2024, "All meaningful images should have alt text."),
    "text_to_html_ratio_min": (0.1, "ratio", "Common technical-SEO guidance",
                               "https://moz.com/learn/seo/on-page-factors", 2024, None),
    # Technical
    "https_required": (1.0, "bool", "Google Search Central — HTTPS",
                       "https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes",
                       2024, "HTTPS is a confirmed ranking signal."),
    "mobile_viewport": (1.0, "bool", "Google — Mobile-friendly / Mobile-first indexing",
                        "https://developers.google.com/search/mobile-sites", 2024, None),
    "indexable": (1.0, "bool", "Google Search Central — Robots meta",
                  "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                  2024, "Key pages must not be noindex."),
    "structured_data": (1.0, "bool", "Google Search Central — Structured data",
                        "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
                        2024, "Schema.org markup enables rich results / AEO."),
    "canonical_present": (1.0, "bool", "Google Search Central — Canonicalization",
                          "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
                          2024, None),
    # Internal linking
    "internal_links_per_page_min": (10, "links", "Ahrefs — Internal Links for SEO",
                                     "https://ahrefs.com/blog/internal-links-for-seo/", 2023,
                                     "Important pages should have ample internal links."),
    "orphan_rate_max": (0.0, "ratio", "Ahrefs — Orphan Pages",
                        "https://ahrefs.com/blog/orphan-pages/", 2023,
                        "Indexable pages should have at least one internal inbound link."),
    "max_click_depth": (3, "clicks", "Ahrefs / common crawl-depth guidance",
                        "https://ahrefs.com/blog/website-structure/", 2023,
                        "Key pages should be within ~3 clicks of the homepage."),
    # Backlinks
    "domain_rating_min": (40, "DR", "Ahrefs — Domain Rating",
                          "https://ahrefs.com/blog/domain-rating/", 2024,
                          "DR is a 0-100 strength score; ~40+ is competitive for many niches."),
    "dofollow_ratio_min": (0.5, "ratio", "Ahrefs — Dofollow vs Nofollow",
                           "https://ahrefs.com/blog/nofollow-links/", 2023,
                           "A healthy profile has a substantial share of dofollow links."),
    "referring_domains_min": (100, "domains", "Ahrefs — Referring Domains",
                              "https://ahrefs.com/blog/referring-domains/", 2024,
                              "Referring-domain count correlates with ranking ability."),
    # Keywords
    "top10_share_min": (0.3, "ratio", "Ahrefs — Organic Keywords / SERP CTR",
                        "https://ahrefs.com/blog/google-ctr-study/", 2023,
                        "A meaningful share of tracked keywords should rank in the top 10."),
    "striking_distance": (10, "position", "Common SEO practice — positions 4-10",
                          "https://ahrefs.com/blog/striking-distance-keywords/", 2023,
                          "Positions 4-10 are quick-win optimization targets."),
    # AEO (Answer Engine Optimization)
    "aeo_answer_length": (54, "words", "Backlinko — Featured Snippet study",
                          "https://backlinko.com/hub/seo/featured-snippets", 2023,
                          "Snippet-winning answers average ~40-60 words; lead with the answer."),
    "aeo_faq_schema": (1.0, "bool", "Google Search Central — FAQ structured data",
                       "https://developers.google.com/search/docs/appearance/structured-data/faqpage",
                       2024, "FAQ/QAPage markup powers PAA and rich results."),
    "aeo_question_headings": (0.3, "ratio", "Google — People Also Ask / question content",
                              "https://developers.google.com/search/docs/appearance/featured-snippets",
                              2024, "Question-led H2/H3 align content with PAA and AI Overviews."),
    "aeo_org_schema": (1.0, "bool", "Google Search Central — Organization structured data",
                       "https://developers.google.com/search/docs/appearance/structured-data/organization",
                       2024, "Organization/sameAs markup supports Knowledge Panel eligibility."),
    "aeo_speakable": (1.0, "bool", "Google Search Central — Speakable (voice)",
                      "https://developers.google.com/search/docs/appearance/structured-data/speakable",
                      2024, "Speakable markup flags voice-friendly answer passages."),
    "aeo_structure": (1.0, "bool", "Google — Content structure for rich results",
                      "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
                      2024, "Lists/tables and clear headings improve answer extractability."),
}


@dataclass
class Benchmark:
    metric: str
    value: float | None
    unit: str | None
    source: str  # citation string for the data contract's `source` field


def seed_default_benchmarks(db: Session) -> int:
    """Insert any missing default benchmarks (idempotent). Returns rows added."""
    added = 0
    for metric, (value, unit, name, url, year, notes) in DEFAULT_BENCHMARKS.items():
        exists = (
            db.query(BenchmarkSource)
            .filter(BenchmarkSource.metric == metric, BenchmarkSource.industry.is_(None))
            .first()
        )
        if exists:
            continue
        db.add(
            BenchmarkSource(
                metric=metric, industry=None, value=value, unit=unit,
                source_name=name, source_url=url, source_year=year, notes=notes,
            )
        )
        added += 1
    if added:
        db.commit()
    return added


def _citation(row: BenchmarkSource) -> str:
    bits = [row.source_name]
    if row.source_year:
        bits.append(f"({row.source_year})")
    return " ".join(bits)


def list_benchmarks(db: Session) -> list[dict]:
    """All benchmark rows (seeded first) for dashboard markers + source tooltips."""
    seed_default_benchmarks(db)
    rows = db.query(BenchmarkSource).order_by(BenchmarkSource.metric).all()
    return [
        {
            "metric": r.metric, "value": r.value, "unit": r.unit,
            "source": _citation(r), "source_name": r.source_name,
            "source_url": r.source_url, "source_year": r.source_year, "notes": r.notes,
        }
        for r in rows
    ]


def get_benchmark(db: Session, metric: str, industry: str | None = None) -> Benchmark | None:
    """Look up a benchmark, preferring an industry-specific row over the default."""
    seed_default_benchmarks(db)
    row = None
    if industry:
        row = (
            db.query(BenchmarkSource)
            .filter(BenchmarkSource.metric == metric, BenchmarkSource.industry == industry)
            .first()
        )
    if row is None:
        row = (
            db.query(BenchmarkSource)
            .filter(BenchmarkSource.metric == metric, BenchmarkSource.industry.is_(None))
            .first()
        )
    if row is None:
        return None
    return Benchmark(metric=metric, value=row.value, unit=row.unit, source=_citation(row))
