"""
tests/test_checkpoint_store.py

Core test suite for Checkpoint Storage & Persistence layer.
Sprint 4.1: Human-in-the-Loop Clarification State Machine & Checkpoints.
"""

import os
import shutil
import tempfile
import pytest

from backend.storage.checkpoint_serializer import verify_resume_token
from backend.storage.checkpoint_store import get_checkpoint_store
from backend.storage.checkpoint_store_firestore import build_checkpoint_document_path
from backend.storage.checkpoint_store_local import LocalCheckpointStore
from backend.storage.checkpoint_types import CorruptedResumeTokenError


@pytest.fixture
def temp_checkpoint_dir():
    temp_dir = tempfile.mkdtemp(prefix="lienmark_test_checkpoints_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_checkpoint_store(temp_checkpoint_dir):
    return get_checkpoint_store(base_output_dir=temp_checkpoint_dir, force_local=True)


def test_firestore_collection_hierarchy_path():
    """Validates exact Firestore hierarchy."""
    path = build_checkpoint_document_path(
        org_id="org_paramount",
        prod_id="prod_godfather",
        run_id="run_101",
        checkpoint_id="ckpt_999",
    )
    assert path == "/organizations/org_paramount/productions/prod_godfather/runs/run_101/checkpoints/ckpt_999"


def test_local_filesystem_pathing(temp_checkpoint_dir):
    """Validates local filesystem fallback path format: output/checkpoints/{tenant_id}/{run_id}/{checkpoint_id}.json."""
    store = LocalCheckpointStore(base_dir=temp_checkpoint_dir)
    resolved = store._resolve_file_path("org_universal", "run_202", "ckpt_abc")
    expected = os.path.normpath(os.path.join(temp_checkpoint_dir, "org_universal", "run_202", "ckpt_abc.json"))
    assert resolved == expected


def test_checkpoint_creation_and_schema(sample_checkpoint_store):
    """Validates ExecutionCheckpoint schema contains all required fields."""
    agent_state = {
        "active_role": "adk_orchestrator",
        "current_step": "clarification_pause",
        "pending_clarification_ids": ["clr_001"],
        "active_claim_ids": ["clm_jazz_solo"],
        "completed_step_count": 3,
        "context_variables": {"ambiguity_score": 0.88},
    }
    dag_data = {
        "plan_id": "dag_plan_1",
        "claim_id": "clm_jazz_solo",
        "root_query": "uncredited jazz solo 1958",
        "nodes": [{"node_id": "n1", "query_string": "jazz solo master rights"}],
    }
    subgoals = [{"subgoal_id": "sg_1", "description": "Identify master recording owner"}]

    cp = sample_checkpoint_store.create_checkpoint(
        tenant_id="org_warner",
        production_id="prod_noir",
        run_id="run_303",
        checkpoint_id="ckpt_noir_01",
        agent_state=agent_state,
        investigation_dag=dag_data,
        uncompleted_subgoals=subgoals,
        ttl_days=30,
        trigger_reason="suspension_for_clarification",
    )

    _assert_checkpoint_schema_fields(cp)


def _assert_checkpoint_schema_fields(cp):
    """Helper verifying field presence and cryptographic tokens on ExecutionCheckpoint."""
    assert cp.checkpoint_id == "ckpt_noir_01"
    assert cp.tenant_id == "org_warner"
    assert cp.org_id == "org_warner"
    assert cp.production_id == "prod_noir"
    assert cp.run_id == "run_303"
    assert cp.revision == 1
    assert cp.agent_state.active_role == "adk_orchestrator"
    assert cp.agent_state.pending_clarification_ids == ["clr_001"]
    assert cp.investigation_dag["plan_id"] == "dag_plan_1"
    assert len(cp.uncompleted_subgoals) == 1
    assert len(cp.state_hash) == 64
    assert len(cp.resume_token) == 64
    assert verify_resume_token(cp) is True


def test_idempotency_same_state_preserves_revision(sample_checkpoint_store):
    """Validates re-saving identical state yields identical hash and preserves revision."""
    cp = sample_checkpoint_store.create_checkpoint(
        tenant_id="org_sony",
        production_id="prod_spider",
        run_id="run_404",
        checkpoint_id="ckpt_idempotent",
        agent_state={"active_role": "researcher", "current_step": "step_1"},
    )
    saved_1 = sample_checkpoint_store.save_checkpoint(cp)
    assert saved_1.revision == 1
    initial_hash = saved_1.state_hash
    initial_token = saved_1.resume_token

    saved_2 = sample_checkpoint_store.save_checkpoint(saved_1)
    assert saved_2.revision == 1
    assert saved_2.state_hash == initial_hash
    assert saved_2.resume_token == initial_token


def test_corrupted_resume_token_rejection(sample_checkpoint_store):
    """Validates corrupted resume token causes CorruptedResumeTokenError."""
    cp = sample_checkpoint_store.create_checkpoint(
        tenant_id="org_mubi",
        production_id="prod_arthouse",
        run_id="run_707",
        checkpoint_id="ckpt_tamper",
        agent_state={"active_role": "auditor", "current_step": "checking"},
    )
    tampered = cp.model_copy(update={"resume_token": "f" * 64})
    with pytest.raises(CorruptedResumeTokenError):
        sample_checkpoint_store.save_checkpoint(tampered)
