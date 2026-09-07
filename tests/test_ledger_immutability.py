"""
tests/test_ledger_immutability.py

Automated Test Suite for Sprint 1.3 CryptographicLedger.
Verifies genesis creation, append-only hash chaining, tamper-evident immutability,
supersession preservation, broken link detection, and high-speed chain verification.
"""

from __future__ import annotations

import time
import pytest
from typing import Any, Dict, List, Tuple

from backend.storage.ledger import (
    CryptographicLedger,
    AuditEvent,
    LedgerTamperError,
    LedgerIntegrityError,
    compute_canonical_digest,
    compute_entry_hash,
)


@pytest.fixture
def ledger() -> CryptographicLedger:
    """Provides a fresh, isolated CryptographicLedger instance."""
    return CryptographicLedger()


class TestGenesisAndSequenceNumbering:
    """Validates genesis block creation, sequence numbers, and initialization invariants."""

    def test_genesis_creation_and_sequence_numbering(self, ledger: CryptographicLedger) -> None:
        genesis: AuditEvent = ledger.initialize_production_ledger(
            tenant_id="org_studio_alpha",
            production_id="prod_noir_001",
            actor_id="user_admin_01",
        )
        assert genesis.sequence_number == 1
        assert genesis.previous_event_hash == "0" * 64
        assert genesis.action_type == "GENESIS"
        assert len(genesis.entry_hash) == 64

        events = ledger.get_events("prod_noir_001")
        assert len(events) == 1
        assert events[0].event_id == genesis.event_id

    def test_reinitialization_raises_ledger_integrity_error(self, ledger: CryptographicLedger) -> None:
        ledger.initialize_production_ledger("org_studio_alpha", "prod_noir_001", "user_admin_01")
        with pytest.raises(LedgerIntegrityError, match="already initialized"):
            ledger.initialize_production_ledger("org_studio_alpha", "prod_noir_001", "user_admin_01")


class TestAppendOnlyEventChaining:
    """Validates SHA-256 parent hash continuity across sequential event additions."""

    def test_append_only_event_chaining(self, ledger: CryptographicLedger) -> None:
        genesis = ledger.initialize_production_ledger("org_alpha", "prod_chain", "actor_1")

        # Event 2: Claim created
        evt_claim = ledger.append_event(
            tenant_id="org_alpha",
            production_id="prod_chain",
            actor_id="agent_discovery",
            action_type="CLAIM_CREATED",
            payload={"claim_id": "c1", "type": "music", "title": "Midnight Serenade"},
        )
        assert evt_claim.sequence_number == 2
        assert evt_claim.previous_event_hash == genesis.entry_hash

        # Event 3: Finding attached
        evt_finding = ledger.append_event(
            tenant_id="org_alpha",
            production_id="prod_chain",
            actor_id="agent_research",
            action_type="FINDING_ATTACHED",
            payload={"claim_id": "c1", "publisher": "Vanguard Media", "status": "active"},
        )
        assert evt_finding.sequence_number == 3
        assert evt_finding.previous_event_hash == evt_claim.entry_hash

        is_valid, err, count = ledger.verify_chain("prod_chain")
        assert is_valid is True
        assert err is None
        assert count == 3


class TestImmutabilityAndTamperError:
    """Validates that mutating, updating, or deleting any event raises LedgerTamperError."""

    def test_update_and_delete_methods_raise_ledger_tamper_error(self, ledger: CryptographicLedger) -> None:
        ledger.initialize_production_ledger("org_alpha", "prod_tamper", "actor_1")

        with pytest.raises(LedgerTamperError, match="immutable and cannot be updated"):
            ledger.update_event("prod_tamper", "evt_1", {})

        with pytest.raises(LedgerTamperError, match="append-only; entries cannot be deleted"):
            ledger.delete_event("prod_tamper", "evt_1")

        with pytest.raises(LedgerTamperError, match="does not support direct index assignment"):
            ledger["prod_tamper"] = []

        with pytest.raises(LedgerTamperError, match="does not support entry deletion"):
            del ledger["prod_tamper"]

    def test_audit_event_attribute_mutation_raises_ledger_tamper_error(
        self, ledger: CryptographicLedger
    ) -> None:
        event = ledger.initialize_production_ledger("org_alpha", "prod_evt_mut", "actor_1")

        with pytest.raises(LedgerTamperError, match="AuditEvent is immutable"):
            event.action_type = "TAMPERED"

        with pytest.raises(LedgerTamperError, match="AuditEvent is immutable"):
            del event.actor_id

    def test_immutable_payload_mutation_raises_ledger_tamper_error(
        self, ledger: CryptographicLedger
    ) -> None:
        event = ledger.initialize_production_ledger("org_alpha", "prod_pl_mut", "actor_1")

        with pytest.raises(LedgerTamperError, match="Cannot modify"):
            event.payload["new_key"] = "tampered"

        with pytest.raises(LedgerTamperError, match="Cannot delete"):
            del event.payload["action"]

        with pytest.raises(LedgerTamperError, match="forbidden"):
            event.payload.clear()



class TestSupersessionIntegrity:
    """Validates that supersession appends a new event while leaving historical events unaltered."""

    def test_supersession_recorded_via_superseded_event(self, ledger: CryptographicLedger) -> None:
        ledger.initialize_production_ledger("org_alpha", "prod_super", "actor_1")
        original_claim = ledger.append_event(
            tenant_id="org_alpha",
            production_id="prod_super",
            actor_id="agent_intake",
            action_type="CLAIM_CREATED",
            payload={"claim_id": "c1", "status": "needs_review"},
        )
        orig_hash = original_claim.entry_hash
        orig_seq = original_claim.sequence_number

        super_event = ledger.record_supersession(
            tenant_id="org_alpha",
            production_id="prod_super",
            actor_id="counsel_01",
            superseded_event_id=original_claim.event_id,
            superseding_payload={"claim_id": "c1", "status": "approved", "rationale": "Fair use § 107"},
        )
        assert super_event.action_type == "SUPERSEDED"
        assert super_event.sequence_number == 3
        assert super_event.payload["superseded_event_id"] == original_claim.event_id
        assert super_event.previous_event_hash == orig_hash

        # Original event in chain is completely unaltered
        events = ledger.get_events("prod_super")
        assert events[1].entry_hash == orig_hash
        assert events[1].sequence_number == orig_seq
        assert events[1].payload["status"] == "needs_review"

        is_valid, err, count = ledger.verify_chain("prod_super")
        assert is_valid is True
        assert count == 3

    def test_supersession_nonexistent_event_raises_integrity_error(
        self, ledger: CryptographicLedger
    ) -> None:
        ledger.initialize_production_ledger("org_alpha", "prod_super_err", "actor_1")
        with pytest.raises(LedgerIntegrityError, match="not found"):
            ledger.record_supersession(
                tenant_id="org_alpha",
                production_id="prod_super_err",
                actor_id="counsel_01",
                superseded_event_id="evt_missing_id",
                superseding_payload={},
            )


class TestTamperingDetectionAndPinpointing:
    """Validates that modifying payload, previous hash, or timestamp causes verify_chain to fail."""

    def test_tampering_payload_fails_verification_and_pinpoints_link(
        self, ledger: CryptographicLedger
    ) -> None:
        ledger.initialize_production_ledger("org_alpha", "prod_tamper_det", "actor_1")
        evt2 = ledger.append_event("org_alpha", "prod_tamper_det", "actor_2", "CLAIM_CREATED", {"c": 1})
        evt3 = ledger.append_event("org_alpha", "prod_tamper_det", "actor_3", "FINDING_ATTACHED", {"f": 2})

        # Bypass frozen Pydantic via object.__setattr__ to simulate malicious storage tampering
        tampered_payload = {"c": 999999}
        object.__setattr__(evt2, "payload", tampered_payload)

        is_valid, err, link_idx = ledger.verify_chain("prod_tamper_det")
        assert is_valid is False
        assert "Payload digest mismatch" in str(err)
        assert link_idx == 1  # Pinpoints index 1 (evt2)

    def test_tampering_previous_hash_pinpoints_broken_link(self, ledger: CryptographicLedger) -> None:
        ledger.initialize_production_ledger("org_alpha", "prod_prev_tamper", "actor_1")
        ledger.append_event("org_alpha", "prod_prev_tamper", "actor_2", "CLAIM_CREATED", {"c": 1})
        evt3 = ledger.append_event("org_alpha", "prod_prev_tamper", "actor_3", "FINDING_ATTACHED", {"f": 2})

        # Tamper previous_event_hash of block 3
        object.__setattr__(evt3, "previous_event_hash", "f" * 64)

        is_valid, err, link_idx = ledger.verify_chain("prod_prev_tamper")
        assert is_valid is False
        assert "Broken chain link" in str(err)
        assert link_idx == 2  # Pinpoints index 2 (evt3)


class TestLedgerVerificationBenchmark:
    """Validates high-performance hash chain verification (< 2.0s for 1,000 events)."""

    def test_1000_event_chain_verification_under_2_seconds(self, ledger: CryptographicLedger) -> None:
        prod_id = "prod_benchmark_1000"
        ledger.initialize_production_ledger("org_alpha", prod_id, "genesis_actor")

        for i in range(1, 1001):
            ledger.append_event(
                tenant_id="org_alpha",
                production_id=prod_id,
                actor_id="benchmark_worker",
                action_type="CLAIM_CREATED",
                payload={"claim_id": f"claim_{i}", "index": i, "score": 0.85},
            )

        start_time = time.perf_counter()
        is_valid, err, count = ledger.verify_chain(prod_id)
        elapsed = time.perf_counter() - start_time

        assert is_valid is True
        assert err is None
        assert count == 1001
        assert elapsed < 2.0, f"Benchmark failed: 1,000 events took {elapsed:.4f}s (required < 2.0s)"
