"""
Lienmark Budget Governor Domain Models and Types.
Canonical schemas and pricing specifications for clearance budget enforcement.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import copy
import hashlib
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.orchestration.budget_store_types import (
    BudgetPeriodSummary,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetStoreError,
    ReservationNotFoundError,
    ReservationStatus,
)

PAGE_RATE_USD: float = 0.015
CLAIM_RATE_USD: float = 0.040
MICROS_PER_USD: int = 1_000_000
PAGE_RATE_MICROS: int = 15_000
CLAIM_RATE_MICROS: int = 40_000
PARALLEL_FAST_MICROS: int = 1_000
PARALLEL_BASIC_MICROS: int = 5_000
PARALLEL_FAST_USD: float = 0.001
PARALLEL_BASIC_USD: float = 0.005


def usd_to_micros(usd: float) -> int:
    return int(round(float(usd) * MICROS_PER_USD))


def micros_to_usd(micros: int) -> float:
    return round(float(micros) / MICROS_PER_USD, 6)


def calculate_parallel_cost_micros(mode_or_model: str = "basic") -> int:
    return PARALLEL_FAST_MICROS if "fast" in str(mode_or_model).lower() else PARALLEL_BASIC_MICROS


def calculate_parallel_cost_usd(mode_or_model: str = "basic") -> float:
    return micros_to_usd(calculate_parallel_cost_micros(mode_or_model))


def calculate_gemini_cost_micros(
    model: str = "gemini-1.5-pro", prompt_tokens: int = 0, completion_tokens: int = 0,
) -> int:
    if "flash" in str(model).lower():
        return int(round((prompt_tokens * 0.075) + (completion_tokens * 0.30)))
    return int(round((prompt_tokens * 1.25) + (completion_tokens * 5.00)))


def calculate_gemini_cost_usd(
    model: str = "gemini-1.5-pro", prompt_tokens: int = 0, completion_tokens: int = 0,
) -> float:
    return micros_to_usd(calculate_gemini_cost_micros(model, prompt_tokens, completion_tokens))


class BudgetGovernorError(BudgetStoreError):
    pass


class BudgetExceededError(BudgetGovernorError):
    def __init__(
        self, run_id: str = "", current_spend: float = 0.0, spend_limit: float = 0.0,
        message: Optional[str] = None, period_id: str = "", current_spend_micros: int = 0,
        limit_micros: int = 0,
    ):
        self.run_id, self.current_spend, self.spend_limit = run_id, current_spend, spend_limit
        self.period_id, self.current_spend_micros, self.limit_micros = period_id, current_spend_micros, limit_micros
        msg = message or (
            f"Run '{run_id}' exceeded budget cap: ${current_spend:.4f} spent of ${spend_limit:.4f} limit."
            if run_id else f"Budget exceeded: ${current_spend:.4f} exceeds limit ${spend_limit:.4f}"
        )
        super().__init__(msg)


class ProviderName(str, Enum):
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    PARALLEL_SEARCH = "parallel_search"
    ASCAP_BMI = "ascap_bmi"
    LOC_COPYRIGHT_OFFICE = "loc_copyright_office"


class ProviderRate(BaseModel):
    provider_name: str = Field(..., min_length=1)
    cost_per_prompt_token_usd: float = Field(default=0.0, ge=0.0)
    cost_per_completion_token_usd: float = Field(default=0.0, ge=0.0)
    cost_per_call_usd: float = Field(default=0.0, ge=0.0)
    description: str = Field(default="")


class CostBreakdown(BaseModel):
    page_count: int = Field(ge=0)
    estimated_claims: int = Field(ge=0)
    page_cost_usd: float = Field(ge=0.0)
    claims_cost_usd: float = Field(ge=0.0)
    total_estimated_usd: float = Field(ge=0.0)


class BudgetTrackingRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: f"btr_{uuid.uuid4().hex[:12]}")
    run_id: str = Field(..., min_length=1)
    production_id: Optional[str] = None
    provider: str = Field(..., min_length=1)
    tokens_prompt: int = Field(default=0, ge=0)
    tokens_completion: int = Field(default=0, ge=0)
    cost_usd: float = Field(ge=0.0)
    query: Optional[str] = None
    is_cached: bool = Field(default=False)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BudgetAuthorization(BaseModel):
    run_id: str = Field(..., min_length=1)
    production_id: Optional[str] = None
    authorized: bool = Field(...)
    estimated_cost: float = Field(ge=0.0)
    allocated_budget: float = Field(ge=0.0)
    current_spend: float = Field(ge=0.0)
    remaining_budget: float = Field(ge=0.0)
    reason: str = Field(..., min_length=1)
    authorized_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CachedEvidence(BaseModel):
    query_hash: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    result: Dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = Field(default=0.0, ge=0.0)
    cached_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hits: int = Field(default=0, ge=0)


class DuplicateQueryCache:
    def __init__(self):
        self._cache: Dict[str, CachedEvidence] = {}
        self._lock = threading.RLock()

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        if not query or not str(query).strip():
            return None
        with self._lock:
            entry = self._cache.get(query.strip().lower())
            if entry:
                entry.hits += 1
                cached = copy.deepcopy(entry.result)
                cached.update({"cost_usd": 0.0, "is_cached": True})
                return cached
            return None

    def put(self, query: str, result: Dict[str, Any]) -> None:
        if not query or not str(query).strip():
            return
        with self._lock:
            key = query.strip().lower()
            q_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
            self._cache[key] = CachedEvidence(
                query_hash=q_hash, query=query.strip(),
                result=copy.deepcopy(result), cost_usd=0.0,
            )

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


DEFAULT_PROVIDER_RATES: Dict[str, ProviderRate] = {
    ProviderName.GEMINI_1_5_PRO.value: ProviderRate(
        provider_name=ProviderName.GEMINI_1_5_PRO.value,
        cost_per_prompt_token_usd=0.00000125, cost_per_completion_token_usd=0.00000500,
    ),
    ProviderName.GEMINI_1_5_FLASH.value: ProviderRate(
        provider_name=ProviderName.GEMINI_1_5_FLASH.value,
        cost_per_prompt_token_usd=0.000000075, cost_per_completion_token_usd=0.00000030,
    ),
    ProviderName.PARALLEL_SEARCH.value: ProviderRate(
        provider_name=ProviderName.PARALLEL_SEARCH.value, cost_per_call_usd=0.010,
    ),
    ProviderName.ASCAP_BMI.value: ProviderRate(
        provider_name=ProviderName.ASCAP_BMI.value, cost_per_call_usd=0.005,
    ),
    ProviderName.LOC_COPYRIGHT_OFFICE.value: ProviderRate(
        provider_name=ProviderName.LOC_COPYRIGHT_OFFICE.value, cost_per_call_usd=0.005,
    ),
}


def normalize_provider_name(provider: str) -> str:
    norm = str(provider).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    if "flash" in norm:
        return ProviderName.GEMINI_1_5_FLASH.value
    if "pro" in norm or ("gemini" in norm and "flash" not in norm):
        return ProviderName.GEMINI_1_5_PRO.value
    if "parallel" in norm:
        return ProviderName.PARALLEL_SEARCH.value
    if "ascap" in norm or "bmi" in norm:
        return ProviderName.ASCAP_BMI.value
    if "loc" in norm or "copyright" in norm:
        return ProviderName.LOC_COPYRIGHT_OFFICE.value
    return str(provider).strip().lower()


__all__ = [
    "PAGE_RATE_USD", "CLAIM_RATE_USD", "MICROS_PER_USD", "PAGE_RATE_MICROS",
    "CLAIM_RATE_MICROS", "PARALLEL_FAST_MICROS", "PARALLEL_BASIC_MICROS",
    "PARALLEL_FAST_USD", "PARALLEL_BASIC_USD", "usd_to_micros", "micros_to_usd",
    "calculate_parallel_cost_micros", "calculate_parallel_cost_usd",
    "calculate_gemini_cost_micros", "calculate_gemini_cost_usd",
    "BudgetGovernorError", "BudgetExceededError", "BudgetReservation",
    "BudgetSettlementRecord", "BudgetPeriodSummary", "ReservationStatus",
    "ReservationNotFoundError", "ProviderName", "ProviderRate", "CostBreakdown",
    "BudgetTrackingRecord", "BudgetAuthorization", "CachedEvidence",
    "DuplicateQueryCache", "DEFAULT_PROVIDER_RATES", "normalize_provider_name",
]
