"""
scripts/ledger_fixtures.py

Demo generators, synthetic benchmark data, and report formatting for ledger integrity.
Sprint 1.3 / Security Specification SEC-SPEC-03-AUDIT-CRYPTO.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
from scripts.ledger_verification_core import GENESIS_PARENT_HASH, VerificationResult


def _append_counsel_and_seal(ledger: Any, tenant_id: str, production_id: str) -> None:
    """Appends counsel decisions and report sealed events to demo ledger."""
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="counsel_sjenkins_001",
        action_type="counsel_decision_recorded",
        payload={
            "action": "re_attest", "decision_id": "dec_v8_poster_noir_7a8b1c",
            "lineage_key": "poster_noir", "new_state": "RE_ATTESTED", "new_status": "APPROVED",
            "rationale": "Artwork verified in public domain via LOC registration records.",
            "reviewer": "Sarah Jenkins, Esq.",
        },
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="counsel_sjenkins_001",
        action_type="counsel_decision_recorded",
        payload={
            "action": "exception", "decision_id": "dec_v8_music_cue_8b9c2d",
            "lineage_key": "music_cue", "new_state": "EXCEPTION", "new_status": "REJECTED",
            "rationale": "Active ownership conflict identified; designated exception.",
            "reviewer": "Sarah Jenkins, Esq.",
        },
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_report_sealer",
        action_type="report_sealed",
        payload={
            "carried_forward_count": 10, "exception_count": 1, "form_eo_certificate": "FORM-EO-2026-PROD-01",
            "re_attested_count": 1, "status": "VERIFIED_TAMPER_FREE", "total_claims_evaluated": 12,
        },
    )


def build_demo_ledger(
    production_id: str = "prod_broadway_01",
    tenant_id: str = "org_studio_alpha",
) -> List[Dict[str, Any]]:
    """Builds a realistic 6-event cryptographic clearance chain matching Lienmark demo."""
    from backend.storage.ledger import CryptographicLedger

    ledger = CryptographicLedger()
    ledger.initialize_production_ledger(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_intake_script_hasher"
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_research_router",
        action_type="investigation_dispatched",
        payload={
            "target_claims": ["poster_noir_detective_magazine", "music_cue_midnight_serenade"],
            "search_provider": "Parallel Search API v1",
            "stale_reasons": ["prominence_shift", "adverse_claim_flagged"],
        },
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_research_parallel_adapter",
        action_type="evidence_retrieved",
        payload={
            "citations": [
                {"claim_id": "poster_noir", "provider_call_id": "prl_loc_882910", "status": "PUBLIC_DOMAIN"},
                {"claim_id": "music_cue", "provider_call_id": "prl_vanguard_882911", "status": "CONFLICT"},
            ]
        },
    )
    _append_counsel_and_seal(ledger, tenant_id, production_id)
    return [e.model_dump() for e in ledger.get_events(production_id=production_id, limit=100)]


def build_secondary_demo_ledger(
    production_id: str = "prod_noir_film_v8",
    tenant_id: str = "org_studio_alpha",
) -> List[Dict[str, Any]]:
    """Builds a 4-event secondary chain to demonstrate multi-production auditing."""
    from backend.storage.ledger import CryptographicLedger

    ledger = CryptographicLedger()
    ledger.initialize_production_ledger(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_intake_002"
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_research_002",
        action_type="investigation_dispatched",
        payload={"title": "Shadows Over Broadway", "cue_sheet_id": "cs_noir_001", "total_claims": 8},
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_research_002",
        action_type="evidence_retrieved",
        payload={"serial_number": "78912345", "finding": "LITIGATION_CLEAR"},
    )
    ledger.append_event(
        tenant_id=tenant_id, production_id=production_id, actor_id="agent_report_002",
        action_type="report_sealed",
        payload={"status": "APPROVED", "certificate_url": "gs://lienmark-certs/noir_v8_sealed.pdf"},
    )
    return [e.model_dump() for e in ledger.get_events(production_id=production_id, limit=100)]


def generate_synthetic_chain(
    count: int = 1000,
    production_id: str = "prod_benchmark_1000",
    tenant_id: str = "org_studio_alpha",
) -> List[Dict[str, Any]]:
    """Generates synthetic audit events linked from genesis for latency benchmarking."""
    events: List[Dict[str, Any]] = []
    prev_hash = GENESIS_PARENT_HASH
    fixed_ts = "2026-09-07T08:00:00.000Z"

    for i in range(1, count + 1):
        p_load = {
            "benchmark_index": i, "claim_id": f"claim_bench_{i:04d}",
            "action": "re_attest", "status": "APPROVED", "statutory_reference": "17 U.S.C. § 107",
        }
        p_digest = hashlib.sha256(
            json.dumps(p_load, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()

        e_hash = hashlib.sha256(f"{prev_hash}{p_digest}{fixed_ts}{i}".encode("utf-8")).hexdigest()

        events.append({
            "event_id": f"evt_bench_{i:05d}", "tenant_id": tenant_id, "production_id": production_id,
            "sequence_number": i, "actor_id": "counsel_sjenkins_001", "action_type": "counsel_re_attestation",
            "payload": p_load, "payload_digest": p_digest, "timestamp_utc": fixed_ts,
            "previous_event_hash": prev_hash, "entry_hash": e_hash,
        })
        prev_hash = e_hash

    return events


def render_summary_table(results: List[VerificationResult]) -> str:
    """Renders a structured ASCII table showing audit results per production."""
    headers = ["Production ID", "Total Events", "Valid Links", "Tampered Links", "Elapsed Time (ms)", "Status"]
    col_widths = [18, 14, 13, 16, 19, 24]
    for r in results:
        col_widths[0] = max(col_widths[0], len(r.production_id) + 2)

    top = "┌" + "┬".join("─" * w for w in col_widths) + "┐"
    header_line = "│" + "│".join(f" {h:<{w-2}} " for h, w in zip(headers, col_widths)) + "│"
    mid = "├" + "┼".join("─" * w for w in col_widths) + "┤"
    rows = []
    for r in results:
        status_str = "[PASS] VERIFIED INTACT" if r.is_valid else "[FAIL] TAMPER DETECTED"
        elapsed_str = f"{r.elapsed_ms:.2f} ms"
        rows.append(
            f"│ {r.production_id:<{col_widths[0]-2}} "
            f"│ {r.total_events:>{col_widths[1]-2}} "
            f"│ {r.valid_links:>{col_widths[2]-2}} "
            f"│ {r.tampered_links:>{col_widths[3]-2}} "
            f"│ {elapsed_str:>{col_widths[4]-2}} "
            f"│ {status_str:<{col_widths[5]-2}} │"
        )
    bottom = "└" + "┴".join("─" * w for w in col_widths) + "┘"
    return "\n".join([top, header_line, mid] + rows + [bottom])


def _parse_dict_ledger(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Helper to parse dictionary-formatted ledger contents."""
    for key in ("events", "audit_events"):
        if key in data and isinstance(data[key], list):
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for item in data[key]:
                if isinstance(item, dict):
                    grouped.setdefault(item.get("production_id", "prod_unknown"), []).append(item)
            return grouped
    return {k: v for k, v in data.items() if isinstance(v, list)}


def load_events_from_file(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parses a ledger file (JSON or JSONL) into a dictionary mapping production_id -> events."""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"Ledger file not found: {file_path}")
    content = p.read_text(encoding="utf-8").strip()
    if not content:
        return {}

    try:
        data = json.loads(content)
        if isinstance(data, list):
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for item in data:
                if isinstance(item, dict):
                    grouped.setdefault(item.get("production_id", "prod_unknown"), []).append(item)
            return grouped
        if isinstance(data, dict):
            dict_res = _parse_dict_ledger(data)
            if dict_res:
                return dict_res
    except json.JSONDecodeError:
        pass

    grouped = {}
    for line in content.splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                grouped.setdefault(item.get("production_id", "prod_unknown"), []).append(item)
    return grouped
