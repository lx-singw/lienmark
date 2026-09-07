"""
trap_handler.py

Post-inference validation, deterministic reconciliation, and safe trapping
of adversarial prompt injection payloads into canonical clearance claim models.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import List, Optional

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.intake.injection_detector import InjectionDetectionResult
from backend.domain.models import CreativeUse
from backend.storage.schema import Claim


def create_trapped_extracted_claim(
    detection: InjectionDetectionResult,
    production_id: str = "prod_default",
) -> ExtractedClaim:
    """
    Creates a canonical ExtractedClaim securely trapping an adversarial injection directive.
    """
    claim_id = f"clm_trap_{uuid.uuid4().hex[:8]}"
    words = detection.suspicious_span.split()[:14]
    desc = "Suspicious embedded instruction: " + " ".join(words)
    return ExtractedClaim(
        claim_id=claim_id,
        category=ClaimCategory.OTHER,
        scene_or_timecode=detection.scene_ref or "Unknown Scene",
        extracted_description=desc,
        context_snippet=detection.suspicious_span[:120],
        confidence=1.0,
        needs_clarification=True,
        flagged_reason="suspicious_embedded_instruction",
    )


def create_trapped_creative_use(
    detection: InjectionDetectionResult,
    version_id: str = "v1",
) -> CreativeUse:
    """
    Creates a canonical CreativeUse domain node trapping an adversarial injection directive.
    """
    use_id = f"use_trap_{uuid.uuid4().hex[:8]}"
    words = detection.suspicious_span.split()[:14]
    desc = "Suspicious embedded instruction: " + " ".join(words)
    ctx_hash = hashlib.sha256(detection.suspicious_span.encode("utf-8")).hexdigest()
    return CreativeUse(
        use_id=use_id,
        version_id=version_id,
        scene_or_timecode=detection.scene_ref or "Unknown Scene",
        asset_type="other",
        description=desc,
        duration_or_prominence="adversarial_embedded_note",
        context=detection.suspicious_span[:150],
        stable_lineage_key=f"trap_lineage_{ctx_hash[:12]}",
        context_hash=ctx_hash,
        needs_clarification=True,
        metadata={
            "flagged_reason": "suspicious_embedded_instruction",
            "matched_rules": detection.matched_rules,
            "confidence_score": detection.confidence_score,
        },
    )


def create_trapped_claim(
    detection: InjectionDetectionResult,
    production_id: str = "prod_default",
) -> Claim:
    """
    Creates a storage Claim securely trapping an adversarial injection directive.
    """
    claim_id = f"clm_trap_{uuid.uuid4().hex[:8]}"
    words = detection.suspicious_span.split()[:14]
    desc = "Suspicious embedded instruction: " + " ".join(words)
    return Claim(
        claim_id=claim_id,
        production_id=production_id,
        type="other",
        scene_ref=detection.scene_ref or "Unknown Scene",
        extracted_description=desc,
        needs_clarification=True,
        flagged_reason="suspicious_embedded_instruction",
    )


def reconcile_extracted_claims(
    model_claims: List[ExtractedClaim],
    pre_detections: List[InjectionDetectionResult],
    production_id: str = "prod_default",
) -> List[ExtractedClaim]:
    """
    Ensures any detected injection payload is represented in the ExtractedClaim list.
    Fails closed: if the LLM omitted or was blinded by an injection, this injects the trap.
    """
    reconciled = list(model_claims)
    existing_trap_reasons = {
        c.flagged_reason for c in reconciled if c.flagged_reason is not None
    }

    for det in pre_detections:
        if not det.is_suspicious:
            continue
        if "suspicious_embedded_instruction" not in existing_trap_reasons:
            reconciled.append(
                create_trapped_extracted_claim(det, production_id=production_id)
            )
            existing_trap_reasons.add("suspicious_embedded_instruction")

    return reconciled


def reconcile_creative_uses(
    model_uses: List[CreativeUse],
    pre_detections: List[InjectionDetectionResult],
    version_id: str = "v1",
) -> List[CreativeUse]:
    """
    Reconciles CreativeUse models against pre-inference injection detections.
    """
    reconciled = list(model_uses)
    has_trap = any(
        u.metadata.get("flagged_reason") == "suspicious_embedded_instruction"
        for u in reconciled
    )

    for det in pre_detections:
        if det.is_suspicious and not has_trap:
            reconciled.append(create_trapped_creative_use(det, version_id=version_id))
            has_trap = True

    return reconciled


def reconcile_claims(
    model_claims: List[Claim],
    pre_detections: List[InjectionDetectionResult],
    production_id: str = "prod_default",
) -> List[Claim]:
    """
    Reconciles storage Claim models against pre-inference injection detections.
    """
    reconciled = list(model_claims)
    has_trap = any(
        c.flagged_reason == "suspicious_embedded_instruction" for c in reconciled
    )

    for det in pre_detections:
        if det.is_suspicious and not has_trap:
            reconciled.append(create_trapped_claim(det, production_id=production_id))
            has_trap = True

    return reconciled


def evaluate_zero_claim_anomaly(
    claims_count: int,
    scene_count: int,
    word_count: int,
    scene_ref: str = "Script Intake",
) -> Optional[ExtractedClaim]:
    """
    Flags statistically improbable clean extractions on scripts exceeding complexity thresholds.
    """
    if claims_count == 0 and (scene_count >= 5 or word_count >= 500):
        return ExtractedClaim(
            claim_id=f"clm_anomaly_{uuid.uuid4().hex[:8]}",
            category=ClaimCategory.OTHER,
            scene_or_timecode=scene_ref,
            extracted_description="Statistically improbable clean script with zero extracted claims",
            context_snippet=f"Script contains {scene_count} scenes and {word_count} words but yielded 0 claims",
            confidence=1.0,
            needs_clarification=True,
            flagged_reason="statistically_improbable_clean_script",
        )
    return None
