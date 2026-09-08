"""
backend/orchestration/resumption_pipeline.py

Resumption Pipeline Service for Milestone D.
Provides atomic clarification commit, queue-based dispatch tracking,
fenced expiring worker leases, storage freshness validation, zero-waste hydration,
downstream action execution, and lease expiration sweeper recovery.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import threading
from typing import Dict, List, Optional, Union
import uuid

from backend.orchestration.checkpoint_types import SuspensionState
from backend.orchestration.resumption_helpers import (
    determine_resumption_stage,
    hydrate_resumed_memory,
    run_coroutine_sync,
)
from backend.orchestration.resumption_types import (
    CheckpointFreshnessError,
    ClaimSupersededError,
    ResolutionPayload,
    ResumptionDispatchRecord,
    ResumptionDispatchStatus,
    is_claim_active_in_revision,
    verify_checkpoint_token,
    verify_checkpoint_ttl,
)
from backend.storage.locks import DistributedLockManager

logger = logging.getLogger("lienmark.orchestration.resumption_pipeline")


class ResumptionPipelineService:
    """Coordinates atomic resumption enqueuing, fenced worker execution, and sweeper recovery."""

    def __init__(
        self,
        checkpoint_store: Optional[object] = None,
        suspension_manager: Optional[object] = None,
        adk_coordinator: Optional[object] = None,
        clarification_store: Optional[object] = None,
        lock_manager: Optional[DistributedLockManager] = None,
        budget_governor: Optional[object] = None,
        default_lease_seconds: float = 300.0,
    ) -> None:
        self.checkpoint_store = checkpoint_store
        self.suspension_manager = suspension_manager
        self.adk_coordinator = adk_coordinator
        self.clarification_store = clarification_store
        self.lock_manager = lock_manager or DistributedLockManager(in_memory=True)
        self.budget_governor = budget_governor
        self.default_lease_seconds = default_lease_seconds
        self.dispatches: Dict[str, ResumptionDispatchRecord] = {}
        self._lock = threading.RLock()
        self.hydrate_memory = hydrate_resumed_memory
        self.determine_next_stage = determine_resumption_stage

    def _commit_clarification(self, tenant_id: str, prod_id: str, claim_id: str, res: Optional[ResolutionPayload]) -> None:
        """Atomically records resolution in clarification store if present."""
        if not res or not self.clarification_store:
            return
        clrf_id = res.clarification_id
        if not clrf_id and hasattr(self.clarification_store, "list_open_clarifications"):
            open_list = getattr(self.clarification_store, "list_open_clarifications")(tenant_id, prod_id)
            match = next((c for c in open_list if getattr(c, "claim_id", None) == claim_id), None)
            clrf_id = getattr(match, "request_id", None) if match else None
        if clrf_id and hasattr(self.clarification_store, "resolve_clarification"):
            first_doc = res.attached_documents[0] if res.attached_documents else None
            getattr(self.clarification_store, "resolve_clarification")(
                request_id=clrf_id, tenant_id=tenant_id, actor_id=res.resolved_by,
                responder_role=res.resolved_by, response_text=res.notes,
                attached_document_id=first_doc, selected_option=res.resolution_status,
            )

    def enqueue_resumption(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        claim_id: str,
        checkpoint_id: str,
        resolution_payload: Optional[Union[ResolutionPayload, Dict[str, object]]] = None,
        resume_token: Optional[str] = None,
        checkpoint_revision: int = 1,
    ) -> ResumptionDispatchRecord:
        """Atomically commits clarification response and resume dispatch record."""
        res_obj = ResolutionPayload.model_validate(resolution_payload) if isinstance(resolution_payload, dict) else resolution_payload
        with self._lock:
            self._commit_clarification(tenant_id, production_id, claim_id, res_obj)
            now_utc = datetime.now(timezone.utc).isoformat()
            dispatch = ResumptionDispatchRecord(
                dispatch_id=f"dsp_{uuid.uuid4().hex[:10]}", tenant_id=tenant_id, production_id=production_id,
                run_id=run_id, claim_id=claim_id, checkpoint_id=checkpoint_id,
                checkpoint_revision=checkpoint_revision, resolution_payload=res_obj, resume_token=resume_token,
                status=ResumptionDispatchStatus.QUEUED_FOR_RESUMPTION.value, created_at_utc=now_utc, updated_at_utc=now_utc,
            )
            self.dispatches[dispatch.dispatch_id] = dispatch
            if self.suspension_manager and hasattr(self.suspension_manager, "states"):
                getattr(self.suspension_manager, "states")[claim_id] = SuspensionState.RESUMING
            if self.adk_coordinator and hasattr(self.adk_coordinator, "claim_states"):
                getattr(self.adk_coordinator, "claim_states")[claim_id] = SuspensionState.RESUMING.value
            return dispatch

    def _acquire_worker_lease(self, dispatch: ResumptionDispatchRecord, worker_id: str, lease_seconds: float) -> int:
        """Acquires expiring worker lease with strictly monotonic fencing token."""
        rec = self.lock_manager.acquire_lock(f"resumption:{dispatch.tenant_id}:{dispatch.claim_id}", owner_id=worker_id, ttl_seconds=lease_seconds)
        token = getattr(rec, "fence_token", getattr(rec, "fencing_token", 1))
        exp_utc = getattr(rec, "expires_at_utc", None) or (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat()
        dispatch.worker_id, dispatch.fencing_token = worker_id, int(token)
        dispatch.lease_expires_at_utc, dispatch.status = str(exp_utc), ResumptionDispatchStatus.PROCESSING.value
        dispatch.updated_at_utc = datetime.now(timezone.utc).isoformat()
        return dispatch.fencing_token

    def _load_checkpoint(self, dispatch: ResumptionDispatchRecord) -> object:
        """Loads checkpoint from CheckpointStore or SuspensionManager."""
        mgr_cps = getattr(self.suspension_manager, "checkpoints", {})
        if dispatch.checkpoint_id in mgr_cps:
            return mgr_cps[dispatch.checkpoint_id]
        if self.checkpoint_store and hasattr(self.checkpoint_store, "get_checkpoint"):
            return getattr(self.checkpoint_store, "get_checkpoint")(
                dispatch.tenant_id, dispatch.production_id, dispatch.run_id, dispatch.checkpoint_id, allow_expired=True,
            )
        return None

    def _validate_freshness(self, dispatch: ResumptionDispatchRecord, cp: object, revision_uses: Optional[List[object]]) -> None:
        """Validates checkpoint existence, TTL, token, and revision freshness."""
        if not cp:
            raise CheckpointFreshnessError(f"Checkpoint '{dispatch.checkpoint_id}' not found in storage.")
        if not verify_checkpoint_ttl(cp):
            raise CheckpointFreshnessError("Checkpoint has exceeded retention TTL window.")
        if dispatch.resume_token and not verify_checkpoint_token(cp, dispatch.resume_token):
            raise CheckpointFreshnessError("Resume token failed validation.")
        if not is_claim_active_in_revision(dispatch.claim_id, revision_uses):
            raise ClaimSupersededError(f"Claim '{dispatch.claim_id}' was superseded.")

    def _check_blockers_and_budget(self, dispatch: ResumptionDispatchRecord, cp: object) -> bool:
        """Validates remaining clarification blockers and budget limits."""
        pending = list(getattr(cp, "pending_clarification_ids", []))
        if dispatch.resolution_payload and dispatch.resolution_payload.clarification_id in pending:
            pending.remove(dispatch.resolution_payload.clarification_id)
        if pending and self.clarification_store:
            open_ones = [cid for cid in pending if self._is_clarification_open(cid, dispatch.tenant_id)]
            if open_ones:
                dispatch.status, dispatch.error_message = ResumptionDispatchStatus.BLOCKED.value, f"Blocker clarifications pending: {open_ones}"
                return False
        if self.budget_governor and hasattr(self.budget_governor, "check_mid_flight_cap"):
            if not getattr(self.budget_governor, "check_mid_flight_cap")(dispatch.run_id, dispatch.production_id):
                dispatch.status, dispatch.error_message = ResumptionDispatchStatus.BLOCKED.value, "Budget cap reached."
                return False
        return True

    def _is_clarification_open(self, clrf_id: str, tenant_id: str) -> bool:
        """Checks if a clarification request remains unresolved."""
        if not self.clarification_store or not hasattr(self.clarification_store, "get_clarification"):
            return False
        clrf = getattr(self.clarification_store, "get_clarification")(clrf_id, tenant_id=tenant_id)
        return clrf is not None and getattr(clrf, "status", "").lower() not in ("resolved", "cancelled", "expired")

    def _execute_stage(self, stage_action: str, claim_id: str) -> Dict[str, object]:
        """Executes next eligible stage via adk_coordinator.execute_action()."""
        if not self.adk_coordinator:
            return {"action": stage_action, "status": "COORDINATOR_NOT_ATTACHED"}
        claims = getattr(self.adk_coordinator, "claims", {})
        if claim_id not in claims and hasattr(self.adk_coordinator, "register_claim"):
            from backend.domain.models import AtomicRightsClaim, CensusDisposition
            getattr(self.adk_coordinator, "register_claim")(AtomicRightsClaim(
                claim_id=claim_id, occurrence_id=f"occ_{claim_id}", occurrence_lineage_id=f"lin_{claim_id}",
                right_category="music", rights_subject=f"Claim {claim_id}", disposition=CensusDisposition.NEEDS_REVIEW,
            ))
        from backend.orchestration.adk_pipeline import CoordinatorAction
        act_enum = CoordinatorAction(stage_action) if stage_action in CoordinatorAction._value2member_map_ else stage_action
        coro = getattr(self.adk_coordinator, "execute_action")(act_enum, claim_id)
        res = run_coroutine_sync(coro)
        if hasattr(self.adk_coordinator, "claim_states"):
            getattr(self.adk_coordinator, "claim_states")[claim_id] = "active_investigation"
        return res if isinstance(res, dict) else {"result": str(res)}

    def execute_dispatch(
        self,
        dispatch_id: str,
        worker_id: Optional[str] = None,
        current_revision_uses: Optional[List[object]] = None,
        lease_seconds: Optional[float] = None,
    ) -> ResumptionDispatchRecord:
        """Worker execution loop: acquires lease, validates freshness, executes next stage."""
        dispatch = self.dispatches.get(dispatch_id)
        if not dispatch:
            raise KeyError(f"Resumption dispatch '{dispatch_id}' not found.")
        eff_worker = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        eff_lease = lease_seconds or self.default_lease_seconds
        self._acquire_worker_lease(dispatch, eff_worker, eff_lease)
        cp = self._load_checkpoint(dispatch)
        try:
            self._validate_freshness(dispatch, cp, current_revision_uses)
            if not self._check_blockers_and_budget(dispatch, cp):
                return dispatch
            memory, _ = self.hydrate_memory(cp, dispatch.resolution_payload)
            next_stage = self.determine_next_stage(dispatch.claim_id, memory, dispatch.resolution_payload)
            if self.adk_coordinator and hasattr(self.adk_coordinator, "claim_contexts"):
                getattr(self.adk_coordinator, "claim_contexts").setdefault(dispatch.claim_id, {}).update(memory.context_variables)
            dispatch.execution_result = self._execute_stage(next_stage.stage_action, dispatch.claim_id)
            dispatch.status = ResumptionDispatchStatus.INVESTIGATION_RESUMED.value
        except Exception as exc:
            dispatch.status, dispatch.error_message = ResumptionDispatchStatus.FAILED.value, str(exc)
            raise
        finally:
            dispatch.updated_at_utc = datetime.now(timezone.utc).isoformat()
            self.lock_manager.release_lock(f"resumption:{dispatch.tenant_id}:{dispatch.claim_id}", owner_id=eff_worker)
        return dispatch

    def process_next_dispatch(self, worker_id: Optional[str] = None) -> Optional[ResumptionDispatchRecord]:
        """Pulls and executes the next queued dispatch in FIFO order."""
        with self._lock:
            pending = next((d for d in self.dispatches.values() if d.status == ResumptionDispatchStatus.QUEUED_FOR_RESUMPTION.value), None)
        return self.execute_dispatch(pending.dispatch_id, worker_id=worker_id) if pending else None

    def sweep_and_recover_abandoned_dispatches(self, lease_timeout_buffer_sec: float = 0.0) -> List[ResumptionDispatchRecord]:
        """Sweeps abandoned/stranded resumption dispatches whose worker leases have expired."""
        recovered: List[ResumptionDispatchRecord] = []
        now = datetime.now(timezone.utc)
        with self._lock:
            for d in self.dispatches.values():
                if d.status != ResumptionDispatchStatus.PROCESSING.value or not d.lease_expires_at_utc:
                    continue
                try:
                    exp = datetime.fromisoformat(d.lease_expires_at_utc)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if now >= exp + timedelta(seconds=lease_timeout_buffer_sec):
                    d.worker_id, d.lease_expires_at_utc = None, None
                    d.retry_count += 1
                    d.status, d.updated_at_utc = ResumptionDispatchStatus.QUEUED_FOR_RESUMPTION.value, now.isoformat()
                    self.lock_manager.release_lock(f"resumption:{d.tenant_id}:{d.claim_id}")
                    recovered.append(d)
        return recovered

    def get_dispatch(self, dispatch_id: str) -> Optional[ResumptionDispatchRecord]:
        """Retrieves a dispatch record by ID."""
        with self._lock:
            return self.dispatches.get(dispatch_id)
