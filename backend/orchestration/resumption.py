"""
backend/orchestration/resumption.py

Durable Checkpoint Hydration and Incremental Investigation Resumption subsystem.
Enforces zero-waste query invariants, cryptographic verification, script cut freshness,
and seamless handoff to next active investigation stages.
Sprint 4.2 under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.orchestration.checkpoint_types import ExecutionCheckpoint as OrchCheckpoint, SuspensionState
from backend.orchestration.resumption_types import (
    NextStageDispatch,
    NextStageType,
    ResolutionPayload,
    ResumedAgentMemory,
    ResumptionResult,
    ResumptionStatus,
    has_attached_contracts,
    is_claim_active_in_revision,
    verify_checkpoint_token,
    verify_checkpoint_ttl,
)
from backend.orchestration.suspension import ClarificationStateMachine, SuspensionManager
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_types import ExecutionCheckpoint as StorageCheckpoint

logger = logging.getLogger("lienmark.orchestration.resumption")


class ResumptionCoordinator:
    """
    Orchestrates checkpoint loading, cryptographic and TTL validation,
    script revision cut freshness, zero-waste memory hydration, and stage dispatch.
    """

    def __init__(
        self,
        checkpoint_store: Optional[CheckpointStore] = None,
        suspension_manager: Optional[SuspensionManager] = None,
        adk_coordinator: Optional[Any] = None,
    ) -> None:
        self.checkpoint_store = checkpoint_store
        self.suspension_manager = suspension_manager
        self.adk_coordinator = adk_coordinator

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
        return next((cp for cp in cache.values() if cp.checkpoint_id == checkpoint_id), None)

    def _extract_identifiers(self, checkpoint: Any) -> Tuple[str, str, str]:
        """Extracts (claim_id, run_id, paused_stage) across checkpoint schemas."""
        run_id = getattr(checkpoint, "run_id", "unknown_run")
        if isinstance(checkpoint, OrchCheckpoint):
            return checkpoint.claim_id, run_id, checkpoint.paused_stage
        agent_state = getattr(checkpoint, "agent_state", None)
        cids = getattr(agent_state, "active_claim_ids", [])
        return (cids[0] if cids else "unknown_claim"), run_id, getattr(agent_state, "current_step", "active_investigation")

    def _hydrate_agent_memory(
        self, checkpoint: Any, resolution: Optional[ResolutionPayload]
    ) -> Tuple[ResumedAgentMemory, int]:
        """Hydrates execution memory, preserves upstream boundaries, and merges resolution facts."""
        completed_sg, uncompleted_sg, dag = ResumedAgentMemory.extract_subgoals_and_dag(checkpoint)
        role, step_count = "adk_orchestrator", 0
        context_vars: Dict[str, Any] = {}
        queries: List[Dict[str, Any]] = []

        if isinstance(checkpoint, StorageCheckpoint):
            role = checkpoint.agent_state.active_role
            step_count = checkpoint.agent_state.completed_step_count
            context_vars = dict(checkpoint.agent_state.context_variables)
        elif isinstance(checkpoint, OrchCheckpoint):
            queries = list(checkpoint.agent_memory_snapshot.query_history)
            context_vars = dict(checkpoint.agent_memory_snapshot.context_variables)
            step_count = len(checkpoint.agent_memory_snapshot.findings)

        if resolution:
            context_vars.update(resolution.provided_facts)
            context_vars["last_resolution_id"] = resolution.resolution_id
            context_vars["clarification_resolved"] = True
            if resolution.attached_documents:
                context_vars["attached_contracts"] = list(resolution.attached_documents)

        memory = ResumedAgentMemory(
            active_role=role,
            current_step="resuming",
            completed_step_count=step_count,
            completed_subgoals=completed_sg,
            uncompleted_subgoals=uncompleted_sg,
            partial_dag=dag,
            query_history=queries,
            context_variables=context_vars,
            upstream_frozen_count=len(completed_sg) + len(queries),
        )
        return memory, len(completed_sg)

    def _determine_next_stage(
        self,
        claim_id: str,
        memory: ResumedAgentMemory,
        resolution: Optional[ResolutionPayload],
    ) -> NextStageDispatch:
        """Determines target next stage: agreement verification, next DAG node, or review."""
        if has_attached_contracts(resolution):
            docs = resolution.attached_documents if resolution else []
            return NextStageDispatch(
                stage_type=NextStageType.TARGETED_AGREEMENT_VERIFICATION,
                stage_action="ACT_01_RETRIEVE_PRIVATE_AGREEMENTS",
                target_claim_id=claim_id,
                dispatch_payload={"attached_contracts": docs},
                reasoning="Resolution payload contains private agreement requiring targeted verification.",
            )
        if memory.uncompleted_subgoals:
            next_sg = memory.uncompleted_subgoals[0]
            next_id = next_sg.get("id", "subgoal_next") if isinstance(next_sg, dict) else str(next_sg)
            return NextStageDispatch(
                stage_type=NextStageType.NEXT_INVESTIGATION_NODE,
                stage_action="ACT_02_SEARCH_PUBLIC_SOURCES",
                target_claim_id=claim_id,
                pending_node_id=next_id,
                dispatch_payload={"subgoal": next_sg},
                reasoning="Proceeding to next uncompleted investigation node; upstream nodes frozen.",
            )
        return NextStageDispatch(
            stage_type=NextStageType.READY_FOR_REVIEW,
            stage_action="ACT_07_PREPARE_REVIEW_BRIEF",
            target_claim_id=claim_id,
            reasoning="All subgoals and evidence nodes satisfied; dispatching final review brief.",
        )

    def _transition_claim_state(self, claim_id: str, target: SuspensionState) -> None:
        """Updates claim suspension state in SuspensionManager and ADK coordinator."""
        if self.suspension_manager:
            curr = self.suspension_manager.states.get(claim_id, SuspensionState.WAITING_FOR_INFORMATION)
            if curr != target and ClarificationStateMachine.can_transition(curr, target):
                target = ClarificationStateMachine.transition(curr, target)
            self.suspension_manager.states[claim_id] = target
        if self.adk_coordinator:
            self.adk_coordinator.claim_states[claim_id] = target.value

    def _validate_checkpoint_gate(
        self,
        cp: Any,
        checkpoint_id: str,
        cid: str,
        cp_run_id: str,
        resume_token: str,
        current_revision_uses: Optional[List[Any]],
        now_utc: str,
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
        resolution_payload: Optional[Union[ResolutionPayload, Dict[str, Any]]] = None,
        current_revision_uses: Optional[List[Any]] = None,
        tenant_id: Optional[str] = None,
        production_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> ResumptionResult:
        """Main entrypoint: hydrates checkpoint, verifies token/TTL/freshness, and dispatches stage."""
        now_utc = datetime.now(timezone.utc).isoformat()
        res_obj = (
            ResolutionPayload.model_validate(resolution_payload)
            if isinstance(resolution_payload, dict)
            else resolution_payload
        )
        cp = self._load_checkpoint(checkpoint_id, tenant_id, production_id, run_id)
        if not cp:
            return ResumptionResult.create_failure(
                checkpoint_id, run_id or "unknown", "unknown", ResumptionStatus.CHECKPOINT_NOT_FOUND,
                SuspensionState.WAITING_FOR_INFORMATION, f"Checkpoint '{checkpoint_id}' not found.", now_utc
            )

        cid, cp_run_id, _ = self._extract_identifiers(cp)
        gate_failure = self._validate_checkpoint_gate(
            cp, checkpoint_id, cid, cp_run_id, resume_token, current_revision_uses, now_utc
        )
        if gate_failure:
            return gate_failure

        return self._execute_resumption_dispatch(cp, cid, cp_run_id, res_obj, now_utc)

    def _execute_resumption_dispatch(
        self, cp: Any, cid: str, cp_run_id: str, res_obj: Optional[ResolutionPayload], now_utc: str
    ) -> ResumptionResult:
        """Executes state transitions, memory hydration, and next stage dispatch."""
        self._transition_claim_state(cid, SuspensionState.RESUMING)
        self._transition_claim_state(cid, SuspensionState.ACTIVE_INVESTIGATION)
        memory, skipped = self._hydrate_agent_memory(cp, res_obj)
        next_stage = self._determine_next_stage(cid, memory, res_obj)

        if self.adk_coordinator:
            self.adk_coordinator.claim_contexts.setdefault(cid, {}).update(memory.context_variables)

        ck_id = getattr(cp, "checkpoint_id", "") or (cp.get("checkpoint_id", "") if isinstance(cp, dict) else "")
        return ResumptionResult(
            checkpoint_id=ck_id, run_id=cp_run_id, claim_id=cid,
            status=ResumptionStatus.SUCCESS, previous_state=SuspensionState.WAITING_FOR_INFORMATION,
            current_state=SuspensionState.ACTIVE_INVESTIGATION, hydrated_memory=memory,
            next_stage=next_stage, reinvestigated_upstream_count=0,
            skipped_completed_subgoals=skipped, resumed_at_utc=now_utc,
        )
