"""Dispatch an ingestion job.

Strategy (local-first friendly):
  * ``INGEST_INLINE`` -> run synchronously in-process (default; no Redis needed).
  * otherwise enqueue on Celery; if the broker is unreachable, fall back to a
    daemon thread so local dev still works without a running worker.
"""

from __future__ import annotations

import threading

from app.core.config import settings
from app.services.ingest.pipeline import run_ingestion


def dispatch_ingestion(job_id: int) -> str:
    if settings.INGEST_INLINE:
        run_ingestion(job_id)
        return "inline"
    try:
        from app.core.celery_app import run_ingestion_task

        run_ingestion_task.delay(job_id)
        return "queued"
    except Exception:  # noqa: BLE001 - broker down; degrade to a background thread
        threading.Thread(target=run_ingestion, args=(job_id,), daemon=True).start()
        return "thread"
