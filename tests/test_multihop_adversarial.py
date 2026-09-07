"""
tests/test_multihop_adversarial.py

Adversarial test suite verifying defensive invariants against multi-hop failure modes.
Sprint 3.2: Multi-Hop Lead Chasing & Autonomous Plan Synthesis.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from typing import Optional
import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.entity_extractor import EntityExtractor
from backend.agents.research.planner import InvestigationPlanner
from backend.agents.research.planner_types import (
    CycleDetectedError,
    ExtractedLead,
    MaxHopDepthExceededError,
    MaxQueryLimitReachedError,
    SubgoalType,
)
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelSearchFinding,
    ParallelSearchResult,
)


def _build_test_claim(claim_id: str = "clm_adv_001") -> ExtractedClaim:
    """Helper building a standard ambiguous music clearance claim."""
    return ExtractedClaim(
        claim_id=claim_id,
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 4 - Lounge Cue",
        extracted_description="Midnight Serenade by David Miller",
    )


def _make_lead(
    lead_id: str,
    name: str,
    lead_type: str = "publisher",
    conf: float = 0.75,
    sg: Optional[SubgoalType] = None,
) -> ExtractedLead:
    """Factory creating consistent ExtractedLead instances for adversarial tests."""
    return ExtractedLead(
        lead_id=lead_id,
        lead_type=lead_type,
        entity_name=name,
        subgoal_type=sg,
        confidence=conf,
    )


def test_adversarial_depth_ceiling_strictly_enforced():
    """Verifies that attempting hop depth > 2 immediately raises MaxHopDepthExceededError."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())
    root = dag.get_root_node()
    assert root.hop_depth == 0

    lead_h1 = _make_lead("l1", "Vanguard Media Group", "publisher", 0.75, SubgoalType.COMPOSITION_PUBLISHING)
    node_h1 = planner.evaluate_hop_opportunity(dag, root, lead_h1)
    assert node_h1 is not None and node_h1.hop_depth == 1

    lead_h2 = _make_lead("l2", "Apex Global Holdings", "corporate_parent", 0.70, SubgoalType.COMPOSITION_PUBLISHING)
    node_h2 = planner.evaluate_hop_opportunity(dag, node_h1, lead_h2)
    assert node_h2 is not None and node_h2.hop_depth == 2

    lead_h3 = _make_lead("l3", "Miller Heritage Trust", "trust_foundation", 0.65, SubgoalType.COMPOSITION_PUBLISHING)
    with pytest.raises(MaxHopDepthExceededError) as exc_info:
        planner.evaluate_hop_opportunity(dag, node_h2, lead_h3)

    assert "Hop depth limit (2) reached" in str(exc_info.value)
    assert len(dag.nodes) == 3


def test_adversarial_query_quota_exhaustion_enforced():
    """Verifies that attempting > 5 queries raises MaxQueryLimitReachedError."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())
    root = dag.get_root_node()

    for idx in range(1, 5):
        lead = _make_lead(f"lead_quota_{idx}", f"Licensing Affiliate {idx}", "publisher", 0.65)
        child = planner.evaluate_hop_opportunity(dag, root, lead)
        assert child is not None

    assert len(dag.nodes) == 5

    overflow_lead = _make_lead("lead_overflow", "Licensing Affiliate 6", "publisher", 0.65)
    with pytest.raises(MaxQueryLimitReachedError) as exc_info:
        planner.evaluate_hop_opportunity(dag, root, overflow_lead)

    assert "Query budget exhausted (5)" in str(exc_info.value)
    assert len(dag.nodes) == 5


def test_adversarial_confidence_threshold_immediate_stop():
    """Verifies that evidence achieving confidence >= 0.80 halts hopping immediately."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())

    finding = ParallelSearchFinding(
        url="https://www.ascap.com/ace/work/998877",
        title="Midnight Serenade - Official ASCAP Repertoire",
        domain="ascap.com",
        authority_tier=DomainAuthorityTier.TIER_2_RIGHTS_ORG,
        authority_score=0.90,
        confidence_score=0.92,
    )
    results = ParallelSearchResult(findings=[finding], http_status=200)
    updated_dag = planner.advance_plan(dag, results)

    assert updated_dag.current_confidence >= 0.80
    assert updated_dag.is_complete is True
    assert planner.should_terminate(updated_dag) is True

    candidate = _make_lead("lead_post_stop", "Sony Music Publishing", "publisher", 0.85)
    assert planner.evaluate_hop_opportunity(updated_dag, updated_dag.nodes[0], candidate) is None
    assert len(updated_dag.nodes) == 1


def test_adversarial_circular_ownership_ping_pong_trapped():
    """Verifies that A -> B -> A circular loops are detected and trapped without infinite recursion."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())
    root = dag.get_root_node()

    lead_b = _make_lead("lead_b", "Company B Music Group", "publisher", 0.75)
    node_b = planner.evaluate_hop_opportunity(dag, root, lead_b)
    assert node_b is not None

    loop_lead_a = _make_lead("lead_a_loop", "David Miller", "corporate_parent", 0.80)
    with pytest.raises(CycleDetectedError) as exc_info:
        planner.evaluate_hop_opportunity(dag, node_b, loop_lead_a)
    assert "already queried in ancestor" in str(exc_info.value)

    duplicate_lead_b = _make_lead("lead_b_dup", "Company B Music Group", "publisher", 0.75)
    with pytest.raises(CycleDetectedError) as exc_info:
        planner.evaluate_hop_opportunity(dag, root, duplicate_lead_b)
    assert "Duplicate query cycle" in str(exc_info.value)


def test_adversarial_false_lead_studio_venue_sponsor_rejected():
    """Verifies that recording studios, venues, and sponsors are rejected from query generation."""
    extractor = EntityExtractor()
    snippet = (
        "Recorded at Sony Music Studios in New York. "
        "Session engineered at Abbey Road Studios and sponsored by Red Bull. "
        "Available on Spotify, master courtesy of Decca Records."
    )
    leads = extractor.extract_leads_from_text(snippet, parent_finding_id="find_fl")
    entities = {l.entity_name.lower() for l in leads}
    assert "sony music studios" not in entities
    assert "abbey road studios" not in entities
    assert "red bull" not in entities
    assert "spotify" not in entities
    assert "decca records" in entities

    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())
    root = dag.get_root_node()

    lead_studio = _make_lead("fl_studio", "Electric Lady Studios", "publisher", 0.70)
    lead_sponsor = _make_lead("fl_sponsor", "Red Bull", "publisher", 0.70)
    assert planner.evaluate_hop_opportunity(dag, root, lead_studio) is None
    assert planner.evaluate_hop_opportunity(dag, root, lead_sponsor) is None
    assert len(dag.nodes) == 1


def test_adversarial_disambiguation_key_preserved_across_hops():
    """Verifies that child queries preserve parent entity anchors to prevent context drift."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())
    root = dag.get_root_node()

    assert root.disambiguation_key is not None
    assert root.parent_entity_anchor == "Midnight Serenade by David Miller"
    assert dag.disambiguation_key == root.disambiguation_key

    lead_h1 = _make_lead("l_h1", "Sony Music Publishing", "publisher", 0.75, SubgoalType.COMPOSITION_PUBLISHING)
    node_h1 = planner.evaluate_hop_opportunity(dag, root, lead_h1)
    assert node_h1 is not None
    assert node_h1.disambiguation_key == root.disambiguation_key
    assert node_h1.parent_entity_anchor == root.parent_entity_anchor
    assert "Sony Music Publishing" in node_h1.query_string
    assert "Midnight Serenade" in node_h1.query_string


def test_adversarial_latency_budget_exhaustion_terminates():
    """Verifies that exceeding 30-second UX SLA stops hopping immediately."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(_build_test_claim())
    root = dag.get_root_node()

    dag.total_elapsed_seconds = 30.5
    assert planner.should_terminate(dag) is True

    lead = _make_lead("l_slow", "Warner Chappell Music", "publisher", 0.75)
    assert planner.evaluate_hop_opportunity(dag, root, lead) is None
    assert len(dag.nodes) == 1
