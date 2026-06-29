"""Ahrefs MCP client.

Talks to the tenant's Ahrefs MCP server (URL stored encrypted in Settings as the
``ahrefs_mcp_url`` provider). Every pull:
  * uses a **trailing 6-month window** (``AHREFS_WINDOW_MONTHS``), and
  * is **cached** in ``api_cache`` (keyed incl. the window) so identical calls
    are not re-billed.

Graceful degradation: when no MCP URL is configured or the server is unreachable,
methods return ``None``/empty so analyzers fall back. The transport is a small
MCP-style ``tools/call`` POST; adjust ``_call_tool`` to match your MCP gateway.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.cache import get_or_set
from app.services.keys import get_api_key


def trailing_window(months: int | None = None, today: date | None = None) -> tuple[str, str]:
    """Return (date_from, date_to) ISO strings for a trailing N-month window."""
    months = settings.AHREFS_WINDOW_MONTHS if months is None else months
    end = today or date.today()
    y, m = end.year, end.month - months
    while m <= 0:
        m += 12
        y -= 1
    # Clamp day to a valid value for the start month (28 is always safe).
    start = date(y, m, min(end.day, 28))
    return start.isoformat(), end.isoformat()


@dataclass
class AhrefsClient:
    db: Session
    mcp_url: str | None = None
    _resolved: bool = False

    @classmethod
    def from_db(cls, db: Session, tenant_id: int | None = None) -> AhrefsClient:
        return cls(db=db, mcp_url=get_api_key(db, "ahrefs_mcp_url", tenant_id))

    @property
    def enabled(self) -> bool:
        return bool(self.mcp_url)

    # --- transport -----------------------------------------------------------
    def _call_tool(self, tool: str, arguments: dict):
        """POST an MCP tools/call to the gateway. Returns parsed JSON or raises."""
        import httpx

        payload = {"method": "tools/call", "params": {"name": tool, "arguments": arguments}}
        resp = httpx.post(
            self.mcp_url.rstrip("/") + "/mcp",
            json=payload,
            timeout=settings.FETCH_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        body = resp.json()
        # MCP responses wrap results under "result"; tolerate flat bodies too.
        return body.get("result", body)

    def _cached_tool(self, tool: str, arguments: dict, default):
        if not self.enabled:
            return default
        date_from, date_to = trailing_window()
        params = {**arguments, "date_from": date_from, "date_to": date_to, "tool": tool}

        def fetch():
            return self._call_tool(tool, {**arguments, "date_from": date_from, "date_to": date_to})

        try:
            return get_or_set(
                self.db, provider="ahrefs", endpoint=tool, params=params, fetch=fetch
            )
        except Exception:  # noqa: BLE001 - unreachable MCP -> deterministic fallback
            return default

    # --- backlinks (module 4) ------------------------------------------------
    def backlinks_stats(self, target: str) -> dict | None:
        """Domain rating, referring domains, backlinks, dofollow ratio, etc."""
        return self._cached_tool("backlinks_stats", {"target": target}, None)

    def referring_domains(self, target: str, limit: int = 100) -> list[dict]:
        return self._cached_tool(
            "referring_domains", {"target": target, "limit": limit}, []
        ) or []

    def anchors(self, target: str, limit: int = 50) -> list[dict]:
        return self._cached_tool("anchors", {"target": target, "limit": limit}, []) or []

    # --- keywords (module 5) -------------------------------------------------
    def organic_keywords(self, target: str, limit: int = 1000) -> list[dict]:
        """Organic keywords with volume, position, traffic, SERP features."""
        return self._cached_tool(
            "organic_keywords", {"target": target, "limit": limit}, []
        ) or []

    # --- internal links (module 3 enrichment) --------------------------------
    def best_by_internal_links(self, target: str, limit: int = 100) -> list[dict]:
        return self._cached_tool(
            "best_by_internal_links", {"target": target, "limit": limit}, []
        ) or []


def build_ahrefs_client(db: Session, tenant_id: int | None = None) -> AhrefsClient:
    return AhrefsClient.from_db(db, tenant_id)
