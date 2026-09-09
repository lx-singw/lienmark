import io
import json
import re
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.middleware.tenant import TenantContext, get_tenant_context
from .models import DecisionInput, RevisionInput, AutomationPolicy, SourceInput
from .service import current, decide, public_job, scope, submit
from .store import Conflict, get_store

router = APIRouter(prefix="/api/clearance", tags=["Live clearance"])


@router.put("/productions/{production_id}/automation")
def configure_automation(production_id: str, payload: AutomationPolicy,
                         ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    from .automation import save_policy
    return operation(lambda: save_policy(store, scope(ctx, production_id), payload, ctx.user_id))


@router.post("/productions/{production_id}/documents", status_code=202)
async def upload_document(production_id: str, request: Request, name: str, kind: str = "revision", clarification_id: str | None = None,
                          ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    from .automation import decode_document, ingest
    root = scope(ctx, production_id)
    if kind not in ("revision", "agreement") or len(name) > 200:
        raise HTTPException(422, "Supply a revision or agreement document with a valid filename.")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 4_000_000:
            raise HTTPException(413, "Documents must be smaller than 4 MB.")
    text = operation(lambda: decode_document(name, bytes(raw)))
    try:
        source = SourceInput(kind=kind, name=name, text=text, clarification_id=clarification_id)
    except ValueError:
        raise HTTPException(422, "Invalid document or clarification reference.") from None
    return operation(lambda: ingest(store, root, source, ctx.user_id))


@router.get("/productions/{production_id}/documents/{event_id}")
def read_document(production_id: str, event_id: str, ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    root = scope(ctx, production_id)
    event = store.get(f"{root}/live_sources/{valid_id(event_id)}")
    if not event or event.get("kind") not in ("revision", "agreement"):
        raise HTTPException(404, "Document not found.")
    return Response(event.get("text", ""), media_type="text/plain", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/productions/{production_id}/documents/{event_id}/assign", status_code=202)
def assign_document(production_id: str, event_id: str, clarification_id: str,
                    ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    from .automation import record_event
    root = scope(ctx, production_id)
    def commit(tx):
        event_path = f"{root}/live_sources/{valid_id(event_id)}"
        event = tx.get(event_path)
        question = tx.get(f"{root}/live_clarifications/{valid_id(clarification_id)}")
        if not event or event.get("kind") != "agreement" or event["status"] != "WAITING_FOR_MATCH":
            raise Conflict("This document is not awaiting assignment.")
        if not question or question["status"] != "PENDING":
            raise Conflict("The clarification is no longer open.")
        source = SourceInput(kind="agreement", name=event["name"], text=event["text"], source_uri=event["source_uri"], clarification_id=clarification_id)
        result = record_event(tx, root, source, ctx.user_id, f"assign:{event_id}:{clarification_id}")
        tx.put(event_path, {**event, "status": "ASSIGNED", "assigned_by": ctx.user_id})
        return result
    return operation(lambda: store.atomic(commit))


def valid_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise HTTPException(422, "Invalid record identifier.")
    return value


def operation(callback):
    try:
        return callback()
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/productions/{production_id}")
def workspace(production_id: str, ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    return current(store, scope(ctx, production_id))


@router.post("/revisions", status_code=202)
def revision(payload: RevisionInput, request: Request, ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    root = scope(ctx, payload.production_id)
    return operation(lambda: submit(store, root, payload, ctx.user_id, request.headers.get("Idempotency-Key")))


@router.get("/productions/{production_id}/audits/{audit_id}")
def audit(production_id: str, audit_id: str, ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    root = scope(ctx, production_id)
    job = store.get(f"{root}/live_jobs/{valid_id(audit_id)}")
    if not job:
        raise HTTPException(404, "Audit not found.")
    result = public_job(job)
    if job.get("snapshot_path"):
        result["snapshot"] = store.get(job["snapshot_path"])
    return result


@router.post("/productions/{production_id}/claims/{claim_id}/decision")
def decision(production_id: str, claim_id: str, payload: DecisionInput,
             ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    root = scope(ctx, production_id, reviewer=True)
    return operation(lambda: decide(store, root, valid_id(claim_id), payload, ctx.user_id))


def read_snapshot(store, root, revision_id, snapshot_id):
    snapshot = store.get(f"{root}/live_revisions/{valid_id(revision_id)}/snapshots/{valid_id(snapshot_id)}")
    if not snapshot:
        raise HTTPException(404, "Snapshot not found.")
    return snapshot


@router.get("/productions/{production_id}/revisions/{revision_id}/snapshots/{snapshot_id}")
def snapshot(production_id: str, revision_id: str, snapshot_id: str,
             ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    return read_snapshot(store, scope(ctx, production_id), revision_id, snapshot_id)


@router.get("/productions/{production_id}/revisions/{revision_id}/snapshots/{snapshot_id}/execution-record")
def execution_record(production_id: str, revision_id: str, snapshot_id: str,
                     ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    from .models import digest, now
    root = scope(ctx, production_id)
    data = read_snapshot(store, root, revision_id, snapshot_id)
    job = store.get(f"{root}/live_jobs/{valid_id(data['audit_id'])}")
    if not job or job['revision_id'] != revision_id:
        raise HTTPException(409, "The snapshot's execution record is unavailable.")
    body = {"format": "lienmark-execution-record-v1", "exported_at": now(), "snapshot": data,
        "execution": public_job(job), "limitations": ["This record contains production evidence; review before sharing.",
            "Dispatch reservations are not reconciled billing.", "An ADK trace proves local SDK execution, not a managed cloud deployment.",
            "Reviewer decisions are recorded actions, not underwriter acceptance."]}
    body['record_sha256'] = digest(body)
    return Response(json.dumps(body, indent=2), media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="clearance-execution-record.json"',
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/productions/{production_id}/revisions/{revision_id}/snapshots/{snapshot_id}/pdf")
def export(production_id: str, revision_id: str, snapshot_id: str,
           ctx: TenantContext = Depends(get_tenant_context), store=Depends(get_store)):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    data = read_snapshot(store, scope(ctx, production_id), revision_id, snapshot_id)
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []
    def paragraph(text, style="BodyText"):
        story.append(Paragraph(escape(str(text)), styles[style]))
        gap = Spacer(1, 8)
        gap.keepWithNext = style.startswith('Heading') or style == 'Title'
        story.append(gap)
    paragraph("Draft Exceptions Schedule", "Title")
    for text in (data.get("production_name", "Production workspace"), "Prepared: " + data["created_at"], revision_id, snapshot_id, "Snapshot SHA-256: " + data["content_sha256"],
                 "This draft records the decisions and unresolved matters in this snapshot. It is not an insurance certificate."):
        paragraph(text)
    comparison = data.get("comparison", {})
    if comparison.get("baseline_snapshot_id"):
        paragraph("Change and delivery summary", "Heading2")
        paragraph(f"Baseline approvals: {comparison['approvals_before']} | Approvals preserved: {sum(c['state'] == 'carried_forward' for c in data['claims'])}")
        paragraph(f"Blockers before: {comparison['blockers_before']} | Blockers in this snapshot: {sum(c['state'] not in ('carried_forward', 're_attested', 'removed') for c in data['claims'])}")
        paragraph(f"Missing facts resolved during investigation: {comparison['missing_facts_resolved']} | Elapsed seconds: {comparison['elapsed_seconds']}")
    for claim in data["claims"]:
        story.append(KeepTogether([Paragraph(escape(claim["description"]), styles['Heading2']), Spacer(1, 8),
            Paragraph(escape(f'{claim["scene"]} | {claim["prominence"]} | {claim["state"]}'), styles['BodyText']), Spacer(1, 8)]))
        paragraph(claim["reason_code"])
        for missing in (claim.get("investigation") or {}).get("missing_facts", []):
            label = "Research question recorded before reviewer decision: " if claim.get("decision") else "Unresolved: "
            paragraph(label + missing)
        decision = claim.get("decision")
        if decision:
            paragraph(f'Reviewer: {decision["actor_id"]} | Recorded: {decision["created_at"]}')
            paragraph("Decision basis: " + decision["basis_snapshot_id"])
        for evidence in claim["evidence_citations"]:
            paragraph(f'{evidence["evidence_id"]}: {evidence["title"]} - {evidence["url"]}')
            paragraph("Retrieved: " + evidence["retrieved_at"] + " | Response SHA-256: " + evidence["response_sha256"])
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorRGB(.3, .4, .37)
        canvas.drawString(document.leftMargin, 32, 'Lienmark | Draft for authorized review')
        canvas.drawRightString(document.pagesize[0] - document.rightMargin, 32, f'Page {document.page}')
        canvas.restoreState()
    SimpleDocTemplate(output, title="Lienmark Draft Exceptions Schedule").build(story, onFirstPage=footer, onLaterPages=footer)
    return Response(output.getvalue(), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="lienmark-{snapshot_id}.pdf"',
        "X-Snapshot-SHA256": data["content_sha256"], "Cache-Control": "private, no-store"})
