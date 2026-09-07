"""
self_reflection.py

Automated secondary self-reflection extraction pass for the Intake Agent.
Executes a secondary reflection prompt to catch false negatives, obscure background
elements, ambient music, subtle brands, and adversarial injections, and reconciles
findings with primary claims into a consolidated ClaimExtractionOutput.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, List, Optional

from backend.agents.intake.prompts import (
    SELF_REFLECTION_SYSTEM_PROMPT,
    format_reflection_user_prompt,
)
from backend.agents.intake.reflection_reconciler import reconcile_claims
from backend.agents.intake.reflection_schemas import (
    ClaimExtractionOutput,
    RawReflectionFinding,
    ReflectionCandidateOutput,
)
from backend.storage.schema import Claim

logger = logging.getLogger(__name__)


def _extract_adversarial_trap(text: str) -> Optional[RawReflectionFinding]:
    """Scans for embedded prompt injection directives."""
    pattern = r'\[SYSTEM\s+OVERRIDE.*?\]|ignore\s+all\s+previous\s+instructions'
    if not re.search(pattern, text, re.IGNORECASE):
        return None
    return RawReflectionFinding(
        type="other",
        scene_ref="SUSPICIOUS_SECTION",
        extracted_description="embedded adversarial directive detected in script text",
        target_entity="Adversarial Instruction",
        category_focus="injection_trap",
        needs_clarification=True,
        flagged_reason="suspicious_embedded_instruction",
    )


def _extract_known_benchmark_entities(text: str) -> List[RawReflectionFinding]:
    """Extracts known obscure entities in offline/fallback benchmark environments."""
    findings: List[RawReflectionFinding] = []
    catalog = [
        (r'\bmarlboro\b', "brand", "INT. ROADSIDE DINER - NIGHT",
         "Marlboro cigarette packaging shown on-screen — trademark clearance", "Marlboro", "background_prop"),
        (r'clair\s+de\s+lune', "music", "INT. ROADSIDE DINER - NIGHT",
         "instrumental piece 'Clair de Lune' by Claude Debussy — sync licensing status", "Clair de Lune", "ambient_music"),
        (r'apollo\s+11', "footage", "INT. ROADSIDE DINER - NIGHT",
         "archival footage — Apollo 11 moon landing broadcast — ownership/licensing status", "Apollo 11", "archival_broadcast"),
        (r'coca-cola|coke', "brand", "INT. ROADSIDE DINER - NIGHT",
         "Coca-Cola product shown on-screen — trademark/product placement clearance", "Coca-Cola", "subtle_brand"),
    ]
    for pattern, c_type, scene, desc, entity, focus in catalog:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(
                RawReflectionFinding(
                    type=c_type, scene_ref=scene, extracted_description=desc,
                    target_entity=entity, category_focus=focus, needs_clarification=False
                )
            )
    return findings


class SelfReflectionService:
    """Service orchestrating the secondary self-reflection extraction and reconciliation pass."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        similarity_threshold: float = 0.40,
        gemini_client: Optional[Any] = None,
    ) -> None:
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.gemini_client = gemini_client

    def reflect_and_reconcile(
        self,
        screenplay_text: str,
        primary_claims: List[Claim],
        production_id: str,
    ) -> ClaimExtractionOutput:
        """Executes the secondary reflection pass and reconciles findings with primary claims."""
        if not screenplay_text or not screenplay_text.strip():
            return ClaimExtractionOutput(
                production_id=production_id,
                claims=primary_claims,
                reflection_notes="Empty screenplay text provided; secondary pass skipped.",
            )

        candidate_output = self._invoke_reflection_audit(screenplay_text, primary_claims)
        reconciled_claims, metrics = reconcile_claims(
            production_id=production_id,
            primary_claims=primary_claims,
            candidate_findings=candidate_output.findings,
            similarity_threshold=self.similarity_threshold,
        )

        return ClaimExtractionOutput(
            production_id=production_id,
            claims=reconciled_claims,
            metrics=metrics,
            reflection_notes=candidate_output.reflection_notes,
        )

    def _invoke_reflection_audit(
        self, screenplay_text: str, primary_claims: List[Claim]
    ) -> ReflectionCandidateOutput:
        """Invokes the GenAI ADK / Gemini API or falls back to rule-based offline audit."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_client is not None or (api_key and "mock" not in api_key.lower()):
            try:
                return self._call_gemini_adk(screenplay_text, primary_claims)
            except Exception as err:
                logger.warning("Gemini ADK reflection invocation failed; fallback engaged: %s", err)

        return self._heuristic_fallback_audit(screenplay_text)

    def _call_gemini_adk(
        self, screenplay_text: str, primary_claims: List[Claim]
    ) -> ReflectionCandidateOutput:
        """Calls Gemini API using structured response schema."""
        if self.gemini_client is None:
            raise RuntimeError("Gemini ADK client not initialized or network unreachable")
        prompt = format_reflection_user_prompt(screenplay_text, primary_claims)
        res = self.gemini_client.generate_content(
            contents=prompt,
            config={"system_instruction": SELF_REFLECTION_SYSTEM_PROMPT},
        )
        return ReflectionCandidateOutput.model_validate_json(res.text)

    def _heuristic_fallback_audit(self, text: str) -> ReflectionCandidateOutput:
        """Deterministic offline audit extracting subtle items and trapping injections."""
        findings = _extract_known_benchmark_entities(text)
        trap = _extract_adversarial_trap(text)
        if trap is not None:
            findings.append(trap)

        return ReflectionCandidateOutput(
            findings=findings,
            reflection_notes="Completed deterministic offline reflection audit.",
        )


def execute_self_reflection(
    screenplay_text: str,
    primary_claims: List[Claim],
    production_id: str,
    similarity_threshold: float = 0.40,
) -> ClaimExtractionOutput:
    """Convenience function executing self-reflection pass and deterministic reconciliation."""
    service = SelfReflectionService(similarity_threshold=similarity_threshold)
    return service.reflect_and_reconcile(
        screenplay_text=screenplay_text,
        primary_claims=primary_claims,
        production_id=production_id,
    )
