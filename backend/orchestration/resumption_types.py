"""
backend/orchestration/resumption_types.py

Canonical Pydantic v2 schemas, data contracts, and enums for checkpoint
hydration, revision freshness verification, and incremental investigation resumption.
Sprint 4.2 under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.orchestration.checkpoint_types import (
    ExecutionCheckpoint as OrchCheckpoint,
    SuspensionState,
    validate_resume_token,
)
from backend.storage.checkpoint_serializer import verify_resume_token
from backend.storage.checkpoint_types import (
    ExecutionCheckpoint as StorageCheckpoint,
)


class ResumptionStatus(str, Enum):
    """Lifecycle resumption statuses returned by ResumptionCoordinator."""
    SUCCESS = "success"
    CANCELLED_SUPERSEDED = "cancelled_superseded"
    EXPIRED_TTL = "expired_ttl"
    TOKEN_INVALID = "token_invalid"
    CHECKPOINT_NOT_FOUND = "checkpoint_not_found"
    FAILED = "failed"


class NextStageType(str, Enum):
    """Categorical classification of the next stage dispatched after resumption."""
    TARGETED_AGREEMENT_VERIFICATION = "targeted_agreement_verification"
    NEXT_INVESTIGATION_NODE = "next_investigation_node"
    EVIDENCE_RECONCILIATION = "evidence_reconciliation"
    READY_FOR_REVIEW = "ready_for_review"
    STOP_UNRESOLVED = "stop_unresolved"


class ResolutionPayload(BaseModel):
    """Contract for clarification responses unblocking suspended claims."""
    model_config = ConfigDict(extra="ignore")

    resolution_id: str = Field(..., description="Unique resolution ID")
    claim_id: str = Field(..., description="Target claim being resolved")
    clarification_id: Optional[str] = Field(default=None, description="Bound clarification request ID")
    resolved_by: str = Field(default="counsel", description="Origin of resolution (e.g. counsel)")
    provided_facts: Dict[str, Any] = Field(
        default_factory=dict, description="Factual assertions, e.g. license scope confirmation"
    )
    resolution_status: str = Field(default="confirmed", description="Resolution outcome status")
    attached_documents: List[str] = Field(default_factory=list, description="IDs of private contracts attached")
    notes: Optional[str] = Field(default=None, description="Counsel explanatory remarks")


class ResumedAgentMemory(BaseModel):
    """Hydrated agent memory capturing reasoning state and upstream boundary."""
    model_config = ConfigDict(extra="ignore")

    active_role: str = Field(default="adk_orchestrator", description="Active agent role upon resumption")
    current_step: str = Field(default="resuming", description="Pipeline execution step name")
    completed_step_count: int = Field(default=0, ge=0, description="Count of completed steps")
    completed_subgoals: List[str] = Field(default_factory=list, description="Subgoal IDs verified completed")
    uncompleted_subgoals: List[Dict[str, Any]] = Field(default_factory=list, description="Pending sub-objectives")
    partial_dag: Dict[str, Any] = Field(default_factory=dict, description="DAG state with completed nodes marked")
    query_history: List[Dict[str, Any]] = Field(default_factory=list, description="Prior queries executed (cached)")
    context_variables: Dict[str, Any] = Field(default_factory=dict, description="Working context merged with facts")
    upstream_frozen_count: int = Field(default=0, ge=0, description="Count of upstream elements protected from re-query")

    @classmethod
    def extract_subgoals_and_dag(
        cls, checkpoint: Any
    ) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
        """Separates completed from pending subgoals and extracts DAG graph."""
        completed_sg: List[str] = []
        uncompleted_sg: List[Dict[str, Any]] = []
        dag: Dict[str, Any] = {}
        if hasattr(checkpoint, "investigation_dag"):
            dag = getattr(checkpoint, "investigation_dag") or {}
            for sg in getattr(checkpoint, "uncompleted_subgoals", []):
                status = sg.get("status") if isinstance(sg, dict) else getattr(sg, "status", None)
                sg_id = sg.get("id") if isinstance(sg, dict) else getattr(sg, "id", str(sg))
                if status == "completed":
                    completed_sg.append(sg_id)
                else:
                    uncompleted_sg.append(sg if isinstance(sg, dict) else sg.model_dump())
        elif hasattr(checkpoint, "agent_memory_snapshot"):
            snap = getattr(checkpoint, "agent_memory_snapshot")
            dag = dict(snap.partial_dag)
            uncompleted_sg = [{"id": s, "status": "pending"} for s in snap.subgoals]
        return completed_sg, uncompleted_sg, dag


class NextStageDispatch(BaseModel):
    """Instruction packet describing the next pipeline stage dispatched after resumption."""
    model_config = ConfigDict(extra="ignore")

    stage_type: NextStageType = Field(..., description="Target stage category")
    stage_action: str = Field(..., description="Specific action string (e.g. ACT_01)")
    target_claim_id: str = Field(..., description="Claim ID undergoing investigation")
    pending_node_id: Optional[str] = Field(default=None, description="Next DAG node ID to execute")
    dispatch_payload: Dict[str, Any] = Field(default_factory=dict, description="Context variables passed to stage")
    reasoning: str = Field(..., description="Causal justification for stage selection")


class ResumptionResult(BaseModel):
    """Structured outcome of an incremental pipeline resumption execution."""
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(..., description="Identifier of the hydrated checkpoint")
    run_id: str = Field(..., description="ADK pipeline run identifier")
    claim_id: str = Field(..., description="Target claim identifier")
    status: ResumptionStatus = Field(..., description="Terminal or interim status")
    previous_state: SuspensionState = Field(..., description="SuspensionState before resumption")
    current_state: SuspensionState = Field(..., description="SuspensionState achieved")
    hydrated_memory: Optional[ResumedAgentMemory] = Field(default=None, description="Restored agent memory")
    next_stage: Optional[NextStageDispatch] = Field(default=None, description="Dispatched next stage packet")
    reinvestigated_upstream_count: int = Field(default=0, ge=0, description="Invariant: MUST be 0")
    skipped_completed_subgoals: int = Field(default=0, ge=0, description="Count of completed subgoals skipped")
    resumed_at_utc: str = Field(..., description="ISO 8601 UTC timestamp of resumption")
    error_message: Optional[str] = Field(default=None, description="Diagnostic message if resumption failed")

    @classmethod
    def create_failure(
        cls, checkpoint_id: str, run_id: str, claim_id: str, status: ResumptionStatus,
        target_state: SuspensionState, error_msg: str, now_utc: str
    ) -> ResumptionResult:
        """Constructs a failure ResumptionResult with explicit diagnostic message."""
        return cls(
            checkpoint_id=checkpoint_id, run_id=run_id, claim_id=claim_id, status=status,
            previous_state=SuspensionState.WAITING_FOR_INFORMATION, current_state=target_state,
            resumed_at_utc=now_utc, error_message=error_msg,
        )


def verify_checkpoint_token(checkpoint: Any, resume_token: str) -> bool:
    """Validates cryptographic SHA-256 resume token against checkpoint digest."""
    if isinstance(checkpoint, OrchCheckpoint):
        return validate_resume_token(checkpoint, resume_token)
    if isinstance(checkpoint, StorageCheckpoint):
        return checkpoint.resume_token == resume_token and verify_resume_token(checkpoint)
    return getattr(checkpoint, "resume_token", None) == resume_token


def verify_checkpoint_ttl(checkpoint: Any) -> bool:
    """Verifies checkpoint TTL expiration timestamp has not elapsed."""
    exp_iso = getattr(checkpoint, "expires_at_utc", getattr(checkpoint, "ttl_expires_at_utc", None))
    if not exp_iso:
        return True
    try:
        exp_dt = datetime.fromisoformat(exp_iso)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) <= exp_dt
    except Exception:
        return False


def is_claim_active_in_revision(claim_id: str, revision_uses: Optional[List[Any]]) -> bool:
    """Verifies target claim is still present and active in current script revision cut."""
    if revision_uses is None:
        return True
    for item in revision_uses:
        if isinstance(item, dict):
            cid = item.get("claim_id") or item.get("occurrence_lineage_id") or item.get("stable_lineage_key")
        else:
            cid = getattr(item, "claim_id", getattr(item, "occurrence_lineage_id", None))
        if cid == claim_id:
            return True
def has_attached_contracts(resolution: Optional[ResolutionPayload]) -> bool:
    """Helper checking if resolution payload contains attached contracts or license scope."""
    if not resolution:
        return False
    facts_str = str(resolution.provided_facts).lower()
    return bool(
        resolution.attached_documents
        or "contract_id" in resolution.provided_facts
        or "license" in facts_str
    )


class ResumptionError(Exception):
    """Base exception for all pipeline resumption errors."""
    pass


class CheckpointFreshnessError(ResumptionError):
    """Raised when checkpoint TTL has expired or script cut is stale."""
    pass


class ClaimSupersededError(ResumptionError):
    """Raised when a paused claim has been removed or superseded in latest cut."""
    pass


class UpstreamInvariantViolation(ResumptionError):
    """Raised when an attempt is made to re-execute completed upstream queries."""
    pass
