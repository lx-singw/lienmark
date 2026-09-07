"""
backend/storage/policy_store_types.py

Domain models, data contracts, and exceptions for PolicyStore persistence layer.
Sprint 5.2 - Durable Versioned Policy Store & Dispatch Intents.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PolicyStoreMode(str, Enum):
    """Execution persistence modes for policy storage."""
    FIRESTORE = "firestore"
    LOCAL_DISK = "local_disk"


class PolicyStoreError(RuntimeError):
    """Base exception for policy storage operations."""
    pass


class PolicyConcurrencyError(PolicyStoreError):
    """Raised when expected version preconditions or concurrency checks fail."""
    pass


def compute_canonical_digest(payload: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 digest of dictionary payload."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def next_policy_version_id(current_v: Optional[str]) -> str:
    """Calculates next monotonically increasing revision identifier (e.g. v1 -> v2)."""
    if not current_v:
        return "v1"
    match = re.match(r"^(.*?)([0-9]+)$", current_v)
    if match:
        prefix, num_str = match.group(1), match.group(2)
        return f"{prefix}{int(num_str) + 1}"
    return f"{current_v}_v2"


def detect_affected_rules(old_cfg: Optional[Dict[str, Any]], new_cfg: Dict[str, Any]) -> List[str]:
    """Calculates delta keys between preceding and new policy configurations."""
    if not old_cfg:
        return sorted(list(new_cfg.keys()))
    changed: List[str] = []
    for k in set(old_cfg.keys()).union(new_cfg.keys()):
        if old_cfg.get(k) != new_cfg.get(k):
            changed.append(k)
    return sorted(changed)


def atomic_write_json(file_path: str, data: Dict[str, Any]) -> None:
    """Writes JSON payload using atomic rename to guarantee crash-consistency."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = f"{file_path}.tmp.{uuid.uuid4().hex}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise PolicyStoreError(f"Failed atomic write to '{file_path}': {exc}") from exc


def read_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Safely loads JSON payload from disk or returns None if absent."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise PolicyStoreError(f"Corrupted file '{file_path}': {exc}") from exc


class PolicyVersionRecord(BaseModel):
    """
    Immutable snapshot of a studio policy revision.
    Captures full configuration, SHA-256 digest, author, and ledger provenance.
    """
    model_config = ConfigDict(extra="ignore")

    version_id: str = Field(..., description="Revision identifier (e.g. v1, v2)")
    policy_id: str = Field(..., description="Policy configuration identifier")
    org_id: str = Field(..., description="Owning studio organization boundary")
    policy_config: Dict[str, Any] = Field(..., description="Configuration dictionary")
    policy_digest: str = Field(..., description="Canonical SHA-256 payload digest")
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp",
    )
    created_by_actor_id: str = Field(..., description="Admin actor committing revision")
    ledger_event_id: Optional[str] = Field(
        default=None, description="Cryptographic audit ledger event ID"
    )
    idempotency_key: Optional[str] = Field(
        default=None, description="Optional idempotency key preventing duplicate commits"
    )


class PolicyChangeDispatchIntent(BaseModel):
    """
    Asynchronous dispatch intent emitted atomically upon policy revision activation.
    Tracks downstream revalidation pipeline tasks and rule changes.
    """
    model_config = ConfigDict(extra="ignore")

    intent_id: str = Field(..., description="Unique intent identifier")
    org_id: str = Field(..., description="Target studio organization identifier")
    from_version: Optional[str] = Field(
        default=None, description="Predecessor version ID, if any"
    )
    to_version: str = Field(..., description="Newly activated version ID")
    status: str = Field(
        default="PENDING",
        description="Dispatch status: PENDING | PROCESSING | COMPLETED | FAILED",
    )
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp",
    )
    affected_rules: List[str] = Field(
        default_factory=list,
        description="Identifiers of modified, added, or removed rules",
    )
