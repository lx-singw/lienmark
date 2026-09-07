"""
Sprint 4.1 Acceptance Gate: tests/test_clarification_flow.py

Validates end-to-end suspension flow when an ambiguous screenplay cue is fed:
1. Cue: 'an uncredited jazz solo plays in the background of the diner scene'.
2. Primary research pass flags rights ambiguity (no composer/publisher identified).
3. Pipeline enters suspension:
   - Run status transitions to waiting_for_information.
   - ClarificationRequest generated with specific question, required document, role.
   - Valid ExecutionCheckpoint persisted with SHA-256 resume token.
   - Worker threads/tasks cleanly release with zero lingering tasks.
4. Resumption verifies unblocking upon license arrival.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Tuple
import pytest

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    ClarificationRequest,
    WorkflowReason,
)
from backend.agents.clarification import (
    ClarificationGenerator,
    ClarificationInput,
    DocumentTypeRequirement,
    ProductionRole,
    TargetedClarification,
)
from backend.orchestration.adk_pipeline import EvidenceDrivenCoordinator
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    ExecutionCheckpoint,
    SuspensionReason,
    SuspensionState,
    validate_resume_token,
)
from backend.orchestration.resource_releaser import ResourceReleaser
from backend.orchestration.suspension import SuspensionManager


def _build_ambiguous_jazz_claim() -> AtomicRightsClaim:
    """Builds atomic claim for ambiguous diner jazz cue."""
    return AtomicRightsClaim(
        claim_id="clm_scene14_jazz_solo",
        occurrence_id="occ_scene14_diner_jazz",
        occurrence_lineage_id="lineage_diner_jazz_solo",
        right_category="music",
        rights_subject="uncredited jazz solo",
        intended_territory=["Worldwide"],
        intended_media=["theatrical", "streaming"],
        intended_context="diner scene background",
        disposition=CensusDisposition.NEEDS_REVIEW,
        notes="an uncredited jazz solo plays in the background of the diner scene",
    )


def _setup_mock_worker_resources() -> Tuple[List[asyncio.Task], List[threading.Lock], Dict[str, Any]]:
    """Creates active tasks, locks, and handles to verify defensive teardown."""
    loop = asyncio.new_event_loop()
    task = loop.create_task(asyncio.sleep(30))
    lock = threading.Lock()
    lock.acquire()
    worker_refs = {"worker_id": "wrk_music_01", "context": {"thread_id": 992}}
    return [task], [lock], worker_refs


def test_acceptance_primary_research_flags_ambiguity():
    """Acceptance Step 1 & 2: Flags rights ambiguity and generates specific question."""
    generator = ClarificationGenerator(use_fallback=True)
    cue_text = "an uncredited jazz solo plays in the background of the diner scene"

    clrf_input = ClarificationInput(
        claim_id="clm_scene14_jazz_solo",
        category="music",
        scene_anchor="Scene 14, 00:18:22",
        asset_name_or_cue="uncredited jazz solo",
        context_snippet=cue_text,
        flagged_reason="No composer, songwriter, or publisher identified in public copyright registries",
        revision_id="v8",
        stable_lineage_key="lineage_diner_jazz_solo",
    )
    result = generator.generate_clarification_sync(clrf_input)

    assert isinstance(result, TargetedClarification)
    assert "Scene 14, 00:18:22" in result.scene_anchor
    assert "uncredited jazz solo" in result.question_text.lower()
    assert result.designated_role in (
        ProductionRole.MUSIC_SUPERVISOR.value,
        ProductionRole.PRODUCER.value,
    )
    assert result.required_document_type in (
        DocumentTypeRequirement.SYNC_LICENSE.value,
        DocumentTypeRequirement.MASTER_USE_LICENSE.value,
    )
    assert len(result.suggested_options) >= 2


def test_acceptance_pipeline_enters_suspension_with_clean_worker_release():
    """Acceptance Step 3: Status is waiting_for_information, valid checkpoint, zero lingering tasks."""
    claim = _build_ambiguous_jazz_claim()
    active_tasks, active_locks, workers = _setup_mock_worker_resources()
    suspension_mgr = SuspensionManager()

    snapshot = AgentMemorySnapshot(
        findings=[{"subject": "ASCAP/BMI", "result": "0 matches"}],
        subgoals=["locate_master_rights_holder"],
        context_variables={"cue_type": "jazz_solo", "scene": "diner"},
    )

    checkpoint = suspension_mgr.suspend_investigation(
        tenant_id="org_paramount_01",
        production_id="prod_diner_noir_v8",
        run_id="run_v8_reval_001",
        claim_id=claim.claim_id,
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_jazz_001"],
        active_tasks=active_tasks,
        active_locks=active_locks,
        worker_handles=workers,
    )

    # Invariant A: Run / Claim status transitions to waiting_for_information
    assert suspension_mgr.states[claim.claim_id] == SuspensionState.WAITING_FOR_INFORMATION

    # Invariant B: Valid ExecutionCheckpoint persisted with SHA-256 resume token
    assert checkpoint.checkpoint_id.startswith("chk_")
    assert len(checkpoint.resume_token) == 64
    assert validate_resume_token(checkpoint, checkpoint.resume_token) is True
    assert checkpoint.paused_stage == "ACT_06_REQUEST_INFORMATION"

    # Invariant C: Worker threads cleanly release with zero lingering tasks or locks
    assert all(t.cancelling() > 0 or t.cancelled() for t in active_tasks)
    assert all(not l.locked() for l in active_locks)
    assert len(workers) == 0


def test_acceptance_coordinator_claim_level_suspension():
    """Acceptance Step 4: EvidenceDrivenCoordinator integrates suspension with domain models."""
    coord = EvidenceDrivenCoordinator(
        run_id="run_diner_001",
        revision_id="v8",
        use_fallback=True,
    )
    jazz_claim = _build_ambiguous_jazz_claim()
    coord.register_claim(jazz_claim)

    clrf = coord.suspend_claim(
        claim=jazz_claim,
        question_text="Uncredited jazz solo requires confirmed licensing source.",
        required_document_type="Executed Synchronization License",
        suggested_options=["Commissioned score", "Commercial sync license"],
        assigned_role="Music Supervisor",
    )

    assert coord.claim_states[jazz_claim.claim_id] == "waiting_for_information"
    assert jazz_claim.workflow_reason == WorkflowReason.WAITING_FOR_INFORMATION
    assert jazz_claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert isinstance(clrf, ClarificationRequest)
    assert clrf.required_document_type == "Executed Synchronization License"
    assert clrf.status == "pending"


def test_acceptance_checkpoint_resumption_unblocks_pipeline():
    """Acceptance Step 5: Providing required document restores execution and unblocks claim."""
    claim = _build_ambiguous_jazz_claim()
    suspension_mgr = SuspensionManager()
    snapshot = AgentMemorySnapshot(subgoals=["locate_master_rights_holder"])

    cp = suspension_mgr.suspend_investigation(
        tenant_id="org_paramount_01",
        production_id="prod_diner_noir_v8",
        run_id="run_v8_reval_001",
        claim_id=claim.claim_id,
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_jazz_001"],
    )

    active_uses = [{"claim_id": claim.claim_id, "title": "uncredited jazz solo"}]
    resumed = suspension_mgr.resume_investigation(
        checkpoint_id=cp.checkpoint_id,
        resume_token=cp.resume_token,
        current_revision_uses=active_uses,
    )

    assert resumed["status"] == SuspensionState.RESUMING.value
    assert resumed["claim_id"] == claim.claim_id
    assert suspension_mgr.states[claim.claim_id] == SuspensionState.RESUMING
