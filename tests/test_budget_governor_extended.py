"""
tests/test_budget_governor_extended.py

Extended verification for ExecutionBudgetGovernor:
- Thread-safe concurrency under multi-threaded load
- Dual-import parity between budget_governor and execution_budget_governor
- Two-phase reservation protocol, recovery, and invariant enforcement
- Zero-spend duplicate cache settlement and pricing helpers
"""

import threading
import pytest
from backend.domain.models import RunStatus
from backend.orchestration.budget_governor import (
    ExecutionBudgetGovernor,
    BudgetAuthorization,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetTrackingRecord,
    CostBreakdown,
    CachedEvidence,
    ProviderRate,
    ProviderName,
    ReservationStatus,
    BudgetExceededError,
    BudgetGovernorError,
    usd_to_micros,
    micros_to_usd,
    calculate_parallel_cost_micros,
    calculate_parallel_cost_usd,
    calculate_gemini_cost_micros,
    calculate_gemini_cost_usd,
    budget_governor as singleton_gov,
)
import backend.orchestration.execution_budget_governor as ebg_module


def test_concurrent_usage_recording():
    """Assert concurrent record_usage calls from multiple threads accumulate spend safely."""
    gov = ExecutionBudgetGovernor(default_max_run_spend_usd=100.0)
    run_id = "run_concurrent_test"
    gov.authorize_run(run_id=run_id, estimated_cost=0.1, run_budget_limit=100.0)

    num_threads, calls_per_thread, cost_per_call = 10, 10, 0.05

    def worker():
        for _ in range(calls_per_thread):
            gov.record_usage(run_id=run_id, provider="custom", tokens_prompt=0, tokens_completion=0, cost_usd=cost_per_call)

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads: t.start()
    for t in threads: t.join()

    expected_total = num_threads * calls_per_thread * cost_per_call
    assert gov.get_total_spent(run_id) == pytest.approx(expected_total, abs=1e-4)
    assert len(gov.get_records(run_id)) == (num_threads * calls_per_thread)


def test_dual_import_parity():
    """Verify execution_budget_governor exports all symbols from budget_governor."""
    for symbol in (
        "ExecutionBudgetGovernor", "BudgetStore", "BudgetAuthorization", "BudgetReservation",
        "BudgetSettlementRecord", "BudgetTrackingRecord", "CostBreakdown", "CachedEvidence",
        "ProviderRate", "ProviderName", "ReservationStatus", "PAGE_RATE_USD", "CLAIM_RATE_USD",
        "PAGE_RATE_MICROS", "CLAIM_RATE_MICROS", "PARALLEL_FAST_MICROS", "PARALLEL_BASIC_MICROS",
        "budget_governor", "usd_to_micros", "micros_to_usd", "init",
    ):
        assert hasattr(ebg_module, symbol), f"Missing symbol {symbol} in execution_budget_governor"
    assert ebg_module.ExecutionBudgetGovernor is ExecutionBudgetGovernor
    assert ebg_module.BudgetAuthorization is BudgetAuthorization


def test_micro_cent_conversions_and_pricing_helpers():
    """Validate µUSD conversions and pricing calculations for Parallel and Gemini."""
    assert usd_to_micros(1.0) == 1_000_000
    assert usd_to_micros(0.005) == 5_000
    assert micros_to_usd(1_000_000) == 1.0
    assert micros_to_usd(1_000) == 0.001

    assert calculate_parallel_cost_micros("fast") == 1_000
    assert calculate_parallel_cost_usd("fast") == 0.001
    assert calculate_parallel_cost_micros("basic") == 5_000
    assert calculate_parallel_cost_usd("basic") == 0.005

    # Gemini 1.5 Flash: 1000 prompt (75 µUSD) + 1000 completion (300 µUSD) = 375 µUSD
    assert calculate_gemini_cost_micros("gemini-1.5-flash", 1000, 1000) == 375
    assert calculate_gemini_cost_usd("gemini-1.5-flash", 1000, 1000) == 0.000375
    # Gemini 1.5 Pro: 1000 prompt (1250 µUSD) + 1000 completion (5000 µUSD) = 6250 µUSD
    assert calculate_gemini_cost_micros("gemini-1.5-pro", 1000, 1000) == 6250
    assert calculate_gemini_cost_usd("gemini-1.5-pro", 1000, 1000) == 0.00625


def test_two_phase_reservation_and_settlement_lifecycle():
    """Verify reserve -> external call -> settle workflow."""
    gov = ExecutionBudgetGovernor()
    gov.set_run_limit("run_proto_01", 1.0)

    res: BudgetReservation = gov.reserve(
        org_id="org_1", production_id="prod_1", run_id="run_proto_01", period_id="2026-09",
        action_id="act_01", provider="parallel_search", model_or_mode="fast", max_cost_micros=10_000,
    )
    assert res.status in (ReservationStatus.RESERVED, ReservationStatus.ACTIVE)
    assert gov.get_run_reserved_micros("run_proto_01") == 10_000

    record: BudgetSettlementRecord = gov.settle(
        reservation_id=res.reservation_id, actual_usage={"mode": "fast"}, provider_cost_micros=1_000,
    )
    assert record.settled_cost_micros == 1_000
    assert record.provider_cost_micros == 1_000
    assert gov.get_run_reserved_micros("run_proto_01") == 0
    assert gov.get_run_spend_micros("run_proto_01") == 1_000
    assert gov.get_total_spent("run_proto_01") == 0.001


def test_two_phase_recovery_on_provider_failure():
    """Verify recover releases reserved allocation upon provider invocation error."""
    gov = ExecutionBudgetGovernor()
    gov.set_run_limit("run_recov_01", 1.0)

    res = gov.reserve(
        org_id="org_1", production_id="prod_1", run_id="run_recov_01", period_id="2026-09",
        action_id="act_fail", provider="gemini-1.5-pro", model_or_mode="pro", max_cost_micros=20_000,
    )
    assert gov.get_run_reserved_micros("run_recov_01") == 20_000

    gov.recover(res.reservation_id, error_reason="503 Service Unavailable")
    assert gov.get_run_reserved_micros("run_recov_01") == 0
    assert gov.get_run_spend_micros("run_recov_01") == 0


def test_invariant_spend_plus_reservations_le_limit():
    """Assert settled_spend + outstanding_reservations <= budget_limit_micros."""
    gov = ExecutionBudgetGovernor()
    gov.set_run_limit("run_inv_01", 0.010)  # 10,000 µUSD limit

    res1 = gov.reserve("o", "p", "run_inv_01", "per", "a1", "parallel", "fast", 6_000)
    assert res1.max_cost_micros == 6_000

    with pytest.raises(BudgetExceededError):
        gov.reserve("o", "p", "run_inv_01", "per", "a2", "parallel", "fast", 5_000)

    gov.settle(res1.reservation_id, {}, provider_cost_micros=4_000)
    assert gov.get_run_spend_micros("run_inv_01") == 4_000
    assert gov.get_run_reserved_micros("run_inv_01") == 0

    res2 = gov.reserve("o", "p", "run_inv_01", "per", "a3", "parallel", "fast", 5_000)
    assert res2.max_cost_micros == 5_000

    with pytest.raises(BudgetExceededError):
        gov.reserve("o", "p", "run_inv_01", "per", "a4", "parallel", "fast", 2_000)


def test_zero_spend_duplicate_cache_in_settlement():
    """Assert settlement with cache_hit=True records strictly 0 provider cost."""
    gov = ExecutionBudgetGovernor()
    gov.set_run_limit("run_cache_01", 0.50)

    res = gov.reserve("o", "p", "run_cache_01", "per", "a1", "parallel", "basic", 5_000)
    settlement = gov.settle(
        res.reservation_id, actual_usage={"cached_key": "hit"}, provider_cost_micros=5_000, cache_hit=True,
    )
    assert settlement.provider_cost_micros == 0
    assert settlement.settled_cost_micros == 0
    assert settlement.cache_hit is True
    assert gov.get_total_spent("run_cache_01") == 0.0


def test_mid_flight_cap_four_arg_signature():
    """Verify check_mid_flight_cap with (org_id, production_id, period_id, run_id)."""
    gov = ExecutionBudgetGovernor()
    gov.set_run_limit("run_cap_4", 0.010)

    assert gov.check_mid_flight_cap("org1", "prod1", "per1", "run_cap_4") is True
    res = gov.reserve("org1", "prod1", "run_cap_4", "per1", "a1", "parallel", "basic", 5_000)
    gov.settle(res.reservation_id, {}, provider_cost_micros=10_000)

    assert gov.check_mid_flight_cap("org1", "prod1", "per1", "run_cap_4") is False
    assert gov.get_run_status("run_cap_4") == RunStatus.WAITING_FOR_BUDGET
