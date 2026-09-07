"""
tests/test_events_sse.py

Exhaustive integration test suite for Server-Sent Events (SSE) Real-Time Hub:
1. Connection and handshake header validation (text/event-stream)
2. Initial handshake event reception (event: connected)
3. Real-time broadcast delivery to subscribers
4. Disconnect cleanup and queue deregistration (zero memory leaks)
5. Cross-tenant isolation
6. Heartbeat ping verification
7. Unauthenticated fail-closed
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import asyncio
import json
import pytest
import httpx

from backend.api.routes.events import (
    broadcast_event,
    get_broadcaster,
)
from backend.main import app
from tests.test_tenant_middleware import create_test_jwt


@pytest.fixture(autouse=True)
def clean_broadcaster():
    """Clears all active SSE subscribers before and after each test."""
    broadcaster = get_broadcaster()
    broadcaster.clear()
    yield
    broadcaster.clear()


@pytest.mark.asyncio
async def test_sse_unauthenticated_fail_closed():
    """Fail-closed invariant: Missing credentials returns 401 Unauthorized."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/events")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_sse_handshake_and_connected_event():
    """Verifies text/event-stream headers and initial 'event: connected' payload."""
    tid = "org_paramount_sse"
    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    broadcaster = get_broadcaster()

    async def closer():
        while broadcaster.active_subscriber_count(tid) == 0:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.02)
        await broadcaster.close_all(tid)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        task = asyncio.create_task(closer())
        res = await ac.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})
        await task

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert res.headers.get("cache-control") == "no-cache"
        assert "event: connected" in res.text
        assert f'"tenant_id": "{tid}"' in res.text


@pytest.mark.asyncio
async def test_sse_broadcast_reception():
    """Verifies that broadcast_event delivers real-time payload to active subscriber."""
    tid = "org_warner_sse"
    token = create_test_jwt(tenant_id=tid, roles=["producer"])
    broadcaster = get_broadcaster()

    async def broadcaster_worker():
        while broadcaster.active_subscriber_count(tid) == 0:
            await asyncio.sleep(0.01)
        delivered = await broadcast_event(
            tenant_id=tid,
            event_type="claim_updated",
            data={"claim_id": "clm_hero_cue", "status": "approved"},
        )
        assert delivered == 1
        await asyncio.sleep(0.02)
        await broadcaster.close_all(tid)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        task = asyncio.create_task(broadcaster_worker())
        res = await ac.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})
        await task

        assert res.status_code == 200
        assert "event: connected" in res.text
        assert "event: claim_updated" in res.text
        assert "clm_hero_cue" in res.text
        assert "approved" in res.text


@pytest.mark.asyncio
async def test_sse_disconnect_cleanup_no_leaks():
    """Resource invariant: Exiting stream unregisters queue from memory (zero leak)."""
    tid = "org_cleanup_sse"
    broadcaster = get_broadcaster()
    assert broadcaster.active_subscriber_count(tid) == 0

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])

    async def closer():
        while broadcaster.active_subscriber_count(tid) == 0:
            await asyncio.sleep(0.01)
        assert broadcaster.active_subscriber_count(tid) == 1
        await asyncio.sleep(0.02)
        await broadcaster.close_all(tid)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        task = asyncio.create_task(closer())
        res = await ac.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})
        await task
        assert res.status_code == 200

    # After stream completion, subscriber count must return strictly to 0
    assert broadcaster.active_subscriber_count(tid) == 0


async def _run_tenant_isolated_broadcast(broadcaster, tid_a: str, tid_b: str):
    """Helper worker to broadcast tenant-specific events and close."""
    while (
        broadcaster.active_subscriber_count(tid_a) == 0
        or broadcaster.active_subscriber_count(tid_b) == 0
    ):
        await asyncio.sleep(0.01)

    d_a = await broadcast_event(tid_a, "alpha_alert", {"secret": "alpha_classified"})
    assert d_a == 1
    d_b = await broadcast_event(tid_b, "beta_alert", {"secret": "beta_classified"})
    assert d_b == 1
    await asyncio.sleep(0.02)
    await broadcaster.close_all()


@pytest.mark.asyncio
async def test_sse_cross_tenant_isolation():
    """Security invariant: Tenant A's broadcast never leaks to Tenant B's stream."""
    tid_a, tid_b = "org_tenant_alpha", "org_tenant_beta"
    token_a = create_test_jwt(tenant_id=tid_a, roles=["reviewer"])
    token_b = create_test_jwt(tenant_id=tid_b, roles=["reviewer"])
    broadcaster = get_broadcaster()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        b_task = asyncio.create_task(_run_tenant_isolated_broadcast(broadcaster, tid_a, tid_b))
        req_a = ac.get("/api/v1/events", headers={"Authorization": f"Bearer {token_a}"})
        req_b = ac.get("/api/v1/events", headers={"Authorization": f"Bearer {token_b}"})
        res_a, res_b = await asyncio.gather(req_a, req_b)
        await b_task

        assert "event: alpha_alert" in res_a.text
        assert "alpha_classified" in res_a.text
        assert "beta_classified" not in res_a.text

        assert "event: beta_alert" in res_b.text
        assert "beta_classified" in res_b.text
        assert "alpha_classified" not in res_b.text


@pytest.mark.asyncio
async def test_sse_heartbeat_ping(monkeypatch):
    """Verifies periodic keep-alive ping emitted when queue is idle."""
    import backend.api.routes.events as events_module
    # Set ping interval to 30ms for swift verification
    monkeypatch.setattr(events_module, "HEARTBEAT_INTERVAL_SECONDS", 0.03)

    tid = "org_heartbeat_sse"
    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    broadcaster = get_broadcaster()

    async def closer():
        while broadcaster.active_subscriber_count(tid) == 0:
            await asyncio.sleep(0.01)
        # Sleep long enough for 2-3 pings to be emitted
        await asyncio.sleep(0.1)
        await broadcaster.close_all(tid)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        task = asyncio.create_task(closer())
        res = await ac.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})
        await task

        assert res.status_code == 200
        assert ": ping" in res.text
