"""
backend/agents/research/__init__.py

Research agent subsystem exports.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

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

__all__ = [
    "AssetClass",
    "EntityDisambiguationError",
    "EvidenceEvaluation",
    "GeneratedQuery",
    "InvalidAssetClassError",
    "InvalidSteeringTransitionError",
    "InverseDomainSteeringEngine",
    "QueryBuilderError",
    "SearchQueryRequest",
    "SteeringState",
    "StructuredQueryBuilder",
    "compute_finding_hash",
    "sanitize_excerpt",
    "sanitize_url",
    "wrap_untrusted_evidence",
]
