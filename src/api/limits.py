"""
Rate limits and a concurrency cap for report runs.

Every report costs several Claude calls (two with web search) plus dozens of
GitHub API calls, and POST /reports/run is open to anonymous visitors. These
limits bound what one caller — or many anonymous callers together — can spend.

State is in-process, which matches the single Railway instance this runs on.
Limits are configurable via env vars; defaults are conservative.
"""

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_HOUR = 3600
_DAY = 86400

ANON_PER_IP_PER_HOUR = int(os.environ.get("REPORT_LIMIT_ANON_PER_IP_HOUR", "3"))
ANON_GLOBAL_PER_HOUR = int(os.environ.get("REPORT_LIMIT_ANON_GLOBAL_HOUR", "30"))
USER_PER_DAY = int(os.environ.get("REPORT_LIMIT_USER_DAY", "20"))
MAX_CONCURRENT_REPORTS = int(os.environ.get("REPORT_MAX_CONCURRENT", "5"))


class SlidingWindowLimiter:
    """Allow at most `limit` hits per key within `window` seconds."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record a hit for `key`. Returns False (and records nothing) if over the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class ConcurrencyCap:
    """Counts in-flight report runs and refuses new ones past `limit`."""

    def __init__(self, limit: int):
        self.limit = limit
        self._active = 0
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        with self._lock:
            if self._active >= self.limit:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    def reset(self) -> None:
        with self._lock:
            self._active = 0


anon_ip_limiter = SlidingWindowLimiter(ANON_PER_IP_PER_HOUR, _HOUR)
anon_global_limiter = SlidingWindowLimiter(ANON_GLOBAL_PER_HOUR, _HOUR)
user_limiter = SlidingWindowLimiter(USER_PER_DAY, _DAY)
report_slots = ConcurrencyCap(MAX_CONCURRENT_REPORTS)


def client_ip(request: Request) -> str:
    """
    Best-effort client IP. Railway's proxy appends the address it saw to
    X-Forwarded-For, so the rightmost entry is the one a client can't forge.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _too_many(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


def check_report_quota(request: Request, user_id: str | None) -> None:
    """Raise 429 if this caller has used up their report quota."""
    if user_id:
        if not user_limiter.hit(user_id):
            raise _too_many(
                f"Daily report limit reached ({USER_PER_DAY} per day). Try again tomorrow."
            )
        return

    if not anon_ip_limiter.hit(client_ip(request)):
        raise _too_many(
            f"Report limit reached ({ANON_PER_IP_PER_HOUR} per hour). Sign in to run more reports."
        )
    if not anon_global_limiter.hit("global"):
        raise _too_many("Too many reports are being run right now. Sign in or try again later.")
