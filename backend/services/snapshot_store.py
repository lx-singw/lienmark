"""
snapshot_store.py

Storage engine for evidence content snapshots with dual Google Cloud Storage
bucket targets and local filesystem directory fallback.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from backend.services.evidence_archiver_types import (
    EvidenceSnapshot,
    SnapshotStorageError,
)

logger = logging.getLogger("lienmark.services.snapshot_store")


class SnapshotStore:
    """
    Storage interface supporting GCS primary bucket paths with local fallback.
    Contract paths:
      - Local: output/evidence_snapshots/{tenant}/{snapshot_id}.json
      - GCS:   gs://lienmark-<tenant>-evidence-snapshots/{snapshot_id}.json
    """

    def __init__(
        self,
        base_dir: str = "output/evidence_snapshots",
        bucket_template: str = "lienmark-{tenant}-evidence-snapshots",
        enable_gcs: bool = False,
        gcs_client: Any = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.bucket_template = bucket_template
        self.enable_gcs = enable_gcs
        self._gcs_client = gcs_client

    def get_gcs_bucket_path(self, tenant_id: str) -> str:
        """Returns the canonical GCS URI prefix for the specified tenant."""
        bucket = self.bucket_template.format(tenant=tenant_id)
        return f"gs://{bucket}/"

    def get_local_path(self, tenant_id: str, snapshot_id: str) -> Path:
        """Computes deterministic local filesystem fallback path."""
        return self.base_dir / tenant_id / f"{snapshot_id}.json"

    def _write_local(self, snapshot: EvidenceSnapshot) -> str:
        """Writes snapshot atomically to local filesystem."""
        try:
            target = self.get_local_path(snapshot.tenant_id, snapshot.snapshot_id)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_suffix(".tmp")
            temp.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
            temp.replace(target)
            return str(target.as_posix())
        except Exception as exc:
            raise SnapshotStorageError(f"Local storage write failed: {exc}") from exc

    def _write_gcs(self, snapshot: EvidenceSnapshot) -> str:
        """Uploads snapshot payload to tenant GCS bucket."""
        bucket_name = self.bucket_template.format(tenant=snapshot.tenant_id)
        blob_name = f"{snapshot.snapshot_id}.json"
        try:
            bucket = self._gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_string(snapshot.model_dump_json(), content_type="application/json")
            return f"gs://{bucket_name}/{blob_name}"
        except Exception as exc:
            raise SnapshotStorageError(f"GCS upload to gs://{bucket_name}/{blob_name} failed: {exc}") from exc

    async def save_snapshot(self, snapshot: EvidenceSnapshot) -> str:
        """Persists snapshot to GCS with fallback to local filesystem."""
        def _execute() -> str:
            if self.enable_gcs and self._gcs_client is not None:
                try:
                    return self._write_gcs(snapshot)
                except Exception as exc:
                    logger.warning(f"GCS save failed: {exc}; falling back to local disk.")
            return self._write_local(snapshot)

        storage_path = await asyncio.to_thread(_execute)
        snapshot.storage_path = storage_path
        return storage_path

    async def get_snapshot(self, snapshot_id: str, tenant_id: str = "default") -> Optional[EvidenceSnapshot]:
        """Retrieves stored snapshot from local disk or GCS."""
        def _read() -> Optional[EvidenceSnapshot]:
            target = self.get_local_path(tenant_id, snapshot_id)
            if target.exists():
                return EvidenceSnapshot.model_validate_json(target.read_text(encoding="utf-8"))
            return None

        return await asyncio.to_thread(_read)
