"""API-key / config (BYO) request/response schemas.

Secrets are never returned in plaintext — only a masked preview. URL-kind config
values (e.g. the Ahrefs MCP URL) are returned in full since they are not secrets.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProviderOut(BaseModel):
    key: str
    label: str
    kind: str  # secret | url
    required: bool
    group: str
    help: str | None = None
    configured: bool = False


class ApiKeyIn(BaseModel):
    provider: str
    value: str
    label: str | None = None


class ApiKeyOut(BaseModel):
    id: int
    provider: str
    kind: str
    label: str | None = None
    masked_value: str
    # Populated only for non-secret (url) kinds.
    value: str | None = None
    created_at: datetime
    updated_at: datetime
