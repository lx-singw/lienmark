"""
tests/test_resumption_pipeline.py

Comprehensive test suite verifying Milestone D Resumption Pipeline Service.
Tests atomic enqueueing, expiring worker lease fencing, storage freshness validation,
blocker and budget limits, zero-waste hydration, downstream action execution,
sweeper recovery of stranded leases, and unified ResumptionCoordinator entrypoints.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from backend.domain.models import ClarificationRequest
from backend.orchestration.adk_pipeline import EvidenceDrivenCoordinator
from backend.orchestration.budget_governor import ExecutionBudgetGovernor
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    ExecutionCheckpoint as OrchCheckpoint,
    SuspensionState,
    compute_resume_token,
)
from backend.orchestration.resumption import ResumptionCoordinator
from backend.orchestration.resumption_pipeline import ResumptionPipelineService
from backend.orchestration.resumption_types import (
    NextStageType,
    ResolutionPayload,
    ResumptionDispatchStatus,
    ResumptionStatus,
)
from backend.orchestration.suspension import SuspensionManager
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_types import AgentStateVector, ExecutionCheckpoint as StorageCheckpoint
from backend.storage.clarification_store import ClarificationStore
import tempfile


def _build_test_checkpoint(
    claim_id: str = "clm_jazz_pipeline",
    run_id: str = "run_pipe_01",
    subgoals: Optional[List[str]] = None,
    pending_clrf: Optional[List[str]] = None,
) -> Tuple[OrchCheckpoint, str]:
    """Helper to construct valid ExecutionCheckpoint and SHA-256 token."""
    now_utc = datetime.now(timezone.utc)
    sgs = subgoals if subgoals is not None else ["subgoal_sync_license", "subgoal_master_rights"]
    clrfs = pending_clrf if pending_clrf is not None else ["clrf_jazz_01"]
    token = compute_resume_token(
        tenant_id="tenant_sony", production_id="prod_pipe_01", run_id=run_id,
        claim_id=claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        pending_clarification_ids=clrfs, created_at_utc=now_utc.isoformat(),
    )
    cp = OrchCheckpoint(
        checkpoint_id="chk_pipe_001", run_id=run_id, tenant_id="tenant_sony",
        production_id="prod_pipe_01", claim_id=claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        agent_memory_snapshot=AgentMemorySnapshot(
            findings=[{"entity": "BMI", "status": "no_match"}],
            subgoals=sgs,
            partial_dag={"node_01": ["node_02"]},
            query_history=[{"query": "Blue Monk Thelonious Monk"}],
            context_variables={"track_title": "Blue Monk"},
        ),
        pending_clarification_ids=clrfs, resume_token=token,
        created_at_utc=now_utc.isoformat(),
        ttl_expires_at_utc=(now_utc + timedelta(days=2)).isoformat(),
    )
    return cp, token


def test_enqueue_resumption_atomic_commit_and_queued_status():
    """Verifies atomic clarification commit and dispatch creation with queued status."""
    store = ClarificationStore()
    mgr = SuspensionManager()
    service = ResumptionPipelineService(suspension_manager=mgr, clarification_store=store)

    clrf = ClarificationRequest(
        request_id="clrf_jazz_01", run_id="run_pipe_01", claim_id="clm_jazz_pipeline",
        stable_lineage_key="lineage_jazz_01", question_text="Confirm sync license scope.",
        tenant_id="tenant_sony", production_id="prod_pipe_01", status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="tenant_sony", production_id="prod_pipe_01")
    mgr.states["clm_jazz_pipeline"] = SuspensionState.WAITING_FOR_INFORMATION

    res = ResolutionPayload(
        resolution_id="res_001", claim_id="clm_jazz_pipeline", clarification_id="clrf_jazz_01",
        provided_facts={"scope": "worldwide"}, attached_documents=["agr_sony_01"],
    )
    dispatch = service.enqueue_resumption(
        tenant_id="tenant_sony", production_id="prod_pipe_01", run_id="run_pipe_01",
        claim_id="clm_jazz_pipeline", checkpoint_id="chk_pipe_001", resolution_payload=res,
        resume_token="tok_123", checkpoint_revision=2,
    )

    assert dispatch.status == "queued for resumption"
    assert dispatch.checkpoint_revision == 2
    assert dispatch.claim_id == "clm_jazz_pipeline"
    saved_clrf = store.get_clarification("clrf_jazz_01", tenant_id="tenant_sony")
    assert saved_clrf is not None and saved_clrf.status == "resolved"


def test_worker_execution_loop_fencing_lease_and_status():
    """Verifies worker loop acquires expiring fenced lease and updates status to investigation resumed."""
    cp, token = _build_test_checkpoint(subgoals=[])
    mgr = SuspensionManager()
    mgr.checkpoints[cp.checkpoint_id] = cp
    adk = EvidenceDrivenCoordinator(use_fallback=True)
    service = ResumptionPipelineService(suspension_manager=mgr, adk_coordinator=adk)

    dispatch = service.enqueue_resumption(
        tenant_id=cp.tenant_id, production_id=cp.production_id, run_id=cp.run_id,
        claim_id=cp.claim_id, checkpoint_id=cp.checkpoint_id, resume_token=token,
    )
    processed = service.execute_dispatch(dispatch.dispatch_id, worker_id="worker_alpha_01", lease_seconds=300.0)

    assert processed.status == "investigation resumed"
    assert processed.fencing_token is not None and processed.fencing_token >= 1
    assert processed.worker_id == "worker_alpha_01"
    assert processed.execution_result is not None
    assert adk.claim_states[cp.claim_id] == "active_investigation"


def test_zero_waste_skips_completed_subgoals_no_respend():
    """Verifies zero-waste hydration freezes upstream queries and skips completed subgoals."""
    service = ResumptionPipelineService()
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = CheckpointStore(base_output_dir=tmp_dir, force_local=True)
        agent_state = AgentStateVector(
            active_role="clearance_investigator", current_step="resuming",
            active_claim_ids=["clm_jazz_pipeline"], completed_step_count=2,
        )
        cp = store.create_checkpoint(
            tenant_id="tenant_sony", production_id="prod_pipe_01", run_id="run_pipe_01",
            agent_state=agent_state, uncompleted_subgoals=[
                {"id": "sg_sync_license", "status": "completed"},
                {"id": "sg_master_rights", "status": "pending"},
            ],
            investigation_dag={"node_01": ["node_02"]},
        )

        memory, skipped = service.hydrate_memory(cp, resolution=None)
        assert skipped == 1
        assert "sg_sync_license" in memory.completed_subgoals
        assert len(memory.uncompleted_subgoals) == 1
        assert memory.uncompleted_subgoals[0]["id"] == "sg_master_rights"
        assert memory.upstream_frozen_count >= 1

        stage = service.determine_next_stage("clm_jazz_pipeline", memory, resolution=None)
        assert stage.stage_type == NextStageType.NEXT_INVESTIGATION_NODE
        assert stage.pending_node_id == "sg_master_rights"


def test_blocker_recheck_blocks_resumption_if_clarification_open():
    """Verifies worker execution halts when remaining blocker clarifications are unresolved."""
    store = ClarificationStore()
    cp, token = _build_test_checkpoint(pending_clrf=["clrf_01", "clrf_02"])
    mgr = SuspensionManager()
    mgr.checkpoints[cp.checkpoint_id] = cp

    for cid in ["clrf_01", "clrf_02"]:
        store.save_clarification(
            ClarificationRequest(
                request_id=cid, run_id=cp.run_id, claim_id=cp.claim_id,
                stable_lineage_key=f"lineage_{cid}", question_text=f"Question {cid}",
                tenant_id=cp.tenant_id, production_id=cp.production_id, status="waiting_for_information",
            ),
            tenant_id=cp.tenant_id, production_id=cp.production_id,
        )

    service = ResumptionPipelineService(suspension_manager=mgr, clarification_store=store)
    res = ResolutionPayload(resolution_id="res_01", claim_id=cp.claim_id, clarification_id="clrf_01")
    dispatch = service.enqueue_resumption(
        tenant_id=cp.tenant_id, production_id=cp.production_id, run_id=cp.run_id,
        claim_id=cp.claim_id, checkpoint_id=cp.checkpoint_id, resolution_payload=res, resume_token=token,
    )
    result = service.execute_dispatch(dispatch.dispatch_id)

    assert result.status == ResumptionDispatchStatus.BLOCKED.value
    assert "clrf_02" in (result.error_message or "")


def test_budget_cap_blocks_resumption():
    """Verifies mid-flight budget cap breach transitions dispatch to blocked status."""
    cp, token = _build_test_checkpoint()
    mgr = SuspensionManager()
    mgr.checkpoints[cp.checkpoint_id] = cp
    governor = ExecutionBudgetGovernor(default_max_run_spend_usd=10.0)
    governor._run_spend[cp.run_id] = 15.0

    service = ResumptionPipelineService(suspension_manager=mgr, budget_governor=governor)
    dispatch = service.enqueue_resumption(
        tenant_id=cp.tenant_id, production_id=cp.production_id, run_id=cp.run_id,
        claim_id=cp.claim_id, checkpoint_id=cp.checkpoint_id, resume_token=token,
    )
    result = service.execute_dispatch(dispatch.dispatch_id)

    assert result.status == ResumptionDispatchStatus.BLOCKED.value
    assert "budget cap" in (result.error_message or "").lower()


def test_sweeper_recovers_abandoned_dispatches_with_expired_leases():
    """Verifies sweeper identifies expired worker leases and resets them to queued for resumption."""
    service = ResumptionPipelineService()
    past_utc = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    d = service.enqueue_resumption(
        tenant_id="tenant_01", production_id="prod_01", run_id="run_01",
        claim_id="clm_abandoned", checkpoint_id="chk_01",
    )
    d.status = ResumptionDispatchStatus.PROCESSING.value
    d.worker_id = "dead_worker_99"
    d.lease_expires_at_utc = past_utc

    recovered = service.sweep_and_recover_abandoned_dispatches()
    assert len(recovered) == 1
    assert recovered[0].dispatch_id == d.dispatch_id
    assert recovered[0].status == "queued for resumption"
    assert recovered[0].worker_id is None
    assert recovered[0].retry_count == 1


def test_resumption_coordinator_unified_resume_from_clarification():
    """Verifies unified resume_from_clarification on ResumptionCoordinator enqueues and executes."""
    cp, token = _build_test_checkpoint(subgoals=[])
    mgr = SuspensionManager()
    mgr.checkpoints[cp.checkpoint_id] = cp
    mgr.states[cp.claim_id] = SuspensionState.WAITING_FOR_INFORMATION
    adk = EvidenceDrivenCoordinator(use_fallback=True)

    coord = ResumptionCoordinator(suspension_manager=mgr, adk_coordinator=adk)
    res = ResolutionPayload(
        resolution_id="res_unify", claim_id=cp.claim_id,
        provided_facts={"publisher": "Blue Note", "rights_cleared": True},
    )
    result = coord.resume_from_clarification(
        claim_id=cp.claim_id, resolution_payload=res, resume_token=token,
    )

    assert result.status == ResumptionStatus.SUCCESS
    assert result.current_state == SuspensionState.ACTIVE_INVESTIGATION
    assert result.next_stage is not None
    assert result.next_stage.dispatch_id is not None
    assert adk.claim_states[cp.claim_id] == "active_investigation"
    assert adk.claim_contexts[cp.claim_id]["rights_cleared"] is True
