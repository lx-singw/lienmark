"""
Lienmark Role-Based Access Control (RBAC) Subsystem
Sprint 5C / Multi-Tenant Security & Agentic Cinema Compliance

Provides:
1. LienmarkRole & LienmarkPermission Enums: Canonical roles (PRODUCER, ANALYST, REVIEWER,
   ADMIN, VIEWER) with robust string normalization handling aliases (e.g. 'post_supervisor',
   'authorized_reviewer', 'counsel', 'studio_executive').
2. Fine-grained Permission Matrix: Production-grade capability assignments for script intake,
   clearance analysis, counsel checkpoint decisions, legal defense brief export, and administration.
3. Fast & Robust Role Extraction: Request-scoped RBACContext synthesizing TenantContext,
   production-scoped roles, and CounselAuthContext / verify_counsel_token with O(1) request caching.
4. Route Decorators: @require_role and @require_permission supporting both sync and async FastAPI
   endpoints, preserving route metadata, reflection signatures, and docstrings.
5. FastAPI Dependencies: RequireRole and RequirePermission callables for Depends() injection with
   fail-closed 403 Forbidden diagnostic logging, correlation IDs, and structured JSON error responses.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from fastapi import Depends, HTTPException, Request, Response, status
from starlette.datastructures import Headers

from backend.middleware.tenant import (
    TenantContext,
    get_current_tenant_context,
)
from backend.core.security import (
    CounselAuthContext,
    get_correlation_id,
    verify_counsel_token,
    is_strict_auth_enabled,
    VALID_COUNSEL_REGISTRY,
)

logger = logging.getLogger("lienmark.security.rbac")

F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# 1. Role & Permission Enums with Robust String Normalization
# =============================================================================

class LienmarkRole(str, Enum):
    """
    Canonical principal roles governing clearance workflows in Lienmark.
    """
    PRODUCER = "producer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    VIEWER = "viewer"

    @classmethod
    def normalize(cls, val: Any) -> Optional[LienmarkRole]:
        """
        Normalizes any input string or enum into a canonical LienmarkRole,
        transparently resolving aliases and case/punctuation variations.
        Returns None if unrecognized.
        """
        return normalize_role_name(val)

    @classmethod
    def from_value(
        cls,
        val: Any,
        default: Optional[LienmarkRole] = None,
    ) -> LienmarkRole:
        """
        Strictly parses input into a LienmarkRole.
        Raises ValueError if unrecognized and no default is provided.
        """
        norm = cls.normalize(val)
        if norm is not None:
            return norm
        if default is not None:
            return default
        raise ValueError(
            f"Unrecognized role string: {val!r}. "
            f"Valid roles: {[r.value for r in cls]}"
        )

    @classmethod
    def coerce_set(cls, items: Iterable[Any]) -> Set[LienmarkRole]:
        """Coerces an iterable of raw role strings or enums into a set of canonical roles."""
        result: Set[LienmarkRole] = set()
        for item in items:
            norm = cls.normalize(item)
            if norm is not None:
                result.add(norm)
        return result

    @property
    def permissions(self) -> FrozenSet[LienmarkPermission]:
        """Returns the default set of fine-grained permissions granted to this role."""
        return DEFAULT_ROLE_PERMISSIONS.get(self, frozenset())

    def has_permission(self, permission: Union[str, LienmarkPermission]) -> bool:
        """Checks if this role possesses the specified permission."""
        norm = LienmarkPermission.normalize(permission)
        return norm is not None and norm in self.permissions


class LienmarkPermission(str, Enum):
    """
    Fine-grained capability identifiers for multi-tenant entertainment clearance.
    """
    # Pipeline & Intake
    INTAKE_SUBMIT = "intake:submit"
    INTAKE_READ = "intake:read"
    INTAKE_EDIT = "intake:edit"
    PIPELINE_TRIGGER = "pipeline:trigger"

    # Analysis & Research
    ANALYSIS_RUN = "analysis:run"
    ANALYSIS_READ = "analysis:read"
    EVIDENCE_RESEARCH = "evidence:research"
    DELTA_DIFF = "delta:diff"

    # Counsel Checkpoint & Human-in-the-Loop Review
    CLAIM_REVIEW = "claim:review"
    CLAIM_APPROVE = "claim:approve"
    CLAIM_REJECT = "claim:reject"
    CLAIM_OVERRIDE = "claim:override"
    COUNSEL_ATTEST = "counsel:attest"
    COUNSEL_REATTEST = "counsel:reattest"

    # Reports, Briefs & Exceptions Schedules
    EXCEPTIONS_SCHEDULE_GENERATE = "exceptions_schedule:generate"
    EXCEPTIONS_SCHEDULE_EXPORT = "exceptions_schedule:export"
    LEGAL_BRIEF_EXPORT = "legal_brief:export"
    AUDIT_EXPORT = "audit:export"

    # Tenant Administration & Configuration
    TENANT_MANAGE = "tenant:manage"
    USERS_MANAGE = "users:manage"
    POLICY_OVERRIDE = "policy:override"
    DEMO_RESET = "demo:reset"

    @classmethod
    def normalize(cls, val: Any) -> Optional[LienmarkPermission]:
        """Normalizes permission representation (colon or underscore separated)."""
        if val is None:
            return None
        if isinstance(val, cls):
            return val
        s = str(val).strip().lower()
        # Direct value match (e.g. "claim:approve")
        for member in cls:
            if member.value == s:
                return member
        # Name match (e.g. "claim_approve" or "CLAIM_APPROVE")
        s_clean = re.sub(r"[\s\-:]+", "_", s).upper()
        if s_clean in cls.__members__:
            return cls.__members__[s_clean]
        return None

    @classmethod
    def from_value(
        cls,
        val: Any,
        default: Optional[LienmarkPermission] = None,
    ) -> LienmarkPermission:
        """Strictly parses input into a LienmarkPermission or raises ValueError."""
        norm = cls.normalize(val)
        if norm is not None:
            return norm
        if default is not None:
            return default
        raise ValueError(
            f"Unrecognized permission: {val!r}. "
            f"Valid permissions: {[p.value for p in cls]}"
        )


# =============================================================================
# 2. Alias Mapping & Permission Matrix
# =============================================================================

ROLE_ALIASES: Dict[str, LienmarkRole] = {
    # PRODUCER aliases (post supervisor, production management)
    "producer": LienmarkRole.PRODUCER,
    "producers": LienmarkRole.PRODUCER,
    "lead_producer": LienmarkRole.PRODUCER,
    "executive_producer": LienmarkRole.PRODUCER,
    "line_producer": LienmarkRole.PRODUCER,
    "post_supervisor": LienmarkRole.PRODUCER,
    "post_super": LienmarkRole.PRODUCER,
    "post_production": LienmarkRole.PRODUCER,
    "production_coordinator": LienmarkRole.PRODUCER,
    "production_manager": LienmarkRole.PRODUCER,
    "showrunner": LienmarkRole.PRODUCER,

    # REVIEWER aliases (counsel, authorized reviewer, clearance attorney)
    "reviewer": LienmarkRole.REVIEWER,
    "reviewers": LienmarkRole.REVIEWER,
    "authorized_reviewer": LienmarkRole.REVIEWER,
    "counsel": LienmarkRole.REVIEWER,
    "lead_counsel": LienmarkRole.REVIEWER,
    "associate_counsel": LienmarkRole.REVIEWER,
    "production_attorney": LienmarkRole.REVIEWER,
    "attorney": LienmarkRole.REVIEWER,
    "legal": LienmarkRole.REVIEWER,
    "legal_counsel": LienmarkRole.REVIEWER,
    "clearance_counsel": LienmarkRole.REVIEWER,
    "legal_reviewer": LienmarkRole.REVIEWER,
    "counsel_reviewer": LienmarkRole.REVIEWER,
    "judge": LienmarkRole.REVIEWER,
    "presenter": LienmarkRole.REVIEWER,

    # ANALYST aliases (clearance researcher, automated agent pipeline)
    "analyst": LienmarkRole.ANALYST,
    "analysts": LienmarkRole.ANALYST,
    "clearance_analyst": LienmarkRole.ANALYST,
    "researcher": LienmarkRole.ANALYST,
    "paralegal": LienmarkRole.ANALYST,
    "automated_agent_pipeline": LienmarkRole.ANALYST,
    "pipeline_agent": LienmarkRole.ANALYST,
    "agent": LienmarkRole.ANALYST,
    "ai_agent": LienmarkRole.ANALYST,
    "service_account": LienmarkRole.ANALYST,

    # ADMIN aliases (studio executive, administrator, superadmin)
    "admin": LienmarkRole.ADMIN,
    "admins": LienmarkRole.ADMIN,
    "administrator": LienmarkRole.ADMIN,
    "superadmin": LienmarkRole.ADMIN,
    "superuser": LienmarkRole.ADMIN,
    "studio_admin": LienmarkRole.ADMIN,
    "studio_executive": LienmarkRole.ADMIN,
    "executive": LienmarkRole.ADMIN,
    "owner": LienmarkRole.ADMIN,
    "root": LienmarkRole.ADMIN,

    # VIEWER aliases (read-only observer, guest, auditor)
    "viewer": LienmarkRole.VIEWER,
    "viewers": LienmarkRole.VIEWER,
    "read_only": LienmarkRole.VIEWER,
    "readonly": LienmarkRole.VIEWER,
    "observer": LienmarkRole.VIEWER,
    "guest": LienmarkRole.VIEWER,
    "auditor": LienmarkRole.VIEWER,
}


def normalize_role_name(raw_value: Any) -> Optional[LienmarkRole]:
    """
    Cleanses, canonicalizes, and translates arbitrary strings and aliases
    into a valid LienmarkRole.
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, LienmarkRole):
        return raw_value

    text = str(raw_value).strip().lower()
    if not text:
        return None

    # Replace spaces, hyphens, and slashes with underscores
    cleaned = re.sub(r"[\s\-\/]+", "_", text).strip("_")

    # 1. Direct match on enum values
    for role in LienmarkRole:
        if role.value == cleaned:
            return role

    # 2. Match on enum names (PRODUCER, ANALYST, etc.)
    cleaned_upper = cleaned.upper()
    if cleaned_upper in LienmarkRole.__members__:
        return LienmarkRole.__members__[cleaned_upper]

    # 3. Lookup in configured aliases
    if cleaned in ROLE_ALIASES:
        return ROLE_ALIASES[cleaned]

    return None


DEFAULT_ROLE_PERMISSIONS: Dict[LienmarkRole, FrozenSet[LienmarkPermission]] = {
    # ADMIN possesses all capabilities across the workspace
    LienmarkRole.ADMIN: frozenset(LienmarkPermission),

    # REVIEWER (Production Clearance Counsel)
    LienmarkRole.REVIEWER: frozenset({
        LienmarkPermission.INTAKE_READ,
        LienmarkPermission.ANALYSIS_READ,
        LienmarkPermission.ANALYSIS_RUN,
        LienmarkPermission.EVIDENCE_RESEARCH,
        LienmarkPermission.DELTA_DIFF,
        LienmarkPermission.CLAIM_REVIEW,
        LienmarkPermission.CLAIM_APPROVE,
        LienmarkPermission.CLAIM_REJECT,
        LienmarkPermission.CLAIM_OVERRIDE,
        LienmarkPermission.COUNSEL_ATTEST,
        LienmarkPermission.COUNSEL_REATTEST,
        LienmarkPermission.EXCEPTIONS_SCHEDULE_GENERATE,
        LienmarkPermission.EXCEPTIONS_SCHEDULE_EXPORT,
        LienmarkPermission.LEGAL_BRIEF_EXPORT,
        LienmarkPermission.AUDIT_EXPORT,
    }),

    # PRODUCER (Post Supervisor / Executive Producer)
    LienmarkRole.PRODUCER: frozenset({
        LienmarkPermission.INTAKE_SUBMIT,
        LienmarkPermission.INTAKE_READ,
        LienmarkPermission.INTAKE_EDIT,
        LienmarkPermission.PIPELINE_TRIGGER,
        LienmarkPermission.ANALYSIS_READ,
        LienmarkPermission.ANALYSIS_RUN,
        LienmarkPermission.DELTA_DIFF,
        LienmarkPermission.CLAIM_REVIEW,
        LienmarkPermission.EXCEPTIONS_SCHEDULE_EXPORT,
        LienmarkPermission.DEMO_RESET,
    }),

    # ANALYST (Clearance Researcher / Automated Pipeline)
    LienmarkRole.ANALYST: frozenset({
        LienmarkPermission.INTAKE_READ,
        LienmarkPermission.ANALYSIS_READ,
        LienmarkPermission.ANALYSIS_RUN,
        LienmarkPermission.EVIDENCE_RESEARCH,
        LienmarkPermission.DELTA_DIFF,
        LienmarkPermission.CLAIM_REVIEW,
    }),

    # VIEWER (Auditor / Guest)
    LienmarkRole.VIEWER: frozenset({
        LienmarkPermission.INTAKE_READ,
        LienmarkPermission.ANALYSIS_READ,
    }),
}


# =============================================================================
# 3. Domain Model: RBACContext
# =============================================================================

@dataclass(frozen=True)
class RBACContext:
    """
    Immutable authorization context synthesized for the active request.
    Encapsulates verified global roles, production-scoped roles, permissions,
    and provenance from TenantContext and CounselAuthContext.
    """
    user_id: Optional[str]
    organization_id: Optional[str]
    roles: FrozenSet[LienmarkRole] = field(default_factory=frozenset)
    permissions: FrozenSet[LienmarkPermission] = field(default_factory=frozenset)
    active_production_id: Optional[str] = None
    auth_method: str = "anonymous"
    is_authenticated: bool = False
    is_demo: bool = False
    tenant_context: Optional[TenantContext] = None
    counsel_auth: Optional[CounselAuthContext] = None

    def has_role(self, role: Union[str, LienmarkRole]) -> bool:
        """Checks if the principal holds the given role."""
        norm = LienmarkRole.normalize(role)
        return norm is not None and norm in self.roles

    def has_any_role(self, *roles: Union[str, LienmarkRole]) -> bool:
        """Checks if the principal holds at least one of the specified roles."""
        norm_roles = {LienmarkRole.normalize(r) for r in roles}
        norm_roles.discard(None)
        return bool(self.roles.intersection(norm_roles))

    def has_all_roles(self, *roles: Union[str, LienmarkRole]) -> bool:
        """Checks if the principal holds all specified roles."""
        norm_roles = {LienmarkRole.normalize(r) for r in roles}
        norm_roles.discard(None)
        if not norm_roles:
            return True
        return norm_roles.issubset(self.roles)

    def has_permission(self, permission: Union[str, LienmarkPermission]) -> bool:
        """Checks if the principal possesses the specified permission."""
        norm = LienmarkPermission.normalize(permission)
        return norm is not None and norm in self.permissions

    def has_any_permission(self, *permissions: Union[str, LienmarkPermission]) -> bool:
        """Checks if the principal possesses at least one of the specified permissions."""
        norm_perms = {LienmarkPermission.normalize(p) for p in permissions}
        norm_perms.discard(None)
        return bool(self.permissions.intersection(norm_perms))

    def has_all_permissions(self, *permissions: Union[str, LienmarkPermission]) -> bool:
        """Checks if the principal possesses all specified permissions."""
        norm_perms = {LienmarkPermission.normalize(p) for p in permissions}
        norm_perms.discard(None)
        if not norm_perms:
            return True
        return norm_perms.issubset(self.permissions)


# =============================================================================
# 4. Fast & Robust Role Extraction
# =============================================================================

STATE_RBAC_KEY = "_lienmark_rbac_context"


def extract_rbac_context(
    request: Optional[Request] = None,
    production_id: Optional[str] = None,
    enforce_counsel_verification: bool = False,
) -> RBACContext:
    """
    Synthesizes and memoizes a verified RBACContext for the active request.

    Extraction order:
    1. Request state cache (_lienmark_rbac_context) for sub-microsecond retrieval.
    2. TenantContext from request.state.tenant or ContextVar get_current_tenant_context().
       - Global roles (tenant_ctx.roles) normalized into LienmarkRole.
       - Production-scoped roles (tenant_ctx.production_roles) if production_id matches.
    3. CounselAuthContext from request.state.counsel_auth or verify_counsel_token().
       - Valid counsel identity injects LienmarkRole.REVIEWER.
    4. Aggregation of all fine-grained permissions for all verified roles.
    """
    # 1. Fast Cache Retrieval on request.state
    if request is not None and hasattr(request, "state"):
        cached = getattr(request.state, STATE_RBAC_KEY, None)
        if isinstance(cached, RBACContext):
            if production_id is None or cached.active_production_id == production_id:
                return cached

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    auth_method: str = "anonymous"
    is_authenticated: bool = False
    is_demo: bool = False
    active_prod: Optional[str] = production_id

    tenant_ctx: Optional[TenantContext] = None
    counsel_ctx: Optional[CounselAuthContext] = None

    collected_roles: Set[LienmarkRole] = set()

    # 2. Extract from TenantContext
    if request is not None and hasattr(request, "state"):
        tenant_ctx = getattr(request.state, "tenant", None) or getattr(request.state, "tenant_context", None)

    if tenant_ctx is None:
        tenant_ctx = get_current_tenant_context(required=False)

    if isinstance(tenant_ctx, TenantContext):
        org_id = tenant_ctx.organization_id or tenant_ctx.org_id
        user_id = tenant_ctx.user_id
        auth_method = tenant_ctx.auth_method
        is_authenticated = bool(user_id or auth_method not in ("anonymous", "default"))
        is_demo = bool(tenant_ctx.is_demo)

        if active_prod is None:
            if request is not None:
                active_prod = (
                    request.path_params.get("production_id")
                    or request.query_params.get("production_id")
                    or request.headers.get("X-Production-Id")
                )
            if active_prod is None:
                active_prod = tenant_ctx.current_production_id

        # Normalize global tenant roles
        for raw_role in tenant_ctx.roles:
            norm_role = LienmarkRole.normalize(raw_role)
            if norm_role is not None:
                collected_roles.add(norm_role)

        # Normalize production-scoped roles if active production is recognized
        if active_prod and active_prod in tenant_ctx.production_roles:
            prod_raw = tenant_ctx.production_roles[active_prod]
            norm_prod = LienmarkRole.normalize(prod_raw)
            if norm_prod is not None:
                collected_roles.add(norm_prod)

    # 3. Extract / Verify Counsel Authentication
    if request is not None and hasattr(request, "state"):
        counsel_ctx = getattr(request.state, "counsel_auth", None)

    if counsel_ctx is None and request is not None:
        # Check if counsel credentials exist
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        counsel_header = request.headers.get("X-Counsel-Token") or request.headers.get("x-counsel-token")
        has_credentials = bool(auth_header or counsel_header)
        requires_counsel_auth = (
            request.headers.get("X-Require-Counsel-Auth", "").lower() in ("true", "1")
            or is_strict_auth_enabled()
        )
        is_demo_context = tenant_ctx and (tenant_ctx.is_demo or tenant_ctx.auth_method in ("demo_default", "header", "anonymous"))

        if has_credentials or enforce_counsel_verification or requires_counsel_auth or is_demo_context:
            try:
                counsel_ctx = verify_counsel_token(request, enforce_auth=enforce_counsel_verification)
                if hasattr(request, "state"):
                    request.state.counsel_auth = counsel_ctx
            except HTTPException as exc:
                if has_credentials or enforce_counsel_verification or requires_counsel_auth:
                    raise exc
                logger.debug(f"Counsel token verification skipped/failed: {exc}")

    if isinstance(counsel_ctx, CounselAuthContext) and counsel_ctx.is_authenticated:
        collected_roles.add(LienmarkRole.REVIEWER)
        is_authenticated = True
        if counsel_ctx.is_demo:
            is_demo = True
        if user_id is None and counsel_ctx.reviewer_identity:
            user_id = counsel_ctx.reviewer_identity.reviewer_id
        if auth_method == "anonymous":
            auth_method = "counsel_token"

    # 4. Synthesize Aggregate Permissions
    collected_permissions: Set[LienmarkPermission] = set()
    for role in collected_roles:
        collected_permissions.update(role.permissions)

    rbac = RBACContext(
        user_id=user_id,
        organization_id=org_id,
        roles=frozenset(collected_roles),
        permissions=frozenset(collected_permissions),
        active_production_id=active_prod,
        auth_method=auth_method,
        is_authenticated=is_authenticated,
        is_demo=is_demo,
        tenant_context=tenant_ctx,
        counsel_auth=counsel_ctx,
    )

    # Cache for the remainder of this request
    if request is not None and hasattr(request, "state"):
        setattr(request.state, STATE_RBAC_KEY, rbac)

    return rbac


# =============================================================================
# 5. Fail-Closed Structured Rejections & Diagnostic Logging
# =============================================================================

class RBACAccessDeniedException(HTTPException):
    """
    Fail-closed 403 Forbidden exception returning structured JSON error details
    and anti-tamper security response headers.
    """
    def __init__(
        self,
        message: str,
        required: Iterable[str],
        granted: Iterable[str],
        check_type: str = "role",
        status_code: int = status.HTTP_403_FORBIDDEN,
        headers: Optional[Dict[str, str]] = None,
    ):
        corr_id = get_correlation_id()
        timestamp = datetime.now(timezone.utc).isoformat()

        detail: Dict[str, Any] = {
            "error": "FORBIDDEN",
            "error_code": "INSUFFICIENT_PERMISSIONS" if check_type == "permission" else "INSUFFICIENT_ROLE",
            "message": message,
            "detail": f"Forbidden: {message}",
            "status_code": status_code,
            "check_type": check_type,
            "required": sorted(list(set(required))),
            "granted": sorted(list(set(granted))),
            "correlation_id": corr_id,
            "timestamp": timestamp,
        }

        response_headers = {
            "X-Security-Policy": "fail-closed-rbac",
            "X-Correlation-ID": corr_id,
        }
        if headers:
            response_headers.update(headers)

        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=response_headers,
        )


def log_rbac_violation(
    request: Optional[Request],
    rbac: Optional[RBACContext],
    required: Iterable[Any],
    check_type: str,
    reason: str,
) -> None:
    """
    Emits structured security warning logs on authorization denial.
    Guarantees secrets and raw tokens are never leaked into log streams.
    """
    corr_id = get_correlation_id()
    client_ip = request.client.host if (request and request.client) else "unknown"
    method = request.method if request else "N/A"
    path = request.url.path if request else "N/A"
    user_id = rbac.user_id if rbac else "anonymous"
    org_id = rbac.organization_id if rbac else "unknown"
    granted = [r.value for r in rbac.roles] if rbac else []

    logger.warning(
        f"SECURITY VIOLATION [RBAC Fail-Closed Access Denied]: "
        f"correlation_id={corr_id} method={method} path={path} client_ip={client_ip} "
        f"org_id={org_id} user_id={user_id} check_type={check_type} "
        f"required={sorted([str(r) for r in required])} granted={sorted(granted)} "
        f"reason={reason}"
    )


# =============================================================================
# 6. Helper: Request Locator
# =============================================================================

def _find_request(*args: Any, **kwargs: Any) -> Optional[Request]:
    """
    Inspects positional and keyword arguments to locate the Starlette/FastAPI
    Request instance regardless of parameter naming (e.g. 'request', 'http_req').
    """
    for arg in args:
        if isinstance(arg, Request):
            return arg
    for v in kwargs.values():
        if isinstance(v, Request):
            return v
    return None


# =============================================================================
# 7. FastAPI Dependencies: RequireRole & RequirePermission
# =============================================================================

class RequireRole:
    """
    FastAPI dependency enforcing that the calling principal holds required LienmarkRole(s).
    Supports single or multiple roles (OR logic by default, AND logic with require_all=True).
    Provides automatic admin bypass unless explicitly disabled.

    Usage:
        @router.post("/review", dependencies=[Depends(RequireRole(LienmarkRole.REVIEWER))])
        async def review(...): ...

        or injecting verified RBACContext:
        @router.post("/review")
        async def review(rbac: RBACContext = Depends(RequireRole(LienmarkRole.REVIEWER))): ...
    """
    def __init__(
        self,
        *roles: Union[LienmarkRole, str, Iterable[Union[LienmarkRole, str]]],
        require_all: bool = False,
        admin_bypass: bool = True,
        production_id_param: Optional[str] = None,
    ):
        flat_roles: List[Union[LienmarkRole, str]] = []
        for r in roles:
            if isinstance(r, (list, tuple, set, frozenset)):
                flat_roles.extend(r)
            else:
                flat_roles.append(r)

        self.required_roles: Set[LienmarkRole] = {
            LienmarkRole.from_value(r) for r in flat_roles if r is not None
        }
        if not self.required_roles:
            raise ValueError("RequireRole requires at least one valid role.")

        self.require_all = require_all
        self.admin_bypass = admin_bypass
        self.production_id_param = production_id_param

    async def __call__(self, request: Request) -> RBACContext:
        return self.enforce(request)

    def enforce(self, request: Optional[Request] = None) -> RBACContext:
        prod_id: Optional[str] = None
        if request is not None and self.production_id_param:
            prod_id = (
                request.path_params.get(self.production_id_param)
                or request.query_params.get(self.production_id_param)
            )

        rbac = extract_rbac_context(
            request=request,
            production_id=prod_id,
            enforce_counsel_verification=False,
        )

        # Admin bypass check
        if self.admin_bypass and LienmarkRole.ADMIN in rbac.roles:
            return rbac

        has_access = (
            rbac.has_all_roles(*self.required_roles)
            if self.require_all
            else rbac.has_any_role(*self.required_roles)
        )

        if not has_access:
            req_str = [r.value for r in self.required_roles]
            grant_str = [r.value for r in rbac.roles]
            mode = "all" if self.require_all else "any"
            reason = (
                f"Principal lacks {mode} of required role(s): {req_str}. "
                f"Granted roles: {grant_str}"
            )
            log_rbac_violation(request, rbac, req_str, "role", reason)

            raise RBACAccessDeniedException(
                message=f"Access denied: Principal lacks required role(s): {', '.join(req_str)}.",
                required=req_str,
                granted=grant_str,
                check_type="role",
            )

        return rbac


class RequirePermission:
    """
    FastAPI dependency enforcing that the calling principal possesses required LienmarkPermission(s).
    Supports single or multiple permissions (AND logic by default, OR logic with require_all=False).

    Usage:
        @router.post("/claims/{id}/approve", dependencies=[Depends(RequirePermission(LienmarkPermission.CLAIM_APPROVE))])
        async def approve(...): ...
    """
    def __init__(
        self,
        *permissions: Union[LienmarkPermission, str, Iterable[Union[LienmarkPermission, str]]],
        require_all: bool = True,
        admin_bypass: bool = True,
        production_id_param: Optional[str] = None,
    ):
        flat_perms: List[Union[LienmarkPermission, str]] = []
        for p in permissions:
            if isinstance(p, (list, tuple, set, frozenset)):
                flat_perms.extend(p)
            else:
                flat_perms.append(p)

        self.required_permissions: Set[LienmarkPermission] = {
            LienmarkPermission.from_value(p) for p in flat_perms if p is not None
        }
        if not self.required_permissions:
            raise ValueError("RequirePermission requires at least one valid permission.")

        self.require_all = require_all
        self.admin_bypass = admin_bypass
        self.production_id_param = production_id_param

    async def __call__(self, request: Request) -> RBACContext:
        return self.enforce(request)

    def enforce(self, request: Optional[Request] = None) -> RBACContext:
        prod_id: Optional[str] = None
        if request is not None and self.production_id_param:
            prod_id = (
                request.path_params.get(self.production_id_param)
                or request.query_params.get(self.production_id_param)
            )

        rbac = extract_rbac_context(
            request=request,
            production_id=prod_id,
            enforce_counsel_verification=False,
        )

        # Admin bypass check
        if self.admin_bypass and LienmarkRole.ADMIN in rbac.roles:
            return rbac

        has_access = (
            rbac.has_all_permissions(*self.required_permissions)
            if self.require_all
            else rbac.has_any_permission(*self.required_permissions)
        )

        if not has_access:
            req_str = [p.value for p in self.required_permissions]
            grant_str = [p.value for p in rbac.permissions]
            mode = "all" if self.require_all else "any"
            reason = (
                f"Principal lacks {mode} of required permission(s): {req_str}. "
                f"Granted permissions count: {len(grant_str)}"
            )
            log_rbac_violation(request, rbac, req_str, "permission", reason)

            raise RBACAccessDeniedException(
                message=f"Access denied: Principal lacks required permission(s): {', '.join(req_str)}.",
                required=req_str,
                granted=grant_str,
                check_type="permission",
            )

        return rbac


# Dependency helpers
def get_rbac_context(request: Request) -> RBACContext:
    """FastAPI route dependency resolving verified RBACContext without role enforcement."""
    return extract_rbac_context(request=request)


# =============================================================================
# 8. Route Decorators: @require_role & @require_permission
# =============================================================================

def require_role(
    *roles: Union[LienmarkRole, str, Iterable[Union[LienmarkRole, str]]],
    require_all: bool = False,
    admin_bypass: bool = True,
    production_id_param: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Route decorator enforcing role authorization on both sync and async endpoints.
    Preserves route docstrings, annotations, reflection signatures, and metadata.

    Usage:
        @app.post("/api/admin/system-reset")
        @require_role(LienmarkRole.ADMIN)
        def reset_system(): ...

        @app.post("/api/counsel/override")
        @require_role(LienmarkRole.REVIEWER)
        async def override_claim(request: Request, claim_id: str): ...
    """
    checker = RequireRole(
        *roles,
        require_all=require_all,
        admin_bypass=admin_bypass,
        production_id_param=production_id_param,
    )

    def decorator(func: F) -> F:
        orig_sig = inspect.signature(func)
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                req = _find_request(*args, **kwargs)
                checker.enforce(req)
                return await func(*args, **kwargs)

            async_wrapper.__signature__ = orig_sig  # type: ignore[attr-defined]
            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                req = _find_request(*args, **kwargs)
                checker.enforce(req)
                return func(*args, **kwargs)

            sync_wrapper.__signature__ = orig_sig  # type: ignore[attr-defined]
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def require_permission(
    *permissions: Union[LienmarkPermission, str, Iterable[Union[LienmarkPermission, str]]],
    require_all: bool = True,
    admin_bypass: bool = True,
    production_id_param: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Route decorator enforcing fine-grained permission authorization on sync and async endpoints.
    Preserves route docstrings, annotations, reflection signatures, and metadata.

    Usage:
        @app.post("/api/claims/{claim_id}/approve")
        @require_permission(LienmarkPermission.CLAIM_APPROVE)
        async def approve_claim(request: Request, claim_id: str): ...
    """
    checker = RequirePermission(
        *permissions,
        require_all=require_all,
        admin_bypass=admin_bypass,
        production_id_param=production_id_param,
    )

    def decorator(func: F) -> F:
        orig_sig = inspect.signature(func)
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                req = _find_request(*args, **kwargs)
                checker.enforce(req)
                return await func(*args, **kwargs)

            async_wrapper.__signature__ = orig_sig  # type: ignore[attr-defined]
            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                req = _find_request(*args, **kwargs)
                checker.enforce(req)
                return func(*args, **kwargs)

            sync_wrapper.__signature__ = orig_sig  # type: ignore[attr-defined]
            return sync_wrapper  # type: ignore[return-value]

    return decorator
