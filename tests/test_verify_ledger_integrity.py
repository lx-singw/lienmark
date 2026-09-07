"""
tests/test_verify_ledger_integrity.py

Enterprise test suite verifying scripts/verify_ledger_integrity.py.
Sprint 1.3 / Security Specification SEC-SPEC-03-AUDIT-CRYPTO.

Validates:
1. Genesis block invariants (previous_event_hash == '0'*64 and sequence_number == 1).
2. Strict monotonic sequence numbers (1, 2, 3, ...).
3. Continuous parent hash linkage (E_{i}.previous_event_hash == E_{i-1}.entry_hash).
4. Payload digest matches SHA-256 canonical JSON.
5. Entry hash matches canonical formula.
6. 1,000-event benchmark executes in strictly < 2.0s.
7. CLI argument parsing and exit codes (0 for intact, 1 for tamper, 2 for usage error).
"""

import copy
import json
import os
import tempfile
import time
import pytest

from scripts.verify_ledger_integrity import (
    GENESIS_PARENT_HASH,
    VerificationResult,
    build_demo_ledger,
    build_secondary_demo_ledger,
    compute_canonical_digest,
    compute_entry_hash,
    generate_synthetic_chain,
    load_events_from_file,
    main,
    render_summary_table,
    run_benchmark_suite,
    verify_chain,
)


class TestGenesisInvariants:
    """Tests Invariant 1: Genesis block constraints."""

    def test_genesis_valid_defaults(self):
        events = build_demo_ledger("prod_test_01")
        assert len(events) >= 1
        assert events[0]["sequence_number"] == 1
        assert events[0]["previous_event_hash"] == GENESIS_PARENT_HASH

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is True
        assert result.tampered_links == 0
        assert result.valid_links == len(events)

    def test_genesis_invalid_previous_hash_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        events[0]["previous_event_hash"] = "f" * 64

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert result.tampered_links == 1
        assert result.tampered_sequence == 1
        assert "Invalid genesis previous_event_hash" in result.tampered_reason

    def test_genesis_invalid_sequence_number_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        events[0]["sequence_number"] = 2

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert result.tampered_links == 1
        assert "Invalid genesis sequence_number" in result.tampered_reason


class TestMonotonicSequenceInvariants:
    """Tests Invariant 2: Strict monotonic sequence numbers (1, 2, 3, ...)."""

    def test_sequence_gap_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        # Introduce gap at index 2 (seq 3 -> 4)
        events[2]["sequence_number"] = 4

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert result.tampered_links == 1
        assert "Non-monotonic sequence number" in result.tampered_reason

    def test_sequence_duplicate_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        events[2]["sequence_number"] = 2

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert "Non-monotonic sequence number" in result.tampered_reason


class TestContinuousParentHashInvariants:
    """Tests Invariant 3: Continuous parent hash linkage."""

    def test_broken_parent_link_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        # Alter parent hash of event 3
        events[2]["previous_event_hash"] = "a" * 64

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert result.tampered_links == 1
        assert "Broken parent hash linkage" in result.tampered_reason

    def test_reordered_events_fail(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        # Swap events 2 and 3
        events[1], events[2] = events[2], events[1]

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False


class TestPayloadDigestInvariants:
    """Tests Invariant 4: Payload digest matching canonical JSON SHA-256."""

    def test_mutated_payload_content_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        # Alter claim description in payload without updating payload_digest
        events[1]["payload"]["target_claims"].append("fraudulent_unapproved_claim")

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert "Payload digest mismatch" in result.tampered_reason

    def test_forged_payload_digest_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        events[1]["payload_digest"] = "e" * 64

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert "Payload digest mismatch" in result.tampered_reason


class TestEntryHashInvariants:
    """Tests Invariant 5: Entry hash matching canonical formula."""

    def test_corrupted_entry_hash_fails(self):
        events = copy.deepcopy(build_demo_ledger("prod_test_01"))
        events[2]["entry_hash"] = "0" * 64

        result = verify_chain(events, production_id="prod_test_01")
        assert result.is_valid is False
        assert "Entry hash mismatch" in result.tampered_reason


class TestEmptyAndEdgeCases:
    """Tests edge cases such as empty chains and summary rendering."""

    def test_empty_chain_is_trivially_valid(self):
        result = verify_chain([], production_id="prod_empty")
        assert result.is_valid is True
        assert result.total_events == 0
        assert result.valid_links == 0
        assert result.tampered_links == 0

    def test_summary_table_rendering(self):
        res1 = VerificationResult(
            production_id="prod_01", total_events=6, valid_links=6,
            tampered_links=0, elapsed_ms=1.23, is_valid=True
        )
        res2 = VerificationResult(
            production_id="prod_02", total_events=4, valid_links=3,
            tampered_links=1, elapsed_ms=0.95, is_valid=False
        )
        table = render_summary_table([res1, res2])
        assert "prod_01" in table
        assert "prod_02" in table
        assert "[PASS] VERIFIED INTACT" in table
        assert "[FAIL] TAMPER DETECTED" in table


class TestBenchmarkPerformance:
    """Tests requirement: 1,000 synthetic events verified in < 2.0s."""

    def test_benchmark_synthetic_chain_under_2_seconds(self):
        t0 = time.perf_counter()
        events = generate_synthetic_chain(count=1000, production_id="prod_bench_test")
        gen_time = (time.perf_counter() - t0) * 1000.0

        assert len(events) == 1000
        assert events[0]["sequence_number"] == 1
        assert events[0]["previous_event_hash"] == GENESIS_PARENT_HASH
        assert events[-1]["sequence_number"] == 1000

        result = verify_chain(events, production_id="prod_bench_test")
        assert result.is_valid is True
        assert result.total_events == 1000
        assert result.valid_links == 1000
        assert result.tampered_links == 0
        # Verification latency must be strictly < 2.0s (2000 ms)
        assert result.elapsed_ms < 2000.0

    def test_run_benchmark_suite_exit_code(self):
        exit_code = run_benchmark_suite(count=1000)
        assert exit_code == 0


class TestCliExecutionAndExitCodes:
    """Tests CLI entrypoint and exit codes (0 for intact, 1 for fail, 2 for error)."""

    def test_cli_missing_args_returns_code_2(self):
        exit_code = main([])
        assert exit_code == 2

    def test_cli_benchmark_returns_code_0(self):
        exit_code = main(["--benchmark"])
        assert exit_code == 0

    def test_cli_single_production_returns_code_0(self):
        exit_code = main(["--production-id", "prod_broadway_01"])
        assert exit_code == 0

    def test_cli_all_productions_returns_code_0(self):
        exit_code = main(["--all"])
        assert exit_code == 0

    def test_cli_nonexistent_file_returns_code_2(self):
        exit_code = main(["--ledger-file", "nonexistent_ledger_file_12345.json", "--all"])
        assert exit_code == 2

    def test_cli_ledger_file_valid_and_tampered(self):
        events = build_demo_ledger("prod_file_test")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump({"events": events}, tf)
            temp_path = tf.name

        try:
            # 1. Clean file -> code 0
            code_clean = main(["--ledger-file", temp_path, "--production-id", "prod_file_test"])
            assert code_clean == 0

            # 2. Tamper file -> code 1
            tampered_events = copy.deepcopy(events)
            tampered_events[1]["payload"]["fraud"] = True
            with open(temp_path, "w", encoding="utf-8") as tf:
                json.dump({"events": tampered_events}, tf)

            code_tampered = main(["--ledger-file", temp_path, "--production-id", "prod_file_test"])
            assert code_tampered == 1
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
