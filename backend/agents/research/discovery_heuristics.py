"""
backend/agents/research/discovery_heuristics.py

Heuristic rule engines and pattern matchers for secondary IP detection.
Sprint 3.2: Mid-Run Claim Discovery & Secondary IP Detection.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import re
from typing import List, Set
from pydantic import BaseModel, ConfigDict, Field

from backend.agents.research.discovery_types import SecondaryIPType
from backend.agents.research.query_types import AssetClass

STOP_LOOKAHEAD = r"(?=\s+(?:on|in|at|for|as|was|is|during|with|and)\b|\s*[\(,\.\-–—]|\s*$)"

SAMPLE_RE_1 = re.compile(
    r'(?i)(?:contains?\s+(?:an?\s+)?samples?\s+(?:from|of)|samples?\s+(?:from|of)?|'
    r'sampled\s+(?:from|by|in)?|sample\s+of)\s+["\u201c]?([^"\u201d\n\r]+?)["\u201d]?'
    r'\s+(?:by|performed by|recorded by|courtesy of)\s+([A-Z0-9][A-Za-z0-9\s&.\'-]{1,40}?)'
    + STOP_LOOKAHEAD
)
SAMPLE_RE_2 = re.compile(
    r'(?i)\buncredited\s+samples?\s+(?:from|of)?\s+["\u201c]?([^"\u201d\n\r]+?)["\u201d]?'
    r'\s+by\s+([A-Z0-9][A-Za-z0-9\s&.\'-]{1,40}?)'
    + STOP_LOOKAHEAD
)
INTERP_RE_1 = re.compile(
    r'(?i)(?:interpolates?|interpolated\s+(?:from)?|interpolation\s+of)\s+'
    r'(?:elements\s+of\s+)?["\u201c]?([^"\u201d\n\r]+?)["\u201d]?'
    r'\s+(?:by|written by|composed by)\s+([A-Z0-9][A-Za-z0-9\s&.\'-]{1,40}?)'
    + STOP_LOOKAHEAD
)
INTERP_RE_2 = re.compile(
    r'(?i)(?:melody|lyrics|hook|chorus)\s+(?:is\s+an\s+interpolation\s+of|interpolates?|'
    r'interpolated\s+from)\s+["\u201c]?([^"\u201d\n\r]+?)["\u201d]?'
    r'(?:\s+by\s+([A-Z0-9][A-Za-z0-9\s&.\'-]{1,40}?))?'
    + STOP_LOOKAHEAD
)
ARTIST_RE_1 = re.compile(
    r'(?i)\b(?:feat\.|featuring|ft\.)\s+([A-Z0-9][A-Za-z0-9\s&.\'-]{1,40}?)'
    + STOP_LOOKAHEAD
)
ARTIST_RE_2 = re.compile(
    r'(?i)\b(?:vocals?\s+by|voice\s+of|likeness\s+of|guest\s+appearance\s+by)\s+'
    r'([A-Z0-9][A-Za-z0-9\s&.\'-]{2,40}?)'
    + STOP_LOOKAHEAD
)
TRADEMARK_RE_1 = re.compile(
    r'(?i)\b(?:secondary\s+trademark|trademark\s+visible|prominently\s+features?\s+(?:the\s+)?logo\s+of|'
    r'brand\s+placement\s+for|unblurred\s+logo\s+of)\s*:?\s*["\u201c]?([A-Z0-9][A-Za-z0-9\s&\'.-]{2,30})["\u201d]?'
)
TRADEMARK_RE_2 = re.compile(
    r'(?i)\btrademark\s+["\u201c]?([A-Z0-9][A-Za-z0-9\s&\'.-]{2,30})["\u201d]?'
    r'\s+(?:appearing|visible|featured|seen)\s+in'
)


class RawCandidate(BaseModel):
    """Raw candidate finding extracted by heuristic matchers before normalization."""
    model_config = ConfigDict(frozen=True)

    detected_entity: str = Field(..., min_length=1)
    category: AssetClass
    discovery_type: SecondaryIPType
    rationale: str = Field(..., min_length=1)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


def extract_musical_samples(text: str) -> List[RawCandidate]:
    """Detects credited and uncredited musical samples in research text."""
    results: List[RawCandidate] = []
    seen_entities: Set[str] = set()
    for pattern in (SAMPLE_RE_1, SAMPLE_RE_2):
        for match in pattern.finditer(text):
            song, artist = match.group(1).strip(), match.group(2).strip()
            entity = f"{song} by {artist}"
            norm = entity.lower()
            if norm not in seen_entities:
                seen_entities.add(norm)
                results.append(RawCandidate(
                    detected_entity=entity,
                    category=AssetClass.MUSIC,
                    discovery_type=SecondaryIPType.MUSICAL_SAMPLE,
                    rationale=f"Musical sample detected: '{song}' by {artist}.",
                    confidence=0.92,
                ))
    return results


def extract_interpolations(text: str) -> List[RawCandidate]:
    """Detects melodic, lyrical, or harmonic interpolations in research text."""
    results: List[RawCandidate] = []
    seen_songs: Set[str] = set()
    for match in INTERP_RE_1.finditer(text):
        song, artist = match.group(1).strip(), match.group(2).strip()
        seen_songs.add(song.lower())
        entity = f"{song} by {artist}"
        results.append(RawCandidate(
            detected_entity=entity,
            category=AssetClass.MUSIC,
            discovery_type=SecondaryIPType.INTERPOLATION,
            rationale=f"Interpolation detected: '{song}' by {artist}.",
            confidence=0.88,
        ))
    for match in INTERP_RE_2.finditer(text):
        song = match.group(1).strip()
        if song.lower() in seen_songs:
            continue
        seen_songs.add(song.lower())
        artist = match.group(2).strip() if match.group(2) else ""
        entity = f"{song} by {artist}" if artist else song
        results.append(RawCandidate(
            detected_entity=entity,
            category=AssetClass.MUSIC,
            discovery_type=SecondaryIPType.INTERPOLATION,
            rationale=f"Melodic/lyrical interpolation detected: '{song}'.",
            confidence=0.86,
        ))
    return results


def extract_featured_artists(text: str) -> List[RawCandidate]:
    """Detects featured artists with distinct voice or likeness rights."""
    results: List[RawCandidate] = []
    seen: Set[str] = set()
    for pattern in (ARTIST_RE_1, ARTIST_RE_2):
        for match in pattern.finditer(text):
            artist = match.group(1).strip()
            norm = artist.lower()
            if len(artist) > 1 and not norm.startswith("the track") and norm not in seen:
                seen.add(norm)
                results.append(RawCandidate(
                    detected_entity=artist,
                    category=AssetClass.LIKENESS,
                    discovery_type=SecondaryIPType.FEATURED_ARTIST,
                    rationale=f"Featured artist likeness/voice rights detected: '{artist}'.",
                    confidence=0.89,
                ))
    return results


def extract_secondary_trademarks(text: str) -> List[RawCandidate]:
    """Detects secondary trademarks appearing in broadcasts or footage."""
    results: List[RawCandidate] = []
    seen: Set[str] = set()
    for pattern in (TRADEMARK_RE_1, TRADEMARK_RE_2):
        for match in pattern.finditer(text):
            brand = match.group(1).strip()
            norm = brand.lower()
            if norm not in seen:
                seen.add(norm)
                results.append(RawCandidate(
                    detected_entity=brand,
                    category=AssetClass.BRAND,
                    discovery_type=SecondaryIPType.SECONDARY_TRADEMARK,
                    rationale=f"Secondary trademark display detected in archival material: '{brand}'.",
                    confidence=0.84,
                ))
    return results


def scan_text_for_candidates(text: str) -> List[RawCandidate]:
    """Aggregates all secondary IP heuristic detectors across the text input."""
    candidates: List[RawCandidate] = []
    candidates.extend(extract_musical_samples(text))
    candidates.extend(extract_interpolations(text))
    candidates.extend(extract_featured_artists(text))
    candidates.extend(extract_secondary_trademarks(text))
    return candidates
