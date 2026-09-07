"""
tests/test_policy_remediation.py

Sprint 5.2 Acceptance Test Suite: Policy Remediation & Governance Hardening.
Tests:
- Test 1: Failed audit write fails closed (neither config nor pointer changes, 0 phantom ID)
- Test 2: RBAC scope isolation (cross-prod 403, studio admin 403, waiver needs review, no body spoof)
- Test 3: Fail-closed evaluation on missing facts (artwork UNKNOWN, trailer cue multi-findings)
- Test 4: Atomic dispatch intent persistence (records from/to versions and rule deltas)
- Test 5: Worker restart persistence (reloaded engine confirms version, digest, and lineage)

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.core import (
    CLARIFICATION,
    COUNSEL_REVIEW,
    PolicyActionRequirement,
    RuleEvaluationStatus,
    StudioPolicyConfig,
    StudioPolicyEngine,
    StudioProfileType,
    evaluate_claim_against_policy,
    get_preset_profile_policy,
)
from backend.main import app
from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store_local import LocalPolicyStore
from backend.storage.policy_store_types import PolicyStoreError
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


def test_failed_audit_write_fails_closed(tmp_path):
    """Attempting policy mutation without ledger or on write failure fails closed with zero phantom ID."""
    org_id, prod_id = "org_a24_remediation", "prod_remediation_01"
    store_no_ledger = LocalPolicyStore(base_dir=str(tmp_path / "no_ledger"), ledger=None)
    engine_no_ledger = StudioPolicyEngine(store=store_no_ledger, ledger=None)
    mutated_policy = StudioPolicyConfig(
        policy_id=f"pol_{org_id}_streamer", org_id=org_id, profile_type=StudioProfileType.STREAMER_EXCLUSIVE,
    )
    with pytest.raises(PolicyStoreError, match="Mandatory audit ledger infrastructure is missing"):
        engine_no_ledger.set_studio_policy(mutated_policy)
    assert store_no_ledger.get_active_policy(org_id) is None

    real_ledger = CryptographicLedger()
    store = LocalPolicyStore(base_dir=str(tmp_path / "fail_store"), ledger=real_ledger)
    engine = StudioPolicyEngine(store=store, ledger=real_ledger)
    base_policy = engine.get_studio_policy(org_id)
    initial_ver = engine.get_active_version(org_id)

    with patch.object(real_ledger, "append_event", side_effect=RuntimeError("Disk write failure")):
        with pytest.raises(PolicyStoreError, match="Ledger audit append failed"):
            engine.set_studio_policy(mutated_policy)

    assert engine.get_active_version(org_id) == initial_ver
    assert engine.get_studio_policy(org_id).profile_type == base_policy.profile_type

    admin_token = create_test_jwt(tenant_id=org_id, user_id="usr_adm", roles=["admin"])
    with patch("backend.api.routes.policies._resolve_ledger", return_value=None):
        resp = client.post(
            f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"admin_actor_id": "usr_adm", "actor_role": "admin", "rationale": "Scope waiver"},
        )
        assert resp.status_code == 500
        assert "audit_event_id" not in resp.json()


def test_rbac_scope_isolation():
    """Validates cross-production isolation, studio admin boundaries, waiver review, and body claims."""
    org, p_a, p_b = "org_paramount_rbac", "prod_gladiator", "prod_topgun"
    p_adm_tok = create_test_jwt(tenant_id=org, user_id="usr_prod_a", roles=[], claims_extra={"production_roles": {p_a: "admin"}})
    v_tok = create_test_jwt(tenant_id=org, user_id="usr_viewer", roles=["viewer"])
    s_adm_tok = create_test_jwt(tenant_id=org, user_id="usr_adm", roles=["admin"])

    # 1. Admin for Production A cannot modify Production B (HTTP 403)
    r_cross = client.post(f"/api/v1/organizations/{org}/productions/{p_b}/policy-override",
                          headers={"Authorization": f"Bearer {p_adm_tok}"},
                          json={"admin_actor_id": "usr_prod_a", "actor_role": "admin", "rationale": "Cross-prod breach"})
    assert r_cross.status_code == 403
    assert "not authorized to administer target production" in r_cross.json()["detail"]

    # 2. Production Admin attempting to modify Studio policy is rejected with HTTP 403
    r_stu = client.put(f"/api/v1/organizations/{org}/policy", headers={"Authorization": f"Bearer {p_adm_tok}"},
                       json={"profile_type": "streamer_exclusive"})
    assert r_stu.status_code == 403
    assert "Studio policy configuration requires Admin" in r_stu.json()["detail"]

    # 3. Self-declared legal credential in request body grants zero clearance authority
    r_spoof = client.post(f"/api/v1/organizations/{org}/productions/{p_a}/policy-override",
                          headers={"Authorization": f"Bearer {v_tok}"},
                          json={"admin_actor_id": "usr_viewer", "actor_role": "admin", "rationale": "Self-declared bar credential"})
    assert r_spoof.status_code == 403

    # 4. Authorized waiver leaves claim awaiting counsel review (never automatically approved)
    client.post(f"/api/v1/organizations/{org}/productions/{p_a}/policy-override",
                headers={"Authorization": f"Bearer {s_adm_tok}"},
                json={"admin_actor_id": "usr_adm", "actor_role": "admin", "rationale": "Fair use waiver", "allow_trademark_fair_use": True})
    ev = client.post(f"/api/v1/organizations/{org}/productions/{p_a}/claims/claim_tm_01/evaluate-policy",
                     headers={"Authorization": f"Bearer {v_tok}"},
                     json={"asset_type": "trademark", "category": "trademark", "description": "Prop logo", "stance": "fair_use", "territory": "worldwide"})
    assert ev.status_code == 200 and ev.json()["decision_state"] == "needs_review"
    assert ev.json()["evaluation_state"] == "override_applied"
    assert any("formal counsel review" in a.lower() for a in ev.json()["required_actions"])


def test_fail_closed_evaluation_missing_facts():
    """Artwork claim without grant evaluates UNKNOWN; trailer cue surfaces UNKNOWN, NOT_SATISFIED, SATISFIED."""
    policy = get_preset_profile_policy("org_remediation", StudioProfileType.MAJOR_THEATRICAL)

    # 1. Artwork claim with no grant or agreement
    art_claim = {"asset_type": "artwork", "category": "artwork", "description": "Oil canvas prop", "has_agreement": False}
    art_res = evaluate_claim_against_policy(art_claim, policy)
    assert art_res.overall_status == RuleEvaluationStatus.UNKNOWN
    assert art_res.is_compliant is False
    assert PolicyActionRequirement.CLARIFICATION in art_res.required_actions
    assert PolicyActionRequirement.COUNSEL_REVIEW in art_res.required_actions
    assert CLARIFICATION in art_res.required_actions
    assert COUNSEL_REVIEW in art_res.required_actions

    # 2. Promotional trailer music cue with unknown permission + excluded territory + studio second review
    trailer_cue = {
        "asset_type": "music_cue", "category": "music", "description": "Trailer cue",
        "term": "perpetual", "territory": "worldwide", "permission_unknown": True, "excluded_territories": ["apac"],
        "is_promotional_trailer": True,
    }
    trailer_res = evaluate_claim_against_policy(trailer_cue, policy)
    statuses = {e.status for e in trailer_res.rule_evaluations}
    assert RuleEvaluationStatus.UNKNOWN in statuses
    assert RuleEvaluationStatus.NOT_SATISFIED in statuses
    assert RuleEvaluationStatus.SATISFIED in statuses
    assert trailer_res.is_compliant is False

    actions = set(trailer_res.required_actions)
    assert PolicyActionRequirement.CLARIFICATION in actions
    assert PolicyActionRequirement.COUNSEL_REVIEW in actions
    assert PolicyActionRequirement.SECOND_REVIEW in actions
    assert PolicyActionRequirement.AGREEMENT_AMENDMENT in actions


def test_atomic_dispatch_intent_persistence(tmp_path):
    """Updating studio policy atomically persists PolicyChangeDispatchIntent record with deltas."""
    ledger = CryptographicLedger()
    store = LocalPolicyStore(base_dir=str(tmp_path / "intent_store"), ledger=ledger)
    org_id = "org_sony_dispatch"

    cfg_v1 = {"profile_type": "major_theatrical", "theatrical_perpetual": True}
    rec_v1, intent_v1 = store.save_policy_revision(org_id, cfg_v1, "admin_1")
    assert intent_v1.to_version == "v1"

    cfg_v2 = {"profile_type": "streamer_exclusive", "theatrical_perpetual": False}
    rec_v2, intent_v2 = store.save_policy_revision(org_id, cfg_v2, "admin_1")

    assert intent_v2.from_version == "v1"
    assert intent_v2.to_version == "v2"
    assert "profile_type" in intent_v2.affected_rules
    assert "theatrical_perpetual" in intent_v2.affected_rules

    intents = store.list_dispatch_intents(org_id, status="PENDING")
    assert len(intents) == 2
    assert intents[1].intent_id == intent_v2.intent_id


def test_worker_restart_persistence(tmp_path):
    """Worker reload verifies active policy version, canonical digest, and audit lineage remain identical."""
    ledger = CryptographicLedger()
    store_dir = str(tmp_path / "restart_store")
    store1 = LocalPolicyStore(base_dir=store_dir, ledger=ledger)
    engine1 = StudioPolicyEngine(store=store1, ledger=ledger)
    org_id = "org_a24_restart"

    policy1 = get_preset_profile_policy(org_id, StudioProfileType.MAJOR_THEATRICAL)
    engine1.set_studio_policy(policy1, actor_id="admin_init")

    policy2 = get_preset_profile_policy(org_id, StudioProfileType.STREAMER_EXCLUSIVE)
    engine1.set_studio_policy(policy2, actor_id="admin_update")

    v1 = engine1.get_active_version(org_id)
    digest1 = engine1.get_policy_digest(org_id)
    lineage1 = engine1.get_audit_lineage(org_id)

    store2 = LocalPolicyStore(base_dir=store_dir, ledger=ledger)
    engine2 = StudioPolicyEngine(store=store2, ledger=ledger)

    v2 = engine2.get_active_version(org_id)
    digest2 = engine2.get_policy_digest(org_id)
    lineage2 = engine2.get_audit_lineage(org_id)

    assert v1 == v2
    assert digest1 == digest2
    assert [e.event_id for e in lineage1] == [e.event_id for e in lineage2]
    assert engine2.get_studio_policy(org_id).profile_type == StudioProfileType.STREAMER_EXCLUSIVE
