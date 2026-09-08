"""
tests/test_budget_store_local.py

Comprehensive test suite for LocalBudgetStore:
File-locked JSON persistence, thread-safety, budget caps, settlement, and expiration.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import concurrent.futures
import os
import shutil
import tempfile
import pytest

from backend.orchestration.budget_store_local import LocalBudgetStore
from backend.orchestration.budget_store_types import (
    BudgetExceededError,
    BudgetStoreError,
    ReservationNotFoundError,
    ReservationStatus,
)


@pytest.fixture
def local_store():
    """Provides an isolated temporary LocalBudgetStore instance."""
    temp_dir = tempfile.mkdtemp(prefix="budget_test_")
    store = LocalBudgetStore(base_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_reserve_and_settle(local_store):
    """Verifies standard lifecycle: reserve budget, settle expenditure, update summary."""
    local_store.set_budget_limit("org_warner", "prod_batman", "period_q3", 100_000)
    res = local_store.reserve_budget(
        "org_warner", "prod_batman", "period_q3", "run_1", "act_gemini",
        "gemini-1.5-pro", "pro", 20_000, expires_in_seconds=300,
    )
    assert res.reservation_id.startswith("res_")
    assert res.max_cost_micros == 20_000
    assert res.status == ReservationStatus.ACTIVE

    summary1 = local_store.get_summary("org_warner", "prod_batman", "period_q3")
    assert summary1.outstanding_reservations_micros == 20_000
    assert summary1.settled_spend_micros == 0

    settlement = local_store.settle_reservation(
        res.reservation_id, actual_cost_micros=15_000, usage_measurements={"tokens": 3000},
    )
    assert settlement.actual_cost_micros == 15_000
    assert settlement.reservation_id == res.reservation_id

    summary2 = local_store.get_summary("org_warner", "prod_batman", "period_q3")
    assert summary2.outstanding_reservations_micros == 0
    assert summary2.settled_spend_micros == 15_000


def test_budget_limit_exceeded(local_store):
    """Verifies that reserving spend exceeding configured limit raises BudgetExceededError."""
    local_store.set_budget_limit("org_a24", "prod_midsommar", "period_q3", 50_000)

    # First reservation succeeds (40,000 / 50,000)
    local_store.reserve_budget(
        "org_a24", "prod_midsommar", "period_q3", "run_1", "act_1",
        "gemini", "pro", 40_000,
    )

    # Second reservation exceeds limit (40,000 + 15,000 = 55,000 > 50,000)
    with pytest.raises(BudgetExceededError) as exc_info:
        local_store.reserve_budget(
            "org_a24", "prod_midsommar", "period_q3", "run_1", "act_2",
            "gemini", "pro", 15_000,
        )
    assert exc_info.value.period_id == "period_q3"
    assert exc_info.value.limit_micros == 50_000


def test_settle_errors(local_store):
    """Verifies error handling when settling nonexistent or already settled reservation."""
    with pytest.raises(ReservationNotFoundError):
        local_store.settle_reservation("res_nonexistent", 5000, {})

    res = local_store.reserve_budget(
        "org_mgm", "prod_bond", "period_1", "run_1", "act_1", "gemini", "pro", 10_000
    )
    local_store.settle_reservation(res.reservation_id, 8000, {})

    with pytest.raises(BudgetStoreError) as exc_info:
        local_store.settle_reservation(res.reservation_id, 8000, {})
    assert "already settled" in str(exc_info.value)


def test_recover_reservation(local_store):
    """Verifies recovering an abandoned reservation releases held outstanding budget."""
    local_store.set_budget_limit("org_neon", "prod_parasite", "period_q4", 100_000)
    res = local_store.reserve_budget(
        "org_neon", "prod_parasite", "period_q4", "run_1", "act_fail",
        "parallel", "basic", 30_000,
    )

    summary1 = local_store.get_summary("org_neon", "prod_parasite", "period_q4")
    assert summary1.outstanding_reservations_micros == 30_000

    local_store.recover_reservation(res.reservation_id, status=ReservationStatus.UNCERTAIN)

    summary2 = local_store.get_summary("org_neon", "prod_parasite", "period_q4")
    assert summary2.outstanding_reservations_micros == 0
    assert summary2.settled_spend_micros == 0

    reservations = local_store.list_reservations("org_neon", "prod_parasite", "period_q4", status=ReservationStatus.UNCERTAIN)
    assert len(reservations) == 1
    assert reservations[0].status == ReservationStatus.UNCERTAIN


def test_reservation_expiration_lifecycle(local_store):
    """Verifies that expired reservations release budget automatically upon next evaluation."""
    local_store.set_budget_limit("org_fox", "prod_avatar", "period_1", 20_000)
    # Reservation with 0 second TTL expires immediately
    res = local_store.reserve_budget(
        "org_fox", "prod_avatar", "period_1", "run_1", "act_exp",
        "gemini", "flash", 15_000, expires_in_seconds=-1,
    )

    summary = local_store.get_summary("org_fox", "prod_avatar", "period_1")
    assert summary.outstanding_reservations_micros == 0

    res_list = local_store.list_reservations("org_fox", "prod_avatar", "period_1", status=ReservationStatus.EXPIRED)
    assert len(res_list) == 1
    assert res_list[0].reservation_id == res.reservation_id


def test_concurrent_reservations_thread_safety(local_store):
    """Verifies multi-threaded reservation concurrency safety under internal locks."""
    local_store.set_budget_limit("org_columbia", "prod_spiderman", "period_concurrency", 500_000)
    num_threads = 10
    cost_per_thread = 5_000

    def _worker(idx: int):
        return local_store.reserve_budget(
            "org_columbia", "prod_spiderman", "period_concurrency",
            f"run_{idx}", f"act_{idx}", "gemini", "pro", cost_per_thread,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(_worker, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads
    summary = local_store.get_summary("org_columbia", "prod_spiderman", "period_concurrency")
    assert summary.outstanding_reservations_micros == num_threads * cost_per_thread

    all_reservations = local_store.list_reservations("org_columbia", "prod_spiderman", "period_concurrency")
    assert len(all_reservations) == num_threads


def test_reset_and_clean(local_store):
    """Verifies that reset clears the storage directory and cached indexes."""
    local_store.reserve_budget(
        "org_test", "prod_test", "period_test", "run_test", "act_test",
        "gemini", "pro", 10_000,
    )
    assert os.path.exists(local_store._base_dir)
    local_store.reset()
    assert not os.path.exists(local_store._base_dir) or len(os.listdir(local_store._base_dir)) == 0
