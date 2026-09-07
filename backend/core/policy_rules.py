"""
backend/core/policy_rules.py

Preset profiles, inheritance resolution, and 4-state policy evaluation rules.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from backend.core.policy_types import (
    LicensingScope,
    PolicyActionRequirement,
    PolicyEvaluationResult,
    PolicyViolation,
    ProductionPolicyOverride,
    RuleEvaluationItem,
    RuleEvaluationStatus,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
    compute_policy_digest,
)

RULE_THEATRICAL_SYNC_PERPETUAL = "RULE_THEATRICAL_SYNC_PERPETUAL"
RULE_TRADEMARK_FAIR_USE = "RULE_TRADEMARK_FAIR_USE"
RULE_TERRITORY_SCOPE = "RULE_TERRITORY_SCOPE"
RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW = "RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW"
RULE_GRANT_VERIFICATION = "RULE_GRANT_VERIFICATION"

_VL = {
    RULE_THEATRICAL_SYNC_PERPETUAL: ("THEATRICAL_PERPETUAL_REQUIRED", "CRITICAL", "Negotiate Worldwide Perpetual synchronization license agreement."),
    RULE_TRADEMARK_FAIR_USE: ("TRADEMARK_FAIR_USE_PROHIBITED", "HIGH", "Secure executed trademark license or formal counsel nominative fair-use sign-off."),
    RULE_TERRITORY_SCOPE: ("TERRITORY_EXCLUSION_MISMATCH", "HIGH", "Expand territorial grant to encompass all mandatory distribution territories."),
    RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW: ("SECOND_REVIEW_REQUIRED", "HIGH", "Submit promotional trailer cue for secondary counsel review."),
    RULE_GRANT_VERIFICATION: ("GRANT_VERIFICATION_REQUIRED", "HIGH", "Locate executed grant documentation or seek legal counsel clarification."),
}

_PRESETS = {
    StudioProfileType.MAJOR_THEATRICAL: (list(LicensingScope), [TerritoryScope.WORLDWIDE], True, True, 0.70),
    StudioProfileType.STREAMER_EXCLUSIVE: ([LicensingScope.SVOD, LicensingScope.AVOD, LicensingScope.PROMOTIONAL_TRAILER], [TerritoryScope.WORLDWIDE], False, True, 0.70),
    StudioProfileType.FESTIVAL_ACQUISITION: ([LicensingScope.THEATRICAL, LicensingScope.PROMOTIONAL_TRAILER], [TerritoryScope.NORTH_AMERICA, TerritoryScope.EMEA], False, False, 0.85),
}


def _make_item(code: str, status: RuleEvaluationStatus, actions: List[PolicyActionRequirement], facts: Dict[str, Any], exp: str, reason: Optional[str] = None) -> RuleEvaluationItem:
    """Helper constructing validated RuleEvaluationItem."""
    return RuleEvaluationItem(rule_code=code, status=status, required_actions=actions, relevant_facts=facts, explanation=exp, applicability_reason=reason)


def get_preset_profile_policy(org_id: str, profile_type: StudioProfileType = StudioProfileType.MAJOR_THEATRICAL) -> StudioPolicyConfig:
    """Factory returning baseline policy configuration for studio archetype."""
    now = datetime.now(timezone.utc).isoformat()
    scopes, terrs, perp, tm, risk = _PRESETS.get(profile_type, ([LicensingScope.SVOD, LicensingScope.PROMOTIONAL_TRAILER], [TerritoryScope.NORTH_AMERICA], False, True, 0.70))
    return StudioPolicyConfig(
        policy_id=f"pol_{org_id}_{profile_type.value}", org_id=org_id, profile_type=profile_type,
        required_media_scopes=list(scopes), distribution_territories=list(terrs),
        mandatory_perpetual_for_theatrical=perp, prohibit_unvetted_trademark_fair_use=tm,
        risk_tolerance_threshold=risk, created_at_utc=now, updated_at_utc=now,
    )


def resolve_effective_policy(base_policy: StudioPolicyConfig, override: Optional[ProductionPolicyOverride] = None) -> StudioPolicyConfig:
    """Merges studio organization baseline with production-level override."""
    if override is None:
        return base_policy
    scopes = override.overridden_media_scopes if override.overridden_media_scopes is not None else base_policy.required_media_scopes
    terrs = override.overridden_territories if override.overridden_territories is not None else base_policy.distribution_territories
    prohibit_tm = (not override.allow_trademark_fair_use) if override.allow_trademark_fair_use is not None else base_policy.prohibit_unvetted_trademark_fair_use
    req_tr = override.require_promotional_trailer_second_review if override.require_promotional_trailer_second_review is not None else getattr(base_policy, "require_promotional_trailer_second_review", True)
    return StudioPolicyConfig(
        policy_id=f"{base_policy.policy_id}#override-{override.override_id}",
        org_id=base_policy.org_id, profile_type=base_policy.profile_type, version=getattr(base_policy, "version", "1.0"),
        required_media_scopes=scopes, distribution_territories=terrs,
        mandatory_perpetual_for_theatrical=base_policy.mandatory_perpetual_for_theatrical,
        prohibit_unvetted_trademark_fair_use=prohibit_tm, require_promotional_trailer_second_review=req_tr,
        risk_tolerance_threshold=base_policy.risk_tolerance_threshold,
        created_at_utc=base_policy.created_at_utc, updated_at_utc=override.created_at_utc,
    )


def _get_claim_field(claim: Any, *names: str, default: Any = None) -> Any:
    """Safely extracts field value across dicts, Pydantic models, or objects."""
    for n in names:
        if isinstance(claim, dict) and claim.get(n) is not None:
            return claim[n]
        if hasattr(claim, n) and getattr(claim, n) is not None:
            return getattr(claim, n)
    return default


def _is_music_sync(claim: Any) -> bool:
    """Determines whether claim involves music or synchronization rights."""
    txt = f"{_get_claim_field(claim, 'category', 'claim_category', 'asset_type', default='')} {_get_claim_field(claim, 'description', 'scope', default='')}".lower()
    return any(k in txt for k in ("music", "sync", "score", "composition", "song"))


def _is_trademark(claim: Any) -> bool:
    """Determines whether claim represents a commercial trademark or brand."""
    txt = f"{_get_claim_field(claim, 'category', 'claim_category', 'asset_type', default='')} {_get_claim_field(claim, 'description', default='')}".lower()
    return any(k in txt for k in ("brand", "trademark", "logo"))


def _is_trailer(claim: Any) -> bool:
    """Determines if claim is designated for promotional trailer usage."""
    txt = f"{_get_claim_field(claim, 'scope', 'media_scope', 'usage', 'description', default='')}".lower()
    scopes = [str(s).lower() for s in (_get_claim_field(claim, "scopes", "media_scopes", default=[]) or [])]
    return _get_claim_field(claim, "is_promotional_trailer", "trailer", default=False) is True or any("trailer" in s for s in scopes) or "trailer" in txt


def _eval_theatrical_sync_perpetual(claim: Any, policy: StudioPolicyConfig) -> RuleEvaluationItem:
    """Selected studio rule: theatrical music sync must have Worldwide Perpetual grant."""
    studio_selected = policy.mandatory_perpetual_for_theatrical and LicensingScope.THEATRICAL in policy.required_media_scopes
    if not (studio_selected and _is_music_sync(claim)):
        return _make_item(RULE_THEATRICAL_SYNC_PERPETUAL, RuleEvaluationStatus.NOT_APPLICABLE, [], {"claim_is_music": _is_music_sync(claim)},
                          "Theatrical sync perpetual term not applicable.", "Claim is not music sync or policy does not mandate perpetual theatrical scope.")
    term = str(_get_claim_field(claim, "term", "grant_term", "duration", default="")).strip().lower()
    is_perp = any(p in term for p in ("perpetual", "perpetuity", "in perpetuity")) or _get_claim_field(claim, "is_perpetual", default=False) is True
    terr = str(_get_claim_field(claim, "territory", "territories", default="")).strip().lower()
    is_ww = "worldwide" in terr or "global" in terr or TerritoryScope.WORLDWIDE.value in terr
    facts = {"term": term, "territory": terr, "is_perpetual": is_perp, "is_worldwide": is_ww}
    if is_perp and is_ww:
        return _make_item(RULE_THEATRICAL_SYNC_PERPETUAL, RuleEvaluationStatus.SATISFIED, [], facts, "Theatrical music sync has verified Worldwide Perpetual grant.")
    return _make_item(RULE_THEATRICAL_SYNC_PERPETUAL, RuleEvaluationStatus.NOT_SATISFIED,
                      [PolicyActionRequirement.AGREEMENT_AMENDMENT, PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER], facts,
                      "Theatrical sync licensing requires Worldwide Perpetual grant under studio policy.")


def _eval_trademark_fair_use(claim: Any, policy: StudioPolicyConfig) -> RuleEvaluationItem:
    """Commercial trademarks prohibit unvetted fair use without executed release or nominative exemption."""
    if not policy.prohibit_unvetted_trademark_fair_use or not _is_trademark(claim):
        return _make_item(RULE_TRADEMARK_FAIR_USE, RuleEvaluationStatus.NOT_APPLICABLE, [], {"claim_is_trademark": _is_trademark(claim)},
                          "Trademark fair-use vetting is not applicable.", "Claim is not trademark or policy permits unvetted fair use.")
    stance = str(_get_claim_field(claim, "stance", "defense", "legal_basis", default="")).lower()
    if not ("fair_use" in stance or "fair use" in stance or _get_claim_field(claim, "fair_use_claimed", "is_fair_use", default=False) is True):
        return _make_item(RULE_TRADEMARK_FAIR_USE, RuleEvaluationStatus.SATISFIED, [], {"claims_fair_use": False}, "Trademark claim does not rely on fair-use doctrine.")
    has_rel = any(_get_claim_field(claim, f, default=False) is True for f in ("has_executed_release", "executed_release", "has_release", "release_executed"))
    has_exm = any(_get_claim_field(claim, f, default=False) is True for f in ("is_nominative_exemption", "nominative_exemption", "is_vetted"))
    facts = {"claims_fair_use": True, "has_release": has_rel, "has_exemption": has_exm}
    if has_rel or has_exm:
        return _make_item(RULE_TRADEMARK_FAIR_USE, RuleEvaluationStatus.SATISFIED, [], facts, "Commercial trademark fair use supported by executed release or nominative exemption.")
    return _make_item(RULE_TRADEMARK_FAIR_USE, RuleEvaluationStatus.NOT_SATISFIED,
                      [PolicyActionRequirement.AGREEMENT_AMENDMENT, PolicyActionRequirement.COUNSEL_REVIEW, PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER],
                      facts, "Commercial trademark fair-use claims prohibited without executed release or nominative exemption.")


def _eval_territory_scope(claim: Any, policy: StudioPolicyConfig) -> RuleEvaluationItem:
    """Rights grant must cover policy distribution territories."""
    if not policy.distribution_territories:
        return _make_item(RULE_TERRITORY_SCOPE, RuleEvaluationStatus.NOT_APPLICABLE, [], {}, "No distribution territories configured.", "Policy has no mandatory distribution territories.")
    raw_excl = _get_claim_field(claim, "excluded_territories", "territory_exclusions", "exclusions", default=[])
    excl_set = {str(x).lower().replace("territoryscope.", "") for x in (raw_excl if isinstance(raw_excl, (list, set, tuple)) else [raw_excl])} - {""}
    raw_gr = _get_claim_field(claim, "territories", "granted_territories", default=None)
    gr_set = {str(x).lower().replace("territoryscope.", "") for x in (raw_gr if isinstance(raw_gr, (list, set, tuple)) else [raw_gr])} - {""} if raw_gr is not None else None
    if gr_set is not None and any("worldwide" in g or "global" in g for g in gr_set):
        gr_set = None
    for req in policy.distribution_territories:
        val = req.value.lower()
        if val in excl_set or (req == TerritoryScope.WORLDWIDE and len(excl_set) > 0):
            return _make_item(RULE_TERRITORY_SCOPE, RuleEvaluationStatus.NOT_SATISFIED, [PolicyActionRequirement.AGREEMENT_AMENDMENT, PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER],
                              {"excluded_territories": list(excl_set), "required_territory": req.value}, f"Distribution territory exclusion detected: required territory '{req.value}' is explicitly excluded.")
        if gr_set is not None and val not in gr_set:
            return _make_item(RULE_TERRITORY_SCOPE, RuleEvaluationStatus.NOT_SATISFIED, [PolicyActionRequirement.AGREEMENT_AMENDMENT, PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER],
                              {"granted_territories": list(gr_set), "required_territory": req.value}, f"Distribution territory deficiency: required territory '{req.value}' missing from license grant.")
    return _make_item(RULE_TERRITORY_SCOPE, RuleEvaluationStatus.SATISFIED, [], {"policy_territories": [t.value for t in policy.distribution_territories]}, "Rights grant covers all mandatory distribution territories.")


def _eval_promotional_trailer_second_review(claim: Any, policy: StudioPolicyConfig) -> RuleEvaluationItem:
    """If asset is used in a promotional trailer and policy requires second review, trigger SECOND_REVIEW action."""
    policy_req = getattr(policy, "require_promotional_trailer_second_review", True)
    is_trl = _is_trailer(claim)
    if not (is_trl and policy_req):
        return _make_item(RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW, RuleEvaluationStatus.NOT_APPLICABLE, [], {"is_trailer": is_trl},
                          "Promotional trailer second review not applicable.", "Non-trailer usage or second review not mandated by policy.")
    has_2nd = any(_get_claim_field(claim, f, default=False) is True for f in ("second_review_approved", "second_review_completed", "has_second_review"))
    facts = {"second_review_approved": has_2nd, "is_promotional_trailer": True}
    if has_2nd:
        return _make_item(RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW, RuleEvaluationStatus.SATISFIED, [], facts, "Promotional trailer secondary review completed and signed off.")
    return _make_item(RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW, RuleEvaluationStatus.NOT_SATISFIED, [PolicyActionRequirement.SECOND_REVIEW], facts,
                      "Promotional trailer usage requires secondary review sign-off.")


def _eval_grant_verification(claim: Any, policy: StudioPolicyConfig) -> RuleEvaluationItem:
    """Checks whether valid grant or license exists; fails-closed to UNKNOWN if facts missing."""
    perm_st = str(_get_claim_field(claim, "permission_status", "grant_status", default="")).lower()
    has_agr = _get_claim_field(claim, "has_agreement", "agreement_on_file", "has_license", "license_on_file", default=None)
    agr_id = _get_claim_field(claim, "agreement_id", "license_id", "contract_id", default=None)
    perm_unk = _get_claim_field(claim, "permission_unknown", default=False) is True
    term = str(_get_claim_field(claim, "term", "grant_term", default="")).strip()
    is_exm = any(_get_claim_field(claim, f, default=False) is True for f in ("is_public_domain", "public_domain", "is_nominative_exemption", "nominative_exemption", "is_de_minimis", "de_minimis"))
    legal_basis = str(_get_claim_field(claim, "legal_basis", "defense", "exemption", default="")).lower()
    has_exm = is_exm or any(b in legal_basis for b in ("public_domain", "de_minimis", "nominative"))
    has_grant = ((has_agr is True) or (agr_id is not None and str(agr_id).strip() != "") or perm_st in ("executed", "granted", "valid", "licensed", "cleared", "active")
                 or ((term != "" or _get_claim_field(claim, "territory", "territories", default=None) is not None) and has_agr is not False and perm_st not in ("unknown", "missing", "none")))
    facts = {"has_agreement": has_agr, "permission_status": perm_st, "has_legal_exemption": has_exm}
    if perm_unk or has_agr is False or perm_st in ("unknown", "missing", "none") or (not has_grant and not has_exm):
        return _make_item(RULE_GRANT_VERIFICATION, RuleEvaluationStatus.UNKNOWN,
                          [PolicyActionRequirement.CLARIFICATION, PolicyActionRequirement.COUNSEL_REVIEW], facts,
                          "No executed agreement, license grant, or legal exemption on file; rights status is unknown.")
    return _make_item(RULE_GRANT_VERIFICATION, RuleEvaluationStatus.SATISFIED, [], {"has_grant": True, "legal_exemption": has_exm}, "Valid rights grant or legal exemption verified.")


def _compute_overall_status(evals: List[RuleEvaluationItem]) -> RuleEvaluationStatus:
    """Aggregates rule statuses into composite 4-state outcome."""
    s = {e.status for e in evals}
    if RuleEvaluationStatus.NOT_SATISFIED in s:
        return RuleEvaluationStatus.NOT_SATISFIED
    if RuleEvaluationStatus.UNKNOWN in s:
        return RuleEvaluationStatus.UNKNOWN
    return RuleEvaluationStatus.SATISFIED if RuleEvaluationStatus.SATISFIED in s else RuleEvaluationStatus.NOT_APPLICABLE


def evaluate_claim_against_policy(claim: Any, policy: StudioPolicyConfig) -> PolicyEvaluationResult:
    """Evaluates intellectual property claim against effective studio policy."""
    evals = [
        _eval_grant_verification(claim, policy), _eval_theatrical_sync_perpetual(claim, policy),
        _eval_trademark_fair_use(claim, policy), _eval_territory_scope(claim, policy),
        _eval_promotional_trailer_second_review(claim, policy),
    ]
    overall = _compute_overall_status(evals)
    applicable = [e for e in evals if e.status != RuleEvaluationStatus.NOT_APPLICABLE]
    is_comp = len(applicable) > 0 and all(e.status == RuleEvaluationStatus.SATISFIED for e in applicable)
    actions = list(dict.fromkeys(a for e in evals for a in e.required_actions))
    violations = [
        PolicyViolation(rule_code=_VL.get(e.rule_code, (e.rule_code, "HIGH", ""))[0],
                        severity=_VL.get(e.rule_code, (e.rule_code, "HIGH", ""))[1],
                        message=e.explanation,
                        remedy=_VL.get(e.rule_code, (e.rule_code, "HIGH", ""))[2])
        for e in evals if e.status in (RuleEvaluationStatus.NOT_SATISFIED, RuleEvaluationStatus.UNKNOWN)
    ]
    return PolicyEvaluationResult(
        overall_status=overall, is_compliant=is_comp, rule_evaluations=evals, required_actions=actions,
        effective_policy_id=policy.policy_id, effective_policy_version=getattr(policy, "version", "1.0"),
        effective_policy_digest=compute_policy_digest(policy),
        requires_special_waiver=(not is_comp) or (PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER in actions),
        violations=violations,
    )
