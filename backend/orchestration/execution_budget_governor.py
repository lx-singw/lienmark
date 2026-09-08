"""
Lienmark Execution Budget Governor Alias Module.
Re-exports ExecutionBudgetGovernor and all canonical domain models for dual-import compliance.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from backend.orchestration.budget_types import (
    CLAIM_RATE_MICROS,
    CLAIM_RATE_USD,
    DEFAULT_PROVIDER_RATES,
    MICROS_PER_USD,
    PAGE_RATE_MICROS,
    PAGE_RATE_USD,
    PARALLEL_BASIC_MICROS,
    PARALLEL_FAST_MICROS,
    BudgetAuthorization,
    BudgetExceededError,
    BudgetGovernorError,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetTrackingRecord,
    CachedEvidence,
    CostBreakdown,
    DuplicateQueryCache,
    ProviderName,
    ProviderRate,
    ReservationStatus,
    calculate_gemini_cost_micros,
    calculate_gemini_cost_usd,
    calculate_parallel_cost_micros,
    calculate_parallel_cost_usd,
    micros_to_usd,
    normalize_provider_name,
    usd_to_micros,
)
from backend.orchestration.budget_store import BudgetStore
from backend.orchestration.budget_governor import (
    ExecutionBudgetGovernor,
    budget_governor,
)

__all__ = [
    "ExecutionBudgetGovernor",
    "BudgetStore",
    "BudgetAuthorization",
    "BudgetReservation",
    "BudgetSettlementRecord",
    "BudgetTrackingRecord",
    "CostBreakdown",
    "CachedEvidence",
    "DuplicateQueryCache",
    "ProviderRate",
    "ProviderName",
    "ReservationStatus",
    "BudgetExceededError",
    "BudgetGovernorError",
    "DEFAULT_PROVIDER_RATES",
    "PAGE_RATE_USD",
    "CLAIM_RATE_USD",
    "PAGE_RATE_MICROS",
    "CLAIM_RATE_MICROS",
    "PARALLEL_FAST_MICROS",
    "PARALLEL_BASIC_MICROS",
    "MICROS_PER_USD",
    "calculate_gemini_cost_micros",
    "calculate_gemini_cost_usd",
    "calculate_parallel_cost_micros",
    "calculate_parallel_cost_usd",
    "micros_to_usd",
    "usd_to_micros",
    "budget_governor",
    "normalize_provider_name",
    "init",
]


def init() -> None:
    """Module initialization hook for backwards compatibility."""
    pass
