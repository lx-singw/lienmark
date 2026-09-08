"""
backend/orchestration/resumption.py

Durable Checkpoint Hydration and Incremental Investigation Resumption coordinator.
Dispatches to ResumptionPipelineService for fenced worker execution, freshness checks,
zero-waste memory hydration, and unified clarification unblocking.
Sprint 4.2 under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple, Union

from backend.orchestration.checkpoint_types import (
    ExecutionCheckpoint as OrchCheckpoint,
    SuspensionState,
)
from backend.orchestration.resumption_helpers import (
    determine_resumption_stage,
    hydrate_resumed_memory,
)
from backend.orchestration.resumption_pipeline import ResumptionPipelineService
from backend.orchestration.resumption_types import (
    NextStageDispatch,
    ResolutionPayload,
    ResumedAgentMemory,
    ResumptionResult,
    ResumptionStatus,
    is_claim_active_in_revision,
    verify_checkpoint_token,
    verify_checkpoint_ttl,
)
from backend.orchestration.suspension import ClarificationStateMachine, SuspensionManager
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_types import (
    ExecutionCheckpoint as StorageCheckpoint,
)

logger = logging.getLogger("lienmark.orchestration.resumption")


class ResumptionCoordinator:
    """Orchestrates checkpoint validation, pipeline dispatch, memory hydration, and stage dispatch."""

    def __init__(
        self,
        checkpoint_store: Optional[CheckpointStore] = None,
        suspension_manager: Optional[SuspensionManager] = None,
        adk_coordinator: Optional[object] = None,
        pipeline_service: Optional[ResumptionPipelineService] = None,
        clarification_store: Optional[object] = None,
        budget_governor: Optional[object] = None,
    ) -> None:
        self.checkpoint_store = checkpoint_store
        self.suspension_manager = suspension_manager
        self.adk_coordinator = adk_coordinator
        self.pipeline_service = pipeline_service or ResumptionPipelineService(
            checkpoint_store=checkpoint_store, suspension_manager=suspension_manager,
            adk_coordinator=adk_coordinator, clarification_store=clarification_store,
            budget_governor=budget_governor,
        )

    _hydrate_agent_memory = staticmethod(hydrate_resumed_memory)
    _determine_next_stage = staticmethod(determine_resumption_stage)

    def _load_checkpoint(
        self,
        checkpoint_id: str,
        tenant_id: Optional[str] = None,
        production_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[Union[StorageCheckpoint, OrchCheckpoint]]:
        """Loads ExecutionCheckpoint from SuspensionManager, CheckpointStore, or cache."""
        if self.suspension_manager and checkpoint_id in self.suspension_manager.checkpoints:
            return self.suspension_manager.checkpoints[checkpoint_id]
        if not self.checkpoint_store:
            return None
        if tenant_id and run_id:
            return self.checkpoint_store.get_checkpoint(
                tenant_id, production_id or "", run_id, checkpoint_id, allow_expired=True
            )
        local = getattr(self.checkpoint_store, "_local_store", None)
        cache = getattr(local, "_memory_cache", {})
        return next((cp for cp in cache.values() if getattr(cp, "checkpoint_id", "") == checkpoint_id), None)

    def _find_checkpoint_for_claim(self, claim_id: str) -> Optional[object]:
        """Locates latest checkpoint for target claim in suspension manager."""
        if self.suspension_manager and hasattr(self.suspension_manager, "checkpoints"):
            for cp in reversed(list(self.suspension_manager.checkpoints.values())):
                if getattr(cp, "claim_id", None) == claim_id:
                    return cp
        return None

    def _extract_identifiers(self, checkpoint: object) -> Tuple[str, str, str]:
        """Extracts (claim_id, run_id, paused_stage) across checkpoint schemas."""
        run_id = str(getattr(checkpoint, "run_id", "unknown_run"))
        if isinstance(checkpoint, OrchCheckpoint):
            return checkpoint.claim_id, run_id, checkpoint.paused_stage
        agent_state = getattr(checkpoint, "agent_state", None)
        cids = getattr(agent_state, "active_claim_ids", [])
        return (str(cids[0]) if cids else "unknown_claim"), run_id, getattr(agent_state, "current_step", "active_investigation")

    def _transition_claim_state(self, claim_id: str, target: SuspensionState) -> None:
        """Updates claim suspension state in SuspensionManager and ADK coordinator."""
        if self.suspension_manager and hasattr(self.suspension_manager, "states"):
            curr = self.suspension_manager.states.get(claim_id, SuspensionState.WAITING_FOR_INFORMATION)
            if curr != target and ClarificationStateMachine.can_transition(curr, target):
                target = ClarificationStateMachine.transition(curr, target)
            self.suspension_manager.states[claim_id] = target
        if self.adk_coordinator and hasattr(self.adk_coordinator, "claim_states"):
            getattr(self.adk_coordinator, "claim_states")[claim_id] = target.value

    def _validate_checkpoint_gate(
        self, cp: object, checkpoint_id: str, cid: str, cp_run_id: str,
        resume_token: str, current_revision_uses: Optional[List[object]], now_utc: str,
    ) -> Optional[ResumptionResult]:
        """Validates token, TTL expiration, and revision freshness gates."""
        if not verify_checkpoint_token(cp, resume_token):
            return ResumptionResult.create_failure(
                checkpoint_id, cp_run_id, cid, ResumptionStatus.TOKEN_INVALID,
                SuspensionState.WAITING_FOR_INFORMATION, "Cryptographic resume token verification failed.", now_utc
            )
        if not verify_checkpoint_ttl(cp):
            self._transition_claim_state(cid, SuspensionState.EXPIRED_TTL)
            return ResumptionResult.create_failure(
                checkpoint_id, cp_run_id, cid, ResumptionStatus.EXPIRED_TTL,
                SuspensionState.EXPIRED_TTL, "Checkpoint has exceeded its retention TTL window.", now_utc
            )
        if not is_claim_active_in_revision(cid, current_revision_uses):
            self._transition_claim_state(cid, SuspensionState.CANCELLED_SUPERSEDED)
            return ResumptionResult.create_failure(
                checkpoint_id, cp_run_id, cid, ResumptionStatus.CANCELLED_SUPERSEDED,
                SuspensionState.CANCELLED_SUPERSEDED, f"Claim '{cid}' was superseded in script cut.", now_utc
            )
        return None

    def resume_run(
        self,
        checkpoint_id: str,
        resume_token: str,
        resolution_payload: Optional[Union[ResolutionPayload, Dict[str, object]]] = None,
        current_revision_uses: Optional[List[object]] = None,
        tenant_id: Optional[str] = None,
        production_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> ResumptionResult:
        """Main entrypoint: validates gates, enqueues to pipeline service, executes, and returns result."""
        now_utc = datetime.now(timezone.utc).isoformat()
        res_obj = ResolutionPayload.model_validate(resolution_payload) if isinstance(resolution_payload, dict) else resolution_payload
        cp = self._load_checkpoint(checkpoint_id, tenant_id, production_id, run_id)
        if not cp:
            return ResumptionResult.create_failure(
                checkpoint_id, run_id or "unknown", "unknown", ResumptionStatus.CHECKPOINT_NOT_FOUND,
                SuspensionState.WAITING_FOR_INFORMATION, f"Checkpoint '{checkpoint_id}' not found.", now_utc,
            )
        cid, cp_run_id, _ = self._extract_identifiers(cp)
        gate_failure = self._validate_checkpoint_gate(cp, checkpoint_id, cid, cp_run_id, resume_token, current_revision_uses, now_utc)
        if gate_failure:
            return gate_failure

        eff_tenant = tenant_id or str(getattr(cp, "tenant_id", "tenant_default"))
        eff_prod = production_id or str(getattr(cp, "production_id", "prod_default"))
        return self._execute_resumption_dispatch(
            cp=cp, cid=cid, cp_run_id=cp_run_id, res_obj=res_obj, tenant_id=eff_tenant,
            production_id=eff_prod, resume_token=resume_token, current_revision_uses=current_revision_uses, now_utc=now_utc,
        )

    def _execute_resumption_dispatch(
        self, cp: object, cid: str, cp_run_id: str, res_obj: Optional[ResolutionPayload],
        tenant_id: str, production_id: str, resume_token: str,
        current_revision_uses: Optional[List[object]], now_utc: str,
    ) -> ResumptionResult:
        """Enqueues and executes stage via ResumptionPipelineService, preserving state invariants."""
        self._transition_claim_state(cid, SuspensionState.RESUMING)
        self._transition_claim_state(cid, SuspensionState.ACTIVE_INVESTIGATION)
        memory, skipped = hydrate_resumed_memory(cp, res_obj)
        next_stage = determine_resumption_stage(cid, memory, res_obj)

        if self.adk_coordinator and hasattr(self.adk_coordinator, "claim_contexts"):
            getattr(self.adk_coordinator, "claim_contexts").setdefault(cid, {}).update(memory.context_variables)

        ck_id = getattr(cp, "checkpoint_id", "") or (cp.get("checkpoint_id", "") if isinstance(cp, dict) else "")
        dispatch = self.pipeline_service.enqueue_resumption(
            tenant_id=tenant_id, production_id=production_id, run_id=cp_run_id,
            claim_id=cid, checkpoint_id=str(ck_id), resolution_payload=res_obj, resume_token=resume_token,
        )
        dispatch_rec = self.pipeline_service.execute_dispatch(
            dispatch_id=dispatch.dispatch_id, current_revision_uses=current_revision_uses
        )
        next_stage.dispatch_id, next_stage.execution_result = dispatch_rec.dispatch_id, dispatch_rec.execution_result
        self._transition_claim_state(cid, SuspensionState.ACTIVE_INVESTIGATION)

        return ResumptionResult(
            checkpoint_id=str(ck_id), run_id=cp_run_id, claim_id=cid,
            status=ResumptionStatus.SUCCESS, previous_state=SuspensionState.WAITING_FOR_INFORMATION,
            current_state=SuspensionState.ACTIVE_INVESTIGATION, hydrated_memory=memory,
            next_stage=next_stage, reinvestigated_upstream_count=0,
            skipped_completed_subgoals=skipped, resumed_at_utc=now_utc,
        )

    def resume_from_clarification(
        self,
        claim_id: str,
        resolution_payload: Union[ResolutionPayload, Dict[str, object]],
        checkpoint_id: Optional[str] = None,
        resume_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        production_id: Optional[str] = None,
        run_id: Optional[str] = None,
        current_revision_uses: Optional[List[object]] = None,
    ) -> ResumptionResult:
        """Unified entrypoint resuming investigation from clarification response."""
        cp = self._find_checkpoint_for_claim(claim_id) if not checkpoint_id else None
        eff_cp_id = checkpoint_id or (getattr(cp, "checkpoint_id", "") if cp else "")
        eff_tok = resume_token or (str(getattr(cp, "resume_token", "")) if cp else "")
        return self.resume_run(
            checkpoint_id=eff_cp_id, resume_token=eff_tok, resolution_payload=resolution_payload,
            current_revision_uses=current_revision_uses, tenant_id=tenant_id or getattr(cp, "tenant_id", None),
            production_id=production_id or getattr(cp, "production_id", None), run_id=run_id or getattr(cp, "run_id", None),
        )
