"""
backend/agents/research/subgoal_planner.py

Clearance subgoal taxonomy synthesis and status tracking.
Sprint 3.2: Multi-Hop Planning & Investigation DAG Architecture.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.planner_types import (
    ExtractedLead,
    InvestigationSubgoal,
    SubgoalStatus,
    SubgoalType,
)

SUBGOAL_TEMPLATES: Dict[ClaimCategory, List[Tuple[SubgoalType, str, int]]] = {
    ClaimCategory.MUSIC: [
        (SubgoalType.COMPOSITION_PUBLISHING, "Clear musical composition publishing and PRO songwriter rights.", 1),
        (SubgoalType.MASTER_RECORDING, "Clear master sound recording copyright and record label ownership.", 2),
        (SubgoalType.SYNC_LICENSE, "Verify synchronization licensing availability and rights holder terms.", 3),
    ],
    ClaimCategory.BRAND: [
        (SubgoalType.TRADEMARK_CLASS, "Clear trademark registration, Nice classification, and goods/services scope.", 1),
    ],
    ClaimCategory.REAL_PERSON: [
        (SubgoalType.LIKENESS_ESTATE, "Clear right of publicity, estate administration, and persona licensing.", 1),
    ],
    ClaimCategory.HISTORICAL_FIGURE: [
        (SubgoalType.LIKENESS_ESTATE, "Clear right of publicity, estate administration, and persona licensing.", 1),
        (SubgoalType.PUBLIC_DOMAIN_PROOF, "Verify public domain status of historical persona and lack of active marks.", 2),
    ],
}


class SubgoalPlanner:
    """Decomposes claims into domain subgoals and tracks their evidentiary progress."""

    def generate_subgoals(self, claim: ExtractedClaim) -> List[InvestigationSubgoal]:
        """Dynamically breaks down an intake claim into prioritized clearance subgoals."""
        cid = claim.claim_id
        templates = SUBGOAL_TEMPLATES.get(
            claim.category,
            [
                (SubgoalType.PUBLIC_DOMAIN_PROOF, "Verify copyright term, renewal records, and public domain status.", 1),
                (SubgoalType.SYNC_LICENSE, "Identify archival licensing agency or rights holder representation.", 2),
            ],
        )
        subgoals = [
            InvestigationSubgoal(
                id=f"{cid}_sub_{i}",
                subgoal_type=sg_type,
                description=desc,
                priority=prio,
            )
            for i, (sg_type, desc, prio) in enumerate(templates, 1)
        ]
        desc_lower = claim.extracted_description.lower()
        if claim.category == ClaimCategory.MUSIC and any(w in desc_lower for w in ("sample", "interpolat")):
            subgoals.append(
                InvestigationSubgoal(
                    id=f"{cid}_sub_sample",
                    subgoal_type=SubgoalType.SAMPLE_CLEARANCE,
                    description="Investigate underlying sample clearance and interpolated rights.",
                    priority=4,
                )
            )
        return subgoals

    def resolve_lead_subgoal(
        self, subgoals: List[InvestigationSubgoal], lead: Any
    ) -> Optional[str]:
        """Matches an extracted lead to an existing subgoal ID or returns the first subgoal ID."""
        target_type = getattr(lead, "subgoal_type", None)
        if not target_type:
            entity_type = str(getattr(lead, "entity_type", "")).lower()
            if "publisher" in entity_type:
                target_type = SubgoalType.COMPOSITION_PUBLISHING
            elif "label" in entity_type:
                target_type = SubgoalType.MASTER_RECORDING
            elif "estate" in entity_type:
                target_type = SubgoalType.LIKENESS_ESTATE
            elif "assignee" in entity_type:
                target_type = SubgoalType.TRADEMARK_CLASS

        if target_type:
            for sg in subgoals:
                if sg.subgoal_type == target_type:
                    return sg.id
        return subgoals[0].id if subgoals else None

    def update_subgoals(
        self, subgoals: List[InvestigationSubgoal], subgoal_id: Optional[str], confidence: float
    ) -> None:
        """Updates target subgoal confidence score and status."""
        if not subgoal_id:
            return
        for sg in subgoals:
            if sg.id == subgoal_id:
                sg.confidence_score = max(sg.confidence_score, confidence)
                if sg.confidence_score >= 0.80:
                    sg.status = SubgoalStatus.COMPLETED
                elif sg.status == SubgoalStatus.PENDING:
                    sg.status = SubgoalStatus.IN_PROGRESS
