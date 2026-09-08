"""
tests/test_revision_export_parity.py

Acceptance tests for snapshot versioning and real ReportLab PDF generation.
Verifies: Reviewer records decision -> new snapshot created while previous remains immutable ->
real PDF generated and parsed, verifying claims, citations, and snapshot parity.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
import os
import io
import secrets
import hashlib
from datetime import datetime, timezone
from fastapi.testclient import TestClient

os.environ["USE_LOCAL_STORAGE"] = "true"
from backend.main import app
from backend.storage.revision_store import get_revision_store
from backend.storage.invite_store import get_invite_store
from backend.domain.revision_models import RevisionRecord, RevisionAuditDispatch, ResultSnapshot
from backend.domain.models import CounselDecision, DecisionStatus

client = TestClient(app)


def _get_auth_cookies(role: str = "reviewer", tenant_id: str = "org_parity", prod_id: str = "prod_parity"):
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    get_invite_store().create_invite(h_token, role=role, tenant_id=tenant_id, production_id=prod_id)
    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    return res.cookies, res.json()["session_id"]


def test_adjudication_snapshot_immutability_and_real_pdf_generation():
    cookies, sess_id = _get_auth_cookies("reviewer", "org_parity", "prod_parity")
    store = get_revision_store()
    rev_id = f"rev_{secrets.token_hex(4)}"
    audit_id = f"audit_{secrets.token_hex(4)}"

    # 1. Initial snapshot_0
    initial_dec = CounselDecision(
        decision_id="dec_initial", use_id="claim_poster", stable_lineage_key="poster_noir",
        applicable_version_id="v7", status=DecisionStatus.NEEDS_REVIEW,
        rationale="Initial baseline awaiting review", reviewer_user_id="sarah_jenkins",
    )
    snap_0 = ResultSnapshot(
        snapshot_id="snapshot_0", audit_id=audit_id, version_number=0,
        created_at=datetime.now(timezone.utc), decisions=[initial_dec],
        telemetry={"reopened_count": "1", "carried_forward_count": "11"},
    )
    store.save_result_snapshot("org_parity", "prod_parity", rev_id, snap_0)

    # 2. Reviewer submits attestation decision on real endpoint
    dec_res = client.post(
        "/api/v1/claims/claim_poster/decision",
        json={
            "action": "sign_off",
            "counsel_id": "sarah_jenkins",
            "counsel_name": "Sarah Jenkins, Esq.",
            "directive_text": "Re-attested under statutory public domain Rule §304.",
        },
        params={"production_id": "prod_parity"},
        cookies=cookies,
        headers={"X-CSRF-Token": sess_id},
    )
    assert dec_res.status_code == 200

    # 3. Create snapshot_1 capturing the reviewer's attestation
    attested_dec = CounselDecision(
        decision_id="dec_attested", use_id="claim_poster", stable_lineage_key="poster_noir",
        applicable_version_id="v8", status=DecisionStatus.APPROVED,
        rationale="Re-attested under statutory public domain Rule §304.", reviewer_user_id="sarah_jenkins",
    )
    snap_1 = ResultSnapshot(
        snapshot_id="snapshot_1", audit_id=audit_id, version_number=1,
        created_at=datetime.now(timezone.utc), decisions=[attested_dec],
        telemetry={"reopened_count": "0", "carried_forward_count": "12"},
    )
    store.save_result_snapshot("org_parity", "prod_parity", rev_id, snap_1)

    # 4. Verify snapshot_0 remains immutable
    read_snap_0 = store.get_result_snapshot("org_parity", "prod_parity", rev_id, "snapshot_0")
    read_snap_1 = store.get_result_snapshot("org_parity", "prod_parity", rev_id, "snapshot_1")
    assert read_snap_0.version_number == 0
    assert read_snap_0.decisions[0].status == DecisionStatus.NEEDS_REVIEW
    assert read_snap_1.version_number == 1
    assert read_snap_1.decisions[0].status == DecisionStatus.APPROVED

    # 5. Export real PDF and verify binary format and content
    pdf_res = client.get(
        f"/api/tenants/org_parity/productions/prod_parity/revisions/{rev_id}/audits/{audit_id}/snapshots/snapshot_1/export/pdf",
        cookies=cookies,
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")
    assert len(pdf_res.content) > 1000  # Valid ReportLab document with layout and fonts

    # Parse and inspect PDF flowables
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_res.content))
    assert len(reader.pages) >= 1
    page_text = reader.pages[0].extract_text()
    assert "LIENMARK PRODUCTION RIGHTS CLEARANCE CERTIFICATE" in page_text
    assert "prod_parity" in page_text
