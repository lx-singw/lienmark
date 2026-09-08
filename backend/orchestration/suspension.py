"""
backend/orchestration/suspension.py

Active Clarification State Machine and Suspension Manager.
Coordinates durable checkpoints, resource release, and zero-leak worker termination.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Set, Tuple, Union

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
    """Active lifecycle state machine governing claim and run suspension/resumption."""

    VALID_TRANSITIONS: Dict[SuspensionState, Set[SuspensionState]] = {
        SuspensionState.INITIALIZING: {SuspensionState.ACTIVE_INVESTIGATION, SuspensionState.SUSPENDING},
        SuspensionState.ACTIVE_INVESTIGATION: {SuspensionState.SUSPENDING, SuspensionState.READY_FOR_REVIEW, SuspensionState.RESOLVED},
        SuspensionState.SUSPENDING: {SuspensionState.WAITING_FOR_INFORMATION},
        SuspensionState.WAITING_FOR_INFORMATION: {SuspensionState.RESUMING, SuspensionState.CANCELLED_SUPERSEDED, SuspensionState.EXPIRED_TTL},
        SuspensionState.RESUMING: {SuspensionState.ACTIVE_INVESTIGATION, SuspensionState.READY_FOR_REVIEW, SuspensionState.CANCELLED_SUPERSEDED},
        SuspensionState.READY_FOR_REVIEW: {SuspensionState.RESOLVED, SuspensionState.SUSPENDING},
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
    """Orchestrates checkpoint creation, resource release, and stateful resumption."""

    def __init__(
        self,
        checkpoint_store: Optional[object] = None,
        clarification_store: Optional[object] = None,
    ) -> None:
        self.checkpoints: Dict[str, ExecutionCheckpoint] = {}
        self.states: Dict[str, SuspensionState] = {}
        self._checkpoint_store = checkpoint_store
        self._clarification_store = clarification_store

    def _get_checkpoint_store(self) -> Optional[object]:
        """Resolves CheckpointStore instance lazily."""
        if self._checkpoint_store is not None:
            return self._checkpoint_store
        try:
            from backend.storage.checkpoint_store import get_checkpoint_store
            return get_checkpoint_store()
        except ImportError:
            return None

    def _get_clarification_store(self) -> Optional[object]:
        """Resolves ClarificationStore instance lazily."""
        if self._clarification_store is not None:
            return self._clarification_store
        try:
            from backend.storage.clarification_store import get_clarification_store
            return get_clarification_store()
        except ImportError:
            return None

    def _build_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, claim_id: str,
        paused_stage: str, reason: SuspensionReason, agent_memory_snapshot: AgentMemorySnapshot,
        pending_clarification_ids: List[str], ttl_seconds: int,
        completed_subgoals: Optional[List[str]] = None, evidence_digests: Optional[List[str]] = None,
        remaining_budget: Optional[float] = None, structured_state: Optional[Dict[str, object]] = None,
    ) -> ExecutionCheckpoint:
        """Constructs ExecutionCheckpoint with cryptographic resume token and execution state."""
        now_utc = datetime.now(timezone.utc).isoformat()
        token = compute_resume_token(
            tenant_id=tenant_id, production_id=production_id, run_id=run_id, claim_id=claim_id,
            paused_stage=paused_stage, pending_clarification_ids=pending_clarification_ids, created_at_utc=now_utc,
        )
        c_sub = completed_subgoals or getattr(agent_memory_snapshot, "completed_subgoals", [])
        e_dig = evidence_digests or getattr(agent_memory_snapshot, "evidence_digests", [])
        rem_b = remaining_budget if remaining_budget is not None else getattr(agent_memory_snapshot, "remaining_budget", None)
        meta: Dict[str, object] = {
            "suspension_reason": reason.value, "completed_subgoals": c_sub,
            "evidence_digests": e_dig, "remaining_budget": rem_b, "structured_execution_state": structured_state or {},
        }
        return ExecutionCheckpoint(
            checkpoint_id=f"chk_{uuid.uuid4().hex[:10]}", run_id=run_id, tenant_id=tenant_id,
            production_id=production_id, claim_id=claim_id, paused_stage=paused_stage,
            agent_memory_snapshot=agent_memory_snapshot, pending_clarification_ids=list(pending_clarification_ids),
            resume_token=token, created_at_utc=now_utc, ttl_expires_at_utc=calculate_ttl_timestamp(ttl_seconds=ttl_seconds),
            metadata=meta, completed_subgoals=c_sub, evidence_digests=e_dig,
            remaining_budget=rem_b, structured_execution_state=structured_state or {},
        )

    def suspend_investigation(
        self, tenant_id: str, production_id: str, run_id: str, claim_id: str,
        paused_stage: str, reason: SuspensionReason, agent_memory_snapshot: AgentMemorySnapshot,
        pending_clarification_ids: List[str], active_tasks: Optional[Sequence[asyncio.Task]] = None,
        active_locks: Optional[Sequence[object]] = None,
        worker_handles: Optional[Union[Dict[str, object], List[object]]] = None,
        ttl_seconds: int = 172800, completed_subgoals: Optional[List[str]] = None,
        evidence_digests: Optional[List[str]] = None, remaining_budget: Optional[float] = None,
        structured_execution_state: Optional[Dict[str, object]] = None,
    ) -> ExecutionCheckpoint:
        """Commits checkpoint to CheckpointStore and sets WAITING_FOR_INFORMATION before releasing resources."""
        current = self.states.get(claim_id, SuspensionState.ACTIVE_INVESTIGATION)
        interim = ClarificationStateMachine.transition(current, SuspensionState.SUSPENDING)
        self.states[claim_id] = ClarificationStateMachine.transition(interim, SuspensionState.WAITING_FOR_INFORMATION)
        cp = self._build_checkpoint(
            tenant_id=tenant_id, production_id=production_id, run_id=run_id, claim_id=claim_id,
            paused_stage=paused_stage, reason=reason, agent_memory_snapshot=agent_memory_snapshot,
            pending_clarification_ids=pending_clarification_ids, ttl_seconds=ttl_seconds,
            completed_subgoals=completed_subgoals, evidence_digests=evidence_digests,
            remaining_budget=remaining_budget, structured_state=structured_execution_state,
        )
        self.checkpoints[cp.checkpoint_id] = cp
        store = self._get_checkpoint_store()
        if store is not None and hasattr(store, "save_checkpoint"):
            store.save_checkpoint(cp)

        ResourceReleaser.cancel_async_tasks(active_tasks or [])
        ResourceReleaser.release_locks(active_locks or [])
        if worker_handles is not None:
            ResourceReleaser.purge_worker_references(worker_handles)
        return cp

    def resume_investigation(
        self, checkpoint_id: str, resume_token: str, current_revision_uses: Optional[List[object]] = None,
    ) -> Dict[str, object]:
        """Resumes checkpoint after verifying token, TTL, clarification eligibility, and cut freshness."""
        cp = self.checkpoints.get(checkpoint_id)
        if not cp:
            store = self._get_checkpoint_store()
            cp = store.get_checkpoint("", "", "", checkpoint_id, allow_expired=True) if store else None
            if not cp:
                raise KeyError(f"Checkpoint '{checkpoint_id}' not found.")

        if not validate_resume_token(cp, resume_token):
            raise InvalidResumeTokenError("Resume token failed cryptographic SHA-256 validation.")

        c_store = self._get_clarification_store()
        if c_store and hasattr(c_store, "is_resume_eligible"):
            if not c_store.is_resume_eligible(cp.run_id, cp.tenant_id, cp.pending_clarification_ids):
                self.states[cp.claim_id] = SuspensionState.EXPIRED_TTL
                raise CheckpointExpiredError(f"Checkpoint '{checkpoint_id}' resume invalid: clarification expired.")

        if datetime.now(timezone.utc).isoformat() > cp.ttl_expires_at_utc:
            self.states[cp.claim_id] = SuspensionState.EXPIRED_TTL
            raise CheckpointExpiredError(f"Checkpoint '{checkpoint_id}' expired at {cp.ttl_expires_at_utc}.")

        if current_revision_uses is not None and not self._is_claim_active_in_revision(cp.claim_id, current_revision_uses):
            self.states[cp.claim_id] = SuspensionState.CANCELLED_SUPERSEDED
            return {"status": SuspensionState.CANCELLED_SUPERSEDED.value, "checkpoint_id": cp.checkpoint_id}

        self.states[cp.claim_id] = ClarificationStateMachine.transition(
            self.states.get(cp.claim_id, SuspensionState.WAITING_FOR_INFORMATION), SuspensionState.RESUMING,
        )
        return {
            "status": SuspensionState.RESUMING.value, "claim_id": cp.claim_id,
            "paused_stage": cp.paused_stage, "memory_snapshot": cp.agent_memory_snapshot.model_dump(),
        }

    @staticmethod
    def _is_claim_active_in_revision(claim_id: str, current_revision_uses: List[object]) -> bool:
        """Determines if suspended claim is present in latest revision cut."""
        for u in current_revision_uses:
            cid = u.get("claim_id") or u.get("occurrence_lineage_id") if isinstance(u, dict) else getattr(u, "claim_id", getattr(u, "occurrence_lineage_id", None))
            if cid == claim_id:
                return True
        return False
