"""
backend/orchestration/suspension.py

Active Clarification State Machine and Suspension Manager.
Converts legacy static 'needs_human_review' into an active suspend-and-resume engine.
Enforces zero CPU/memory leaks by coordinating with ResourceReleaser and checkpoints.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    ExecutionCheckpoint,
    SuspensionReason,
    SuspensionState,
    calculate_ttl_timestamp,
    compute_resume_token,
    validate_resume_token,
)
from backend.orchestration.resource_releaser import ResourceReleaser

logger = logging.getLogger("lienmark.orchestration.suspension")


class SuspensionError(Exception):
    """Base exception for suspension and state machine operations."""
    pass


class InvalidStateTransitionError(SuspensionError):
    """Raised when an illegal lifecycle state transition is requested."""

    def __init__(self, current: SuspensionState, target: SuspensionState):
        super().__init__(f"Illegal state transition from '{current.value}' to '{target.value}'.")
        self.current = current
        self.target = target


class CheckpointExpiredError(SuspensionError):
    """Raised when attempting to resume an expired checkpoint past its TTL."""
    pass


class InvalidResumeTokenError(SuspensionError):
    """Raised when a provided resume token fails cryptographic validation."""
    pass


class ClarificationStateMachine:
    """
    Active lifecycle state machine governing claim and run suspension/resumption.
    Enforces unambiguous forward-progress invariants and terminal gates.
    """

    VALID_TRANSITIONS: Dict[SuspensionState, Set[SuspensionState]] = {
        SuspensionState.INITIALIZING: {
            SuspensionState.ACTIVE_INVESTIGATION,
            SuspensionState.SUSPENDING,
        },
        SuspensionState.ACTIVE_INVESTIGATION: {
            SuspensionState.SUSPENDING,
            SuspensionState.READY_FOR_REVIEW,
            SuspensionState.RESOLVED,
        },
        SuspensionState.SUSPENDING: {
            SuspensionState.WAITING_FOR_INFORMATION,
        },
        SuspensionState.WAITING_FOR_INFORMATION: {
            SuspensionState.RESUMING,
            SuspensionState.CANCELLED_SUPERSEDED,
            SuspensionState.EXPIRED_TTL,
        },
        SuspensionState.RESUMING: {
            SuspensionState.ACTIVE_INVESTIGATION,
            SuspensionState.READY_FOR_REVIEW,
            SuspensionState.CANCELLED_SUPERSEDED,
        },
        SuspensionState.READY_FOR_REVIEW: {
            SuspensionState.RESOLVED,
            SuspensionState.SUSPENDING,
        },
        SuspensionState.RESOLVED: set(),
        SuspensionState.CANCELLED_SUPERSEDED: set(),
        SuspensionState.EXPIRED_TTL: set(),
    }

    @classmethod
    def can_transition(cls, current: SuspensionState, target: SuspensionState) -> bool:
        """Checks if a proposed state transition is valid per the lifecycle matrix."""
        return target in cls.VALID_TRANSITIONS.get(current, set())

    @classmethod
    def transition(cls, current: SuspensionState, target: SuspensionState) -> SuspensionState:
        """Executes validated state transition or raises InvalidStateTransitionError."""
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(current, target)
        logger.debug(f"ClarificationStateMachine: {current.value} -> {target.value}")
        return target


class SuspensionManager:
    """
    High-level orchestrator coordinating checkpoint creation, resource release,
    and stateful resumption with revision freshness checks.
    """

    def __init__(self) -> None:
        self.checkpoints: Dict[str, ExecutionCheckpoint] = {}
        self.states: Dict[str, SuspensionState] = {}

    def _build_checkpoint(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        claim_id: str,
        paused_stage: str,
        reason: SuspensionReason,
        agent_memory_snapshot: AgentMemorySnapshot,
        pending_clarification_ids: List[str],
        ttl_seconds: int,
    ) -> ExecutionCheckpoint:
        """Constructs and hashes ExecutionCheckpoint with cryptographic resume token."""
        now_utc = datetime.now(timezone.utc).isoformat()
        token = compute_resume_token(
            tenant_id=tenant_id,
            production_id=production_id,
            run_id=run_id,
            claim_id=claim_id,
            paused_stage=paused_stage,
            pending_clarification_ids=pending_clarification_ids,
            created_at_utc=now_utc,
        )
        return ExecutionCheckpoint(
            checkpoint_id=f"chk_{uuid.uuid4().hex[:10]}",
            run_id=run_id,
            tenant_id=tenant_id,
            production_id=production_id,
            claim_id=claim_id,
            paused_stage=paused_stage,
            agent_memory_snapshot=agent_memory_snapshot,
            pending_clarification_ids=list(pending_clarification_ids),
            resume_token=token,
            created_at_utc=now_utc,
            ttl_expires_at_utc=calculate_ttl_timestamp(ttl_seconds=ttl_seconds),
            metadata={"suspension_reason": reason.value},
        )

    def suspend_investigation(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        claim_id: str,
        paused_stage: str,
        reason: SuspensionReason,
        agent_memory_snapshot: AgentMemorySnapshot,
        pending_clarification_ids: List[str],
        active_tasks: Optional[Sequence[asyncio.Task]] = None,
        active_locks: Optional[Sequence[Any]] = None,
        worker_handles: Optional[Union[Dict[str, Any], List[Any]]] = None,
        ttl_seconds: int = 172800,
    ) -> ExecutionCheckpoint:
        """Suspends run, captures checkpoint, releases all resources, and sets WAITING_FOR_INFORMATION."""
        current = self.states.get(claim_id, SuspensionState.ACTIVE_INVESTIGATION)
        interim = ClarificationStateMachine.transition(current, SuspensionState.SUSPENDING)
        final_state = ClarificationStateMachine.transition(interim, SuspensionState.WAITING_FOR_INFORMATION)
        self.states[claim_id] = final_state

        ResourceReleaser.cancel_async_tasks(active_tasks or [])
        ResourceReleaser.release_locks(active_locks or [])
        if worker_handles is not None:
            ResourceReleaser.purge_worker_references(worker_handles)

        checkpoint = self._build_checkpoint(
            tenant_id=tenant_id,
            production_id=production_id,
            run_id=run_id,
            claim_id=claim_id,
            paused_stage=paused_stage,
            reason=reason,
            agent_memory_snapshot=agent_memory_snapshot,
            pending_clarification_ids=pending_clarification_ids,
            ttl_seconds=ttl_seconds,
        )
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint

    def resume_investigation(
        self,
        checkpoint_id: str,
        resume_token: str,
        current_revision_uses: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Resumes suspended checkpoint after verifying token, TTL, and revision cut freshness."""
        cp = self.checkpoints.get(checkpoint_id)
        if not cp:
            raise KeyError(f"Checkpoint '{checkpoint_id}' not found.")

        if not validate_resume_token(cp, resume_token):
            raise InvalidResumeTokenError("Resume token failed cryptographic SHA-256 validation.")

        now_utc = datetime.now(timezone.utc).isoformat()
        if now_utc > cp.ttl_expires_at_utc:
            self.states[cp.claim_id] = SuspensionState.EXPIRED_TTL
            raise CheckpointExpiredError(f"Checkpoint '{checkpoint_id}' expired at {cp.ttl_expires_at_utc}.")

        if current_revision_uses is not None and not self._is_claim_active_in_revision(cp.claim_id, current_revision_uses):
            self.states[cp.claim_id] = SuspensionState.CANCELLED_SUPERSEDED
            return {"status": SuspensionState.CANCELLED_SUPERSEDED.value, "checkpoint_id": cp.checkpoint_id}

        self.states[cp.claim_id] = ClarificationStateMachine.transition(
            self.states.get(cp.claim_id, SuspensionState.WAITING_FOR_INFORMATION),
            SuspensionState.RESUMING,
        )
        return {
            "status": SuspensionState.RESUMING.value,
            "claim_id": cp.claim_id,
            "paused_stage": cp.paused_stage,
            "memory_snapshot": cp.agent_memory_snapshot.model_dump(),
        }

    @staticmethod
    def _is_claim_active_in_revision(claim_id: str, current_revision_uses: List[Any]) -> bool:
        """Determines if the suspended claim is present in the latest script cut."""
        for u in current_revision_uses:
            if isinstance(u, dict):
                cid = u.get("claim_id") or u.get("occurrence_lineage_id") or u.get("stable_lineage_key")
                if cid == claim_id:
                    return True
            else:
                cid = getattr(u, "claim_id", getattr(u, "occurrence_lineage_id", None))
                if cid == claim_id:
                    return True
        return False
