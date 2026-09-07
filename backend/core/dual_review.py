"""
backend/core/dual_review.py

Accountable two-stage dual-review workflow engine for clearance sign-off.
Sprint 5.2: Two Distinct Authorized Principals Invariant & Material Invalidation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.core.conflict_checker import check_counsel_conflict
from backend.core.decision_package_types import (
    DecisionPackage,
    DualReviewStatus,
    PackageApprovalRecord,
)
from backend.core.dual_review_exceptions import (
    ConflictAttestationError,
    ConflictOfInterestError,
    DistinctReviewerError,
    DualReviewError,
    PackageNotFoundError,
    StalePackageError,
)
from backend.core.dual_review_invalidation import (
    apply_non_material_updates,
    create_superseding_package,
    is_material_package_change,
)
from backend.domain.models import CensusDisposition

__all__ = [
    "DualReviewStatus",
    "PackageApprovalRecord",
    "DecisionPackage",
    "DualReviewCoordinator",
    "is_material_package_change",
    "DualReviewError",
    "DistinctReviewerError",
    "ConflictAttestationError",
    "ConflictOfInterestError",
    "StalePackageError",
    "PackageNotFoundError",
    "get_dual_review_coordinator",
]


class DualReviewCoordinator:
    """Manages accountable dual-review workflow and material invalidation."""

    def __init__(self, ledger: Optional[Any] = None) -> None:
        self._packages: Dict[str, DecisionPackage] = {}
        self._ledger = ledger

    def get_package(self, package_id: str) -> Optional[DecisionPackage]:
        """Retrieves a decision package by its unique identifier."""
        return self._packages.get(package_id)

    def get_active_package_for_claim(self, claim_id: str) -> Optional[DecisionPackage]:
        """Returns the latest active (non-stale) decision package for a claim, or None."""
        candidates = [
            p for p in self._packages.values()
            if p.claim_id == claim_id and p.status != DualReviewStatus.STALE_INVALIDATED
        ]
        return max(candidates, key=lambda p: p.version) if candidates else None

    def create_package(self, claim_id: str, **kwargs: Any) -> DecisionPackage:
        """Instantiates and registers a new decision package."""
        if not kwargs.get("cut_revision"):
            kwargs["cut_revision"] = "cut_v1"
        pkg = DecisionPackage(claim_id=claim_id, **kwargs)
        if not pkg.canonical_digest:
            pkg.canonical_digest = pkg.compute_digest()
        self._packages[pkg.package_id] = pkg
        return pkg

    def _emit(self, ledger: Any, pkg: DecisionPackage, actor: str, action: str, extra: Dict[str, Any]) -> Any:
        target = ledger or self._ledger
        if not target:
            return None
        chains = getattr(target, "_chains", None)
        if isinstance(chains, dict) and len(chains.get(pkg.production_id, [])) == 0:
            if hasattr(target, "initialize_production_ledger"):
                target.initialize_production_ledger(pkg.tenant_id, pkg.production_id, actor)
        if hasattr(target, "append_event"):
            payload = {"action": action, "package_id": pkg.package_id, "claim_id": pkg.claim_id, "version": pkg.version, **extra}
            return target.append_event(pkg.tenant_id, pkg.production_id, actor, action, payload)
        return None

    def submit_approval(
        self, package_id: str, reviewer_id: str, reviewer_name: str, reviewer_role: str,
        conflict_attested: bool = True, ledger: Any = None, notes: Optional[str] = None,
        conflict_attestation: Optional[bool] = None, **kwargs: Any,
    ) -> Tuple[DecisionPackage, PackageApprovalRecord]:
        """Submits primary or secondary approval under two distinct principals rule."""
        attestation = conflict_attestation if conflict_attestation is not None else conflict_attested
        if not attestation:
            raise ConflictAttestationError()
        pkg = self.get_package(package_id)
        if not pkg:
            raise PackageNotFoundError(f"DecisionPackage '{package_id}' not found.")
        if pkg.status == DualReviewStatus.STALE_INVALIDATED:
            raise StalePackageError(f"Cannot approve stale invalidated package '{package_id}'.")
        if pkg.status == DualReviewStatus.FINAL_APPROVED:
            raise ValueError(f"Package '{package_id}' is already fully approved.")
        if check_counsel_conflict(reviewer_id, pkg.entity_names or []).has_conflict:
            raise ConflictOfInterestError()
        if pkg.status == DualReviewStatus.PENDING_FIRST_REVIEW:
            return self._process_primary(pkg, reviewer_id, reviewer_name, reviewer_role, ledger, notes)
        if pkg.status == DualReviewStatus.FIRST_REVIEW_APPROVED:
            return self._process_secondary(pkg, reviewer_id, reviewer_name, reviewer_role, ledger, notes)
        raise DualReviewError(f"Cannot approve package in status '{pkg.status}'.")

    def _process_primary(
        self, pkg: DecisionPackage, rid: str, rname: str, rrole: str, ledger: Any, notes: Optional[str],
    ) -> Tuple[DecisionPackage, PackageApprovalRecord]:
        pkg.canonical_digest = pkg.compute_digest()
        record = PackageApprovalRecord(
            package_id=pkg.package_id, package_version=pkg.version, package_digest=pkg.canonical_digest,
            reviewer_id=rid, reviewer_name=rname, reviewer_role=rrole,
            is_primary_or_secondary="primary", conflict_attestation=True, notes=notes,
        )
        pkg.primary_approval = record
        pkg.status = DualReviewStatus.FIRST_REVIEW_APPROVED
        pkg.updated_at_utc = datetime.now(timezone.utc).isoformat()
        extra = {"reviewer_id": rid, "reviewer_name": rname, "reviewer_role": rrole, "package_digest": pkg.canonical_digest, "canonical_digest": pkg.canonical_digest, "notes": notes}
        evt = self._emit(ledger, pkg, rid, "FIRST_REVIEW_APPROVED", extra)
        if evt and hasattr(evt, "event_id"):
            record.ledger_event_id = evt.event_id
            record.audit_event_id = evt.event_id
        return pkg, record

    def _process_secondary(
        self, pkg: DecisionPackage, rid: str, rname: str, rrole: str, ledger: Any, notes: Optional[str],
    ) -> Tuple[DecisionPackage, PackageApprovalRecord]:
        if not pkg.primary_approval:
            raise ValueError("Primary approval record missing on FIRST_REVIEW_APPROVED package.")
        if rid == pkg.primary_approval.reviewer_id:
            raise DistinctReviewerError()
        fresh_digest = pkg.compute_digest()
        if fresh_digest != pkg.primary_approval.package_digest:
            raise ValueError(f"Package freshness violation: '{fresh_digest}' != '{pkg.primary_approval.package_digest}'.")
        record = PackageApprovalRecord(
            package_id=pkg.package_id, package_version=pkg.version, package_digest=fresh_digest,
            reviewer_id=rid, reviewer_name=rname, reviewer_role=rrole,
            is_primary_or_secondary="secondary", conflict_attestation=True, notes=notes,
        )
        pkg.secondary_approval = record
        pkg.status = DualReviewStatus.FINAL_APPROVED
        pkg.disposition = CensusDisposition.APPROVED
        self._update_claim_disp(pkg, CensusDisposition.APPROVED)
        pkg.updated_at_utc = datetime.now(timezone.utc).isoformat()
        extra = {"reviewer_1_id": pkg.primary_approval.reviewer_id, "reviewer_2_id": rid, "reviewer_name": rname, "reviewer_role": rrole, "package_digest": fresh_digest, "canonical_digest": fresh_digest, "disposition": CensusDisposition.APPROVED.value, "notes": notes}
        evt = self._emit(ledger, pkg, rid, "DUAL_REVIEW_FINAL_APPROVED", extra)
        if evt and hasattr(evt, "event_id"):
            record.ledger_event_id = evt.event_id
            record.audit_event_id = evt.event_id
        return pkg, record

    def _update_claim_disp(self, pkg: DecisionPackage, disp: CensusDisposition) -> None:
        if pkg.claim is not None:
            if hasattr(pkg.claim, "disposition"):
                pkg.claim.disposition = disp
            elif isinstance(pkg.claim, dict):
                pkg.claim["disposition"] = disp.value

    def invalidate_package_if_material_change(
        self, package_id: str, updated_package_data: Dict[str, Any], reason: str, ledger: Any,
    ) -> Tuple[DecisionPackage, Optional[DecisionPackage]]:
        """Invalidates package and forks Package B if material dependencies shift."""
        pkg = self.get_package(package_id)
        if not pkg:
            raise PackageNotFoundError(f"DecisionPackage '{package_id}' not found.")
        if not is_material_package_change(pkg, updated_package_data):
            apply_non_material_updates(pkg, updated_package_data)
            return pkg, None
        pkg.status = DualReviewStatus.STALE_INVALIDATED
        pkg.updated_at_utc = datetime.now(timezone.utc).isoformat()
        self._update_claim_disp(pkg, CensusDisposition.NEEDS_REVIEW)
        new_pkg = create_superseding_package(pkg, updated_package_data)
        self._packages[new_pkg.package_id] = new_pkg
        extra = {"reason": reason, "superseded_by_package_id": new_pkg.package_id}
        self._emit(ledger, pkg, "system_coordinator", "PACKAGE_STALE_INVALIDATED", extra)
        return pkg, new_pkg

    def invalidate_pending_package(
        self, package_id: str, updated_package_data: Dict[str, Any], reason: str, ledger: Any,
    ) -> Tuple[DecisionPackage, Optional[DecisionPackage]]:
        return self.invalidate_package_if_material_change(package_id, updated_package_data, reason, ledger)


_global_dual_review_coordinator: Optional[DualReviewCoordinator] = None


def get_dual_review_coordinator() -> DualReviewCoordinator:
    """Dependency provider returning singleton DualReviewCoordinator instance."""
    global _global_dual_review_coordinator
    if _global_dual_review_coordinator is None:
        _global_dual_review_coordinator = DualReviewCoordinator()
    return _global_dual_review_coordinator
