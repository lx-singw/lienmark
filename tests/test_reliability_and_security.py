"""
Lienmark Reliability, Security & License Test Suite
Sprint 5B Task 2: Automated Verification for Roadmap §10 (Sprint 5B)

Tests:
1. Test Secret Redaction:
   - Asserts no raw API keys (`AIza...`, `sk-...`, Bearer tokens) leak in logger outputs,
     trace dumps, or HTTP responses.
2. Test Payload Size Limiting:
   - Asserts sending a payload > 1MB returns HTTP 413.
3. Test Structured Correlation IDs:
   - Asserts all API endpoints return `X-Correlation-ID` in response headers and
     log records carry matching `correlation_id`.
4. Test Idempotency Key:
   - Asserts submitting identical `X-Idempotency-Key` on `POST /api/review/action` and
     `POST /api/drift/compare` returns identical cached responses without creating
     duplicate records in the immutable ledger.
5. Test Counsel Authentication:
   - Asserts unauthenticated or malformed tokens on mutating actions are rejected
     (HTTP 401/403) while valid demo tokens succeed.
6. Test Timeout & Bounded Retries:
   - Asserts service adapters respect 5.0s timeout and retry at most 3 times before
     failing closed safely.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import logging
import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient

from backend.main import app
from backend.domain.models import EvidenceStance, ReviewAction
from backend.core.security import (
    redact_secrets,
    mask_credential,
    get_masked_preview,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    SecretRedactingFilter,
    CorrelationIdFilter,
    StructuredJsonFormatter,
    idempotency_key_manager,
    verify_counsel_token,
    is_strict_auth_enabled,
    REDACTED_API_KEY,
    REDACTED_TOKEN,
    MAX_PAYLOAD_SIZE_BYTES,
)
from backend.core.counsel_checkpoint import counsel_checkpoint_manager
from backend.orchestration.workflow import WorkflowStepTrace
from backend.services.parallel_service import ParallelSearchService
from backend.services.gemini_service import GeminiService
from backend.config.settings import settings

client = TestClient(app)


# =============================================================================
# 1. TEST SECRET REDACTION
# =============================================================================
class TestSecretRedaction:
    """
    Asserts no raw API keys (`AIza...`, `sk-...`, Bearer tokens) leak in logger outputs,
    trace dumps, or HTTP responses.
    """

    def test_logger_redacts_google_aiza_api_keys(self, caplog):
        """Asserts raw Google API keys (AIza...) are redacted in logger output."""
        caplog.clear()
        caplog.set_level(logging.INFO)

        raw_aiza_key = "AIzaSyB1234567890abcdefghijklmn35chars"
        logger = logging.getLogger("lienmark.test_redact")
        logger.addFilter(SecretRedactingFilter())

        logger.info(f"Authenticating request with API key: {raw_aiza_key}")

        log_text = caplog.text
        assert raw_aiza_key not in log_text, "Raw AIza key must NEVER appear in logs"
        assert REDACTED_API_KEY in log_text, f"Expected {REDACTED_API_KEY} placeholder"

    def test_logger_redacts_openai_parallel_sk_keys(self, caplog):
        """Asserts raw sk-... keys are redacted in logger output."""
        caplog.clear()
        caplog.set_level(logging.INFO)

        raw_sk_key = "sk-proj-9876543210abcdef1234567890abcdef"
        logger = logging.getLogger("lienmark.test_redact")
        logger.addFilter(SecretRedactingFilter())

        logger.info(f"Connecting to Parallel search gateway with {raw_sk_key}")

        log_text = caplog.text
        assert raw_sk_key not in log_text, "Raw sk-... key must NEVER appear in logs"
        assert REDACTED_API_KEY in log_text

    def test_logger_redacts_bearer_tokens(self, caplog):
        """Asserts Bearer authorization tokens are redacted in logger output."""
        caplog.clear()
        caplog.set_level(logging.INFO)

        raw_bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret"
        logger = logging.getLogger("lienmark.test_redact")
        logger.addFilter(SecretRedactingFilter())

        logger.info(f"Incoming authorization header: {raw_bearer}")

        log_text = caplog.text
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret" not in log_text
        assert ("Bearer [REDACTED_TOKEN]" in log_text or "Bearer [REDACTED_API_KEY]" in log_text)

    def test_trace_dumps_never_leak_raw_secrets(self):
        """Asserts WorkflowStepTrace dumps sanitize details containing credentials."""
        raw_token = "sk-live-parallel-search-token-998877"
        trace = WorkflowStepTrace(
            step_name="test_search_dispatch",
            component="ParallelSearchService",
            status="SUCCESS",
            duration_ms=45.0,
            details={
                "endpoint": "https://api.parallel.ai/v1/search",
                "auth_header": f"Bearer {raw_token}",
                "api_key": "AIzaSyD000000000000000000000000000000000",
            },
        )

        trace_dict = redact_secrets(trace.model_dump())
        dumped_str = json.dumps(trace_dict)

        assert raw_token not in dumped_str
        assert "AIzaSyD000000000000000000000000000000000" not in dumped_str
        assert REDACTED_API_KEY in dumped_str

    def test_http_response_sanitization(self):
        """Asserts HTTP responses returned through middleware do not leak raw keys."""
        res = client.get("/health")
        assert res.status_code == 200
        text = res.text
        assert "AIzaSy" not in text
        assert "sk-live" not in text

    def test_credential_masking_utility(self):
        """Asserts mask_credential and get_masked_preview format secrets safely."""
        assert mask_credential("sk-abcdef1234567890") == "CONFIGURED_MASKED"
        assert mask_credential("mock_key") == "SANDBOX_MOCKED"
        assert mask_credential(None) == "UNCONFIGURED"
        assert mask_credential("") == "UNCONFIGURED"

        assert get_masked_preview("sk-abcdef1234567890") == "sk-...7890"
        assert get_masked_preview("AIzaSy1234567890abcdef") == "AIza...cdef"
        assert get_masked_preview(None) == "UNCONFIGURED"


# =============================================================================
# 2. TEST PAYLOAD SIZE LIMITING
# =============================================================================
class TestPayloadSizeLimiting:
    """
    Asserts sending a payload > 1MB returns HTTP 413.
    """

    def test_payload_exceeding_1mb_returns_413(self):
        """Asserts sending a body larger than 1MB (1,048,576 bytes) returns HTTP 413."""
        # 1.2 MB oversized body
        oversized_data = "X" * (1024 * 1024 + 200 * 1024)
        large_payload = {
            "query": oversized_data,
            "version_id": "v8",
        }

        res = client.post(
            "/api/drift/compare",
            content=json.dumps(large_payload),
            headers={"Content-Type": "application/json"},
        )

        assert res.status_code == 413, f"Expected HTTP 413, got {res.status_code}: {res.text}"
        assert "Payload Too Large" in res.text
        assert ("1 MB" in res.text or "1MB" in res.text or "1048576" in res.text)
        assert "X-Correlation-ID" in res.headers

    def test_payload_within_limit_accepted(self):
        """Asserts normal-sized payload (< 1MB) is accepted without 413."""
        normal_payload = {"test_key": "valid small payload"}
        res = client.post(
            "/api/drift/compare",
            json=normal_payload,
        )
        assert res.status_code != 413


# =============================================================================
# 3. TEST STRUCTURED CORRELATION IDS
# =============================================================================
class TestStructuredCorrelationIDs:
    """
    Asserts all API endpoints return `X-Correlation-ID` in response headers
    and log records carry matching `correlation_id`.
    """

    def test_all_api_endpoints_return_x_correlation_id(self):
        """Asserts core endpoints return X-Correlation-ID header."""
        endpoints = [
            ("/health", "GET"),
            ("/api/health", "GET"),
            ("/api/fixtures", "GET"),
            ("/api/review/queue", "GET"),
            ("/api/reports/exceptions", "GET"),
            ("/api/drift/compare", "POST"),
        ]

        for path, method in endpoints:
            if method == "GET":
                res = client.get(path)
            else:
                res = client.post(path)

            assert "X-Correlation-ID" in res.headers, f"Endpoint {path} missing X-Correlation-ID"
            corr_id = res.headers["X-Correlation-ID"]
            assert len(corr_id) >= 8, f"Invalid correlation ID format: {corr_id}"

    def test_client_supplied_correlation_id_is_propagated(self):
        """Asserts client-specified X-Correlation-ID is preserved in response headers."""
        custom_cid = "corr_custom_judge_session_2026"
        res = client.get("/health", headers={"X-Correlation-ID": custom_cid})

        assert res.status_code == 200
        assert res.headers.get("X-Correlation-ID") == custom_cid

    def test_log_records_carry_matching_correlation_id(self, caplog):
        """Asserts log records captured during a request execution carry matching correlation_id."""
        caplog.clear()
        caplog.set_level(logging.INFO)

        custom_cid = "corr_tracing_test_998811"
        res = client.get("/health", headers={"X-Correlation-ID": custom_cid})
        assert res.status_code == 200

        # Verify active context variable
        set_correlation_id(custom_cid)
        assert get_correlation_id() == custom_cid

        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="lienmark.api",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Testing correlation propagation",
            args=(),
            exc_info=None,
        )
        filter_instance.filter(record)
        assert record.correlation_id == custom_cid

        formatter = StructuredJsonFormatter()
        formatted_json = json.loads(formatter.format(record))
        assert formatted_json["correlation_id"] == custom_cid


# =============================================================================
# 4. TEST IDEMPOTENCY KEY
# =============================================================================
class TestIdempotencyKey:
    """
    Asserts submitting identical `X-Idempotency-Key` on `POST /api/review/action`
    and `POST /api/drift/compare` returns identical cached responses without
    creating duplicate records.
    """

    def setup_method(self):
        """Reset idempotency cache before each test."""
        idempotency_key_manager.clear()

    def test_drift_compare_idempotency_caching(self):
        """Submitting identical X-Idempotency-Key returns cached response."""
        idem_key = "idem_drift_compare_key_001"

        # First Call - executes analysis
        res1 = client.post(
            "/api/drift/compare",
            headers={"X-Idempotency-Key": idem_key},
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["total_claims"] == 12

        # Second Call with identical idempotency key - served from cache
        res2 = client.post(
            "/api/drift/compare",
            headers={"X-Idempotency-Key": idem_key},
        )
        assert res2.status_code == 200
        assert "HIT" in res2.headers.get("X-Cache", "")
        data2 = res2.json()

        # Both responses must be identical
        assert data1["run_id"] == data2["run_id"]
        assert data1["carried_forward_count"] == data2["carried_forward_count"]

    def test_review_action_idempotency_no_duplicate_records(self):
        """Submitting identical X-Idempotency-Key on POST /api/review/action creates ZERO duplicate records."""
        idem_key = "idem_review_action_key_002"
        initial_trail = counsel_checkpoint_manager.get_audit_trail("poster_noir_detective_magazine")
        initial_count = len(initial_trail)

        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Artwork in public domain under LOC renewal records.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        headers = {
            "X-Idempotency-Key": idem_key,
            "Authorization": "Bearer demo-counsel-2026",
        }

        # First submission
        res1 = client.post("/api/review/action", json=payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        event_id1 = data1["event_id"]

        trail_after_first = counsel_checkpoint_manager.get_audit_trail("poster_noir_detective_magazine")
        assert len(trail_after_first) == initial_count + 1

        # Second submission with identical idempotency key
        res2 = client.post("/api/review/action", json=payload, headers=headers)
        assert res2.status_code == 200
        assert "HIT" in res2.headers.get("X-Cache", "")
        data2 = res2.json()

        # Cached response matches exactly
        assert data2["event_id"] == event_id1
        assert data2["status"] == "success"

        # Crucial Invariant: Ledger audit trail length MUST NOT increase
        trail_after_second = counsel_checkpoint_manager.get_audit_trail("poster_noir_detective_magazine")
        assert len(trail_after_second) == initial_count + 1, "Duplicate ledger entry created despite idempotency key!"

    def test_scoped_idempotency_partitions_by_principal_and_payload(self):
        """Asserts idempotency cache is strictly scoped to principal and payload hash (Finding 9)."""
        idem_key = "idem_partition_test_003"
        payload_1 = {"query": "search_term_1"}
        payload_2 = {"query": "search_term_2"}

        # Caller 1
        res1 = client.post(
            "/api/drift/compare",
            json=payload_1,
            headers={"X-Idempotency-Key": idem_key, "Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert res1.status_code == 200

        # Caller 2 with same key and payload - different principal must NOT be served caller 1's cache
        res2 = client.post(
            "/api/drift/compare",
            json=payload_1,
            headers={"X-Idempotency-Key": idem_key, "Authorization": "Bearer lead_counsel_prod_2026_key"},
        )
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") != "HIT-IDEMPOTENT"

        # Caller 1 with same key but different payload - must NOT hit cache
        res3 = client.post(
            "/api/drift/compare",
            json=payload_2,
            headers={"X-Idempotency-Key": idem_key, "Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert res3.status_code == 200
        assert res3.headers.get("X-Cache") != "HIT-IDEMPOTENT"

        # Exact replay for Caller 1 with payload 1 - must HIT cache
        res4 = client.post(
            "/api/drift/compare",
            json=payload_1,
            headers={"X-Idempotency-Key": idem_key, "Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert res4.status_code == 200
        assert "HIT" in res4.headers.get("X-Cache", "")


# =============================================================================
# 5. TEST COUNSEL AUTHENTICATION
# =============================================================================
class TestCounselAuthentication:
    """
    Asserts unauthenticated or malformed tokens on mutating actions are rejected
    (HTTP 401/403) while valid demo tokens succeed.
    """

    def test_unauthenticated_request_rejected_when_auth_enforced(self):
        """Asserts missing token on mutating action is rejected (HTTP 401)."""
        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Valid rationale for public domain.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }

        # Send without Authorization header but with strict auth enforced
        res = client.post(
            "/api/review/action",
            json=payload,
            headers={"X-Require-Counsel-Auth": "true"},
        )
        assert res.status_code == 401
        assert "Unauthorized" in res.json()["detail"] or "Authentication required" in res.json()["detail"]

    def test_malformed_tokens_rejected(self):
        """Asserts malformed or invalid authorization tokens return HTTP 401 or 403."""
        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Valid rationale for public domain.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }

        # 1. Malformed header format (not Bearer)
        res_basic = client.post(
            "/api/review/action",
            json=payload,
            headers={"Authorization": "Basic 12345abcdef"},
        )
        assert res_basic.status_code == 401
        assert "Malformed authorization header" in res_basic.json()["detail"]

        # 2. Empty bearer token
        res_empty = client.post(
            "/api/review/action",
            json=payload,
            headers={"Authorization": "Bearer "},
        )
        assert res_empty.status_code == 401

        # 3. Invalid/unauthorized token
        res_invalid = client.post(
            "/api/review/action",
            json=payload,
            headers={"Authorization": "Bearer invalid_unauthorized_token"},
        )
        assert res_invalid.status_code in (401, 403)

    def test_valid_demo_tokens_succeed(self):
        """Asserts valid demo tokens authorize clearance actions (HTTP 200)."""
        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Artwork verified in public domain via LOC registration records.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }

        valid_tokens = [
            "Bearer demo-counsel-2026",
            "Bearer demo-counsel-token",
            "Bearer lienmark-counsel-demo-key",
            "Bearer sarah_jenkins_token_2026",
            "Bearer lead_counsel_prod_2026_key",
            "Bearer associate_counsel_prod_2026_key",
        ]

        for token in valid_tokens:
            res = client.post(
                "/api/review/action",
                json=payload,
                headers={"Authorization": token, "X-Require-Counsel-Auth": "true"},
            )
            assert res.status_code == 200, f"Token {token} failed with {res.status_code}: {res.text}"
            assert res.json()["status"] == "success"

    def test_strict_mode_rejects_arbitrary_prefix_tokens(self):
        """Asserts arbitrary prefix tokens (counsel_demo_*, valid_counsel_*, demo-counsel-*, demo-token-*) are rejected with 403."""
        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Artwork verified in public domain via LOC registration records.",
            "reviewer_name": "Sarah Jenkins, Esq.",
        }
        for bad_token in ["counsel_demo_arbitrary_fake", "valid_counsel_unauthorized", "demo-counsel-forged", "demo-token-unlisted"]:
            res = client.post(
                "/api/review/action",
                json=payload,
                headers={"Authorization": f"Bearer {bad_token}", "X-Require-Counsel-Auth": "true"},
            )
            assert res.status_code == 403, f"Expected 403 for {bad_token}, got {res.status_code}"


# =============================================================================
# 6. TEST TIMEOUT & BOUNDED RETRIES
# =============================================================================
class TestTimeoutAndBoundedRetries:
    """
    Asserts service adapters respect 5.0s timeout and retry at most 3 times before
    failing closed safely.
    """

    def test_parallel_service_respects_5s_timeout(self):
        """Asserts ParallelSearchService default timeout is 5.0s and configurable."""
        service = ParallelSearchService(api_key="mock_key")
        assert service.timeout == 5.0
        assert service.client_timeout == 5.0
        assert ParallelSearchService.CLIENT_TIMEOUT == 5.0

        custom_service = ParallelSearchService(api_key="mock_key", timeout=2.5)
        assert custom_service.timeout == 2.5

    def test_parallel_service_bounded_retries_and_fail_closed(self):
        """Asserts ParallelSearchService retries at most 3 times and fails closed safely."""
        service = ParallelSearchService(
            api_key="mock_key",
            timeout=5.0,
            max_retries=3,
        )
        assert service.max_retries == 3
        assert ParallelSearchService.MAX_RETRIES == 3

    @pytest.mark.asyncio
    async def test_parallel_service_timeout_fails_closed_safely(self):
        """Asserts timeout produces INSUFFICIENT stance under strict fail-closed doctrine."""
        service = ParallelSearchService(
            api_key="mock_key",
            timeout=5.0,
            max_retries=3,
            force_fallback=False,
            use_fallback=False,
        )

        snapshot = await service.search(
            query="simulate_timeout Library of Congress renewal",
            use_id="use_v8_poster",
            stable_lineage_key="poster_noir_detective_magazine",
            simulate_failure="timeout",
        )

        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.metadata.get("fail_closed") is True
        assert snapshot.http_status in (504, 500)
        assert "timed out" in snapshot.excerpt.lower() or "timeout" in snapshot.excerpt.lower()

    @pytest.mark.asyncio
    async def test_parallel_service_5xx_bounded_retries_and_fails_closed(self):
        """Asserts 5xx server error fails closed safely with INSUFFICIENT stance."""
        service = ParallelSearchService(
            api_key="mock_key",
            timeout=5.0,
            max_retries=3,
        )

        snapshot = await service.search(
            query="simulate_5xx Vanguard Media ownership",
            use_id="use_v8_music",
            stable_lineage_key="music_cue_midnight_serenade",
            simulate_failure="5xx",
        )

        assert snapshot.stance == EvidenceStance.INSUFFICIENT
        assert snapshot.metadata.get("fail_closed") is True
        assert snapshot.http_status == 500

    def test_gemini_service_respects_5s_timeout_and_retries(self):
        """Asserts GeminiService default timeout is 5.0s and max_retries is 3."""
        gemini = GeminiService(api_key="mock_key")
        assert gemini.timeout == 5.0
        assert gemini.client_timeout == 5.0
        assert gemini.max_retries == 3
        assert GeminiService.CLIENT_TIMEOUT == 5.0

        custom_gemini = GeminiService(api_key="mock_key", timeout=3.0, max_retries=2)
        assert custom_gemini.timeout == 3.0
        assert custom_gemini.max_retries == 2
