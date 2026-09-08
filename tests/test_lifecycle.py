"""
tests/test_lifecycle.py

Authoritative test suite for Lifecycle transitions under Lienmark Milestone B:
1. Cache hit transitions from QUEUED to COMPLETED and READY_FOR_REVIEW.
2. Mandatory reason="DEDUPLICATION_CACHE_HIT" and reused baseline metadata linkage.
3. Strict enforcement: Cache hit transitions NEVER create or imply unapproved legal clearance.
4. Comprehensive audit logging across transitions.
"""

from __future__ import annotations

import pytest

from backend.core.lifecycle import (
    ALLOWED_TRANSITIONS,
    CACHE_HIT_REASON,
    InvalidStateTransitionError,
    LifecycleAuditEvent,
    RunLifecycleManager,
    can_transition,
    get_allowed_transitions,
    is_terminal_state,
    transition_run,
)
from backend.domain.models import InvestigationRun, RunStatus


def _create_queued_run(run_id: str = "run_test_001") -> InvestigationRun:
    return InvestigationRun(
        run_id=run_id,
        organization_id="org_paramount",
        production_id="prod_godfather",
        base_version_id="v1",
        target_version_id="v2",
    )


class TestLifecycleAllowedTransitions:
    """Verifies transition matrix updates for Milestone B."""

    def test_queued_contains_completed_and_ready_for_review(self) -> None:
        allowed = ALLOWED_TRANSITIONS[RunStatus.QUEUED]
        assert RunStatus.COMPLETED in allowed
        assert RunStatus.READY_FOR_REVIEW in allowed
        assert RunStatus.INVESTIGATING in allowed
        assert RunStatus.CANCELLED in allowed
        assert RunStatus.FAILED in allowed
        assert RunStatus.SUPERSEDED in allowed

    def test_get_allowed_transitions_for_queued(self) -> None:
        allowed = get_allowed_transitions(RunStatus.QUEUED)
        assert RunStatus.COMPLETED in allowed
        assert RunStatus.READY_FOR_REVIEW in allowed


class TestCacheHitTransitions:
    """Verifies deduplication cache-hit transitions and security constraints."""

    def test_queued_to_completed_cache_hit_success(self) -> None:
        run = _create_queued_run("run_cache_hit_completed")
        assert run.status == RunStatus.QUEUED

        metadata = {
            "reused_baseline_id": "v1",
            "all_claims_approved": True,
            "claims_count": 5,
            "unapproved_claims_count": 0,
        }
        assert can_transition(
            RunStatus.QUEUED,
            RunStatus.COMPLETED,
            reason=CACHE_HIT_REASON,
            metadata=metadata,
        )

        updated = transition_run(
            run=run,
            target_state=RunStatus.COMPLETED,
            actor_id="dedup_engine",
            reason=CACHE_HIT_REASON,
            metadata=metadata,
        )

        assert updated.status == RunStatus.COMPLETED
        assert updated.metadata["completed_at"] is not None
        assert updated.metadata["terminal_timestamp"] is not None
        assert updated.metadata["reused_baseline_id"] == "v1"

        audit_log = updated.metadata.get("audit_log", [])
        assert len(audit_log) == 1
        assert audit_log[0]["reason"] == CACHE_HIT_REASON
        assert audit_log[0]["metadata"]["reused_baseline_id"] == "v1"

    def test_queued_to_ready_for_review_cache_hit_success(self) -> None:
        run = _create_queued_run("run_cache_hit_review")
        assert run.status == RunStatus.QUEUED

        metadata = {
            "reused_baseline_id": "v2",
            "all_claims_approved": False,
            "claims_count": 3,
            "unapproved_claims_count": 2,
        }
        assert can_transition(
            RunStatus.QUEUED,
            RunStatus.READY_FOR_REVIEW,
            reason=CACHE_HIT_REASON,
            metadata=metadata,
        )

        updated = transition_run(
            run=run,
            target_state=RunStatus.READY_FOR_REVIEW,
            actor_id="dedup_engine",
            reason=CACHE_HIT_REASON,
            metadata=metadata,
        )

        assert updated.status == RunStatus.READY_FOR_REVIEW
        assert updated.metadata["requires_counsel_review"] is True
        assert updated.metadata["legal_clearance_approved"] is False

    def test_queued_to_completed_rejected_without_cache_hit_reason(self) -> None:
        run = _create_queued_run("run_invalid_reason")
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            transition_run(
                run=run,
                target_state=RunStatus.COMPLETED,
                reason="FAST_TRACK_CLEARANCE",
                metadata={"reused_baseline_id": "v1", "all_claims_approved": True},
            )
        assert CACHE_HIT_REASON in str(exc_info.value)

    def test_queued_to_completed_rejected_without_baseline_metadata(self) -> None:
        run = _create_queued_run("run_no_metadata")
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            transition_run(
                run=run,
                target_state=RunStatus.COMPLETED,
                reason=CACHE_HIT_REASON,
                metadata={"all_claims_approved": True},
            )
        assert "metadata linking reused baseline" in str(exc_info.value)

    def test_queued_to_ready_for_review_rejected_without_cache_hit_reason(self) -> None:
        run = _create_queued_run("run_invalid_review_reason")
        with pytest.raises(InvalidStateTransitionError):
            transition_run(
                run=run,
                target_state=RunStatus.READY_FOR_REVIEW,
                reason="MANUAL_SKIP",
                metadata={"reused_baseline_id": "v1"},
            )

    def test_queued_to_ready_for_review_rejected_without_baseline_linkage(self) -> None:
        run = _create_queued_run("run_missing_baseline_link")
        with pytest.raises(InvalidStateTransitionError):
            transition_run(
                run=run,
                target_state=RunStatus.READY_FOR_REVIEW,
                reason=CACHE_HIT_REASON,
                metadata={},
            )


class TestLegalClearanceSafeguards:
    """Verifies that cache hit transitions NEVER create or imply unapproved legal clearance."""

    def test_completed_rejected_when_claims_not_approved(self) -> None:
        run = _create_queued_run("run_unapproved_claims")
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            transition_run(
                run=run,
                target_state=RunStatus.COMPLETED,
                reason=CACHE_HIT_REASON,
                metadata={
                    "reused_baseline_id": "v1",
                    "all_claims_approved": False,
                    "unapproved_claims_count": 1,
                },
            )
        assert "all baseline claims to be approved" in str(exc_info.value)

    def test_completed_rejected_when_unapproved_count_greater_than_zero(self) -> None:
        run = _create_queued_run("run_contradictory_metadata")
        with pytest.raises(InvalidStateTransitionError):
            transition_run(
                run=run,
                target_state=RunStatus.COMPLETED,
                reason=CACHE_HIT_REASON,
                metadata={
                    "reused_baseline_id": "v1",
                    "all_claims_approved": True,
                    "unapproved_claims_count": 3,
                },
            )

    def test_ready_for_review_explicitly_disclaims_legal_clearance(self) -> None:
        run = _create_queued_run("run_review_no_clearance")
        updated = transition_run(
            run=run,
            target_state=RunStatus.READY_FOR_REVIEW,
            reason=CACHE_HIT_REASON,
            metadata={
                "reused_baseline_id": "v1",
                "legal_clearance_approved": True,  # Attempting to forge clearance
            },
        )
        assert updated.metadata["legal_clearance_approved"] is False
        assert updated.metadata["requires_counsel_review"] is True


class TestLifecycleAuditAndManager:
    """Verifies RunLifecycleManager integration and audit trail completeness."""

    def test_manager_records_cache_hit_in_ledger(self) -> None:
        manager = RunLifecycleManager(default_actor="cache_orchestrator")
        run = _create_queued_run("run_mgr_001")

        manager.transition(
            run=run,
            target_state=RunStatus.COMPLETED,
            reason=CACHE_HIT_REASON,
            metadata={"reused_baseline_id": "v1", "all_claims_approved": True},
        )

        history = manager.get_audit_history("run_mgr_001")
        assert len(history) == 1
        evt = history[0]
        assert evt.from_state == RunStatus.QUEUED
        assert evt.to_state == RunStatus.COMPLETED
        assert evt.reason == CACHE_HIT_REASON
        assert evt.metadata["reused_baseline_id"] == "v1"

    def test_terminal_states_prohibit_outbound_transitions(self) -> None:
        run = _create_queued_run("run_terminal")
        run = transition_run(
            run=run,
            target_state=RunStatus.COMPLETED,
            reason=CACHE_HIT_REASON,
            metadata={"reused_baseline_id": "v1", "all_claims_approved": True},
        )
        assert is_terminal_state(run.status)

        with pytest.raises(InvalidStateTransitionError):
            transition_run(run, RunStatus.INVESTIGATING)
        with pytest.raises(InvalidStateTransitionError):
            transition_run(run, RunStatus.QUEUED)
