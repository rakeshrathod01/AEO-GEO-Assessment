"""Project / competitor request + response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompetitorIn(BaseModel):
    name: str
    url: str


class CompetitorOut(CompetitorIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProjectIn(BaseModel):
    name: str
    target_url: str
    industry: str | None = None
    notes: str | None = None
    competitors: list[CompetitorIn] = []


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    target_url: str
    industry: str | None = None
    notes: str | None = None
    competitors: list[CompetitorOut] = []
    created_at: datetime
    updated_at: datetime
