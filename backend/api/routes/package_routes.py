"""
backend/api/routes/package_routes.py

REST API endpoints for Decision Package dual-review workflow.
Sprint 5.2: Two-Person Accountable Review & Decision Package Binding.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.routes.decision_schemas import (
    ApprovePackageRequest,
    CreatePackageRequest,
    DecisionPackageResponse,
    PackageApprovalResponse,
)
from backend.core.decision_package_types import (
    DecisionPackage,
    PackageApprovalRecord,
)
from backend.core.dual_review import (
    DualReviewCoordinator,
    get_dual_review_coordinator,
)
from backend.core.dual_review_exceptions import (
    ConflictAttestationError,
    ConflictOfInterestError,
    DistinctReviewerError,
    DualReviewError,
    PackageNotFoundError,
    StalePackageError,
)
from backend.core.rbac import LienmarkRole
from backend.middleware.tenant import TenantContext, get_tenant_context

logger = logging.getLogger("lienmark.api.routes.packages")

package_router = APIRouter(prefix="/api/v1/claims", tags=["packages"])

AUTHORIZED_PACKAGE_ROLES = frozenset({
    LienmarkRole.REVIEWER,
    LienmarkRole.ADMIN,
})


def _extract_actor_identity(
    tenant_ctx: TenantContext, request: Request,
) -> tuple[str, str, str]:
    """Server-side actor extraction. Returns (actor_id, actor_name, actor_role)."""
    actor_id = tenant_ctx.user_id
    if not actor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated principal identity.",
        )
    actor_name = tenant_ctx.email or actor_id
    user_roles = LienmarkRole.coerce_set(tenant_ctx.roles)
    if tenant_ctx.production_roles:
        user_roles.update(LienmarkRole.coerce_set(tenant_ctx.production_roles.values()))
    counsel_auth = getattr(request.state, "counsel_auth", None)
    if counsel_auth and getattr(counsel_auth, "is_authenticated", False):
        user_roles.add(LienmarkRole.REVIEWER)
    matching = user_roles.intersection(AUTHORIZED_PACKAGE_ROLES)
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Principal lacks required REVIEWER or ADMIN role for package operations.",
        )
    role = next(iter(matching))
    return actor_id, actor_name, role.value


def _to_approval_response(
    record: Optional[PackageApprovalRecord],
) -> Optional[PackageApprovalResponse]:
    """Maps a domain PackageApprovalRecord to its REST response model."""
    if record is None:
        return None
    return PackageApprovalResponse(
        approval_id=record.approval_id,
        reviewer_id=record.reviewer_id,
        reviewer_name=record.reviewer_name,
        reviewer_role=record.reviewer_role,
        is_primary_or_secondary=record.is_primary_or_secondary,
        conflict_attestation=record.conflict_attestation,
        timestamp_utc=record.timestamp_utc,
        notes=record.notes,
    )


def _to_package_response(pkg: DecisionPackage) -> DecisionPackageResponse:
    """Maps a domain DecisionPackage to its REST response envelope."""
    return DecisionPackageResponse(
        package_id=pkg.package_id,
        version=pkg.version,
        claim_id=pkg.claim_id,
        status=pkg.status.value,
        canonical_digest=pkg.canonical_digest or pkg.compute_digest(),
        proposed_disposition=pkg.proposed_disposition,
        conditions=pkg.conditions,
        policy_version=pkg.policy_version,
        primary_approval=_to_approval_response(pkg.primary_approval),
        secondary_approval=_to_approval_response(pkg.secondary_approval),
        supersedes_package_id=pkg.supersedes_package_id,
        created_at_utc=pkg.created_at_utc,
        updated_at_utc=pkg.updated_at_utc,
    )


@package_router.post(
    "/{claim_id}/packages",
    response_model=DecisionPackageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Retrieve Active Decision Package",
)
async def create_or_get_package(
    claim_id: str,
    payload: CreatePackageRequest,
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    coordinator: DualReviewCoordinator = Depends(get_dual_review_coordinator),
) -> DecisionPackageResponse:
    """Creates a new decision package or returns the existing active package for this claim."""
    actor_id, _, _ = _extract_actor_identity(tenant_ctx, request)
    tenant_id = tenant_ctx.tenant_id or tenant_ctx.organization_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing verified tenant identity in request credentials.",
        )
    existing = coordinator.get_active_package_for_claim(claim_id)
    if existing:
        return _to_package_response(existing)
    prod_id = tenant_ctx.current_production_id or "prod_default"
    pkg = coordinator.create_package(
        claim_id=claim_id,
        cut_revision=payload.cut_revision,
        proposed_disposition=payload.proposed_disposition,
        conditions=payload.conditions,
        evidence_bundle=payload.evidence_bundle,
        policy_version=payload.policy_version or "v1.0",
        policy_digest=payload.policy_digest,
        intended_scope=payload.intended_scope,
        entity_names=payload.entity_names,
        tenant_id=str(tenant_id),
        production_id=prod_id,
    )
    logger.info("Package created: %s for claim %s by %s", pkg.package_id, claim_id, actor_id)
    return _to_package_response(pkg)


@package_router.post(
    "/{claim_id}/packages/{package_id}/approve",
    response_model=DecisionPackageResponse,
    summary="Submit Primary or Secondary Approval on Decision Package",
)
async def approve_package(
    claim_id: str,
    package_id: str,
    payload: ApprovePackageRequest,
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    coordinator: DualReviewCoordinator = Depends(get_dual_review_coordinator),
) -> DecisionPackageResponse:
    """Submits primary or secondary approval under two-distinct-principals invariant."""
    actor_id, actor_name, actor_role = _extract_actor_identity(tenant_ctx, request)
    try:
        pkg, _record = coordinator.submit_approval(
            package_id=package_id,
            reviewer_id=actor_id,
            reviewer_name=actor_name,
            reviewer_role=actor_role,
            conflict_attestation=payload.conflict_attestation,
            notes=payload.notes,
            ledger=getattr(request.app.state, "ledger", None),
        )
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StalePackageError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ConflictAttestationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DistinctReviewerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConflictOfInterestError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DualReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if pkg.claim_id != claim_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Package claim_id mismatch.")
    logger.info("Package %s approved by %s (stage: %s)", package_id, actor_id, pkg.status.value)
    return _to_package_response(pkg)


@package_router.get(
    "/{claim_id}/packages/{package_id}",
    response_model=DecisionPackageResponse,
    summary="Get Decision Package and Approval Lineage",
)
async def get_package(
    claim_id: str,
    package_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    coordinator: DualReviewCoordinator = Depends(get_dual_review_coordinator),
) -> DecisionPackageResponse:
    """Retrieves a decision package with its full approval lineage."""
    pkg = coordinator.get_package(package_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision package '{package_id}' not found.",
        )
    if pkg.claim_id != claim_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Package claim_id does not match URL claim_id.",
        )
    return _to_package_response(pkg)
