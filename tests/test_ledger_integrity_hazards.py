"""tests/test_ledger_integrity_hazards.py: Adversarial corruption and CLI verifier tests."""
from __future__ import annotations

import pytest
from backend.storage.ledger import AuditEvent, CryptographicLedger
from scripts.verify_ledger_integrity import verify_chain as verify_script_chain, build_demo_ledger


def create_sample_chain() -> CryptographicLedger:
    ledger = CryptographicLedger()
    ledger.initialize_production_ledger("org_neon", "prod_hazard", "usr_1")
    for i in range(3):
        ledger.append_event("org_neon", "prod_hazard", "usr_1", "FINDING_ATTACHED", {"v": i})
    return ledger


def test_chain_broken_parent_hash() -> None:
    ledger = create_sample_chain()
    chain = ledger._chains["prod_hazard"]
    tampered = AuditEvent(
        event_id=chain[2].event_id,
        tenant_id=chain[2].tenant_id,
        production_id=chain[2].production_id,
        actor_id=chain[2].actor_id,
        action_type=chain[2].action_type,
        payload=chain[2].payload,
        payload_digest=chain[2].payload_digest,
        sequence_number=chain[2].sequence_number,
        timestamp_utc=chain[2].timestamp_utc,
        previous_event_hash="f" * 64,
        entry_hash=chain[2].entry_hash,
    )
    chain[2] = tampered
    valid, reason, fail_idx = ledger.verify_chain("prod_hazard")
    assert valid is False
    assert "Broken chain link" in str(reason)
    assert fail_idx == 2


def test_chain_corrupted_payload_digest() -> None:
    ledger = create_sample_chain()
    chain = ledger._chains["prod_hazard"]
    tampered = AuditEvent(
        event_id=chain[1].event_id,
        tenant_id=chain[1].tenant_id,
        production_id=chain[1].production_id,
        actor_id=chain[1].actor_id,
        action_type=chain[1].action_type,
        payload=chain[1].payload,
        payload_digest="a" * 64,
        sequence_number=chain[1].sequence_number,
        timestamp_utc=chain[1].timestamp_utc,
        previous_event_hash=chain[1].previous_event_hash,
        entry_hash=chain[1].entry_hash,
    )
    chain[1] = tampered
    valid, reason, fail_idx = ledger.verify_chain("prod_hazard")
    assert valid is False
    assert "Payload digest mismatch" in str(reason)
    assert fail_idx == 1


def test_chain_corrupted_entry_hash() -> None:
    ledger = create_sample_chain()
    chain = ledger._chains["prod_hazard"]
    tampered = AuditEvent(
        event_id=chain[1].event_id,
        tenant_id=chain[1].tenant_id,
        production_id=chain[1].production_id,
        actor_id=chain[1].actor_id,
        action_type=chain[1].action_type,
        payload=chain[1].payload,
        payload_digest=chain[1].payload_digest,
        sequence_number=chain[1].sequence_number,
        timestamp_utc=chain[1].timestamp_utc,
        previous_event_hash=chain[1].previous_event_hash,
        entry_hash="b" * 64,
    )
    chain[1] = tampered
    valid, reason, fail_idx = ledger.verify_chain("prod_hazard")
    assert valid is False
    assert "Entry hash mismatch" in str(reason)
    assert fail_idx == 1


def test_scripts_verify_production_ledger() -> None:
    demo_events = build_demo_ledger("prod_broadway_01")
    res = verify_script_chain(demo_events, production_id="prod_broadway_01")
    assert res.is_valid is True
    assert res.total_events == 6
    assert res.valid_links == 6
