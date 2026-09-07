"""
backend/core/intake_audit.py

Layer 4 forensic audit ledger integration committing raw document hashes,
stripped character counts, and sanitization nonces into immutable ledger events.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field

logger = logging.getLogger("lienmark.intake.audit")


class IntakeAuditRecord(BaseModel):
    """Forensic immutable audit record capturing raw intake telemetry."""

    tenant_id: str = Field(description="Tenant or organization identifier")
    production_id: str = Field(description="Production identifier")
    document_id: str = Field(description="Source document or scene identifier")
    raw_document_hash: str = Field(description="SHA-256 hash of raw input content")
    sanitized_text_hash: str = Field(description="SHA-256 hash of sanitized content")
    chars_stripped_count: int = Field(
        default=0, description="Count of stripped Trojan Bidi or control codes"
    )
    nonce: str = Field(description="Cryptographic containment nonce")
    injections_detected_count: int = Field(
        default=0, description="Number of detected prompt injection anomalies"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def compute_content_hash(content: Union[str, bytes]) -> str:
    """Computes a canonical hex SHA-256 hash for raw or sanitized content."""
    raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(raw_bytes).hexdigest()


def create_intake_audit_record(
    tenant_id: str,
    production_id: str,
    document_id: str,
    raw_content: Union[str, bytes],
    sanitized_content: str,
    chars_stripped_count: int,
    nonce: str,
    injections_count: int = 0,
) -> IntakeAuditRecord:
    """Constructs a validated IntakeAuditRecord ready for ledger commitment."""
    raw_hash = compute_content_hash(raw_content)
    san_hash = compute_content_hash(sanitized_content)
    return IntakeAuditRecord(
        tenant_id=tenant_id or "org_default",
        production_id=production_id or "prod_default",
        document_id=document_id or "doc_intake",
        raw_document_hash=raw_hash,
        sanitized_text_hash=san_hash,
        chars_stripped_count=chars_stripped_count,
        nonce=nonce,
        injections_detected_count=injections_count,
    )


def commit_intake_audit_to_ledger(
    ledger: Any,
    record: IntakeAuditRecord,
    actor_id: str = "intake_agent",
) -> Optional[Any]:
    """
    Commits an IntakeAuditRecord to the CryptographicLedger as an immutable event.
    Returns the generated AuditEvent or None if ledger is unavailable.
    """
    if ledger is None:
        logger.debug("No cryptographic ledger supplied; skipping intake commit.")
        return None

    payload: Dict[str, Any] = {
        "action": "DOCUMENT_INTAKE_AUDIT",
        "document_id": record.document_id,
        "raw_document_hash": record.raw_document_hash,
        "sanitized_text_hash": record.sanitized_text_hash,
        "chars_stripped_count": record.chars_stripped_count,
        "nonce": record.nonce,
        "injections_detected_count": record.injections_detected_count,
        "recorded_at": record.timestamp,
    }

    try:
        return ledger.append_event(
            tenant_id=record.tenant_id,
            production_id=record.production_id,
            actor_id=actor_id,
            action_type="INTAKE_AUDIT_RECORD",
            payload=payload,
        )
    except Exception as exc:
        logger.error(f"Failed to commit intake audit event to ledger: {exc}")
        return None
