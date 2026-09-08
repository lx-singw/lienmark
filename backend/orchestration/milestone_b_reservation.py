"""
backend/orchestration/milestone_b_reservation.py

Milestone B durable budget reservation and checkpointing contract.
Enforces fund reservation before paid search, extraction, entity calls, and briefing calls
using BudgetGovernor, and checkpoints results before advancing actions.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.orchestration.budget_governor import (
    ExecutionBudgetGovernor,
    budget_governor as default_budget_governor,
)
from backend.orchestration.budget_types import (
    PARALLEL_BASIC_MICROS,
    PARALLEL_FAST_MICROS,
    ProviderName,
    calculate_gemini_cost_micros,
)
from backend.orchestration.budget_store_types import (
    BudgetReservation,
    BudgetSettlementRecord,
)
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    ExecutionCheckpoint,
    calculate_ttl_timestamp,
    compute_resume_token,
)

logger = logging.getLogger("lienmark.orchestration.milestone_b")


class PaidActionType(str, Enum):
    """Paid operations requiring two-phase durable budget reservation."""
    PAID_SEARCH = "paid_search"
    EXTRACTION = "extraction"
    ENTITY_CALL = "entity_call"
    BRIEFING_CALL = "briefing_call"


DEFAULT_ESTIMATED_MICROS: Dict[PaidActionType, int] = {
    PaidActionType.PAID_SEARCH: 10_000,      # $0.010
    PaidActionType.EXTRACTION: 20_000,       # $0.020
    PaidActionType.ENTITY_CALL: 5_000,        # $0.005
    PaidActionType.BRIEFING_CALL: 20_000,     # $0.020
}

DEFAULT_PROVIDERS: Dict[PaidActionType, str] = {
    PaidActionType.PAID_SEARCH: ProviderName.PARALLEL_SEARCH.value,
    PaidActionType.EXTRACTION: ProviderName.PARALLEL_SEARCH.value,
    PaidActionType.ENTITY_CALL: ProviderName.ASCAP_BMI.value,
    PaidActionType.BRIEFING_CALL: ProviderName.GEMINI_1_5_PRO.value,
}


class MilestoneBBudgetManager:
    """
    Coordinates Milestone B budget reservation contracts: reserves funds before
    paid operations and checkpoints results before advancing coordinator actions.
    """

    def __init__(
        self,
        governor: Optional[ExecutionBudgetGovernor] = None,
        tenant_id: str = "lienmark_default",
    ) -> None:
        self.governor = governor or default_budget_governor
        self.tenant_id = tenant_id
        self.checkpoints: Dict[str, ExecutionCheckpoint] = {}

    def get_estimated_cost_micros(
        self,
        action_type: PaidActionType,
        model_or_mode: str = "basic",
        prompt_tokens: int = 1000,
        completion_tokens: int = 500,
    ) -> int:
        """Estimates maximum cost in micros for a paid operation."""
        if action_type == PaidActionType.BRIEFING_CALL:
            return calculate_gemini_cost_micros(model_or_mode, prompt_tokens, completion_tokens)
        return DEFAULT_ESTIMATED_MICROS.get(action_type, 10_000)

    def reserve_for_action(
        self,
        run_id: str,
        production_id: str,
        action_type: PaidActionType,
        action_id: Optional[str] = None,
        period_id: str = "current_period",
        model_or_mode: str = "basic",
        custom_cost_micros: Optional[int] = None,
    ) -> BudgetReservation:
        """Reserves budget before paid search, extraction, entity call, or briefing call."""
        act_id = action_id or f"act_{action_type.value}_{uuid.uuid4().hex[:6]}"
        provider = DEFAULT_PROVIDERS.get(action_type, ProviderName.PARALLEL_SEARCH.value)
        cost_micros = (
            custom_cost_micros
            if custom_cost_micros is not None
            else self.get_estimated_cost_micros(action_type, model_or_mode)
        )
        logger.info(
            "Reserving %d micros for %s (%s) on run %s",
            cost_micros, action_type.value, provider, run_id,
        )
        return self.governor.reserve(
            org_id=self.tenant_id,
            production_id=production_id,
            run_id=run_id,
            period_id=period_id,
            action_id=act_id,
            provider=provider,
            model_or_mode=model_or_mode,
            max_cost_micros=cost_micros,
        )

    def checkpoint_before_advancing(
        self, run_id: str, production_id: str, claim_id: str, paused_stage: str,
        findings: List[Dict[str, Any]], context_vars: Optional[Dict[str, Any]] = None,
        pending_clarifications: Optional[List[str]] = None,
    ) -> ExecutionCheckpoint:
        """Checkpoints results and reasoning state before advancing to next action."""
        chk_id = f"chk_{claim_id}_{uuid.uuid4().hex[:6]}"
        now_utc, ttl_utc = datetime.now(timezone.utc).isoformat(), calculate_ttl_timestamp(ttl_seconds=86400)
        clarifs = list(pending_clarifications or [])
        token = compute_resume_token(
            tenant_id=self.tenant_id, production_id=production_id, run_id=run_id,
            claim_id=claim_id, paused_stage=paused_stage,
            pending_clarification_ids=clarifs, created_at_utc=now_utc,
        )
        checkpoint = ExecutionCheckpoint(
            checkpoint_id=chk_id, run_id=run_id, tenant_id=self.tenant_id,
            production_id=production_id, claim_id=claim_id, paused_stage=paused_stage,
            agent_memory_snapshot=AgentMemorySnapshot(findings=findings, context_variables=context_vars or {}),
            pending_clarification_ids=clarifs, resume_token=token,
            created_at_utc=now_utc, ttl_expires_at_utc=ttl_utc,
            metadata={"checkpoint_timestamp": now_utc},
        )
        self.checkpoints[chk_id] = checkpoint
        logger.info("Saved durable checkpoint %s for stage %s", chk_id, paused_stage)
        return checkpoint

    def settle_for_action(
        self,
        reservation_id: str,
        actual_usage: Optional[Dict[str, Any]] = None,
        provider_cost_micros: Optional[int] = None,
        cache_hit: bool = False,
    ) -> BudgetSettlementRecord:
        """Settles budget reservation upon successful action execution."""
        usage = actual_usage or {}
        return self.governor.settle(
            reservation_id=reservation_id,
            actual_usage=usage,
            provider_cost_micros=provider_cost_micros,
            cache_hit=cache_hit,
        )

    def recover_on_failure(self, reservation_id: str, reason: str = "execution_failed") -> None:
        """Releases reserved funds when action execution encounters an error."""
        logger.warning("Recovering reservation %s due to %s", reservation_id, reason)
        self.governor.recover(reservation_id=reservation_id, error_reason=reason)
