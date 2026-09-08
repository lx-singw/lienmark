import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

snapshots = {
    "snapshot_0": {"counts": 10, "citations": ["cite_1"], "provenance": "v0"},
}

@app.post("/adjudicate")
def adjudicate():
    # snapshot_0 remains immutable, create snapshot_1
    snapshots["snapshot_1"] = {"counts": 15, "citations": ["cite_1", "cite_2"], "provenance": "v1"}
    return {"status": "success", "new_snapshot": "snapshot_1"}

@app.get("/preview/{snapshot_id}")
def get_preview(snapshot_id: str):
    return snapshots.get(snapshot_id)

@app.get("/export/{snapshot_id}")
def get_export(snapshot_id: str):
    # Simulates exported PDF metadata extraction
    return snapshots.get(snapshot_id)

client = TestClient(app)

def test_adjudication_snapshot_immutability():
    # Initial state check
    assert "snapshot_1" not in snapshots
    initial = snapshots["snapshot_0"].copy()
    
    # Adjudicate
    res = client.post("/adjudicate")
    assert res.status_code == 200
    
    # Check snapshot_0 immutable
    assert snapshots["snapshot_0"] == initial
    
    # Check snapshot_1 created
    assert "snapshot_1" in snapshots
    assert snapshots["snapshot_1"]["counts"] == 15

def test_preview_export_parity():
    # In-app preview
    preview_res = client.get("/preview/snapshot_1")
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    
    # Exported PDF
    export_res = client.get("/export/snapshot_1")
    assert export_res.status_code == 200
    export_data = export_res.json()
    
    # Check parity
    assert preview_data["counts"] == export_data["counts"]
    assert preview_data["citations"] == export_data["citations"]
    assert preview_data["provenance"] == export_data["provenance"]
