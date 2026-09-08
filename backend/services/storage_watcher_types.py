"""
Domain models, enums, and path validation logic for the Storage Watcher service.
Enforces strict tenant scoping, sandboxing rejections, and lock metadata contracts.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    """Status lifecycle for incoming storage and document ingestion events."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED_OUT_OF_SCOPE = "rejected_out_of_scope"
    FAILED = "failed"


class StorageEvent(BaseModel):
    """Immutable representation of an object storage event."""
    event_id: str = Field(..., description="Unique event notification identifier")
    bucket: str = Field(..., description="Source storage bucket name")
    object_name: str = Field(..., description="Full GCS object path / key")
    etag: str = Field(..., description="Cryptographic ETag digest of the object")
    size_bytes: int = Field(..., ge=0, description="Payload size in bytes")
    generation: Optional[str] = Field(None, description="GCS object generation counter")
    time_created_utc: str = Field(..., description="ISO 8601 UTC creation timestamp")
    content_type: str = Field(default="application/pdf", description="MIME content type")
    source: str = Field(default="eventarc", description="Event emitter: eventarc, gcs_poller, browser_upload")


class FolderScopeResult(BaseModel):
    """Result of evaluating an incoming storage object path against tenant contracts."""
    is_valid_scope: bool = Field(..., description="True if object is inside locked production folder")
    organization_id: Optional[str] = Field(None, description="Extracted tenant organization ID")
    production_id: Optional[str] = Field(None, description="Extracted production container ID")
    filename: Optional[str] = Field(None, description="Extracted locked PDF document filename")
    rejection_reason: Optional[str] = Field(None, description="Explicit rationale if rejected")


class WatcherConfig(BaseModel):
    """Configuration parameters for Storage Watcher poller and event processor."""
    polling_interval_seconds: float = Field(default=5.0, ge=0.1, description="Interval between poller ticks")
    max_batch_size: int = Field(default=50, ge=1, le=500, description="Maximum objects processed per poll")
    lease_ttl_seconds: float = Field(default=60.0, ge=5.0, description="Distributed lease TTL in seconds")


GCS_LOCKED_PATH_REGEX = re.compile(
    r"^organizations/(?P<org_id>[a-zA-Z0-9_-]+)/productions/(?P<prod_id>[a-zA-Z0-9_-]+)/locked/(?P<filename>[a-zA-Z0-9_.-]+\.pdf)$"
)

LOCKED_DRAFT_REGEX = re.compile(
    r"^organizations/[a-zA-Z0-9_-]+/productions/[a-zA-Z0-9_-]+/locked/.*"
)

SANDBOX_KEYWORDS = ("/sandbox/", "/drafts/", "/temp/", "/scratch/")


def _validate_traversal_and_empty(path: str) -> Optional[FolderScopeResult]:
    """Validates that path is non-empty and contains no directory traversal sequences."""
    if not path or not isinstance(path, str) or not path.strip():
        return FolderScopeResult(
            is_valid_scope=False,
            rejection_reason="Path cannot be empty or null",
        )
    if ".." in path:
        return FolderScopeResult(
            is_valid_scope=False,
            rejection_reason="Path traversal attempt detected: '..' not permitted",
        )
    return None


def _check_sandbox_violation(normalized: str) -> Optional[FolderScopeResult]:
    """Inspects path for disallowed writer sandbox prefixes and folder markers."""
    path_with_slashes = f"/{normalized}/"
    for marker in SANDBOX_KEYWORDS:
        if marker in path_with_slashes:
            clean_marker = marker.strip("/")
            return FolderScopeResult(
                is_valid_scope=False,
                rejection_reason=f"Writer sandbox path rejected: contains '{clean_marker}'",
            )
    return None


def _match_locked_gcs_contract(normalized: str, raw_path: str) -> FolderScopeResult:
    """Validates PDF extension and matches strict organizations/.../locked/... contract."""
    if not normalized.lower().endswith(".pdf"):
        return FolderScopeResult(
            is_valid_scope=False,
            rejection_reason="Only PDF documents are supported for locked production ingestion",
        )

    match = GCS_LOCKED_PATH_REGEX.match(normalized)
    if not match:
        return FolderScopeResult(
            is_valid_scope=False,
            rejection_reason=(
                f"Path '{raw_path}' does not match required locked schema: "
                "organizations/{org_id}/productions/{prod_id}/locked/{filename}.pdf"
            ),
        )

    return FolderScopeResult(
        is_valid_scope=True,
        organization_id=match.group("org_id"),
        production_id=match.group("prod_id"),
        filename=match.group("filename"),
        rejection_reason=None,
    )


def parse_and_validate_gcs_path(path: str) -> FolderScopeResult:
    """
    Validates that a GCS object path strictly adheres to the locked production hierarchy:
    organizations/{org_id}/productions/{prod_id}/locked/{filename}.pdf
    """
    empty_or_traversal = _validate_traversal_and_empty(path)
    if empty_or_traversal is not None:
        return empty_or_traversal

    normalized = path.strip().strip("/")
    sandbox_violation = _check_sandbox_violation(normalized)
    if sandbox_violation is not None:
        return sandbox_violation

    return _match_locked_gcs_contract(normalized, path)
