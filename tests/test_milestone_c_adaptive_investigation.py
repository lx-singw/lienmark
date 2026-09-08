"""
tests/test_milestone_c_adaptive_investigation.py

Milestone C Acceptance Test Suite: Adaptive Investigation.
Covers 1930 vs 1931 public domain boundary (17 U.S.C. §§ 304, 305), separate-rights vs
genuine-conflict arbitration, de minimis triage without auto-clearance, ACT_03 failed
extraction handling without premature completion, and bounded query reformulation.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.agents.research.query_builder import InverseDomainSteeringEngine
from backend.agents.research.query_types import (
    AssetClass,
    EvidenceEvaluation,
    SearchQueryRequest,
    SteeringState,
)
from backend.core.conflict_arbiter import (
    CorroborationEngine,
    arbitrate_claim_conflicts,
)
from backend.core.conflict_types import (
    ClaimStatusAssertion,
    ConflictStance,
    EvidenceFinding,
    RightsLayer,
    SourceAuthorityTier,
)
from backend.core.statutory_public_domain import eval_public_domain
from backend.core.statutory_rules import eval_de_minimis
from backend.core.statutory_types import StatutoryEra
from backend.domain.models import (
    ApprovalOrigin,
    AtomicRightsClaim,
    CensusDisposition,
    ContractAgreement,
    WorkflowReason,
)
from backend.orchestration.adk_pipeline import (
    CoordinatorAction,
    CoordinatorBudget,
    EvidenceDrivenCoordinator,
)
from backend.services.parallel_extract import ParallelExtractService


@pytest.mark.asyncio
async def test_adaptive_action_selection_unfamiliar_asset():
    """Unfamiliar asset adapts query/tool path via model-directed action selection."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    unfamiliar = AtomicRightsClaim(
        claim_id="clm_astral_01", occurrence_id="occ_astral",
        occurrence_lineage_id="sculpture_kinetic_astral_1973",
        right_category="artwork", rights_subject="Kinetic Astral Sculpture 1973",
    )
    d1 = coord.decide_next_action(unfamiliar)
    assert d1.action == CoordinatorAction.ACT_02_SEARCH_PUBLIC_SOURCES
    r1 = await coord.execute_action(CoordinatorAction.ACT_02_SEARCH_PUBLIC_SOURCES, unfamiliar)
    assert r1["status"] == "SUCCESS"
    assert coord.claim_contexts[unfamiliar.claim_id]["public_search_performed"] is True

    d2 = coord.decide_next_action(unfamiliar)
    assert d2.action == CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION

    contract = ContractAgreement(
        agreement_id="agr_mural_99", stable_lineage_key="fresco_mosaic_1982",
        licensor="Art Trust", licensee="Studio", scope="worldwide", term="perpetual",
        agreement_hash="hash_mural_99", is_active=True,
    )
    coord_contract = EvidenceDrivenCoordinator(contracts=[contract], use_fallback=True)
    claim_contract = AtomicRightsClaim(
        claim_id="clm_mural_02", occurrence_id="occ_mural",
        occurrence_lineage_id="fresco_mosaic_1982", right_category="artwork",
        rights_subject="Fresco Mosaic 1982",
    )
    d_contract = coord_contract.decide_next_action(claim_contract)
    assert d_contract.action == CoordinatorAction.ACT_01_RETRIEVE_PRIVATE_AGREEMENTS
    assert "ACT_02" in [h["code"] for h in coord.action_history[unfamiliar.claim_id]]


def test_bounded_query_reformulation():
    """Irrelevant/empty search results trigger bounded reformulation within budget."""
    engine, budget = InverseDomainSteeringEngine(), CoordinatorBudget(max_calls=3)
    req = SearchQueryRequest(
        asset_id="clm_indie_01", asset_class=AssetClass.MUSIC,
        title="Neon Echoes at Twilight", creator_or_owner="The Twilight Ensemble",
        current_state=SteeringState.STRICT_REGISTRY,
    )
    zero_hits = EvidenceEvaluation(result_count=0, confidence_score=0.0)
    assert engine.should_trigger_inverse_steering(zero_hits) is True
    req, q2 = engine.next_query(req, zero_hits)
    budget.consume(calls=1)
    assert req.current_state == SteeringState.INVERSE_STEERING
    assert "site:" not in q2.query_string and "-lyrics" in q2.query_string

    weak_hits = EvidenceEvaluation(result_count=1, confidence_score=0.35)
    req, q3 = engine.next_query(req, weak_hits)
    budget.consume(calls=1)
    assert req.current_state == SteeringState.ADVERSARIAL_PROBE
    assert "dispute OR infringement OR lawsuit" in q3.query_string

    budget.consume(calls=1)
    assert budget.is_exhausted is True
    coord = EvidenceDrivenCoordinator(budget=budget, use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_ex_01", occurrence_id="occ_ex",
        occurrence_lineage_id="lin_ex", right_category="music", rights_subject="Track",
    )
    decision = coord.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_08_STOP_UNRESOLVED
    assert decision.reason == WorkflowReason.WAITING_FOR_BUDGET


def test_1930_vs_1931_public_domain_boundary():
    """1930 is public domain in 2026; 1931 is protected through Dec 31, 2026 under §§ 304, 305."""
    # 1. 1930 work: 95-year term expired Dec 31, 2025; public domain Jan 1, 2026
    res_1930 = eval_public_domain(1930, reference_year=2026)
    assert res_1930.is_public_domain is True
    assert res_1930.statutory_era == StatutoryEra.YEARS_1923_TO_1977
    assert res_1930.threshold_year == 1930
    assert "Dec 31, 2025" in res_1930.rationale
    assert "17 U.S.C." in res_1930.statutory_citation

    # 2. 1931 work: Protected through Dec 31, 2026; enters public domain Jan 1, 2027
    res_1931 = eval_public_domain(1931, reference_year=2026)
    assert res_1931.is_public_domain is False
    assert res_1931.threshold_year == 1930
    assert "Protected through Dec 31, 2026" in res_1931.rationale
    assert "entering PD Jan 1, 2027" in res_1931.rationale
    assert "17 U.S.C." in res_1931.statutory_citation

    # 3. 1930 vs 1931 claim differentiation in statutory clearance evaluation
    claim_1930 = AtomicRightsClaim(
        claim_id="clm_pd_1930", occurrence_id="occ_1930",
        occurrence_lineage_id="jazz_standard_1930", right_category="composition",
        rights_subject="1930 Jazz Standard",
    )
    claim_1931 = AtomicRightsClaim(
        claim_id="clm_prot_1931", occurrence_id="occ_1931",
        occurrence_lineage_id="jazz_standard_1931", right_category="composition",
        rights_subject="1931 Jazz Standard",
    )
    assert eval_public_domain(1930, reference_year=2026).is_public_domain is True
    assert eval_public_domain(1931, reference_year=2026).is_public_domain is False


def test_separate_rights_vs_genuine_conflict():
    """Dual subgoals (PD composition + protected recording) are NOT contradictory; same-layer conflict is."""
    # 1. Separate rights on distinct layers -> NEUTRAL stance, no contradictory conflict
    comp_pd = EvidenceFinding(
        finding_id="f_comp_pd", source_title="LOC Registry",
        excerpt="1920 musical composition in U.S. public domain.",
        asserted_status=ClaimStatusAssertion.PUBLIC_DOMAIN,
        rights_layer=RightsLayer.UNDERLYING_WORK,
        authority_tier=SourceAuthorityTier.TIER_1_GOVERNMENT_REGISTRY,
    )
    rec_prot = EvidenceFinding(
        finding_id="f_rec_prot", source_title="Master Label Rights",
        excerpt="Sound recording master 2020 all rights reserved.",
        asserted_status=ClaimStatusAssertion.LICENSING_REQUIRED,
        asserted_owner="Studio Master Records",
        rights_layer=RightsLayer.RECORDING_OR_BROADCAST_MASTER,
        authority_tier=SourceAuthorityTier.TIER_2_ORGANIZATION_PRO_NEWS,
    )
    assert CorroborationEngine.classify_pair(comp_pd, rec_prot).stance == ConflictStance.NEUTRAL
    arb_dual = arbitrate_claim_conflicts("clm_dual_01", [comp_pd, rec_prot])
    assert arb_dual.conflict_detected is False and arb_dual.overall_stance != ConflictStance.CONTRADICTORY

    # 2. Genuine contradiction: incompatible assertions on same layer
    comp_owned = EvidenceFinding(
        finding_id="f_comp_owned", source_title="Publisher Registry",
        excerpt="Exclusive composition copyright claimed by Apex Publishing.",
        asserted_status=ClaimStatusAssertion.COPYRIGHTED, asserted_owner="Apex Publishing",
        rights_layer=RightsLayer.UNDERLYING_WORK,
        authority_tier=SourceAuthorityTier.TIER_2_ORGANIZATION_PRO_NEWS,
    )
    assert CorroborationEngine.classify_pair(comp_pd, comp_owned).stance == ConflictStance.CONTRADICTORY
    arb_conflict = arbitrate_claim_conflicts("clm_conflict_01", [comp_pd, comp_owned])
    assert arb_conflict.conflict_detected is True
    assert arb_conflict.overall_stance == ConflictStance.CONTRADICTORY
    assert arb_conflict.route_to_exceptions_schedule is True


def test_de_minimis_triage_no_automatic_clearance():
    """De minimis provides triage only with confidence < 1.0; never auto-clears."""
    eval_dm = eval_de_minimis(duration_sec=1.8, focal_prominence="background_fleeting", total_work_ratio=0.01)
    assert eval_dm.is_de_minimis is True
    assert eval_dm.confidence == 0.70
    assert eval_dm.confidence < 1.0
    assert eval_dm.actionable_risk == "TRIAGE_FAVORABLE_DE_MINIMIS"
    assert "Triage indicator only, requiring counsel review" in eval_dm.rationale
    assert "Ringgold v. Black Entertainment Television" in eval_dm.legal_precedent

    coord = EvidenceDrivenCoordinator(use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_dm_poster", occurrence_id="occ_dm",
        occurrence_lineage_id="prop_background_poster",
        right_category="artwork", rights_subject="Background Fleeting Poster",
    )
    coord.register_claim(claim)
    coord.claim_contexts[claim.claim_id]["de_minimis_eval"] = eval_dm.model_dump()
    coord.claim_contexts[claim.claim_id]["public_search_performed"] = True

    assert claim.disposition != CensusDisposition.APPROVED
    assert claim.approval_origin == ApprovalOrigin.NONE
    assert claim.approval_origin.value != "system_cleared_deterministic"


@pytest.mark.asyncio
async def test_act03_failed_extraction_no_premature_completion(monkeypatch):
    """Empty or failed ACT_03 extraction returns failure and prevents premature completion."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_fail_insp", occurrence_id="occ_fail_insp",
        occurrence_lineage_id="artwork_sculpture_unreachable",
        right_category="artwork", rights_subject="Unreachable Sculpture Site",
    )
    coord.register_claim(claim)
    coord.claim_contexts[claim.claim_id]["public_search_performed"] = True
    coord.claim_contexts[claim.claim_id]["urls_to_inspect"] = ["https://broken.registry.invalid/record"]

    async def mock_fail_extract(self, urls, objective=None):
        return []

    monkeypatch.setattr(ParallelExtractService, "extract", mock_fail_extract)
    res = await coord.execute_action(CoordinatorAction.ACT_03_INSPECT_SPECIFIC_SOURCE, claim)

    assert res["status"] == "FAILURE"
    assert len(res["extracted_sources"]) == 0
    assert coord.claim_contexts[claim.claim_id].get("source_inspection_performed", False) is False

    decide = coord.decide_next_action(claim)
    assert decide.action != CoordinatorAction.ACT_07_PREPARE_REVIEW_BRIEF
    assert claim.disposition != CensusDisposition.APPROVED
    assert claim.approval_origin == ApprovalOrigin.NONE
