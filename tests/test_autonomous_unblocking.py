"""
tests/test_autonomous_unblocking.py

Sprint 4.2 Acceptance Gate: Autonomous Folder-Arrival Unblocking and Resumption.
End-to-end integration test executing the full unblocking lifecycle:
1. Script run suspended on ambiguous music cue (WAITING_FOR_INFORMATION).
2. Simulated folder arrival of mock_sync_license.pdf into watched storage.
3. DocumentMatcher metadata extraction (Licensor, Asset, Type).
4. Dual-key matching (confidence > 0.85), auto-resolution, and ResumptionCoordinator invocation.
5. Checkpoint hydration, zero upstream re-querying, agreement verification, pipeline READY_FOR_REVIEW.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import time
import pytest

from backend.domain.models import CensusDisposition, ClarificationRequest
from backend.orchestration.adk_pipeline import EvidenceDrivenCoordinator
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    SuspensionReason,
    SuspensionState,
    validate_resume_token,
)
from backend.orchestration.resumption import ResumptionCoordinator
from backend.orchestration.resumption_types import (
    NextStageType,
    ResolutionPayload,
    ResumptionStatus,
)
from backend.orchestration.suspension import ClarificationStateMachine, SuspensionManager
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.agreement_verifier import AgreementVerifier
from backend.services.agreement_verifier_types import ProductionRequirements, RightType, VerificationStatus
from backend.services.document_matcher import DocumentMatcherService
from backend.services.document_matcher_types import DocumentArrivalEvent, MatchingDecision
from backend.storage.clarification_store import ClarificationStore
from tests.fixtures_resumption import (
    build_diner_jazz_claim,
    create_verified_doc_input,
    mock_sync_license_content,
)


def test_step_1_run_enters_suspension():
    """Step 1: Suspends run, creates clarification request and valid checkpoint."""
    mgr, store = SuspensionManager(), ClarificationStore()
    claim = build_diner_jazz_claim()
    snapshot = AgentMemorySnapshot(
        findings=[{"registry": "ASCAP", "status": "no_match"}],
        subgoals=["subgoal_sync_license", "subgoal_master_rights"],
        query_history=[{"query": "diner jazz solo Blue Note"}],
        context_variables={"cue": "jazz_solo", "scene": "14"},
    )
    cp = mgr.suspend_investigation(
        tenant_id="tenant_paramount", production_id="prod_diner_noir_v8", run_id="run_diner_001",
        claim_id=claim.claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_jazz_001"],
    )
    clrf = ClarificationRequest(
        request_id="clrf_jazz_001", run_id="run_diner_001", claim_id=claim.claim_id,
        stable_lineage_key="lineage_diner_jazz_cue",
        question_text="Scene 14: Uncredited jazz solo ('Diner Jazz Solo Cue') requires sync license.",
        required_document_type="Executed Synchronization License",
        tenant_id="tenant_paramount", production_id="prod_diner_noir_v8", status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="tenant_paramount", production_id="prod_diner_noir_v8")

    assert mgr.states[claim.claim_id] == SuspensionState.WAITING_FOR_INFORMATION
    assert validate_resume_token(cp, cp.resume_token) is True
    assert clrf.required_document_type == "Executed Synchronization License"


def test_step_2_to_4_folder_arrival_matching_and_auto_resumption():
    """Steps 2-4: Storage folder arrival extracts metadata and executes dual-key auto-resolution."""
    store, mgr = ClarificationStore(), SuspensionManager()
    clrf = ClarificationRequest(
        request_id="clrf_jazz_001", claim_id="clm_scene14_diner_jazz",
        stable_lineage_key="lineage_diner_jazz_cue",
        question_text="Scene 14: Uncredited jazz solo ('Diner Jazz Solo Cue') requires sync license.",
        required_document_type="Executed Synchronization License",
        tenant_id="tenant_paramount", production_id="prod_diner_noir_v8", status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="tenant_paramount", production_id="prod_diner_noir_v8")
    mgr.states[clrf.claim_id] = SuspensionState.WAITING_FOR_INFORMATION

    parser, text = AgreementParser(use_fallback=True), mock_sync_license_content()
    meta = parser.parse_agreement(text)
    assert "Blue Note Publishing" in meta.parties.licensor
    assert meta.asset_title == "Diner Jazz Solo Cue"
    assert meta.agreement_type == "Sync License"

    matcher = DocumentMatcherService(clarification_store=store, suspension_manager=mgr, parser=parser)
    event = DocumentArrivalEvent(
        file_path="gs://lienmark-paramount-locked-drafts/agreements/prod_diner_noir_v8/mock_sync_license.pdf",
        tenant_id="tenant_paramount", file_hash=compute_file_hash(text), production_id="prod_diner_noir_v8",
    )
    res = matcher.on_document_arrival(event, file_content=text)
    assert res.decision == MatchingDecision.AUTO_RESOLVE
    assert res.confidence_score > 0.85
    assert res.dual_key_valid is True

    updated_clrf = store.get_clarification("clrf_jazz_001", tenant_id="tenant_paramount")
    assert updated_clrf.status == "resolved"
    assert updated_clrf.resolution_channel == "folder_arrival_autonomous"


def test_step_5_hydration_agreement_verification_and_review_readiness():
    """Step 5: Checkpoint hydrated, zero queries re-run, agreement verified, advances to review."""
    claim, mgr = build_diner_jazz_claim(), SuspensionManager()
    snapshot = AgentMemorySnapshot(
        findings=[{"registry": "ASCAP", "status": "no_match"}],
        subgoals=["subgoal_sync_license", "subgoal_master_rights"],
        query_history=[{"query": "diner jazz solo Blue Note"}],
    )
    cp = mgr.suspend_investigation(
        tenant_id="tenant_paramount", production_id="prod_diner_noir_v8", run_id="run_diner_001",
        claim_id=claim.claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_jazz_001"],
    )
    coord = ResumptionCoordinator(suspension_manager=mgr)
    resolution = ResolutionPayload(
        resolution_id="res_auto_01", claim_id=claim.claim_id,
        attached_documents=["agr_sync_blue_note_001"], provided_facts={"license_verified": True},
    )
    res_result = coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token=cp.resume_token, resolution_payload=resolution)
    assert res_result.status == ResumptionStatus.SUCCESS
    assert res_result.reinvestigated_upstream_count == 0
    assert res_result.next_stage.stage_type == NextStageType.TARGETED_AGREEMENT_VERIFICATION

    text = mock_sync_license_content()
    doc_input, verifier = create_verified_doc_input(text), AgreementVerifier()
    req = ProductionRequirements(required_territory="worldwide", required_rights=[RightType.SYNCHRONIZATION])
    v_res = verifier.verify_agreement(doc=doc_input, requirements=req, claim=claim)
    assert v_res.is_valid is True
    assert v_res.status == VerificationStatus.VERIFIED_COMPLIANT
    assert v_res.grant_scope.is_worldwide is True
    assert v_res.grant_scope.is_perpetual is True

    updated_claim = verifier.update_claim_state(claim, v_res)
    assert updated_claim.licensor_grant_confirmed is True
    assert updated_claim.disposition == CensusDisposition.APPROVED


def _setup_e2e_suspension():
    """Sets up claim, suspension manager, clarification store, and coordinator."""
    claim, mgr, store = build_diner_jazz_claim(), SuspensionManager(), ClarificationStore()
    adk = EvidenceDrivenCoordinator(use_fallback=True)
    adk.register_claim(claim)

    snapshot = AgentMemorySnapshot(
        findings=[{"entity": "USCO", "status": "unregistered"}],
        subgoals=["subgoal_sync_license"],
        query_history=[{"query": "Blue Note jazz solo"}],
    )
    cp = mgr.suspend_investigation(
        tenant_id="tenant_paramount", production_id="prod_diner_noir_v8", run_id="run_diner_001",
        claim_id=claim.claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_jazz_001"],
    )
    clrf = ClarificationRequest(
        request_id="clrf_jazz_001", claim_id=claim.claim_id,
        stable_lineage_key="lineage_diner_jazz_cue",
        question_text="Scene 14: Uncredited jazz solo ('Diner Jazz Solo Cue') requires sync license.",
        required_document_type="Executed Synchronization License",
        tenant_id="tenant_paramount", production_id="prod_diner_noir_v8", status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="tenant_paramount", production_id="prod_diner_noir_v8")
    return claim, mgr, store, adk, cp


def _verify_unblocked_agreement(claim, text):
    """Verifies agreement and updates claim disposition."""
    doc_input, verifier = create_verified_doc_input(text), AgreementVerifier()
    v_res = verifier.verify_agreement(
        doc=doc_input,
        requirements=ProductionRequirements(required_territory="worldwide", required_rights=[RightType.SYNCHRONIZATION]),
        claim=claim,
    )
    assert v_res.is_valid is True
    verifier.update_claim_state(claim, v_res)


def test_acceptance_gate_e2e_autonomous_unblocking_under_10_seconds():
    """Sprint 4.2 Acceptance Gate: Complete end-to-end unblocking under 10 seconds."""
    start_time = time.monotonic()
    claim, mgr, store, adk, cp = _setup_e2e_suspension()
    text = mock_sync_license_content()
    res_coord = ResumptionCoordinator(suspension_manager=mgr, adk_coordinator=adk)

    matcher = DocumentMatcherService(
        clarification_store=store, suspension_manager=mgr,
        resumption_callback=lambda c, m: res_coord.resume_run(
            checkpoint_id=cp.checkpoint_id, resume_token=cp.resume_token,
            resolution_payload=ResolutionPayload(
                resolution_id="res_auto", claim_id=c.claim_id,
                attached_documents=[m.document_id], provided_facts={"asset": m.asset_title},
            ),
        ),
    )
    event = DocumentArrivalEvent(
        file_path="gs://lienmark-paramount-locked-drafts/agreements/prod_diner_noir_v8/mock_sync_license.pdf",
        tenant_id="tenant_paramount", file_hash=compute_file_hash(text), production_id="prod_diner_noir_v8",
    )
    match_result = matcher.on_document_arrival(event, file_content=text)

    assert match_result.decision == MatchingDecision.AUTO_RESOLVE
    assert match_result.confidence_score > 0.85
    assert match_result.pipeline_resumed is True

    _verify_unblocked_agreement(claim, text)
    mgr.states[claim.claim_id] = ClarificationStateMachine.transition(
        mgr.states[claim.claim_id], SuspensionState.READY_FOR_REVIEW
    )

    assert mgr.states[claim.claim_id] == SuspensionState.READY_FOR_REVIEW
    assert claim.licensor_grant_confirmed is True
    assert store.get_clarification("clrf_jazz_001", "tenant_paramount").status == "resolved"

    elapsed = time.monotonic() - start_time
    assert elapsed < 10.0, f"Acceptance gate took {elapsed:.2f}s, exceeding 10s budget."
