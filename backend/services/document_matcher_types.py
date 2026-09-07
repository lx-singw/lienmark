"""
backend/services/document_matcher_types.py

Domain models, enums, scoring schemas, and path validation for autonomous document matching.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgreementType(str, Enum):
    """Recognized legal clearance contract classifications."""
    SYNC_LICENSE = "Sync License"
    MASTER_USE = "Master Use"
    TRADEMARK_RELEASE = "Trademark Release"
    VARA_WAIVER = "VARA Waiver"
    LOCATION_RELEASE = "Location Release"
    TALENT_RELEASE = "Talent Release"
    CUSTOM_AGREEMENT = "Custom Agreement"


class AgreementParties(BaseModel):
    """Legal parties bound to the agreement."""
    licensor: str = Field(..., description="Grantor or licensor party name")
    licensee: str = Field(..., description="Grantee, licensee, or production company name")


class ExtractedAgreementMetadata(BaseModel):
    """Structured legal metadata extracted from incoming agreement document."""
    document_id: str = Field(
        default_factory=lambda: f"doc_{uuid.uuid4().hex[:10]}",
        description="Unique ingested document identifier",
    )
    file_hash: str = Field(..., description="Cryptographic SHA-256 digest of document")
    parties: AgreementParties
    asset_title: str = Field(..., description="Asset title, cue name, or trademark name")
    agreement_type: str = Field(..., description="Legal agreement classification")
    execution_date: Optional[str] = Field(None, description="ISO execution date if detected")
    grant_territory: Optional[List[str]] = Field(
        default_factory=list,
        description="Explicit territorial grant scope",
    )
    grant_media: Optional[List[str]] = Field(
        default_factory=list,
        description="Permitted exploitation media scope",
    )
    grant_term: Optional[str] = Field(None, description="License duration / term")
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    extraction_source: str = Field(
        default="heuristic_regex",
        description="'gemini_multimodal' or 'heuristic_regex'",
    )
    raw_snippet: Optional[str] = None


class DocumentArrivalEvent(BaseModel):
    """Notification event payload when a document lands in storage or local folder."""
    event_id: str = Field(
        default_factory=lambda: f"arr_{uuid.uuid4().hex[:10]}",
        description="Unique document arrival event ID",
    )
    file_path: str = Field(..., description="Local path or storage object path")
    tenant_id: str = Field(..., description="Owning tenant organization boundary")
    gcs_uri: Optional[str] = Field(None, description="Full GCS URI if in Google Cloud Storage")
    file_hash: str = Field(..., description="SHA-256 cryptographic digest of document content")
    production_id: Optional[str] = Field(None, description="Cinematic production container ID")
    file_size_bytes: int = Field(default=0, ge=0)
    mime_type: str = Field(default="application/pdf")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MatchScoreBreakdown(BaseModel):
    """Granular breakdown of fuzzy matching component scores."""
    asset_score: float = Field(..., ge=0.0, le=1.0)
    parties_score: float = Field(..., ge=0.0, le=1.0)
    agreement_type_score: float = Field(..., ge=0.0, le=1.0)
    composite_score: float = Field(..., ge=0.0, le=1.0)


class MatchingDecision(str, Enum):
    """Actionable decision tier based on confidence threshold."""
    AUTO_RESOLVE = "auto_resolve"
    CANDIDATE_DETECTED = "candidate_document_detected"
    NO_MATCH = "no_match"


class MatchResult(BaseModel):
    """Complete result of dual-key document matching against ClarificationStore."""
    match_id: str = Field(
        default_factory=lambda: f"mtch_{uuid.uuid4().hex[:10]}",
        description="Unique match evaluation ID",
    )
    event_id: str
    document_id: str
    matched_request_id: Optional[str] = None
    matched_claim_id: Optional[str] = None
    decision: MatchingDecision
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: Optional[MatchScoreBreakdown] = None
    dual_key_valid: bool = False
    pipeline_resumed: bool = False
    resolution_channel: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    processed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


GCS_AGREEMENT_URI_REGEX = re.compile(
    r"^gs://lienmark-(?P<tenant>[a-zA-Z0-9_-]+)-locked-drafts/agreements/(?:(?P<prod>[a-zA-Z0-9_-]+)/)?(?P<filename>[^/]+)$"
)
LOCAL_AGREEMENT_PATH_REGEX = re.compile(
    r"^(?:.*[/\\])?output[/\\]agreements(?:[/\\](?P<tenant>[a-zA-Z0-9_-]+))?(?:[/\\](?P<prod>[a-zA-Z0-9_-]+))?[/\\](?P<filename>[^/\\]+)$"
)
ORGANIZATION_LOCKED_REGEX = re.compile(
    r"^organizations/(?P<tenant>[a-zA-Z0-9_-]+)/productions/(?P<prod>[a-zA-Z0-9_-]+)/(?:locked|agreements)/(?P<filename>[^/]+)$"
)


def parse_agreement_path(raw_path: str) -> Dict[str, Optional[str]]:
    """
    Parses storage path or GCS URI extracting tenant_id, production_id, and filename.
    Supports gs://lienmark-<tenant>-locked-drafts/agreements/ and output/agreements/.
    """
    if not raw_path or not isinstance(raw_path, str):
        return {"tenant_id": None, "production_id": None, "filename": None}

    cleaned = raw_path.strip()
    gcs_match = GCS_AGREEMENT_URI_REGEX.match(cleaned)
    if gcs_match:
        return {
            "tenant_id": gcs_match.group("tenant"),
            "production_id": gcs_match.group("prod"),
            "filename": gcs_match.group("filename"),
        }

    org_match = ORGANIZATION_LOCKED_REGEX.match(cleaned.replace("\\", "/"))
    if org_match:
        return {
            "tenant_id": org_match.group("tenant"),
            "production_id": org_match.group("prod"),
            "filename": org_match.group("filename"),
        }

    local_match = LOCAL_AGREEMENT_PATH_REGEX.match(cleaned)
    if local_match:
        return {
            "tenant_id": local_match.group("tenant"),
            "production_id": local_match.group("prod"),
            "filename": local_match.group("filename"),
        }

    parts = re.split(r"[/\\]", cleaned)
    filename = parts[-1] if parts else None
    return {"tenant_id": None, "production_id": None, "filename": filename}
