"""
backend/storage/checkpoint_store.py

Durable Checkpoint Storage & Retention Pinning Layer for Lienmark Sprint 4.1.
Coordinates dual-mode persistence, retention pinning, and resume token validation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple, Union

from backend.storage.checkpoint_serializer import (
    calculate_expiration_timestamp,
    compute_checkpoint_state_hash,
    generate_resume_token,
    is_checkpoint_expired,
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
    CheckpointExpiredError,
    CheckpointMetadata,
    ExecutionCheckpoint,
)

logger = logging.getLogger("lienmark.storage.checkpoint_store")


class CheckpointStore:
    """Unified persistence manager with retention pinning for execution checkpoints."""

    def __init__(
        self,
        firestore_client: Optional[object] = None,
        base_output_dir: str = "output/checkpoints",
        force_local: bool = False,
        clarification_store: Optional[object] = None,
    ) -> None:
        self._firestore_client = firestore_client
        self._force_local = force_local
        self._local_store = LocalCheckpointStore(base_dir=base_output_dir)
        self._clarification_store = clarification_store

    def _get_clrf_store(self) -> Optional[object]:
        """Resolves clarification store instance for retention pinning queries."""
        if self._clarification_store is not None:
            return self._clarification_store
        try:
            from backend.storage.clarification_store import get_clarification_store
            return get_clarification_store()
        except ImportError:
            return None

    def is_checkpoint_pinned(self, tenant_id: str, run_id: str, checkpoint: object) -> bool:
        """Determines if a checkpoint is pinned by active PENDING clarifications."""
        store = self._get_clrf_store()
        if store is None or not hasattr(store, "is_checkpoint_pinned"):
            return False
        clrf_ids: List[str] = []
        if hasattr(checkpoint, "pending_clarification_ids"):
            clrf_ids = list(getattr(checkpoint, "pending_clarification_ids", []))
        elif hasattr(checkpoint, "agent_state"):
            clrf_ids = list(getattr(checkpoint.agent_state, "pending_clarification_ids", []))
        return store.is_checkpoint_pinned(run_id=run_id, tenant_id=tenant_id, clarification_ids=clrf_ids)

    def _build_checkpoint_metadata(
        self,
        cid: str,
        t_id: str,
        p_id: str,
        r_id: str,
        now: str,
        exp: str,
        ttl: int,
        creator: str,
        reason: str,
        attrs: Optional[Dict[str, object]],
    ) -> CheckpointMetadata:
        """Constructs CheckpointMetadata model."""
        return CheckpointMetadata(
            checkpoint_id=cid, tenant_id=t_id, production_id=p_id, run_id=r_id,
            revision=1, created_at_utc=now, updated_at_utc=now, expires_at_utc=exp,
            ttl_days=ttl, created_by=creator, trigger_reason=reason,
            custom_attributes=attrs or {},
        )

    def _prepare_checkpoint_components(
        self,
        agent_state: Union[AgentStateVector, Dict[str, object]],
        investigation_dag: Optional[object],
        uncompleted_subgoals: Optional[Sequence[object]],
    ) -> Tuple[AgentStateVector, Dict[str, object], List[Dict[str, object]]]:
        """Serializes agent state vector, DAG dictionary, and subgoals list."""
        state_vec = (
            agent_state if isinstance(agent_state, AgentStateVector)
            else AgentStateVector.model_validate(agent_state)
        )
        return (
            state_vec,
            serialize_investigation_dag(investigation_dag),
            serialize_subgoals(uncompleted_subgoals),
        )

    def create_checkpoint(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        agent_state: Union[AgentStateVector, Dict[str, object]],
        checkpoint_id: Optional[str] = None,
        investigation_dag: Optional[object] = None,
        uncompleted_subgoals: Optional[Sequence[object]] = None,
        ttl_days: int = 30,
        trigger_reason: str = "suspension_for_clarification",
        created_by: str = "adk_orchestrator",
        custom_attributes: Optional[Dict[str, object]] = None,
    ) -> ExecutionCheckpoint:
        """Constructs ExecutionCheckpoint calculating TTL, state hash, and resume token."""
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
            ttl_days, created_by, trigger_reason, custom_attributes,
        )
        return ExecutionCheckpoint(
            checkpoint_id=cid, tenant_id=tenant_id, production_id=production_id, run_id=run_id,
            revision=1, metadata=meta, agent_state=state_vec, investigation_dag=dag_dict,
            uncompleted_subgoals=subgoals, state_hash=state_hash, resume_token=resume_token,
            created_at_utc=now_utc, expires_at_utc=exp_utc,
        )

    def save_checkpoint(self, checkpoint: object) -> object:
        """Saves checkpoint to local store and synchronizes to Firestore if available."""
        saved_local = self._local_store.save_checkpoint(checkpoint)
        if self._firestore_client is not None and not self._force_local and hasattr(saved_local, "metadata"):
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
    ) -> Optional[object]:
        """Retrieves checkpoint with fallback to local store and retention pinning check."""
        cp = None
        if self._firestore_client is not None and not self._force_local:
            try:
                cp = get_checkpoint_from_firestore(
                    self._firestore_client, tenant_id, production_id, run_id, checkpoint_id, allow_expired=True
                )
            except Exception as err:
                logger.debug(f"Firestore checkpoint lookup failed: {err}")
        if cp is None:
            cp = self._local_store.get_checkpoint(
                tenant_id, production_id, run_id, checkpoint_id, allow_expired=True
            )
        if cp is None:
            return None

        exp_ts = getattr(cp, "expires_at_utc", None) or getattr(cp, "ttl_expires_at_utc", "")
        if not allow_expired and is_checkpoint_expired(exp_ts):
            if self.is_checkpoint_pinned(tenant_id, run_id, cp):
                logger.info(f"Checkpoint '{checkpoint_id}' expiration prevented by retention pinning.")
                return cp
            raise CheckpointExpiredError(f"Checkpoint '{checkpoint_id}' expired at {exp_ts}.")
        return cp

    def get_latest_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, allow_expired: bool = False
    ) -> Optional[object]:
        """Retrieves highest revision or most recent checkpoint for an investigation run."""
        all_cps = self.list_checkpoints(tenant_id, production_id, run_id, include_expired=allow_expired)
        return all_cps[0] if all_cps else None

    def list_checkpoints(
        self, tenant_id: str, production_id: str, run_id: str, include_expired: bool = False
    ) -> List[object]:
        """Lists checkpoints for run, retaining pinned checkpoints even if TTL expired."""
        cps = self._local_store.list_checkpoints(tenant_id, production_id, run_id, include_expired=True)
        if include_expired:
            return cps
        valid_cps: List[object] = []
        for cp in cps:
            exp_ts = getattr(cp, "expires_at_utc", None) or getattr(cp, "ttl_expires_at_utc", "")
            if not is_checkpoint_expired(exp_ts) or self.is_checkpoint_pinned(tenant_id, run_id, cp):
                valid_cps.append(cp)
        return valid_cps

    def delete_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, checkpoint_id: str
    ) -> bool:
        """Deletes checkpoint if not pinned by active PENDING clarifications."""
        cp = self.get_checkpoint(tenant_id, production_id, run_id, checkpoint_id, allow_expired=True)
        if cp is not None and self.is_checkpoint_pinned(tenant_id, run_id, cp):
            logger.warning(f"Checkpoint '{checkpoint_id}' deletion prevented: pinned by PENDING clarifications.")
            return False
        deleted = self._local_store.delete_checkpoint(tenant_id, production_id, run_id, checkpoint_id)
        if self._firestore_client is not None and not self._force_local:
            try:
                delete_checkpoint_from_firestore(
                    self._firestore_client, tenant_id, production_id, run_id, checkpoint_id
                )
            except Exception as err:
                logger.warning(f"Failed to delete checkpoint from Firestore: {err}")
        return deleted


def get_checkpoint_store(
    firestore_client: Optional[object] = None,
    base_output_dir: str = "output/checkpoints",
    force_local: bool = False,
    clarification_store: Optional[object] = None,
) -> CheckpointStore:
    """Factory helper providing a configured CheckpointStore instance."""
    return CheckpointStore(
        firestore_client=firestore_client,
        base_output_dir=base_output_dir,
        force_local=force_local,
        clarification_store=clarification_store,
    )
