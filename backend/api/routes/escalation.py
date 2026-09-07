"""
escalation.py

REST API Endpoints for Autonomous Dispute & SLA Escalation Daemon.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.escalation import DisputeEscalationService
from backend.storage.repository import InMemoryTenantRepository, TenantRepository

logger = logging.getLogger("lienmark.api.routes.escalation")

escalation_router = APIRouter(prefix="/api/v1/escalation", tags=["escalation"])


def _extract_verified_tenant_id(tenant_ctx: TenantContext) -> str:
    """Extracts verified tenant identity, strictly rejecting unauthenticated callers."""
    if getattr(tenant_ctx, "auth_method", None) in ("anonymous", "default", "demo_default"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Fail-closed: Anonymous and unauthenticated access prohibited on escalation endpoints.",
        )
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant credentials in request.",
        )
    return str(tenant_id)


def _get_escalation_service(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DisputeEscalationService:
    """Factory returning DisputeEscalationService scoped to authenticated tenant repository."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    repo = getattr(request.app.state, "tenant_repository", None)
    if repo is None or getattr(repo, "organization_id", None) != tenant_id:
        repo = InMemoryTenantRepository(organization_id=tenant_id)
    ledger = getattr(request.app.state, "cryptographic_ledger", None)
    return DisputeEscalationService(repository=repo, ledger=ledger)


@escalation_router.post(
    "/sweep",
    summary="Trigger Autonomous SLA Escalation Sweep",
)
async def trigger_escalation_sweep(
    production_id: str = Query(..., description="Target production identifier"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    service: DisputeEscalationService = Depends(_get_escalation_service),
) -> Dict[str, Any]:
    """Evaluates unreviewed claims against 72h SLA and auto-escalates breaches."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    return service.sweep_escalations(production_id=production_id, tenant_id=tenant_id)


@escalation_router.get(
    "/status",
    summary="Get SLA Compliance & Escalation Status",
)
async def get_escalation_status(
    production_id: str = Query(..., description="Target production identifier"),
    service: DisputeEscalationService = Depends(_get_escalation_service),
) -> Dict[str, Any]:
    """Returns SLA compliance rates, 48h warning counts, and 72h breach metrics."""
    return service.get_escalation_status(production_id=production_id)
