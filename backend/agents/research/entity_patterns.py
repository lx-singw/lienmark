"""
backend/agents/research/entity_patterns.py

Compiled regular expression patterns and heuristic extractors for IP lead signals.
Sprint 3.2: Snippet Entity & Lead Extractor Specialist.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional, Tuple

from backend.agents.research.entity_catalog import (
    is_false_lead,
    match_known_entity,
    normalize_entity_name,
)
from backend.agents.research.lead_types import (
    LeadEntityType,
    LeadRelationshipType,
)


class RawMatch(NamedTuple):
    entity_name: str
    entity_type: LeadEntityType
    relationship_type: LeadRelationshipType
    confidence_score: float
    source_sentence: str


PATTERN_ADMINISTERED = re.compile(
    r'\badministered\s+by\s+(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|\bfor\b|\bon\b|\bunder\b|$)',
    re.IGNORECASE,
)
PATTERN_PUBLISHED = re.compile(
    r'\bpublished\s+by\s+(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|\bfor\b|\bon\b|$)',
    re.IGNORECASE,
)
PATTERN_CATALOG_OWNED = re.compile(
    r'\b(?:catalog(?:\s+is)?\s+owned\s+by|rights\s+owned\s+by|owned\s+by)\s+(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|\bfor\b|\bon\b|$)',
    re.IGNORECASE,
)
PATTERN_COURTESY_OF = re.compile(
    r'\b(?:master\s+recording\s+courtesy\s+of|master\s+courtesy\s+of|courtesy\s+of)\s+(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|\bfor\b|\bon\b|$)',
    re.IGNORECASE,
)
PATTERN_LICENSED_TO = re.compile(
    r'\b(?:under\s+exclusive\s+license\s+to|exclusively\s+licensed\s+to|licensed\s+to)\s+(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|\bfor\b|\bon\b|$)',
    re.IGNORECASE,
)
PATTERN_SUBSIDIARY_OF = re.compile(
    r'\b(?:a\s+division\s+of|subsidiary\s+of|parent\s+company\s+is)\s+(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|\bfor\b|\bon\b|$)',
    re.IGNORECASE,
)
PATTERN_ESTATE = re.compile(
    r'\bEstate\s+of\s+([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+)+)',
)
PATTERN_TRUST = re.compile(
    r'\b(?:The\s+)?([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+)*\s+(?:Living\s+Trust|Family\s+Trust|Revocable\s+Trust|Trust|Foundation))\b',
)
PATTERN_TRADEMARK_ASSIGNMENT = re.compile(
    r'\b(?:assigned\s+to\s+|assignee:\s*|registrant:\s*|trademark\s+owner:\s*)(?:the\s+)?([A-Z0-9][A-Za-z0-9&.,\'\s\-]+?)(?=[,.;\(\)\[\]]|\band\b|$)',
    re.IGNORECASE,
)


def split_into_sentences(text: str) -> List[str]:
    """Splits arbitrary text block into distinct sentences respecting punctuation boundaries."""
    if not text:
        return []
    normalized = re.sub(r'[\r\n\t]+', " ", text)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(])', normalized)
    return [s.strip() for s in sentences if s and len(s.strip()) > 3]


def build_query_extension(entity_name: str, entity_type: LeadEntityType) -> str:
    """Generates an actionable follow-up query extension tailored to the entity type."""
    clean = normalize_entity_name(entity_name)
    if entity_type == LeadEntityType.PUBLISHER:
        return f'"{clean}" music publishing sync licensing catalog contact'
    if entity_type == LeadEntityType.LABEL:
        return f'"{clean}" master recording sync licensing clearance contact'
    if entity_type in (LeadEntityType.ESTATE, LeadEntityType.TRUST_FOUNDATION):
        return f'"{clean}" estate representative executor rights clearance'
    if entity_type == LeadEntityType.ASSIGNEE:
        return f'"{clean}" trademark assignment owner USPTO'
    if entity_type == LeadEntityType.CORPORATE_PARENT:
        return f'"{clean}" corporate music licensing clearance catalog'
    return f'"{clean}" rights owner licensing clearance contact'


def _evaluate_candidate(
    raw_name: str,
    default_type: LeadEntityType,
    relationship: LeadRelationshipType,
    sentence: str,
    base_confidence: float,
) -> Optional[RawMatch]:
    """Validates candidate against filters and assigns catalog-enhanced confidence."""
    if is_false_lead(raw_name):
        return None
    matched = match_known_entity(raw_name)
    if matched:
        canonical_name, detected_type = matched
        final_type = detected_type
        final_conf = min(0.98, base_confidence + 0.15)
        clean_name = canonical_name
    else:
        clean_name = normalize_entity_name(raw_name)
        final_type = default_type
        final_conf = base_confidence
    if not clean_name or len(clean_name) < 2:
        return None
    return RawMatch(clean_name, final_type, relationship, final_conf, sentence)


def extract_regex_matches(sentence: str) -> List[RawMatch]:
    """Executes deterministic regular expression scan across single sentence."""
    matches: List[RawMatch] = []
    specs: List[Tuple[re.Pattern, LeadEntityType, LeadRelationshipType, float]] = [
        (PATTERN_ADMINISTERED, LeadEntityType.PUBLISHER, LeadRelationshipType.ADMINISTERED_BY, 0.85),
        (PATTERN_PUBLISHED, LeadEntityType.PUBLISHER, LeadRelationshipType.PUBLISHED_BY, 0.82),
        (PATTERN_CATALOG_OWNED, LeadEntityType.PUBLISHER, LeadRelationshipType.CATALOG_OWNED_BY, 0.80),
        (PATTERN_COURTESY_OF, LeadEntityType.LABEL, LeadRelationshipType.COURTESY_OF, 0.88),
        (PATTERN_LICENSED_TO, LeadEntityType.LABEL, LeadRelationshipType.LICENSED_TO, 0.82),
        (PATTERN_SUBSIDIARY_OF, LeadEntityType.CORPORATE_PARENT, LeadRelationshipType.SUBSIDIARY_OF, 0.86),
        (PATTERN_TRADEMARK_ASSIGNMENT, LeadEntityType.ASSIGNEE, LeadRelationshipType.TRADEMARK_ASSIGNED, 0.84),
    ]
    for pattern, def_type, rel_type, base_conf in specs:
        for m in pattern.finditer(sentence):
            cand = _evaluate_candidate(m.group(1), def_type, rel_type, sentence, base_conf)
            if cand:
                matches.append(cand)

    for m in PATTERN_ESTATE.finditer(sentence):
        full_name = f"Estate of {m.group(1).strip()}"
        cand = _evaluate_candidate(full_name, LeadEntityType.ESTATE, LeadRelationshipType.ESTATE_ADMINISTERED, sentence, 0.90)
        if cand:
            matches.append(cand)

    for m in PATTERN_TRUST.finditer(sentence):
        cand = _evaluate_candidate(m.group(1).strip(), LeadEntityType.TRUST_FOUNDATION, LeadRelationshipType.ESTATE_ADMINISTERED, sentence, 0.88)
        if cand:
            matches.append(cand)

    return matches
