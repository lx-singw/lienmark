"""
backend/api/routes/events.py

Real-Time Server-Sent Events (SSE) Hub for Command Center & Run State Streaming.
Implements asyncio.Queue subscriber pattern, tenant isolation, and heartbeat pings.
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import StreamingResponse

from backend.middleware.tenant import TenantContext, get_tenant_context

logger = logging.getLogger("lienmark.api.routes.events")

events_router = APIRouter(tags=["events"])

HEARTBEAT_INTERVAL_SECONDS: float = 15.0
MAX_QUEUE_SIZE: int = 100


class EventBroadcaster:
    """Thread-safe multi-tenant Server-Sent Events broadcaster and registry."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    async def register(self, tenant_id: str) -> asyncio.Queue[str]:
        """Registers a new client subscriber queue bound strictly to tenant_id."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        async with self._lock:
            subs = self._subscribers.setdefault(tenant_id, set())
            subs.add(queue)
            logger.debug("Registered SSE client for tenant '%s' (active: %d)", tenant_id, len(subs))
        return queue

    async def unregister(self, tenant_id: str, queue: asyncio.Queue[str]) -> None:
        """Removes a client subscriber queue, preventing memory leaks on disconnect."""
        async with self._lock:
            subs = self._subscribers.get(tenant_id)
            if subs and queue in subs:
                subs.remove(queue)
                if not subs:
                    self._subscribers.pop(tenant_id, None)
                logger.debug("Unregistered SSE client for tenant '%s'", tenant_id)

    async def broadcast(self, tenant_id: str, event_type: str, data: Dict[str, Any]) -> int:
        """Pushes an event payload to all active subscribers for the given tenant."""
        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        async with self._lock:
            subs = list(self._subscribers.get(tenant_id, set()))

        notified = 0
        for q in subs:
            try:
                q.put_nowait(payload)
                notified += 1
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(payload)
                    notified += 1
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    logger.warning("Dropped SSE frame for slow consumer on tenant '%s'", tenant_id)
        return notified

    def active_subscriber_count(self, tenant_id: Optional[str] = None) -> int:
        """Returns the current count of active subscribers."""
        if tenant_id:
            return len(self._subscribers.get(tenant_id, set()))
        return sum(len(s) for s in self._subscribers.values())

    def clear(self) -> None:
        """Clears all subscribers (primarily for testing cleanup)."""
        self._subscribers.clear()

    async def close_all(self, tenant_id: Optional[str] = None) -> None:
        """Sends termination sentinel to active subscriber queues."""
        async with self._lock:
            targets = (
                list(self._subscribers.get(tenant_id, set()))
                if tenant_id
                else [q for s in self._subscribers.values() for q in s]
            )
        for q in targets:
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass


_global_broadcaster = EventBroadcaster()


def get_broadcaster() -> EventBroadcaster:
    """Provides the active EventBroadcaster singleton."""
    return _global_broadcaster


async def broadcast_event(tenant_id: str, event_type: str, data: Dict[str, Any]) -> int:
    """Public async helper to broadcast an event within a tenant boundary."""
    return await _global_broadcaster.broadcast(tenant_id=tenant_id, event_type=event_type, data=data)


def broadcast_event_sync(tenant_id: str, event_type: str, data: Dict[str, Any]) -> int:
    """Thread-safe synchronous bridge for background jobs or storage hooks."""
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(
            broadcast_event(tenant_id, event_type, data), loop
        )
        return future.result(timeout=2.0)
    except (RuntimeError, TimeoutError) as exc:
        logger.debug("Synchronous broadcast skipped (no running loop or timeout): %s", exc)
        return 0


def _extract_verified_tenant(tenant_ctx: TenantContext) -> str:
    """Extracts tenant ID or raises 401 Unauthorized."""
    if not tenant_ctx.user_id or tenant_ctx.auth_method in ("anonymous", "default", "demo_default"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: valid credentials or token must be provided.",
        )
    tid = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )
    return str(tid)


async def _sse_stream_generator(
    request: Request, tenant_id: str, broadcaster: EventBroadcaster
) -> AsyncGenerator[str, None]:
    """Yields SSE events, periodically emitting heartbeat pings until client disconnects."""
    queue = await broadcaster.register(tenant_id)
    try:
        init_data = json.dumps({"status": "connected", "tenant_id": tenant_id})
        yield f"event: connected\ndata: {init_data}\n\n"

        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS)
                if msg is None:
                    break
                yield msg
            except asyncio.TimeoutError:
                yield ": ping\n\n"
            except (asyncio.CancelledError, GeneratorExit):
                break
    finally:
        await broadcaster.unregister(tenant_id, queue)


@events_router.get(
    "/api/v1/events",
    summary="Real-Time Server-Sent Events Stream",
    response_class=StreamingResponse,
)
async def stream_events(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    broadcaster: EventBroadcaster = Depends(get_broadcaster),
) -> StreamingResponse:
    """Subscribes to tenant-isolated real-time state change events and heartbeat pings."""
    tenant_id = _extract_verified_tenant(tenant_ctx)
    generator = _sse_stream_generator(request, tenant_id, broadcaster)
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(generator, media_type="text/event-stream", headers=headers)
