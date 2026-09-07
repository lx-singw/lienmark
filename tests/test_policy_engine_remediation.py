"""
tests/test_policy_engine_remediation.py

Comprehensive verification suite for Sprint 5.1/5.2 StudioPolicyEngine remediation:
1. Mandatory CryptographicLedger on set_studio_policy & apply_production_override
2. Atomic PolicyStore commit (revision, pointer, intent) & rollback on failure
3. POLICY_UPDATED event with canonical SHA-256 digest
4. Target production Admin authority scope verification
5. 4-state PolicyEvaluationResult with separate required_actions & full provenance
6. Zero silent fallback for Firestore mode

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import shutil
from unittest.mock import MagicMock
import pytest

from backend.core.policy_engine import StudioPolicyEngine
from backend.core.policy_rules import get_preset_profile_policy
from backend.core.policy_types import (
    LicensingScope,
    PolicyActionRequirement,
    PolicyEvaluationResult,
    ProductionPolicyOverride,
    RuleEvaluationStatus,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
)
from backend.core.rbac import LienmarkRole
from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store_types import PolicyStoreError, PolicyStoreMode


@pytest.fixture(autouse=True)
def clean_policies_env():
    """Isolates disk persistence state before and after each test."""
    shutil.rmtree("output/policies", ignore_errors=True)
    yield
    shutil.rmtree("output/policies", ignore_errors=True)


def test_set_studio_policy_requires_active_ledger_when_none_configured():
    """Missing ledger raises RuntimeError('Policy mutation requires an active CryptographicLedger.')."""
    engine = StudioPolicyEngine(ledger=None)
    policy = get_preset_profile_policy("org_remediation", StudioProfileType.MAJOR_THEATRICAL)
    with pytest.raises(RuntimeError, match="Policy mutation requires an active CryptographicLedger"):
        engine.set_studio_policy(policy)


def test_set_studio_policy_explicit_none_ledger_raises():
    """Passing ledger=None explicitly raises RuntimeError even if engine has default."""
    engine = StudioPolicyEngine(ledger=CryptographicLedger())
    policy = get_preset_profile_policy("org_remediation", StudioProfileType.MAJOR_THEATRICAL)
    with pytest.raises(RuntimeError, match="Policy mutation requires an active CryptographicLedger"):
        engine.set_studio_policy(policy, actor_id="admin_1", ledger=None)


def test_set_studio_policy_atomic_commit_and_event():
    """Commits revision, pointer, intent via PolicyStore and emits POLICY_UPDATED with digest."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    policy = get_preset_profile_policy("org_mgm_studios", StudioProfileType.STREAMER_EXCLUSIVE)

    saved = engine.set_studio_policy(policy, actor_id="exec_admin")
    assert saved.profile_type == StudioProfileType.STREAMER_EXCLUSIVE

    active_rec = engine._policy_store.get_active_policy("org_mgm_studios")
    assert active_rec is not None
    assert active_rec.version_id == "v1"

    intents = engine._policy_store.list_dispatch_intents("org_mgm_studios")
    assert len(intents) == 1
    assert intents[0].to_version == "v1"

    events = ledger.get_events("policy_org_mgm_studios")
    assert len(events) == 2  # Genesis + POLICY_UPDATED
    upd_event = events[-1]
    assert upd_event.action_type == "POLICY_UPDATED"
    assert len(upd_event.payload["policy_digest"]) == 64


def test_set_studio_policy_rollback_on_ledger_append_failure():
    """Ledger failure triggers rollback in PolicyStore leaving zero phantom IDs."""
    broken_ledger = CryptographicLedger()
    broken_ledger.append_event = MagicMock(side_effect=RuntimeError("Simulated ledger disk failure"))
    engine = StudioPolicyEngine(ledger=broken_ledger)
    policy = get_preset_profile_policy("org_fail_safe", StudioProfileType.FESTIVAL_ACQUISITION)

    with pytest.raises(RuntimeError, match="Policy mutation requires an active CryptographicLedger"):
        engine.set_studio_policy(policy, actor_id="admin_test")

    assert engine._policy_store.get_active_policy("org_fail_safe") is None
    assert "org_fail_safe" not in engine._studio_policies


def test_apply_production_override_requires_active_ledger():
    """Override without active ledger raises RuntimeError."""
    engine = StudioPolicyEngine(ledger=None)
    override = ProductionPolicyOverride(
        override_id="ovr_test_01", production_id="prod_01", org_id="org_test",
        admin_actor_id="adm_1", admin_actor_name="Admin", rationale="Test waiver",
    )
    with pytest.raises(RuntimeError, match="Policy override requires an active CryptographicLedger"):
        engine.apply_production_override("org_test", "prod_01", override, actor_role=LienmarkRole.ADMIN)


def test_apply_production_override_enforces_admin_and_target_scope():
    """Enforces Admin role and matches target production scope strictly."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    override = ProductionPolicyOverride(
        override_id="ovr_target_01", production_id="prod_target", org_id="org_scope",
        admin_actor_id="adm_1", admin_actor_name="Admin", rationale="Target waiver",
    )

    with pytest.raises(PermissionError, match="requires Admin role"):
        engine.apply_production_override("org_scope", "prod_target", override, actor_role=LienmarkRole.VIEWER)

    with pytest.raises(PermissionError, match="Admin role sign-off for target production scope"):
        engine.apply_production_override("org_scope", "prod_DIFFERENT", override, actor_role=LienmarkRole.ADMIN)


def test_apply_production_override_persistence_and_no_contractual_clearance():
    """Override persists in store, logs ledger event, but never grants contractual clearance."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    override = ProductionPolicyOverride(
        override_id="ovr_clearance_01", production_id="prod_clearance", org_id="org_clearance",
        admin_actor_id="adm_legal", admin_actor_name="Legal Admin", rationale="Permit fair use",
        allow_trademark_fair_use=True,
    )
    eff = engine.apply_production_override("org_clearance", "prod_clearance", override, actor_role="admin")
    assert eff.prohibit_unvetted_trademark_fair_use is False

    persisted = engine._policy_store.get_production_override("org_clearance", "prod_clearance")
    assert persisted is not None
    assert persisted["allow_trademark_fair_use"] is True

    # Claim without music grant still fails rule evaluation (never auto-approved)
    claim_music = {"category": "music", "description": "Unlicensed cue", "permission_status": "unknown"}
    res = engine.evaluate_claim(claim_music, "org_clearance", "prod_clearance")
    assert res.is_compliant is False
    assert res.overall_status in (RuleEvaluationStatus.UNKNOWN, RuleEvaluationStatus.NOT_SATISFIED)


def test_apply_production_override_rollback_on_failure():
    """Ledger failure during override rolls back PolicyStore state fail-closed."""
    broken_ledger = CryptographicLedger()
    broken_ledger.append_event = MagicMock(side_effect=RuntimeError("Simulated override ledger append error"))
    engine = StudioPolicyEngine(ledger=broken_ledger)
    override = ProductionPolicyOverride(
        override_id="ovr_rb_01", production_id="prod_rb", org_id="org_rb",
        admin_actor_id="adm_1", admin_actor_name="Admin", rationale="Rollback waiver",
    )

    with pytest.raises(RuntimeError, match="Policy override requires an active CryptographicLedger"):
        engine.apply_production_override("org_rb", "prod_rb", override, actor_role="admin")

    assert engine._policy_store.get_production_override("org_rb", "prod_rb") is None
    assert "org_rb:prod_rb" not in engine._production_overrides


def test_evaluate_claim_returns_4_state_result_and_provenance():
    """Returns 4-state RuleEvaluationStatus, separate required_actions, and full provenance."""
    ledger = CryptographicLedger()
    engine = StudioPolicyEngine(ledger=ledger)
    claim = {
        "claim_id": "claim_cue_101",
        "category": "music",
        "description": "Theatrical master sync cue",
        "term": "3 years limited",
        "territory": "worldwide",
        "permission_status": "executed",
        "has_agreement": True,
    }
    res = engine.evaluate_claim(claim, "org_a24", "prod_movie_01")
    assert isinstance(res, PolicyEvaluationResult)
    assert res.overall_status == RuleEvaluationStatus.NOT_SATISFIED
    assert res.is_compliant is False

    assert isinstance(res.required_actions, list)
    assert PolicyActionRequirement.AGREEMENT_AMENDMENT in res.required_actions

    prov = res.provenance
    assert prov["org_id"] == "org_a24"
    assert prov["production_id"] == "prod_movie_01"
    assert prov["policy_id"].startswith("pol_org_a24")
    assert len(prov["policy_digest"]) == 64
    assert "evaluated_at_utc" in prov


def test_policy_store_firestore_zero_silent_fallback():
    """PolicyStore with mode=FIRESTORE and no client strictly raises PolicyStoreError."""
    with pytest.raises(PolicyStoreError, match="Silent fallback to local disk is strictly prohibited"):
        StudioPolicyEngine(store_mode=PolicyStoreMode.FIRESTORE, firestore_adapter=None)
