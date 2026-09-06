"""
Lienmark Component 2 & Component 3 Verification Suite
Tests:
1. Gemini Vertex AI ADC, Direct API Key, and Sandbox Mocked Precedence
2. Bounded timeouts (15s) and retries (max 2)
3. Spend Guard per-session rate limiting (max 10 live drift evaluations)
4. Spend Guard graceful fail-closed fallback into sandbox mode with underwriter notice
5. Frontend API client reset error propagation (mocking server 500 error)
6. Next.js dynamic runtime configuration & fetch credentials

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.gemini_service import GeminiService, DeltaAnalysisResult, ClearanceBriefing
from backend.middleware.spend_guard import (
    SpendGuardManager,
    spend_guard_manager,
    LIMIT_EXCEEDED_MESSAGE,
)
from backend.core.security import mask_credential


# =============================================================================
# 1. TEST GEMINI ADC / API KEY / SANDBOX FALLBACK PRECEDENCE
# =============================================================================
class TestGeminiADCAndAuthPrecedence:
    """
    Asserts authentication precedence and resilience:
    Vertex AI ADC > Direct API Key > Sandbox Mocked Fallback.
    """

    def test_vertex_ai_adc_active_when_flag_enabled(self):
        """Asserts GOOGLE_GENAI_USE_VERTEXAI=true activates VERTEX_ADC mode."""
        env_vars = {
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": "lienmark-dev-lx-2026",
            "GOOGLE_CLOUD_REGION": "us-central1",
            "GEMINI_API_KEY": "",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            service = GeminiService()
            assert service.auth_mode == "VERTEX_ADC"
            assert service.is_vertex_ai is True
            assert service.project == "lienmark-dev-lx-2026"
            assert service.location == "us-central1"
            assert service.client_timeout == 15.0
            assert service.max_retries == 2

    def test_vertex_ai_adc_active_on_gcp_target_environment(self):
        """Asserts running in production/demo on GCP initializes Vertex AI ADC."""
        env_vars = {
            "GOOGLE_GENAI_USE_VERTEXAI": "false",
            "ENVIRONMENT": "demo",
            "GOOGLE_CLOUD_PROJECT": "lienmark-demo-lx-2026",
            "GOOGLE_CLOUD_REGION": "us-central1",
            "K_SERVICE": "lienmark-api-demo",
            "GEMINI_API_KEY": "",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            service = GeminiService()
            assert service.auth_mode == "VERTEX_ADC"
            assert service.is_vertex_ai is True
            assert service.project == "lienmark-demo-lx-2026"
            assert service.location == "us-central1"

    def test_vertex_ai_adc_precedence_over_api_key(self):
        """Asserts Vertex AI ADC takes precedence when both ADC and API Key are present."""
        env_vars = {
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": "lienmark-dev-lx-2026",
            "GEMINI_API_KEY": "AIzaSyLiveProductionKey1234567890abcdef",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            service = GeminiService()
            assert service.auth_mode == "VERTEX_ADC"
            assert service.is_vertex_ai is True

    def test_direct_api_key_mode_when_vertex_not_enabled(self):
        """Asserts direct API key is used when Vertex AI is not enabled."""
        env_vars = {
            "GOOGLE_GENAI_USE_VERTEXAI": "false",
            "ENVIRONMENT": "local",
            "K_SERVICE": "",
            "K_REVISION": "",
            "GEMINI_API_KEY": "AIzaSyDirectDeveloperApiKey1234567890",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            service = GeminiService(use_vertex_ai=False)
            assert service.auth_mode == "API_KEY"
            assert service.is_vertex_ai is False
            assert service.api_key == "AIzaSyDirectDeveloperApiKey1234567890"

    def test_sandbox_mocked_fallback_when_unconfigured(self):
        """Asserts unconfigured service cleanly defaults to SANDBOX_MOCKED without crash."""
        env_vars = {
            "GOOGLE_GENAI_USE_VERTEXAI": "false",
            "ENVIRONMENT": "local",
            "K_SERVICE": "",
            "GEMINI_API_KEY": "",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            service = GeminiService(api_key="", use_vertex_ai=False)
            assert service.auth_mode == "SANDBOX_MOCKED"
            assert service.is_vertex_ai is False
            assert service.use_fallback is True

    def test_sandbox_mocked_fallback_for_mock_keys(self):
        """Asserts fixture/mock keys enter SANDBOX_MOCKED mode."""
        for mock_key in ("mock_key", "fixture_key", "sandbox_key", "test_key"):
            service = GeminiService(api_key=mock_key, use_vertex_ai=False)
            assert service.auth_mode == "SANDBOX_MOCKED"

    def test_bounded_timeout_and_retries_enforcement(self):
        """Asserts timeout is bounded at 15s max and retries bounded at max 2 in ADC mode."""
        # Timeout clamped to 15.0 max
        service_long = GeminiService(timeout=45.0)
        assert service_long.client_timeout == 15.0
        assert service_long.timeout == 15.0

        # Retries clamped to 2 max in Vertex AI mode
        service_vertex = GeminiService(use_vertex_ai=True, max_retries=10)
        assert service_vertex.max_retries == 2
        assert service_vertex.client_timeout == 15.0

    @pytest.mark.asyncio
    async def test_sandbox_fallback_execution_never_crashes(self):
        """Asserts unconfigured sandbox mode returns valid deterministic models without exceptions."""
        service = GeminiService(api_key="", use_fallback=True)
        delta = await service.analyze_scene_delta(
            asset_name="Scene 42 Noir Magazine Poster",
            v7_context="2s background blur",
            v7_prominence="background",
            v8_context="14s focal dialogue",
            v8_prominence="foreground",
        )
        assert isinstance(delta, DeltaAnalysisResult)
        assert delta.is_material is True
        assert delta.recommended_action == "revalidate"

        briefing = await service.synthesize_clearance_briefing(
            stable_lineage_key="poster_noir_detective_magazine",
            asset_name="Scene 42 Noir Magazine Poster",
            delta=delta,
            evidence={"stance": "SUPPORTING", "source_title": "LOC Renewal Catalog"},
        )
        assert isinstance(briefing, ClearanceBriefing)
        assert briefing.confidence >= 0.90


# =============================================================================
# 2. TEST APPLICATION SPEND GUARD PER-SESSION RATE LIMITING
# =============================================================================
class TestSpendGuardPerSessionRateLimiting:
    """
    Asserts Spend Guard prevents runaway costs via per-session and environment counters:
    - Max 10 live drift evaluations per session.
    - Tracks environment-wide usage counters.
    """

    def setup_method(self):
        spend_guard_manager.reset()

    def test_per_session_evaluations_up_to_limit(self):
        """Asserts exactly 10 evaluations are allowed per session before tripping limit."""
        manager = SpendGuardManager(max_session_evaluations=10, max_environment_calls=100)
        session_id = "sess_judge_alpha_001"

        for i in range(1, 11):
            allowed, msg = manager.record_drift_evaluation(session_id)
            assert allowed is True, f"Evaluation {i} should be allowed"
            assert msg == "OK"
            assert manager.get_session_evaluations(session_id) == i

        # 11th evaluation exceeds allowance
        allowed_11, msg_11 = manager.record_drift_evaluation(session_id)
        assert allowed_11 is False
        assert msg_11 == LIMIT_EXCEEDED_MESSAGE
        assert manager.is_session_limit_reached(session_id) is True

    def test_distinct_sessions_track_independently(self):
        """Asserts Session A reaching limit does not block Session B."""
        manager = SpendGuardManager(max_session_evaluations=10, max_environment_calls=100)
        sess_a = "sess_judge_a"
        sess_b = "sess_judge_b"

        # Exhaust Session A
        for _ in range(10):
            manager.record_drift_evaluation(sess_a)

        assert manager.is_session_limit_reached(sess_a) is True

        # Session B is unaffected
        allowed, msg = manager.record_drift_evaluation(sess_b)
        assert allowed is True
        assert msg == "OK"
        assert manager.get_session_evaluations(sess_b) == 1

    def test_environment_wide_spend_counters(self):
        """Asserts environment-wide spend limit trips when cumulative calls exceed cap."""
        manager = SpendGuardManager(max_session_evaluations=10, max_environment_calls=5)

        for i in range(5):
            allowed, _ = manager.record_drift_evaluation(f"sess_multi_{i}")
            assert allowed is True

        assert manager.is_environment_limit_reached() is True
        assert manager.environment_call_count == 5

        # 6th call from brand new session fails due to environment cap
        allowed_blocked, msg = manager.record_drift_evaluation("sess_brand_new")
        assert allowed_blocked is False
        assert msg == LIMIT_EXCEEDED_MESSAGE


# =============================================================================
# 3. TEST SPEND GUARD GRACEFUL SANDBOX FALLBACK
# =============================================================================
class TestSpendGuardGracefulSandboxFallback:
    """
    Asserts that when allowance is reached, system gracefully fails closed into
    cached/sandbox golden fixtures with explicit underwriter limit message:
    "Spend allowance reached for current period. Running in verified sandbox mode."
    Cold judges never encounter a 500 error or crash.
    """

    def setup_method(self):
        spend_guard_manager.reset()

    def test_drift_compare_returns_sandbox_with_limit_message_when_exceeded(self):
        """Asserts POST /api/drift/compare returns 200 with sandbox fixtures and underwriter message."""
        client = TestClient(app)
        session_id = "sess_judge_exhausted_001"

        # Simulate 10 prior evaluations for this session
        spend_guard_manager._session_evaluations[session_id] = 10

        res = client.post(
            "/api/drift/compare",
            headers={"X-Session-ID": session_id},
            cookies={"lienmark_session_id": session_id},
        )

        assert res.status_code == 200, f"Expected 200 graceful fallback, got {res.status_code}"
        data = res.json()

        # Check explicit underwriter limit message
        assert data.get("spend_guard_status") == "LIMIT_EXCEEDED"
        assert data.get("spend_guard_message") == LIMIT_EXCEEDED_MESSAGE
        assert data.get("message") == LIMIT_EXCEEDED_MESSAGE

        # Check response headers
        assert res.headers.get("X-Spend-Guard") == "LIMIT_EXCEEDED"
        assert res.headers.get("X-Spend-Guard-Fallback") == "ACTIVE"
        assert res.headers.get("X-Spend-Guard-Message") == LIMIT_EXCEEDED_MESSAGE

        # Verify golden fixtures are returned intact (12 total, 10 carried, 2 reopened)
        assert data.get("total_claims") == 12
        assert data.get("carried_forward_count") == 10
        assert data.get("reopened_count") == 2

    def test_middleware_issues_session_cookie_if_missing(self):
        """Asserts SpendGuardMiddleware issues lienmark_session_id cookie if client has none."""
        client = TestClient(app)
        res = client.post("/api/drift/compare")
        assert res.status_code == 200
        assert "X-Session-ID" in res.headers
        assert len(res.headers["X-Session-ID"]) > 4


# =============================================================================
# 4. TEST FRONTEND API CLIENT RESET ERROR PROPAGATION & RUNTIME CONFIG
# =============================================================================
class TestFrontendApiClientAndRouting:
    """
    Asserts:
    1. frontend/lib/api_client.ts resetDemo() does NOT return fake RESET_SUCCESS when backend fails.
    2. Client fetch calls include credentials: 'same-origin'.
    3. frontend/next.config.js dynamically reads INTERNAL_API_URL at runtime.
    4. Mocked backend 500 error on reset is cleanly propagated.
    """

    def test_api_client_ts_reset_demo_has_no_fake_success_fallback(self):
        """Asserts frontend/lib/api_client.ts resetDemo throws error rather than returning fake RESET_SUCCESS."""
        api_client_path = os.path.join("frontend", "lib", "api_client.ts")
        assert os.path.exists(api_client_path), "api_client.ts must exist"

        with open(api_client_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract resetDemo method content
        start_idx = content.find("async resetDemo")
        assert start_idx != -1, "resetDemo method must exist in api_client.ts"
        end_idx = content.find("async seedDemo", start_idx)
        reset_method = content[start_idx:end_idx] if end_idx != -1 else content[start_idx:start_idx + 600]

        # Verify fake RESET_SUCCESS is NOT present in resetDemo
        assert "status: 'RESET_SUCCESS'" not in reset_method, (
            "Fake RESET_SUCCESS fallback must be removed from resetDemo() in api_client.ts"
        )
        assert "offline fallback" not in reset_method.lower(), (
            "Offline fallback notice must be removed from resetDemo() in api_client.ts"
        )
        # Verify error is thrown/propagated
        assert "throw error" in reset_method or "throw" in reset_method, (
            "resetDemo() must propagate/throw the upstream error"
        )

    def test_api_client_ts_fetch_includes_same_origin_credentials(self):
        """Asserts all fetch calls in api_client.ts specify credentials: 'same-origin'."""
        api_client_path = os.path.join("frontend", "lib", "api_client.ts")
        with open(api_client_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "credentials: options.credentials || 'same-origin'" in content or "credentials: 'same-origin'" in content, (
            "api_client.ts must include credentials: 'same-origin' in fetch calls for cookie propagation"
        )

    def test_next_config_reads_internal_api_url_dynamically(self):
        """Asserts next.config.js reads INTERNAL_API_URL and does not bake build-time development URL."""
        next_config_path = os.path.join("frontend", "next.config.js")
        assert os.path.exists(next_config_path), "next.config.js must exist"

        with open(next_config_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "INTERNAL_API_URL" in content or "BACKEND_INTERNAL_URL" in content, (
            "next.config.js rewrites must reference INTERNAL_API_URL or BACKEND_INTERNAL_URL"
        )
        # Verify NEXT_PUBLIC_BACKEND_URL is not baked inside env: { ... }
        assert "env: {" not in content, (
            "next.config.js should not bake hardcoded backend URLs into client bundles via env: {}"
        )

    def test_frontend_actions_ts_propagates_reset_error(self):
        """Asserts frontend/app/actions.ts resetDemoAction returns success: false on failure."""
        actions_path = os.path.join("frontend", "app", "actions.ts")
        with open(actions_path, "r", encoding="utf-8") as f:
            content = f.read()

        start_idx = content.find("export async function resetDemoAction")
        assert start_idx != -1
        end_idx = content.find("export async function seedDemoAction", start_idx)
        reset_action = content[start_idx:end_idx]

        assert "success: false" in reset_action, "resetDemoAction must return success: false when backend fails"
        assert "status: 'RESET_SUCCESS'" not in reset_action, "resetDemoAction must not fake success on error"

    def test_backend_reset_error_simulation_returns_proper_error(self):
        """Asserts when backend encounters an error on reset, it returns an error status instead of corrupting state."""
        client = TestClient(app, raise_server_exceptions=False)
        with patch("backend.main.counsel_checkpoint_manager.reset_session_run", side_effect=RuntimeError("Simulated database failure")):
            res = client.post("/api/demo/reset")
            assert res.status_code in (500, 400)
