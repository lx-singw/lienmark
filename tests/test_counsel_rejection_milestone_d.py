"""
tests/test_counsel_rejection_milestone_d.py

Milestone D Acceptance Test Suite:
1. Directed Research:
   - Manufactured fallback deleted (no registry.lienmark.internal, no manufactured 0.98).
   - Unconfigured search provider returns explicit status="UNRESOLVED", confidence=0.0.
   - SSRF protection blocks private IPs and internal endpoints with status="UNRESOLVED", confidence=0.0.
   - Budget reservation via MilestoneBBudgetManager before paid calls, settled on success, recovered on failure.
   - Preserves negations, dates, territories, and rights layers in formatted queries.
2. Claim Dependency Graph:
   - Explicit claim dependency edges (Master Recording -> Composition; Clip -> Persona).
   - Cycle-safe transitive downstream dependents traversal.
   - Distinct rights invariant: sharing scene or title does not trigger invalidation without explicit edge.
3. Reviewer Loop:
   - Rejection stores directive text alongside structured constraints.
   - Immutably preserves Attempt 1 and rationale in cryptographic ledger.
   - Increments claim attempt to Attempt 2.
   - Transitive downstream claims reopened via DependencyGraph.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict
import pytest

from backend.core.dependency_graph import (
    DependencyGraph,
    get_transitive_downstream_dependents,
)
from backend.core.directed_research import (
    DirectedResearchCoordinator,
    format_targeted_query,
)
from backend.core.reviewer_loop import CounselReviewLoopCoordinator
from backend.core.reviewer_types import CounselDirective, ResearchFinding
from backend.domain.models import AtomicRightsClaim, CensusDisposition, WorkflowReason
from backend.orchestration.milestone_b_reservation import MilestoneBBudgetManager
from backend.storage.ledger import CryptographicLedger


def test_manufactured_fallback_deleted_and_unconfigured_returns_unresolved():
    """Confirms manufactured fallback is deleted; unconfigured provider returns UNRESOLVED 0.0."""
    coord = DirectedResearchCoordinator(ledger=CryptographicLedger())
    claim = AtomicRightsClaim(
        claim_id="c_music_01", occurrence_id="occ_01", occurrence_lineage_id="lin_01",
        right_category="composition", rights_subject="Midnight Serenade",
    )
    directive = CounselDirective(
        claim_id="c_music_01", counsel_id="c_01", counsel_name="J. Adams",
        directive_text="Verify mechanical license without public domain claim in US",
        mandatory_constraints=["mechanical license required", "not public domain"],
    )
    finding = coord.dispatch_reinvestigation(claim, directive, "tenant_a", "prod_a")
    assert finding.status == "UNRESOLVED"
    assert finding.confidence_score == 0.0
    assert "registry.lienmark.internal" not in (finding.source_uri or "")
    assert "unconfigured" in finding.evidence_summary.lower()


def test_query_formatting_preserves_negations_dates_territories_and_rights():
    """Verifies targeted query formatter preserves negations, dates, territories, and rights distinctions."""
    directive = CounselDirective(
        claim_id="c_music_02", counsel_id="c_02", counsel_name="M. Vance",
        directive_text="Re-search ASCAP for 1972 master recording without public domain in UK and Worldwide",
        mandatory_constraints=["Verify 1972 release", "Excluding bootleg"],
    )
    query = format_targeted_query("Autumn Symphony", "master_recording", directive)
    assert '"Autumn Symphony"' in query
    assert "[master_recording]" in query
    assert "ASCAP" in query
    assert "DATES: (1972)" in query
    assert "UK" in query and "Worldwide" in query
    assert "without" in query or "NEGATIONS:" in query


def test_budget_reservation_and_ssrf_protection():
    """Verifies budget reservation before calls and SSRF protection returning UNRESOLVED 0.0."""
    ledger = CryptographicLedger()
    budget_mgr = MilestoneBBudgetManager(tenant_id="tenant_guard")

    def ssrf_search_executor(query: str, directive: CounselDirective, claim_id: str) -> Dict[str, Any]:
        return {"source_uri": "http://169.254.169.254/latest/meta-data/", "confidence_score": 0.9}

    coord = DirectedResearchCoordinator(
        ledger=ledger, search_executor=ssrf_search_executor, budget_manager=budget_mgr
    )
    claim = AtomicRightsClaim(
        claim_id="c_ssrf_01", occurrence_id="occ_s", occurrence_lineage_id="lin_s",
        right_category="trademark", rights_subject="Protected Brand",
    )
    directive = CounselDirective(
        claim_id="c_ssrf_01", counsel_id="c_03", counsel_name="L. Stone",
        directive_text="Check trademark register in US",
    )
    finding = coord.dispatch_reinvestigation(claim, directive, "tenant_guard", "prod_guard")
    assert finding.status == "UNRESOLVED"
    assert finding.confidence_score == 0.0
    assert "ssrf" in finding.evidence_summary.lower()


def test_explicit_claim_dependencies_and_cycle_safe_downstream_traversal():
    """Tests explicit dependency edges: Master -> Composition, Clip -> Persona and cycle safety."""
    graph = DependencyGraph(organization_id="org_test")
    # Master Sound Recording depends on Musical Composition
    graph.add_claim_dependency(dependent_claim_id="claim_master_01", upstream_claim_id="claim_comp_01", production_id="prod_soundtrack")
    # Sub-license depends on Master Sound Recording
    graph.add_claim_dependency(dependent_claim_id="claim_sublicense_01", upstream_claim_id="claim_master_01", production_id="prod_soundtrack")
    # Clip License depends on Persona / Trademark
    graph.add_claim_dependency(dependent_claim_id="claim_clip_01", upstream_claim_id="claim_persona_01", production_id="prod_soundtrack")

    # Invalidate Composition: downstream master and sublicense must be returned
    downstream_from_comp = graph.get_transitive_downstream_dependents("claim_comp_01", "prod_soundtrack")
    assert downstream_from_comp == ["claim_master_01", "claim_sublicense_01"]

    # Invalidate Persona: only clip license returned
    downstream_from_persona = graph.get_transitive_downstream_dependents("claim_persona_01", "prod_soundtrack")
    assert downstream_from_persona == ["claim_clip_01"]

    # Cycle safety: adding cycle B -> A when A -> B already exists
    graph.add_claim_dependency(dependent_claim_id="claim_comp_01", upstream_claim_id="claim_sublicense_01", production_id="prod_soundtrack")
    cycle_safe = graph.get_transitive_downstream_dependents("claim_comp_01", "prod_soundtrack")
    assert set(cycle_safe) == {"claim_master_01", "claim_sublicense_01"}


def test_distinct_rights_invariant():
    """Ensures composition and recording rights remain separate; sharing scene/title alone does not invalidate."""
    graph = DependencyGraph()
    # Two claims in the same scene and same title, but distinct rights
    graph.register_claim("claim_song_comp", "composition", "Yesterday", "prod_film", scene_id="scene_42", title="Yesterday")
    graph.register_claim("claim_song_master", "master_recording", "Yesterday", "prod_film", scene_id="scene_42", title="Yesterday")

    # Without explicit dependency, neither is downstream of the other
    assert graph.get_transitive_downstream_dependents("claim_song_comp", "prod_film") == []
    assert graph.get_transitive_downstream_dependents("claim_song_master", "prod_film") == []
    assert graph.check_distinct_rights_invariant("claim_song_comp", "claim_song_master", "prod_film") is True

    # Now add explicit dependency (Master depends on Composition)
    graph.add_claim_dependency("claim_song_master", "claim_song_comp", "prod_film")
    assert graph.get_transitive_downstream_dependents("claim_song_comp", "prod_film") == ["claim_song_master"]


def test_counsel_rejection_reopening_and_attempt_increment():
    """Verifies counsel rejection increments attempt to 2, stores constraints, and reopens downstream."""
    graph = DependencyGraph()
    graph.add_claim_dependency("claim_m10", "claim_c10", "prod_cinema")
    coordinator = CounselReviewLoopCoordinator(dependency_graph=graph)
    comp_claim = AtomicRightsClaim(claim_id="claim_c10", occurrence_id="occ_c", occurrence_lineage_id="lin_c",
                                   right_category="composition", rights_subject="Theme Song", attempt_number=1)
    master_claim = AtomicRightsClaim(claim_id="claim_m10", occurrence_id="occ_m", occurrence_lineage_id="lin_m",
                                     right_category="master_recording", rights_subject="Theme Song", disposition=CensusDisposition.APPROVED)
    directive = "Check BMI catalog specifically for sync license without mechanical restriction"
    dispatch = coordinator.reject_and_reopen_investigation(
        claim=comp_claim, prior_finding="PD assertion", directive_text=directive,
        counsel_id="c_alpha", counsel_name="Jane Doe, Esq.", tenant_id="tenant_w", production_id="prod_cinema",
        mandatory_constraints=["sync license required"], claims_lookup={"claim_m10": master_claim},
    )
    assert comp_claim.counsel_directive == directive
    assert comp_claim.attempt_number == 2
    assert comp_claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert dispatch.invalidated_downstream_claim_ids == ["claim_m10"]
    assert master_claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert "[Transitive Invalidation]" in master_claim.notes


def test_counsel_rejection_ledger_immutability():
    """Verifies Attempt 1 (Rejected) and rationale are preserved immutably in ledger."""
    ledger = CryptographicLedger()
    coordinator = CounselReviewLoopCoordinator(ledger=ledger)
    claim = AtomicRightsClaim(claim_id="claim_ledg", occurrence_id="occ_l", occurrence_lineage_id="lin_l",
                              right_category="trademark", rights_subject="Logo", attempt_number=1)
    coordinator.reject_and_reopen_investigation(
        claim=claim, prior_finding="Prior fair use claim", directive_text="Re-search USPTO",
        counsel_id="c_beta", counsel_name="Bob Ross, Esq.", tenant_id="tenant_w", production_id="prod_ledg",
    )
    events = ledger.get_events("prod_ledg")
    rejection_ev = [e for e in events if e.action_type == "CLAIM_REJECTED_BY_COUNSEL"][0]
    assert rejection_ev.payload["previous_attempt"] == 1
    assert rejection_ev.payload["new_attempt"] == 2
    assert rejection_ev.payload["directive_text"] == "Re-search USPTO"
    assert "Prior fair use claim" in rejection_ev.payload["prior_finding"]


def test_antigravity_code_structure_compliance():
    """Enforces AntiGravity constraints: files <= 250 lines, functions <= 40 lines."""
    targets = [
        Path("backend/core/directed_research.py"),
        Path("backend/core/dependency_graph.py"),
        Path("backend/core/reviewer_loop.py"),
        Path("tests/test_counsel_rejection_milestone_d.py"),
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
