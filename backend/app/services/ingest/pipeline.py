"""Ingestion pipeline orchestrator.

Resolves URLs (sitemap / Excel / paste), ranks + selects the top-N client pages,
crawls them (Firecrawl -> Playwright-stealth fallback), extracts cleaned text +
signals to the DB and raw HTML to disk, then does the same for each competitor on
pages matched comparable to the client's set — emitting progress throughout.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.crawl import (
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_RUNNING,
    CrawlJob,
    Page,
)
from app.models.project import Project
from app.services.ingest.competitor_match import match_by_similarity, mirror_client_paths
from app.services.ingest.extract import extract
from app.services.ingest.fetcher import Fetcher, build_default_fetcher
from app.services.ingest.progress import ProgressPublisher
from app.services.ingest.ranking import select_top
from app.services.ingest.sitemap import fetch_sitemap_entries
from app.services.ingest.storage import content_hash, save_raw_html
from app.services.keys import get_api_key


def _firecrawl_key(db: Session, tenant_id: int | None = None) -> str | None:
    return get_api_key(db, "firecrawl", tenant_id)


def _resolve_ranked(spec: dict, top_n: int):
    """Return the top-N RankedUrl entries for a client/competitor spec."""
    priority_by_url: dict[str, float] = {}
    if spec.get("sitemap_url"):
        entries = fetch_sitemap_entries(spec["sitemap_url"])
        urls = [e.url for e in entries]
        priority_by_url = {e.url: e.priority for e in entries if e.priority is not None}
    else:
        urls = spec.get("urls") or []
    return select_top(urls, n=top_n, priority_by_url=priority_by_url)


def _crawl_one(
    db: Session,
    job: CrawlJob,
    fetcher: Fetcher,
    url: str,
    *,
    is_competitor: bool,
    competitor_id: int | None = None,
    matched_page_id: int | None = None,
    rank_score: float | None = None,
    rank_reasons: dict | None = None,
) -> Page:
    result = fetcher.fetch(url)
    page = Page(
        project_id=job.project_id,
        crawl_job_id=job.id,
        competitor_id=competitor_id,
        matched_page_id=matched_page_id,
        url=url,
        is_competitor=is_competitor,
        selected=True,
        rank_score=rank_score,
        rank_reasons=json.dumps(rank_reasons) if rank_reasons else None,
        fetch_method=result.method,
        http_status=result.status_code,
        fetch_ok=result.success,
        fetch_error=result.error,
    )
    if result.success and result.html:
        page.raw_html_path = save_raw_html(job.project_id, job.id, url, result.html)
        ex = extract(result.html, url, http_status=result.status_code)
        page.cleaned_text = ex.cleaned_text
        page.title = ex.title
        page.meta_description = ex.meta_description
        page.word_count = ex.word_count
        page.signals_json = json.dumps(ex.signals, default=str)
        page.content_hash = content_hash(ex.cleaned_text)
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def run_ingestion(job_id: int, fetcher: Fetcher | None = None) -> None:
    """Execute the full ingestion run for a job (used by the Celery task / inline)."""
    db = SessionLocal()
    try:
        job = db.get(CrawlJob, job_id)
        if job is None:
            return
        plan = json.loads(job.input_json or "{}")
        client_spec = plan.get("client", {})
        competitor_specs = plan.get("competitors", [])
        top_n = int(client_spec.get("top_n") or settings.TOP_N_PAGES)

        pub = ProgressPublisher(db, job)
        if fetcher is None:
            project = db.get(Project, job.project_id)
            tenant_id = project.tenant_id if project else None
            fetcher = build_default_fetcher(_firecrawl_key(db, tenant_id))

        pub.emit("Resolving client URLs…", processed=0, total=0, status=STATUS_RUNNING)
        ranked = _resolve_ranked(client_spec, top_n)
        client_urls = [r.url for r in ranked]
        ranked_by_url = {r.url: r for r in ranked}

        # Pre-resolve competitor comparable sets so we can compute an accurate total.
        comp_plans: list[dict] = []
        for cspec in competitor_specs:
            if cspec.get("sitemap_url") or cspec.get("urls"):
                comp_urls = [r.url for r in _resolve_ranked(cspec, top_n)]
                pairs = match_by_similarity(client_urls, comp_urls)
                matches = [(m.client_url, m.competitor_url) for m in pairs]
            else:
                base = cspec.get("base_url") or cspec.get("url") or ""
                matches = [
                    (m.client_url, m.competitor_url)
                    for m in mirror_client_paths(client_urls, base)
                ]
            comp_plans.append({"competitor_id": cspec.get("competitor_id"), "matches": matches})

        total = len(client_urls) + sum(len(cp["matches"]) for cp in comp_plans)
        processed = 0
        pub.emit(
            f"Selected {len(client_urls)} client pages + "
            f"{total - len(client_urls)} competitor pages.",
            processed=0,
            total=total,
        )

        # --- Client pages ---
        client_page_by_url: dict[str, int] = {}
        for url in client_urls:
            r = ranked_by_url.get(url)
            page = _crawl_one(
                db, job, fetcher, url,
                is_competitor=False,
                rank_score=r.score if r else None,
                rank_reasons=r.reasons if r else None,
            )
            client_page_by_url[url] = page.id
            processed += 1
            pub.emit(
                f"Crawled client page {processed}/{total}: {url}",
                processed=processed,
                extra={"page_id": page.id, "method": page.fetch_method, "ok": page.fetch_ok},
            )

        # --- Competitor pages (comparable to client pages) ---
        for cp in comp_plans:
            for client_url, comp_url in cp["matches"]:
                page = _crawl_one(
                    db, job, fetcher, comp_url,
                    is_competitor=True,
                    competitor_id=cp["competitor_id"],
                    matched_page_id=client_page_by_url.get(client_url),
                )
                processed += 1
                pub.emit(
                    f"Crawled competitor page {processed}/{total}: {comp_url}",
                    processed=processed,
                    extra={"page_id": page.id, "method": page.fetch_method, "ok": page.fetch_ok},
                )

        pub.emit("Ingestion complete.", processed=processed, total=total, status=STATUS_DONE)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(CrawlJob, job_id)
        if job is not None:
            job.status = STATUS_FAILED
            job.error = str(exc)
            job.message = f"Failed: {exc}"[:512]
            db.add(job)
            db.commit()
        raise
    finally:
        db.close()
