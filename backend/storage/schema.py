"""
schema.py

Lienmark Data Schema Definitions.
Mirrors docs/06-data-schema.md exactly with full Pydantic data models for:
- Production
- Claim
- ResearchFinding
- LedgerEntry
- RiskScore
- Report
- AgentState
"""

from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# ─── Production ─────────────────────────────────────────────────────────────

class Production(BaseModel):
    production_id: str
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_document_ref: str
    script_content_hash: str
    status: Literal["processing", "complete", "needs_review"] = "processing"

# ─── Claim ──────────────────────────────────────────────────────────────────

class Claim(BaseModel):
    claim_id: str
    production_id: str
    type: Literal["music", "footage", "brand", "real_person", "genai_flag", "other"]
    scene_ref: str
    extracted_description: str
    needs_clarification: bool = False
    proposed_by_agent: Optional[str] = None
    is_delta_modified: bool = False
    revision_color: Optional[str] = None
    co_occurring_claim_ids: List[str] = Field(default_factory=list)
    genai_provenance_required: bool = False
    opt_out_registry_flagged: bool = False
    territory_codes: List[str] = Field(default_factory=lambda: ["US"])
    union_option_expires_at: Optional[datetime] = None
    performer_prominence: Optional[Literal["crowd_background", "featured_speaking"]] = None
    usage_classification: Optional[Literal["background_instrumental", "visual_vocal", "feature_music", "logo_visual"]] = None
    pro_work_ids: Optional[Dict[str, Optional[str]]] = None
    visual_bounding_box: Optional[Dict[str, float]] = None
    visual_prominence: Optional[Dict[str, Any]] = None
    edl_timecode_in: Optional[str] = None
    edl_timecode_out: Optional[str] = None
    timecode_fps: Optional[Literal["23.976_ndf", "24.0", "29.97_df", "30.0"]] = None
    parent_claim_id: Optional[str] = None
    suggested_fair_use_defense: Optional[str] = None
    is_docudrama_context: bool = False
    is_brand_disparaged: bool = False
    drm_protected: bool = False
    licensing_scope: Optional[Literal["festival_rights_only", "worldwide_all_media_perpetual"]] = None
    window_stage: Optional[Literal["us_theatrical", "eu_streaming", "uk_freetoair"]] = None
    flagged_reason: Optional[str] = None
    query_plan: Optional[List[Dict[str, Any]]] = None
    adapted_extraction_schema: Optional[Dict[str, Any]] = None
    peer_vote_consensus: Optional[str] = None
    estimated_licensing_cost_min: Optional[float] = None
    estimated_licensing_cost_max: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ─── ResearchFinding ────────────────────────────────────────────────────────

class ResearchFinding(BaseModel):
    finding_id: str
    claim_id: str
    production_id: str
    query_issued: str
    source_url: str
    source_title: str
    snippet: str
    confidence_raw: float
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_used: Literal["parallel_search_api", "parallel_extract_api", "task_api", "vertex_search"] = "parallel_search_api"
    execution_latency_ms: Optional[int] = None
    call_status: Literal["success", "failed", "fallback_used"] = "success"
    error_detail: Optional[str] = None

# ─── LedgerEntry ────────────────────────────────────────────────────────────

class LedgerEntry(BaseModel):
    entry_id: str
    production_id: str
    claim_id: str
    action_type: Literal[
        "claim_created",
        "finding_attached",
        "score_assigned",
        "conflict_flagged",
        "attorney_approval",
        "attorney_override"
    ]
    agent_id: str
    payload: Dict[str, Any]
    supersedes_entry_id: Optional[str] = None
    ledger_entry_hash: str
    verification_ttl_days: int = 30
    attorney_signature: Optional[str] = None
    rfc3161_timestamp_token: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ─── RiskScore ──────────────────────────────────────────────────────────────

class RiskScore(BaseModel):
    score_id: str
    claim_id: str
    production_id: str
    score: Literal["CLEARED", "HIGH_RISK", "CONFLICT_FLAGGED", "NEEDS_HUMAN_REVIEW", "PENDING_VERIFICATION"]
    confidence: float
    confidence_rationale: str
    conflict_detected: bool = False
    conflict_description: Optional[str] = None
    statutory_damages_exposure_usd: Optional[float] = None
    statutory_citations: List[str] = Field(default_factory=list)
    fair_use_scorecard: Optional[Dict[str, float]] = None
    suggested_legal_citation: Optional[str] = None
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ─── Report ─────────────────────────────────────────────────────────────────

class Report(BaseModel):
    report_id: str
    production_id: str
    summary_stats: Dict[str, int]
    bond_compliance_score: float
    clearance_velocity_score: float
    form_eo_2026_certificate_url: Optional[str] = None
    cue_sheet_url: Optional[str] = None
    legal_audit_manifest_url: Optional[str] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ─── AgentState ─────────────────────────────────────────────────────────────

class AgentState(BaseModel):
    agent_id: str
    status: Literal["idle", "processing", "paused_for_human", "error"]
    current_production_id: Optional[str] = None
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_capabilities: List[str] = Field(default_factory=list)
    state_payload: Dict[str, Any] = Field(default_factory=dict)
