"""
backend/agents/research/planner.py

Autonomous multi-hop investigation planner and DAG architecture.
Sprint 3.2: Multi-Hop Planning & Investigation DAG Architecture.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
from typing import Any, List, Optional, Set, Union

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.entity_catalog import is_false_lead
from backend.agents.research.planner_types import (
    CycleDetectedError,
    ExtractedLead,
    InvestigationPlanDAG,
    InvestigationPlannerError,
    MaxHopDepthExceededError,
    MaxQueryLimitReachedError,
    NodeStatus,
    QueryPlanNode,
    SubgoalType,
)
from backend.agents.research.subgoal_planner import SubgoalPlanner
from backend.services.parallel_types import ParallelSearchFinding, ParallelSearchResult


class InvestigationPlanner:
    """Autonomous multi-hop clearance investigation planner and DAG manager."""

    def __init__(self, subgoal_planner: Optional[SubgoalPlanner] = None) -> None:
        self.subgoal_planner = subgoal_planner or SubgoalPlanner()

    def _synthesize_root_query(self, claim: ExtractedClaim) -> str:
        """Constructs the initial root query based on claim category and description."""
        clean_desc = " ".join(claim.extracted_description.replace('"', "").split())
        if claim.category == ClaimCategory.MUSIC:
            return f'"{clean_desc}" catalog publishing master rights site:ascap.com OR site:bmi.com'
        if claim.category == ClaimCategory.BRAND:
            return f'"{clean_desc}" trademark registration site:tmsearch.uspto.gov OR site:wipo.int'
        if claim.category in (ClaimCategory.REAL_PERSON, ClaimCategory.HISTORICAL_FIGURE):
            return f'"{clean_desc}" "right of publicity" OR "estate of" OR site:cmgworldwide.com'
        return f'"{clean_desc}" "public domain" OR "copyright renewal" site:cocatalog.loc.gov'

    def create_initial_plan(self, claim: ExtractedClaim) -> InvestigationPlanDAG:
        """Dynamically evaluates claim complexity and synthesizes initial DAG."""
        subgoals = self.subgoal_planner.generate_subgoals(claim)
        root_query = self._synthesize_root_query(claim)
        anchor = " ".join(claim.extracted_description.replace('"', "").split())
        disam_key = hashlib.sha256(f"{claim.claim_id}:{anchor.lower()}".encode("utf-8")).hexdigest()[:16]
        root_node = QueryPlanNode(
            node_id=f"node_{claim.claim_id}_0",
            parent_node_id=None,
            claim_id=claim.claim_id,
            subgoal_id=subgoals[0].id if subgoals else None,
            query_string=root_query,
            hop_depth=0,
            generated_reason="Initial root query for primary clearance subgoal.",
            findings=[],
            status=NodeStatus.PENDING,
            stop_condition_met=False,
            disambiguation_key=disam_key,
            parent_entity_anchor=anchor,
        )
        return InvestigationPlanDAG(
            plan_id=f"plan_{claim.claim_id}",
            claim_id=claim.claim_id,
            root_query=root_query,
            subgoals=subgoals,
            nodes=[root_node],
            max_depth=2,
            max_queries=5,
            total_queries_executed=0,
            current_confidence=0.0,
            is_complete=False,
            disambiguation_key=disam_key,
            parent_entity_anchor=anchor,
        )

    def _detect_cycle(self, dag: InvestigationPlanDAG, current_node: QueryPlanNode, lead_entity: str) -> None:
        """Detects structural loops and repeated semantic queries in the DAG."""
        norm_entity = lead_entity.lower().strip()
        curr: Optional[QueryPlanNode] = current_node
        visited_ids: Set[str] = set()
        while curr is not None:
            if curr.node_id in visited_ids:
                raise CycleDetectedError(f"Structural cycle detected at node {curr.node_id}")
            visited_ids.add(curr.node_id)
            if norm_entity in curr.query_string.lower():
                raise CycleDetectedError(
                    f"Semantic cycle detected: lead '{lead_entity}' already queried in ancestor {curr.node_id}"
                )
            curr = dag.get_node(curr.parent_node_id) if curr.parent_node_id else None

        for node in dag.nodes:
            if f'"{norm_entity}"' in node.query_string.lower():
                raise CycleDetectedError(
                    f"Duplicate query cycle: entity '{lead_entity}' already targeted in node {node.node_id}"
                )

    def _build_hop_query(self, current_node: QueryPlanNode, lead: Any) -> str:
        """Formulates a disambiguated query string carrying parent entity anchor."""
        clean_entity = " ".join(lead.entity_name.replace('"', "").split())
        anchor = current_node.parent_entity_anchor
        anchor_clause = f' "{anchor}"' if anchor and anchor.lower() not in clean_entity.lower() else ""
        extension = getattr(lead, "proposed_query_extension", None)
        if extension and str(extension).strip():
            return f'"{clean_entity}"{anchor_clause} {str(extension).strip()}'
        sg_type = getattr(lead, "subgoal_type", None)
        if sg_type == SubgoalType.COMPOSITION_PUBLISHING:
            return f'"{clean_entity}"{anchor_clause} publishing catalog rights PRO site:ascap.com OR site:bmi.com'
        if sg_type == SubgoalType.MASTER_RECORDING:
            return f'"{clean_entity}"{anchor_clause} sound recording master rights record label'
        if sg_type == SubgoalType.SYNC_LICENSE:
            return f'"{clean_entity}"{anchor_clause} synchronization license rights agent clearance'
        if sg_type == SubgoalType.SAMPLE_CLEARANCE:
            return f'"{clean_entity}"{anchor_clause} sample clearance master original composition'
        if sg_type == SubgoalType.TRADEMARK_CLASS:
            return f'"{clean_entity}"{anchor_clause} trademark registration owner site:tmsearch.uspto.gov'
        if sg_type == SubgoalType.LIKENESS_ESTATE:
            return f'"{clean_entity}"{anchor_clause} estate right of publicity licensing representative'
        if sg_type == SubgoalType.PUBLIC_DOMAIN_PROOF:
            return f'"{clean_entity}"{anchor_clause} public domain copyright renewal status LOC'
        return f'"{clean_entity}"{anchor_clause} legal clearance rights owner'

    def _validate_hop_eligibility(
        self, dag: InvestigationPlanDAG, current_node: QueryPlanNode, extracted_lead: Any
    ) -> bool:
        """Validates depth, budgets, false leads, and lead confidence thresholds."""
        if self.should_terminate(dag):
            return False
        if current_node.hop_depth >= dag.max_depth:
            raise MaxHopDepthExceededError(
                f"Hop depth limit ({dag.max_depth}) reached at node {current_node.node_id}"
            )
        if len(dag.nodes) >= dag.max_queries:
            raise MaxQueryLimitReachedError(
                f"Query budget exhausted ({dag.max_queries}) for plan {dag.plan_id}"
            )
        if is_false_lead(extracted_lead.entity_name):
            return False
        lead_conf = getattr(
            extracted_lead, "confidence", getattr(extracted_lead, "confidence_score", 0.5)
        )
        return lead_conf >= 0.30 and bool(extracted_lead.entity_name.strip())

    def evaluate_hop_opportunity(
        self,
        dag: InvestigationPlanDAG,
        current_node: QueryPlanNode,
        extracted_lead: Any,
    ) -> Optional[QueryPlanNode]:
        """Evaluates extracted evidence lead and branches to a child query node if justified."""
        if not self._validate_hop_eligibility(dag, current_node, extracted_lead):
            return None

        self._detect_cycle(dag, current_node, extracted_lead.entity_name)

        child_depth = current_node.hop_depth + 1
        child_id = f"node_{dag.claim_id}_{len(dag.nodes)}"
        query_str = self._build_hop_query(current_node, extracted_lead)
        l_type = getattr(
            extracted_lead, "lead_type", getattr(extracted_lead, "entity_type", "lead")
        )
        l_type_val = l_type.value if hasattr(l_type, "value") else str(l_type)

        child_node = QueryPlanNode(
            node_id=child_id,
            parent_node_id=current_node.node_id,
            claim_id=dag.claim_id,
            subgoal_id=self.subgoal_planner.resolve_lead_subgoal(dag.subgoals, extracted_lead),
            query_string=query_str,
            hop_depth=child_depth,
            generated_reason=f"Hop {child_depth} investigating {l_type_val}: {extracted_lead.entity_name}",
            findings=[],
            status=NodeStatus.PENDING,
            stop_condition_met=False,
            disambiguation_key=current_node.disambiguation_key or dag.disambiguation_key,
            parent_entity_anchor=current_node.parent_entity_anchor or dag.parent_entity_anchor,
        )
        dag.nodes.append(child_node)
        return child_node

    def should_terminate(self, dag: InvestigationPlanDAG) -> bool:
        """Hard enforcement of depth <= 2, query count <= 5, confidence >= 0.80, and latency <= 30s."""
        if dag.is_complete:
            return True
        if dag.current_confidence >= 0.80:
            return True
        if dag.total_queries_executed >= dag.max_queries:
            return True
        if dag.total_elapsed_seconds >= dag.max_latency_seconds:
            return True
        if len(dag.nodes) >= dag.max_queries and all(
            n.status in (NodeStatus.COMPLETED, NodeStatus.FAILED) for n in dag.nodes
        ):
            return True
        return False

    def _calculate_findings_confidence(self, findings: List[ParallelSearchFinding]) -> float:
        """Calculates weighted confidence across findings based on authority tier."""
        if not findings:
            return 0.0
        scores = [
            min(1.0, f.confidence_score * (0.6 + 0.4 * f.authority_score))
            for f in findings
        ]
        return max(scores, default=0.0)

    def advance_plan(
        self,
        dag: InvestigationPlanDAG,
        results: ParallelSearchResult,
    ) -> InvestigationPlanDAG:
        """Advances DAG state with incoming search findings, updating confidence and termination."""
        target_node = dag.get_active_node()
        if target_node is None:
            raise InvestigationPlannerError(f"No active or pending node available in plan {dag.plan_id}")

        target_node.findings = list(results.findings)
        target_node.status = (
            NodeStatus.COMPLETED if results.http_status < 400 else NodeStatus.FAILED
        )
        dag.total_queries_executed += 1

        findings_conf = self._calculate_findings_confidence(results.findings)
        if findings_conf >= 0.80:
            target_node.stop_condition_met = True

        dag.current_confidence = max(dag.current_confidence, findings_conf)
        self.subgoal_planner.update_subgoals(dag.subgoals, target_node.subgoal_id, findings_conf)

        if self.should_terminate(dag):
            dag.is_complete = True
        return dag
