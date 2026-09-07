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

    def save_checkpoint(self, checkpoint: ExecutionCheckpoint) -> ExecutionCheckpoint:
        """
        Saves checkpoint with idempotency: identical state preserves revision,
        mutated state increments revision and updates resume token.
        """
        with self._lock:
            key = (
                checkpoint.tenant_id,
                checkpoint.production_id,
                checkpoint.run_id,
                checkpoint.checkpoint_id,
            )
            existing = self._get_raw_checkpoint(
                checkpoint.tenant_id,
                checkpoint.production_id,
                checkpoint.run_id,
                checkpoint.checkpoint_id,
            )

            to_save = copy.deepcopy(checkpoint)
            if existing is not None:
                if existing.state_hash == to_save.state_hash:
                    return copy.deepcopy(existing)
                to_save = self._bump_checkpoint_revision(to_save, existing.revision)

            if not verify_resume_token(to_save):
                raise CorruptedResumeTokenError("Resume token does not match checkpoint state.")

            self._memory_cache[key] = copy.deepcopy(to_save)
            self._write_to_disk(to_save)
            return copy.deepcopy(to_save)

    def _write_to_disk(self, checkpoint: ExecutionCheckpoint) -> None:
        """Writes serialized checkpoint JSON to the local filesystem."""
        file_path = self._resolve_file_path(
            checkpoint.tenant_id, checkpoint.run_id, checkpoint.checkpoint_id
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.model_dump(), f, indent=2)

    def _get_raw_checkpoint(
        self, tenant_id: str, production_id: str, run_id: str, checkpoint_id: str
    ) -> Optional[ExecutionCheckpoint]:
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
            checkpoint = ExecutionCheckpoint.model_validate(data)
            if checkpoint.tenant_id != tenant_id or checkpoint.production_id != production_id:
                raise CrossTenantCheckpointViolation("Tenant or production boundary mismatch.")
            self._memory_cache[key] = checkpoint
            return checkpoint
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
    ) -> Optional[ExecutionCheckpoint]:
        """Retrieves checkpoint validating boundary, expiration TTL, and resume token."""
        with self._lock:
            cp = self._get_raw_checkpoint(tenant_id, production_id, run_id, checkpoint_id)
            if cp is None:
                return None
            if not allow_expired and is_checkpoint_expired(cp.expires_at_utc):
                raise CheckpointExpiredError(
                    f"Checkpoint '{checkpoint_id}' expired at {cp.expires_at_utc}."
                )
            if not verify_resume_token(cp):
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
    ) -> List[ExecutionCheckpoint]:
        """Lists all checkpoints matching tenant, production, and run IDs."""
        with self._lock:
            results: List[ExecutionCheckpoint] = []
            run_dir = os.path.join(self._base_dir, tenant_id.strip(), run_id.strip())
            if os.path.isdir(run_dir):
                for fname in os.listdir(run_dir):
                    if fname.endswith(".json"):
                        cid = fname[:-5]
                        cp = self._get_raw_checkpoint(tenant_id, production_id, run_id, cid)
                        if cp and (include_expired or not is_checkpoint_expired(cp.expires_at_utc)):
                            results.append(copy.deepcopy(cp))

            for (t, p, r, _), cp in self._memory_cache.items():
                if t == tenant_id and p == production_id and r == run_id:
                    if not any(r_item.checkpoint_id == cp.checkpoint_id for r_item in results):
                        if include_expired or not is_checkpoint_expired(cp.expires_at_utc):
                            results.append(copy.deepcopy(cp))

            results.sort(key=lambda c: (c.revision, c.created_at_utc), reverse=True)
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
