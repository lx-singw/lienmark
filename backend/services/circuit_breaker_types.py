"""
backend/services/circuit_breaker_types.py

Domain models, enums, exception hierarchy, and Pydantic v2 contracts
for the Resilience & Circuit Breaker subsystem.
Strictly compliant with Google AntiGravity architectural standards.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, List, Optional
import httpx
from pydantic import BaseModel, ConfigDict, Field


class CircuitState(str, Enum):
    """Operating lifecycle states of the resilience circuit breaker."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    """Base domain exception for all circuit breaker faults and rejections."""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """
    Raised when an invocation is rejected because the circuit is OPEN.
    Preserves stale fallback data and retry metadata to allow fail-soft degradation.
    """

    def __init__(
        self,
        message: str,
        circuit_name: str,
        retry_after: float,
        fallback_data: Optional[Any] = None,
        is_stale: bool = True,
    ) -> None:
        super().__init__(message)
        self.circuit_name = circuit_name
        self.retry_after = max(0.0, float(retry_after))
        self.fallback_data = fallback_data
        self.is_stale = is_stale


class CircuitBreakerProbeError(CircuitBreakerError):
    """Raised when a canary probe attempt fails while in HALF_OPEN state."""

    def __init__(
        self,
        message: str,
        circuit_name: str,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.circuit_name = circuit_name
        self.cause = cause


class StateTransitionRecord(BaseModel):
    """Immutable audit entry capturing an atomic circuit breaker state transition."""
    model_config = ConfigDict(frozen=True)

    from_state: CircuitState = Field(..., description="Previous circuit state")
    to_state: CircuitState = Field(..., description="New circuit state")
    timestamp: float = Field(..., description="Epoch timestamp of the transition")
    reason: str = Field(..., description="Triggering condition or event rationale")


class CircuitBreakerConfig(BaseModel):
    """Immutable configuration invariants for the Circuit Breaker subsystem."""
    model_config = ConfigDict(frozen=True)

    failure_threshold: int = Field(
        default=3,
        ge=1,
        description="Strict consecutive qualifying failures before tripping to OPEN",
    )
    recovery_timeout: float = Field(
        default=60.0,
        ge=0.01,
        description="Cooldown duration in seconds before attempting a HALF_OPEN probe",
    )
    probe_threshold: int = Field(
        default=1,
        ge=1,
        description="Consecutive successful probes in HALF_OPEN to reset to CLOSED",
    )
    service_name: str = Field(
        default="default_service",
        description="Identifier for telemetry and logging attribution",
    )


class CircuitBreakerTelemetry(BaseModel):
    """Pydantic v2 snapshot of circuit breaker runtime state and metrics."""
    model_config = ConfigDict(frozen=True)

    circuit_name: str = Field(..., description="Identifier of the circuit breaker")
    state: CircuitState = Field(..., description="Current operational state")
    consecutive_failures: int = Field(default=0, ge=0)
    consecutive_successes: int = Field(default=0, ge=0)
    total_requests: int = Field(default=0, ge=0)
    total_successes: int = Field(default=0, ge=0)
    total_failures: int = Field(default=0, ge=0)
    total_trips: int = Field(default=0, ge=0)
    total_fallbacks: int = Field(default=0, ge=0)
    last_failure_timestamp: Optional[float] = None
    last_success_timestamp: Optional[float] = None
    last_state_change_timestamp: float = Field(...)
    time_until_retry: float = Field(default=0.0, ge=0.0)
    transition_history: List[StateTransitionRecord] = Field(default_factory=list)


def is_qualifying_failure(exc: BaseException) -> bool:
    """
    Evaluates if an exception qualifies as a breaker trip trigger.
    Strictly captures HTTP 5xx, network timeouts, and connection drops.
    Excludes HTTP 4xx (client errors) and business logic exceptions.
    """
    if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError)):
        return True
    if isinstance(
        exc,
        (
            httpx.NetworkError,
            ConnectionError,
            ConnectionResetError,
            ConnectionRefusedError,
            BrokenPipeError,
            OSError,
        ),
    ):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    status = getattr(exc, "status_code", getattr(exc, "http_status", None))
    if isinstance(status, int) and status >= 500:
        return True
    return False
