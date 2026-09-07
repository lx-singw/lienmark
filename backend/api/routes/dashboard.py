"""
backend/api/routes/dashboard.py

REST API endpoints for Command Center Dashboard (Inbox and Clearance Velocity).
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.routes.dashboard_schemas import InboxResponse, VelocityResponse
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.dashboard_service import (
    DashboardService,
    DashboardServiceError,
    get_dashboard_service,
)

logger = logging.getLogger("lienmark.api.routes.dashboard")

dashboard_router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _extract_verified_tenant_id(tenant_ctx: TenantContext) -> str:
    """Extracts verified tenant / organization identity or raises 401 Unauthorized."""
    if not tenant_ctx.user_id or tenant_ctx.auth_method in ("anonymous", "default", "demo_default"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: valid credentials or token must be provided.",
        )
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )
    return str(tenant_id)


@dashboard_router.get(
    "/inbox",
    response_model=InboxResponse,
    summary="Get Triage Action Queue & Clearance Blockers",
)
async def get_dashboard_inbox(
    production_id: Optional[str] = Query(None, description="Optional production container ID filter"),
    severity: Optional[str] = Query(None, description="Filter by severity ('P0_CRITICAL', 'P1_HIGH', etc.)"),
    category: Optional[str] = Query(None, description="Filter by category ('reopened_creative_drift', etc.)"),
    limit: int = Query(50, ge=1, le=200, description="Pagination item limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> InboxResponse:
    """Retrieves prioritized clearance action items and blockers strictly scoped by tenant."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    try:
        return service.get_inbox(
            tenant_id=tenant_id,
            production_id=production_id,
            severity=severity,
            category=category,
            limit=limit,
            offset=offset,
        )
    except DashboardServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@dashboard_router.get(
    "/velocity",
    response_model=VelocityResponse,
    summary="Get Clearance Velocity & Risk Regression Stats",
)
async def get_dashboard_velocity(
    production_id: Optional[str] = Query(None, description="Optional production container ID filter"),
    window_days: int = Query(30, ge=1, le=365, description="Historical calculation lookback window in days"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> VelocityResponse:
    """Computes median resolution times, stale aging, and blocker burn rates for the tenant."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    try:
        return service.get_velocity(
            tenant_id=tenant_id,
            production_id=production_id,
            window_days=window_days,
        )
    except DashboardServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
