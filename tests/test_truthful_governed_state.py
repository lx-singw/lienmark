"""
tests/test_truthful_governed_state.py

Lienmark Milestone A Acceptance Gate Test Suite: Truthful Governed State.
Covers all 9 required acceptance criteria:
1. test_concurrent_workers_reservation_exhaustion
2. test_worker_crash_preserves_reservation
3. test_firestore_unavailable_fails_closed
4. test_document_arrival_resumes_without_approval
5. test_act_07_briefing_leaves_claim_unapproved
6. test_multi_tenant_namespace_isolation
7. test_frontend_disconnected_fails_closed_without_fixtures
8. test_snapshot_reconciliation_parity
9. test_published_pricing_micro_cent_accuracy
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from concurrent.futures import ThreadPoolExecutor
import os
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    ApprovalOrigin,
    AtomicRightsClaim,
    CensusDisposition,
    ClarificationRequest,
    WorkflowReason,
)
from backend.core.unfamiliar_workflows import resume_claim_investigation
from backend.orchestration.adk_pipeline import CoordinatorAction, EvidenceDrivenCoordinator
from backend.orchestration.budget_governor import (
    calculate_gemini_cost_micros,
    calculate_gemini_cost_usd,
    calculate_parallel_cost_micros,
    calculate_parallel_cost_usd,
)
from backend.orchestration.budget_store import get_budget_store
from backend.orchestration.budget_store_firestore import FirestoreBudgetStore
from backend.orchestration.budget_store_local import LocalBudgetStore
from backend.orchestration.budget_store_types import (
    BudgetExceededError,
    BudgetStoreError,
    PARALLEL_BASIC_MICROS,
    PARALLEL_FAST_MICROS,
    ReservationStatus,
)
from backend.main import app
from tests.test_export_reconciliation import seed_standard_reconciled_counsel_decisions

client = TestClient(app)


def test_concurrent_workers_reservation_exhaustion(tmp_path):
    """Two independent workers reserve against nearly exhausted budget; only affordable proceeds."""
    store = LocalBudgetStore(base_dir=str(tmp_path))
    store.set_budget_limit("org_1", "prod_1", "per_1", limit_micros=7_000)
    provider_calls = []

    def run_worker(w_id: str) -> bool:
        try:
            res = store.reserve_budget("org_1", "prod_1", "per_1", f"run_{w_id}", f"act_{w_id}", "parallel", "basic", 5_000)
            provider_calls.append((w_id, res.reservation_id))
            store.settle_reservation(res.reservation_id, actual_cost_micros=5_000, usage_measurements={})
            return True
        except BudgetExceededError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run_worker, ["worker_a", "worker_b"]))

    assert results.count(True) == 1 and results.count(False) == 1
    assert len(provider_calls) == 1
    summary = store.get_summary("org_1", "prod_1", "per_1")
    assert summary.settled_spend_micros == 5_000 and summary.outstanding_reservations_micros == 0


def test_worker_crash_preserves_reservation(tmp_path):
    """Worker dies after reservation; reservation survives in store without artificial zero cost."""
    store = LocalBudgetStore(base_dir=str(tmp_path))
    store.set_budget_limit("org_crash", "prod_c", "per_c", 50_000)
    res = store.reserve_budget("org_crash", "prod_c", "per_c", "run_c", "act_c", "gemini", "pro", 10_000)

    recovered_store = LocalBudgetStore(base_dir=str(tmp_path))
    sum1 = recovered_store.get_summary("org_crash", "prod_c", "per_c")
    assert sum1.outstanding_reservations_micros == 10_000 and sum1.settled_spend_micros == 0

    recovered_store.recover_reservation(res.reservation_id, status=ReservationStatus.UNCERTAIN)
    sum2 = recovered_store.get_summary("org_crash", "prod_c", "per_c")
    assert sum2.settled_spend_micros == 0
    assert sum2.outstanding_reservations_micros == 0


def test_firestore_unavailable_fails_closed():
    """Disabling Firestore causes immediate fail-closed error; zero silent fallback or paid calls."""
    calls = []

    class MockDocRef:
        def collection(self, _):
            return self
        def document(self, _):
            return self

    class BrokenClient:
        def collection(self, _):
            return MockDocRef()
        def transaction(self):
            raise ConnectionError("Firestore network partition")

    store = FirestoreBudgetStore(client=BrokenClient())
    with pytest.raises(BudgetStoreError) as exc_info:
        store.reserve_budget("org_gcp", "prod_gcp", "per_gcp", "run_1", "act_1", "parallel", "fast", 1_000)
    assert "Firestore" in str(exc_info.value) or "partition" in str(exc_info.value)

    # Client is required; passing None fails closed immediately without silent fallback
    with pytest.raises(BudgetStoreError):
        FirestoreBudgetStore(client=None)

    def dispatch_call():
        store.reserve_budget("org_gcp", "prod_gcp", "per_gcp", "run_1", "act_1", "parallel", "fast", 1_000)
        calls.append("paid_call")

    with pytest.raises(BudgetStoreError):
        dispatch_call()
    assert len(calls) == 0


def test_document_arrival_resumes_without_approval():
    """resume_claim_investigation attaches document and resumes, but keeps disposition NEEDS_REVIEW."""
    claim = AtomicRightsClaim(
        claim_id="clm_doc_resumption", occurrence_id="occ_doc_01",
        occurrence_lineage_id="occ_lin_doc_01", right_category="synchronization",
        rights_subject="Licensor Master Agreement", disposition=CensusDisposition.NEEDS_REVIEW,
        workflow_reason=WorkflowReason.WAITING_FOR_INFORMATION,
    )
    clrf = ClarificationRequest(
        request_id="req_doc_01", claim_id=claim.claim_id,
        stable_lineage_key=claim.occurrence_lineage_id,
        question_text="Please provide sync license agreement", status="PENDING",
    )
    doc_uri = "gs://studio-vault/agreements/executed_sync_license.pdf"

    resumed, resolved_clrf, success = resume_claim_investigation(
        claim=claim, clarification=clrf, document_uri=doc_uri, active_lineage_keys=["occ_lin_doc_01"],
    )
    assert success is True
    assert resolved_clrf.status == "RESOLVED"
    assert resolved_clrf.attached_document_ref == doc_uri
    assert resumed.disposition == CensusDisposition.NEEDS_REVIEW
    assert resumed.licensor_grant_confirmed is True


@pytest.mark.asyncio
async def test_act_07_briefing_leaves_claim_unapproved():
    """ACT_07_PREPARE_REVIEW_BRIEF synthesizes briefing and sets ready_for_review without approving."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    claim = AtomicRightsClaim(
        claim_id="clm_brief_gate", occurrence_id="occ_b_01", occurrence_lineage_id="poster_art",
        right_category="copyright", rights_subject="Vintage Poster",
        disposition=CensusDisposition.NEEDS_REVIEW, workflow_reason=WorkflowReason.NORMAL_OPERATION,
    )
    coord.claims[claim.claim_id] = claim
    res = await coord.execute_action(CoordinatorAction.ACT_07_PREPARE_REVIEW_BRIEF, claim)

    assert res["status"] == "SUCCESS"
    assert "briefing" in res
    assert coord.claim_states[claim.claim_id] == "ready_for_review"
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert claim.approval_origin == ApprovalOrigin.NONE


def test_multi_tenant_namespace_isolation(tmp_path):
    """Identical production_id and run_id under two different orgs maintain segregated pools."""
    store = LocalBudgetStore(base_dir=str(tmp_path))
    p_id, r_id, per_id = "prod_blockbuster", "run_001", "2026-Q3"

    store.set_budget_limit("org_paramount", p_id, per_id, limit_micros=10_000)
    store.set_budget_limit("org_warner", p_id, per_id, limit_micros=50_000)

    res_p = store.reserve_budget("org_paramount", p_id, per_id, r_id, "act_1", "parallel", "fast", 8_000)
    store.settle_reservation(res_p.reservation_id, actual_cost_micros=8_000, usage_measurements={})

    res_w = store.reserve_budget("org_warner", p_id, per_id, r_id, "act_1", "parallel", "fast", 30_000)
    store.settle_reservation(res_w.reservation_id, actual_cost_micros=30_000, usage_measurements={})

    sum_p = store.get_summary("org_paramount", p_id, per_id)
    sum_w = store.get_summary("org_warner", p_id, per_id)
    assert sum_p.settled_spend_micros == 8_000 and sum_p.budget_limit_micros == 10_000
    assert sum_w.settled_spend_micros == 30_000 and sum_w.budget_limit_micros == 50_000

    with pytest.raises(BudgetExceededError):
        store.reserve_budget("org_paramount", p_id, per_id, r_id, "act_2", "parallel", "fast", 3_000)
    res_w2 = store.reserve_budget("org_warner", p_id, per_id, r_id, "act_2", "parallel", "fast", 10_000)
    assert res_w2.max_cost_micros == 10_000


def test_frontend_disconnected_fails_closed_without_fixtures():
    """API failure triggers unavailable / error state without silent golden fixture injection."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_client_path = os.path.join(repo_root, "frontend", "lib", "api_client.ts")
    with open(api_client_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "enableFallback: false" in content
    assert "if (!this.enableFallback) throw error;" in content

    # Backend fail-closed check: unauthenticated dashboard call rejects with 401 Unauthorized
    res = client.get("/api/v1/dashboard/inbox")
    assert res.status_code == 401


def test_snapshot_reconciliation_parity():
    """Dashboard census counts and report export match exact authoritative snapshot with identical dispositions."""
    seed_standard_reconciled_counsel_decisions()
    client.post("/api/demo/seed", json={"mode": "resolved"})
    s_data = client.get("/api/demo/state").json()
    e_data = client.get("/api/reports/export?format=json").json()

    assert e_data["total_claims"] == s_data["total_claims"] == 12
    assert e_data["carried_forward_count"] == s_data["carried_forward_count"] == 10
    assert e_data["re_attested_count"] == s_data["reattested_count"] == 1
    assert e_data["unresolved_exception_count"] == s_data["exception_count"] == 1


def test_published_pricing_micro_cent_accuracy():
    """Parallel fast ($0.001) / basic ($0.005) and Gemini token rates billed in integer µUSD."""
    assert calculate_parallel_cost_micros("fast") == PARALLEL_FAST_MICROS == 1_000
    assert calculate_parallel_cost_usd("fast") == 0.001
    assert calculate_parallel_cost_micros("basic") == PARALLEL_BASIC_MICROS == 5_000
    assert calculate_parallel_cost_usd("basic") == 0.005

    flash_micros = calculate_gemini_cost_micros("gemini-1.5-flash", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert flash_micros == 375_000
    assert calculate_gemini_cost_usd("gemini-1.5-flash", 1_000_000, 1_000_000) == 0.375

    pro_micros = calculate_gemini_cost_micros("gemini-1.5-pro", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert pro_micros == 6_250_000
    assert calculate_gemini_cost_usd("gemini-1.5-pro", 1_000_000, 1_000_000) == 6.25

    assert sum(calculate_parallel_cost_micros("fast") for _ in range(10_000)) == 10_000_000
