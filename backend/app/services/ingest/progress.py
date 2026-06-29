"""Celery progress stream.

The pipeline reports progress through a :class:`ProgressPublisher` which:
  * writes a snapshot (processed/total/message/events) onto the CrawlJob row, and
  * best-effort publishes each event to a Redis channel ``crawl:<job_id>``.

The SSE endpoint can tail Redis when available and otherwise polls the DB
snapshot, so progress streams in both Celery-worker and inline modes.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.crawl import CrawlJob

MAX_EVENTS = 200


def channel_for(job_id: int) -> str:
    return f"crawl:{job_id}"


class ProgressPublisher:
    def __init__(self, db: Session, job: CrawlJob):
        self.db = db
        self.job = job
        self._events: list[dict] = []
        if job.events_json:
            try:
                self._events = json.loads(job.events_json)
            except json.JSONDecodeError:
                self._events = []
        self._redis = self._connect_redis()

    @staticmethod
    def _connect_redis():
        try:
            import redis  # lazy

            client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
            client.ping()
            return client
        except Exception:  # noqa: BLE001 - Redis optional in local-first mode
            return None

    def emit(
        self,
        message: str,
        *,
        processed: int | None = None,
        total: int | None = None,
        status: str | None = None,
        extra: dict | None = None,
    ) -> None:
        if processed is not None:
            self.job.processed = processed
        if total is not None:
            self.job.total = total
        if status is not None:
            self.job.status = status
        self.job.message = message[:512]

        event = {
            "message": message,
            "processed": self.job.processed,
            "total": self.job.total,
            "percent": self.job.percent,
            "status": self.job.status,
        }
        if extra:
            event.update(extra)
        self._events.append(event)
        self._events = self._events[-MAX_EVENTS:]
        self.job.events_json = json.dumps(self._events)
        self.db.add(self.job)
        self.db.commit()

        if self._redis is not None:
            try:
                self._redis.publish(channel_for(self.job.id), json.dumps(event))
            except Exception:  # noqa: BLE001
                pass
