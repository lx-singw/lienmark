"""
tests/test_offline_verifier_cli.py

Exhaustive tests for the Standalone Offline Verifier (scripts/verify_evidence_pack.py).
Tests strict stdlib compliance, defensive zip-slip prevention, CLI flags,
exit codes, and code structure constraints (<=250 lines file, <=40 lines/func).
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import ast
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import pytest

from scripts.verify_evidence_pack import (
    _canonical_digest,
    _canonical_json,
    _safe_extract_zip,
    verify_pack_directory,
)


def _create_minimal_valid_pack(base_dir: Path) -> Path:
    """Constructs a minimal valid evidence pack directory."""
    pack_dir = base_dir / "evidence_pack_dummy"
    pack_dir.mkdir(parents=True, exist_ok=True)
    pol_dir = pack_dir / "policies"
    pol_dir.mkdir(parents=True, exist_ok=True)
    led_dir = pack_dir / "ledger"
    led_dir.mkdir(parents=True, exist_ok=True)

    pol_file = pol_dir / "active_policy.json"
    pol_data = {"version_id": "v1.0", "policy_digest": "genesis_policy", "policy_config": {}}
    pol_file.write_text(json.dumps(pol_data, indent=2), encoding="utf-8")

    led_file = led_dir / "ledger_events.json"
    led_file.write_text("[]", encoding="utf-8")

    sum_file = pack_dir / "summary.md"
    sum_file.write_text("# Clearance Summary\nAll cleared.", encoding="utf-8")

    files_map = {}
    for rel in ["ledger/ledger_events.json", "policies/active_policy.json", "summary.md"]:
        fpath = pack_dir / rel
        data = fpath.read_bytes()
        files_map[rel] = {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    lines = [f"{p}:{files_map[p]['sha256']}" for p in sorted(files_map.keys())]
    root_hash = hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()
    manifest = {"production_id": "prod_dummy_01", "root_hash": root_hash, "file_count": len(files_map), "files": files_map}
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pack_dir


def test_strict_standard_library_compliance():
    """Verifies that verify_evidence_pack.py imports ONLY Python standard library modules."""
    script_path = Path("scripts/verify_evidence_pack.py")
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    stdlib_modules = set(sys.stdlib_module_names) | {"__future__", "typing", "argparse", "hashlib", "json", "os", "sys", "zipfile", "tempfile", "shutil"}
    forbidden = imported - stdlib_modules
    assert not forbidden, f"Forbidden non-stdlib imports found: {forbidden}"
    for disallowed in ["requests", "pydantic", "fastapi", "pytest", "aiohttp", "httpx"]:
        assert disallowed not in imported, f"Third-party library '{disallowed}' must not be imported!"


def test_file_and_function_length_limits():
    """Enforces AntiGravity constraints: file <= 250 lines, functions <= 40 lines."""
    script_path = Path("scripts/verify_evidence_pack.py")
    lines = script_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 250, f"File exceeds 250 lines: {len(lines)}"

    tree = ast.parse("\n".join(lines))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            span = node.end_lineno - node.lineno + 1
            assert span <= 40, f"Function '{node.name}' has {span} lines (> 40 lines limit)"


def test_defensive_zip_slip_prevention(tmp_path):
    """Verifies that archives attempting path traversal outside extraction target are blocked."""
    zip_path = tmp_path / "malicious_slip.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../escaped_root.txt", "MALICIOUS CONTENT")
        zf.writestr("legit.txt", "LEGIT CONTENT")

    extract_target = tmp_path / "extract_dest"
    extract_target.mkdir()

    with zipfile.ZipFile(zip_path, "r") as zf:
        with pytest.raises(ValueError, match="Zip-slip path traversal detected"):
            _safe_extract_zip(zf, str(extract_target))

    assert not (tmp_path / "escaped_root.txt").exists()


def test_cli_execution_with_flags_and_telemetry(tmp_path):
    """Tests CLI flag handling (--pack-dir, --output-json, positional) and report structure."""
    pack_dir = _create_minimal_valid_pack(tmp_path)
    cli_path = str(Path("scripts/verify_evidence_pack.py").resolve())
    out_json = tmp_path / "report.json"

    cmd = [sys.executable, cli_path, "--pack-dir", str(pack_dir), "--output-json", str(out_json)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "PASSED (VERIFIED)" in res.stdout
    assert out_json.is_file()

    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert report["is_valid"] is True
    assert report["failed_checks"] == 0
    assert report["passed_checks"] >= 4
    assert "production_id" in report


def test_cli_zip_input_and_tampered_exit_code(tmp_path):
    """Tests CLI handling of zip input and non-zero exit code on tampering."""
    pack_dir = _create_minimal_valid_pack(tmp_path)
    zip_path = tmp_path / "dummy_pack.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in pack_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(pack_dir))

    cli_path = str(Path("scripts/verify_evidence_pack.py").resolve())
    res_clean = subprocess.run([sys.executable, cli_path, str(zip_path)], capture_output=True, text=True)
    assert res_clean.returncode == 0
    assert "PASSED (VERIFIED)" in res_clean.stdout

    # Tamper with the pack dir and test failure exit code 1
    (pack_dir / "summary.md").write_text("TAMPERED")
    res_tamper = subprocess.run([sys.executable, cli_path, "--pack-dir", str(pack_dir)], capture_output=True, text=True)
    assert res_tamper.returncode == 1
    assert "FAILED (TAMPERED/INVALID)" in res_tamper.stdout


def test_cli_nonexistent_target_fails_gracefully(tmp_path):
    """Tests CLI behavior when a non-existent path is provided."""
    cli_path = str(Path("scripts/verify_evidence_pack.py").resolve())
    out_json = tmp_path / "missing_report.json"
    res = subprocess.run([sys.executable, cli_path, "--pack-dir", str(tmp_path / "does_not_exist"), "--output-json", str(out_json)], capture_output=True, text=True)
    assert res.returncode == 1
    assert out_json.is_file()
    rep = json.loads(out_json.read_text(encoding="utf-8"))
    assert rep["is_valid"] is False
