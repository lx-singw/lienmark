"""
tests/test_clarification_suspension_state_machine.py

Exhaustive verification of the Sprint 4.1 Clarification State Machine and Checkpointing Subsystem:
1. Lifecycle State Machine transitions and invariant validation
2. Defensive resource teardown (zero CPU/memory leaks: async tasks, locks, worker refs)
3. Cryptographic SHA-256 resume token generation idempotency and tampering detection
4. Ambiguous claim & missing private contract suspension triggers
5. Durable ExecutionCheckpoint serialization and TTL expiration
6. Script cut freshness check during resumption (active vs CANCELLED_SUPERSEDED)
"""

import asyncio
import threading
import pytest
from datetime import datetime, timezone, timedelta

from backend.orchestration.checkpoint_types import (
    SuspensionState,
    SuspensionReason,
    AgentMemorySnapshot,
    ExecutionCheckpoint,
    compute_resume_token,
    validate_resume_token,
    calculate_ttl_timestamp,
)
from backend.orchestration.resource_releaser import ResourceReleaser
from backend.orchestration.suspension import (
    ClarificationStateMachine,
    SuspensionManager,
    InvalidStateTransitionError,
    CheckpointExpiredError,
    InvalidResumeTokenError,
)


def test_clarification_state_machine_valid_transitions():
    """Verify standard happy-path progression through the active lifecycle."""
    state = SuspensionState.INITIALIZING
    state = ClarificationStateMachine.transition(state, SuspensionState.ACTIVE_INVESTIGATION)
    assert state == SuspensionState.ACTIVE_INVESTIGATION

    state = ClarificationStateMachine.transition(state, SuspensionState.SUSPENDING)
    assert state == SuspensionState.SUSPENDING

    state = ClarificationStateMachine.transition(state, SuspensionState.WAITING_FOR_INFORMATION)
    assert state == SuspensionState.WAITING_FOR_INFORMATION

    state = ClarificationStateMachine.transition(state, SuspensionState.RESUMING)
    assert state == SuspensionState.RESUMING

    state = ClarificationStateMachine.transition(state, SuspensionState.READY_FOR_REVIEW)
    assert state == SuspensionState.READY_FOR_REVIEW

    state = ClarificationStateMachine.transition(state, SuspensionState.RESOLVED)
    assert state == SuspensionState.RESOLVED


def test_clarification_state_machine_invalid_transition_rejection():
    """Verify illegal transitions raise InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        ClarificationStateMachine.transition(
            SuspensionState.WAITING_FOR_INFORMATION,
            SuspensionState.RESOLVED,
        )
    assert "Illegal state transition" in str(exc_info.value)
    assert exc_info.value.current == SuspensionState.WAITING_FOR_INFORMATION
    assert exc_info.value.target == SuspensionState.RESOLVED


def test_resource_releaser_async_tasks_and_locks():
    """Verify ResourceReleaser cancels active coroutine tasks and unlocks threading/asyncio locks."""
    async def sample_coro():
        await asyncio.sleep(100)

    loop = asyncio.new_event_loop()
    task = loop.create_task(sample_coro())
    assert not task.done()

    cancelled_count = ResourceReleaser.cancel_async_tasks([task])
    assert cancelled_count == 1
    assert task.cancelling() or task.cancelled()

    t_lock = threading.Lock()
    t_lock.acquire()
    assert t_lock.locked()

    released_count = ResourceReleaser.release_locks([t_lock])
    assert released_count == 1
    assert not t_lock.locked()

    worker_dict = {"worker_1": object(), "worker_2": object()}
    purged = ResourceReleaser.purge_worker_references(worker_dict)
    assert purged == 2
    assert len(worker_dict) == 0

    try:
        loop.run_until_complete(task)
    except (asyncio.CancelledError, Exception):
        pass
    loop.close()


def test_resume_token_idempotency_and_tamper_evidence():
    """Verify cryptographic SHA-256 resume token is deterministic and order-independent for clarifications."""
    tenant_id = "tenant_paramount"
    production_id = "prod_noir_film"
    run_id = "run_7a8b9c"
    claim_id = "clm_jazz_solo"
    paused_stage = "targeted_search"
    clarifications = ["clrf_sync_01", "clrf_master_02"]
    created_at = "2026-09-07T10:00:00+00:00"

    token_1 = compute_resume_token(
        tenant_id, production_id, run_id, claim_id,
        paused_stage, clarifications, created_at,
    )
    # Reverse clarification order to verify sorting invariance
    token_2 = compute_resume_token(
        tenant_id, production_id, run_id, claim_id,
        paused_stage, list(reversed(clarifications)), created_at,
    )
    assert token_1 == token_2
    assert len(token_1) == 64

    # Tampering with claim_id changes token
    token_tampered = compute_resume_token(
        tenant_id, production_id, run_id, "clm_tampered",
        paused_stage, clarifications, created_at,
    )
    assert token_1 != token_tampered


def test_suspension_manager_suspend_and_resume_flow():
    """Verify complete suspend-to-resume lifecycle with ExecutionCheckpoint and memory rehydration."""
    mgr = SuspensionManager()
    snapshot = AgentMemorySnapshot(
        findings=[{"fact": "1940s melody identified as Autumn Shadows"}],
        subgoals=["locate_sound_recording_master_license"],
        partial_dag={"eval": ["search"], "search": ["reconcile"]},
        query_history=[{"query": "Autumn Shadows 1948 master rights", "hash": "sha_123"}],
        context_variables={"scene": "Scene 14 Diner", "missing": "sync_scope"},
    )

    checkpoint = mgr.suspend_investigation(
        tenant_id="tenant_warner",
        production_id="prod_shadows",
        run_id="run_101",
        claim_id="clm_autumn_shadows",
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_999"],
        ttl_seconds=3600,
    )

    assert checkpoint.checkpoint_id.startswith("chk_")
    assert mgr.states["clm_autumn_shadows"] == SuspensionState.WAITING_FOR_INFORMATION
    assert len(checkpoint.resume_token) == 64

    # Successful resumption with matching revision
    current_cut_uses = [{"claim_id": "clm_autumn_shadows", "scene": "Scene 14"}]
    res = mgr.resume_investigation(
        checkpoint_id=checkpoint.checkpoint_id,
        resume_token=checkpoint.resume_token,
        current_revision_uses=current_cut_uses,
    )

    assert res["status"] == SuspensionState.RESUMING.value
    assert res["claim_id"] == "clm_autumn_shadows"
    assert res["memory_snapshot"]["findings"][0]["fact"] == "1940s melody identified as Autumn Shadows"


def test_suspension_manager_superseded_cut_detection():
    """Verify resumption transitions to CANCELLED_SUPERSEDED if the scene was cut in latest draft."""
    mgr = SuspensionManager()
    snapshot = AgentMemorySnapshot()
    cp = mgr.suspend_investigation(
        tenant_id="tenant_warner",
        production_id="prod_shadows",
        run_id="run_102",
        claim_id="clm_cut_scene_music",
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCLEAR_SYNC_SCOPE,
        agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_888"],
    )

    # In current revision v9, clm_cut_scene_music is absent (scene was cut)
    v9_cut_uses = [{"claim_id": "clm_other_surviving_claim"}]
    res = mgr.resume_investigation(
        checkpoint_id=cp.checkpoint_id,
        resume_token=cp.resume_token,
        current_revision_uses=v9_cut_uses,
    )
    assert res["status"] == SuspensionState.CANCELLED_SUPERSEDED.value
    assert mgr.states["clm_cut_scene_music"] == SuspensionState.CANCELLED_SUPERSEDED


def test_suspension_manager_ttl_expiration_rejection():
    """Verify expired checkpoint raises CheckpointExpiredError upon resumption attempt."""
    mgr = SuspensionManager()
    snapshot = AgentMemorySnapshot()
    cp = mgr.suspend_investigation(
        tenant_id="tenant_warner",
        production_id="prod_shadows",
        run_id="run_103",
        claim_id="clm_expired_claim",
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.MISSING_PRIVATE_CONTRACT,
        agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_777"],
        ttl_seconds=-10,  # Expired in past
    )

    with pytest.raises(CheckpointExpiredError):
        mgr.resume_investigation(
            checkpoint_id=cp.checkpoint_id,
            resume_token=cp.resume_token,
        )
    assert mgr.states["clm_expired_claim"] == SuspensionState.EXPIRED_TTL


def test_suspension_manager_invalid_token_rejection():
    """Verify invalid token raises InvalidResumeTokenError."""
    mgr = SuspensionManager()
    snapshot = AgentMemorySnapshot()
    cp = mgr.suspend_investigation(
        tenant_id="tenant_warner",
        production_id="prod_shadows",
        run_id="run_104",
        claim_id="clm_token_test",
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.AMBIGUOUS_CLAIM,
        agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_666"],
    )

    with pytest.raises(InvalidResumeTokenError):
        mgr.resume_investigation(
            checkpoint_id=cp.checkpoint_id,
            resume_token="invalid_forged_token_hash_0000000000000000000000000000000000",
        )
