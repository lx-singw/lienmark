"""
tests/test_evidence_pack_adversarial.py

Adversarial test suite for Sprint 5.4 Offline Verifier hardening.
Verifies resistance to Zip-Slip, path traversal, reviewer bypasses,
non-canonical JSON, and ledger tampering vectors.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import json
import os
import zipfile
import pytest

from backend.services.evidence_pack_builder import build_evidence_pack
from scripts.verify_evidence_pack import (
    _canonical_json,
    _extract_zip_if_needed,
    verify_file_integrity,
    verify_pack_directory,
)
from tests.test_evidence_pack_and_verifier import _rehash_manifest, _setup_test_environment


def test_canonical_json_nan_rejected():
    """Verifies that non-RFC-8259 NaN and Infinity values are rejected."""
    with pytest.raises(ValueError):
        _canonical_json({"invalid_float": float("nan")})
    with pytest.raises(ValueError):
        _canonical_json({"invalid_float": float("inf")})


def test_zip_slip_attempt_raises(tmp_path):
    """Verifies that zip archives with directory traversal paths are blocked."""
    zip_path = str(tmp_path / "malicious.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../slip.txt", b"malicious content")
    with pytest.raises(ValueError, match="Zip-slip path traversal detected in archive"):
        _extract_zip_if_needed(zip_path)


def test_manifest_path_traversal_rejected(tmp_path):
    """Verifies that manifest paths escaping the pack directory are rejected."""
    from backend.services.evidence_pack_types import compute_manifest_root_hash
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, manifest = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    man_path = os.path.join(pack_dir, "manifest.json")
    with open(man_path, "r", encoding="utf-8") as f:
        m_data = json.load(f)
    m_data["files"]["../../escaped.txt"] = {"size_bytes": 10, "sha256": "0" * 64, "category": "evidence"}
    m_data["file_count"] = len(m_data["files"])
    m_data["root_hash"] = compute_manifest_root_hash(m_data["files"])
    ok, msg, _ = verify_file_integrity(pack_dir, m_data)
    assert ok is False
    assert "Manifest path traversal detected" in msg


def test_self_clearing_case_insensitive_bypass(tmp_path):
    """Verifies that case manipulation in reviewer ID fails Gate 3."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    pkg_dir = os.path.join(pack_dir, "packages")
    pkg_file = os.path.join(pkg_dir, os.listdir(pkg_dir)[0])
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    pkg_data["secondary_approval"]["reviewer_id"] = pkg_data["primary_approval"]["reviewer_id"].upper()
    with open(pkg_file, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["two_distinct_principals"] == "FAILED"


def test_self_clearing_whitespace_bypass(tmp_path):
    """Verifies that whitespace padding in reviewer ID fails Gate 3."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    pkg_dir = os.path.join(pack_dir, "packages")
    pkg_file = os.path.join(pkg_dir, os.listdir(pkg_dir)[0])
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    pkg_data["secondary_approval"]["reviewer_id"] = f"  {pkg_data['primary_approval']['reviewer_id']}  "
    with open(pkg_file, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["two_distinct_principals"] == "FAILED"


def test_self_clearing_identical_legal_name(tmp_path):
    """Verifies that distinct IDs with identical reviewer legal names fail Gate 3."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    pkg_dir = os.path.join(pack_dir, "packages")
    pkg_file = os.path.join(pkg_dir, os.listdir(pkg_dir)[0])
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    pkg_data["secondary_approval"]["reviewer_id"] = "usr_different_account_02"
    pkg_data["secondary_approval"]["reviewer_name"] = pkg_data["primary_approval"]["reviewer_name"].upper()
    with open(pkg_file, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["two_distinct_principals"] == "FAILED"


def test_type_juggling_conflict_attestation(tmp_path):
    """Verifies that non-boolean conflict attestation (e.g. string 'true') fails Gate 3."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    pkg_dir = os.path.join(pack_dir, "packages")
    pkg_file = os.path.join(pkg_dir, os.listdir(pkg_dir)[0])
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    pkg_data["primary_approval"]["conflict_attestation"] = "true"
    with open(pkg_file, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["two_distinct_principals"] == "FAILED"


def test_ledger_chain_type_tamper(tmp_path):
    """Verifies that sequence number type manipulation (string instead of int) fails Gate 5."""
    org_id, prod_id, out_dir, ledger, coord, store = _setup_test_environment(tmp_path)
    pack_dir, _ = build_evidence_pack(prod_id, org_id, out_dir, store, coord, ledger)
    ledger_path = os.path.join(pack_dir, "ledger", "ledger_events.json")
    with open(ledger_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    events[0]["sequence_number"] = "1"
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    _rehash_manifest(pack_dir)
    report = verify_pack_directory(pack_dir)
    assert report["is_valid"] is False
    statuses = {c["check_name"]: c["status"] for c in report["checks"]}
    assert statuses["ledger_chain"] == "FAILED"
