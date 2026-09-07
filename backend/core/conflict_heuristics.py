"""
backend/core/conflict_heuristics.py

Pattern matching and statutory heuristics for Corroboration and Conflict Arbitration.
Identifies US Federal Government creations (17 U.S.C. § 105), network master
broadcasts (CBS, telecasts), public domain assertions, and active copyright claims.
"""

from __future__ import annotations

import re
from typing import Sequence

from backend.core.conflict_types import (
    ClaimStatusAssertion,
    EvidenceFinding,
    RightsLayer,
)

FED_PATTERNS = (
    re.compile(r"\b17\s*u\.?s\.?c\.?\s*§?\s*105\b", re.I),
    re.compile(r"\bwork\s+of\s+the\s+u\.?s\.?\s+government\b", re.I),
    re.compile(r"\bnasa\b", re.I),
    re.compile(r"\bnara\b", re.I),
    re.compile(r"\bu\.?s\.?\s+federal\s+government\b", re.I),
)

NET_PATTERNS = (
    re.compile(r"\bcbs\s*(?:news)?\b", re.I),
    re.compile(r"\bbroadcast\s+commentary\b", re.I),
    re.compile(r"\bmaster\s+recording\b", re.I),
    re.compile(r"\bnetwork\s+(?:television\s+)?broadcast\b", re.I),
    re.compile(r"\bmaster\s+clearance\b", re.I),
    re.compile(r"\bnetwork\s+release\b", re.I),
    re.compile(r"\bprivate\s+master\b", re.I),
    re.compile(r"\bedited\s+master\b", re.I),
)

PD_PATTERNS = (
    re.compile(r"\bpublic\s+domain\b", re.I),
    re.compile(r"\bunrestricted\s+public\b", re.I),
    re.compile(r"\bno\s+active\s+copyright\b", re.I),
    re.compile(r"\bexpired\b", re.I),
)

COPY_PATTERNS = (
    re.compile(r"\ball\s+rights\s+reserved\b", re.I),
    re.compile(r"\bcopyrighted\b", re.I),
    re.compile(r"\blicensing\s+required\b", re.I),
    re.compile(r"\bprivate\s+copyright\b", re.I),
    re.compile(r"\bexclusive\s+(?:sync|copyright|rights)\b", re.I),
)


class ConflictHeuristics:
    """Heuristic evaluators for evidence findings."""

    @staticmethod
    def _matches_any(text: str, patterns: Sequence[re.Pattern]) -> bool:
        return any(p.search(text) for p in patterns)

    @classmethod
    def is_federal(cls, f: EvidenceFinding) -> bool:
        """Detects US Federal Government work under 17 U.S.C. § 105."""
        if f.is_federal_work or (f.statutory_citation and "105" in f.statutory_citation):
            return True
        text = f"{f.source_title} {f.excerpt} {f.snippet or ''}"
        return cls._matches_any(text, FED_PATTERNS)

    @classmethod
    def is_network_master(cls, f: EvidenceFinding) -> bool:
        """Detects private broadcast master, commentary, or telecast rights."""
        if f.rights_layer == RightsLayer.RECORDING_OR_BROADCAST_MASTER:
            return True
        text = f"{f.source_title} {f.excerpt} {f.snippet or ''}"
        return cls._matches_any(text, NET_PATTERNS)

    @classmethod
    def is_public_domain(cls, f: EvidenceFinding) -> bool:
        """Detects explicit assertion of public domain status."""
        if f.asserted_status == ClaimStatusAssertion.PUBLIC_DOMAIN:
            return True
        text = f"{f.source_title} {f.excerpt} {f.snippet or ''}"
        return cls._matches_any(text, PD_PATTERNS)

    @classmethod
    def is_copyrighted(cls, f: EvidenceFinding) -> bool:
        """Detects assertion of private copyright or required licensing."""
        if f.asserted_status in (ClaimStatusAssertion.COPYRIGHTED, ClaimStatusAssertion.LICENSING_REQUIRED):
            return True
        text = f"{f.source_title} {f.excerpt} {f.snippet or ''}"
        return cls._matches_any(text, COPY_PATTERNS)
