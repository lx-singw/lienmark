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
    DecisionState,
    DecisionValidity,
    PublicEvidenceSnapshot,
    ReattestationRequest,
    ExceptionsSchedule,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.services.gemini_service import GeminiService, ClearanceBriefing
from backend.services.parallel_service import ParallelSearchService
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)


class WorkflowStepTrace(BaseModel):
    step_name: str
    component: str  # Gemini, InvalidationEngine, ParallelSearch
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


class LienmarkWorkflow:
    """
    Main Agentic Workflow for Lienmark.
    Follows Google Cloud Agent Builder / ADK orchestration principles.
    """

    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        parallel_service: Optional[ParallelSearchService] = None,
    ):
        self.gemini = gemini_service or GeminiService()
        self.parallel = parallel_service or ParallelSearchService()

    async def execute_drift_detection(self) -> WorkflowRunResult:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        overall_start = time.perf_counter()
        traces: List[WorkflowStepTrace] = []

        # Step 1: Ingest versions & golden fixtures
        t0 = time.perf_counter()
        v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()
        traces.append(
            WorkflowStepTrace(
                step_name="version_ingestion",
                component="LienmarkEngine",
                status="SUCCESS",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details={"v7_uses": len(v7_uses), "v8_uses": len(v8_uses)},
            )
        )

        # Step 2: Gemini Semantic Delta Analysis
        t1 = time.perf_counter()
        v7_poster = next(u for u in v7_uses if u.stable_lineage_key == "poster_noir_detective_magazine")
        v8_poster = next(u for u in v8_uses if u.stable_lineage_key == "poster_noir_detective_magazine")
        gemini_delta = await self.gemini.analyze_scene_delta(
            asset_name=v8_poster.description,
            v7_context=v7_poster.context,
            v7_prominence=v7_poster.duration_or_prominence,
            v8_context=v8_poster.context,
            v8_prominence=v8_poster.duration_or_prominence,
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
                },
            )
        )

        # Step 3: Invalidation Engine Dependency Evaluation
        t2 = time.perf_counter()
        validity_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v8",
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

        # Step 4: Targeted Parallel Search Refresh for Stale Items
        refreshed_evidence: Dict[str, PublicEvidenceSnapshot] = {}
        for item in stale:
            t_search = time.perf_counter()
            query = (
                "1946 Crime Detective Magazine Shadows Over Broadway copyright renewal"
                if "poster" in item.stable_lineage_key
                else "Midnight Serenade jazz sync rights copyright owner 2026"
            )
            evidence = await self.parallel.search(
                query=query,
                use_id=item.decision_id,
                stable_lineage_key=item.stable_lineage_key,
            )
            refreshed_evidence[item.stable_lineage_key] = evidence
            traces.append(
                WorkflowStepTrace(
                    step_name=f"parallel_targeted_search_{item.stable_lineage_key}",
                    component="Parallel Search API",
                    status="SUCCESS",
                    duration_ms=round((time.perf_counter() - t_search) * 1000, 2),
                    details={
                        "query": query,
                        "source_title": evidence.source_title,
                        "source_url": evidence.source_url,
                        "stance": evidence.stance.value,
                        "provider_call_id": evidence.provider_call_id,
                    },
                )
            )

        # Step 5: Gemini Clearance Briefings
        briefings: Dict[str, ClearanceBriefing] = {}
        for item in stale:
            ev = refreshed_evidence.get(item.stable_lineage_key)
            if ev:
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
        use_map = {u.stable_lineage_key: u for u in v8_uses}
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
            base_version="v7",
            target_version="v8",
            total_claims=len(validity_results),
            carried_forward_count=len(carried),
            reopened_count=len(stale),
            claims=claims_payload,
            counsel_briefings=briefings,
            execution_traces=traces,
            total_duration_ms=total_duration,
        )
