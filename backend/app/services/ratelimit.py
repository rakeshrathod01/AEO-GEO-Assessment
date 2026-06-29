"""Per-provider client-side rate limiting for outbound external calls.

A process-global, thread-safe min-interval limiter throttles calls per provider
key (ahrefs, firecrawl, anthropic, geo:*) so we never hammer paid APIs. Applied
at the cached-call choke point (only on cache misses). Set the rate to 0 to
disable (used in tests).
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self):
        self._next_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str, rate_per_sec: float, *, sleep=time.sleep) -> float:
        """Block until ``key`` is allowed to fire. Returns the seconds waited."""
        if rate_per_sec <= 0:
            return 0.0
        interval = 1.0 / rate_per_sec
        with self._lock:
            now = time.monotonic()
            scheduled = max(now, self._next_at.get(key, 0.0))
            wait = scheduled - now
            self._next_at[key] = scheduled + interval
        if wait > 0:
            sleep(wait)
        return wait


# Process-global limiter shared across all external clients.
limiter = RateLimiter()
