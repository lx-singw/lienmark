"""
backend/services/domain_authority.py

Domain authority classification, TLD parsing, and authority scoring for clearance research.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from urllib.parse import urlsplit
from backend.services.parallel_types import DomainAuthorityTier

# Statutory Government Registries & Official IP Offices
TIER_1_DOMAINS: frozenset[str] = frozenset({
    "uspto.gov",
    "tmsearch.uspto.gov",
    "uspto.report",
    "copyright.gov",
    "cocatalog.loc.gov",
    "loc.gov",
    "wipo.int",
    "archives.gov",
    "images.nasa.gov",
    "nasa.gov",
    "si.edu",
    "govinfo.gov",
})

# Statutory Collective Management & Performing Rights Organizations
TIER_2_DOMAINS: frozenset[str] = frozenset({
    "ascap.com",
    "bmi.com",
    "sesac.com",
    "soundexchange.com",
    "harryfox.com",
    "songview.com",
    "ccli.com",
    "cisac.org",
    "cmgworldwide.com",
    "sagaftra.org",
    "prsformusic.com",
    "gema.de",
    "sacem.fr",
    "socan.com",
})

# Trade Press & Entertainment Editorial Publications
TIER_3_DOMAINS: frozenset[str] = frozenset({
    "billboard.com",
    "variety.com",
    "hollywoodreporter.com",
    "deadline.com",
    "reuters.com",
    "nytimes.com",
    "wsj.com",
    "bbc.com",
    "discogs.com",
    "allmusic.com",
    "imdb.com",
    "wikipedia.org",
})

TIER_SCORES: dict[DomainAuthorityTier, float] = {
    DomainAuthorityTier.TIER_1_GOVERNMENT: 1.00,
    DomainAuthorityTier.TIER_2_RIGHTS_ORG: 0.85,
    DomainAuthorityTier.TIER_3_NEWS_EDITORIAL: 0.60,
    DomainAuthorityTier.TIER_4_GENERAL_WEB: 0.25,
}


def extract_canonical_domain(url: str) -> str:
    """Extracts lowercased canonical hostname from URL, stripping www and port numbers."""
    if not url or not isinstance(url, str):
        return "unknown"
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    try:
        netloc = urlsplit(cleaned).netloc.lower()
        host = netloc.split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        return host or "unknown"
    except Exception:
        return "unknown"


def classify_domain_tier(domain: str) -> DomainAuthorityTier:
    """Classifies domain into one of 4 authority tiers based on exact or suffix match."""
    dom = domain.lower().strip()
    if dom.endswith(".gov") or dom.endswith(".mil") or dom in TIER_1_DOMAINS:
        return DomainAuthorityTier.TIER_1_GOVERNMENT
    for t1 in TIER_1_DOMAINS:
        if dom == t1 or dom.endswith("." + t1):
            return DomainAuthorityTier.TIER_1_GOVERNMENT
    for t2 in TIER_2_DOMAINS:
        if dom == t2 or dom.endswith("." + t2):
            return DomainAuthorityTier.TIER_2_RIGHTS_ORG
    for t3 in TIER_3_DOMAINS:
        if dom == t3 or dom.endswith("." + t3):
            return DomainAuthorityTier.TIER_3_NEWS_EDITORIAL
    return DomainAuthorityTier.TIER_4_GENERAL_WEB


def score_domain_authority(domain: str) -> float:
    """Returns numeric trust score [0.0 - 1.0] for domain based on classified tier."""
    tier = classify_domain_tier(domain)
    return TIER_SCORES.get(tier, 0.25)
