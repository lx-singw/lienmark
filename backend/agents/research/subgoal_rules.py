"""
backend/agents/research/subgoal_rules.py

Rules matrix, identifier regexes, and registry targets for rights subgoal decomposition.
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import re
from typing import Dict, List, Pattern
from backend.services.parallel_types import DomainAuthorityTier

SAMPLE_TRIGGER_KEYWORDS: List[str] = [
    "sample",
    "sampled",
    "sampling",
    "interpolation",
    "interpolated",
    "interpolating",
    "remix",
    "remixed",
    "mashup",
    "bootleg",
    "cover",
    "derivative",
    "replayed",
    "replay",
    "adapted from",
    "contains a sample",
]

IDENTIFIER_PATTERNS: Dict[str, Pattern[str]] = {
    "ISWC": re.compile(r"\bT-?\d{3}\.?\d{3}\.?\d{3}-?\d\b", re.IGNORECASE),
    "ISRC": re.compile(r"\b[A-Z]{2}-?[A-Z0-9]{3}-?\d{2}-?\d{5}\b", re.IGNORECASE),
    "ASCAP_BMI_WORK_ID": re.compile(
        r"\b(?:ASCAP|BMI)\s*(?:Work\s*)?(?:ID|#)?\s*[:#]?\s*(\d{5,10})\b",
        re.IGNORECASE,
    ),
    "USPTO_REG_NO": re.compile(
        r"\b(?:Reg(?:istration)?\.?\s*(?:No\.?)?|RN)\s*[:#]?\s*(\d{6,8})\b",
        re.IGNORECASE,
    ),
    "USPTO_SERIAL_NO": re.compile(
        r"\b(?:Serial\s*(?:No\.?)?|SN)\s*[:#]?\s*(\d{7,8})\b",
        re.IGNORECASE,
    ),
    "NICE_CLASS": re.compile(
        r"\b(?:Class|IC|Nice\s*Class)\s*[:#]?\s*(\d{1,2})\b",
        re.IGNORECASE,
    ),
    "NASA_NARA_ID": re.compile(
        r"\b(?:NASA\s*ID|NARA\s*ID|ARC\s*Identifier|Record\s*Group)\s*[:#]?\s*([A-Za-z0-9_\-]+)\b",
        re.IGNORECASE,
    ),
    "COPYRIGHT_REG_NO": re.compile(
        r"\b(?:TX|VA|PA|RE|SR)\s*-?\s*\d{3,7}(?:-\d{3})?\b",
        re.IGNORECASE,
    ),
    "PUBLIC_DOMAIN_NOTICE": re.compile(
        r"\b(?:public\s*domain|17\s*U\.?S\.?C\.?\s*§?\s*105|no\s*copyright\s*protection)\b",
        re.IGNORECASE,
    ),
}

AUTHORITY_WEIGHTS: Dict[DomainAuthorityTier, float] = {
    DomainAuthorityTier.TIER_1_GOVERNMENT: 1.0,
    DomainAuthorityTier.TIER_2_RIGHTS_ORG: 0.85,
    DomainAuthorityTier.TIER_3_NEWS_EDITORIAL: 0.55,
    DomainAuthorityTier.TIER_4_GENERAL_WEB: 0.25,
}

MUSIC_REGISTRIES: Dict[str, List[str]] = {
    "publishing": ["site:ascap.com", "site:bmi.com", "site:sesac.com", "site:cocatalog.loc.gov"],
    "master": ["site:isrc.soundexchange.com", "site:discogs.com", "site:musicbrainz.org"],
    "sync": ["site:songfinder.com", "site:tunelicensing.com"],
}

BRAND_REGISTRIES: Dict[str, List[str]] = {
    "word_mark": ["site:tmsearch.uspto.gov", "site:uspto.report", "site:wipo.int"],
    "logo_stylized": ["site:tmsearch.uspto.gov", "site:cocatalog.loc.gov"],
    "goods_services": ["site:tmsearch.uspto.gov", "site:uspto.report"],
}

FOOTAGE_REGISTRIES: Dict[str, List[str]] = {
    "federal": ["site:images.nasa.gov", "site:archives.gov", "site:loc.gov"],
    "broadcaster": ["site:cbsnews.com", "site:nbcuniversal.com", "site:itnsource.com"],
}

ARTWORK_REGISTRIES: Dict[str, List[str]] = {
    "original": ["site:cocatalog.loc.gov", "site:loc.gov", "site:si.edu"],
    "periodical": ["site:cocatalog.loc.gov", "site:pulpmags.org"],
    "renewal": ["site:cocatalog.loc.gov", "site:exhibits.stanford.edu/copyrightrenewals"],
}
