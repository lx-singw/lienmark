"""
Lienmark Execution Budget Governor Subsystem.
Enforces hard spend caps per run/production, pre-flight estimation, and fail-closed state pausing.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import copy
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.domain.models import RunStatus, InvestigationRun
from backend.core.lifecycle import transition_run
from backend.orchestration.budget_types import (
    CLAIM_RATE_USD,
    DEFAULT_PROVIDER_RATES,
    PAGE_RATE_USD,
    BudgetAuthorization,
    BudgetExceededError,
    BudgetGovernorError,
    BudgetTrackingRecord,
    CachedEvidence,
    CostBreakdown,
    DuplicateQueryCache,
    ProviderName,
    ProviderRate,
    normalize_provider_name,
)

logger = logging.getLogger("lienmark.orchestration.budget_governor")

class ExecutionBudgetGovernor:
    """Thread-safe multi-tenant budget governor enforcing financial constraints and cache resolution."""

    def __init__(
        self,
        default_max_run_spend_usd: float = 50.0,
        default_max_production_spend_usd: float = 500.0,
        provider_rates: Optional[Dict[str, ProviderRate]] = None,
    ):
        self.default_max_run_spend_usd = float(default_max_run_spend_usd)
        self.default_max_production_spend_usd = float(default_max_production_spend_usd)
        self._rates: Dict[str, ProviderRate] = copy.deepcopy(provider_rates or DEFAULT_PROVIDER_RATES)
        self._run_limits: Dict[str, float] = {}
        self._production_limits: Dict[str, float] = {}
        self._run_productions: Dict[str, str] = {}
        self._run_spend: Dict[str, float] = {}
        self._production_spend: Dict[str, float] = {}
        self._records: Dict[str, List[BudgetTrackingRecord]] = {}
        self._run_statuses: Dict[str, RunStatus] = {}
        self._partial_findings: Dict[str, List[Any]] = {}
        self._cache = DuplicateQueryCache()
        self._lock = threading.RLock()

    def estimate_preflight_cost(self, page_count: int, estimated_claims: int) -> float:
        """Calculate preflight cost formula: (Page Count * 0.015) + (Estimated Claims * 0.04)."""
        if page_count < 0 or estimated_claims < 0:
            raise ValueError("page_count and estimated_claims must be non-negative integers")
        return round((page_count * PAGE_RATE_USD) + (estimated_claims * CLAIM_RATE_USD), 4)

    def get_preflight_breakdown(self, page_count: int, estimated_claims: int) -> CostBreakdown:
        """Return granular itemized preflight cost breakdown."""
        total = self.estimate_preflight_cost(page_count, estimated_claims)
        return CostBreakdown(
            page_count=page_count, estimated_claims=estimated_claims,
            page_cost_usd=round(page_count * PAGE_RATE_USD, 4),
            claims_cost_usd=round(estimated_claims * CLAIM_RATE_USD, 4), total_estimated_usd=total,
        )

    def authorize_run(
        self, run_id: str, estimated_cost: float,
        run_budget_limit: Optional[float] = None, production_id: Optional[str] = None,
    ) -> BudgetAuthorization:
        """Authorize an investigation run against run and production spend caps."""
        if not run_id or not str(run_id).strip():
            raise ValueError("run_id must be a non-empty string")
        with self._lock:
            lim = float(run_budget_limit) if run_budget_limit is not None else self.default_max_run_spend_usd
            self._run_limits[run_id] = lim
            if production_id:
                self._run_productions[run_id] = production_id
            curr = self._run_spend.get(run_id, 0.0)
            rem = max(0.0, round(lim - curr, 6))
            authorized = (curr + estimated_cost) <= lim
            reason = f"Authorized: preflight cost ${estimated_cost:.4f} within run budget limit ${lim:.4f}"
            if not authorized:
                reason = f"Rejection: estimated cost ${estimated_cost:.4f} exceeds remaining run budget ${rem:.4f}"
                self._run_statuses[run_id] = RunStatus.WAITING_FOR_BUDGET
            elif production_id:
                plim = self._production_limits.get(production_id, self.default_max_production_spend_usd)
                pspent = self._production_spend.get(production_id, 0.0)
                if (pspent + estimated_cost) > plim:
                    authorized = False
                    reason = f"Rejection: estimated cost exceeds production cap (${pspent:.4f}/${plim:.4f})"
                    self._run_statuses[run_id] = RunStatus.WAITING_FOR_BUDGET
            return BudgetAuthorization(
                run_id=run_id, production_id=production_id, authorized=authorized,
                estimated_cost=round(estimated_cost, 4), allocated_budget=lim,
                current_spend=curr, remaining_budget=rem, reason=reason,
            )

    def record_usage(
        self, run_id: str, provider: str, tokens_prompt: int, tokens_completion: int,
        cost_usd: Optional[float] = None, query: Optional[str] = None,
    ) -> BudgetTrackingRecord:
        """Record external token or query usage, checking duplicate cache for $0 spend."""
        with self._lock:
            c_prov = normalize_provider_name(provider)
            is_cached = False
            effective_cost: float = 0.0
            if query and self.check_duplicate_cache(query) is not None:
                is_cached = True
                effective_cost = 0.0
            elif cost_usd is not None:
                effective_cost = max(0.0, float(cost_usd))
            else:
                rate = self._rates.get(c_prov, DEFAULT_PROVIDER_RATES.get(c_prov, ProviderRate(provider_name=c_prov)))
                tok_cost = (tokens_prompt * rate.cost_per_prompt_token_usd) + (tokens_completion * rate.cost_per_completion_token_usd)
                call_cost = rate.cost_per_call_usd if (tokens_prompt == 0 and tokens_completion == 0) or rate.cost_per_call_usd > 0 else 0.0
                effective_cost = round(tok_cost + call_cost, 6)

            prod_id = self._run_productions.get(run_id)
            rec = BudgetTrackingRecord(
                run_id=run_id, production_id=prod_id, provider=c_prov,
                tokens_prompt=tokens_prompt, tokens_completion=tokens_completion,
                cost_usd=effective_cost, query=query, is_cached=is_cached,
            )
            self._records.setdefault(run_id, []).append(rec)
            self._run_spend[run_id] = round(self._run_spend.get(run_id, 0.0) + effective_cost, 6)
            if prod_id:
                self._production_spend[prod_id] = round(self._production_spend.get(prod_id, 0.0) + effective_cost, 6)
            self.check_mid_flight_cap(run_id)
            return rec

    def check_mid_flight_cap(self, run_id: str, run: Optional[InvestigationRun] = None) -> bool:
        """Check mid-flight spend cap; transitions to WAITING_FOR_BUDGET if cap breached."""
        with self._lock:
            lim = self._run_limits.get(run_id, self.default_max_run_spend_usd)
            spent = self._run_spend.get(run_id, 0.0)
            prod_id = self._run_productions.get(run_id)
            prod_breach = False
            if prod_id:
                plim = self._production_limits.get(prod_id, self.default_max_production_spend_usd)
                prod_breach = self._production_spend.get(prod_id, 0.0) >= plim

            if spent >= lim or prod_breach:
                self._run_statuses[run_id] = RunStatus.WAITING_FOR_BUDGET
                if run and run.status != RunStatus.WAITING_FOR_BUDGET:
                    try:
                        transition_run(
                            run=run, target_state=RunStatus.WAITING_FOR_BUDGET,
                            actor_id="budget_governor", reason=f"Mid-flight spend cap reached (${spent:.4f} of ${lim:.4f})",
                            metadata={"budget_spent_usd": spent, "spend_cap_usd": lim},
                        )
                    except Exception as exc:
                        logger.warning("Could not transition run '%s' via lifecycle engine: %s", run_id, exc)
                return False
            return True

    def get_remaining_budget(self, run_id: str) -> float:
        """Return remaining dollar allowance for target investigation run."""
        with self._lock:
            lim = self._run_limits.get(run_id, self.default_max_run_spend_usd)
            return max(0.0, round(lim - self._run_spend.get(run_id, 0.0), 6))

    def get_total_spent(self, run_id: str) -> float:
        """Return cumulative expenditure incurred by target investigation run."""
        with self._lock:
            return round(self._run_spend.get(run_id, 0.0), 6)

    def check_duplicate_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Return cached evidence query result with guaranteed strictly $0.00 spend."""
        return self._cache.get(query)

    def cache_query_result(self, query: str, result: Dict[str, Any]) -> None:
        """Store evidence search result into zero-spend duplicate query cache."""
        self._cache.put(query, result)

    def pause_run_for_budget(
        self, run_id: str, partial_findings: List[Any], run: Optional[InvestigationRun] = None,
    ) -> Dict[str, Any]:
        """Cleanly transition run to WAITING_FOR_BUDGET preserving 100% of partial findings."""
        with self._lock:
            self._run_statuses[run_id] = RunStatus.WAITING_FOR_BUDGET
            self._partial_findings[run_id] = copy.deepcopy(partial_findings)
            spent = self.get_total_spent(run_id)
            lim = self._run_limits.get(run_id, self.default_max_run_spend_usd)
            if run and run.status != RunStatus.WAITING_FOR_BUDGET:
                try:
                    transition_run(
                        run=run, target_state=RunStatus.WAITING_FOR_BUDGET,
                        actor_id="budget_governor", reason="Budget exhausted. Execution paused preserving partial findings.",
                        metadata={"budget_spent_usd": spent, "partial_count": len(partial_findings)},
                    )
                except Exception as exc:
                    logger.warning("Could not transition run '%s': %s", run_id, exc)

            return {
                "run_id": run_id, "status": RunStatus.WAITING_FOR_BUDGET.value,
                "reason": "Budget limit exhausted. Execution paused to protect spend cap.",
                "budget_spent_usd": spent, "budget_limit_usd": lim,
                "remaining_budget_usd": self.get_remaining_budget(run_id),
                "partial_findings_count": len(partial_findings),
                "partial_findings": list(partial_findings),
                "paused_at": datetime.now(timezone.utc).isoformat(),
                "synthetic_completion": False,
            }

    def get_run_status(self, run_id: str) -> RunStatus:
        """Get internal run status recorded by governor."""
        with self._lock:
            return self._run_statuses.get(run_id, RunStatus.QUEUED)

    def get_partial_findings(self, run_id: str) -> List[Any]:
        """Retrieve preserved partial findings for a paused run."""
        with self._lock:
            return list(self._partial_findings.get(run_id, []))

    def get_records(self, run_id: str) -> List[BudgetTrackingRecord]:
        """Retrieve tracking records for an investigation run."""
        with self._lock:
            return list(self._records.get(run_id, []))

    def set_production_limit(self, production_id: str, limit_usd: float) -> None:
        """Set explicit spend cap in USD for a production container."""
        with self._lock:
            self._production_limits[production_id] = max(0.0, float(limit_usd))

    def set_run_limit(self, run_id: str, limit_usd: float) -> None:
        """Set explicit spend cap in USD for an individual investigation run."""
        with self._lock:
            self._run_limits[run_id] = max(0.0, float(limit_usd))

    def reset(self) -> None:
        """Reset internal memory structures for clean testing state."""
        with self._lock:
            for store in (
                self._run_limits, self._production_limits, self._run_productions,
                self._run_spend, self._production_spend, self._records,
                self._run_statuses, self._partial_findings,
            ):
                store.clear()
            self._cache.clear()

budget_governor = ExecutionBudgetGovernor()
