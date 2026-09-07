"""
tests/test_multihop_research.py

Sprint 3.2 Acceptance Gate: Autonomous Multi-Hop Clearance Research.
Validates decomposition into composition & master subgoals, Hop 0 execution,
parent publisher entity extraction, Hop 1 child query formulation, and invariants:
depth <= 2, queries <= 5, cycle detection, and parent finding lineage.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ExtractedClaim
from backend.agents.research.entity_extractor import EntityExtractor
from backend.agents.research.lead_types import (
    ExtractedLead,
    LeadEntityType,
    LeadRelationshipType,
)
from backend.agents.research.planner import InvestigationPlanner
from backend.agents.research.planner_types import (
    CycleDetectedError,
    InvestigationPlanDAG,
    MaxHopDepthExceededError,
    MaxQueryLimitReachedError,
    NodeStatus,
    QueryPlanNode,
    SubgoalType,
)
from backend.services.parallel_types import ParallelSearchResult

pytest_plugins = ["tests.fixtures_multihop"]


def test_autonomous_decomposition_into_subgoals(ambiguous_music_claim: ExtractedClaim):
    """Asserts autonomous decomposition into composition and master subgoals."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)

    assert dag.claim_id == "clm_mus_ambiguous_001"
    subgoal_types = [sg.subgoal_type for sg in dag.subgoals]
    assert SubgoalType.COMPOSITION_PUBLISHING in subgoal_types
    assert SubgoalType.MASTER_RECORDING in subgoal_types

    root = dag.get_root_node()
    assert root is not None
    assert root.hop_depth == 0
    assert root.parent_node_id is None
    assert "Midnight Echoes at Twilight" in root.query_string
    assert len(dag.nodes) == 1


def test_primary_query_hop0_execution(
    ambiguous_music_claim: ExtractedClaim,
    hop0_search_result: ParallelSearchResult,
):
    """Executes primary query (Hop 0) and records search findings."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)
    root = dag.get_root_node()
    assert root is not None

    dag = planner.advance_plan(dag, hop0_search_result)
    assert root.status == NodeStatus.COMPLETED
    assert dag.total_queries_executed == 1
    assert len(root.findings) == 1
    assert root.findings[0].domain == "ascap.com"


def test_entity_extractor_extracts_parent_publisher_lead(
    ambiguous_music_claim: ExtractedClaim,
    hop0_search_result: ParallelSearchResult,
):
    """Extracts parent publisher lead from snippet and validates parent finding ID."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)
    dag = planner.advance_plan(dag, hop0_search_result)
    root = dag.get_root_node()
    assert root is not None

    extractor = EntityExtractor()
    leads = extractor.extract_leads_from_findings(root.findings)
    assert len(leads) >= 1

    lead = next((item for item in leads if item.entity_name == "Sony Music Publishing"), None)
    assert lead is not None
    assert lead.entity_type == LeadEntityType.PUBLISHER
    assert lead.relationship_type == LeadRelationshipType.ADMINISTERED_BY
    assert len(lead.parent_finding_id) > 0
    assert "music publishing" in lead.proposed_query_extension


def test_single_multihop_child_query_execution(
    ambiguous_music_claim: ExtractedClaim,
    hop0_search_result: ParallelSearchResult,
    hop1_search_result: ParallelSearchResult,
):
    """Executes exactly 1 multi-hop follow-up query (Hop 1) targeting the parent catalog."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)
    root = dag.get_root_node()
    assert root is not None
    dag = planner.advance_plan(dag, hop0_search_result)

    extractor = EntityExtractor()
    lead = next(item for item in extractor.extract_leads_from_findings(root.findings) if item.entity_name == "Sony Music Publishing")

    child_node = planner.evaluate_hop_opportunity(dag, root, lead)
    assert child_node is not None
    assert child_node.hop_depth == 1
    assert child_node.parent_node_id == root.node_id
    assert "Sony Music Publishing" in child_node.query_string
    assert len(dag.nodes) == 2

    dag = planner.advance_plan(dag, hop1_search_result)
    assert child_node.status == NodeStatus.COMPLETED
    assert child_node.stop_condition_met is True
    assert dag.total_queries_executed == 2
    assert dag.is_complete is True


def _build_depth_nodes(dag: InvestigationPlanDAG, root: QueryPlanNode) -> QueryPlanNode:
    """Helper to assemble a depth-2 branch in the DAG."""
    n1 = QueryPlanNode(
        node_id="node_1",
        parent_node_id=root.node_id,
        claim_id=dag.claim_id,
        query_string="child query hop 1",
        hop_depth=1,
        generated_reason="Hop 1",
    )
    dag.nodes.append(n1)
    n2 = QueryPlanNode(
        node_id="node_2",
        parent_node_id=n1.node_id,
        claim_id=dag.claim_id,
        query_string="grandchild query hop 2",
        hop_depth=2,
        generated_reason="Hop 2",
    )
    dag.nodes.append(n2)
    return n2


def test_hop_depth_limit_invariant(ambiguous_music_claim: ExtractedClaim):
    """Enforces hop depth invariant: depth <= 2 strictly, rejecting depth > 2."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)
    root = dag.get_root_node()
    assert root is not None
    node_hop2 = _build_depth_nodes(dag, root)

    lead = ExtractedLead(
        lead_id="ld_overflow",
        parent_finding_id="f_overflow",
        entity_name="BMG Rights",
        entity_type=LeadEntityType.PUBLISHER,
        relationship_type=LeadRelationshipType.ADMINISTERED_BY,
        confidence_score=0.9,
        source_sentence="Administered by BMG Rights.",
        proposed_query_extension="BMG Rights catalog",
    )
    with pytest.raises(MaxHopDepthExceededError):
        planner.evaluate_hop_opportunity(dag, node_hop2, lead)


def test_max_queries_budget_invariant(ambiguous_music_claim: ExtractedClaim):
    """Enforces maximum query limit invariant (total <= 5 across DAG)."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)
    root = dag.get_root_node()
    assert root is not None

    for i in range(1, 5):
        dag.nodes.append(
            QueryPlanNode(
                node_id=f"node_{i}",
                parent_node_id=root.node_id,
                claim_id=dag.claim_id,
                query_string=f"extra query {i}",
                hop_depth=1,
                generated_reason=f"Extra branch {i}",
            )
        )
    assert len(dag.nodes) == 5

    lead = ExtractedLead(
        lead_id="ld_budget",
        parent_finding_id="f_budget",
        entity_name="Kobalt Music",
        entity_type=LeadEntityType.PUBLISHER,
        relationship_type=LeadRelationshipType.ADMINISTERED_BY,
        confidence_score=0.85,
        source_sentence="Administered by Kobalt Music.",
        proposed_query_extension="Kobalt Music catalog",
    )
    with pytest.raises(MaxQueryLimitReachedError):
        planner.evaluate_hop_opportunity(dag, root, lead)


def test_cycle_prevention_invariants(ambiguous_music_claim: ExtractedClaim):
    """Verifies prevention of semantic cycles targeting already queried entities."""
    planner = InvestigationPlanner()
    dag = planner.create_initial_plan(ambiguous_music_claim)
    root = dag.get_root_node()
    assert root is not None

    lead_cycle = ExtractedLead(
        lead_id="ld_cycle",
        parent_finding_id="f_cycle",
        entity_name="Midnight Echoes at Twilight",
        entity_type=LeadEntityType.PUBLISHER,
        relationship_type=LeadRelationshipType.ADMINISTERED_BY,
        confidence_score=0.9,
        source_sentence="Administered by Midnight Echoes at Twilight.",
        proposed_query_extension="catalog search",
    )
    with pytest.raises(CycleDetectedError):
        planner.evaluate_hop_opportunity(dag, root, lead_cycle)
