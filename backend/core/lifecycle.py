"""
Lienmark Core Lifecycle Engine
Canonical State Machine for Investigation Runs under Sprint 1.1.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Set, List, Optional, Any, Union, Callable

from pydantic import BaseModel, Field

from backend.domain.models import RunStatus, InvestigationRun

logger = logging.getLogger("lienmark.core.lifecycle")


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is attempted on an InvestigationRun."""

    def __init__(
        self,
        current_state: Union[RunStatus, str],
        target_state: Union[RunStatus, str],
        run_id: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        self.current_state = (
            current_state if isinstance(current_state, RunStatus) else str(current_state)
        )
        self.target_state = (
            target_state if isinstance(target_state, RunStatus) else str(target_state)
        )
        self.run_id = run_id
        self.reason = reason

        curr_val = self.current_state.value if isinstance(self.current_state, RunStatus) else str(self.current_state)
        targ_val = self.target_state.value if isinstance(self.target_state, RunStatus) else str(self.target_state)

        msg = f"Invalid state transition"
        if run_id:
            msg += f" for run '{run_id}'"
        msg += f": cannot transition from '{curr_val}' to '{targ_val}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)


class LifecycleAuditEvent(BaseModel):
    """Immutable audit record generated on each state transition."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    run_id: str = Field(..., min_length=1, description="Bound investigation run identifier")
    organization_id: str = Field(..., min_length=1, description="Tenant boundary identifier")
    production_id: Optional[str] = Field(None, description="Cinematic production identifier")
    from_state: RunStatus = Field(..., description="Previous lifecycle state")
    to_state: RunStatus = Field(..., description="Target lifecycle state")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor_id: str = Field(default="system", description="User or system service that triggered transition")
    reason: Optional[str] = Field(None, description="Explanatory justification for transition")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Canonical Allowed State Transition Matrix
ALLOWED_TRANSITIONS: Dict[RunStatus, Set[RunStatus]] = {
    RunStatus.QUEUED: {
        RunStatus.INVESTIGATING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
        RunStatus.SUPERSEDED,
    },
    RunStatus.INVESTIGATING: {
        RunStatus.WAITING_FOR_INFORMATION,
        RunStatus.WAITING_FOR_BUDGET,
        RunStatus.READY_FOR_REVIEW,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.SUPERSEDED,
    },
    RunStatus.WAITING_FOR_INFORMATION: {
        RunStatus.INVESTIGATING,
        RunStatus.READY_FOR_REVIEW,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
        RunStatus.SUPERSEDED,
    },
    RunStatus.WAITING_FOR_BUDGET: {
        RunStatus.INVESTIGATING,
        RunStatus.READY_FOR_REVIEW,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
        RunStatus.SUPERSEDED,
    },
    RunStatus.READY_FOR_REVIEW: {
        RunStatus.COMPLETED,
        RunStatus.INVESTIGATING,
        RunStatus.WAITING_FOR_INFORMATION,
        RunStatus.CANCELLED,
        RunStatus.SUPERSEDED,
    },
    # Terminal states: no outbound transitions permitted
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
    RunStatus.SUPERSEDED: set(),
}

# Legacy sub-phase transitions supported for backward compatibility
ALLOWED_TRANSITIONS[RunStatus.INITIALIZING] = {
    RunStatus.INVESTIGATING,
    RunStatus.EXTRACTING,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}
ALLOWED_TRANSITIONS[RunStatus.EXTRACTING] = {
    RunStatus.INVESTIGATING,
    RunStatus.EVALUATING,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}
ALLOWED_TRANSITIONS[RunStatus.EVALUATING] = {
    RunStatus.READY_FOR_REVIEW,
    RunStatus.WAITING_FOR_INFORMATION,
    RunStatus.WAITING_FOR_BUDGET,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}

TERMINAL_STATES: Set[RunStatus] = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.SUPERSEDED,
}


def coerce_run_status(status: Union[RunStatus, str]) -> RunStatus:
    """Safely coerce a string or RunStatus into a validated RunStatus enum."""
    if isinstance(status, RunStatus):
        return status
    try:
        return RunStatus(str(status).strip().lower())
    except ValueError:
        raise ValueError(f"Unknown lifecycle status: '{status}'")


def is_terminal_state(status: Union[RunStatus, str]) -> bool:
    """Return True if the given state is an immutable terminal state."""
    coerced = coerce_run_status(status)
    return coerced in TERMINAL_STATES


def get_allowed_transitions(current_state: Union[RunStatus, str]) -> Set[RunStatus]:
    """Retrieve the set of allowed target states from the given current state."""
    coerced = coerce_run_status(current_state)
    return set(ALLOWED_TRANSITIONS.get(coerced, set()))


def can_transition(current_state: Union[RunStatus, str], target_state: Union[RunStatus, str]) -> bool:
    """Return True if transition from current_state to target_state is legal."""
    try:
        curr_enum = coerce_run_status(current_state)
        target_enum = coerce_run_status(target_state)
    except ValueError:
        return False
    return target_enum in ALLOWED_TRANSITIONS.get(curr_enum, set())


def validate_transition(
    current_state: Union[RunStatus, str],
    target_state: Union[RunStatus, str],
    run_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    """
    Validate that transition from current_state to target_state is allowed.
    Raises InvalidStateTransitionError if the transition is illegal.
    """
    curr_enum = coerce_run_status(current_state)
    target_enum = coerce_run_status(target_state)

    allowed = ALLOWED_TRANSITIONS.get(curr_enum, set())
    if target_enum not in allowed:
        logger.warning(
            "Illegal state transition attempted for run '%s': %s -> %s (allowed: %s)",
            run_id or "unknown",
            curr_enum.value,
            target_enum.value,
            [s.value for s in allowed],
        )
        raise InvalidStateTransitionError(
            current_state=curr_enum,
            target_state=target_enum,
            run_id=run_id,
            reason=reason,
        )


def transition_run(
    run: InvestigationRun,
    target_state: Union[RunStatus, str],
    actor_id: str = "system",
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    audit_sink: Optional[Callable[[LifecycleAuditEvent], None]] = None,
) -> InvestigationRun:
    """
    Execute a validated state transition on an InvestigationRun.
    
    1. Validates non-nullable organization_id on the run (tenant isolation invariant).
    2. Validates transition legality via explicit transition matrix.
    3. Records ISO 8601 UTC timestamp and updates run.updated_at.
    4. Records terminal metadata if entering a terminal state.
    5. Appends structured LifecycleAuditEvent to run.metadata["audit_log"].
    6. Emits structured log and optionally invokes audit_sink.
    """
    if not run.organization_id or not run.organization_id.strip():
        raise ValueError("Cannot transition run with missing or empty organization_id (tenant boundary violation)")

    target_enum = coerce_run_status(target_state)
    from_enum = run.status

    validate_transition(
        current_state=from_enum,
        target_state=target_enum,
        run_id=run.run_id,
        reason=reason,
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # Build structured audit event
    audit_event = LifecycleAuditEvent(
        run_id=run.run_id,
        organization_id=run.organization_id,
        production_id=run.production_id,
        from_state=from_enum,
        to_state=target_enum,
        timestamp=now_iso,
        actor_id=actor_id,
        reason=reason,
        metadata=metadata or {},
    )

    # Mutate run model state defensively
    run.status = target_enum
    run.updated_at = now_iso

    if target_enum in TERMINAL_STATES:
        run.metadata["terminal_timestamp"] = now_iso
        if target_enum == RunStatus.COMPLETED:
            run.metadata["completed_at"] = now_iso

    audit_log = run.metadata.setdefault("audit_log", [])
    audit_log.append(audit_event.model_dump())

    logger.info(
        "Run '%s' (org '%s') transitioned %s -> %s by actor '%s'. Reason: %s",
        run.run_id,
        run.organization_id,
        from_enum.value,
        target_enum.value,
        actor_id,
        reason or "None",
    )

    if audit_sink:
        audit_sink(audit_event)

    return run


class RunLifecycleManager:
    """
    Enterprise Lifecycle State Machine Manager.
    Maintains an authoritative audit trail of lifecycle events and coordinates
    atomic transitions across InvestigationRun instances.
    """

    def __init__(self, default_actor: str = "lifecycle_engine"):
        self.default_actor = default_actor
        self._audit_ledger: Dict[str, List[LifecycleAuditEvent]] = {}

    def can_transition(
        self,
        current_state: Union[RunStatus, str],
        target_state: Union[RunStatus, str],
    ) -> bool:
        """Check if transition is permitted."""
        return can_transition(current_state, target_state)

    def get_allowed_transitions(
        self,
        current_state: Union[RunStatus, str],
    ) -> Set[RunStatus]:
        """Return all legal target states from current_state."""
        return get_allowed_transitions(current_state)

    def is_terminal(self, state: Union[RunStatus, str]) -> bool:
        """Check if state is terminal."""
        return is_terminal_state(state)

    def transition(
        self,
        run: InvestigationRun,
        target_state: Union[RunStatus, str],
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InvestigationRun:
        """
        Transition an InvestigationRun to a new state and record in the ledger.
        """
        actor = actor_id or self.default_actor

        def record_in_ledger(evt: LifecycleAuditEvent) -> None:
            history = self._audit_ledger.setdefault(evt.run_id, [])
            history.append(evt)

        return transition_run(
            run=run,
            target_state=target_state,
            actor_id=actor,
            reason=reason,
            metadata=metadata,
            audit_sink=record_in_ledger,
        )

    def get_audit_history(self, run_id: str) -> List[LifecycleAuditEvent]:
        """Retrieve chronological audit trail for a given run ID."""
        return list(self._audit_ledger.get(run_id, []))
