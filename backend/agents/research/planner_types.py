"""
backend/agents/research/planner_types.py

Canonical Pydantic v2 schemas and taxonomy for autonomous multi-hop investigation planning.
Sprint 3.2: Multi-Hop Planning & Investigation DAG Architecture.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.services.parallel_types import ParallelSearchFinding


class SubgoalType(str, Enum):
    """Clearance subgoals categorizing orthogonal dimensions of IP rights."""
    COMPOSITION_PUBLISHING = "composition_publishing"
    MASTER_RECORDING = "master_recording"
    SYNC_LICENSE = "sync_license"
    SAMPLE_CLEARANCE = "sample_clearance"
    TRADEMARK_CLASS = "trademark_class"
    LIKENESS_ESTATE = "likeness_estate"
    PUBLIC_DOMAIN_PROOF = "public_domain_proof"


class SubgoalStatus(str, Enum):
    """Lifecycle progression states for an investigation subgoal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeStatus(str, Enum):
    """Execution status for an individual query plan node in the DAG."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationPlannerError(Exception):
    """Base domain exception for autonomous investigation planning."""
    pass


class MaxHopDepthExceededError(InvestigationPlannerError):
    """Raised when an investigation branch attempts to exceed max allowed hop depth."""
    pass


class MaxQueryLimitReachedError(InvestigationPlannerError):
    """Raised when a plan attempts to schedule queries beyond the max query budget."""
    pass


class CycleDetectedError(InvestigationPlannerError):
    """Raised when a proposed query or entity hop creates a cycle in the plan DAG."""
    pass


class FalseLeadRejectedError(InvestigationPlannerError):
    """Raised when an extracted lead is identified as a non-licensable studio or sponsor."""
    pass


class LatencyBudgetExceededError(InvestigationPlannerError):
    """Raised when investigation exceeds 30-second latency SLA budget."""
    pass


class ExtractedLead(BaseModel):
    """Entity or evidentiary lead extracted from search findings prompting a hop."""
    model_config = ConfigDict(frozen=True)

    lead_id: str = Field(..., description="Unique lead identifier.")
    lead_type: str = Field(..., description="Classification of lead (e.g. publisher, label, estate).")
    entity_name: str = Field(..., min_length=1, description="Discovered entity or rights-holder name.")
    context: str = Field(default="", description="Contextual excerpt or reason this lead was surfaced.")
    subgoal_type: Optional[SubgoalType] = Field(default=None, description="Targeted clearance subgoal.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in lead validity.")


class InvestigationSubgoal(BaseModel):
    """High-level clearance objective addressing a specific rights category."""
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(..., description="Unique identifier for the subgoal.")
    subgoal_type: SubgoalType = Field(..., description="Subgoal clearance type category.")
    description: str = Field(..., description="Detailed description of the clearance objective.")
    priority: int = Field(default=1, ge=1, description="Execution priority (1 is highest).")
    status: SubgoalStatus = Field(default=SubgoalStatus.PENDING, description="Current lifecycle state.")
    target_entities: List[str] = Field(default_factory=list, description="Target entities identified.")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Reconciled confidence score.")


class QueryPlanNode(BaseModel):
    """Single node in the investigation DAG representing a discrete query execution."""
    model_config = ConfigDict(validate_assignment=True)

    node_id: str = Field(..., description="Unique node identifier.")
    parent_node_id: Optional[str] = Field(default=None, description="Identifier of parent node, or None for root.")
    claim_id: str = Field(..., description="Identifier of parent clearance claim.")
    subgoal_id: Optional[str] = Field(default=None, description="Associated subgoal identifier if mapped.")
    query_string: str = Field(..., min_length=1, description="Synthesized search query string.")
    hop_depth: int = Field(default=0, ge=0, le=2, description="Hop depth from root (0 = root, max 2).")
    generated_reason: str = Field(..., description="Justification and lineage note for this query.")
    findings: List[ParallelSearchFinding] = Field(default_factory=list, description="Search findings retrieved.")
    status: NodeStatus = Field(default=NodeStatus.PENDING, description="Node execution status.")
    stop_condition_met: bool = Field(default=False, description="Whether stopping threshold was reached.")
    disambiguation_key: Optional[str] = Field(default=None, description="Deterministic entity isolation key.")
    parent_entity_anchor: Optional[str] = Field(default=None, description="Anchor entity from root/parent.")


class InvestigationPlanDAG(BaseModel):
    """Directed Acyclic Graph governing multi-hop clearance research for a claim."""
    model_config = ConfigDict(validate_assignment=True)

    plan_id: str = Field(..., description="Unique identifier for this investigation plan.")
    claim_id: str = Field(..., description="Identifier of the clearance claim being investigated.")
    root_query: str = Field(..., description="Initial root query formulated for the claim.")
    subgoals: List[InvestigationSubgoal] = Field(default_factory=list, description="Clearance subgoals.")
    nodes: List[QueryPlanNode] = Field(default_factory=list, description="Query nodes in the DAG.")
    max_depth: int = Field(default=2, ge=0, le=2, description="Maximum permitted hop depth.")
    max_queries: int = Field(default=5, ge=1, description="Maximum queries allowed across DAG.")
    total_queries_executed: int = Field(default=0, ge=0, description="Total queries actually executed.")
    current_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Current highest confidence.")
    is_complete: bool = False
    max_latency_seconds: float = Field(default=30.0, description="Hard timeout ceiling for multi-hop claim research.")
    total_elapsed_seconds: float = Field(default=0.0, ge=0.0, description="Cumulative query execution latency.")
    disambiguation_key: Optional[str] = Field(default=None, description="Deterministic entity isolation key.")
    parent_entity_anchor: Optional[str] = Field(default=None, description="Anchor entity from root/parent.")

    def get_node(self, node_id: str) -> Optional[QueryPlanNode]:
        """Finds node by ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_root_node(self) -> Optional[QueryPlanNode]:
        """Retrieves root query node (hop_depth == 0)."""
        for node in self.nodes:
            if node.hop_depth == 0 and node.parent_node_id is None:
                return node
        return None

    def get_active_node(self) -> Optional[QueryPlanNode]:
        """Retrieves current in-progress or first pending node."""
        for node in self.nodes:
            if node.status == NodeStatus.IN_PROGRESS:
                return node
        for node in self.nodes:
            if node.status == NodeStatus.PENDING:
                return node
        return None

    def get_children(self, parent_node_id: str) -> List[QueryPlanNode]:
        """Retrieves direct children nodes for a given parent node."""
        return [node for node in self.nodes if node.parent_node_id == parent_node_id]
