"""
evidence.py

REST API Endpoints for Evidence Explorer search, detail, and side-by-side comparison.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.routes.evidence_schemas import (
    EvidenceCompareResponse,
    EvidenceDetailResponse,
    EvidenceSearchResponse,
)
from backend.core.rbac import LienmarkRole
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.evidence_search import EvidenceSearchService
from backend.storage.repository import InMemoryTenantRepository, TenantRepository

logger = logging.getLogger("lienmark.api.routes.evidence")

evidence_router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


def _extract_verified_tenant_id(tenant_ctx: TenantContext) -> str:
    """Extracts verified tenant identity, strictly rejecting unauthenticated callers."""
    if getattr(tenant_ctx, "auth_method", None) in ("anonymous", "default", "demo_default"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Fail-closed: Anonymous and unauthenticated access prohibited on evidence endpoints.",
        )
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant credentials in request.",
        )
    return str(tenant_id)


def _get_evidence_service(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> EvidenceSearchService:
    """Factory returning EvidenceSearchService scoped to the authenticated tenant repository."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    repo = getattr(request.app.state, "tenant_repository", None)
    if repo is None or getattr(repo, "organization_id", None) != tenant_id:
        repo = InMemoryTenantRepository(organization_id=tenant_id)
    return EvidenceSearchService(repository=repo)


@evidence_router.get(
    "/search",
    response_model=EvidenceSearchResponse,
    summary="Multi-Facet Evidence Search",
)
async def search_evidence(
    q: Optional[str] = Query(None, description="Free-text search query across snippets and titles"),
    production_id: Optional[str] = Query(None, description="Filter by production scope"),
    domain: Optional[str] = Query(None, description="Filter by source domain"),
    tier: Optional[str] = Query(None, description="Filter by confidence tier"),
    category: Optional[str] = Query(None, description="Filter by asset category"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    service: EvidenceSearchService = Depends(_get_evidence_service),
) -> EvidenceSearchResponse:
    """Executes multi-facet filtered search across public snapshots and private contracts."""
    return service.search_evidence(
        q=q,
        production_id=production_id,
        domain=domain,
        tier=tier,
        category=category,
        source_type=source_type,
        page=page,
        page_size=page_size,
    )


@evidence_router.get(
    "/compare",
    response_model=EvidenceCompareResponse,
    summary="Side-by-Side Public vs Private Evidence Comparison",
)
async def compare_evidence(
    claim_id: str = Query(..., description="Claim identifier to reconcile"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    service: EvidenceSearchService = Depends(_get_evidence_service),
) -> EvidenceCompareResponse:
    """Compares public search findings against private executed contracts for a claim."""
    roles = LienmarkRole.coerce_set(tenant_ctx.roles)
    res = service.compare_evidence_for_claim(claim_id=claim_id, caller_roles=roles)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_id}' not found in active tenant scope.",
        )
    return res


@evidence_router.get(
    "/{evidence_id}",
    response_model=EvidenceDetailResponse,
    summary="Get Single Evidence Record Detail",
)
async def get_evidence_detail(
    evidence_id: str,
    service: EvidenceSearchService = Depends(_get_evidence_service),
) -> EvidenceDetailResponse:
    """Retrieves detailed evidence payload with raw headers and cryptographic verification."""
    detail = service.get_evidence_detail(evidence_id=evidence_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence record '{evidence_id}' not found.",
        )
    return detail
