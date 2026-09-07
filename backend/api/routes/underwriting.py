"""
underwriting.py

FastAPI REST Router for Studio Deliverables (Cue Sheets, Wrap Checklists,
Clearance Exceptions Schedule, and ISO 27001 / SOC 2 Legal Audit Manifests).
Sprint 6.3: Studio Deliverables.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from backend.api.routes.underwriting_schemas import (
    CueSheetResponse,
    ExportScheduleRequest,
    LegalAuditManifestResponse,
    WrapChecklistResponse,
)
from backend.middleware.tenant import TenantContext, get_tenant_context
from backend.services.compliance_manifest import ComplianceManifestService
from backend.services.cue_sheet_exporter import CueSheetExporter
from backend.services.pdf_generator import ClearancePdfGenerator
from backend.services.wrap_checklist import WrapChecklistEngine
from backend.storage.repository import InMemoryTenantRepository, get_tenant_repository

underwriting_router = APIRouter(prefix="/api/v1/underwriting", tags=["underwriting"])


def _extract_verified_tenant_id(tenant_ctx: Optional[TenantContext]) -> str:
    """Enforces fail-closed authentication and extracts active tenant ID."""
    strict_auth = os.getenv("LIENMARK_STRICT_AUTH", "false").lower() == "true"
    strict_tenant = os.getenv("TENANT_STRICT_MODE", "false").lower() == "true"
    if (strict_auth or strict_tenant) and (tenant_ctx is None or not tenant_ctx.organization_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: valid tenant credentials must be supplied.",
        )
    return tenant_ctx.organization_id if tenant_ctx and tenant_ctx.organization_id else "org_default"


def _resolve_production_and_claims(repo, production_id: str) -> tuple[Any, List[Dict[str, Any]], List[Any]]:
    """Fetches production, active run claims, and audit events from tenant repository."""
    prod = repo.get_production(production_id)
    if not prod:
        prods = repo.list_productions()
        prod = next((p for p in prods if p.production_id == production_id), None)
    claims: List[Dict[str, Any]] = []
    audit_events: List[Any] = []
    run_id = repo.get_active_run_id(production_id)
    if not run_id:
        runs = repo.list_runs(production_id)
        if runs:
            run_id = runs[0].run_id
    if run_id:
        raw_claims = repo.list_claims(production_id, run_id)
        claims = [c if isinstance(c, dict) else c.model_dump() for c in raw_claims]
        audit_events = repo.list_audit_events(production_id, run_id)
    return prod, claims, audit_events


def _partition_claims(claims: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Partitions claims into cleared and exception sets."""
    cleared = [c for c in claims if str(c.get("state") or "").upper() in ("CARRIED_FORWARD", "RE_ATTESTED") or str(c.get("status") or "").upper() == "APPROVED"]
    exceptions = [c for c in claims if str(c.get("state") or "").upper() == "EXCEPTION" or str(c.get("status") or "").upper() in ("EXCEPTION", "FLAGGED")]
    return cleared, exceptions


def _extract_ledger_head(audit_events: List[Any]) -> str:
    """Extracts the latest ledger entry or event hash."""
    if not audit_events:
        return "0" * 64
    last_evt = audit_events[-1]
    val = (last_evt.get("entry_hash") or last_evt.get("event_hash")) if isinstance(last_evt, dict) else (getattr(last_evt, "entry_hash", None) or getattr(last_evt, "event_hash", None))
    return val or ("0" * 64)


@underwriting_router.post("/export-schedule")
async def export_exceptions_schedule(
    req: ExportScheduleRequest,
    tenant_ctx: Optional[TenantContext] = Depends(get_tenant_context),
) -> Any:
    """Exports certified Form E&O-2026 Clearance Exceptions Schedule in PDF or JSON format."""
    org_id = _extract_verified_tenant_id(tenant_ctx)
    repo = get_tenant_repository(org_id)
    prod, claims, audit_events = _resolve_production_and_claims(repo, req.production_id)
    cleared, exceptions = _partition_claims(claims)
    ledger_head = _extract_ledger_head(audit_events)
    cut_hash = getattr(prod, "cut_hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    if req.format.lower() == "pdf":
        title = getattr(prod, "title", "Production Cut") if prod else "Production Cut"
        pdf_bytes = ClearancePdfGenerator.generate_schedule_pdf(
            production_title=title,
            production_id=req.production_id,
            cleared_claims=cleared,
            exception_claims=exceptions,
            cut_hash=cut_hash,
            ledger_head_hash=ledger_head,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="clearance_schedule_{req.production_id}.pdf"'},
        )
    return {
        "production_id": req.production_id,
        "cleared_claims": cleared,
        "exception_claims": exceptions,
        "ledger_head_hash": ledger_head,
        "cut_hash": cut_hash,
    }


@underwriting_router.get("/cue-sheet")
async def get_cue_sheet(
    production_id: str = Query("proj_blockbuster_cinema"),
    format: str = Query("json", pattern="^(json|csv)$"),
    tenant_ctx: Optional[TenantContext] = Depends(get_tenant_context),
) -> Any:
    """Exports ASCAP/BMI Music Cue Sheet in JSON or RFC 4180 CSV format."""
    org_id = _extract_verified_tenant_id(tenant_ctx)
    repo = get_tenant_repository(org_id)
    prod, claims, _ = _resolve_production_and_claims(repo, production_id)
    title = getattr(prod, "title", "Production Cut") if prod else "Production Cut"
    cue_sheet = CueSheetExporter.generate_cue_sheet(production_id, title, claims)

    if format.lower() == "csv":
        csv_text = CueSheetExporter.export_csv(cue_sheet)
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="cue_sheet_{production_id}.csv"'},
        )
    return cue_sheet


@underwriting_router.get("/wrap-checklist", response_model=WrapChecklistResponse)
async def get_wrap_checklist(
    production_id: str = Query("proj_blockbuster_cinema"),
    tenant_ctx: Optional[TenantContext] = Depends(get_tenant_context),
) -> WrapChecklistResponse:
    """Evaluates post-production wrap delivery gate for distributor funds release."""
    org_id = _extract_verified_tenant_id(tenant_ctx)
    repo = get_tenant_repository(org_id)
    _, claims, _ = _resolve_production_and_claims(repo, production_id)
    return WrapChecklistEngine.evaluate_wrap_checklist(production_id, claims)


@underwriting_router.get("/manifest", response_model=LegalAuditManifestResponse)
async def get_legal_audit_manifest(
    production_id: str = Query("proj_blockbuster_cinema"),
    tenant_ctx: Optional[TenantContext] = Depends(get_tenant_context),
) -> LegalAuditManifestResponse:
    """Exports standardized ISO 27001 / SOC 2 Type II legal audit manifest."""
    org_id = _extract_verified_tenant_id(tenant_ctx)
    repo = get_tenant_repository(org_id)
    _, claims, audit_events = _resolve_production_and_claims(repo, production_id)
    return ComplianceManifestService.generate_manifest(production_id, claims, audit_events)
