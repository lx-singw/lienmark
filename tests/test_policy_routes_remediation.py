"""
tests/test_policy_routes_remediation.py

Verification suite for Sprint 5.1 Policy Routes Remediation:
1. Actor identity server-side extraction & disregarding caller body claims
2. Scope separation: Studio Admin required for studio baseline (prod admin rejected)
3. Scope separation: Production Admin scoped to target production (cross-prod rejected with 403)
4. Fail-closed audit handling: HTTP 500 when ledger missing, genuine audit event IDs committed
5. 4-state evaluation response with required actions and provenance

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core.policy_engine import get_policy_engine
from backend.main import app
from backend.storage.ledger import CryptographicLedger
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Ensures clean state for policy engine and ledger between tests."""
    engine = get_policy_engine()
    engine._studio_policies.clear()
    engine._production_overrides.clear()
    orig_ledger = getattr(app.state, "ledger", None)
    app.state.ledger = CryptographicLedger()
    yield
    engine._studio_policies.clear()
    engine._production_overrides.clear()
    app.state.ledger = orig_ledger if orig_ledger is not None else CryptographicLedger()


def test_server_side_actor_identity_disregards_caller_supplied_id():
    """Actor identity is strictly derived from JWT principal; body admin_actor_id is disregarded."""
    org_id = "org_a24_audit"
    prod_id = "prod_everything_2"
    real_user_id = "usr_real_counsel_007"
    token = create_test_jwt(tenant_id=org_id, user_id=real_user_id, roles=["admin"])

    payload = {
        "admin_actor_id": "spoofed_hacker_id",
        "admin_actor_name": "Spoofed Actor",
        "rationale": "Legitimate legal fair use waiver",
        "actor_role": "admin",
        "allow_trademark_fair_use": True,
    }
    res = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    events = app.state.ledger.get_events(prod_id)
    override_event = next(e for e in events if e.action_type == "POLICY_OVERRIDE")
    assert override_event.actor_id == real_user_id
    assert override_event.actor_id != "spoofed_hacker_id"


def test_disregard_caller_supplied_role_for_authorization():
    """Caller with non-admin token passing actor_role='admin' in body is rejected with 403."""
    org_id = "org_paramount_audit"
    prod_id = "prod_topgun_3"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_producer", roles=["producer"])

    payload = {
        "admin_actor_id": "usr_producer",
        "admin_actor_name": "Producer Jack",
        "rationale": "Attempting privilege escalation via request body role field",
        "actor_role": "admin",
        "allow_trademark_fair_use": True,
    }
    res = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "Admin role" in res.json()["detail"]


def test_studio_admin_scope_separation_rejects_production_admin():
    """PUT /policy strictly requires Studio Admin; production-scoped admin authority is rejected."""
    org_id = "org_warner_scope"
    prod_id = "prod_batman_2"
    token = create_test_jwt(
        tenant_id=org_id, user_id="usr_prod_admin", roles=["viewer"],
        claims_extra={"production_roles": {prod_id: "admin"}},
    )
    res = client.put(
        f"/api/v1/organizations/{org_id}/policy",
        json={"profile_type": "streamer_exclusive"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "Admin or studio_executive" in res.json()["detail"]


def test_production_override_cross_production_forbidden():
    """Admin on Production A attempting override on Production B receives explicit 403."""
    org_id = "org_sony_scope"
    prod_a, prod_b = "prod_spiderman_a", "prod_spiderman_b"
    token = create_test_jwt(
        tenant_id=org_id, user_id="usr_prod_a_admin", roles=["viewer"],
        claims_extra={"production_roles": {prod_a: "admin"}},
    )

    # 1. Calling on own production (prod_a) succeeds
    payload_a = {"rationale": "Authorized override on Production A", "allow_trademark_fair_use": True}
    res_a = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_a}/policy-override",
        json=payload_a, headers={"Authorization": f"Bearer {token}"},
    )
    assert res_a.status_code == 200

    # 2. Calling on different production (prod_b) is rejected with explicit target authorization error
    payload_b = {"rationale": "Unauthorized cross-production override attempt", "allow_trademark_fair_use": True}
    res_b = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_b}/policy-override",
        json=payload_b, headers={"Authorization": f"Bearer {token}"},
    )
    assert res_b.status_code == 403
    assert res_b.json()["detail"] == "Principal not authorized to administer target production."


def test_studio_admin_can_override_any_production():
    """Studio Admin authority can apply overrides across any production in the organization."""
    org_id = "org_universal_studio"
    prod_id = "prod_wicked_part_2"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_studio_exec", roles=["studio_executive"])

    res = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json={"rationale": "Studio executive global clearance waiver", "allow_trademark_fair_use": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "applied"


def test_fail_closed_audit_handling_ledger_inactive_raises_500():
    """Override endpoint fails closed with HTTP 500 when CryptographicLedger is unavailable."""
    org_id = "org_lionsgate_fail_closed"
    prod_id = "prod_john_wick_5"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_admin", roles=["admin"])

    app.state.ledger = None
    engine = get_policy_engine()
    engine._ledger = None

    res = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json={"rationale": "Override during ledger outage", "allow_trademark_fair_use": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 500
    assert "ledger is not active or unavailable" in res.json()["detail"]


def test_genuine_audit_event_id_committed_no_phantom_ids():
    """Returned audit_event_id strictly matches the event committed to CryptographicLedger."""
    org_id = "org_focus_features"
    prod_id = "prod_nosferatu"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_focus_adm", roles=["admin"])

    res = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json={"rationale": "European festival distribution territory override", "overridden_territories": ["emea"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    returned_evt_id = res.json()["audit_event_id"]
    assert returned_evt_id.startswith("evt_")

    events = app.state.ledger.get_events(prod_id)
    assert any(e.event_id == returned_evt_id for e in events)


def test_evaluate_policy_four_state_response_actions_and_provenance():
    """POST evaluate-policy returns canonical 4-state outcome, explicit actions, and provenance."""
    org_id = "org_universal_eval"
    prod_id = "prod_oppenheimer_2"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_counsel", roles=["reviewer"])

    # 1. State: exception (critical violation)
    res_crit = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/claims/claim_c1/evaluate-policy",
        json={"category": "music", "term": "3 years linear", "territory": "worldwide"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_crit.status_code == 200
    data_crit = res_crit.json()
    assert data_crit["evaluation_state"] == "exception"
    assert data_crit["decision_state"] == "exception"
    assert data_crit["is_compliant"] is False
    assert len(data_crit["required_actions"]) > 0
    assert any("Worldwide Perpetual" in a for a in data_crit["required_actions"])
    assert data_crit["provenance"]["claim_id"] == "claim_c1"
    assert data_crit["provenance"]["production_id"] == prod_id

    # 2. State: compliant (no violations)
    res_comp = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/claims/claim_c2/evaluate-policy",
        json={"category": "music", "term": "perpetual worldwide", "territory": "worldwide"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert data_comp["evaluation_state"] == "compliant"
    assert data_comp["decision_state"] == "carried_forward"
    assert data_comp["is_compliant"] is True
    assert data_comp["required_actions"] == []
