"""
backend/agents/research/directed_research.py

Targeted query reformulator and directed research coordinator for counsel re-investigations.
Sprint 4.3: Counsel Rejection & Directed Re-Investigation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Optional

from backend.agents.research.directed_research_sanitizer import DirectiveSanitizer
from backend.agents.research.directed_research_types import (
    DirectedResearchError,
    DirectedSearchRequest,
    DirectedSearchResult,
    DirectedSearchStatus,
    DirectedSearchTimeoutError,
    DirectiveConstraint,
    DirectiveConstraintType,
    SanitizedDirective,
)
from backend.domain.models import PublicEvidenceSnapshot
from backend.services.parallel_service import ParallelSearchService


class DirectedQueryReformulator:
    """Merges baseline claim identity with sanitized directive constraints."""

    REGISTRY_TEMPLATES = {
        "USPTO": "site:tmsearch.uspto.gov OR site:uspto.report trademark status assignment",
        "ASCAP": "ASCAP rights assignment repertoire",
        "BMI": "BMI rights repertoire catalog",
        "LOC": "LOC copyright renewal public domain registration",
        "USCO": "US Copyright Office registration catalog records",
    }

    def _build_primary(self, title: str, artist: Optional[str], addon: str) -> str:
        """Constructs identity-anchored primary directed query."""
        parts = [f'"{title.strip()}"']
        if artist and artist.strip():
            parts.append(f'"{artist.strip()}"')
        if addon:
            parts.append(addon)
        return " ".join(parts).strip()

    def _build_registry_targeted(
        self, title: str, artist: Optional[str], constraints: List[DirectiveConstraint], addon: str
    ) -> Optional[str]:
        """Builds registry-specific targeted query if registry constraint exists."""
        reg_vals = [c.value.upper() for c in constraints if c.constraint_type == DirectiveConstraintType.REGISTRY]
        if not reg_vals:
            return None
        target = reg_vals[0]
        template = self.REGISTRY_TEMPLATES.get(target, f"{target} records registration")
        parts = [f'"{title.strip()}"']
        if artist and artist.strip():
            parts.append(f'"{artist.strip()}"')
        parts.append(template)
        return " ".join(parts).strip()

    def _build_probe(self, title: str, artist: Optional[str], addon: str) -> str:
        """Constructs adversarial probe query to verify disputes or assignments."""
        parts = [f'"{title.strip()}"']
        if artist and artist.strip():
            parts.append(f'"{artist.strip()}"')
        if addon:
            parts.append(addon)
        parts.append('dispute OR infringement OR assignment OR "competing claim"')
        return " ".join(parts).strip()

    def reformulate_queries(
        self, request: DirectedSearchRequest, sanitized: Optional[SanitizedDirective] = None
    ) -> List[str]:
        """Synthesizes prioritized list of reformulated search queries."""
        sd = sanitized or request.sanitized_directive or DirectiveSanitizer().sanitize(request.raw_directive)
        addon = sd.sanitized_query_addon or sd.clean_directive
        queries: List[str] = [self._build_primary(request.title, request.artist_or_author, addon)]

        reg_query = self._build_registry_targeted(
            request.title, request.artist_or_author, sd.extracted_constraints, addon
        )
        if reg_query and reg_query not in queries:
            queries.append(reg_query)

        probe_query = self._build_probe(request.title, request.artist_or_author, addon)
        if probe_query not in queries:
            queries.append(probe_query)

        return [q for q in queries if q]


class DirectedResearchCoordinator:
    """Coordinates directive sanitization, query reformulation, and search execution."""

    def __init__(
        self,
        search_service: Optional[ParallelSearchService] = None,
        default_timeout: float = 15.0,
    ) -> None:
        self.search_service = search_service or ParallelSearchService(use_fallback=True)
        self.default_timeout = min(default_timeout, 15.0)
        self.sanitizer = DirectiveSanitizer()
        self.reformulator = DirectedQueryReformulator()

    async def _execute_single_search(
        self, query: str, request: DirectedSearchRequest
    ) -> PublicEvidenceSnapshot:
        """Executes a single search query against ParallelSearchService."""
        eff_use_id = request.claim_id or f"directed_{request.asset_id or 'claim'}"
        clean_title = request.title.strip().lower().replace(" ", "_")
        eff_lineage_key = request.stable_lineage_key or f"lineage_{clean_title}"

        return await self.search_service.search(
            query=query,
            use_id=eff_use_id,
            stable_lineage_key=eff_lineage_key,
            asset_id=request.asset_id or eff_use_id,
            artist_or_author=request.artist_or_author,
            title=request.title,
            year=request.year,
            use_cache=request.use_cache,
        )

    async def _gather_queries(
        self, queries: List[str], request: DirectedSearchRequest
    ) -> List[PublicEvidenceSnapshot]:
        """Executes reformulated queries concurrently and aggregates evidence snapshots."""
        tasks = [self._execute_single_search(q, request) for q in queries[:2]]
        return await asyncio.gather(*tasks)

    def _create_result(
        self,
        request: DirectedSearchRequest,
        sanitized: SanitizedDirective,
        queries: List[str],
        primary: str,
        snapshots: List[PublicEvidenceSnapshot],
        elapsed: float,
        status: DirectedSearchStatus,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DirectedSearchResult:
        """Helper to construct standardized DirectedSearchResult."""
        return DirectedSearchResult(
            title=request.title,
            raw_directive=request.raw_directive,
            clean_directive=sanitized.clean_directive,
            reformulated_queries=queries,
            primary_query=primary,
            snapshots=snapshots,
            constraints_applied=sanitized.extracted_constraints,
            execution_time_seconds=elapsed,
            status=status.value,
            error_message=error_message,
            metadata=metadata or {},
        )

    async def execute_directed_search(
        self, request: DirectedSearchRequest
    ) -> DirectedSearchResult:
        """Executes directed research run under strict hard execution timeout (15.0s max)."""
        start = time.perf_counter()
        timeout = min(request.timeout_seconds, 15.0)
        sanitized = request.sanitized_directive or self.sanitizer.sanitize(request.raw_directive)
        queries = self.reformulator.reformulate_queries(request, sanitized=sanitized)
        primary = queries[0] if queries else f'"{request.title}"'

        try:
            snapshots = await asyncio.wait_for(self._gather_queries(queries, request), timeout=timeout)
            elapsed = round(time.perf_counter() - start, 3)
            meta = {"query_count": len(queries), "hard_timeout_applied": timeout}
            return self._create_result(request, sanitized, queries, primary, list(snapshots), elapsed, DirectedSearchStatus.SUCCESS, metadata=meta)
        except asyncio.TimeoutError:
            elapsed = round(time.perf_counter() - start, 3)
            msg = f"Directed search timed out after {timeout:.1f}s execution limit."
            return self._create_result(request, sanitized, queries, primary, [], elapsed, DirectedSearchStatus.TIMEOUT, error_message=msg, metadata={"timeout_seconds": timeout})
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 3)
            return self._create_result(request, sanitized, queries, primary, [], elapsed, DirectedSearchStatus.ERROR, error_message=str(exc))
