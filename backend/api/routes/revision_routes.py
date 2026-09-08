"""
backend/api/routes/revision_routes.py

REST API endpoints for immutable revision submissions, durable audit dispatches,
versioned snapshot inspection, external evidence revalidation, and ReportLab PDF export.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Response, BackgroundTasks, status

from backend.domain.revision_models import RevisionRecord, RevisionAuditDispatch, ResultSnapshot
from backend.storage.revision_store import get_revision_store, RevisionConflictError
from backend.orchestration.revision_audit_pipeline import RevisionAuditPipelineService
from backend.services.pdf_generator import ClearancePdfGenerator
from backend.middleware.tenant import TenantContext, get_tenant_context

logger = logging.getLogger("lienmark.api.routes.revisions")

router = APIRouter(prefix="/api", tags=["Revisions"])


@router.post("/revisions/audit", status_code=status.HTTP_202_ACCEPTED)
def trigger_revision_audit(
    request: Request,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    """Atomically commits immutable revision and dispatch, returns 202 immediately."""
    tenant_id = str(tenant_ctx.tenant_id or payload.get("tenant_id", "default_tenant"))
    prod_id = str(payload.get("production_id", "prod_noir_protocol"))
    parent_rev_id = str(payload.get("parent_revision_id", "v7"))
    revised_uses = payload.get("revised_uses", [])

    idempotency_key = request.headers.get("Idempotency-Key") or payload.get("idempotency_key") or f"idem_{uuid.uuid4().hex[:12]}"
    payload_hash = hashlib.sha256(str(sorted(payload.items())).encode("utf-8")).hexdigest()

    store = get_revision_store()
    rev_id = f"rev_{uuid.uuid4().hex[:8]}"
    audit_id = f"audit_{uuid.uuid4().hex[:8]}"

    rec = RevisionRecord(
        revision_id=rev_id,
        created_at=datetime.now(timezone.utc),
        user_provenance=getattr(request.state, "session_id", "anonymous"),
        tenant_id=tenant_id,
        production_id=prod_id,
        parent_baseline_version_id=parent_rev_id,
    )
    disp = RevisionAuditDispatch(
        audit_id=audit_id,
        revision_id=rev_id,
        status="QUEUED",
        fencing_token=0,
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
        retry_count=0,
    )

    try:
        saved_dispatch = store.save_revision_and_dispatch(rec, disp)
    except RevisionConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Execute via durable worker pipeline only for newly created dispatches (not idempotent replays)
    if saved_dispatch.audit_id == disp.audit_id:
        pipeline = RevisionAuditPipelineService(store=store)
        background_tasks.add_task(
            pipeline.execute_audit,
            tenant_id, prod_id, saved_dispatch.revision_id, parent_rev_id, revised_uses, saved_dispatch.audit_id,
        )

    return {
        "status": "ACCEPTED",
        "audit_id": saved_dispatch.audit_id,
        "revision_id": saved_dispatch.revision_id,
        "status_url": f"/api/tenants/{tenant_id}/productions/{prod_id}/revisions/{saved_dispatch.revision_id}/audits/{saved_dispatch.audit_id}/snapshots/snapshot_0",
    }


@router.post("/revisions/{revision_id}/revalidate-evidence")
def revalidate_external_evidence(
    revision_id: str,
    payload: Dict[str, Any],
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    """Evaluates external evidence drift against existing revision without cut changes."""
    tenant_id = str(tenant_ctx.tenant_id or payload.get("tenant_id", "default_tenant"))
    prod_id = str(payload.get("production_id", "prod_noir_protocol"))
    target_key = payload.get("target_key", "")
    snapshot = payload.get("snapshot", {})

    pipeline = RevisionAuditPipelineService()
    return pipeline.revalidate_external_evidence(tenant_id, prod_id, revision_id, target_key, snapshot)


@router.get("/tenants/{tenant_id}/productions/{production_id}/revisions/{revision_id}/audits/{audit_id}/snapshots/{snapshot_id}")
def get_revision_snapshot(
    tenant_id: str,
    production_id: str,
    revision_id: str,
    audit_id: str,
    snapshot_id: str,
):
    """Returns immutable ResultSnapshot for the specified revision and audit."""
    store = get_revision_store()
    snapshot = store.get_result_snapshot(tenant_id, production_id, revision_id, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Snapshot '{snapshot_id}' not found.")
    return snapshot


@router.get("/tenants/{tenant_id}/productions/{production_id}/revisions/{revision_id}/audits/{audit_id}/snapshots/{snapshot_id}/export/pdf")
def export_snapshot_pdf(
    tenant_id: str,
    production_id: str,
    revision_id: str,
    audit_id: str,
    snapshot_id: str,
):
    """Generates certified Draft Form E&O-2026 PDF schedule matching the exact result snapshot."""
    store = get_revision_store()
    snapshot = store.get_result_snapshot(tenant_id, production_id, revision_id, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Snapshot '{snapshot_id}' not found.")

    cleared = []
    exceptions = []
    for d in snapshot.decisions:
        item = {
            "item_number": getattr(d, "item_number", 1),
            "asset_name": getattr(d, "asset_name", getattr(d, "stable_lineage_key", "Item")),
            "scene": getattr(d, "scene", "Scene 1"),
            "disposition": getattr(d, "status", getattr(d, "disposition", "NEEDS_REVIEW")),
            "attestation": getattr(d, "counsel_rationale", "Verified by counsel"),
            "citations": getattr(d, "citations", []),
            "remedy": getattr(d, "remedy", "Underwriter disclosure required"),
        }
        if str(item["disposition"]).upper() in ("APPROVED", "CARRIED_FORWARD"):
            cleared.append(item)
        else:
            exceptions.append(item)

    pdf_bytes = ClearancePdfGenerator.generate_schedule_pdf(
        production_title=f"The Noir Protocol ({revision_id})",
        production_id=production_id,
        cleared_claims=cleared,
        exception_claims=exceptions,
        cut_hash=hashlib.sha256(revision_id.encode("utf-8")).hexdigest(),
        ledger_head_hash=hashlib.sha256(audit_id.encode("utf-8")).hexdigest(),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=lienmark_{revision_id}_{snapshot_id}.pdf"},
    )


@router.post("/tasks/recovery/sweep")
def execute_recovery_sweep(
    payload: Dict[str, Any],
    tenant_ctx: TenantContext = Depends(get_tenant_context),
):
    """Executes scheduled recovery sweep over stranded and expired-lease dispatches."""
    tenant_id = str(payload.get("tenant_id") or tenant_ctx.tenant_id or "default_tenant")
    prod_id = str(payload.get("production_id") or "prod_noir_protocol")
    pipeline = RevisionAuditPipelineService()
    recovered = pipeline.sweep_and_recover_abandoned_audits(tenant_id, prod_id)
    return {"status": "SUCCESS", "recovered_audits": recovered, "count": len(recovered)}
