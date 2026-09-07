"""
backend/core/anomaly_detector.py

Layer 3 statistical anomaly engine evaluating script complexity vs claim density,
scene counts, page counts, and word counts.
Emits AnomalyReport and injects statistically_improbable_clean_script trap claims.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.agents.intake.claim_types import ExtractedClaim
from backend.domain.models import CreativeUse


class AnomalyReport(BaseModel):
    """Telemetry report emitted by Layer 3 statistical anomaly engine."""

    is_anomalous: bool = Field(
        description="True if script complexity vs claim extraction is anomalous"
    )
    anomaly_type: Optional[str] = Field(
        default=None, description="Identifier of detected statistical anomaly"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in anomaly detection"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Metrics driving anomaly score"
    )
    recommended_action: str = Field(
        default="allow", description="Recommended pipeline routing action"
    )


def compute_claim_density(claims_count: int, word_count: int) -> float:
    """Computes claims per 1,000 words to evaluate statistical plausibility."""
    if word_count <= 0:
        return 0.0
    return round((claims_count / word_count) * 1000.0, 4)


def evaluate_script_anomaly(
    claims_count: int,
    scene_count: int,
    word_count: int,
    page_count: int = 0,
) -> AnomalyReport:
    """
    Evaluates script volume and complexity against extracted claims count.
    Flags zero-claim extractions on complex scripts as statistically improbable.
    """
    is_complex = scene_count >= 5 or word_count >= 500 or page_count >= 5
    density = compute_claim_density(claims_count, word_count)
    metrics = {
        "claims_count": claims_count,
        "scene_count": scene_count,
        "word_count": word_count,
        "page_count": page_count,
        "density_per_kword": density,
    }

    if claims_count == 0 and is_complex:
        return AnomalyReport(
            is_anomalous=True,
            anomaly_type="statistically_improbable_clean_script",
            confidence=1.0,
            details=metrics,
            recommended_action="flag_for_human_review",
        )

    return AnomalyReport(
        is_anomalous=False,
        anomaly_type=None,
        confidence=0.0,
        details=metrics,
        recommended_action="allow",
    )


def generate_trap_claim_if_anomalous(
    report: AnomalyReport,
    scene_ref: str = "Script Intake",
) -> Optional[ExtractedClaim]:
    """Constructs a trapped ExtractedClaim if the anomaly report warrants gating."""
    if not report.is_anomalous:
        return None

    from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim

    scenes = report.details.get("scene_count", 0)
    words = report.details.get("word_count", 0)
    pages = report.details.get("page_count", 0)
    reason = report.anomaly_type or "statistically_improbable_clean_script"

    return ExtractedClaim(
        claim_id=f"clm_anomaly_{uuid.uuid4().hex[:8]}",
        category=ClaimCategory.OTHER,
        scene_or_timecode=scene_ref,
        extracted_description="Statistically improbable clean script with zero extracted claims",
        context_snippet=f"Script contains {scenes} scenes, {pages} pages, {words} words but yielded 0 claims",
        confidence=1.0,
        needs_clarification=True,
        flagged_reason=reason,
    )


def generate_trap_use_if_anomalous(
    report: AnomalyReport,
    version_id: str = "v1",
    scene_ref: str = "Script Intake",
) -> Optional[CreativeUse]:
    """
    Constructs a trapped CreativeUse domain model if an anomaly is detected.
    """
    if not report.is_anomalous:
        return None

    scenes = report.details.get("scene_count", 0)
    words = report.details.get("word_count", 0)
    pages = report.details.get("page_count", 0)
    reason = report.anomaly_type or "statistically_improbable_clean_script"

    return CreativeUse(
        use_id=f"use_anomaly_{uuid.uuid4().hex[:8]}",
        version_id=version_id,
        scene_or_timecode=scene_ref,
        asset_type="other",
        description="Statistically improbable clean script with zero extracted claims",
        duration_or_prominence="statistical_anomaly_flag",
        context=f"Complexity metrics: {scenes} scenes, {pages} pages, {words} words with 0 claims",
        stable_lineage_key=f"trap_anomaly_{uuid.uuid4().hex[:8]}",
        context_hash="0" * 64,
        needs_clarification=True,
        metadata={
            "flagged_reason": reason,
            "anomaly_report": report.model_dump(),
        },
    )


def reconcile_anomalies_into_claims(
    claims: List[ExtractedClaim],
    scene_count: int,
    word_count: int,
    page_count: int = 0,
    scene_ref: str = "Script Intake",
) -> List[ExtractedClaim]:
    """
    Gating helper: evaluates script anomaly and injects trap claim if required.
    """
    report = evaluate_script_anomaly(
        claims_count=len(claims),
        scene_count=scene_count,
        word_count=word_count,
        page_count=page_count,
    )
    trap = generate_trap_claim_if_anomalous(report, scene_ref=scene_ref)
    if trap is not None:
        reconciled = list(claims)
        reconciled.append(trap)
        return reconciled
    return claims
