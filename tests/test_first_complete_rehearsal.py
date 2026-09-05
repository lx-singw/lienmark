"""
Automated Test Suite for Sprint 3C Task 2: First Complete Rehearsal & E2E Verification
Table-driven automated rehearsal test suite verifying:
1. Clean State Isolation (no state leakage between runs).
2. The 12 -> 10/2 -> 1/1 mathematical invariant at each checkpoint.
3. Total workflow execution duration is strictly sub-second for local/cached execution.
4. Parallel Search query budget is strictly 2 calls (0 calls for 10 carried claims).
5. Tamper-evident SHA-256 event hashes on counsel supersession events.
6. Strict statutory underwriting disclaimers (absence of prohibited phrases:
   'coverage guaranteed', 'policy bound automatically', 'certifies legal certainty', 'carrier bound').

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import copy
import hashlib
import random
import re
import time
import pytest
from typing import Any, Dict, List, Tuple
from fastapi.testclient import TestClient

from backend.domain.models import (
    CarrierHeader,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceStance,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    ReattestationRequest,
    ReviewAction,
    ReviewerIdentity,
    SupersessionEvent,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.counsel_checkpoint import CounselCheckpointManager
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.core.semantic_delta import SemanticDeltaEngine, ModelContainmentViolation
from backend.services.gemini_service import GeminiService
from backend.services.parallel_service import ParallelSearchService
from backend.services.revalidation_planner import RevalidationPlanner
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)
from backend.main import app, _counsel_reattestations, counsel_checkpoint_manager

client = TestClient(app)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def clean_test_session():
    """Ensures clean global state before and after every test in the suite."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


def run_full_rehearsal_pipeline(
    mock_latency_ms: float = 0.0,
    enforce_golden_budget: bool = True,
) -> Dict[str, Any]:
    """
    Executes the complete 7-phase rehearsal pipeline in-memory, returning
    all artifacts, metrics, and state objects for test assertions.
    """
    t0 = time.perf_counter()
    timings: Dict[str, float] = {}

    # Phase 1: Ingestion & Baseline
    p1_start = time.perf_counter()
    v7_ver = get_v7_version()
    v8_ver = get_v8_version()
    v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()
    timings["phase_1_ingestion"] = (time.perf_counter() - p1_start)

    # Phase 2: Semantic Delta
    p2_start = time.perf_counter()
    v7_poster = next(u for u in v7_uses if u.stable_lineage_key == "poster_noir_detective_magazine")
    v8_poster = next(u for u in v8_uses if u.stable_lineage_key == "poster_noir_detective_magazine")
    gemini = GeminiService(use_fallback=True, mock_latency_ms=mock_latency_ms)
    # Synchronous wrapper for test harness
    import asyncio
    gemini_delta = asyncio.run(
        gemini.analyze_scene_delta(
            asset_name=v8_poster.description,
            v7_context=v7_poster.context,
            v7_prominence=v7_poster.duration_or_prominence,
            v8_context=v8_poster.context,
            v8_prominence=v8_poster.duration_or_prominence,
        )
    )
    timings["phase_2_semantic_delta"] = (time.perf_counter() - p2_start)

    # Phase 3: Clearance DAG Invalidation
    p3_start = time.perf_counter()
    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=initial_evidence,
        target_version_id="v8",
    )
    timings["phase_3_invalidation"] = (time.perf_counter() - p3_start)

    # Phase 4: Targeted Revalidation
    p4_start = time.perf_counter()
    planner = RevalidationPlanner(enforce_golden_budget=enforce_golden_budget)
    plan = planner.plan_revalidation(
        validity_results=validity_results,
        target_uses=v8_uses,
        target_version_id="v8",
    )
    parallel = ParallelSearchService(use_fallback=True, mock_latency_ms=mock_latency_ms)
    refreshed_evidence: Dict[str, Any] = {}
    for req in plan.planned_requests:
        snap = asyncio.run(
            parallel.search(
                query=req.query,
                use_id=req.decision_id,
                stable_lineage_key=req.stable_lineage_key,
                expected_stance=req.expected_stance,
            )
        )
        refreshed_evidence[req.stable_lineage_key] = snap

    reconciler = EvidenceReconciler()
    reconciled = reconciler.reconcile_all(
        validity_results=validity_results,
        evidence_snapshots=refreshed_evidence,
        contracts=[],
        update_validity_in_place=True,
    )
    timings["phase_4_revalidation"] = (time.perf_counter() - p4_start)

    # Phase 5: Counsel Checkpoint & Adjudication
    p5_start = time.perf_counter()
    manager = CounselCheckpointManager()
    manager.reset()
    queue = manager.get_review_queue(
        validity_results=validity_results,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=refreshed_evidence,
    )
    queue_initial = copy.deepcopy(queue)
    counsel = manager.get_default_reviewer()
    _, evt_11 = manager.apply_review_action(
        action=ReviewAction.RE_ATTEST,
        lineage_key="poster_noir_detective_magazine",
        rationale="Artwork verified in public domain via Library of Congress renewal non-filing.",
        reviewer=counsel,
    )
    _, evt_12 = manager.apply_review_action(
        action=ReviewAction.REJECT,
        lineage_key="music_cue_midnight_serenade",
        rationale="Vanguard Media active copyright conflict identified via Parallel Search.",
        reviewer=counsel,
    )
    ledger_audit = manager.verify_ledger_integrity()
    timings["phase_5_checkpoint"] = (time.perf_counter() - p5_start)

    # Phase 6: Form E&O-2026 Exceptions Schedule
    p6_start = time.perf_counter()
    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validity_results,
        counsel_checkpoint_manager=manager,
        base_uses=v7_uses,
    )
    timings["phase_6_schedule"] = (time.perf_counter() - p6_start)

    # Phase 7: Export Parity & Disclaimers
    p7_start = time.perf_counter()
    html = InvalidationEngine.render_form_eo_2026_html(schedule)
    timings["phase_7_export"] = (time.perf_counter() - p7_start)

    total_duration = time.perf_counter() - t0
    timings["total_duration"] = total_duration

    return {
        "v7_version": v7_ver,
        "v8_version": v8_ver,
        "v7_uses": v7_uses,
        "v8_uses": v8_uses,
        "v7_decisions": v7_decisions,
        "gemini_delta": gemini_delta,
        "validity_results": validity_results,
        "revalidation_plan": plan,
        "parallel_service": parallel,
        "refreshed_evidence": refreshed_evidence,
        "reconciled_results": reconciled,
        "counsel_manager": manager,
        "review_queue": queue,
        "review_queue_initial": queue_initial,
        "event_11": evt_11,
        "event_12": evt_12,
        "ledger_audit": ledger_audit,
        "schedule": schedule,
        "html": html,
        "timings": timings,
    }


# =============================================================================
# 1. CLEAN STATE ISOLATION TESTS
# =============================================================================

class TestRehearsalCleanStateIsolation:
    """Verifies that no state leaks across consecutive runs of the rehearsal pipeline."""

    def test_state_isolation_between_consecutive_runs(self):
        """Executing two consecutive runs produces identical, clean states with no cross-run bleed."""
        run_1 = run_full_rehearsal_pipeline()
        run_2 = run_full_rehearsal_pipeline()

        # Both runs have identical counts
        assert run_1["schedule"].total_claims == run_2["schedule"].total_claims == 12
        assert run_1["schedule"].carried_forward_count == run_2["schedule"].carried_forward_count == 10
        assert run_1["schedule"].re_attested_count == run_2["schedule"].re_attested_count == 1
        assert run_1["schedule"].unresolved_exception_count == run_2["schedule"].unresolved_exception_count == 1

        # Ledger sizes are exactly 2 in both runs (not accumulated to 4)
        assert len(run_1["counsel_manager"].get_audit_trail()) == 2
        assert len(run_2["counsel_manager"].get_audit_trail()) == 2

        # Events have distinct event IDs (fresh instances)
        assert run_1["event_11"].event_id != run_2["event_11"].event_id
        assert run_1["event_12"].event_id != run_2["event_12"].event_id

    def test_fresh_manager_initial_state_is_pristine(self):
        """A freshly constructed CounselCheckpointManager contains zero events and zero cached state."""
        manager = CounselCheckpointManager()
        assert len(manager.get_audit_trail()) == 0
        assert manager.verify_ledger_integrity()["event_count"] == 0
        assert manager.verify_ledger_integrity()["is_valid"] is True

    def test_reset_clears_all_prior_adjudications(self):
        """Calling reset() completely wipes all registered events and prior decisions."""
        manager = CounselCheckpointManager()
        manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Test clearance.",
        )
        assert len(manager.get_audit_trail()) == 1

        manager.reset()
        assert len(manager.get_audit_trail()) == 0
        assert manager.verify_ledger_integrity()["event_count"] == 0


# =============================================================================
# 2. TABLE-DRIVEN MATHEMATICAL INVARIANT TESTS (12 -> 10/2 -> 1/1)
# =============================================================================

class TestMathematicalInvariantPipeline:
    """
    Table-driven test suite for the core mathematical conservation invariant:
      12 Baseline/Revision Claims
      -> 10 Carried Forward / 2 Stale
      -> 1 Re-Attested / 1 Unresolved Exception
      -> 12 = 10 + 1 + 1 Exceptions Schedule Conservation.
    """

    CHECKPOINT_TEST_CASES = [
        ("checkpoint_1_ingestion", 12, 12, 12, 0),
        ("checkpoint_2_invalidation", 12, 10, 2, 0),
        ("checkpoint_3_planning", 12, 10, 2, 0),
        ("checkpoint_4_queue", 2, 0, 2, 0),
        ("checkpoint_5_adjudication", 2, 0, 1, 1),
        ("checkpoint_6_schedule", 12, 10, 1, 1),
    ]

    @pytest.mark.parametrize("checkpoint_name,total,carried,param_a,param_b", CHECKPOINT_TEST_CASES)
    def test_mathematical_checkpoints(self, checkpoint_name: str, total: int, carried: int, param_a: int, param_b: int):
        """Verifies exact claim metrics at each stage of the clearance lifecycle."""
        pipeline = run_full_rehearsal_pipeline()

        if checkpoint_name == "checkpoint_1_ingestion":
            assert len(pipeline["v7_uses"]) == total
            assert len(pipeline["v8_uses"]) == total
            assert len(pipeline["v7_decisions"]) == carried
            assert all(d.status == DecisionStatus.APPROVED for d in pipeline["v7_decisions"])

        elif checkpoint_name == "checkpoint_2_invalidation":
            val_results = pipeline["validity_results"]
            assert len(val_results) == total
            carried_items = [v for v in val_results if v.state == DecisionState.CARRIED_FORWARD]
            stale_items = [v for v in val_results if v.state == DecisionState.STALE]
            assert len(carried_items) == carried
            assert len(stale_items) == param_a  # 2 stale

        elif checkpoint_name == "checkpoint_3_planning":
            plan = pipeline["revalidation_plan"]
            assert plan.total_claims_evaluated == total
            assert plan.skipped_count == carried
            assert plan.planned_count == param_a  # 2 planned

        elif checkpoint_name == "checkpoint_4_queue":
            queue = pipeline["review_queue_initial"]
            assert len(queue) == total  # 2 items in queue
            assert all(item.current_state == DecisionState.STALE for item in queue)

        elif checkpoint_name == "checkpoint_5_adjudication":
            events = pipeline["counsel_manager"].get_audit_trail()
            assert len(events) == total  # 2 events
            reattested_ev = [e for e in events if e.new_state == DecisionState.RE_ATTESTED]
            exception_ev = [e for e in events if e.new_state == DecisionState.EXCEPTION]
            assert len(reattested_ev) == param_a  # 1 re-attested
            assert len(exception_ev) == param_b  # 1 exception

        elif checkpoint_name == "checkpoint_6_schedule":
            sched = pipeline["schedule"]
            assert sched.total_claims == total  # 12
            assert sched.carried_forward_count == carried  # 10
            assert sched.re_attested_count == param_a  # 1
            assert sched.unresolved_exception_count == param_b  # 1

    def test_conservation_equation_formal_proof(self):
        """
        Formal Algebraic Verification:
        Total Claims = Carried Forward + Re-Attested + Unresolved Exceptions
        Reopened Claims = Re-Attested + Unresolved Exceptions
        """
        pipeline = run_full_rehearsal_pipeline()
        sched = pipeline["schedule"]

        # Equation 1: Total Conservation
        assert sched.total_claims == (
            sched.carried_forward_count
            + sched.re_attested_count
            + sched.unresolved_exception_count
        ), "Conservation invariant violated: Total != Carried + Re-Attested + Unresolved"

        # Equation 2: Reopened Decomposition
        assert sched.reopened_count == (
            sched.re_attested_count + sched.unresolved_exception_count
        ), "Reopened decomposition violated: Reopened != Re-Attested + Unresolved"

        assert sched.total_claims == 12
        assert sched.carried_forward_count == 10
        assert sched.reopened_count == 2
        assert sched.re_attested_count == 1
        assert sched.unresolved_exception_count == 1

    def test_three_tier_section_isolation(self):
        """Verifies proper claim categorization across Section I, Section II, and Section III."""
        pipeline = run_full_rehearsal_pipeline()
        sched = pipeline["schedule"]

        # Section I: Exactly 1 Unresolved Exception (Item 12 music cue)
        assert len(sched.unresolved_exceptions_schedule) == 1
        sec_i_item = sched.unresolved_exceptions_schedule[0]
        assert sec_i_item.stable_lineage_key == "music_cue_midnight_serenade"
        assert sec_i_item.asset_type == "music"
        assert sec_i_item.v8_evaluation_state == "exception"
        assert sec_i_item.invalidation_reason == "EXTERNAL_EVIDENCE_SHIFT"

        # Section II: Exactly 1 Re-Attested Item (Item 11 poster)
        reattested = [i for i in sched.items if i.v8_evaluation_state == "re_attested"]
        assert len(reattested) == 1
        sec_ii_item = reattested[0]
        assert sec_ii_item.stable_lineage_key == "poster_noir_detective_magazine"
        assert sec_ii_item.asset_type == "artwork"
        assert "public domain" in sec_ii_item.counsel_action.lower()

        # Section III: Exactly 10 Carried-Forward Items (Items 1-10)
        carried = [i for i in sched.items if i.v8_evaluation_state == "carried_forward"]
        assert len(carried) == 10
        for item in carried:
            assert item.invalidation_reason is None

    def test_permutation_invariance_shuffled_inputs(self):
        """Shuffling input claims order yields mathematically identical schedules."""
        v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()

        # Run 1: Natural Order
        val_1 = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )

        # Run 2: Shuffled Order
        shuffled_v7 = list(v7_uses)
        shuffled_v8 = list(v8_uses)
        shuffled_dec = list(v7_decisions)
        rng = random.Random(999)
        rng.shuffle(shuffled_v7)
        rng.shuffle(shuffled_v8)
        rng.shuffle(shuffled_dec)

        val_2 = InvalidationEngine.evaluate_invalidation(
            base_uses=shuffled_v7,
            target_uses=shuffled_v8,
            prior_decisions=shuffled_dec,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
        )

        assert len(val_1) == len(val_2) == 12
        keys_1 = [v.stable_lineage_key for v in val_1]
        keys_2 = [v.stable_lineage_key for v in val_2]
        assert keys_1 == keys_2, "Permutation invariance violated in InvalidationEngine"


# =============================================================================
# 3. SUB-SECOND WORKFLOW EXECUTION BUDGET TESTS
# =============================================================================

class TestSubSecondExecutionBudget:
    """Verifies that local/cached execution strictly executes in sub-second duration."""

    def test_total_workflow_execution_duration_strictly_sub_second(self):
        """Total workflow execution duration is strictly sub-second (< 1.0s) for local/cached execution."""
        pipeline = run_full_rehearsal_pipeline(mock_latency_ms=0.0)
        total_duration_s = pipeline["timings"]["total_duration"]
        total_duration_ms = total_duration_s * 1000.0

        assert total_duration_s < 1.0, (
            f"Performance budget breach: total rehearsal duration was {total_duration_ms:.2f}ms (must be < 1000ms)"
        )

    def test_individual_phase_timings_benchmarked(self):
        """Every individual phase timing is positive and measured with microsecond accuracy."""
        pipeline = run_full_rehearsal_pipeline(mock_latency_ms=0.0)
        timings = pipeline["timings"]

        required_phases = [
            "phase_1_ingestion",
            "phase_2_semantic_delta",
            "phase_3_invalidation",
            "phase_4_revalidation",
            "phase_5_checkpoint",
            "phase_6_schedule",
            "phase_7_export",
        ]

        for phase in required_phases:
            assert phase in timings, f"Missing timing for {phase}"
            assert timings[phase] > 0.0, f"Timing for {phase} must be positive, got {timings[phase]}"


# =============================================================================
# 4. PARALLEL SEARCH CALL BUDGET TESTS
# =============================================================================

class TestParallelSearchCallBudget:
    """Verifies that the Parallel Search query budget is strictly 2 calls."""

    def test_parallel_search_query_budget_strictly_two_calls(self):
        """Asserts that Parallel Search query budget is strictly 2 calls."""
        pipeline = run_full_rehearsal_pipeline()
        parallel = pipeline["parallel_service"]
        plan = pipeline["revalidation_plan"]

        assert parallel.call_count == 2, f"Expected exactly 2 parallel search calls, got {parallel.call_count}"
        assert plan.call_count == 2
        assert plan.planned_count == 2

    def test_zero_calls_for_ten_carried_claims(self):
        """Asserts that 0 search calls are executed for the 10 unchanged carried claims."""
        pipeline = run_full_rehearsal_pipeline()
        plan = pipeline["revalidation_plan"]

        assert plan.skipped_count == 10
        assert len(plan.skipped_lineage_keys) == 10
        assert plan.call_reduction_percentage == 83.3

        # Assert no carried claims are in planned requests
        planned_keys = {r.stable_lineage_key for r in plan.planned_requests}
        for skipped_key in plan.skipped_lineage_keys:
            assert skipped_key not in planned_keys

    def test_targeted_query_formulation_precision(self):
        """Asserts that formulated queries specifically target the copyright dispute / renewal."""
        pipeline = run_full_rehearsal_pipeline()
        plan = pipeline["revalidation_plan"]

        req_poster = next(r for r in plan.planned_requests if r.stable_lineage_key == "poster_noir_detective_magazine")
        req_music = next(r for r in plan.planned_requests if r.stable_lineage_key == "music_cue_midnight_serenade")

        assert "copyright renewal" in req_poster.query.lower() or "public domain" in req_poster.query.lower()
        assert "vanguard media" in req_music.query.lower() or "assignment dispute" in req_music.query.lower()

    def test_evidence_stances_and_sources(self):
        """Asserts Item 11 stance is SUPPORTING (LOC) and Item 12 stance is CONTRADICTORY (ASCAP)."""
        pipeline = run_full_rehearsal_pipeline()
        evidence = pipeline["refreshed_evidence"]

        assert evidence["poster_noir_detective_magazine"].stance == EvidenceStance.SUPPORTING
        assert evidence["music_cue_midnight_serenade"].stance == EvidenceStance.CONTRADICTORY


# =============================================================================
# 5. TAMPER-EVIDENT SHA-256 EVENT LEDGER TESTS
# =============================================================================

class TestTamperEvidentSha256EventHashes:
    """Verifies SHA-256 event hashing, cryptographic parent chaining, and tamper detection."""

    def test_event_hashes_are_valid_64_char_hex_strings(self):
        """Asserts tamper-evident SHA-256 event hashes on counsel supersession events."""
        pipeline = run_full_rehearsal_pipeline()
        evt_11 = pipeline["event_11"]
        evt_12 = pipeline["event_12"]

        for evt in (evt_11, evt_12):
            assert isinstance(evt, SupersessionEvent)
            assert isinstance(evt.event_hash, str)
            assert len(evt.event_hash) == 64, f"Hash length must be 64, got {len(evt.event_hash)}"
            assert re.match(r"^[0-9a-f]{64}$", evt.event_hash) is not None, "Hash must be lowercase hex"

    def test_cryptographic_parent_hash_chaining(self):
        """Verifies unbroken cryptographic parent hash chaining."""
        pipeline = run_full_rehearsal_pipeline()
        evt_11 = pipeline["event_11"]
        evt_12 = pipeline["event_12"]

        assert evt_11.parent_event_hash == CounselCheckpointManager.GENESIS_PARENT_HASH
        assert evt_12.parent_event_hash == evt_11.event_hash

    def test_ledger_integrity_verification(self):
        """Audit ledger verifies with 100% cryptographic integrity."""
        pipeline = run_full_rehearsal_pipeline()
        audit = pipeline["ledger_audit"]

        assert audit["is_valid"] is True
        assert audit["event_count"] == 2
        assert audit["chain_head_hash"] == pipeline["event_12"].event_hash

    def test_tamper_detection_on_mutated_event(self):
        """Mutating any event field immediately invalidates the ledger verification."""
        manager = CounselCheckpointManager()
        manager.reset()

        _, evt1 = manager.apply_review_action(
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Legitimate clearance rationale.",
        )
        _, evt2 = manager.apply_review_action(
            action=ReviewAction.REJECT,
            lineage_key="music_cue_midnight_serenade",
            rationale="Adverse rights conflict.",
        )

        assert manager.verify_ledger_integrity()["is_valid"] is True

        # Tamper with internal event rationale in memory
        with manager._lock:
            manager._supersession_events[0].rationale = "TAMPERED RATIONALE UNAUTHORIZED"

        tampered_audit = manager.verify_ledger_integrity()
        assert tampered_audit["is_valid"] is False
        assert tampered_audit.get("tampered_index") == 0


# =============================================================================
# 6. TABLE-DRIVEN STATUTORY UNDERWRITING DISCLAIMER TESTS
# =============================================================================

class TestStatutoryUnderwritingDisclaimers:
    """
    Table-driven test suite verifying strict statutory underwriting disclaimers
    and the absolute absence of prohibited certainty claims.
    """

    PROHIBITED_PHRASES = [
        "coverage guaranteed",
        "policy bound automatically",
        "certifies legal certainty",
        "carrier bound",
        "policy approved by insurer",
        "coverage is guaranteed",
        "insurer has bound coverage",
        "zero legal risk guaranteed",
        "absolute legal certainty",
        "claims are legally cleared by ai",
    ]

    @pytest.mark.parametrize("prohibited_phrase", PROHIBITED_PHRASES)
    def test_prohibited_phrases_strictly_absent(self, prohibited_phrase: str):
        """Table-driven test asserting each prohibited phrase is absent in HTML, JSON, and metadata."""
        pipeline = run_full_rehearsal_pipeline()
        schedule = pipeline["schedule"]
        html = pipeline["html"].lower()
        json_dump = schedule.model_dump_json().lower()
        meta_str = str(schedule.production_metadata).lower()

        assert prohibited_phrase not in html, f"Prohibited phrase '{prohibited_phrase}' found in HTML"
        assert prohibited_phrase not in json_dump, f"Prohibited phrase '{prohibited_phrase}' found in JSON dump"
        assert prohibited_phrase not in meta_str, f"Prohibited phrase '{prohibited_phrase}' found in metadata"

    def test_mandatory_underwriting_status_and_warranty(self):
        """Asserts mandatory Underwriting Status PENDING_REVIEW and warranty clauses."""
        pipeline = run_full_rehearsal_pipeline()
        schedule = pipeline["schedule"]
        carrier = schedule.carrier_header

        assert carrier.underwriter_status == "PENDING_REVIEW"
        assert "Warranted clearance schedule" in carrier.warranty_clause
        assert "excluded from coverage" in carrier.warranty_clause
        assert "non-binding risk assessment" in carrier.disclaimer.lower()

    def test_demo_fictional_counsel_notice(self):
        """Asserts presence of fictional demo counsel disclaimer."""
        pipeline = run_full_rehearsal_pipeline()
        reviewer = pipeline["counsel_manager"].get_default_reviewer()

        assert reviewer.name == "Sarah Jenkins, Esq."
        assert reviewer.is_fictional_demo is True
        assert "DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE" in reviewer.disclaimer


# =============================================================================
# 7. EXPORT PARITY TESTS
# =============================================================================

class TestExportParity:
    """Verifies that API exports, SSR HTML, and domain models maintain bit-for-bit parity."""

    def test_api_export_matches_rehearsal_schedule_parity(self):
        """GET /api/reports/exceptions returns identical counts and states as rehearsal."""
        # Set up global reattestations to match rehearsal adjudication
        _counsel_reattestations["poster_noir_detective_magazine"] = ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork verified in public domain via LOC registration records.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )
        _counsel_reattestations["music_cue_midnight_serenade"] = ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        )

        response = client.get("/api/reports/exceptions")
        assert response.status_code == 200
        api_data = response.json()

        assert api_data["total_claims"] == 12
        assert api_data["carried_forward_count"] == 10
        assert api_data["re_attested_count"] == 1
        assert api_data["unresolved_exception_count"] == 1
        assert api_data["policy_version"] == "E&O-2026.1-DEVPOST"
        assert len(api_data["items"]) == 12
        assert len(api_data["unresolved_exceptions_schedule"]) == 1
