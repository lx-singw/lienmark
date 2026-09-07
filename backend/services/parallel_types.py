"""
backend/services/parallel_types.py

Data models, enums, and typed domain exceptions for the Parallel Search API SDK.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DomainAuthorityTier(str, Enum):
    """Four-tier authority classification for evidence sources."""
    TIER_1_GOVERNMENT = "tier_1_government_registry"
    TIER_2_RIGHTS_ORG = "tier_2_rights_organization"
    TIER_3_NEWS_EDITORIAL = "tier_3_news_editorial"
    TIER_4_GENERAL_WEB = "tier_4_general_web"


class ParallelClientError(Exception):
    """Base domain exception for Parallel Search API client errors."""
    pass


class ParallelAuthError(ParallelClientError):
    """Raised when authentication credentials (API key) are invalid or missing."""
    pass


class ParallelRateLimitError(ParallelClientError):
    """Raised when the API returns HTTP 429 Too Many Requests and retries exhaust."""
    pass


class ParallelTimeoutError(ParallelClientError):
    """Raised when request times out and retries are exhausted."""
    pass


class ParallelServerError(ParallelClientError):
    """Raised on upstream 5xx gateway or internal server errors."""
    pass


class ParallelValidationError(ParallelClientError):
    """Raised when request payload or parameters violate API constraints."""
    pass


class ParallelSearchRequest(BaseModel):
    """Request specification conforming to Parallel Search API v1."""
    model_config = ConfigDict(frozen=True)

    objective: str = Field(
        ..., min_length=3, description="Natural language description of clearance intent."
    )
    search_queries: List[str] = Field(
        ..., min_length=1, max_length=20, description="Targeted search query strings."
    )
    mode: str = Field(default="fast", description="Search execution mode: turbo, fast, basic, advanced.")
    max_chars_total: int = Field(default=4000, ge=500, le=16000, description="Total excerpt character budget.")
    include_domains: List[str] = Field(default_factory=list, description="Explicit domains to scope search to.")
    exclude_domains: List[str] = Field(default_factory=list, description="Explicit domains to block from search.")
    max_results: int = Field(default=10, ge=1, le=20, description="Maximum number of findings to retrieve.")

    def to_api_payload(self) -> Dict[str, Any]:
        """Converts request to the exact wire payload for the Parallel Search API v1."""
        payload: Dict[str, Any] = {
            "objective": self.objective,
            "search_queries": list(self.search_queries),
            "mode": self.mode,
            "max_chars_total": self.max_chars_total,
        }
        adv: Dict[str, Any] = {}
        if self.include_domains or self.exclude_domains:
            source_policy: Dict[str, Any] = {}
            if self.include_domains:
                source_policy["include_domains"] = list(self.include_domains)
            if self.exclude_domains:
                source_policy["exclude_domains"] = list(self.exclude_domains)
            adv["source_policy"] = source_policy
        if self.max_results != 10:
            adv["max_results"] = self.max_results
        if adv:
            payload["advanced_settings"] = adv
        return payload

    def compute_payload_hash(self) -> str:
        """Returns deterministic SHA-256 hash of canonical JSON wire payload."""
        wire = json.dumps(self.to_api_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(wire.encode("utf-8")).hexdigest()


class ParallelSearchFinding(BaseModel):
    """Individual source finding returned by Parallel Search API."""
    model_config = ConfigDict(frozen=True)

    url: str = Field(..., description="Canonical source URL.")
    title: str = Field(default="", description="Web page or document title.")
    domain: str = Field(default="", description="Extracted canonical host/domain.")
    publish_date: Optional[str] = Field(default=None, description="ISO publication date if known.")
    excerpts: List[str] = Field(default_factory=list, description="Attributable text snippets.")
    full_excerpt: str = Field(default="", description="Concatenated excerpt text.")
    authority_tier: DomainAuthorityTier = Field(
        default=DomainAuthorityTier.TIER_4_GENERAL_WEB,
        description="Classified authority tier.",
    )
    authority_score: float = Field(default=0.25, ge=0.0, le=1.0, description="Numeric trust weight.")
    confidence_score: float = Field(default=0.50, ge=0.0, le=1.0, description="Relevance confidence.")


class ParallelSearchResult(BaseModel):
    """Complete response envelope from Parallel Search API with telemetry and hashes."""
    model_config = ConfigDict(frozen=True)

    search_id: str = Field(default="", description="Provider call tracking ID.")
    session_id: Optional[str] = Field(default=None, description="Optional provider session ID.")
    findings: List[ParallelSearchFinding] = Field(default_factory=list, description="Retrieved source findings.")
    raw_response_hash: str = Field(default="", description="SHA-256 digest of raw provider JSON response.")
    request_payload_hash: str = Field(default="", description="SHA-256 digest of outgoing request payload.")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Round-trip network latency in ms.")
    http_status: int = Field(default=200, description="HTTP status code.")
    top_authority_tier: DomainAuthorityTier = Field(
        default=DomainAuthorityTier.TIER_4_GENERAL_WEB,
        description="Highest authority tier found.",
    )
    warnings: List[str] = Field(default_factory=list, description="Diagnostic warnings or fallback notes.")
