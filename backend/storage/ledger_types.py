"""
Lienmark Cryptographic Ledger Domain Models and Types.

Provides immutable payload wrappers, audit event data models, cryptographic
hashing functions, and domain exceptions for tamper-evident E&O audit ledgers.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LedgerTamperError(Exception):
    """Raised when an illegal attempt is made to mutate, update, or delete ledger entries."""
    pass


class LedgerIntegrityError(Exception):
    """Raised when cryptographic verification or chain continuity fails."""
    pass


def compute_canonical_digest(payload: Dict[str, Any]) -> str:
    """
    Computes the SHA-256 hex digest of canonically serialized JSON.
    
    Guarantees deterministic serialization across runtimes by enforcing
    sorted keys, compact separators (no trailing whitespace), and ASCII encoding.
    """
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_entry_hash(
    previous_event_hash: str,
    payload_digest: str,
    timestamp_utc: str,
    sequence_number: int,
) -> str:
    """
    Computes the canonical SHA-256 entry hash linking cryptographic blocks.
    
    Hash formula:
        SHA256(previous_event_hash + payload_digest + timestamp_utc + str(sequence_number))
    """
    raw = f"{previous_event_hash}{payload_digest}{timestamp_utc}{sequence_number}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ImmutablePayload(dict):
    """
    Read-only dictionary that raises LedgerTamperError on any mutation attempt.
    
    Recursively wraps nested dictionaries to prevent in-place mutation of
    child nodes within audit event payloads.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for key, val in list(self.items()):
            if isinstance(val, dict) and not isinstance(val, ImmutablePayload):
                super().__setitem__(key, ImmutablePayload(val))

    def __setitem__(self, key: Any, value: Any) -> None:
        raise LedgerTamperError(f"Cannot modify immutable ledger payload key '{key}'")

    def __delitem__(self, key: Any) -> None:
        raise LedgerTamperError(f"Cannot delete immutable ledger payload key '{key}'")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise LedgerTamperError("pop() is forbidden on immutable ledger payloads")

    def popitem(self) -> Tuple[Any, Any]:
        raise LedgerTamperError("popitem() is forbidden on immutable ledger payloads")

    def clear(self) -> None:
        raise LedgerTamperError("clear() is forbidden on immutable ledger payloads")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise LedgerTamperError("update() is forbidden on immutable ledger payloads")

    def setdefault(self, key: Any, default: Any = None) -> Any:
        raise LedgerTamperError("setdefault() is forbidden on immutable ledger payloads")


class AuditEvent(BaseModel):
    """
    Cryptographic audit event representing an append-only ledger block.
    
    Each block contains a monotonic sequence number, canonical payload digest,
    and a cryptographic link to the entry hash of the immediate predecessor.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    tenant_id: str
    production_id: str
    actor_id: str
    action_type: str
    payload: Dict[str, Any]
    payload_digest: str
    sequence_number: int = Field(..., ge=1)
    timestamp_utc: str
    previous_event_hash: str
    entry_hash: str

    @field_validator("payload", mode="after")
    @classmethod
    def _validate_payload_immutable(cls, v: Any) -> ImmutablePayload:
        return v if isinstance(v, ImmutablePayload) else ImmutablePayload(v)

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, "__pydantic_fields_set__"):
            raise LedgerTamperError(f"AuditEvent is immutable; cannot modify attribute '{name}'")
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        raise LedgerTamperError(f"AuditEvent is immutable; cannot delete attribute '{name}'")
