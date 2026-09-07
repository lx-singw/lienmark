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

PAGE_RATE_USD: float = 0.015
CLAIM_RATE_USD: float = 0.040


class BudgetGovernorError(Exception):
    """Base exception for budget governor operations."""
    pass


class BudgetExceededError(BudgetGovernorError):
    """Raised when hard spend cap per run or per production is breached."""

    def __init__(
        self,
        run_id: str,
        current_spend: float,
        spend_limit: float,
        message: Optional[str] = None,
    ):
        self.run_id = run_id
        self.current_spend = current_spend
        self.spend_limit = spend_limit
        msg = (
            message
            or f"Run '{run_id}' exceeded budget cap: ${current_spend:.4f} spent of ${spend_limit:.4f} limit."
        )
        super().__init__(msg)


class ProviderName(str, Enum):
    """Supported clearance research and AI provider names."""
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    PARALLEL_SEARCH = "parallel_search"
    ASCAP_BMI = "ascap_bmi"
    LOC_COPYRIGHT_OFFICE = "loc_copyright_office"


class ProviderRate(BaseModel):
    """Pricing rates for an external AI or clearance search provider."""
    provider_name: str = Field(..., min_length=1, description="Canonical or raw provider name")
    cost_per_prompt_token_usd: float = Field(default=0.0, ge=0.0, description="Cost per prompt token in USD")
    cost_per_completion_token_usd: float = Field(default=0.0, ge=0.0, description="Cost per completion token in USD")
    cost_per_call_usd: float = Field(default=0.0, ge=0.0, description="Cost per search/API lookup call in USD")
    description: str = Field(default="", description="Provider description and rate context")


class CostBreakdown(BaseModel):
    """Granular breakdown of pre-flight cost estimation."""
    page_count: int = Field(ge=0, description="Total script pages processed")
    estimated_claims: int = Field(ge=0, description="Estimated total claims identified")
    page_cost_usd: float = Field(ge=0.0, description="Cost attributed to page processing ($0.015/page)")
    claims_cost_usd: float = Field(ge=0.0, description="Cost attributed to claims verification ($0.04/claim)")
    total_estimated_usd: float = Field(ge=0.0, description="Total preflight estimated cost in USD")


class BudgetTrackingRecord(BaseModel):
    """Immutable ledger record tracking live token and API expenditure."""
    record_id: str = Field(default_factory=lambda: f"btr_{uuid.uuid4().hex[:12]}")
    run_id: str = Field(..., min_length=1, description="Bound investigation run identifier")
    production_id: Optional[str] = Field(None, description="Bound production container identifier")
    provider: str = Field(..., min_length=1, description="External provider identifier")
    tokens_prompt: int = Field(default=0, ge=0, description="Prompt input tokens consumed")
    tokens_completion: int = Field(default=0, ge=0, description="Completion tokens generated")
    cost_usd: float = Field(ge=0.0, description="Calculated or recorded financial expenditure in USD")
    query: Optional[str] = Field(None, description="Query string if external search lookup")
    is_cached: bool = Field(default=False, description="True if query resolved from cache with $0.00 spend")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BudgetAuthorization(BaseModel):
    """Result of pre-flight run budget authorization check."""
    run_id: str = Field(..., min_length=1, description="Target investigation run identifier")
    production_id: Optional[str] = None
    authorized: bool = Field(..., description="Whether the run is cleared to execute under spend cap")
    estimated_cost: float = Field(ge=0.0, description="Pre-flight estimated cost in USD")
    allocated_budget: float = Field(ge=0.0, description="Allocated budget limit for run in USD")
    current_spend: float = Field(ge=0.0, description="Current cumulative spend in USD")
    remaining_budget: float = Field(ge=0.0, description="Remaining budget allowance in USD")
    reason: str = Field(..., min_length=1, description="Authorization status justification")
    authorized_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CachedEvidence(BaseModel):
    """Cached external evidence payload with zero-cost reuse metadata."""
    query_hash: str = Field(..., min_length=1, description="SHA-256 hash of normalized query")
    query: str = Field(..., min_length=1, description="Original query string")
    result: Dict[str, Any] = Field(default_factory=dict, description="Cached evidence result dictionary")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Spend incurred for cached evidence, strictly $0.00")
    cached_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hits: int = Field(default=0, ge=0, description="Number of duplicate query cache hits")


class DuplicateQueryCache:
    """Thread-safe cache for duplicate query resolution at strictly $0.00 spend."""

    def __init__(self):
        self._cache: Dict[str, CachedEvidence] = {}
        self._lock = threading.RLock()

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        if not query or not str(query).strip():
            return None
        with self._lock:
            key = query.strip().lower()
            if key in self._cache:
                entry = self._cache[key]
                entry.hits += 1
                cached = copy.deepcopy(entry.result)
                cached["cost_usd"] = 0.0
                cached["is_cached"] = True
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
        cost_per_prompt_token_usd=0.00000125,
        cost_per_completion_token_usd=0.00000500,
        cost_per_call_usd=0.0,
        description="Gemini 1.5 Pro multimodal reasoning ($1.25/1M input, $5.00/1M output)",
    ),
    ProviderName.GEMINI_1_5_FLASH.value: ProviderRate(
        provider_name=ProviderName.GEMINI_1_5_FLASH.value,
        cost_per_prompt_token_usd=0.000000075,
        cost_per_completion_token_usd=0.00000030,
        cost_per_call_usd=0.0,
        description="Gemini 1.5 Flash rapid semantic delta analysis ($0.075/1M input, $0.30/1M output)",
    ),
    ProviderName.PARALLEL_SEARCH.value: ProviderRate(
        provider_name=ProviderName.PARALLEL_SEARCH.value,
        cost_per_prompt_token_usd=0.0,
        cost_per_completion_token_usd=0.0,
        cost_per_call_usd=0.010,
        description="Parallel Search API v1 targeted legal evidence search ($0.010/call)",
    ),
    ProviderName.ASCAP_BMI.value: ProviderRate(
        provider_name=ProviderName.ASCAP_BMI.value,
        cost_per_prompt_token_usd=0.0,
        cost_per_completion_token_usd=0.0,
        cost_per_call_usd=0.005,
        description="ASCAP & BMI Music Repertoire database lookup ($0.005/call)",
    ),
    ProviderName.LOC_COPYRIGHT_OFFICE.value: ProviderRate(
        provider_name=ProviderName.LOC_COPYRIGHT_OFFICE.value,
        cost_per_prompt_token_usd=0.0,
        cost_per_completion_token_usd=0.0,
        cost_per_call_usd=0.005,
        description="Library of Congress and US Copyright Office catalog lookup ($0.005/call)",
    ),
}


def normalize_provider_name(provider: str) -> str:
    """Normalize user or external provider string into canonical provider name."""
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
