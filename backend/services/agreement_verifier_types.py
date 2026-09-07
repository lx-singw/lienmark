"""
backend/services/agreement_verifier_types.py

Domain models, enums, and Pydantic v2 schemas for agreement verification.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TerritoryScope(str, Enum):
    """Territory coverage classification."""
    WORLDWIDE = "worldwide"
    NORTH_AMERICA = "north_america"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class MediaScope(str, Enum):
    """Media rights exploitation scope."""
    ALL_MEDIA = "all_media"
    THEATRICAL = "theatrical"
    STREAMING = "streaming"
    HOME_VIDEO = "home_video"
    VOD = "vod"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class TermScope(str, Enum):
    """Temporal duration of granted rights."""
    PERPETUAL = "perpetual"
    IN_LICENSE_TERM = "in_license_term"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class RightType(str, Enum):
    """Atomic rights granted under the contract."""
    SYNCHRONIZATION = "synchronization"
    MASTER_RECORDING = "master_recording"
    TRADEMARK_APPEARANCE = "trademark_appearance"
    ARTWORK_DISPLAY = "artwork_display"
    LIFE_RIGHTS = "life_rights"
    OTHER = "other"


class VerificationStatus(str, Enum):
    """Overall outcome of legal agreement verification."""
    VERIFIED_COMPLIANT = "verified_compliant"
    CONDITIONALLY_COMPLIANT = "conditionally_compliant"
    NON_COMPLIANT = "non_compliant"
    REJECTED = "rejected"


class SignatureParty(BaseModel):
    """Execution signature details for a contracting party."""
    model_config = ConfigDict(extra="forbid")

    party_name: str = Field(..., min_length=1)
    party_role: str = Field(default="licensor", description="licensor, licensee, or producer")
    is_signed: bool = Field(default=False)
    signed_date: Optional[str] = Field(default=None)
    signer_title: Optional[str] = Field(default=None)


class ExecutionValidity(BaseModel):
    """Verification results for contractual signature blocks and execution date."""
    model_config = ConfigDict(extra="forbid")

    is_executed: bool = Field(default=False)
    licensor_signed: bool = Field(default=False)
    licensee_signed: bool = Field(default=False)
    execution_date: Optional[str] = Field(default=None)
    is_date_within_window: bool = Field(default=True)
    execution_deficiencies: List[str] = Field(default_factory=list)


class GrantScopeAnalysis(BaseModel):
    """Detailed breakdown of territory, media, term, and rights scope."""
    model_config = ConfigDict(extra="forbid")

    territory_scope: TerritoryScope = Field(default=TerritoryScope.UNKNOWN)
    permitted_territories: List[str] = Field(default_factory=list)
    is_worldwide: bool = Field(default=False)
    media_scope: MediaScope = Field(default=MediaScope.UNKNOWN)
    permitted_media: List[str] = Field(default_factory=list)
    has_all_media_devised: bool = Field(default=False)
    term_scope: TermScope = Field(default=TermScope.UNKNOWN)
    is_perpetual: bool = Field(default=False)
    term_expiry: Optional[str] = Field(default=None)
    rights_granted: List[RightType] = Field(default_factory=list)
    satisfies_territory: bool = Field(default=False)
    satisfies_media: bool = Field(default=False)
    satisfies_term: bool = Field(default=False)
    satisfies_rights: bool = Field(default=False)
    scope_deficiencies: List[str] = Field(default_factory=list)


class VerificationCitation(BaseModel):
    """Tamper-evident citation tying verification results to agreement clauses."""
    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(default_factory=lambda: f"cit_{uuid.uuid4().hex[:8]}")
    clause_type: str = Field(..., description="territory, media, term, rights, execution")
    quoted_clause: str = Field(...)
    page_number: Optional[int] = Field(default=None)
    source_clause_ref: Optional[str] = Field(default=None)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class ProductionRequirements(BaseModel):
    """Target production exploitation scope requirements."""
    model_config = ConfigDict(extra="forbid")

    required_territory: str = Field(default="worldwide")
    required_media: List[str] = Field(
        default_factory=lambda: ["theatrical", "streaming", "home_video", "vod"]
    )
    requires_perpetual: bool = Field(default=True)
    production_start: Optional[str] = Field(default=None)
    production_end: Optional[str] = Field(default=None)
    distribution_window_start: Optional[str] = Field(default=None)
    required_rights: List[RightType] = Field(default_factory=list)


class AgreementDocumentInput(BaseModel):
    """Input representation of an agreement document submitted for verification."""
    model_config = ConfigDict(extra="allow")

    agreement_id: str = Field(..., min_length=1)
    document_name: str = Field(..., min_length=1)
    licensor: str = Field(..., min_length=1)
    licensee: str = Field(default="Production Co.")
    execution_date: Optional[str] = Field(default=None)
    territories: List[str] = Field(default_factory=list)
    media: List[str] = Field(default_factory=list)
    term: Optional[str] = Field(default=None)
    term_expiry: Optional[str] = Field(default=None)
    granted_rights: List[str] = Field(default_factory=list)
    signatures: List[SignatureParty] = Field(default_factory=list)
    clauses: Dict[str, str] = Field(default_factory=dict)
    raw_text: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None)


class AgreementVerificationResult(BaseModel):
    """Authoritative legal verification result for post-resumption clearance."""
    model_config = ConfigDict(extra="forbid")

    verification_id: str = Field(default_factory=lambda: f"vrf_{uuid.uuid4().hex[:10]}")
    agreement_id: str = Field(...)
    claim_id: str = Field(...)
    is_valid: bool = Field(...)
    compliance_score: float = Field(..., ge=0.0, le=1.0)
    missing_clauses: List[str] = Field(default_factory=list)
    grant_scope: GrantScopeAnalysis = Field(...)
    execution_validity: ExecutionValidity = Field(...)
    verified_citations: List[VerificationCitation] = Field(default_factory=list)
    requires_counsel_rider: bool = Field(default=False)
    rider_reasons: List[str] = Field(default_factory=list)
    verified_license_ref: Optional[str] = Field(default=None)
    status: VerificationStatus = Field(default=VerificationStatus.NON_COMPLIANT)
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ledger_event_id: Optional[str] = Field(default=None)
    notes: str = Field(default="")
