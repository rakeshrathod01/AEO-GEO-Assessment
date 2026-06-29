"""Module analysis + export endpoints (Excel / PDF)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, owned_project
from app.db.session import get_db
from app.models.tenant import Tenant
from app.modules_registry import get_module
from app.schemas.contract import ModuleResult, Scope
from app.services.analysis.runner import (
    AnalysisError,
    latest_run,
    result_from_run,
    run_module_analysis,
)
from app.services.exports.excel import build_excel
from app.services.exports.pdf import build_pdf

router = APIRouter(prefix="/projects/{project_id}/modules/{module_key}", tags=["analysis"])


def _module_title(module_key: str) -> str:
    meta = get_module(module_key)
    return meta.title if meta else module_key


@router.post("/analyze", response_model=ModuleResult)
def analyze(
    project_id: int,
    module_key: str,
    scope: Scope = Query(default=Scope.site),
    page_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ModuleResult:
    owned_project(db, project_id, tenant)
    try:
        return run_module_analysis(db, project_id, module_key, scope.value, page_id)
    except AnalysisError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _latest_or_409(db: Session, project_id: int, module_key: str, scope: str) -> dict:
    run = latest_run(db, project_id, module_key, scope)
    if run is None:
        raise HTTPException(
            status_code=409, detail="No analysis yet — run /analyze before exporting"
        )
    return result_from_run(run)


@router.get("/export.xlsx")
def export_excel(
    project_id: int,
    module_key: str,
    scope: Scope = Query(default=Scope.site),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Response:
    owned_project(db, project_id, tenant)
    result = _latest_or_409(db, project_id, module_key, scope.value)
    data = build_excel(result, _module_title(module_key))
    filename = f"{module_key}_{scope.value}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/report.pdf")
def export_pdf(
    project_id: int,
    module_key: str,
    scope: Scope = Query(default=Scope.site),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Response:
    owned_project(db, project_id, tenant)
    result = _latest_or_409(db, project_id, module_key, scope.value)
    data = build_pdf(result, _module_title(module_key))
    filename = f"{module_key}_{scope.value}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
