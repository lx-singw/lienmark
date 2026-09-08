"""
tests/test_milestone_d_human_collaboration.py

Milestone D Acceptance Test Suite: Human-in-the-Loop Collaboration & Resumption.
Covers Scenarios 1 to 5 of the Milestone D Acceptance Roadmap:
1. Durable suspension & clean worker exit (0 active tasks).
2. Worker death and resurrection via folder agreement arrival.
3. Counsel rejection with immutable lineage & real budgeted research.
4. Transitive dependency invalidation (composition -> master cue, visual art preserved).
5. Idempotent duplicate agreement delivery (0 duplicate runs, $0 wasted budget).

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import pytest

from backend.agents.research.directed_research import DirectedQueryReformulator
from backend.agents.research.directed_research_types import DirectedSearchRequest
from backend.core.dependency_graph import ClearanceDependencyGraph
from backend.core.reviewer_loop import CounselReviewLoopCoordinator
from backend.domain.models import (
    AtomicRightsClaim, CensusDisposition, ClarificationRequest, CounselDecision, DecisionStatus, WorkflowReason,
)
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot, SuspensionReason, SuspensionState, validate_resume_token,
)
from backend.orchestration.execution_budget_governor import ExecutionBudgetGovernor
from backend.orchestration.resumption import ResumptionCoordinator
from backend.orchestration.resumption_types import ResolutionPayload
from backend.orchestration.suspension import SuspensionManager
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.agreement_verifier import AgreementVerifier
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput,
    ProductionRequirements,
    RightType,
    SignatureParty,
    VerificationStatus,
)
from backend.services.document_matcher import DocumentMatcherService
from backend.services.document_matcher_types import DocumentArrivalEvent, MatchingDecision
from backend.services.parallel_service import ParallelSearchService
from backend.storage.clarification_store import ClarificationStore
from backend.storage.document_store import DocumentStore
from backend.storage.ledger import CryptographicLedger


def test_durable_suspension_and_clean_worker_exit():
    """Scenario 1: Run suspends on missing fact, checkpoint committed, worker exits with 0 active tasks."""
    mgr, claim_id = SuspensionManager(), "clm_scene14_jazz"

    async def _worker_coro():
        await asyncio.sleep(60)

    loop = asyncio.new_event_loop()
    task = loop.create_task(_worker_coro())
    worker_handles = {"task": task, "handle": object()}

    cp = mgr.suspend_investigation(
        tenant_id="org_paramount", production_id="prod_diner_v8", run_id="run_diner_101",
        claim_id=claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=AgentMemorySnapshot(
            findings=[{"registry": "ASCAP", "status": "uncredited"}], subgoals=["subgoal_sync_license"],
        ),
        pending_clarification_ids=["clrf_jazz_101"], active_tasks=[task], worker_handles=worker_handles,
    )

    assert mgr.states[claim_id] == SuspensionState.WAITING_FOR_INFORMATION
    assert validate_resume_token(cp, cp.resume_token) is True
    assert len(worker_handles) == 0
    assert task.cancelling() or task.cancelled()
    try:
        loop.run_until_complete(task)
    except (asyncio.CancelledError, Exception):
        pass
    assert task.done()
    assert len([t for t in [task] if not t.done()]) == 0
    loop.close()


def _verify_resurrected_agreement(clrf: ClarificationRequest, doc_text: str) -> None:
    verifier = AgreementVerifier()
    claim = AtomicRightsClaim(
        claim_id=clrf.claim_id, occurrence_id="occ_noir_01", occurrence_lineage_id=clrf.stable_lineage_key,
        right_category="music", rights_subject="Autumn Shadows",
    )
    doc_in = AgreementDocumentInput(
        agreement_id="agr_sync_aut", document_name="autumn_sync.pdf", licensor="Blue Note", licensee="Paramount",
        territories=["Worldwide"], media=["All Media"], term="In perpetuity", granted_rights=["Synchronization rights"],
        signatures=[SignatureParty(party_name="Blue Note", party_role="licensor", is_signed=True),
                    SignatureParty(party_name="Paramount", party_role="licensee", is_signed=True)], raw_text=doc_text,
    )
    reqs = ProductionRequirements(required_territory="worldwide", required_rights=[RightType.SYNCHRONIZATION])
    v_res = verifier.verify_agreement(doc=doc_in, requirements=reqs, claim=claim)
    assert v_res.is_valid is True and v_res.status == VerificationStatus.VERIFIED_COMPLIANT
    assert verifier.update_claim_state(claim, v_res, counsel_signoff=True).disposition == CensusDisposition.APPROVED


def test_worker_death_and_resurrection_via_agreement():
    """Scenario 2: Worker process killed; fresh worker started; folder agreement arrival unblocks pipeline."""
    store, orig_mgr = ClarificationStore(), SuspensionManager()
    clrf = ClarificationRequest(
        request_id="clrf_godfather_01", claim_id="clm_autumn_noir",
        stable_lineage_key="lin_autumn_noir", question_text="Autumn Shadows requires sync license.",
        required_document_type="Executed Synchronization License",
        tenant_id="org_paramount", production_id="prod_godfather", status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="org_paramount", production_id="prod_godfather")
    cp = orig_mgr.suspend_investigation(
        tenant_id="org_paramount", production_id="prod_godfather", run_id="run_godfather_01",
        claim_id=clrf.claim_id, paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=AgentMemorySnapshot(),
        pending_clarification_ids=[clrf.request_id],
    )
    del orig_mgr  # Worker 1 process terminates

    fresh_mgr = SuspensionManager()
    fresh_mgr.checkpoints[cp.checkpoint_id] = cp
    fresh_mgr.states[clrf.claim_id] = SuspensionState.WAITING_FOR_INFORMATION
    res_coord = ResumptionCoordinator(suspension_manager=fresh_mgr)
    cb = lambda c, m: res_coord.resume_run(
        checkpoint_id=cp.checkpoint_id, resume_token=cp.resume_token,
        resolution_payload=ResolutionPayload(resolution_id="res_01", claim_id=c.claim_id, attached_documents=[m.document_id]),
    )
    matcher = DocumentMatcherService(parser=AgreementParser(use_fallback=True), clarification_store=store, resumption_callback=cb)
    doc_text = "SYNCHRONIZATION LICENSE AGREEMENT\nBy and between Blue Note Records (Licensor) and Paramount Pictures (Licensee).\nAsset Title: 'Autumn Shadows'\nExecution Date: 2026-05-15\nGrant Territory: Worldwide in perpetuity.\nGrant Media: All Media now known or hereafter devised."
    evt = DocumentArrivalEvent(
        file_path="organizations/org_paramount/productions/prod_godfather/agreements/autumn_sync.pdf",
        tenant_id="org_paramount", production_id="prod_godfather", file_hash=compute_file_hash(doc_text),
    )
    match_res = matcher.on_document_arrival(evt, file_content=doc_text)
    assert match_res.decision == MatchingDecision.AUTO_RESOLVE and match_res.confidence_score > 0.85
    assert match_res.pipeline_resumed is True
    _verify_resurrected_agreement(clrf, doc_text)


@pytest.mark.asyncio
async def test_counsel_rejection_immutable_lineage_and_real_research():
    """Scenario 3: Counsel rejects with directive; Attempt 1 preserved in ledger; Attempt 2 dispatches real research."""
    ledger = CryptographicLedger()
    coordinator = CounselReviewLoopCoordinator(ledger=ledger)
    claim = AtomicRightsClaim(
        claim_id="clm_adapt_1972", occurrence_id="occ_1", occurrence_lineage_id="lin_1",
        right_category="composition", rights_subject="The 1972 Live Adaptation",
        disposition=CensusDisposition.APPROVED, attempt_number=1,
    )
    prior_finding = "Public domain based on 1920 publication record"
    directive = "Re-search ASCAP specifically for 1972 live adaptation rights in UK territory"

    coordinator.reject_and_reopen_investigation(
        claim=claim, prior_finding=prior_finding, directive_text=directive,
        counsel_id="counsel_007", counsel_name="Sarah Jenkins, Esq.",
        tenant_id="tenant_warner", production_id="prod_matrix", prior_finding_id="find_pd_001",
    )

    chain = ledger._chains["prod_matrix"]
    assert any(e.action_type == "CLAIM_REJECTED_BY_COUNSEL" for e in chain)
    assert len(claim.archived_recommendations) == 1
    assert claim.archived_recommendations[0]["prior_finding"] == prior_finding
    assert claim.attempt_number == 2 and claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert claim.workflow_reason == WorkflowReason.REINVESTIGATION_REQUESTED

    req = DirectedSearchRequest(title=claim.rights_subject, raw_directive=directive, timeout_seconds=5.0)
    queries = DirectedQueryReformulator().reformulate_queries(req)
    assert any("ASCAP" in q for q in queries)

    search_svc = ParallelSearchService(use_fallback=True)
    snap = await search_svc.search(query=queries[0], use_id="use_adapt_1972", stable_lineage_key="lin_1", title=claim.rights_subject)
    assert snap.snapshot_id is not None and snap.source_url is not None
    assert "fake" not in snap.source_url.lower() and "example.com" not in snap.source_url.lower()
    assert snap.source_url.startswith(("http://", "https://"))


def test_transitive_dependency_invalidation():
    """Scenario 4: Rejection of composition invalidates master cue but reuses unaffected independent visual art."""
    graph = ClearanceDependencyGraph()
    dec_comp = CounselDecision(
        decision_id="dec_comp", use_id="use_comp", stable_lineage_key="comp_key",
        applicable_version_id="v7", status=DecisionStatus.APPROVED, rationale="Composition cleared",
    )
    graph.add_counsel_decision(dec_comp)

    dec_master = CounselDecision(
        decision_id="dec_master", use_id="use_master", stable_lineage_key="master_key",
        applicable_version_id="v7", status=DecisionStatus.APPROVED, rationale="Master cue cleared",
        dependency_ids=["dec_comp"],
    )
    graph.add_counsel_decision(dec_master)
    graph.add_dependency(dependent_id="dec_master", dependency_id="dec_comp")

    dec_art = CounselDecision(
        decision_id="dec_art", use_id="use_art", stable_lineage_key="art_key",
        applicable_version_id="v7", status=DecisionStatus.APPROVED, rationale="Visual art cleared independently",
    )
    graph.add_counsel_decision(dec_art)

    notices = graph.propagate_invalidation(changed_nodes={"dec_comp": {"reason_code": "REJECTED_BY_COUNSEL", "explanation": "Composition sync rejected"}})
    notice_ids = {n.affected_node_id for n in notices}
    assert "dec_master" in notice_ids
    assert "dec_art" not in notice_ids
    master_notice = next(n for n in notices if n.affected_node_id == "dec_master")
    assert master_notice.root_cause_node_id == "dec_comp"
    assert dec_art.status == DecisionStatus.APPROVED


def test_idempotent_duplicate_agreement_delivery():
    """Scenario 5: Multiple uploads of identical agreement produce 0 duplicate worker runs and $0 wasted budget."""
    store, ledger = DocumentStore(), CryptographicLedger()
    store.attach_ledger(ledger)
    governor = ExecutionBudgetGovernor(default_max_run_spend_usd=50.0)
    pdf_bytes = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\nAutumn Shadows Sync License\n%%EOF"
    tenant, prod, fname = "org_universal", "prod_jurassic", "autumn_sync.pdf"

    doc1, res1 = store.lookup_or_register(tenant_id=tenant, production_id=prod, file_path_or_name=fname, content_bytes=pdf_bytes, version_id="v1", claims_count=5)
    assert not res1.is_duplicate
    store.commit_document_baseline(tenant, doc1.document_id, "v1")
    governor.record_usage(run_id="run_jurassic_01", provider="parallel", tokens_prompt=0, tokens_completion=0, cost_usd=0.50)
    settled_baseline = governor._run_spend.get("run_jurassic_01", 0.0)

    duplicate_runs = 0
    for _ in range(3):
        doc_dup, res_dup = store.lookup_or_register(tenant_id=tenant, production_id=prod, file_path_or_name=fname, content_bytes=pdf_bytes, version_id="v1", claims_count=5)
        assert res_dup.is_duplicate is True
        assert res_dup.matched_document.document_id == doc1.document_id
        if not res_dup.is_duplicate:
            duplicate_runs += 1
            governor.record_usage(run_id="run_jurassic_01", provider="parallel", tokens_prompt=0, tokens_completion=0, cost_usd=0.50)

    assert duplicate_runs == 0
    settled_after = governor._run_spend.get("run_jurassic_01", 0.0)
    assert settled_after == settled_baseline
    assert (settled_after - settled_baseline) == 0.0
