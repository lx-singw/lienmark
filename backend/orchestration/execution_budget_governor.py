"""
Lienmark Execution Budget Governor Alias Module.
Re-exports ExecutionBudgetGovernor and all canonical domain models for dual-import compliance.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from backend.orchestration.budget_types import (
    BudgetAuthorization,
    BudgetExceededError,
    BudgetGovernorError,
    BudgetTrackingRecord,
    CachedEvidence,
    CostBreakdown,
    DEFAULT_PROVIDER_RATES,
    ProviderName,
    ProviderRate,
    normalize_provider_name,
)
from backend.orchestration.budget_governor import (
    CLAIM_RATE_USD,
    PAGE_RATE_USD,
    ExecutionBudgetGovernor,
    budget_governor,
)

__all__ = [
    "ExecutionBudgetGovernor",
    "BudgetAuthorization",
    "BudgetTrackingRecord",
    "CostBreakdown",
    "CachedEvidence",
    "ProviderRate",
    "ProviderName",
    "BudgetExceededError",
    "BudgetGovernorError",
    "DEFAULT_PROVIDER_RATES",
    "PAGE_RATE_USD",
    "CLAIM_RATE_USD",
    "budget_governor",
    "normalize_provider_name",
    "init",
]


def init() -> None:
    """Module initialization hook for backwards compatibility."""
    pass
