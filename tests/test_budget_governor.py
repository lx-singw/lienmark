"""
tests/test_budget_governor.py

Automated Test Suite for Sprint 1.3 ExecutionBudgetGovernor.
Verifies pre-flight cost estimation, hard spend caps, mid-flight halting,
partial findings preservation, and zero-spend cache resolution.
"""

from __future__ import annotations

import pytest
from typing import Any, Dict, List

from backend.domain.models import RunStatus, InvestigationRun
from backend.orchestration.budget_types import (
    BudgetAuthorization,
    CostBreakdown,
    BudgetTrackingRecord,
    CachedEvidence,
    ProviderName,
)
from backend.orchestration.execution_budget_governor import (
    ExecutionBudgetGovernor,
    PAGE_RATE_USD,
    CLAIM_RATE_USD,
)


@pytest.fixture
def governor() -> ExecutionBudgetGovernor:
    """Provides a fresh, isolated ExecutionBudgetGovernor instance."""
    gov = ExecutionBudgetGovernor(
        default_max_run_spend_usd=50.0,
        default_max_production_spend_usd=500.0,
    )
    gov.reset()
    return gov


@pytest.fixture
def sample_run() -> InvestigationRun:
    """Constructs a valid InvestigationRun domain entity."""
    return InvestigationRun(
        run_id="run_gov_test_001",
        organization_id="org_studio_alpha",
        production_id="prod_noir_001",
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.INVESTIGATING,
        budget_spent_usd=0.0,
    )


class TestPreFlightCostEstimation:
    """Validates pre-flight estimation: (Page Count * 0.015) + (Estimated Claims * 0.04)."""

    def test_preflight_estimation_formula_exact_values(self, governor: ExecutionBudgetGovernor) -> None:
        assert governor.estimate_preflight_cost(0, 0) == 0.0
        # 100 pages ($1.50) + 10 claims ($0.40) = $1.90
        assert governor.estimate_preflight_cost(100, 10) == 1.90
        # 120 pages ($1.80) + 25 claims ($1.00) = $2.80
        assert governor.estimate_preflight_cost(120, 25) == 2.80
        # Constants verification
        assert PAGE_RATE_USD == 0.015
        assert CLAIM_RATE_USD == 0.040

    def test_preflight_estimation_negative_input_rejection(self, governor: ExecutionBudgetGovernor) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            governor.estimate_preflight_cost(-1, 10)
        with pytest.raises(ValueError, match="non-negative"):
            governor.estimate_preflight_cost(100, -5)

    def test_preflight_cost_breakdown_itemization(self, governor: ExecutionBudgetGovernor) -> None:
        breakdown: CostBreakdown = governor.get_preflight_breakdown(page_count=150, estimated_claims=30)
        assert breakdown.page_count == 150
        assert breakdown.estimated_claims == 30
        assert breakdown.page_cost_usd == 2.25
        assert breakdown.claims_cost_usd == 1.20
        assert breakdown.total_estimated_usd == 3.45


class TestRunAuthorizationAndBudgetBreach:
    """Validates authorizing runs within budget vs exceeding budget limits."""

    def test_authorize_run_within_budget(self, governor: ExecutionBudgetGovernor) -> None:
        auth: BudgetAuthorization = governor.authorize_run(
            run_id="run_auth_pass",
            estimated_cost=2.80,
            run_budget_limit=10.00,
            production_id="prod_test",
        )
        assert auth.authorized is True
        assert auth.estimated_cost == 2.80
        assert auth.allocated_budget == 10.00
        assert auth.remaining_budget == 10.00

    def test_authorize_run_exceeding_budget_halts_to_waiting_for_budget(
        self, governor: ExecutionBudgetGovernor
    ) -> None:
        auth: BudgetAuthorization = governor.authorize_run(
            run_id="run_auth_fail",
            estimated_cost=15.00,
            run_budget_limit=10.00,
            production_id="prod_test",
        )
        assert auth.authorized is False
        assert "exceeds remaining" in auth.reason
        assert governor.get_run_status("run_auth_fail") == RunStatus.WAITING_FOR_BUDGET

    def test_authorize_run_exceeding_production_cap(self, governor: ExecutionBudgetGovernor) -> None:
        governor.set_production_limit("prod_cap_exceeded", 5.00)
        governor.authorize_run("run_prior", 4.50, run_budget_limit=10.00, production_id="prod_cap_exceeded")
        governor.record_usage("run_prior", "parallel_search", 0, 0, cost_usd=4.50)

        # Next run needs $2.00, exceeding $5.00 production limit ($4.50 spent + $2.00 > $5.00)
        auth: BudgetAuthorization = governor.authorize_run(
            run_id="run_next",
            estimated_cost=2.00,
            run_budget_limit=10.00,
            production_id="prod_cap_exceeded",
        )
        assert auth.authorized is False
        assert "production cap" in auth.reason
        assert governor.get_run_status("run_next") == RunStatus.WAITING_FOR_BUDGET

    def test_authorize_run_empty_id_raises_value_error(self, governor: ExecutionBudgetGovernor) -> None:
        with pytest.raises(ValueError, match="run_id must be a non-empty string"):
            governor.authorize_run("", estimated_cost=1.0)


class TestMidFlightSpendTracking:
    """Validates live provider token and API call expenditure accounting."""

    def test_record_usage_providers_and_cost_calculation(self, governor: ExecutionBudgetGovernor) -> None:
        rec_gemini: BudgetTrackingRecord = governor.record_usage(
            run_id="run_mid_01",
            provider="gemini-1.5-pro",
            tokens_prompt=1000,
            tokens_completion=500,
        )
        assert rec_gemini.cost_usd > 0.0
        assert rec_gemini.provider == ProviderName.GEMINI_1_5_PRO.value

        rec_parallel: BudgetTrackingRecord = governor.record_usage(
            run_id="run_mid_01",
            provider="parallel_search",
            tokens_prompt=0,
            tokens_completion=0,
            cost_usd=0.15,
        )
        assert rec_parallel.cost_usd == 0.15
        assert governor.get_total_spent("run_mid_01") == round(rec_gemini.cost_usd + 0.15, 6)


class TestHardSpendLimitHaltingAndPartialFindings:
    """Validates clean transition to WAITING_FOR_BUDGET preserving partial findings."""

    def test_hard_spend_limit_0_05_milestone_a_halting(
        self, governor: ExecutionBudgetGovernor, sample_run: InvestigationRun
    ) -> None:
        governor.authorize_run(sample_run.run_id, estimated_cost=0.04, run_budget_limit=0.05)
        # 1st claim cost $0.03 (under $0.05 cap)
        allowed_1 = governor.check_mid_flight_cap(sample_run.run_id, sample_run)
        assert allowed_1 is True
        governor.record_usage(sample_run.run_id, "parallel_search", 0, 0, cost_usd=0.03)

        # 2nd claim cost $0.03 ($0.06 total > $0.05 cap)
        governor.record_usage(sample_run.run_id, "parallel_search", 0, 0, cost_usd=0.03)
        allowed_2 = governor.check_mid_flight_cap(sample_run.run_id, sample_run)
        assert allowed_2 is False
        assert governor.get_run_status(sample_run.run_id) == RunStatus.WAITING_FOR_BUDGET
        assert sample_run.status == RunStatus.WAITING_FOR_BUDGET

    def test_partial_findings_preservation_no_synthetic_completion(
        self, governor: ExecutionBudgetGovernor, sample_run: InvestigationRun
    ) -> None:
        governor.authorize_run(sample_run.run_id, estimated_cost=0.04, run_budget_limit=0.05)
        governor.record_usage(sample_run.run_id, "parallel_search", 0, 0, cost_usd=0.06)

        partial_data = [
            {"claim_id": "c1", "status": "cleared", "source": "Parallel Search"},
            {"claim_id": "c2", "status": "conflict", "source": "LOC Database"},
        ]
        result: Dict[str, Any] = governor.pause_run_for_budget(
            run_id=sample_run.run_id,
            partial_findings=partial_data,
            run=sample_run,
        )
        assert result["synthetic_completion"] is False
        assert result["status"] == RunStatus.WAITING_FOR_BUDGET.value
        assert result["partial_findings_count"] == 2
        assert result["partial_findings"] == partial_data
        assert governor.get_partial_findings(sample_run.run_id) == partial_data
        assert sample_run.status == RunStatus.WAITING_FOR_BUDGET


class TestCacheResolutionZeroSpend:
    """Validates that identical duplicate queries return cached evidence with $0.00 spend."""

    def test_identical_duplicate_query_zero_spend(self, governor: ExecutionBudgetGovernor) -> None:
        query = "ASCAP Midnight Serenade Title Search"
        mock_result = {"status": "ACTIVE_RIGHTSHOLDER", "publisher": "Vanguard Media"}
        governor.cache_query_result(query, mock_result)

        cached = governor.check_duplicate_cache(query)
        assert cached is not None
        assert cached["cost_usd"] == 0.0
        assert cached["is_cached"] is True
        assert cached["publisher"] == "Vanguard Media"

        # Record usage with the cached query ensures $0.00 expenditure
        rec = governor.record_usage(
            run_id="run_cached_01",
            provider="parallel_search",
            tokens_prompt=500,
            tokens_completion=200,
            query=query,
        )
        assert rec.is_cached is True
        assert rec.cost_usd == 0.0
        assert governor.get_total_spent("run_cached_01") == 0.0

    def test_cache_query_normalization_case_and_whitespace(self, governor: ExecutionBudgetGovernor) -> None:
        governor.cache_query_result("  Loc Copyright Poster Noir  ", {"doc_id": "loc_123"})
        hit = governor.check_duplicate_cache("loc copyright poster noir")
        assert hit is not None
        assert hit["doc_id"] == "loc_123"
        assert hit["cost_usd"] == 0.0
