"""Circuit breaker para resiliencia de polling.

Circuit breaker for resilient polling.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Deque


@dataclass
class CircuitBreaker:
    """/** Circuit breaker con estados CLOSED/OPEN/HALF-OPEN. / Circuit breaker with CLOSED/OPEN/HALF-OPEN states. **/"""

    failure_threshold: int = 5
    failure_window_seconds: int = 600
    open_timeout_seconds: int = 1800
    half_open_after_seconds: int = 600
    success_threshold: int = 2
    open_log_interval_seconds: int = 300
    state: str = "CLOSED"
    _failures: Deque[datetime] = field(default_factory=deque)
    _opened_at: datetime | None = None
    _next_log_at: datetime | None = None
    _half_open_successes: int = 0
    _alert_sent: bool = False

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _trim_failures(self, now: datetime) -> None:
        window = timedelta(seconds=self.failure_window_seconds)
        while self._failures and now - self._failures[0] > window:
            self._failures.popleft()

    def _open(self, now: datetime) -> bool:
        if self.state == "OPEN":
            return False
        self.state = "OPEN"
        self._opened_at = now
        self._next_log_at = now
        self._half_open_successes = 0
        self._alert_sent = False
        return True

    def _half_open(self, now: datetime) -> None:
        self.state = "HALF_OPEN"
        self._half_open_successes = 0
        self._opened_at = now
        self._next_log_at = None

    def _close(self) -> None:
        self.state = "CLOSED"
        self._failures.clear()
        self._opened_at = None
        self._next_log_at = None
        self._half_open_successes = 0
        self._alert_sent = False

    def _next_half_open_at(self) -> datetime | None:
        if not self._opened_at:
            return None
        wait_seconds = min(self.half_open_after_seconds, self.open_timeout_seconds)
        return self._opened_at + timedelta(seconds=wait_seconds)

    def seconds_until_half_open(self, now: datetime | None = None) -> float:
        now = now or self._now()
        target = self._next_half_open_at()
        if not target:
            return 0.0
        return max(0.0, (target - now).total_seconds())

    def allow_request(self, now: datetime | None = None) -> bool:
        now = now or self._now()
        if self.state != "OPEN":
            return True
        next_half_open = self._next_half_open_at()
        if next_half_open and now >= next_half_open:
            self._half_open(now)
            return True
        return False

    def record_failure(self, now: datetime | None = None) -> bool:
        now = now or self._now()
        if self.state == "HALF_OPEN":
            return self._open(now)
        self._failures.append(now)
        self._trim_failures(now)
        if self.state == "CLOSED" and len(self._failures) >= self.failure_threshold:
            return self._open(now)
        return False

    def record_success(self, now: datetime | None = None) -> bool:
        if self.state != "HALF_OPEN":
            return False
        self._half_open_successes += 1
        if self._half_open_successes >= self.success_threshold:
            self._close()
            return True
        return False

    def should_log_open_wait(self, now: datetime | None = None) -> bool:
        if self.state != "OPEN":
            return False
        now = now or self._now()
        if not self._next_log_at or now >= self._next_log_at:
            self._next_log_at = now + timedelta(seconds=self.open_log_interval_seconds)
            return True
        return False

    def consume_open_alert(self) -> bool:
        if self.state != "OPEN" or self._alert_sent:
            return False
        self._alert_sent = True
        return True
