"""Helpers for reading and aggregating extracted Page signals."""

from __future__ import annotations

import json
from statistics import mean
from urllib.parse import urlparse

from app.models.crawl import Page


def page_signals(page: Page) -> dict:
    if not page.signals_json:
        return {}
    try:
        return json.loads(page.signals_json)
    except json.JSONDecodeError:
        return {}


def is_https(url: str) -> bool:
    return urlparse(url).scheme == "https"


def ratio(values: list[bool]) -> float:
    """Fraction of True values (0..1); 0 for an empty list."""
    return round(sum(1 for v in values if v) / len(values), 4) if values else 0.0


def avg(values: list[float | int | None]) -> float:
    nums = [float(v) for v in values if v is not None]
    return round(mean(nums), 2) if nums else 0.0


def pct(n: float) -> str:
    return f"{round(n * 100)}%"
