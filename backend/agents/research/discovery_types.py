"""
backend/agents/research/discovery_types.py

Domain schemas, enums, and exceptions for mid-run clearance claim discovery.
Sprint 3.2: Mid-Run Claim Discovery & Secondary IP Detection.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.agents.research.query_types import AssetClass


class ProposedClaimStatus(str, Enum):
    """Lifecycle review status for a mid-run proposed claim."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


class SecondaryIPType(str, Enum):
    """Categorical classification of discovered secondary intellectual property."""
    MUSICAL_SAMPLE = "musical_sample"
    INTERPOLATION = "interpolation"
    FEATURED_ARTIST = "featured_artist"
    SECONDARY_TRADEMARK = "secondary_trademark"


class DiscoveryHandlerError(Exception):
    """Base domain exception for mid-run discovery handler errors."""
    pass


class DiscoveryValidationError(DiscoveryHandlerError):
    """Raised when a proposed claim violates intake schema invariants."""
    pass


class ProposedClaimNotFoundError(DiscoveryHandlerError):
    """Raised when a requested proposed claim ID does not exist in the ledger."""
    pass


class ProposedClaimEvent(BaseModel):
    """
    Contract event representing a secondary intellectual property clearance claim
    uncovered dynamically during research agent execution.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposed_claim_id: str = Field(..., min_length=1, description="Unique proposed claim identifier.")
    parent_claim_id: str = Field(..., min_length=1, description="Primary parent claim ID.")
    source_finding_id: str = Field(..., min_length=1, description="Originating finding URL or digest.")
    detected_entity: str = Field(..., min_length=1, description="Detected title, artist, or mark.")
    category: AssetClass = Field(..., description="Target intellectual property asset class.")
    rationale: str = Field(..., min_length=1, description="Legal and factual rationale.")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence score.")
    scene_locator: str = Field(..., min_length=1, description="Scene heading or timecode locator.")
    status: ProposedClaimStatus = Field(
        default=ProposedClaimStatus.PROPOSED,
        description="Current clearance proposal status.",
    )
    discovery_type: SecondaryIPType = Field(
        default=SecondaryIPType.MUSICAL_SAMPLE,
        description="Specific heuristic classification.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC creation timestamp.",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provenance metadata.")

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v: Any) -> ProposedClaimStatus:
        if isinstance(v, ProposedClaimStatus):
            return v
        if isinstance(v, str):
            cleaned = v.strip().lower()
            return ProposedClaimStatus(cleaned)
        raise ValueError(f"Invalid proposed claim status: {v}")
