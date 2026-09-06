"""
API Endpoint Integration Tests for Lienmark
Tests the FastAPI endpoints and judge-facing reviewer dashboard.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app, counsel_checkpoint_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_counsel_state():
    yield
    counsel_checkpoint_manager.reset()


def test_health_endpoints():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "Google AntiGravity" in data["provenance"]
    assert data["track"] == "Parallel Track ($15,000 Prize Pool)"

    res_api = client.get("/api/health")
    assert res_api.status_code == 200


def test_fixtures_endpoint():
    res = client.get("/api/fixtures")
    assert res.status_code == 200
    data = res.json()
    assert data["v7_version"]["version_id"] == "v7"
    assert data["v8_version"]["version_id"] == "v8"
    assert len(data["v7_claims"]) == 12


def test_drift_compare_and_review_flow():
    # 1. Run Drift Comparison
    res = client.post("/api/drift/compare")
    assert res.status_code == 200
    data = res.json()
    assert data["total_claims"] == 12
    assert data["carried_forward_count"] == 10
    assert data["reopened_count"] == 2
    assert len(data["claims"]) == 12
    assert len(data["execution_traces"]) >= 4

    # 2. Record Counsel Re-attestation for Item 11 (poster)
    poster_payload = {
        "decision_id": "dec_poster_noir",
        "stable_lineage_key": "poster_noir_detective_magazine",
        "version_id": "v8",
        "new_status": "approved",
        "counsel_rationale": "Artwork in public domain under LOC renewal catalog.",
        "reviewer_name": "Sarah Jenkins, Esq.",
    }
    attest_res = client.post("/api/review/attest", json=poster_payload)
    assert attest_res.status_code == 200
    assert attest_res.json()["status"] == "recorded"

    # 3. Record Counsel Exception for Item 12 (music)
    music_payload = {
        "decision_id": "dec_music_midnight",
        "stable_lineage_key": "music_cue_midnight_serenade",
        "version_id": "v8",
        "new_status": "rejected",
        "counsel_rationale": "Vanguard Media conflict; cue must be removed.",
        "reviewer_name": "Sarah Jenkins, Esq.",
    }
    client.post("/api/review/attest", json=music_payload)

    # 4. Fetch Exceptions Schedule
    sched_res = client.get("/api/reports/exceptions")
    assert sched_res.status_code == 200
    schedule = sched_res.json()
    assert schedule["total_claims"] == 12
    assert schedule["carried_forward_count"] == 10
    assert schedule["re_attested_count"] == 1
    assert schedule["unresolved_exception_count"] == 1


def test_dashboard_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Lienmark" in res.text
    assert "Parallel Track" in res.text
    assert "Form E&O-2026" in res.text
