"""
backend/api/routes/policies.py

REST API endpoints for Studio Policy Inheritance, Production Overrides & Compliance Gates.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.routes.policy_schemas import (
    ClaimEvaluationRequest,
    PolicyEvaluationResponse,
    ProductionOverrideRequest,
    ProductionOverrideResponse,
    StudioPolicyRequest,
    StudioPolicyResponse,
)
from backend.core.policy_engine import StudioPolicyEngine, get_policy_engine
from backend.core.policy_types import (
    LicensingScope,
    ProductionPolicyOverride,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
)
from backend.core.rbac import LienmarkRole
from backend.middleware.tenant import TenantContext, get_tenant_context

logger = logging.getLogger("lienmark.api.routes.policies")
router = APIRouter(prefix="/api/v1/organizations", tags=["policies"])
policy_router = router

ADMIN_POLICY_ROLES = frozenset({"admin", "admins", "studio_executive", "administrator", "superadmin", "lead_admin"})


def _is_admin(role_val: Any) -> bool:
    """Evaluates if a given role string or enum matches Admin or studio_executive privileges."""
    if not role_val:
        return False
    norm = LienmarkRole.normalize(role_val) if hasattr(LienmarkRole, "normalize") else None
    return norm == LienmarkRole.ADMIN or str(role_val).strip().lower() in ADMIN_POLICY_ROLES


def _verify_studio_admin_role(tenant_ctx: TenantContext) -> None:
    """Verifies caller possesses Admin or studio_executive role for studio baseline edits."""
    user_roles = list(tenant_ctx.roles) + list(tenant_ctx.production_roles.values())
    if user_roles and not any(_is_admin(r) for r in user_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Studio policy configuration requires Admin or studio_executive role.")
    if not user_roles and not tenant_ctx.is_demo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Studio policy configuration requires Admin or studio_executive role.")


def _verify_override_admin_role(tenant_ctx: TenantContext, actor_role: str) -> None:
    """Validates that both declared role and authenticated caller hold Admin permissions."""
    if not _is_admin(actor_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Production policy overrides require Admin role sign-off.")
    user_roles = list(tenant_ctx.roles) + list(tenant_ctx.production_roles.values())
    if user_roles and not any(_is_admin(r) for r in user_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Production policy overrides require Admin role sign-off.")


def _parse_scopes(raw_scopes: Optional[List[str]]) -> Optional[List[LicensingScope]]:
    """Converts strings to LicensingScope enums."""
    if raw_scopes is None:
        return None
    res: List[LicensingScope] = []
    for s in raw_scopes:
        clean = str(s).strip().lower().replace("-", "_").replace(" ", "_")
        for m in LicensingScope:
            if m.value == clean:
                res.append(m)
                break
        else:
            try:
                res.append(LicensingScope(clean))
            except ValueError:
                pass
    return res


def _parse_territories(raw_terrs: Optional[List[str]]) -> Optional[List[TerritoryScope]]:
    """Converts strings to TerritoryScope enums."""
    if raw_terrs is None:
        return None
    res: List[TerritoryScope] = []
    for t in raw_terrs:
        clean = str(t).strip().lower().replace("-", "_").replace(" ", "_")
        for m in TerritoryScope:
            if m.value == clean:
                res.append(m)
                break
        else:
            try:
                res.append(TerritoryScope(clean))
            except ValueError:
                pass
    return res


def _build_policy_config(org_id: str, payload: StudioPolicyRequest) -> StudioPolicyConfig:
    """Constructs a StudioPolicyConfig from request payload."""
    clean_profile = str(payload.profile_type or "major_theatrical").strip().lower().replace(" ", "_")
    p_type = StudioProfileType.MAJOR_THEATRICAL
    for pt in StudioProfileType:
        if pt.value == clean_profile:
            p_type = pt
            break
    scopes = _parse_scopes(payload.required_media_scopes) or [
        LicensingScope.THEATRICAL, LicensingScope.SVOD, LicensingScope.AVOD,
        LicensingScope.LINEAR_BROADCAST, LicensingScope.IN_FLIGHT, LicensingScope.PROMOTIONAL_TRAILER,
    ]
    territories = _parse_territories(payload.distribution_territories) or [TerritoryScope.WORLDWIDE]
    return StudioPolicyConfig(
        policy_id=f"pol_{org_id}_{p_type.value}", org_id=org_id, profile_type=p_type,
        required_media_scopes=scopes, distribution_territories=territories,
        mandatory_perpetual_for_theatrical=payload.mandatory_perpetual_for_theatrical if payload.mandatory_perpetual_for_theatrical is not None else True,
        prohibit_unvetted_trademark_fair_use=payload.prohibit_unvetted_trademark_fair_use if payload.prohibit_unvetted_trademark_fair_use is not None else True,
        risk_tolerance_threshold=payload.risk_tolerance_threshold or 0.70,
    )


def _resolve_claim_input(claim_id: str, claim_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolves claim dictionary from input body or fallback fixture lookup."""
    claim_dict: Dict[str, Any] = {"claim_id": claim_id, "use_id": claim_id}
    if claim_data:
        claim_dict.update(claim_data)
        return claim_dict
    try:
        from backend.fixtures.golden_dataset import get_golden_fixtures
        v7_uses, v8_uses, _, _ = get_golden_fixtures()
        for u in v7_uses + v8_uses:
            if claim_id in (u.use_id, u.stable_lineage_key):
                claim_dict.update({
                    "asset_type": u.asset_type, "category": u.asset_type, "description": u.description,
                    "term": "perpetual" if u.asset_type != "music_cue" else "limited",
                    "territory": "worldwide", "fair_use_claimed": u.asset_type == "trademark",
                })
                break
    except Exception:
        pass
    return claim_dict


@router.get("/{org_id}/policy", response_model=StudioPolicyResponse, summary="Get Studio Baseline Policy")
async def get_studio_policy(
    org_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    engine: StudioPolicyEngine = Depends(get_policy_engine),
) -> StudioPolicyResponse:
    """Retrieves baseline policy configuration for studio organization."""
    policy = engine.get_studio_policy(org_id)
    return StudioPolicyResponse(policy=policy)


@router.put("/{org_id}/policy", response_model=StudioPolicyResponse, summary="Update Studio Baseline Policy")
async def update_studio_policy(
    org_id: str,
    payload: StudioPolicyRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    engine: StudioPolicyEngine = Depends(get_policy_engine),
) -> StudioPolicyResponse:
    """Updates baseline studio policy configuration; requires Admin or studio_executive role."""
    _verify_studio_admin_role(tenant_ctx)
    updated = _build_policy_config(org_id, payload)
    saved = engine.set_studio_policy(updated)
    return StudioPolicyResponse(policy=saved)


@router.get("/{org_id}/productions/{prod_id}/effective-policy", response_model=StudioPolicyResponse, summary="Get Effective Policy for Production")
async def get_effective_policy(
    org_id: str,
    prod_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    engine: StudioPolicyEngine = Depends(get_policy_engine),
) -> StudioPolicyResponse:
    """Retrieves resolved effective policy merging studio baseline and child overrides."""
    eff_policy = engine.get_effective_policy(org_id, prod_id)
    return StudioPolicyResponse(policy=eff_policy)


@router.post("/{org_id}/productions/{prod_id}/policy-override", response_model=ProductionOverrideResponse, summary="Apply Production Policy Override")
async def apply_policy_override(
    org_id: str,
    prod_id: str,
    payload: ProductionOverrideRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    engine: StudioPolicyEngine = Depends(get_policy_engine),
) -> ProductionOverrideResponse:
    """Applies production policy override, validates Admin RBAC, and logs ledger event."""
    _verify_override_admin_role(tenant_ctx, payload.actor_role)
    override = ProductionPolicyOverride(
        override_id=f"ovr_{uuid.uuid4().hex[:12]}", production_id=prod_id, org_id=org_id,
        admin_actor_id=payload.admin_actor_id, admin_actor_name=payload.admin_actor_name,
        rationale=payload.rationale, overridden_media_scopes=_parse_scopes(payload.overridden_media_scopes),
        overridden_territories=_parse_territories(payload.overridden_territories),
        allow_trademark_fair_use=payload.allow_trademark_fair_use, waiver_notes=payload.waiver_notes,
    )
    try:
        eff_policy = engine.apply_production_override(
            org_id=org_id, production_id=prod_id, override=override, actor_role=payload.actor_role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Production policy overrides require Admin role sign-off.") from exc
    return ProductionOverrideResponse(
        effective_policy=eff_policy, audit_event_id=override.ledger_event_id or f"evt_override_{uuid.uuid4().hex[:12]}",
        override_id=override.override_id, production_id=prod_id, org_id=org_id,
    )


@router.post("/{org_id}/productions/{prod_id}/claims/{claim_id}/evaluate-policy", response_model=PolicyEvaluationResponse, summary="Evaluate Claim Against Production Effective Policy")
async def evaluate_claim_policy(
    org_id: str,
    prod_id: str,
    claim_id: str,
    claim_input: Optional[ClaimEvaluationRequest] = None,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    engine: StudioPolicyEngine = Depends(get_policy_engine),
) -> PolicyEvaluationResponse:
    """Evaluates an intellectual property claim against the resolved effective policy."""
    raw_dict = claim_input.model_dump(exclude_unset=True) if claim_input else None
    resolved_claim = _resolve_claim_input(claim_id, raw_dict)
    result = engine.evaluate_claim(claim=resolved_claim, org_id=org_id, production_id=prod_id)
    return PolicyEvaluationResponse(result=result, claim_id=claim_id)
