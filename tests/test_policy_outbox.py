"""
tests/test_policy_outbox.py

Unit and integration tests for Transactional Outbox Policy Invalidation Cascade.
Sprint 5.3: Asynchronous Policy Dispatch, Rule Dependencies, and Golden Demo.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from backend.core.decision_package_types import DecisionPackage, DualReviewStatus
from backend.core.dual_review import DualReviewCoordinator
from backend.core.policy_outbox import PolicyOutboxDispatcher
from backend.core.policy_outbox_types import (
    CascadeAction,
    DispatchIntentStatus,
)
from backend.domain.models import AtomicRightsClaim, CensusDisposition
from backend.main import app
from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store import PolicyStore, PolicyStoreMode


@pytest.fixture
def temp_store_dir():
    d = tempfile.mkdtemp(prefix="lmk_outbox_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def ledger():
    led = CryptographicLedger()
    led.initialize_production_ledger("org_warner", "prod_default", "test_init")
    return led


@pytest.fixture
def policy_store(temp_store_dir, ledger):
    return PolicyStore(mode=PolicyStoreMode.LOCAL_DISK, base_dir=temp_store_dir, ledger=ledger)


@pytest.fixture
def coordinator(ledger):
    return DualReviewCoordinator(ledger=ledger)


@pytest.fixture
def dispatcher(policy_store, coordinator, ledger):
    return PolicyOutboxDispatcher(policy_store=policy_store, coordinator=coordinator, ledger=ledger)


def _make_trailer_claim(claim_id="claim_trailer_001"):
    return AtomicRightsClaim(
        claim_id=claim_id, occurrence_id="occ_trailer_01", occurrence_lineage_id="lin_01",
        right_category="music", rights_subject="Cinematic Trailer Cue",
        intended_scope={"media_scopes": ["promotional_trailer", "theatrical"], "description": "trailer promo"},
        disposition=CensusDisposition.NEEDS_REVIEW,
    )


def _make_non_trailer_claim(claim_id="claim_bg_002"):
    return AtomicRightsClaim(
        claim_id=claim_id, occurrence_id="occ_bg_02", occurrence_lineage_id="lin_02",
        right_category="music", rights_subject="Background Diner Radio",
        intended_scope={"media_scopes": ["linear_broadcast"], "description": "background source"},
        disposition=CensusDisposition.NEEDS_REVIEW,
    )


def test_compute_policy_diff_detects_trailer_second_review_rule(dispatcher):
    old_cfg = {"required_media_scopes": ["theatrical"], "require_promotional_trailer_second_review": False}
    new_cfg = {"required_media_scopes": ["theatrical"], "require_promotional_trailer_second_review": True}
    diff = dispatcher.compute_policy_diff(old_cfg, new_cfg, "v1", "v2")
    assert "require_promotional_trailer_second_review" in diff.modified_rules
    assert len(diff.target_filters) >= 1
    assert diff.target_filters[0].rule_code == "RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW"
    assert diff.target_filters[0].requires_second_review is True


def test_rule_targeting_matches_only_trailer_claims(dispatcher):
    old_cfg = {"require_promotional_trailer_second_review": False}
    new_cfg = {"require_promotional_trailer_second_review": True}
    diff = dispatcher.compute_policy_diff(old_cfg, new_cfg, "v1", "v2")
    flt = diff.target_filters[0]

    trailer_claim = _make_trailer_claim()
    non_trailer_claim = _make_non_trailer_claim()
    assert dispatcher.matches_claim_filter(trailer_claim, flt) is True
    assert dispatcher.matches_claim_filter(non_trailer_claim, flt) is False


def test_historical_approved_decision_preserved(dispatcher, coordinator, policy_store, ledger):
    claim = _make_trailer_claim("claim_approved_001")
    pkg = coordinator.create_package(claim_id=claim.claim_id, tenant_id="org_warner", production_id="prod_001", claim=claim)
    coordinator.submit_approval(pkg.package_id, "counsel_01", "Elena", "lead", True, ledger)
    coordinator.submit_approval(pkg.package_id, "counsel_02", "Marcus", "assoc", True, ledger)
    assert pkg.status == DualReviewStatus.FINAL_APPROVED

    _, intent = policy_store.save_policy_revision(
        "org_warner", {"require_promotional_trailer_second_review": True}, "admin_01", action="POLICY_UPDATED",
    )
    report = dispatcher.process_single_intent(intent, [claim], ledger)
    assert report.historical_preserved == 1
    assert report.packages_invalidated == 0
    assert pkg.status == DualReviewStatus.FINAL_APPROVED
    assert claim.disposition == CensusDisposition.APPROVED


def test_in_progress_package_invalidated_and_routed_v2(dispatcher, coordinator, policy_store, ledger):
    claim = _make_trailer_claim("claim_pending_001")
    pkg = coordinator.create_package(claim_id=claim.claim_id, tenant_id="org_warner", production_id="prod_001", claim=claim)
    coordinator.submit_approval(pkg.package_id, "counsel_01", "Elena", "lead", True, ledger)
    assert pkg.status == DualReviewStatus.FIRST_REVIEW_APPROVED

    _, intent = policy_store.save_policy_revision(
        "org_warner", {"require_promotional_trailer_second_review": True}, "admin_01", action="POLICY_UPDATED",
    )
    report = dispatcher.process_single_intent(intent, [claim], ledger)
    assert report.packages_invalidated == 1
    assert pkg.status == DualReviewStatus.STALE_INVALIDATED

    active = coordinator.get_active_package_for_claim(claim.claim_id)
    assert active is not None
    assert active.version == 2
    assert active.status == DualReviewStatus.PENDING_FIRST_REVIEW
    assert active.supersedes_package_id == pkg.package_id


def test_worker_restart_recovery_reclaims_interrupted_intents(dispatcher, policy_store):
    _, intent = policy_store.save_policy_revision("org_warner", {"policy_val": 42}, "admin_01")
    policy_store.update_dispatch_intent_status(intent.intent_id, DispatchIntentStatus.PROCESSING.value)
    reclaimed = dispatcher.recover_abandoned_intents("org_warner")
    assert reclaimed == 1
    intents = policy_store.list_dispatch_intents("org_warner", status=DispatchIntentStatus.PENDING.value)
    assert any(i.intent_id == intent.intent_id for i in intents)


def test_outbox_rest_api_endpoints():
    from tests.test_tenant_middleware import create_test_jwt

    client = TestClient(app, raise_server_exceptions=False)
    org_id = "org_lienmark_legal_llp"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_admin_01", roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    r_list = client.get(f"/api/v1/organizations/{org_id}/policy/intents", headers=headers)
    assert r_list.status_code in (200, 404)
    r_rec = client.post(f"/api/v1/organizations/{org_id}/policy/recover-intents", headers=headers)
    assert r_rec.status_code == 200
    assert r_rec.json().get("status") == "reclaimed"
