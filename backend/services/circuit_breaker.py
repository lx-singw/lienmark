"""
backend/services/circuit_breaker.py

Thread and async-safe Circuit Breaker implementation with fail-closed/fail-soft
fallback routing, probe health checking, and telemetry metrics.
Strictly compliant with Google AntiGravity architectural standards.
"""

from __future__ import annotations

import asyncio
from collections import deque
import inspect
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from backend.services.circuit_breaker_types import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerTelemetry,
    CircuitState,
    StateTransitionRecord,
    is_qualifying_failure,
)

logger = logging.getLogger("lienmark.circuit_breaker")
T = TypeVar("T")


class CircuitBreaker:
    """Async-safe circuit breaker protecting downstream dependencies."""

    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Any] = None,
        failure_predicate: Optional[Callable[[BaseException], bool]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig(service_name=name)
        self._custom_fallback = fallback
        self._failure_predicate = failure_predicate
        self._clock = clock or time.time

        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._consecutive_probes = 0
        self._total_requests = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_trips = 0
        self._total_fallbacks = 0
        self._last_failure_timestamp: Optional[float] = None
        self._last_success_timestamp: Optional[float] = None
        self._last_state_change_timestamp = self._clock()
        self._cached_mirror: Optional[Any] = None
        self._probe_in_flight = False
        self._history: deque[StateTransitionRecord] = deque(maxlen=100)

    def _time(self) -> float:
        return self._clock()

    @property
    def state(self) -> CircuitState:
        """Current operational state, evaluating timeout expiration if OPEN."""
        if self._state == CircuitState.OPEN:
            if (self._time() - self._last_state_change_timestamp) >= self.config.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    def set_cached_mirror(self, data: Any) -> None:
        """Updates the cached mirror / offline registry for fallback routing."""
        self._cached_mirror = data

    def reset(self) -> None:
        """Manually restores circuit to CLOSED and resets counters."""
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._consecutive_probes = 0
        self._probe_in_flight = False
        self._last_state_change_timestamp = self._time()

    def get_telemetry(self) -> CircuitBreakerTelemetry:
        """Produces a validated Pydantic snapshot of telemetry and transitions."""
        current_state = self.state
        time_until_retry = 0.0
        if current_state == CircuitState.OPEN:
            elapsed = self._time() - self._last_state_change_timestamp
            time_until_retry = max(0.0, self.config.recovery_timeout - elapsed)

        return CircuitBreakerTelemetry(
            circuit_name=self.name,
            state=current_state,
            consecutive_failures=self._consecutive_failures,
            consecutive_successes=self._consecutive_successes,
            total_requests=self._total_requests,
            total_successes=self._total_successes,
            total_failures=self._total_failures,
            total_trips=self._total_trips,
            total_fallbacks=self._total_fallbacks,
            last_failure_timestamp=self._last_failure_timestamp,
            last_success_timestamp=self._last_success_timestamp,
            last_state_change_timestamp=self._last_state_change_timestamp,
            time_until_retry=time_until_retry,
            transition_history=list(self._history),
        )

    def _transition_to(self, new_state: CircuitState, reason: str) -> None:
        if self._state == new_state:
            return
        old_state = self._state
        self._state = new_state
        now = self._time()
        self._last_state_change_timestamp = now
        if new_state == CircuitState.OPEN:
            self._total_trips += 1
        elif new_state == CircuitState.HALF_OPEN:
            self._consecutive_probes = 0
        self._history.append(
            StateTransitionRecord(
                from_state=old_state,
                to_state=new_state,
                timestamp=now,
                reason=reason,
            )
        )
        logger.warning(
            "Circuit '%s' transitioned %s -> %s: %s",
            self.name, old_state.value, new_state.value, reason,
        )

    async def _resolve_fallback(self, fallback: Optional[Any], *args: Any, **kwargs: Any) -> Any:
        handler = fallback if fallback is not None else self._custom_fallback
        if handler is not None:
            self._total_fallbacks += 1
            if callable(handler):
                try:
                    res = handler(*args, **kwargs)
                except TypeError:
                    res = handler()
                return (await res) if inspect.isawaitable(res) else res
            return handler

        if self._cached_mirror is not None:
            self._total_fallbacks += 1
            return self._cached_mirror

        retry_after = max(0.0, self.config.recovery_timeout - (self._time() - self._last_state_change_timestamp))
        raise CircuitBreakerOpenError(
            message=f"Circuit breaker '{self.name}' is OPEN; execution rejected.",
            circuit_name=self.name,
            retry_after=retry_after,
            fallback_data=self._cached_mirror,
            is_stale=True,
        )

    async def _check_call_gate(self) -> bool:
        async with self._lock:
            self._total_requests += 1
            if self._state == CircuitState.OPEN:
                if (self._time() - self._last_state_change_timestamp) >= self.config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN, "Recovery timeout reached; initiating probe")

            if self._state == CircuitState.OPEN:
                return True
            if self._state == CircuitState.HALF_OPEN:
                if self._probe_in_flight:
                    return True
                self._probe_in_flight = True
                return False
            return False

    async def _record_success(self, result: Any) -> None:
        async with self._lock:
            now = self._time()
            self._total_successes += 1
            self._consecutive_failures = 0
            self._last_success_timestamp = now
            self._cached_mirror = result
            if self._state == CircuitState.HALF_OPEN:
                self._probe_in_flight = False
                self._consecutive_probes += 1
                if self._consecutive_probes >= self.config.probe_threshold:
                    self._transition_to(CircuitState.CLOSED, "Probe succeeded; circuit recovered")
                    self._consecutive_successes = 1
            else:
                self._consecutive_successes += 1

    async def _record_failure(self, exc: BaseException) -> None:
        is_fail = self._failure_predicate(exc) if self._failure_predicate else is_qualifying_failure(exc)
        async with self._lock:
            self._total_failures += 1
            if not is_fail:
                if self._state == CircuitState.HALF_OPEN:
                    self._probe_in_flight = False
                return

            self._last_failure_timestamp = self._time()
            self._consecutive_successes = 0
            if self._state == CircuitState.HALF_OPEN:
                self._probe_in_flight = False
                self._transition_to(CircuitState.OPEN, f"Probe failed ({type(exc).__name__}); re-tripping")
            elif self._state == CircuitState.CLOSED:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(
                        CircuitState.OPEN,
                        f"Failure threshold ({self.config.failure_threshold}) reached; tripping circuit",
                    )

    async def call_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        fallback: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Executes an async or sync callable protected by circuit invariants."""
        must_fallback = await self._check_call_gate()
        if must_fallback:
            return await self._resolve_fallback(fallback, *args, **kwargs)

        try:
            res = func(*args, **kwargs)
            if inspect.isawaitable(res):
                res = await res
        except BaseException as exc:
            await self._record_failure(exc)
            raise
        else:
            await self._record_success(res)
            return res


from backend.services.circuit_breaker_registry import (  # noqa: E402
    circuit_breaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)

__all__ = ["CircuitBreaker", "circuit_breaker", "get_circuit_breaker", "reset_all_circuit_breakers"]

