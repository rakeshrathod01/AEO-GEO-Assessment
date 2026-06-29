"""API-key (BYO) request/response schemas. Plaintext is never returned."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ApiKeyIn(BaseModel):
    provider: str  # anthropic | firecrawl | ahrefs | ...
    value: str
    label: str | None = None


class ApiKeyOut(BaseModel):
    id: int
    provider: str
    label: str | None = None
    masked_value: str
    created_at: datetime
    updated_at: datetime
