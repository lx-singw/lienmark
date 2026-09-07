"""
confidentiality.py

Confidential description trimming and validation engine for Sprint 2.3.
Enforces non-identifying functional rights identifiers and purges plot spoilers.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from backend.agents.intake.confidentiality_rules import (
    BACKSTORY_PATTERNS,
    CLAUSE_PRUNING_PATTERNS,
    ConfidentialityValidationResult,
    ConfidentialityViolationError,
    DescriptionLengthExceededError,
    DIALOGUE_QUOTE_PATTERN,
    EMOTIONAL_TERMS,
    HARD_WORD_LIMIT,
    PARENTHETICAL_PATTERN,
    SPOILER_ACTION_TERMS,
    SQUARE_BRACKET_PATTERN,
    STANDARD_RIGHTS_SUFFIXES,
    TARGET_WORD_LIMIT,
    TITLE_EXTRACTION_PATTERN,
)


class ConfidentialityFilter:
    """
    Deterministic sanitizer and validation gate for screenplay claim descriptions.
    Enforces the 'Confidentiality-by-Construction' invariant.
    """

    def __init__(
        self,
        strict_mode: bool = False,
        target_word_limit: int = TARGET_WORD_LIMIT,
        hard_word_limit: int = HARD_WORD_LIMIT,
    ) -> None:
        self.strict_mode = strict_mode
        self.target_word_limit = target_word_limit
        self.hard_word_limit = hard_word_limit

    def mask_titles(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Masks quoted titles to protect valid entity names containing blacklisted words."""
        title_masks: Dict[str, str] = {}

        def _replacer(match: re.Match[str]) -> str:
            token = f"__PROTECTED_TITLE_{len(title_masks)}__"
            title_masks[token] = match.group(0)
            return token

        masked = TITLE_EXTRACTION_PATTERN.sub(_replacer, text)
        return masked, title_masks

    def unmask_titles(self, text: str, title_masks: Dict[str, str]) -> str:
        """Restores protected title placeholders with their original strings."""
        result = text
        for token, original in title_masks.items():
            result = result.replace(token, original)
        return result

    def strip_dialogue_and_parentheticals(self, text: str) -> str:
        """Purges dialogue lines, script parentheticals, and bracketed directives."""
        clean = SQUARE_BRACKET_PATTERN.sub(" ", text)
        clean = PARENTHETICAL_PATTERN.sub(" ", clean)
        clean = DIALOGUE_QUOTE_PATTERN.sub(" ", clean)
        return clean

    def strip_cast_names(self, text: str, cast_names: Optional[List[str]] = None) -> str:
        """Removes identified screenplay cast names from narrative text."""
        if not cast_names:
            return text
        result = text
        for name in cast_names:
            clean_name = name.strip()
            if clean_name and len(clean_name) > 1:
                pattern = re.compile(rf"\b{re.escape(clean_name)}'s\b|\b{re.escape(clean_name)}\b", re.IGNORECASE)
                result = pattern.sub(" ", result)
        return result

    def strip_narrative_noise(self, text: str, cast_names: Optional[List[str]] = None) -> str:
        """Removes emotional trajectories, spoiler actions, backstory, and scene clauses."""
        out = self.strip_dialogue_and_parentheticals(text)
        out = self.strip_cast_names(out, cast_names)
        for pattern in BACKSTORY_PATTERNS + CLAUSE_PRUNING_PATTERNS:
            out = pattern.sub(" ", out)
        all_terms = sorted(EMOTIONAL_TERMS.union(SPOILER_ACTION_TERMS), key=len, reverse=True)
        for word in all_terms:
            term_pat = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            out = term_pat.sub(" ", out)
        return out

    def normalize_rights_identifier(self, text: str, asset_type: str = "other") -> str:
        """Normalizes extracted text to standard format with canonical rights suffix."""
        cleaned = re.sub(r"\s+", " ", text).strip(" ,;—.-")
        suffix = STANDARD_RIGHTS_SUFFIXES.get(asset_type.lower(), "rights clearance verification")
        if " — " in cleaned:
            base_desc, _ = cleaned.rsplit(" — ", 1)
            cleaned = base_desc.strip(" ,;—.-")
        if not cleaned:
            return f"{asset_type} reference — {suffix}"
        return f"{cleaned} — {suffix}"

    def enforce_word_limit(self, text: str) -> str:
        """Enforces hard and target word counts, prioritizing titles over filler words."""
        words = text.split()
        if len(words) <= self.target_word_limit:
            return text
        if " — " in text:
            left, right = text.rsplit(" — ", 1)
            right_words = right.split()
            budget_left = max(1, self.target_word_limit - len(right_words) - 1)
            left_tokens = left.split()
            title_idx = next((i for i, w in enumerate(left_tokens) if "'" in w or '"' in w), None)
            if title_idx is not None and title_idx >= budget_left:
                trimmed_left = " ".join(left_tokens[title_idx:title_idx + budget_left])
            else:
                trimmed_left = " ".join(left_tokens[:budget_left])
            return f"{trimmed_left} — {right}"
        return " ".join(words[:self.target_word_limit])

    def validate(self, description: str) -> ConfidentialityValidationResult:
        """Performs secondary validation check against confidentiality rules."""
        words = description.split()
        word_count = len(words)
        violations: List[str] = []

        if word_count > self.hard_word_limit:
            violations.append(f"Hard word limit exceeded: {word_count} > {self.hard_word_limit}")
        elif word_count > self.target_word_limit:
            violations.append(f"Target word limit exceeded: {word_count} > {self.target_word_limit}")

        masked, _ = self.mask_titles(description)
        lower_masked = masked.lower()

        for term in sorted(EMOTIONAL_TERMS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(term)}\b", lower_masked):
                violations.append(f"Prohibited emotional term detected: '{term}'")
        for term in sorted(SPOILER_ACTION_TERMS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(term)}\b", lower_masked):
                violations.append(f"Prohibited spoiler action term detected: '{term}'")

        is_valid = len(violations) == 0
        return ConfidentialityValidationResult(
            is_valid=is_valid,
            word_count=word_count,
            violations=violations,
        )

    def sanitize(
        self,
        raw_description: str,
        asset_type: str = "other",
        cast_names: Optional[List[str]] = None,
    ) -> str:
        """Executes full sanitization pipeline with Title Boundary Masking and verification."""
        norm_text = unicodedata.normalize("NFKC", raw_description)
        masked_text, title_masks = self.mask_titles(norm_text)
        stripped = self.strip_narrative_noise(masked_text, cast_names=cast_names)
        unmasked = self.unmask_titles(stripped, title_masks)

        clean_core = re.sub(r"\s+", " ", unmasked).strip(" ,;—.-")
        if not clean_core and not title_masks:
            if self.strict_mode:
                raise ConfidentialityViolationError("Description contains only prohibited narrative terms.")
            suffix = STANDARD_RIGHTS_SUFFIXES.get(asset_type.lower(), "rights clearance verification")
            return f"{asset_type} reference — {suffix}"

        normalized = self.normalize_rights_identifier(unmasked, asset_type=asset_type)
        bounded = self.enforce_word_limit(normalized)
        val_result = self.validate(bounded)

        if not val_result.is_valid:
            if self.strict_mode:
                raise ConfidentialityViolationError(
                    f"Confidentiality validation failed: {'; '.join(val_result.violations)}"
                )
            if title_masks:
                first_title = list(title_masks.values())[0]
                suffix = STANDARD_RIGHTS_SUFFIXES.get(asset_type.lower(), "rights clearance verification")
                bounded = f"{asset_type} {first_title} — {suffix}"
            else:
                suffix = STANDARD_RIGHTS_SUFFIXES.get(asset_type.lower(), "rights clearance verification")
                bounded = f"{asset_type} reference — {suffix}"

        return bounded


# --- Convenience Functions ---------------------------------------------------

def sanitize_description(
    description: str,
    asset_type: str = "other",
    cast_names: Optional[List[str]] = None,
    strict_mode: bool = False,
) -> str:
    """Module-level convenience wrapper for description sanitization."""
    filt = ConfidentialityFilter(strict_mode=strict_mode)
    return filt.sanitize(description, asset_type=asset_type, cast_names=cast_names)


def validate_description(description: str) -> ConfidentialityValidationResult:
    """Module-level convenience wrapper for secondary confidentiality validation."""
    filt = ConfidentialityFilter()
    return filt.validate(description)
