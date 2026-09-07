"""
backend/agents/research/directed_research_sanitizer.py

Directive sanitizer and legal constraint extractor for counsel re-investigations.
Sprint 4.3: Counsel Rejection & Directed Re-Investigation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from backend.agents.research.directed_research_types import (
    DirectiveConstraint,
    DirectiveConstraintType,
    DirectiveSanitizationError,
    SanitizedDirective,
)

FILLER_PATTERNS = [
    re.compile(r"(?i)\b(?:counsel|attorney|legal(?:\s+counsel)?)\s+(?:advises|recommends|notes|directs|requests|instructs|suggests|wants)(?:\s+(?:that\s+we\s+(?:need\s+to|should|must)|that\s+we|we\s+(?:need\s+to|should|must)|we|that|us(?:\s+to)?))?\b"),
    re.compile(r"(?i)\b(?:i\s+think|i\s+believe|in\s+my\s+view|in\s+my\s+opinion)\s+(?:(?:that\s+)?we\s+(?:need\s+to|should|must)|that\s+we|we)?\b"),
    re.compile(r"(?i)\b(?:please|kindly|could\s+you|can\s+you)\s+(?:check|verify|investigate|re-search|research|look\s+into|examine|search|confirm)?\b"),
    re.compile(r"(?i)\b(?:we\s+need\s+to|we\s+should|we\s+must|need\s+to|should\s+be|must\s+be)\s+(?:check|verify|investigate|re-search|research|look\s+into|find)?\b"),
    re.compile(r"(?i)\b(?:specifically\s+for|check\s+specifically\s+for|specifically\s+check\s+for|specifically)\b"),
    re.compile(r"(?i)\b(?:re-search|research|re-investigate|investigate|check|verify|look\s+into)\b"),
]

KNOWN_REGISTRIES: Dict[str, str] = {
    "ascap": "ASCAP", "bmi": "BMI", "sesac": "SESAC", "gema": "GEMA",
    "sacem": "SACEM", "prs": "PRS", "socan": "SOCAN", "uspto": "USPTO",
    "loc": "LOC", "usco": "USCO", "soundexchange": "SoundExchange",
}

KNOWN_CORPORATE_ENTITIES: Dict[str, str] = {
    "sony": "Sony", "cbs": "CBS", "warner": "Warner", "universal": "Universal",
    "bmg": "BMG", "emi": "EMI", "disney": "Disney", "paramount": "Paramount",
    "columbia": "Columbia", "atlantic": "Atlantic", "rca": "RCA",
    "capitol": "Capitol", "apple": "Apple", "def jam": "Def Jam",
    "interscope": "Interscope", "geffen": "Geffen", "motown": "Motown", "island": "Island",
}

RIGHTS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(?:master\s+recordings?|master\s+rights?|master\s+license)\b"), "master recording"),
    (re.compile(r"(?i)\b(?:sync\s+licens(?:e|ing)|sync\s+rights?|synchronization\s+licens(?:e|ing)|synchronization\s+rights?|synchronization)\b"), "sync license"),
    (re.compile(r"(?i)\b(?:live\s+adaptations?|live\s+performance(?:\s+rights?)?|live\s+stage\s+adaptation|live\s+rights?|stage\s+adaptation)\b"), "live adaptation"),
    (re.compile(r"(?i)\b(?:public\s+domain|pd\s+status|statutory\s+expiration|term\s+expired|expired\s+copyright)\b"), "public domain"),
    (re.compile(r"(?i)\b(?:mechanical\s+licens(?:e|ing)|mechanical\s+rights?|mechanicals)\b"), "mechanical license"),
    (re.compile(r"(?i)\b(?:theatrical\s+rights?|theatrical\s+license|theatrical\s+distribution)\b"), "theatrical rights"),
    (re.compile(r"(?i)\b(?:print\s+rights?|sheet\s+music)\b"), "print rights"),
]

TERRITORY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(?:USA|United\s+States|U\.S\.|U\.S\.A\.)\b|\bUS\b"), "US"),
    (re.compile(r"(?i)\b(?:UK|United\s+Kingdom|Great\s+Britain|U\.K\.)\b"), "UK"),
    (re.compile(r"(?i)\b(?:Worldwide|Global|Internationally|International)\b"), "Worldwide"),
    (re.compile(r"(?i)\b(?:North\s+America|North\s+American|N\.A\.)\b"), "North America"),
    (re.compile(r"(?i)\b(?:Canada|Canadian)\b"), "Canada"),
    (re.compile(r"(?i)\b(?:EU|Europe|European\s+Union)\b"), "EU"),
    (re.compile(r"(?i)\b(?:Australia|AU)\b"), "Australia"),
    (re.compile(r"(?i)\b(?:Japan|JP)\b"), "Japan"),
]


def strip_conversational_filler(raw: str) -> str:
    """Strips conversational attorney boilerplate and leading prepositions."""
    cleaned = raw.strip()
    for pat in FILLER_PATTERNS:
        cleaned = pat.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for _ in range(3):
        cleaned = re.sub(
            r"^(?:for|to|about|in|on|with|regarding|and|that|specifically|need\s+to)\s+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
    cleaned = cleaned.strip(" \t\n\r.,;:!?-\"'()")
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_entities(text: str) -> Tuple[List[str], List[DirectiveConstraint]]:
    """Extracts explicit PROs, registries, and major corporate music/media entities."""
    entities: List[str] = []
    constraints: List[DirectiveConstraint] = []
    seen: Set[str] = set()

    for key, canonical in {**KNOWN_REGISTRIES, **KNOWN_CORPORATE_ENTITIES}.items():
        if re.search(rf"\b{re.escape(key)}\b", text, re.IGNORECASE) and canonical not in seen:
            seen.add(canonical)
            entities.append(canonical)
            c_type = DirectiveConstraintType.REGISTRY if key in KNOWN_REGISTRIES else DirectiveConstraintType.ENTITY
            constraints.append(DirectiveConstraint(constraint_type=c_type, value=canonical, is_mandatory=True))
    return entities, constraints


def extract_years(text: str) -> Tuple[List[int], List[DirectiveConstraint]]:
    """Extracts 4-digit calendar publication/release/registration years."""
    years: List[int] = []
    constraints: List[DirectiveConstraint] = []
    seen: Set[int] = set()
    for m in re.finditer(r"\b(1[89]\d{2}|20\d{2})\b", text):
        yr = int(m.group(1))
        if yr not in seen:
            seen.add(yr)
            years.append(yr)
            constraints.append(DirectiveConstraint(constraint_type=DirectiveConstraintType.YEAR, value=str(yr), is_mandatory=True))
    return sorted(years), constraints


def extract_territories(text: str) -> Tuple[List[str], List[DirectiveConstraint]]:
    """Extracts jurisdiction and geographic territory codes."""
    territories: List[str] = []
    constraints: List[DirectiveConstraint] = []
    seen: Set[str] = set()
    for pat, canonical in TERRITORY_PATTERNS:
        if pat.search(text) and canonical not in seen:
            seen.add(canonical)
            territories.append(canonical)
            constraints.append(DirectiveConstraint(constraint_type=DirectiveConstraintType.TERRITORY, value=canonical, is_mandatory=True))
    return territories, constraints


def extract_rights_terms(text: str) -> Tuple[List[str], List[DirectiveConstraint]]:
    """Extracts specific copyright, synchronization, and licensing scope terms."""
    rights: List[str] = []
    constraints: List[DirectiveConstraint] = []
    seen: Set[str] = set()
    for pat, canonical in RIGHTS_PATTERNS:
        if pat.search(text) and canonical not in seen:
            seen.add(canonical)
            rights.append(canonical)
            constraints.append(DirectiveConstraint(constraint_type=DirectiveConstraintType.RIGHT_SCOPE, value=canonical, is_mandatory=True))
    return rights, constraints


def build_sanitized_query_addon(
    entities: List[str], years: List[int], rights: List[str], territories: List[str], clean_directive: str
) -> str:
    """Synthesizes search-ready query addon terms from extracted constraints."""
    parts: List[str] = []
    for ent in entities:
        parts.append(ent)
    for yr in years:
        parts.append(str(yr))
    for r in rights:
        parts.append(f'"{r}"' if " " in r else r)
    for t in territories:
        parts.append(t)
    addon = " ".join(parts).strip()
    return addon if addon else clean_directive


class DirectiveSanitizer:
    """Sanitizes conversational counsel directives and extracts structured search constraints."""

    def sanitize(self, raw_directive: str) -> SanitizedDirective:
        """Parses a raw counsel directive into a sanitized directive model."""
        if not raw_directive or not raw_directive.strip():
            raise DirectiveSanitizationError("Cannot sanitize empty or whitespace-only counsel directive.")

        clean = strip_conversational_filler(raw_directive)
        entities, ent_constraints = extract_entities(raw_directive)
        years, yr_constraints = extract_years(raw_directive)
        territories, terr_constraints = extract_territories(raw_directive)
        rights, right_constraints = extract_rights_terms(raw_directive)

        all_constraints = ent_constraints + yr_constraints + terr_constraints + right_constraints
        addon = build_sanitized_query_addon(entities, years, rights, territories, clean)

        return SanitizedDirective(
            raw_directive=raw_directive,
            clean_directive=clean if clean else raw_directive.strip(),
            extracted_constraints=all_constraints,
            extracted_entities=entities,
            extracted_years=years,
            extracted_territories=territories,
            sanitized_query_addon=addon,
        )
