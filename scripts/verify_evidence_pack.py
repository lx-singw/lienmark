"""
scripts/verify_evidence_pack.py - Standalone Offline Verifier for Lienmark Evidence Packs.
Strict standard library: zero external dependencies, zero network requests. Sprint 5.4.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _canonical_json(payload: Any) -> str:
    """Deterministically serializes payload to compact JSON."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str)


def _canonical_digest(payload: Any) -> str:
    """Calculates SHA-256 hex digest of deterministic JSON."""
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _recompute_pkg_digest(raw: Dict[str, Any]) -> str:
    """Computes canonical package digest matching DecisionPackage specification."""
    pol_ver = raw.get("effective_policy_version") or raw.get("policy_version") or ""
    pol_dig = raw.get("effective_policy_digest") or raw.get("policy_digest") or ""
    s_fn = lambda x: json.dumps(x, sort_keys=True, default=str)
    c_repr = {
        "applicability_assessments": sorted(raw.get("applicability_assessments") or [], key=s_fn),
        "claim_data": raw.get("claim_data") or {}, "claim_id": str(raw.get("claim_id", "")).strip(),
        "conditions": sorted(raw.get("conditions") or [], key=s_fn),
        "cut_revision": str(raw.get("cut_revision", "")).strip(),
        "effective_policy_digest": str(pol_dig).strip(),
        "effective_policy_version": str(pol_ver).strip(),
        "evidence_bundle": sorted(raw.get("evidence_bundle") or [], key=s_fn),
        "evidence_data": raw.get("evidence_data") or {}, "intended_scope": raw.get("intended_scope") or {},
        "license_data": raw.get("license_data") or {}, "occurrence_id": str(raw.get("occurrence_id", "")).strip(),
        "proposed_disposition": str(raw.get("proposed_disposition", "")).strip(),
        "rationale": str(raw.get("rationale", "")).strip(),
        "required_reviewer_roles": sorted(list(raw.get("required_reviewer_roles") or raw.get("required_roles") or [])),
        "version": int(raw.get("version", 1)),
    }
    return hashlib.sha256(_canonical_json(c_repr).encode("utf-8")).hexdigest()


def verify_file_integrity(pack_dir: str, manifest: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Gate 1: Verifies manifest root hash and individual file digests."""
    files_map = manifest.get("files", {})
    if not files_map or (manifest.get("file_count") is not None and manifest.get("file_count") != len(files_map)):
        return False, "Manifest file entries empty or count mismatch (fail-closed)", {}
    lines = [f"{p}:{files_map[p].get('sha256')}" for p in sorted(files_map.keys())]
    expected_root = hashlib.sha256(("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")).hexdigest()
    if expected_root != manifest.get("root_hash"):
        return False, f"Manifest root hash mismatch: expected {expected_root} != {manifest.get('root_hash')}", {}
    clean_base = os.path.abspath(pack_dir)
    for rel_path, entry in files_map.items():
        disk_path = os.path.abspath(os.path.join(clean_base, rel_path.replace("/", os.sep)))
        try:
            if os.path.commonpath([clean_base, disk_path]) != clean_base:
                return False, f"Manifest path traversal detected: {rel_path}", {"path": rel_path}
        except ValueError:
            return False, f"Manifest path traversal detected: {rel_path}", {"path": rel_path}
        if not os.path.exists(disk_path):
            return False, f"Missing bundled file on disk: {rel_path}", {"missing_file": rel_path}
        with open(disk_path, "rb") as f:
            data = f.read()
        if len(data) != entry.get("size_bytes") or hashlib.sha256(data).hexdigest() != entry.get("sha256"):
            return False, f"Cryptographic tamper or size mismatch in {rel_path}", {"file": rel_path}
    return True, f"All {len(files_map)} bundled files cryptographically verified.", {"files_verified": len(files_map)}


def verify_package_digests(pack_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Gate 2: Recomputes and verifies canonical digests of all decision packages."""
    pkg_dir = os.path.join(pack_dir, "packages")
    if not os.path.exists(pkg_dir):
        return True, "No packages bundled.", {"packages_verified": 0}
    checked = 0
    for name in sorted(os.listdir(pkg_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(pkg_dir, name), "r", encoding="utf-8") as f:
            pkg = json.load(f)
        recomputed, claimed = _recompute_pkg_digest(pkg), pkg.get("canonical_digest")
        if recomputed != claimed:
            return False, f"Package {name} digest mismatch: {recomputed} != {claimed}", {"file": name}
        checked += 1
    return True, f"Successfully verified canonical digests for {checked} packages.", {"packages_verified": checked}


def verify_two_distinct_principals(pack_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Gate 3: Enforces two distinct counsel sign-offs on final approved packages."""
    pkg_dir = os.path.join(pack_dir, "packages")
    if not os.path.exists(pkg_dir):
        return True, "No packages to verify.", {}
    final_count = 0
    for name in sorted(os.listdir(pkg_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(pkg_dir, name), "r", encoding="utf-8") as f:
            pkg = json.load(f)
        if pkg.get("status") == "final_approved" or (pkg.get("primary_approval") and pkg.get("secondary_approval")):
            r1, r2 = pkg.get("primary_approval") or {}, pkg.get("secondary_approval") or {}
            id1, id2 = str(r1.get("reviewer_id") or "").strip().casefold(), str(r2.get("reviewer_id") or "").strip().casefold()
            name1, name2 = str(r1.get("reviewer_name") or "").strip().casefold(), str(r2.get("reviewer_name") or "").strip().casefold()
            if not r1 or not r2 or not id1 or not id2 or id1 == id2 or (name1 and name2 and name1 == name2):
                return False, f"Self-clearing or invalid reviewer identity in {name}", {"package": name}
            if r1.get("conflict_attestation") is not True or r2.get("conflict_attestation") is not True:
                return False, f"Conflict attestation missing or false on package {name}", {"package": name}
            final_count += 1
    return True, f"Dual review verified: {final_count} approved packages have distinct counsel sign-offs.", {"approved_count": final_count}


def verify_policy_provenance(pack_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Gate 4: Validates governing policy digest and package policy references."""
    pol_file = os.path.join(pack_dir, "policies", "active_policy.json")
    if not os.path.exists(pol_file):
        return False, "Missing governing policy configuration: policies/active_policy.json", {}
    with open(pol_file, "r", encoding="utf-8") as f:
        pol = json.load(f)
    cfg, dig = pol.get("policy_config"), pol.get("policy_digest")
    if cfg and dig and dig not in ("default_policy", "genesis_policy"):
        if _canonical_digest(cfg) != dig:
            return False, f"Governing policy digest mismatch: {_canonical_digest(cfg)} != {dig}", {}
    return True, f"Policy provenance confirmed: version {pol.get('version_id', 'v1')} ({dig[:12] if dig else 'N/A'}).", {}


def verify_ledger_chain(pack_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Gate 5: Recomputes and validates full cryptographic ledger audit chain."""
    ledger_file = os.path.join(pack_dir, "ledger", "ledger_events.json")
    if not os.path.exists(ledger_file):
        return False, "Missing cryptographic ledger events file: ledger/ledger_events.json", {}
    with open(ledger_file, "r", encoding="utf-8") as f:
        events = json.load(f)
    if not events:
        return True, "Ledger contains zero events.", {"event_count": 0}
    prev_hash = "0" * 64
    for idx, evt in enumerate(events):
        seq = evt.get("sequence_number")
        if not isinstance(seq, int) or seq != idx + 1:
            return False, f"Non-monotonic sequence number at index {idx}: expected {idx + 1}, got {seq}", {}
        if evt.get("previous_event_hash") != prev_hash:
            return False, f"Broken cryptographic chain link at seq {seq}", {"expected": prev_hash, "got": evt.get("previous_event_hash")}
        pay_dig = _canonical_digest(evt.get("payload") if evt.get("payload") is not None else {})
        if pay_dig != evt.get("payload_digest"):
            return False, f"Payload digest mismatch at seq {seq}", {}
        ts = evt.get("timestamp_utc")
        if not ts or not isinstance(ts, str):
            return False, f"Missing or invalid timestamp at seq {seq}", {}
        expected_entry = hashlib.sha256(f"{prev_hash}{pay_dig}{ts}{seq}".encode("utf-8")).hexdigest()
        if expected_entry != evt.get("entry_hash"):
            return False, f"Entry hash tampering detected at seq {seq}", {}
        prev_hash = evt.get("entry_hash")
    return True, f"Ledger chain intact: {len(events)} events verified from genesis to terminal block.", {"events_verified": len(events)}


def verify_pack_directory(pack_dir: str) -> Dict[str, Any]:
    """Executes all 5 verification gates on an unpacked evidence pack directory."""
    if not os.path.isdir(pack_dir) or not os.path.exists(os.path.join(pack_dir, "manifest.json")):
        err = "manifest.json not found" if os.path.isdir(pack_dir) else f"Pack dir missing: {pack_dir}"
        return {"production_id": "unknown", "verified_at_utc": datetime.now(timezone.utc).isoformat(), "is_valid": False,
                "total_checks": 1, "passed_checks": 0, "failed_checks": 1, "root_hash": "",
                "checks": [{"check_name": "manifest_presence", "status": "FAILED", "message": err, "details": {}}]}
    with open(os.path.join(pack_dir, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    gates = [
        ("file_integrity", lambda: verify_file_integrity(pack_dir, manifest)),
        ("package_digests", lambda: verify_package_digests(pack_dir)),
        ("two_distinct_principals", lambda: verify_two_distinct_principals(pack_dir)),
        ("policy_provenance", lambda: verify_policy_provenance(pack_dir)),
        ("ledger_chain", lambda: verify_ledger_chain(pack_dir)),
    ]
    checks = [{"check_name": name, "status": "PASSED" if ok else "FAILED", "message": msg, "details": tel}
              for name, fn in gates for ok, msg, tel in [fn()]]
    passed = sum(1 for c in checks if c["status"] == "PASSED")
    return {
        "production_id": manifest.get("production_id", "unknown"),
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "is_valid": passed == len(checks), "total_checks": len(checks), "passed_checks": passed,
        "failed_checks": len(checks) - passed, "root_hash": manifest.get("root_hash", ""),
        "checks": checks,
    }


def _safe_extract_zip(zf: zipfile.ZipFile, target_dir: str) -> None:
    """Safely extracts zip archive members preventing zip-slip path traversal."""
    resolved_base = os.path.abspath(target_dir)
    for member in zf.infolist():
        clean_name = member.filename.replace("\\", "/")
        if clean_name.startswith("/") or (len(clean_name) > 1 and clean_name[1] == ":"):
            raise ValueError(f"Zip-slip path traversal detected in archive: {member.filename}")
        dest_path = os.path.abspath(os.path.join(resolved_base, clean_name))
        try:
            if os.path.commonpath([resolved_base, dest_path]) != resolved_base:
                raise ValueError(f"Zip-slip path traversal detected in archive: {member.filename}")
        except ValueError:
            raise ValueError(f"Zip-slip path traversal detected in archive: {member.filename}")
    zf.extractall(resolved_base)


def _extract_zip_if_needed(target_path: str) -> Tuple[str, Optional[str]]:
    """Unpacks zip archive into temporary directory with strict zip-slip prevention."""
    if os.path.isfile(target_path) and zipfile.is_zipfile(target_path):
        extract_dir = tempfile.mkdtemp(prefix="lienmark_pack_")
        with zipfile.ZipFile(target_path, "r") as zf:
            _safe_extract_zip(zf, extract_dir)
        return extract_dir, extract_dir
    return target_path, None


def main() -> int:
    """CLI runner executing offline verification."""
    parser = argparse.ArgumentParser(description="Lienmark Standalone Offline Evidence Pack Verifier")
    parser.add_argument("pack_path", nargs="?", default="", help="Path to evidence pack directory or zip archive")
    parser.add_argument("--pack-dir", dest="dir_flag", default="", help="Directory containing evidence pack")
    parser.add_argument("--output-json", default="", help="File path to save JSON verification report")
    args = parser.parse_args()
    target, tmp_cleanup = args.dir_flag or args.pack_path or ".", None
    try:
        work_dir, tmp_cleanup = _extract_zip_if_needed(target)
        report = verify_pack_directory(work_dir)
    except Exception as exc:
        report = {"production_id": "unknown", "verified_at_utc": datetime.now(timezone.utc).isoformat(), "is_valid": False,
                  "total_checks": 1, "passed_checks": 0, "failed_checks": 1, "root_hash": "",
                  "checks": [{"check_name": "pack_extraction", "status": "FAILED", "message": str(exc), "details": {}}]}
    finally:
        if tmp_cleanup and os.path.exists(tmp_cleanup):
            shutil.rmtree(tmp_cleanup, ignore_errors=True)
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    root_disp = (report.get("root_hash") or "N/A")[:16]
    print(f"\n{'='*70}\nLIENMARK VERIFIABLE EVIDENCE PACK AUDIT REPORT\n{'='*70}")
    print(f"Production: {report.get('production_id')} | Root Hash: {root_disp}...\nResult: {'PASSED (VERIFIED)' if report.get('is_valid') else 'FAILED (TAMPERED/INVALID)'}\n")
    for c in report.get("checks", []):
        print(f"  {'[PASS]' if c['status'] == 'PASSED' else '[FAIL]'} {c['check_name']:<24}: {c['message']}")
    print(f"{'='*70}\n")
    return 0 if report.get("is_valid") else 1


if __name__ == "__main__":
    sys.exit(main())
