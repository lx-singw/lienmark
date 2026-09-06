"""
tests/test_tenant_middleware.py

Exhaustive verification test suite for Lienmark Multi-Tenant Architecture & Middleware.
Validates:
1. Valid JWT token extraction (tenant_id, user_id, roles)
2. Valid API key extraction and mapping
3. Header-based extraction (X-Organization-Id / X-Tenant-Id)
4. Precedence rules and strict mode conflict resolution
5. Missing credentials fail-closed (HTTP 401 Unauthorized)
6. Invalid, expired, and tampered tokens (HTTP 401 Unauthorized)
7. Unknown / rogue API keys (HTTP 401/403)
8. Exempt route allowlisting (/api/health, /docs, /openapi.json, demo public endpoints)
9. URL path parameter matching ({organization_id} == authenticated tenant -> HTTP 200)
10. URL path parameter mismatch ({organization_id} != authenticated tenant -> HTTP 403 Forbidden)
11. ContextVar request isolation across concurrent async requests

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Set

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from backend.middleware.tenant import (
    TenantContext,
    TenantContextMiddleware,
    get_current_tenant,
    get_current_user,
    get_current_tenant_context,
    get_tenant_context,
    validate_tenant_url_match,
    require_tenant_param,
    api_key_registry,
    _current_tenant_context,
    decode_jwt_token,
)

TEST_JWT_SECRET = "lienmark-test-secret-salt-2026-anti-gravity"


# =============================================================================
# Helper Utilities: Token Generators
# =============================================================================

def create_test_jwt(
    tenant_id: str,
    user_id: str = "usr_test_counsel_001",
    email: str = "counsel@lienmarklegal.com",
    roles: Optional[List[str]] = None,
    claims_extra: Optional[Dict[str, Any]] = None,
    expires_in_seconds: int = 3600,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Creates a signed HMAC-SHA256 test JWT."""
    import hashlib
    import hmac

    header = {"alg": "HS256", "typ": "JWT"}
    payload: Dict[str, Any] = {
        "iss": "https://identity.lienmark.com",
        "aud": "lienmark-clearance-api",
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "org_id": tenant_id,
        "roles": roles or ["authorized_reviewer"],
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds,
    }
    if claims_extra:
        payload.update(claims_extra)

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


# =============================================================================
# Pytest Fixtures & Test Application Builder
# =============================================================================

def build_test_app(strict_mode: bool = False, allow_header_auth: bool = True) -> FastAPI:
    """Constructs a test FastAPI application instrumented with TenantContextMiddleware."""
    test_app = FastAPI(title="Lienmark Tenant Test Gateway")

    test_app.add_middleware(
        TenantContextMiddleware,
        strict_mode=strict_mode,
        allow_header_auth=allow_header_auth,
        jwt_secret=TEST_JWT_SECRET,
    )

    # 1. Exempt routes
    @test_app.get("/api/health")
    def api_health():
        return {"status": "healthy", "service": "lienmark-api"}

    @test_app.get("/health")
    def root_health():
        return {"status": "ok"}

    @test_app.get("/api/demo/state")
    def demo_state():
        return {"mode": "baseline", "total_claims": 12}

    # 2. Protected generic routes
    @test_app.get("/api/clearance/evaluate")
    def protected_evaluate(tenant: TenantContext = Depends(get_tenant_context)):
        return {
            "status": "evaluated",
            "tenant_id": tenant.organization_id,
            "user_id": tenant.user_id,
            "roles": tenant.roles,
            "auth_method": tenant.auth_method,
        }

    # 3. Path parameter scoped routes: /api/organizations/{organization_id}/...
    @test_app.get("/api/organizations/{organization_id}/runs")
    def get_tenant_runs(
        organization_id: str,
        tenant: TenantContext = Depends(validate_tenant_url_match),
    ):
        return {
            "requested_organization": organization_id,
            "authenticated_tenant": tenant.organization_id,
            "runs": [f"run_{organization_id}_cut_v7", f"run_{organization_id}_cut_v8"],
        }

    @test_app.get("/api/organizations/{organization_id}/productions/{production_id}/claims")
    def get_tenant_production_claims(
        organization_id: str,
        production_id: str,
        tenant: TenantContext = Depends(validate_tenant_url_match),
    ):
        return {
            "organization_id": organization_id,
            "production_id": production_id,
            "tenant_id": tenant.organization_id,
            "claims_count": 12,
        }

    # 4. Custom parameter factory scoped route: /api/studios/{studio_id}/evidence
    @test_app.get("/api/studios/{studio_id}/evidence")
    def get_studio_evidence(
        studio_id: str,
        tenant: TenantContext = Depends(require_tenant_param("studio_id")),
    ):
        return {
            "studio_id": studio_id,
            "tenant_id": tenant.organization_id,
        }

    # 5. Async delay route for concurrency testing
    @test_app.get("/api/async/tenant-echo")
    async def async_tenant_echo(
        delay_seconds: float = 0.01,
        tenant: TenantContext = Depends(get_tenant_context),
    ):
        await asyncio.sleep(delay_seconds)
        active_ctx = get_current_tenant_context()
        return {
            "dependency_tenant_id": tenant.organization_id,
            "contextvar_tenant_id": active_ctx.organization_id if active_ctx else None,
            "user_id": tenant.user_id,
            "auth_method": tenant.auth_method,
        }

    return test_app


@pytest.fixture
def permissive_app() -> FastAPI:
    return build_test_app(strict_mode=False, allow_header_auth=True)


@pytest.fixture
def strict_app() -> FastAPI:
    return build_test_app(strict_mode=True, allow_header_auth=False)


@pytest.fixture
def permissive_client(permissive_app: FastAPI) -> TestClient:
    return TestClient(permissive_app)


@pytest.fixture
def strict_client(strict_app: FastAPI) -> TestClient:
    return TestClient(strict_app)


# =============================================================================
# 1. JWT Authentication Verification Tests
# =============================================================================

class TestJwtExtraction:
    """Verifies JWT decoding, claim extraction, and role mapping."""

    def test_valid_jwt_extracts_tenant_user_and_roles(self, permissive_client: TestClient):
        token = create_test_jwt(
            tenant_id="org_warner_bros_001",
            user_id="usr_counsel_sjenkins_9918",
            email="sjenkins@lienmarklegal.com",
            roles=["authorized_reviewer", "production_counsel"],
        )
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_warner_bros_001"
        assert data["user_id"] == "usr_counsel_sjenkins_9918"
        assert data["roles"] == ["authorized_reviewer", "production_counsel"]
        assert data["auth_method"] == "jwt"
        assert res.headers.get("X-Tenant-ID") == "org_warner_bros_001"

    def test_valid_jwt_with_complex_dict_roles(self, permissive_client: TestClient):
        token = create_test_jwt(
            tenant_id="org_universal_002",
            claims_extra={
                "roles": {"prod_tentpole_1": "authorized_reviewer", "prod_indie_2": "viewer"}
            },
        )
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_universal_002"
        assert "authorized_reviewer" in data["roles"]

    def test_invalid_jwt_malformed_token_returns_401(self, permissive_client: TestClient):
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": "Bearer not.a.valid.jwt.payload"},
        )
        assert res.status_code == 401
        assert "Malformed JWT" in res.json()["detail"]
        assert "WWW-Authenticate" in res.headers

    def test_invalid_jwt_expired_token_returns_401(self, permissive_client: TestClient):
        token = create_test_jwt(
            tenant_id="org_warner_bros_001",
            expires_in_seconds=-300,  # Expired 5 minutes ago
        )
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()

    def test_invalid_jwt_bad_signature_returns_401(self, permissive_client: TestClient):
        token = create_test_jwt(
            tenant_id="org_warner_bros_001",
            secret="untrusted-attacker-secret-key",
        )
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401
        assert "signature" in res.json()["detail"].lower()

    def test_missing_tenant_id_in_jwt_returns_401(self, permissive_client: TestClient):
        import hashlib, hmac

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"sub": "usr_rogue", "email": "rogue@domain.com", "exp": int(time.time()) + 3600}
        hb = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        pb = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig = hmac.new(TEST_JWT_SECRET.encode(), f"{hb}.{pb}".encode(), hashlib.sha256).digest()
        token = f"{hb}.{pb}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"

        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401
        assert "missing 'org_id'" in res.json()["detail"]


# =============================================================================
# 2. API Key Authentication Verification Tests
# =============================================================================

class TestApiKeyExtraction:
    """Verifies API key resolution from registry and associated tenant mapping."""

    def test_valid_api_key_header_extracts_mapped_tenant(self, permissive_client: TestClient):
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"X-API-Key": "lmk_live_wb_secret_key_88"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_warner_bros_001"
        assert data["auth_method"] == "api_key"
        assert "service_account" in data["roles"]

    def test_valid_api_key_via_authorization_header(self, permissive_client: TestClient):
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": "Api-Key lmk_live_universal_key_42"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_universal_002"
        assert data["auth_method"] == "api_key"

    def test_unknown_api_key_returns_401(self, permissive_client: TestClient):
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"X-API-Key": "lmk_live_unregistered_rogue_999"},
        )
        assert res.status_code == 401
        assert "Invalid or unknown API key" in res.json()["detail"]


# =============================================================================
# 3. Direct Header Extraction & Precedence Rules
# =============================================================================

class TestHeaderExtractionAndPrecedence:
    """Verifies header extraction, JWT precedence, and strict mode conflict gate."""

    def test_x_organization_id_header_in_permissive_mode(self, permissive_client: TestClient):
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"X-Organization-Id": "org_universal_002"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_universal_002"
        assert data["auth_method"] == "header"

    def test_x_tenant_id_alias_header_in_permissive_mode(self, permissive_client: TestClient):
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"X-Tenant-Id": "org_sony_pictures_003"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_sony_pictures_003"
        assert data["auth_method"] == "header"

    def test_header_auth_rejected_in_strict_mode(self, strict_client: TestClient):
        res = strict_client.get(
            "/api/clearance/evaluate",
            headers={"X-Organization-Id": "org_universal_002"},
        )
        assert res.status_code == 401
        assert "Missing valid tenant authentication credentials" in res.json()["detail"]

    def test_jwt_precedence_over_conflicting_header_in_permissive_mode(
        self, permissive_client: TestClient
    ):
        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-Id": "org_sony_pictures_003",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "org_warner_bros_001"
        assert data["auth_method"] == "jwt"

    def test_header_vs_jwt_conflict_raises_403_in_strict_mode(self, strict_client: TestClient):
        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = strict_client.get(
            "/api/clearance/evaluate",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-Id": "org_sony_pictures_003",
            },
        )
        assert res.status_code == 403
        detail = res.json()["detail"]
        assert "Tenant mismatch in strict mode" in detail
        assert "org_sony_pictures_003" in detail
        assert "org_warner_bros_001" in detail


# =============================================================================
# 4. Fail-Closed Behavior & Route Allowlisting
# =============================================================================

class TestFailClosedAndRouteAllowlisting:
    """Verifies fail-closed defaults and unauthenticated allowlist bypass."""

    def test_missing_credentials_on_protected_route_returns_401(self, strict_client: TestClient):
        res = strict_client.get("/api/clearance/evaluate")
        assert res.status_code == 401
        assert res.headers.get("WWW-Authenticate") == "Bearer"
        assert "Missing valid tenant authentication credentials" in res.json()["detail"]

    @pytest.mark.parametrize(
        "exempt_path",
        [
            "/api/health",
            "/health",
            "/docs",
            "/openapi.json",
            "/api/demo/state",
        ],
    )
    def test_exempt_routes_pass_without_credentials(
        self, strict_client: TestClient, exempt_path: str
    ):
        res = strict_client.get(exempt_path)
        assert res.status_code == 200


# =============================================================================
# 5. URL Parameter Mismatch & Cross-Tenant Access Prevention
# =============================================================================

class TestUrlPathParameterAuthorization:
    """Verifies {organization_id} path parameter consistency against authenticated tenant."""

    def test_route_with_matching_path_param_succeeds(self, permissive_client: TestClient):
        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = permissive_client.get(
            "/api/organizations/org_warner_bros_001/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["requested_organization"] == "org_warner_bros_001"
        assert data["authenticated_tenant"] == "org_warner_bros_001"
        assert len(data["runs"]) == 2

    def test_route_with_mismatched_path_param_returns_403_forbidden(
        self, permissive_client: TestClient
    ):
        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = permissive_client.get(
            "/api/organizations/org_sony_pictures_003/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        data = res.json()
        assert "Cross-tenant access" in data["detail"]
        assert "org_sony_pictures_003" in data["detail"]
        assert "org_warner_bros_001" in data["detail"]

    def test_nested_path_matching_succeeds(self, permissive_client: TestClient):
        token = create_test_jwt(tenant_id="org_universal_002")
        res = permissive_client.get(
            "/api/organizations/org_universal_002/productions/prod_blockbuster_v8/claims",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["organization_id"] == "org_universal_002"
        assert data["claims_count"] == 12

    def test_nested_path_mismatch_fails_closed(self, permissive_client: TestClient):
        token = create_test_jwt(tenant_id="org_universal_002")
        res = permissive_client.get(
            "/api/organizations/org_warner_bros_001/productions/prod_blockbuster_v8/claims",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert "Cross-tenant access" in res.json()["detail"]

    def test_custom_tenant_param_matching(self, permissive_client: TestClient):
        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = permissive_client.get(
            "/api/studios/org_warner_bros_001/evidence",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["studio_id"] == "org_warner_bros_001"

    def test_custom_tenant_param_mismatch_raises_403(self, permissive_client: TestClient):
        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = permissive_client.get(
            "/api/studios/org_paramount_004/evidence",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403


# =============================================================================
# 6. Asynchronous Concurrency & ContextVar Isolation
# =============================================================================

class TestAsyncContextVarIsolation:
    """Verifies that ContextVar state never leaks across concurrent async requests."""

    @pytest.mark.asyncio
    async def test_concurrent_async_requests_maintain_contextvar_isolation(
        self, permissive_app: FastAPI
    ):
        tenants = [
            "org_warner_bros_001",
            "org_universal_002",
            "org_sony_pictures_003",
            "org_paramount_004",
            "org_a24_indie_005",
        ]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=permissive_app), base_url="http://testserver"
        ) as client:

            async def send_concurrent_call(tenant_id: str, index: int) -> Dict[str, Any]:
                token = create_test_jwt(
                    tenant_id=tenant_id,
                    user_id=f"usr_{tenant_id}_{index}",
                )
                delay = (index % 5) * 0.005
                res = await client.get(
                    f"/api/async/tenant-echo?delay_seconds={delay}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert res.status_code == 200, f"Call failed for {tenant_id}: {res.text}"
                payload = res.json()
                assert payload["contextvar_tenant_id"] == tenant_id
                assert payload["dependency_tenant_id"] == tenant_id
                return payload

            tasks = [
                send_concurrent_call(tenants[i % len(tenants)], i)
                for i in range(50)
            ]
            results = await asyncio.gather(*tasks)

            assert len(results) == 50
            for i, r in enumerate(results):
                expected_tenant = tenants[i % len(tenants)]
                assert r["contextvar_tenant_id"] == expected_tenant

    def test_contextvar_is_none_outside_request_lifecycle(self, permissive_client: TestClient):
        assert _current_tenant_context.get() is None

        token = create_test_jwt(tenant_id="org_warner_bros_001")
        res = permissive_client.get(
            "/api/clearance/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200

        # Assert clean reset
        assert _current_tenant_context.get() is None
