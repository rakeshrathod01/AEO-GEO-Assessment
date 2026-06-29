"""Resolve a decrypted BYO API key for a provider, isolated per tenant."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.setting import ApiKey


def get_api_key(db: Session, provider: str, tenant_id: int | None = None) -> str | None:
    """Return the decrypted key for (tenant, provider), or None.

    When ``tenant_id`` is None the lookup is not tenant-filtered (used by direct
    unit tests / single-tenant local flows).
    """
    q = db.query(ApiKey).filter(ApiKey.provider == provider)
    if tenant_id is not None:
        q = q.filter(ApiKey.tenant_id == tenant_id)
    row = q.first()
    return row.value if row else None
