"""External-call cache helper.

Every external API call (Ahrefs, Firecrawl, LLM) should route through
:func:`get_or_set` so identical requests are served from the DB rather than
re-billed. Used from Phase 1 onward; defined here so the contract is stable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.models.api_cache import ApiCache


def make_cache_key(provider: str, endpoint: str, params: dict[str, Any] | None) -> str:
    payload = json.dumps(
        {"provider": provider, "endpoint": endpoint, "params": params or {}},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached(db: Session, cache_key: str) -> Any | None:
    row = db.query(ApiCache).filter(ApiCache.cache_key == cache_key).one_or_none()
    if row is None:
        return None
    if row.expires_at is not None:
        expires = row.expires_at
        # SQLite returns naive datetimes; assume UTC so the comparison is tz-safe.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < utcnow():
            db.delete(row)
            db.commit()
            return None
    return json.loads(row.response_body)


def set_cached(
    db: Session,
    *,
    cache_key: str,
    provider: str,
    endpoint: str,
    params: dict[str, Any] | None,
    response: Any,
    ttl_hours: int | None = None,
) -> None:
    ttl = settings.CACHE_TTL_HOURS if ttl_hours is None else ttl_hours
    expires = utcnow() + timedelta(hours=ttl) if ttl else None
    row = db.query(ApiCache).filter(ApiCache.cache_key == cache_key).one_or_none()
    body = json.dumps(response, default=str)
    if row is None:
        row = ApiCache(
            cache_key=cache_key,
            provider=provider,
            endpoint=endpoint,
            request_params=json.dumps(params or {}, default=str),
            response_body=body,
            expires_at=expires,
        )
        db.add(row)
    else:
        row.response_body = body
        row.expires_at = expires
    db.commit()


def get_or_set(
    db: Session,
    *,
    provider: str,
    endpoint: str,
    params: dict[str, Any] | None,
    fetch: Callable[[], Any],
    ttl_hours: int | None = None,
) -> Any:
    """Return a cached response or call ``fetch`` and cache it."""
    key = make_cache_key(provider, endpoint, params)
    cached = get_cached(db, key)
    if cached is not None:
        return cached
    fresh = fetch()
    set_cached(
        db,
        cache_key=key,
        provider=provider,
        endpoint=endpoint,
        params=params,
        response=fresh,
        ttl_hours=ttl_hours,
    )
    return fresh
