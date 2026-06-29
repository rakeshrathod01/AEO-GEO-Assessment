"""Anthropic client with model tiering, prompt caching and DB response caching.

Design goals:
  * BYO key — the Anthropic key comes from the encrypted Settings store, never code.
  * Cost control — Haiku for extraction/classification, Sonnet for analysis;
    static system blocks are sent with ``cache_control`` for prompt caching, and
    every call is cached in ``api_cache`` keyed by (model, system, user).
  * Graceful degradation — when no key is configured or the SDK/network fails,
    calls return ``None`` so analyzers fall back to deterministic logic. This
    keeps the whole platform runnable (and testable) without an API key.
"""

from __future__ import annotations

import json
from enum import Enum

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.setting import ApiKey
from app.services.cache import get_or_set


class Tier(str, Enum):
    extract = "haiku"   # HTML/text extraction, schema detection, classification
    analyze = "sonnet"  # per-module analysis + recommendations
    synthesis = "opus"  # leadership synthesis only


def _model_for(tier: Tier) -> str:
    return {
        Tier.extract: settings.MODEL_HAIKU,
        Tier.analyze: settings.MODEL_SONNET,
        Tier.synthesis: settings.MODEL_OPUS,
    }[tier]


class LLMClient:
    """Thin wrapper. ``enabled`` is False when no Anthropic key is configured."""

    def __init__(self, db: Session):
        self.db = db
        row = db.query(ApiKey).filter(ApiKey.provider == "anthropic").one_or_none()
        self._api_key = row.value if row else None

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def _call(self, tier: Tier, system: str, user: str, max_tokens: int | None) -> str | None:
        if not self.enabled:
            return None
        model = _model_for(tier)
        params = {
            "model": model,
            "system": system,
            "user": user,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        }

        def fetch():
            from anthropic import Anthropic  # lazy import

            client = Anthropic(api_key=self._api_key)
            resp = client.messages.create(
                model=model,
                max_tokens=params["max_tokens"],
                system=[
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ],
                messages=[{"role": "user", "content": user}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")

        try:
            # Cache by (model, system, user) so identical prompts are not re-billed.
            return get_or_set(
                self.db, provider="anthropic", endpoint=model, params=params, fetch=fetch
            )
        except Exception:  # noqa: BLE001 - network/SDK failure -> deterministic fallback
            return None

    def analyze_text(self, system: str, user: str, max_tokens: int | None = None) -> str | None:
        """Sonnet-tier free-text analysis (e.g. recommendation how-to prose)."""
        return self._call(Tier.analyze, system, user, max_tokens)

    def extract_json(
        self, system: str, user: str, max_tokens: int | None = None
    ) -> dict | None:
        """Haiku-tier structured extraction. Returns parsed JSON or None."""
        raw = self._call(Tier.extract, system, user, max_tokens)
        if not raw:
            return None
        raw = raw.strip()
        # Tolerate fenced code blocks.
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[raw.find("{") :] if "{" in raw else raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("{"), raw.rfind("}")
            if 0 <= start < end:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None
