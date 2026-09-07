"""
reflection_schemas.py

Pydantic v2 schemas for the secondary intake self-reflection extraction pass,
candidate findings, and consolidated claim extraction outputs.
"""

from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from backend.storage.schema import Claim


class RawReflectionFinding(BaseModel):
    """An individual candidate finding identified during the secondary reflection audit."""

    type: Literal["music", "footage", "brand", "real_person", "genai_flag", "other"] = Field(
        ..., description="Standardized claim category."
    )
    scene_ref: str = Field(..., description="Scene locator or heading from screenplay.")
    extracted_description: str = Field(
        ..., description="Minimal, non-identifying description under 20 words."
    )
    target_entity: str = Field(
        ..., description="Identified entity name (e.g., 'Marlboro', 'Clair de Lune')."
    )
    category_focus: Optional[str] = Field(
        default="other",
        description="Focal category: background_prop, ambient_music, subtle_brand, etc.",
    )
    needs_clarification: bool = Field(
        default=False, description="Whether the entity is ambiguous or underspecified."
    )
    flagged_reason: Optional[str] = Field(
        default=None, description="Security or ambiguity reason if flagged."
    )
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Confidence score from model audit."
    )


class ReflectionCandidateOutput(BaseModel):
    """Structured response payload returned by the Gemini reflection pass."""

    findings: List[RawReflectionFinding] = Field(
        default_factory=list, description="List of candidate findings discovered during audit."
    )
    reflection_notes: Optional[str] = Field(
        default=None, description="Model notes on omissions, false negatives, or trapped input."
    )


class ReconciliationMetrics(BaseModel):
    """Execution telemetry from reconciling primary claims with reflection candidates."""

    primary_claim_count: int = Field(default=0, ge=0)
    reflection_claim_count: int = Field(default=0, ge=0)
    deduplicated_claim_count: int = Field(default=0, ge=0)
    new_claims_discovered_count: int = Field(default=0, ge=0)
    adversarial_trapped_count: int = Field(default=0, ge=0)


class ClaimExtractionOutput(BaseModel):
    """Consolidated and reconciled output produced by the Intake Agent."""

    production_id: str = Field(..., description="Target production container ID.")
    claims: List[Claim] = Field(
        default_factory=list, description="Consolidated, de-duplicated rights claims."
    )
    metrics: ReconciliationMetrics = Field(
        default_factory=ReconciliationMetrics,
        description="Detailed telemetry from the extraction and reflection phases.",
    )
    reflection_notes: Optional[str] = Field(
        default=None, description="Audit commentary or observations from the reflection pass."
    )
