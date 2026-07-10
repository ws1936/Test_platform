"""In-memory rate limiter for authentication endpoints.

This is intentionally simple: a sliding window of failed attempts per
key (e.g. email, IP, or both). For multi-instance deployments the
state MUST be moved to Redis (see ``AI_RULES.md`` §4.4).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque


class SlidingWindowLimiter:
    """Track the count of events per key within a time window.

    After ``max_attempts`` events in ``window_seconds`` the key is
    considered locked for ``lockout_seconds``.
    """

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        lockout_seconds: int,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._events: dict[str, Deque[float]] = {}
        self._lockouts: dict[str, float] = {}
        self._lock = threading.Lock()

    def is_locked(self, key: str) -> bool:
        """Return True if ``key`` is currently locked out."""
        now = time.time()
        with self._lock:
            until = self._lockouts.get(key)
            if until is None:
                return False
            if until <= now:
                # Lockout expired, clear state.
                self._lockouts.pop(key, None)
                self._events.pop(key, None)
                return False
            return True

    def lockout_remaining(self, key: str) -> int:
        """Seconds remaining for the current lockout, or 0."""
        now = time.time()
        with self._lock:
            until = self._lockouts.get(key)
            if until is None or until <= now:
                return 0
            return int(until - now)

    def record_failure(self, key: str) -> None:
        """Record a failed attempt; trigger lockout if the window is full."""
        now = time.time()
        with self._lock:
            events = self._events.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while events and events[0] < cutoff:
                events.popleft()
            events.append(now)
            if len(events) >= self.max_attempts:
                self._lockouts[key] = now + self.lockout_seconds
                # Drop the window so we don't keep counting during lockout.
                self._events.pop(key, None)

    def record_success(self, key: str) -> None:
        """Clear state for ``key`` after a successful authentication."""
        with self._lock:
            self._events.pop(key, None)
            self._lockouts.pop(key, None)

    def reset(self) -> None:
        """Clear all state. Tests-only."""
        with self._lock:
            self._events.clear()
            self._lockouts.clear()


# Module-level singletons used by the auth router.
# Created lazily so they pick up the latest settings on every call.
_login_limiter: SlidingWindowLimiter | None = None
_register_limiter: SlidingWindowLimiter | None = None
_lock = threading.Lock()


def _build_login_limiter() -> SlidingWindowLimiter:
    from app.config import settings

    return SlidingWindowLimiter(
        max_attempts=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
    )


def _build_register_limiter() -> SlidingWindowLimiter:
    from app.config import settings

    return SlidingWindowLimiter(
        max_attempts=3,
        window_seconds=60,
        lockout_seconds=600,
    )


def login_limiter() -> SlidingWindowLimiter:
    global _login_limiter
    with _lock:
        if _login_limiter is None:
            _login_limiter = _build_login_limiter()
        return _login_limiter


def register_limiter() -> SlidingWindowLimiter:
    global _register_limiter
    with _lock:
        if _register_limiter is None:
            _register_limiter = _build_register_limiter()
        return _register_limiter


def reset_for_tests() -> None:
    """Clear limiter state. Tests-only."""
    global _login_limiter, _register_limiter
    with _lock:
        _login_limiter = None
        _register_limiter = None