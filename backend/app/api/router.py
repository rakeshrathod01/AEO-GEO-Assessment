"""Aggregate API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    analysis,
    auth,
    health,
    ingest,
    leadership,
    modules,
    projects,
    settings,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(projects.router)
api_router.include_router(modules.router)
api_router.include_router(ingest.router)
api_router.include_router(analysis.router)
api_router.include_router(leadership.router)
