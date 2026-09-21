"""In-process login rate limiting for v1. Correct for a single backend
process (this Compose setup runs exactly one); a multi-process deployment
would need this backed by Redis instead — noted as the natural upgrade
once Redis enters the stack for real background jobs, not built now for
a case that doesn't exist yet.
"""
from __future__ import annotations

import time
from collections import defaultdict

from app.core.config import settings


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_seconds = settings.login_rate_limit_window_minutes * 60
        attempts = [t for t in self._attempts[key] if now - t < window_seconds]
        attempts.append(now)
        self._attempts[key] = attempts
        return len(attempts) <= settings.login_rate_limit_attempts
