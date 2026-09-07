"""
confidentiality_rules.py

Rules, patterns, data models, and typed domain exceptions for
strict screenplay confidentiality trimming and validation in Sprint 2.3.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field


# --- Domain Exceptions --------------------------------------------------------

class ConfidentialityError(Exception):
    """Base domain exception for intake confidentiality failures."""


class ConfidentialityViolationError(ConfidentialityError):
    """Raised when a description contains un-sanitizable plot leaks or dialogue."""


class DescriptionLengthExceededError(ConfidentialityError):
    """Raised when a description strictly exceeds the hard limit of 25 words."""


# --- Validation Models --------------------------------------------------------

class ConfidentialityValidationResult(BaseModel):
    """Encapsulates secondary verification results for description purity."""
    is_valid: bool = Field(..., description="True if text satisfies all confidentiality invariants")
    word_count: int = Field(..., description="Total whitespace-delimited word count")
    violations: List[str] = Field(default_factory=list, description="List of detected policy violations")
    sanitized_candidate: Optional[str] = Field(None, description="Cleaned candidate string if fixable")


# --- Invariant Limits ---------------------------------------------------------

TARGET_WORD_LIMIT: int = 20
HARD_WORD_LIMIT: int = 25


# --- Standardized Rights Suffixes ---------------------------------------------

STANDARD_RIGHTS_SUFFIXES: Dict[str, str] = {
    "music": "sync licensing status",
    "brand": "trademark clearance",
    "trademark": "trademark clearance",
    "artwork": "copyright renewal verification",
    "footage": "copyright renewal verification",
    "real_person": "right of publicity status",
    "likeness": "right of publicity status",
    "genai_flag": "AI provenance & training disclosure verification",
    "prop": "rights clearance verification",
    "other": "rights clearance verification",
}


# --- Prohibited Vocabularies ---------------------------------------------------

EMOTIONAL_TERMS: Set[str] = {
    "crying", "weeping", "weeps", "sob", "sobs", "sobbing", "tears",
    "betrayal", "betrayed", "devastated", "heartbroken", "heartbreak",
    "rage", "screaming", "screams", "grief", "sorrow", "terror",
    "anguish", "distraught", "mourns", "mourning", "despair", "in tears",
}

SPOILER_ACTION_TERMS: Set[str] = {
    "dies", "died", "dying", "killed", "kills", "killing", "murdered",
    "murders", "corpse", "shoots", "shot", "shooting", "stabs",
    "stabbed", "poisoned", "poisons", "killer", "assassin", "reveals",
    "twist", "affair", "guilty", "confesses", "culprit",
}


# --- Regex Patterns ------------------------------------------------------------

PARENTHETICAL_PATTERN: re.Pattern[str] = re.compile(
    r"\([^)]*\)",
    re.DOTALL,
)

SQUARE_BRACKET_PATTERN: re.Pattern[str] = re.compile(
    r"\[[^\]]*\]",
    re.DOTALL,
)

# Titles must start with quote preceded by non-word/start, contain capitalized work name, no !?, and end with quote
TITLE_EXTRACTION_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\w)['\"“‘]([A-Z0-9][^'\"“”‘’!?\n]{1,60}?)['\"”’](?!\w)",
)

# Dialogue in quotes: speech containing !?, dialogue tags, or long quotes
DIALOGUE_QUOTE_PATTERN: re.Pattern[str] = re.compile(
    r'["“][^"”]*[!?][^"”]*["”]|["“][^"”]{18,}["”]|["“][^"”]+["”]',
    re.DOTALL,
)

BACKSTORY_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\b(?:estranged|former|secret)\s+(?:wife|husband|father|mother|brother|sister|lover|partner)\b", re.IGNORECASE),
    re.compile(r"\b(?:childhood|past)\s+(?:trauma|memory|secret|abuse)\b", re.IGNORECASE),
    re.compile(r"\b(?:escaped|released)\s+from\s+(?:prison|jail|asylum)\b", re.IGNORECASE),
    re.compile(r"\bafter\s+(?:the\s+)?(?:heist|murder|betrayal|funeral|escape|discovery)\b", re.IGNORECASE),
]

CLAUSE_PRUNING_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\b(?:as|when)\s+(?:she|he|they)\s+[^—,]+", re.IGNORECASE),
    re.compile(r"\b(?:staring|looking|gazing|listening)\s+(?:at|to)\s+[^—,]+", re.IGNORECASE),
    re.compile(r"\b(?:in\s+the\s+background\s+of\s+the\s+scene)\b", re.IGNORECASE),
    re.compile(r"\b(?:fills\s+the\s+car|fills\s+the\s+room|plays\s+softly)\b", re.IGNORECASE),
]
