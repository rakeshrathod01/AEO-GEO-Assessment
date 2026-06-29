"""Project + competitor CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Competitor, Project
from app.models.serp import SerpQuery
from app.schemas.project import ProjectIn, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectIn, db: Session = Depends(get_db)) -> Project:
    project = Project(
        name=payload.name,
        target_url=payload.target_url,
        industry=payload.industry,
        notes=payload.notes,
        competitors=[Competitor(name=c.name, url=c.url) for c in payload.competitors],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return Response(status_code=204)


@router.get("/{project_id}/serp-queries")
def list_serp_queries(
    project_id: int, query_type: str | None = None, db: Session = Depends(get_db)
) -> list[dict]:
    """PAA + featured-snippet seeds captured during Keyword Universe (for Phase 5)."""
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    q = db.query(SerpQuery).filter(SerpQuery.project_id == project_id)
    if query_type:
        q = q.filter(SerpQuery.query_type == query_type)
    rows = q.order_by(SerpQuery.is_question.desc(), SerpQuery.volume.desc().nullslast()).all()
    return [
        {
            "id": r.id, "query": r.query, "query_type": r.query_type,
            "is_question": r.is_question, "volume": r.volume,
            "difficulty": r.difficulty, "ranking_url": r.ranking_url,
            "seed_keyword": r.seed_keyword,
        }
        for r in rows
    ]
