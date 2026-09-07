"""
tests/test_evidence_pack_and_verifier.py

Acceptance and regression test suite for Sprint 5.4:
Verifiable Evidence Pack & Standalone Offline Verifier.
Verifies all 5 fail-closed gates, tampering detection, and offline CLI invocation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import json
import os
import subprocess
import sys
from typing import Any, Dict, Tuple
import pytest

from backend.core.decision_package import create_decision_package
from backend.core.dual_review import DualReviewCoordinator
from backend.services.evidence_pack_builder import build_evidence_pack
from backend.services.evidence_pack_types import compute_manifest_root_hash
from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store import PolicyStore
from backend.storage.policy_store_types import PolicyStoreMode
from scripts.verify_evidence_pack import (
    _canonical_digest,
    verify_file_integrity,
    verify_pack_directory,
)


def _setup_test_environment(tmp_path) -> Tuple[str, str, str, CryptographicLedger, DualReviewCoordinator, PolicyStore]:
    """Sets up a populated environment with policy, package, approvals, and ledger."""
    org_id = "org_paramount_demo"
    prod_id = "prod_topgun_2026"
    ledger = CryptographicLedger()
    ledger.initialize_production_ledger("tenant_paramount", prod_id, "admin_user_1")
    store = PolicyStore(mode=PolicyStoreMode.LOCAL_DISK, base_dir=str(tmp_path / "policies"), ledger=ledger)
    cfg = {"theatrical_sync_perpetual": True, "promotional_second_review": True}
    ver_rec, _ = store.save_policy_revision(org_id, cfg, "admin_user_1")
    coord = DualReviewCoordinator(ledger=ledger)
    pkg = create_decision_package(
        claim_id="clm_trailer_cue_99", cut_revision="cut_v3",
        intended_scope={"theatrical": True, "promotional_trailer": True},
        proposed_disposition="approved", rationale="Synch license fully executed.",
        conditions=["worldwide_perpetual"], evidence_bundle=[{"doc_id": "lic_sync_001"}],
        policy_version=ver_rec.version_id, policy_digest=ver_rec.policy_digest,
    )
    pkg.production_id = prod_id
    coord._packages[pkg.package_id] = pkg
    coord.submit_approval(pkg.package_id, "usr_counsel_alpha", "Counsel Alpha", "lead_counsel", True, ledger)
    coord.submit_approval(pkg.package_id, "usr_counsel_beta", "Counsel Beta", "supervising_partner", True, ledger)
    return org_id, prod_id, str(tmp_path), ledger, coord, store


def _rehash_manifest(pack_dir: str) -> None:
    """Helper updating manifest hashes when intentionally testing non-file-integrity gates."""
    man_path = os.path.join(pack_dir, "manifest.json")
    with open(man_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    for rel_path, entry in manifest["files"].items():
        full = os.path.join(pack_dir, rel_path)
        with open(full, "rb") as f:
            b = f.read()
        entry["size_bytes"] = len(b)
        entry["sha256"] = _canonical_digest(json.loads(b) if rel_path.endswith(".json") else b.decode("utf-8")) if False else None
        import hashlib
        entry["sha256"] = hashlib.sha256(b).hexdigest()
    manifest["root_hash"] = compute_manifest_root_hash(manifest["files"])
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def test_build_and_verify_clean_evidence_pack(tmp_path):
    """Verifies that an untampered evidence pack passes 100% of all 5 verification gates."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, manifest = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    assert os.path.isdir(pack_dir)
    assert manifest.file_count >= 4
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is True
    assert report["failed_checks"] == 0
    assert report["passed_checks"] == 5
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses == {
        "file_integrity": "PASSED", "package_digests": "PASSED",
        "two_distinct_principals": "PASSED", "policy_provenance": "PASSED",
        "ledger_chain": "PASSED",
    }


def test_tamper_file_byte_fails_file_integrity(tmp_path):
    """Verifies that tampering with a single byte in any bundled file triggers Gate 1 failure."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    summary_path = os.path.join(pack_dir, "summary.md")
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("\nTAMPERED_MALICIOUS_EXTRA_LINE\n")
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["file_integrity"] == "FAILED"


def test_self_clearing_counsel_tamper_fails_gate(tmp_path):
    """Verifies Gate 3 failure when Reviewer 2 is manipulated to equal Reviewer 1."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    pkg_dir = os.path.join(pack_dir, "packages")
    pkg_file = os.path.join(pkg_dir, os.listdir(pkg_dir)[0])
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    pkg_data["secondary_approval"]["reviewer_id"] = pkg_data["primary_approval"]["reviewer_id"]
    with open(pkg_file, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["file_integrity"] == "PASSED"
    assert statuses["two_distinct_principals"] == "FAILED"


def test_tamper_ledger_chain_fails_gate(tmp_path):
    """Verifies Gate 5 failure when cryptographic ledger audit trail is altered."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    ledger_path = os.path.join(pack_dir, "ledger", "ledger_events.json")
    with open(ledger_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    events[-1]["payload"]["forged_field"] = "malicious_injection"
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["ledger_chain"] == "FAILED"


def test_tamper_policy_config_fails_provenance_gate(tmp_path):
    """Verifies Gate 4 failure when governing policy configuration is silently modified."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    pol_path = os.path.join(pack_dir, "policies", "active_policy.json")
    with open(pol_path, "r", encoding="utf-8") as f:
        pol = json.load(f)
    pol["policy_config"]["unauthorized_waiver"] = True
    with open(pol_path, "w", encoding="utf-8") as f:
        json.dump(pol, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["policy_provenance"] == "FAILED"


def test_standalone_cli_execution(tmp_path):
    """Verifies that the standalone CLI returns exit code 0 on clean pack and 1 on tampered pack."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    cli_path = os.path.join(os.getcwd(), "scripts", "verify_evidence_pack.py")
    res_clean = subprocess.run([sys.executable, cli_path, "--pack-dir", pack_dir], capture_output=True, text=True)
    assert res_clean.returncode == 0
    assert "PASSED (VERIFIED)" in res_clean.stdout
    with open(os.path.join(pack_dir, "summary.md"), "a") as f:
        f.write("tamper")
    res_tampered = subprocess.run([sys.executable, cli_path, "--pack-dir", pack_dir], capture_output=True, text=True)
    assert res_tampered.returncode == 1
    assert "FAILED" in res_tampered.stdout


def test_zipped_evidence_pack_export_and_verification(tmp_path):
    """Verifies export to .zip format and transparent verifier extraction and validation."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    zip_path, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger, export_zip=True)
    assert os.path.isfile(zip_path)
    assert zip_path.endswith(".zip")
    cli_path = os.path.join(os.getcwd(), "scripts", "verify_evidence_pack.py")
    res = subprocess.run([sys.executable, cli_path, zip_path], capture_output=True, text=True)
    assert res.returncode == 0
    assert "PASSED (VERIFIED)" in res.stdout
