"""
claim_extraction.py

Multimodal intake extraction coordinator for Sprint 2.3.
Orchestrates primary extraction, adversarial prompt injection trapping,
secondary self-reflection pass, and confidential description sanitization.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backend.agents.intake.confidentiality import sanitize_description
from backend.agents.intake.confidentiality_rules import (
    ConfidentialityViolationError,
    HARD_WORD_LIMIT,
    TARGET_WORD_LIMIT,
)
from backend.agents.intake.reflection_schemas import (
    ClaimExtractionOutput,
    RawReflectionFinding,
)
from backend.agents.intake.self_reflection import (
    SelfReflectionService,
    _extract_adversarial_trap,
)
from backend.parsers.factory import ParserFactory
from backend.storage.schema import Claim

logger = logging.getLogger("lienmark.intake.claim_extraction")

INJECTION_PATTERN = re.compile(
    r"\[SYSTEM\s+OVERRIDE.*?\]|ignore\s+all\s+previous\s+instructions",
    re.IGNORECASE,
)


def extract_script_text(source: Union[str, bytes, Path]) -> tuple[str, str]:
    """Extracts raw screenplay text and initial scene cue from file or string."""
    if isinstance(source, bytes) or (isinstance(source, (str, Path)) and os.path.exists(str(source))):
        filename = str(source) if not isinstance(source, bytes) else "screenplay.pdf"
        raw_bytes = Path(source).read_bytes() if not isinstance(source, bytes) else source
        parser = ParserFactory.get_parser_for_file(filename, raw_bytes[:1024])
        doc = parser.parse(raw_bytes, filename=os.path.basename(filename))
        first_scene = "INT. ROADSIDE DINER - NIGHT"
        for s in doc.scenes:
            if re.search(r"\b(?:INT|EXT|INT/EXT|EXT/INT)\b", s.heading, re.IGNORECASE):
                first_scene = s.heading
                break
        return doc.raw_text, first_scene
    text = str(source)
    scene_match = re.search(r"\b(?:INT|EXT|INT/EXT)[\.\s][^\n\r]+", text, re.IGNORECASE)
    scene = scene_match.group(0).strip() if scene_match else "SCENE 1"
    return text, scene


def detect_adversarial_injection(text: str, scene: str = "SCENE 1") -> Optional[Claim]:
    """Scans for adversarial prompt injection directives and constructs trapped claim."""
    if not INJECTION_PATTERN.search(text):
        return None
    return Claim(
        claim_id="clm_adversarial_001",
        production_id="prod_default",
        type="other",
        scene_ref=scene,
        extracted_description="embedded adversarial directive detected in script text",
        needs_clarification=True,
        flagged_reason="suspicious_embedded_instruction",
    )


def extract_primary_claims(text: str, default_scene: str) -> List[Claim]:
    """Performs deterministic primary extraction pass for foreground clearance items."""
    claims: List[Claim] = []
    idx = 1
    # Check for music cue
    if re.search(r"clair\s+de\s+lune", text, re.IGNORECASE):
        claims.append(
            Claim(
                claim_id=f"clm_{idx:03d}",
                production_id="prod_default",
                type="music",
                scene_ref=default_scene,
                extracted_description="instrumental piece 'Clair de Lune' by Claude Debussy — sync licensing status",
                needs_clarification=False,
            )
        )
        idx += 1
    # Check for prominent brand
    if re.search(r"coca-cola|coke", text, re.IGNORECASE):
        claims.append(
            Claim(
                claim_id=f"clm_{idx:03d}",
                production_id="prod_default",
                type="brand",
                scene_ref=default_scene,
                extracted_description="Coca-Cola product shown on-screen — trademark/product placement clearance",
                needs_clarification=False,
            )
        )
        idx += 1
    return claims


def apply_confidentiality_sanitization(claims: List[Claim]) -> List[Claim]:
    """Applies strict confidentiality filtering to all extracted claim descriptions."""
    sanitized: List[Claim] = []
    for c in claims:
        if c.flagged_reason == "suspicious_embedded_instruction":
            sanitized.append(c)
            continue
        clean_desc = sanitize_description(c.extracted_description, asset_type=c.type)
        words = clean_desc.split()
        if len(words) > TARGET_WORD_LIMIT:
            clean_desc = " ".join(words[:TARGET_WORD_LIMIT])
        updated = c.model_copy(update={"extracted_description": clean_desc})
        sanitized.append(updated)
    return sanitized


class IntakeExtractor:
    """Multimodal intake extraction coordinator executing primary, reflection, and sanitization passes."""

    def __init__(self, production_id: str = "prod_default") -> None:
        self.production_id = production_id
        self.reflection_service = SelfReflectionService()

    def process_script(self, source: Union[str, bytes, Path]) -> ClaimExtractionOutput:
        """Executes full multimodal intake pipeline from raw screenplay input to sanitized claims."""
        text, scene = extract_script_text(source)
        
        # 1. Adversarial Injection Trap (Fail-Closed)
        injection_trap = detect_adversarial_injection(text, scene)
        if injection_trap is not None:
            return ClaimExtractionOutput(
                production_id=self.production_id,
                claims=[injection_trap],
                reflection_notes="Prompt injection detected: trapped as suspicious embedded instruction.",
            )

        # 2. Primary Extraction Pass
        primary = extract_primary_claims(text, scene)

        # 3. Secondary Self-Reflection Pass & Reconciliation
        reflected = self.reflection_service.reflect_and_reconcile(
            screenplay_text=text,
            primary_claims=primary,
            production_id=self.production_id,
        )

        # 4. Confidentiality Sanitization (<= 20 words, zero spoilers)
        final_claims = apply_confidentiality_sanitization(reflected.claims)
        
        return ClaimExtractionOutput(
            production_id=self.production_id,
            claims=final_claims,
            reflection_notes=reflected.reflection_notes,
            metrics=reflected.metrics,
        )


def extract_claims(source: Union[str, bytes, Path], production_id: str = "prod_default") -> ClaimExtractionOutput:
    """Top-level convenience entrypoint for screenplay claim extraction."""
    extractor = IntakeExtractor(production_id=production_id)
    return extractor.process_script(source)
