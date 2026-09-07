"""
tests/test_investigation_planner.py

Automated test suite for InvestigationPlanner and clearance DAG execution.
Sprint 3.2: Multi-Hop Planning & Investigation DAG Architecture.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.planner import InvestigationPlanner
from backend.agents.research.planner_types import (
    ExtractedLead,
    InvestigationPlannerError,
    NodeStatus,
    SubgoalStatus,
    SubgoalType,
)
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelSearchFinding,
    ParallelSearchResult,
)


def _build_music_claim() -> ExtractedClaim:
    """Helper creating sample music clearance claim."""
    return ExtractedClaim(
        claim_id="clm_mus_001",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 12 - Bar Scene",
        extracted_description="Sample of Funky Drummer by James Brown",
    )


def test_create_initial_plan_music_with_sample():
    """Verifies initial DAG synthesis for music claim with detected sample cues."""
    planner = InvestigationPlanner()
    claim = _build_music_claim()
    dag = planner.create_initial_plan(claim)

    assert dag.plan_id == "plan_clm_mus_001"
    assert dag.claim_id == "clm_mus_001"
    assert dag.max_depth == 2
    assert dag.max_queries == 5
    assert dag.total_queries_executed == 0
    assert dag.current_confidence == 0.0
    assert dag.is_complete is False

    # Subgoals should include publishing, master, sync, and sample clearance
    subgoal_types = [sg.subgoal_type for sg in dag.subgoals]
    assert SubgoalType.COMPOSITION_PUBLISHING in subgoal_types
    assert SubgoalType.MASTER_RECORDING in subgoal_types
    assert SubgoalType.SYNC_LICENSE in subgoal_types
    assert SubgoalType.SAMPLE_CLEARANCE in subgoal_types

    # Verify root node
    assert len(dag.nodes) == 1
    root = dag.get_root_node()
    assert root is not None
    assert root.hop_depth == 0
    assert root.parent_node_id is None
    assert root.status == NodeStatus.PENDING
    assert "site:ascap.com" in root.query_string


def test_create_initial_plan_brand_trademark():
    """Verifies initial DAG synthesis for brand/trademark clearance claim."""
    planner = InvestigationPlanner()
    claim = ExtractedClaim(
        claim_id="clm_brd_002",
        category=ClaimCategory.BRAND,
        scene_or_timecode="Scene 3 - Billboard",
        extracted_description="Acme Rocket Skates logo",
    )
    dag = planner.create_initial_plan(claim)
    assert len(dag.subgoals) == 1
    assert dag.subgoals[0].subgoal_type == SubgoalType.TRADEMARK_CLASS
    assert "site:tmsearch.uspto.gov" in dag.root_query


def test_advance_plan_updates_confidence_and_subgoal():
    """Verifies advance_plan updates node findings, confidence, and subgoal state."""
    planner = InvestigationPlanner()
    claim = _build_music_claim()
    dag = planner.create_initial_plan(claim)

    finding = ParallelSearchFinding(
        url="https://www.ascap.com/repertory#/ace/work/12345",
        title="Funky Drummer - ASCAP Repertory",
        domain="ascap.com",
        authority_tier=DomainAuthorityTier.TIER_2_RIGHTS_ORG,
        authority_score=0.85,
        confidence_score=0.90,
    )
    results = ParallelSearchResult(
        findings=[finding],
        http_status=200,
        top_authority_tier=DomainAuthorityTier.TIER_2_RIGHTS_ORG,
    )

    updated_dag = planner.advance_plan(dag, results)
    assert updated_dag.total_queries_executed == 1
    assert updated_dag.current_confidence >= 0.80

    root_node = updated_dag.get_root_node()
    assert root_node is not None
    assert root_node.status == NodeStatus.COMPLETED
    assert root_node.stop_condition_met is True
    assert len(root_node.findings) == 1

    # Subgoal mapped to root should be marked completed
    first_subgoal = updated_dag.subgoals[0]
    assert first_subgoal.status == SubgoalStatus.COMPLETED
    assert first_subgoal.confidence_score >= 0.80

    # DAG should mark completion due to >= 0.80 confidence threshold
    assert updated_dag.is_complete is True


def test_advance_plan_raises_when_no_active_node():
    """Verifies advance_plan raises InvestigationPlannerError if no node is pending."""
    planner = InvestigationPlanner()
    claim = _build_music_claim()
    dag = planner.create_initial_plan(claim)
    dag.nodes[0].status = NodeStatus.COMPLETED

    results = ParallelSearchResult(findings=[], http_status=200)
    with pytest.raises(InvestigationPlannerError) as exc_info:
        planner.advance_plan(dag, results)
    assert "No active or pending node" in str(exc_info.value)


def test_early_termination_on_high_confidence():
    """Verifies that high confidence findings trigger immediate graceful termination."""
    planner = InvestigationPlanner()
    claim = _build_music_claim()
    dag = planner.create_initial_plan(claim)

    high_conf_finding = ParallelSearchFinding(
        url="https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1",
        title="Copyright Catalog Entry",
        domain="cocatalog.loc.gov",
        authority_tier=DomainAuthorityTier.TIER_1_GOVERNMENT,
        authority_score=1.0,
        confidence_score=0.95,
    )
    results = ParallelSearchResult(findings=[high_conf_finding], http_status=200)
    updated_dag = planner.advance_plan(dag, results)

    assert planner.should_terminate(updated_dag) is True
    assert updated_dag.is_complete is True

    # Attempting hop on completed DAG should gracefully return None
    lead = ExtractedLead(
        lead_id="lead_01",
        lead_type="publisher",
        entity_name="Crited Music Inc",
        confidence=0.85,
    )
    hop = planner.evaluate_hop_opportunity(updated_dag, updated_dag.nodes[0], lead)
    assert hop is None
