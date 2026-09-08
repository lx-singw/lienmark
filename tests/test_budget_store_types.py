"""
tests/test_budget_store_types.py

Tests for budget store domain types, enums, pricing constants, models, and exceptions.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from backend.orchestration.budget_store_types import (
    GEMINI_COMPLETION_MICROS_PER_TOKEN,
    GEMINI_PROMPT_MICROS_PER_TOKEN,
    MICROS_PER_USD,
    PARALLEL_BASIC_MICROS,
    PARALLEL_FAST_MICROS,
    BudgetExceededError,
    BudgetPeriodSummary,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetStoreError,
    ReservationNotFoundError,
    ReservationStatus,
    is_reservation_expired,
    parse_utc_timestamp,
    utc_now_iso,
)


def test_pricing_constants():
    """Validates required micro-cent pricing constants."""
    assert MICROS_PER_USD == 1_000_000
    assert PARALLEL_FAST_MICROS == 1_000
    assert PARALLEL_BASIC_MICROS == 5_000
    assert GEMINI_PROMPT_MICROS_PER_TOKEN == 1.25
    assert GEMINI_COMPLETION_MICROS_PER_TOKEN == 5.0


def test_reservation_status_enum():
    """Validates all canonical reservation status values."""
    assert ReservationStatus.ACTIVE == "active"
    assert ReservationStatus.SETTLED == "settled"
    assert ReservationStatus.RELEASED == "released"
    assert ReservationStatus.UNCERTAIN == "uncertain"
    assert ReservationStatus.EXPIRED == "expired"


def test_budget_reservation_model():
    """Validates BudgetReservation Pydantic model validation and serialization."""
    now_iso = utc_now_iso()
    res = BudgetReservation(
        reservation_id="res_test123",
        action_id="act_clearance_search",
        org_id="org_paramount",
        production_id="prod_topgun",
        budget_period_id="period_2026_q3",
        run_id="run_001",
        provider="gemini",
        model_or_mode="pro",
        max_cost_micros=15_000,
        status=ReservationStatus.ACTIVE,
        created_at_utc=now_iso,
        expires_at_utc=now_iso,
    )
    assert res.reservation_id == "res_test123"
    assert res.max_cost_micros == 15_000
    assert res.status == ReservationStatus.ACTIVE
    dumped = res.model_dump()
    assert dumped["action_id"] == "act_clearance_search"

    # Validation errors
    with pytest.raises(ValidationError):
        BudgetReservation.model_validate({"reservation_id": ""})


def test_budget_settlement_record_model():
    """Validates BudgetSettlementRecord model fields and defaults."""
    now_iso = utc_now_iso()
    record = BudgetSettlementRecord(
        settlement_id="stl_abc456",
        reservation_id="res_test123",
        actual_cost_micros=12_500,
        usage_measurements={"tokens_prompt": 1000, "tokens_completion": 200},
        provider_confirmed_cost_micros=12_500,
        cache_hit=False,
        settled_at_utc=now_iso,
    )
    assert record.actual_cost_micros == 12_500
    assert record.cache_hit is False
    assert record.provider_confirmed_cost_micros == 12_500


def test_budget_period_summary_model():
    """Validates BudgetPeriodSummary model calculation fields."""
    summary = BudgetPeriodSummary(
        org_id="org_universal",
        production_id="prod_oppenheimer",
        budget_period_id="q3_2026",
        budget_limit_micros=50_000_000,
        settled_spend_micros=10_000_000,
        outstanding_reservations_micros=5_000_000,
        updated_at_utc=utc_now_iso(),
    )
    assert summary.budget_limit_micros == 50_000_000
    assert summary.settled_spend_micros == 10_000_000
    assert summary.outstanding_reservations_micros == 5_000_000


def test_budget_exceptions():
    """Validates inheritance and attributes of domain exceptions."""
    assert issubclass(BudgetExceededError, BudgetStoreError)
    assert issubclass(ReservationNotFoundError, BudgetStoreError)

    ex = BudgetExceededError("Spend exceeded cap", period_id="p1", current_spend_micros=150, limit_micros=100)
    assert ex.period_id == "p1"
    assert ex.current_spend_micros == 150
    assert ex.limit_micros == 100
    assert "Spend exceeded cap" in str(ex)

    rnf = ReservationNotFoundError("res_999")
    assert rnf.reservation_id == "res_999"
    assert "res_999" in str(rnf)


def test_timestamp_and_expiration_helpers():
    """Validates utc_now_iso, parse_utc_timestamp, and is_reservation_expired."""
    ts = utc_now_iso()
    dt = parse_utc_timestamp(ts)
    assert dt.tzinfo is not None

    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    assert is_reservation_expired(past) is True
    assert is_reservation_expired(future) is False
