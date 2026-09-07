"""
backend/api/routes/policy_outbox_routes.py

REST API endpoints for asynchronous Policy Change Dispatch Intents & Outbox Cascade.
Sprint 5.3: Asynchronous Policy Dispatch, Rule Dependencies, and Golden Demo.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.core.policy_outbox import PolicyOutboxDispatcher, get_policy_outbox_dispatcher
from backend.core.policy_outbox_types import DispatchExecutionReport
from backend.core.rbac import LienmarkRole
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.storage.policy_store import PolicyStore, get_policy_store
from backend.storage.policy_store_types import PolicyChangeDispatchIntent

logger = logging.getLogger("lienmark.api.routes.policy_outbox")

outbox_router = APIRouter(prefix="/api/v1/organizations", tags=["policy_outbox"])

ADMIN_ROLES = frozenset({LienmarkRole.ADMIN})


def _verify_admin_access(tenant_ctx: TenantContext, org_id: str) -> None:
    """Ensures authenticated caller holds Admin role within target organization."""
    caller_org = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if caller_org and str(caller_org) != str(org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Principal organization does not match target organization.",
        )
    user_roles = LienmarkRole.coerce_set(tenant_ctx.roles)
    if tenant_ctx.production_roles:
        user_roles.update(LienmarkRole.coerce_set(tenant_ctx.production_roles.values()))
    if not user_roles.intersection(ADMIN_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatch operations require Admin role sign-off.",
        )


def _get_dispatcher() -> PolicyOutboxDispatcher:
    return get_policy_outbox_dispatcher()


def _get_store() -> PolicyStore:
    return get_policy_store()


@outbox_router.post(
    "/{org_id}/policy/dispatch-pending",
    response_model=List[DispatchExecutionReport],
    summary="Process Pending Policy Change Dispatch Intents",
)
async def dispatch_pending_intents(
    org_id: str,
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    dispatcher: PolicyOutboxDispatcher = Depends(_get_dispatcher),
) -> List[DispatchExecutionReport]:
    """Processes all PENDING dispatch intents, cascading rule updates to target claims."""
    _verify_admin_access(tenant_ctx, org_id)
    try:
        reports = dispatcher.process_pending_intents(org_id=org_id)
        logger.info("Processed %d dispatch intents for org %s", len(reports), org_id)
        return reports
    except Exception as exc:
        logger.error("Failed dispatching pending intents for %s: %s", org_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy dispatch failed: {exc}",
        ) from exc


@outbox_router.get(
    "/{org_id}/policy/intents",
    response_model=List[PolicyChangeDispatchIntent],
    summary="List Policy Change Dispatch Intents",
)
async def list_dispatch_intents(
    org_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    policy_store: PolicyStore = Depends(_get_store),
) -> List[PolicyChangeDispatchIntent]:
    """Retrieves chronological policy dispatch intents for an organization."""
    caller_org = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if caller_org and str(caller_org) != str(org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Principal organization does not match target organization.",
        )
    return policy_store.list_dispatch_intents(org_id=org_id, status=status_filter)


@outbox_router.post(
    "/{org_id}/policy/recover-intents",
    response_model=dict,
    summary="Recover Abandoned Dispatch Intents",
)
async def recover_abandoned_intents(
    org_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    dispatcher: PolicyOutboxDispatcher = Depends(_get_dispatcher),
) -> dict:
    """Recovers and resets any interrupted PROCESSING intents back to PENDING."""
    _verify_admin_access(tenant_ctx, org_id)
    recovered_count = dispatcher.recover_abandoned_intents(org_id=org_id)
    return {"org_id": org_id, "recovered_count": recovered_count, "status": "reclaimed"}
