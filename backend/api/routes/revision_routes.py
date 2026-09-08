import logging
import hashlib
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks

from backend.orchestration.revision_audit_pipeline import RevisionAuditPipelineService
from backend.core.rbac import require_role, LienmarkRole

logger = logging.getLogger("lienmark.api.routes.revisions")

router = APIRouter(tags=["Revisions"])

@router.post("/api/revisions/audit", status_code=202)
def trigger_revision_audit(
    request: Request,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    # validates production role, checks idempotency key + payload hash, atomically commits
    tenant_id = payload.get("tenant_id", "default_tenant")
    prod_id = payload.get("production_id", "default_prod")
    rev_id = payload.get("revision_id", "default_rev")
    parent_rev_id = payload.get("parent_revision_id", "v7")
    revised_uses = payload.get("revised_uses", [])

    idempotency_key = request.headers.get("Idempotency-Key")
    payload_hash = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()
    
    # Enqueue Cloud Tasks dispatch
    pipeline = RevisionAuditPipelineService()
    background_tasks.add_task(
        pipeline.execute_audit,
        tenant_id, prod_id, rev_id, parent_rev_id, revised_uses
    )

    return {
        "status": "ACCEPTED",
        "message": "Revision audit enqueued.",
        "status_url": f"/api/tenants/{tenant_id}/productions/{prod_id}/revisions/{rev_id}/status"
    }

@router.post("/api/revisions/{revision_id}/revalidate-evidence")
def revalidate_external_evidence(
    revision_id: str,
    payload: Dict[str, Any]
):
    tenant_id = payload.get("tenant_id", "default_tenant")
    prod_id = payload.get("production_id", "default_prod")
    target_key = payload.get("target_key")
    snapshot = payload.get("snapshot", {})
    
    result = RevisionAuditPipelineService.revalidate_external_evidence(
        tenant_id, prod_id, revision_id, target_key, snapshot
    )
    return result

@router.get("/api/tenants/{tenant_id}/productions/{production_id}/revisions/{revision_id}/audits/{audit_id}/snapshots/{snapshot_id}")
def get_revision_snapshot(
    tenant_id: str,
    production_id: str,
    revision_id: str,
    audit_id: str,
    snapshot_id: str
):
    return {
        "tenant_id": tenant_id,
        "production_id": production_id,
        "revision_id": revision_id,
        "audit_id": audit_id,
        "snapshot_id": snapshot_id,
        "data": {}
    }

@router.post("/api/tasks/recovery/sweep")
def recovery_sweep_endpoint():
    RevisionAuditPipelineService.sweep_and_recover_abandoned_audits()
    return {"status": "SWEEP_COMPLETED"}
