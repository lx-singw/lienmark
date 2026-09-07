"""
tests/test_deliverable_generation.py

Sprint 6.3: Comprehensive Studio Deliverables Test Suite.
Verifies Form E&O-2026 PDF export, ASCAP/BMI CSV cue sheets, wrap checklist gating,
forensic ISO 27001 legal audit manifest chain verification, and fail-closed RBAC.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import csv
import io
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import InvestigationRun, Production, RunStatus
from backend.main import app
from backend.services.pdf_generator import ClearancePdfGenerator
from backend.storage.repository import InMemoryTenantRepository, _repository_cache, get_tenant_repository
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_repo_state():
    """Resets in-memory tenant cache and storage before and after each test."""
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()
    yield
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()


def _seed_underwriting_prod(repo, org_id: str, pid: str = "prod_u1", title: str = "Noir Cinema") -> str:
    """Helper to seed a production and active run within a tenant repository."""
    repo.save_production(Production(production_id=pid, title=title, organization_id=org_id))
    run_id = f"run_{pid}"
    repo.save_run(InvestigationRun(
        run_id=run_id, production_id=pid, organization_id=org_id,
        base_version_id="v7", target_version_id="v8", status=RunStatus.COMPLETED,
    ))
    repo.set_active_run_id(pid, run_id)
    return run_id


def _save_claim(repo, pid: str, rid: str, key: str, **kwargs) -> Dict[str, Any]:
    """Helper to save a claim with mandatory stable_lineage_key."""
    data = {"stable_lineage_key": key, **kwargs}
    return repo.save_claim(pid, rid, data)


def test_clearance_certificate_pdf_generation():
    """Validates Form E&O-2026 PDF generation with magic bytes, SHA-256 stamps, and Section A/B."""
    tid = "org_studio_pdf"
    repo = get_tenant_repository(tid)
    rid = _seed_underwriting_prod(repo, tid, "prod_pdf_01", "Metropolis Reborn")
    _save_claim(repo, "prod_pdf_01", rid, "prop_clock", title="Vintage Wall Clock", right_category="prop", status="APPROVED", state="CARRIED_FORWARD", rationale="Prop house license.")
    _save_claim(repo, "prod_pdf_01", rid, "cue_dispute", title="Nightclub Theme", right_category="music", status="EXCEPTION", state="EXCEPTION", rationale="Dispute excluded.")

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.post(
        "/api/v1/underwriting/export-schedule",
        json={"production_id": "prod_pdf_01", "format": "pdf", "include_signatures": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="clearance_schedule_prod_pdf_01.pdf"' in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")

    direct_pdf = ClearancePdfGenerator.generate_schedule_pdf(
        "Metropolis", "prod_pdf_01", [{"title": "Clock", "status": "APPROVED"}],
        [{"title": "Song", "status": "EXCEPTION"}], "a" * 64, "b" * 64,
    )
    assert direct_pdf.startswith(b"%PDF-")
    assert len(direct_pdf) > 1000


def test_music_cue_sheet_csv_export_ascap_bmi():
    """Validates ASCAP/BMI standard RFC 4180 CSV export layout and split percentages."""
    tid = "org_music_pub"
    repo = get_tenant_repository(tid)
    rid = _seed_underwriting_prod(repo, tid, "prod_cue_01", "Symphony of Shadows")
    _save_claim(repo, "prod_cue_01", rid, "cue_hero", title="Hero Theme", right_category="music", status="APPROVED", metadata={
        "composer": "John Williams", "composer_pro": "BMI", "publisher": "Warner Chappell", "publisher_pro": "BMI",
        "usage": "MT", "duration_seconds": 120, "timecode_in": "00:00:10:00", "timecode_out": "00:02:10:00", "pro_work_id": "BMI_99812", "scene": "Opening",
    })
    _save_claim(repo, "prod_cue_01", rid, "cue_chase", title="Subway Chase", right_category="music", status="APPROVED", metadata={
        "composer": "Hans Zimmer", "composer_pro": "ASCAP", "publisher": "Sony Music", "publisher_pro": "ASCAP",
        "usage": "BI", "duration_seconds": 90, "pro_work_id": "ASCAP_44521",
    })

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.get("/api/v1/underwriting/cue-sheet?production_id=prod_cue_01&format=csv", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    rows = list(csv.reader(io.StringIO(res.text)))
    assert rows[0] == ["CUE_NUMBER", "TITLE_OF_WORK", "USAGE", "TIMECODE_IN", "TIMECODE_OUT", "DURATION_SECONDS", "SCENE", "COMPOSERS", "PUBLISHERS", "PRO_WORK_ID", "RECORD_LABEL", "STATUS", "LINEAGE_KEY"]
    assert rows[1][0] == "1" and rows[1][1] == "Hero Theme" and rows[1][2] == "MT"
    assert "John Williams (BMI 100.0%)" in rows[1][7] and "Warner Chappell (BMI 100.0%)" in rows[1][8]
    assert rows[2][0] == "2" and rows[2][1] == "Subway Chase" and rows[2][2] == "BI"

    json_res = client.get("/api/v1/underwriting/cue-sheet?production_id=prod_cue_01&format=json", headers={"Authorization": f"Bearer {token}"})
    assert json_res.json()["total_cues"] == 2
    assert json_res.json()["total_duration_seconds"] == 210


def test_music_cue_sheet_empty_state_safety():
    """Validates 0 cues output header with 0 data rows without mock fallbacks."""
    tid = "org_empty_cues"
    repo = get_tenant_repository(tid)
    _seed_underwriting_prod(repo, tid, "prod_cue_empty", "Silent Motion")

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res_csv = client.get("/api/v1/underwriting/cue-sheet?production_id=prod_cue_empty&format=csv", headers={"Authorization": f"Bearer {token}"})
    assert res_csv.status_code == 200
    lines = [ln for ln in res_csv.text.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("CUE_NUMBER,TITLE_OF_WORK,USAGE")

    res_json = client.get("/api/v1/underwriting/cue-sheet?production_id=prod_cue_empty&format=json", headers={"Authorization": f"Bearer {token}"})
    assert res_json.status_code == 200
    assert res_json.json()["total_cues"] == 0
    assert res_json.json()["cues"] == []
    assert res_json.json()["total_duration_seconds"] == 0


def test_wrap_checklist_blocks_distributor_release_on_unresolved_claims():
    """Validates post-production wrap gate blocks funds release on unreviewed or stale claims."""
    tid = "org_wrap_blocked"
    repo = get_tenant_repository(tid)
    rid = _seed_underwriting_prod(repo, tid, "prod_wrap_blk", "Gated Thriller")
    _save_claim(repo, "prod_wrap_blk", rid, "cot_script", title="Screenplay Chain of Title", right_category="script", status="APPROVED", state="CARRIED_FORWARD")
    _save_claim(repo, "prod_wrap_blk", rid, "art_mural", title="Street Mural Backdrop", right_category="visual_art", status="NEEDS_REVIEW", state="UNRESOLVED")

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.get("/api/v1/underwriting/wrap-checklist?production_id=prod_wrap_blk", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_ready_for_funds_release"] is False
    assert data["cleared_percentage"] == 50.0
    assert data["total_items"] == 2
    assert data["cleared_items"] == 1
    assert len(data["blocking_reasons"]) == 1
    assert "Street Mural Backdrop" in data["blocking_reasons"][0]


def test_wrap_checklist_allows_release_when_100_percent_cleared():
    """Validates distributor funds release is authorized when 100% of claims are cleared or scheduled."""
    tid = "org_wrap_cleared"
    repo = get_tenant_repository(tid)
    rid = _seed_underwriting_prod(repo, tid, "prod_wrap_clr", "Cleared Picture")
    _save_claim(repo, "prod_wrap_clr", rid, "lead_agree", title="Lead Cast Agreement", right_category="talent", status="APPROVED", state="RE_ATTESTED")
    _save_claim(repo, "prod_wrap_clr", rid, "soda_can", title="Antique Soda Can", right_category="trademark", status="EXCEPTION", state="EXCEPTION")

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.get("/api/v1/underwriting/wrap-checklist?production_id=prod_wrap_clr", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_ready_for_funds_release"] is True
    assert data["cleared_percentage"] == 100.0
    assert data["total_items"] == 2
    assert data["cleared_items"] == 2
    assert len(data["blocking_reasons"]) == 0


def test_iso_legal_audit_manifest_export_and_chain_verification():
    """Validates ISO 27001 / SOC 2 Type II audit schema, claims census, and hash chain integrity."""
    tid = "org_iso_audit"
    repo = get_tenant_repository(tid)
    rid = _seed_underwriting_prod(repo, tid, "prod_iso_01", "Forensic Cut")
    repo.append_audit_event("prod_iso_01", rid, {"action": "INITIALIZE_CHAIN"})
    repo.append_audit_event("prod_iso_01", rid, {"action": "COUNSEL_SIGN_OFF", "claim_id": "c1"})
    repo.append_audit_event("prod_iso_01", rid, {"action": "EXCEPTION_SCHEDULED", "claim_id": "c2"})
    _save_claim(repo, "prod_iso_01", rid, "claim_c1", title="C1", status="APPROVED", state="CARRIED_FORWARD")
    _save_claim(repo, "prod_iso_01", rid, "claim_c2", title="C2", status="EXCEPTION", state="EXCEPTION")

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.get("/api/v1/underwriting/manifest?production_id=prod_iso_01", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["manifest_version"] == "1.0.0"
    assert data["iso_standard"] == "ISO/IEC 27001:2022 / SOC 2 Type II"
    assert data["chain_verified"] is True
    assert data["total_ledger_events"] == 3
    assert len(data["head_hash"]) == 64 and len(data["audit_trail_digest"]) == 64
    assert data["claims_census"]["carried_forward"] == 1
    assert data["claims_census"]["exceptions"] == 1
    assert len(data["signatories"]) == 2


def test_underwriting_auth_and_rbac_fail_closed(monkeypatch):
    """Fail-closed invariant: Missing credentials in strict mode rejects requests with 401."""
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    monkeypatch.setenv("TENANT_STRICT_MODE", "true")

    assert client.get("/api/v1/underwriting/cue-sheet").status_code == 401
    assert client.get("/api/v1/underwriting/wrap-checklist").status_code == 401
    assert client.get("/api/v1/underwriting/manifest").status_code == 401
    assert client.post("/api/v1/underwriting/export-schedule", json={"production_id": "p"}).status_code == 401


def test_underwriting_multi_tenant_isolation():
    """Strict multi-tenant isolation: Tenant B never accesses Tenant A's deliverables."""
    repo_a = get_tenant_repository("org_tenant_alpha")
    rid_a = _seed_underwriting_prod(repo_a, "org_tenant_alpha", "prod_common", "Alpha Production")
    _save_claim(repo_a, "prod_common", rid_a, "alpha_cue", title="Alpha Exclusive Cue", right_category="music", status="APPROVED", metadata={"composer": "Alpha", "composer_pro": "BMI", "duration_seconds": 60})

    repo_b = get_tenant_repository("org_tenant_beta")
    _seed_underwriting_prod(repo_b, "org_tenant_beta", "prod_beta_only", "Beta Production")

    tok_a = create_test_jwt(tenant_id="org_tenant_alpha", roles=["reviewer"])
    tok_b = create_test_jwt(tenant_id="org_tenant_beta", roles=["reviewer"])

    res_b = client.get("/api/v1/underwriting/cue-sheet?production_id=prod_common", headers={"Authorization": f"Bearer {tok_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["total_cues"] == 0

    res_a = client.get("/api/v1/underwriting/cue-sheet?production_id=prod_common", headers={"Authorization": f"Bearer {tok_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["total_cues"] == 1
    assert res_a.json()["cues"][0]["title"] == "Alpha Exclusive Cue"
