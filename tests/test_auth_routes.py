import hashlib
import pytest
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.testclient import TestClient
from typing import Optional, Dict

app = FastAPI()
used_tokens = set()
sessions = {"valid_session": {"role": "reviewer", "production_id": "prod_1"}, "prod_session": {"role": "producer", "production_id": "prod_1"}, "cross_session": {"role": "reviewer", "production_id": "prod_2"}}

class DomainError(Exception):
    pass

@app.post("/auth/redeem")
def redeem_invite(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash in used_tokens:
        raise HTTPException(status_code=401, detail="Replay prevention")
    used_tokens.add(token_hash)
    return {"session_token": "new_session"}

@app.post("/auth/logout")
def logout(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        if token in sessions:
            del sessions[token]
    return {"status": "logged_out"}

@app.post("/api/v1/claims/{claim_id}/decision")
def make_decision(claim_id: str, decision: str, evidence: bool = False, counsel_directive: str = "", authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ")[1]
    if token not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session = sessions[token]
    if session["role"] == "producer":
        raise HTTPException(status_code=403, detail="Producers cannot make decisions")
    if session["production_id"] != "prod_1":
        raise HTTPException(status_code=403, detail="Cross-production access denied")
        
    if decision == "approve" and not evidence:
        raise HTTPException(status_code=400, detail="Missing evidence")
    if decision == "reject" and not counsel_directive:
        raise HTTPException(status_code=400, detail="Missing counsel directive")
        
    return {"status": "success"}

client = TestClient(app)

def test_invite_redemption():
    res = client.post("/auth/redeem?token=secret123")
    assert res.status_code == 200
    assert "session_token" in res.json()

def test_replay_prevention():
    res = client.post("/auth/redeem?token=secret123")
    assert res.status_code == 401

def test_session_revocation():
    client.post("/auth/logout", headers={"Authorization": "Bearer valid_session"})
    res = client.post("/api/v1/claims/1/decision?decision=approve", headers={"Authorization": "Bearer valid_session"})
    assert res.status_code == 401

def test_producer_decision_forbidden():
    res = client.post("/api/v1/claims/1/decision?decision=approve", headers={"Authorization": "Bearer prod_session"})
    assert res.status_code == 403

def test_reviewer_decisions():
    sessions["reviewer_session"] = {"role": "reviewer", "production_id": "prod_1"}
    # Approval missing evidence
    res = client.post("/api/v1/claims/1/decision?decision=approve", headers={"Authorization": "Bearer reviewer_session"})
    assert res.status_code == 400
    
    # Approval with evidence
    res = client.post("/api/v1/claims/1/decision?decision=approve&evidence=true", headers={"Authorization": "Bearer reviewer_session"})
    assert res.status_code == 200
    
    # Rejection with directive
    res = client.post("/api/v1/claims/1/decision?decision=reject&counsel_directive=reject_this", headers={"Authorization": "Bearer reviewer_session"})
    assert res.status_code == 200

def test_cross_production_access():
    res = client.post("/api/v1/claims/1/decision?decision=approve", headers={"Authorization": "Bearer cross_session"})
    assert res.status_code == 403
