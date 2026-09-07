"""
backend/agents/research/entity_catalog.py

Standardized catalogs of music publishers, record labels, and false-lead rejections.
Sprint 3.2: Snippet Entity & Lead Extractor Specialist.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Set, Tuple
from backend.agents.research.lead_types import LeadEntityType

KNOWN_PUBLISHERS: Dict[str, str] = {
    "sony music publishing": "Sony Music Publishing",
    "sony/atv": "Sony Music Publishing",
    "sony/atv music publishing": "Sony Music Publishing",
    "universal music publishing group": "Universal Music Publishing Group",
    "umpg": "Universal Music Publishing Group",
    "universal music publishing": "Universal Music Publishing Group",
    "warner chappell": "Warner Chappell Music",
    "warner chappell music": "Warner Chappell Music",
    "warner/chappell": "Warner Chappell Music",
    "bmg rights management": "BMG Rights Management",
    "bmg": "BMG Rights Management",
    "concord music": "Concord Music",
    "concord music publishing": "Concord Music",
    "concord": "Concord Music",
    "kobalt": "Kobalt Music Group",
    "kobalt music": "Kobalt Music Group",
    "kobalt music group": "Kobalt Music Group",
    "kobalt music publishing": "Kobalt Music Group",
    "primary wave": "Primary Wave Music",
    "primary wave music": "Primary Wave Music",
    "downtown music publishing": "Downtown Music Publishing",
    "peermusic": "peermusic",
    "peer music": "peermusic",
}

KNOWN_LABELS: Dict[str, str] = {
    "columbia records": "Columbia Records",
    "columbia": "Columbia Records",
    "atlantic records": "Atlantic Records",
    "atlantic": "Atlantic Records",
    "interscope records": "Interscope Records",
    "interscope": "Interscope Records",
    "interscope geffen a&m": "Interscope Records",
    "capitol records": "Capitol Records",
    "capitol": "Capitol Records",
    "rca records": "RCA Records",
    "rca": "RCA Records",
    "decca records": "Decca Records",
    "decca": "Decca Records",
    "verve records": "Verve Records",
    "verve": "Verve Records",
    "republic records": "Republic Records",
    "def jam": "Def Jam Recordings",
    "def jam recordings": "Def Jam Recordings",
    "epic records": "Epic Records",
    "island records": "Island Records",
    "motown": "Motown Records",
    "motown records": "Motown Records",
    "geffen records": "Geffen Records",
    "warner records": "Warner Records",
    "virgin records": "Virgin Records",
    "blue note records": "Blue Note Records",
}

FALSE_LEAD_REJECTIONS: Set[str] = {
    "abbey road studios", "sunset sound", "electric lady studios", "record plant",
    "sound city", "criteria studios", "capitol studios", "olympic studios",
    "spotify", "apple music", "youtube", "tidal", "amazon music", "soundcloud",
    "bandcamp", "tiktok", "instagram", "twitter", "facebook",
    "red bull", "gibson", "fender", "marshall", "billboard", "grammy awards",
    "super bowl", "various artists", "unknown", "public domain", "anonymous",
    "traditional", "instrumental", "remastered", "live version", "studio",
}


def normalize_entity_name(raw_name: str) -> str:
    """Normalizes whitespace, casing, and trailing punctuation of extracted names."""
    if not raw_name:
        return ""
    clean = re.sub(r'[\r\n\t]+', " ", raw_name)
    clean = clean.strip(" \t\n\r\"'.,;:()[]{}")
    clean = re.sub(r'\s+', " ", clean)
    clean = re.sub(r'\s+(?:inc\.?|llc|ltd\.?|corp\.?|corporation)$', "", clean, flags=re.IGNORECASE)
    return clean.strip(" \t\n\r\"'.,;:()[]{}")


def is_false_lead(candidate: str) -> bool:
    """Evaluates if candidate entity is a non-licensable studio, sponsor, or generic tag."""
    normalized = normalize_entity_name(candidate).lower()
    if not normalized or len(normalized) < 2:
        return True
    if normalized in FALSE_LEAD_REJECTIONS:
        return True
    return any(rejected in normalized for rejected in ("studios", "recording studio") if len(normalized.split()) > 1)


def match_known_entity(candidate: str) -> Optional[Tuple[str, LeadEntityType]]:
    """Matches raw entity candidate against curated global rights owner catalogs."""
    normalized = normalize_entity_name(candidate).lower()
    if normalized in KNOWN_PUBLISHERS:
        return KNOWN_PUBLISHERS[normalized], LeadEntityType.PUBLISHER
    if normalized in KNOWN_LABELS:
        return KNOWN_LABELS[normalized], LeadEntityType.LABEL
    for key, canonical in KNOWN_PUBLISHERS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', normalized):
            return canonical, LeadEntityType.PUBLISHER
    for key, canonical in KNOWN_LABELS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', normalized):
            return canonical, LeadEntityType.LABEL
    return None
