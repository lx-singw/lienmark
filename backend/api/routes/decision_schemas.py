"""
backend/api/routes/decision_schemas.py

Pydantic v2 request and response schemas for Counsel Decision API endpoints.
Sprint 4.3 - Reviewer Rejection & Directed Re-Investigation Loop.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CounselDecisionRequest(BaseModel):
    """Payload for counsel clearance adjudication (sign-off or rejection)."""

    action: str = Field(
        ...,
        description="Adjudication action: 'sign_off' to approve or 'reject' to direct reinvestigation",
    )
    counsel_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the adjudicating counsel / reviewer",
    )
    counsel_name: str = Field(
        ...,
        min_length=1,
        description="Full display name and professional title of adjudicating counsel",
    )
    directive_text: Optional[str] = Field(
        default=None,
        description="Binding reinvestigation instructions and search constraints on rejection",
    )
    citation_text: Optional[str] = Field(
        default=None,
        description="Statutory, case law, or contractual citation supporting the decision",
    )
    conditions: Optional[List[str]] = Field(
        default=None,
        description="Clearance conditions or delivery caveats if conditionally approved",
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Enforces canonical action values 'sign_off' or 'reject'."""
        clean = v.strip().lower()
        if clean not in ("sign_off", "reject"):
            raise ValueError(
                f"Invalid action '{v}'. Must be either 'sign_off' or 'reject'."
            )
        return clean


class CounselDecisionResponse(BaseModel):
    """Outcome envelope returned upon successful counsel decision adjudication."""

    claim_id: str = Field(..., description="Target rights claim identifier")
    status: str = Field(..., description="Lifecycle status post-decision")
    disposition: str = Field(..., description="Mutually exclusive clearance disposition")
    attempt_number: int = Field(..., ge=1, description="Chronological attempt sequence number")
    reinvestigation_run_id: Optional[str] = Field(
        default=None,
        description="Child investigation run ID spawned if rejected with directive",
    )
    audit_event_id: str = Field(
        ...,
        description="Cryptographic SHA-256 chained audit ledger event identifier",
    )
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of adjudication")

    model_config = ConfigDict(extra="forbid")


class LegalCitationTemplate(BaseModel):
    """Pre-populated statutory, case law, or contractual citation template."""

    template_id: str = Field(..., description="Unique template identifier")
    citation_type: str = Field(
        ...,
        description="Citation category: 'statutory', 'case_law', 'contractual', 'fair_use'",
    )
    title: str = Field(..., description="Human-readable legal doctrine or statute title")
    statutory_reference: Optional[str] = Field(
        default=None,
        description="Formal statutory code or case citation reference",
    )
    citation_text: str = Field(..., description="Pre-formatted standard citation text")
    applicable_right: Optional[str] = Field(
        default=None,
        description="Target right category, e.g. 'composition', 'artwork', 'trademark'",
    )
    conditions: Optional[List[str]] = Field(
        default=None,
        description="Suggested standard clearance conditions tied to this citation",
    )

    model_config = ConfigDict(extra="forbid")


class CitationSuggestionResponse(BaseModel):
    """Envelope containing legal citation templates suggested for a claim."""

    claim_id: str = Field(..., description="Target rights claim identifier")
    suggestions: List[LegalCitationTemplate] = Field(
        default_factory=list,
        description="List of suggested citation templates matching claim context",
    )

    model_config = ConfigDict(extra="forbid")


class AttemptRecord(BaseModel):
    """Historical record of an individual investigation attempt and adjudication."""

    attempt_number: int = Field(..., ge=1, description="Sequential attempt index")
    action: str = Field(..., description="Action taken on this attempt")
    status: str = Field(..., description="Resulting status of this attempt")
    disposition: str = Field(..., description="Clearance disposition assigned")
    counsel_id: Optional[str] = Field(default=None, description="Adjudicating counsel ID")
    counsel_name: Optional[str] = Field(default=None, description="Counsel display name")
    directive_text: Optional[str] = Field(default=None, description="Reinvestigation directive")
    citation_text: Optional[str] = Field(default=None, description="Legal citation recorded")
    conditions: Optional[List[str]] = Field(default=None, description="Assigned conditions")
    reinvestigation_run_id: Optional[str] = Field(
        default=None,
        description="Child run ID spawned from this attempt",
    )
    audit_event_id: Optional[str] = Field(
        default=None,
        description="Ledger event ID for this attempt",
    )
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of attempt record")

    model_config = ConfigDict(extra="forbid")


class AttemptLineageResponse(BaseModel):
    """Complete chronological history of investigation and review attempts for a claim."""

    claim_id: str = Field(..., description="Target rights claim identifier")
    total_attempts: int = Field(..., ge=0, description="Total count of recorded attempts")
    attempts: List[AttemptRecord] = Field(
        default_factory=list,
        description="Chronologically sorted list of prior attempt records",
    )

    model_config = ConfigDict(extra="forbid")
