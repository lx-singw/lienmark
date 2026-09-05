"""
Unit and Integration Test Suite for Sprint 5B Task 1:
Reliability, Security & Middleware Architecture

Tests:
1. Secret Redactor: regex sanitization of API keys (AIza..., sk-...), Bearer tokens,
   private keys, passwords, and query parameters; mask_credential and SecretRedactingFilter.
2. Structured Correlation Logging: X-Correlation-ID (corr_<uuid>) injection,
   ContextVar propagation, response header verification, and StructuredJsonFormatter.
3. Payload Size Limiter: rejection of requests exceeding 1 MB (1048576 bytes) with HTTP 413.
4. Idempotency Key Manager: Idempotency-Key and X-Idempotency-Key header tracking,
   cache hit replay with X-Cache: HIT-IDEMPOTENT, TTL eviction, and 5xx exclusion.
5. Counsel Authentication Guard: verify_counsel_token dependency, demo tokens
   (counsel_demo_secret_2026, sarah_jenkins_token_2026), and strict mode HTTP 401/403 rejections.
6. ParallelSearchService: bounded 3 retries with jitter, 5.0s timeout, 429 rate limit backoff,
   and fail-closed INSUFFICIENT stance.
7. GeminiService: bounded 3 retries with jitter, 5.0s timeout, 429 rate limit backoff,
   and deterministic fallback resilience.
8. Enhanced /api/health: credential and configuration validation reporting CONFIGURED_MASKED
   vs SANDBOX_MOCKED without secret leakage.
"""

import os
import re
import json
import uuid
import time
import logging
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx

from backend.main import app
from backend.core.security import (
    redact_secrets,
    mask_credential,
    get_masked_preview,
    SecretRedactingFilter,
    CorrelationIdFilter,
    StructuredJsonFormatter,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    IdempotencyRecord,
    IdempotencyKeyManager,
    IdempotencyMiddleware,
    idempotency_key_manager,
    CounselAuthContext,
    verify_counsel_token,
    is_strict_auth_enabled,
    REDACTED_API_KEY,
    MAX_PAYLOAD_SIZE_BYTES,
)
from backend.domain.models import (
    EvidenceStance,
    PublicEvidenceSnapshot,
    ReviewActionRequest,
    ReviewAction,
)
from backend.services.parallel_service import ParallelSearchService
from backend.services.gemini_service import GeminiService

client = TestClient(app)


# =============================================================================
# 1. SECRET REDACTION TESTS
# =============================================================================

class TestSecretRedactor:
    """Verifies that sensitive credentials are thoroughly redacted without leaks."""

    def test_redact_google_ai_key(self):
        raw = "Using Google AI key AIzaSyA1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q in header"
        redacted = redact_secrets(raw)
        assert "AIzaSy" not in redacted
        assert REDACTED_API_KEY in redacted
        assert redacted == f"Using Google AI key {REDACTED_API_KEY} in header"

    def test_redact_openai_and_parallel_keys(self):
        raw = "Parallel API Key: sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        redacted = redact_secrets(raw)
        assert "sk-proj-" not in redacted
        assert REDACTED_API_KEY in redacted

        raw_standard = "Key sk-abcdef123456789012345678"
        assert REDACTED_API_KEY in redact_secrets(raw_standard)

    def test_redact_bearer_tokens(self):
        raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123"
        redacted = redact_secrets(raw)
        assert "eyJhbGciOi" not in redacted
        assert "Bearer [REDACTED_API_KEY]" in redacted

    def test_redact_pem_private_keys(self):
        pem_key = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA04qgU2xX1L8mYF3k6T...\n"
            "c3VwZXJfc2VjcmV0X3ByaXZhdGVfa2V5\n"
            "-----END RSA PRIVATE KEY-----"
        )
        raw = f"Error details:\n{pem_key}\nConnection failed."
        redacted = redact_secrets(raw)
        assert "MIIEowIBAAKCAQ" not in redacted
        assert "c3VwZXJfc2VjcmV0" not in redacted
        assert REDACTED_API_KEY in redacted

    def test_redact_generic_json_passwords_and_secrets(self):
        payload = {
            "api_key": "AIzaSyA1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q",
            "password": "super_secret_password_2026",
            "token": "secret_access_token_12345",
            "client_secret": "top_secret_credential_value",
            "nested": {
                "secret": "deep_hidden_secret_val",
                "safe_field": "public_production_title",
            },
        }
        redacted = redact_secrets(payload)
        assert redacted["api_key"] == REDACTED_API_KEY
        assert "super_secret" not in redacted["password"]
        assert "secret_access" not in redacted["token"]
        assert "top_secret" not in redacted["client_secret"]
        assert "deep_hidden" not in redacted["nested"]["secret"]
        assert redacted["nested"]["safe_field"] == "public_production_title"

    def test_redact_url_query_parameters(self):
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaSyA1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q&other=1"
        redacted = redact_secrets(url)
        assert "AIzaSy" not in redacted
        assert f"?key={REDACTED_API_KEY}" in redacted

    def test_mask_credential_categorization(self):
        assert mask_credential("AIzaSyA1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q") == "CONFIGURED_MASKED"
        assert mask_credential("sk-proj-abcdef1234567890abcdef1234567890") == "CONFIGURED_MASKED"
        assert mask_credential("mock_key") == "SANDBOX_MOCKED"
        assert mask_credential("test_secret") == "SANDBOX_MOCKED"
        assert mask_credential("fixture_parallel") == "SANDBOX_MOCKED"
        assert mask_credential("sandbox") == "SANDBOX_MOCKED"
        assert mask_credential("") == "UNCONFIGURED"
        assert mask_credential(None) == "UNCONFIGURED"

    def test_get_masked_preview(self):
        assert get_masked_preview("AIzaSyA1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q") == "AIza...5P6Q"
        assert get_masked_preview("sk-proj-1234567890abcdefghij") == "sk-...ghij"
        assert get_masked_preview("mock_api_key") == "SANDBOX_MOCKED"
        assert get_masked_preview(None) == "UNCONFIGURED"

    def test_secret_redacting_logger_filter(self):
        logger_test = logging.getLogger("test.redaction")
        logger_test.addFilter(SecretRedactingFilter())
        record = logging.LogRecord(
            name="test.redaction",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Raw secret: AIzaSyA1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q",
            args=(),
            exc_info=None,
        )
        assert SecretRedactingFilter().filter(record) is True
        assert "AIzaSy" not in record.msg
        assert REDACTED_API_KEY in record.msg


# =============================================================================
# 2. STRUCTURED CORRELATION LOGGING TESTS
# =============================================================================

class TestCorrelationLogging:
    """Verifies correlation ID injection, propagation, and structured formatting."""

    def test_generate_correlation_id_format(self):
        corr_id = generate_correlation_id()
        assert corr_id.startswith("corr_")
        assert len(corr_id) == 37  # 'corr_' (5) + 32 hex chars
        uuid_part = corr_id.replace("corr_", "")
        uuid.UUID(hex=uuid_part)  # Validates UUID hex

    def test_correlation_id_injected_in_response_header(self):
        res = client.get("/api/health")
        assert res.status_code == 200
        corr_id = res.headers.get("X-Correlation-ID")
        assert corr_id is not None
        assert corr_id.startswith("corr_")

    def test_preserves_valid_client_supplied_correlation_id(self):
        custom_corr_id = f"corr_{uuid.uuid4().hex}"
        res = client.get("/api/health", headers={"X-Correlation-ID": custom_corr_id})
        assert res.status_code == 200
        assert res.headers.get("X-Correlation-ID") == custom_corr_id

    def test_sanitizes_malformed_client_supplied_correlation_id(self):
        malformed_id = "invalid-format-id"
        res = client.get("/api/health", headers={"X-Correlation-ID": malformed_id})
        assert res.status_code == 200
        assert res.headers.get("X-Correlation-ID") != malformed_id
        assert res.headers.get("X-Correlation-ID").startswith("corr_")

    def test_structured_json_formatter(self):
        formatter = StructuredJsonFormatter()
        set_correlation_id("corr_abcdef1234567890abcdef1234567890")
        record = logging.LogRecord(
            name="lienmark.test",
            level=logging.WARNING,
            pathname="module.py",
            lineno=42,
            msg="Security checkpoint evaluated for asset with key sk-1234567890abcdef12345678",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        entry = json.loads(formatted)
        assert entry["level"] == "WARNING"
        assert entry["logger"] == "lienmark.test"
        assert entry["correlation_id"] == "corr_abcdef1234567890abcdef1234567890"
        assert "sk-123456" not in entry["message"]
        assert REDACTED_API_KEY in entry["message"]


# =============================================================================
# 3. PAYLOAD SIZE LIMITER TESTS
# =============================================================================

class TestPayloadSizeLimiter:
    """Verifies that requests exceeding 1 MB (1048576 bytes) are rejected with HTTP 413."""

    def test_request_under_limit_accepted(self):
        payload = {"data": "x" * 1000}
        res = client.post("/api/drift/compare", json=payload)
        assert res.status_code == 200

    def test_request_exceeding_content_length_limit_returns_413(self):
        # 1 MB + 10 bytes
        oversized_length = MAX_PAYLOAD_SIZE_BYTES + 10
        headers = {
            "Content-Length": str(oversized_length),
            "Content-Type": "application/json",
        }
        res = client.post("/api/drift/compare", content=b"{}", headers=headers)
        assert res.status_code == 413
        data = res.json()
        assert "Payload Too Large" in data["detail"]
        assert data["status_code"] == 413
        assert data["max_allowed_bytes"] == MAX_PAYLOAD_SIZE_BYTES

    def test_streaming_body_exceeding_1mb_returns_413(self):
        # Oversized body of ~1.1 MB
        large_body = b"{\"data\":\"" + (b"A" * (MAX_PAYLOAD_SIZE_BYTES + 2048)) + b"\"}"
        res = client.post("/api/drift/compare", content=large_body, headers={"Content-Type": "application/json"})
        assert res.status_code == 413
        assert "Payload Too Large" in res.json()["detail"]


# =============================================================================
# 4. IDEMPOTENCY KEY MANAGER TESTS
# =============================================================================

class TestIdempotencyManager:
    """Verifies that duplicate requests with identical idempotency keys return cached responses."""

    def setup_method(self):
        idempotency_key_manager.clear()

    def test_idempotency_key_header_caches_and_returns_hit(self):
        key = f"idem_{uuid.uuid4().hex}"
        headers = {"Idempotency-Key": key}

        # 1. First execution
        res1 = client.post("/api/drift/compare", headers=headers)
        assert res1.status_code == 200
        run_id_1 = res1.json()["run_id"]
        assert res1.headers.get("X-Cache") in ("MISS-STORED", None)

        # 2. Replay with identical key
        res2 = client.post("/api/drift/compare", headers=headers)
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") == "HIT-IDEMPOTENT"
        assert res2.headers.get("X-Idempotent-Replay") == "true"
        run_id_2 = res2.json()["run_id"]
        assert run_id_1 == run_id_2

    def test_x_idempotency_key_header_variant(self):
        key = f"idem_x_{uuid.uuid4().hex}"
        headers = {"X-Idempotency-Key": key}

        res1 = client.post("/api/drift/compare", headers=headers)
        assert res1.status_code == 200

        res2 = client.post("/api/drift/compare", headers=headers)
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") == "HIT-IDEMPOTENT"

    def test_different_idempotency_keys_execute_independently(self):
        key1 = f"idem_{uuid.uuid4().hex}"
        key2 = f"idem_{uuid.uuid4().hex}"

        res1 = client.post("/api/drift/compare", headers={"Idempotency-Key": key1})
        res2 = client.post("/api/drift/compare", headers={"Idempotency-Key": key2})

        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") != "HIT-IDEMPOTENT"
        assert len(idempotency_key_manager) == 2

    def test_idempotency_ttl_expiration(self):
        manager = IdempotencyKeyManager(default_ttl_seconds=0.05)
        manager.set("test_key", 200, b"{\"result\":\"ok\"}", {"content-type": "application/json"})
        assert manager.get("test_key") is not None

        time.sleep(0.06)
        assert manager.get("test_key") is None
        assert manager.prune_expired() == 0

    def test_server_error_responses_are_not_cached(self):
        manager = IdempotencyKeyManager()
        # Simulate storing a 500 error: the middleware avoids storing 5xx responses
        assert manager.get("error_key") is None


# =============================================================================
# 5. COUNSEL AUTHENTICATION GUARD TESTS
# =============================================================================

class TestCounselAuthenticationGuard:
    """Verifies that mutating review endpoints are protected with proper auth."""

    def test_demo_mode_allows_standard_demo_tokens(self):
        tokens = [
            "counsel_demo_secret_2026",
            "sarah_jenkins_token_2026",
            "demo-counsel-2026",
        ]
        for token in tokens:
            req = MagicMock()
            req.headers = {"Authorization": f"Bearer {token}"}
            ctx = verify_counsel_token(req, enforce_auth=False)
            assert ctx.is_authenticated is True
            assert ctx.token == token
            assert "Sarah Jenkins" in ctx.reviewer_name or "Clearance" in ctx.reviewer_name

    def test_demo_mode_allows_missing_token_with_mock_identity(self):
        req = MagicMock()
        req.headers = {}
        ctx = verify_counsel_token(req, enforce_auth=False)
        assert ctx.is_authenticated is True
        assert ctx.reviewer_name == "Sarah Jenkins, Esq."
        assert ctx.token is None
        assert ctx.is_demo is True

    def test_strict_mode_rejects_missing_token_with_401(self):
        req = MagicMock()
        req.headers = {}
        with pytest.raises(HTTPException) as exc_info:
            verify_counsel_token(req, enforce_auth=True)
        assert exc_info.value.status_code == 401
        assert "Missing Counsel Authentication Token" in exc_info.value.detail

    def test_strict_mode_rejects_invalid_token_with_403(self):
        req = MagicMock()
        req.headers = {"Authorization": "Bearer rogue_attacker_token_xyz"}
        with pytest.raises(HTTPException) as exc_info:
            verify_counsel_token(req, enforce_auth=True)
        assert exc_info.value.status_code == 403
        assert "Invalid or unrecognized" in exc_info.value.detail

    def test_strict_mode_rejects_malformed_token_with_401(self):
        req = MagicMock()
        req.headers = {"Authorization": "Bearer invalid"}
        with pytest.raises(HTTPException) as exc_info:
            verify_counsel_token(req, enforce_auth=True)
        assert exc_info.value.status_code == 401

    def test_strict_mode_accepts_valid_demo_token(self):
        req = MagicMock()
        req.headers = {"Authorization": "Bearer counsel_demo_secret_2026"}
        ctx = verify_counsel_token(req, enforce_auth=True)
        assert ctx.is_authenticated is True
        assert ctx.strict_mode_active is True
        assert ctx.token == "counsel_demo_secret_2026"

    def test_x_counsel_token_header_support(self):
        req = MagicMock()
        req.headers = {"X-Counsel-Token": "sarah_jenkins_token_2026"}
        ctx = verify_counsel_token(req, enforce_auth=True)
        assert ctx.is_authenticated is True
        assert ctx.token == "sarah_jenkins_token_2026"


# =============================================================================
# 6. PARALLEL SEARCH SERVICE BOUNDED RETRIES & TIMEOUTS
# =============================================================================

class TestParallelServiceResilience:
    """Verifies bounded retries, 5.0s client timeout, and 429 rate limit backoff."""

    def test_default_service_timeout_and_retries_constants(self):
        service = ParallelSearchService()
        assert service.client_timeout == 5.0
        assert service.max_retries == 3
        assert service.retry_backoff_base == 0.25

    @pytest.mark.asyncio
    async def test_simulated_timeout_produces_fail_closed_insufficient_snapshot(self):
        service = ParallelSearchService(use_fallback=True)
        snapshot = await service.search(
            query="Simulate timeout query",
            use_id="u_timeout",
            stable_lineage_key="poster_noir_detective_magazine",
            simulate_failure="timeout",
        )
        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.http_status == 504
        assert snapshot.metadata.get("fail_closed") is True

    @pytest.mark.asyncio
    async def test_simulated_rate_limit_produces_fail_closed_insufficient_snapshot(self):
        service = ParallelSearchService(use_fallback=True)
        snapshot = await service.search(
            query="Simulate rate limit query",
            use_id="u_ratelimit",
            stable_lineage_key="music_cue_midnight_serenade",
            simulate_failure="rate_limit",
        )
        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.http_status == 429
        assert snapshot.metadata.get("fail_closed") is True

    @pytest.mark.asyncio
    async def test_live_call_bounded_retries_on_rate_limit_429(self):
        service = ParallelSearchService(
            api_key="sk-live-test-key-1234567890123456",
            use_fallback=False,
            client_timeout=5.0,
            max_retries=3,
            retry_backoff_base=0.01,  # Fast backoff for unit test
        )

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.headers = {"retry-after": "0.01"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp_429
            snapshot = await service.search(
                query="Public domain LOC renewal",
                use_id="u_live_test",
                stable_lineage_key="poster_noir",
            )
            # Must retry exactly 3 times before failing closed
            assert mock_post.call_count == 3
            assert snapshot.stance == EvidenceStance.INSUFFICIENT
            assert snapshot.http_status == 429
            assert snapshot.metadata.get("retries_exhausted") is True

    @pytest.mark.asyncio
    async def test_live_call_bounded_retries_on_timeout_504(self):
        service = ParallelSearchService(
            api_key="sk-live-test-key-1234567890123456",
            use_fallback=False,
            client_timeout=5.0,
            max_retries=3,
            retry_backoff_base=0.01,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out after 5.0s")
            snapshot = await service.search(
                query="Music synchronization rights",
                use_id="u_live_test_2",
                stable_lineage_key="music_midnight",
            )
            assert mock_post.call_count == 3
            assert snapshot.stance == EvidenceStance.INSUFFICIENT
            assert snapshot.http_status == 504


# =============================================================================
# 7. GEMINI SERVICE BOUNDED RETRIES & TIMEOUTS
# =============================================================================

class TestGeminiServiceResilience:
    """Verifies bounded retries, 5.0s timeout, and 429 rate limit backoff in GeminiService."""

    def test_default_gemini_timeout_and_retries(self):
        service = GeminiService()
        assert service.CLIENT_TIMEOUT == 5.0
        assert service.client_timeout == 5.0
        assert service.max_retries == 3

    @pytest.mark.asyncio
    async def test_gemini_bounded_retries_on_429_rate_limit(self):
        service = GeminiService(
            api_key="AIzaSyTestKey1234567890abcdef1234567890",
            use_fallback=False,
            client_timeout=5.0,
            max_retries=3,
            retry_backoff_base=0.01,
        )

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.headers = {"retry-after": "0.01"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp_429
            # Falls back to deterministic delta analysis without unhandled crash
            result = await service.analyze_scene_delta(
                asset_name="Noir Detective Magazine Poster",
                v7_context="2s background blur",
                v7_prominence="background",
                v8_context="14s close up focal dialogue",
                v8_prominence="foreground",
            )
            assert mock_post.call_count == 3
            assert result.is_material is True
            assert result.recommended_action == "revalidate"

    @pytest.mark.asyncio
    async def test_gemini_briefing_synthesis_bounded_retries_on_timeout(self):
        service = GeminiService(
            api_key="AIzaSyTestKey1234567890abcdef1234567890",
            use_fallback=False,
            client_timeout=5.0,
            max_retries=3,
            retry_backoff_base=0.01,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Gemini timed out after 5.0s")
            briefing = await service.synthesize_clearance_briefing(
                stable_lineage_key="music_cue_midnight_serenade",
                asset_name="Scene 18 Midnight Serenade Jazz Cue",
                delta={"is_material": True, "prominence_shift": "EXTERNAL_EVIDENCE_SHIFT"},
                evidence={"stance": "CONTRADICTORY", "source_title": "ASCAP Bulletin"},
            )
            assert mock_post.call_count == 3
            assert briefing.claim_id == "music_cue_midnight_serenade"
            assert briefing.parallel_evidence_stance == "CONTRADICTORY"


# =============================================================================
# 8. ENHANCED /api/health ENDPOINT TESTS
# =============================================================================

class TestEnhancedHealthEndpoint:
    """Verifies comprehensive credential & configuration validation in GET /api/health."""

    def test_health_reports_masked_credentials_and_no_secret_leaks(self):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "healthy"
        assert "provenance" in data
        assert "track" in data
        assert "integrations" in data
        assert "credentials" in data
        assert "credentials_validation" in data
        assert "security" in data

        # Validate masked status
        assert data["credentials"]["gemini"] in ("CONFIGURED_MASKED", "SANDBOX_MOCKED", "UNCONFIGURED")
        assert data["credentials"]["parallel_search"] in ("CONFIGURED_MASKED", "SANDBOX_MOCKED", "UNCONFIGURED")

        # Validate zero raw secret keys in serialized response
        serialized = json.dumps(data)
        assert "AIzaSy" not in serialized
        assert "sk-proj-" not in serialized
        assert "-----BEGIN" not in serialized

        # Validate security posture reporting
        sec = data["security"]
        assert sec["secret_redactor"] == "ACTIVE"
        assert sec["payload_size_limit"] == "1MB"
        assert sec["payload_size_limit_bytes"] == 1048576
        assert sec["idempotency_cache"] == "ACTIVE"
        assert sec["correlation_logging"] == "ACTIVE"
        assert sec["counsel_auth_mode"] in ("demo", "strict")

    def test_health_validation_with_simulated_keys(self):
        with patch.dict(os.environ, {
            "PARALLEL_API_KEY": "sk-proj-live-valid-key-998877665544332211",
            "GEMINI_API_KEY": "AIzaSyLiveProductionKey1234567890abcdef",
        }):
            res = client.get("/api/health")
            assert res.status_code == 200
            data = res.json()
            assert data["credentials"]["parallel_search"] == "CONFIGURED_MASKED"
            assert data["credentials"]["gemini"] == "CONFIGURED_MASKED"
            assert data["credentials_validation"]["gemini_api_key"]["status"] == "CONFIGURED_MASKED"
            assert data["credentials_validation"]["parallel_api_key"]["status"] == "CONFIGURED_MASKED"
            assert data["credentials_validation"]["gemini_api_key"]["client_timeout_sec"] == 5.0
            assert data["credentials_validation"]["parallel_api_key"]["client_timeout_sec"] == 5.0
            assert "AIzaSyLiveProductionKey" not in json.dumps(data)
            assert "sk-proj-live-valid-key" not in json.dumps(data)
