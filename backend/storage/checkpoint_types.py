"""
backend/storage/checkpoint_types.py

Domain models, data contracts, and custom exceptions for the checkpoint
storage and persistence subsystem.
Sprint 4.1: Human-in-the-Loop Clarification State Machine & Resumption.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CheckpointStorageError(Exception):
    """Base exception for all checkpoint storage operations."""
    pass


class CheckpointNotFoundError(CheckpointStorageError):
    """Raised when a requested checkpoint cannot be located."""
    pass


class CheckpointExpiredError(CheckpointStorageError):
    """Raised when an accessed checkpoint has exceeded its retention TTL."""
    pass


class CrossTenantCheckpointViolation(CheckpointStorageError):
    """Raised when an operation attempts unauthorized cross-tenant access."""
    pass


class CorruptedResumeTokenError(CheckpointStorageError):
    """Raised when a checkpoint resume token fails integrity verification."""
    pass


class InvalidCheckpointStateError(CheckpointStorageError):
    """Raised when checkpoint state payload is malformed or invalid."""
    pass


class AgentStateVector(BaseModel):
    """
    Structured snapshot of agent runtime memory, active roles, and pipeline context.
    Captures execution coordinates required for lossless resumption.
    """
    model_config = ConfigDict(extra="ignore")

    active_role: str = Field(default="adk_orchestrator", description="Active agent role/agent_id")
    current_step: str = Field(default="init", description="Execution pipeline step name")
    pending_clarification_ids: List[str] = Field(
        default_factory=list, description="IDs of unresolved clarification questions"
    )
    active_claim_ids: List[str] = Field(
        default_factory=list, description="Claim IDs currently being processed"
    )
    completed_step_count: int = Field(default=0, ge=0, description="Count of completed steps")
    context_variables: Dict[str, Any] = Field(
        default_factory=dict, description="Pipeline context variables and flags"
    )
    memory_snapshot: Dict[str, Any] = Field(
        default_factory=dict, description="Working memory dictionary of active agents"
    )


class CheckpointMetadata(BaseModel):
    """
    Administrative and lifecycle metadata attached to an execution checkpoint.
    Includes retention scheduling, revision history, and provenance.
    """
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(..., min_length=1, description="Unique checkpoint identifier")
    tenant_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    production_id: str = Field(..., min_length=1, description="Associated production identifier")
    run_id: str = Field(..., min_length=1, description="Associated investigation run identifier")
    revision: int = Field(default=1, ge=1, description="Monotonically increasing revision number")
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp",
    )
    updated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC last update timestamp",
    )
    expires_at_utc: str = Field(..., description="ISO 8601 UTC expiration timestamp")
    ttl_days: int = Field(default=30, ge=1, description="Retention TTL policy in days")
    created_by: str = Field(default="adk_pipeline", description="Originating service or user")
    trigger_reason: str = Field(
        default="suspension_for_clarification",
        description="Reason for snapshotting checkpoint state",
    )
    custom_attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Optional caller-defined diagnostic tags"
    )

    @property
    def org_id(self) -> str:
        """Alias for tenant_id maintaining Firestore path alignment."""
        return self.tenant_id


class ExecutionCheckpoint(BaseModel):
    """
    Authoritative entity representing a durable, serialized pipeline checkpoint.
    Allows exact pause-and-resume semantics for human-in-the-loop workflows.
    """
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(..., min_length=1, description="Unique checkpoint identifier")
    tenant_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    production_id: str = Field(..., min_length=1, description="Bound cinematic production ID")
    run_id: str = Field(..., min_length=1, description="Bound investigation run ID")
    revision: int = Field(default=1, ge=1, description="Revision number bumped on state change")
    metadata: CheckpointMetadata = Field(..., description="Administrative lifecycle metadata")
    agent_state: AgentStateVector = Field(..., description="Serialized agent state vector")
    investigation_dag: Optional[Dict[str, Any]] = Field(
        default=None, description="Serialized InvestigationPlanDAG graph state"
    )
    uncompleted_subgoals: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of uncompleted or pending subgoals"
    )
    state_hash: str = Field(..., min_length=16, description="Deterministic SHA-256 state digest")
    resume_token: str = Field(..., min_length=16, description="Cryptographic SHA-256 resume token")
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp",
    )
    expires_at_utc: str = Field(..., description="ISO 8601 UTC expiration timestamp")

    @property
    def org_id(self) -> str:
        """Alias for tenant_id maintaining Firestore collection alignment."""
        return self.tenant_id

    @field_validator("tenant_id", "production_id", "run_id", "checkpoint_id")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value or not isinstance(value, str) or not value.strip():
            raise ValueError("Field must be a non-empty string.")
        return value.strip()
