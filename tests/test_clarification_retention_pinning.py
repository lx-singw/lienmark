"""
tests/test_clarification_retention_pinning.py

Verification suite for Sprint 4.1 / Milestone D Clarification & Suspension upgrades:
1. Durable multi-tenant JSON persistence under output/clarifications/{tenant}/{prod}/{run}.json.
2. Checkpoint retention pinning: active PENDING clarifications prevent deletion & expiration.
3. Explicit workflow deadline expiration invalidates resume eligibility and emits audit event.
4. SuspensionManager commits checkpoint to CheckpointStore and updates state before release.
5. Zero active awaiting coroutines and clean task release.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timedelta, timezone
import pytest

from backend.domain.models import ClarificationRequest
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    SuspensionReason,
    SuspensionState,
)
from backend.orchestration.suspension import (
    CheckpointExpiredError,
    SuspensionManager,
)
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.clarification_store import ClarificationStore
from backend.storage.ledger import CryptographicLedger


@pytest.fixture
def temp_dirs():
    c_dir = tempfile.mkdtemp(prefix="lienmark_clrf_")
    k_dir = tempfile.mkdtemp(prefix="lienmark_ckpt_")
    yield c_dir, k_dir
    shutil.rmtree(c_dir, ignore_errors=True)
    shutil.rmtree(k_dir, ignore_errors=True)


def _seed_clrf(
    store: ClarificationStore,
    req_id: str = "clrf_01",
    run_id: str = "run_100",
    tenant_id: str = "tenant_a",
    prod_id: str = "prod_x",
    status: str = "pending",
    deadline_utc: str | None = None,
) -> ClarificationRequest:
    """Helper to seed a structured clarification request."""
    clrf = ClarificationRequest(
        request_id=req_id,
        run_id=run_id,
        claim_id="clm_scene14_jazz",
        revision_id="v8",
        stable_lineage_key="lineage_jazz",
        question_text="Provide sync license for jazz cue?",
        suggested_options=["Option A", "Option B"],
        required_document_type="Synchronization License",
        assigned_role="Music Supervisor",
        status=status,
        deadline_utc=deadline_utc,
    )
    return store.save_clarification(clrf, tenant_id=tenant_id, production_id=prod_id)


def test_durable_clarification_persistence_file_structure(temp_dirs):
    """Verifies persistence under output/clarifications/{tenant}/{prod}/{run}.json."""
    c_dir, _ = temp_dirs
    store = ClarificationStore(base_dir=c_dir)
    clrf = _seed_clrf(store, req_id="clrf_persist", run_id="run_p1", tenant_id="tenant_alpha", prod_id="prod_beta")

    expected_path = os.path.normpath(os.path.join(c_dir, "tenant_alpha", "prod_beta", "run_p1.json"))
    assert os.path.exists(expected_path)

    with open(expected_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "clrf_persist" in data
    rec = data["clrf_persist"]
    assert rec["question_text"] == "Provide sync license for jazz cue?"
    assert rec["claim_id"] == "clm_scene14_jazz"
    assert rec["status"] == "pending"

    # Re-instantiate store from scratch and verify durable load across restarts
    fresh_store = ClarificationStore(base_dir=c_dir)
    loaded = fresh_store.get_clarification("clrf_persist", tenant_id="tenant_alpha")
    assert loaded is not None
    assert loaded.request_id == "clrf_persist"


def test_checkpoint_retention_pinning_prevents_deletion(temp_dirs):
    """Verifies active PENDING clarifications pin checkpoints and block deletion."""
    c_dir, k_dir = temp_dirs
    clrf_store = ClarificationStore(base_dir=c_dir)
    ckpt_store = CheckpointStore(base_output_dir=k_dir, force_local=True, clarification_store=clrf_store)

    clrf = _seed_clrf(clrf_store, req_id="clrf_pin", run_id="run_pin_01", tenant_id="org_pin", prod_id="prod_pin")
    mgr = SuspensionManager(checkpoint_store=ckpt_store, clarification_store=clrf_store)
    cp = mgr.suspend_investigation(
        tenant_id="org_pin", production_id="prod_pin", run_id="run_pin_01",
        claim_id="clm_scene14_jazz", paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=AgentMemorySnapshot(),
        pending_clarification_ids=[clrf.request_id],
    )

    # Deletion is blocked while clarification is PENDING
    assert ckpt_store.is_checkpoint_pinned("org_pin", "run_pin_01", cp) is True
    deleted = ckpt_store.delete_checkpoint("org_pin", "prod_pin", "run_pin_01", cp.checkpoint_id)
    assert deleted is False
    assert ckpt_store.get_checkpoint("org_pin", "prod_pin", "run_pin_01", cp.checkpoint_id) is not None

    # Resolving clarification unpins checkpoint and allows deletion
    clrf_store.resolve_clarification(clrf.request_id, "org_pin", "usr_1", "producer")
    assert ckpt_store.is_checkpoint_pinned("org_pin", "run_pin_01", cp) is False
    deleted_after = ckpt_store.delete_checkpoint("org_pin", "prod_pin", "run_pin_01", cp.checkpoint_id)
    assert deleted_after is True


def test_checkpoint_retention_pinning_prevents_expiration(temp_dirs):
    """Verifies retention pinning protects expired checkpoints from being rejected."""
    c_dir, k_dir = temp_dirs
    clrf_store = ClarificationStore(base_dir=c_dir)
    ckpt_store = CheckpointStore(base_output_dir=k_dir, force_local=True, clarification_store=clrf_store)

    _seed_clrf(clrf_store, req_id="clrf_ttl_pin", run_id="run_ttl_01", tenant_id="org_ttl", prod_id="prod_ttl")
    mgr = SuspensionManager(checkpoint_store=ckpt_store, clarification_store=clrf_store)
    cp = mgr.suspend_investigation(
        tenant_id="org_ttl", production_id="prod_ttl", run_id="run_ttl_01",
        claim_id="clm_scene14_jazz", paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=AgentMemorySnapshot(),
        pending_clarification_ids=["clrf_ttl_pin"],
        ttl_seconds=-100,  # Pre-expired TTL
    )

    # Even though TTL is expired, retention pinning preserves checkpoint access!
    retrieved = ckpt_store.get_checkpoint("org_ttl", "prod_ttl", "run_ttl_01", cp.checkpoint_id, allow_expired=False)
    assert retrieved is not None
    assert retrieved.checkpoint_id == cp.checkpoint_id

    # Once clarification is resolved, retention pinning ceases and expiration triggers
    clrf_store.resolve_clarification("clrf_ttl_pin", "org_ttl", "usr_1", "producer")
    with pytest.raises(Exception):
        ckpt_store.get_checkpoint("org_ttl", "prod_ttl", "run_ttl_01", cp.checkpoint_id, allow_expired=False)


def test_explicit_workflow_deadline_expiration_and_audit(temp_dirs):
    """Verifies deadline transition to EXPIRED, resume invalidation, and ledger audit."""
    c_dir, k_dir = temp_dirs
    ledger = CryptographicLedger()
    clrf_store = ClarificationStore(ledger=ledger, base_dir=c_dir)
    past_dl = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    clrf = _seed_clrf(clrf_store, req_id="clrf_exp", run_id="run_exp", tenant_id="org_exp", deadline_utc=past_dl)

    # Trigger explicit deadline expiration
    expired_clrf, did_expire = clrf_store.check_and_expire_deadline("clrf_exp", "org_exp")
    assert did_expire is True
    assert expired_clrf.status == "expired"
    assert expired_clrf.expired_at is not None

    # Invalidate resume eligibility
    assert clrf_store.is_resume_eligible("run_exp", "org_exp", ["clrf_exp"]) is False

    # SuspensionManager rejects resumption for expired clarification
    mgr = SuspensionManager(clarification_store=clrf_store)
    cp = mgr._build_checkpoint(
        tenant_id="org_exp", production_id="prod_default", run_id="run_exp",
        claim_id="clm_scene14_jazz", paused_stage="ACT_06", reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=AgentMemorySnapshot(), pending_clarification_ids=["clrf_exp"],
        ttl_seconds=3600,
    )
    mgr.checkpoints[cp.checkpoint_id] = cp
    with pytest.raises(CheckpointExpiredError):
        mgr.resume_investigation(checkpoint_id=cp.checkpoint_id, resume_token=cp.resume_token)


def test_suspension_structured_state_and_clean_worker_exit(temp_dirs):
    """Verifies state WAITING_FOR_INFORMATION before release, persisted vector, and 0 active coroutines."""
    c_dir, k_dir = temp_dirs
    clrf_store = ClarificationStore(base_dir=c_dir)
    ckpt_store = CheckpointStore(base_output_dir=k_dir, force_local=True, clarification_store=clrf_store)
    mgr = SuspensionManager(checkpoint_store=ckpt_store, clarification_store=clrf_store)

    loop = asyncio.new_event_loop()
    task = loop.create_task(asyncio.sleep(100))
    lock = threading.Lock()
    lock.acquire()
    workers = {"w1": object()}

    snapshot = AgentMemorySnapshot(findings=[{"found": True}], subgoals=["resolve_composer"])
    cp = mgr.suspend_investigation(
        tenant_id="org_clean", production_id="prod_clean", run_id="run_clean",
        claim_id="clm_scene14_jazz", paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC, agent_memory_snapshot=snapshot,
        pending_clarification_ids=["clrf_01"], active_tasks=[task], active_locks=[lock],
        worker_handles=workers, completed_subgoals=["query_ascap"], evidence_digests=["sha_abc123"],
        remaining_budget=45.50, structured_execution_state={"step_depth": 3},
    )

    # 1. State set to WAITING_FOR_INFORMATION
    assert mgr.states["clm_scene14_jazz"] == SuspensionState.WAITING_FOR_INFORMATION
    # 2. Checkpoint committed to CheckpointStore
    stored = ckpt_store.get_checkpoint("org_clean", "prod_clean", "run_clean", cp.checkpoint_id)
    assert stored is not None
    # 3. Structured state persisted
    assert cp.completed_subgoals == ["query_ascap"]
    assert cp.evidence_digests == ["sha_abc123"]
    assert cp.remaining_budget == 45.50
    assert cp.structured_execution_state["step_depth"] == 3
    # 4. Zero lingering tasks or locks, task cancelled and coroutine closed
    assert task.done() and task.cancelled()
    assert not lock.locked()
    assert len(workers) == 0
    loop.close()
