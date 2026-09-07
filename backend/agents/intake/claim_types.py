"""
Lienmark Multimodal Intake Domain Types.
Canonical Pydantic v2 schemas and taxonomy for clearance claim extraction.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ClaimCategory(str, Enum):
    """
    Categorical taxonomy for entertainment intellectual property clearance claims.
    """
    MUSIC = "music"
    BRAND = "brand"
    ARTWORK = "artwork"
    FOOTAGE = "footage"
    HISTORICAL_FIGURE = "historical_figure"
    REAL_PERSON = "real_person"
    SYNTHETIC_AI = "synthetic_ai"
    OTHER = "other"


class ExtractedClaim(BaseModel):
    """
    Individual clearance claim extracted from script, storyboard, or media.
    """
    claim_id: str = Field(
        description="Unique identifier for the extracted claim."
    )
    category: ClaimCategory = Field(
        description="Clearance legal classification category."
    )
    scene_or_timecode: str = Field(
        description="Scene heading, page number, or timecode location."
    )
    extracted_description: str = Field(
        description="Succinct description of the clearable asset, maximum 20 words."
    )
    context_snippet: Optional[str] = Field(
        default=None,
        description="Verbatim excerpt or visual staging context."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score between 0.0 and 1.0."
    )
    needs_clarification: bool = Field(
        default=False,
        description="Flag indicating counsel review or factual verification required."
    )
    flagged_reason: Optional[str] = Field(
        default=None,
        description="Specific legal risk or ambiguity explanation if flagged."
    )

    @field_validator("extracted_description")
    @classmethod
    def validate_and_normalize_word_count(cls, v: str) -> str:
        """Enforces max 20 words boundary, normalizing whitespace."""
        cleaned = " ".join(v.strip().split())
        words = cleaned.split(" ")
        if len(words) > 20:
            return " ".join(words[:20])
        return cleaned


class ClaimExtractionOutput(BaseModel):
    """
    Structured envelope returned by the intake extraction pipeline.
    """
    claims: List[ExtractedClaim] = Field(
        default_factory=list,
        description="List of extracted clearance claims."
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Identifier of source document or scene."
    )
    extraction_model: Optional[str] = Field(
        default=None,
        description="Identifier of model or fallback engine that extracted claims."
    )
    total_claims_count: int = Field(
        default=0,
        description="Total number of claims extracted."
    )


class MultimodalIntakeInput(BaseModel):
    """
    Standard input envelope for multimodal intake extraction.
    """
    content: str = Field(
        default="",
        description="Script text, transcript, or narrative context."
    )
    media_type: str = Field(
        default="text/plain",
        description="MIME type of primary or accompanying asset."
    )
    media_bytes: Optional[bytes] = Field(
        default=None,
        description="Raw binary content for images, audio, video, or documents."
    )
    media_uri: Optional[str] = Field(
        default=None,
        description="Google Cloud Storage URI or local file path."
    )
    scene_cue: Optional[str] = Field(
        default=None,
        description="Scene heading, timecode, or structural reference."
    )


class IntakeExtractionError(Exception):
    """Base domain exception for intake extraction pipeline."""
    pass


class SchemaValidationRetryExhaustedError(IntakeExtractionError):
    """Raised when JSON schema validation fails after maximum repair retries."""
    pass


class RateLimitExceededError(IntakeExtractionError):
    """Raised when leaky bucket acquisition times out under quota backpressure."""
    pass
