"""Ingestion API: three input modes + job progress (snapshot + SSE stream)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.crawl import (
    SOURCE_EXCEL,
    SOURCE_PASTE,
    SOURCE_SITEMAP,
    STATUS_DONE,
    STATUS_FAILED,
    CrawlJob,
    Page,
)
from app.models.project import Project
from app.schemas.ingest import JobOut, PageOut, PasteIngestIn, SitemapIngestIn
from app.services.ingest.dispatch import dispatch_ingestion
from app.services.ingest.urls import parse_excel_urls, parse_pasted_urls

router = APIRouter(tags=["ingest"])


def _require_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _default_competitor_specs(project: Project) -> list[dict]:
    """Mirror client paths onto each tracked competitor domain by default."""
    return [
        {"competitor_id": c.id, "base_url": c.url} for c in project.competitors
    ]


def _job_out(job: CrawlJob) -> JobOut:
    return JobOut(
        id=job.id,
        project_id=job.project_id,
        source_type=job.source_type,
        status=job.status,
        total=job.total,
        processed=job.processed,
        percent=job.percent,
        message=job.message,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _create_and_dispatch(db: Session, project_id: int, source_type: str, plan: dict) -> CrawlJob:
    job = CrawlJob(project_id=project_id, source_type=source_type, input_json=json.dumps(plan))
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    dispatch_ingestion(job_id)
    # Reload to reflect inline-run progress.
    db.expire_all()
    return db.get(CrawlJob, job_id)


@router.post("/projects/{project_id}/ingest/sitemap", response_model=JobOut, status_code=201)
def ingest_sitemap(
    project_id: int, payload: SitemapIngestIn, db: Session = Depends(get_db)
) -> JobOut:
    project = _require_project(db, project_id)
    competitors = (
        [c.model_dump() for c in payload.competitors]
        if payload.competitors
        else _default_competitor_specs(project)
    )
    plan = {
        "client": {"mode": "sitemap", "sitemap_url": payload.sitemap_url, "top_n": payload.top_n},
        "competitors": competitors,
    }
    return _job_out(_create_and_dispatch(db, project_id, SOURCE_SITEMAP, plan))


@router.post("/projects/{project_id}/ingest/paste", response_model=JobOut, status_code=201)
def ingest_paste(project_id: int, payload: PasteIngestIn, db: Session = Depends(get_db)) -> JobOut:
    project = _require_project(db, project_id)
    urls = parse_pasted_urls(payload.text)
    if not urls:
        raise HTTPException(status_code=422, detail="No valid URLs found in pasted text")
    competitors = (
        [c.model_dump() for c in payload.competitors]
        if payload.competitors
        else _default_competitor_specs(project)
    )
    plan = {
        "client": {"mode": "paste", "urls": urls, "top_n": payload.top_n},
        "competitors": competitors,
    }
    return _job_out(_create_and_dispatch(db, project_id, SOURCE_PASTE, plan))


@router.post("/projects/{project_id}/ingest/excel", response_model=JobOut, status_code=201)
async def ingest_excel(
    project_id: int,
    file: UploadFile = File(...),
    url_column: str | None = Form(default=None),
    top_n: int = Form(default=50),
    db: Session = Depends(get_db),
) -> JobOut:
    project = _require_project(db, project_id)
    content = await file.read()
    try:
        urls = parse_excel_urls(content, url_column=url_column)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not parse Excel: {exc}") from exc
    if not urls:
        raise HTTPException(status_code=422, detail="No valid URLs found in the spreadsheet")
    plan = {
        "client": {"mode": "excel", "urls": urls, "top_n": top_n},
        "competitors": _default_competitor_specs(project),
    }
    return _job_out(_create_and_dispatch(db, project_id, SOURCE_EXCEL, plan))


@router.get("/projects/{project_id}/jobs", response_model=list[JobOut])
def list_jobs(project_id: int, db: Session = Depends(get_db)) -> list[JobOut]:
    _require_project(db, project_id)
    jobs = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project_id)
        .order_by(CrawlJob.created_at.desc())
        .all()
    )
    return [_job_out(j) for j in jobs]


@router.get("/crawl/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(CrawlJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_out(job)


@router.get("/crawl/jobs/{job_id}/pages", response_model=list[PageOut])
def get_job_pages(
    job_id: int, competitors: bool | None = None, db: Session = Depends(get_db)
) -> list[PageOut]:
    job = db.get(CrawlJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    q = db.query(Page).filter(Page.crawl_job_id == job_id)
    if competitors is not None:
        q = q.filter(Page.is_competitor == competitors)
    pages = q.order_by(Page.is_competitor, Page.rank_score.desc().nullslast()).all()
    return [PageOut.model_validate(p, from_attributes=True) for p in pages]


@router.get("/crawl/jobs/{job_id}/stream")
async def stream_job(job_id: int) -> StreamingResponse:
    """Server-Sent Events stream of the Celery ingestion progress.

    Polls the job snapshot (which the worker/inline run updates) and emits each
    new progress event, then closes when the job reaches a terminal state.
    """

    async def event_gen():
        last_idx = 0
        # Bound the stream so a stuck job can't hold the connection forever.
        for _ in range(600):  # ~10 min at 1s cadence
            db = SessionLocal()
            try:
                job = db.get(CrawlJob, job_id)
                if job is None:
                    yield f"event: error\ndata: {json.dumps({'detail': 'job not found'})}\n\n"
                    return
                events = json.loads(job.events_json) if job.events_json else []
                for ev in events[last_idx:]:
                    yield f"data: {json.dumps(ev)}\n\n"
                last_idx = len(events)
                terminal = job.status in (STATUS_DONE, STATUS_FAILED)
            finally:
                db.close()
            if terminal:
                yield f"event: done\ndata: {json.dumps({'status': job.status})}\n\n"
                return
            await asyncio.sleep(1.0)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
