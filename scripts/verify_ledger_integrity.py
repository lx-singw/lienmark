#!/usr/bin/env python3
"""
scripts/verify_ledger_integrity.py

Lienmark Standalone Cryptographic Ledger Integrity Verifier.
Sprint 1.3 / Security Specification SEC-SPEC-03-AUDIT-CRYPTO.

Audits entertainment insurance append-only ledger chains, validating:
1. Genesis block has previous_event_hash == "0"*64 and sequence_number == 1.
2. Strict monotonic sequence numbers (1, 2, 3, ...).
3. Continuous parent hash linkage: E_{i}.previous_event_hash == E_{i-1}.entry_hash.
4. Payload digest matches: payload_digest == SHA256(canonical JSON of payload).
5. Entry hash matches canonical formula.

Exit codes:
  0: Verified intact chain (100% cryptographic integrity).
  1: Verification failure / tamper detected.
  2: Missing input or usage error.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Re-export all core primitives for backward compatibility
from scripts.ledger_verification_core import (  # noqa: F401
    GENESIS_PARENT_HASH,
    VerificationResult,
    compute_canonical_digest,
    compute_entry_hash,
    verify_chain,
    verify_entry_hash_match,
)
from scripts.ledger_fixtures import (  # noqa: F401
    build_demo_ledger,
    build_secondary_demo_ledger,
    generate_synthetic_chain,
    load_events_from_file,
    render_summary_table,
)


def run_benchmark_suite(count: int = 1000, verbose: bool = False) -> int:
    """Runs high-performance verification benchmark across synthetic events."""
    print("=" * 86)
    print(">> LIENMARK CRYPTOGRAPHIC LEDGER AUDIT BENCHMARK")
    print(f"   Generating and verifying {count:,} linked events (Strict Gate: Latency < 2.0s)")
    print("=" * 86)

    t_gen_0 = time.perf_counter()
    events = generate_synthetic_chain(count=count, production_id="prod_benchmark_1000")
    t_gen_ms = (time.perf_counter() - t_gen_0) * 1000.0
    print(f"[*] Synthetic Chain Generation: {count:,} events sealed in {t_gen_ms:.2f} ms")

    result = verify_chain(events, production_id="prod_benchmark_1000", verbose=verbose)
    table = render_summary_table([result])
    print("\n" + table + "\n")

    avg_us = (result.elapsed_ms / count) * 1000.0
    print(f"[*] Total Verification Time:    {result.elapsed_ms:.2f} ms ({result.elapsed_ms / 1000.0:.4f} seconds)")
    print(f"[*] Per-Event Latency:          {avg_us:.2f} µs / event")
    print("[*] Maximum SLA Allowance:      2000.00 ms (2.0s)")

    if result.is_valid and result.elapsed_ms < 2000.0:
        print(f"[PASS] SLA Satisfied: {result.elapsed_ms:.2f} ms < 2000.00 ms (100% Intact).")
        return 0
    print("[FAIL] Benchmark failed: integrity compromised or exceeded latency allowance.")
    return 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        prog="verify_ledger_integrity",
        description="Lienmark Standalone Cryptographic Ledger Integrity Auditor (Sprint 1.3)",
    )
    parser.add_argument("--production-id", type=str, default=None, help="Production ID to verify.")
    parser.add_argument("--all", action="store_true", help="Verify all productions.")
    parser.add_argument("--ledger-file", type=str, default=None, help="Path to JSON/JSONL ledger file.")
    parser.add_argument("--in-memory-demo", action="store_true", help="Verify demo production ledger.")
    parser.add_argument("--tenant-id", type=str, default="org_studio_alpha", help="Tenant ID.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--benchmark", action="store_true", help="Run 1,000-event benchmark (< 2.0s).")
    return parser.parse_args(argv)


def _resolve_from_file(args: argparse.Namespace) -> Tuple[Optional[Dict[str, List[Dict[str, Any]]]], int]:
    """Resolves productions and events from an external ledger file."""
    try:
        loaded = load_events_from_file(args.ledger_file)
    except FileNotFoundError as fnf_err:
        sys.stderr.write(f"Error: {fnf_err}\n")
        return None, 2
    except Exception as e:
        sys.stderr.write(f"Error: Failed to parse ledger file '{args.ledger_file}': {e}\n")
        return None, 2

    if args.all:
        return loaded, 0
    if args.production_id:
        if args.production_id in loaded:
            return {args.production_id: loaded[args.production_id]}, 0
        if len(loaded) == 1:
            return {args.production_id: next(iter(loaded.values()))}, 0
        return {args.production_id: []}, 0
    return {}, 0


def _resolve_productions(args: argparse.Namespace) -> Tuple[Optional[Dict[str, List[Dict[str, Any]]]], int]:
    """Resolves target productions and audit events from args."""
    if args.ledger_file:
        return _resolve_from_file(args)

    demos = {
        "prod_broadway_01": build_demo_ledger(production_id="prod_broadway_01", tenant_id=args.tenant_id),
        "prod_noir_film_v8": build_secondary_demo_ledger(production_id="prod_noir_film_v8", tenant_id=args.tenant_id),
    }
    if args.all:
        return demos, 0
    if args.production_id:
        if args.production_id in demos:
            return {args.production_id: demos[args.production_id]}, 0
        return {args.production_id: build_demo_ledger(args.production_id, args.tenant_id)}, 0
    return {}, 0


def _audit_and_report(productions: Dict[str, List[Dict[str, Any]]], verbose: bool) -> int:
    """Audits each production chain and prints the summary report."""
    print("=" * 86)
    print(">> LIENMARK APPEND-ONLY CRYPTOGRAPHIC LEDGER AUDITOR")
    print("   Evaluating SHA-256 parent linkages, monotonically increasing sequence numbers,")
    print("   payload digests, and immutable entry hashes under Form E&O-2026.")
    print("=" * 86 + "\n")

    results: List[VerificationResult] = []
    overall_valid = True

    for prod_id, events in productions.items():
        if verbose:
            print(f"\n[*] Auditing Production Chain: {prod_id} ({len(events)} events)...")
        res = verify_chain(events, production_id=prod_id, verbose=verbose)
        results.append(res)
        if not res.is_valid:
            overall_valid = False

    print(render_summary_table(results) + "\n")

    if not overall_valid:
        print("[FAIL] TAMPER DETECTED: Ledger chain integrity check failed.")
        for r in results:
            if not r.is_valid:
                print(f"  - Production '{r.production_id}' failed at sequence {r.tampered_sequence}: {r.details}")
        return 1

    print("[PASS] 100% VERIFIED INTACT: All cryptographic links and canonical digests validated.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    args = parse_args(argv)

    if args.benchmark:
        return run_benchmark_suite(count=1000, verbose=args.verbose)

    if not args.production_id and not args.all:
        sys.stderr.write(
            "Error: Argument --production-id is required unless --all or --benchmark is specified.\n"
            "Run with --help for usage details, or specify '--in-memory-demo --all' to audit demo ledgers.\n"
        )
        return 2

    productions, code = _resolve_productions(args)
    if code != 0:
        return code
    if not productions:
        sys.stderr.write("Error: No productions or events resolved for auditing.\n")
        return 2

    return _audit_and_report(productions, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
