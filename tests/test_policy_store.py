"""
tests/test_policy_store.py

Comprehensive test suite for versioned PolicyStore persistence layer.
Sprint 5.2 - PolicyStore Invariants, Idempotency, Concurrency & Ledger Enforcement.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import shutil
import tempfile
from unittest.mock import MagicMock
import pytest

from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store_types import (
    PolicyChangeDispatchIntent,
    PolicyConcurrencyError,
    PolicyStoreError,
    PolicyStoreMode,
    PolicyVersionRecord,
    compute_canonical_digest,
)
from backend.storage.policy_store_local import LocalPolicyStore
from backend.storage.policy_store import PolicyStore, get_policy_store


@pytest.fixture
def temp_dir():
    """Provides an isolated temporary directory for policy store tests."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def ledger():
    """Provides a clean in-memory CryptographicLedger instance."""
    return CryptographicLedger()


def test_compute_canonical_digest():
    """Deterministic canonical SHA-256 digest invariant."""
    payload_a = {"z": 1, "a": 2}
    payload_b = {"a": 2, "z": 1}
    digest_a = compute_canonical_digest(payload_a)
    digest_b = compute_canonical_digest(payload_b)
    assert digest_a == digest_b
    assert len(digest_a) == 64


def test_mandatory_ledger_enforcement_fail_closed(temp_dir):
    """Missing audit ledger strictly raises PolicyStoreError (fail-closed, no phantom IDs)."""
    store = LocalPolicyStore(base_dir=temp_dir, ledger=None)
    with pytest.raises(PolicyStoreError) as exc_info:
        store.save_policy_revision(
            org_id="org_test",
            config={"profile_type": "major_theatrical"},
            actor_id="admin_1",
        )
    assert "Mandatory audit ledger infrastructure is missing" in str(exc_info.value)


def test_save_and_get_policy_revisions(temp_dir, ledger):
    """Commits immutable revisions and updates active pointer monotonically."""
    store = LocalPolicyStore(base_dir=temp_dir, ledger=ledger)
    cfg1 = {"profile_type": "major_theatrical", "theatrical_perpetual": True}
    rec1, intent1 = store.save_policy_revision("org_a24", cfg1, "actor_1")

    assert rec1.version_id == "v1"
    assert rec1.org_id == "org_a24"
    assert rec1.ledger_event_id is not None
    assert intent1.from_version is None
    assert intent1.to_version == "v1"
    assert intent1.status == "PENDING"

    active = store.get_active_policy("org_a24")
    assert active is not None
    assert active.version_id == "v1"

    cfg2 = {"profile_type": "streamer_exclusive", "theatrical_perpetual": False}
    rec2, intent2 = store.save_policy_revision("org_a24", cfg2, "actor_2")
    assert rec2.version_id == "v2"
    assert intent2.from_version == "v1"
    assert intent2.to_version == "v2"
    assert "profile_type" in intent2.affected_rules

    v1_lookup = store.get_policy_revision("org_a24", "v1")
    assert v1_lookup is not None
    assert v1_lookup.policy_config["profile_type"] == "major_theatrical"


def test_idempotency_prevents_duplicate_commits(temp_dir, ledger):
    """Idempotency key prevents duplicate revisions and duplicate audit events."""
    store = LocalPolicyStore(base_dir=temp_dir, ledger=ledger)
    cfg = {"profile_type": "custom", "threshold": 0.8}
    rec1, intent1 = store.save_policy_revision("org_warner", cfg, "actor_1", idempotency_key="key_123")
    rec2, intent2 = store.save_policy_revision("org_warner", cfg, "actor_1", idempotency_key="key_123")

    assert rec1.version_id == rec2.version_id
    assert intent1.intent_id == intent2.intent_id
    events = ledger.get_events("policy_org_warner")
    assert len(events) == 2  # 1 genesis + 1 revision event


def test_revision_precondition_concurrency_error(temp_dir, ledger):
    """Expected version mismatch strictly raises PolicyConcurrencyError."""
    store = LocalPolicyStore(base_dir=temp_dir, ledger=ledger)
    cfg = {"profile": "standard"}
    store.save_policy_revision("org_paramount", cfg, "actor_1")

    with pytest.raises(PolicyConcurrencyError):
        store.save_policy_revision(
            "org_paramount", cfg, "actor_2", expected_current_version="v99"
        )

    # Correct precondition succeeds
    rec2, _ = store.save_policy_revision(
        "org_paramount", cfg, "actor_2", expected_current_version="v1"
    )
    assert rec2.version_id == "v2"


def test_production_override_and_ledger(temp_dir, ledger):
    """Saves scoped production override and commits tamper-evident audit event."""
    store = LocalPolicyStore(base_dir=temp_dir, ledger=ledger)
    override = {
        "admin_actor_id": "usr_legal",
        "rationale": "Fair use waiver approved by GC",
        "allow_trademark_fair_use": True,
    }
    ovr_id = store.save_production_override("org_universal", "prod_99", override)
    assert ovr_id is not None

    loaded = store.get_production_override("org_universal", "prod_99")
    assert loaded is not None
    assert loaded["override_id"] == ovr_id
    assert loaded["allow_trademark_fair_use"] is True
    assert loaded["ledger_event_id"] is not None


def test_dispatch_intents_lifecycle(temp_dir, ledger):
    """Listing and updating dispatch intents across lifecycle states."""
    store = LocalPolicyStore(base_dir=temp_dir, ledger=ledger)
    _, intent = store.save_policy_revision("org_mubi", {"k": "v"}, "actor_1")

    intents = store.list_dispatch_intents("org_mubi", status="PENDING")
    assert len(intents) == 1
    assert intents[0].intent_id == intent.intent_id

    store.update_dispatch_intent_status(intent.intent_id, "PROCESSING")
    processing = store.list_dispatch_intents("org_mubi", status="PROCESSING")
    assert len(processing) == 1

    store.update_dispatch_intent_status(intent.intent_id, "COMPLETED")
    completed = store.list_dispatch_intents("org_mubi", status="COMPLETED")
    assert len(completed) == 1


def test_policy_store_facade_zero_silent_fallback():
    """PolicyStore with mode=FIRESTORE strictly raises PolicyStoreError on missing client."""
    with pytest.raises(PolicyStoreError) as exc_info:
        PolicyStore(
            mode=PolicyStoreMode.FIRESTORE,
            firestore_client=None,
        )
    assert "Silent fallback to local disk is strictly prohibited" in str(exc_info.value)


def test_policy_store_facade_local_disk_success(temp_dir, ledger):
    """PolicyStore unified facade delegates properly to LocalPolicyStore."""
    store = PolicyStore(
        mode=PolicyStoreMode.LOCAL_DISK,
        base_dir=temp_dir,
        ledger=ledger,
    )
    rec, intent = store.save_policy_revision("org_facade", {"rule": "strict"}, "actor_lead")
    assert rec.version_id == "v1"
    assert store.get_active_policy("org_facade").version_id == "v1"
