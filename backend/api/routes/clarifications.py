"""
backend/api/routes/clarifications.py

REST API endpoints for querying and responding to clearance ClarificationRequests.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.routes.clarification_schemas import (
    ClarificationRespondRequest,
    ClarificationRespondResponse,
    ClarificationStatusFilter,
)
from backend.core.rbac import LienmarkRole
from backend.domain.models import ClarificationRequest
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.storage.clarification_store import (
    ClarificationStore,
    get_clarification_store,
)

logger = logging.getLogger("lienmark.api.routes.clarifications")

clarification_router = APIRouter(tags=["clarifications"])

AUTHORIZED_RESPONDER_ROLES = frozenset({
    LienmarkRole.PRODUCER,
    LienmarkRole.REVIEWER,
    LienmarkRole.ADMIN,
})


def _validate_responder_authorization(
    tenant_ctx: TenantContext,
    declared_role_str: str,
) -> LienmarkRole:
    """Validates that declared role and authenticated principal hold authorized clearance roles."""
    norm_declared = LienmarkRole.normalize(declared_role_str)
    if norm_declared is None or norm_declared not in AUTHORIZED_RESPONDER_ROLES:
        req_roles = [r.value for r in sorted(AUTHORIZED_RESPONDER_ROLES, key=lambda r: r.value)]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{declared_role_str}' is not authorized to resolve clarifications. Required: {req_roles}.",
        )

    user_roles = LienmarkRole.coerce_set(tenant_ctx.roles)
    if tenant_ctx.production_roles:
        user_roles.update(LienmarkRole.coerce_set(tenant_ctx.production_roles.values()))

    has_auth = bool(user_roles.intersection(AUTHORIZED_RESPONDER_ROLES))
    if not has_auth and not tenant_ctx.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authenticated principal lacks authorized role to respond as '{norm_declared.value}'.",
        )

    return norm_declared


@clarification_router.get(
    "/api/v1/runs/{run_id}/clarifications",
    response_model=List[ClarificationRequest],
    summary="List Clarification Requests for Run",
)
async def list_run_clarifications(
    run_id: str,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status ('pending', 'resolved', 'cancelled')",
    ),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    store: ClarificationStore = Depends(get_clarification_store),
) -> List[ClarificationRequest]:
    """Retrieves all clarification requests for a run, strictly scoped by tenant_id."""
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )

    return store.list_clarifications_for_run(
        run_id=run_id,
        tenant_id=tenant_id,
        status_filter=status_filter,
    )


def _execute_store_resolution(
    store: ClarificationStore,
    request_id: str,
    tenant_id: str,
    actor_id: str,
    role_str: str,
    payload: ClarificationRespondRequest,
):
    """Invokes clarification store resolution with HTTP-mapped error handling."""
    try:
        return store.resolve_clarification(
            request_id=request_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            responder_role=role_str,
            response_text=payload.response_text,
            attached_document_id=payload.attached_document_id,
            selected_option=payload.selected_option,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@clarification_router.post(
    "/api/v1/clarifications/{request_id}/respond",
    response_model=ClarificationRespondResponse,
    summary="Respond to and Resolve Clarification Request",
)
async def respond_to_clarification(
    request_id: str,
    payload: ClarificationRespondRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    store: ClarificationStore = Depends(get_clarification_store),
) -> ClarificationRespondResponse:
    """Validates responder role, updates clarification status, and records cryptographic audit event."""
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )

    norm_role = _validate_responder_authorization(tenant_ctx, payload.responder_role)
    actor_id = tenant_ctx.user_id or "usr_anonymous"

    updated_clrf, audit_event = _execute_store_resolution(
        store, request_id, tenant_id, actor_id, norm_role.value, payload
    )

    return ClarificationRespondResponse(
        success=True,
        request_id=updated_clrf.request_id,
        status=updated_clrf.status,
        resolved_at=updated_clrf.resolved_at or "",
        resolved_by=updated_clrf.resolved_by or actor_id,
        responder_role=norm_role.value,
        event_id=audit_event.event_id if audit_event else None,
        clarification=updated_clrf,
    )
