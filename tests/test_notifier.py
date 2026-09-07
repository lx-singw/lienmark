"""
tests/test_notifier.py

Comprehensive test suite for Clarification Notification Dispatcher.
Validates webhook payload digests, HMAC signatures, formatted alerts, and resilient fallback.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from unittest.mock import AsyncMock, patch

from backend.domain.models import ClarificationRequest
from backend.services.notifier import ClarificationNotifier, get_notifier
from backend.services.notifier_types import (
    DeliveryStatus,
    NotificationEventType,
    build_clarification_webhook_payload,
    format_clarification_email_alert,
)
from backend.storage.ledger_types import compute_canonical_digest


@pytest.fixture
def sample_clarification() -> ClarificationRequest:
    return ClarificationRequest(
        request_id="clrf_test_101",
        run_id="run_test_900",
        claim_id="clm_jazz_solo_42",
        revision_id="v8",
        stable_lineage_key="lineage_jazz_cue",
        question_text="Uncredited jazz cue in diner scene. Master recording rights unverified.",
        suggested_options=["Option 1: Work-for-hire", "Option 2: Sync License"],
        required_document_type="Executed Synchronization License",
        assigned_role="Music Supervisor",
        status="pending",
    )


def test_build_webhook_payload_and_canonical_digest(sample_clarification):
    payload = build_clarification_webhook_payload(sample_clarification, "org_warner_001")
    assert payload["event_type"] == NotificationEventType.CLARIFICATION_REQUESTED.value
    assert payload["tenant_id"] == "org_warner_001"
    assert payload["data"]["request_id"] == "clrf_test_101"

    digest = compute_canonical_digest(payload)
    assert len(digest) == 64
    assert digest == compute_canonical_digest(payload)


def test_format_clarification_email_alert(sample_clarification):
    subject, text_body, html_body = format_clarification_email_alert(
        sample_clarification, "org_paramount_003"
    )
    assert "clm_jazz_solo_42" in subject
    assert "Music Supervisor" in subject
    assert "Executed Synchronization License" in text_body
    assert "Option 1: Work-for-hire" in text_body
    assert "<h2>Lienmark E&O Clearance Notice</h2>" in html_body


@pytest.mark.asyncio
async def test_dispatch_clarification_requested_fallback_mode(sample_clarification):
    notifier = ClarificationNotifier(fallback_mode=True)
    notifier.clear_delivery_history()

    res = await notifier.dispatch_clarification_requested(
        clarification=sample_clarification,
        tenant_id="org_sony_004",
        recipient_email="supervisor@sony.local",
    )

    assert res.success is True
    assert res.event_type == NotificationEventType.CLARIFICATION_REQUESTED.value
    assert res.request_id == "clrf_test_101"
    assert len(res.payload_digest) == 64
    assert res.delivery_record.webhook_status == DeliveryStatus.FALLBACK_LOGGED

    history = notifier.get_delivery_history()
    assert len(history) == 1
    assert history[0].request_id == "clrf_test_101"
    assert history[0].email_recipient == "supervisor@sony.local"


@pytest.mark.asyncio
async def test_dispatch_clarification_requested_live_mock_success(sample_clarification):
    notifier = ClarificationNotifier(
        default_webhook_url="https://webhooks.production.local/clearance",
        fallback_mode=False,
    )
    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await notifier.dispatch_clarification_requested(
            clarification=sample_clarification,
            tenant_id="org_universal_005",
        )
        assert res.success is True
        assert res.webhook_delivered is True
        assert mock_post.called
        headers = mock_post.call_args[1]["headers"]
        assert headers["X-Tenant-Id"] == "org_universal_005"
        assert "sha256=" in headers["X-Lienmark-Signature"]


@pytest.mark.asyncio
async def test_dispatch_clarification_network_error_resilience(sample_clarification):
    notifier = ClarificationNotifier(
        default_webhook_url="https://unreachable.endpoint.local/hook",
        fallback_mode=False,
        timeout_seconds=0.5,
    )

    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection timed out")):
        # Must never raise or crash the application
        res = await notifier.dispatch_clarification_requested(
            clarification=sample_clarification,
            tenant_id="org_a24_006",
        )
        assert res.delivery_record.webhook_status == DeliveryStatus.FALLBACK_LOGGED
        assert "Connection timed out" in str(res.delivery_record.error_detail)


def test_notifier_singleton_and_history_clearing():
    notifier = get_notifier()
    notifier.clear_delivery_history()
    assert len(notifier.get_delivery_history()) == 0
