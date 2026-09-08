"""
backend/api/routes/decisions.py

REST API endpoints for counsel clearance decisions, citation suggestions, and attempt lineage.
Sprint 4.3 - Reviewer Rejection & Directed Re-Investigation Loop.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.routes.decision_schemas import (
    AttemptLineageResponse,
    CitationSuggestionResponse,
    CounselDecisionRequest,
    CounselDecisionResponse,
)
from backend.core.rbac import LienmarkRole
from backend.core.reviewer_loop import (
    CounselReviewLoopCoordinator,
    get_reviewer_loop_coordinator,
)
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.citation_templates import (
    CitationSuggestionEngine,
    get_citation_engine,
)

logger = logging.getLogger("lienmark.api.routes.decisions")

decision_router = APIRouter(prefix="/api/v1/claims", tags=["decisions"])

AUTHORIZED_DECISION_ROLES: frozenset[LienmarkRole] = frozenset({
    LienmarkRole.REVIEWER,
    LienmarkRole.ADMIN,
})


def _extract_verified_tenant_id(tenant_ctx: TenantContext) -> str:
    """Extracts verified tenant / organization identity or raises 401 Unauthorized."""
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )
    return str(tenant_id)


def _resolve_target_production_id(
    claim_id: str,
    tenant_ctx: TenantContext,
    coordinator: CounselReviewLoopCoordinator,
    query_prod_id: Optional[str] = None,
) -> str:
    """Resolves target production identifier from coordinator registry, query, context, or fallback."""
    if hasattr(coordinator, "get_claim_production"):
        known = coordinator.get_claim_production(claim_id)
        if known:
            return known
    if query_prod_id:
        return query_prod_id
    if tenant_ctx.current_production_id:
        return tenant_ctx.current_production_id
    return f"prod_{claim_id}"


def _validate_scoped_production_role(
    prod_role_raw: Optional[str],
    target_production_id: str,
) -> LienmarkRole:
    """Validates production-scoped role: Reviewer/Admin allowed, Producer strictly rejected with 403."""
    norm_prod = LienmarkRole.normalize(prod_role_raw) if prod_role_raw else None
    if norm_prod == LienmarkRole.PRODUCER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Principal holds role 'producer' on production '{target_production_id}', which is not authorized to adjudicate claims.",
        )
    if norm_prod in AUTHORIZED_DECISION_ROLES:
        return norm_prod
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: Principal lacks authorized decision role on production '{target_production_id}'.",
    )


def _validate_decision_rbac(
    tenant_ctx: TenantContext,
    request: Request,
    target_production_id: str,
) -> LienmarkRole:
    """Validates user roles scoped strictly to target production; prevents cross-production leaks."""
    if target_production_id in tenant_ctx.production_roles:
        return _validate_scoped_production_role(
            tenant_ctx.production_roles.get(target_production_id),
            target_production_id,
        )

    if tenant_ctx.production_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Authorized roles belong to a different production; cross-production leaking prevented.",
        )

    counsel_auth = getattr(request.state, "counsel_auth", None)
    if counsel_auth and getattr(counsel_auth, "is_authenticated", False):
        return LienmarkRole.REVIEWER

    global_roles = {
        norm for r in tenant_ctx.roles if (norm := LienmarkRole.normalize(r)) is not None
    }
    matching = global_roles.intersection(AUTHORIZED_DECISION_ROLES)
    if matching:
        return next(iter(matching))

    req_names = sorted([r.value for r in AUTHORIZED_DECISION_ROLES])
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: Principal lacks required role(s) to adjudicate claims: {', '.join(req_names)}.",
    )


@decision_router.post(
    "/{claim_id}/decision",
    response_model=CounselDecisionResponse,
    summary="Adjudicate Counsel Clearance Decision",
)
async def submit_counsel_decision(
    claim_id: str,
    payload: CounselDecisionRequest,
    request: Request,
    production_id: Optional[str] = Query(None, description="Optional target production scope"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    coordinator: CounselReviewLoopCoordinator = Depends(get_reviewer_loop_coordinator),
) -> CounselDecisionResponse:
    """Validates target production RBAC (Reviewer/Admin), records decision, and logs cryptographic audit event."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    target_prod_id = _resolve_target_production_id(claim_id, tenant_ctx, coordinator, production_id)
    _validate_decision_rbac(tenant_ctx, request, target_prod_id)

    actor_id = tenant_ctx.user_id or payload.counsel_id
    return coordinator.record_decision(
        tenant_id=tenant_id,
        production_id=target_prod_id,
        claim_id=claim_id,
        actor_id=actor_id,
        request=payload,
    )


@decision_router.get(
    "/{claim_id}/citation-suggestions",
    response_model=CitationSuggestionResponse,
    summary="Get Suggested Legal Citation Templates for Claim",
)
async def get_citation_suggestions(
    claim_id: str,
    right_category: Optional[str] = Query(None, description="Optional right category filter"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    coordinator: CounselReviewLoopCoordinator = Depends(get_reviewer_loop_coordinator),
    engine: CitationSuggestionEngine = Depends(get_citation_engine),
) -> CitationSuggestionResponse:
    """Returns statutory and contractual citation templates recommended for a claim."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    coordinator.verify_tenant_ownership(tenant_id, claim_id)
    return engine.suggest_citations(claim_id=claim_id, right_category=right_category)


@decision_router.get(
    "/{claim_id}/attempts",
    response_model=AttemptLineageResponse,
    summary="Get Chronological Attempt Lineage for Claim",
)
async def get_claim_attempts(
    claim_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    coordinator: CounselReviewLoopCoordinator = Depends(get_reviewer_loop_coordinator),
) -> AttemptLineageResponse:
    """Retrieves full historical attempt lineage and prior counsel adjudications for a claim."""
    tenant_id = _extract_verified_tenant_id(tenant_ctx)
    return coordinator.get_attempts(tenant_id=tenant_id, claim_id=claim_id)
