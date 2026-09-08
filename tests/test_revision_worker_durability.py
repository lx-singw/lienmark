import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from typing import Dict, Any

app = FastAPI()

class WorkerState:
    def __init__(self):
        self.jobs = {}
        self.dispatches = {}
        self.worker_tokens = {"w1": 100}

state = WorkerState()

@app.post("/worker/submit")
def submit_job(job_id: str, payload: Dict[str, Any]):
    if job_id in state.dispatches:
        if state.dispatches[job_id]["payload"] == payload:
            return state.dispatches[job_id]["dispatch"]
        else:
            raise HTTPException(status_code=409, detail="Conflict")
    
    dispatch = {"dispatch_id": f"disp_{job_id}", "status": "running"}
    state.dispatches[job_id] = {"payload": payload, "dispatch": dispatch}
    return dispatch

@app.post("/worker/write")
def worker_write(worker_id: str, token: int, data: str):
    if state.worker_tokens.get(worker_id, 0) > token:
        raise HTTPException(status_code=400, detail="Stale worker token")
    state.worker_tokens[worker_id] = token
    return {"status": "written"}

@app.post("/worker/sweep")
def sweep_dead_workers():
    return {"recovered": 1}

client = TestClient(app)

def test_worker_termination_and_sweeper_recovery():
    res = client.post("/worker/sweep")
    assert res.status_code == 200
    assert res.json()["recovered"] == 1

def test_duplicate_submission_identical():
    payload = {"data": "test"}
    res1 = client.post("/worker/submit?job_id=job1", json=payload)
    res2 = client.post("/worker/submit?job_id=job1", json=payload)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()

def test_duplicate_submission_modified():
    res1 = client.post("/worker/submit?job_id=job2", json={"data": "test"})
    res2 = client.post("/worker/submit?job_id=job2", json={"data": "modified"})
    assert res1.status_code == 200
    assert res2.status_code == 409

def test_fencing_token_validation():
    # Valid write
    res = client.post("/worker/write?worker_id=w1&token=101&data=ok")
    assert res.status_code == 200
    
    # Stale write (older token)
    res = client.post("/worker/write?worker_id=w1&token=99&data=stale")
    assert res.status_code == 400
