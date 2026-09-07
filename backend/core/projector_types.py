"""
backend/core/projector_types.py

Domain models and exceptions for deterministic event-sourcing projection.
Sprint 1.3 / Security Specification SEC-SPEC-03-AUDIT-CRYPTO.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field


class ProjectorError(ValueError):
    """Base exception for state projection failures."""
    pass


class InvalidEventError(ProjectorError):
    """Raised when an event in the stream cannot be normalized or validated."""
    pass


class AuditEvent(BaseModel):
    """Immutable audit record representing a discrete ledger entry or state transition."""
    model_config = ConfigDict(frozen=True, extra="allow")
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    production_id: str = Field(..., min_length=1, description="Bound production identifier")
    action: str = Field(..., min_length=1, description="Ledger action type")
    sequence_number: int = Field(default=0, ge=0, description="Strict sequence order")
    claim_id: Optional[str] = Field(default=None, description="Optional target claim ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured event payload")
    actor_id: str = Field(default="system", description="User or agent actor")
    parent_event_hash: Optional[str] = Field(default=None, description="Hash of preceding event")
    event_hash: Optional[str] = Field(default=None, description="SHA-256 event digest")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductionStateProjection(BaseModel):
    """Materialized projection of production clearance state reconstructed from audit events."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    production_id: str = Field(default="", description="Production identifier")
    claims: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    findings: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    risk_scores: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    attorney_decisions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    superseded_claims: Set[str] = Field(default_factory=set)
    budget_events: List[Dict[str, Any]] = Field(default_factory=list)
    total_events_projected: int = Field(default=0, ge=0)
    last_sequence_number: int = Field(default=0, ge=0)
    state_digest: str = Field(default="", description="Deterministic SHA-256 state hash")


def compute_state_digest(state: ProductionStateProjection) -> str:
    """Computes a bit-for-bit deterministic SHA-256 digest of the projected state."""
    canonical_repr = {
        "production_id": state.production_id,
        "claims": state.claims,
        "findings": state.findings,
        "risk_scores": state.risk_scores,
        "attorney_decisions": state.attorney_decisions,
        "superseded_claims": sorted(list(state.superseded_claims)),
        "budget_events": state.budget_events,
        "total_events_projected": state.total_events_projected,
        "last_sequence_number": state.last_sequence_number,
    }
    serialized = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
