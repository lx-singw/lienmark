"""
backend/core/policy_rules.py

Preset profiles, multi-tier inheritance resolution, and statutory cascade rules.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from backend.core.policy_types import (
    LicensingScope,
    PolicyEvaluationResult,
    PolicyViolation,
    ProductionPolicyOverride,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
)


def _build_major_theatrical(pid: str, org_id: str, now: str) -> StudioPolicyConfig:
    """Builds preset for major theatrical profile."""
    scopes = [
        LicensingScope.THEATRICAL, LicensingScope.SVOD, LicensingScope.AVOD,
        LicensingScope.LINEAR_BROADCAST, LicensingScope.IN_FLIGHT,
        LicensingScope.PROMOTIONAL_TRAILER,
    ]
    return StudioPolicyConfig(
        policy_id=pid, org_id=org_id, profile_type=StudioProfileType.MAJOR_THEATRICAL,
        required_media_scopes=scopes, distribution_territories=[TerritoryScope.WORLDWIDE],
        mandatory_perpetual_for_theatrical=True, prohibit_unvetted_trademark_fair_use=True,
        risk_tolerance_threshold=0.70, created_at_utc=now, updated_at_utc=now,
    )


def _build_streamer_exclusive(pid: str, org_id: str, now: str) -> StudioPolicyConfig:
    """Builds preset for streamer exclusive profile."""
    scopes = [LicensingScope.SVOD, LicensingScope.AVOD, LicensingScope.PROMOTIONAL_TRAILER]
    return StudioPolicyConfig(
        policy_id=pid, org_id=org_id, profile_type=StudioProfileType.STREAMER_EXCLUSIVE,
        required_media_scopes=scopes, distribution_territories=[TerritoryScope.WORLDWIDE],
        mandatory_perpetual_for_theatrical=False, prohibit_unvetted_trademark_fair_use=True,
        risk_tolerance_threshold=0.70, created_at_utc=now, updated_at_utc=now,
    )


def _build_festival_acquisition(pid: str, org_id: str, now: str) -> StudioPolicyConfig:
    """Builds preset for festival acquisition profile."""
    scopes = [LicensingScope.THEATRICAL, LicensingScope.PROMOTIONAL_TRAILER]
    return StudioPolicyConfig(
        policy_id=pid, org_id=org_id, profile_type=StudioProfileType.FESTIVAL_ACQUISITION,
        required_media_scopes=scopes,
        distribution_territories=[TerritoryScope.NORTH_AMERICA, TerritoryScope.EMEA],
        mandatory_perpetual_for_theatrical=False, prohibit_unvetted_trademark_fair_use=False,
        risk_tolerance_threshold=0.85, created_at_utc=now, updated_at_utc=now,
    )


def get_preset_profile_policy(
    org_id: str,
    profile_type: StudioProfileType = StudioProfileType.MAJOR_THEATRICAL,
) -> StudioPolicyConfig:
    """Factory returning baseline policy configuration for studio archetype."""
    now = datetime.now(timezone.utc).isoformat()
    pid = f"pol_{org_id}_{profile_type.value}"
    if profile_type == StudioProfileType.MAJOR_THEATRICAL:
        return _build_major_theatrical(pid, org_id, now)
    if profile_type == StudioProfileType.STREAMER_EXCLUSIVE:
        return _build_streamer_exclusive(pid, org_id, now)
    if profile_type == StudioProfileType.FESTIVAL_ACQUISITION:
        return _build_festival_acquisition(pid, org_id, now)
    return StudioPolicyConfig(
        policy_id=pid, org_id=org_id, profile_type=StudioProfileType.CUSTOM,
        required_media_scopes=[LicensingScope.SVOD, LicensingScope.PROMOTIONAL_TRAILER],
        distribution_territories=[TerritoryScope.NORTH_AMERICA],
        mandatory_perpetual_for_theatrical=False, prohibit_unvetted_trademark_fair_use=True,
        risk_tolerance_threshold=0.70, created_at_utc=now, updated_at_utc=now,
    )


def resolve_effective_policy(
    base_policy: StudioPolicyConfig,
    override: Optional[ProductionPolicyOverride] = None,
) -> StudioPolicyConfig:
    """Merges studio organization baseline with production-level override."""
    if override is None:
        return base_policy

    scopes = (
        override.overridden_media_scopes
        if override.overridden_media_scopes is not None
        else base_policy.required_media_scopes
    )
    territories = (
        override.overridden_territories
        if override.overridden_territories is not None
        else base_policy.distribution_territories
    )
    prohibit_tm = (
        not override.allow_trademark_fair_use
        if override.allow_trademark_fair_use is not None
        else base_policy.prohibit_unvetted_trademark_fair_use
    )
    return StudioPolicyConfig(
        policy_id=f"{base_policy.policy_id}#override-{override.override_id}",
        org_id=base_policy.org_id, profile_type=base_policy.profile_type,
        required_media_scopes=scopes, distribution_territories=territories,
        mandatory_perpetual_for_theatrical=base_policy.mandatory_perpetual_for_theatrical,
        prohibit_unvetted_trademark_fair_use=prohibit_tm,
        risk_tolerance_threshold=base_policy.risk_tolerance_threshold,
        created_at_utc=base_policy.created_at_utc, updated_at_utc=override.created_at_utc,
    )


def _get_claim_field(claim: Any, *names: str, default: Any = None) -> Any:
    """Safely extracts field value across dicts, Pydantic models, or objects."""
    if isinstance(claim, dict):
        for name in names:
            if name in claim and claim[name] is not None:
                return claim[name]
    for name in names:
        if hasattr(claim, name):
            val = getattr(claim, name)
            if val is not None:
                return val
    return default


def _is_music_sync(claim: Any) -> bool:
    """Determines whether claim involves music or synchronization rights."""
    cat = str(_get_claim_field(claim, "category", "claim_category", "asset_type", default="")).lower()
    desc = str(_get_claim_field(claim, "extracted_description", "description", "scope", default="")).lower()
    return any(k in cat for k in ("music", "sync", "score", "composition")) or any(k in desc for k in ("music", "sync", "song"))


def _is_trademark(claim: Any) -> bool:
    """Determines whether claim represents a commercial trademark or brand."""
    cat = str(_get_claim_field(claim, "category", "claim_category", "asset_type", default="")).lower()
    desc = str(_get_claim_field(claim, "extracted_description", "description", default="")).lower()
    return any(k in cat for k in ("brand", "trademark", "logo")) or any(k in desc for k in ("trademark", "brand", "logo"))


def _check_theatrical_sync(claim: Any, policy: StudioPolicyConfig) -> List[PolicyViolation]:
    """Statutory Rule 1: Worldwide Perpetual mandatory for theatrical sync."""
    if not (policy.mandatory_perpetual_for_theatrical and LicensingScope.THEATRICAL in policy.required_media_scopes):
        return []
    if not _is_music_sync(claim):
        return []

    term = str(_get_claim_field(claim, "term", "grant_term", "duration", default="")).strip().lower()
    is_perp = any(p in term for p in ("perpetual", "perpetuity", "in perpetuity")) or _get_claim_field(claim, "is_perpetual", default=False) is True
    terr = str(_get_claim_field(claim, "territory", "territories", default="")).strip().lower()
    is_ww = "worldwide" in terr or "global" in terr or TerritoryScope.WORLDWIDE.value in terr

    if not (is_perp and is_ww):
        return [PolicyViolation(
            rule_code="THEATRICAL_PERPETUAL_REQUIRED", severity="CRITICAL",
            message="Theatrical sync licensing requires Worldwide Perpetual grant under studio policy.",
            remedy="Negotiate and execute a Worldwide Perpetual synchronization license agreement.",
        )]
    return []


def _check_trademark_fair_use(claim: Any, policy: StudioPolicyConfig) -> List[PolicyViolation]:
    """Statutory Rule 2: Commercial trademarks prohibit unvetted fair-use claims."""
    if not policy.prohibit_unvetted_trademark_fair_use or not _is_trademark(claim):
        return []

    stance = str(_get_claim_field(claim, "stance", "defense", "legal_basis", default="")).lower()
    claims_fu = "fair_use" in stance or "fair use" in stance or _get_claim_field(claim, "fair_use_claimed", "is_fair_use", default=False) is True
    if not claims_fu:
        return []

    has_release = any(_get_claim_field(claim, f, default=False) is True for f in ("has_executed_release", "executed_release", "has_release", "release_executed"))
    has_exemption = any(_get_claim_field(claim, f, default=False) is True for f in ("is_nominative_exemption", "nominative_exemption", "is_vetted"))
    if not (has_release or has_exemption):
        return [PolicyViolation(
            rule_code="TRADEMARK_FAIR_USE_PROHIBITED", severity="HIGH",
            message="Commercial trademark fair-use claims prohibited without executed release or nominative exemption.",
            remedy="Secure an executed trademark license or formal legal counsel nominative fair-use sign-off.",
        )]
    return []


def _check_territory_scope(claim: Any, policy: StudioPolicyConfig) -> List[PolicyViolation]:
    """Statutory Rule 3: Distribution territory exclusions check."""
    raw_excl = _get_claim_field(claim, "excluded_territories", "territory_exclusions", "exclusions", default=[])
    excl_set: Set[str] = {str(x).lower().replace("territoryscope.", "") for x in (raw_excl if isinstance(raw_excl, (list, set, tuple)) else [raw_excl])}

    raw_granted = _get_claim_field(claim, "territories", "granted_territories", default=None)
    granted_set: Optional[Set[str]] = None
    if raw_granted is not None:
        granted_set = {str(x).lower().replace("territoryscope.", "") for x in (raw_granted if isinstance(raw_granted, (list, set, tuple)) else [raw_granted])}
        if any("worldwide" in g or "global" in g for g in granted_set):
            granted_set = None

    for req in policy.distribution_territories:
        val = req.value.lower()
        if val in excl_set or (req == TerritoryScope.WORLDWIDE and len(excl_set) > 0):
            return [PolicyViolation(
                rule_code="TERRITORY_EXCLUSION_MISMATCH", severity="HIGH",
                message=f"Distribution territory exclusion detected: required territory '{req.value}' is explicitly excluded.",
                remedy="Negotiate territorial rider removing territorial carve-outs.",
            )]
        if granted_set is not None and val not in granted_set:
            return [PolicyViolation(
                rule_code="TERRITORY_EXCLUSION_MISMATCH", severity="HIGH",
                message=f"Distribution territory deficiency: required territory '{req.value}' missing from license grant.",
                remedy="Expand territorial grant to encompass all mandatory distribution territories.",
            )]
    return []


def evaluate_claim_against_policy(
    claim: Any,
    policy: StudioPolicyConfig,
) -> PolicyEvaluationResult:
    """Evaluates intellectual property claim against effective studio policy."""
    violations: List[PolicyViolation] = []
    violations.extend(_check_theatrical_sync(claim, policy))
    violations.extend(_check_trademark_fair_use(claim, policy))
    violations.extend(_check_territory_scope(claim, policy))

    is_comp = len(violations) == 0
    return PolicyEvaluationResult(
        is_compliant=is_comp,
        violations=violations,
        effective_policy_id=policy.policy_id,
        requires_special_waiver=not is_comp,
    )
