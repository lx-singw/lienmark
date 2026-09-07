"""
backend/services/notifier_types.py

Domain models, delivery records, and formatting helpers for clarification dispatching.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.domain.models import ClarificationRequest
from backend.storage.ledger_types import compute_canonical_digest


class NotificationEventType(str, Enum):
    """Supported notification and webhook event types."""
    CLARIFICATION_REQUESTED = "clarification.requested"
    CLARIFICATION_RESOLVED = "clarification.resolved"
    CLARIFICATION_CANCELLED = "clarification.cancelled"


class DeliveryStatus(str, Enum):
    """Outcome status for webhook and alert delivery attempts."""
    SUCCESS = "success"
    FALLBACK_LOGGED = "fallback_logged"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationDeliveryRecord(BaseModel):
    """Audit record capturing the delivery attempt of a clarification notification."""
    delivery_id: str = Field(
        default_factory=lambda: f"dlv_{uuid.uuid4().hex[:12]}",
        description="Unique delivery attempt identifier",
    )
    event_type: str = Field(default=NotificationEventType.CLARIFICATION_REQUESTED.value)
    request_id: str
    claim_id: str
    tenant_id: str
    webhook_url: Optional[str] = None
    webhook_status: DeliveryStatus = DeliveryStatus.SKIPPED
    webhook_digest: Optional[str] = None
    email_recipient: Optional[str] = None
    email_status: DeliveryStatus = DeliveryStatus.SKIPPED
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error_detail: Optional[str] = None


class NotificationDispatchResult(BaseModel):
    """Aggregate result envelope returned by the notification dispatcher."""
    success: bool
    event_type: str
    request_id: str
    payload_digest: str
    webhook_delivered: bool
    email_delivered: bool
    delivery_record: NotificationDeliveryRecord


def build_clarification_webhook_payload(
    clarification: ClarificationRequest,
    tenant_id: str,
) -> Dict[str, Any]:
    """Constructs the canonical webhook envelope with consistent field ordering."""
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "event_type": NotificationEventType.CLARIFICATION_REQUESTED.value,
        "tenant_id": tenant_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "request_id": clarification.request_id,
            "run_id": clarification.run_id,
            "claim_id": clarification.claim_id,
            "revision_id": clarification.revision_id,
            "stable_lineage_key": clarification.stable_lineage_key,
            "question_text": clarification.question_text,
            "suggested_options": clarification.suggested_options or [],
            "required_document_type": clarification.required_document_type,
            "assigned_role": clarification.assigned_role,
            "status": clarification.status,
            "scope_field_missing": clarification.scope_field_missing,
        },
    }


def _build_email_text_body(
    clrf: ClarificationRequest,
    tenant_id: str,
    options_list: str,
    doc_required: str,
) -> str:
    """Renders plain text body for email alert."""
    return (
        f"Lienmark E&O Clearance Notice\nTenant ID: {tenant_id}\n"
        f"Run ID: {clrf.run_id}\nRequest ID: {clrf.request_id}\n"
        f"Target Claim: {clrf.claim_id} (Rev {clrf.revision_id})\n"
        f"Assigned Role: {clrf.assigned_role}\n\n"
        f"Question:\n{clrf.question_text}\n\n"
        f"Suggested Pathways:\n{options_list}\n\n"
        f"Mandated Document Type: {doc_required}\n\n"
        f"Respond via the Lienmark Dashboard or REST API."
    )


def _build_email_html_body(
    clrf: ClarificationRequest,
    options_html: str,
    doc_required: str,
) -> str:
    """Renders HTML body for email alert."""
    return (
        f"<h2>Lienmark E&O Clearance Notice</h2>"
        f"<p><strong>Clarification Request:</strong> {clrf.request_id}<br>"
        f"<strong>Target Claim:</strong> {clrf.claim_id} (Rev {clrf.revision_id})<br>"
        f"<strong>Assigned Role:</strong> {clrf.assigned_role}</p>"
        f"<h3>Question</h3><p>{clrf.question_text}</p>"
        f"<h3>Suggested Pathways</h3><ul>{options_html}</ul>"
        f"<p><strong>Mandated Document:</strong> {doc_required}</p>"
    )


def format_clarification_email_alert(
    clarification: ClarificationRequest,
    tenant_id: str,
) -> Tuple[str, str, str]:
    """Formats notification email returning (subject, body_text, body_html)."""
    subject = (
        f"[ACTION REQUIRED] Legal Clarification Requested: "
        f"Claim {clarification.claim_id} ({clarification.assigned_role})"
    )
    opts = clarification.suggested_options or ["No preset options provided"]
    opts_txt = "\n".join(f"  - {opt}" for opt in opts)
    opts_html = "".join(f"<li>{opt}</li>" for opt in opts)
    doc_req = clarification.required_document_type or "None specified"

    body_txt = _build_email_text_body(clarification, tenant_id, opts_txt, doc_req)
    body_html = _build_email_html_body(clarification, opts_html, doc_req)
    return subject, body_txt, body_html
