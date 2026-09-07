"""
backend/storage/checkpoint_store.py

Durable Checkpoint Storage & Persistence Layer for Lienmark Sprint 4.1.
Coordinates dual-mode persistence (Native Firestore + Local Filesystem Fallback),
idempotent revision management, 30-day default TTL lifecycle, and resume tokens.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from backend.storage.checkpoint_serializer import (
    calculate_expiration_timestamp,
    compute_checkpoint_state_hash,
    generate_resume_token,
    serialize_investigation_dag,
    serialize_subgoals,
)
from backend.storage.checkpoint_store_firestore import (
    delete_checkpoint_from_firestore,
    get_checkpoint_from_firestore,
    list_checkpoints_from_firestore,
    save_checkpoint_to_firestore,
)
from backend.storage.checkpoint_store_local import LocalCheckpointStore
from backend.storage.checkpoint_types import (
    AgentStateVector,
    CheckpointMetadata,
    ExecutionCheckpoint,
)

logger = logging.getLogger("lienmark.storage.checkpoint_store")


class CheckpointStore:
    """
    Unified persistence manager for execution checkpoints.
    Partitions data under /organizations/{org_id}/productions/{prod_id}/runs/{run_id}/checkpoints/{id}.
    Falls back gracefully to local disk and in-memory storage for offline CI.
    """

    def __init__(
        self,
        firestore_client: Optional[Any] = None,
        base_output_dir: str = "output/checkpoints",
        force_local: bool = False,
    ) -> None:
        self._firestore_client = firestore_client
        self._force_local = force_local
        self._local_store = LocalCheckpointStore(base_dir=base_output_dir)

    def _build_checkpoint_metadata(
        self,
        checkpoint_id: str,
        tenant_id: str,
        production_id: str,
        run_id: str,
        now_utc: str,
        exp_utc: str,
        ttl_days: int,
        created_by: str,
        trigger_reason: str,
        custom_attributes: Optional[Dict[str, Any]],
    ) -> CheckpointMetadata:
        """Constructs CheckpointMetadata model."""
        return CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            tenant_id=tenant_id,
            production_id=production_id,
            run_id=run_id,
            revision=1,
            created_at_utc=now_utc,
            updated_at_utc=now_utc,
            expires_at_utc=exp_utc,
            ttl_days=ttl_days,
            created_by=created_by,
            trigger_reason=trigger_reason,
            custom_attributes=custom_attributes or {},
        )

    def _prepare_checkpoint_components(
        self,
        agent_state: Union[AgentStateVector, Dict[str, Any]],
        investigation_dag: Optional[Any],
        uncompleted_subgoals: Optional[Sequence[Any]],
    ) -> Tuple[AgentStateVector, Dict[str, Any], List[Dict[str, Any]]]:
        """Serializes agent state vector, DAG dictionary, and subgoals list."""
        state_vec = (
            agent_state
            if isinstance(agent_state, AgentStateVector)
            else AgentStateVector.model_validate(agent_state)
        )
        dag_dict = serialize_investigation_dag(investigation_dag)
        subgoals_list = serialize_subgoals(uncompleted_subgoals)
        return state_vec, dag_dict, subgoals_list

    def create_checkpoint(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        agent_state: Union[AgentStateVector, Dict[str, Any]],
        checkpoint_id: Optional[str] = None,
        investigation_dag: Optional[Any] = None,
        uncompleted_subgoals: Optional[Sequence[Any]] = None,
        ttl_days: int = 30,
        trigger_reason: str = "suspension_for_clarification",
        created_by: str = "adk_orchestrator",
        custom_attributes: Optional[Dict[str, Any]] = None,
    ) -> ExecutionCheckpoint:
        """Constructs an ExecutionCheckpoint calculating TTL, state hash, and resume token."""
        cid = checkpoint_id or f"ckpt_{run_id}_{uuid.uuid4().hex[:8]}"
        state_vec, dag_dict, subgoals = self._prepare_checkpoint_components(
            agent_state, investigation_dag, uncompleted_subgoals
        )
        now_utc = datetime.now(timezone.utc).isoformat()
        exp_utc = calculate_expiration_timestamp(ttl_days=ttl_days)
        state_hash = compute_checkpoint_state_hash(state_vec, dag_dict, subgoals)
        resume_token = generate_resume_token(tenant_id, production_id, run_id, cid, 1, state_hash)
        meta = self._build_checkpoint_metadata(
            cid, tenant_id, production_id, run_id, now_utc, exp_utc,
            ttl_days, created_by, trigger_reason, custom_attributes
        )
        return ExecutionCheckpoint(
            checkpoint_id=cid, tenant_id=tenant_id, production_id=production_id, run_id=run_id,
            revision=1, metadata=meta, agent_state=state_vec, investigation_dag=dag_dict,
            uncompleted_subgoals=subgoals, state_hash=state_hash, resume_token=resume_token,
            created_at_utc=now_utc, expires_at_utc=exp_utc,
        )

    def save_checkpoint(self, checkpoint: ExecutionCheckpoint) -> ExecutionCheckpoint:
        """Saves checkpoint to local store and synchronizes to Firestore if available."""
        saved_local = self._local_store.save_checkpoint(checkpoint)
        if self._firestore_client is not None and not self._force_local:
            try:
                save_checkpoint_to_firestore(self._firestore_client, saved_local)
            except Exception as err:
                logger.warning(f"Failed to sync checkpoint to Firestore: {err}")
        return saved_local

    def get_checkpoint(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        checkpoint_id: str,
        allow_expired: bool = False,
    ) -> Optional[ExecutionCheckpoint]:
        """Retrieves checkpoint with fallback to local store."""
        if self._firestore_client is not None and not self._force_local:
            try:
                cp = get_checkpoint_from_firestore(
                    self._firestore_client,
                    tenant_id,
                    production_id,
                    run_id,
                    checkpoint_id,
                    allow_expired=allow_expired,
                )
                if cp is not None:
                    return cp
            except Exception as err:
                logger.debug(f"Firestore checkpoint lookup failed, falling back: {err}")

        return self._local_store.get_checkpoint(
            tenant_id, production_id, run_id, checkpoint_id, allow_expired=allow_expired
        )

    def get_latest_checkpoint(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        allow_expired: bool = False,
    ) -> Optional[ExecutionCheckpoint]:
        """Retrieves the highest revision or most recent checkpoint for an investigation run."""
        all_cps = self.list_checkpoints(
            tenant_id, production_id, run_id, include_expired=allow_expired
        )
        return all_cps[0] if all_cps else None

    def list_checkpoints(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        include_expired: bool = False,
    ) -> List[ExecutionCheckpoint]:
        """Lists all checkpoints for an investigation run."""
        if self._firestore_client is not None and not self._force_local:
            try:
                return list_checkpoints_from_firestore(
                    self._firestore_client,
                    tenant_id,
                    production_id,
                    run_id,
                    include_expired=include_expired,
                )
            except Exception as err:
                logger.debug(f"Firestore checkpoint list failed, falling back: {err}")

        return self._local_store.list_checkpoints(
            tenant_id, production_id, run_id, include_expired=include_expired
        )

    def delete_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, checkpoint_id: str
    ) -> bool:
        """Deletes checkpoint from both local store and Firestore."""
        deleted = self._local_store.delete_checkpoint(
            tenant_id, production_id, run_id, checkpoint_id
        )
        if self._firestore_client is not None and not self._force_local:
            try:
                delete_checkpoint_from_firestore(
                    self._firestore_client, tenant_id, production_id, run_id, checkpoint_id
                )
            except Exception as err:
                logger.warning(f"Failed to delete checkpoint from Firestore: {err}")
        return deleted


def get_checkpoint_store(
    firestore_client: Optional[Any] = None,
    base_output_dir: str = "output/checkpoints",
    force_local: bool = False,
) -> CheckpointStore:
    """Factory helper providing a configured CheckpointStore instance."""
    return CheckpointStore(
        firestore_client=firestore_client,
        base_output_dir=base_output_dir,
        force_local=force_local,
    )
