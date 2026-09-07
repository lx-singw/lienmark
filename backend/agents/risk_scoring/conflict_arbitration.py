"""
backend/agents/risk_scoring/conflict_arbitration.py

Lienmark Risk Scoring Agent - Multi-Source Conflict Arbitration Module.
Sprint 3.3 / Milestone C integration: bridges agentic risk scoring
with backend/core/conflict_arbiter.
"""

from backend.core.conflict_arbiter import (
    ConflictArbiter,
    CorroborationEngine,
    arbitrate_claim_conflicts,
)
from backend.core.conflict_types import (
    ArbitrationResult,
    ClaimStatusAssertion,
    ConflictStance,
    DualLayerConflictInfo,
    EvidenceFinding,
    RightsLayer,
    SourceAuthorityTier,
    StancePairEvaluation,
)

__all__ = [
    "ConflictArbiter",
    "CorroborationEngine",
    "arbitrate_claim_conflicts",
    "ArbitrationResult",
    "ClaimStatusAssertion",
    "ConflictStance",
    "DualLayerConflictInfo",
    "EvidenceFinding",
    "RightsLayer",
    "SourceAuthorityTier",
    "StancePairEvaluation",
]
