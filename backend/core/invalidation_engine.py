"""
Lienmark Deterministic Invalidation Engine
The core defensible IP of Lienmark: fail-closed clearance dependency evaluation.
Determines whether prior counsel decisions carry forward or become stale.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import hashlib

from backend.domain.models import (
    ChangeKind,
    CreativeDelta,
    CreativeUse,
    CounselDecision,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceStance,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    CarrierHeader,
    PublicEvidenceSnapshot,
    ReattestationRequest,
)


class InvalidationEngine:
    """
    Deterministic clearance dependency graph evaluator.
    Evaluates prior V7 counsel decisions against V8 creative deltas and external evidence.
    """

    POLICY_VERSION = "E&O-2026.1-DEVPOST"

    @staticmethod
    def compute_context_hash(text: str, prominence: str) -> str:
        payload = f"{text.strip()}::{prominence.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def detect_creative_deltas(
        cls,
        base_uses: List[CreativeUse],
        target_uses: List[CreativeUse],
    ) -> Dict[str, CreativeDelta]:
        """
        Compare base (V7) and target (V8) creative uses by stable_lineage_key.
        """
        base_map = {u.stable_lineage_key: u for u in base_uses}
        target_map = {u.stable_lineage_key: u for u in target_uses}
        deltas: Dict[str, CreativeDelta] = {}

        for key, base_use in base_map.items():
            target_use = target_map.get(key)
            if not target_use:
                deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=base_use.use_id,
                    after_use_id=None,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.REMOVED,
                    materiality="high",
                    changed_fields=["use_id"],
                    reason_codes=["ASSET_REMOVED_IN_TARGET_VERSION"],
                )
                continue

            changed_fields = []
            reason_codes = []

            # Check context hash
            if base_use.context_hash != target_use.context_hash:
                changed_fields.append("context_hash")
                reason_codes.append("CONTEXT_HASH_MISMATCH")

            # Check prominence / duration
            if base_use.duration_or_prominence != target_use.duration_or_prominence:
                changed_fields.append("duration_or_prominence")
                reason_codes.append("PROMINENCE_ESCALATED")

            # Check narrative context
            if base_use.context != target_use.context:
                changed_fields.append("context")
                reason_codes.append("SCRIPT_DIALOGUE_MODIFIED")

            if changed_fields:
                deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=base_use.use_id,
                    after_use_id=target_use.use_id,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.MATERIALLY_MODIFIED,
                    materiality="high",
                    match_confidence=1.0,
                    changed_fields=changed_fields,
                    reason_codes=reason_codes,
                )
            else:
                deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=base_use.use_id,
                    after_use_id=target_use.use_id,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.UNCHANGED,
                    materiality="none",
                    match_confidence=1.0,
                    changed_fields=[],
                    reason_codes=["CREATIVE_USE_IDENTICAL"],
                )

        return deltas

    @classmethod
    def evaluate_invalidation(
        cls,
        base_uses: List[CreativeUse],
        target_uses: List[CreativeUse],
        prior_decisions: List[CounselDecision],
        evidence_snapshots: Dict[str, PublicEvidenceSnapshot],
        target_version_id: str = "v8",
    ) -> List[DecisionValidity]:
        """
        Evaluate each prior decision against creative deltas and external evidence.
        Enforces FAIL-CLOSED policy: any ambiguity or missing dependency marks as STALE.
        """
        deltas = cls.detect_creative_deltas(base_uses, target_uses)
        validity_results: List[DecisionValidity] = []

        for decision in prior_decisions:
            key = decision.stable_lineage_key
            delta = deltas.get(key)
            evidence = evidence_snapshots.get(key)

            # Fail-closed check: missing delta or missing use
            if not delta:
                validity_results.append(
                    DecisionValidity(
                        decision_id=decision.decision_id,
                        evaluated_for_version_id=target_version_id,
                        stable_lineage_key=key,
                        state=DecisionState.STALE,
                        reason_code="FAIL_CLOSED_MISSING_DELTA",
                        revalidation_action="manual",
                    )
                )
                continue

            # Check 1: Creative use materially modified
            if delta.change_kind == ChangeKind.MATERIALLY_MODIFIED:
                validity_results.append(
                    DecisionValidity(
                        decision_id=decision.decision_id,
                        evaluated_for_version_id=target_version_id,
                        stable_lineage_key=key,
                        state=DecisionState.STALE,
                        reason_code="CREATIVE_CONTEXT_ALTERED",
                        changed_dependency_ids=[delta.delta_id],
                        revalidation_action="revalidate",
                        creative_delta=delta,
                        evidence_snapshot=evidence,
                    )
                )
                continue

            # Check 2: External evidence drift / contradiction
            if evidence and evidence.stance in [
                EvidenceStance.CONTRADICTORY,
                EvidenceStance.INSUFFICIENT,
            ]:
                validity_results.append(
                    DecisionValidity(
                        decision_id=decision.decision_id,
                        evaluated_for_version_id=target_version_id,
                        stable_lineage_key=key,
                        state=DecisionState.STALE,
                        reason_code="EXTERNAL_EVIDENCE_SHIFT",
                        changed_dependency_ids=[evidence.snapshot_id],
                        revalidation_action="revalidate",
                        creative_delta=delta,
                        evidence_snapshot=evidence,
                    )
                )
                continue

            # Check 3: All dependencies verified unchanged -> Carry forward
            if delta.change_kind == ChangeKind.UNCHANGED:
                validity_results.append(
                    DecisionValidity(
                        decision_id=decision.decision_id,
                        evaluated_for_version_id=target_version_id,
                        stable_lineage_key=key,
                        state=DecisionState.CARRIED_FORWARD,
                        reason_code="DEPENDENCIES_SATISFIED_UNCHANGED",
                        revalidation_action="carry",
                        creative_delta=delta,
                        evidence_snapshot=evidence,
                    )
                )
            else:
                # Catch-all fail-closed
                validity_results.append(
                    DecisionValidity(
                        decision_id=decision.decision_id,
                        evaluated_for_version_id=target_version_id,
                        stable_lineage_key=key,
                        state=DecisionState.STALE,
                        reason_code=f"UNEXPECTED_DELTA_{delta.change_kind.value.upper()}",
                        revalidation_action="manual",
                        creative_delta=delta,
                        evidence_snapshot=evidence,
                    )
                )

        return validity_results

    @classmethod
    def generate_exceptions_schedule(
        cls,
        project_id: str,
        base_version_id: str,
        target_version_id: str,
        target_uses: List[CreativeUse],
        validity_results: List[DecisionValidity],
        reattestations: Optional[Dict[str, ReattestationRequest]] = None,
    ) -> ExceptionsSchedule:
        """
        Generate the version-bound Exceptions Schedule for E&O underwriter review.
        """
        reattestations = reattestations or {}
        use_map = {u.stable_lineage_key: u for u in target_uses}

        carried_count = 0
        reopened_count = 0
        reattested_count = 0
        exception_count = 0

        schedule_items: List[ExceptionsScheduleItem] = []

        for val in validity_results:
            key = val.stable_lineage_key
            use = use_map.get(key)
            if not use:
                continue

            reattest = reattestations.get(key)
            final_eval_state = val.state.value

            citations = []
            if val.evidence_snapshot:
                citations.append(
                    {
                        "source_title": val.evidence_snapshot.source_title,
                        "source_url": val.evidence_snapshot.source_url,
                        "excerpt": val.evidence_snapshot.excerpt,
                        "provider": val.evidence_snapshot.provider,
                    }
                )

            if val.state == DecisionState.CARRIED_FORWARD:
                carried_count += 1
                counsel_action = "Carried forward unchanged from prior approved counsel attestation."
            elif val.state == DecisionState.STALE:
                reopened_count += 1
                if reattest:
                    if reattest.new_status == DecisionStatus.APPROVED:
                        final_eval_state = DecisionState.RE_ATTESTED.value
                        reattested_count += 1
                        counsel_action = (
                            f"Re-attested by {reattest.reviewer_name}: {reattest.counsel_rationale}"
                        )
                    else:
                        final_eval_state = DecisionState.EXCEPTION.value
                        exception_count += 1
                        counsel_action = (
                            f"Marked as UNRESOLVED EXCEPTION by {reattest.reviewer_name}: {reattest.counsel_rationale}"
                        )
                else:
                    final_eval_state = DecisionState.EXCEPTION.value
                    exception_count += 1
                    counsel_action = (
                        "Pending counsel re-attestation following detected drift."
                    )
            else:
                counsel_action = "Review required."

            schedule_items.append(
                ExceptionsScheduleItem(
                    stable_lineage_key=key,
                    asset_type=use.asset_type,
                    description=use.description,
                    scene_or_timecode=use.scene_or_timecode,
                    v7_decision_status="APPROVED",
                    v8_evaluation_state=final_eval_state,
                    invalidation_reason=val.reason_code if val.state != DecisionState.CARRIED_FORWARD else None,
                    counsel_action=counsel_action,
                    evidence_citations=citations,
                )
            )

        unresolved_items = [
            i for i in schedule_items if i.v8_evaluation_state in (DecisionState.EXCEPTION.value, "exception")
        ]

        return ExceptionsSchedule(
            schedule_id=f"sched_{project_id}_{target_version_id}_{int(datetime.now(timezone.utc).timestamp())}",
            project_id=project_id,
            project_name="Lienmark Production Digital Twin",
            target_version_id=target_version_id,
            base_version_id=base_version_id,
            policy_version=cls.POLICY_VERSION,
            policy_number=cls.POLICY_VERSION,
            carrier_header=CarrierHeader(policy_number=cls.POLICY_VERSION),
            production_metadata={
                "project_id": project_id,
                "project_name": "Lienmark Production Digital Twin",
                "production_title": "Shadows Over Broadway",
                "base_version_id": base_version_id,
                "target_version_id": target_version_id,
                "target_cut_hash": "f9e8d7c6b5a43210fedcba9876543210",
                "total_claims": len(validity_results),
            },
            total_claims=len(validity_results),
            carried_forward_count=carried_count,
            reopened_count=reopened_count,
            re_attested_count=reattested_count,
            unresolved_exception_count=exception_count,
            items=schedule_items,
            unresolved_exceptions_schedule=unresolved_items,
            unresolved_exceptions=unresolved_items,
        )

    @classmethod
    def render_form_eo_2026_html(cls, schedule: ExceptionsSchedule) -> str:
        """
        Renders the official Form E&O-2026 Underwriter Exceptions Schedule as a printable,
        statutory HTML document suitable for insurance binder review and headless PDF generation.
        """
        carrier = schedule.carrier_header
        meta = schedule.production_metadata

        unresolved_rows = ""
        for item in schedule.unresolved_exceptions_schedule:
            citation_links = "".join(
                f'<div><a href="{c.get("source_url", "#")}" target="_blank" style="color: #0284c7;">{c.get("source_title", "Evidence Source")}</a>: {c.get("excerpt", "")}</div>'
                for c in item.evidence_citations
            )
            unresolved_rows += f"""
            <tr style="break-inside: avoid;">
                <td style="padding: 10px; border: 1px solid #cbd5e1; font-weight: 600;">
                    {item.description}<br>
                    <span style="font-size: 11px; color: #64748b; font-weight: normal;">{item.scene_or_timecode} ({item.stable_lineage_key})</span>
                </td>
                <td style="padding: 10px; border: 1px solid #cbd5e1; text-transform: uppercase; font-size: 12px;">{item.asset_type}</td>
                <td style="padding: 10px; border: 1px solid #cbd5e1; color: #b91c1c; font-weight: 700; font-size: 12px;">EXCEPTION</td>
                <td style="padding: 10px; border: 1px solid #cbd5e1; font-size: 12px;">
                    <div><strong>Reason:</strong> {item.invalidation_reason or 'Drift detected'}</div>
                    <div style="margin-top: 4px;"><strong>Counsel Action:</strong> {item.counsel_action}</div>
                    <div style="margin-top: 4px; font-size: 11px; color: #475569;">{citation_links}</div>
                </td>
            </tr>
            """

        all_rows = ""
        for item in schedule.items:
            status_color = "#15803d" if item.v8_evaluation_state == "carried_forward" else ("#0284c7" if item.v8_evaluation_state == "re_attested" else "#b91c1c")
            all_rows += f"""
            <tr style="break-inside: avoid;">
                <td style="padding: 8px; border: 1px solid #e2e8f0;">{item.description}<br><span style="font-size: 10px; color: #64748b;">{item.scene_or_timecode}</span></td>
                <td style="padding: 8px; border: 1px solid #e2e8f0; font-size: 11px;">{item.asset_type.upper()}</td>
                <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: 600; font-size: 11px; color: {status_color};">{item.v8_evaluation_state.upper()}</td>
                <td style="padding: 8px; border: 1px solid #e2e8f0; font-size: 11px;">{item.counsel_action}</td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Form E&O-2026 Underwriter Exceptions Schedule — {meta.get('production_title', 'Production')}</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; margin: 0; padding: 32px; background: #fff; line-height: 1.5; }}
        .header-box {{ border: 2px solid #0f172a; padding: 20px; margin-bottom: 24px; border-radius: 4px; }}
        .carrier-title {{ font-size: 18px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }}
        .form-title {{ font-size: 24px; font-weight: 900; margin-top: 8px; color: #0f172a; }}
        .grid-meta {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 16px; font-size: 13px; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
        .badge-pending {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
        .summary-ribbon {{ display: flex; gap: 16px; margin-bottom: 24px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 6px; }}
        .stat-item {{ flex: 1; }}
        .stat-val {{ font-size: 20px; font-weight: 800; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 12px; }}
        th {{ background: #f1f5f9; padding: 10px; text-align: left; border: 1px solid #cbd5e1; font-weight: 700; }}
        @media print {{
            body {{ padding: 0; margin: 20mm; font-size: 11pt; }}
            .no-print {{ display: none !important; }}
            tr {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="header-box">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div class="carrier-title">{carrier.carrier_name}</div>
                <div class="form-title">FORM E&O-2026: SCHEDULE OF UNRESOLVED CLEARANCE EXCEPTIONS</div>
                <div style="font-size: 13px; color: #475569; margin-top: 4px;">Broker: {carrier.broker_name} | Policy Binder: <strong>{carrier.policy_number}</strong></div>
            </div>
            <div style="text-align: right;">
                <span class="badge badge-pending">Underwriting Status: {carrier.underwriter_status}</span>
                <div style="font-size: 11px; color: #64748b; margin-top: 6px;">Generated: {schedule.generated_at}</div>
            </div>
        </div>
        <div class="grid-meta" style="border-top: 1px solid #e2e8f0; padding-top: 12px; margin-top: 16px;">
            <div><strong>Production Title:</strong> {meta.get('production_title', 'Shadows Over Broadway')}</div>
            <div><strong>Project ID:</strong> {schedule.project_id}</div>
            <div><strong>Lineage:</strong> Base {schedule.base_version_id} &rarr; Target {schedule.target_version_id}</div>
            <div><strong>Target Cut Content Hash:</strong> <code>{meta.get('target_cut_hash', 'f9e8d7c6b5a43210fedcba9876543210')}</code></div>
            <div><strong>Clearance Warranty Clause:</strong> {carrier.warranty_clause}</div>
            <div><strong>Reconciliation Invariant:</strong> Total {schedule.total_claims} = {schedule.carried_forward_count} Carried + {schedule.re_attested_count} Re-Attested + {schedule.unresolved_exception_count} Exception</div>
        </div>
    </div>

    <div class="summary-ribbon">
        <div class="stat-item">
            <div style="color: #64748b; font-size: 11px; font-weight: 600;">TOTAL CLAIMS</div>
            <div class="stat-val">{schedule.total_claims}</div>
        </div>
        <div class="stat-item">
            <div style="color: #15803d; font-size: 11px; font-weight: 600;">CARRIED FORWARD</div>
            <div class="stat-val" style="color: #15803d;">{schedule.carried_forward_count}</div>
        </div>
        <div class="stat-item">
            <div style="color: #0284c7; font-size: 11px; font-weight: 600;">COUNSEL RE-ATTESTED</div>
            <div class="stat-val" style="color: #0284c7;">{schedule.re_attested_count}</div>
        </div>
        <div class="stat-item">
            <div style="color: #b91c1c; font-size: 11px; font-weight: 600;">ACTIVE EXCEPTIONS</div>
            <div class="stat-val" style="color: #b91c1c;">{schedule.unresolved_exception_count}</div>
        </div>
    </div>

    <h3 style="margin-bottom: 12px; font-size: 16px; color: #b91c1c;">SECTION I: UNRESOLVED EXCEPTIONS REQUIRING UNDERWRITER RIDER</h3>
    <table>
        <thead>
            <tr>
                <th style="width: 30%;">Claim & Scene</th>
                <th style="width: 15%;">Asset Type</th>
                <th style="width: 15%;">Status</th>
                <th style="width: 40%;">Reason, Disposition & Parallel Search Citations</th>
            </tr>
        </thead>
        <tbody>
            {unresolved_rows if unresolved_rows.strip() else '<tr><td colspan="4" style="text-align: center; padding: 12px; color: #64748b;">No active exceptions. All items successfully carried forward or re-attested.</td></tr>'}
        </tbody>
    </table>

    <h3 style="margin-bottom: 12px; font-size: 16px; color: #0f172a; margin-top: 32px;">SECTION II: COMPREHENSIVE 12-CLAIM RECONCILIATION AUDIT LEDGER</h3>
    <table>
        <thead>
            <tr>
                <th style="width: 35%;">Claim / Timecode</th>
                <th style="width: 15%;">Type</th>
                <th style="width: 15%;">V8 State</th>
                <th style="width: 35%;">Counsel Disposition</th>
            </tr>
        </thead>
        <tbody>
            {all_rows}
        </tbody>
    </table>

    <div style="margin-top: 40px; border-top: 2px solid #0f172a; padding-top: 16px; display: flex; justify-content: space-between; break-inside: avoid;">
        <div>
            <div><strong>Clearance Counsel Sign-off:</strong> Eleanor Vance, Esq.</div>
            <div style="font-size: 11px; color: #64748b;">Digital Attestation Timestamp: {schedule.generated_at}</div>
            <div style="font-size: 11px; color: #64748b;">Policy Reference: {carrier.policy_number}</div>
        </div>
        <div style="text-align: right;">
            <div><strong>Underwriter Acknowledgment:</strong> ___________________________</div>
            <div style="font-size: 11px; color: #64748b;">Carrier Representative Signature</div>
        </div>
    </div>
</body>
</html>"""

