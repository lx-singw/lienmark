"""
backend/storage/document_store_types.py

Domain models, data contracts, and domain exceptions for the multi-tenant
document store and deduplication subsystem.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Set
from pydantic import BaseModel, ConfigDict, Field, field_validator


VALID_DOCUMENT_FORMATS: Set[str] = {
    "pdf",
    "fdx",
    "fountain",
    "edl",
    "plaintext",
}


class DocumentProcessingStatus(str, Enum):
    """Lifecycle processing status of an ingested document."""

    PENDING = "pending"
    COMMITTED = "committed"
    FAILED = "failed"


class DeduplicationError(Exception):
    """Base exception for document deduplication and store errors."""
    pass


class DocumentNotFoundError(DeduplicationError):
    """Raised when a requested ingested document record is not found."""
    pass


class CrossTenantAccessViolation(DeduplicationError):
    """Raised when an operation attempts unauthorized cross-tenant data access."""
    pass


class IngestedDocumentRecord(BaseModel):
    """
    Immutable representation of an ingested and parsed document record.
    
    Scoped strictly to a tenant boundary (tenant_id) and bound to a production.
    Maintains both raw content SHA-256 and semantic hashes for rename invariance.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(..., min_length=1, description="Unique document record identifier")
    tenant_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    production_id: str = Field(..., min_length=1, description="Bound cinematic production ID")
    filename: str = Field(..., min_length=1, description="Original ingested document file name")
    content_hash: str = Field(..., min_length=16, description="Raw SHA-256 hex digest of file bytes")
    semantic_hash: Optional[str] = Field(default=None, description="Normalized semantic SHA-256 digest")
    format: str = Field(..., description="Document format: pdf, fdx, fountain, edl, plaintext")
    page_count: int = Field(default=0, ge=0, description="Total pages or calculated page units")
    scene_count: int = Field(default=0, ge=0, description="Total scenes parsed from screenplay or cutlist")
    version_id: str = Field(default="v1", description="Bound production version or script iteration")
    claims_count: int = Field(default=0, ge=0, description="Extracted legal or clearance claims count")
    processing_status: DocumentProcessingStatus = Field(
        default=DocumentProcessingStatus.PENDING,
        description="Lifecycle processing status: pending, committed, or failed",
    )
    linked_baseline_version_id: Optional[str] = Field(
        default=None,
        description="Linked downstream investigation baseline version identifier",
    )
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary parser or extractor metadata")

    @property
    def org_id(self) -> str:
        """Alias for tenant_id maintaining backwards compatibility."""
        return self.tenant_id

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_DOCUMENT_FORMATS:
            raise ValueError(
                f"Invalid document format '{value}'. Must be one of: {sorted(VALID_DOCUMENT_FORMATS)}"
            )
        return normalized

    @field_validator("tenant_id", "production_id", "document_id", "content_hash")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        if not value or not isinstance(value, str) or not value.strip():
            raise ValueError("Field must be a non-empty string.")
        return value.strip()


class DedupLookupResult(BaseModel):
    """
    Telemetry and resolution payload returned by deduplication lookups.
    
    Provides sub-100ms cache-hit verification and exact financial spend savings.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_duplicate: bool = Field(..., description="True if an identical document was found in tenant scope")
    matched_document: Optional[IngestedDocumentRecord] = Field(
        default=None,
        description="Matched existing record if duplicate was detected",
    )
    cache_hit_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution latency in milliseconds for deduplication check",
    )
    claims_reused_count: int = Field(
        default=0,
        ge=0,
        description="Number of existing legal claims reused without model re-extraction",
    )
    api_spend_saved_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Financial USD savings calculated from avoided re-parsing and re-extraction",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation of lookup resolution (e.g. raw match, semantic match)",
    )
