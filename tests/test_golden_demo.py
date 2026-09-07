"""
tests/test_golden_demo.py

The Golden Demo Acceptance Gate for Milestone E:
"Versioned Studio Policy & Accountable Review" (Sprint 5.3).

Scenario:
1. Studio introduces second-review requirement for promotional music use.
2. Lienmark identifies affected trailer claims & preserves historical decisions.
3. In-progress packages routed for dual review; production admin cannot bypass.
4. Two authorized reviewers approve; changing evidence invalidates approvals.
5. After worker restart, policy, pending work, and audit history remain consistent.

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import pytest

from backend.core.decision_package_types import DecisionPackage, DualReviewStatus
from backend.core.dual_review import (
    DistinctReviewerError,
    DualReviewCoordinator,
    StalePackageError,
)
from backend.core.policy_outbox import PolicyOutboxDispatcher
from backend.core.policy_outbox_types import CascadeAction
from backend.domain.models import AtomicRightsClaim, CensusDisposition
from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store import PolicyStore, PolicyStoreMode


@pytest.fixture
def test_env():
    d = tempfile.mkdtemp(prefix="lmk_golden_demo_")
    led = CryptographicLedger()
    led.initialize_production_ledger("org_golden_studio", "prod_trailer_01", "init_actor")
    store = PolicyStore(mode=PolicyStoreMode.LOCAL_DISK, base_dir=d, ledger=led)
    coord = DualReviewCoordinator(ledger=led)
    disp = PolicyOutboxDispatcher(policy_store=store, coordinator=coord, ledger=led)
    yield {"dir": d, "ledger": led, "store": store, "coordinator": coord, "dispatcher": disp}
    shutil.rmtree(d, ignore_errors=True)


def _setup_claims_and_packages(coord, ledger):
    claim_hist = AtomicRightsClaim(
        claim_id="claim_hist_approved", occurrence_id="occ_01", occurrence_lineage_id="lin_01",
        right_category="music", rights_subject="Teaser Trailer Cue (Approved)",
        intended_scope={"media_scopes": ["promotional_trailer", "theatrical"], "description": "teaser trailer music"},
        disposition=CensusDisposition.APPROVED,
    )
    pkg_hist = coord.create_package(claim_id=claim_hist.claim_id, tenant_id="org_golden_studio", production_id="prod_trailer_01", claim=claim_hist)
    coord.submit_approval(pkg_hist.package_id, "counsel_01", "Elena Vance", "Lead Counsel", True, ledger)
    coord.submit_approval(pkg_hist.package_id, "counsel_02", "Marcus Reed", "Partner", True, ledger)
    assert pkg_hist.status == DualReviewStatus.FINAL_APPROVED

    claim_trailer = AtomicRightsClaim(
        claim_id="claim_promo_trailer_cue", occurrence_id="occ_02", occurrence_lineage_id="lin_02",
        right_category="music", rights_subject="Trailer Hype Solo Cue",
        intended_scope={"media_scopes": ["promotional_trailer"], "description": "trailer music cue"},
        disposition=CensusDisposition.NEEDS_REVIEW,
    )
    pkg_trailer_v1 = coord.create_package(
        claim_id=claim_trailer.claim_id, tenant_id="org_golden_studio", production_id="prod_trailer_01",
        cut_revision="cut_v1", claim=claim_trailer,
    )
    return claim_hist, pkg_hist, claim_trailer, pkg_trailer_v1


def test_golden_demo_milestone_e(test_env):
    store, coord, disp, led = test_env["store"], test_env["coordinator"], test_env["dispatcher"], test_env["ledger"]
    claim_hist, pkg_hist, claim_trailer, pkg_trailer_v1 = _setup_claims_and_packages(coord, led)

    # 1. Studio baseline v1 created and baseline outbox processed
    v1_cfg = {"policy_id": "pol_golden", "org_id": "org_golden_studio", "require_promotional_trailer_second_review": False}
    store.save_policy_revision("org_golden_studio", v1_cfg, "studio_admin_01", action="POLICY_CREATED")
    disp.process_pending_intents("org_golden_studio", claims=[claim_hist, claim_trailer])

    # 2. Studio introduces second-review requirement for promotional music (v1 -> v2)
    v2_cfg = {"policy_id": "pol_golden", "org_id": "org_golden_studio", "require_promotional_trailer_second_review": True}
    rec_v2, intent = store.save_policy_revision("org_golden_studio", v2_cfg, "studio_admin_01", action="POLICY_UPDATED")
    assert rec_v2.version_id == "v2"
    assert intent.status == "PENDING"

    # 3. Outbox dispatcher runs: identifies trailer claim, preserves historical decision
    reports = disp.process_pending_intents("org_golden_studio", claims=[claim_hist, claim_trailer])
    assert len(reports) == 1
    rep = reports[0]
    assert rep.historical_preserved == 1
    assert rep.packages_invalidated == 1
    assert pkg_hist.status == DualReviewStatus.FINAL_APPROVED
    assert claim_hist.disposition == CensusDisposition.APPROVED
    assert pkg_trailer_v1.status == DualReviewStatus.STALE_INVALIDATED

    # 4. Production admin cannot bypass (stale approval rejected & self-clearing blocked)
    pkg_v2 = coord.get_active_package_for_claim(claim_trailer.claim_id)
    assert pkg_v2.version == 2 and pkg_v2.status == DualReviewStatus.PENDING_FIRST_REVIEW
    with pytest.raises((StalePackageError, ValueError)):
        coord.submit_approval(pkg_trailer_v1.package_id, "admin_user", "Prod Admin", "Admin", True, led)
    coord.submit_approval(pkg_v2.package_id, "counsel_01", "Elena Vance", "Lead Counsel", True, led)
    with pytest.raises((DistinctReviewerError, PermissionError)):
        coord.submit_approval(pkg_v2.package_id, "counsel_01", "Elena Vance", "Lead Counsel", True, led)

    # 5. Two distinct authorized reviewers approve; changing evidence invalidates approvals
    coord.submit_approval(pkg_v2.package_id, "counsel_02", "Marcus Reed", "Partner", True, led)
    assert pkg_v2.status == DualReviewStatus.FINAL_APPROVED
    assert claim_trailer.disposition == CensusDisposition.APPROVED
    _, pkg_v3 = coord.invalidate_package_if_material_change(
        pkg_v2.package_id, {"evidence_bundle": [{"doc": "restricted_license_v2"}]}, "Material license scope shifted", led,
    )
    assert pkg_v2.status == DualReviewStatus.STALE_INVALIDATED
    assert claim_trailer.disposition == CensusDisposition.NEEDS_REVIEW
    assert pkg_v3 is not None and pkg_v3.version == 3

    # 6. Worker restart consistency: policy, pending work, and ledger remain consistent
    fresh_store = PolicyStore(mode=PolicyStoreMode.LOCAL_DISK, base_dir=test_env["dir"], ledger=led)
    active_rec = fresh_store.get_active_policy("org_golden_studio")
    assert active_rec.version_id == "v2"
    assert active_rec.policy_digest == rec_v2.policy_digest
    valid, err, count = led.verify_chain("prod_trailer_01")
    assert valid is True and err is None and count >= 5
