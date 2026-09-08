"""
Adversarial Disconfirmation & Counsel Briefing Audit Tests.
Verifies disconfirming evidence flow from ACT_05 to ACT_07 without reversion to public snapshots.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import ast
import pytest
from pathlib import Path

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    EvidenceStance,
    WorkflowReason,
    PublicEvidenceSnapshot,
)
from backend.orchestration.adk_pipeline import (
    CoordinatorAction,
    EvidenceDrivenCoordinator,
)
from backend.services.gemini_service import GeminiService, ClearanceBriefing
from backend.services.briefing_synthesis import (
    evaluate_evidence_stance,
    extract_adverse_claimants,
    synthesize_counsel_action,
    synthesize_counsel_summary,
)


@pytest.mark.asyncio
async def test_act05_captures_snapshot_and_stance():
    """ACT_05 captures disconfirming snapshot ID and marks adverse evidence."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_audit_radio_01",
        occurrence_id="occ_radio_01",
        occurrence_lineage_id="radio_broadcast_cue",
        right_category="copyright",
        rights_subject="Radio Drama 1948",
    )
    coord.register_claim(claim)

    res = await coord.execute_action(CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION, claim)
    assert res["status"] == "SUCCESS"
    assert "tool_output" in res
    assert len(claim.evidence_ids) >= 1
    assert claim.evidence_ids[-1] == res["tool_output"]["snapshot_id"]
    ctx = coord.claim_contexts[claim.claim_id]
    assert ctx["adversarial_disconfirmation_performed"] is True
    assert "adversarial_evidence" in ctx


@pytest.mark.asyncio
async def test_act07_synthesizes_brief_from_adversarial_disconfirmation():
    """ACT_07 prioritizes contradictory disconfirmation over preliminary public snapshot."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_audit_radio_02",
        occurrence_id="occ_radio_02",
        occurrence_lineage_id="radio_broadcast_cue",
        right_category="copyright",
        rights_subject="Radio Drama 1948",
    )
    coord.register_claim(claim)

    # 1. Phase 1 Public Search (returns preliminary supporting registry hit)
    res_pub = await coord.execute_action(CoordinatorAction.ACT_02_SEARCH_PUBLIC_SOURCES, claim)
    assert res_pub["status"] == "SUCCESS"

    # 2. Phase 2 Adversarial Disconfirmation (detects adverse dispute)
    res_adv = await coord.execute_action(CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION, claim)
    assert res_adv["status"] == "SUCCESS"

    # 3. Phase 3 Prepare Review Brief
    res_brief = await coord.execute_action(CoordinatorAction.ACT_07_PREPARE_REVIEW_BRIEF, claim)
    assert res_brief["status"] == "SUCCESS"

    briefing = res_brief["briefing"]
    assert briefing["parallel_evidence_stance"] == "CONTRADICTORY"
    assert any(kw in briefing["suggested_counsel_action"].upper() for kw in ("EXCEPTION", "NEGOTIATION", "LICENSE"))
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert coord.claim_states[claim.claim_id] == "ready_for_review"


@pytest.mark.asyncio
async def test_gemini_service_contradictory_stance_evaluation():
    """GeminiService evaluates arbitrary asset with contradictory evidence."""
    service = GeminiService()
    adv_ev = {
        "source_title": "Apex Trademark Docket",
        "source_url": "https://tm.records.gov/apex",
        "excerpt": "Apex Global asserts exclusive ownership and copyright infringement against uncredited usage.",
        "stance": "CONTRADICTORY",
    }
    briefing = await service.synthesize_counsel_briefing(
        asset_name="Solaris Navigation Logo",
        reason_code="EXTERNAL_EVIDENCE_CONFLICT",
        evidence_excerpt=adv_ev["excerpt"],
        source_title=adv_ev["source_title"],
        source_url=adv_ev["source_url"],
        evidence_stance="CONTRADICTORY",
    )
    assert isinstance(briefing, ClearanceBriefing)
    assert briefing.parallel_evidence_stance == "CONTRADICTORY"
    assert "Apex Global" in briefing.counsel_summary
    assert "UNRESOLVED EXCEPTION" in briefing.suggested_counsel_action


@pytest.mark.asyncio
async def test_gemini_service_supporting_stance_evaluation():
    """GeminiService evaluates arbitrary asset with supporting public domain evidence."""
    service = GeminiService()
    supp_ev = {
        "source_title": "LOC Copyright Catalog",
        "source_url": "https://cocatalog.loc.gov/1922",
        "excerpt": "Statutory copyright term expired; work entered public domain without renewal.",
        "stance": "SUPPORTING",
    }
    briefing = await service.synthesize_counsel_briefing(
        asset_name="1922 Silent Film Reel",
        reason_code="EVIDENCE_VERIFIED",
        evidence_excerpt=supp_ev["excerpt"],
        source_title=supp_ev["source_title"],
        source_url=supp_ev["source_url"],
        evidence_stance="SUPPORTING",
    )
    assert briefing.parallel_evidence_stance == "SUPPORTING"
    assert "APPROVED" in briefing.suggested_counsel_action.upper()


def test_briefing_synthesis_helpers():
    """Verifies standalone helper functions for stance, claimants, and counsel advice."""
    assert evaluate_evidence_stance(None, excerpt="exclusive assigned rights") == "CONTRADICTORY"
    assert evaluate_evidence_stance(None, excerpt="statutory duration lapse public domain") == "SUPPORTING"
    assert evaluate_evidence_stance(None, excerpt="zero matching records found") == "INSUFFICIENT"

    claimants = extract_adverse_claimants("Assigned to Vanguard Media Holdings LLC under sync deal.")
    assert len(claimants) >= 1
    assert "Vanguard Media Holdings" in claimants[0]

    action_contra = synthesize_counsel_action("CONTRADICTORY")
    assert "UNRESOLVED EXCEPTION" in action_contra
    assert "license negotiation" in action_contra


def test_antigravity_budget_compliance():
    """Enforces AntiGravity constraints: files <= 250 lines, functions <= 40 lines."""
    targets = [
        Path("backend/services/briefing_synthesis.py"),
        Path("tests/test_adversarial_counsel_audit.py"),
    ]
    for p in targets:
        assert p.exists(), f"Target file {p} must exist"
        lines = p.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 250, f"{p.name} exceeds 250 lines ({len(lines)} lines)"

        tree = ast.parse("\n".join(lines))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or 0) - node.lineno + 1
                assert length <= 40, f"Function '{node.name}' in {p.name} exceeds 40 lines ({length})"
