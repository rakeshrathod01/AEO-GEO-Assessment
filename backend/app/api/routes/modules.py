"""Module registry endpoints.

Phase 0 exposes the registry and a placeholder analysis endpoint that returns a
valid (empty) :class:`ModuleResult`, so the frontend can be wired before the
real analyzers land in later phases.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.modules_registry import MODULES, get_module
from app.schemas.contract import ModuleResult, Scope, Status

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("")
def list_modules() -> list[dict]:
    return [m.model_dump() for m in MODULES]


@router.post("/{module_key}/analyze", response_model=ModuleResult)
def analyze(module_key: str, target_url: str, scope: Scope = Scope.page) -> ModuleResult:
    """Placeholder analyzer. Real implementations arrive in each module's phase."""
    meta = get_module(module_key)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown module '{module_key}'")
    return ModuleResult(
        scope=scope,
        target_url=target_url,
        score=0,
        status=Status.warn,
        module=module_key,
        findings=[],
        recommendations=[],
        competitor_delta=[],
    )
