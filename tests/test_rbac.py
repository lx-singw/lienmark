"""
tests/test_rbac.py

Comprehensive test suite verifying Lienmark Role-Based Access Control (RBAC):
1. LienmarkRole & LienmarkPermission Enums with string normalization & alias resolution.
2. Fast role extraction from TenantContext, production-scoped roles, and CounselAuthContext.
3. Route decorators (@require_role, @require_permission) across sync and async handlers.
4. FastAPI dependencies (RequireRole, RequirePermission) via Depends().
5. Fail-closed HTTP 403 rejections with structured JSON errors, headers, and diagnostic logging.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Any, Dict, List, Optional
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from backend.core.rbac import (
    LienmarkRole,
    LienmarkPermission,
    RBACContext,
    RBACAccessDeniedException,
    RequireRole,
    RequirePermission,
    require_role,
    require_permission,
    extract_rbac_context,
    get_rbac_context,
    normalize_role_name,
)
from backend.middleware.tenant import (
    TenantContext,
    _current_tenant_context,
)
from backend.core.security import (
    CounselAuthContext,
    SARAH_JENKINS_IDENTITY,
    ELENA_VANCE_IDENTITY,
)


# =============================================================================
# 1. Role & Permission Enums & Alias Normalization Tests
# =============================================================================

class TestRoleAndPermissionEnums:
    def test_canonical_roles_defined(self):
        assert LienmarkRole.PRODUCER.value == "producer"
        assert LienmarkRole.ANALYST.value == "analyst"
        assert LienmarkRole.REVIEWER.value == "reviewer"
        assert LienmarkRole.ADMIN.value == "admin"
        assert LienmarkRole.VIEWER.value == "viewer"

    @pytest.mark.parametrize(
        "raw_input,expected_role",
        [
            # Direct canonical values
            ("producer", LienmarkRole.PRODUCER),
            ("analyst", LienmarkRole.ANALYST),
            ("reviewer", LienmarkRole.REVIEWER),
            ("admin", LienmarkRole.ADMIN),
            ("viewer", LienmarkRole.VIEWER),
            # Uppercase & casing
            ("PRODUCER", LienmarkRole.PRODUCER),
            ("Reviewer", LienmarkRole.REVIEWER),
            ("aDmiN", LienmarkRole.ADMIN),
            # Producer / Post Supervisor aliases
            ("post_supervisor", LienmarkRole.PRODUCER),
            ("post-supervisor", LienmarkRole.PRODUCER),
            ("Post Supervisor", LienmarkRole.PRODUCER),
            ("post_super", LienmarkRole.PRODUCER),
            ("production_coordinator", LienmarkRole.PRODUCER),
            ("lead_producer", LienmarkRole.PRODUCER),
            ("executive_producer", LienmarkRole.PRODUCER),
            # Reviewer / Counsel aliases
            ("authorized_reviewer", LienmarkRole.REVIEWER),
            ("counsel", LienmarkRole.REVIEWER),
            ("lead_counsel", LienmarkRole.REVIEWER),
            ("associate_counsel", LienmarkRole.REVIEWER),
            ("production_attorney", LienmarkRole.REVIEWER),
            ("attorney", LienmarkRole.REVIEWER),
            ("legal", LienmarkRole.REVIEWER),
            ("clearance_counsel", LienmarkRole.REVIEWER),
            ("judge", LienmarkRole.REVIEWER),
            # Analyst aliases
            ("clearance_analyst", LienmarkRole.ANALYST),
            ("researcher", LienmarkRole.ANALYST),
            ("paralegal", LienmarkRole.ANALYST),
            ("automated_agent_pipeline", LienmarkRole.ANALYST),
            ("service_account", LienmarkRole.ANALYST),
            # Admin aliases
            ("superadmin", LienmarkRole.ADMIN),
            ("studio_admin", LienmarkRole.ADMIN),
            ("studio_executive", LienmarkRole.ADMIN),
            ("owner", LienmarkRole.ADMIN),
            # Viewer aliases
            ("read_only", LienmarkRole.VIEWER),
            ("readonly", LienmarkRole.VIEWER),
            ("observer", LienmarkRole.VIEWER),
            ("auditor", LienmarkRole.VIEWER),
            ("guest", LienmarkRole.VIEWER),
        ],
    )
    def test_role_alias_normalization(self, raw_input, expected_role):
        assert LienmarkRole.normalize(raw_input) == expected_role
        assert LienmarkRole.from_value(raw_input) == expected_role

    def test_unrecognized_role_handling(self):
        assert LienmarkRole.normalize("unrecognized_intruder") is None
        assert LienmarkRole.normalize("") is None
        assert LienmarkRole.normalize(None) is None

        with pytest.raises(ValueError, match="Unrecognized role string"):
            LienmarkRole.from_value("unrecognized_intruder")

        # Fallback default
        assert LienmarkRole.from_value("unknown", default=LienmarkRole.VIEWER) == LienmarkRole.VIEWER

    def test_coerce_set(self):
        raw = ["post_supervisor", "counsel", "invalid_role", "admin"]
        roles = LienmarkRole.coerce_set(raw)
        assert roles == {LienmarkRole.PRODUCER, LienmarkRole.REVIEWER, LienmarkRole.ADMIN}

    def test_permission_normalization_and_matrix(self):
        assert LienmarkPermission.normalize("claim:approve") == LienmarkPermission.CLAIM_APPROVE
        assert LienmarkPermission.normalize("CLAIM_APPROVE") == LienmarkPermission.CLAIM_APPROVE
        assert LienmarkPermission.normalize("claim_approve") == LienmarkPermission.CLAIM_APPROVE
        assert LienmarkPermission.normalize("intake:submit") == LienmarkPermission.INTAKE_SUBMIT

        # Check default matrix assignments
        assert LienmarkPermission.CLAIM_APPROVE in LienmarkRole.REVIEWER.permissions
        assert LienmarkPermission.CLAIM_APPROVE not in LienmarkRole.PRODUCER.permissions
        assert LienmarkPermission.CLAIM_APPROVE not in LienmarkRole.VIEWER.permissions

        # Admin has all permissions
        for perm in LienmarkPermission:
            assert perm in LienmarkRole.ADMIN.permissions

        # Producers can submit intake and trigger pipeline
        assert LienmarkRole.PRODUCER.has_permission(LienmarkPermission.INTAKE_SUBMIT)
        assert LienmarkRole.PRODUCER.has_permission(LienmarkPermission.PIPELINE_TRIGGER)


# =============================================================================
# 2. Fast Role Extraction Tests (TenantContext & CounselAuthContext)
# =============================================================================

class TestRoleExtraction:
    def test_extract_from_tenant_context_global_and_production(self):
        tenant = TenantContext(
            organization_id="org_wb_001",
            user_id="usr_producer_123",
            roles=["post_supervisor"],
            production_roles={"prod_action_hero": "authorized_reviewer"},
            auth_method="jwt",
        )

        app = FastAPI()
        client = TestClient(app)

        # Mock request with tenant attached
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "path_params": {},
            "query_string": b"",
        }
        req = Request(scope)
        req.state.tenant = tenant

        # 1. Global context extraction
        rbac_global = extract_rbac_context(req)
        assert LienmarkRole.PRODUCER in rbac_global.roles
        assert LienmarkRole.REVIEWER not in rbac_global.roles

        # 2. Production context extraction
        # Clear cache to simulate a route scoped to prod_action_hero
        del req.state._lienmark_rbac_context
        rbac_prod = extract_rbac_context(req, production_id="prod_action_hero")
        assert LienmarkRole.PRODUCER in rbac_prod.roles
        assert LienmarkRole.REVIEWER in rbac_prod.roles
        assert rbac_prod.has_permission(LienmarkPermission.CLAIM_APPROVE)

    def test_extract_from_counsel_auth_context(self):
        counsel_auth = CounselAuthContext(
            reviewer_name="Sarah Jenkins, Esq.",
            token="sarah_jenkins_token_2026",
            is_authenticated=True,
            is_demo=True,
            reviewer_identity=SARAH_JENKINS_IDENTITY,
        )

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/counsel/checkpoint",
            "headers": [],
            "path_params": {},
            "query_string": b"",
        }
        req = Request(scope)
        req.state.counsel_auth = counsel_auth

        rbac = extract_rbac_context(req)
        assert LienmarkRole.REVIEWER in rbac.roles
        assert rbac.is_authenticated is True
        assert rbac.user_id == SARAH_JENKINS_IDENTITY.reviewer_id
        assert rbac.has_permission(LienmarkPermission.CLAIM_APPROVE)

    def test_extract_caching_on_request_state(self):
        tenant = TenantContext(
            organization_id="org_demo_001",
            roles=["viewer"],
            auth_method="header",
        )
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/status",
            "headers": [],
            "path_params": {},
            "query_string": b"",
        }
        req = Request(scope)
        req.state.tenant = tenant

        rbac_first = extract_rbac_context(req)
        rbac_second = extract_rbac_context(req)
        assert rbac_first is rbac_second  # Same instance cached on request.state


# =============================================================================
# 3. Decorator Tests (@require_role & @require_permission)
# =============================================================================

class TestRouteDecorators:
    def test_decorator_preserves_function_signature_and_metadata(self):
        @require_role(LienmarkRole.REVIEWER)
        async def sample_async_route(request: Request, claim_id: str, count: int = 5) -> Dict[str, Any]:
            """Sample docstring for doc generation."""
            return {"claim_id": claim_id, "count": count}

        assert sample_async_route.__name__ == "sample_async_route"
        assert sample_async_route.__doc__ == "Sample docstring for doc generation."
        sig = inspect.signature(sample_async_route)
        assert "claim_id" in sig.parameters
        assert "count" in sig.parameters
        assert "request" in sig.parameters

    def test_decorator_sync_and_async_in_fastapi(self):
        app = FastAPI()

        @app.get("/async-counsel-only")
        @require_role(LienmarkRole.REVIEWER)
        async def async_counsel_endpoint(request: Request):
            return {"status": "authorized_async"}

        @app.get("/sync-admin-only")
        @require_role(LienmarkRole.ADMIN)
        def sync_admin_endpoint(request: Request):
            return {"status": "authorized_sync"}

        @app.get("/sync-permission-endpoint")
        @require_permission(LienmarkPermission.INTAKE_SUBMIT)
        def sync_permission_endpoint(request: Request):
            return {"status": "authorized_submit"}

        client = TestClient(app)

        # 1. Access without credentials -> 403 Forbidden fail-closed
        resp = client.get("/async-counsel-only")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        data = resp.json()["detail"]
        assert data["error"] == "FORBIDDEN"
        assert "reviewer" in data["required"]
        assert "correlation_id" in data

        # 2. Access with counsel token -> 200 OK
        resp_counsel = client.get(
            "/async-counsel-only",
            headers={"Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert resp_counsel.status_code == status.HTTP_200_OK
        assert resp_counsel.json() == {"status": "authorized_async"}

        # 3. Access admin route with counsel token -> 403 Forbidden
        resp_admin_fail = client.get(
            "/sync-admin-only",
            headers={"Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert resp_admin_fail.status_code == status.HTTP_403_FORBIDDEN

    def test_decorator_without_explicit_request_parameter(self):
        """Tests that @require_role can resolve TenantContext from ContextVar even if request is not an argument."""
        app = FastAPI()

        @app.get("/no-request-param")
        @require_role(LienmarkRole.PRODUCER)
        def no_param_endpoint():
            return {"status": "producer_confirmed"}

        client = TestClient(app)

        # Without context -> 403 Forbidden
        resp = client.get("/no-request-param")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        # Set ContextVar
        token = _current_tenant_context.set(
            TenantContext(
                organization_id="org_test",
                roles=["post_supervisor"],
                auth_method="jwt",
            )
        )
        try:
            resp_ok = client.get("/no-request-param")
            assert resp_ok.status_code == status.HTTP_200_OK
            assert resp_ok.json() == {"status": "producer_confirmed"}
        finally:
            _current_tenant_context.reset(token)


# =============================================================================
# 4. FastAPI Dependency Tests (RequireRole & RequirePermission via Depends)
# =============================================================================

class TestFastAPIDependencies:
    def test_require_role_dependency_injection(self):
        app = FastAPI()

        @app.post("/api/claims/{claim_id}/approve")
        async def approve_claim_endpoint(
            claim_id: str,
            rbac: RBACContext = Depends(RequireRole(LienmarkRole.REVIEWER)),
        ):
            return {
                "claim_id": claim_id,
                "approved_by": rbac.user_id,
                "roles": [r.value for r in rbac.roles],
            }

        client = TestClient(app)

        # 1. Missing role -> 403 Forbidden
        resp = client.post("/api/claims/CLM-001/approve")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        err = resp.json()["detail"]
        assert err["error_code"] == "INSUFFICIENT_ROLE"
        assert "reviewer" in err["required"]

        # 2. Valid counsel token -> 200 OK with injected RBACContext
        resp_ok = client.post(
            "/api/claims/CLM-001/approve",
            headers={"Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert resp_ok.status_code == status.HTTP_200_OK
        data = resp_ok.json()
        assert data["claim_id"] == "CLM-001"
        assert data["approved_by"] == SARAH_JENKINS_IDENTITY.reviewer_id
        assert "reviewer" in data["roles"]

    def test_require_permission_dependency(self):
        app = FastAPI()

        @app.post(
            "/api/intake/submit",
            dependencies=[Depends(RequirePermission(LienmarkPermission.INTAKE_SUBMIT))],
        )
        async def submit_intake():
            return {"status": "intake_accepted"}

        client = TestClient(app)

        # 1. Reviewer lacks INTAKE_SUBMIT permission -> 403 Forbidden
        resp_reviewer = client.post(
            "/api/intake/submit",
            headers={"Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert resp_reviewer.status_code == status.HTTP_403_FORBIDDEN
        err = resp_reviewer.json()["detail"]
        assert err["error_code"] == "INSUFFICIENT_PERMISSIONS"
        assert LienmarkPermission.INTAKE_SUBMIT.value in err["required"]

    def test_admin_bypass(self):
        app = FastAPI()

        @app.get(
            "/restricted",
            dependencies=[Depends(RequireRole(LienmarkRole.REVIEWER, admin_bypass=True))],
        )
        def restricted_route(rbac: RBACContext = Depends(get_rbac_context)):
            return {"status": "ok", "roles": [r.value for r in rbac.roles]}

        client = TestClient(app)

        # Set tenant with ADMIN role
        token = _current_tenant_context.set(
            TenantContext(
                organization_id="org_admin_001",
                roles=["admin"],
                auth_method="jwt",
            )
        )
        try:
            resp = client.get("/restricted")
            assert resp.status_code == status.HTTP_200_OK
            assert "admin" in resp.json()["roles"]
        finally:
            _current_tenant_context.reset(token)


# =============================================================================
# 5. Fail-Closed Diagnostics & Security Headers Tests
# =============================================================================

class TestFailClosedDiagnostics:
    def test_structured_error_response_format(self):
        app = FastAPI()

        @app.get("/secret-zone")
        def secret_zone(rbac: RBACContext = Depends(RequireRole(LienmarkRole.ADMIN))):
            return {"secret": 42}

        client = TestClient(app)
        resp = client.get("/secret-zone")

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.headers.get("X-Security-Policy") == "fail-closed-rbac"
        assert resp.headers.get("X-Correlation-ID") is not None

        body = resp.json()
        assert "detail" in body
        detail = body["detail"]
        assert detail["error"] == "FORBIDDEN"
        assert detail["status_code"] == 403
        assert detail["check_type"] == "role"
        assert detail["required"] == ["admin"]
        assert detail["granted"] == []
        assert "timestamp" in detail
        assert "correlation_id" in detail
