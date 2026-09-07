"""
ledger.py

REST API Endpoints for Decision History, Timeline & Cryptographic Ledger Verification.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.routes.ledger_schemas import (
    DecisionChainResponse,
    LedgerVerificationResponse,
    SupersessionRecord,
)
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.ledger_service import LedgerService
from backend.storage.repository import InMemoryTenantRepository, TenantRepository

logger = logging.getLogger("lienmark.api.routes.ledger")

ledger_router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])


def _extract_verified_tenant_id(tenant_ctx: TenantContext) -> str:
    """Extracts verified tenant identity, strictly rejecting unauthenticated callers."""
    if getattr(tenant_ctx, "auth_method", None) in ("anonymous", "default", "demo_default"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Fail-closed: Anonymous and unauthenticated access prohibited on ledger endpoints.",
        )
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant credentials in request.",
        )
    return str(tenant_id)


def _get_ledger_service(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> LedgerService:
    """Factory returning LedgerService scoped to the authenticated tenant repository."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    repo = getattr(request.app.state, "tenant_repository", None)
    if repo is None or getattr(repo, "organization_id", None) != tenant_id:
        repo = InMemoryTenantRepository(organization_id=tenant_id)
    ledger = getattr(request.app.state, "cryptographic_ledger", None)
    return LedgerService(repository=repo, ledger=ledger)


@ledger_router.get(
    "/decisions",
    response_model=DecisionChainResponse,
    summary="Get Chronological Decision Chain",
)
async def get_decisions(
    production_id: str = Query(..., description="Target production identifier"),
    claim_id: Optional[str] = Query(None, description="Optional claim filter"),
    service: LedgerService = Depends(_get_ledger_service),
) -> DecisionChainResponse:
    """Returns chronological decision history for production or claim with chain validity."""
    return service.get_decision_chain(production_id=production_id, claim_id=claim_id)


@ledger_router.get(
    "/verify/{event_id}",
    response_model=LedgerVerificationResponse,
    summary="Verify Ledger Block Cryptographic Proof",
)
async def verify_event(
    event_id: str,
    production_id: str = Query(..., description="Target production identifier"),
    service: LedgerService = Depends(_get_ledger_service),
) -> LedgerVerificationResponse:
    """Authoritative server-side verification of SHA-256 block hash, digest, and parent link."""
    res = service.verify_event(production_id=production_id, event_id=event_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ledger event '{event_id}' not found in production '{production_id}'.",
        )
    return res


@ledger_router.get(
    "/supersessions",
    response_model=List[SupersessionRecord],
    summary="List Decision Supersessions",
)
async def get_supersessions(
    production_id: str = Query(..., description="Target production identifier"),
    service: LedgerService = Depends(_get_ledger_service),
) -> List[SupersessionRecord]:
    """Returns all non-destructive supersession override records for the production."""
    return service.get_supersessions(production_id=production_id)
