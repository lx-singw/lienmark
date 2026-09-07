"""backend/storage/ledger.py: Append-only cryptographic audit ledger for film & TV E&O clearance."""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LedgerTamperError(Exception):
    """Raised when an illegal attempt is made to mutate, update, or delete ledger entries."""
    pass

class LedgerIntegrityError(Exception):
    """Raised when cryptographic verification or chain continuity fails."""
    pass


def compute_canonical_digest(payload: Dict[str, Any]) -> str:
    """Computes SHA-256 hex digest of canonically serialized JSON (sorted keys, compact)."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def compute_entry_hash(
    previous_event_hash: str, payload_digest: str, timestamp_utc: str, sequence_number: int
) -> str:
    """Computes SHA-256 entry hash chaining previous hash, payload digest, timestamp, sequence."""
    raw = f"{previous_event_hash}{payload_digest}{timestamp_utc}{sequence_number}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ImmutablePayload(dict):
    """Read-only dictionary that raises LedgerTamperError on any mutation attempt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for k, v in list(self.items()):
            if isinstance(v, dict) and not isinstance(v, ImmutablePayload):
                super().__setitem__(k, ImmutablePayload(v))

    def __setitem__(self, key: Any, value: Any) -> None: raise LedgerTamperError(f"Cannot modify '{key}'")
    def __delitem__(self, key: Any) -> None: raise LedgerTamperError(f"Cannot delete '{key}'")
    def pop(self, *args: Any, **kwargs: Any) -> Any: raise LedgerTamperError("pop() forbidden")
    def popitem(self) -> Tuple[Any, Any]: raise LedgerTamperError("popitem() forbidden")
    def clear(self) -> None: raise LedgerTamperError("clear() forbidden")
    def update(self, *args: Any, **kwargs: Any) -> None: raise LedgerTamperError("update() forbidden")
    def setdefault(self, key: Any, default: Any = None) -> Any: raise LedgerTamperError("forbidden")


class AuditEvent(BaseModel):
    """Cryptographic audit event representing an append-only ledger block."""
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


class CryptographicLedger:
    """Append-only, tamper-evident cryptographic audit ledger for film & TV E&O clearance."""

    GENESIS_HASH: str = "0" * 64

    def __init__(self, repository: Optional[Any] = None) -> None:
        self._repository: Optional[Any] = repository
        self._chains: Dict[str, List[AuditEvent]] = {}
        self._lock: threading.RLock = threading.RLock()

    def initialize_production_ledger(
        self, tenant_id: str, production_id: str, actor_id: str
    ) -> AuditEvent:
        """Initializes a new production audit ledger with a genesis block (seq 1)."""
        with self._lock:
            if production_id in self._chains and len(self._chains[production_id]) > 0:
                raise LedgerIntegrityError(f"Ledger for production '{production_id}' is already initialized.")
            payload = {"action": "GENESIS", "production_id": production_id, "tenant_id": tenant_id}
            digest = compute_canonical_digest(payload)
            timestamp = datetime.now(timezone.utc).isoformat()
            seq = 1
            prev_hash = self.GENESIS_HASH
            entry_hash = compute_entry_hash(prev_hash, digest, timestamp, seq)
            event = AuditEvent(
                event_id=f"evt_{uuid.uuid4().hex}",
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id=actor_id,
                action_type="GENESIS",
                payload=ImmutablePayload(payload),
                payload_digest=digest,
                sequence_number=seq,
                timestamp_utc=timestamp,
                previous_event_hash=prev_hash,
                entry_hash=entry_hash,
            )
            self._chains[production_id] = [event]
            self._persist_event(event)
            return event

    def append_event(
        self,
        tenant_id: str,
        production_id: str,
        actor_id: str,
        action_type: str,
        payload: Dict[str, Any],
    ) -> AuditEvent:
        """Appends a new event linking cryptographically to the parent block."""
        with self._lock:
            chain = self._chains.get(production_id)
            if not chain:
                raise LedgerIntegrityError(f"Ledger for '{production_id}' not initialized. Call genesis first.")
            prev_event = chain[-1]
            seq = prev_event.sequence_number + 1
            prev_hash = prev_event.entry_hash
            digest = compute_canonical_digest(payload)
            timestamp = datetime.now(timezone.utc).isoformat()
            entry_hash = compute_entry_hash(prev_hash, digest, timestamp, seq)
            event = AuditEvent(
                event_id=f"evt_{uuid.uuid4().hex}",
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id=actor_id,
                action_type=action_type,
                payload=ImmutablePayload(copy.deepcopy(payload)),
                payload_digest=digest,
                sequence_number=seq,
                timestamp_utc=timestamp,
                previous_event_hash=prev_hash,
                entry_hash=entry_hash,
            )
            chain.append(event)
            self._persist_event(event)
            return event

    def record_supersession(
        self,
        tenant_id: str,
        production_id: str,
        actor_id: str,
        superseded_event_id: str,
        superseding_payload: Dict[str, Any],
    ) -> AuditEvent:
        """Records supersession of a prior event without mutating existing history."""
        with self._lock:
            chain = self._chains.get(production_id)
            if not chain:
                raise LedgerIntegrityError(f"Ledger for '{production_id}' is not initialized.")
            target = next((e for e in chain if e.event_id == superseded_event_id), None)
            if not target:
                raise LedgerIntegrityError(f"Superseded event '{superseded_event_id}' not found in '{production_id}'.")
            payload = copy.deepcopy(superseding_payload)
            payload["superseded_event_id"] = superseded_event_id
            return self.append_event(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id=actor_id,
                action_type="SUPERSEDED",
                payload=payload,
            )

    def verify_chain(self, production_id: str) -> Tuple[bool, Optional[str], int]:
        """Verifies sequence numbers, parent hash continuity, and payload digests."""
        with self._lock:
            chain = self._chains.get(production_id)
            if not chain:
                return False, f"Ledger for production '{production_id}' is empty or not found", 0
            for i, event in enumerate(chain):
                if i == 0:
                    if event.sequence_number != 1:
                        return False, f"Invalid genesis sequence number: {event.sequence_number}", 0
                    if event.previous_event_hash != self.GENESIS_HASH:
                        return False, "Invalid genesis previous_event_hash", 0
                else:
                    prev = chain[i - 1]
                    if event.sequence_number != prev.sequence_number + 1:
                        return False, f"Non-monotonic sequence number at seq {event.sequence_number}", i
                    if event.previous_event_hash != prev.entry_hash:
                        return False, f"Broken chain link at seq {event.sequence_number}", i
                if event.payload_digest != compute_canonical_digest(event.payload):
                    return False, f"Payload digest mismatch at seq {event.sequence_number}", i
                expected_entry_hash = compute_entry_hash(
                    event.previous_event_hash,
                    event.payload_digest,
                    event.timestamp_utc,
                    event.sequence_number,
                )
                if event.entry_hash != expected_entry_hash:
                    return False, f"Entry hash mismatch at seq {event.sequence_number}", i
            return True, None, len(chain)

    def get_events(
        self, production_id: str, start_seq: int = 1, limit: int = 100
    ) -> List[AuditEvent]:
        """Retrieves audit events starting from start_seq up to limit."""
        with self._lock:
            chain = self._chains.get(production_id, [])
            return [e for e in chain if e.sequence_number >= start_seq][:limit]

    def update_event(self, *args: Any, **kwargs: Any) -> None:
        """Modifying ledger entries is strictly prohibited by cryptographic audit policy."""
        raise LedgerTamperError("Cryptographic ledger entries are immutable and cannot be updated.")

    def delete_event(self, *args: Any, **kwargs: Any) -> None:
        """Deleting ledger entries is strictly prohibited by cryptographic audit policy."""
        raise LedgerTamperError("Cryptographic ledger is append-only; entries cannot be deleted.")

    def __setitem__(self, key: Any, value: Any) -> None:
        raise LedgerTamperError("Cryptographic ledger does not support direct index assignment.")

    def __delitem__(self, key: Any) -> None:
        raise LedgerTamperError("Cryptographic ledger does not support entry deletion.")

    def _persist_event(self, event: AuditEvent) -> None:
        """Dispatches event to backing repository if available."""
        if self._repository is not None and hasattr(self._repository, "append_audit_event"):
            try:
                self._repository.append_audit_event(
                    production_id=event.production_id,
                    run_id="default_run",
                    event_payload=event.model_dump(),
                )
            except Exception:
                pass
