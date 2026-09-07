"""
tests/test_suspension_checkpoints.py

Verification test suite for suspension checkpoints:
1. Checkpoint serialization and deserialization roundtrip.
2. Cryptographic SHA-256 resume token integrity and tamper detection.
3. TTL calculation, lifecycle evaluation, and expiration rejection.
4. Offline fallback local store persistence without network/cloud dependencies.
5. Strict cross-tenant isolation enforcement on checkpoint retrieval.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
import pytest

from backend.storage.checkpoint_serializer import (
    calculate_expiration_timestamp,
    canonical_json_dumps,
    compute_checkpoint_state_hash,
    generate_resume_token,
    is_checkpoint_expired,
    verify_resume_token,
)
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_store_local import LocalCheckpointStore
from backend.storage.checkpoint_types import (
    AgentStateVector,
    CheckpointExpiredError,
    CorruptedResumeTokenError,
    CrossTenantCheckpointViolation,
    ExecutionCheckpoint,
)
from backend.orchestration.checkpoint_types import (
    AgentMemorySnapshot,
    ExecutionCheckpoint as OrchCheckpoint,
    SuspensionReason,
    compute_resume_token,
    validate_resume_token,
)
from backend.orchestration.suspension import (
    CheckpointExpiredError as OrchCheckpointExpiredError,
    SuspensionManager,
)


def _build_test_agent_state() -> AgentStateVector:
    """Builds sample AgentStateVector for checkpoint testing."""
    return AgentStateVector(
        active_role="clearance_specialist",
        current_step="ACT_06_REQUEST_INFORMATION",
        pending_clarification_ids=["clrf_scene14_jazz"],
        active_claim_ids=["clm_scene14_jazz_solo"],
        completed_step_count=3,
        context_variables={"cue": "jazz_solo", "scene": "14"},
        memory_snapshot={"search_hits": 0, "registry": "USCO"},
    )


def test_checkpoint_serialization_and_deserialization():
    """Verifies lossless serialization and deserialization of ExecutionCheckpoint."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = CheckpointStore(base_output_dir=tmp_dir, force_local=True)
        state_vec = _build_test_agent_state()

        original = store.create_checkpoint(
            tenant_id="org_paramount_01",
            production_id="prod_diner_noir",
            run_id="run_v8_001",
            agent_state=state_vec,
            ttl_days=30,
            trigger_reason="suspension_for_clarification",
        )

        serialized_dict = original.model_dump()
        json_str = canonical_json_dumps(serialized_dict)
        restored = ExecutionCheckpoint.model_validate_json(json_str)

        assert restored.checkpoint_id == original.checkpoint_id
        assert restored.tenant_id == "org_paramount_01"
        assert restored.state_hash == original.state_hash
        assert restored.resume_token == original.resume_token
        assert restored.agent_state.active_role == "clearance_specialist"
        assert restored.agent_state.completed_step_count == 3


def test_resume_token_integrity_and_tamper_detection():
    """Verifies cryptographic SHA-256 token verification rejects tampered state."""
    state_vec = _build_test_agent_state()
    state_hash = compute_checkpoint_state_hash(state_vec, {}, [])
    token = generate_resume_token(
        tenant_id="org_paramount_01",
        production_id="prod_diner_noir",
        run_id="run_v8_001",
        checkpoint_id="chk_test_01",
        revision=1,
        state_hash=state_hash,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        store = CheckpointStore(base_output_dir=tmp_dir, force_local=True)
        cp = store.create_checkpoint(
            tenant_id="org_paramount_01",
            production_id="prod_diner_noir",
            run_id="run_v8_001",
            agent_state=state_vec,
            checkpoint_id="chk_test_01",
        )

        # Valid checkpoint resume token verification succeeds
        assert verify_resume_token(cp) is True

        # Tampered resume token fails verification
        tampered_cp = cp.model_copy(update={"resume_token": "0" * 64})
        assert verify_resume_token(tampered_cp) is False

        # Tampered state hash fails verification
        tampered_hash_cp = cp.model_copy(update={"state_hash": "a" * 64})
        assert verify_resume_token(tampered_hash_cp) is False


def test_ttl_calculation_and_expiration_lifecycle():
    """Verifies TTL calculation and ensures expired checkpoints reject resumption."""
    now = datetime.now(timezone.utc)
    future_ttl = calculate_expiration_timestamp(ttl_days=30, base_time=now)
    past_ttl = (now - timedelta(days=1)).isoformat()

    assert is_checkpoint_expired(future_ttl) is False
    assert is_checkpoint_expired(past_ttl) is True

    # SuspensionManager rejects expired checkpoints on resume
    suspension_mgr = SuspensionManager()
    expired_cp = suspension_mgr.suspend_investigation(
        tenant_id="org_paramount_01",
        production_id="prod_diner_noir",
        run_id="run_v8_001",
        claim_id="clm_scene14_jazz_solo",
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=AgentMemorySnapshot(),
        pending_clarification_ids=["clrf_01"],
        ttl_seconds=-10,  # Pre-expired
    )

    with pytest.raises(OrchCheckpointExpiredError):
        suspension_mgr.resume_investigation(
            checkpoint_id=expired_cp.checkpoint_id,
            resume_token=expired_cp.resume_token,
        )


def test_offline_fallback_local_checkpoint_store():
    """Verifies local filesystem storage operates cleanly in air-gapped/offline mode."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        local_store = LocalCheckpointStore(base_dir=tmp_dir)
        store = CheckpointStore(base_output_dir=tmp_dir, force_local=True)
        state_vec = _build_test_agent_state()

        cp = store.create_checkpoint(
            tenant_id="org_offline_studio",
            production_id="prod_offline_01",
            run_id="run_offline_100",
            agent_state=state_vec,
            ttl_days=14,
        )

        # Save to local disk
        saved = local_store.save_checkpoint(cp)
        assert saved.revision == 1

        # Retrieve from local store
        loaded = local_store.get_checkpoint(
            tenant_id="org_offline_studio",
            production_id="prod_offline_01",
            run_id="run_offline_100",
            checkpoint_id=cp.checkpoint_id,
        )
        assert loaded is not None
        assert loaded.checkpoint_id == cp.checkpoint_id

        # Idempotency check: saving identical checkpoint preserves revision
        resaved = local_store.save_checkpoint(cp)
        assert resaved.revision == 1


def test_cross_tenant_isolation_enforcement():
    """Verifies checkpoints cannot be accessed by unauthorized cross-tenant callers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        local_store = LocalCheckpointStore(base_dir=tmp_dir)
        store = CheckpointStore(base_output_dir=tmp_dir, force_local=True)
        state_vec = _build_test_agent_state()

        cp = store.create_checkpoint(
            tenant_id="org_tenant_alpha",
            production_id="prod_alpha_01",
            run_id="run_alpha_001",
            agent_state=state_vec,
        )
        local_store.save_checkpoint(cp)

        # Cross-tenant query with tenant_beta returns None or raises violation
        cross_tenant_result = local_store.get_checkpoint(
            tenant_id="org_tenant_beta",
            production_id="prod_alpha_01",
            run_id="run_alpha_001",
            checkpoint_id=cp.checkpoint_id,
        )
        assert cross_tenant_result is None
