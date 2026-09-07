"""
tests/test_policy_engine.py

Comprehensive unit tests for Sprint 5.1 Studio Policy Engine & Models:
- StudioPolicyConfig Pydantic model contracts and validations
- resolve_effective_policy merge semantics and selective override preservation
- evaluate_claim_against_policy statutory rules and multi-violation aggregation
- StudioPolicyEngine lifecycle, caching, RBAC, ledger integration, and singleton

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from backend.core.policy_engine import (
    StudioPolicyEngine,
    get_policy_engine,
)
from backend.core.policy_rules import (
    evaluate_claim_against_policy,
    get_preset_profile_policy,
    resolve_effective_policy,
)
from backend.core.policy_types import (
    LicensingScope,
    PolicyEvaluationResult,
    PolicyViolation,
    ProductionPolicyOverride,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
)
import shutil
from backend.core.rbac import LienmarkRole
from backend.storage.ledger import CryptographicLedger


@pytest.fixture(autouse=True)
def clean_policies():
    """Isolates disk persistence state between test executions."""
    shutil.rmtree("output/policies", ignore_errors=True)
    yield
    shutil.rmtree("output/policies", ignore_errors=True)


def test_studio_policy_config_model_validation():
    """Verify StudioPolicyConfig construction, default fields, and threshold validation."""
    now = datetime.now(timezone.utc).isoformat()
    cfg = StudioPolicyConfig(
        policy_id="pol_test_01",
        org_id="org_test",
        required_media_scopes=[LicensingScope.THEATRICAL],
        distribution_territories=[TerritoryScope.WORLDWIDE],
        risk_tolerance_threshold=0.65,
    )
    assert cfg.policy_id == "pol_test_01"
    assert cfg.profile_type == StudioProfileType.MAJOR_THEATRICAL
    assert cfg.mandatory_perpetual_for_theatrical is True
    assert cfg.prohibit_unvetted_trademark_fair_use is True
    assert cfg.risk_tolerance_threshold == 0.65

    with pytest.raises(ValidationError):
        StudioPolicyConfig(
            policy_id="pol_err",
            org_id="org_err",
            risk_tolerance_threshold=1.5,
        )


def test_resolve_effective_policy_selective_overrides():
    """Verify selective overrides override specific fields while preserving untouched baseline."""
    base = get_preset_profile_policy("org_mgm", StudioProfileType.MAJOR_THEATRICAL)
    now = datetime.now(timezone.utc).isoformat()

    # 1. Override only media scopes
    ovr_scope = ProductionPolicyOverride(
        override_id="ovr_s1",
        production_id="prod_s1",
        org_id="org_mgm",
        admin_actor_id="admin_1",
        admin_actor_name="MGM Exec",
        rationale="Festival only exhibition waiver",
        overridden_media_scopes=[LicensingScope.THEATRICAL],
        created_at_utc=now,
    )
    eff_scope = resolve_effective_policy(base, ovr_scope)
    assert eff_scope.required_media_scopes == [LicensingScope.THEATRICAL]
    assert eff_scope.distribution_territories == base.distribution_territories
    assert eff_scope.prohibit_unvetted_trademark_fair_use == base.prohibit_unvetted_trademark_fair_use

    # 2. Override only trademark fair use
    ovr_tm = ProductionPolicyOverride(
        override_id="ovr_tm1",
        production_id="prod_tm1",
        org_id="org_mgm",
        admin_actor_id="admin_1",
        admin_actor_name="MGM Exec",
        rationale="Permit trademark fair use",
        allow_trademark_fair_use=True,
    )
    eff_tm = resolve_effective_policy(base, ovr_tm)
    assert eff_tm.prohibit_unvetted_trademark_fair_use is False
    assert eff_tm.required_media_scopes == base.required_media_scopes


def test_evaluate_claim_against_policy_compliant_and_multi_violation():
    """Verify clean pass for compliant claim and multi-violation aggregation."""
    policy = get_preset_profile_policy("org_warner", StudioProfileType.MAJOR_THEATRICAL)

    # Compliant sync claim
    good_claim = {
        "category": "music",
        "description": "Soundtrack sync master and composition",
        "territory": "worldwide",
        "term": "perpetual",
    }
    good_res = evaluate_claim_against_policy(good_claim, policy)
    assert good_res.is_compliant is True
    assert len(good_res.violations) == 0
    assert good_res.requires_special_waiver is False

    # Multi-violation claim: limited sync AND unvetted trademark fair use
    bad_claim = {
        "category": "music_trademark",
        "description": "Commercial jingle featuring luxury car logo",
        "term": "3 years",
        "territory": "worldwide",
        "stance": "fair_use",
        "has_executed_release": False,
    }
    bad_res = evaluate_claim_against_policy(bad_claim, policy)
    assert bad_res.is_compliant is False
    assert len(bad_res.violations) >= 2
    rule_codes = {v.rule_code for v in bad_res.violations}
    assert "THEATRICAL_PERPETUAL_REQUIRED" in rule_codes
    assert "TRADEMARK_FAIR_USE_PROHIBITED" in rule_codes


def test_evaluate_claim_against_policy_territory_variations():
    """Verify territory evaluation across missing territory and explicit exclusion."""
    policy = get_preset_profile_policy("org_focus", StudioProfileType.MAJOR_THEATRICAL)

    # Missing mandatory worldwide territory
    claim_missing_terr = {
        "category": "artwork",
        "description": "Painting hung in hotel lobby scene",
        "territories": ["north_america"],
    }
    res_miss = evaluate_claim_against_policy(claim_missing_terr, policy)
    assert res_miss.is_compliant is False
    assert any(v.rule_code == "TERRITORY_EXCLUSION_MISMATCH" for v in res_miss.violations)

    # Explicit excluded territory
    claim_excl = {
        "category": "prop",
        "description": "Vintage magazine advertisement",
        "excluded_territories": ["apac"],
        "territory": "worldwide",
    }
    res_excl = evaluate_claim_against_policy(claim_excl, policy)
    assert res_excl.is_compliant is False
    assert any(v.rule_code == "TERRITORY_EXCLUSION_MISMATCH" for v in res_excl.violations)


def test_studio_policy_engine_crud_and_caching():
    """Verify StudioPolicyEngine default creation, caching, and custom update."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    org_id = "org_lionsgate"

    # Default policy created on demand
    default_pol = engine.get_studio_policy(org_id)
    assert default_pol.org_id == org_id
    assert default_pol.profile_type == StudioProfileType.MAJOR_THEATRICAL

    # Mutate and update
    custom_pol = StudioPolicyConfig(
        policy_id=f"pol_{org_id}_custom",
        org_id=org_id,
        profile_type=StudioProfileType.CUSTOM,
        required_media_scopes=[LicensingScope.SVOD],
        distribution_territories=[TerritoryScope.NORTH_AMERICA],
    )
    saved = engine.set_studio_policy(custom_pol)
    assert saved.profile_type == StudioProfileType.CUSTOM
    assert engine.get_studio_policy(org_id).profile_type == StudioProfileType.CUSTOM


def test_studio_policy_engine_evaluate_claim_flow():
    """Verify StudioPolicyEngine end-to-end claim evaluation with and without overrides."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    org_id = "org_hbo"
    prod_id = "prod_succession_s5"

    claim = {
        "category": "trademark",
        "description": "Waystar Royco competitor corporate logo",
        "stance": "fair_use",
        "territory": "worldwide",
    }

    # Step 1: Fails under studio baseline
    res1 = engine.evaluate_claim(claim, org_id, prod_id)
    assert res1.is_compliant is False

    # Step 2: Admin applies override
    override = ProductionPolicyOverride(
        override_id="ovr_waystar_01",
        production_id=prod_id,
        org_id=org_id,
        admin_actor_id="admin_logan",
        admin_actor_name="Logan Roy",
        rationale="Executive sign-off on satirical brand parody",
        allow_trademark_fair_use=True,
    )
    engine.apply_production_override(org_id, prod_id, override, actor_role=LienmarkRole.ADMIN)

    # Step 3: Passes under updated effective policy
    res2 = engine.evaluate_claim(claim, org_id, prod_id)
    assert res2.is_compliant is True


def test_get_policy_engine_singleton():
    """Verify get_policy_engine provides a consistent process singleton."""
    eng1 = get_policy_engine()
    eng2 = get_policy_engine()
    assert eng1 is eng2
    assert isinstance(eng1, StudioPolicyEngine)
