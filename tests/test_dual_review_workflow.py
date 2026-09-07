"""
tests/test_dual_review_workflow.py

Sprint 5.2 Acceptance Gate: Accountable Dual-Review Clearance Sign-Off.
Verifies two-person approval workflow, distinct reviewer guard, conflict screening,
material dependency stale invalidation, and post-approval reopening.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.core.conflict_checker import clear_conflict_registry, register_counsel_conflict
from backend.core.dual_review import (
    ConflictAttestationError,
    ConflictOfInterestError,
    DecisionPackage,
    DistinctReviewerError,
    DualReviewCoordinator,
    DualReviewStatus,
    StalePackageError,
)
from backend.domain.models import AtomicRightsClaim, CensusDisposition
from backend.storage.ledger import CryptographicLedger


@pytest.fixture
def ledger() -> CryptographicLedger:
    """Provides a clean CryptographicLedger instance."""
    return CryptographicLedger()


@pytest.fixture
def coordinator() -> DualReviewCoordinator:
    """Provides a fresh DualReviewCoordinator."""
    return DualReviewCoordinator()


@pytest.fixture(autouse=True)
def clean_conflicts() -> None:
    """Ensures conflict registry is reset around each test."""
    clear_conflict_registry()
    yield
    clear_conflict_registry()


def _make_sample_claim(claim_id: str = "claim_vintage_poster_01") -> AtomicRightsClaim:
    return AtomicRightsClaim(
        claim_id=claim_id,
        occurrence_id="occ_scene_12",
        occurrence_lineage_id="occ_lin_vintage_poster",
        right_category="copyright",
        rights_subject="Visual Artwork",
        disposition=CensusDisposition.NEEDS_REVIEW,
    )


def test_full_two_person_approval_workflow(coordinator: DualReviewCoordinator, ledger: CryptographicLedger) -> None:
    """Test 1: Full two-person workflow transitions to FINAL_APPROVED with dual attribution."""
    claim = _make_sample_claim()
    pkg = coordinator.create_package(
        claim_id=claim.claim_id, tenant_id="org_alpha", production_id="prod_001",
        entity_names=["Acme Art Licensing"], claim=claim,
    )
    assert pkg.status == DualReviewStatus.PENDING_FIRST_REVIEW

    pkg, rec1 = coordinator.submit_approval(
        package_id=pkg.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha, Esq.",
        reviewer_role="Lead Clearance Counsel", conflict_attested=True, ledger=ledger,
    )
    assert pkg.status == DualReviewStatus.FIRST_REVIEW_APPROVED
    assert rec1.audit_event_id is not None
    events = ledger.get_events("prod_001")
    assert any(e.action_type == "FIRST_REVIEW_APPROVED" for e in events)

    pkg, rec2 = coordinator.submit_approval(
        package_id=pkg.package_id, reviewer_id="counsel_beta", reviewer_name="Counsel Beta, Esq.",
        reviewer_role="Supervising Partner", conflict_attested=True, ledger=ledger,
    )
    assert pkg.status == DualReviewStatus.FINAL_APPROVED
    assert claim.disposition == CensusDisposition.APPROVED
    assert rec2.audit_event_id is not None

    valid, reason, count = ledger.verify_chain("prod_001")
    assert valid is True and reason is None and count >= 3


def test_self_clearing_prevention_distinct_reviewer_invariant(
    coordinator: DualReviewCoordinator, ledger: CryptographicLedger
) -> None:
    """Test 2: Reviewer 1 attempting second review is strictly rejected (distinct principal rule)."""
    claim = _make_sample_claim()
    pkg = coordinator.create_package(claim_id=claim.claim_id, claim=claim)
    coordinator.submit_approval(
        package_id=pkg.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha, Esq.",
        reviewer_role="Lead Counsel", conflict_attested=True, ledger=ledger,
    )
    with pytest.raises((DistinctReviewerError, PermissionError), match="distinct authorized counsel") as exc:
        coordinator.submit_approval(
            package_id=pkg.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha, Esq.",
            reviewer_role="Lead Counsel", conflict_attested=True, ledger=ledger,
        )
    assert getattr(exc.value, "status_code", 403) in (400, 403)
    assert pkg.status == DualReviewStatus.FIRST_REVIEW_APPROVED


def test_conflict_of_interest_screening_block(
    coordinator: DualReviewCoordinator, ledger: CryptographicLedger
) -> None:
    """Test 3: Unconfirmed attestation and declared conflicts strictly block approval."""
    claim = _make_sample_claim()
    pkg = coordinator.create_package(
        claim_id=claim.claim_id, entity_names=["Paramount Pictures", "Universal Archive"], claim=claim,
    )
    with pytest.raises((ConflictAttestationError, ValueError), match="attestation is mandatory") as exc_att:
        coordinator.submit_approval(
            package_id=pkg.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha",
            reviewer_role="Counsel", conflict_attested=False, ledger=ledger,
        )
    assert getattr(exc_att.value, "status_code", 400) == 400

    register_counsel_conflict("counsel_gamma", ["Paramount Pictures"], "Prior adverse engagement")
    with pytest.raises((ConflictOfInterestError, PermissionError), match="conflict of interest") as exc_conf:
        coordinator.submit_approval(
            package_id=pkg.package_id, reviewer_id="counsel_gamma", reviewer_name="Counsel Gamma",
            reviewer_role="Counsel", conflict_attested=True, ledger=ledger,
        )
    assert getattr(exc_conf.value, "status_code", 403) in (400, 403)


def test_stale_package_invalidation_on_material_change(
    coordinator: DualReviewCoordinator, ledger: CryptographicLedger
) -> None:
    """Test 4: Material dependency change marks Package A stale; Package B requires both approvals."""
    claim = _make_sample_claim()
    pkg_a = coordinator.create_package(
        claim_id=claim.claim_id, cut_revision="cut_v1", license_data={"fee": 500}, claim=claim,
    )
    coordinator.submit_approval(
        package_id=pkg_a.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha",
        reviewer_role="Counsel", conflict_attested=True, ledger=ledger,
    )
    old_pkg, pkg_b = coordinator.invalidate_package_if_material_change(
        package_id=pkg_a.package_id, updated_package_data={"license_data": {"fee": 1500, "term": "5y"}},
        reason="License terms materially altered", ledger=ledger,
    )
    assert old_pkg.status == DualReviewStatus.STALE_INVALIDATED
    assert pkg_b is not None and pkg_b.version == 2
    assert pkg_b.canonical_digest != old_pkg.canonical_digest

    with pytest.raises((StalePackageError, ValueError), match="stale") as exc_stale:
        coordinator.submit_approval(
            package_id=pkg_a.package_id, reviewer_id="counsel_beta", reviewer_name="Counsel Beta",
            reviewer_role="Counsel", conflict_attested=True, ledger=ledger,
        )
    assert getattr(exc_stale.value, "status_code", 409) == 409

    coordinator.submit_approval(
        package_id=pkg_b.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha",
        reviewer_role="Counsel", conflict_attested=True, ledger=ledger,
    )
    assert pkg_b.status == DualReviewStatus.FIRST_REVIEW_APPROVED
    coordinator.submit_approval(
        package_id=pkg_b.package_id, reviewer_id="counsel_beta", reviewer_name="Counsel Beta",
        reviewer_role="Counsel", conflict_attested=True, ledger=ledger,
    )
    assert pkg_b.status == DualReviewStatus.FINAL_APPROVED


def test_unrelated_non_material_change_preserves_package(
    coordinator: DualReviewCoordinator, ledger: CryptographicLedger
) -> None:
    """Test 5: Non-material comments and styling metadata do not alter digest or invalidate approvals."""
    claim = _make_sample_claim()
    pkg = coordinator.create_package(claim_id=claim.claim_id, claim=claim)
    coordinator.submit_approval(
        package_id=pkg.package_id, reviewer_id="counsel_alpha", reviewer_name="Counsel Alpha",
        reviewer_role="Counsel", conflict_attested=True, ledger=ledger,
    )
    digest_before = pkg.canonical_digest
    pkg_same, superseded = coordinator.invalidate_package_if_material_change(
        package_id=pkg.package_id,
        updated_package_data={"comment": "Review note for editorial team", "formatting_metadata": {"font": "sans"}},
        reason="Editorial formatting update", ledger=ledger,
    )
    assert superseded is None
    assert pkg_same.status == DualReviewStatus.FIRST_REVIEW_APPROVED
    assert pkg_same.canonical_digest == digest_before
    assert pkg_same.compute_digest() == digest_before


def test_post_approval_material_change_reopens_claim(
    coordinator: DualReviewCoordinator, ledger: CryptographicLedger
) -> None:
    """Test 6: Post-approval material change reopens claim to NEEDS_REVIEW while preserving ledger history."""
    claim = _make_sample_claim()
    pkg = coordinator.create_package(
        claim_id=claim.claim_id, cut_revision="cut_v1", production_id="prod_post", claim=claim,
    )
    coordinator.submit_approval(pkg.package_id, "counsel_alpha", "Alpha", "Counsel", True, ledger)
    coordinator.submit_approval(pkg.package_id, "counsel_beta", "Beta", "Partner", True, ledger)
    assert pkg.status == DualReviewStatus.FINAL_APPROVED
    assert claim.disposition == CensusDisposition.APPROVED

    old_pkg, pkg_v2 = coordinator.invalidate_package_if_material_change(
        package_id=pkg.package_id, updated_package_data={"cut_revision": "cut_v2_director"},
        reason="Director cut revision v2 replaced v1", ledger=ledger,
    )
    assert old_pkg.status == DualReviewStatus.STALE_INVALIDATED
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert pkg_v2 is not None and pkg_v2.version == 2
    assert pkg_v2.status == DualReviewStatus.PENDING_FIRST_REVIEW

    events = ledger.get_events("prod_post")
    actions = [e.action_type for e in events]
    assert "DUAL_REVIEW_FINAL_APPROVED" in actions
    assert "PACKAGE_STALE_INVALIDATED" in actions
    valid, _, count = ledger.verify_chain("prod_post")
    assert valid is True and count >= 4
