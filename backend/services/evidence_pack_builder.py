"""
backend/services/evidence_pack_builder.py

Builds self-contained, tamper-evident Verifiable Evidence Packs.
Bundles policy configurations, decision packages, cryptographic ledger chains,
and human-readable clearance summaries with SHA-256 manifest anchoring.
Sprint 5.4: Verifiable Evidence Pack & Standalone Offline Verifier.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services.evidence_pack_types import (
    EvidenceCategory,
    EvidencePackFileEntry,
    EvidencePackManifest,
    compute_manifest_root_hash,
)


def _hash_bytes(data: bytes) -> Tuple[int, str]:
    """Returns byte size and hex SHA-256 hash."""
    return len(data), hashlib.sha256(data).hexdigest()


def _write_json_artifact(file_path: str, payload: Any, cat: EvidenceCategory, files: Dict[str, EvidencePackFileEntry], rel: str) -> None:
    """Serializes data to formatted JSON and records manifest file entry."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
    with open(file_path, "wb") as f:
        f.write(raw)
    sz, digest = _hash_bytes(raw)
    files[rel] = EvidencePackFileEntry(path=rel, size_bytes=sz, sha256=digest, category=cat)


def _write_text_artifact(file_path: str, text: str, cat: EvidenceCategory, files: Dict[str, EvidencePackFileEntry], rel: str) -> None:
    """Writes text payload and records manifest file entry."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    raw = text.encode("utf-8")
    with open(file_path, "wb") as f:
        f.write(raw)
    sz, digest = _hash_bytes(raw)
    files[rel] = EvidencePackFileEntry(path=rel, size_bytes=sz, sha256=digest, category=cat)


def _format_summary_markdown(prod_id: str, org_id: str, pkgs: List[Any], events: List[Any], pol: Dict[str, Any]) -> str:
    """Constructs human-readable clearance census and verification guide."""
    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# Clearance & Chain of Custody Evidence Pack: {prod_id}",
        f"**Organization**: `{org_id}` | **Generated UTC**: `{ts}`\n",
        "## 1. Governing Policy",
        f"- **Policy Version**: `{pol.get('version_id', 'v1')}`",
        f"- **Policy Digest**: `{pol.get('policy_digest', 'N/A')}`\n",
        "## 2. Decision Package Clearance Census",
        f"- **Total Bundled Packages**: {len(pkgs)}",
        f"- **Cryptographic Ledger Audit Events**: {len(events)}\n",
        "| Package ID | Claim ID | Status | Reviewer 1 | Reviewer 2 | Canonical Digest |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for p in pkgs:
        d = p.model_dump() if hasattr(p, "model_dump") else dict(p)
        r1 = (d.get("primary_approval") or {}).get("reviewer_id", "Pending")
        r2 = (d.get("secondary_approval") or {}).get("reviewer_id", "Pending")
        dig = str(d.get("canonical_digest", ""))[:12] + "..."
        lines.append(f"| `{d.get('package_id')}` | `{d.get('claim_id')}` | `{d.get('status')}` | `{r1}` | `{r2}` | `{dig}` |")
    lines.extend(["\n## 3. Standalone Verification", "Verify offline via CLI:", "```bash", f"python scripts/verify_evidence_pack.py --pack-dir evidence_pack_{prod_id}", "```\n"])
    return "\n".join(lines)


def _collect_packages(prod_id: str, coord: Optional[Any], explicit: Optional[List[Any]]) -> List[Any]:
    """Collects target decision packages for the specified production."""
    if explicit is not None:
        return explicit
    if not coord:
        return []
    res: List[Any] = []
    pool = getattr(coord, "_packages", {})
    for p in pool.values():
        p_prod = getattr(p, "production_id", None) or (p.get("production_id") if isinstance(p, dict) else None)
        if not p_prod or p_prod == prod_id or p_prod == "prod_default":
            res.append(p)
    return res


def _collect_ledger_events(prod_id: str, ledger: Optional[Any]) -> List[Dict[str, Any]]:
    """Retrieves and serializes audit event lineage for target production."""
    if not ledger:
        return []
    events = ledger.get_events(prod_id, start_seq=1, limit=10000) if hasattr(ledger, "get_events") else []
    if not events and hasattr(ledger, "_chains"):
        events = getattr(ledger, "_chains", {}).get(prod_id, [])
    serialized: List[Dict[str, Any]] = []
    for evt in events:
        if hasattr(evt, "model_dump"):
            serialized.append(evt.model_dump())
        elif isinstance(evt, dict):
            serialized.append(evt)
    return serialized


def _collect_policy(org_id: str, store: Optional[Any]) -> Dict[str, Any]:
    """Retrieves active studio policy payload from policy store."""
    if not store:
        return {"version_id": "v1", "policy_digest": "genesis_policy", "policy_config": {}}
    rec = store.get_active_policy(org_id) if hasattr(store, "get_active_policy") else None
    if rec:
        return rec.model_dump() if hasattr(rec, "model_dump") else dict(rec)
    return {"version_id": "v1", "policy_digest": "default_policy", "policy_config": {}}


def _zip_directory(source_dir: str, zip_path: str) -> None:
    """Packs directory into standalone zip archive."""
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full = os.path.join(root, file)
                rel = os.path.relpath(full, source_dir)
                zf.write(full, rel)


def _write_package_entries(pack_dir: str, pkgs: List[Any], files_map: Dict[str, EvidencePackFileEntry]) -> None:
    """Serializes decision packages to individual evidence artifacts."""
    for p in pkgs:
        d = p.model_dump() if hasattr(p, "model_dump") else dict(p)
        pkg_id = d.get("package_id", f"pkg_{hashlib.sha256(str(d).encode()).hexdigest()[:8]}")
        rel = f"packages/{pkg_id}.json"
        _write_json_artifact(os.path.join(pack_dir, rel), d, EvidenceCategory.PACKAGE, files_map, rel)


def build_evidence_pack(
    production_id: str, org_id: str, output_base_dir: str,
    policy_store: Optional[Any] = None, coordinator: Optional[Any] = None,
    ledger: Optional[Any] = None, packages: Optional[List[Any]] = None,
    export_zip: bool = False,
) -> Tuple[str, EvidencePackManifest]:
    """Assembles and signs a complete Verifiable Evidence Pack for a production."""
    pack_name = f"evidence_pack_{production_id}"
    pack_dir = os.path.join(output_base_dir, pack_name)
    os.makedirs(pack_dir, exist_ok=True)
    files_map: Dict[str, EvidencePackFileEntry] = {}

    pol_data = _collect_policy(org_id, policy_store)
    _write_json_artifact(os.path.join(pack_dir, "policies", "active_policy.json"), pol_data, EvidenceCategory.POLICY, files_map, "policies/active_policy.json")

    pkgs = _collect_packages(production_id, coordinator, packages)
    _write_package_entries(pack_dir, pkgs, files_map)

    events = _collect_ledger_events(production_id, ledger)
    _write_json_artifact(os.path.join(pack_dir, "ledger", "ledger_events.json"), events, EvidenceCategory.LEDGER, files_map, "ledger/ledger_events.json")

    summary_md = _format_summary_markdown(production_id, org_id, pkgs, events, pol_data)
    _write_text_artifact(os.path.join(pack_dir, "summary.md"), summary_md, EvidenceCategory.SUMMARY, files_map, "summary.md")

    root_hash = compute_manifest_root_hash(files_map)
    manifest = EvidencePackManifest(
        production_id=production_id, org_id=org_id, root_hash=root_hash,
        file_count=len(files_map), files=files_map,
    )
    with open(os.path.join(pack_dir, "manifest.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest.model_dump(), indent=2, sort_keys=True))

    final_path = pack_dir
    if export_zip:
        zip_path = os.path.join(output_base_dir, f"{pack_name}.zip")
        _zip_directory(pack_dir, zip_path)
        final_path = zip_path

    return final_path, manifest
