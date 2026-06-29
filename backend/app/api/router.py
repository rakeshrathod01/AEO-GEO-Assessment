"""Aggregate API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import analysis, health, ingest, modules, projects, settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(settings.router)
api_router.include_router(projects.router)
api_router.include_router(modules.router)
api_router.include_router(ingest.router)
api_router.include_router(analysis.router)
