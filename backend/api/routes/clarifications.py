"""
backend/api/routes/clarifications.py

REST API endpoints for querying and responding to clearance ClarificationRequests.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.routes.clarification_schemas import (
    ClarificationRespondRequest,
    ClarificationRespondResponse,
)
from backend.core.rbac import LienmarkRole
from backend.domain.models import CensusDisposition, ClarificationRequest
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.resumption_pipeline import (
    ResumptionPipelineService,
    get_resumption_pipeline_service,
)
from backend.storage.clarification_store import (
    ClarificationStore,
    get_clarification_store,
)
from backend.storage.ledger_types import AuditEvent

logger = logging.getLogger("lienmark.api.routes.clarifications")

clarification_router = APIRouter(tags=["clarifications"])

AUTHORIZED_RESPONDER_ROLES: frozenset[LienmarkRole] = frozenset({
    LienmarkRole.PRODUCER,
    LienmarkRole.REVIEWER,
    LienmarkRole.ADMIN,
})


def _extract_tenant_id(tenant_ctx: TenantContext) -> str:
    """Extracts verified tenant identity or raises 401 Unauthorized."""
    tid = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )
    return str(tid)


def _lookup_target_clarification(
    store: ClarificationStore,
    request_id: str,
    tenant_id: str,
) -> ClarificationRequest:
    """Retrieves target clarification and enforces strict tenant boundary checks."""
    clrf = store.get_clarification(request_id=request_id, tenant_id=tenant_id)
    if clrf is not None:
        return clrf

    raw = getattr(store, "_records", {}).get(request_id)
    if raw is not None and getattr(raw, "tenant_id", None) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-tenant access forbidden for request '{request_id}'.",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Clarification request '{request_id}' not found.",
    )


def _validate_scoped_responder_role(
    prod_role_raw: Optional[str],
    declared_role: LienmarkRole,
    target_prod_id: str,
) -> LienmarkRole:
    """Validates responder role scoped to target production; prevents privilege elevation."""
    norm_prod = LienmarkRole.normalize(prod_role_raw) if prod_role_raw else None
    if norm_prod in AUTHORIZED_RESPONDER_ROLES:
        if declared_role != norm_prod:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Principal lacks verified '{declared_role.value}' role on production '{target_prod_id}'.",
            )
        return norm_prod
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Principal lacks authorized role on production '{target_prod_id}' to respond as '{declared_role.value}'.",
    )


def _validate_responder_authorization(
    tenant_ctx: TenantContext,
    declared_role_str: str,
    target_production_id: str,
) -> LienmarkRole:
    """Validates responder holds authorized role scoped strictly to target production."""
    norm_declared = LienmarkRole.normalize(declared_role_str)
    if norm_declared is None or norm_declared not in AUTHORIZED_RESPONDER_ROLES:
        req_roles = [r.value for r in sorted(AUTHORIZED_RESPONDER_ROLES, key=lambda r: r.value)]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{declared_role_str}' is not authorized to resolve clarifications. Required: {req_roles}.",
        )

    if target_production_id in tenant_ctx.production_roles:
        return _validate_scoped_responder_role(
            tenant_ctx.production_roles.get(target_production_id),
            norm_declared,
            target_production_id,
        )

    if tenant_ctx.production_roles and not tenant_ctx.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Authorized roles belong to a different production; cross-production leaking prevented.",
        )

    global_roles = {
        norm for r in tenant_ctx.roles if (norm := LienmarkRole.normalize(r)) is not None
    }
    if norm_declared in global_roles or tenant_ctx.is_demo:
        return norm_declared

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Authenticated principal lacks authorized role to respond as '{norm_declared.value}'.",
    )


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
    tenant_id = _extract_tenant_id(tenant_ctx)
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
) -> Tuple[ClarificationRequest, Optional[AuditEvent]]:
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


def _enforce_non_approved_disposition(clrf: ClarificationRequest) -> None:
    """Ensures clarification resolution never mutates clearance disposition to APPROVED."""
    disp = getattr(clrf, "disposition", None)
    if disp and str(disp).lower().strip() in (CensusDisposition.APPROVED.value, "approved"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Illegal state: clarification resolution cannot set clearance disposition to APPROVED.",
        )


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
    resumption_service: ResumptionPipelineService = Depends(get_resumption_pipeline_service),
) -> ClarificationRespondResponse:
    """Validates responder role, updates clarification status, and records cryptographic audit event."""
    tenant_id = _extract_tenant_id(tenant_ctx)
    clrf = _lookup_target_clarification(store, request_id, tenant_id)
    target_prod_id = clrf.production_id or "prod_default"

    norm_role = _validate_responder_authorization(tenant_ctx, payload.responder_role, target_prod_id)
    actor_id = tenant_ctx.user_id or "usr_anonymous"

    updated_clrf, audit_event = _execute_store_resolution(
        store, request_id, tenant_id, actor_id, norm_role.value, payload
    )
    _enforce_non_approved_disposition(updated_clrf)

    resumption_service.trigger_resumption(
        clarification=updated_clrf,
        tenant_id=tenant_id,
        actor_id=actor_id,
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
