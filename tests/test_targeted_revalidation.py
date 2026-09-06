"""
Sprint 2C Task 3 Verification Suite: Targeted Revalidation & Reconciliation Tests
Comprehensive automated tests for:
1. Revalidation Planner:
   - Exactly 2 requests generated for golden dataset (call_count == 2).
   - 10 unchanged claims generate 0 search requests (83.3% call reduction).
2. Evidence Stance Categorization:
   - Test all 4 stances: SUPPORTING, INFORMATIONAL, CONTRADICTORY, INSUFFICIENT.
3. Public Evidence vs Private Agreement Reconciliation:
   - When active ContractAgreement exists for a claim, public catalog dispute without revocation does not automatically void the license.
   - When no contract exists and public evidence is CONTRADICTORY, claim is strictly marked STALE / EXCEPTION.
4. Fail-Closed Network Resilience:
   - Simulated search timeout or HTTP 500 produces INSUFFICIENT stance and preserves STALE state; never defaults to approved.
5. Attribution & Citations:
   - Assert all evidence snapshots include attributable source URL, citation title, and SHA-256 payload hash.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import hashlib
import json
import re
import pytest

from backend.domain.models import (
    ContractAgreement,
    CounselDecision,
    CreativeDelta,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceReconciliationResult,
    EvidenceStance,
    PlannedRevalidationRequest,
    PublicEvidenceSnapshot,
    ReattestationRequest,
    RevalidationPlan,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.dependency_graph import ClearanceDependencyGraph
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.services.revalidation_planner import (
    RevalidationPlanner,
    ResearchPlanner,
    MinimalBudgetViolationError,
)
from backend.services.parallel_service import ParallelSearchService
from backend.orchestration.workflow import LienmarkWorkflow
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)


# =============================================================================
# 1. REVALIDATION PLANNER TESTS (83.3% CALL REDUCTION & 2 REQUESTS)
# =============================================================================

class TestRevalidationPlanner:
    """Tests selective planning and minimal API budget enforcement."""

    def test_golden_dataset_exact_two_requests_and_reduction_metric(self):
        """
        Acceptance Criterion 1:
        - Exactly 2 search requests generated for golden dataset (call_count == 2).
        - 10 unchanged claims generate 0 search requests (83.3% call reduction).
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        # Step 1: Invalidation evaluation produces 10 CARRIED_FORWARD and 2 STALE
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        assert len(validity_results) == 12

        # Step 2: Revalidation Planner generates targeted plan
        planner = RevalidationPlanner(enforce_golden_budget=True)
        plan = planner.plan_revalidation(
            validity_results=validity_results,
            target_uses=v8_uses,
            target_version_id="v8",
        )

        # Core Invariants
        assert isinstance(plan, RevalidationPlan)
        assert plan.total_claims_evaluated == 12
        assert plan.planned_count == 2
        assert plan.call_count == 2
        assert len(plan.planned_requests) == 2
        assert len(plan.revalidation_requests) == 2

        # Verify exactly 10 unchanged claims skipped (0 requests generated)
        assert plan.skipped_count == 10
        assert len(plan.skipped_lineage_keys) == 10
        assert len(plan.carried_forward_claims) == 10

        # Verify 83.3% call reduction: ((12 - 2) / 12) * 100 = 83.3%
        assert plan.call_reduction_percentage == 83.3

        # Verify planned keys are strictly Item 11 (poster) and Item 12 (music cue)
        planned_keys = {req.stable_lineage_key for req in plan.planned_requests}
        assert planned_keys == {"poster_noir_detective_magazine", "music_cue_midnight_serenade"}

        # Verify the 10 unchanged claims are correctly identified in skipped keys
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
        for k in unchanged_expected:
            assert k in plan.skipped_lineage_keys

    def test_unchanged_claims_generate_zero_search_requests(self):
        """
        Acceptance Criterion 1:
        10 unchanged claims generate 0 search requests (100% reduction for that subset).
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        carried_only = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        assert len(carried_only) == 10

        planner = RevalidationPlanner(enforce_golden_budget=False)
        plan = planner.plan_revalidation(
            validity_results=carried_only,
            target_uses=v8_uses,
        )

        assert plan.planned_count == 0
        assert plan.call_count == 0
        assert len(plan.planned_requests) == 0
        assert plan.skipped_count == 10
        assert len(plan.skipped_lineage_keys) == 10
        assert plan.call_reduction_percentage == 100.0

    @pytest.mark.asyncio
    async def test_revalidation_planner_execution_call_count_two(self):
        """
        Asserts that executing the plan through ParallelSearchService dispatches
        exclusively 2 requests, asserting call_count == 2.
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
        plan = planner.plan_revalidation(validity_results=validity_results, target_uses=v8_uses)

        parallel_service = ParallelSearchService()
        assert parallel_service.call_count == 0

        results = await planner.execute_plan(plan, parallel_service)

        # Call count strictly asserted == 2
        assert parallel_service.call_count == 2
        assert len(results) == 2
        assert "poster_noir_detective_magazine" in results
        assert "music_cue_midnight_serenade" in results
        assert results["poster_noir_detective_magazine"].stance == EvidenceStance.SUPPORTING
        assert results["music_cue_midnight_serenade"].stance == EvidenceStance.CONTRADICTORY

    def test_formulates_exact_targeted_queries(self):
        """Formulates targeted queries tailored for Parallel Search API."""
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
        assert query_map["poster_noir_detective_magazine"] == (
            "Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC"
        )
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
        plan = planner.plan_from_graph(graph=graph, target_uses=v8_uses)

        assert len(plan) == 2
        assert plan.planned_count == 2
        assert plan.skipped_count == 10
        assert plan.total_claims_evaluated == 12

    def test_budget_violation_raises_error(self):
        """Verifies that RevalidationPlanner raises MinimalBudgetViolationError on budget breach."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        # Tamper to 3 stale items
        tampered = [v.model_copy() for v in validity_results]
        tampered[0].state = DecisionState.STALE
        tampered[0].revalidation_action = "revalidate"
        tampered[0].reason_code = "CREATIVE_CONTEXT_ALTERED"

        planner = RevalidationPlanner(enforce_golden_budget=True)
        with pytest.raises(MinimalBudgetViolationError):
            planner.plan_revalidation(validity_results=tampered, target_uses=v8_uses)


# =============================================================================
# 2. EVIDENCE STANCE CATEGORIZATION TESTS (ALL 4 STANCES)
# =============================================================================

class TestEvidenceStanceCategorization:
    """Tests all 4 stances: SUPPORTING, INFORMATIONAL, CONTRADICTORY, INSUFFICIENT."""

    def test_stance_supporting(self):
        """Acceptance Criterion 2: Test EvidenceStance.SUPPORTING."""
        reconciler = EvidenceReconciler()

        evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_test_supporting",
            use_id="use_poster_01",
            stable_lineage_key="poster_noir_detective_magazine",
            query="Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC",
            source_url="https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1944-shadows-manhattan",
            source_title="US Copyright Office Historical Catalog - Renewal Records (LOC)",
            excerpt="Registration #B-1944-7712 expired 1972 without timely renewal. Work is in the public domain.",
            stance=EvidenceStance.SUPPORTING,
        )

        classified = reconciler.classify_stance(evidence)
        assert classified == EvidenceStance.SUPPORTING

        res = reconciler.reconcile_claim(
            stable_lineage_key="poster_noir_detective_magazine",
            decision_id="dec_poster_01",
            evidence=evidence,
            contract=None,
        )
        assert res.reconciled_stance == EvidenceStance.SUPPORTING
        assert res.reason_code == "EVIDENCE_CONFIRMED_PUBLIC_DOMAIN"
        assert res.is_license_voided is False
        assert "public domain" in res.explanation.lower()

    def test_stance_informational(self):
        """Acceptance Criterion 2: Test EvidenceStance.INFORMATIONAL."""
        reconciler = EvidenceReconciler()

        evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_test_info",
            use_id="use_jazz_01",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade Savoy Ballroom discography 1946",
            source_url="https://jazzdiscography.org/records/midnight-serenade",
            source_title="Historical Jazz Discography & Sessionography",
            excerpt="Recorded June 14, 1946 at Savoy Ballroom, New York. Personnel: Tenor Sax, Upright Bass, Drums.",
            stance=EvidenceStance.INFORMATIONAL,
        )

        classified = reconciler.classify_stance(evidence)
        assert classified == EvidenceStance.INFORMATIONAL

        res = reconciler.reconcile_claim(
            stable_lineage_key="music_cue_midnight_serenade",
            decision_id="dec_music_01",
            evidence=evidence,
            contract=None,
        )
        assert res.reconciled_stance == EvidenceStance.INFORMATIONAL
        assert res.decision_state == DecisionState.STALE
        assert res.revalidation_action == "manual"
        assert res.reason_code == "INFORMATIONAL_EVIDENCE_UNRESOLVED"
        assert res.requires_counsel_rider is True

    def test_stance_contradictory(self):
        """Acceptance Criterion 2: Test EvidenceStance.CONTRADICTORY."""
        reconciler = EvidenceReconciler()

        evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_test_contradictory",
            use_id="use_jazz_01",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade jazz sync rights copyright owner 2026",
            source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
            source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC (Kobalt Music admin).",
            stance=EvidenceStance.CONTRADICTORY,
        )

        classified = reconciler.classify_stance(evidence)
        assert classified == EvidenceStance.CONTRADICTORY

        res = reconciler.reconcile_claim(
            stable_lineage_key="music_cue_midnight_serenade",
            decision_id="dec_music_01",
            evidence=evidence,
            contract=None,
        )
        assert res.reconciled_stance == EvidenceStance.CONTRADICTORY
        assert res.decision_state == DecisionState.STALE
        assert res.is_license_voided is True
        assert res.requires_counsel_rider is True
        assert res.reason_code == "UNRESOLVED_RIGHTS_DISPUTE"

    def test_stance_insufficient(self):
        """Acceptance Criterion 2: Test EvidenceStance.INSUFFICIENT."""
        reconciler = EvidenceReconciler()

        # Case A: HTTP 500
        ev_500 = PublicEvidenceSnapshot(
            snapshot_id="ev_test_500",
            use_id="use_fail_01",
            stable_lineage_key="prop_vintage_telephone",
            query="clearance query",
            source_url="https://search.parallel.ai/errors",
            source_title="Parallel Search Internal Error",
            excerpt="Search failed with upstream HTTP 500 Internal Server Error",
            http_status=500,
            stance=EvidenceStance.INSUFFICIENT,
        )
        assert reconciler.classify_stance(ev_500) == EvidenceStance.INSUFFICIENT

        # Case B: HTTP 504 Timeout
        ev_timeout = PublicEvidenceSnapshot(
            snapshot_id="ev_test_timeout",
            use_id="use_fail_02",
            stable_lineage_key="prop_vintage_telephone",
            query="clearance query timeout",
            source_url="https://search.parallel.ai/timeout",
            source_title="Parallel Search Timeout",
            excerpt="Search request timed out after 10000ms",
            http_status=504,
            stance=EvidenceStance.INSUFFICIENT,
        )
        assert reconciler.classify_stance(ev_timeout) == EvidenceStance.INSUFFICIENT

        # Case C: None / Empty
        assert reconciler.classify_stance(None) == EvidenceStance.INSUFFICIENT

    def test_competing_evidence_resolves_contradictory_defensively(self):
        """When evidence contains both public domain claim and adverse dispute, resolves to CONTRADICTORY."""
        reconciler = EvidenceReconciler()

        evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_competing",
            use_id="use_competing",
            stable_lineage_key="artwork_disputed_lithograph",
            query="1932 lithograph copyright dispute",
            source_url="https://courtlistener.com/docket/lithograph-appeal",
            source_title="Federal Court Docket: Lithograph Rights Appeal",
            excerpt="Work was formerly asserted in the public domain, but exclusive copyright ownership was assigned to Estate Trustees; prior public domain status disputed.",
            stance=EvidenceStance.CONTRADICTORY,
        )

        classified = reconciler.classify_stance(evidence)
        assert classified == EvidenceStance.CONTRADICTORY


# =============================================================================
# 3. PUBLIC EVIDENCE VS PRIVATE AGREEMENT RECONCILIATION
# =============================================================================

class TestPublicEvidenceVsPrivateAgreementReconciliation:
    """Tests reconciliation of public catalog changes against private contracts."""

    def test_active_contract_shields_against_public_catalog_dispute(self):
        """
        Acceptance Criterion 3:
        When an active ContractAgreement exists for a claim, a public catalog dispute
        without revocation does not automatically void the license.
        Statutory Basis: 17 U.S.C. § 205(e), California contract law.
        """
        reconciler = EvidenceReconciler()

        contract = ContractAgreement(
            agreement_id="agr_sync_midnight_2026",
            stable_lineage_key="music_cue_midnight_serenade",
            licensor="Savoy Music / Original Composer Estate",
            licensee="Production Co.",
            scope="Worldwide theatrical, streaming, broadcast in perpetuity",
            term="Perpetuity",
            agreement_hash="c3a4b5d6e7f8091a2b3c4d5e6f708192a3b4c5d6",
            is_active=True,
        )

        public_evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_vanguard_catalog_shift",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade jazz sync rights copyright owner 2026",
            source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
            source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
            stance=EvidenceStance.CONTRADICTORY,
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key="music_cue_midnight_serenade",
            decision_id="dec_v7_music_midnight",
            evidence=public_evidence,
            contract=contract,
        )

        # Invariants:
        assert result.has_contract is True
        assert result.contract_shield_applied is True
        assert result.contract_id == "agr_sync_midnight_2026"
        assert result.is_license_voided is False
        assert result.decision_state == DecisionState.CARRIED_FORWARD
        assert result.revalidation_action == "carry"
        assert result.reason_code == "PRIVATE_CONTRACT_SHIELD_APPLIED"
        assert result.raw_stance == EvidenceStance.CONTRADICTORY
        assert result.reconciled_stance == EvidenceStance.SUPPORTING
        assert "does not void" in result.explanation.lower() or "binding" in result.explanation.lower()

    def test_unshielded_contradictory_evidence_strictly_stale_exception(self):
        """
        Acceptance Criterion 3:
        When NO contract exists and public evidence is CONTRADICTORY,
        claim is strictly marked STALE / EXCEPTION.
        """
        reconciler = EvidenceReconciler()

        public_evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_vanguard_catalog_shift",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade jazz sync rights copyright owner 2026",
            source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
            source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
            stance=EvidenceStance.CONTRADICTORY,
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key="music_cue_midnight_serenade",
            decision_id="dec_v7_music_midnight",
            evidence=public_evidence,
            contract=None,
        )

        assert result.has_contract is False
        assert result.contract_shield_applied is False
        assert result.is_license_voided is True
        assert result.decision_state == DecisionState.STALE
        assert result.revalidation_action == "manual"
        assert result.reason_code == "UNRESOLVED_RIGHTS_DISPUTE"
        assert result.requires_counsel_rider is True

    def test_contract_revocation_or_injunction_defeats_contract_shield(self):
        """Judicial injunction or formal license revocation defeats the contract shield."""
        reconciler = EvidenceReconciler()

        contract = ContractAgreement(
            agreement_id="agr_revoked_01",
            stable_lineage_key="music_cue_midnight_serenade",
            licensor="Original Publisher",
            scope="Theatrical",
            term="Perpetuity",
            agreement_hash="hash_revoked_01",
            is_active=True,
        )

        injunction_evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_injunction",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade litigation injunction",
            source_url="https://dockets.justia.com/docket/circuit-injunction",
            source_title="Federal District Court Injunction Order",
            excerpt="Permanent judicial injunction entered enjoining distribution; prior license revoked and terminated due to fraudulent transfer.",
            stance=EvidenceStance.CONTRADICTORY,
        )

        result = reconciler.reconcile_claim(
            stable_lineage_key="music_cue_midnight_serenade",
            decision_id="dec_v7_music_midnight",
            evidence=injunction_evidence,
            contract=contract,
        )

        assert result.contract_shield_applied is False
        assert result.decision_state == DecisionState.STALE
        assert result.is_license_voided is True
        assert result.reason_code == "CONTRACT_REVOCATION_OR_INJUNCTION_PROVEN"
        assert result.revalidation_action == "manual"


# =============================================================================
# 4. FAIL-CLOSED NETWORK RESILIENCE TESTS
# =============================================================================

class TestFailClosedNetworkResilience:
    """Tests simulated search timeout or HTTP 500 error produces INSUFFICIENT and preserves STALE."""

    @pytest.mark.asyncio
    async def test_simulated_search_timeout_produces_insufficient_and_preserves_stale(self):
        """
        Acceptance Criterion 4:
        Simulated search timeout produces INSUFFICIENT stance and preserves STALE state;
        never defaults to approved.
        """
        parallel_service = ParallelSearchService()

        snapshot = await parallel_service.search(
            query="Midnight Serenade copyright query",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            simulate_failure="timeout",
        )

        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.http_status == 504
        assert snapshot.raw_payload_hash is not None and len(snapshot.raw_payload_hash) == 64

        reconciler = EvidenceReconciler()
        result = reconciler.reconcile_claim(
            stable_lineage_key="music_cue_midnight_serenade",
            decision_id="dec_v7_music_midnight",
            evidence=snapshot,
            contract=None,
        )

        # Strictly preserved STALE state; NEVER approved
        assert result.decision_state == DecisionState.STALE
        assert result.revalidation_action == "manual"
        assert result.raw_stance == EvidenceStance.INSUFFICIENT
        assert result.reconciled_stance == EvidenceStance.INSUFFICIENT
        assert result.reason_code == "SEARCH_EVIDENCE_INSUFFICIENT"
        assert result.decision_state != DecisionState.CARRIED_FORWARD

    @pytest.mark.asyncio
    async def test_simulated_http_500_server_error_produces_insufficient_and_preserves_stale(self):
        """
        Acceptance Criterion 4:
        Simulated HTTP 500 server error produces INSUFFICIENT stance and preserves STALE state;
        never defaults to approved.
        """
        parallel_service = ParallelSearchService()

        snapshot = await parallel_service.search(
            query="1944 detective magazine renewal search",
            use_id="dec_v7_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            simulate_failure="5xx",
        )

        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.http_status == 500
        assert snapshot.raw_payload_hash is not None and len(snapshot.raw_payload_hash) == 64

        reconciler = EvidenceReconciler()
        result = reconciler.reconcile_claim(
            stable_lineage_key="poster_noir_detective_magazine",
            decision_id="dec_v7_poster_noir",
            evidence=snapshot,
            contract=None,
        )

        assert result.decision_state == DecisionState.STALE
        assert result.revalidation_action == "manual"
        assert result.raw_stance == EvidenceStance.INSUFFICIENT
        assert result.reconciled_stance == EvidenceStance.INSUFFICIENT
        assert result.reason_code == "SEARCH_EVIDENCE_INSUFFICIENT"
        assert result.decision_state != DecisionState.CARRIED_FORWARD

    def test_batch_reconciliation_fail_closed_prevents_unauthorized_approval(self):
        """Batch reconciliation guarantees unverified network errors stay STALE."""
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        corrupt_evidence = dict(v8_evidence)
        corrupt_evidence["music_cue_midnight_serenade"] = PublicEvidenceSnapshot(
            snapshot_id="ev_corrupt_timeout",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade query",
            source_url="https://search.parallel.ai/timeout",
            source_title="Parallel Search Gateway Failure",
            excerpt="HTTP 504 Gateway Timeout during search retrieval.",
            http_status=504,
            stance=EvidenceStance.INSUFFICIENT,
        )

        reconciler = EvidenceReconciler()
        reconciled_results = reconciler.reconcile_all(
            validity_results=validity_results,
            evidence_snapshots=corrupt_evidence,
            contracts=None,
            update_validity_in_place=True,
        )

        music_val = next(v for v in validity_results if v.stable_lineage_key == "music_cue_midnight_serenade")
        assert music_val.state == DecisionState.STALE
        assert music_val.revalidation_action == "manual"
        assert music_val.reason_code == "SEARCH_EVIDENCE_INSUFFICIENT"


# =============================================================================
# 5. ATTRIBUTION & CITATIONS TESTS
# =============================================================================

class TestAttributionAndCitations:
    """Tests attributable source URL, citation title, and SHA-256 payload hash."""

    def test_evidence_snapshots_attribution_and_payload_hash_format(self):
        """
        Acceptance Criterion 5:
        Assert all evidence snapshots include:
        - Attributable source URL (valid http/https URL)
        - Citation title (non-empty)
        - SHA-256 payload hash (strictly 64 lowercase hex characters)
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        sha256_regex = re.compile(r"^[0-9a-f]{64}$")

        for key, snapshot in v8_evidence.items():
            # 1. Attributable source URL
            assert snapshot.source_url.startswith("http://") or snapshot.source_url.startswith("https://"), (
                f"Snapshot '{snapshot.snapshot_id}' has invalid source_url: '{snapshot.source_url}'"
            )

            # 2. Citation title
            assert snapshot.source_title and len(snapshot.source_title.strip()) > 0, (
                f"Snapshot '{snapshot.snapshot_id}' missing source_title"
            )

            # 3. Attributable excerpt / snippet
            assert snapshot.excerpt and len(snapshot.excerpt.strip()) > 0, (
                f"Snapshot '{snapshot.snapshot_id}' missing excerpt"
            )

            # 4. SHA-256 payload hash
            hash_val = snapshot.payload_hash or snapshot.raw_payload_hash
            assert hash_val is not None, f"Snapshot '{snapshot.snapshot_id}' missing payload_hash"
            assert len(hash_val) == 64, f"Payload hash '{hash_val}' must be exactly 64 characters"
            assert sha256_regex.match(hash_val) is not None, f"Payload hash '{hash_val}' must be lowercase hexadecimal"

    @pytest.mark.asyncio
    async def test_runtime_parallel_search_attribution_and_sha256_hashing(self):
        """Asserts runtime searches produce verifiable citations, URLs, and SHA-256 hashes."""
        service = ParallelSearchService()

        queries = [
            ("poster_noir_detective_magazine", "Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC"),
            ("music_cue_midnight_serenade", "Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute"),
        ]

        sha256_regex = re.compile(r"^[0-9a-f]{64}$")

        for key, q in queries:
            snapshot = await service.search(
                query=q,
                use_id=f"use_{key}",
                stable_lineage_key=key,
            )

            assert snapshot.source_url.startswith("https://")
            assert len(snapshot.source_title) > 5

            assert snapshot.raw_payload_hash is not None
            assert len(snapshot.raw_payload_hash) == 64
            assert sha256_regex.match(snapshot.raw_payload_hash) is not None

            # Verify cryptographic hash of payload conforming to Parallel API v1 V1SearchRequest
            expected_payload = {
                "objective": f"Clearance and intellectual property evidence verification for production asset '{key}': {q}",
                "search_queries": [q],
                "mode": "fast",
                "max_chars_total": 4000,
            }
            expected_serialized = json.dumps(expected_payload, sort_keys=True, separators=(",", ":"))
            expected_hash = hashlib.sha256(expected_serialized.encode("utf-8")).hexdigest()
            assert snapshot.raw_payload_hash == expected_hash

    def test_reconciled_citations_structure(self):
        """Verifies EvidenceReconciler builds structured citation blocks."""
        reconciler = EvidenceReconciler()

        evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_cite_test",
            use_id="use_cite_01",
            stable_lineage_key="poster_noir_detective_magazine",
            query="1944 detective magazine renewal search",
            source_url="https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1944-shadows-manhattan",
            source_title="US Copyright Office Renewal Records (LOC)",
            excerpt="Copyright expired without renewal. Work in public domain.",
            stance=EvidenceStance.SUPPORTING,
        )

        res = reconciler.reconcile_claim(
            stable_lineage_key="poster_noir_detective_magazine",
            decision_id="dec_cite_01",
            evidence=evidence,
        )

        assert len(res.citations) == 1
        citation = res.citations[0]
        assert citation["source_title"] == "US Copyright Office Renewal Records (LOC)"
        assert citation["source_url"] == "https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1944-shadows-manhattan"
        assert citation["domain"] == "cocatalog.loc.gov"
        assert "public domain" in citation["excerpt"].lower()
        assert citation["stance"] == "supporting"


# =============================================================================
# 6. END-TO-END REVALIDATION LIFECYCLE INTEGRATION TEST
# =============================================================================

class TestEndToEndRevalidationLifecycle:
    """Full end-to-end integration test verifying the complete Sprint 2C cycle."""

    @pytest.mark.asyncio
    async def test_complete_revalidation_and_reconciliation_lifecycle(self):
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        # Step 1 & 2: Invalidation Engine
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        assert len(validity_results) == 12
        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]
        assert len(carried) == 10
        assert len(stale) == 2

        # Step 3: Revalidation Planner
        planner = RevalidationPlanner(enforce_golden_budget=True)
        plan = planner.plan_revalidation(validity_results, v8_uses)
        assert plan.call_count == 2
        assert plan.call_reduction_percentage == 83.3

        # Step 4: Parallel Search Execution
        parallel_service = ParallelSearchService()
        refreshed_evidence = await planner.execute_plan(plan, parallel_service)
        assert parallel_service.call_count == 2

        # Step 5: Evidence & Contract Reconciliation
        reconciler = EvidenceReconciler()
        reconciliation_results = reconciler.reconcile_all(
            validity_results=validity_results,
            evidence_snapshots=refreshed_evidence,
            contracts=None,
            update_validity_in_place=True,
        )
        assert len(reconciliation_results) == 12

        # Step 6: Form E&O Exceptions Schedule
        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            reattestations={
                "poster_noir_detective_magazine": ReattestationRequest(
                    decision_id="dec_v7_poster_noir",
                    stable_lineage_key="poster_noir_detective_magazine",
                    version_id="v8",
                    new_status=DecisionStatus.APPROVED,
                    counsel_rationale="LOC copyright registration expired without renewal; verified in public domain via Parallel Search.",
                ),
                "music_cue_midnight_serenade": ReattestationRequest(
                    decision_id="dec_v7_music_midnight",
                    stable_lineage_key="music_cue_midnight_serenade",
                    version_id="v8",
                    new_status=DecisionStatus.REJECTED,
                    counsel_rationale="Unshielded Vanguard Media copyright conflict identified; replace track.",
                ),
            },
        )

        assert schedule.total_claims == 12
        assert schedule.carried_forward_count == 10
        assert schedule.reopened_count == 2
        assert schedule.re_attested_count == 1
        assert schedule.unresolved_exception_count == 1
        assert len(schedule.items) == 12


# =============================================================================
# 7. CLUSTER 3 REMEDIATION: FINDINGS 4, 5, 6 VERIFICATION
# =============================================================================

class TestCluster3RemediationFindings:
    """
    Direct verification for Cluster 3 of the approved remediation plan:
    - Finding 4: Cross-Version Approval Bleed
    - Finding 5: Empty Search Marked as Supporting Evidence
    - Finding 6: Stored XSS in HTML Reports & URL Scheme Sanitization
    """

    def test_finding_4_cross_version_approval_bleed_prevention(self):
        """
        Finding 4: When a reattestation was recorded for v7 or another version,
        it must NEVER bleed into target_version_id (e.g. v8). It must remain STALE/EXCEPTION.
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        # Poster was STALE. Provide a reattestation explicitly bound to "v7"
        v7_bleed_reattestations = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_v7_poster_noir",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v7",  # WRONG VERSION: must not bleed into v8
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Attempted cross-version approval bleed from v7",
            )
        }

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_bleed_test",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            reattestations=v7_bleed_reattestations,
            base_uses=v7_uses,
        )

        poster_item = next(i for i in schedule.items if i.stable_lineage_key == "poster_noir_detective_magazine")
        # Must strictly remain EXCEPTION, NOT re_attested!
        assert poster_item.v8_evaluation_state == "exception", (
            f"Expected 'exception' due to version mismatch ('v7' vs 'v8'), got {poster_item.v8_evaluation_state}"
        )
        assert schedule.re_attested_count == 0
        assert schedule.unresolved_exception_count == 2  # poster and music cue both exceptions

    def test_finding_4_version_matching_and_legacy_calls(self):
        """
        Finding 4: Reattestation matches when version_id == target_version_id,
        or when version_id is None in legacy calls targeting v8.
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        # 1. Matching target_version_id "v8"
        matching_reattestations = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_v8_poster_noir",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Valid v8 approval",
            )
        }

        sched_v8 = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_matching_test",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=validity_results,
            reattestations=matching_reattestations,
            base_uses=v7_uses,
        )
        poster_v8 = next(i for i in sched_v8.items if i.stable_lineage_key == "poster_noir_detective_magazine")
        assert poster_v8.v8_evaluation_state == "re_attested"

    def test_finding_5_empty_search_marked_insufficient(self):
        """
        Finding 5: In _parse_v1_search_response, when results is empty:
        - stance = EvidenceStance.INSUFFICIENT
        - source_title = "No Attributable Evidence Found"
        - source_url = ""
        - excerpt = "Query returned zero matching catalog records."
        - publisher = "Parallel Search Index"
        - citation = "No matching records"
        - expected_stance must NEVER override missing evidence!
        """
        service = ParallelSearchService(api_key="mock_key")

        empty_data = {
            "results": [],
            "search_id": "search_empty_test_001",
        }

        # Test with expected_stance=SUPPORTING to verify it does NOT override
        snapshot = service._parse_v1_search_response(
            data=empty_data,
            query="Empty query test",
            use_id="use_empty_01",
            stable_lineage_key="claim_empty_test",
            raw_payload_hash="hash123",
            elapsed_ms=45.0,
            http_status=200,
            expected_stance=EvidenceStance.SUPPORTING,
        )

        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.source_title == "No Attributable Evidence Found"
        assert snapshot.source_url == ""
        assert snapshot.excerpt == "Query returned zero matching catalog records."
        assert snapshot.publisher == "Parallel Search Index"
        assert snapshot.citation == "No matching records"

    def test_finding_6_stored_xss_prevention_in_html_reports(self):
        """
        Finding 6: In render_html_schedule:
        - Apply html.escape() to dynamic strings in the template.
        - Validate citation URLs: only allow http/https, sanitize javascript:/data:/invalid to about:blank or #.
        """
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

        xss_payload = "<script>alert('XSS-INJECTION')</script>"
        xss_img = '<img src=x onerror="alert(\'img-xss\')">'

        schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_xss_test",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=InvalidationEngine.evaluate_invalidation(
                base_uses=v7_uses,
                target_uses=v8_uses,
                prior_decisions=v7_decisions,
                evidence_snapshots=v8_evidence,
                target_version_id="v8",
            ),
        )

        # Inject XSS vectors into metadata
        schedule.production_metadata["production_title"] = f"Production {xss_payload}"
        schedule.production_metadata["project_id"] = f"proj_{xss_img}"
        schedule.production_metadata["producer_company"] = f"Producer & Co {xss_payload}"

        # Inject XSS vectors into an exception item (rendered in Section I with citations)
        item = next(i for i in schedule.items if i.v8_evaluation_state == "exception")
        item.description = f"Scene prop {xss_payload}"
        item.scene_or_timecode = f"Scene 1 {xss_img}"
        item.stable_lineage_key = f"key_{xss_payload}"
        item.asset_type = f"asset_{xss_payload}"
        item.invalidation_reason = f"reason_{xss_payload}"
        item.counsel_action = f"action_{xss_payload}"

        # Inject XSS and malicious URLs into citation
        item.evidence_citations = [
            {
                "source_title": f"Title {xss_payload}",
                "source_url": "javascript:alert(document.cookie)",
                "excerpt": f"Quote {xss_img}",
                "provider": f"Provider {xss_payload}",
            },
            {
                "source_title": "Data URI Test",
                "source_url": "data:text/html,<script>alert('pwn')</script>",
                "excerpt": "Data excerpt",
                "provider": "Test Provider",
            },
            {
                "source_title": "Valid HTTPS Test",
                "source_url": "https://example.com/valid?ref=1",
                "excerpt": "Valid excerpt",
                "provider": "Valid Provider",
            }
        ]

        rendered_html = InvalidationEngine.render_html_schedule(schedule)

        # 1. Assert raw unescaped script and img onerror tags are strictly absent
        assert "<script>alert('XSS-INJECTION')</script>" not in rendered_html
        assert '<img src=x onerror="alert(\'img-xss\')">' not in rendered_html
        assert "javascript:alert" not in rendered_html
        assert "data:text/html" not in rendered_html

        # 2. Assert properly escaped entities are present
        assert "&lt;script&gt;alert(&#x27;XSS-INJECTION&#x27;)&lt;/script&gt;" in rendered_html or "&lt;script&gt;alert('XSS-INJECTION')&lt;/script&gt;" in rendered_html
        assert "about:blank" in rendered_html
        assert 'href="https://example.com/valid?ref=1"' in rendered_html

