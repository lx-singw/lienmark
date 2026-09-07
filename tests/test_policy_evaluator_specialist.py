"""
tests/test_policy_evaluator_specialist.py

Unit tests verifying 4-state policy evaluation and required action mitigations.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest

from backend.core.policy_rules import (
    RULE_GRANT_VERIFICATION,
    RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW,
    RULE_TERRITORY_SCOPE,
    RULE_THEATRICAL_SYNC_PERPETUAL,
    RULE_TRADEMARK_FAIR_USE,
    evaluate_claim_against_policy,
    get_preset_profile_policy,
)
from backend.core.policy_types import (
    LicensingScope,
    PolicyActionRequirement,
    RuleEvaluationStatus,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
    compute_policy_digest,
)


def test_rule_evaluation_status_and_action_enums():
    """Verify 4-state status values and actionable remediation enum values."""
    assert RuleEvaluationStatus.SATISFIED.value == "satisfied"
    assert RuleEvaluationStatus.NOT_SATISFIED.value == "not_satisfied"
    assert RuleEvaluationStatus.UNKNOWN.value == "unknown"
    assert RuleEvaluationStatus.NOT_APPLICABLE.value == "not_applicable"

    assert PolicyActionRequirement.CLARIFICATION.value == "clarification"
    assert PolicyActionRequirement.AGREEMENT_AMENDMENT.value == "agreement_amendment"
    assert PolicyActionRequirement.COUNSEL_REVIEW.value == "counsel_review"
    assert PolicyActionRequirement.SECOND_REVIEW.value == "second_review"
    assert PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER.value == "authorized_policy_waiver"


def test_rule_theatrical_sync_perpetual_demoted_to_studio_selection():
    """Verify Theatrical Worldwide Perpetual is studio-selectable, not hardcoded."""
    music_claim = {"category": "music", "term": "3 years", "territory": "worldwide", "has_agreement": True}

    # Major theatrical mandates perpetual theatrical
    theatrical_policy = get_preset_profile_policy("org_test", StudioProfileType.MAJOR_THEATRICAL)
    res_theatrical = evaluate_claim_against_policy(music_claim, theatrical_policy)
    item_theatrical = next(i for i in res_theatrical.rule_evaluations if i.rule_code == RULE_THEATRICAL_SYNC_PERPETUAL)
    assert item_theatrical.status == RuleEvaluationStatus.NOT_SATISFIED
    assert PolicyActionRequirement.AGREEMENT_AMENDMENT in item_theatrical.required_actions

    # Streamer exclusive does not mandate perpetual theatrical -> NOT_APPLICABLE
    streamer_policy = get_preset_profile_policy("org_test", StudioProfileType.STREAMER_EXCLUSIVE)
    res_streamer = evaluate_claim_against_policy(music_claim, streamer_policy)
    item_streamer = next(i for i in res_streamer.rule_evaluations if i.rule_code == RULE_THEATRICAL_SYNC_PERPETUAL)
    assert item_streamer.status == RuleEvaluationStatus.NOT_APPLICABLE
    assert item_streamer.applicability_reason is not None


def test_rule_trademark_fair_use_vetted_and_unvetted():
    """Verify commercial trademark fair-use gating with release or nominative exemption."""
    policy = get_preset_profile_policy("org_test", StudioProfileType.MAJOR_THEATRICAL)

    # 1. Unvetted fair use -> NOT_SATISFIED
    unvetted = {"category": "trademark", "stance": "fair_use", "has_executed_release": False, "has_agreement": True}
    res_unvetted = evaluate_claim_against_policy(unvetted, policy)
    item_unvetted = next(i for i in res_unvetted.rule_evaluations if i.rule_code == RULE_TRADEMARK_FAIR_USE)
    assert item_unvetted.status == RuleEvaluationStatus.NOT_SATISFIED
    assert PolicyActionRequirement.COUNSEL_REVIEW in item_unvetted.required_actions
    assert PolicyActionRequirement.AUTHORIZED_POLICY_WAIVER in item_unvetted.required_actions

    # 2. Nominative exemption -> SATISFIED
    vetted = {"category": "trademark", "stance": "fair_use", "is_nominative_exemption": True, "has_agreement": True}
    res_vetted = evaluate_claim_against_policy(vetted, policy)
    item_vetted = next(i for i in res_vetted.rule_evaluations if i.rule_code == RULE_TRADEMARK_FAIR_USE)
    assert item_vetted.status == RuleEvaluationStatus.SATISFIED


def test_rule_grant_verification_missing_facts_fail_closed():
    """Verify missing facts fail-closed to UNKNOWN with CLARIFICATION and COUNSEL_REVIEW."""
    policy = get_preset_profile_policy("org_test", StudioProfileType.MAJOR_THEATRICAL)

    # Claim with no agreement, no grant, no exemption
    missing_artwork = {"category": "artwork", "description": "Oil painting in restaurant"}
    res = evaluate_claim_against_policy(missing_artwork, policy)

    grant_item = next(i for i in res.rule_evaluations if i.rule_code == RULE_GRANT_VERIFICATION)
    assert grant_item.status == RuleEvaluationStatus.UNKNOWN
    assert PolicyActionRequirement.CLARIFICATION in grant_item.required_actions
    assert PolicyActionRequirement.COUNSEL_REVIEW in grant_item.required_actions

    # Composite evaluation must be UNKNOWN and NOT compliant
    assert res.overall_status == RuleEvaluationStatus.UNKNOWN
    assert res.is_compliant is False


def test_promotional_trailer_second_review_and_triple_finding_scenario():
    """Verify promotional trailer cue with unknown grant, excluded territory, and 2nd review."""
    policy = get_preset_profile_policy("org_test", StudioProfileType.MAJOR_THEATRICAL)

    trailer_cue = {
        "category": "music",
        "description": "Trailer teaser orchestral cue",
        "scope": "promotional_trailer",
        "permission_unknown": True,
        "excluded_territories": ["emea"],
        "territory": "worldwide",
    }
    res = evaluate_claim_against_policy(trailer_cue, policy)

    # Surface finding 1: permission unknown
    grant_item = next(i for i in res.rule_evaluations if i.rule_code == RULE_GRANT_VERIFICATION)
    assert grant_item.status == RuleEvaluationStatus.UNKNOWN
    assert PolicyActionRequirement.CLARIFICATION in grant_item.required_actions

    # Surface finding 2: territory excluded
    terr_item = next(i for i in res.rule_evaluations if i.rule_code == RULE_TERRITORY_SCOPE)
    assert terr_item.status == RuleEvaluationStatus.NOT_SATISFIED
    assert PolicyActionRequirement.AGREEMENT_AMENDMENT in terr_item.required_actions

    # Surface finding 3: trailer second review required
    trailer_item = next(i for i in res.rule_evaluations if i.rule_code == RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW)
    assert trailer_item.status == RuleEvaluationStatus.NOT_SATISFIED
    assert PolicyActionRequirement.SECOND_REVIEW in trailer_item.required_actions

    # Consolidated actions must contain all actionable next-steps
    assert PolicyActionRequirement.CLARIFICATION in res.required_actions
    assert PolicyActionRequirement.COUNSEL_REVIEW in res.required_actions
    assert PolicyActionRequirement.AGREEMENT_AMENDMENT in res.required_actions
    assert PolicyActionRequirement.SECOND_REVIEW in res.required_actions
    assert res.overall_status == RuleEvaluationStatus.NOT_SATISFIED
    assert res.is_compliant is False


def test_composite_evaluation_unknown_status_and_digest():
    """Verify composite status UNKNOWN when unknown present and none NOT_SATISFIED, plus digest."""
    policy = get_preset_profile_policy("org_test", StudioProfileType.MAJOR_THEATRICAL)

    # Valid territories and non-trailer non-music, but missing agreement
    claim = {
        "category": "prop",
        "description": "Antique clock",
        "territory": "worldwide",
        "permission_unknown": True,
    }
    res = evaluate_claim_against_policy(claim, policy)
    assert res.overall_status == RuleEvaluationStatus.UNKNOWN
    assert res.is_compliant is False
    assert len(res.effective_policy_digest) == 64
    assert res.effective_policy_digest == compute_policy_digest(policy)
    assert res.effective_policy_version == "1.0"
