"""
backend/orchestration/checkpoint_types.py

Canonical checkpoint models, suspension enums, and SHA-256 resume token utilities.
Supports Sprint 4.1 Human-in-the-Loop Clarification State Machine and durable checkpoints.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SuspensionState(str, Enum):
    """
    Active lifecycle states for clearance runs and individual claims.
    Replaces legacy static 'needs_human_review' terminal flag with active state machine.
    """
    INITIALIZING = "initializing"
    ACTIVE_INVESTIGATION = "active_investigation"
    SUSPENDING = "suspending"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    RESUMING = "resuming"
    READY_FOR_REVIEW = "ready_for_review"
    RESOLVED = "resolved"
    CANCELLED_SUPERSEDED = "cancelled_superseded"
    EXPIRED_TTL = "expired_ttl"


class SuspensionReason(str, Enum):
    """Canonical root causes triggering pipeline or claim suspension."""
    AMBIGUOUS_CLAIM = "ambiguous_claim"
    MISSING_PRIVATE_CONTRACT = "missing_private_contract"
    UNCLEAR_SYNC_SCOPE = "unclear_sync_scope"
    UNCREDITED_MUSIC = "uncredited_music"
    MISSING_AUTHOR_COMPOSER = "missing_author_composer"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    BUDGET_EXHAUSTED = "budget_exhausted"


class AgentMemorySnapshot(BaseModel):
    """
    Serialized agent execution memory capturing partial reasoning state.
    Enables zero-data-loss restoration without redundant upstream queries.
    """
    findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Completed factual findings and evidence citations",
    )
    subgoals: List[str] = Field(
        default_factory=list,
        description="Pending sub-objectives awaiting resolution",
    )
    partial_dag: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Workflow DAG execution graph mapping completed to pending nodes",
    )
    query_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Historical external API queries and payload hashes",
    )
    context_variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scoped working variables, e.g. license scope and music cue metadata",
    )


class ExecutionCheckpoint(BaseModel):
    """
    Durable checkpoint contract persisting paused pipeline state.
    Provides complete state capture and cryptographic resume tokens.
    """
    checkpoint_id: str = Field(..., description="Unique checkpoint identifier, e.g. chk_9a12c")
    run_id: str = Field(..., description="ADK pipeline run identifier")
    tenant_id: str = Field(..., description="Multi-tenant identifier")
    production_id: str = Field(..., description="Production / Film identifier")
    claim_id: str = Field(..., description="Target claim instance identifier")
    paused_stage: str = Field(..., description="Pipeline stage or CoordinatorAction where pause occurred")
    agent_memory_snapshot: AgentMemorySnapshot = Field(..., description="Serialized agent reasoning memory")
    pending_clarification_ids: List[str] = Field(
        default_factory=list,
        description="Clarification request IDs awaiting human or document response",
    )
    resume_token: str = Field(..., description="Cryptographic SHA-256 token validating resumption")
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 creation timestamp",
    )
    ttl_expires_at_utc: str = Field(..., description="ISO-8601 TTL expiration timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional operational metadata (e.g. revision_id, reason code)",
    )


def compute_resume_token(
    tenant_id: str,
    production_id: str,
    run_id: str,
    claim_id: str,
    paused_stage: str,
    pending_clarification_ids: List[str],
    created_at_utc: str,
    secret_salt: str = "lienmark_resumption_salt_v1",
) -> str:
    """
    Computes an idempotent, tamper-evident SHA-256 token for checkpoint resumption.
    Sorts clarification IDs to guarantee deterministic digest across execution contexts.
    """
    sorted_clarifications = ",".join(sorted(pending_clarification_ids))
    canonical_payload = (
        f"{tenant_id}|{production_id}|{run_id}|{claim_id}|"
        f"{paused_stage}|{sorted_clarifications}|{created_at_utc}|{secret_salt}"
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def validate_resume_token(
    checkpoint: ExecutionCheckpoint,
    token_to_verify: str,
    secret_salt: str = "lienmark_resumption_salt_v1",
) -> bool:
    """Validates provided resume token against expected cryptographic checkpoint digest."""
    expected = compute_resume_token(
        tenant_id=checkpoint.tenant_id,
        production_id=checkpoint.production_id,
        run_id=checkpoint.run_id,
        claim_id=checkpoint.claim_id,
        paused_stage=checkpoint.paused_stage,
        pending_clarification_ids=checkpoint.pending_clarification_ids,
        created_at_utc=checkpoint.created_at_utc,
        secret_salt=secret_salt,
    )
    return expected == token_to_verify


def calculate_ttl_timestamp(
    ttl_seconds: int = 172800,
    base_time: Optional[datetime] = None,
) -> str:
    """Calculates UTC ISO-8601 expiration timestamp with configurable duration."""
    start = base_time or datetime.now(timezone.utc)
    expiration = start + timedelta(seconds=ttl_seconds)
    return expiration.isoformat()
