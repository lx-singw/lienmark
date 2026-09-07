"""
backend/core/remediation_rules.py

Remediation evaluation rules for statutory clearance:
- Fail-closed evaluation on missing facts (e.g. artwork without grant -> UNKNOWN with CLARIFICATION & COUNSEL_REVIEW)
- Multi-finding evaluation for promotional trailer cues (UNKNOWN + NOT_SATISFIED + SATISFIED)
- Waiver tracking: authorized waivers leave claim awaiting counsel review (never auto-approved)

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from typing import Any, List, Optional, Set

from backend.core.policy_types import (
    LicensingScope,
    PolicyAction,
    PolicyEvaluationResult,
    PolicyViolation,
    ProductionPolicyOverride,
    RuleEvaluationStatus,
    RuleFinding,
    StudioPolicyConfig,
    TerritoryScope,
)


def _get_claim_val(claim: Any, *keys: str, default: Any = None) -> Any:
    """Safely extracts field value across dicts, Pydantic models, or objects."""
    if isinstance(claim, dict):
        for k in keys:
            if k in claim and claim[k] is not None:
                return claim[k]
    for k in keys:
        if hasattr(claim, k):
            val = getattr(claim, k)
            if val is not None:
                return val
    return default


def _check_missing_facts(claim: Any, policy: StudioPolicyConfig) -> List[RuleFinding]:
    """Surfaces UNKNOWN status and required actions when required legal facts are missing."""
    findings: List[RuleFinding] = []
    cat = str(_get_claim_val(claim, "category", "asset_type", default="")).lower()
    
    # 1. Artwork claim without grant or agreement
    if "artwork" in cat or "art" in cat:
        has_grant = _get_claim_val(claim, "has_grant", "has_executed_release", "has_agreement", default=None)
        grant = _get_claim_val(claim, "grant", "agreement", "license", default=None)
        if has_grant is False or (has_grant is None and grant is None):
            findings.append(RuleFinding(
                rule_code="ARTWORK_GRANT_REQUIRED",
                status=RuleEvaluationStatus.UNKNOWN,
                message="Artwork claim lacks executed grant or agreement documentation.",
                required_actions=[PolicyAction.CLARIFICATION, PolicyAction.COUNSEL_REVIEW],
            ))

    # 2. Unknown permission for music/sync cue
    perm = str(_get_claim_val(claim, "permission_status", "permission", default="")).lower()
    is_music = any(k in cat for k in ("music", "sync", "score"))
    if is_music and (perm in ("unknown", "unverified") or _get_claim_val(claim, "has_permission", default=None) is False):
        findings.append(RuleFinding(
            rule_code="MUSIC_PERMISSION_UNKNOWN",
            status=RuleEvaluationStatus.UNKNOWN,
            message="Music cue permission is unknown or unverified.",
            required_actions=[PolicyAction.CLARIFICATION, PolicyAction.COUNSEL_REVIEW],
        ))

    return findings


def _check_territory_findings(claim: Any, policy: StudioPolicyConfig) -> List[RuleFinding]:
    """Surfaces territory mismatch findings and next actions."""
    raw_excl = _get_claim_val(claim, "excluded_territories", "territory_exclusions", default=[])
    excl = [str(x).lower().replace("territoryscope.", "") for x in (raw_excl if isinstance(raw_excl, (list, set, tuple)) else [raw_excl])] if raw_excl else []
    if excl:
        return [RuleFinding(
            rule_code="TERRITORY_EXCLUSION_MISMATCH",
            status=RuleEvaluationStatus.NOT_SATISFIED,
            message=f"Mandatory distribution territory explicitly excluded: {excl}.",
            required_actions=[PolicyAction.TERRITORIAL_RIDER],
        )]
    return []


def _check_second_review_findings(claim: Any, policy: StudioPolicyConfig) -> List[RuleFinding]:
    """Surfaces studio second-review requirement finding and next actions."""
    scope = str(_get_claim_val(claim, "media_scope", "scope", default="")).lower()
    scopes = _get_claim_val(claim, "required_media_scopes", default=[])
    second_req = _get_claim_val(claim, "requires_second_review", "second_review_required", default=False)
    is_promo = "promotional_trailer" in scope or any("promotional" in str(s).lower() for s in scopes)

    if second_req or is_promo:
        return [RuleFinding(
            rule_code="STUDIO_SECOND_REVIEW_TRIGGERED",
            status=RuleEvaluationStatus.SATISFIED,
            message="Promotional trailer placement triggers mandatory studio second-review gate.",
            required_actions=[PolicyAction.SECOND_COUNSEL_REVIEW],
        )]
    return []


def _collect_all_findings(
    claim: Any,
    policy: StudioPolicyConfig,
    base_violations: List[PolicyViolation],
) -> List[RuleFinding]:
    """Gathers all statutory and remediation findings without early exit."""
    findings: List[RuleFinding] = []
    findings.extend(_check_missing_facts(claim, policy))
    findings.extend(_check_territory_findings(claim, policy))
    findings.extend(_check_second_review_findings(claim, policy))

    existing_codes = {f.rule_code for f in findings}
    for v in base_violations:
        if v.rule_code not in existing_codes:
            findings.append(RuleFinding(
                rule_code=v.rule_code,
                status=RuleEvaluationStatus.NOT_SATISFIED,
                message=v.message,
                required_actions=[PolicyAction.COUNSEL_REVIEW],
            ))
    return findings


def evaluate_claim_with_remediation(
    claim: Any,
    policy: StudioPolicyConfig,
    base_violations: List[PolicyViolation],
    override: Optional[ProductionPolicyOverride] = None,
) -> PolicyEvaluationResult:
    """Evaluates intellectual property claim against effective studio policy with remediation tracking."""
    findings = _collect_all_findings(claim, policy, base_violations)
    req_actions: List[PolicyAction] = []
    for f in findings:
        for a in f.required_actions:
            if a not in req_actions:
                req_actions.append(a)

    statuses = {f.status for f in findings}
    has_unknown = RuleEvaluationStatus.UNKNOWN in statuses
    has_not_satisfied = (RuleEvaluationStatus.NOT_SATISFIED in statuses) or (len(base_violations) > 0)
    is_compliant = not has_unknown and not has_not_satisfied

    if has_unknown:
        comp_status = RuleEvaluationStatus.UNKNOWN
    elif has_not_satisfied:
        comp_status = RuleEvaluationStatus.NOT_SATISFIED
    else:
        comp_status = RuleEvaluationStatus.SATISFIED

    has_waiver = override is not None and (
        bool(override.allow_trademark_fair_use)
        or bool(override.overridden_media_scopes)
        or bool(override.overridden_territories)
        or bool(override.waiver_notes)
    )
    awaiting_counsel = has_waiver or (not is_compliant)
    decision = "needs_review" if (has_waiver or not is_compliant) else "approved"

    all_violations = list(base_violations)
    for f in findings:
        if f.status in (RuleEvaluationStatus.UNKNOWN, RuleEvaluationStatus.NOT_SATISFIED):
            if not any(v.rule_code == f.rule_code for v in all_violations):
                all_violations.append(PolicyViolation(
                    rule_code=f.rule_code,
                    severity="CRITICAL" if f.status == RuleEvaluationStatus.UNKNOWN else "HIGH",
                    message=f.message,
                    remedy="; ".join(a.value for a in f.required_actions),
                ))

    return PolicyEvaluationResult(
        is_compliant=is_compliant,
        violations=all_violations,
        effective_policy_id=policy.policy_id,
        requires_special_waiver=not is_compliant,
        status=comp_status,
        findings=findings,
        required_actions=req_actions,
        awaiting_counsel_review=awaiting_counsel,
        decision_status=decision,
    )
