"""
Lienmark Execution Budget Governor Subsystem.
Enforces hard spend caps per run/production, pre-flight estimation, and fail-closed state pausing.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import contextlib
import copy
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.domain.models import RunStatus, InvestigationRun
from backend.core.lifecycle import transition_run
from backend.orchestration.budget_store import BudgetStore, get_budget_store
from backend.orchestration.budget_types import (
    CLAIM_RATE_MICROS, CLAIM_RATE_USD, DEFAULT_PROVIDER_RATES, PAGE_RATE_MICROS,
    PAGE_RATE_USD, BudgetAuthorization, BudgetExceededError, BudgetGovernorError,
    BudgetReservation, BudgetSettlementRecord, BudgetTrackingRecord, CachedEvidence,
    CostBreakdown, DuplicateQueryCache, ProviderName, ProviderRate, ReservationStatus,
    calculate_gemini_cost_micros, calculate_gemini_cost_usd, calculate_parallel_cost_micros,
    calculate_parallel_cost_usd, micros_to_usd, normalize_provider_name, usd_to_micros,
)

logger = logging.getLogger("lienmark.orchestration.budget_governor")


class ExecutionBudgetGovernor:
    """Thread-safe multi-tenant budget governor enforcing two-phase reservations and spend caps."""

    def __init__(
        self, default_max_run_spend_usd: float = 50.0, default_max_production_spend_usd: float = 500.0,
        provider_rates: Optional[Dict[str, ProviderRate]] = None, store: Optional[Any] = None,
    ):
        self.default_max_run_spend_usd, self.default_max_production_spend_usd = float(default_max_run_spend_usd), float(default_max_production_spend_usd)
        self.store = store or get_budget_store()
        self._rates = copy.deepcopy(provider_rates or DEFAULT_PROVIDER_RATES)
        self._run_limits, self._production_limits, self._run_productions = {}, {}, {}
        self._run_spend, self._production_spend = {}, {}
        self._run_reserved_micros, self._run_spend_micros = {}, {}
        self._res_runs, self._res_max_micros = {}, {}
        self._records, self._run_statuses, self._partial_findings = {}, {}, {}
        self._cache, self._lock = DuplicateQueryCache(), threading.RLock()

    def estimate_preflight_cost(self, page_count: int, estimated_claims: int) -> float:
        if page_count < 0 or estimated_claims < 0: raise ValueError("page_count and estimated_claims must be non-negative integers")
        return round(micros_to_usd((page_count * PAGE_RATE_MICROS) + (estimated_claims * CLAIM_RATE_MICROS)), 4)

    def get_preflight_breakdown(self, page_count: int, estimated_claims: int) -> CostBreakdown:
        return CostBreakdown(
            page_count=page_count, estimated_claims=estimated_claims,
            page_cost_usd=round(micros_to_usd(page_count * PAGE_RATE_MICROS), 4),
            claims_cost_usd=round(micros_to_usd(estimated_claims * CLAIM_RATE_MICROS), 4),
            total_estimated_usd=self.estimate_preflight_cost(page_count, estimated_claims),
        )

    def reserve(
        self, org_id: str, production_id: str, run_id: str, period_id: str,
        action_id: str, provider: str, model_or_mode: str, max_cost_micros: int,
    ) -> BudgetReservation:
        if max_cost_micros < 0: raise ValueError("max_cost_micros must be non-negative")
        with self._lock:
            self._run_productions[run_id] = production_id
            run_lim = self._run_limits.get(run_id, self.default_max_run_spend_usd)
            run_curr = self._run_spend_micros.get(run_id, 0) + self._run_reserved_micros.get(run_id, 0)
            if run_curr + max_cost_micros > usd_to_micros(run_lim):
                raise BudgetExceededError(run_id=run_id, current_spend=micros_to_usd(run_curr + max_cost_micros), spend_limit=run_lim)
            prod_lim = self._production_limits.get(production_id)
            if prod_lim is not None: self.store.set_budget_limit(org_id, production_id, period_id, usd_to_micros(prod_lim))
            res = self.store.reserve_budget(
                org_id=org_id, production_id=production_id, budget_period_id=period_id,
                run_id=run_id, action_id=action_id, provider=provider, model_or_mode=model_or_mode,
                max_cost_micros=max_cost_micros,
            )
            self._run_reserved_micros[run_id] = self._run_reserved_micros.get(run_id, 0) + max_cost_micros
            self._res_runs[res.reservation_id], self._res_max_micros[res.reservation_id] = run_id, max_cost_micros
            return res

    def settle(
        self, reservation_id: str, actual_usage: Dict[str, Any],
        provider_cost_micros: Optional[int] = None, cache_hit: bool = False,
    ) -> BudgetSettlementRecord:
        with self._lock:
            cost = 0 if cache_hit else (max(0, int(provider_cost_micros)) if provider_cost_micros is not None else self._calc_usage_cost(actual_usage))
            record = self.store.settle_reservation(
                reservation_id=reservation_id, actual_cost_micros=cost, usage_measurements=actual_usage,
                provider_confirmed_cost_micros=0 if cache_hit else cost, cache_hit=cache_hit,
            )
            run_id, res_max = self._res_runs.get(reservation_id, ""), self._res_max_micros.get(reservation_id, 0)
            if run_id:
                self._run_reserved_micros[run_id] = max(0, self._run_reserved_micros.get(run_id, 0) - res_max)
                self._run_spend_micros[run_id] = self._run_spend_micros.get(run_id, 0) + cost
                self._run_spend[run_id] = round(self._run_spend.get(run_id, 0.0) + micros_to_usd(cost), 6)
                pid = self._run_productions.get(run_id)
                if pid: self._production_spend[pid] = round(self._production_spend.get(pid, 0.0) + micros_to_usd(cost), 6)
            return record

    def recover(self, reservation_id: str, error_reason: str) -> None:
        with self._lock:
            self.store.recover_reservation(reservation_id=reservation_id, status=ReservationStatus.RELEASED)
            run_id, res_max = self._res_runs.get(reservation_id, ""), self._res_max_micros.get(reservation_id, 0)
            if run_id: self._run_reserved_micros[run_id] = max(0, self._run_reserved_micros.get(run_id, 0) - res_max)

    def _calc_usage_cost(self, actual_usage: Dict[str, Any]) -> int:
        p_mode = str(actual_usage.get("mode", actual_usage.get("model", ""))).lower()
        if "fast" in p_mode or "basic" in p_mode: return calculate_parallel_cost_micros(p_mode)
        prompt, comp = actual_usage.get("tokens_prompt", actual_usage.get("prompt_tokens", 0)), actual_usage.get("tokens_completion", actual_usage.get("completion_tokens", 0))
        return calculate_gemini_cost_micros(p_mode or "gemini-1.5-pro", prompt, comp)

    def authorize_run(
        self, run_id: str, estimated_cost: float,
        run_budget_limit: Optional[float] = None, production_id: Optional[str] = None,
    ) -> BudgetAuthorization:
        if not run_id or not str(run_id).strip(): raise ValueError("run_id must be a non-empty string")
        with self._lock:
            lim = float(run_budget_limit) if run_budget_limit is not None else self.default_max_run_spend_usd
            self._run_limits[run_id] = lim
            if production_id:
                self._run_productions[run_id] = production_id
                plim = self._production_limits.get(production_id, self.default_max_production_spend_usd)
            curr, rem = self._run_spend.get(run_id, 0.0), max(0.0, round(lim - self._run_spend.get(run_id, 0.0), 6))
            authorized = (curr + estimated_cost) <= lim
            reason = f"Authorized: preflight cost ${estimated_cost:.4f} within run budget limit ${lim:.4f}"
            if not authorized:
                reason, self._run_statuses[run_id] = f"Rejection: estimated cost ${estimated_cost:.4f} exceeds remaining run budget ${rem:.4f}", RunStatus.WAITING_FOR_BUDGET
            elif production_id and (self._production_spend.get(production_id, 0.0) + estimated_cost) > plim:
                authorized, reason, self._run_statuses[run_id] = False, "Rejection: estimated cost exceeds production cap", RunStatus.WAITING_FOR_BUDGET
            return BudgetAuthorization(
                run_id=run_id, production_id=production_id, authorized=authorized,
                estimated_cost=round(estimated_cost, 4), allocated_budget=lim,
                current_spend=curr, remaining_budget=rem, reason=reason,
            )

    def record_usage(
        self, run_id: str, provider: str, tokens_prompt: int, tokens_completion: int,
        cost_usd: Optional[float] = None, query: Optional[str] = None,
    ) -> BudgetTrackingRecord:
        with self._lock:
            c_prov = normalize_provider_name(provider)
            is_cached = bool(query and self.check_duplicate_cache(query) is not None)
            if is_cached: eff = 0.0
            elif cost_usd is not None: eff = max(0.0, float(cost_usd))
            else:
                rate = self._rates.get(c_prov, DEFAULT_PROVIDER_RATES.get(c_prov, ProviderRate(provider_name=c_prov)))
                call = rate.cost_per_call_usd if (tokens_prompt == 0 and tokens_completion == 0) or rate.cost_per_call_usd > 0 else 0.0
                eff = round((tokens_prompt * rate.cost_per_prompt_token_usd) + (tokens_completion * rate.cost_per_completion_token_usd) + call, 6)
            prod_id = self._run_productions.get(run_id)
            rec = BudgetTrackingRecord(
                run_id=run_id, production_id=prod_id, provider=c_prov, tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion, cost_usd=eff, query=query, is_cached=is_cached,
            )
            self._records.setdefault(run_id, []).append(rec)
            self._run_spend[run_id] = round(self._run_spend.get(run_id, 0.0) + eff, 6)
            self._run_spend_micros[run_id] = self._run_spend_micros.get(run_id, 0) + usd_to_micros(eff)
            if prod_id: self._production_spend[prod_id] = round(self._production_spend.get(prod_id, 0.0) + eff, 6)
            self.check_mid_flight_cap(run_id)
            return rec

    def check_mid_flight_cap(
        self, org_id_or_run_id: str, production_id_or_run: Any = None,
        period_id: Optional[str] = None, run_id: Optional[str] = None,
        run: Optional[InvestigationRun] = None, org_id: Optional[str] = None,
        production_id: Optional[str] = None,
    ) -> bool:
        with self._lock:
            target_org = org_id or (org_id_or_run_id if period_id else None)
            target_prod = production_id or (production_id_or_run if isinstance(production_id_or_run, str) else None)
            target_run_id = run_id or (org_id_or_run_id if not period_id else None)
            target_run = run or (production_id_or_run if isinstance(production_id_or_run, InvestigationRun) else None)
            if target_org and period_id:
                summary = self.store.get_summary(target_org, target_prod or "", period_id)
                cap_b = summary.budget_limit_micros > 0 and (summary.settled_spend_micros + summary.outstanding_reservations_micros) >= summary.budget_limit_micros
                rid = target_run_id or ""
                run_b = (self._run_spend_micros.get(rid, 0) + self._run_reserved_micros.get(rid, 0)) >= usd_to_micros(self._run_limits.get(rid, self.default_max_run_spend_usd))
                if cap_b or run_b:
                    self._handle_cap_breach(rid, target_run)
                    return False
                return True
            rid = target_run_id or org_id_or_run_id
            lim, spent = self._run_limits.get(rid, self.default_max_run_spend_usd), self._run_spend.get(rid, 0.0)
            pid = target_prod or self._run_productions.get(rid)
            plim = self._production_limits.get(pid, self.default_max_production_spend_usd) if pid else 0.0
            if spent >= lim or (pid and self._production_spend.get(pid, 0.0) >= plim):
                self._handle_cap_breach(rid, target_run)
                return False
            return True

    def _handle_cap_breach(self, run_id: str, run: Optional[InvestigationRun]) -> None:
        self._run_statuses[run_id] = RunStatus.WAITING_FOR_BUDGET
        if run and run.status != RunStatus.WAITING_FOR_BUDGET:
            with contextlib.suppress(Exception):
                transition_run(run=run, target_state=RunStatus.WAITING_FOR_BUDGET, actor_id="budget_governor",
                               reason=f"Mid-flight spend cap reached (${self._run_spend.get(run_id, 0.0):.4f})",
                               metadata={"budget_spent_usd": self._run_spend.get(run_id, 0.0)})

    def pause_run_for_budget(
        self, run_id: str, partial_findings: List[Any], run: Optional[InvestigationRun] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self._handle_cap_breach(run_id, run)
            self._partial_findings[run_id] = copy.deepcopy(partial_findings)
            return {
                "run_id": run_id, "status": RunStatus.WAITING_FOR_BUDGET.value,
                "reason": "Budget limit exhausted. Execution paused to protect spend cap.",
                "budget_spent_usd": self.get_total_spent(run_id),
                "budget_limit_usd": self._run_limits.get(run_id, self.default_max_run_spend_usd),
                "remaining_budget_usd": self.get_remaining_budget(run_id),
                "partial_findings_count": len(partial_findings), "partial_findings": list(partial_findings),
                "paused_at": datetime.now(timezone.utc).isoformat(), "synthetic_completion": False,
            }

    def get_remaining_budget(self, run_id: str) -> float:
        with self._lock: return max(0.0, round(self._run_limits.get(run_id, self.default_max_run_spend_usd) - self._run_spend.get(run_id, 0.0), 6))
    def get_total_spent(self, run_id: str) -> float:
        with self._lock: return round(self._run_spend.get(run_id, 0.0), 6)
    def get_run_spend_micros(self, run_id: str) -> int:
        with self._lock: return self._run_spend_micros.get(run_id, 0)
    def get_run_reserved_micros(self, run_id: str) -> int:
        with self._lock: return self._run_reserved_micros.get(run_id, 0)
    def check_duplicate_cache(self, query: str) -> Optional[Dict[str, Any]]: return self._cache.get(query)
    def cache_query_result(self, query: str, result: Dict[str, Any]) -> None: self._cache.put(query, result)
    def get_run_status(self, run_id: str) -> RunStatus:
        with self._lock: return self._run_statuses.get(run_id, RunStatus.QUEUED)
    def get_partial_findings(self, run_id: str) -> List[Any]:
        with self._lock: return list(self._partial_findings.get(run_id, []))
    def get_records(self, run_id: str) -> List[BudgetTrackingRecord]:
        with self._lock: return list(self._records.get(run_id, []))
    def set_production_limit(self, production_id: str, limit_usd: float) -> None:
        with self._lock: self._production_limits[production_id] = max(0.0, float(limit_usd))
    def set_run_limit(self, run_id: str, limit_usd: float) -> None:
        with self._lock: self._run_limits[run_id] = max(0.0, float(limit_usd))

    def reset(self) -> None:
        with self._lock:
            for s in (self._run_limits, self._production_limits, self._run_productions,
                      self._run_spend, self._production_spend, self._run_reserved_micros,
                      self._run_spend_micros, self._res_runs, self._res_max_micros,
                      self._records, self._run_statuses, self._partial_findings):
                s.clear()
            self._cache.clear()
            if hasattr(self.store, "reset"):
                self.store.reset()

budget_governor = ExecutionBudgetGovernor()
