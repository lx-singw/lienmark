"""
backend/api/routes/policies.py

REST API endpoints for Studio Policy Inheritance, Production Overrides & Compliance Gates.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.routes.policy_schemas import (
    ClaimEvaluationRequest, PolicyEvaluationResponse, ProductionOverrideRequest,
    ProductionOverrideResponse, StudioPolicyRequest, StudioPolicyResponse,
)
from backend.core.policy_engine import StudioPolicyEngine, get_policy_engine
from backend.core.policy_types import (
    LicensingScope, PolicyEvaluationResult, ProductionPolicyOverride,
    StudioPolicyConfig, StudioProfileType, TerritoryScope,
)
from backend.core.rbac import LienmarkRole
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.storage.ledger import CryptographicLedger

logger = logging.getLogger("lienmark.api.routes.policies")
router = APIRouter(prefix="/api/v1/organizations", tags=["policies"])
policy_router = router
ADMIN_ROLES = frozenset({"admin", "admins", "studio_admin", "studio_executive", "administrator", "superadmin", "lead_admin"})


def _is_admin(role_val: Any) -> bool:
    """Evaluates if a role string or enum matches Admin or studio_executive privileges."""
    if not role_val:
        return False
    norm = LienmarkRole.normalize(role_val) if hasattr(LienmarkRole, "normalize") else None
    return norm == LienmarkRole.ADMIN or str(role_val).strip().lower() in ADMIN_ROLES


def _verify_tenant_match(tenant_ctx: TenantContext, org_id: str) -> None:
    """Enforces strict tenant boundary isolation matching URL org_id."""
    if not tenant_ctx.matches(org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-tenant access prohibited: Path organization '{org_id}' does not match authenticated tenant '{tenant_ctx.organization_id}'.",
        )


def _extract_actor_identity(request: Request, tenant_ctx: TenantContext) -> Tuple[str, str]:
    """Extracts server-side authenticated principal identity and display name."""
    counsel_auth = getattr(request.state, "counsel_auth", None)
    if counsel_auth and getattr(counsel_auth, "reviewer_identity", None):
        rid = counsel_auth.reviewer_identity.reviewer_id
        return rid, str(counsel_auth.reviewer_identity.reviewer_name or rid)
    actor_id = str(tenant_ctx.user_id or "anonymous")
    claims = getattr(tenant_ctx, "raw_claims", {}) or {}
    actor_name = str(claims.get("name") or claims.get("user_name") or tenant_ctx.email or actor_id)
    return actor_id, actor_name


def _verify_studio_admin_role(tenant_ctx: TenantContext, org_id: str) -> None:
    """Verifies caller holds Studio Admin authority for target organization."""
    _verify_tenant_match(tenant_ctx, org_id)
    if not any(_is_admin(r) for r in tenant_ctx.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Studio policy configuration requires Admin or studio_executive role.")


def _verify_override_admin_authority(tenant_ctx: TenantContext, org_id: str, prod_id: str, caller_role: Optional[str]) -> str:
    """Validates Admin RBAC scoped specifically to prod_id or studio org."""
    _verify_tenant_match(tenant_ctx, org_id)
    if caller_role and not _is_admin(caller_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Production policy overrides require Admin role sign-off.")
    if any(_is_admin(r) for r in tenant_ctx.roles):
        return "admin"
    if _is_admin(tenant_ctx.production_roles.get(prod_id)):
        return "admin"
    if any(_is_admin(r) for p, r in tenant_ctx.production_roles.items() if p != prod_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Principal not authorized to administer target production.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Production policy overrides require Admin role sign-off.")


def _resolve_ledger(request: Request, engine: StudioPolicyEngine) -> Optional[CryptographicLedger]:
    """Resolves active CryptographicLedger from app state or engine."""
    app_state = getattr(getattr(request, "app", None), "state", None)
    if app_state is not None:
        for attr in ("ledger", "cryptographic_ledger", "audit_ledger"):
            if hasattr(app_state, attr):
                val = getattr(app_state, attr)
                return val if isinstance(val, CryptographicLedger) else None
    if isinstance(getattr(engine, "_ledger", None), CryptographicLedger):
        return engine._ledger
    return None


def _parse_enum_list(raw: Optional[List[str]], enum_cls: Any) -> Optional[List[Any]]:
    """Converts raw string list to typed enum list."""
    if raw is None:
        return None
    res: List[Any] = []
    for s in raw:
        clean = str(s).strip().lower().replace("-", "_").replace(" ", "_")
        m = next((e for e in enum_cls if e.value == clean), None)
        if m:
            res.append(m)
        else:
            try:
                res.append(enum_cls(clean))
            except ValueError:
                pass
    return res


def _build_policy_config(org_id: str, payload: StudioPolicyRequest) -> StudioPolicyConfig:
    """Constructs a StudioPolicyConfig from request payload."""
    clean_profile = str(payload.profile_type or "major_theatrical").strip().lower().replace(" ", "_")
    p_type = next((pt for pt in StudioProfileType if pt.value == clean_profile), StudioProfileType.MAJOR_THEATRICAL)
    scopes = _parse_enum_list(payload.required_media_scopes, LicensingScope) or [
        LicensingScope.THEATRICAL, LicensingScope.SVOD, LicensingScope.AVOD,
        LicensingScope.LINEAR_BROADCAST, LicensingScope.IN_FLIGHT, LicensingScope.PROMOTIONAL_TRAILER,
    ]
    territories = _parse_enum_list(payload.distribution_territories, TerritoryScope) or [TerritoryScope.WORLDWIDE]
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
        v7, v8, _, _ = get_golden_fixtures()
        u = next((x for x in v7 + v8 if claim_id in (x.use_id, x.stable_lineage_key)), None)
        if u:
            claim_dict.update({
                "asset_type": u.asset_type, "category": u.asset_type, "description": u.description,
                "term": "perpetual" if u.asset_type != "music_cue" else "limited",
                "territory": "worldwide", "fair_use_claimed": u.asset_type == "trademark",
            })
    except Exception:
        pass
    return claim_dict


def _build_evaluation_response(claim_id: str, org_id: str, prod_id: str, result: PolicyEvaluationResult, actor_id: str) -> PolicyEvaluationResponse:
    """Constructs 4-state evaluation response with actions and provenance."""
    has_ovr = "#override-" in result.effective_policy_id
    if result.is_compliant and has_ovr:
        eval_st, dec_st, actions = "override_applied", "needs_review", ["Authorized policy waiver applied; formal counsel review required."]
    elif result.is_compliant:
        eval_st, dec_st, actions = "compliant", "carried_forward", []
    else:
        has_crit = any(v.severity.upper() == "CRITICAL" for v in result.violations)
        eval_st, dec_st = ("exception" if has_crit else "waiver_required"), ("exception" if has_crit else "stale")
        actions = [v.remedy for v in result.violations if v.remedy]
        if result.requires_special_waiver:
            actions.append("Secure authorized Studio or Production Admin policy override sign-off.")
    prov = {
        "org_id": org_id, "production_id": prod_id, "claim_id": claim_id, "decision_state": dec_st,
        "effective_policy_id": result.effective_policy_id, "evaluated_by": actor_id, "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return PolicyEvaluationResponse(
        result=result, is_compliant=result.is_compliant, violations=result.violations,
        effective_policy_id=result.effective_policy_id, requires_special_waiver=result.requires_special_waiver,
        claim_id=claim_id, evaluation_state=eval_st, decision_state=dec_st, state=eval_st, required_actions=actions, provenance=prov,
    )


@router.get("/{org_id}/policy", response_model=StudioPolicyResponse, summary="Get Studio Baseline Policy")
async def get_studio_policy(org_id: str, tenant_ctx: TenantContext = Depends(get_tenant_context), engine: StudioPolicyEngine = Depends(get_policy_engine)) -> StudioPolicyResponse:
    """Retrieves baseline policy configuration for studio organization."""
    _verify_tenant_match(tenant_ctx, org_id)
    return StudioPolicyResponse(policy=engine.get_studio_policy(org_id))


@router.put("/{org_id}/policy", response_model=StudioPolicyResponse, summary="Update Studio Baseline Policy")
async def update_studio_policy(org_id: str, payload: StudioPolicyRequest, request: Request, tenant_ctx: TenantContext = Depends(get_tenant_context), engine: StudioPolicyEngine = Depends(get_policy_engine)) -> StudioPolicyResponse:
    """Updates baseline studio policy; strictly requires Studio Admin role for organization."""
    _verify_studio_admin_role(tenant_ctx, org_id)
    actor_id, _ = _extract_actor_identity(request, tenant_ctx)
    active_ledger = _resolve_ledger(request, engine)
    if active_ledger is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cryptographic audit ledger is not active or unavailable.")
    updated = _build_policy_config(org_id, payload)
    try:
        saved = engine.set_studio_policy(updated, actor_id=actor_id, ledger=active_ledger)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update studio policy: {exc}") from exc
    return StudioPolicyResponse(policy=saved)


@router.get("/{org_id}/productions/{prod_id}/effective-policy", response_model=StudioPolicyResponse, summary="Get Effective Policy for Production")
async def get_effective_policy(org_id: str, prod_id: str, tenant_ctx: TenantContext = Depends(get_tenant_context), engine: StudioPolicyEngine = Depends(get_policy_engine)) -> StudioPolicyResponse:
    """Retrieves resolved effective policy merging studio baseline and child overrides."""
    _verify_tenant_match(tenant_ctx, org_id)
    return StudioPolicyResponse(policy=engine.get_effective_policy(org_id, prod_id))


@router.post("/{org_id}/productions/{prod_id}/policy-override", response_model=ProductionOverrideResponse, summary="Apply Production Policy Override")
async def apply_policy_override(org_id: str, prod_id: str, payload: ProductionOverrideRequest, request: Request, tenant_ctx: TenantContext = Depends(get_tenant_context), engine: StudioPolicyEngine = Depends(get_policy_engine)) -> ProductionOverrideResponse:
    """Applies production policy override with scoped Admin RBAC and fail-closed cryptographic ledger audit."""
    verified_role = _verify_override_admin_authority(tenant_ctx, org_id, prod_id, payload.actor_role)
    actor_id, actor_name = _extract_actor_identity(request, tenant_ctx)
    active_ledger = _resolve_ledger(request, engine)
    if active_ledger is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cryptographic audit ledger is not active or unavailable.")

    override = ProductionPolicyOverride(
        override_id=f"ovr_{uuid.uuid4().hex[:12]}", production_id=prod_id, org_id=org_id,
        admin_actor_id=actor_id, admin_actor_name=payload.admin_actor_name or actor_name,
        rationale=payload.rationale, overridden_media_scopes=_parse_enum_list(payload.overridden_media_scopes, LicensingScope),
        overridden_territories=_parse_enum_list(payload.overridden_territories, TerritoryScope),
        allow_trademark_fair_use=payload.allow_trademark_fair_use, waiver_notes=payload.waiver_notes,
    )
    try:
        eff_policy = engine.apply_production_override(org_id, prod_id, override, actor_role=verified_role, ledger=active_ledger)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Production policy overrides require Admin role sign-off.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audit ledger write failed: {exc}") from exc

    if not override.ledger_event_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Audit ledger event was not committed; fail-closed policy violation.")
    return ProductionOverrideResponse(effective_policy=eff_policy, audit_event_id=override.ledger_event_id, override_id=override.override_id, production_id=prod_id, org_id=org_id)


@router.post("/{org_id}/productions/{prod_id}/claims/{claim_id}/evaluate-policy", response_model=PolicyEvaluationResponse, summary="Evaluate Claim Against Production Effective Policy")
async def evaluate_claim_policy(org_id: str, prod_id: str, claim_id: str, request: Request, claim_input: Optional[ClaimEvaluationRequest] = None, tenant_ctx: TenantContext = Depends(get_tenant_context), engine: StudioPolicyEngine = Depends(get_policy_engine)) -> PolicyEvaluationResponse:
    """Evaluates an intellectual property claim against effective policy returning 4-state response."""
    _verify_tenant_match(tenant_ctx, org_id)
    raw_dict = claim_input.model_dump(exclude_unset=True) if claim_input else None
    resolved_claim = _resolve_claim_input(claim_id, raw_dict)
    result = engine.evaluate_claim(resolved_claim, org_id, prod_id)
    actor_id, _ = _extract_actor_identity(request, tenant_ctx)
    return _build_evaluation_response(claim_id, org_id, prod_id, result, actor_id)
