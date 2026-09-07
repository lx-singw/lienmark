"""
tests/test_dual_review.py

Exhaustive unit test suite for Accountable Dual-Review Workflow Engine.
Sprint 5.2: Two Distinct Authorized Principals Invariant & Material Invalidation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from backend.core.conflict_checker import clear_conflict_registry, register_counsel_conflict
from backend.core.decision_package_types import DecisionPackage, DualReviewStatus
from backend.core.dual_review import DualReviewCoordinator, is_material_package_change
from backend.domain.models import CensusDisposition
from backend.storage.ledger import CryptographicLedger


@pytest.fixture(autouse=True)
def clean_conflicts():
    clear_conflict_registry()
    yield
    clear_conflict_registry()


@pytest.fixture
def ledger():
    led = CryptographicLedger()
    led.initialize_production_ledger("tenant_01", "prod_01", "actor_init")
    return led


@pytest.fixture
def coordinator(ledger):
    return DualReviewCoordinator(ledger=ledger)


def create_sample_package(coord: DualReviewCoordinator, claim_id="claim_sync_001"):
    return coord.create_package(
        claim_id=claim_id,
        tenant_id="tenant_01",
        production_id="prod_01",
        cut_revision="cut_v1",
        entity_names=["Warner Chappell", "Sony Music"],
        evidence_bundle=[{"id": "doc_1", "type": "license"}],
        effective_policy_version="v1.0",
        claim={"claim_id": claim_id, "disposition": "needs_review"},
    )


def test_two_stage_approval_happy_path(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    assert pkg.status == DualReviewStatus.PENDING_FIRST_REVIEW

    # Stage 1: Primary Approval
    p1, r1 = coordinator.submit_approval(
        package_id=pkg.package_id,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance, Esq.",
        reviewer_role="lead_counsel",
        conflict_attested=True,
        ledger=ledger,
        notes="Primary clearance verified.",
    )
    assert p1.status == DualReviewStatus.FIRST_REVIEW_APPROVED
    assert p1.primary_approval is not None
    assert p1.primary_approval.reviewer_id == "counsel_01"

    # Stage 2: Secondary Approval
    p2, r2 = coordinator.submit_approval(
        package_id=pkg.package_id,
        reviewer_id="counsel_02",
        reviewer_name="Marcus Reed, Esq.",
        reviewer_role="associate_counsel",
        conflict_attested=True,
        ledger=ledger,
        notes="Secondary confirmation.",
    )
    assert p2.status == DualReviewStatus.FINAL_APPROVED
    assert p2.secondary_approval is not None
    assert p2.secondary_approval.reviewer_id == "counsel_02"
    assert p2.disposition == CensusDisposition.APPROVED
    assert p2.claim["disposition"] == CensusDisposition.APPROVED.value


def test_two_distinct_principals_invariant(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    coordinator.submit_approval(
        package_id=pkg.package_id,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance, Esq.",
        reviewer_role="lead_counsel",
        conflict_attested=True,
        ledger=ledger,
    )
    # Attempting self-approval strictly raises PermissionError
    with pytest.raises(PermissionError, match="distinct authorized counsel"):
        coordinator.submit_approval(
            package_id=pkg.package_id,
            reviewer_id="counsel_01",
            reviewer_name="Elena Vance, Esq.",
            reviewer_role="lead_counsel",
            conflict_attested=True,
            ledger=ledger,
        )


def test_mandatory_conflict_attestation(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    with pytest.raises(ValueError, match="attestation is mandatory"):
        coordinator.submit_approval(
            package_id=pkg.package_id,
            reviewer_id="counsel_01",
            reviewer_name="Elena Vance",
            reviewer_role="lead_counsel",
            conflict_attested=False,
            ledger=ledger,
        )


def test_ethical_conflict_screening(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    register_counsel_conflict(
        counsel_id="counsel_conflicted",
        conflicted_entities=["Warner Chappell"],
        details="Prior adverse client representation",
    )
    with pytest.raises(PermissionError, match="ethical conflict of interest"):
        coordinator.submit_approval(
            package_id=pkg.package_id,
            reviewer_id="counsel_conflicted",
            reviewer_name="Conflicted Counsel",
            reviewer_role="lead_counsel",
            conflict_attested=True,
            ledger=ledger,
        )


def test_package_freshness_digest_mismatch(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    coordinator.submit_approval(
        package_id=pkg.package_id,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance",
        reviewer_role="lead_counsel",
        conflict_attested=True,
        ledger=ledger,
    )
    # Secretly mutate cut_revision after primary approval
    pkg.cut_revision = "cut_v2_tampered"
    with pytest.raises(ValueError, match="Package freshness violation"):
        coordinator.submit_approval(
            package_id=pkg.package_id,
            reviewer_id="counsel_02",
            reviewer_name="Marcus Reed",
            reviewer_role="associate_counsel",
            conflict_attested=True,
            ledger=ledger,
        )


def test_material_invalidation_creates_package_b(coordinator, ledger):
    pkg_a = create_sample_package(coordinator)
    coordinator.submit_approval(
        package_id=pkg_a.package_id,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance",
        reviewer_role="lead_counsel",
        conflict_attested=True,
        ledger=ledger,
    )
    # Material change: cut_revision updated
    old_pkg, new_pkg = coordinator.invalidate_package_if_material_change(
        package_id=pkg_a.package_id,
        updated_package_data={"cut_revision": "cut_v2"},
        reason="Script rewrite in scene 42",
        ledger=ledger,
    )
    assert old_pkg.status == DualReviewStatus.STALE_INVALIDATED
    assert new_pkg is not None
    assert new_pkg.version == 2
    assert new_pkg.status == DualReviewStatus.PENDING_FIRST_REVIEW
    assert new_pkg.primary_approval is None
    assert new_pkg.supersedes_package_id == old_pkg.package_id

    # Active package for claim points to Package B
    active = coordinator.get_active_package_for_claim(pkg_a.claim_id)
    assert active.package_id == new_pkg.package_id

    # Stale package cannot be approved
    with pytest.raises(ValueError, match="stale invalidated"):
        coordinator.submit_approval(
            package_id=old_pkg.package_id,
            reviewer_id="counsel_02",
            reviewer_name="Marcus Reed",
            reviewer_role="associate_counsel",
            conflict_attested=True,
            ledger=ledger,
        )


def test_non_material_changes_do_not_invalidate(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    curr_pkg, new_pkg = coordinator.invalidate_package_if_material_change(
        package_id=pkg.package_id,
        updated_package_data={"comment": "Clarified sync cue timing", "notes": "Cosmetic note"},
        reason="Minor counsel notes",
        ledger=ledger,
    )
    assert new_pkg is None
    assert curr_pkg.status == DualReviewStatus.PENDING_FIRST_REVIEW
    assert "Clarified sync cue timing" in curr_pkg.comments
    assert curr_pkg.notes == "Cosmetic note"


def test_already_approved_package_rejects_further_approval(coordinator, ledger):
    pkg = create_sample_package(coordinator)
    coordinator.submit_approval(pkg.package_id, "counsel_01", "Elena", "lead", True, ledger)
    coordinator.submit_approval(pkg.package_id, "counsel_02", "Marcus", "assoc", True, ledger)
    with pytest.raises(ValueError, match="already fully approved"):
        coordinator.submit_approval(pkg.package_id, "counsel_03", "Sarah", "partner", True, ledger)
