"""
Evidence Explorer Domain Schemas and Request/Response Models.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceSourceType(str, Enum):
    """Origin taxonomy for clearance evidence artifacts."""
    PUBLIC_SEARCH = "public_search"
    ARCHIVED_SNAPSHOT = "archived_snapshot"
    PRIVATE_CONTRACT = "private_contract"
    DOCUMENT_RECORD = "document_record"


class EvidenceConfidenceTier(str, Enum):
    """Categorized provenance confidence tier."""
    PRIMARY_STATUTORY = "primary_statutory"
    SECONDARY_REGISTRY = "secondary_registry"
    TERTIARY_WEB = "tertiary_web"
    PRIVATE_LEGAL = "private_legal"


class EvidenceItem(BaseModel):
    """Normalized evidence record presented in search and detail views."""
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(..., description="Unique evidence identifier")
    source_type: EvidenceSourceType = Field(..., description="Origin taxonomy")
    title: str = Field(..., description="Source title or contract name")
    source_url: Optional[str] = Field(default=None, description="Attributable external URL or doc path")
    domain: Optional[str] = Field(default=None, description="Extracted domain or registry origin")
    snippet: str = Field(..., description="Attributable snippet, quotation, or clause excerpt")
    retrieved_at: str = Field(..., description="ISO 8601 retrieval timestamp")
    confidence_tier: str = Field(default="primary_statutory", description="Evidence confidence tier")
    stance: str = Field(default="SUPPORTING", description="Evidentiary stance")
    asset_category: str = Field(default="general", description="Asset category e.g. music, visual_art, prop")
    http_status: Optional[int] = Field(default=200, description="HTTP liveness status code")
    liveness_status: str = Field(default="LIVE", description="Liveness classification")
    payload_digest: str = Field(..., description="SHA-256 digest of verbatim excerpt/content")
    linked_claims: List[str] = Field(default_factory=list, description="Claim IDs relying on this evidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance attributes")


class EvidenceFacets(BaseModel):
    """Aggregated facet distributions for faceted search exploration."""
    model_config = ConfigDict(extra="ignore")

    domains: Dict[str, int] = Field(default_factory=dict)
    source_types: Dict[str, int] = Field(default_factory=dict)
    stances: Dict[str, int] = Field(default_factory=dict)
    tiers: Dict[str, int] = Field(default_factory=dict)
    asset_categories: Dict[str, int] = Field(default_factory=dict)


class EvidenceSearchResponse(BaseModel):
    """Paginated search response for the Evidence Explorer."""
    model_config = ConfigDict(extra="ignore")

    items: List[EvidenceItem] = Field(default_factory=list)
    total_count: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)
    facets: EvidenceFacets = Field(default_factory=EvidenceFacets)


class EvidenceDetailResponse(BaseModel):
    """Full evidence detail with raw HTTP headers and verification state."""
    model_config = ConfigDict(extra="ignore")

    item: EvidenceItem
    raw_headers: Dict[str, str] = Field(default_factory=dict)
    storage_path: Optional[str] = None
    linked_claims: List[str] = Field(default_factory=list)
    is_verified: bool = True
    sha256_verified: bool = True


class EvidenceCompareResponse(BaseModel):
    """Side-by-side reconciliation between public search findings and private contracts."""
    model_config = ConfigDict(extra="ignore")

    claim_id: str
    claim_title: str
    public_findings: List[EvidenceItem] = Field(default_factory=list)
    private_contract_clauses: List[Dict[str, Any]] = Field(default_factory=list)
    concordance_status: str = Field(..., description="SHIELDED, CONFLICT, or UNSHIELDED")
    legal_shield_active: bool = Field(default=False)
    analysis: str = Field(..., description="Legal rationale for counsel review")
