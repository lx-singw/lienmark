"""
tests/test_milestone_c_extended.py

Milestone C Acceptance Test Suite: Extended Investigation Hardening.
Covers evidence archiver content verification & SSRF protection, shared query limits
and cyclic lead prevention, circuit breaker 429 recovery & run-state separation,
bounded budget reservations, adversarial briefing, and fail-closed contract matching.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.planner import InvestigationPlanner
from backend.agents.research.planner_types import (
    CycleDetectedError, ExtractedLead, MaxQueryLimitReachedError,
)
from backend.domain.models import (
    ApprovalOrigin, AtomicRightsClaim, CensusDisposition, WorkflowReason,
)
from backend.orchestration.adk_pipeline import (
    CoordinatorAction, CoordinatorBudget, EvidenceDrivenCoordinator,
)
from backend.orchestration.budget_governor import ExecutionBudgetGovernor
from backend.orchestration.budget_types import BudgetExceededError
from backend.orchestration.circuit_breaker_governor import (
    CircuitOpenError, InvestigationCircuitBreaker, ProviderStatus,
)
from backend.orchestration.milestone_b_reservation import (
    MilestoneBBudgetManager, PaidActionType,
)
from backend.services.agreement_verifier import AgreementVerifier
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput, ProductionRequirements, SignatureParty,
    TermScope, TerritoryScope,
)
from backend.services.evidence_archiver import EvidenceArchiver, SnapshotStore
from backend.services.evidence_archiver_types import (
    CitationLivenessStatus, EvidenceSnapshot, SSRFSecurityError,
    compute_payload_digest,
)
from backend.services.parallel_types import ParallelSearchResult


@pytest.mark.asyncio
async def test_adversarial_disconfirming_evidence_in_briefing():
    """Adverse claimant discovered in ACT_05 is faithfully incorporated into briefing with CONTRADICTORY stance."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_cue_midnight", occurrence_id="occ_midnight",
        occurrence_lineage_id="music_cue_midnight_serenade",
        right_category="composition", rights_subject="Midnight Serenade Foreground Playback",
    )
    coord.register_claim(claim)
    r5 = await coord.execute_action(CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION, claim)
    assert r5["status"] == "SUCCESS"
    assert r5["tool_output"]["stance"].upper() == "CONTRADICTORY"
    assert "Vanguard Media Holdings" in r5["tool_output"]["excerpt"]

    r7 = await coord.execute_action(CoordinatorAction.ACT_07_PREPARE_REVIEW_BRIEF, claim)
    assert r7["status"] == "SUCCESS"
    briefing = r7["briefing"]
    assert briefing["parallel_evidence_stance"] == "CONTRADICTORY"
    assert "Vanguard Media Holdings" in briefing["counsel_summary"]
    assert "UNRESOLVED EXCEPTION" in briefing["suggested_counsel_action"]
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert claim.approval_origin == ApprovalOrigin.NONE
    assert coord.claim_states[claim.claim_id] == "ready_for_review"


def test_contract_matching_no_arbitrary_worldwide_defaults():
    """Contract missing territory/term does not fabricate worldwide/perpetual grants and triggers ACT_06."""
    verifier = AgreementVerifier()
    doc = AgreementDocumentInput(
        agreement_id="agr_limited_01", document_name="Limited License",
        licensor="Indie Publisher", licensee="Production Co", execution_date="2026-01-10",
        territories=[], media=["Theatrical"], term="", granted_rights=["Synchronization rights"],
        signatures=[SignatureParty(party_name="Indie Publisher", party_role="licensor", is_signed=True)],
        raw_text="Licensor grants theatrical rights in designated local markets only.",
    )
    res = verifier.verify_agreement(doc=doc, requirements=ProductionRequirements(required_territory="worldwide", requires_perpetual=True))
    assert res.grant_scope.is_worldwide is False and res.grant_scope.is_perpetual is False
    assert res.grant_scope.territory_scope != TerritoryScope.WORLDWIDE
    assert res.grant_scope.term_scope == TermScope.UNKNOWN and res.is_valid is False

    coord = EvidenceDrivenCoordinator(contracts=[], use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_missing_scope", occurrence_id="occ_ms", occurrence_lineage_id="prop_special_lamp",
        right_category="prop", rights_subject="Special Vintage Prop Lamp",
        intended_territory=["Worldwide"], intended_media=["theatrical", "svod"],
    )
    coord.register_claim(claim)
    coord.claim_contexts[claim.claim_id].update({
        "private_agreements_evaluated": True, "missing_crucial_scope": True,
        "scope_field_missing": "territory_and_term_scope",
    })
    decision = coord.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_06_REQUEST_INFORMATION
    assert decision.reason == WorkflowReason.WAITING_FOR_INFORMATION


@pytest.mark.asyncio
async def test_evidence_archiver_content_verification_and_ssrf(tmp_path):
    """Evidence archiver enforces content verification and SSRF defense on private/metadata IPs."""
    store = SnapshotStore(base_dir=str(tmp_path / "snaps"))
    archiver = EvidenceArchiver(store=store)

    # 1. SSRF Protection: Private IPs and cloud metadata are rejected with SSRFSecurityError
    ssrf_targets = [
        "http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:8080/admin",
        "http://localhost:5000/internal", "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for target in ssrf_targets:
        with pytest.raises(SSRFSecurityError):
            await archiver.archive_citation(url=target, snippet="Test Snippet")

    # 2. Content verification beyond URL liveness
    snippet = "Valid registered copyright entry for 1955 film print."
    full_body = f"Prefix text... {snippet} Suffix text..."
    locators = archiver.compute_locators(snippet, full_body)
    assert locators["type"] == "exact" and full_body[locators["char_start"]:locators["char_end"]] == snippet

    snap = await archiver.archive_citation(
        url="https://cocatalog.loc.gov/record/1955",
        snippet=snippet, fetched_content=full_body, excerpt_locators=locators,
    )
    assert snap.content_digest_sha256 == compute_payload_digest(snippet)
    assert snap.response_digest_sha256 == compute_payload_digest(full_body)

    # 3. Fails validation if both fetched_content and attributable provider are absent
    with pytest.raises(ValueError, match="Requires fetched_content or attributable provider"):
        EvidenceSnapshot(
            snapshot_id="snp_invalid", url="https://example.com", status=CitationLivenessStatus.LIVE,
            raw_snippet="snippet", fetched_content="", provider_extraction="", attributable_provider="",
            excerpt_locators={"type": "root"}, retrieval_time_utc="2026-09-08T00:00:00Z",
        )


def test_shared_limits_queries_cycle_prevention_and_deadline():
    """5-query shared budget across subgoals, cyclic lead cycle prevention, and 30s deadline."""
    planner = InvestigationPlanner()
    claim = ExtractedClaim(
        claim_id="clm_lim_01", category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 4", extracted_description="Test Track Theme",
    )
    dag = planner.create_initial_plan(claim)
    assert dag.max_queries == 5

    # 1. Cyclic lead cycle prevention: duplicate entity query raises CycleDetectedError
    root = dag.get_root_node()
    cyclic_lead = ExtractedLead(lead_id="ld_cyc", lead_type="publisher", entity_name="Test Track Theme", confidence=0.8)
    with pytest.raises(CycleDetectedError):
        planner.evaluate_hop_opportunity(dag, root, cyclic_lead)

    # 2. Shared 5-query budget limit across parent and child subgoals
    for i in range(1, 5):
        lead = ExtractedLead(lead_id=f"ld_{i}", lead_type="publisher", entity_name=f"Publisher {i}", confidence=0.8)
        planner.evaluate_hop_opportunity(dag, root, lead)
    assert len(dag.nodes) == 5

    overflow_lead = ExtractedLead(lead_id="ld_over", lead_type="label", entity_name="Label 99", confidence=0.8)
    with pytest.raises(MaxQueryLimitReachedError):
        planner.evaluate_hop_opportunity(dag, root, overflow_lead)

    # 3. 30s deadline partial return: should_terminate returns True on latency threshold
    dag.total_elapsed_seconds = 30.5
    assert planner.should_terminate(dag) is True
    results = ParallelSearchResult(findings=[], http_status=200)
    updated_dag = planner.advance_plan(dag, results)
    assert updated_dag.is_complete is True and updated_dag.total_elapsed_seconds >= dag.max_latency_seconds


def test_circuit_breaker_429_cooldown_half_open_and_run_states():
    """429 recovery, cooldown window, HALF_OPEN canary probe, and 3-way run state separation."""
    class Clock:
        def __init__(self, t: float = 1000.0): self.t = t
        def __call__(self) -> float: return self.t
        def advance(self, s: float): self.t += s

    clock = Clock()
    cb = InvestigationCircuitBreaker(provider_name="parallel_search", failure_threshold=1, recovery_timeout=30.0, clock=clock)

    # 1. 429 backoff sets cooldown window and transitions to RATE_LIMITED
    delay = cb.handle_429(retry_after_seconds=20.0)
    assert cb.status == ProviderStatus.RATE_LIMITED and cb.cooldown_until == 1020.0

    # 2. Cooldown active: check_breaker raises CircuitOpenError
    with pytest.raises(CircuitOpenError) as exc_info:
        cb.check_breaker()
    assert exc_info.value.retry_after == 20.0

    # 3. Cooldown elapsed: transitions to HALF_OPEN and permits single canary probe
    clock.advance(21.0)
    cb.check_breaker()
    assert cb.status == ProviderStatus.HALF_OPEN and cb.canary_in_flight is True
    with pytest.raises(CircuitOpenError):
        cb.check_breaker()

    cb.record_success()
    assert cb.status == ProviderStatus.HEALTHY and cb.consecutive_failures == 0

    # 4. Strict 3-way separation: WAITING_FOR_INFORMATION strictly forbidden for provider outages
    claim = AtomicRightsClaim(claim_id="c_outage", occurrence_id="occ_o", occurrence_lineage_id="lin_o", right_category="prop", rights_subject="Outage Asset")
    outage_info = cb.handle_provider_outage("ACT_02", preserved_evidence=["ev1"], claim=claim)
    assert outage_info["provider_status"] in (ProviderStatus.CIRCUIT_OPEN.value, ProviderStatus.OFFLINE.value)
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW and claim.workflow_reason == WorkflowReason.PROVIDER_OFFLINE


def test_bounded_budget_reservations_before_every_call():
    """Budget governor enforces bounded reservations prior to every external call."""
    # 1. CoordinatorBudget can_consume boundary check
    budget = CoordinatorBudget(max_calls=2, max_dollars=0.08)
    assert budget.can_consume(calls=1, dollars=0.04) is True
    budget.consume(calls=1, dollars=0.04)
    assert budget.can_consume(calls=1, dollars=0.04) is True
    budget.consume(calls=1, dollars=0.04)
    assert budget.can_consume(calls=1, dollars=0.04) is False and budget.is_exhausted is True

    coord = EvidenceDrivenCoordinator(budget=budget, use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_res_stop", occurrence_id="occ_res", occurrence_lineage_id="lin_res_stop",
        right_category="music", rights_subject="Budget Test Track",
    )
    decision = coord.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_08_STOP_UNRESOLVED
    assert decision.reason == WorkflowReason.WAITING_FOR_BUDGET

    # 2. MilestoneBBudgetManager reserve_for_action bounded reservation
    gov = ExecutionBudgetGovernor(default_max_run_spend_usd=0.05)
    mgr = MilestoneBBudgetManager(governor=gov)
    res1 = mgr.reserve_for_action(
        run_id="run_b_01", production_id="prod_01",
        action_type=PaidActionType.PAID_SEARCH, custom_cost_micros=20_000,
    )
    assert res1.status.value == "active" and res1.max_cost_micros == 20_000

    with pytest.raises(BudgetExceededError):
        mgr.reserve_for_action(
            run_id="run_b_01", production_id="prod_01",
            action_type=PaidActionType.PAID_SEARCH, custom_cost_micros=40_000,
        )
