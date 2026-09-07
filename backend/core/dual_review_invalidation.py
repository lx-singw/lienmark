"""
backend/core/dual_review_invalidation.py

Material change detection and decision package invalidation engine.
Sprint 5.2: Invalidation rules and package version supersession.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from backend.core.decision_package_types import DecisionPackage, DualReviewStatus


def is_material_package_change(
    package: DecisionPackage,
    updated_data: Dict[str, Any],
) -> bool:
    """Determines whether updated package data introduces a material dependency change."""
    if "is_material" in updated_data:
        return bool(updated_data["is_material"])
    for key, val in updated_data.items():
        if key in ("cut_revision", "cut_version") and val != package.cut_revision:
            return True
        if key in ("policy_version", "policy_id", "effective_policy_version"):
            if val != package.policy_version and val != package.effective_policy_version:
                return True
        if key in ("license_data", "license") and val != package.license_data:
            return True
        if key in ("evidence_data", "evidence") and val != package.evidence_data:
            return True
        if key in ("entity_names", "entities"):
            if sorted(package.entity_names or []) != sorted(val or []):
                return True
        if key == "claim_data" and val != package.claim_data:
            return True
    return False


def apply_non_material_updates(pkg: DecisionPackage, data: Dict[str, Any]) -> None:
    """Applies non-material updates (comments, notes, formatting) without altering digest."""
    if "comment" in data:
        pkg.comments.append(str(data["comment"]))
    if "comments" in data and isinstance(data["comments"], list):
        pkg.comments.extend([str(c) for c in data["comments"]])
    if "notes" in data:
        pkg.notes = str(data["notes"])
    if "formatting_metadata" in data and isinstance(data["formatting_metadata"], dict):
        pkg.formatting_metadata.update(data["formatting_metadata"])
    pkg.updated_at_utc = datetime.now(timezone.utc).isoformat()


def create_superseding_package(
    old_pkg: DecisionPackage,
    updated_data: Dict[str, Any],
) -> DecisionPackage:
    """Creates a new superseded DecisionPackage (version + 1) with refreshed dependencies."""
    cut_rev = updated_data.get("cut_revision", updated_data.get("cut_version", old_pkg.cut_revision))
    new_data = {
        "package_id": f"pkg_{uuid.uuid4().hex[:12]}",
        "claim_id": old_pkg.claim_id,
        "tenant_id": old_pkg.tenant_id,
        "production_id": old_pkg.production_id,
        "version": old_pkg.version + 1,
        "status": DualReviewStatus.PENDING_FIRST_REVIEW,
        "proposed_disposition": "NEEDS_REVIEW",
        "entity_names": updated_data.get("entity_names", updated_data.get("entities", old_pkg.entity_names)),
        "license_data": updated_data.get("license_data", updated_data.get("license", old_pkg.license_data)),
        "evidence_data": updated_data.get("evidence_data", updated_data.get("evidence", old_pkg.evidence_data)),
        "cut_revision": cut_rev or "cut_v1",
        "policy_version": updated_data.get("policy_version", updated_data.get("policy_id", old_pkg.policy_version)),
        "claim_data": updated_data.get("claim_data", old_pkg.claim_data),
        "supersedes_package_id": old_pkg.package_id,
        "claim": old_pkg.claim,
        "primary_approval": None,
        "secondary_approval": None,
    }
    new_pkg = DecisionPackage(**new_data)
    new_pkg.canonical_digest = new_pkg.compute_digest()
    return new_pkg
