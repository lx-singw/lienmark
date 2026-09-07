"""
underwriting_schemas.py

Pydantic v2 Schemas for Studio Deliverables (Music Cue Sheets, Wrap Checklists,
Clearance Exceptions Schedules, and ISO 27001 / SOC 2 Legal Audit Manifests).
Sprint 6.3: Studio Deliverables.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CueUsageType(str, Enum):
    """Standard PRO music usage classification codes."""
    BI = "BI"  # Background Instrumental
    BV = "BV"  # Background Vocal
    VV = "VV"  # Visual Vocal (Source Music on-camera)
    VI = "VI"  # Visual Instrumental
    MT = "MT"  # Main Title Theme
    ET = "ET"  # End Title Theme
    BG = "BG"  # General Background


class CueComposer(BaseModel):
    """Composer / songwriter credit and split for PRO cue sheets."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Legal name of composer / songwriter")
    pro: str = Field(default="ASCAP", description="Performing Rights Organization (ASCAP, BMI, SESAC, etc.)")
    split_percentage: float = Field(default=100.0, ge=0.0, le=100.0, description="Composer share %")


class CuePublisher(BaseModel):
    """Publisher credit and split for PRO cue sheets."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Music publisher name")
    pro: str = Field(default="ASCAP", description="PRO affiliation")
    split_percentage: float = Field(default=100.0, ge=0.0, le=100.0, description="Publisher share %")


class CueSheetEntry(BaseModel):
    """Itemized musical cue conforming to ASCAP/BMI RapidCue layout."""
    model_config = ConfigDict(extra="ignore")

    cue_number: int = Field(..., ge=1, description="Sequential cue order")
    title: str = Field(..., description="Title of musical work")
    usage: CueUsageType = Field(default=CueUsageType.BI, description="Music usage code")
    timecode_in: str = Field(default="00:00:00:00", description="SMPTE start timecode")
    timecode_out: str = Field(default="00:00:00:00", description="SMPTE end timecode")
    duration_seconds: int = Field(default=0, ge=0, description="Running cue duration in seconds")
    scene: Optional[str] = Field(default=None, description="Scene identifier")
    composers: List[CueComposer] = Field(default_factory=list)
    publishers: List[CuePublisher] = Field(default_factory=list)
    record_label: Optional[str] = Field(default=None, description="Master recording owner / label")
    pro_work_id: Optional[str] = Field(default=None, description="ASCAP / BMI PRO catalog registration ID")
    status: str = Field(default="CLEARED", description="Legal clearance disposition")
    lineage_key: str = Field(..., description="Stable asset lineage identifier")


class CueSheetResponse(BaseModel):
    """Standardized Music Cue Sheet delivery package."""
    model_config = ConfigDict(extra="ignore")

    production_id: str
    production_title: str
    total_cues: int = Field(default=0, ge=0)
    total_duration_seconds: int = Field(default=0, ge=0)
    cues: List[CueSheetEntry] = Field(default_factory=list)


class WrapChecklistItem(BaseModel):
    """Single itemized condition in the post-production wrap gate."""
    model_config = ConfigDict(extra="ignore")

    item_id: str
    category: str = Field(..., description="e.g. Screenplay, Music, Props, SAG-AFTRA, Trademarks")
    title: str
    description: str
    status: str = Field(..., description="CLEARED, BLOCKED, or FLAGGED")
    blocking_reason: Optional[str] = None
    lineage_key: Optional[str] = None


class WrapChecklistResponse(BaseModel):
    """Comprehensive post-production wrap delivery gate evaluating funds release."""
    model_config = ConfigDict(extra="ignore")

    production_id: str
    is_ready_for_funds_release: bool = Field(..., description="100% clearance completeness gate")
    cleared_percentage: float = Field(..., ge=0.0, le=100.0)
    total_items: int = Field(default=0, ge=0)
    cleared_items: int = Field(default=0, ge=0)
    blocking_reasons: List[str] = Field(default_factory=list)
    items: List[WrapChecklistItem] = Field(default_factory=list)
    signed_off: bool = Field(default=False)
    signed_off_by: Optional[str] = None
    signed_off_at: Optional[str] = None


class LegalAuditManifestResponse(BaseModel):
    """Forensic legal audit manifest conforming to ISO/IEC 27001:2022 & SOC 2 Type II."""
    model_config = ConfigDict(extra="ignore")

    manifest_version: str = Field(default="1.0.0")
    iso_standard: str = Field(default="ISO/IEC 27001:2022 / SOC 2 Type II")
    generated_at: str
    production_id: str
    head_hash: str = Field(..., description="Root SHA-256 ledger block hash")
    previous_hash: str = Field(..., description="Genesis or parent chain hash")
    total_ledger_events: int = Field(default=0, ge=0)
    chain_verified: bool = Field(default=True)
    claims_census: Dict[str, int] = Field(default_factory=dict)
    signatories: List[Dict[str, str]] = Field(default_factory=list)
    audit_trail_digest: str = Field(..., description="SHA-256 digest of entire audit log")


class ExportScheduleRequest(BaseModel):
    """Parameters for exporting certified clearance exceptions schedule."""
    model_config = ConfigDict(extra="ignore")

    production_id: str = Field(default="proj_blockbuster_cinema")
    format: str = Field(default="pdf", description="'pdf' or 'json'")
    include_signatures: bool = Field(default=True)
