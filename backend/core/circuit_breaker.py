"""
backend/core/circuit_breaker.py

Authoritative 3-state Circuit Breaker (CLOSED, OPEN, HALF_OPEN) with single-probe
canary mutex, decorrelated exponential jitter, and fail-closed truthfulness.
Emits UNVERIFIED_CIRCUIT_DEGRADED stance to eliminate false-positive clearances.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("lienmark.core.circuit_breaker")

DEGRADED_CIRCUIT_STANCE = "UNVERIFIED_CIRCUIT_DEGRADED"


class CircuitState(str, Enum):
    """Lifecycle states of the fault-tolerant circuit breaker."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is attempted while circuit is in OPEN state."""
    def __init__(self, message: str, retry_after_sec: float = 0.0):
        super().__init__(message)
        self.retry_after_sec = retry_after_sec
        self.stance = DEGRADED_CIRCUIT_STANCE


def compute_decorrelated_jitter(
    base_timeout: float,
    max_timeout: float,
    attempt: int,
    prev_timeout: float,
) -> float:
    """Computes decorrelated exponential jitter delay for circuit recovery."""
    if attempt <= 1:
        jitter = random.uniform(0.0, min(1.0, base_timeout * 0.1))
        return min(max_timeout, base_timeout + jitter)
    low = base_timeout
    high = max(base_timeout, prev_timeout * 3.0)
    sleep = random.uniform(low, high)
    return min(max_timeout, sleep)


class CircuitBreaker:
    """
    Thread-safe and coroutine-safe 3-state circuit breaker.
    Gates access to flaky external services (Parallel Search, Gemini APIs).
    """

    def __init__(
        self,
        name: str = "default_circuit",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        max_timeout: float = 120.0,
    ):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(0.01, recovery_timeout)
        self.max_timeout = max(self.recovery_timeout, max_timeout)
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_state_change = time.monotonic()
        self._current_recovery_delay = self.recovery_timeout
        self._canary_in_flight = False
        self._lock = threading.Lock()
        self._async_lock: Optional[asyncio.Lock] = None

    @property
    def state(self) -> CircuitState:
        """Evaluates and returns current state, transitioning OPEN -> HALF_OPEN if timeout expired."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                now = time.monotonic()
                if now - self._last_state_change >= self._current_recovery_delay:
                    self._state = CircuitState.HALF_OPEN
                    self._last_state_change = now
                    self._canary_in_flight = False
                    logger.info(f"Circuit '{self.name}' transitioned from OPEN to HALF_OPEN probe.")
            return self._state

    def record_success(self) -> None:
        """Records a successful probe or execution, resetting circuit if in HALF_OPEN."""
        with self._lock:
            self._consecutive_failures = 0
            self._canary_in_flight = False
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._current_recovery_delay = self.recovery_timeout
                self._last_state_change = time.monotonic()
                logger.info(f"Circuit '{self.name}' probe succeeded: reset to CLOSED.")

    def record_failure(self, exc: Optional[Exception] = None) -> None:
        """Records execution failure, tripping circuit to OPEN if threshold breached."""
        with self._lock:
            self._consecutive_failures += 1
            self._canary_in_flight = False
            now = time.monotonic()
            if self._state == CircuitState.HALF_OPEN or self._consecutive_failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                prev = self._current_recovery_delay
                self._current_recovery_delay = compute_decorrelated_jitter(
                    self.recovery_timeout, self.max_timeout, self._consecutive_failures, prev
                )
                self._last_state_change = now
                logger.warning(
                    f"Circuit '{self.name}' tripped to OPEN (delay={self._current_recovery_delay:.2f}s). Exc: {exc}"
                )

    def acquire_execution_permission(self) -> bool:
        """Evaluates whether current request is permitted to execute or probe."""
        cur = self.state
        if cur == CircuitState.CLOSED:
            return True
        if cur == CircuitState.HALF_OPEN:
            with self._lock:
                if not self._canary_in_flight:
                    self._canary_in_flight = True
                    return True
                return False
        return False

    async def call_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executes asynchronous operation through circuit breaker with fail-closed gating."""
        if not self.acquire_execution_permission():
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is OPEN. Operation gated under {DEGRADED_CIRCUIT_STANCE}.",
                retry_after_sec=self._current_recovery_delay,
            )
        try:
            res = await func(*args, **kwargs)
            self.record_success()
            return res
        except Exception as exc:
            self.record_failure(exc)
            raise

    def call_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executes synchronous operation through circuit breaker with fail-closed gating."""
        if not self.acquire_execution_permission():
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is OPEN. Operation gated under {DEGRADED_CIRCUIT_STANCE}.",
                retry_after_sec=self._current_recovery_delay,
            )
        try:
            res = func(*args, **kwargs)
            self.record_success()
            return res
        except Exception as exc:
            self.record_failure(exc)
            raise
