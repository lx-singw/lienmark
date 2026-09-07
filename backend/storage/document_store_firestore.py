"""
backend/storage/document_store_firestore.py

Firestore persistence adapter for the multi-tenant document store.
Manages physical documents under /organizations/{org_id}/documents/{doc_id}.
Enforces strict tenant isolation on every read and write operation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    IngestedDocumentRecord,
)

logger = logging.getLogger("lienmark.storage.document_store.firestore")


def save_document_to_firestore(
    client: Optional[Any], doc: IngestedDocumentRecord
) -> None:
    """Persists an ingested document to /organizations/{org_id}/documents/{doc_id}."""
    if client is None:
        return

    try:
        db = getattr(client, "db", client)
        if hasattr(db, "collection"):
            doc_ref = (
                db.collection("organizations")
                .document(doc.tenant_id)
                .collection("documents")
                .document(doc.document_id)
            )
            doc_ref.set(doc.model_dump(), merge=True)
    except Exception as exc:
        logger.error(
            "Firestore write failed for doc '%s' in tenant '%s': %s",
            doc.document_id,
            doc.tenant_id,
            exc,
        )


def lookup_document_by_hash_from_firestore(
    client: Optional[Any],
    tenant_id: str,
    content_hash: str,
    semantic_hash: Optional[str] = None,
) -> Optional[IngestedDocumentRecord]:
    """Queries Firestore documents within tenant boundary matching raw or semantic hash."""
    if client is None:
        return None

    try:
        db = getattr(client, "db", client)
        if not hasattr(db, "collection"):
            return None

        coll = db.collection("organizations").document(tenant_id).collection("documents")
        # 1. Check raw content_hash
        snaps = list(coll.where("content_hash", "==", content_hash).limit(1).stream())
        if snaps and snaps[0].exists:
            return _validate_and_extract_record(snaps[0].to_dict() or {}, tenant_id)

        # 2. Check semantic_hash fallback
        if semantic_hash:
            snaps_sem = list(coll.where("semantic_hash", "==", semantic_hash).limit(1).stream())
            if snaps_sem and snaps_sem[0].exists:
                return _validate_and_extract_record(snaps_sem[0].to_dict() or {}, tenant_id)
    except Exception as exc:
        logger.warning(
            "Firestore lookup failed for tenant '%s' and hash '%s': %s",
            tenant_id,
            content_hash,
            exc,
        )
    return None


def get_document_from_firestore(
    client: Optional[Any], tenant_id: str, document_id: str
) -> Optional[IngestedDocumentRecord]:
    """Fetches a specific document by ID from Firestore, validating tenant boundary."""
    if client is None:
        return None

    try:
        db = getattr(client, "db", client)
        if hasattr(db, "collection"):
            snap = (
                db.collection("organizations")
                .document(tenant_id)
                .collection("documents")
                .document(document_id)
                .get()
            )
            if snap.exists:
                return _validate_and_extract_record(snap.to_dict() or {}, tenant_id)
    except Exception as exc:
        logger.warning(
            "Firestore get_document failed for doc '%s' in tenant '%s': %s",
            document_id,
            tenant_id,
            exc,
        )
    return None


def _validate_and_extract_record(
    data: dict[str, Any], expected_tenant_id: str
) -> IngestedDocumentRecord:
    """Validates tenant boundary on Firestore document data and deserializes model."""
    doc_tenant = data.get("tenant_id")
    if doc_tenant != expected_tenant_id:
        raise CrossTenantAccessViolation(
            f"Cross-tenant data egress detected: doc tenant '{doc_tenant}' != expected '{expected_tenant_id}'"
        )
    return IngestedDocumentRecord.model_validate(data)
