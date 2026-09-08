"""
backend/core/conflict_arbiter.py

Corroboration Engine and Conflict Arbiter for Sprint 3.3.
Compares multi-source evidence, detects dual-layer conflicts (e.g. Apollo 11),
evaluates stance pairs/sets, and routes unresolved exceptions to Form E&O-2026.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence
from urllib.parse import urlsplit

from backend.core.conflict_heuristics import ConflictHeuristics
from backend.core.conflict_types import (
    ArbitrationResult,
    ConflictStance,
    DualLayerConflictInfo,
    EvidenceFinding,
    StancePairEvaluation,
)
from backend.domain.models import ExceptionsScheduleItem

logger = logging.getLogger("lienmark.conflict_arbiter")


class CorroborationEngine:
    """Classifies pairwise and aggregate stances across multi-source evidence."""

    @staticmethod
    def is_insufficient(f: EvidenceFinding) -> bool:
        """Determines if a finding represents a failed or empty search result."""
        if f.http_status and f.http_status in (408, 429, 500, 502, 503, 504):
            return True
        text = f"{f.excerpt} {f.snippet or ''}".strip().lower()
        return not text or "timed out" in text or "search failure" in text

    @classmethod
    def classify_pair(cls, a: EvidenceFinding, b: EvidenceFinding) -> StancePairEvaluation:
        """Classifies stance between two evidence findings with dual-layer distinction."""
        if cls.is_insufficient(a) or cls.is_insufficient(b):
            return StancePairEvaluation(
                source_a_id=a.finding_id, source_b_id=b.finding_id,
                stance=ConflictStance.INSUFFICIENT, explanation="Insufficient evidence or timeout.",
            )
        fed_a, fed_b = ConflictHeuristics.is_federal(a), ConflictHeuristics.is_federal(b)
        net_a, net_b = ConflictHeuristics.is_network_master(a), ConflictHeuristics.is_network_master(b)
        if (fed_a and net_b) or (fed_b and net_a):
            return StancePairEvaluation(
                source_a_id=a.finding_id, source_b_id=b.finding_id,
                stance=ConflictStance.NEUTRAL, is_dual_layer_conflict=True,
                explanation="Dual-layer distinction: public domain composition and protected recording are valid.",
            )
        pd_a, pd_b = ConflictHeuristics.is_public_domain(a), ConflictHeuristics.is_public_domain(b)
        cp_a, cp_b = ConflictHeuristics.is_copyrighted(a), ConflictHeuristics.is_copyrighted(b)
        same_layer = (a.rights_layer == b.rights_layer) if (a.rights_layer and b.rights_layer) else True
        if (pd_a and cp_b and same_layer) or (pd_b and cp_a and same_layer):
            return StancePairEvaluation(
                source_a_id=a.finding_id, source_b_id=b.finding_id,
                stance=ConflictStance.CONTRADICTORY,
                explanation="Direct contradiction: incompatible assertions about the same work and rights layer.",
            )
        if (pd_a and pd_b) or (cp_a and cp_b and a.asserted_owner == b.asserted_owner):
            return StancePairEvaluation(
                source_a_id=a.finding_id, source_b_id=b.finding_id,
                stance=ConflictStance.CORROBORATING, explanation="Independent sources corroborate rights status.",
            )
        return StancePairEvaluation(
            source_a_id=a.finding_id, source_b_id=b.finding_id,
            stance=ConflictStance.NEUTRAL, explanation="Neutral or background mention without definitive claim.",
        )

    @classmethod
    def classify_set(cls, findings: Sequence[EvidenceFinding]) -> ConflictStance:
        """Classifies overall stance across an entire collection of evidence findings."""
        valid = [f for f in findings if not cls.is_insufficient(f)]
        if not valid:
            return ConflictStance.INSUFFICIENT
        if len(valid) == 1:
            return ConflictStance.NEUTRAL
        has_corroborating = False
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                res = cls.classify_pair(valid[i], valid[j])
                if res.stance == ConflictStance.CONTRADICTORY:
                    return ConflictStance.CONTRADICTORY
                if res.stance == ConflictStance.CORROBORATING:
                    has_corroborating = True
        return ConflictStance.CORROBORATING if has_corroborating else ConflictStance.NEUTRAL


class ConflictArbiter:
    """Arbitrates multi-source evidence disputes and formats exception schedule routing."""

    @classmethod
    def _extract_citations(cls, findings: Sequence[EvidenceFinding]) -> List[Dict[str, str]]:
        citations: List[Dict[str, str]] = []
        for f in findings:
            dom = f.domain or (urlsplit(f.source_url).netloc if f.source_url else "search.parallel.ai")
            citations.append({
                "source_title": f.source_title, "source_url": f.source_url or "",
                "excerpt": f.excerpt, "domain": dom, "authority_tier": f.authority_tier.value,
            })
        return citations

    @classmethod
    def _build_dual_layer(cls, findings: Sequence[EvidenceFinding]) -> Optional[DualLayerConflictInfo]:
        feds = [f.finding_id for f in findings if ConflictHeuristics.is_federal(f)]
        nets = [f.finding_id for f in findings if ConflictHeuristics.is_network_master(f)]
        if feds and nets:
            return DualLayerConflictInfo(
                is_dual_layer=True, underlying_status="public_domain", underlying_source_ids=feds,
                master_status="licensing_required", master_source_ids=nets,
                rationale="Factual transcript/raw creation is US Gov (17 U.S.C. § 105) public domain, but broadcast commentary/master requires private clearance.",
            )
        return None

    @classmethod
    def _build_contradictory_result(
        cls, claim_id: str, findings: Sequence[EvidenceFinding], citations: List[Dict[str, str]]
    ) -> ArbitrationResult:
        """Constructs an ArbitrationResult for genuine contradictory findings."""
        conf_sources = [f.model_dump() for f in findings if not CorroborationEngine.is_insufficient(f)]
        return ArbitrationResult(
            claim_id=claim_id, conflict_detected=True, overall_stance=ConflictStance.CONTRADICTORY,
            risk_score=0.85, conflict_sources=conf_sources, dual_layer=None,
            route_to_exceptions_schedule=True, exceptions_schedule_state="unresolved_exception",
            recommended_action="Manual attorney review required: conflicting ownership claims across sources.",
            summary=f"Contradictory evidence detected for claim {claim_id}.", citations=citations,
        )

    @classmethod
    def _build_dual_layer_result(
        cls, claim_id: str, findings: Sequence[EvidenceFinding], dual_layer: DualLayerConflictInfo, citations: List[Dict[str, str]]
    ) -> ArbitrationResult:
        """Constructs an ArbitrationResult for dual-layer distinction findings."""
        return ArbitrationResult(
            claim_id=claim_id, conflict_detected=False, overall_stance=ConflictStance.NEUTRAL,
            risk_score=0.30, dual_layer=dual_layer, route_to_exceptions_schedule=False,
            exceptions_schedule_state="carried_forward",
            recommended_action="Leave recording clearance outstanding.",
            summary=f"Dual-layer findings for claim {claim_id}.", citations=citations,
        )

    @classmethod
    def arbitrate(
        cls, claim_id: str, findings: Sequence[EvidenceFinding], asset_type: str = "archival_footage",
    ) -> ArbitrationResult:
        """Arbitrates multi-source evidence, flagging dual-layer conflicts and exception routing."""
        citations = cls._extract_citations(findings)
        stance = CorroborationEngine.classify_set(findings)
        dual_layer = cls._build_dual_layer(findings)
        if stance == ConflictStance.CONTRADICTORY:
            return cls._build_contradictory_result(claim_id, findings, citations)
        if dual_layer:
            return cls._build_dual_layer_result(claim_id, findings, dual_layer, citations)
        if stance == ConflictStance.CORROBORATING:
            corr_sources = [f.model_dump() for f in findings]
            return ArbitrationResult(
                claim_id=claim_id, conflict_detected=False, overall_stance=ConflictStance.CORROBORATING,
                risk_score=0.10, corroborating_sources=corr_sources, route_to_exceptions_schedule=False,
                exceptions_schedule_state="carried_forward", recommended_action="Proceed: public domain corroborated.",
                summary=f"Independent sources corroborate rights status for claim {claim_id}.", citations=citations,
            )
        if stance == ConflictStance.INSUFFICIENT:
            return ArbitrationResult(
                claim_id=claim_id, conflict_detected=False, overall_stance=ConflictStance.INSUFFICIENT,
                risk_score=0.65, route_to_exceptions_schedule=True, exceptions_schedule_state="unresolved_exception",
                recommended_action="Reinvestigate: search findings insufficient or timed out.",
                summary=f"Search findings insufficient for claim {claim_id}.", citations=citations,
            )
        return ArbitrationResult(
            claim_id=claim_id, conflict_detected=False, overall_stance=ConflictStance.NEUTRAL,
            risk_score=0.40, route_to_exceptions_schedule=False, exceptions_schedule_state="carried_forward",
            recommended_action="Informational records without definitive conflict.",
            summary=f"Neutral evidence findings for claim {claim_id}.", citations=citations,
        )

    @classmethod
    def to_exceptions_schedule_item(
        cls, result: ArbitrationResult, asset_type: str, description: str, scene_or_timecode: str = "00:00:00",
    ) -> ExceptionsScheduleItem:
        """Converts an arbitration result into an ExceptionsScheduleItem for Form E&O-2026."""
        eval_state = "exception" if result.route_to_exceptions_schedule else "carried_forward"
        inval_reason = "Multi-source rights conflict detected" if result.conflict_detected else None
        return ExceptionsScheduleItem(
            stable_lineage_key=result.claim_id, asset_type=asset_type, description=description,
            scene_or_timecode=scene_or_timecode, v7_decision_status="needs_review",
            v8_evaluation_state=eval_state, invalidation_reason=inval_reason,
            counsel_action=result.recommended_action, evidence_citations=result.citations,
        )


def arbitrate_claim_conflicts(
    claim_id: str, findings: Sequence[EvidenceFinding], asset_type: str = "archival_footage",
) -> ArbitrationResult:
    """Convenience functional wrapper for multi-source conflict arbitration."""
    return ConflictArbiter.arbitrate(claim_id=claim_id, findings=findings, asset_type=asset_type)
