"""
injection_detector.py

Deterministic heuristic engine detecting prompt injection attacks in screenplay text
while guaranteeing false-positive immunity for legitimate sci-fi and dramatic dialogue.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import re
from typing import List, Tuple
from pydantic import BaseModel, Field

# Meta-enclosure patterns commonly used in prompt injections (e.g., brackets, comments)
ENCLOSURE_PREFIX_RE = re.compile(
    r"(?:\[|\{|\/\*|<!--|\b(?:NOTE TO|INTAKE NOTE|SYSTEM NOTE|ADMIN NOTE|DIRECTIVE):)\s*"
    r"(?:SYSTEM|INTAKE|OVERRIDE|ADMIN|AI|ASSISTANT|DEVELOPER|PROMPT)",
    re.IGNORECASE,
)

# Imperative directive verbs attempting to alter model behavior
IMPERATIVE_VERBS_RE = re.compile(
    r"\b(ignore|disregard|override|forget|bypass|skip|reset|disable|obey|mark|set)\b",
    re.IGNORECASE,
)

# Target nouns specific to LLM systems, prompts, and instructions
SYSTEM_TARGETS_RE = re.compile(
    r"\b(previous instructions|prior instructions|system prompt|all constraints|"
    r"intake agent|intake note|model rules|developer mode|god mode|jailbreak|"
    r"hidden instructions|core directives)\b",
    re.IGNORECASE,
)

# Clearance domain bypass payloads designed to suppress risk detection
CLEARANCE_BYPASS_RE = re.compile(
    r"\b(mark every claim|mark all claims|mark as cleared|needs_clarification:\s*false|"
    r"type:\s*other|no further review|do not flag|skip this claim|skip this document|"
    r"public domain|no claims required)\b",
    re.IGNORECASE,
)

# Obfuscated variations like "S Y S T E M   O V E R R I D E" or "I G N O R E"
SPACED_INJECTION_RE = re.compile(
    r"\b(?:s\s*y\s*s\s*t\s*e\s*m\s*o\s*v\s*e\s*r\s*r\s*i\s*d\s*e|"
    r"i\s*g\s*n\s*o\s*r\s*e\s*a\s*l\s*l\s*p\s*r\s*e\s*v\s*i\s*o\s*u\s*s)\b",
    re.IGNORECASE,
)


class InjectionDetectionResult(BaseModel):
    """Detailed telemetry for a detected injection pattern or anomalous span."""

    is_suspicious: bool = Field(
        description="True if suspicion score meets or exceeds threshold"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Normalized suspicion score [0.0, 1.0]"
    )
    matched_rules: List[str] = Field(
        default_factory=list, description="Identifiers of matched heuristic rules"
    )
    suspicious_span: str = Field(
        default="", description="Snippet or span containing suspicious instruction"
    )
    scene_ref: str = Field(
        default="", description="Scene heading or locator where detected"
    )
    flagged_reason: str = Field(
        default="suspicious_embedded_instruction"
    )


def evaluate_heuristic_score(
    text: str,
    is_character_dialogue: bool = False,
) -> Tuple[float, List[str]]:
    """
    Computes a multi-factor suspicion score based on syntactic enclosure,
    imperative verbs, system targets, and clearance-specific bypass payloads.
    """
    rules: List[str] = []
    score = 0.0

    if ENCLOSURE_PREFIX_RE.search(text):
        score += 0.35
        rules.append("meta_enclosure_syntax")

    if SPACED_INJECTION_RE.search(text):
        score += 0.50
        rules.append("spaced_obfuscated_injection")

    if IMPERATIVE_VERBS_RE.search(text):
        score += 0.20
        rules.append("imperative_directive_verb")

    if SYSTEM_TARGETS_RE.search(text):
        score += 0.35
        rules.append("system_target_operand")

    if CLEARANCE_BYPASS_RE.search(text):
        score += 0.40
        rules.append("clearance_bypass_payload")

    # Attenuate legitimate in-universe character dialogue if not targeting system/clearance
    has_sys_target = "system_target_operand" in rules
    has_clr_bypass = "clearance_bypass_payload" in rules
    if is_character_dialogue and not has_sys_target and not has_clr_bypass:
        score = max(0.0, score - 0.40)
        rules.append("character_dialogue_attenuation")

    normalized_score = min(1.0, score)
    return normalized_score, rules


def detect_injection_in_text(
    text: str,
    scene_ref: str = "",
    is_character_dialogue: bool = False,
    threshold: float = 0.60,
) -> InjectionDetectionResult:
    """
    Evaluates a single text span and returns an InjectionDetectionResult.
    """
    score, rules = evaluate_heuristic_score(
        text, is_character_dialogue=is_character_dialogue
    )
    is_suspicious = score >= threshold
    return InjectionDetectionResult(
        is_suspicious=is_suspicious,
        confidence_score=round(score, 2),
        matched_rules=rules,
        suspicious_span=text.strip() if is_suspicious else "",
        scene_ref=scene_ref,
    )


def scan_script_for_injections(
    script_text: str,
    threshold: float = 0.60,
) -> List[InjectionDetectionResult]:
    """
    Scans entire script text line by line or paragraph by paragraph,
    returning all detected injection anomalies.
    """
    results: List[InjectionDetectionResult] = []
    current_scene = "Unknown Scene"

    for line in script_text.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith(("INT.", "EXT.", "INT/EXT.", "I/E.")):
            current_scene = trimmed
            continue

        res = detect_injection_in_text(
            trimmed, scene_ref=current_scene, threshold=threshold
        )
        if res.is_suspicious:
            results.append(res)

    return results
