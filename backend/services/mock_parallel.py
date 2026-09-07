"""
backend/services/mock_parallel.py

Deterministic offline replay server and mock client for Parallel Search API testing.
Provides golden fixtures for benchmark queries and simulated fault injection.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional

from backend.services.domain_authority import (
    classify_domain_tier,
    extract_canonical_domain,
    score_domain_authority,
)
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelAuthError,
    ParallelRateLimitError,
    ParallelSearchFinding,
    ParallelSearchRequest,
    ParallelSearchResult,
    ParallelServerError,
    ParallelTimeoutError,
)

FIXTURES: List[Dict[str, Any]] = [
    {
        "match_keys": ["clair de lune", "debussy"],
        "findings": [
            {
                "url": "https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?Search_Arg=Clair+de+Lune+Debussy&DB=local",
                "title": "U.S. Copyright Office - Clair de Lune Musical Work Catalog Record",
                "publish_date": "1905-01-01",
                "excerpts": [
                    "Musical composition 'Clair de Lune' by Claude Debussy published 1905. Public domain composition status.",
                    "Master recordings require individual synchronization licenses from respective record labels.",
                ],
            },
            {
                "url": "https://www.ascap.com/repertory#/ace/search/workID/330128491",
                "title": "ASCAP Clearance Repertory: Clair de Lune (Debussy)",
                "publish_date": "2024-01-15",
                "excerpts": [
                    "Work Title: CLAIR DE LUNE. Composer: DEBUSSY CLAUDE. Status: Public Domain Composition.",
                    "Arrangements and sound recordings may be subject to active copyright administration.",
                ],
            },
        ],
    },
    {
        "match_keys": ["apollo 11", "moon landing", "nasa"],
        "findings": [
            {
                "url": "https://images.nasa.gov/details/as11-40-5874",
                "title": "NASA Image and Video Library - Apollo 11 Lunar Module Descent and Surface Broadcast",
                "publish_date": "1969-07-20",
                "excerpts": [
                    "NASA astronaut Neil Armstrong broadcasts from the lunar surface. Work of the U.S. Federal Government.",
                    "Generally in the public domain under 17 U.S.C. 105; commercial use requires no likeness infringement.",
                ],
            },
            {
                "url": "https://www.archives.gov/research/military/space/apollo-11",
                "title": "National Archives (NARA) - Apollo 11 Mission Audio, Video & Transmission Clearance",
                "publish_date": "2023-05-10",
                "excerpts": [
                    "Original audio broadcasts and video transmissions created by NASA personnel are unrestricted public records.",
                ],
            },
        ],
    },
    {
        "match_keys": ["coca-cola"],
        "findings": [
            {
                "url": "https://tmsearch.uspto.gov/bin/showfield?f=doc&state=4801:1.1.1",
                "title": "Modern USPTO Trademark Search - COCA-COLA Word Mark Registration #0022406",
                "publish_date": "2024-02-01",
                "excerpts": [
                    "Word Mark: COCA-COLA. Goods and Services: Beverages. Live/Dead: LIVE. Owner: The Coca-Cola Company.",
                    "Status: Registered and Renewed. Third-party film use requires trademark clearance or nominative fair use review.",
                ],
            },
        ],
    },
    {
        "match_keys": ["marlboro"],
        "findings": [
            {
                "url": "https://tmsearch.uspto.gov/bin/showfield?f=doc&state=4801:2.1.1",
                "title": "Modern USPTO Trademark Search - MARLBORO Word Mark Registration #0068509",
                "publish_date": "2024-01-10",
                "excerpts": [
                    "Word Mark: MARLBORO. Status: LIVE. Owner: Philip Morris USA Inc. Trademark active and enforced.",
                    "Incidental background display in dramatic motion pictures evaluated under incidental trademark principles.",
                ],
            },
        ],
    },
    {
        "match_keys": ["detective magazine", "shadows of manhattan", "poster"],
        "findings": [
            {
                "url": "https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?Search_Arg=Crime+Detective+1944&DB=local",
                "title": "LOC Catalog of Copyright Entries: Crime Detective Magazine Poster (1944)",
                "publish_date": "1944-03-15",
                "excerpts": [
                    "Periodical cover illustration 'Shadows of Manhattan' registered March 1944. Copyright not renewed in 28th year.",
                    "Status: Entered public domain in 1972 due to non-renewal under the 1909 Copyright Act.",
                ],
            },
        ],
    },
    {
        "match_keys": ["midnight echoes at twilight", "-lyrics"],
        "findings": [
            {
                "url": "https://www.ascap.com/repertory#/ace/search/workID/891244012",
                "title": "ASCAP Repertory: Midnight Echoes at Twilight (Evelyn Vance Catalog)",
                "publish_date": "2023-11-20",
                "excerpts": [
                    "Work: MIDNIGHT ECHOES AT TWILIGHT. Writer: VANCE EVELYN. Publisher: VANCE MUSIC PUBLISHING LLC.",
                    "Administered worldwide by Concord Music Publishing. All synchronization rights reserved.",
                ],
            },
        ],
    },
]


class MockParallelClient:
    """Mock client returning deterministic fixtures for offline test execution."""

    def __init__(
        self,
        simulated_latency_ms: float = 12.0,
        simulate_failure: Optional[str] = None,
    ):
        self.simulated_latency_ms = simulated_latency_ms
        self.simulate_failure = simulate_failure
        self.call_count: int = 0

    def _match_fixtures(self, query: str) -> List[ParallelSearchFinding]:
        """Matches query text against stored fixture keys."""
        q_lower = query.lower()
        for fix in FIXTURES:
            keys = fix["match_keys"]
            if all(k.lower() in q_lower for k in keys):
                findings = []
                for r in fix["findings"]:
                    dom = extract_canonical_domain(r["url"])
                    findings.append(
                        ParallelSearchFinding(
                            url=r["url"],
                            title=r["title"],
                            domain=dom,
                            publish_date=r.get("publish_date"),
                            excerpts=r.get("excerpts", []),
                            full_excerpt="\n".join(r.get("excerpts", [])),
                            authority_tier=classify_domain_tier(dom),
                            authority_score=score_domain_authority(dom),
                            confidence_score=0.92,
                        )
                    )
                return findings
        return []

    async def search(self, request: ParallelSearchRequest) -> ParallelSearchResult:
        """Simulates an asynchronous Parallel Search execution."""
        self.call_count += 1
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        if self.simulate_failure == "429":
            raise ParallelRateLimitError("Mock simulated HTTP 429 rate limit")
        if self.simulate_failure == "5xx":
            raise ParallelServerError("Mock simulated HTTP 503 gateway drop")
        if self.simulate_failure == "timeout":
            raise ParallelTimeoutError("Mock simulated request timeout")
        if self.simulate_failure == "auth":
            raise ParallelAuthError("Mock simulated invalid API key (401)")

        combined_q = " ".join(request.search_queries)
        findings = self._match_fixtures(combined_q)
        req_hash = request.compute_payload_hash()
        resp_data = {"search_id": f"mock_search_{self.call_count}", "results": [f.model_dump() for f in findings]}
        resp_hash = hashlib.sha256(json.dumps(resp_data, sort_keys=True).encode("utf-8")).hexdigest()

        return ParallelSearchResult(
            search_id=f"mock_search_{self.call_count}",
            findings=findings,
            raw_response_hash=resp_hash,
            request_payload_hash=req_hash,
            latency_ms=self.simulated_latency_ms,
            http_status=200,
            top_authority_tier=findings[0].authority_tier if findings else DomainAuthorityTier.TIER_4_GENERAL_WEB,
        )
