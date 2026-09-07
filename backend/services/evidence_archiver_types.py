"""
evidence_archiver_types.py

Domain models, status enums, configuration schemas, and typed exceptions for
evidence snapshot archiving and citation liveness verification in Lienmark.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class CitationLivenessStatus(str, Enum):
    """
    Classified verification states for external citation links.
    Distinguishes anti-scraper authorization walls from truly dead endpoints.
    """
    LIVE = "LIVE"
    LIVE_RESTRICTED = "LIVE_RESTRICTED"
    DEAD = "DEAD"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"

    @property
    def is_live(self) -> bool:
        """Returns True if the URL is reachable or restricted by access controls."""
        return self in (CitationLivenessStatus.LIVE, CitationLivenessStatus.LIVE_RESTRICTED)

    @property
    def is_restricted(self) -> bool:
        """Returns True if the URL returned an anti-scraper challenge or paywall."""
        return self == CitationLivenessStatus.LIVE_RESTRICTED

    @property
    def is_dead(self) -> bool:
        """Returns True if the endpoint was permanently or temporarily not found."""
        return self == CitationLivenessStatus.DEAD


# Aliases for pre-mortem and audit compliance
CITATION_LIVE = CitationLivenessStatus.LIVE
CITATION_LIVE_RESTRICTED = CitationLivenessStatus.LIVE_RESTRICTED
CITATION_DEAD_404 = CitationLivenessStatus.DEAD
CITATION_ERROR = CitationLivenessStatus.ERROR
CITATION_TIMEOUT = CitationLivenessStatus.TIMEOUT


class SnapshotHttpHeaders(BaseModel):
    """Captured HTTP response headers relevant for caching and evidence provenance."""
    content_type: Optional[str] = Field(default=None, description="MIME content type")
    last_modified: Optional[str] = Field(default=None, description="Last-Modified header")
    etag: Optional[str] = Field(default=None, description="ETag validation token")
    raw_headers: Dict[str, str] = Field(default_factory=dict, description="Normalized response headers")


class LivenessVerificationResult(BaseModel):
    """Result of asynchronous URL liveness verification via HEAD and fallback GET."""
    url: str = Field(..., description="Target citation URL")
    status: CitationLivenessStatus = Field(..., description="Classified liveness status")
    http_status: Optional[int] = Field(default=None, description="Observed HTTP status code")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Verification latency in ms")
    method_used: str = Field(default="HEAD", description="HTTP method used: HEAD or GET")
    headers: SnapshotHttpHeaders = Field(default_factory=SnapshotHttpHeaders, description="Observed headers")
    checked_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC check timestamp",
    )
    error_detail: Optional[str] = Field(default=None, description="Error message if check failed")


class EvidenceSnapshot(BaseModel):
    """
    Immutable content snapshot capturing search citation text, headers, and digest.
    Provides verifiable provenance for clearance and audit workflows.
    """
    snapshot_id: str = Field(..., description="Unique evidence snapshot identifier")
    url: str = Field(..., description="Target citation URL")
    status: CitationLivenessStatus = Field(..., description="Classified liveness status")
    http_status: Optional[int] = Field(default=None, description="Observed HTTP status code")
    raw_snippet: str = Field(..., description="Raw text snippet of evidence citation")
    headers: SnapshotHttpHeaders = Field(default_factory=SnapshotHttpHeaders, description="Observed HTTP headers")
    retrieved_at_utc: str = Field(..., description="ISO 8601 UTC retrieval timestamp")
    payload_digest_sha256: str = Field(..., description="SHA-256 digest of the raw snippet payload")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Verification latency in milliseconds")
    method_used: str = Field(default="HEAD", description="HTTP method used: HEAD or GET")
    tenant_id: str = Field(default="default", description="Tenant organization or studio identifier")
    storage_path: Optional[str] = Field(default=None, description="Storage location (local or GCS URI)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional domain metadata")


class CitationRequest(BaseModel):
    """Batch input model for archiving citations."""
    url: str = Field(..., description="Target citation URL")
    snippet: str = Field(..., description="Raw snippet or excerpt from search results")
    tenant_id: str = Field(default="default", description="Tenant organization or studio identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class EvidenceArchiverConfig(BaseModel):
    """Configuration options for the Evidence Archiver and Snapshot Store."""
    timeout_seconds: float = Field(default=4.0, ge=0.5, le=30.0, description="Liveness check timeout")
    user_agent: str = Field(
        default="Lienmark-Evidence-Archiver/1.0 (+https://lienmark.internal/bot; clearance-audit)",
        description="HTTP User-Agent header string",
    )
    local_storage_dir: str = Field(default="output/evidence_snapshots", description="Local fallback directory")
    gcs_bucket_template: str = Field(
        default="lienmark-{tenant}-evidence-snapshots",
        description="GCS bucket naming template",
    )
    enable_gcs: bool = Field(default=False, description="Whether to attempt GCS upload")
    max_concurrency: int = Field(default=10, ge=1, le=50, description="Max concurrent async checks")


def compute_payload_digest(raw_snippet: str) -> str:
    """Computes SHA-256 hexadecimal digest for raw text payload."""
    content = raw_snippet if raw_snippet is not None else ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class EvidenceArchiverError(Exception):
    """Base typed exception for evidence archiver and snapshot store failures."""
    pass


class SnapshotStorageError(EvidenceArchiverError):
    """Raised when persistence to local disk or GCS fails."""
    pass


class LivenessCheckError(EvidenceArchiverError):
    """Raised when an unrecoverable protocol error occurs during verification."""
    pass


class InvalidCitationUrlError(EvidenceArchiverError):
    """Raised when a provided citation URL violates URI validation rules."""
    pass
