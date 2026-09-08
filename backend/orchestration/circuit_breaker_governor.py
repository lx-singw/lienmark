"""
backend/orchestration/circuit_breaker_governor.py

Circuit breaker recovery, 429 rate limit backoff, and run-state separation.
Enforces strict 3-way separation: ProviderStatus, ClaimDisposition, and RunLifecycle.
Provider outages preserve evidence and schedule bounded retries; WAITING_FOR_INFORMATION
is strictly reserved for human input.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import random
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.domain.models import CensusDisposition, RunStatus, WorkflowReason

logger = logging.getLogger("lienmark.orchestration.circuit_breaker")


class ProviderStatus(str, Enum):
    """External provider availability and health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    RATE_LIMITED = "rate_limited"
    HALF_OPEN = "half_open"
    OFFLINE = "offline"


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker faults."""
    pass


class CircuitOpenError(CircuitBreakerError):
    """Raised when call is rejected because breaker is open or rate limited."""
    def __init__(self, provider: str, retry_after: float):
        super().__init__(f"Circuit open for provider '{provider}'. Retry after {retry_after:.1f}s.")
        self.provider = provider
        self.retry_after = retry_after


class ScheduledRetry(BaseModel):
    """Descriptor for a bounded retry attempt scheduled after provider failure."""
    model_config = ConfigDict(frozen=True)

    provider: str
    attempt_number: int
    max_retries: int = 3
    delay_seconds: float
    target_action: str
    scheduled_at: float = Field(default_factory=time.time)


class InvestigationCircuitBreaker:
    """
    Manages circuit breaker lifecycle, 429 exponential backoff, HALF_OPEN canary probes,
    and provider outage recovery while preserving collected evidence.
    """

    def __init__(
        self,
        provider_name: str = "parallel_search",
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        max_retries: int = 3,
        clock: Optional[Any] = None,
    ) -> None:
        self.provider_name = provider_name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(0.1, float(recovery_timeout))
        self.max_retries = max(1, max_retries)
        self._clock = clock or time.time

        self.status = ProviderStatus.HEALTHY
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.retry_attempts = 0
        self.cooldown_until = 0.0
        self.canary_in_flight = False
        self.scheduled_retries: List[ScheduledRetry] = []

    def check_breaker(self) -> None:
        """Evaluates circuit before sending requests; transitions to HALF_OPEN when cooldown expires."""
        now = self._clock()
        if self.status in (ProviderStatus.CIRCUIT_OPEN, ProviderStatus.RATE_LIMITED):
            if now >= self.cooldown_until:
                self.status = ProviderStatus.HALF_OPEN
                self.canary_in_flight = False
                logger.info("Provider '%s' cooldown elapsed; entering HALF_OPEN canary probe.", self.provider_name)
            else:
                retry_after = max(0.0, self.cooldown_until - now)
                raise CircuitOpenError(self.provider_name, retry_after)

        if self.status == ProviderStatus.HALF_OPEN:
            if self.canary_in_flight:
                retry_after = max(0.0, self.cooldown_until - now)
                raise CircuitOpenError(self.provider_name, retry_after)
            self.canary_in_flight = True

    def handle_429(self, retry_after_seconds: Optional[float] = None) -> float:
        """Applies 429 Too Many Requests backoff with jitter and sets cooldown."""
        now = self._clock()
        if retry_after_seconds and retry_after_seconds > 0:
            delay = float(retry_after_seconds)
        else:
            base = min(60.0, self.recovery_timeout * (2 ** min(self.retry_attempts, 4)))
            delay = base + random.uniform(0.1, 1.0)

        self.status = ProviderStatus.RATE_LIMITED
        self.cooldown_until = now + delay
        self.consecutive_failures += 1
        logger.warning("Provider '%s' 429 received. Cooldown set for %.2fs.", self.provider_name, delay)
        return delay

    def record_success(self) -> None:
        """Records successful call, resetting breaker to HEALTHY if in HALF_OPEN."""
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        self.canary_in_flight = False
        self.retry_attempts = 0
        self.status = ProviderStatus.HEALTHY

    def record_failure(self, is_429: bool = False, retry_after: Optional[float] = None) -> None:
        """Records qualifying failure or 429, tripping breaker if threshold reached."""
        self.canary_in_flight = False
        self.consecutive_successes = 0
        if is_429:
            self.handle_429(retry_after)
            return

        self.consecutive_failures += 1
        now = self._clock()
        if self.status == ProviderStatus.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
            self.status = ProviderStatus.CIRCUIT_OPEN
            self.cooldown_until = now + self.recovery_timeout
            logger.warning("Provider '%s' tripped to CIRCUIT_OPEN for %.1fs.", self.provider_name, self.recovery_timeout)

    def _schedule_retry(self, action_name: str) -> Optional[ScheduledRetry]:
        """Schedules bounded retry if limit not reached, else marks OFFLINE."""
        if self.retry_attempts >= self.max_retries:
            self.status = ProviderStatus.OFFLINE
            return None
        self.retry_attempts += 1
        delay = min(60.0, 2.0 ** self.retry_attempts)
        retry_obj = ScheduledRetry(
            provider=self.provider_name, attempt_number=self.retry_attempts,
            max_retries=self.max_retries, delay_seconds=delay, target_action=action_name,
        )
        self.scheduled_retries.append(retry_obj)
        return retry_obj

    def handle_provider_outage(
        self, action_name: str, preserved_evidence: List[Any],
        claim: Any, run: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Preserves evidence, schedules bounded retry, and enforces state separation."""
        self.record_failure()
        retry_obj = self._schedule_retry(action_name)
        claim_disposition, workflow_reason = CensusDisposition.NEEDS_REVIEW, WorkflowReason.PROVIDER_OFFLINE
        if hasattr(claim, "disposition"): claim.disposition = claim_disposition
        if hasattr(claim, "workflow_reason"): claim.workflow_reason = workflow_reason
        if run is not None and hasattr(run, "status"):
            assert run.status != RunStatus.WAITING_FOR_INFORMATION, (
                "Invariant violation: WAITING_FOR_INFORMATION is strictly for human input, not provider outages."
            )
        return {
            "status": "PROVIDER_OUTAGE_HANDLED", "provider": self.provider_name,
            "provider_status": self.status.value, "claim_disposition": claim_disposition.value,
            "workflow_reason": workflow_reason.value, "evidence_preserved_count": len(preserved_evidence),
            "preserved_evidence": list(preserved_evidence), "retry_scheduled": retry_obj is not None,
            "scheduled_retry": retry_obj.model_dump() if retry_obj else None,
        }
