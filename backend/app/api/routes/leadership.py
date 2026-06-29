"""Leadership Dashboard (module 9) endpoints: synthesis + master exports."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.analysis import AnalysisRun
from app.models.crawl import STATUS_DONE, CrawlJob, Page
from app.models.project import Project
from app.schemas.contract import Scope
from app.schemas.leadership import LeadershipReport
from app.services.analysis.leadership import MODULE, run_leadership
from app.services.analysis.runner import AnalysisError
from app.services.exports.master import build_master_excel
from app.services.exports.pdf import build_leadership_pdf

router = APIRouter(prefix="/projects/{project_id}", tags=["leadership"])


@router.post("/leadership", response_model=LeadershipReport)
def leadership(
    project_id: int,
    scope: Scope = Query(default=Scope.site),
    page_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> LeadershipReport:
    try:
        return run_leadership(db, project_id, scope.value, page_id)
    except AnalysisError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _latest_report(db: Session, project_id: int, scope: str) -> dict:
    run = (
        db.query(AnalysisRun)
        .filter(
            AnalysisRun.project_id == project_id,
            AnalysisRun.module == MODULE,
            AnalysisRun.scope == scope,
        )
        .order_by(AnalysisRun.created_at.desc())
        .first()
    )
    if run is None or not run.result_json:
        raise HTTPException(
            status_code=409, detail="No leadership synthesis yet — run it before exporting"
        )
    return json.loads(run.result_json)


@router.get("/leadership/export.xlsx")
def export_master_excel(
    project_id: int, scope: Scope = Query(default=Scope.site), db: Session = Depends(get_db)
) -> Response:
    data = build_master_excel(_latest_report(db, project_id, scope.value))
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="leadership_master.xlsx"'},
    )


@router.get("/leadership/report.pdf")
def export_leadership_pdf(
    project_id: int, scope: Scope = Query(default=Scope.site), db: Session = Depends(get_db)
) -> Response:
    data = build_leadership_pdf(_latest_report(db, project_id, scope.value))
    return Response(
        content=data, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="leadership_summary.pdf"'},
    )


@router.get("/pages")
def list_project_pages(project_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Client pages from the latest completed crawl — powers the page-selector."""
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    job = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project_id, CrawlJob.status == STATUS_DONE)
        .order_by(CrawlJob.created_at.desc())
        .first()
    )
    if job is None:
        return []
    pages = (
        db.query(Page)
        .filter(Page.crawl_job_id == job.id, Page.is_competitor.is_(False))
        .order_by(Page.rank_score.desc().nullslast())
        .all()
    )
    return [{"id": p.id, "url": p.url, "title": p.title} for p in pages]
