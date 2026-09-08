"""evidence_archiver_types.py
Domain models, status enums, configuration schemas, SSRF validation, and typed
exceptions for evidence snapshot archiving and citation verification in Lienmark.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import ipaddress
import socket
from typing import Any, Dict, Optional, Self
from urllib.parse import urlsplit
from pydantic import BaseModel, Field, model_validator


class CitationLivenessStatus(str, Enum):
    """Classified verification states for external citation links."""
    LIVE = "LIVE"
    LIVE_RESTRICTED = "LIVE_RESTRICTED"
    DEAD = "DEAD"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"

    @property
    def is_live(self) -> bool:
        return self in (CitationLivenessStatus.LIVE, CitationLivenessStatus.LIVE_RESTRICTED)

    @property
    def is_restricted(self) -> bool:
        return self == CitationLivenessStatus.LIVE_RESTRICTED

    @property
    def is_dead(self) -> bool:
        return self == CitationLivenessStatus.DEAD


CITATION_LIVE = CitationLivenessStatus.LIVE
CITATION_LIVE_RESTRICTED = CitationLivenessStatus.LIVE_RESTRICTED
CITATION_DEAD_404 = CitationLivenessStatus.DEAD
CITATION_ERROR = CitationLivenessStatus.ERROR
CITATION_TIMEOUT = CitationLivenessStatus.TIMEOUT


class SnapshotHttpHeaders(BaseModel):
    """Captured HTTP response headers relevant for caching and provenance."""
    content_type: Optional[str] = None
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    raw_headers: Dict[str, str] = Field(default_factory=dict)


class LivenessVerificationResult(BaseModel):
    """Result of asynchronous URL liveness verification via HEAD/GET."""
    url: str
    final_url: str = ""
    status: CitationLivenessStatus
    http_status: Optional[int] = None
    latency_ms: float = Field(default=0.0, ge=0.0)
    method_used: str = "HEAD"
    headers: SnapshotHttpHeaders = Field(default_factory=SnapshotHttpHeaders)
    checked_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_detail: Optional[str] = None
    redirect_count: int = 0
    fetched_body: Optional[str] = None


def compute_payload_digest(raw_snippet: str) -> str:
    """Computes SHA-256 hexadecimal digest for raw text payload."""
    content = raw_snippet if raw_snippet is not None else ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class EvidenceSnapshot(BaseModel):
    """Immutable content snapshot capturing citation text, headers, digests, and provenance."""
    snapshot_id: str
    url: str
    final_url: str = ""
    status: CitationLivenessStatus
    http_status: Optional[int] = None
    raw_snippet: str = ""
    fetched_content: Optional[str] = None
    provider_extraction: Optional[str] = None
    attributable_provider: Optional[str] = None
    excerpt_locators: Dict[str, Any] = Field(default_factory=dict)
    retrieval_time_utc: str = ""
    retrieved_at_utc: Optional[str] = None
    response_digest_sha256: Optional[str] = None
    content_digest_sha256: str = ""
    payload_digest_sha256: Optional[str] = None
    headers: SnapshotHttpHeaders = Field(default_factory=SnapshotHttpHeaders)
    latency_ms: float = Field(default=0.0, ge=0.0)
    method_used: str = "GET"
    tenant_id: str = "default"
    storage_path: Optional[str] = None
    is_historical: bool = False
    historical_label: Optional[str] = None
    original_retrieval_time_utc: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _sync_provenance_inputs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        ret_time = data.get("retrieval_time_utc") or data.get("retrieved_at_utc")
        if not ret_time:
            ret_time = datetime.now(timezone.utc).isoformat()
        data["retrieval_time_utc"] = data["retrieved_at_utc"] = ret_time
        if not data.get("final_url") and data.get("url"):
            data["final_url"] = data["url"]
        content = data.get("raw_snippet") or data.get("fetched_content") or data.get("provider_extraction") or ""
        c_digest = data.get("content_digest_sha256") or data.get("payload_digest_sha256")
        if not c_digest:
            c_digest = compute_payload_digest(content)
        data["content_digest_sha256"] = data["payload_digest_sha256"] = c_digest
        if not data.get("response_digest_sha256") and data.get("fetched_content") is not None:
            data["response_digest_sha256"] = compute_payload_digest(data["fetched_content"])
        if not data.get("excerpt_locators"):
            snip, ftd = data.get("raw_snippet") or "", data.get("fetched_content") or ""
            if snip and ftd and snip in ftd:
                idx = ftd.find(snip)
                data["excerpt_locators"] = {"char_start": idx, "char_end": idx + len(snip), "type": "exact"}
            elif snip:
                data["excerpt_locators"] = {"char_start": 0, "char_end": len(snip), "type": "snippet"}
            else:
                data["excerpt_locators"] = {"type": "content_root"}
        return data

    @model_validator(mode="after")
    def _validate_provenance_requirements(self) -> Self:
        has_fetched = bool(self.fetched_content and self.fetched_content.strip())
        has_provider = bool(self.provider_extraction and self.provider_extraction.strip())
        has_attr = bool(self.attributable_provider and (self.raw_snippet or has_provider))
        if not has_fetched and not has_provider and not has_attr:
            raise ValueError("Requires fetched_content or attributable provider extraction.")
        if not self.excerpt_locators:
            raise ValueError("EvidenceSnapshot requires excerpt_locators.")
        if not self.final_url:
            raise ValueError("EvidenceSnapshot requires final_url.")
        if not self.content_digest_sha256:
            raise ValueError("EvidenceSnapshot requires content_digest_sha256.")
        if self.is_historical:
            self.historical_label = self.historical_label or "historical"
            self.original_retrieval_time_utc = self.original_retrieval_time_utc or self.retrieval_time_utc
        return self


class CitationRequest(BaseModel):
    """Batch input model for archiving citations."""
    url: str
    snippet: str
    tenant_id: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    fetched_content: Optional[str] = None
    provider_extraction: Optional[str] = None
    attributable_provider: Optional[str] = None
    excerpt_locators: Dict[str, Any] = Field(default_factory=dict)
    is_historical: bool = False
    historical_timestamp: Optional[str] = None


class EvidenceArchiverConfig(BaseModel):
    """Configuration options for the Evidence Archiver and Snapshot Store."""
    timeout_seconds: float = Field(default=4.0, ge=0.5, le=30.0)
    user_agent: str = "Lienmark-Evidence-Archiver/1.0 (+https://lienmark.internal/bot; clearance-audit)"
    local_storage_dir: str = "output/evidence_snapshots"
    gcs_bucket_template: str = "lienmark-{tenant}-evidence-snapshots"
    enable_gcs: bool = False
    max_concurrency: int = Field(default=10, ge=1, le=50)
    max_redirects: int = Field(default=10, ge=0, le=20)


BLOCKED_HOSTS = frozenset({"metadata.google.internal", "metadata", "localhost", "169.254.169.254", "[::1]"})


def is_blocked_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Detects RFC 1918, loopback, link-local, or cloud metadata IP addresses."""
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        return is_blocked_ip(ip_obj.ipv4_mapped)
    return (
        ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified
    )


def validate_url_ssrf(url: str) -> None:
    """Validates that a URL does not target private, loopback, link-local, or cloud metadata endpoints."""
    if not url or not isinstance(url, str):
        raise SSRFSecurityError("Citation URL must be a non-empty string.")
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFSecurityError(f"Prohibited scheme '{parsed.scheme}'; only http/https allowed.")
    if not parsed.hostname:
        raise SSRFSecurityError(f"Missing or invalid hostname in citation URL: '{url}'")
    cleaned = parsed.hostname.lower().strip("[]")
    if cleaned in BLOCKED_HOSTS or cleaned.endswith((".internal", ".local", ".localhost")):
        raise SSRFSecurityError(f"SSRF blocked target host: '{cleaned}'")
    try:
        if is_blocked_ip(ipaddress.ip_address(cleaned)):
            raise SSRFSecurityError(f"SSRF blocked target IP: '{cleaned}'")
        return
    except ValueError:
        pass
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        for entry in socket.getaddrinfo(cleaned, port, proto=socket.IPPROTO_TCP):
            if is_blocked_ip(ipaddress.ip_address(entry[4][0])):
                raise SSRFSecurityError(f"SSRF blocked host '{cleaned}' resolving to '{entry[4][0]}'")
    except socket.gaierror:
        pass


class EvidenceArchiverError(Exception):
    """Base typed exception for evidence archiver failures."""
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


class SSRFSecurityError(EvidenceArchiverError):
    """Raised when a target URL violates SSRF security boundaries."""
    pass


class RegistrationExtractionError(EvidenceArchiverError):
    """Raised when registration number extraction fails, e.g. from HEAD checks."""
    pass
