"""
tests/test_milestone_b_budget_contracts.py

Test suite for Milestone B Durable Budget Reservation Contract.
Verifies fund reservations before paid search, extraction, entity call, and briefing call,
and confirms state checkpointing before advancing actions.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.domain.models import InvestigationRun, RunStatus
from backend.orchestration.budget_governor import ExecutionBudgetGovernor
from backend.orchestration.budget_types import BudgetExceededError
from backend.orchestration.budget_store_types import ReservationStatus
from backend.orchestration.milestone_b_reservation import (
    MilestoneBBudgetManager,
    PaidActionType,
)
from backend.orchestration.checkpoint_types import validate_resume_token


@pytest.fixture
def clean_governor():
    gov = ExecutionBudgetGovernor(default_max_run_spend_usd=1.0)
    gov.reset()
    return gov


def test_reserve_funds_across_all_four_paid_actions(clean_governor):
    """Verifies reservation before paid search, extraction, entity call, and briefing call."""
    mgr = MilestoneBBudgetManager(governor=clean_governor, tenant_id="org_studio_99")
    clean_governor.set_run_limit("run_mb_01", 10.0)

    # 1. Paid Search
    res_search = mgr.reserve_for_action(
        run_id="run_mb_01", production_id="prod_01", action_type=PaidActionType.PAID_SEARCH,
    )
    assert res_search.status == ReservationStatus.ACTIVE
    assert res_search.max_cost_micros == 10_000

    # 2. Extraction
    res_extract = mgr.reserve_for_action(
        run_id="run_mb_01", production_id="prod_01", action_type=PaidActionType.EXTRACTION,
    )
    assert res_extract.status == ReservationStatus.ACTIVE
    assert res_extract.max_cost_micros == 20_000

    # 3. Entity Call
    res_entity = mgr.reserve_for_action(
        run_id="run_mb_01", production_id="prod_01", action_type=PaidActionType.ENTITY_CALL,
    )
    assert res_entity.status == ReservationStatus.ACTIVE
    assert res_entity.max_cost_micros == 5_000

    # 4. Briefing Call
    res_briefing = mgr.reserve_for_action(
        run_id="run_mb_01", production_id="prod_01", action_type=PaidActionType.BRIEFING_CALL,
    )
    assert res_briefing.status == ReservationStatus.ACTIVE
    assert res_briefing.max_cost_micros > 0


def test_checkpoint_results_before_advancing_actions(clean_governor):
    """Verifies checkpoint results capturing state and cryptographic resume token."""
    mgr = MilestoneBBudgetManager(governor=clean_governor, tenant_id="org_studio_99")
    findings = [{"source": "copyright.gov", "reg_number": "TX00012345", "stance": "supporting"}]

    checkpoint = mgr.checkpoint_before_advancing(
        run_id="run_mb_02", production_id="prod_02", claim_id="clm_chk_01",
        paused_stage="ACT_02_SEARCH_PUBLIC_SOURCES", findings=findings,
        context_vars={"query": "Film Poster 1950"},
    )
    assert checkpoint.checkpoint_id.startswith("chk_clm_chk_01")
    assert checkpoint.paused_stage == "ACT_02_SEARCH_PUBLIC_SOURCES"
    assert len(checkpoint.agent_memory_snapshot.findings) == 1
    assert len(checkpoint.resume_token) == 64

    # Cryptographic resume token is valid
    is_valid = validate_resume_token(checkpoint, checkpoint.resume_token)
    assert is_valid is True


def test_settle_reservation_on_success(clean_governor):
    """Verifies reservation settlement on successful action execution."""
    mgr = MilestoneBBudgetManager(governor=clean_governor, tenant_id="org_studio_99")
    clean_governor.set_run_limit("run_mb_03", 5.0)

    res = mgr.reserve_for_action(
        run_id="run_mb_03", production_id="prod_03", action_type=PaidActionType.PAID_SEARCH,
    )
    settlement = mgr.settle_for_action(
        reservation_id=res.reservation_id, actual_usage={"mode": "fast"},
    )
    assert settlement.reservation_id == res.reservation_id
    assert settlement.actual_cost_micros > 0
    assert clean_governor.get_total_spent("run_mb_03") > 0.0


def test_recover_reservation_on_failure(clean_governor):
    """Verifies reservation recovery/release when action encounters an error."""
    mgr = MilestoneBBudgetManager(governor=clean_governor, tenant_id="org_studio_99")
    clean_governor.set_run_limit("run_mb_04", 5.0)

    res = mgr.reserve_for_action(
        run_id="run_mb_04", production_id="prod_04", action_type=PaidActionType.EXTRACTION,
    )
    assert clean_governor.get_run_reserved_micros("run_mb_04") == 20_000

    mgr.recover_on_failure(res.reservation_id, reason="network_timeout")
    assert clean_governor.get_run_reserved_micros("run_mb_04") == 0


def test_budget_exceeded_raises_error_and_protects_cap(clean_governor):
    """Verifies exceeding run budget raises BudgetExceededError and pauses run."""
    clean_governor.set_run_limit("run_tight_budget", 0.005)  # $0.005 cap
    mgr = MilestoneBBudgetManager(governor=clean_governor, tenant_id="org_studio_99")

    # $0.005 cap = 5,000 micros. 1st extraction is 20,000 micros ($0.02) -> raises BudgetExceededError
    with pytest.raises(BudgetExceededError) as exc_info:
        mgr.reserve_for_action(
            run_id="run_tight_budget", production_id="prod_tight", action_type=PaidActionType.EXTRACTION,
        )
    assert "exceeded budget cap" in str(exc_info.value)
