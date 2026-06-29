"""Health + readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": __version__,
        "env": settings.APP_ENV,
        "database": "sqlite" if settings.is_sqlite else "postgres",
    }


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
