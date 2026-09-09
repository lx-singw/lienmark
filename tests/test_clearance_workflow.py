"""Mounted application acceptance tests; doubles exist only at provider HTTP boundary."""
import io
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

os.environ["BUDGET_STORE_MODE"] = "local_disk"
os.environ["USE_LOCAL_STORAGE"] = "true"

import httpx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.main import app
from backend.api.routes.auth_routes import sign_session_id
from backend.storage.session_store import get_session_store, SessionRecord
from backend.clearance.models import RevisionInput, digest
from backend.clearance.providers import Providers
from backend.clearance.service import submit
from backend.clearance.store import SQLiteStore, get_store, Conflict
from backend.clearance.worker import Worker

ROOT = "organizations/org_acceptance/productions/production_acceptance"
BASE = "/api/clearance/productions/production_acceptance"


def use(key, dependencies=None):
    return {"stable_lineage_key": key, "description": "Public work " + key, "asset_type": "music",
            "scene_or_timecode": "Scene " + key, "duration_or_prominence": "2 seconds background",
            "dependency_keys": dependencies or []}


@pytest.fixture
def harness(tmp_path, monkeypatch):
    store = SQLiteStore(tmp_path / "clearance.db")
    app.dependency_overrides[get_store] = lambda: store
    monkeypatch.setenv("CLEARANCE_LIVE_ENABLED", "true")
    monkeypatch.setenv("PARALLEL_API_KEY", "test-only")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    calls = []
    def transport(request):
        data = json.loads(request.content)
        calls.append((str(request.url), data))
        if request.url.host == "api.parallel.ai":
            return httpx.Response(200, json={"search_id": "search_" + uuid.uuid4().hex, "results": [{
                "title": "Rights catalogue", "url": "https://catalogue.example.test/record", "excerpts": ["Publisher catalogue attribution; a private license is still required."]}]})
        incoming = json.loads(data["contents"][0]["parts"][0]["text"])
        if "source_text" in incoming:
            result = {"uses": [use("extracted") ]}
        elif "objective" in data["generationConfig"]["responseSchema"]["properties"]:
            result = {"objective": "Verify asset attribution", "public_query": incoming["use"]["description"] + " rights ownership",
                "private_facts_needed": ["Private grant"], "stop_condition": "Attribution supported or private grant missing"}
        elif "assessment" in incoming:
            result = {"verdict": "needs_information", "explanation": "The attribution is supported; the private grant is still missing.",
                "cited_ids": [incoming["evidence"][0]["evidence_id"]], "missing_facts": ["Private grant"], "next_query": None}
        else:
            result = {"summary": "The catalogue supports attribution; confirm the private grant.",
                "cited_ids": [incoming["evidence"][0]["evidence_id"]], "missing_facts": ["Private grant"], "next_query": None}
        return httpx.Response(200, json={"responseId": "model_request", "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 70},
            "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}]})
    provider = Providers(httpx.Client(transport=httpx.MockTransport(transport)))
    worker = Worker(store, provider)
    def client(role="PRODUCER", production="production_acceptance"):
        sid = "test_" + uuid.uuid4().hex
        get_session_store().create_session(SessionRecord(sid, "test-" + role, "test@example.test", "Test " + role,
            role, "org_acceptance", production, time.time() + 600))
        c = TestClient(app)
        c.cookies.set("lienmark_session", sign_session_id(sid))
        c.headers["X-CSRF-Token"] = sid
        return c
    yield store, worker, calls, client
    app.dependency_overrides.pop(get_store, None)


def intake(client, worker, uses=None, **extra):
    payload = {"production_id": "production_acceptance", **extra}
    if "source_text" not in extra:
        payload["initial_uses"] = uses or [use("a"), use("b")]
    response = client.post("/api/clearance/revisions", json=payload, headers={"Idempotency-Key": uuid.uuid4().hex})
    assert response.status_code == 202, response.text
    job = response.json()
    worker.run(ROOT + "/live_jobs/" + job["audit_id"])
    return client.get(job["status_url"]).json()["snapshot"]


def sign(client, snapshot, index=0, action="sign_off"):
    claim = snapshot["claims"][index]
    return client.post(BASE + "/claims/" + claim["claim_id"] + "/decision", json={
        "action": action, "revision_id": snapshot["revision_id"], "expected_snapshot_id": snapshot["snapshot_id"],
        "rationale": "Test reviewer inspected the supporting evidence.",
        "evidence_ids": [e["evidence_id"] for e in claim["evidence_citations"]]})


def test_empty_production_never_returns_example_claims(harness):
    _, _, _, client = harness
    assert client().get(BASE).json()["claims"] == []
    response = client().post("/api/clearance/revisions", json={"production_id": "production_acceptance", "parent_revision_id": "v7",
        "expected_parent_snapshot_id": "snapshot_fake"}, headers={"Idempotency-Key": "unknown"})
    assert response.status_code == 409


def test_intake_signoff_revision_and_export_share_persisted_snapshot(harness):
    store, worker, calls, client = harness
    producer, reviewer = client(), client("REVIEWER")
    snapshot = intake(producer, worker)
    assert len(calls) == 8
    assert all(c["decision"] is None for c in snapshot["claims"])
    assert sign(producer, snapshot).status_code == 403
    old = snapshot
    response = sign(reviewer, snapshot)
    assert response.status_code == 200, response.text
    snapshot = response.json()
    assert snapshot["claims"][0]["decision"]["actor_id"] == "test-REVIEWER"
    assert sign(reviewer, old).status_code == 409
    snapshot = sign(reviewer, snapshot, 1).json()
    assert SQLiteStore(store.path).get(ROOT + "/live_control/head")["snapshot_path"].endswith(snapshot["snapshot_id"])
    calls.clear()
    result = producer.post("/api/clearance/revisions", json={"production_id": "production_acceptance",
        "parent_revision_id": snapshot["revision_id"], "expected_parent_snapshot_id": snapshot["snapshot_id"],
        "revised_uses": [{"stable_lineage_key": "a", "duration_or_prominence": "14 seconds foreground"}]}, headers={"Idempotency-Key": "revision-change"})
    assert result.status_code == 202, result.text
    worker.run(ROOT + "/live_jobs/" + result.json()["audit_id"])
    updated = producer.get(BASE).json()["snapshot"]
    assert [c["state"] for c in updated["claims"]] == ["stale", "carried_forward"]
    assert len(calls) == 4
    assert updated["claims"][1]["decision"] == snapshot["claims"][1]["decision"]
    assert updated["claims"][0]["decision"] is None
    assert updated["content_sha256"] == digest({k: v for k, v in updated.items() if k != "content_sha256"})
    pdf = producer.get(BASE + f'/revisions/{updated["revision_id"]}/snapshots/{updated["snapshot_id"]}/pdf')
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Public work a" in text and "carried_forward" in text and "stale" in text
    assert pdf.headers["X-Snapshot-SHA256"] == updated["content_sha256"]


def test_authority_unknown_claim_tenant_scope_and_csrf(harness):
    _, worker, _, client = harness
    reviewer = client("REVIEWER")
    data = intake(client(), worker)
    assert client("REVIEWER", "other_production").get(BASE).status_code == 403
    assert TestClient(app).get(BASE).status_code in (401, 403)
    assert reviewer.post(BASE + "/claims/claim_unknown/decision", json={"action": "reject", "revision_id": data["revision_id"],
        "expected_snapshot_id": data["snapshot_id"], "rationale": "Unknown claim"}).status_code == 404
    reviewer.headers.pop("X-CSRF-Token")
    assert sign(reviewer, data).status_code == 403


def test_provider_failure_keeps_claim_unresolved(harness):
    _, worker, _, client = harness
    worker.providers.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    data = intake(client(), worker, [use("a")])
    assert data["claims"][0]["state"] == "new"
    assert data["claims"][0]["decision"] is None
    assert data["claims"][0]["evidence_citations"] == []
    assert "503" in data["claims"][0]["reason_code"]
    assert sign(client("REVIEWER"), data).status_code == 422


def test_recovery_preserves_payload_and_fences_crashed_worker(harness):
    store, worker, calls, client = harness
    result = client().post("/api/clearance/revisions", json={"production_id": "production_acceptance", "initial_uses": [use("unfamiliar")]}, headers={"Idempotency-Key": "recovery"}).json()
    path = ROOT + "/live_jobs/" + result["audit_id"]
    first = worker.acquire(path)
    assert worker.acquire(path) is None
    store.atomic(lambda tx: tx.put(path, {**tx.get(path), "lease_until": 0}))
    recovered = Worker(SQLiteStore(store.path), worker.providers)
    recovered.run(path)
    assert recovered.store.get(path)["status"] == "COMPLETED"
    with pytest.raises(Conflict):
        worker.update(path, first["fence"], lambda j: j.update(status="COMPLETED"))
    assert any("Public work unfamiliar" in data.get("search_queries", [""])[0] for _, data in calls)


def test_idempotency_concurrent_submissions_are_atomic(harness):
    store, _, _, _ = harness
    payload = RevisionInput(production_id="production_acceptance", initial_uses=[use("a")])
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = list(pool.map(lambda _: submit(SQLiteStore(store.path), ROOT, payload, "test-producer", "shared"), range(2)))
    assert jobs[0]["audit_id"] == jobs[1]["audit_id"]
    with pytest.raises(Conflict):
        submit(store, ROOT, RevisionInput(production_id="production_acceptance", initial_uses=[use("b")]), "test-producer", "shared")


def test_source_intake_uses_real_extraction_boundary(harness):
    _, worker, calls, client = harness
    data = intake(client(), worker, source_text="Scene 5. A radio plays an unfamiliar composition in the background.")
    assert data["claims"][0]["stable_lineage_key"] == "extracted"
    assert len(calls) == 5


def test_rejection_reopens_transitive_dependencies_only(harness):
    _, worker, _, client = harness
    reviewer = client("REVIEWER")
    data = intake(client(), worker, [use("a"), use("b", ["a"]), use("c", ["b"]), use("independent")])
    for i in range(4):
        response = sign(reviewer, data, i)
        assert response.status_code == 200, response.text
        data = response.json()
    data = sign(reviewer, data, 0, "reject").json()
    assert [c["state"] for c in data["claims"]] == ["exception", "stale", "stale", "re_attested"]


def test_uncertain_paid_call_is_not_repeated_on_recovery(harness):
    store, worker, calls, client = harness
    result = client().post("/api/clearance/revisions", json={"production_id": "production_acceptance", "initial_uses": [use("a")]}, headers={"Idempotency-Key": "uncertain"}).json()
    path = ROOT + "/live_jobs/" + result["audit_id"]
    job = worker.acquire(path)
    key = "claim_" + digest("a")[:24] + ":0:search"
    store.atomic(lambda tx: tx.put(path, {**tx.get(path), "lease_until": 0, "reserved_usd": .01, "calls": {key: {"status": "STARTED"}}}))
    Worker(SQLiteStore(store.path), worker.providers).run(path)
    assert calls == []
    snapshot = client().get(BASE).json()["snapshot"]
    assert "uncertain" in snapshot["claims"][0]["investigation_error"]


def test_budget_exhaustion_dispatches_no_provider_call(harness):
    _, worker, calls, client = harness
    data = intake(client(), worker, [use("a")], max_spend_usd=.001)
    assert calls == []
    assert data["claims"][0]["evidence_citations"] == []
    assert "budget exhausted" in data["claims"][0]["reason_code"]


def test_adaptive_followup_comes_from_observed_provider_response(harness):
    _, worker, _, client = harness
    seen = []
    def respond(request):
        data = json.loads(request.content)
        if request.url.host == "api.parallel.ai":
            seen.append(data["search_queries"][0])
            return httpx.Response(200, json={"search_id": "search_live_contract", "results": [{"url": "https://source.example.test", "excerpts": ["Ownership changed in 2025"]}]})
        incoming = json.loads(data["contents"][0]["parts"][0]["text"])
        output = {"summary": "Ownership transition needs verification.", "cited_ids": [incoming["evidence"][0]["evidence_id"]],
                  "missing_facts": ["Successor owner"], "next_query": "Public work successor catalogue 2025" if len(seen) == 1 else None}
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(output)}]}}]})
    worker.providers.client = httpx.Client(transport=httpx.MockTransport(respond))
    data = intake(client(), worker, [use("a")], agentic=False)
    assert seen[1] == "Public work successor catalogue 2025"
    assert len(data["claims"][0]["evidence_citations"]) == 2
    assert data["claims"][0]["decision"] is None


def test_fixture_workspace_endpoints_are_retired(harness):
    _, _, _, client = harness
    assert client().get("/api/reports/form-eo-2026").status_code == 410
    assert client().post("/api/v1/claims/made_up/decision", json={}).status_code == 410
    assert client().post("/api/revisions/audit", json={}).status_code == 410


def test_valid_invitation_can_recover_an_expired_session(harness):
    import hashlib
    from backend.storage.invite_store import get_invite_store
    _, _, _, client = harness
    c = client()
    get_session_store().revoke_session(c.headers["X-CSRF-Token"])
    assert c.get(BASE).status_code == 401
    token = uuid.uuid4().hex + uuid.uuid4().hex
    get_invite_store().create_invite(hashlib.sha256(token.encode()).hexdigest(), role="producer",
        tenant_id="org_acceptance", production_id="production_acceptance")
    result = c.post("/api/auth/redeem-invite", json={"invite_token": token})
    assert result.status_code == 200
    assert c.get(BASE).status_code == 200
