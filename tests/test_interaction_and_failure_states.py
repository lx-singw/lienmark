"""
Automated Test Suite for Sprint 4B Task 2: Interaction & Failure States Test Engineer

Verifies:
1. Multi-Stage Orchestration & Progress Telemetry:
   Asserts that LienmarkWorkflow.execute_drift_detection() produces structured
   execution_traces covering all pipeline phases with duration and component tags.
2. Optimistic Update & Error Rollback Contracts:
   Asserts that if an invalid review action is submitted (e.g. empty rationale for re_attest),
   the backend raises HTTP 403 or 400 and preserves prior decision state.
3. Empty / No-Change State Invariant (f(v7, v7) = 12/12):
   Asserts that evaluating baseline against baseline yields exactly 12 carried forward,
   0 stale, 0 parallel search calls, and $0 review cost.
4. Partial Research Degradation & Fail-Closed Robustness:
   Asserts that a simulated search failure or timeout returns INSUFFICIENT stance,
   preserves STALE state, sets revalidation_action='manual', and DOES NOT crash
   the workflow or mark the decision approved.
5. Idempotency & Retry Without Duplication:
   Asserts that retrying apply_review_action on the same lineage key updates the existing
   decision and adds a properly parent-chained supersession event without duplicating items
   in review_queue.
6. Citation Metadata, Timestamps & Latencies:
   Asserts that evidence snapshots contain attributable source_title, valid source_url,
   retrieval_latency_ms, and valid timestamps.
7. Print Engine Parity:
   Asserts that SSR Form E&O-2026 report HTML contains @media print CSS rules,
   print-hide classes, and page break controls.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    CarrierHeader,
    ChangeKind,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceStance,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    PublicEvidenceSnapshot,
    ReattestationRequest,
    ReviewAction,
    ReviewActionRequest,
    ReviewerIdentity,
    SupersessionEvent,
    UnauthorizedApprovalError,
    FailClosedSecurityViolation,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.counsel_checkpoint import CounselCheckpointManager
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.orchestration.workflow import LienmarkWorkflow, WorkflowRunResult
from backend.services.gemini_service import GeminiService
from backend.services.parallel_service import ParallelSearchService
from backend.services.revalidation_planner import RevalidationPlanner
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)
from backend.main import app, counsel_checkpoint_manager, _counsel_reattestations

client = TestClient(app)


# =============================================================================
# GLOBAL TEST FIXTURES & STATE ISOLATION
# =============================================================================

@pytest.fixture(autouse=True)
def clean_test_environment():
    """Ensures clean state isolation between all test invocations."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


# =============================================================================
# 1. MULTI-STAGE ORCHESTRATION & PROGRESS TELEMETRY
# =============================================================================

class TestMultiStageOrchestrationAndProgressTelemetry:
    """
    Empirical tests asserting that LienmarkWorkflow.execute_drift_detection()
    produces structured execution_traces covering all pipeline phases with
    accurate duration and component tags.
    """

    @pytest.mark.asyncio
    async def test_workflow_produces_structured_execution_traces(self):
        """
        Asserts that execute_drift_detection() yields execution_traces covering:
        1. Version Ingestion (LienmarkEngine)
        2. Gemini Semantic Delta Analysis (Gemini 2.5 Flash)
        3. Deterministic Invalidation Evaluation (InvalidationEngine)
        4. Selective Revalidation Planning (RevalidationPlanner)
        5. Targeted Parallel Search (Parallel Search API)
        6. Evidence & Contract Reconciliation (EvidenceReconciler)
        """
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection()

        assert isinstance(result, WorkflowRunResult)
        assert result.run_id.startswith("run_")
        assert result.base_version == "v7"
        assert result.target_version == "v8"
        assert result.total_claims == 12
        assert result.carried_forward_count == 10
        assert result.reopened_count == 2
        assert result.total_duration_ms > 0.0

        traces = result.execution_traces
        assert isinstance(traces, list)
        assert len(traces) >= 6, f"Expected at least 6 phase traces, got {len(traces)}"

        # Validate structured attributes of every execution trace
        trace_step_names = []
        trace_components = []

        for trace in traces:
            assert trace.step_name and isinstance(trace.step_name, str)
            assert trace.component and isinstance(trace.component, str)
            assert trace.status in ("SUCCESS", "FAIL_CLOSED")
            assert isinstance(trace.duration_ms, (int, float))
            assert trace.duration_ms >= 0.0
            assert isinstance(trace.details, dict)
            assert len(trace.details) > 0, f"Trace '{trace.step_name}' details must not be empty"

            trace_step_names.append(trace.step_name)
            trace_components.append(trace.component)

        # Check required pipeline phases
        assert "version_ingestion" in trace_step_names
        assert "semantic_delta_analysis" in trace_step_names
        assert "deterministic_dependency_invalidation" in trace_step_names
        assert "selective_revalidation_planning" in trace_step_names
        assert any(name.startswith("parallel_targeted_search_") for name in trace_step_names)
        assert "evidence_and_contract_reconciliation" in trace_step_names

        # Check required component tags
        assert "LienmarkEngine" in trace_components
        assert "Gemini 2.5 Flash" in trace_components
        assert "InvalidationEngine" in trace_components
        assert "RevalidationPlanner" in trace_components
        assert "Parallel Search API" in trace_components
        assert "EvidenceReconciler" in trace_components

    @pytest.mark.asyncio
    async def test_trace_telemetry_metrics_and_budget_details(self):
        """
        Validates phase-specific telemetry metrics inside trace details.
        Ensures the 10 unchanged carried claims are not submitted to search.
        """
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection()

        trace_map = {t.step_name: t for t in result.execution_traces}

        # Step 1: version_ingestion telemetry
        t_ingest = trace_map["version_ingestion"]
        assert t_ingest.details.get("v7_uses") == 12
        assert t_ingest.details.get("v8_uses") == 12

        # Step 2: semantic_delta_analysis telemetry
        t_delta = trace_map["semantic_delta_analysis"]
        assert t_delta.details.get("is_material") is True
        assert "prominence_shift" in t_delta.details
        assert str(t_delta.details.get("recommended_action")).lower() == "revalidate"

        # Step 3: deterministic_dependency_invalidation telemetry
        t_inval = trace_map["deterministic_dependency_invalidation"]
        assert t_inval.details.get("carried_forward") == 10
        assert t_inval.details.get("reopened") == 2
        assert t_inval.details.get("policy") == InvalidationEngine.POLICY_VERSION

        # Step 4: selective_revalidation_planning telemetry
        t_plan = trace_map["selective_revalidation_planning"]
        assert t_plan.details.get("planned_count") == 2
        assert t_plan.details.get("skipped_count") == 10
        assert t_plan.details.get("api_call_budget_enforced") is True
        planned_keys = t_plan.details.get("planned_keys", [])
        assert "poster_noir_detective_magazine" in planned_keys
        assert "music_cue_midnight_serenade" in planned_keys

        # Step 6: evidence_and_contract_reconciliation telemetry
        t_recon = trace_map["evidence_and_contract_reconciliation"]
        assert t_recon.details.get("reconciled_claims") == 12
        assert "contract_shields_applied" in t_recon.details


# =============================================================================
# 2. OPTIMISTIC UPDATE & ERROR ROLLBACK CONTRACTS
# =============================================================================

class TestOptimisticUpdateAndErrorRollbackContracts:
    """
    Verifies that invalid or unauthenticated review actions are rejected
    with HTTP 403 or 400, strictly preserving prior decision states and
    preventing state corruption / illegitimate approvals.
    """

    def test_empty_rationale_for_re_attest_raises_403_and_preserves_state(self):
        """
        Asserts that submitting re_attest without explicit legal rationale:
        1. Fails closed with HTTP 403.
        2. Preserves prior STALE decision state in counsel_checkpoint_manager.
        3. Leaves the review queue item in STALE state without approving it.
        """
        # Ensure review queue is populated
        queue = counsel_checkpoint_manager.get_review_queue()
        assert len(queue.items) == 2
        poster_item = next(it for it in queue.items if it.stable_lineage_key == "poster_noir_detective_magazine")
        assert poster_item.current_state == DecisionState.STALE

        # Attempt re_attest with empty rationale
        payload = {
            "action": "re_attest",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "counsel_rationale": "",  # Empty rationale
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code == 403, f"Expected HTTP 403, got {res.status_code}: {res.text}"
        data = res.json()
        assert "Fail-closed safety invariant" in data["detail"]

        # Verify prior state is preserved
        updated_queue = counsel_checkpoint_manager.get_review_queue()
        updated_poster = next(it for it in updated_queue.items if it.stable_lineage_key == "poster_noir_detective_magazine")
        assert updated_poster.current_state == DecisionState.STALE
        assert updated_poster.current_status != DecisionStatus.APPROVED or updated_poster.current_state != DecisionState.RE_ATTESTED

        # Verify no bogus supersession event was committed to the ledger
        events = counsel_checkpoint_manager.get_audit_trail("poster_noir_detective_magazine")
        assert len(events) == 0

    def test_whitespace_rationale_for_re_attest_raises_403(self):
        """Whitespace-only rationale must also be rejected under fail-closed security."""
        payload = {
            "action": "re_attest",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "counsel_rationale": "   \n\t   ",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code == 403
        assert "Fail-closed safety invariant" in res.json()["detail"]

    def test_empty_rationale_for_reject_raises_400_and_preserves_state(self):
        """Reject actions also require an explanatory rationale (HTTP 400 on empty)."""
        counsel_checkpoint_manager.get_review_queue()
        payload = {
            "action": "reject",
            "stable_lineage_key": "music_cue_midnight_serenade",
            "counsel_rationale": "",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code == 400
        assert "Counsel rationale is required" in res.json()["detail"]

        # Ensure state preserved
        events = counsel_checkpoint_manager.get_audit_trail("music_cue_midnight_serenade")
        assert len(events) == 0

    def test_invalid_review_action_raises_400_and_preserves_state(self):
        """Invalid review action verb raises HTTP 400."""
        counsel_checkpoint_manager.get_review_queue()
        payload = {
            "action": "bypass_clearance",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "counsel_rationale": "Attempting unauthorized clearance bypass.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code in (400, 422)

        # Ensure state preserved
        events = counsel_checkpoint_manager.get_audit_trail("poster_noir_detective_magazine")
        assert len(events) == 0

    def test_unauthenticated_or_empty_reviewer_raises_403_and_preserves_state(self):
        """Empty or unauthenticated reviewer identity raises HTTP 403."""
        counsel_checkpoint_manager.get_review_queue()
        payload = {
            "action": "re_attest",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "counsel_rationale": "Valid legal rationale for public domain.",
            "reviewer_name": "   ",  # Blank reviewer
            "reviewer": {"name": "", "reviewer_id": ""},
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code == 403
        assert "Reviewer name cannot be empty" in res.json()["detail"] or "Fail-closed" in res.json()["detail"]

        # State preserved
        events = counsel_checkpoint_manager.get_audit_trail("poster_noir_detective_magazine")
        assert len(events) == 0


# =============================================================================
# 3. EMPTY / NO-CHANGE STATE INVARIANT (f(v7, v7) = 12/12)
# =============================================================================

class TestEmptyNoChangeStateInvariant:
    """
    Mathematical Invariant Test: f(v7, v7) = 12/12
    Asserts that evaluating baseline against baseline yields:
    - Exactly 12 carried forward claims.
    - Exactly 0 stale claims.
    - Exactly 0 parallel search calls.
    - Exactly $0 review cost.
    """

    def test_baseline_against_baseline_yields_12_carried_0_stale(self):
        """
        Direct evaluation of V7 against V7 through InvalidationEngine.
        Every prior decision carries forward deterministically.
        """
        v7_uses, _, v7_decisions, initial_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v7_uses,  # Target is identical to base
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v7",
        )

        assert len(validity_results) == 12, "Must evaluate all 12 claims"
        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]
        new_claims = [v for v in validity_results if v.state == DecisionState.NEW]

        assert len(carried) == 12, f"Expected 12 carried forward, got {len(carried)}"
        assert len(stale) == 0, f"Expected 0 stale claims, got {len(stale)}"
        assert len(new_claims) == 0, f"Expected 0 new claims, got {len(new_claims)}"

        for v in validity_results:
            assert v.reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"
            assert v.revalidation_action in ("carry", "carry_forward")

    def test_baseline_against_baseline_triggers_zero_parallel_search_calls(self):
        """
        RevalidationPlanner on V7 vs V7 plans ZERO search calls, strictly
        enforcing the minimal API call budget and skipping all 12 unchanged claims.
        """
        v7_uses, _, v7_decisions, initial_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v7_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v7",
        )

        planner = RevalidationPlanner(enforce_golden_budget=False)
        plan = planner.plan_revalidation(
            validity_results=validity_results,
            target_uses=v7_uses,
            target_version_id="v7",
        )

        assert plan.planned_count == 0, "No research calls should be planned for unchanged baseline"
        assert plan.skipped_count == 12, "All 12 unchanged claims must be skipped"
        assert len(plan.planned_requests) == 0
        assert plan.api_call_budget_enforced is True

    def test_baseline_against_baseline_yields_zero_dollar_review_cost(self):
        """
        Form E&O-2026 Exceptions Schedule for V7 vs V7 confirms:
        - 12 Carried Forward
        - 0 Reopened
        - 0 Unresolved Exceptions
        - Review cost for all items is $0.00
        """
        v7_uses, _, v7_decisions, initial_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v7_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v7",
        )

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v7",
            target_uses=v7_uses,
            validity_results=validity_results,
            base_uses=v7_uses,
        )

        assert schedule.total_claims == 12
        assert schedule.carried_forward_count == 12
        assert schedule.reopened_count == 0
        assert schedule.re_attested_count == 0
        assert schedule.unresolved_exception_count == 0
        assert len(schedule.unresolved_exceptions_schedule) == 0

        # Verify rendered HTML reflects zero exceptions and zero audit cost
        html = InvalidationEngine.render_form_eo_2026_html(schedule)
        assert "TOTAL CLAIMS" in html
        assert ">12<" in html
        assert "CARRIED FORWARD" in html
        assert ">12<" in html
        assert "ACTIVE EXCEPTIONS" in html
        assert ">0<" in html
        assert "$0.00" in html
        assert "No active unresolved exceptions" in html


# =============================================================================
# 4. PARTIAL RESEARCH DEGRADATION & FAIL-CLOSED ROBUSTNESS
# =============================================================================

class TestPartialResearchDegradationAndFailClosedRobustness:
    """
    Verifies system robustness under simulated external API degradation:
    - Search failure or timeout returns INSUFFICIENT stance.
    - Decision remains STALE with revalidation_action='manual'.
    - Workflow does NOT crash and DOES NOT mark unverified decisions approved.
    """

    @pytest.mark.asyncio
    async def test_parallel_search_timeout_returns_insufficient_and_fail_closed(self):
        """Simulated search timeout yields INSUFFICIENT stance and fail_closed metadata."""
        parallel = ParallelSearchService()
        evidence = await parallel.search(
            query="Simulate query for timeout verification",
            use_id="use_v8_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            simulate_failure="timeout",
        )

        assert isinstance(evidence, PublicEvidenceSnapshot)
        assert evidence.stance == EvidenceStance.INSUFFICIENT
        assert evidence.http_status == 504
        assert evidence.metadata.get("fail_closed") is True
        assert "timed out" in evidence.excerpt.lower()
        assert evidence.domain == "search.parallel.ai"

    @pytest.mark.asyncio
    async def test_parallel_search_5xx_and_rate_limit_return_insufficient(self):
        """Simulated 5xx server error and 429 rate limit both fail closed to INSUFFICIENT."""
        parallel = ParallelSearchService()

        # 5xx failure
        ev_5xx = await parallel.search(
            query="Simulate 5xx server error",
            use_id="use_v8_test",
            stable_lineage_key="test_asset_5xx",
            simulate_failure="5xx",
        )
        assert ev_5xx.stance == EvidenceStance.INSUFFICIENT
        assert ev_5xx.http_status == 500

        # Rate limit failure
        ev_429 = await parallel.search(
            query="Simulate 429 rate limit",
            use_id="use_v8_test",
            stable_lineage_key="test_asset_429",
            simulate_failure="rate_limit",
        )
        assert ev_429.stance == EvidenceStance.INSUFFICIENT
        assert ev_429.http_status == 429

    def test_evidence_reconciler_insufficient_preserves_stale_and_manual_action(self):
        """
        EvidenceReconciler handling an INSUFFICIENT snapshot:
        - Keeps decision STALE.
        - Sets revalidation_action='manual'.
        - Sets reason_code='SEARCH_EVIDENCE_INSUFFICIENT'.
        - Does NOT apply contract shield.
        """
        reconciler = EvidenceReconciler()
        insufficient_ev = PublicEvidenceSnapshot(
            snapshot_id="ev_err_timeout",
            use_id="use_v8_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            query="Shadows of Manhattan Detective Magazine 1944 LOC",
            source_url="https://search.parallel.ai/errors",
            source_title="Parallel Search Error Response",
            excerpt="Search failure (HTTP 504): Parallel Search request timed out.",
            stance=EvidenceStance.INSUFFICIENT,
            http_status=504,
            metadata={"fail_closed": True, "error": "timeout"},
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key="poster_noir_detective_magazine",
            decision_id="dec_v7_poster_noir",
            evidence=insufficient_ev,
            contract=None,
        )

        assert result.reconciled_stance == EvidenceStance.INSUFFICIENT
        assert result.decision_state == DecisionState.STALE
        assert result.revalidation_action == "manual"
        assert result.reason_code == "SEARCH_EVIDENCE_INSUFFICIENT"
        assert "Fail-closed policy engaged" in result.explanation
        assert result.contract_shield_applied is False

    @pytest.mark.asyncio
    async def test_workflow_degradation_does_not_crash_and_preserves_stale(self):
        """
        Executes LienmarkWorkflow with an injected failing ParallelSearchService.
        Asserts:
        1. Workflow completes without crashing.
        2. Carried count is 10, reopened count is 2.
        3. The degraded claim remains in STALE state with revalidation_action='manual'.
        4. Stance is 'insufficient' in the claims payload.
        5. The degraded claim is NOT marked approved.
        """
        class FailingParallelSearchService(ParallelSearchService):
            async def search(self, *args, **kwargs):
                return PublicEvidenceSnapshot(
                    snapshot_id="ev_degraded_001",
                    use_id=kwargs.get("use_id", "use_degraded"),
                    stable_lineage_key=kwargs.get("stable_lineage_key", "poster_noir_detective_magazine"),
                    query="degraded query",
                    source_url="https://search.parallel.ai/timeout",
                    source_title="Parallel Search Network Timeout",
                    excerpt="Request timed out after 10000ms. Fail-closed engaged.",
                    stance=EvidenceStance.INSUFFICIENT,
                    http_status=504,
                    metadata={"fail_closed": True, "error": "timeout"},
                )

        failing_service = FailingParallelSearchService()
        workflow = LienmarkWorkflow(parallel_service=failing_service)

        # Workflow must execute cleanly without exception
        result = await workflow.execute_drift_detection()

        assert result.total_claims == 12
        assert result.carried_forward_count == 10
        assert result.reopened_count == 2

        # Check the degraded claim in claims payload
        poster_claim = next(c for c in result.claims if c["stable_lineage_key"] == "poster_noir_detective_magazine")
        assert poster_claim["state"] == "stale"
        assert poster_claim["revalidation_action"] == "manual"
        assert poster_claim["evidence"]["stance"] == "insufficient"
        assert poster_claim["state"] != "carried_forward"
        assert poster_claim["state"] != "re_attested"

        # Check that counsel briefings are omitted for insufficient evidence
        assert "poster_noir_detective_magazine" not in result.counsel_briefings


# =============================================================================
# 5. IDEMPOTENCY & RETRY WITHOUT DUPLICATION
# =============================================================================

class TestIdempotencyAndRetryWithoutDuplication:
    """
    Verifies that repeatedly applying review actions on the same lineage key:
    1. Updates the existing decision in-place.
    2. Adds a properly parent-chained SupersessionEvent.
    3. DOES NOT duplicate items in the review queue.
    4. Maintains cryptographic ledger integrity throughout.
    """

    def test_retry_review_action_updates_existing_decision_without_queue_duplication(self):
        """
        Applies a review action, then immediately applies a second action
        with modified rationale on the same lineage key.
        """
        queue = counsel_checkpoint_manager.get_review_queue()
        initial_queue_count = len(queue.items)
        assert initial_queue_count == 2
        key = "poster_noir_detective_magazine"

        reviewer = counsel_checkpoint_manager.get_default_reviewer()

        # Action 1: Initial re-attestation
        dec1, evt1 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key=key,
            rationale="First pass: Library of Congress catalog confirms 1974 renewal lapse.",
            reviewer=reviewer,
        )

        assert dec1.status == DecisionStatus.APPROVED
        assert evt1.action == ReviewAction.RE_ATTEST
        assert evt1.parent_event_hash == CounselCheckpointManager.GENESIS_PARENT_HASH
        assert len(counsel_checkpoint_manager._current_queue.items) == 2, "Queue must not expand"

        # Action 2: Retry / revised attestation on same lineage key
        dec2, evt2 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key=key,
            rationale="Second pass: Supplemental review of Catalog of Copyright Entries 1974 corroborates lapse.",
            reviewer=reviewer,
        )

        # 1. Decision is updated
        assert dec2.decision_id != dec1.decision_id
        assert dec2.supersedes_decision_id == dec1.decision_id
        assert "Supplemental review" in dec2.rationale
        assert dec2.status == DecisionStatus.APPROVED

        # 2. Supersession event is properly parent-chained
        assert evt2.prior_decision_id == dec1.decision_id
        assert evt2.new_decision_id == dec2.decision_id
        assert evt2.parent_event_hash == evt1.event_hash, "Event 2 parent hash must chain to Event 1 hash"
        assert evt2.event_hash != evt1.event_hash

        # 3. Queue item is updated without duplication
        current_queue_items = counsel_checkpoint_manager._current_queue.items
        assert len(current_queue_items) == 2, f"Expected 2 queue items, found {len(current_queue_items)}"
        unique_keys = [it.stable_lineage_key for it in current_queue_items]
        assert len(unique_keys) == len(set(unique_keys)), "Queue contains duplicate lineage keys!"

        # 4. Verify cryptographic ledger integrity
        integrity = counsel_checkpoint_manager.verify_ledger_integrity()
        assert integrity["is_valid"] is True, f"Ledger integrity failed: {integrity}"

    def test_retry_with_disposition_reversal_supersedes_properly(self):
        """
        Applies re_attest, then reverses disposition to reject on discovery
        of an adverse trademark claim, then verifies sequential chain.
        """
        counsel_checkpoint_manager.get_review_queue()
        key = "poster_noir_detective_magazine"
        reviewer = counsel_checkpoint_manager.get_default_reviewer()

        # Step 1: Re-attest
        dec1, evt1 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key=key,
            rationale="Initial re-attestation based on public domain search.",
            reviewer=reviewer,
        )

        # Step 2: Reverse disposition to REJECT
        dec2, evt2 = counsel_checkpoint_manager.apply_review_action(
            action=ReviewAction.REJECT,
            lineage_key=key,
            rationale="Adverse discovery: Trademark claim asserted on magazine cover masthead. Rejected.",
            reviewer=reviewer,
        )

        assert dec2.status == DecisionStatus.REJECTED
        assert evt2.prior_status == DecisionStatus.APPROVED
        assert evt2.new_status == DecisionStatus.REJECTED
        assert evt2.prior_state == DecisionState.RE_ATTESTED
        assert evt2.new_state == DecisionState.EXCEPTION
        assert evt2.parent_event_hash == evt1.event_hash

        # Step 3: Audit trail inspection
        trail = counsel_checkpoint_manager.get_audit_trail(key)
        assert len(trail) == 2
        assert trail[0].event_hash == evt1.event_hash
        assert trail[1].event_hash == evt2.event_hash
        assert trail[1].parent_event_hash == trail[0].event_hash

        # Queue still contains exactly 2 items
        assert len(counsel_checkpoint_manager._current_queue.items) == 2

        # Ledger valid
        assert counsel_checkpoint_manager.verify_ledger_integrity()["is_valid"] is True


# =============================================================================
# 6. CITATION METADATA, TIMESTAMPS & LATENCIES
# =============================================================================

class TestCitationMetadataTimestampsAndLatencies:
    """
    Verifies evidence snapshots contain complete, attributable metadata:
    - Attributable source_title
    - Valid, well-formed source_url
    - retrieval_latency_ms > 0
    - Valid ISO 8601 timestamps
    - Cryptographic SHA-256 payload hash
    """

    @pytest.mark.asyncio
    async def test_parallel_search_evidence_contains_complete_metadata(self):
        """Validates all metadata fields on search evidence snapshots."""
        parallel = ParallelSearchService(use_fallback=True, mock_latency_ms=45.0)

        # Item 11: Poster search query
        ev_poster = await parallel.search(
            query="Shadows of Manhattan Detective Magazine 1944 LOC copyright renewal",
            use_id="use_v8_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            expected_stance=EvidenceStance.SUPPORTING,
        )

        assert ev_poster.source_title and isinstance(ev_poster.source_title, str)
        assert len(ev_poster.source_title.strip()) > 0
        assert "Copyright" in ev_poster.source_title or "Renewal" in ev_poster.source_title

        assert ev_poster.source_url.startswith("https://") or ev_poster.source_url.startswith("http://")
        parsed_url = urlsplit(ev_poster.source_url)
        assert parsed_url.netloc and len(parsed_url.netloc) > 3

        assert isinstance(ev_poster.retrieval_latency_ms, (int, float))
        assert ev_poster.retrieval_latency_ms > 0.0

        # Validate ISO 8601 timestamp
        assert ev_poster.retrieved_at and isinstance(ev_poster.retrieved_at, str)
        parsed_dt = datetime.fromisoformat(ev_poster.retrieved_at)
        assert parsed_dt.year >= 2026

        # Validate SHA-256 payload hash (64 hex characters)
        assert ev_poster.raw_payload_hash and len(ev_poster.raw_payload_hash) == 64
        assert re.match(r"^[0-9a-f]{64}$", ev_poster.raw_payload_hash)

        # Item 12: Music cue search query
        ev_music = await parallel.search(
            query="Midnight Serenade Vanguard Media copyright assignment ASCAP",
            use_id="use_v8_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            expected_stance=EvidenceStance.CONTRADICTORY,
        )

        assert ev_music.source_title and "ASCAP" in ev_music.source_title
        assert ev_music.source_url.startswith("https://")
        assert urlsplit(ev_music.source_url).netloc == "ascap.com"
        assert ev_music.retrieval_latency_ms > 0.0
        assert datetime.fromisoformat(ev_music.retrieved_at)
        assert len(ev_music.raw_payload_hash) == 64

    @pytest.mark.asyncio
    async def test_claims_payload_carries_citation_telemetry(self):
        """Asserts that claims returned by execute_drift_detection preserve citation metadata."""
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection()

        for claim in result.claims:
            ev = claim.get("evidence")
            if ev:
                assert ev["provider"] == "Parallel"
                assert ev["source_title"] and len(ev["source_title"]) > 0
                assert ev["source_url"] and ev["source_url"].startswith("http")
                assert ev["stance"] in ("supporting", "contradictory", "informational", "insufficient")
                if claim["state"] == "stale":
                    assert ev["latency_ms"] is not None
                    assert ev["latency_ms"] >= 0.0

    def test_exceptions_schedule_items_preserve_evidence_citations(self):
        """Asserts that citations embedded into ExceptionsScheduleItem retain all required attributes."""
        _, _, _, initial_evidence = get_golden_fixtures()
        v7_uses, v8_uses, v7_decisions, _ = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            base_uses=v7_uses,
        )

        # Locate Item 11 and Item 12
        item_11 = next(it for it in schedule.items if it.stable_lineage_key == "poster_noir_detective_magazine")
        item_12 = next(it for it in schedule.items if it.stable_lineage_key == "music_cue_midnight_serenade")

        for item in (item_11, item_12):
            assert len(item.evidence_citations) > 0, f"Item {item.stable_lineage_key} missing citations"
            for cit in item.evidence_citations:
                assert cit.get("source_title") and len(cit["source_title"]) > 0
                assert cit.get("source_url") and cit["source_url"].startswith("http")
                assert cit.get("excerpt") and len(cit["excerpt"]) > 0
                assert cit.get("provider") == "Parallel"


# =============================================================================
# 7. PRINT ENGINE PARITY
# =============================================================================

class TestPrintEngineParity:
    """
    Verifies that the SSR Form E&O-2026 report HTML contains:
    - @media print CSS rules
    - print-hide and no-print classes
    - page break controls (break-inside: avoid, page-break-inside: avoid)
    - Full parity across backend SSR renderer and frontend globals.css.
    """

    def test_ssr_html_contains_media_print_rules_and_print_hide(self):
        """
        Asserts that InvalidationEngine.render_form_eo_2026_html produces
        HTML with complete print styling for underwriter PDF / print generation.
        """
        v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()
        validity = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )
        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity,
            base_uses=v7_uses,
        )

        html = InvalidationEngine.render_form_eo_2026_html(schedule)

        # 1. Asserts @media print CSS rules
        assert "@media print" in html

        # 2. Asserts print-hide classes
        assert ".print-hide" in html or "print-hide" in html
        assert ".no-print" in html or "no-print" in html

        # 3. Asserts page break controls
        assert "break-inside: avoid" in html or "break-inside:avoid" in html
        assert "page-break-inside: avoid" in html or "page-break-inside:avoid" in html

    def test_ssr_endpoints_serve_print_compliant_html(self):
        """
        Asserts that GET /report/{production_id} and GET /api/reports/form-eo-2026/html
        return HTTP 200 text/html with all required print engine rules.
        """
        for path in ("/report/proj_blockbuster_cinema", "/api/reports/form-eo-2026/html"):
            res = client.get(path)
            assert res.status_code == 200
            assert "text/html" in res.headers["content-type"]
            html = res.text

            assert "@media print" in html
            assert "print-hide" in html
            assert "no-print" in html
            assert "break-inside: avoid" in html

    def test_frontend_globals_css_print_parity(self):
        """
        Verifies that frontend/app/globals.css contains matching print rules:
        @media print, .print-hide, .no-print, and page break controls.
        """
        css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "app", "globals.css")
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            assert "@media print" in css_content
            assert ".print-hide" in css_content
            assert ".no-print" in css_content
            assert "page-break-inside: avoid" in css_content or "break-inside: avoid" in css_content
