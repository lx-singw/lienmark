"""
tests/test_budget_governor_extended.py

Extended verification for ExecutionBudgetGovernor:
- Thread-safe concurrency under multi-threaded load
- Dual-import parity between budget_governor and execution_budget_governor
- Provider rate customizations and fallback behaviors
"""

import threading
import pytest
from backend.orchestration.budget_governor import (
    ExecutionBudgetGovernor,
    BudgetAuthorization,
    BudgetTrackingRecord,
    CostBreakdown,
    CachedEvidence,
    ProviderRate,
    ProviderName,
    BudgetExceededError,
    budget_governor as singleton_gov,
)
import backend.orchestration.execution_budget_governor as ebg_module


def test_concurrent_usage_recording():
    """Assert concurrent record_usage calls from multiple threads accumulate spend safely."""
    gov = ExecutionBudgetGovernor(default_max_run_spend_usd=100.0)
    run_id = "run_concurrent_test"
    gov.authorize_run(run_id=run_id, estimated_cost=0.1, run_budget_limit=100.0)

    num_threads = 10
    calls_per_thread = 10
    cost_per_call = 0.05

    def worker():
        for _ in range(calls_per_thread):
            gov.record_usage(
                run_id=run_id,
                provider="custom",
                tokens_prompt=0,
                tokens_completion=0,
                cost_usd=cost_per_call,
            )

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected_total = num_threads * calls_per_thread * cost_per_call
    assert gov.get_total_spent(run_id) == pytest.approx(expected_total, abs=1e-4)
    assert len(gov.get_records(run_id)) == (num_threads * calls_per_thread)


def test_dual_import_parity():
    """Verify execution_budget_governor exports all symbols from budget_governor."""
    assert hasattr(ebg_module, "ExecutionBudgetGovernor")
    assert hasattr(ebg_module, "BudgetAuthorization")
    assert hasattr(ebg_module, "BudgetTrackingRecord")
    assert hasattr(ebg_module, "CostBreakdown")
    assert hasattr(ebg_module, "CachedEvidence")
    assert hasattr(ebg_module, "ProviderRate")
    assert hasattr(ebg_module, "ProviderName")
    assert hasattr(ebg_module, "PAGE_RATE_USD")
    assert hasattr(ebg_module, "CLAIM_RATE_USD")
    assert hasattr(ebg_module, "budget_governor")
    assert hasattr(ebg_module, "init")

    assert ebg_module.ExecutionBudgetGovernor is ExecutionBudgetGovernor
    assert ebg_module.BudgetAuthorization is BudgetAuthorization
