"""
tests/test_policy_routes.py

Comprehensive test suite for Studio Policy Inheritance REST API endpoints.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core.policy_engine import get_policy_engine
from backend.core.policy_types import StudioProfileType
from backend.main import app
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_engine():
    """Ensures a clean state for the policy engine between tests."""
    engine = get_policy_engine()
    engine._studio_policies.clear()
    engine._production_overrides.clear()
    yield
    engine._studio_policies.clear()
    engine._production_overrides.clear()


def test_get_studio_policy_unconfigured_default():
    """GET /api/v1/organizations/{org_id}/policy returns default Major Theatrical template."""
    org_id = "org_a24_demo"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_view", roles=["viewer"])
    res = client.get(
        f"/api/v1/organizations/{org_id}/policy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["org_id"] == org_id
    assert data["profile_type"] == StudioProfileType.MAJOR_THEATRICAL.value
    assert "theatrical" in data["required_media_scopes"]
    assert "worldwide" in data["distribution_territories"]
    assert data["mandatory_perpetual_for_theatrical"] is True
    assert data["policy"]["org_id"] == org_id


def test_put_studio_policy_admin_and_executive_success():
    """PUT /api/v1/organizations/{org_id}/policy succeeds for admin or studio_executive role."""
    org_id = "org_warner_bros"
    exec_token = create_test_jwt(tenant_id=org_id, user_id="usr_exec", roles=["studio_executive"])
    payload = {
        "profile_type": "streamer_exclusive",
        "required_media_scopes": ["svod", "avod", "promotional_trailer"],
        "distribution_territories": ["worldwide"],
        "mandatory_perpetual_for_theatrical": False,
        "prohibit_unvetted_trademark_fair_use": True,
        "risk_tolerance_threshold": 0.60,
    }
    res = client.put(
        f"/api/v1/organizations/{org_id}/policy",
        json=payload,
        headers={"Authorization": f"Bearer {exec_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["profile_type"] == "streamer_exclusive"
    assert "theatrical" not in data["required_media_scopes"]
    assert data["mandatory_perpetual_for_theatrical"] is False


def test_put_studio_policy_non_admin_rejected_403():
    """PUT /api/v1/organizations/{org_id}/policy rejects non-admin roles with HTTP 403."""
    org_id = "org_warner_bros"
    for forbidden_role in ["producer", "reviewer", "analyst", "viewer"]:
        token = create_test_jwt(tenant_id=org_id, user_id=f"usr_{forbidden_role}", roles=[forbidden_role])
        res = client.put(
            f"/api/v1/organizations/{org_id}/policy",
            json={"profile_type": "festival_acquisition"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert "Admin or studio_executive" in res.json()["detail"]


def test_get_effective_policy_inheritance_and_override():
    """GET effective policy returns inherited studio baseline until override is applied."""
    org_id = "org_paramount_01"
    prod_id = "prod_gladiator_2"
    viewer_token = create_test_jwt(tenant_id=org_id, user_id="usr_view", roles=["viewer"])
    admin_token = create_test_jwt(tenant_id=org_id, user_id="usr_adm", roles=["admin"])

    # 1. Initially inherits parent baseline
    res_base = client.get(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/effective-policy",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_base.status_code == 200
    assert "theatrical" in res_base.json()["required_media_scopes"]

    # 2. Post override
    ovr_payload = {
        "admin_actor_id": "usr_adm",
        "admin_actor_name": "Studio Admin",
        "rationale": "Direct-to-streaming distribution pipeline",
        "actor_role": "admin",
        "overridden_media_scopes": ["svod", "avod"],
    }
    res_ovr = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json=ovr_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_ovr.status_code == 200

    # 3. Effective policy reflects override
    res_eff = client.get(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/effective-policy",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_eff.status_code == 200
    assert res_eff.json()["required_media_scopes"] == ["svod", "avod"]


def test_policy_override_rbac_enforcement():
    """POST policy-override strictly validates Admin role and rejects non-admin."""
    org_id = "org_sony_01"
    prod_id = "prod_spiderman_4"
    prod_token = create_test_jwt(tenant_id=org_id, user_id="usr_prod", roles=["producer"])
    admin_token = create_test_jwt(tenant_id=org_id, user_id="usr_adm", roles=["admin"])

    # Attempt with non-admin actor_role
    res_fail1 = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json={
            "admin_actor_id": "usr_prod",
            "admin_actor_name": "Line Producer",
            "rationale": "Waiving clearance scope",
            "actor_role": "producer",
        },
        headers={"Authorization": f"Bearer {prod_token}"},
    )
    assert res_fail1.status_code == 403
    assert res_fail1.json()["detail"] == "Production policy overrides require Admin role sign-off."

    # Successful override with Admin
    res_ok = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/policy-override",
        json={
            "admin_actor_id": "usr_adm",
            "admin_actor_name": "Elena Vance, Studio Counsel",
            "rationale": "Commercial brand fair use authorized under legal counsel clearance waiver",
            "actor_role": "Admin",
            "allow_trademark_fair_use": True,
            "waiver_notes": "Trademark fair use vetted for incidental prop placement.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["audit_event_id"].startswith("evt_")
    assert data["effective_policy"]["prohibit_unvetted_trademark_fair_use"] is False


def test_evaluate_policy_claim_compliance_flow():
    """POST evaluate-policy tests non-conforming claims and waiver/override compliance."""
    org_id = "org_universal_01"
    prod_id = "prod_jurassic_7"
    token = create_test_jwt(tenant_id=org_id, user_id="usr_counsel", roles=["reviewer"])

    # 1. Non-conforming: Theatrical sync with non-perpetual license fails
    music_claim = {
        "asset_type": "music_cue",
        "category": "music",
        "description": "Theme Orchestral Cue",
        "term": "3 years linear only",
        "territory": "worldwide",
    }
    res1 = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/claims/claim_music_99/evaluate-policy",
        json=music_claim,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    eval1 = res1.json()
    assert eval1["is_compliant"] is False
    assert eval1["requires_special_waiver"] is True
    assert any("THEATRICAL_PERPETUAL_REQUIRED" in v["rule_code"] for v in eval1["violations"])

    # 2. Conforming claim: Perpetual worldwide license passes
    compliant_music = {
        "asset_type": "music_cue",
        "category": "music",
        "description": "Theme Orchestral Cue",
        "term": "perpetual worldwide",
        "territory": "worldwide",
    }
    res2 = client.post(
        f"/api/v1/organizations/{org_id}/productions/{prod_id}/claims/claim_music_100/evaluate-policy",
        json=compliant_music,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    eval2 = res2.json()
    assert eval2["is_compliant"] is True
    assert len(eval2["violations"]) == 0
    assert eval2["requires_special_waiver"] is False
