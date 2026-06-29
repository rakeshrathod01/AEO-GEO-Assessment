"""Gather crawl data, run a module analyzer, and persist the AnalysisRun."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.analysis import AnalysisRun
from app.models.crawl import STATUS_DONE, CrawlJob, Page
from app.models.project import Competitor, Project
from app.schemas.contract import ModuleResult
from app.services.ahrefs.client import AhrefsClient, build_ahrefs_client
from app.services.analysis.registry import get_analyzer
from app.services.geo.providers import build_providers
from app.services.llm.client import LLMClient


class AnalysisError(Exception):
    """Raised for recoverable analysis problems (mapped to 4xx by the API)."""


@dataclass
class AnalysisContext:
    db: Session
    scope: str  # site | page
    target_url: str
    client_pages: list[Page]
    competitor_pages: dict[str, list[Page]] = field(default_factory=dict)
    # Ahrefs target per competitor (site URL at site scope; matched page URL at page scope).
    competitor_targets: dict[str, str] = field(default_factory=dict)
    project_id: int | None = None
    llm: LLMClient | None = None
    ahrefs: AhrefsClient | None = None
    geo_providers: list = field(default_factory=list)
    generated_at: str | None = None


def _latest_done_job(db: Session, project_id: int) -> CrawlJob | None:
    return (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project_id, CrawlJob.status == STATUS_DONE)
        .order_by(CrawlJob.created_at.desc())
        .first()
    )


def run_module_analysis(
    db: Session, project_id: int, module_key: str, scope: str, page_id: int | None = None
) -> ModuleResult:
    project = db.get(Project, project_id)
    if project is None:
        raise AnalysisError("Project not found")

    analyzer = get_analyzer(module_key)
    if analyzer is None:
        raise AnalysisError(f"Module '{module_key}' has no analyzer yet")

    job = _latest_done_job(db, project_id)
    if job is None:
        raise AnalysisError("No completed crawl for this project — run ingestion first")

    client_q = (
        db.query(Page)
        .filter(
            Page.crawl_job_id == job.id,
            Page.is_competitor.is_(False),
            Page.fetch_ok.is_(True),
        )
        .order_by(Page.rank_score.desc().nullslast())
    )
    client_pages = client_q.all()
    if not client_pages:
        raise AnalysisError("No successfully crawled client pages to analyze")

    comp_rows = db.query(Competitor).filter(Competitor.project_id == project_id).all()
    comp_name = {c.id: c.name for c in comp_rows}
    comp_site_url = {c.name: c.url for c in comp_rows}

    if scope == "page":
        page = db.get(Page, page_id) if page_id else client_pages[0]
        if page is None or page.crawl_job_id != job.id or page.is_competitor:
            raise AnalysisError("Invalid page_id for this project's latest crawl")
        client_pages = [page]
        target_url = page.url
        comp_pages = (
            db.query(Page)
            .filter(
                Page.crawl_job_id == job.id,
                Page.is_competitor.is_(True),
                Page.matched_page_id == page.id,
                Page.fetch_ok.is_(True),
            )
            .all()
        )
    else:
        target_url = project.target_url
        comp_pages = (
            db.query(Page)
            .filter(
                Page.crawl_job_id == job.id,
                Page.is_competitor.is_(True),
                Page.fetch_ok.is_(True),
            )
            .all()
        )

    competitor_pages: dict[str, list[Page]] = {}
    for p in comp_pages:
        name = comp_name.get(p.competitor_id, f"Competitor {p.competitor_id}")
        competitor_pages.setdefault(name, []).append(p)

    # Ahrefs target per competitor: matched page URL at page scope, else site URL.
    competitor_targets: dict[str, str] = {}
    for name, site_url in comp_site_url.items():
        if scope == "page" and competitor_pages.get(name):
            competitor_targets[name] = competitor_pages[name][0].url
        else:
            competitor_targets[name] = site_url

    ctx = AnalysisContext(
        db=db,
        scope=scope,
        target_url=target_url,
        client_pages=client_pages,
        competitor_pages=competitor_pages,
        competitor_targets=competitor_targets,
        project_id=project_id,
        llm=LLMClient(db, project.tenant_id),
        ahrefs=build_ahrefs_client(db, project.tenant_id),
        geo_providers=build_providers(db, project.tenant_id),
        generated_at=utcnow().isoformat(),
    )
    result = analyzer(ctx)

    run = AnalysisRun(
        project_id=project_id,
        module=module_key,
        scope=scope,
        target_url=target_url,
        score=result.score,
        status=result.status.value,
        result_json=result.model_dump_json(),
    )
    db.add(run)
    db.commit()
    return result


def latest_run(db: Session, project_id: int, module_key: str, scope: str) -> AnalysisRun | None:
    return (
        db.query(AnalysisRun)
        .filter(
            AnalysisRun.project_id == project_id,
            AnalysisRun.module == module_key,
            AnalysisRun.scope == scope,
        )
        .order_by(AnalysisRun.created_at.desc())
        .first()
    )


def result_from_run(run: AnalysisRun) -> dict:
    return json.loads(run.result_json) if run.result_json else {}
