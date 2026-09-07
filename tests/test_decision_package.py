"""
tests/test_decision_package.py

Comprehensive unit tests for the DecisionPackage subsystem:
- Immutable creation and canonical SHA-256 digest computation
- Bit-for-bit determinism across serialization order variations
- Package supersession lineage and approval reset
- Material dependency difference detection vs cosmetic updates
- Dual-review sign-off workflow and four-eyes principle enforcement
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from backend.core.decision_package_types import (
    DecisionPackage,
    DualReviewStatus,
    PackageApprovalRecord,
)
from backend.core.decision_package import (
    compute_package_canonical_digest,
    create_decision_package,
    derive_superseded_package,
    is_material_package_difference,
    apply_package_approval,
    reject_package,
    invalidate_package,
)


def sample_package_payload():
    return {
        "claim_id": "claim_music_42",
        "cut_revision": "cut_v1",
        "intended_scope": {"territory": "Worldwide", "term": "Perpetual"},
        "proposed_disposition": "CLEARED",
        "rationale": "Direct sync license verified with Warner Chappell.",
        "conditions": ["Credit in main titles", "Territory limited to worldwide"],
        "evidence_bundle": [{"doc_id": "lic_001", "type": "sync_license"}],
        "policy_version": "v1.2",
        "policy_digest": "a" * 64,
        "required_roles": ["lead_counsel", "secondary_counsel"],
    }


def test_create_decision_package():
    payload = sample_package_payload()
    pkg = create_decision_package(**payload)
    assert pkg.claim_id == "claim_music_42"
    assert pkg.version == 1
    assert pkg.status == DualReviewStatus.PENDING_FIRST_REVIEW
    assert pkg.primary_approval is None
    assert pkg.secondary_approval is None
    assert len(pkg.canonical_digest) == 64
    assert pkg.effective_policy_version == "v1.2"


def test_canonical_digest_determinism():
    payload = sample_package_payload()
    digest1 = compute_package_canonical_digest(payload)

    # Shuffled dictionary keys and conditions order
    shuffled_payload = dict(reversed(list(payload.items())))
    shuffled_payload["conditions"] = list(reversed(payload["conditions"]))
    digest2 = compute_package_canonical_digest(shuffled_payload)
    assert digest1 == digest2


def test_canonical_digest_ignores_transient_fields():
    payload = sample_package_payload()
    base_digest = compute_package_canonical_digest(payload)

    # Adding transient approval and status fields does not alter content digest
    with_transient = dict(payload)
    with_transient["status"] = DualReviewStatus.FINAL_APPROVED
    with_transient["created_at_utc"] = "2026-01-01T00:00:00Z"
    with_transient["notes"] = "Cosmetic note"
    assert compute_package_canonical_digest(with_transient) == base_digest


def test_canonical_digest_sensitivity():
    payload = sample_package_payload()
    base_digest = compute_package_canonical_digest(payload)

    # Changing cut_revision alters digest
    changed = dict(payload)
    changed["cut_revision"] = "cut_v2"
    assert compute_package_canonical_digest(changed) != base_digest

    # Changing policy alters digest
    changed = dict(payload)
    changed["policy_version"] = "v2.0"
    assert compute_package_canonical_digest(changed) != base_digest


def test_derive_superseded_package():
    pkg = create_decision_package(**sample_package_payload())
    superseded = derive_superseded_package(
        base_package=pkg,
        changed_fields={"cut_revision": "cut_v2", "conditions": ["New condition"]},
        new_version=2,
    )
    assert superseded.version == 2
    assert superseded.cut_revision == "cut_v2"
    assert superseded.status == DualReviewStatus.PENDING_FIRST_REVIEW
    assert superseded.canonical_digest != pkg.canonical_digest
    assert pkg.version == 1  # Base package immutable


def test_is_material_package_difference_material():
    pkg = create_decision_package(**sample_package_payload())

    # Cut revision change
    is_mat, diffs = is_material_package_difference(pkg, {"cut_revision": "cut_v2"})
    assert is_mat is True
    assert "cut_revision" in diffs

    # Conditions change
    is_mat, diffs = is_material_package_difference(pkg, {"conditions": ["Only US"]})
    assert is_mat is True
    assert "conditions" in diffs

    # Evidence bundle change
    is_mat, diffs = is_material_package_difference(pkg, {"evidence": [{"doc_id": "lic_999"}]})
    assert is_mat is True
    assert "evidence_bundle" in diffs


def test_is_material_package_difference_cosmetic():
    pkg = create_decision_package(**sample_package_payload())

    # Rationale and note modifications are non-material
    is_mat, diffs = is_material_package_difference(
        pkg,
        {"rationale": "Updated wording for clarity.", "notes": "Cosmetic review note."},
    )
    assert is_mat is False
    assert diffs == []


def test_dual_review_workflow_success():
    pkg = create_decision_package(**sample_package_payload())

    # Primary review
    primary_appr = PackageApprovalRecord(
        package_id=pkg.package_id,
        package_version=pkg.version,
        package_digest=pkg.canonical_digest,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance",
        reviewer_role="lead_counsel",
        is_primary_or_secondary="primary",
        conflict_attestation=True,
        ledger_event_id="evt_primary_001",
    )
    pkg_v1_rev1 = apply_package_approval(pkg, primary_appr)
    assert pkg_v1_rev1.status == DualReviewStatus.FIRST_REVIEW_APPROVED
    assert pkg_v1_rev1.primary_approval == primary_appr

    # Secondary review
    secondary_appr = PackageApprovalRecord(
        package_id=pkg.package_id,
        package_version=pkg.version,
        package_digest=pkg.canonical_digest,
        reviewer_id="counsel_02",
        reviewer_name="Marcus Reed",
        reviewer_role="secondary_counsel",
        is_primary_or_secondary="secondary",
        conflict_attestation=True,
        ledger_event_id="evt_secondary_002",
    )
    pkg_v1_rev2 = apply_package_approval(pkg_v1_rev1, secondary_appr)
    assert pkg_v1_rev2.status == DualReviewStatus.FINAL_APPROVED
    assert pkg_v1_rev2.secondary_approval == secondary_appr


def test_dual_review_four_eyes_violation():
    pkg = create_decision_package(**sample_package_payload())
    primary_appr = PackageApprovalRecord(
        package_id=pkg.package_id,
        package_version=pkg.version,
        package_digest=pkg.canonical_digest,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance",
        reviewer_role="lead_counsel",
        is_primary_or_secondary="primary",
        conflict_attestation=True,
        ledger_event_id="evt_001",
    )
    pkg_rev1 = apply_package_approval(pkg, primary_appr)

    # Same counsel cannot perform secondary review
    same_counsel_secondary = PackageApprovalRecord(
        package_id=pkg.package_id,
        package_version=pkg.version,
        package_digest=pkg.canonical_digest,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance",
        reviewer_role="secondary_counsel",
        is_primary_or_secondary="secondary",
        conflict_attestation=True,
        ledger_event_id="evt_002",
    )
    with pytest.raises(ValueError, match="Four-eyes violation"):
        apply_package_approval(pkg_rev1, same_counsel_secondary)


def test_dual_review_digest_mismatch():
    pkg = create_decision_package(**sample_package_payload())
    tampered_appr = PackageApprovalRecord(
        package_id=pkg.package_id,
        package_version=pkg.version,
        package_digest="f" * 64,
        reviewer_id="counsel_01",
        reviewer_name="Elena Vance",
        reviewer_role="lead_counsel",
        is_primary_or_secondary="primary",
        conflict_attestation=True,
        ledger_event_id="evt_001",
    )
    with pytest.raises(ValueError, match="package_digest does not match"):
        apply_package_approval(pkg, tampered_appr)


def test_reject_and_invalidate_package():
    pkg = create_decision_package(**sample_package_payload())
    rejected = reject_package(pkg, notes="Insufficient sync grant")
    assert rejected.status == DualReviewStatus.REJECTED

    invalidated = invalidate_package(pkg, reason="Cut revision bumped to v2")
    assert invalidated.status == DualReviewStatus.STALE_INVALIDATED
