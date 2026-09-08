"""
backend/storage/checkpoint_store_local.py

Local filesystem and thread-safe in-memory store for execution checkpoints.
Provides offline CI, local test fallback, and sub-millisecond retrieval.
Pathing: output/checkpoints/{tenant_id}/{run_id}/{checkpoint_id}.json
Sprint 4.1: Checkpoint Storage & Persistence Layer.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import copy
import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from backend.storage.checkpoint_serializer import (
    generate_resume_token,
    is_checkpoint_expired,
    verify_resume_token,
)
from backend.storage.checkpoint_types import (
    CheckpointExpiredError,
    CheckpointMetadata,
    CorruptedResumeTokenError,
    CrossTenantCheckpointViolation,
    ExecutionCheckpoint,
)


class LocalCheckpointStore:
    """
    In-memory and local filesystem storage for execution checkpoints.
    Zero external dependencies; guarantees test execution offline without GCP credentials.
    """

    def __init__(self, base_dir: str = "output/checkpoints") -> None:
        self._base_dir = os.path.normpath(base_dir)
        self._lock = threading.RLock()
        self._memory_cache: Dict[Tuple[str, str, str, str], ExecutionCheckpoint] = {}

    def _resolve_file_path(self, tenant_id: str, run_id: str, checkpoint_id: str) -> str:
        """Computes path: output/checkpoints/{tenant_id}/{run_id}/{checkpoint_id}.json."""
        return os.path.join(
            self._base_dir,
            tenant_id.strip(),
            run_id.strip(),
            f"{checkpoint_id.strip()}.json",
        )

    def _bump_checkpoint_revision(
        self, checkpoint: ExecutionCheckpoint, prior_revision: int
    ) -> ExecutionCheckpoint:
        """Increments revision number and updates resume token."""
        new_rev = prior_revision + 1
        new_token = generate_resume_token(
            checkpoint.tenant_id,
            checkpoint.production_id,
            checkpoint.run_id,
            checkpoint.checkpoint_id,
            new_rev,
            checkpoint.state_hash,
        )
        updated_meta = checkpoint.metadata.model_copy(
            update={
                "revision": new_rev,
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        return checkpoint.model_copy(
            update={
                "revision": new_rev,
                "resume_token": new_token,
                "metadata": updated_meta,
            }
        )

    def save_checkpoint(self, checkpoint: object) -> object:
        """
        Saves checkpoint with idempotency: identical state preserves revision,
        mutated state increments revision and updates resume token.
        """
        with self._lock:
            t_id = getattr(checkpoint, "tenant_id")
            p_id = getattr(checkpoint, "production_id")
            r_id = getattr(checkpoint, "run_id")
            c_id = getattr(checkpoint, "checkpoint_id")
            key = (t_id, p_id, r_id, c_id)
            existing = self._get_raw_checkpoint(t_id, p_id, r_id, c_id)

            to_save = copy.deepcopy(checkpoint)
            if existing is not None and hasattr(to_save, "state_hash") and hasattr(existing, "state_hash"):
                if existing.state_hash == to_save.state_hash:
                    return copy.deepcopy(existing)
                to_save = self._bump_checkpoint_revision(to_save, existing.revision)

            if not self._verify_token(to_save):
                raise CorruptedResumeTokenError("Resume token does not match checkpoint state.")

            self._memory_cache[key] = copy.deepcopy(to_save)
            self._write_to_disk(to_save)
            return copy.deepcopy(to_save)

    def _verify_token(self, checkpoint: object) -> bool:
        """Verifies resume token against either orchestration or storage digest."""
        if hasattr(checkpoint, "agent_memory_snapshot"):
            from backend.orchestration.checkpoint_types import validate_resume_token
            return validate_resume_token(checkpoint, getattr(checkpoint, "resume_token", ""))
        return verify_resume_token(checkpoint)

    def _write_to_disk(self, checkpoint: object) -> None:
        """Writes serialized checkpoint JSON to the local filesystem."""
        file_path = self._resolve_file_path(
            getattr(checkpoint, "tenant_id"),
            getattr(checkpoint, "run_id"),
            getattr(checkpoint, "checkpoint_id"),
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.model_dump(), f, indent=2)

    def _get_raw_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, checkpoint_id: str
    ) -> Optional[object]:
        """Loads checkpoint from memory cache or filesystem without expiration validation."""
        key = (tenant_id.strip(), production_id.strip(), run_id.strip(), checkpoint_id.strip())
        if key in self._memory_cache:
            return self._memory_cache[key]

        file_path = self._resolve_file_path(tenant_id, run_id, checkpoint_id)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "agent_memory_snapshot" in data:
                from backend.orchestration.checkpoint_types import ExecutionCheckpoint as OrchCheckpoint
                cp = OrchCheckpoint.model_validate(data)
            else:
                cp = ExecutionCheckpoint.model_validate(data)
            if cp.tenant_id != tenant_id or cp.production_id != production_id:
                raise CrossTenantCheckpointViolation("Tenant or production boundary mismatch.")
            self._memory_cache[key] = cp
            return cp
        except CrossTenantCheckpointViolation:
            raise
        except Exception:
            return None

    def get_checkpoint(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        checkpoint_id: str,
        allow_expired: bool = False,
    ) -> Optional[object]:
        """Retrieves checkpoint validating boundary, expiration TTL, and resume token."""
        with self._lock:
            cp = self._get_raw_checkpoint(tenant_id, production_id, run_id, checkpoint_id)
            if cp is None:
                return None
            exp_ts = getattr(cp, "expires_at_utc", None) or getattr(cp, "ttl_expires_at_utc", "")
            if not allow_expired and is_checkpoint_expired(exp_ts):
                raise CheckpointExpiredError(
                    f"Checkpoint '{checkpoint_id}' expired at {exp_ts}."
                )
            if not self._verify_token(cp):
                raise CorruptedResumeTokenError(
                    f"Checkpoint '{checkpoint_id}' resume token failed integrity check."
                )
            return copy.deepcopy(cp)

    def list_checkpoints(
        self,
        tenant_id: str,
        production_id: str,
        run_id: str,
        include_expired: bool = False,
    ) -> List[object]:
        """Lists all checkpoints matching tenant, production, and run IDs."""
        with self._lock:
            results: List[object] = []
            run_dir = os.path.join(self._base_dir, tenant_id.strip(), run_id.strip())
            if os.path.isdir(run_dir):
                for fname in os.listdir(run_dir):
                    if fname.endswith(".json"):
                        cid = fname[:-5]
                        cp = self._get_raw_checkpoint(tenant_id, production_id, run_id, cid)
                        if cp:
                            exp_ts = getattr(cp, "expires_at_utc", None) or getattr(cp, "ttl_expires_at_utc", "")
                            if include_expired or not is_checkpoint_expired(exp_ts):
                                results.append(copy.deepcopy(cp))

            for (t, p, r, _), cp in self._memory_cache.items():
                if t == tenant_id and p == production_id and r == run_id:
                    if not any(getattr(r_item, "checkpoint_id") == getattr(cp, "checkpoint_id") for r_item in results):
                        exp_ts = getattr(cp, "expires_at_utc", None) or getattr(cp, "ttl_expires_at_utc", "")
                        if include_expired or not is_checkpoint_expired(exp_ts):
                            results.append(copy.deepcopy(cp))

            results.sort(key=lambda c: (getattr(c, "revision", 1), getattr(c, "created_at_utc", "")), reverse=True)
            return results

    def delete_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, checkpoint_id: str
    ) -> bool:
        """Deletes checkpoint from memory and filesystem."""
        with self._lock:
            key = (tenant_id.strip(), production_id.strip(), run_id.strip(), checkpoint_id.strip())
            removed = self._memory_cache.pop(key, None) is not None
            file_path = self._resolve_file_path(tenant_id, run_id, checkpoint_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                removed = True
            return removed

    def clear(self) -> None:
        """Utility for test suite cleanup."""
        with self._lock:
            self._memory_cache.clear()
