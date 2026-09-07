"""
Lienmark Targeted Clarification Domain Types.
Pydantic v2 schemas and taxonomy for legal clearance clarification generation.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ProductionRole(str, Enum):
    """Production roles accountable for clearance fulfillment."""
    MUSIC_SUPERVISOR = "Music Supervisor"
    CLEARANCE_COUNSEL = "Clearance Counsel"
    LINE_PRODUCER = "Line Producer"
    CLEARANCE_COORDINATOR = "Clearance Coordinator"
    ARCHIVAL_PRODUCER = "Archival Producer"
    POST_SUPERVISOR = "Post Supervisor"
    PRODUCER = "Producer"


class ClarificationUrgency(str, Enum):
    """Urgency tier for legal clarification turnaround."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKING = "blocking"


class DocumentTypeRequirement(str, Enum):
    """Mandated contract or release artifact required for clearance."""
    SYNC_LICENSE = "Executed Synchronization License"
    MASTER_USE_LICENSE = "Executed Master Use License"
    COMPOSER_WORK_FOR_HIRE = "Composer Work-for-Hire Agreement"
    LIBRARY_MUSIC_LICENSE = "Production Music Library License Agreement"
    TRADEMARK_RELEASE = "Trademark & Product Placement Release"
    LOCATION_RELEASE = "Location Agreement & Release"
    TALENT_DEPICTION_RELEASE = "Life Rights / Talent Depiction Release"
    ARCHIVAL_FOOTAGE_LICENSE = "Archival Footage License Agreement"
    ARTIST_WORK_FOR_HIRE = "Artist Release & Work-for-Hire Agreement"
    COUNSEL_FAIR_USE_OPINION = "Counsel Fair Use Opinion Letter"
    PROP_HOUSE_CLEARANCE = "Prop House Clearance Agreement"
    CUSTOM_CLEARANCE_DOC = "Custom Clearance Documentation"


class ClarificationInput(BaseModel):
    """Input envelope representing an ambiguous claim or missing prerequisite."""
    claim_id: str = Field(
        default_factory=lambda: f"clm_{uuid.uuid4().hex[:8]}",
        description="Unique identifier of the target clearance claim.",
    )
    category: Optional[str] = Field(
        default=None,
        description="IP category (music, brand, artwork, footage, real_person, other).",
    )
    scene_anchor: Optional[str] = Field(
        default=None,
        description="Exact scene beat or timecode anchor (e.g. 'Scene 14, 00:18:22').",
    )
    asset_name_or_cue: str = Field(
        ...,
        description="Asset title, cue description, or proprietary element tag.",
    )
    context_snippet: Optional[str] = Field(
        default=None,
        description="Verbatim screenplay cue, staging context, or dialogue excerpt.",
    )
    flagged_reason: Optional[str] = Field(
        default=None,
        description="Reason primary intake pass flagged uncertainty or missing grant.",
    )
    missing_legal_scope: Optional[str] = Field(
        default=None,
        description="Explicit unresolved legal scope (e.g. master rights, sync rights).",
    )
    existing_licenses: Optional[List[str]] = Field(
        default_factory=list,
        description="Existing partial licenses or agreements on file.",
    )
    designated_role: Optional[Union[ProductionRole, str]] = Field(
        default=None,
        description="Override production role assigned to answer this clarification.",
    )
    production_id: Optional[str] = Field(default=None)
    revision_id: str = Field(default="v8", description="Target script cut revision.")
    stable_lineage_key: Optional[str] = Field(
        default=None,
        description="Persistent asset identifier across revisions.",
    )


class TargetedClarification(BaseModel):
    """
    Legally non-generic clarification request citing exact anchors and options.
    Conforms to Form E&O Underwriting and ADK multi-agent clearance specifications.
    """
    request_id: str = Field(
        default_factory=lambda: f"clrf_{uuid.uuid4().hex[:8]}",
        description="Unique clarification request identifier.",
    )
    claim_id: str = Field(..., description="Target claim identifier.")
    scene_anchor: str = Field(
        ...,
        description="Exact scene beat or timecode anchor (e.g. 'Scene 14, 00:18:22').",
    )
    asset_identity: str = Field(
        ...,
        description="Exact asset identity and ambiguous attribute.",
    )
    ambiguous_attribute: str = Field(
        ...,
        description="Specific ambiguous attribute causing clearance uncertainty.",
    )
    missing_legal_scope: str = Field(
        ...,
        description="Missing legal scope (e.g. master recording and sync rights).",
    )
    suggested_options: List[str] = Field(
        ...,
        min_length=2,
        description="Mutually exclusive suggested pathways to resolve ambiguity.",
    )
    required_document_type: str = Field(
        ...,
        description="Specific mandated legal document required to satisfy clearance.",
    )
    designated_role: str = Field(
        ...,
        description="Designated production role accountable for clarification.",
    )
    question_text: str = Field(
        ...,
        description="Legally non-generic question citing anchor, asset, and required doc.",
    )
    urgency: ClarificationUrgency = Field(default=ClarificationUrgency.HIGH)
    status: str = Field(default="pending")
    revision_id: str = Field(default="v8")
    stable_lineage_key: str = Field(
        ...,
        description="Lineage key ensuring cross-cut traceability.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("suggested_options")
    @classmethod
    def validate_options_count(cls, v: List[str]) -> List[str]:
        """Ensures at least two clear, actionable options are provided."""
        cleaned = [opt.strip() for opt in v if opt and opt.strip()]
        if len(cleaned) < 2:
            raise ValueError("Targeted clarification requires at least 2 distinct suggested options.")
        return cleaned

    def to_domain_request(self, run_id: str = "") -> Any:
        """Converts to canonical backend.domain.models.ClarificationRequest."""
        from backend.domain.models import ClarificationRequest
        return ClarificationRequest(
            request_id=self.request_id,
            run_id=run_id or f"run_{uuid.uuid4().hex[:8]}",
            claim_id=self.claim_id,
            revision_id=self.revision_id,
            stable_lineage_key=self.stable_lineage_key,
            scope_field_missing=self.missing_legal_scope,
            question_text=self.question_text,
            suggested_options=self.suggested_options,
            required_document_type=self.required_document_type,
            assigned_role=self.designated_role,
            status=self.status,
            created_at=self.created_at,
        )


class ClarificationOutput(BaseModel):
    """Structured envelope returned by the clarification generator engine."""
    clarifications: List[TargetedClarification] = Field(default_factory=list)
    generation_mode: str = Field(
        default="rule_based_fallback",
        description="Engine mode used: 'rule_based_fallback' or 'genai_live'.",
    )
    total_count: int = Field(default=0)


class ClarificationError(Exception):
    """Base exception for clarification generation operations."""
    pass


class ClarificationGenerationError(ClarificationError):
    """Raised when clarification synthesis encounters an unrecoverable failure."""
    pass


class ClarificationValidationError(ClarificationError):
    """Raised when generated clarification fails schema validation."""
    pass
