"""
backend/storage/checkpoint_store_firestore.py

Firestore persistence adapter for execution checkpoints.
Partitions checkpoints strictly under the multi-tenant collection hierarchy:
/organizations/{org_id}/productions/{prod_id}/runs/{run_id}/checkpoints/{checkpoint_id}
Sprint 4.1: Checkpoint Storage & Persistence Layer.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.storage.checkpoint_serializer import (
    generate_resume_token,
    is_checkpoint_expired,
    verify_resume_token,
)
from backend.storage.checkpoint_types import (
    CheckpointExpiredError,
    CorruptedResumeTokenError,
    ExecutionCheckpoint,
)

logger = logging.getLogger("lienmark.storage.checkpoint_store_firestore")


def build_checkpoint_document_path(
    org_id: str, prod_id: str, run_id: str, checkpoint_id: str
) -> str:
    """Builds canonical Firestore document path for an execution checkpoint."""
    return (
        f"/organizations/{org_id.strip()}/productions/{prod_id.strip()}/"
        f"runs/{run_id.strip()}/checkpoints/{checkpoint_id.strip()}"
    )


def _bump_checkpoint_revision(
    checkpoint: ExecutionCheckpoint, prior_revision: int
) -> ExecutionCheckpoint:
    """Bumps checkpoint revision and computes fresh resume token."""
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


def _get_checkpoint_doc_ref(
    client: Any, tenant_id: str, prod_id: str, run_id: str, checkpoint_id: str
) -> Any:
    """Builds Firestore DocumentReference for a checkpoint."""
    return (
        client.collection("organizations")
        .document(tenant_id.strip())
        .collection("productions")
        .document(prod_id.strip())
        .collection("runs")
        .document(run_id.strip())
        .collection("checkpoints")
        .document(checkpoint_id.strip())
    )


def save_checkpoint_to_firestore(
    client: Any, checkpoint: ExecutionCheckpoint
) -> ExecutionCheckpoint:
    """
    Persists checkpoint to native Firestore under run subcollection.
    Enforces idempotency and revision bumping on state modification.
    """
    if client is None:
        raise ValueError("Firestore client instance is required.")

    doc_ref = _get_checkpoint_doc_ref(
        client, checkpoint.tenant_id, checkpoint.production_id,
        checkpoint.run_id, checkpoint.checkpoint_id
    )

    to_save = copy.deepcopy(checkpoint)
    existing_snap = doc_ref.get()
    if existing_snap.exists:
        existing_cp = ExecutionCheckpoint.model_validate(existing_snap.to_dict() or {})
        if existing_cp.state_hash == to_save.state_hash:
            return existing_cp
        to_save = _bump_checkpoint_revision(to_save, existing_cp.revision)

    if not verify_resume_token(to_save):
        raise CorruptedResumeTokenError("Resume token failed cryptographic verification.")

    doc_ref.set(to_save.model_dump(), merge=True)
    return to_save


def get_checkpoint_from_firestore(
    client: Any,
    org_id: str,
    prod_id: str,
    run_id: str,
    checkpoint_id: str,
    allow_expired: bool = False,
) -> Optional[ExecutionCheckpoint]:
    """Retrieves checkpoint from Firestore validating TTL and resume token."""
    if client is None:
        return None

    doc_ref = _get_checkpoint_doc_ref(client, org_id, prod_id, run_id, checkpoint_id)
    snap = doc_ref.get()
    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    cp = ExecutionCheckpoint.model_validate(data)

    if not allow_expired and is_checkpoint_expired(cp.expires_at_utc):
        raise CheckpointExpiredError(
            f"Checkpoint '{checkpoint_id}' expired at {cp.expires_at_utc}."
        )

    if not verify_resume_token(cp):
        raise CorruptedResumeTokenError(
            f"Checkpoint '{checkpoint_id}' resume token failed verification."
        )

    return cp


def list_checkpoints_from_firestore(
    client: Any,
    org_id: str,
    prod_id: str,
    run_id: str,
    include_expired: bool = False,
) -> List[ExecutionCheckpoint]:
    """Lists checkpoints for run under /checkpoints subcollection."""
    if client is None:
        return []

    coll_ref = (
        client.collection("organizations")
        .document(org_id.strip())
        .collection("productions")
        .document(prod_id.strip())
        .collection("runs")
        .document(run_id.strip())
        .collection("checkpoints")
    )

    results: List[ExecutionCheckpoint] = []
    for snap in coll_ref.stream():
        if not snap.exists:
            continue
        try:
            cp = ExecutionCheckpoint.model_validate(snap.to_dict())
            if include_expired or not is_checkpoint_expired(cp.expires_at_utc):
                results.append(cp)
        except Exception as err:
            logger.warning(f"Skipping malformed checkpoint doc {snap.id}: {err}")

    results.sort(key=lambda c: (c.revision, c.created_at_utc), reverse=True)
    return results


def delete_checkpoint_from_firestore(
    client: Any, org_id: str, prod_id: str, run_id: str, checkpoint_id: str
) -> bool:
    """Deletes checkpoint document from Firestore."""
    if client is None:
        return False

    doc_ref = (
        client.collection("organizations")
        .document(org_id.strip())
        .collection("productions")
        .document(prod_id.strip())
        .collection("runs")
        .document(run_id.strip())
        .collection("checkpoints")
        .document(checkpoint_id.strip())
    )
    doc_ref.delete()
    return True
