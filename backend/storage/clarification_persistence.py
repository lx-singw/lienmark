"""
backend/storage/clarification_persistence.py

File-locked atomic JSON persistence and Firestore sync for ClarificationRequests.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
import uuid
from typing import Dict, Iterator, Optional

from backend.domain.models import ClarificationRequest
from backend.storage.ledger import CryptographicLedger
from backend.storage.ledger_types import AuditEvent

logger = logging.getLogger("lienmark.storage.clarification_persistence")


def build_clarification_path(base_dir: str, tenant_id: str, production_id: str, run_id: str) -> str:
    """Computes durable path: output/clarifications/{tenant_id}/{production_id}/{run_id}.json."""
    return os.path.normpath(
        os.path.join(base_dir, tenant_id.strip(), production_id.strip(), f"{run_id.strip()}.json")
    )


@contextlib.contextmanager
def file_lock(lock_path: str, timeout: float = 10.0) -> Iterator[None]:
    """Process-safe mutual exclusion lock using atomic file creation."""
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    start = time.monotonic()
    fd: Optional[int] = None
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except (FileExistsError, OSError):
            if os.path.exists(lock_path) and (time.time() - os.path.getmtime(lock_path) > 30.0):
                with contextlib.suppress(OSError):
                    os.remove(lock_path)
            if time.monotonic() - start >= timeout:
                raise TimeoutError(f"Timed out waiting for file lock: '{lock_path}'")
            time.sleep(0.01)
    try:
        yield
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
            with contextlib.suppress(OSError):
                os.remove(lock_path)


def read_run_clarifications_file(file_path: str) -> Dict[str, ClarificationRequest]:
    """Reads all ClarificationRequests stored in a run file under lock."""
    if not os.path.exists(file_path):
        return {}
    with file_lock(f"{file_path}.lock"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return {k: ClarificationRequest.model_validate(v) for k, v in data.items()}
        except Exception as err:
            logger.warning(f"Error reading clarification file '{file_path}': {err}")
            return {}


def atomic_save_run_clarifications(file_path: str, records: Dict[str, ClarificationRequest]) -> None:
    """Atomically writes ClarificationRequests dict under file lock."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    payload = {k: v.model_dump() for k, v in records.items()}
    with file_lock(f"{file_path}.lock"):
        tmp_file = f"{file_path}.tmp.{uuid.uuid4().hex}"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            for attempt in range(5):
                try:
                    os.replace(tmp_file, file_path)
                    break
                except OSError:
                    if attempt == 4:
                        raise
                    time.sleep(0.02 * (2 ** attempt))
        finally:
            if os.path.exists(tmp_file):
                with contextlib.suppress(OSError):
                    os.remove(tmp_file)


def sync_clarification_to_firestore(client: Optional[object], clrf: ClarificationRequest) -> None:
    """Syncs clarification to Firestore hierarchy if client is configured."""
    if client is None or not clrf.tenant_id or not clrf.production_id:
        return
    try:
        t_id, p_id = clrf.tenant_id.strip(), clrf.production_id.strip()
        r_id, c_id = clrf.run_id.strip(), clrf.request_id.strip()
        col_fn = getattr(client, "collection", None)
        if callable(col_fn):
            col_fn("organizations").document(t_id).collection("productions").document(p_id).collection(
                "runs"
            ).document(r_id).collection("clarifications").document(c_id).set(clrf.model_dump())
    except Exception as exc:
        logger.warning(f"Firestore clarification sync failed: {exc}")


def discover_clarifications_on_disk(base_dir: str, tenant_id: Optional[str] = None) -> Dict[str, ClarificationRequest]:
    """Scans filesystem to discover persisted clarification records across runs."""
    root = os.path.join(base_dir, tenant_id) if tenant_id else base_dir
    found: Dict[str, ClarificationRequest] = {}
    if not os.path.isdir(root):
        return found
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".json") and not fname.endswith(".tmp.json"):
                fpath = os.path.join(dirpath, fname)
                for req_id, clrf in read_run_clarifications_file(fpath).items():
                    found[req_id] = clrf
    return found


def append_ledger_event_safe(
    ledger: CryptographicLedger,
    tenant_id: str,
    production_id: str,
    actor_id: str,
    action_type: str,
    payload: Dict[str, object],
) -> Optional[AuditEvent]:
    """Appends an event to the ledger, initializing genesis if chain is missing."""
    kwargs = {"tenant_id": tenant_id, "production_id": production_id, "actor_id": actor_id}
    try:
        return ledger.append_event(**kwargs, action_type=action_type, payload=payload)
    except Exception:
        try:
            ledger.initialize_production_ledger(**kwargs)
            return ledger.append_event(**kwargs, action_type=action_type, payload=payload)
        except Exception as retry_exc:
            logger.error(f"Failed to record audit event in ledger: {retry_exc}")
            return None


def apply_clarification_resolution(
    clrf: ClarificationRequest,
    actor_id: str,
    responder_role: str,
    response_text: Optional[str],
    doc_id: Optional[str],
    sel_opt: Optional[str],
    channel: Optional[str],
) -> Tuple[str, Dict[str, object]]:
    """Mutates clarification fields upon resolution and generates audit payload."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    clrf.status, clrf.resolved_at = "resolved", ts
    clrf.resolved_by, clrf.responder_role = actor_id, responder_role
    if response_text is not None:
        clrf.response_text = response_text
    if doc_id is not None:
        clrf.attached_document_ref = doc_id
    if sel_opt is not None:
        clrf.selected_option = sel_opt
    if channel is not None:
        clrf.resolution_channel = channel
    payload: Dict[str, object] = {
        "action": "CLARIFICATION_RESOLVED", "request_id": clrf.request_id,
        "claim_id": clrf.claim_id, "run_id": clrf.run_id, "resolved_at": ts,
    }
    return ts, payload

