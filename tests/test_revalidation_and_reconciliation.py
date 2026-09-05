"""
Unit and Integration Tests for Sprint 2C: Targeted Revalidation & Evidence Reconciliation Engine
Tests:
1. RevalidationPlanner: selective planning, minimal API budget enforcement (len == 2),
   exact query formulation (Query 1 and Query 2), carried-forward skipping (10 items).
2. EvidenceReconciler: stance categorization (SUPPORTING, INFORMATIONAL, CONTRADICTORY, INSUFFICIENT),
   private contract reconciliation (17 U.S.C. § 205(e) contract shield), judicial injunction override,
   non-perpetual contract handling.
3. Fail-Closed Policy: search failure (timeout, 5xx, rate limit) -> stance INSUFFICIENT,
   decision STALE, revalidation_action='manual'.
4. End-to-End Workflow Wiring: LienmarkWorkflow integration traces, revalidation plan,
   and contract reconciliation.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from backend.domain.models import (
    ChangeKind,
    ContractAgreement,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceReconciliationResult,
    EvidenceStance,
    PublicEvidenceSnapshot,
    ReattestationRequest,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.dependency_graph import ClearanceDependencyGraph
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.services.revalidation_planner import (
    RevalidationPlanner,
    RevalidationPlan,
    PlannedRevalidationRequest,
    MinimalBudgetViolationError,
)
from backend.services.parallel_service import ParallelSearchService
from backend.orchestration.workflow import LienmarkWorkflow
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)


# =====================================================================
# TASK 1 TESTS: REVALIDATION PLANNER & BUDGET GOVERNANCE
# =====================================================================

class TestRevalidationPlanner:
    """Tests selective planning and minimal API budget enforcement."""

    def test_golden_dataset_enforces_exactly_two_planned_requests(self):
        """Enforces assertion: len(planned_requests) == 2 for the 12-item golden dataset."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        planner = RevalidationPlanner(enforce_golden_budget=True)
        plan = planner.plan_revalidation(
            validity_results=validity_results,
            target_uses=v8_uses,
            target_version_id="v8",
        )

        # Core Assertion: exactly 2 planned requests, exactly 10 skipped
        assert len(plan) == 2, f"Golden dataset must plan exactly 2 revalidations, got {len(plan)}"
        assert len(plan.planned_requests) == 2
        assert plan.planned_count == 2
        assert plan.skipped_count == 10
        assert plan.total_claims_evaluated == 12
        assert plan.api_call_budget_enforced is True

        planned_keys = {r.stable_lineage_key for r in plan.planned_requests}
        assert "poster_noir_detective_magazine" in planned_keys
        assert "music_cue_midnight_serenade" in planned_keys

    def test_strictly_skips_ten_unchanged_carried_forward_claims(self):
        """Strictly skips the 10 unchanged carried-forward claims, enforcing minimal API call budget."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        planner = RevalidationPlanner(enforce_golden_budget=True)
        plan = planner.plan_revalidation(validity_results, target_uses=v8_uses)

        assert len(plan.skipped_lineage_keys) == 10
        unchanged_expected = [
            "prop_vintage_telephone",
            "poster_paris_expo_1937",
            "car_ford_sedan_1949",
            "trademark_acme_coffee",
            "artwork_abstract_expressionist",
            "likeness_mayor_cameo",
            "architecture_tribunal_facade",
            "text_headline_gazette",
            "wardrobe_fedora_brand",
            "music_incidental_radio_static",
        ]
        for key in unchanged_expected:
            assert key in plan.skipped_lineage_keys, f"Carried forward claim '{key}' must be skipped"

    def test_formulates_exact_targeted_queries(self):
        """Formulates targeted queries tailored for Parallel Search API:
        Query 1: 'Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC'
        Query 2: 'Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute'
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        planner = RevalidationPlanner(enforce_golden_budget=True)
        plan = planner.plan_revalidation(validity_results, target_uses=v8_uses)

        query_map = {r.stable_lineage_key: r.query for r in plan.planned_requests}

        # Query 1 exact check
        assert query_map["poster_noir_detective_magazine"] == (
            "Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC"
        )
        # Query 2 exact check
        assert query_map["music_cue_midnight_serenade"] == (
            "Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute"
        )

    def test_revalidation_planner_from_clearance_dependency_graph(self):
        """Verifies RevalidationPlanner can plan directly from a ClearanceDependencyGraph."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        graph = ClearanceDependencyGraph.build_clearance_graph(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
        )

        planner = RevalidationPlanner(enforce_golden_budget=True)
        plan = planner.plan_from_graph(graph=graph, target_uses=v8_uses, target_version_id="v8")

        assert len(plan) == 2
        assert plan.planned_count == 2
        assert plan.skipped_count == 10
        planned_keys = {r.stable_lineage_key for r in plan.planned_requests}
        assert "poster_noir_detective_magazine" in planned_keys
        assert "music_cue_midnight_serenade" in planned_keys

    def test_idempotent_evaluation_plans_zero_requests(self):
        """Evaluating identical version (v7 against v7) produces 0 planned requests and 12 skipped claims."""
        v7_uses, _, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v7_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v7",
        )

        planner = RevalidationPlanner(enforce_golden_budget=False)
        plan = planner.plan_revalidation(validity_results, target_uses=v7_uses)

        assert len(plan) == 0
        assert plan.planned_count == 0
        assert plan.skipped_count == 12

    def test_budget_violation_raises_error(self):
        """Enforcing max allowed requests raises MinimalBudgetViolationError when exceeded."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        planner = RevalidationPlanner(enforce_golden_budget=False, max_allowed_requests=1)
        with pytest.raises(MinimalBudgetViolationError):
            planner.plan_revalidation(validity_results, target_uses=v8_uses)


# =====================================================================
# TASK 2 TESTS: EVIDENCE RECONCILER & PARALLEL SEARCH
# =====================================================================

class TestEvidenceReconciler:
    """Tests stance categorization, private contract reconciliation, and fail-closed policies."""

    def test_stance_categorization_all_four_stances(self):
        """Categorizes evidence into four stances: SUPPORTING, INFORMATIONAL, CONTRADICTORY, INSUFFICIENT."""
        reconciler = EvidenceReconciler()

        # 1. SUPPORTING
        ev_supporting = PublicEvidenceSnapshot(
            snapshot_id="ev_sup",
            use_id="u1",
            stable_lineage_key="poster_noir_detective_magazine",
            query="Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC",
            source_url="https://cocatalog.loc.gov/1944",
            source_title="US Copyright Office Historical Catalog - LOC",
            excerpt="Cover artwork in public domain in the United States; registration expired without renewal.",
            stance=EvidenceStance.SUPPORTING,
        )
        assert reconciler.classify_stance(ev_supporting) == EvidenceStance.SUPPORTING

        # 2. CONTRADICTORY
        ev_contradictory = PublicEvidenceSnapshot(
            snapshot_id="ev_con",
            use_id="u2",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute",
            source_url="https://ascap.com/midnight",
            source_title="ASCAP Repertory & Rights Registry",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
            stance=EvidenceStance.CONTRADICTORY,
        )
        assert reconciler.classify_stance(ev_contradictory) == EvidenceStance.CONTRADICTORY

        # 3. INFORMATIONAL
        ev_informational = PublicEvidenceSnapshot(
            snapshot_id="ev_info",
            use_id="u3",
            stable_lineage_key="prop_vintage_telephone",
            query="Western Electric rotary phone historical records",
            source_url="https://archives.bellsystem.org/500-model",
            source_title="Historical Catalog Archives",
            excerpt="Model 500 rotary desk set manufactured 1949 to 1984 by Western Electric.",
            stance=EvidenceStance.INFORMATIONAL,
        )
        assert reconciler.classify_stance(ev_informational) == EvidenceStance.INFORMATIONAL

        # 4. INSUFFICIENT (HTTP 500 error, timeout, or empty)
        ev_insufficient_500 = PublicEvidenceSnapshot(
            snapshot_id="ev_err_500",
            use_id="u4",
            stable_lineage_key="some_claim",
            query="test query",
            source_url="https://search.parallel.ai/errors",
            source_title="Parallel Server Error",
            excerpt="Internal server error 500",
            http_status=500,
            stance=EvidenceStance.INSUFFICIENT,
        )
        assert reconciler.classify_stance(ev_insufficient_500) == EvidenceStance.INSUFFICIENT

        ev_insufficient_none = None
        assert reconciler.classify_stance(ev_insufficient_none) == EvidenceStance.INSUFFICIENT

    def test_private_contract_reconciliation_catalog_shift_alone_does_not_void_active_perpetual_contract(self):
        """Private Contract Reconciliation:
        A public catalog ownership shift alone DOES NOT void an existing valid, active, perpetual
        private agreement unless an active revocation or judicial injunction is proven.
        """
        reconciler = EvidenceReconciler()
        music_key = "music_cue_midnight_serenade"

        # Public search reports ownership transfer / assignment to Vanguard Media (normally CONTRADICTORY)
        ev_catalog_shift = PublicEvidenceSnapshot(
            snapshot_id="ev_music_vanguard",
            use_id="use_v8_music_midnight",
            stable_lineage_key=music_key,
            query="Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute",
            source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
            source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC (Kobalt Music admin).",
            stance=EvidenceStance.CONTRADICTORY,
        )

        # Existing valid, active, perpetual private agreement held by production
        perpetual_contract = ContractAgreement(
            agreement_id="agr_sync_midnight_serenade_2024",
            stable_lineage_key=music_key,
            licensor="Blue Note Music Syndicate / Composer Estate",
            licensee="Production Co.",
            scope="Worldwide synchronization and master rights in all media in perpetuity",
            term="In Perpetuity",
            agreement_hash="9f8e7d6c5b4a3210fedcba9876543210",
            is_active=True,
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key=music_key,
            decision_id="dec_v7_music_midnight",
            evidence=ev_catalog_shift,
            contract=perpetual_contract,
        )

        # CONTRACT SHIELD MUST APPLY:
        assert result.contract_shield_applied is True
        assert result.has_contract is True
        assert result.contract_id == "agr_sync_midnight_serenade_2024"
        assert result.raw_stance == EvidenceStance.CONTRADICTORY
        assert result.reconciled_stance == EvidenceStance.SUPPORTING
        assert result.decision_state == DecisionState.CARRIED_FORWARD
        assert result.revalidation_action == "carry"
        assert result.reason_code == "PRIVATE_CONTRACT_SHIELD_APPLIED"
        assert "valid, active, perpetual private agreement" in result.explanation

    def test_private_contract_reconciliation_judicial_injunction_defeats_contract_shield(self):
        """Active revocation or judicial injunction proven in evidence defeats the contract defense."""
        reconciler = EvidenceReconciler()
        music_key = "music_cue_midnight_serenade"

        # Evidence specifically proves a judicial injunction or license revocation
        ev_injunction = PublicEvidenceSnapshot(
            snapshot_id="ev_music_injunction",
            use_id="use_v8_music_midnight",
            stable_lineage_key=music_key,
            query="Midnight Serenade litigation",
            source_url="https://uscourts.gov/opinions/2026-serenade-injunction",
            source_title="US District Court - Judicial Injunction Decree",
            excerpt="Permanent judicial injunction issued enjoining licensee distribution; license revoked for breach.",
            stance=EvidenceStance.CONTRADICTORY,
        )

        perpetual_contract = ContractAgreement(
            agreement_id="agr_sync_midnight_serenade_2024",
            stable_lineage_key=music_key,
            licensor="Original Licensor",
            term="Perpetuity",
            agreement_hash="hash123",
            is_active=True,
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key=music_key,
            decision_id="dec_v7_music_midnight",
            evidence=ev_injunction,
            contract=perpetual_contract,
        )

        # Shield must be defeated by active judicial injunction
        assert result.contract_shield_applied is False
        assert result.reconciled_stance == EvidenceStance.CONTRADICTORY
        assert result.decision_state == DecisionState.STALE
        assert result.revalidation_action == "manual"
        assert result.reason_code == "CONTRACT_REVOCATION_OR_INJUNCTION_PROVEN"
        assert "judicial injunction" in result.explanation.lower()

    def test_private_contract_reconciliation_inactive_or_non_perpetual_contract_fails_shield(self):
        """An inactive or non-perpetual contract does not shield against catalog transfers."""
        reconciler = EvidenceReconciler()
        music_key = "music_cue_midnight_serenade"

        ev_catalog_shift = PublicEvidenceSnapshot(
            snapshot_id="ev_music_vanguard",
            use_id="use_v8_music_midnight",
            stable_lineage_key=music_key,
            query="Midnight Serenade copyright",
            source_url="https://ascap.com",
            source_title="ASCAP Repertory",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
            stance=EvidenceStance.CONTRADICTORY,
        )

        # Case 1: Inactive contract
        inactive_contract = ContractAgreement(
            agreement_id="agr_inactive",
            stable_lineage_key=music_key,
            licensor="Old Owner",
            term="Perpetuity",
            agreement_hash="hash1",
            is_active=False,  # inactive!
        )
        res_inactive = reconciler.reconcile_claim(
            stable_lineage_key=music_key,
            decision_id="dec_1",
            evidence=ev_catalog_shift,
            contract=inactive_contract,
        )
        assert res_inactive.contract_shield_applied is False
        assert res_inactive.decision_state == DecisionState.STALE
        assert res_inactive.reason_code in ("INACTIVE_CONTRACT_WITH_ADVERSE_EVIDENCE", "UNRESOLVED_RIGHTS_DISPUTE")

        # Case 2: Non-perpetual / limited term contract
        limited_contract = ContractAgreement(
            agreement_id="agr_limited",
            stable_lineage_key=music_key,
            licensor="Old Owner",
            scope="Festival screening only",
            term="1 year (expired September 2025)",
            agreement_hash="hash2",
            is_active=True,
        )
        res_limited = reconciler.reconcile_claim(
            stable_lineage_key=music_key,
            decision_id="dec_2",
            evidence=ev_catalog_shift,
            contract=limited_contract,
        )
        assert res_limited.contract_shield_applied is False
        assert res_limited.decision_state == DecisionState.STALE
        assert res_limited.reason_code == "CONTRACT_NON_PERPETUAL_CATALOG_SHIFT"

    def test_fail_closed_policy_on_timeout(self):
        """Fail-Closed Policy: If Parallel Search times out (HTTP 504), marks stance as INSUFFICIENT
        and leaves the clearance decision STALE with revalidation_action='manual'."""
        reconciler = EvidenceReconciler()
        key = "poster_noir_detective_magazine"

        ev_timeout = PublicEvidenceSnapshot(
            snapshot_id="ev_err_timeout",
            use_id="use_v8_poster_noir",
            stable_lineage_key=key,
            query="Shadows of Manhattan",
            source_url="https://search.parallel.ai/timeout",
            source_title="Parallel Search Timeout",
            excerpt="Search failure (HTTP 504): Parallel Search request timed out after 10000ms.",
            http_status=504,
            stance=EvidenceStance.INSUFFICIENT,
            metadata={"fail_closed": True, "error": "timeout"},
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key=key,
            decision_id="dec_v7_poster_noir",
            evidence=ev_timeout,
            contract=None,
        )

        assert result.raw_stance == EvidenceStance.INSUFFICIENT
        assert result.reconciled_stance == EvidenceStance.INSUFFICIENT
        assert result.decision_state == DecisionState.STALE
        assert result.revalidation_action == "manual"
        assert result.reason_code == "SEARCH_EVIDENCE_INSUFFICIENT"
        assert "Fail-closed policy engaged" in result.explanation

    def test_fail_closed_policy_on_5xx_and_rate_limit(self):
        """Fail-Closed Policy: HTTP 500 and 429 rate limit errors mark stance as INSUFFICIENT
        and leave decision STALE with revalidation_action='manual'."""
        reconciler = EvidenceReconciler()
        key = "music_cue_midnight_serenade"

        # HTTP 500 Upstream Server Error
        ev_500 = PublicEvidenceSnapshot(
            snapshot_id="ev_err_500",
            use_id="use_v8_music",
            stable_lineage_key=key,
            query="Midnight Serenade",
            source_url="https://search.parallel.ai/errors",
            source_title="Parallel Search Server Error",
            excerpt="Search failure (HTTP 500): Internal Server Error.",
            http_status=500,
            stance=EvidenceStance.INSUFFICIENT,
            metadata={"fail_closed": True},
        )
        res_500 = reconciler.reconcile_claim(key, "dec_500", ev_500)
        assert res_500.raw_stance == EvidenceStance.INSUFFICIENT
        assert res_500.decision_state == DecisionState.STALE
        assert res_500.revalidation_action == "manual"

        # HTTP 429 Rate Limit
        ev_429 = PublicEvidenceSnapshot(
            snapshot_id="ev_err_429",
            use_id="use_v8_music",
            stable_lineage_key=key,
            query="Midnight Serenade",
            source_url="https://search.parallel.ai/errors",
            source_title="Parallel Search Rate Limit",
            excerpt="Search failure (HTTP 429): Too Many Requests.",
            http_status=429,
            stance=EvidenceStance.INSUFFICIENT,
            metadata={"fail_closed": True},
        )
        res_429 = reconciler.reconcile_claim(key, "dec_429", ev_429)
        assert res_429.raw_stance == EvidenceStance.INSUFFICIENT
        assert res_429.decision_state == DecisionState.STALE
        assert res_429.revalidation_action == "manual"


# =====================================================================
# TASK 2 (PART B) TESTS: PARALLEL SEARCH SERVICE ENHANCEMENTS
# =====================================================================

class TestParallelSearchServiceEnhancements:
    """Tests ParallelSearchService targeted queries and simulated failures."""

    @pytest.mark.asyncio
    async def test_parallel_search_returns_query_1_public_domain_loc(self):
        service = ParallelSearchService(use_fallback=True)
        query = "Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC"
        snapshot = await service.search(
            query=query,
            use_id="use_v8_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
        )
        assert snapshot.stance == EvidenceStance.SUPPORTING
        assert "public domain" in snapshot.excerpt.lower()
        assert "Library of Congress" in snapshot.publisher or "LOC" in snapshot.source_title

    @pytest.mark.asyncio
    async def test_parallel_search_returns_query_2_vanguard_dispute(self):
        service = ParallelSearchService(use_fallback=True)
        query = "Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute"
        snapshot = await service.search(
            query=query,
            use_id="use_v8_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
        )
        assert snapshot.stance == EvidenceStance.CONTRADICTORY
        assert "vanguard media" in snapshot.excerpt.lower()
        assert "assigned" in snapshot.excerpt.lower()

    @pytest.mark.asyncio
    async def test_parallel_search_simulated_failures_fail_closed(self):
        service = ParallelSearchService(use_fallback=True)

        # Timeout simulation
        snap_timeout = await service.search(
            query="test query",
            use_id="u1",
            stable_lineage_key="k1",
            simulate_failure="timeout",
        )
        assert snap_timeout.stance == EvidenceStance.INSUFFICIENT
        assert snap_timeout.http_status == 504
        assert snap_timeout.metadata.get("fail_closed") is True

        # 5xx simulation
        snap_5xx = await service.search(
            query="test query",
            use_id="u2",
            stable_lineage_key="k2",
            simulate_failure="5xx",
        )
        assert snap_5xx.stance == EvidenceStance.INSUFFICIENT
        assert snap_5xx.http_status == 500

        # Rate limit simulation
        snap_429 = await service.search(
            query="test query",
            use_id="u3",
            stable_lineage_key="k3",
            simulate_failure="rate_limit",
        )
        assert snap_429.stance == EvidenceStance.INSUFFICIENT
        assert snap_429.http_status == 429


# =====================================================================
# TASK 3 TESTS: END-TO-END WORKFLOW WIRING
# =====================================================================

class TestWorkflowWiring:
    """Tests end-to-end integration of RevalidationPlanner and EvidenceReconciler in LienmarkWorkflow."""

    @pytest.mark.asyncio
    async def test_workflow_wires_revalidation_planner_and_evidence_reconciler(self):
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection()

        # Step trace verification
        step_names = [t.step_name for t in result.execution_traces]
        assert "selective_revalidation_planning" in step_names
        assert "evidence_and_contract_reconciliation" in step_names

        # Revalidation plan verification
        assert result.revalidation_plan is not None
        assert len(result.revalidation_plan.planned_requests) == 2
        assert result.revalidation_plan.skipped_count == 10
        assert result.revalidation_plan.planned_count == 2

        # Verify only 2 searches were executed (preserving API budget)
        search_traces = [t for t in result.execution_traces if "parallel_targeted_search" in t.step_name]
        assert len(search_traces) == 2, f"Expected exactly 2 parallel search calls, got {len(search_traces)}"

        # Reconciliation results verification
        assert len(result.reconciliation_results) == 12

    @pytest.mark.asyncio
    async def test_workflow_with_active_perpetual_contract_shields_midnight_serenade(self):
        """Verifies that providing an active perpetual contract to the workflow shields Item 12,
        causing 11 claims to carry forward and only 1 to remain stale (Item 11 poster)."""
        music_key = "music_cue_midnight_serenade"
        perpetual_contract = ContractAgreement(
            agreement_id="agr_perpetual_jazz_1952",
            stable_lineage_key=music_key,
            licensor="Original Composer Syndicate",
            licensee="Production Co.",
            scope="Worldwide, all media in perpetuity",
            term="In Perpetuity",
            agreement_hash="hash_perpetual_12345",
            is_active=True,
        )

        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection(contracts=[perpetual_contract])

        # Under contract shield:
        # Midnight Serenade is carried forward by the contract!
        # Poster Noir Detective Magazine remains STALE (pending counsel re-attestation).
        assert result.carried_forward_count == 11, f"Expected 11 carried forward with contract shield, got {result.carried_forward_count}"
        assert result.reopened_count == 1, f"Expected 1 reopened claim (poster), got {result.reopened_count}"

        # Find the reconciliation result for Midnight Serenade
        music_recon = next(r for r in result.reconciliation_results if r.stable_lineage_key == music_key)
        assert music_recon.contract_shield_applied is True
        assert music_recon.decision_state == DecisionState.CARRIED_FORWARD
        assert music_recon.revalidation_action == "carry"
        assert music_recon.reason_code == "PRIVATE_CONTRACT_SHIELD_APPLIED"
