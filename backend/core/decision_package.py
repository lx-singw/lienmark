"""
backend/core/decision_package.py

Deterministic canonical digest calculation, factory methods, supersession lineage,
and material change evaluation for immutable DecisionPackages.
Sprint 5.2: Clearance Decision Packages & Dual-Review Sign-Off.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.core.decision_package_types import (
    DecisionPackage,
    DualReviewStatus,
    PackageApprovalRecord,
)


def _canonicalize_list(items: Sequence[Any]) -> List[Any]:
    """Deterministically normalizes and sorts list items by canonical JSON."""
    if not items:
        return []
    try:
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, default=str))
    except Exception:
        return list(items)


def compute_package_canonical_digest(
    package_data: Dict[str, Any] | DecisionPackage,
) -> str:
    """Computes deterministic SHA-256 over canonically sorted JSON representation of key package content."""
    raw = package_data.model_dump() if hasattr(package_data, "model_dump") else dict(package_data)
    pol_ver = raw.get("effective_policy_version") or raw.get("policy_version") or ""
    pol_dig = raw.get("effective_policy_digest") or raw.get("policy_digest") or ""
    roles = sorted(list(raw.get("required_reviewer_roles") or raw.get("required_roles") or []))
    canonical_repr = {
        "applicability_assessments": _canonicalize_list(raw.get("applicability_assessments") or []),
        "claim_data": raw.get("claim_data") or {},
        "claim_id": str(raw.get("claim_id", "")).strip(),
        "conditions": _canonicalize_list(raw.get("conditions") or []),
        "cut_revision": str(raw.get("cut_revision", "")).strip(),
        "effective_policy_digest": str(pol_dig).strip(),
        "effective_policy_version": str(pol_ver).strip(),
        "evidence_bundle": _canonicalize_list(raw.get("evidence_bundle") or []),
        "evidence_data": raw.get("evidence_data") or {},
        "intended_scope": raw.get("intended_scope") or {},
        "license_data": raw.get("license_data") or {},
        "occurrence_id": str(raw.get("occurrence_id", "")).strip(),
        "proposed_disposition": str(raw.get("proposed_disposition", "")).strip(),
        "rationale": str(raw.get("rationale", "")).strip(),
        "required_reviewer_roles": roles,
        "version": int(raw.get("version", 1)),
    }
    serialized = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def create_decision_package(
    claim_id: str, cut_revision: str, intended_scope: Dict[str, Any],
    proposed_disposition: str, rationale: str, conditions: List[str],
    evidence_bundle: List[Dict[str, Any]], policy_version: str, policy_digest: str,
    required_roles: Optional[List[str]] = None, occurrence_id: Optional[str] = None,
    applicability_assessments: Optional[List[Dict[str, Any]]] = None,
    package_id: Optional[str] = None, version: int = 1,
) -> DecisionPackage:
    """Creates an immutable DecisionPackage with canonical digest and PENDING status."""
    pkg_id = package_id or f"pkg_{uuid.uuid4().hex[:12]}"
    occ_id = occurrence_id if occurrence_id is not None else f"occ_{claim_id}"
    roles = list(required_roles) if required_roles is not None else []
    assessments = list(applicability_assessments or [])
    now_utc = datetime.now(timezone.utc).isoformat()
    pkg_dict = {
        "package_id": pkg_id, "version": version, "claim_id": claim_id, "occurrence_id": occ_id,
        "cut_revision": cut_revision, "intended_scope": intended_scope,
        "proposed_disposition": proposed_disposition, "rationale": rationale,
        "conditions": conditions, "evidence_bundle": evidence_bundle,
        "applicability_assessments": assessments, "effective_policy_version": policy_version,
        "effective_policy_digest": policy_digest, "required_reviewer_roles": roles,
    }
    digest = compute_package_canonical_digest(pkg_dict)
    return DecisionPackage(
        **pkg_dict, canonical_digest=digest, status=DualReviewStatus.PENDING_FIRST_REVIEW,
        primary_approval=None, secondary_approval=None,
        created_at_utc=now_utc, updated_at_utc=now_utc,
    )



def derive_superseded_package(
    base_package: DecisionPackage,
    changed_fields: Dict[str, Any],
    new_version: int,
) -> DecisionPackage:
    """Creates new package version with incremented version and recomputed digest."""
    data = base_package.model_dump()
    data.update(changed_fields)
    data["version"] = new_version
    data["status"] = DualReviewStatus.PENDING_FIRST_REVIEW
    data["primary_approval"] = None
    data["secondary_approval"] = None
    data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    data["canonical_digest"] = compute_package_canonical_digest(data)
    return DecisionPackage(**data)


def _normalize_val(val: Any) -> Any:
    """Normalizes lists, dicts, or scalar values for deterministic comparison."""
    if isinstance(val, (list, set, tuple)):
        return _canonicalize_list(val)
    if isinstance(val, dict):
        return val
    return str(val).strip() if val is not None else ""


def _check_diff(
    diffs: List[str], key: str, val_a: Any, raw_b: Dict[str, Any], aliases: Optional[List[str]] = None
) -> None:
    """Checks whether key or its aliases in raw_b differ from base val_a."""
    candidates = [key] + (aliases or [])
    found = next((k for k in candidates if k in raw_b), None)
    if found is not None:
        norm_a = _normalize_val(val_a)
        norm_b = _normalize_val(raw_b[found])
        str_a = json.dumps(norm_a, sort_keys=True, default=str) if isinstance(norm_a, (dict, list)) else norm_a
        str_b = json.dumps(norm_b, sort_keys=True, default=str) if isinstance(norm_b, (dict, list)) else norm_b
        if str_a != str_b:
            diffs.append(key)


def is_material_package_difference(
    package_a: DecisionPackage,
    package_b_data: Dict[str, Any] | DecisionPackage,
) -> Tuple[bool, List[str]]:
    """Returns whether differences in evidence, scope, cut, conditions, or policy constitute material change."""
    raw_b = package_b_data.model_dump() if hasattr(package_b_data, "model_dump") else dict(package_b_data)
    diffs: List[str] = []
    _check_diff(diffs, "cut_revision", package_a.cut_revision, raw_b)
    _check_diff(diffs, "proposed_disposition", package_a.proposed_disposition, raw_b, ["disposition"])
    _check_diff(diffs, "intended_scope", package_a.intended_scope, raw_b, ["scope"])
    _check_diff(diffs, "conditions", package_a.conditions, raw_b)
    _check_diff(diffs, "evidence_bundle", package_a.evidence_bundle, raw_b, ["evidence"])
    _check_diff(diffs, "effective_policy_version", package_a.effective_policy_version, raw_b, ["policy_version"])
    _check_diff(diffs, "effective_policy_digest", package_a.effective_policy_digest, raw_b, ["policy_digest"])
    _check_diff(diffs, "applicability_assessments", package_a.applicability_assessments, raw_b)
    return len(diffs) > 0, diffs


def apply_package_approval(
    package: DecisionPackage,
    approval: PackageApprovalRecord,
) -> DecisionPackage:
    """Validates and applies a dual-review approval record to a decision package."""
    if approval.package_id != package.package_id:
        raise ValueError(f"Approval package_id '{approval.package_id}' != package '{package.package_id}'")
    if approval.package_version != package.version:
        raise ValueError(f"Approval version {approval.package_version} != package version {package.version}")
    if approval.package_digest != package.canonical_digest:
        raise ValueError("Approval package_digest does not match package canonical_digest")
    if not approval.conflict_attestation:
        raise ValueError("Conflict attestation is required for package approval")

    updated = package.model_copy(deep=True)
    if approval.is_primary_or_secondary == "primary":
        if updated.status != DualReviewStatus.PENDING_FIRST_REVIEW:
            raise ValueError(f"Cannot apply primary approval in status '{updated.status.value}'")
        updated.primary_approval = approval
        updated.status = DualReviewStatus.FIRST_REVIEW_APPROVED
    elif approval.is_primary_or_secondary == "secondary":
        if updated.status != DualReviewStatus.FIRST_REVIEW_APPROVED:
            raise ValueError("Secondary approval requires prior FIRST_REVIEW_APPROVED status")
        if updated.primary_approval and updated.primary_approval.reviewer_id == approval.reviewer_id:
            raise ValueError("Four-eyes violation: secondary reviewer must differ from primary")
        updated.secondary_approval = approval
        updated.status = DualReviewStatus.FINAL_APPROVED

    updated.updated_at_utc = datetime.now(timezone.utc).isoformat()
    return updated


def reject_package(package: DecisionPackage, notes: Optional[str] = None) -> DecisionPackage:
    """Transitions decision package into REJECTED status."""
    updated = package.model_copy(deep=True)
    updated.status = DualReviewStatus.REJECTED
    updated.updated_at_utc = datetime.now(timezone.utc).isoformat()
    return updated


def invalidate_package(package: DecisionPackage, reason: Optional[str] = None) -> DecisionPackage:
    """Transitions decision package into STALE_INVALIDATED status upon upstream change."""
    updated = package.model_copy(deep=True)
    updated.status = DualReviewStatus.STALE_INVALIDATED
    updated.updated_at_utc = datetime.now(timezone.utc).isoformat()
    return updated
