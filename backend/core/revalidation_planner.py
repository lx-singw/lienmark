"""
Lienmark Targeted Revalidation & Reconciliation Module
Re-exports RevalidationPlanner, EvidenceReconciler, and models for core consumption.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from backend.services.revalidation_planner import (
    RevalidationPlanner,
    ResearchPlanner,
    MinimalBudgetViolationError,
)
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.domain.models import (
    PlannedRevalidationRequest,
    RevalidationPlan,
    EvidenceReconciliationResult,
    EvidenceStance,
)

# Semantic aliases for interoperability
RevalidationSearchRequest = PlannedRevalidationRequest
ReconciliationEngine = EvidenceReconciler
EvidenceStanceCategorizer = EvidenceReconciler
ReconciliationResult = EvidenceReconciliationResult

__all__ = [
    "RevalidationPlanner",
    "ResearchPlanner",
    "MinimalBudgetViolationError",
    "EvidenceReconciler",
    "ReconciliationEngine",
    "EvidenceStanceCategorizer",
    "PlannedRevalidationRequest",
    "RevalidationSearchRequest",
    "RevalidationPlan",
    "EvidenceReconciliationResult",
    "ReconciliationResult",
    "EvidenceStance",
]
