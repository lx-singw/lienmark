"""
tests/test_checkpoint_lifecycle.py

Tests for checkpoint mutation, TTL lifecycle expiration, and listing/deletion.
Sprint 4.1: Human-in-the-Loop Clarification State Machine & Checkpoints.
"""

from datetime import datetime, timedelta, timezone
import shutil
import tempfile
import pytest

from backend.storage.checkpoint_serializer import (
    calculate_expiration_timestamp,
    compute_checkpoint_state_hash,
    generate_resume_token,
    is_checkpoint_expired,
    verify_resume_token,
)
from backend.storage.checkpoint_store import get_checkpoint_store
from backend.storage.checkpoint_types import (
    AgentStateVector,
    CheckpointExpiredError,
)


@pytest.fixture
def temp_checkpoint_dir():
    temp_dir = tempfile.mkdtemp(prefix="lienmark_test_lifecycle_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_checkpoint_store(temp_checkpoint_dir):
    return get_checkpoint_store(base_output_dir=temp_checkpoint_dir, force_local=True)


def _build_mutated_checkpoint(saved_cp):
    """Helper to construct a mutated checkpoint with recomputed hash and token."""
    mutated_state = AgentStateVector(
        active_role="adk_orchestrator",
        current_step="step_2_resumed",
        completed_step_count=2,
    )
    new_state_hash = compute_checkpoint_state_hash(
        agent_state=mutated_state,
        investigation_dag=saved_cp.investigation_dag,
        uncompleted_subgoals=saved_cp.uncompleted_subgoals,
    )
    new_token = generate_resume_token(
        tenant_id=saved_cp.tenant_id,
        production_id=saved_cp.production_id,
        run_id=saved_cp.run_id,
        checkpoint_id=saved_cp.checkpoint_id,
        revision=saved_cp.revision,
        state_hash=new_state_hash,
    )
    return saved_cp.model_copy(
        update={
            "agent_state": mutated_state,
            "state_hash": new_state_hash,
            "resume_token": new_token,
        }
    ), new_state_hash


def test_state_mutation_bumps_revision(sample_checkpoint_store):
    """Validates mutating state increments revision and recalculates token."""
    cp = sample_checkpoint_store.create_checkpoint(
        tenant_id="org_disney",
        production_id="prod_tron",
        run_id="run_505",
        checkpoint_id="ckpt_mutable",
        agent_state={"active_role": "adk_orchestrator", "current_step": "step_1"},
    )
    saved_1 = sample_checkpoint_store.save_checkpoint(cp)
    assert saved_1.revision == 1

    mutated_cp, new_hash = _build_mutated_checkpoint(saved_1)
    saved_2 = sample_checkpoint_store.save_checkpoint(mutated_cp)

    assert saved_2.revision == 2
    assert saved_2.state_hash == new_hash
    assert saved_2.resume_token != saved_1.resume_token
    assert verify_resume_token(saved_2) is True


def test_ttl_expiration_calculation():
    """Validates 30-day default TTL calculation and time evaluation."""
    now = datetime.now(timezone.utc)
    exp_iso = calculate_expiration_timestamp(ttl_days=30, base_time=now)
    exp_dt = datetime.fromisoformat(exp_iso)
    assert (exp_dt - now).days == 30
    assert is_checkpoint_expired(exp_iso, current_time=now) is False

    past_iso = (now - timedelta(days=1)).isoformat()
    assert is_checkpoint_expired(past_iso, current_time=now) is True


def test_ttl_expired_checkpoint_retrieval(sample_checkpoint_store):
    """Validates get_checkpoint raises CheckpointExpiredError on expired record."""
    past_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    expired_cp = sample_checkpoint_store.create_checkpoint(
        tenant_id="org_a24",
        production_id="prod_everything",
        run_id="run_606",
        checkpoint_id="ckpt_expired_test",
        agent_state={"active_role": "intake", "current_step": "expired"},
        ttl_days=1,
    )
    sample_checkpoint_store.save_checkpoint(
        expired_cp.model_copy(update={"expires_at_utc": past_iso})
    )

    with pytest.raises(CheckpointExpiredError):
        sample_checkpoint_store.get_checkpoint(
            tenant_id="org_a24",
            production_id="prod_everything",
            run_id="run_606",
            checkpoint_id="ckpt_expired_test",
            allow_expired=False,
        )

    allowed = sample_checkpoint_store.get_checkpoint(
        tenant_id="org_a24",
        production_id="prod_everything",
        run_id="run_606",
        checkpoint_id="ckpt_expired_test",
        allow_expired=True,
    )
    assert allowed is not None
    assert allowed.checkpoint_id == "ckpt_expired_test"


def test_list_and_delete_checkpoints(sample_checkpoint_store):
    """Validates listing checkpoints sorted by revision and deleting checkpoints."""
    for i in range(3):
        cp = sample_checkpoint_store.create_checkpoint(
            tenant_id="org_mgm",
            production_id="prod_bond",
            run_id="run_808",
            checkpoint_id=f"ckpt_seq_{i}",
            agent_state={"active_role": "agent", "current_step": f"step_{i}"},
        )
        sample_checkpoint_store.save_checkpoint(cp)

    listed = sample_checkpoint_store.list_checkpoints("org_mgm", "prod_bond", "run_808")
    assert len(listed) == 3
    latest = sample_checkpoint_store.get_latest_checkpoint("org_mgm", "prod_bond", "run_808")
    assert latest is not None

    deleted = sample_checkpoint_store.delete_checkpoint("org_mgm", "prod_bond", "run_808", "ckpt_seq_1")
    assert deleted is True

    remaining = sample_checkpoint_store.list_checkpoints("org_mgm", "prod_bond", "run_808")
    assert len(remaining) == 2
    assert not any(c.checkpoint_id == "ckpt_seq_1" for c in remaining)
