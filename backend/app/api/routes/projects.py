"""Project + competitor CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Competitor, Project
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
