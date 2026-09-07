"""
tests/test_policy_inheritance.py

Sprint 5.1 Acceptance Gate: Studio Policy Inheritance & Statutory Clearance Invariants.
Tests:
- Test 1: RBAC override rejection without Admin role (HTTP 403 / PermissionError)
- Test 2: Multi-tier inheritance cascade across 5 child productions
- Test 3: Statutory regulatory cascade (Rules 1, 2, 3)
- Test 4: CryptographicLedger audit verification (POLICY_OVERRIDE with diffs)
- Test 5: Profile presets (MAJOR_THEATRICAL, STREAMER_EXCLUSIVE, FESTIVAL_ACQUISITION)

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core import (
    LicensingScope,
    PolicyEvaluationResult,
    ProductionPolicyOverride,
    StudioPolicyConfig,
    StudioPolicyEngine,
    StudioProfileType,
    TerritoryScope,
    evaluate_claim_against_policy,
    get_preset_profile_policy,
    resolve_effective_policy,
)
import shutil
from backend.core.rbac import LienmarkRole
from backend.storage.ledger import CryptographicLedger

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_policies():
    """Isolates disk persistence state between test executions."""
    shutil.rmtree("output/policies", ignore_errors=True)
    yield
    shutil.rmtree("output/policies", ignore_errors=True)


def test_1_rbac_override_rejection_without_admin_role():
    """Test 1: Non-admin role attempting override rejected with PermissionError & HTTP 403."""
    engine = StudioPolicyEngine()
    org_id = "org_a24"
    prod_id = "prod_everything_everywhere"
    override = ProductionPolicyOverride(
        override_id="ovr_illegal_bypass_01",
        production_id=prod_id,
        org_id=org_id,
        admin_actor_id="user_non_admin",
        admin_actor_name="Unauthorized Analyst",
        rationale="Attempting to override theatrical sync scope without Admin role",
        overridden_media_scopes=[LicensingScope.SVOD],
    )

    for non_admin_role in [LienmarkRole.ANALYST, LienmarkRole.REVIEWER, LienmarkRole.VIEWER, "producer"]:
        with pytest.raises(PermissionError, match="requires Admin role"):
            engine.apply_production_override(org_id, prod_id, override, actor_role=non_admin_role)

    # API route rejection verification with HTTP 403
    resp = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        headers={"X-User-Role": "analyst", "X-Actor-Role": "analyst", "X-Tenant-ID": org_id},
        json={
            "admin_actor_id": "user_analyst_01",
            "admin_actor_name": "Junior Analyst",
            "actor_role": "analyst",
            "rationale": "Attempting unauthorized theatrical scope waiver",
            "overridden_media_scopes": ["svod"],
        },
    )
    assert resp.status_code == 403
    assert "Admin role" in resp.json()["detail"]


def test_2_multi_tier_cascade_across_five_child_productions():
    """Test 2: Studio org default automatically cascades across 5 distinct child productions."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    org_id = "org_paramount_pictures"
    prods = [f"prod-{i}" for i in range(1, 6)]

    # 1. Verify 5 child productions inherit default Major Theatrical
    default_policy = engine.get_studio_policy(org_id)
    assert default_policy.profile_type == StudioProfileType.MAJOR_THEATRICAL
    for pid in prods:
        eff = engine.get_effective_policy(org_id, pid)
        assert eff.profile_type == StudioProfileType.MAJOR_THEATRICAL
        assert LicensingScope.THEATRICAL in eff.required_media_scopes
        assert TerritoryScope.WORLDWIDE in eff.distribution_territories

    # 2. Modifying studio default cascades to all children without overrides
    updated_org_policy = StudioPolicyConfig(
        policy_id=f"pol_{org_id}_streamer",
        org_id=org_id,
        profile_type=StudioProfileType.STREAMER_EXCLUSIVE,
        required_media_scopes=[LicensingScope.SVOD, LicensingScope.AVOD],
        distribution_territories=[TerritoryScope.WORLDWIDE],
        mandatory_perpetual_for_theatrical=False,
        risk_tolerance_threshold=0.55,
    )
    engine.set_studio_policy(updated_org_policy)

    for pid in prods:
        eff = engine.get_effective_policy(org_id, pid)
        assert eff.profile_type == StudioProfileType.STREAMER_EXCLUSIVE
        assert eff.required_media_scopes == [LicensingScope.SVOD, LicensingScope.AVOD]
        assert eff.risk_tolerance_threshold == 0.55


def test_3_statutory_regulatory_cascade_all_three_rules():
    """Test 3: Verify statutory rules 1, 2, and 3 generate precise policy violations."""
    policy = get_preset_profile_policy("org_universal", StudioProfileType.MAJOR_THEATRICAL)

    # Rule 1: Theatrical sync without Worldwide Perpetual grant
    claim_r1 = {
        "category": "music_sync",
        "description": "Opening montage song clearance",
        "territory": "worldwide",
        "term": "5 years limited",
    }
    res_r1 = evaluate_claim_against_policy(claim_r1, policy)
    assert res_r1.is_compliant is False
    assert any(v.rule_code == "THEATRICAL_PERPETUAL_REQUIRED" for v in res_r1.violations)

    # Rule 2: Commercial trademark claiming fair use without executed release
    claim_r2 = {
        "category": "brand_trademark",
        "description": "Hero uses branded smartphone on camera",
        "stance": "fair_use",
        "has_executed_release": False,
        "is_nominative_exemption": False,
    }
    res_r2 = evaluate_claim_against_policy(claim_r2, policy)
    assert res_r2.is_compliant is False
    assert any(v.rule_code == "TRADEMARK_FAIR_USE_PROHIBITED" for v in res_r2.violations)

    # Rule 3: Distribution territory exclusions (claim restricted while dist is Worldwide)
    claim_r3 = {
        "category": "prop",
        "description": "Historical artwork background photo",
        "excluded_territories": ["emea", "apac"],
        "territories": ["north_america"],
    }
    res_r3 = evaluate_claim_against_policy(claim_r3, policy)
    assert res_r3.is_compliant is False
    assert any(v.rule_code == "TERRITORY_EXCLUSION_MISMATCH" for v in res_r3.violations)


def test_4_cryptographic_ledger_audit_verification():
    """Test 4: Admin override appends POLICY_OVERRIDE event with diffs to CryptographicLedger."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    org_id = "org_sony_pictures"
    prod_id = "prod_spider_noir_s1"
    admin_id = "admin_amy_pascal"

    override = ProductionPolicyOverride(
        override_id="ovr_sony_statutory_01",
        production_id=prod_id,
        org_id=org_id,
        admin_actor_id=admin_id,
        admin_actor_name="Amy Pascal",
        rationale="Executive waiver permitting restricted festival territories",
        overridden_territories=[TerritoryScope.NORTH_AMERICA, TerritoryScope.EMEA],
        allow_trademark_fair_use=True,
        waiver_notes="Full legal sign-off on festival circuit fair use",
    )

    eff = engine.apply_production_override(
        org_id=org_id,
        production_id=prod_id,
        override=override,
        actor_role=LienmarkRole.ADMIN,
    )
    assert eff.distribution_territories == [TerritoryScope.NORTH_AMERICA, TerritoryScope.EMEA]
    assert override.ledger_event_id is not None

    # Inspect immutable ledger entries
    events = ledger.get_events(prod_id)
    assert len(events) == 2  # Genesis + POLICY_OVERRIDE
    event = events[-1]
    assert event.action_type == "POLICY_OVERRIDE"
    assert event.actor_id == admin_id
    assert event.payload["diff"]["after_territories"] == ["north_america", "emea"]
    assert event.payload["diff"]["after_prohibit_tm"] is False

    # Verify cryptographic hash chain integrity
    is_valid, err, count = ledger.verify_chain(prod_id)
    assert is_valid is True
    assert count == 2
    assert err is None


def test_5_profile_presets_matrix():
    """Test 5: Verify profile presets (MAJOR_THEATRICAL, STREAMER_EXCLUSIVE, FESTIVAL_ACQUISITION)."""
    org_id = "org_a24_indie"

    # Preset 1: MAJOR_THEATRICAL
    theatrical = get_preset_profile_policy(org_id, StudioProfileType.MAJOR_THEATRICAL)
    assert theatrical.profile_type == StudioProfileType.MAJOR_THEATRICAL
    assert LicensingScope.THEATRICAL in theatrical.required_media_scopes
    assert TerritoryScope.WORLDWIDE in theatrical.distribution_territories
    assert theatrical.mandatory_perpetual_for_theatrical is True
    assert theatrical.prohibit_unvetted_trademark_fair_use is True
    assert theatrical.risk_tolerance_threshold == 0.70

    # Preset 2: STREAMER_EXCLUSIVE
    streamer = get_preset_profile_policy(org_id, StudioProfileType.STREAMER_EXCLUSIVE)
    assert streamer.profile_type == StudioProfileType.STREAMER_EXCLUSIVE
    assert LicensingScope.SVOD in streamer.required_media_scopes
    assert LicensingScope.THEATRICAL not in streamer.required_media_scopes
    assert streamer.mandatory_perpetual_for_theatrical is False
    assert streamer.prohibit_unvetted_trademark_fair_use is True

    # Preset 3: FESTIVAL_ACQUISITION
    festival = get_preset_profile_policy(org_id, StudioProfileType.FESTIVAL_ACQUISITION)
    assert festival.profile_type == StudioProfileType.FESTIVAL_ACQUISITION
    assert LicensingScope.THEATRICAL in festival.required_media_scopes
    assert TerritoryScope.NORTH_AMERICA in festival.distribution_territories
    assert festival.mandatory_perpetual_for_theatrical is False
    assert festival.prohibit_unvetted_trademark_fair_use is False
    assert festival.risk_tolerance_threshold == 0.85
