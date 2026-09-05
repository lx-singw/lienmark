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

        return ExceptionsSchedule(
            schedule_id=f"sched_{project_id}_{target_version_id}_{int(datetime.now(timezone.utc).timestamp())}",
            project_id=project_id,
            target_version_id=target_version_id,
            base_version_id=base_version_id,
            policy_version=cls.POLICY_VERSION,
            total_claims=len(validity_results),
            carried_forward_count=carried_count,
            reopened_count=reopened_count,
            re_attested_count=reattested_count,
            unresolved_exception_count=exception_count,
            items=schedule_items,
        )
