"""
tests/test_investigation_dag_invariants.py

Automated test suite for DAG multi-hop invariants, limits, and cycle detection.
Sprint 3.2: Multi-Hop Planning & Investigation DAG Architecture.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.planner import InvestigationPlanner
from backend.agents.research.planner_types import (
    CycleDetectedError,
    ExtractedLead,
    MaxHopDepthExceededError,
    MaxQueryLimitReachedError,
    NodeStatus,
    SubgoalType,
)
from backend.services.parallel_types import ParallelSearchResult


def _create_test_dag():
    """Helper creating a test investigation DAG."""
    planner = InvestigationPlanner()
    claim = ExtractedClaim(
        claim_id="clm_inv_001",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 1",
        extracted_description="Fortunate Son by Creedence Clearwater Revival",
    )
    return planner, planner.create_initial_plan(claim)


def test_valid_hop_creation_and_parent_tracking():
    """Verifies that a valid lead creates a child node tracking parent ID and incremented depth."""
    planner, dag = _create_test_dag()
    root = dag.get_root_node()
    assert root is not None

    lead = ExtractedLead(
        lead_id="lead_001",
        lead_type="publisher",
        entity_name="Jondora Music",
        context="Administered by Jondora Music",
        subgoal_type=SubgoalType.COMPOSITION_PUBLISHING,
        confidence=0.75,
    )
    hop_node = planner.evaluate_hop_opportunity(dag, root, lead)

    assert hop_node is not None
    assert hop_node.parent_node_id == root.node_id
    assert hop_node.hop_depth == 1
    assert hop_node.status == NodeStatus.PENDING
    assert "Jondora Music" in hop_node.query_string
    assert len(dag.nodes) == 2
    assert dag.get_children(root.node_id) == [hop_node]


def test_max_hop_depth_exceeded_error():
    """Verifies hard enforcement of max depth <= 2 by raising MaxHopDepthExceededError."""
    planner, dag = _create_test_dag()
    root = dag.get_root_node()

    # Hop 1 (depth 0 -> 1)
    lead_1 = ExtractedLead(
        lead_id="l1",
        lead_type="publisher",
        entity_name="Fantasy Records",
        subgoal_type=SubgoalType.MASTER_RECORDING,
    )
    node_1 = planner.evaluate_hop_opportunity(dag, root, lead_1)
    assert node_1.hop_depth == 1

    # Hop 2 (depth 1 -> 2)
    lead_2 = ExtractedLead(
        lead_id="l2",
        lead_type="corporate_parent",
        entity_name="Concord Music Group",
        subgoal_type=SubgoalType.MASTER_RECORDING,
    )
    node_2 = planner.evaluate_hop_opportunity(dag, node_1, lead_2)
    assert node_2.hop_depth == 2

    # Hop 3 attempt from depth 2 must raise MaxHopDepthExceededError
    lead_3 = ExtractedLead(
        lead_id="l3",
        lead_type="holding_company",
        entity_name="Alchemy Copyrights",
        subgoal_type=SubgoalType.MASTER_RECORDING,
    )
    with pytest.raises(MaxHopDepthExceededError) as exc_info:
        planner.evaluate_hop_opportunity(dag, node_2, lead_3)
    assert "Hop depth limit (2) reached" in str(exc_info.value)


def test_max_query_limit_reached_error():
    """Verifies hard enforcement of max queries <= 5 by raising MaxQueryLimitReachedError."""
    planner, dag = _create_test_dag()
    root = dag.get_root_node()

    # Create 4 additional sibling nodes to hit total 5 queries
    for i in range(1, 5):
        lead = ExtractedLead(
            lead_id=f"lead_{i}",
            lead_type="publisher",
            entity_name=f"Entity Provider {i}",
            confidence=0.60,
        )
        child = planner.evaluate_hop_opportunity(dag, root, lead)
        assert child is not None

    assert len(dag.nodes) == 5

    # 6th query attempt must raise MaxQueryLimitReachedError
    overflow_lead = ExtractedLead(
        lead_id="lead_overflow",
        lead_type="publisher",
        entity_name="Overflow Entity",
        confidence=0.60,
    )
    with pytest.raises(MaxQueryLimitReachedError) as exc_info:
        planner.evaluate_hop_opportunity(dag, root, overflow_lead)
    assert "Query budget exhausted (5)" in str(exc_info.value)


def test_cycle_detection_in_ancestor_path():
    """Verifies CycleDetectedError is raised when hopping to an entity in ancestor query."""
    planner, dag = _create_test_dag()
    root = dag.get_root_node()

    lead_1 = ExtractedLead(
        lead_id="l1",
        lead_type="publisher",
        entity_name="Creedence Clearwater Revival",
        confidence=0.80,
    )
    # The root query already contains Creedence Clearwater Revival
    with pytest.raises(CycleDetectedError) as exc_info:
        planner.evaluate_hop_opportunity(dag, root, lead_1)
    assert "already queried in ancestor" in str(exc_info.value)


def test_duplicate_query_cycle_detection():
    """Verifies CycleDetectedError is raised when an entity was already targeted in DAG."""
    planner, dag = _create_test_dag()
    root = dag.get_root_node()

    lead_1 = ExtractedLead(
        lead_id="l1",
        lead_type="publisher",
        entity_name="Saul Zaentz Co",
        confidence=0.70,
    )
    node_1 = planner.evaluate_hop_opportunity(dag, root, lead_1)
    assert node_1 is not None

    # Proposing the exact same entity again from root
    lead_repeat = ExtractedLead(
        lead_id="l2",
        lead_type="publisher",
        entity_name="Saul Zaentz Co",
        confidence=0.70,
    )
    with pytest.raises(CycleDetectedError) as exc_info:
        planner.evaluate_hop_opportunity(dag, root, lead_repeat)
    assert "Duplicate query cycle" in str(exc_info.value)


def test_low_confidence_lead_rejection():
    """Verifies that leads below 0.30 confidence or blank entities return None."""
    planner, dag = _create_test_dag()
    root = dag.get_root_node()

    low_conf_lead = ExtractedLead(
        lead_id="l_low",
        lead_type="publisher",
        entity_name="Uncertain Name",
        confidence=0.20,
    )
    assert planner.evaluate_hop_opportunity(dag, root, low_conf_lead) is None

    empty_entity_lead = ExtractedLead(
        lead_id="l_empty",
        lead_type="publisher",
        entity_name="   ",
        confidence=0.80,
    )
    assert planner.evaluate_hop_opportunity(dag, root, empty_entity_lead) is None
