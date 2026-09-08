"""
Domain models, enums, and path validation logic for the Storage Watcher service.
Enforces strict tenant scoping, sandboxing rejections, and lock metadata contracts.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

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
    is_valid_scope: bool = Field(..., description="True if object is inside locked production or agreements folder")
    organization_id: Optional[str] = Field(None, description="Extracted tenant organization ID")
    production_id: Optional[str] = Field(None, description="Extracted production container ID")
    filename: Optional[str] = Field(None, description="Extracted locked PDF or agreement filename")
    rejection_reason: Optional[str] = Field(None, description="Explicit rationale if rejected")
    folder_type: Optional[str] = Field(None, description="Folder type: 'locked' or 'agreements'")
    is_agreement: bool = Field(default=False, description="True if path resides in canonical agreements folder")


class WatcherConfig(BaseModel):
    """Configuration parameters for Storage Watcher poller and event processor."""
    polling_interval_seconds: float = Field(default=5.0, ge=0.1, description="Interval between poller ticks")
    max_batch_size: int = Field(default=50, ge=1, le=500, description="Maximum objects processed per poll")
    lease_ttl_seconds: float = Field(default=60.0, ge=5.0, description="Distributed lease TTL in seconds")
    bucket_tenant_bindings: Dict[str, str] = Field(default_factory=dict, description="Explicit bucket to tenant org_id bindings")
    enforce_production_authorization: bool = Field(default=False, description="Strictly verify production exists in repository")


GCS_CANONICAL_PATH_REGEX = re.compile(
    r"^organizations/(?P<org_id>[a-zA-Z0-9_-]+)/productions/(?P<prod_id>[a-zA-Z0-9_-]+)/(?P<folder>locked|agreements)/(?P<filename>[a-zA-Z0-9_.-]+)$"
)
GCS_LOCKED_PATH_REGEX = GCS_CANONICAL_PATH_REGEX

WATCHED_PATH_REGEX = re.compile(r"^organizations/[a-zA-Z0-9_-]+/productions/[a-zA-Z0-9_-]+/(?:locked|agreements)/.*")
LOCKED_DRAFT_REGEX = WATCHED_PATH_REGEX

SANDBOX_KEYWORDS = ("/sandbox/", "/drafts/", "/temp/", "/scratch/")


def compute_streaming_sha256(content: Union[bytes, str], chunk_size: int = 65536) -> str:
    """Computes streaming SHA-256 hexadecimal digest of raw binary or string payload."""
    hasher = hashlib.sha256()
    raw = content.encode("utf-8") if isinstance(content, str) else content
    for i in range(0, len(raw), chunk_size):
        hasher.update(raw[i : i + chunk_size])
    return hasher.hexdigest()


def validate_bucket_tenant_binding(
    bucket: str, org_id: str, bindings: Optional[Dict[str, str]] = None
) -> Tuple[bool, Optional[str]]:
    """Validates that storage bucket is bound to the target tenant organization."""
    if not bucket or not bucket.strip():
        return False, "Storage bucket cannot be empty or null"
    if bindings:
        bound_org = bindings.get(bucket)
        if not bound_org or bound_org != org_id:
            return False, f"Bucket '{bucket}' is bound to tenant '{bound_org}', not '{org_id}'"
    match = re.search(r"lienmark-(?P<tenant>[a-zA-Z0-9_-]+)-", bucket)
    if match:
        b_tenant = match.group("tenant").lower()
        norm_org = org_id.lower().removeprefix("org_")
        if b_tenant != norm_org and b_tenant != org_id.lower():
            return False, f"Bucket '{bucket}' tenant '{b_tenant}' does not match organization '{org_id}'"
    return True, None


def validate_production_authorization(prod_id: str) -> Tuple[bool, Optional[str]]:
    """Validates format and syntax of target production container identifier."""
    if not prod_id or not prod_id.strip():
        return False, "Target production ID cannot be empty or null"
    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", prod_id):
        return False, f"Target production ID '{prod_id}' contains invalid characters"
    return True, None


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
    """Validates extensions and matches strict organizations/.../[locked|agreements]/... contract."""
    match = GCS_CANONICAL_PATH_REGEX.match(normalized)
    if not match:
        return FolderScopeResult(
            is_valid_scope=False,
            rejection_reason=(
                f"Path '{raw_path}' does not match required locked schema: "
                "organizations/{org_id}/productions/{prod_id}/locked/{filename}.pdf"
            ),
        )

    folder = match.group("folder")
    filename = match.group("filename")
    is_agr = folder == "agreements"

    if folder == "locked" and not normalized.lower().endswith(".pdf"):
        return FolderScopeResult(
            is_valid_scope=False,
            rejection_reason="Only PDF documents are supported for locked production ingestion",
        )

    return FolderScopeResult(
        is_valid_scope=True,
        organization_id=match.group("org_id"),
        production_id=match.group("prod_id"),
        filename=filename,
        folder_type=folder,
        is_agreement=is_agr,
        rejection_reason=None,
    )


def parse_and_validate_gcs_path(path: str) -> FolderScopeResult:
    """
    Validates that a GCS object path strictly adheres to the locked or agreement hierarchy:
    organizations/{org_id}/productions/{prod_id}/[locked|agreements]/{filename}
    """
    empty_or_traversal = _validate_traversal_and_empty(path)
    if empty_or_traversal is not None:
        return empty_or_traversal

    normalized = path.strip().strip("/")
    sandbox_violation = _check_sandbox_violation(normalized)
    if sandbox_violation is not None:
        return sandbox_violation
    return _match_locked_gcs_contract(normalized, path)


def derive_version_ids(filename: str) -> Tuple[str, str]:
    """Derives baseline and target version IDs from filename, defaulting to v7 / v8."""
    if not filename:
        return "v7", "v8"
    match = re.search(r"v(\d+)", filename, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        return (f"v{num - 1}" if num > 1 else "v1"), f"v{num}"
    return "v7", "v8"


def parse_poll_storage_event(item: object, bucket: str) -> Optional[StorageEvent]:
    """Extracts and normalizes StorageEvent from dict or GCS Blob object."""
    d = item if isinstance(item, dict) else {}
    name = d.get("name") or d.get("object_name") or getattr(item, "name", None)
    etag = d.get("etag") or getattr(item, "etag", None)
    if not name or not etag:
        return None
    size = d.get("size_bytes", d.get("size")) or getattr(item, "size", 0) or 0
    gen = d.get("generation") or getattr(item, "generation", None)
    tc = d.get("time_created_utc", d.get("time_created")) or getattr(item, "time_created", None)
    iso = tc.isoformat() if hasattr(tc, "isoformat") else (str(tc) if tc else datetime.now(timezone.utc).isoformat())
    eid = d.get("event_id") or getattr(item, "id", None) or f"poll_{uuid.uuid4().hex[:12]}"
    return StorageEvent(
        event_id=str(eid), bucket=bucket, object_name=str(name), etag=str(etag),
        size_bytes=int(size), generation=str(gen) if gen is not None else None,
        time_created_utc=iso, content_type=str(d.get("content_type") or getattr(item, "content_type", "application/pdf")),
        source="gcs_poller",
    )


def fetch_blob_bytes(storage_client: Optional[object], bucket: str, name: str) -> bytes:
    """Fetches raw blob bytes from local storage path or cloud client."""
    if os.path.exists(name):
        try:
            with open(name, "rb") as fh:
                return fh.read()
        except Exception:
            pass
    if storage_client and hasattr(storage_client, "bucket"):
        try:
            blob = storage_client.bucket(bucket).get_blob(name)
            if blob and hasattr(blob, "download_as_bytes"):
                return blob.download_as_bytes()
        except Exception:
            pass
    return name.encode("utf-8")


def fetch_gcs_blobs(storage_client: Optional[object], bucket: str, prefix: Optional[str], limit: int) -> List[object]:
    """Lists blobs from GCS using client if available."""
    if not storage_client:
        return []
    try:
        if hasattr(storage_client, "list_blobs"):
            return list(storage_client.list_blobs(bucket, prefix=prefix, max_results=limit))
        if hasattr(storage_client, "bucket"):
            return list(storage_client.bucket(bucket).list_blobs(prefix=prefix, max_results=limit))
    except Exception:
        pass
    return []


