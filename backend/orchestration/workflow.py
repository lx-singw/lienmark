"""
Lienmark Orchestration Workflow
Orchestrates the entire agentic clearance drift pipeline:
Version Ingestion -> Semantic Delta (Gemini) -> Invalidation Evaluation -> Targeted Search (Parallel) -> Trace.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import time
import uuid
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from backend.domain.models import (
    CreativeUse,
    CounselDecision,
    ContractAgreement,
    DecisionState,
    DecisionValidity,
    EvidenceReconciliationResult,
    EvidenceStance,
    PlannedRevalidationRequest,
    PublicEvidenceSnapshot,
    ReattestationRequest,
    RevalidationPlan,
    ExceptionsSchedule,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.services.gemini_service import GeminiService, ClearanceBriefing
from backend.services.parallel_service import ParallelSearchService
from backend.services.revalidation_planner import RevalidationPlanner
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)


class WorkflowStepTrace(BaseModel):
    step_name: str
    component: str  # Gemini, InvalidationEngine, ParallelSearch, RevalidationPlanner, EvidenceReconciler
    status: str
    duration_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRunResult(BaseModel):
    run_id: str
    base_version: str = "v7"
    target_version: str = "v8"
    total_claims: int = 12
    carried_forward_count: int = 10
    reopened_count: int = 2
    claims: List[Dict[str, Any]]
    counsel_briefings: Dict[str, ClearanceBriefing]
    execution_traces: List[WorkflowStepTrace]
    total_duration_ms: float
    revalidation_plan: Optional[RevalidationPlan] = None
    reconciliation_results: List[EvidenceReconciliationResult] = Field(default_factory=list)


class LienmarkWorkflow:
    """
    Main Agentic Workflow for Lienmark.
    Follows Google Cloud Agent Builder / ADK orchestration principles.
    Wired with RevalidationPlanner and EvidenceReconciler.
    """

    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        parallel_service: Optional[ParallelSearchService] = None,
        revalidation_planner: Optional[RevalidationPlanner] = None,
        evidence_reconciler: Optional[EvidenceReconciler] = None,
        adk_pipeline: Optional[Any] = None,
    ):
        self.gemini = gemini_service or GeminiService()
        self.parallel = parallel_service or ParallelSearchService()
        self.revalidation_planner = revalidation_planner or RevalidationPlanner()
        self.evidence_reconciler = evidence_reconciler or EvidenceReconciler()
        self._adk_pipeline = adk_pipeline


    async def execute_drift_detection(
        self,
        contracts: Optional[List[ContractAgreement]] = None,
        base_uses: Optional[List[CreativeUse]] = None,
        target_uses: Optional[List[CreativeUse]] = None,
        prior_decisions: Optional[List[CounselDecision]] = None,
        evidence_snapshots: Optional[Dict[str, PublicEvidenceSnapshot]] = None,
        base_version_id: str = "v7",
        target_version_id: str = "v8",
    ) -> WorkflowRunResult:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        overall_start = time.perf_counter()
        traces: List[WorkflowStepTrace] = []

        # Step 1: Ingest versions & golden fixtures
        t0 = time.perf_counter()
        v7_uses_fix, v8_uses_fix, v7_decisions_fix, initial_evidence_fix = get_golden_fixtures()
        eff_base_uses = base_uses if base_uses is not None else v7_uses_fix
        eff_target_uses = target_uses if target_uses is not None else v8_uses_fix
        eff_prior_decisions = prior_decisions if prior_decisions is not None else v7_decisions_fix
        eff_evidence = evidence_snapshots if evidence_snapshots is not None else initial_evidence_fix

        traces.append(
            WorkflowStepTrace(
                step_name="version_ingestion",
                component="LienmarkEngine",
                status="SUCCESS",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details={
                    "v7_uses": len(eff_base_uses),
                    "v8_uses": len(eff_target_uses),
                    "base_uses": len(eff_base_uses),
                    "target_uses": len(eff_target_uses),
                },
            )
        )

        # Step 2: Gemini Semantic Delta Analysis
        t1 = time.perf_counter()
        base_map = {u.stable_lineage_key: u for u in eff_base_uses}
        modified_pairs = []
        for u_target in eff_target_uses:
            u_base = base_map.get(u_target.stable_lineage_key)
            if u_base and (
                getattr(u_base, "context_hash", None) != getattr(u_target, "context_hash", None)
                or getattr(u_base, "duration_or_prominence", None) != getattr(u_target, "duration_or_prominence", None)
                or getattr(u_base, "context", None) != getattr(u_target, "context", None)
            ):
                modified_pairs.append((u_base, u_target))

        chosen_pair = None
        if modified_pairs:
            poster_pair = next((p for p in modified_pairs if p[1].stable_lineage_key == "poster_noir_detective_magazine"), None)
            chosen_pair = poster_pair or modified_pairs[0]
        elif "poster_noir_detective_magazine" in base_map and any(u.stable_lineage_key == "poster_noir_detective_magazine" for u in eff_target_uses):
            chosen_pair = (base_map["poster_noir_detective_magazine"], next(u for u in eff_target_uses if u.stable_lineage_key == "poster_noir_detective_magazine"))
        elif eff_target_uses and eff_base_uses:
            chosen_pair = (eff_base_uses[0], eff_target_uses[0])

        if chosen_pair:
            u_b, u_t = chosen_pair
            gemini_delta = await self.gemini.analyze_scene_delta(
                asset_name=u_t.description,
                v7_context=u_b.context,
                v7_prominence=u_b.duration_or_prominence,
                v8_context=u_t.context,
                v8_prominence=u_t.duration_or_prominence,
            )
            traces.append(
                WorkflowStepTrace(
                    step_name="semantic_delta_analysis",
                    component="Gemini 2.5 Flash",
                    status="SUCCESS",
                    duration_ms=round((time.perf_counter() - t1) * 1000, 2),
                    details={
                        "is_material": gemini_delta.is_material,
                        "prominence_shift": gemini_delta.prominence_shift,
                        "recommended_action": gemini_delta.recommended_action,
                        "evaluated_asset": u_t.stable_lineage_key,
                    },
                )
            )
        else:
            traces.append(
                WorkflowStepTrace(
                    step_name="semantic_delta_analysis",
                    component="Gemini 2.5 Flash",
                    status="SKIPPED",
                    duration_ms=round((time.perf_counter() - t1) * 1000, 2),
                    details={"reason": "No candidate creative uses for semantic delta comparison"},
                )
            )

        # Step 3: Invalidation Engine Dependency Evaluation
        t2 = time.perf_counter()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=eff_base_uses,
            target_uses=eff_target_uses,
            prior_decisions=eff_prior_decisions,
            evidence_snapshots=eff_evidence,
            target_version_id=target_version_id,
        )
        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]
        traces.append(
            WorkflowStepTrace(
                step_name="deterministic_dependency_invalidation",
                component="InvalidationEngine",
                status="SUCCESS",
                duration_ms=round((time.perf_counter() - t2) * 1000, 2),
                details={
                    "carried_forward": len(carried),
                    "reopened": len(stale),
                    "policy": InvalidationEngine.POLICY_VERSION,
                },
            )
        )

        # Step 4: Selective Revalidation Planning (RevalidationPlanner)
        # Selectively plans research ONLY for claims requiring external evidence revalidation
        # Strictly skips the 10 unchanged carried-forward claims, enforcing minimal API call budget
        t_plan = time.perf_counter()
        revalidation_plan = self.revalidation_planner.plan_revalidation(
            validity_results=validity_results,
            target_uses=eff_target_uses,
            target_version_id=target_version_id,
        )
        traces.append(
            WorkflowStepTrace(
                step_name="selective_revalidation_planning",
                component="RevalidationPlanner",
                status="SUCCESS",
                duration_ms=round((time.perf_counter() - t_plan) * 1000, 2),
                details={
                    "planned_count": revalidation_plan.planned_count,
                    "skipped_count": revalidation_plan.skipped_count,
                    "planned_keys": [r.stable_lineage_key for r in revalidation_plan.planned_requests],
                    "api_call_budget_enforced": revalidation_plan.api_call_budget_enforced,
                },
            )
        )

        # Step 5: Targeted Parallel Search Execution (ParallelSearchService)
        # Formulates and executes targeted queries tailored for Parallel Search API:
        # Query 1: 'Shadows of Manhattan Detective Magazine 1944 copyright renewal public domain LOC'
        # Query 2: 'Midnight Serenade jazz cue ASCAP BMI Vanguard Media copyright assignment dispute'
        refreshed_evidence: Dict[str, PublicEvidenceSnapshot] = {}
        for req in revalidation_plan.planned_requests:
            t_search = time.perf_counter()
            evidence = await self.parallel.search(
                query=req.query,
                use_id=req.decision_id,
                stable_lineage_key=req.stable_lineage_key,
                expected_stance=req.expected_stance,
            )
            refreshed_evidence[req.stable_lineage_key] = evidence
            traces.append(
                WorkflowStepTrace(
                    step_name=f"parallel_targeted_search_{req.stable_lineage_key}",
                    component="Parallel Search API",
                    status="SUCCESS" if evidence.stance != EvidenceStance.INSUFFICIENT else "FAIL_CLOSED",
                    duration_ms=round((time.perf_counter() - t_search) * 1000, 2),
                    details={
                        "query": req.query,
                        "source_title": evidence.source_title,
                        "source_url": evidence.source_url,
                        "stance": evidence.stance.value,
                        "provider_call_id": evidence.provider_call_id,
                        "http_status": evidence.http_status,
                    },
                )
            )

        # Step 6: Evidence & Private Contract Reconciliation (EvidenceReconciler)
        # Categorizes stances and applies private contract reconciliation:
        # A public catalog ownership shift alone DOES NOT void an existing valid, active, perpetual
        # private agreement unless an active revocation or judicial injunction is proven.
        t_recon = time.perf_counter()
        reconciliation_results = self.evidence_reconciler.reconcile_all(
            validity_results=validity_results,
            evidence_snapshots=refreshed_evidence,
            contracts=contracts,
            update_validity_in_place=True,
        )
        traces.append(
            WorkflowStepTrace(
                step_name="evidence_and_contract_reconciliation",
                component="EvidenceReconciler",
                status="SUCCESS",
                duration_ms=round((time.perf_counter() - t_recon) * 1000, 2),
                details={
                    "reconciled_claims": len(reconciliation_results),
                    "contract_shields_applied": sum(1 for r in reconciliation_results if r.contract_shield_applied),
                    "fail_closed_insufficient": sum(1 for r in reconciliation_results if r.reconciled_stance == EvidenceStance.INSUFFICIENT),
                },
            )
        )

        # Recalculate carried and stale claims following reconciliation
        carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in validity_results if v.state == DecisionState.STALE]

        # Step 7: Gemini Clearance Briefings
        briefings: Dict[str, ClearanceBriefing] = {}
        for item in stale:
            ev = refreshed_evidence.get(item.stable_lineage_key)
            if ev and ev.stance != EvidenceStance.INSUFFICIENT:
                briefing = await self.gemini.synthesize_counsel_briefing(
                    asset_name=item.stable_lineage_key,
                    reason_code=item.reason_code,
                    evidence_excerpt=ev.excerpt,
                    source_title=ev.source_title,
                    source_url=ev.source_url,
                )
                briefings[item.stable_lineage_key] = briefing

        # Construct Claims payload
        claims_payload = []
        use_map = {u.stable_lineage_key: u for u in eff_target_uses}
        for v in validity_results:
            key = v.stable_lineage_key
            use = use_map.get(key)
            ev = refreshed_evidence.get(key) or v.evidence_snapshot

            claims_payload.append(
                {
                    "stable_lineage_key": key,
                    "asset_type": use.asset_type if use else "unknown",
                    "description": use.description if use else key,
                    "scene": use.scene_or_timecode if use else "Unknown",
                    "prominence": use.duration_or_prominence if use else "",
                    "state": v.state.value,
                    "reason_code": v.reason_code,
                    "revalidation_action": v.revalidation_action,
                    "evidence": {
                        "provider": ev.provider if ev else "Parallel",
                        "source_title": ev.source_title if ev else "",
                        "source_url": ev.source_url if ev else "",
                        "excerpt": ev.excerpt if ev else "",
                        "stance": ev.stance.value if ev else "supporting",
                        "latency_ms": ev.retrieval_latency_ms if ev else None,
                        "call_id": ev.provider_call_id if ev else None,
                    }
                    if ev
                    else None,
                }
            )

        total_duration = round((time.perf_counter() - overall_start) * 1000, 2)

        return WorkflowRunResult(
            run_id=run_id,
            base_version=base_version_id,
            target_version=target_version_id,
            total_claims=len(validity_results),
            carried_forward_count=len(carried),
            reopened_count=len(stale),
            claims=claims_payload,
            counsel_briefings=briefings,
            execution_traces=traces,
            total_duration_ms=total_duration,
            revalidation_plan=revalidation_plan,
            reconciliation_results=reconciliation_results,
        )

    async def execute_adk_workflow(
        self,
        contracts: Optional[List[ContractAgreement]] = None,
        force_offline: bool = False,
    ) -> WorkflowRunResult:
        """
        Executes the clearance change control workflow via Google ADK & Agent Builder pipeline.
        Provides dual-mode execution (live Runner when credentials exist, resilient offline fallback).
        """
        if self._adk_pipeline is None:
            from backend.orchestration.adk_pipeline import ADKClearancePipeline
            self._adk_pipeline = ADKClearancePipeline(
                gemini_service=self.gemini,
                parallel_service=self.parallel,
                revalidation_planner=self.revalidation_planner,
                evidence_reconciler=self.evidence_reconciler,
            )
        return await self._adk_pipeline.execute(
            contracts=contracts,
            force_offline=force_offline,
        )

