"""
backend/storage/checkpoint_serializer.py

Serialization helpers, cryptographic hashing, and TTL expiration utilities
for execution checkpoints.
Sprint 4.1: Checkpoint Storage & Persistence Layer.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel

from backend.storage.checkpoint_types import (
    AgentStateVector,
    CheckpointMetadata,
    ExecutionCheckpoint,
    InvalidCheckpointStateError,
)


def calculate_expiration_timestamp(
    ttl_days: int = 30, base_time: Optional[datetime] = None
) -> str:
    """Calculates ISO 8601 UTC expiration timestamp based on retention TTL days."""
    reference = base_time or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    expiration = reference + timedelta(days=ttl_days)
    return expiration.isoformat()


def is_checkpoint_expired(
    expires_at_utc: str, current_time: Optional[datetime] = None
) -> bool:
    """Evaluates whether an ISO 8601 UTC expiration timestamp has elapsed."""
    try:
        exp_dt = datetime.fromisoformat(expires_at_utc)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        now_dt = current_time or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        return now_dt >= exp_dt
    except Exception as exc:
        raise InvalidCheckpointStateError(
            f"Malformed expiration timestamp '{expires_at_utc}': {exc}"
        ) from exc


def canonical_json_dumps(data: Any) -> str:
    """Generates canonical deterministic JSON string with sorted keys."""
    def _default_encoder(obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        if hasattr(obj, "value"):
            return obj.value
        return str(obj)

    return json.dumps(
        data,
        default=_default_encoder,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def compute_checkpoint_state_hash(
    agent_state: Any,
    investigation_dag: Optional[Any] = None,
    uncompleted_subgoals: Optional[Sequence[Any]] = None,
) -> str:
    """Computes deterministic SHA-256 digest of core execution state components."""
    state_dict = (
        agent_state.model_dump() if isinstance(agent_state, BaseModel) else dict(agent_state)
    )
    dag_dict = (
        investigation_dag.model_dump()
        if isinstance(investigation_dag, BaseModel)
        else (investigation_dag or {})
    )
    subgoals_list = [
        sg.model_dump() if isinstance(sg, BaseModel) else dict(sg)
        for sg in (uncompleted_subgoals or [])
    ]

    canonical_payload = {
        "agent_state": state_dict,
        "investigation_dag": dag_dict,
        "uncompleted_subgoals": subgoals_list,
    }
    encoded = canonical_json_dumps(canonical_payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_resume_token(
    tenant_id: str,
    production_id: str,
    run_id: str,
    checkpoint_id: str,
    revision: int,
    state_hash: str,
) -> str:
    """Generates a cryptographic SHA-256 resume token bound to checkpoint identity."""
    token_seed = (
        f"{tenant_id.strip()}:{production_id.strip()}:{run_id.strip()}:"
        f"{checkpoint_id.strip()}:{revision}:{state_hash}"
    )
    return hashlib.sha256(token_seed.encode("utf-8")).hexdigest()


def verify_resume_token(checkpoint: ExecutionCheckpoint) -> bool:
    """Verifies that an ExecutionCheckpoint resume token matches expected digest."""
    expected_token = generate_resume_token(
        tenant_id=checkpoint.tenant_id,
        production_id=checkpoint.production_id,
        run_id=checkpoint.run_id,
        checkpoint_id=checkpoint.checkpoint_id,
        revision=checkpoint.revision,
        state_hash=checkpoint.state_hash,
    )
    return checkpoint.resume_token == expected_token


def serialize_investigation_dag(dag: Any) -> Optional[Dict[str, Any]]:
    """Converts an InvestigationPlanDAG model or dict into serializable dictionary."""
    if dag is None:
        return None
    if isinstance(dag, BaseModel):
        return dag.model_dump()
    if isinstance(dag, dict):
        return dict(dag)
    raise InvalidCheckpointStateError(f"Unsupported DAG representation type: {type(dag)}")


def serialize_subgoals(subgoals: Optional[Sequence[Any]]) -> List[Dict[str, Any]]:
    """Serializes a collection of InvestigationSubgoals or dicts into standard dicts."""
    if not subgoals:
        return []
    result: List[Dict[str, Any]] = []
    for item in subgoals:
        if isinstance(item, BaseModel):
            result.append(item.model_dump())
        elif isinstance(item, dict):
            result.append(dict(item))
        else:
            raise InvalidCheckpointStateError(f"Unsupported subgoal type: {type(item)}")
    return result
