"""
backend/agents/research/__init__.py

Research agent subsystem exports.
Sprint 3.1 & 3.2: Parallel Search Integration, Subgoals & Multi-Hop Planning DAG.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from backend.agents.research.discovery_handler import DiscoveryHandler
from backend.agents.research.discovery_types import (
    DiscoveryHandlerError,
    DiscoveryValidationError,
    ProposedClaimEvent,
    ProposedClaimNotFoundError,
    ProposedClaimStatus,
    SecondaryIPType,
)
from backend.agents.research.entity_extractor import EntityExtractor
from backend.agents.research.lead_types import (
    ExtractedLead,
    LeadEntityType,
    LeadRelationshipType,
)
from backend.agents.research.planner import InvestigationPlanner
from backend.agents.research.planner_types import (
    CycleDetectedError,
    FalseLeadRejectedError,
    InvestigationPlanDAG,
    InvestigationPlannerError,
    LatencyBudgetExceededError,
    MaxHopDepthExceededError,
    MaxQueryLimitReachedError,
    NodeStatus,
    QueryPlanNode,
    SubgoalStatus,
)
from backend.agents.research.query_builder import (
    InverseDomainSteeringEngine,
    StructuredQueryBuilder,
)
from backend.agents.research.query_types import (
    AssetClass,
    EntityDisambiguationError,
    EvidenceEvaluation,
    GeneratedQuery,
    InvalidAssetClassError,
    InvalidSteeringTransitionError,
    QueryBuilderError,
    SearchQueryRequest,
    SteeringState,
)
from backend.agents.research.result_sanitizer import (
    compute_finding_hash,
    sanitize_excerpt,
    sanitize_url,
    wrap_untrusted_evidence,
)
from backend.agents.research.subgoal_builders import (
    build_artwork_subgoals,
    build_brand_subgoals,
    build_footage_subgoals,
    build_generic_subgoals,
    build_music_subgoals,
    has_sample_or_remix_cues,
)
from backend.agents.research.subgoal_decomposer import (
    SubgoalDecomposer,
    assess_subgoal_readiness,
    decompose_claim_to_subgoals,
)
from backend.agents.research.subgoal_planner import SubgoalPlanner
from backend.agents.research.subgoal_types import (
    InvestigationSubgoal,
    ReadinessStatus,
    SubgoalDecompositionError,
    SubgoalPriority,
    SubgoalReadiness,
    SubgoalReadinessError,
    SubgoalType,
)

__all__ = [
    "AssetClass",
    "CycleDetectedError",
    "DiscoveryHandler",
    "DiscoveryHandlerError",
    "DiscoveryValidationError",
    "EntityDisambiguationError",
    "EntityExtractor",
    "EvidenceEvaluation",
    "ExtractedLead",
    "FalseLeadRejectedError",
    "GeneratedQuery",
    "InvalidAssetClassError",
    "InvalidSteeringTransitionError",
    "InverseDomainSteeringEngine",
    "InvestigationPlanDAG",
    "InvestigationPlanner",
    "InvestigationPlannerError",
    "InvestigationSubgoal",
    "LatencyBudgetExceededError",
    "LeadEntityType",
    "LeadRelationshipType",
    "MaxHopDepthExceededError",
    "MaxQueryLimitReachedError",
    "NodeStatus",
    "ProposedClaimEvent",
    "ProposedClaimNotFoundError",
    "ProposedClaimStatus",
    "QueryBuilderError",
    "QueryPlanNode",
    "ReadinessStatus",
    "SearchQueryRequest",
    "SecondaryIPType",
    "SteeringState",
    "StructuredQueryBuilder",
    "SubgoalDecomposer",
    "SubgoalDecompositionError",
    "SubgoalPlanner",
    "SubgoalPriority",
    "SubgoalReadiness",
    "SubgoalReadinessError",
    "SubgoalStatus",
    "SubgoalType",
    "assess_subgoal_readiness",
    "build_artwork_subgoals",
    "build_brand_subgoals",
    "build_footage_subgoals",
    "build_generic_subgoals",
    "build_music_subgoals",
    "compute_finding_hash",
    "decompose_claim_to_subgoals",
    "has_sample_or_remix_cues",
    "sanitize_excerpt",
    "sanitize_url",
    "wrap_untrusted_evidence",
]
