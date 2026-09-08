"""
backend/storage/document_store_audit.py

Cryptographic audit logging and ledger integration for document deduplication.
Dispatches idempotent audit records to CryptographicLedger on cache hit events.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.storage.document_store_types import IngestedDocumentRecord

logger = logging.getLogger("lienmark.storage.document_store.audit")


def _build_dedup_payload(
    matched: IngestedDocumentRecord, filename: str, claims_reused: int, spend_saved: float, latency_ms: float
) -> Dict[str, Any]:
    return {
        "document_id": matched.document_id,
        "filename": filename,
        "content_hash": matched.content_hash,
        "semantic_hash": matched.semantic_hash,
        "claims_reused_count": claims_reused,
        "api_spend_saved_usd": spend_saved,
        "cache_hit_latency_ms": round(latency_ms, 3),
    }


def emit_dedup_audit_event(
    ledger: Optional[Any],
    tenant_id: str,
    production_id: str,
    matched: IngestedDocumentRecord,
    spend_saved: float,
    claims_reused: int,
    latency_ms: float,
    filename: str,
) -> None:
    """Appends an idempotent deduplication cache hit event to the attached cryptographic ledger."""
    if ledger is None:
        return
    payload = _build_dedup_payload(matched, filename, claims_reused, spend_saved, latency_ms)
    try:
        if hasattr(ledger, "append_event"):
            for action in ("DOCUMENT_DEDUP_CACHE_HIT", "DEDUPLICATION_CACHE_HIT"):
                ledger.append_event(
                    tenant_id=tenant_id,
                    production_id=production_id,
                    actor_id="system_dedup_engine",
                    action_type=action,
                    payload=payload,
                )
    except Exception as exc:
        _try_init_and_append_ledger(ledger, tenant_id, production_id, payload, exc)


def _try_init_and_append_ledger(
    ledger: Any,
    tenant_id: str,
    production_id: str,
    payload: Dict[str, Any],
    initial_err: Exception,
) -> None:
    """Initializes uninitialized ledger chains with a genesis block and retries append."""
    try:
        if hasattr(ledger, "initialize_production_ledger"):
            ledger.initialize_production_ledger(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id="system_dedup_engine",
            )
            ledger.append_event(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id="system_dedup_engine",
                action_type="DOCUMENT_DEDUP_CACHE_HIT",
                payload=payload,
            )
            ledger.append_event(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id="system_dedup_engine",
                action_type="DEDUPLICATION_CACHE_HIT",
                payload=payload,
            )
    except Exception as retry_err:
        logger.warning(
            "Could not record dedup event in ledger for '%s': %s (initial: %s)",
            production_id,
            retry_err,
            initial_err,
        )
