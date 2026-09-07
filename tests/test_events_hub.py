"""
tests/test_events_hub.py

Verification tests for Server-Sent Events (SSE) Hub and EventBroadcaster.
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import asyncio
import json
import pytest

from backend.api.routes.events import EventBroadcaster, broadcast_event


@pytest.fixture
def broadcaster():
    """Provides an isolated EventBroadcaster instance."""
    hub = EventBroadcaster()
    yield hub
    hub.clear()


@pytest.mark.asyncio
async def test_register_and_unregister(broadcaster):
    """Verifies that client queues register and unregister cleanly without leaks."""
    assert broadcaster.active_subscriber_count("org_a") == 0
    q = await broadcaster.register("org_a")
    assert broadcaster.active_subscriber_count("org_a") == 1

    await broadcaster.unregister("org_a", q)
    assert broadcaster.active_subscriber_count("org_a") == 0


@pytest.mark.asyncio
async def test_tenant_isolation_in_broadcast(broadcaster):
    """Strict Multi-Tenant Invariant: Events on Tenant A must not leak to Tenant B."""
    q_a = await broadcaster.register("org_tenant_a")
    q_b = await broadcaster.register("org_tenant_b")

    notified = await broadcaster.broadcast(
        tenant_id="org_tenant_a",
        event_type="inbox_updated",
        data={"item_id": "inb_001", "action": "created"},
    )
    assert notified == 1
    assert not q_a.empty()
    assert q_b.empty()

    msg = await q_a.get()
    assert "event: inbox_updated\n" in msg
    assert '"item_id": "inb_001"' in msg

    await broadcaster.unregister("org_tenant_a", q_a)
    await broadcaster.unregister("org_tenant_b", q_b)


@pytest.mark.asyncio
async def test_bounded_queue_overflow_behavior(broadcaster):
    """Verifies that slow consumers dropping frames do not cause memory deadlock."""
    q = await broadcaster.register("org_slow")
    # Fill queue to max
    for i in range(100):
        await broadcaster.broadcast("org_slow", "ping", {"seq": i})

    # Pushing 101st event should drop oldest frame gracefully
    notified = await broadcaster.broadcast("org_slow", "overflow", {"seq": 101})
    assert notified == 1
    assert q.qsize() == 100

    await broadcaster.unregister("org_slow", q)
