from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel

from backend.domain.models import CreativeUse, PublicEvidenceSnapshot, CounselDecision

class CreativeUseDeltaInput(BaseModel):
    stable_lineage_key: str
    asset_title: Optional[str] = None
    artist_or_author: Optional[str] = None
    duration_seconds: Optional[float] = None
    prominence: Optional[str] = None
    intended_use: Optional[str] = None
    distribution_media: Optional[List[str]] = None
    territory: Optional[List[str]] = None
    term_start: Optional[str] = None
    term_end: Optional[str] = None
    agreement_ids: Optional[List[str]] = None

class RevisionSubmissionRequest(BaseModel):
    tenant_id: str
    production_id: str
    parent_baseline_version_id: str
    idempotency_key: str
    payload_hash: str
    added_uses: List[CreativeUse]
    modified_uses: List[CreativeUseDeltaInput]
    removed_use_keys: List[str]

class ExternalEvidenceUpdateRequest(BaseModel):
    tenant_id: str
    production_id: str
    revision_id: str
    target_lineage_key: str
    updated_evidence_snapshot: PublicEvidenceSnapshot
    idempotency_key: str

class RevisionRecord(BaseModel):
    revision_id: str
    created_at: datetime
    user_provenance: str
    tenant_id: str
    production_id: str
    parent_baseline_version_id: str

    class Config:
        frozen = True  # Immutable snapshot

class RevisionAuditDispatch(BaseModel):
    audit_id: str
    revision_id: str
    status: str
    fencing_token: int
    lease_expires_at: Optional[datetime] = None
    idempotency_key: str
    payload_hash: str
    retry_count: int

class ResultSnapshot(BaseModel):
    snapshot_id: str
    audit_id: str
    version_number: int
    created_at: datetime
    decisions: List[CounselDecision]
    telemetry: Dict[str, str]  # Used Dict[str, str] to avoid Any
