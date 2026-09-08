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
from pydantic import BaseModel
from typing import Optional

from backend.storage.invite_store import get_invite_store
from backend.storage.session_store import get_session_store, SessionRecord

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE_NAME = "lienmark_session"
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "lienmark-session-secret-salt-2026")


def sign_session_id(session_id: str) -> str:
    sig = hashlib.sha256(f"{session_id}::{SESSION_SECRET_KEY}".encode("utf-8")).hexdigest()[:16]
    return f"{session_id}.{sig}"


def verify_session_cookie(cookie_val: Optional[str]) -> Optional[str]:
    if not cookie_val or not isinstance(cookie_val, str):
        return None
    val = cookie_val.strip()
    if "." not in val:
        return None
    parts = val.split(".", 1)
    sess_id, sig = parts[0], parts[1]
    expected_sig = hashlib.sha256(f"{sess_id}::{SESSION_SECRET_KEY}".encode("utf-8")).hexdigest()[:16]
    if hmac.compare_digest(sig, expected_sig):
        return sess_id
    return None


class RedeemInviteRequest(BaseModel):
    invite_token: str


class SessionInfo(BaseModel):
    display_name: str
    email: str
    role: str
    tenant_id: str
    production_id: str


@router.post("/redeem-invite")
async def redeem_invite(req: RedeemInviteRequest, response: Response):
    invite_store = get_invite_store()
    session_store = get_session_store()

    hashed_token = hashlib.sha256(req.invite_token.encode("utf-8")).hexdigest()
    invite_data = invite_store.consume_invite(hashed_token)
    if not invite_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already used invite token.",
        )

    session_id = f"sess_{secrets.token_urlsafe(32)}"
    expires_at = time.time() + 86400

    record = SessionRecord(
        session_id=session_id,
        user_id=f"user_{session_id[:12]}",
        email=invite_data.get("email", f"{invite_data['role'].lower()}@demo.lienmark.internal"),
        display_name=invite_data.get("display_name", f"Demo {invite_data['role'].capitalize()}"),
        role=invite_data["role"],
        tenant_id=invite_data["tenant_id"],
        production_id=invite_data["production_id"],
        expires_at=expires_at,
        revoked=False,
    )
    session_store.create_session(record)

    signed_cookie = sign_session_id(session_id)
    is_secure = os.getenv("ENVIRONMENT", "").lower() in ("production", "demo") or bool(os.getenv("K_SERVICE"))

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_cookie,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=86400,
        path="/",
    )
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
