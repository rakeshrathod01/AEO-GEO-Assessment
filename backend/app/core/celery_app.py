"""Celery application factory.

Tasks are registered from Phase 1 onward (crawler, Ahrefs pulls, AI analysis).
This scaffold wires the broker/backend so workers can start immediately.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "eclerx_assessment",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=60 * 30,  # 30 min hard cap per task
    worker_max_tasks_per_child=100,
)


@celery_app.task(name="health.ping")
def ping() -> str:
    """Trivial task used to verify worker connectivity."""
    return "pong"


@celery_app.task(name="ingest.run")
def run_ingestion_task(job_id: int) -> None:
    """Celery entrypoint for an ingestion run (imports lazily to avoid cycles)."""
    from app.services.ingest.pipeline import run_ingestion

    run_ingestion(job_id)
