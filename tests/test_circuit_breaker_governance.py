"""
tests/test_circuit_breaker_governance.py

Test suite for Circuit Breaker Recovery, 429 Backoff, and Run-State Separation.
Verifies pre-request checks, 429 backoff, cooldown, HALF_OPEN canary probes,
outage evidence preservation, bounded retry, and WAITING_FOR_INFORMATION separation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    InvestigationRun,
    RunStatus,
    WorkflowReason,
)
from backend.orchestration.circuit_breaker_governor import (
    CircuitOpenError,
    InvestigationCircuitBreaker,
    ProviderStatus,
)


class MockClock:
    """Deterministic simulated clock for circuit breaker timing tests."""
    def __init__(self, start_time: float = 1000.0):
        self.current_time = start_time
    def __call__(self) -> float:
        return self.current_time
    def advance(self, seconds: float) -> None:
        self.current_time += seconds


def test_check_breaker_transitions_to_open_after_threshold():
    """Verifies breaker trips to CIRCUIT_OPEN after consecutive qualifying failures."""
    clock = MockClock()
    breaker = InvestigationCircuitBreaker(failure_threshold=3, recovery_timeout=20.0, clock=clock)
    assert breaker.status == ProviderStatus.HEALTHY

    # 1st and 2nd failures
    breaker.record_failure()
    breaker.check_breaker()
    breaker.record_failure()
    breaker.check_breaker()
    assert breaker.status == ProviderStatus.HEALTHY

    # 3rd failure trips circuit
    breaker.record_failure()
    assert breaker.status == ProviderStatus.CIRCUIT_OPEN

    # Subsequent request is blocked by CircuitOpenError
    with pytest.raises(CircuitOpenError) as exc_info:
        breaker.check_breaker()
    assert "Circuit open for provider" in str(exc_info.value)


def test_handle_429_backoff_and_cooldown():
    """Verifies 429 rate limit backoff sets cooldown and status to RATE_LIMITED."""
    clock = MockClock()
    breaker = InvestigationCircuitBreaker(recovery_timeout=15.0, clock=clock)

    delay = breaker.handle_429(retry_after_seconds=10.0)
    assert delay == 10.0
    assert breaker.status == ProviderStatus.RATE_LIMITED

    # Breaker blocked during cooldown
    with pytest.raises(CircuitOpenError):
        breaker.check_breaker()

    # Advance clock past cooldown -> transitions to HALF_OPEN probe
    clock.advance(10.1)
    breaker.check_breaker()
    assert breaker.status == ProviderStatus.HALF_OPEN
    assert breaker.canary_in_flight is True


def test_half_open_canary_probe_success_recovers_to_healthy():
    """Verifies successful canary probe in HALF_OPEN recovers circuit to HEALTHY."""
    clock = MockClock()
    breaker = InvestigationCircuitBreaker(failure_threshold=2, recovery_timeout=10.0, clock=clock)

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.status == ProviderStatus.CIRCUIT_OPEN

    clock.advance(10.1)
    breaker.check_breaker()
    assert breaker.status == ProviderStatus.HALF_OPEN

    # Only one canary in flight permitted
    with pytest.raises(CircuitOpenError):
        breaker.check_breaker()

    # Canary probe succeeds
    breaker.record_success()
    assert breaker.status == ProviderStatus.HEALTHY
    assert breaker.consecutive_failures == 0


def test_provider_outage_preserves_evidence_and_schedules_bounded_retry():
    """Verifies outage preserves collected evidence and schedules bounded retries."""
    clock = MockClock()
    breaker = InvestigationCircuitBreaker(max_retries=3, clock=clock)
    claim = AtomicRightsClaim(
        claim_id="clm_outage_01", occurrence_id="occ_outage",
        occurrence_lineage_id="lin_outage", right_category="music", rights_subject="Track Outage",
    )
    preserved = [{"source": "ascap.com", "id": "12345"}]

    res = breaker.handle_provider_outage(
        action_name="ACT_02_SEARCH_PUBLIC_SOURCES",
        preserved_evidence=preserved,
        claim=claim,
    )
    assert res["status"] == "PROVIDER_OUTAGE_HANDLED"
    assert res["evidence_preserved_count"] == 1
    assert res["retry_scheduled"] is True
    assert res["claim_disposition"] == CensusDisposition.NEEDS_REVIEW.value
    assert res["workflow_reason"] == WorkflowReason.PROVIDER_OFFLINE.value
    assert breaker.retry_attempts == 1


def test_waiting_for_information_strictly_for_human_input_invariant():
    """Verifies invariant: provider outages must NEVER map to WAITING_FOR_INFORMATION."""
    breaker = InvestigationCircuitBreaker()
    claim = AtomicRightsClaim(
        claim_id="clm_human_invariant", occurrence_id="occ_hi",
        occurrence_lineage_id="lin_hi", right_category="prop", rights_subject="Vintage Prop",
    )
    run = InvestigationRun(
        run_id="run_test_01", organization_id="org_test", production_id="prod_test",
        base_version_id="v7", target_version_id="v8", status=RunStatus.INVESTIGATING,
    )

    # Provider outage must update claim without violating run invariant
    res = breaker.handle_provider_outage("ACT_02", [{"id": "ev1"}], claim, run=run)
    assert res["workflow_reason"] == WorkflowReason.PROVIDER_OFFLINE.value
    assert claim.workflow_reason == WorkflowReason.PROVIDER_OFFLINE
    assert run.status != RunStatus.WAITING_FOR_INFORMATION


def test_separate_provider_claim_and_run_dimensions():
    """Verifies complete separation of ProviderStatus, CensusDisposition, and RunStatus."""
    breaker = InvestigationCircuitBreaker(provider_name="parallel_search")
    assert isinstance(breaker.status, ProviderStatus)

    claim = AtomicRightsClaim(
        claim_id="clm_3way", occurrence_id="occ_3way",
        occurrence_lineage_id="lin_3way", right_category="artwork", rights_subject="Mural 3way",
    )
    claim.disposition = CensusDisposition.NEEDS_REVIEW
    assert isinstance(claim.disposition, CensusDisposition)

    run = InvestigationRun(
        run_id="run_3way", organization_id="org_studio", production_id="prod_feature",
        base_version_id="v7", target_version_id="v8", status=RunStatus.INVESTIGATING,
    )
    assert isinstance(run.status, RunStatus)

    # Mutating provider status does not change claim disposition or run lifecycle
    breaker.status = ProviderStatus.CIRCUIT_OPEN
    assert breaker.status == ProviderStatus.CIRCUIT_OPEN
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert run.status == RunStatus.INVESTIGATING
