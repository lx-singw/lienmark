"""
backend/storage/document_store_telemetry.py

Telemetry formatting, latency tracking, and parameter validation for document deduplication.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional, Tuple

from backend.storage.document_store_audit import emit_dedup_audit_event
from backend.storage.document_store_parser import calculate_api_spend_saved
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DeduplicationError,
    DedupLookupResult,
    IngestedDocumentRecord,
)

logger = logging.getLogger("lienmark.storage.document_store.telemetry")


def clean_lookup_parameters(
    tenant_id: str, content_hash: str, semantic_hash: Optional[str]
) -> Tuple[str, str, Optional[str]]:
    """Validates and trims lookup parameter strings."""
    if not tenant_id or not isinstance(tenant_id, str) or not tenant_id.strip():
        raise DeduplicationError("tenant_id must be a non-empty string.")
    if not content_hash or not isinstance(content_hash, str) or not content_hash.strip():
        raise DeduplicationError("content_hash must be a non-empty string.")
    s_hash = semantic_hash.strip() if (semantic_hash and isinstance(semantic_hash, str)) else None
    return tenant_id.strip(), content_hash.strip(), s_hash


def validate_scope_parameters(
    tenant_id: str, production_id: str, content_bytes: bytes
) -> str:
    """Defensively validates tenant and payload parameters."""
    if not tenant_id or not isinstance(tenant_id, str) or not tenant_id.strip():
        raise DeduplicationError("tenant_id must be a non-empty string.")
    if not production_id or not isinstance(production_id, str) or not production_id.strip():
        raise DeduplicationError("production_id must be a non-empty string.")
    if not isinstance(content_bytes, (bytes, bytearray)):
        raise TypeError("content_bytes must be bytes or bytearray.")
    return tenant_id.strip()


def determine_match_reason(matched: IngestedDocumentRecord, raw_hash: str) -> str:
    """Resolves diagnostic explanation distinguishing raw and semantic hash matches."""
    if matched.content_hash == raw_hash:
        return "Exact content hash match detected"
    return "Normalized semantic hash match detected"


def build_duplicate_hit_result(
    matched: IngestedDocumentRecord,
    tenant_id: str,
    production_id: str,
    filename: str,
    start_time: float,
    raw_hash: str,
    claims_count: int,
    ledger: Optional[Any],
) -> Tuple[IngestedDocumentRecord, DedupLookupResult]:
    """Builds telemetry and emits audit log for duplicate cache hits."""
    if matched.tenant_id != tenant_id:
        raise CrossTenantAccessViolation(
            f"Cross-tenant match intercepted: {matched.tenant_id} != {tenant_id}"
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    if elapsed_ms >= 100.0:
        logger.warning("Deduplication latency exceeded 100ms SLA: %.2f ms", elapsed_ms)

    reused_claims = matched.claims_count if matched.claims_count > 0 else claims_count
    spend_saved = calculate_api_spend_saved(matched.page_count, reused_claims)

    emit_dedup_audit_event(
        ledger, tenant_id, production_id, matched, spend_saved,
        reused_claims, elapsed_ms, filename
    )

    telemetry = DedupLookupResult(
        is_duplicate=True,
        matched_document=matched,
        cache_hit_latency_ms=round(elapsed_ms, 3),
        claims_reused_count=reused_claims,
        api_spend_saved_usd=spend_saved,
        reason=determine_match_reason(matched, raw_hash),
    )
    return matched, telemetry


def build_new_document_result(start_time: float) -> DedupLookupResult:
    """Builds telemetry result for newly registered documents."""
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    return DedupLookupResult(
        is_duplicate=False,
        matched_document=None,
        cache_hit_latency_ms=round(elapsed_ms, 3),
        claims_reused_count=0,
        api_spend_saved_usd=0.0,
        reason="New document registered; no previous match found",
    )
