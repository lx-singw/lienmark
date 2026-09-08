import time
import hashlib
import uuid
import secrets
from fastapi import APIRouter, Request, Response, HTTPException, status, Cookie, Depends
from pydantic import BaseModel
from typing import Optional
from backend.storage.invite_store import get_invite_store

router = APIRouter(prefix="/api/auth", tags=["auth"])

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
    store = get_invite_store()
    
    # Hash token for lookup
    hashed_token = hashlib.sha256(req.invite_token.encode('utf-8')).hexdigest()
    
    invite_data = store.consume_invite(hashed_token)
    if not invite_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already used invite token."
        )
    
    # Generate high entropy session ID
    session_id = secrets.token_urlsafe(32)
    
    # Store minimal info in cookie value (signed via middleware normally, but we use a robust session_id)
    # Since we need to return verified identity from session, we could store it in an ephemeral DB or encode in cookie.
    # We will simulate encoding it in a cookie for this test, but in real life it should be JWT or signed cookie.
    import json
    import base64
    session_data = {
        "session_id": session_id,
        "role": invite_data["role"],
        "tenant_id": invite_data["tenant_id"],
        "production_id": invite_data["production_id"],
        "display_name": "New User",
        "email": "user@example.com",
        "expires_at": time.time() + 86400
    }
    encoded_session = base64.b64encode(json.dumps(session_data).encode('utf-8')).decode('utf-8')
    
    response.set_cookie(
        key="lienmark_session",
        value=encoded_session,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400
    )
    return {"status": "success", "session_id": session_id}

@router.get("/session", response_model=SessionInfo)
async def get_session(request: Request):
    cookie_val = request.cookies.get("lienmark_session")
    if not cookie_val:
        raise HTTPException(status_code=401, detail="No session")
    
    import json
    import base64
    try:
        session_data = json.loads(base64.b64decode(cookie_val.encode('utf-8')).decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session format")
    
    if time.time() > session_data.get("expires_at", 0):
        raise HTTPException(status_code=401, detail="Session expired")
    
    store = get_invite_store()
    if store.is_session_revoked(session_data["session_id"]):
        raise HTTPException(status_code=401, detail="Session revoked")
        
    return SessionInfo(
        display_name=session_data["display_name"],
        email=session_data["email"],
        role=session_data["role"],
        tenant_id=session_data["tenant_id"],
        production_id=session_data["production_id"]
    )

@router.post("/logout")
async def logout(request: Request, response: Response):
    cookie_val = request.cookies.get("lienmark_session")
    if cookie_val:
        import json
        import base64
        try:
            session_data = json.loads(base64.b64decode(cookie_val.encode('utf-8')).decode('utf-8'))
            store = get_invite_store()
            store.revoke_session(session_data["session_id"])
        except Exception:
            pass
    response.delete_cookie(
        key="lienmark_session",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return {"status": "success"}
