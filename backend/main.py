"""
Lienmark FastAPI Application
Exposes REST API endpoints and an interactive Reviewer Dashboard for the 12 -> 10/2 demo.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body

logger = logging.getLogger("lienmark.api")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from backend.domain.models import (
    DecisionStatus,
    DecisionState,
    ReattestationRequest,
    ExceptionsSchedule,
    ReviewAction,
    DemoReviewer,
    FourDimensionalExplanation,
    ReviewQueue,
    ReviewQueueItem,
    SupersessionEvent,
    ReviewActionRequest,
    UnauthorizedApprovalError,
    FailClosedSecurityViolation,
)
from backend.core.counsel_checkpoint import (
    CounselCheckpointManager,
    counsel_checkpoint_manager,
)
from backend.orchestration.workflow import LienmarkWorkflow, WorkflowRunResult
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)

app = FastAPI(
    title="Lienmark Clearance Change Control API",
    description="Deterministic clearance drift detection and E&O underwriter change control.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory state for session review
_latest_run_result: Optional[WorkflowRunResult] = None
_counsel_reattestations: Dict[str, ReattestationRequest] = {}


@app.get("/health")
@app.get("/api/health")
def health_check():
    parallel_key = os.getenv("PARALLEL_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    return {
        "status": "healthy",
        "service": "Lienmark E&O Clearance Change Control",
        "provenance": "Google AntiGravity (Agentic Cinema Approved Toolchain)",
        "track": "Parallel Track ($15,000 Prize Pool)",
        "integrations": {
            "gemini": "configured" if gemini_key else "simulated_deterministic",
            "parallel_search": "configured" if parallel_key else "simulated_deterministic",
            "agent_platform": "Google Cloud Agent Builder / ADK",
        },
        "policy_version": InvalidationEngine.POLICY_VERSION,
    }


@app.get("/api/fixtures")
def get_fixtures():
    v7 = get_v7_version()
    v8 = get_v8_version()
    v7_uses, v8_uses, v7_decisions, _ = get_golden_fixtures()

    return {
        "v7_version": v7.model_dump(),
        "v8_version": v8.model_dump(),
        "v7_claims": [
            {
                "use_id": u.use_id,
                "key": u.stable_lineage_key,
                "scene": u.scene_or_timecode,
                "asset_type": u.asset_type,
                "description": u.description,
                "prominence": u.duration_or_prominence,
                "status": "APPROVED",
            }
            for u in v7_uses
        ],
    }


@app.post("/api/drift/compare")
@app.post("/api/diff/evaluate")
async def run_drift_analysis(payload: Optional[Dict[str, Any]] = Body(None)):
    global _latest_run_result, _counsel_reattestations
    workflow = LienmarkWorkflow()
    result = await workflow.execute_drift_detection()
    _latest_run_result = result
    _counsel_reattestations.clear()  # Reset counsel actions for clean run
    return result.model_dump()


@app.get("/api/review/queue")
def get_review_queue(target_version: str = "v8"):
    """
    Returns the active counsel review queue containing strictly stale claims
    with 4-dimensional explanations for version-bound clearance review.
    """
    queue = counsel_checkpoint_manager.get_review_queue(target_version_id=target_version)
    items_data = [item.model_dump() for item in queue.items]
    return {
        "queue_id": queue.queue_id,
        "target_version_id": target_version,
        "base_version_id": queue.base_version_id,
        "items": items_data,
        "queue": items_data,
        "total_stale_count": len(queue),
        "total_count": len(queue),
    }


@app.post("/api/review/action")
def submit_review_action(request: ReviewActionRequest):
    """
    Executes a human counsel review action (re_attest, reject, exception),
    enforcing fail-closed security gates, generating a tamper-evident SupersessionEvent,
    and recording the transition in the immutable audit ledger.
    """
    try:
        key = request.stable_lineage_key
        if not key and request.decision_id:
            key = request.decision_id.replace("dec_v7_", "").replace("dec_", "")

        if not key:
            raise HTTPException(status_code=400, detail="stable_lineage_key or decision_id is required.")

        final_rationale = (request.counsel_rationale or request.rationale or "").strip()
        act_str = request.action.value if hasattr(request.action, "value") else str(request.action).lower()
        if act_str == "re_attest" and not final_rationale:
            raise HTTPException(
                status_code=403,
                detail="Fail-closed safety invariant: Counsel re-attestation requires explicit legal rationale."
            )
        elif not final_rationale:
            raise HTTPException(
                status_code=400,
                detail="Counsel rationale is required and cannot be empty."
            )

        reviewer = request.reviewer
        if not reviewer:
            reviewer = ReviewerIdentity(name=request.reviewer_name or "Sarah Jenkins, Esq.")

        new_decision, event = counsel_checkpoint_manager.apply_review_action(
            action=request.action,
            lineage_key=key,
            rationale=final_rationale,
            reviewer=reviewer,
            target_version_id=request.version_id or "v8",
            decision_id=request.decision_id,
        )

        # Synchronize with legacy _counsel_reattestations for exceptions schedule export
        _counsel_reattestations[key] = ReattestationRequest(
            decision_id=new_decision.decision_id,
            stable_lineage_key=key,
            version_id=request.version_id or "v8",
            new_status=new_decision.status,
            counsel_rationale=final_rationale,
            reviewer_name=reviewer.name if hasattr(reviewer, "name") else "Sarah Jenkins, Esq.",
        )

        return {
            "status": "success",
            "action": event.action.value,
            "stable_lineage_key": event.stable_lineage_key,
            "lineage_key": event.stable_lineage_key,
            "new_state": event.new_state.value,
            "new_status": event.new_status.value,
            "decision": new_decision.model_dump(),
            "new_decision": new_decision.model_dump(),
            "supersession_event": event.model_dump(),
            "event": event.model_dump(),
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "audit_event_hash": event.event_hash,
            "prior_decision_id": event.prior_decision_id,
            "system_recommendation": event.system_recommendation,
        }
    except UnauthorizedApprovalError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/review/history")
@app.get("/api/review/events")
def get_review_history(
    lineage_key: Optional[str] = None,
    stable_lineage_key: Optional[str] = None,
    as_dict: bool = False,
):
    """
    Returns the immutable append-only audit trail of SupersessionEvents,
    distinguishing AI recommendations from human counsel decisions.
    """
    effective_key = lineage_key or stable_lineage_key
    events = counsel_checkpoint_manager.get_audit_trail(lineage_key=effective_key)
    events_dump = [e.model_dump() for e in events]
    if as_dict:
        integrity = counsel_checkpoint_manager.verify_ledger_integrity()
        return {
            "events": events_dump,
            "total_events": len(events_dump),
            "is_ledger_tamper_free": integrity["is_valid"],
            "chain_head_hash": integrity.get("chain_head_hash", "0" * 64),
            "integrity_details": integrity.get("details", ""),
            "lineage_key": effective_key,
        }
    return events_dump


@app.get("/api/review/audit-trail")
def get_review_audit_trail(lineage_key: Optional[str] = None, stable_lineage_key: Optional[str] = None):
    """Structured audit trail response including cryptographic ledger verification."""
    effective_key = lineage_key or stable_lineage_key
    events = counsel_checkpoint_manager.get_audit_trail(lineage_key=effective_key)
    integrity = counsel_checkpoint_manager.verify_ledger_integrity()
    events_dump = [e.model_dump() for e in events]
    return {
        "events": events_dump,
        "total_events": len(events_dump),
        "is_ledger_tamper_free": integrity["is_valid"],
        "chain_head_hash": integrity.get("chain_head_hash", "0" * 64),
        "integrity_details": integrity.get("details", ""),
        "lineage_key": effective_key,
    }


@app.post("/api/review/attest")
@app.post("/api/attorney/override")
@app.post("/api/attorney-override")
def record_counsel_reattestation(request: ReattestationRequest):
    """Backwards-compatible endpoint for legacy tests and dashboard."""
    global _counsel_reattestations
    _counsel_reattestations[request.stable_lineage_key] = request
    action = ReviewAction.RE_ATTEST if request.new_status == DecisionStatus.APPROVED else ReviewAction.REJECT
    try:
        counsel_checkpoint_manager.apply_review_action(
            action=action,
            lineage_key=request.stable_lineage_key,
            rationale=request.counsel_rationale,
            reviewer=ReviewerIdentity(name=request.reviewer_name),
            target_version_id=request.version_id or "v8",
            decision_id=request.decision_id,
        )
    except Exception as e:
        logger.warning(f"Could not record checkpoint event from legacy attest endpoint: {e}")
    return {
        "status": "recorded",
        "stable_lineage_key": request.stable_lineage_key,
        "new_status": request.new_status.value,
        "rationale": request.counsel_rationale,
    }



@app.get("/api/reports/exceptions")
@app.get("/api/reports/form-eo-2026")
def get_exceptions_schedule():
    global _latest_run_result, _counsel_reattestations
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validity_results,
        reattestations=_counsel_reattestations,
    )
    return schedule.model_dump()


@app.get("/report/{production_id}", response_class=HTMLResponse)
def serve_form_eo_2026_report(production_id: str):
    """
    SSR Route for Form E&O-2026 Underwriter Exceptions Schedule.
    Renders high-fidelity, printable HTML directly on the server tier.
    """
    global _counsel_reattestations
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validity_results,
        reattestations=_counsel_reattestations,
    )
    html_content = InvalidationEngine.render_form_eo_2026_html(schedule)
    return HTMLResponse(content=html_content)


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    """
    Renders the responsive Judge/Reviewer Interface for the 40-second magic demo.
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lienmark — Clearance Change Control for E&O</title>
    <style>
        :root {
            --bg-primary: #0a0f1d;
            --bg-secondary: #131b2e;
            --bg-card: #1b2640;
            --text-primary: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #818cf8;
            --border-color: #2e3d60;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-primary); color: var(--text-primary); padding: 24px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border-color); margin-bottom: 24px; }
        .title-group h1 { font-size: 26px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
        .badge-track { background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; border: 1px solid rgba(56, 189, 248, 0.3); }
        .subtitle { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
        .hero-actions { display: flex; gap: 12px; }
        button { background: var(--accent-blue); color: #0a0f1d; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; }
        button:hover { filter: brightness(1.1); transform: translateY(-1px); }
        button.secondary { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color); }
        button.secondary:hover { background: #263554; }
        
        .metrics-ribbon { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 24px; }
        .metric-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; }
        .metric-label { font-size: 12px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; font-weight: 600; }
        .metric-value { font-size: 28px; font-weight: 700; margin-top: 6px; }
        .val-green { color: var(--accent-green); }
        .val-amber { color: var(--accent-amber); }
        .val-blue { color: var(--accent-blue); }
        .val-red { color: var(--accent-red); }

        .workspace-grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 24px; }
        .panel { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .panel-title { font-size: 16px; font-weight: 600; }

        .claims-list { display: flex; flex-direction: column; gap: 10px; max-height: 680px; overflow-y: auto; }
        .claim-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; cursor: pointer; transition: 0.15s; }
        .claim-card:hover { border-color: var(--accent-blue); }
        .claim-card.selected { border-color: var(--accent-blue); background: #243252; }
        .claim-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
        .claim-name { font-size: 14px; font-weight: 600; color: #fff; }
        .status-pill { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }
        .pill-carried { background: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.4); }
        .pill-reopened { background: rgba(245, 158, 11, 0.2); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.4); }
        .pill-reattested { background: rgba(56, 189, 248, 0.2); color: var(--accent-blue); border: 1px solid rgba(56, 189, 248, 0.4); }
        .pill-exception { background: rgba(239, 68, 68, 0.2); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.4); }
        .claim-meta { font-size: 12px; color: var(--text-muted); display: flex; gap: 12px; }

        .drawer-box { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .drawer-label { font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
        .drawer-content { font-size: 13px; line-height: 1.5; color: #e2e8f0; }
        .citation-link { color: var(--accent-blue); text-decoration: none; word-break: break-all; font-weight: 500; }
        .citation-link:hover { text-decoration: underline; }
        .trace-item { font-size: 12px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; }
        
        .action-row { display: flex; gap: 10px; margin-top: 14px; }
        .btn-approve { background: var(--accent-blue); }
        .btn-reject { background: var(--accent-red); color: #fff; }

        /* Modal */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); align-items: center; justify-content: center; z-index: 100; }
        .modal { background: var(--bg-secondary); border: 1px solid var(--border-color); width: 850px; max-height: 85vh; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
        .modal-header { padding: 18px 24px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
        .modal-body { padding: 24px; overflow-y: auto; font-size: 13px; }
        .report-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        .report-table th, .report-table td { padding: 10px 12px; border: 1px solid var(--border-color); text-align: left; }
        .report-table th { background: var(--bg-card); font-size: 12px; text-transform: uppercase; color: var(--text-muted); }
    </style>
</head>
<body>

    <div class="header">
        <div class="title-group">
            <h1>Lienmark <span class="badge-track">Parallel Track — Agentic Cinema</span></h1>
            <p class="subtitle">Clearance Change Control for E&O: Version Lineage & Selective Invalidation Engine</p>
        </div>
        <div class="hero-actions">
            <button id="btn-run" onclick="runAnalysis()">⚡ Ingest V8 & Detect Drift</button>
            <button class="secondary" onclick="openReportModal()">📄 Export Exceptions Schedule</button>
        </div>
    </div>

    <div class="metrics-ribbon">
        <div class="metric-card">
            <div class="metric-label">Total Claims</div>
            <div class="metric-value" id="m-total">12</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Carried Forward</div>
            <div class="metric-value val-green" id="m-carried">10</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Reopened (Drift)</div>
            <div class="metric-value val-amber" id="m-reopened">2</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Counsel Re-Attested</div>
            <div class="metric-value val-blue" id="m-reattested">0</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Exceptions Schedule</div>
            <div class="metric-value val-red" id="m-exceptions">0</div>
        </div>
    </div>

    <div class="workspace-grid">
        <!-- Left Column: Claims Feed -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">Production Lineage: Cut v7 → Cut v8 (12 Claims)</div>
                <span style="font-size: 12px; color: var(--accent-blue);">Fail-Closed Policy Active</span>
            </div>
            <div class="claims-list" id="claims-container">
                <!-- Rendered dynamically -->
            </div>
        </div>

        <!-- Right Column: Parallel Evidence & Gemini Synthesis -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title" id="detail-title">Selected Claim Inspection</div>
            </div>
            
            <div id="detail-empty" style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 40px 0;">
                Select a claim on the left to inspect dependencies, Parallel search citations, and counsel decision history.
            </div>

            <div id="detail-content" style="display: none;">
                <div class="drawer-box">
                    <div class="drawer-label">Creative Context & Prominence</div>
                    <div class="drawer-content" id="detail-creative"></div>
                </div>

                <div class="drawer-box" id="box-parallel" style="border-color: rgba(56, 189, 248, 0.4);">
                    <div class="drawer-label" style="color: var(--accent-blue);">
                        🔍 Parallel Search API — Attributable Evidence
                    </div>
                    <div class="drawer-content" id="detail-parallel"></div>
                </div>

                <div class="drawer-box" id="box-gemini">
                    <div class="drawer-label" style="color: var(--accent-purple);">
                        🤖 Gemini 2.5 Flash — Counsel Briefing
                    </div>
                    <div class="drawer-content" id="detail-gemini"></div>
                </div>

                <div class="drawer-box" id="box-counsel" style="display: none;">
                    <div class="drawer-label">Attestation Action</div>
                    <div class="drawer-content">
                        <textarea id="counsel-rationale" style="width: 100%; height: 60px; background: var(--bg-primary); color: #fff; border: 1px solid var(--border-color); border-radius: 6px; padding: 8px; font-size: 12px; resize: none;" placeholder="Enter attorney clearance rationale..."></textarea>
                        <div class="action-row">
                            <button class="btn-approve" onclick="submitReattestation(true)">Re-Attest (Approve)</button>
                            <button class="btn-reject" onclick="submitReattestation(false)">Mark as Exception</button>
                        </div>
                    </div>
                </div>
            </div>

            <div style="margin-top: 20px;">
                <div class="panel-title" style="font-size: 13px; margin-bottom: 10px;">Agent Builder Execution Traces</div>
                <div id="traces-container" style="background: var(--bg-card); border-radius: 6px; padding: 10px; max-height: 180px; overflow-y: auto;">
                    <div style="font-size: 12px; color: var(--text-muted);">Ready to run drift detection workflow.</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Exceptions Schedule Modal -->
    <div class="modal-overlay" id="modal-report">
        <div class="modal">
            <div class="modal-header">
                <div style="font-size: 16px; font-weight: 700;">Form E&O-2026 Underwriter Exceptions Schedule</div>
                <button class="secondary" style="padding: 4px 10px;" onclick="closeReportModal()">✕</button>
            </div>
            <div class="modal-body" id="modal-body-content">
                Loading schedule...
            </div>
        </div>
    </div>

    <script>
        let currentClaims = [];
        let currentBriefings = {};
        let selectedClaimKey = null;

        async function init() {
            try {
                const res = await fetch('/api/fixtures');
                const data = await res.json();
                renderBaseline(data.v7_claims);
            } catch (e) {
                console.error(e);
            }
        }

        function renderBaseline(claims) {
            const container = document.getElementById('claims-container');
            container.innerHTML = '';
            claims.forEach(c => {
                const div = document.createElement('div');
                div.className = 'claim-card';
                div.onclick = () => selectClaim(c.key);
                div.innerHTML = `
                    <div class="claim-head">
                        <span class="claim-name">${c.description}</span>
                        <span class="status-pill pill-carried">APPROVED (V7)</span>
                    </div>
                    <div class="claim-meta">
                        <span>📍 ${c.scene}</span>
                        <span>🏷️ ${c.asset_type.toUpperCase()}</span>
                        <span>⏱️ ${c.prominence}</span>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        async function runAnalysis() {
            const btn = document.getElementById('btn-run');
            btn.innerText = '⏳ Orchestrating ADK Workflow...';
            btn.disabled = true;

            try {
                const res = await fetch('/api/drift/compare', { method: 'POST' });
                const data = await res.json();
                
                currentClaims = data.claims;
                currentBriefings = data.counsel_briefings;

                // Update Metrics
                document.getElementById('m-total').innerText = data.total_claims;
                document.getElementById('m-carried').innerText = data.carried_forward_count;
                document.getElementById('m-reopened').innerText = data.reopened_count;

                renderEvaluatedClaims(data.claims);
                renderTraces(data.execution_traces);

                // Auto select first reopened claim (Scene 42 Poster)
                selectClaim('poster_noir_detective_magazine');
            } catch (e) {
                alert('Analysis failed: ' + e);
            } finally {
                btn.innerText = '⚡ Re-Run Drift Analysis';
                btn.disabled = false;
            }
        }

        function renderEvaluatedClaims(claims) {
            const container = document.getElementById('claims-container');
            container.innerHTML = '';

            claims.forEach(c => {
                const div = document.createElement('div');
                div.className = 'claim-card ' + (selectedClaimKey === c.stable_lineage_key ? 'selected' : '');
                div.onclick = () => selectClaim(c.stable_lineage_key);

                let pillClass = 'pill-carried';
                let pillText = 'CARRIED FORWARD';
                if (c.state === 'stale') {
                    pillClass = 'pill-reopened';
                    pillText = 'DRIFT REOPENED';
                } else if (c.state === 're_attested') {
                    pillClass = 'pill-reattested';
                    pillText = 'RE-ATTESTED';
                } else if (c.state === 'exception') {
                    pillClass = 'pill-exception';
                    pillText = 'EXCEPTION';
                }

                div.innerHTML = `
                    <div class="claim-head">
                        <span class="claim-name">${c.description}</span>
                        <span class="status-pill ${pillClass}">${pillText}</span>
                    </div>
                    <div class="claim-meta">
                        <span>📍 ${c.scene}</span>
                        <span>🏷️ ${c.asset_type.toUpperCase()}</span>
                        <span>⚡ ${c.reason_code}</span>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function selectClaim(key) {
            selectedClaimKey = key;
            const claim = currentClaims.find(c => c.stable_lineage_key === key);
            if (!claim) return;

            document.querySelectorAll('.claim-card').forEach(c => c.classList.remove('selected'));
            event?.currentTarget?.classList.add('selected');

            document.getElementById('detail-empty').style.display = 'none';
            document.getElementById('detail-content').style.display = 'block';
            document.getElementById('detail-title').innerText = claim.description;

            // Creative Context
            document.getElementById('detail-creative').innerHTML = `
                <div><strong>Location:</strong> ${claim.scene}</div>
                <div style="margin-top: 4px;"><strong>Prominence:</strong> ${claim.prominence}</div>
                <div style="margin-top: 4px;"><strong>Status Reason:</strong> <code>${claim.reason_code}</code></div>
            `;

            // Parallel Search Evidence
            const parallelBox = document.getElementById('box-parallel');
            if (claim.evidence) {
                parallelBox.style.display = 'block';
                document.getElementById('detail-parallel').innerHTML = `
                    <div><strong>Title:</strong> ${claim.evidence.source_title}</div>
                    <div style="margin-top: 4px;"><strong>Source URL:</strong> <a class="citation-link" href="${claim.evidence.source_url}" target="_blank">${claim.evidence.source_url}</a></div>
                    <div style="margin-top: 6px; background: rgba(0,0,0,0.25); padding: 8px; border-radius: 4px; font-style: italic;">"${claim.evidence.excerpt}"</div>
                    <div style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">
                        Latency: ${claim.evidence.latency_ms}ms | Provider Call ID: <code>${claim.evidence.call_id}</code> | Stance: <strong>${claim.evidence.stance.toUpperCase()}</strong>
                    </div>
                `;
            } else {
                parallelBox.style.display = 'none';
            }

            // Gemini Briefing
            const geminiBox = document.getElementById('box-gemini');
            const briefing = currentBriefings[key];
            if (briefing) {
                geminiBox.style.display = 'block';
                document.getElementById('detail-gemini').innerHTML = `
                    <div>${briefing.counsel_summary}</div>
                    <div style="margin-top: 8px; font-weight: 600; color: var(--accent-blue);">Recommendation: ${briefing.suggested_counsel_action}</div>
                `;
            } else {
                geminiBox.style.display = 'none';
            }

            // Counsel Action Box (only for reopened claims)
            const counselBox = document.getElementById('box-counsel');
            if (claim.state === 'stale') {
                counselBox.style.display = 'block';
                const defaultRationale = key.includes('poster')
                    ? 'Artwork verified in public domain via Library of Congress renewal records retrieved by Parallel Search; non-infringing.'
                    : 'Vanguard Media copyright claim active; cue excluded from final master mix.';
                document.getElementById('counsel-rationale').value = defaultRationale;
            } else {
                counselBox.style.display = 'none';
            }
        }

        async function submitReattestation(approved) {
            if (!selectedClaimKey) return;
            const rationale = document.getElementById('counsel-rationale').value;

            const payload = {
                decision_id: 'dec_' + selectedClaimKey,
                stable_lineage_key: selectedClaimKey,
                version_id: 'v8',
                new_status: approved ? 'approved' : 'rejected',
                counsel_rationale: rationale,
                reviewer_name: 'Sarah Jenkins, Esq. (Clearance Counsel)'
            };

            await fetch('/api/review/attest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            // Update local state
            const claim = currentClaims.find(c => c.stable_lineage_key === selectedClaimKey);
            if (claim) {
                claim.state = approved ? 're_attested' : 'exception';
            }

            // Update counters
            const reattested = currentClaims.filter(c => c.state === 're_attested').length;
            const exceptions = currentClaims.filter(c => c.state === 'exception').length;
            document.getElementById('m-reattested').innerText = reattested;
            document.getElementById('m-exceptions').innerText = exceptions;

            renderEvaluatedClaims(currentClaims);
            selectClaim(selectedClaimKey);
        }

        function renderTraces(traces) {
            const container = document.getElementById('traces-container');
            container.innerHTML = '';
            traces.forEach(t => {
                const div = document.createElement('div');
                div.className = 'trace-item';
                div.innerHTML = `
                    <span><strong>${t.component}</strong>: ${t.step_name}</span>
                    <span style="color: var(--text-muted);">${t.duration_ms}ms</span>
                `;
                container.appendChild(div);
            });
        }

        async function openReportModal() {
            document.getElementById('modal-report').style.display = 'flex';
            const body = document.getElementById('modal-body-content');
            body.innerHTML = 'Loading latest schedule...';

            const res = await fetch('/api/reports/exceptions');
            const data = await res.json();

            let rows = '';
            data.items.forEach(item => {
                rows += `
                    <tr>
                        <td><strong>${item.description}</strong><br><small style="color: #94a3b8;">${item.scene_or_timecode}</small></td>
                        <td>${item.asset_type.toUpperCase()}</td>
                        <td>${item.v7_decision_status}</td>
                        <td><strong>${item.v8_evaluation_state.toUpperCase()}</strong></td>
                        <td>${item.counsel_action}</td>
                    </tr>
                `;
            });

            body.innerHTML = `
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 12px;">
                    <div>
                        <div><strong>Project:</strong> ${data.project_name} (${data.project_id})</div>
                        <div><strong>Lineage:</strong> Base ${data.base_version_id} → Target ${data.target_version_id}</div>
                    </div>
                    <div>
                        <div><strong>Policy:</strong> ${data.policy_version}</div>
                        <div><strong>Carried:</strong> ${data.carried_forward_count} | <strong>Re-Attested:</strong> ${data.re_attested_count} | <strong>Exceptions:</strong> ${data.unresolved_exception_count}</div>
                    </div>
                </div>
                <table class="report-table">
                    <thead>
                        <tr>
                            <th>Claim / Scene</th>
                            <th>Type</th>
                            <th>V7 Status</th>
                            <th>V8 Evaluation</th>
                            <th>Counsel Disposition & Provenance</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            `;
        }

        function closeReportModal() {
            document.getElementById('modal-report').style.display = 'none';
        }

        window.onload = init;
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
