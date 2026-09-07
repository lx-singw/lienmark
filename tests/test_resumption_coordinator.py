"""
tests/test_resumption_coordinator.py

Comprehensive test suite verifying Sprint 4.2 Checkpoint Hydration and
Incremental Investigation Resumption subsystem.
Tests cryptographic token verification, TTL evaluation, script cut freshness,
zero-waste re-query invariants, and stage dispatch.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from typing import Tuple
import pytest

from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    ExecutionCheckpoint as OrchCheckpoint,
    SuspensionState,
    compute_resume_token,
)
from backend.orchestration.resumption import ResumptionCoordinator
from backend.orchestration.resumption_types import (
    NextStageType,
    ResolutionPayload,
    ResumptionResult,
    ResumptionStatus,
)
from backend.orchestration.suspension import SuspensionManager
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_types import AgentStateVector
from backend.orchestration.adk_pipeline import EvidenceDrivenCoordinator


def _build_test_orchestration_checkpoint(
    claim_id: str = "clm_jazz_solo",
    run_id: str = "run_test_01",
    is_expired: bool = False,
    subgoals: Optional[list] = None,
) -> Tuple[OrchCheckpoint, str]:
    """Helper to build a test orchestration checkpoint with valid token."""
    now_utc = datetime.now(timezone.utc)
    created_str = now_utc.isoformat()
    ttl_dt = now_utc - timedelta(days=1) if is_expired else now_utc + timedelta(days=2)
    sgs = ["subgoal_sync_license", "subgoal_master_recording"] if subgoals is None else subgoals
    token = compute_resume_token(
        tenant_id="tenant_01", production_id="prod_01", run_id=run_id,
        claim_id=claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        pending_clarification_ids=["clrf_01"], created_at_utc=created_str,
    )
    cp = OrchCheckpoint(
        checkpoint_id="chk_orch_01", run_id=run_id, tenant_id="tenant_01",
        production_id="prod_01", claim_id=claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        agent_memory_snapshot=AgentMemorySnapshot(
            findings=[{"entity": "USCO", "status": "no_match"}],
            subgoals=sgs,
            partial_dag={"node_01": ["node_02"]},
            query_history=[{"query": "Blue Monk Thelonious Monk"}],
            context_variables={"track_title": "Blue Monk"},
        ),
        pending_clarification_ids=["clrf_01"], resume_token=token,
        created_at_utc=created_str, ttl_expires_at_utc=ttl_dt.isoformat(),
    )
    return cp, token


def test_resume_run_success_with_next_investigation_node():
    """Verifies successful resumption hydrates memory and dispatches next investigation node."""
    mgr = SuspensionManager()
    cp, token = _build_test_orchestration_checkpoint()
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    coord = ResumptionCoordinator(suspension_manager=mgr)
    result = coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token=token)

    assert result.status == ResumptionStatus.SUCCESS
    assert result.current_state == SuspensionState.ACTIVE_INVESTIGATION
    assert result.reinvestigated_upstream_count == 0
    assert result.hydrated_memory is not None
    assert result.hydrated_memory.upstream_frozen_count >= 1
    assert result.next_stage is not None
    assert result.next_stage.stage_type == NextStageType.NEXT_INVESTIGATION_NODE


def test_resume_run_with_resolution_payload_dispatches_targeted_agreement():
    """Verifies resolution payload with attached agreement routes to targeted agreement verification."""
    mgr = SuspensionManager()
    cp, token = _build_test_orchestration_checkpoint()
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    coord = ResumptionCoordinator(suspension_manager=mgr)
    resolution = ResolutionPayload(
        resolution_id="res_01", claim_id=cp.claim_id, clarification_id="clrf_01",
        resolved_by="production_counsel", provided_facts={"licensee": "Paramount", "scope": "Worldwide"},
        attached_documents=["agr_warner_sync_001"], notes="Confirmed executed sync license agreement.",
    )
    result = coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token=token, resolution_payload=resolution)

    assert result.status == ResumptionStatus.SUCCESS
    assert result.next_stage is not None
    assert result.next_stage.stage_type == NextStageType.TARGETED_AGREEMENT_VERIFICATION
    assert result.next_stage.stage_action == "ACT_01_RETRIEVE_PRIVATE_AGREEMENTS"
    assert "attached_contracts" in result.hydrated_memory.context_variables


def test_resume_run_rejects_invalid_token():
    """Verifies cryptographic validation blocks resumption with bad token."""
    mgr = SuspensionManager()
    cp, _ = _build_test_orchestration_checkpoint()
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    coord = ResumptionCoordinator(suspension_manager=mgr)
    result = coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token="corrupted_token_value")

    assert result.status == ResumptionStatus.TOKEN_INVALID
    assert "token verification failed" in (result.error_message or "").lower()


def test_resume_run_rejects_expired_ttl():
    """Verifies expired checkpoint TTL transitions claim to EXPIRED_TTL."""
    mgr = SuspensionManager()
    cp, token = _build_test_orchestration_checkpoint(is_expired=True)
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    coord = ResumptionCoordinator(suspension_manager=mgr)
    result = coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token=token)

    assert result.status == ResumptionStatus.EXPIRED_TTL
    assert result.current_state == SuspensionState.EXPIRED_TTL
    assert mgr.states[cp.claim_id] == SuspensionState.EXPIRED_TTL


def test_resume_run_detects_superseded_claim():
    """Verifies claim dropped from latest script revision is marked CANCELLED_SUPERSEDED."""
    mgr = SuspensionManager()
    cp, token = _build_test_orchestration_checkpoint(claim_id="clm_scene12_cut_out")
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    coord = ResumptionCoordinator(suspension_manager=mgr)
    revision_uses = [{"claim_id": "clm_scene01_intro"}, {"claim_id": "clm_scene05_chase"}]
    result = coord.resume_run(
        checkpoint_id=cp.checkpoint_id, resume_token=token, current_revision_uses=revision_uses
    )

    assert result.status == ResumptionStatus.CANCELLED_SUPERSEDED
    assert result.current_state == SuspensionState.CANCELLED_SUPERSEDED
    assert mgr.states[cp.claim_id] == SuspensionState.CANCELLED_SUPERSEDED


def test_resume_run_from_persistent_checkpoint_store():
    """Verifies checkpoint hydration from durable CheckpointStore filesystem layer."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = CheckpointStore(base_output_dir=tmp_dir, force_local=True)
        agent_state = AgentStateVector(
            active_role="clearance_investigator", current_step="ACT_06_REQUEST_INFORMATION",
            pending_clarification_ids=["clrf_99"], active_claim_ids=["clm_neon_billboard"],
            completed_step_count=4, context_variables={"brand": "NeonCorp"},
        )
        saved = store.create_checkpoint(
            tenant_id="org_sony", production_id="prod_cyber", run_id="run_101",
            agent_state=agent_state, uncompleted_subgoals=[
                {"id": "sg_trademark_check", "status": "completed"},
                {"id": "sg_sync_license", "status": "pending"},
            ],
        )
        store.save_checkpoint(saved)

        coord = ResumptionCoordinator(checkpoint_store=store)
        result = coord.resume_run(
            checkpoint_id=saved.checkpoint_id, resume_token=saved.resume_token,
            tenant_id="org_sony", production_id="prod_cyber", run_id="run_101",
        )

        assert result.status == ResumptionStatus.SUCCESS
        assert result.claim_id == "clm_neon_billboard"
        assert result.reinvestigated_upstream_count == 0
        assert result.skipped_completed_subgoals == 1
        assert result.hydrated_memory.completed_step_count == 4
        assert result.hydrated_memory.completed_subgoals == ["sg_trademark_check"]


def test_resume_run_adk_integration_and_review_dispatch():
    """Verifies seamless synchronization with EvidenceDrivenCoordinator and review brief dispatch."""
    adk_coord = EvidenceDrivenCoordinator(use_fallback=True)
    mgr = SuspensionManager()
    cp, token = _build_test_orchestration_checkpoint(subgoals=[])
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    res_coord = ResumptionCoordinator(suspension_manager=mgr, adk_coordinator=adk_coord)
    resolution = ResolutionPayload(
        resolution_id="res_02", claim_id=cp.claim_id,
        provided_facts={"author": "Monk", "verified": True},
    )
    result = res_coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token=token, resolution_payload=resolution)

    assert result.status == ResumptionStatus.SUCCESS
    assert result.next_stage.stage_type == NextStageType.READY_FOR_REVIEW
    assert result.next_stage.stage_action == "ACT_07_PREPARE_REVIEW_BRIEF"
    assert adk_coord.claim_states[cp.claim_id] == "active_investigation"
    assert adk_coord.claim_contexts[cp.claim_id]["clarification_resolved"] is True
    assert adk_coord.claim_contexts[cp.claim_id]["author"] == "Monk"
