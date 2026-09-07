"""
backend/core/conflict_types.py

Data models and schemas for Corroboration and Conflict Arbitration (Sprint 3.3).
Provides Pydantic v2 schemas for evidence stances, authority tiers,
rights layers, and arbitration results.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConflictStance(str, Enum):
    """Canonical classification for evidence agreement or disagreement."""
    CORROBORATING = "corroborating"
    CONTRADICTORY = "contradictory"
    NEUTRAL = "neutral"
    INSUFFICIENT = "insufficient"


class RightsLayer(str, Enum):
    """Categorizes the copyright or IP layer of a creative work."""
    UNDERLYING_WORK = "underlying_work"
    RECORDING_OR_BROADCAST_MASTER = "recording_or_broadcast_master"
    TRADEMARK_OR_BRAND = "trademark_or_brand"
    PUBLICITY_OR_LIKENESS = "publicity_or_likeness"


class SourceAuthorityTier(str, Enum):
    """Authority hierarchy of research and evidence sources."""
    TIER_1_GOVERNMENT_REGISTRY = "tier_1_government_registry"
    TIER_2_ORGANIZATION_PRO_NEWS = "tier_2_organization_pro_news"
    TIER_3_GENERAL_WEB = "tier_3_general_web"


class ClaimStatusAssertion(str, Enum):
    """Rights status asserted by an individual evidence finding."""
    PUBLIC_DOMAIN = "public_domain"
    COPYRIGHTED = "copyrighted"
    LICENSING_REQUIRED = "licensing_required"
    RESTRICTED = "restricted"
    UNVERIFIED = "unverified"
    NEUTRAL_MENTION = "neutral_mention"


class EvidenceFinding(BaseModel):
    """Represents an individual evidence finding from search or registry."""
    finding_id: str
    source_title: str
    source_url: Optional[str] = None
    domain: Optional[str] = None
    excerpt: str
    snippet: Optional[str] = ""
    asserted_status: ClaimStatusAssertion = ClaimStatusAssertion.UNVERIFIED
    asserted_owner: Optional[str] = None
    rights_layer: RightsLayer = RightsLayer.UNDERLYING_WORK
    authority_tier: SourceAuthorityTier = SourceAuthorityTier.TIER_3_GENERAL_WEB
    is_federal_work: bool = False
    statutory_citation: Optional[str] = None
    http_status: Optional[int] = 200
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StancePairEvaluation(BaseModel):
    """Pairwise comparison evaluation between two evidence findings."""
    source_a_id: str
    source_b_id: str
    stance: ConflictStance
    explanation: str
    is_dual_layer_conflict: bool = False


class DualLayerConflictInfo(BaseModel):
    """Details for dual-layer conflicts (e.g. public domain composition vs private master)."""
    is_dual_layer: bool
    underlying_status: str
    underlying_source_ids: List[str] = Field(default_factory=list)
    master_status: str
    master_source_ids: List[str] = Field(default_factory=list)
    rationale: str


class ArbitrationResult(BaseModel):
    """Complete verdict produced by the Conflict Arbiter."""
    claim_id: str
    conflict_detected: bool
    overall_stance: ConflictStance
    risk_score: float = Field(ge=0.0, le=1.0)
    conflict_sources: List[Dict[str, Any]] = Field(default_factory=list)
    corroborating_sources: List[Dict[str, Any]] = Field(default_factory=list)
    dual_layer: Optional[DualLayerConflictInfo] = None
    route_to_exceptions_schedule: bool = False
    exceptions_schedule_state: str = "carried_forward"
    recommended_action: str
    summary: str
    citations: List[Dict[str, str]] = Field(default_factory=list)
