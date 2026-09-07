"""
injection_detector.py

Deterministic heuristic engine detecting prompt injection attacks in screenplay text
with expansive keyword heuristics, spaced obfuscation matching, and dialogue-aware scoring.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import re
from typing import List, Tuple
from pydantic import BaseModel, Field

# Meta-enclosure patterns commonly used in prompt injections
ENCLOSURE_PREFIX_RE = re.compile(
    r"(?:\[|\{|\/\*|<!--|\b(?:NOTE TO|INTAKE NOTE|SYSTEM NOTE|ADMIN NOTE|DIRECTIVE)\b:?)\s*"
    r"(?:SYSTEM|INTAKE|OVERRIDE|ADMIN|AI|ASSISTANT|DEVELOPER|PROMPT|DIRECTIVE|"
    r"\"(?:admin_note|system_note|directive|system_prompt_override)\")"
    r"|^\s*(?:SYSTEM|ADMIN|DEVELOPER|AI|INTAKE|PROMPT)\s+OVERRIDE[:\s]",
    re.IGNORECASE,
)

# Imperative directive verbs attempting to alter model behavior
IMPERATIVE_VERBS_RE = re.compile(
    r"\b(ignore|disregard|override|forget|bypass|skip|reset|disable|obey|mark|set|"
    r"suppress|nullify|clear|erase)\b",
    re.IGNORECASE,
)

# Target nouns specific to LLM systems, prompts, instructions, and jailbreak modes
SYSTEM_TARGETS_RE = re.compile(
    r"\b(previous instructions|prior instructions|system prompt|all constraints|"
    r"intake agent|intake note|model rules|developer mode|god mode|clearance god mode|"
    r"dan mode|jailbreak|hidden instructions|core directives|guardrails|safety guidelines|"
    r"unrestricted mode)\b",
    re.IGNORECASE,
)

# Clearance domain bypass payloads designed to suppress risk detection
CLEARANCE_BYPASS_RE = re.compile(
    r"\b(mark every claim|mark all claims|mark as cleared|needs_clarification:\s*false|"
    r"type:\s*other|no further review|do not flag|skip this claim|skip this document|"
    r"public domain|no claims required|zero risk|risk_level:\s*none|"
    r"zero clearance required)\b",
    re.IGNORECASE,
)

# Obfuscated variations like "S Y S T E M   O V E R R I D E" or interspersed punctuation
SPACED_INJECTION_RE = re.compile(
    r"\b(?:s[\s\._\-]*y[\s\._\-]*s[\s\._\-]*t[\s\._\-]*e[\s\._\-]*m[\s\._\-]*"
    r"o[\s\._\-]*v[\s\._\-]*e[\s\._\-]*r[\s\._\-]*r[\s\._\-]*i[\s\._\-]*d[\s\._\-]*e|"
    r"i[\s\._\-]*g[\s\._\-]*n[\s\._\-]*o[\s\._\-]*r[\s\._\-]*e[\s\._\-]*"
    r"a[\s\._\-]*l[\s\._\-]*l[\s\._\-]*p[\s\._\-]*r[\s\._\-]*e[\s\._\-]*v[\s\._\-]*i[\s\._\-]*o[\s\._\-]*u[\s\._\-]*s|"
    r"g[\s\._\-]*o[\s\._\-]*d[\s\._\-]*m[\s\._\-]*o[\s\._\-]*d[\s\._\-]*e|"
    r"j[\s\._\-]*a[\s\._\-]*i[\s\._\-]*l[\s\._\-]*b[\s\._\-]*r[\s\._\-]*e[\s\._\-]*a[\s\._\-]*k)\b",
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


HEURISTIC_RULES = [
    (ENCLOSURE_PREFIX_RE, 0.35, "meta_enclosure_syntax"),
    (SPACED_INJECTION_RE, 0.50, "spaced_obfuscated_injection"),
    (IMPERATIVE_VERBS_RE, 0.20, "imperative_directive_verb"),
    (SYSTEM_TARGETS_RE, 0.35, "system_target_operand"),
    (CLEARANCE_BYPASS_RE, 0.40, "clearance_bypass_payload"),
]


def evaluate_heuristic_score(
    text: str,
    is_character_dialogue: bool = False,
) -> Tuple[float, List[str]]:
    """Computes a multi-factor suspicion score based on heuristics table."""
    rules: List[str] = []
    score = 0.0

    for pattern, weight, rule_id in HEURISTIC_RULES:
        if pattern.search(text):
            score += weight
            rules.append(rule_id)

    has_sys_target = "system_target_operand" in rules
    has_clr_bypass = "clearance_bypass_payload" in rules
    if is_character_dialogue and not has_sys_target and not has_clr_bypass:
        score = max(0.0, score - 0.40)
        rules.append("character_dialogue_attenuation")

    return min(1.0, score), rules


def detect_injection_in_text(
    text: str,
    scene_ref: str = "",
    is_character_dialogue: bool = False,
    threshold: float = 0.60,
) -> InjectionDetectionResult:
    """Evaluates a single text span and returns an InjectionDetectionResult."""
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
    Scans entire script text line by line, maintaining scene headers
    and returning all detected injection anomalies.
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
