"""
backend/api/routes/auth_routes.py

Authentication endpoints for invited evaluators.
Issues cryptographically signed opaque session cookies backed by server-side SessionStore.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import time
import hashlib
import secrets
import hmac
import os
from fastapi import APIRouter, Request, Response, HTTPException, status
from pydantic import BaseModel, model_validator
from typing import Optional

from backend.storage.invite_store import get_invite_store
from backend.storage.session_store import get_session_store, SessionRecord

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE_NAME = "lienmark_session"
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "lienmark-session-secret-salt-2026")


def compute_signature(session_id: str) -> str:
    """Generates an HMAC-SHA256 signature prefix for the session identifier."""
    return hmac.new(
        SESSION_SECRET_KEY.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]


def sign_session_id(session_id: str) -> str:
    """Signs a session ID using HMAC-SHA256."""
    sig = compute_signature(session_id)
    return f"{session_id}.{sig}"


def verify_session_cookie(cookie_val: Optional[str]) -> Optional[str]:
    """Validates session cookie signature with constant-time comparison."""
    if not cookie_val or not isinstance(cookie_val, str):
        return None
    val = cookie_val.strip()
    if "." not in val:
        return None
    parts = val.split(".", 1)
    sess_id, sig = parts[0], parts[1]
    expected_hmac = compute_signature(sess_id)
    expected_legacy = hashlib.sha256(
        f"{sess_id}::{SESSION_SECRET_KEY}".encode("utf-8")
    ).hexdigest()[:16]
    if hmac.compare_digest(sig, expected_hmac) or hmac.compare_digest(sig, expected_legacy):
        return sess_id
    return None


class RedeemInviteRequest(BaseModel):
    invite_token: Optional[str] = None
    token: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_token_inputs(cls, data: object) -> object:
        if isinstance(data, dict):
            resolved = data.get("invite_token") or data.get("token")
            if resolved is not None:
                token_str = str(resolved).strip()
                data["invite_token"] = token_str
                data["token"] = token_str
        return data

    @model_validator(mode="after")
    def validate_and_resolve_token(self) -> "RedeemInviteRequest":
        token_val = self.invite_token or self.token
        if not token_val or not token_val.strip():
            raise ValueError("Either 'invite_token' or 'token' must be provided.")
        resolved = token_val.strip()
        self.invite_token = resolved
        self.token = resolved
        return self

    @property
    def token_to_consume(self) -> str:
        return (self.invite_token or self.token or "").strip()

    @property
    def resolved_token(self) -> str:
        return self.token_to_consume


class SessionInfo(BaseModel):
    display_name: str
    email: str
    role: str
    tenant_id: str
    production_id: str


def _build_session_record(
    session_id: str,
    invite_data: dict[str, object],
    expires_at: float,
) -> SessionRecord:
    role_str = str(invite_data.get("role", "reviewer"))
    tenant_str = str(invite_data.get("tenant_id", "default_tenant"))
    prod_str = str(invite_data.get("production_id", "default_prod"))
    email_default = f"{role_str.lower()}@demo.lienmark.internal"
    name_default = f"Demo {role_str.capitalize()}"
    return SessionRecord(
        session_id=session_id,
        user_id=f"user_{session_id[:12]}",
        email=str(invite_data.get("email") or email_default),
        display_name=str(invite_data.get("display_name") or name_default),
        role=role_str,
        tenant_id=tenant_str,
        production_id=prod_str,
        expires_at=expires_at,
        revoked=False,
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    signed_cookie = sign_session_id(session_id)
    is_secure = (
        os.getenv("ENVIRONMENT", "").lower() in ("production", "demo")
        or bool(os.getenv("K_SERVICE"))
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_cookie,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=86400,
        path="/",
    )


@router.post("/redeem-invite")
async def redeem_invite(req: RedeemInviteRequest, response: Response):
    invite_store = get_invite_store()
    session_store = get_session_store()

    token_val = req.token_to_consume
    hashed_token = hashlib.sha256(token_val.encode("utf-8")).hexdigest()
    invite_data = invite_store.consume_invite(hashed_token)
    if not invite_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already used invite token.",
        )

    session_id = f"sess_{secrets.token_urlsafe(32)}"
    record = _build_session_record(session_id, invite_data, time.time() + 86400)
    session_store.create_session(record)

    _set_session_cookie(response, session_id)
    return {"status": "success", "session_id": session_id, "role": record.role}


@router.get("/session", response_model=SessionInfo)
async def get_session(request: Request):
    cookie_val = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = verify_session_cookie(cookie_val)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or tampered session cookie.")

    session_store = get_session_store()
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked.")

    return SessionInfo(
        display_name=session.display_name,
        email=session.email,
        role=session.role,
        tenant_id=session.tenant_id,
        production_id=session.production_id,
    )


@router.post("/logout")
@router.post("/signout")
async def logout(request: Request, response: Response):
    cookie_val = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = verify_session_cookie(cookie_val)
    if session_id:
        session_store = get_session_store()
        session_store.revoke_session(session_id)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"status": "success"}
