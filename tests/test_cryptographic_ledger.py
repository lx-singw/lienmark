"""tests/test_cryptographic_ledger.py: Comprehensive tests for CryptographicLedger."""
from __future__ import annotations

import concurrent.futures
import time
from unittest.mock import MagicMock
import pytest

from backend.storage.ledger import (
    AuditEvent,
    CryptographicLedger,
    LedgerTamperError,
    LedgerIntegrityError,
    compute_canonical_digest,
)


@pytest.fixture
def ledger() -> CryptographicLedger:
    return CryptographicLedger()


def test_genesis_initialization(ledger: CryptographicLedger) -> None:
    genesis = ledger.initialize_production_ledger(
        tenant_id="org_marvel",
        production_id="prod_deadpool3",
        actor_id="usr_clearance_lead",
    )
    assert genesis.sequence_number == 1
    assert genesis.action_type == "GENESIS"
    assert genesis.previous_event_hash == "0" * 64
    assert len(genesis.entry_hash) == 64
    assert len(genesis.payload_digest) == 64

    # Duplicate initialization must fail
    with pytest.raises(LedgerIntegrityError, match="already initialized"):
        ledger.initialize_production_ledger("org_marvel", "prod_deadpool3", "usr_other")


def test_append_event_chaining(ledger: CryptographicLedger) -> None:
    # Appending to uninitialized ledger raises LedgerIntegrityError
    with pytest.raises(LedgerIntegrityError, match="not initialized"):
        ledger.append_event("org_marvel", "prod_x", "usr_1", "CLAIM_CREATED", {"claim": 1})

    genesis = ledger.initialize_production_ledger("org_marvel", "prod_x", "usr_1")
    evt1 = ledger.append_event(
        tenant_id="org_marvel",
        production_id="prod_x",
        actor_id="usr_1",
        action_type="CLAIM_CREATED",
        payload={"scene": "Ext. Warehouse", "item": "Vintage Poster", "flag": "visual_ip"},
    )
    assert evt1.sequence_number == 2
    assert evt1.previous_event_hash == genesis.entry_hash

    evt2 = ledger.append_event(
        tenant_id="org_marvel",
        production_id="prod_x",
        actor_id="usr_attorney",
        action_type="ATTORNEY_APPROVAL",
        payload={"status": "CLEARED", "license_fee_usd": 2500.0},
    )
    assert evt2.sequence_number == 3
    assert evt2.previous_event_hash == evt1.entry_hash


def test_canonical_payload_digest(ledger: CryptographicLedger) -> None:
    p1 = {"b": 2, "a": 1, "nested": {"z": 26, "y": 25}}
    p2 = {"a": 1, "nested": {"y": 25, "z": 26}, "b": 2}
    assert compute_canonical_digest(p1) == compute_canonical_digest(p2)


def test_record_supersession_immutability(ledger: CryptographicLedger) -> None:
    ledger.initialize_production_ledger("org_warner", "prod_batman", "usr_1")
    initial_event = ledger.append_event(
        "org_warner", "prod_batman", "usr_1", "SCORE_ASSIGNED", {"score": "HIGH_RISK"}
    )
    initial_hash = initial_event.entry_hash

    # Superseding non-existent event fails
    with pytest.raises(LedgerIntegrityError, match="not found"):
        ledger.record_supersession("org_warner", "prod_batman", "usr_2", "evt_nonexistent", {})

    superseding = ledger.record_supersession(
        tenant_id="org_warner",
        production_id="prod_batman",
        actor_id="usr_counsel",
        superseded_event_id=initial_event.event_id,
        superseding_payload={"score": "CLEARED", "override_reason": "Fair use confirmed"},
    )
    assert superseding.action_type == "SUPERSEDED"
    assert superseding.payload["superseded_event_id"] == initial_event.event_id
    assert superseding.sequence_number == 3

    # Confirm original event remains unchanged
    events = ledger.get_events("prod_batman")
    assert events[1].entry_hash == initial_hash
    assert events[1].payload["score"] == "HIGH_RISK"


def test_tamper_prevention_on_models_and_ledger(ledger: CryptographicLedger) -> None:
    event = ledger.initialize_production_ledger("org_disney", "prod_lion", "usr_1")

    # Modifying model attribute
    with pytest.raises(LedgerTamperError):
        event.actor_id = "usr_attacker"

    # Deleting model attribute
    with pytest.raises(LedgerTamperError):
        del event.actor_id

    # Mutating payload dictionary
    with pytest.raises(LedgerTamperError):
        event.payload["tamper"] = "payload_injected"

    # Ledger level update / delete methods
    with pytest.raises(LedgerTamperError):
        ledger.update_event()

    with pytest.raises(LedgerTamperError):
        ledger.delete_event()

    with pytest.raises(LedgerTamperError):
        ledger["prod_lion"] = []

    with pytest.raises(LedgerTamperError):
        del ledger["prod_lion"]


def test_verify_chain_and_tamper_detection(ledger: CryptographicLedger) -> None:
    valid, _, count = ledger.verify_chain("prod_nonexistent")
    assert not valid
    assert count == 0

    ledger.initialize_production_ledger("org_sony", "prod_spiderman", "usr_1")
    for i in range(5):
        ledger.append_event("org_sony", "prod_spiderman", "usr_1", "CLAIM_CREATED", {"i": i})

    valid, reason, count = ledger.verify_chain("prod_spiderman")
    assert valid is True
    assert reason is None
    assert count == 6

    # Test tampering with sequence number
    chain = ledger._chains["prod_spiderman"]
    tampered_seq = AuditEvent(
        event_id=chain[3].event_id,
        tenant_id=chain[3].tenant_id,
        production_id=chain[3].production_id,
        actor_id=chain[3].actor_id,
        action_type=chain[3].action_type,
        payload=chain[3].payload,
        payload_digest=chain[3].payload_digest,
        sequence_number=999,
        timestamp_utc=chain[3].timestamp_utc,
        previous_event_hash=chain[3].previous_event_hash,
        entry_hash=chain[3].entry_hash,
    )
    chain[3] = tampered_seq
    valid, reason, fail_idx = ledger.verify_chain("prod_spiderman")
    assert valid is False
    assert "Non-monotonic" in str(reason)
    assert fail_idx == 3


def test_get_events_pagination(ledger: CryptographicLedger) -> None:
    ledger.initialize_production_ledger("org_paramount", "prod_gladiator", "usr_1")
    for i in range(10):
        ledger.append_event("org_paramount", "prod_gladiator", "usr_1", "FINDING_ATTACHED", {"step": i})

    page1 = ledger.get_events("prod_gladiator", start_seq=1, limit=5)
    assert len(page1) == 5
    assert [e.sequence_number for e in page1] == [1, 2, 3, 4, 5]

    page2 = ledger.get_events("prod_gladiator", start_seq=6, limit=5)
    assert len(page2) == 5
    assert [e.sequence_number for e in page2] == [6, 7, 8, 9, 10]


def test_multithreaded_concurrency(ledger: CryptographicLedger) -> None:
    ledger.initialize_production_ledger("org_universal", "prod_oppenheimer", "usr_1")

    def append_worker(idx: int) -> None:
        ledger.append_event(
            "org_universal",
            "prod_oppenheimer",
            f"usr_{idx}",
            "SCORE_ASSIGNED",
            {"thread_idx": idx},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(append_worker, i) for i in range(40)]
        concurrent.futures.wait(futures)

    events = ledger.get_events("prod_oppenheimer", limit=100)
    assert len(events) == 41  # 1 genesis + 40 appends
    valid, reason, count = ledger.verify_chain("prod_oppenheimer")
    assert valid is True
    assert reason is None
    assert count == 41


def test_verification_performance_1000_events(ledger: CryptographicLedger) -> None:
    ledger.initialize_production_ledger("org_bench", "prod_bench_1k", "usr_lead")
    for i in range(999):
        ledger.append_event(
            "org_bench",
            "prod_bench_1k",
            "usr_agent",
            "CLAIM_CREATED",
            {"index": i, "data": f"payload_data_{i}", "risk": "LOW"},
        )

    start_time = time.perf_counter()
    valid, reason, count = ledger.verify_chain("prod_bench_1k")
    elapsed = time.perf_counter() - start_time

    assert valid is True
    assert count == 1000
    assert elapsed < 2.0, f"Chain verification took {elapsed:.4f}s, exceeding 2.0s limit"
    print(f"\n[BENCHMARK] Verified 1,000-event cryptographic chain in {elapsed*1000:.2f}ms")


def test_repository_backing_integration(ledger: CryptographicLedger) -> None:
    mock_repo = MagicMock()
    backed_ledger = CryptographicLedger(repository=mock_repo)
    backed_ledger.initialize_production_ledger("org_apple", "prod_napoleon", "usr_1")
    backed_ledger.append_event("org_apple", "prod_napoleon", "usr_1", "BUDGET_INCREASED", {"amt": 10000})

    assert mock_repo.append_audit_event.call_count == 2
