"""
Lienmark Core Lifecycle Engine
Canonical State Machine for Investigation Runs under Agentic Cinema compliance.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from backend.domain.models import InvestigationRun, RunStatus

logger = logging.getLogger("lienmark.core.lifecycle")

CACHE_HIT_REASON = "DEDUPLICATION_CACHE_HIT"
BASELINE_LINK_KEYS = (
    "reused_baseline_id",
    "baseline_id",
    "reused_baseline",
    "reused_version_id",
    "reused_baseline_version_id",
)


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is attempted on an InvestigationRun."""

    def __init__(
        self, current_state: Union[RunStatus, str], target_state: Union[RunStatus, str],
        run_id: Optional[str] = None, reason: Optional[str] = None,
    ):
        self.current_state = current_state if isinstance(current_state, RunStatus) else str(current_state)
        self.target_state = target_state if isinstance(target_state, RunStatus) else str(target_state)
        self.run_id, self.reason = run_id, reason
        c_val = getattr(self.current_state, "value", str(self.current_state))
        t_val = getattr(self.target_state, "value", str(self.target_state))
        msg = f"Invalid state transition" + (f" for run '{run_id}'" if run_id else "") + f": cannot transition from '{c_val}' to '{t_val}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)


class LifecycleAuditEvent(BaseModel):
    """Immutable audit record generated on each state transition."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    run_id: str = Field(..., min_length=1)
    organization_id: str = Field(..., min_length=1)
    production_id: Optional[str] = Field(None)
    from_state: RunStatus = Field(...)
    to_state: RunStatus = Field(...)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor_id: str = Field(default="system")
    reason: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


ALLOWED_TRANSITIONS: Dict[RunStatus, Set[RunStatus]] = {
    RunStatus.QUEUED: {
        RunStatus.INVESTIGATING, RunStatus.READY_FOR_REVIEW, RunStatus.COMPLETED,
        RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.SUPERSEDED,
    },
    RunStatus.INVESTIGATING: {
        RunStatus.QUEUED, RunStatus.WAITING_FOR_INFORMATION, RunStatus.WAITING_FOR_BUDGET, RunStatus.READY_FOR_REVIEW,
        RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.SUPERSEDED,
    },
    RunStatus.WAITING_FOR_INFORMATION: {
        RunStatus.INVESTIGATING, RunStatus.READY_FOR_REVIEW, RunStatus.CANCELLED,
        RunStatus.FAILED, RunStatus.SUPERSEDED,
    },
    RunStatus.WAITING_FOR_BUDGET: {
        RunStatus.INVESTIGATING, RunStatus.READY_FOR_REVIEW, RunStatus.CANCELLED,
        RunStatus.FAILED, RunStatus.SUPERSEDED,
    },
    RunStatus.READY_FOR_REVIEW: {
        RunStatus.COMPLETED, RunStatus.INVESTIGATING, RunStatus.WAITING_FOR_INFORMATION,
        RunStatus.CANCELLED, RunStatus.SUPERSEDED,
    },
    RunStatus.COMPLETED: set(), RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(), RunStatus.SUPERSEDED: set(),
    RunStatus.INITIALIZING: {RunStatus.INVESTIGATING, RunStatus.EXTRACTING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.EXTRACTING: {RunStatus.INVESTIGATING, RunStatus.EVALUATING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.EVALUATING: {
        RunStatus.READY_FOR_REVIEW, RunStatus.WAITING_FOR_INFORMATION, RunStatus.WAITING_FOR_BUDGET,
        RunStatus.FAILED, RunStatus.CANCELLED,
    },
}

TERMINAL_STATES: Set[RunStatus] = {
    RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.SUPERSEDED,
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
    return coerce_run_status(status) in TERMINAL_STATES


def get_allowed_transitions(current_state: Union[RunStatus, str]) -> Set[RunStatus]:
    """Retrieve the set of allowed target states from current state."""
    return set(ALLOWED_TRANSITIONS.get(coerce_run_status(current_state), set()))


def _validate_cache_hit_invariants(
    curr: RunStatus, target: RunStatus, run_id: Optional[str],
    reason: Optional[str], metadata: Optional[Dict[str, Any]],
) -> None:
    """Verify that direct QUEUED cache-hit transitions never imply unapproved clearance."""
    if curr != RunStatus.QUEUED or target not in (RunStatus.COMPLETED, RunStatus.READY_FOR_REVIEW):
        return
    if reason != CACHE_HIT_REASON:
        raise InvalidStateTransitionError(
            curr, target, run_id, f"Transition from QUEUED to {target.value} strictly requires reason='{CACHE_HIT_REASON}'."
        )
    meta = metadata or {}
    if not any(meta.get(k) for k in BASELINE_LINK_KEYS):
        raise InvalidStateTransitionError(
            curr, target, run_id, "Cache hit transition requires metadata linking reused baseline."
        )
    if target == RunStatus.COMPLETED:
        if not meta.get("all_claims_approved", False) or meta.get("unapproved_claims_count", 0) > 0:
            raise InvalidStateTransitionError(
                curr, target, run_id, "Direct transition to COMPLETED requires all baseline claims to be approved."
            )


def can_transition(
    current_state: Union[RunStatus, str], target_state: Union[RunStatus, str],
    reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Return True if transition is legal, enforcing cache hit rules for QUEUED leaps."""
    try:
        curr, target = coerce_run_status(current_state), coerce_run_status(target_state)
    except ValueError:
        return False
    if target not in ALLOWED_TRANSITIONS.get(curr, set()):
        return False
    if curr == RunStatus.QUEUED and target in (RunStatus.COMPLETED, RunStatus.READY_FOR_REVIEW):
        if reason != CACHE_HIT_REASON:
            return False
        meta = metadata or {}
        if not any(meta.get(k) for k in BASELINE_LINK_KEYS):
            return False
        if target == RunStatus.COMPLETED and (not meta.get("all_claims_approved", False) or meta.get("unapproved_claims_count", 0) > 0):
            return False
    return True


def validate_transition(
    current_state: Union[RunStatus, str], target_state: Union[RunStatus, str],
    run_id: Optional[str] = None, reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Validate that transition is allowed. Raises InvalidStateTransitionError on violation."""
    curr, target = coerce_run_status(current_state), coerce_run_status(target_state)
    if target not in ALLOWED_TRANSITIONS.get(curr, set()):
        raise InvalidStateTransitionError(curr, target, run_id=run_id, reason=reason)
    _validate_cache_hit_invariants(curr, target, run_id, reason, metadata)


def transition_run(
    run: InvestigationRun, target_state: Union[RunStatus, str],
    actor_id: str = "system", reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    audit_sink: Optional[Callable[[LifecycleAuditEvent], None]] = None,
) -> InvestigationRun:
    """Execute a validated state transition on an InvestigationRun with audit logging."""
    if not run.organization_id or not run.organization_id.strip():
        raise ValueError("Cannot transition run with missing or empty organization_id")
    target_enum, from_enum = coerce_run_status(target_state), run.status
    validate_transition(from_enum, target_enum, run_id=run.run_id, reason=reason, metadata=metadata)
    now_iso = datetime.now(timezone.utc).isoformat()
    meta_payload = dict(metadata or {})
    if from_enum == RunStatus.QUEUED and target_enum == RunStatus.READY_FOR_REVIEW:
        meta_payload["requires_counsel_review"] = True
        meta_payload["legal_clearance_approved"] = False
    audit_evt = LifecycleAuditEvent(
        run_id=run.run_id, organization_id=run.organization_id, production_id=run.production_id,
        from_state=from_enum, to_state=target_enum, timestamp=now_iso, actor_id=actor_id,
        reason=reason, metadata=meta_payload,
    )
    run.status, run.updated_at = target_enum, now_iso
    if target_enum in TERMINAL_STATES:
        run.metadata["terminal_timestamp"] = now_iso
        if target_enum == RunStatus.COMPLETED:
            run.metadata["completed_at"] = now_iso
    run.metadata.update(meta_payload)
    run.metadata.setdefault("audit_log", []).append(audit_evt.model_dump())
    if audit_sink:
        audit_sink(audit_evt)
    return run


class RunLifecycleManager:
    """Authoritative lifecycle state machine manager coordinating transitions and audit trail."""

    def __init__(self, default_actor: str = "lifecycle_engine"):
        self.default_actor = default_actor
        self._audit_ledger: Dict[str, List[LifecycleAuditEvent]] = {}

    def can_transition(
        self, current_state: Union[RunStatus, str], target_state: Union[RunStatus, str],
        reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return can_transition(current_state, target_state, reason=reason, metadata=metadata)

    def get_allowed_transitions(self, current_state: Union[RunStatus, str]) -> Set[RunStatus]:
        return get_allowed_transitions(current_state)

    def is_terminal(self, state: Union[RunStatus, str]) -> bool:
        return is_terminal_state(state)

    def transition(
        self, run: InvestigationRun, target_state: Union[RunStatus, str],
        actor_id: Optional[str] = None, reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InvestigationRun:
        actor = actor_id or self.default_actor
        def record_sink(evt: LifecycleAuditEvent) -> None:
            self._audit_ledger.setdefault(evt.run_id, []).append(evt)
        return transition_run(
            run=run, target_state=target_state, actor_id=actor,
            reason=reason, metadata=metadata, audit_sink=record_sink,
        )

    def get_audit_history(self, run_id: str) -> List[LifecycleAuditEvent]:
        return list(self._audit_ledger.get(run_id, []))
