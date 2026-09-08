"""
backend/orchestration/resumption_helpers.py

Shared memory hydration, stage determination, and coroutine execution utilities
for resumption coordinator and pipeline services.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Coroutine, Dict, List, Optional, Tuple, TypeVar

from backend.orchestration.checkpoint_types import (
    ExecutionCheckpoint as OrchCheckpoint,
)
from backend.orchestration.resumption_types import (
    NextStageDispatch,
    NextStageType,
    ResolutionPayload,
    ResumedAgentMemory,
    has_attached_contracts,
)
from backend.storage.checkpoint_types import (
    ExecutionCheckpoint as StorageCheckpoint,
)

T = TypeVar("T")


def run_coroutine_sync(coro: Coroutine[object, object, T]) -> T:
    """Safely executes async coroutine from synchronous caller context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return loop.run_until_complete(coro) if loop else asyncio.run(coro)


def hydrate_resumed_memory(
    checkpoint: object, resolution: Optional[ResolutionPayload]
) -> Tuple[ResumedAgentMemory, int]:
    """Hydrates execution memory, preserves upstream boundaries, skips completed subgoals."""
    completed_sg, uncompleted_sg, dag = ResumedAgentMemory.extract_subgoals_and_dag(checkpoint)
    role, step_count, context_vars, queries = "adk_orchestrator", 0, {}, []

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
        active_role=role, current_step="resuming", completed_step_count=step_count,
        completed_subgoals=completed_sg, uncompleted_subgoals=uncompleted_sg, partial_dag=dag,
        query_history=queries, context_variables=context_vars,
        upstream_frozen_count=len(completed_sg) + len(queries),
    )
    return memory, len(completed_sg)


def determine_resumption_stage(
    claim_id: str, memory: ResumedAgentMemory, resolution: Optional[ResolutionPayload]
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
            pending_node_id=str(next_id),
            dispatch_payload={"subgoal": next_sg},
            reasoning="Proceeding to next uncompleted investigation node; upstream nodes frozen.",
        )
    return NextStageDispatch(
        stage_type=NextStageType.READY_FOR_REVIEW,
        stage_action="ACT_07_PREPARE_REVIEW_BRIEF",
        target_claim_id=claim_id,
        reasoning="All subgoals and evidence nodes satisfied; review ready.",
    )
