"""
ledger_schemas.py

Pydantic v2 Schemas for Decision History, Timeline & Cryptographic Ledger Verification.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DecisionTimelineEvent(BaseModel):
    """Chronological decision timeline item projected from immutable AuditEvent."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(..., description="Immutable audit event identifier")
    sequence_number: int = Field(..., ge=1, description="Monotonic block sequence number")
    action_type: str = Field(..., description="GENESIS, COUNSEL_DECISION, SUPERSEDED, etc.")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    actor_id: str = Field(..., description="Actor identifier")
    actor_name: str = Field(default="Clearance Counsel", description="Display name of actor")
    claim_id: Optional[str] = Field(default=None, description="Associated claim ID")
    claim_title: Optional[str] = Field(default=None, description="Associated claim title")
    decision_status: Optional[str] = Field(default=None, description="APPROVED, FLAGGED, REJECTED, etc.")
    counsel_rationale: Optional[str] = Field(default=None, description="Counsel rationale or disposition reason")
    entry_hash: str = Field(..., description="Canonical SHA-256 block hash")
    previous_event_hash: str = Field(..., description="Parent SHA-256 block hash")
    payload_digest: str = Field(..., description="Canonical payload SHA-256 digest")
    is_superseded: bool = Field(default=False, description="Whether this decision has been superseded")
    superseded_event_id: Optional[str] = Field(default=None, description="ID of prior event superseded")
    dual_signatures: List[Dict[str, Any]] = Field(default_factory=list, description="Cryptographic digital signatures")


class DecisionChainResponse(BaseModel):
    """Response model representing the chronological decision history of a production or claim."""
    model_config = ConfigDict(extra="ignore")

    production_id: str = Field(..., description="Target production identifier")
    is_chain_valid: bool = Field(default=True, description="Cryptographic chain continuity status")
    chain_length: int = Field(default=0, ge=0, description="Total number of ledger events")
    head_event_hash: Optional[str] = Field(default=None, description="Current head SHA-256 entry hash")
    events: List[DecisionTimelineEvent] = Field(default_factory=list, description="Ordered event history")


class LedgerVerificationResponse(BaseModel):
    """Deep cryptographic proof of an individual block and chain back-pointers."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    sequence_number: int
    entry_hash: str
    previous_event_hash: str
    payload_digest: str
    is_valid: bool = True
    verification_message: str
    canonical_payload: Dict[str, Any] = Field(default_factory=dict)
    dual_signatures: List[Dict[str, Any]] = Field(default_factory=list)


class SupersessionRecord(BaseModel):
    """Lineage record of a non-destructive supersession override."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    superseded_event_id: str
    superseding_action: str
    counsel_rationale: str
    timestamp: str
    actor_id: str
