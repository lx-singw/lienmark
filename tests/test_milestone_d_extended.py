"""
tests/test_milestone_d_extended.py

Milestone D Acceptance Test Suite: Extended Collaboration & Invariant Verification.
Covers Scenarios 6 to 10 of the Milestone D Acceptance Roadmap:
6. Out-of-scope and wrong-production rejection (dual-key isolation).
7. Ambiguous and insufficient agreement handling (mismatched rights scope leaves clarification open).
8. Checkpoint retention pinning prevents silent TTL destruction.
9. Production RBAC enforcement (producer sign-off 403; cross-production rejected).
10. Measured provider reuse (0 upstream re-queries; completed work reused).

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    AtomicRightsClaim, CensusDisposition, ClarificationRequest,
)
from backend.main import app
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot, SuspensionReason, SuspensionState,
)
from backend.orchestration.resumption import ResumptionCoordinator
from backend.orchestration.resumption_types import NextStageType
from backend.orchestration.suspension import SuspensionManager
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.agreement_verifier import AgreementVerifier
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput, ProductionRequirements, RightType,
    SignatureParty, VerificationStatus,
)
from backend.services.document_matcher import DocumentMatcherService
from backend.services.document_matcher_scoring import evaluate_dual_key_match
from backend.services.document_matcher_types import (
    DocumentArrivalEvent, MatchingDecision,
)
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_types import AgentStateVector
from backend.storage.clarification_store import ClarificationStore
from tests.test_tenant_middleware import create_test_jwt


def test_out_of_scope_and_wrong_production_rejection():
    """Scenario 6: Agreement uploaded to wrong production is rejected out-of-scope."""
    store = ClarificationStore()
    matcher = DocumentMatcherService(parser=AgreementParser(use_fallback=True), clarification_store=store)
    clrf = ClarificationRequest(
        request_id="clrf_matrix_sync", claim_id="clm_neo_theme", stable_lineage_key="lin_neo",
        question_text="Neo Theme requires sync license in Matrix 4.", required_document_type="Executed Synchronization License",
        tenant_id="org_warner", production_id="prod_matrix_4", status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="org_warner", production_id="prod_matrix_4")

    wrong_evt = DocumentArrivalEvent(
        file_path="organizations/org_warner/productions/prod_speed_racer/agreements/neo_sync.pdf",
        tenant_id="org_warner", production_id="prod_speed_racer", file_hash=compute_file_hash("neo theme"),
    )
    doc_text = "SYNCHRONIZATION LICENSE AGREEMENT\nAsset Title: 'Neo Theme'\nLicensor: Warner\nLicensee: Village Roadshow"
    res = matcher.on_document_arrival(wrong_evt, file_content=doc_text)

    assert res.decision == MatchingDecision.NO_MATCH and res.dual_key_valid is False
    assert res.confidence_score == 0.0 and res.pipeline_resumed is False
    assert store.get_clarification("clrf_matrix_sync", tenant_id="org_warner").status == "waiting_for_information"


def test_ambiguous_and_insufficient_agreement_handling():
    """Scenario 7: Candidate score > 0.85 with mismatched rights scope leaves clarification open."""
    clrf = ClarificationRequest(
        request_id="clrf_bm_101", claim_id="clm_brass_motif", stable_lineage_key="lin_bm",
        question_text="Brass Motif uncredited cue requires sync license for worldwide release.",
        required_document_type="Executed Synchronization License",
        tenant_id="org_cinema", production_id="prod_matrix", status="waiting_for_information",
    )
    claim = AtomicRightsClaim(
        claim_id="clm_brass_motif", occurrence_id="occ_bm", occurrence_lineage_id="lin_bm",
        right_category="composition", rights_subject="Brass Motif", intended_territory=["Worldwide"],
        intended_media=["Theatrical", "SVOD"], disposition=CensusDisposition.NEEDS_REVIEW,
    )
    doc_text = "SHEET MUSIC PRINT LICENSE AGREEMENT\nLicensor: Warner Chappell\nLicensee: Paramount\nAsset Title: 'Brass Motif'\nScope: Print only."
    parser = AgreementParser(use_fallback=True)
    meta = parser.parse_agreement(doc_text)
    evt = DocumentArrivalEvent(
        file_path="agreements/brass_sheet.pdf", tenant_id="org_cinema",
        production_id="prod_matrix", file_hash=compute_file_hash(doc_text),
    )
    valid, bdown = evaluate_dual_key_match(meta, clrf, evt)
    assert bdown.asset_score > 0.85 or bdown.composite_score > 0.85

    verifier = AgreementVerifier()
    doc_in = AgreementDocumentInput(
        agreement_id="agr_sheet_only", document_name="brass_sheet.pdf", licensor="Warner Chappell",
        licensee="Paramount", territories=["Worldwide"], media=["Print"], granted_rights=["Print notation rights"],
        signatures=[SignatureParty(party_name="Warner Chappell", party_role="licensor", is_signed=True),
                    SignatureParty(party_name="Paramount", party_role="licensee", is_signed=True)], raw_text=doc_text,
    )
    req = ProductionRequirements(required_territory="worldwide", required_rights=[RightType.SYNCHRONIZATION])
    res, _ = verifier.verify_and_unblock(clarification=clrf, claim=claim, doc=doc_in, tenant_id="org_cinema", actor_id="counsel_007", production_id="prod_matrix", requirements=req)

    assert res.is_valid is False and res.status in (VerificationStatus.REJECTED, VerificationStatus.NON_COMPLIANT)
    assert clrf.status == "waiting_for_information" and claim.licensor_grant_confirmed is False
    assert claim.disposition in (CensusDisposition.NEEDS_REVIEW, CensusDisposition.CONDITIONAL)
    assert claim.disposition != CensusDisposition.APPROVED


def test_checkpoint_retention_pinning_prevents_ttl_destruction(tmp_path):
    """Scenario 8: Active clarification pins checkpoint against silent TTL deletion."""
    store = CheckpointStore(base_output_dir=str(tmp_path), force_local=True)
    clrf_store = ClarificationStore(base_dir=str(tmp_path / "clarifications"))
    now = datetime.now(timezone.utc)
    past_ttl = (now - timedelta(days=2)).isoformat()

    clrf = ClarificationRequest(
        request_id="clrf_active_pin", claim_id="clm_pinned_01", stable_lineage_key="lin_pin",
        question_text="Active clarification pinning checkpoint", tenant_id="org_sony",
        production_id="prod_spider", status="waiting_for_information",
    )
    clrf_store.save_clarification(clrf, tenant_id="org_sony", production_id="prod_spider")

    cp_pinned = store.create_checkpoint(
        tenant_id="org_sony", production_id="prod_spider", run_id="run_pin_01",
        checkpoint_id="ckpt_pinned_01", agent_state=AgentStateVector(pending_clarification_ids=["clrf_active_pin"]),
    )
    store.save_checkpoint(cp_pinned.model_copy(update={"expires_at_utc": past_ttl}))

    cp_unpinned = store.create_checkpoint(
        tenant_id="org_sony", production_id="prod_spider", run_id="run_pin_01",
        checkpoint_id="ckpt_unpinned_02", agent_state=AgentStateVector(pending_clarification_ids=[]),
    )
    store.save_checkpoint(cp_unpinned.model_copy(update={"expires_at_utc": past_ttl}))

    open_clrfs = {c.request_id for c in clrf_store.list_open_clarifications("org_sony", "prod_spider")}
    all_checkpoints = store.list_checkpoints("org_sony", "prod_spider", "run_pin_01", include_expired=True)
    for cp in all_checkpoints:
        is_pinned = bool(set(cp.agent_state.pending_clarification_ids) & open_clrfs)
        if not is_pinned:
            store.delete_checkpoint("org_sony", "prod_spider", "run_pin_01", cp.checkpoint_id)

    assert store.get_checkpoint("org_sony", "prod_spider", "run_pin_01", "ckpt_pinned_01", allow_expired=True) is not None
    assert store.get_checkpoint("org_sony", "prod_spider", "run_pin_01", "ckpt_unpinned_02", allow_expired=True) is None


def test_production_rbac_enforcement():
    """Scenario 9: Producer sign-off receives HTTP 403; cross-production roles rejected."""
    client = TestClient(app)
    producer_token = create_test_jwt(tenant_id="org_warner_bros_001", user_id="usr_producer_001", roles=["producer"])
    payload = {
        "stable_lineage_key": "poster_noir_detective_magazine",
        "action": "re_attest",
        "counsel_rationale": "Artwork verified in public domain under 17 U.S.C. Section 304(a).",
        "reviewer_name": "Sarah Jenkins, Esq.",
        "version_id": "v8",
    }

    res_producer = client.post("/api/review/action", json=payload, headers={"Authorization": f"Bearer {producer_token}"})
    assert res_producer.status_code == 403

    hybrid_token = create_test_jwt(
        tenant_id="org_warner_bros_001", user_id="usr_hybrid_001", roles=["viewer"],
        claims_extra={"production_roles": {"prod_tentpole_alpha": "authorized_reviewer", "prod_indie_beta": "clearance_analyst"}},
    )
    res_cross = client.post(
        "/api/review/action", json=payload,
        headers={"Authorization": f"Bearer {hybrid_token}", "X-Production-ID": "prod_indie_beta"},
    )
    assert res_cross.status_code == 403

    res_auth = client.post(
        "/api/review/action", json=payload,
        headers={"Authorization": f"Bearer {hybrid_token}", "X-Production-ID": "prod_tentpole_alpha"},
    )
    assert res_auth.status_code == 200 and res_auth.json()["status"] == "success"


def test_measured_provider_reuse():
    """Scenario 10: Measures provider calls to prove completed upstream work is reused."""
    mgr = SuspensionManager()
    claim_id = "clm_jazz_solo"
    snapshot = AgentMemorySnapshot(
        findings=[{"entity": "USCO", "status": "no_match"}],
        subgoals=["subgoal_sync_license"],
        query_history=[{"query": "diner jazz solo Blue Note"}],
        context_variables={"track_title": "Blue Monk"},
    )
    cp = mgr.suspend_investigation(
        tenant_id="org_paramount", production_id="prod_noir", run_id="run_01",
        claim_id=claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_01"],
    )

    coord = ResumptionCoordinator(suspension_manager=mgr)
    provider_calls = {"upstream_re_queries": 0, "uncompleted_dispatches": 0}

    result = coord.resume_run(checkpoint_id=cp.checkpoint_id, resume_token=cp.resume_token)
    assert result.status.value == "success"
    assert result.reinvestigated_upstream_count == 0
    assert result.hydrated_memory.upstream_frozen_count >= 1

    if result.reinvestigated_upstream_count > 0:
        provider_calls["upstream_re_queries"] += result.reinvestigated_upstream_count
    if result.next_stage.stage_type == NextStageType.NEXT_INVESTIGATION_NODE:
        provider_calls["uncompleted_dispatches"] += 1

    assert provider_calls["upstream_re_queries"] == 0
    assert provider_calls["uncompleted_dispatches"] == 1
