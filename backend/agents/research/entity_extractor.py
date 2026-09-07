"""
backend/agents/research/entity_extractor.py

Deterministic snippet entity extraction and actionable IP lead discovery.
Sprint 3.2: Snippet Entity & Lead Extractor Specialist.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional

from backend.agents.research.entity_patterns import (
    build_query_extension,
    extract_regex_matches,
    split_into_sentences,
)
from backend.agents.research.lead_types import (
    ExtractedLead,
    LeadEntityType,
    LeadRelationshipType,
)
from backend.services.parallel_types import ParallelSearchFinding

logger = logging.getLogger("lienmark.research.entity_extractor")

__all__ = ["EntityExtractor", "ExtractedLead", "LeadEntityType", "LeadRelationshipType"]


class EntityExtractor:
    """Extracts actionable legal entities and licensing leads from search findings."""

    def __init__(self, use_llm_fallback: bool = False, llm_service: Optional[Any] = None) -> None:
        self.use_llm_fallback = use_llm_fallback
        self.llm_service = llm_service

    @staticmethod
    def compute_lead_id(parent_finding_id: str, entity_name: str, relationship: LeadRelationshipType) -> str:
        """Computes deterministic 16-hex digest for lead deduplication."""
        payload = f"{parent_finding_id}:{entity_name.lower().strip()}:{relationship.value}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def extract_leads_from_sentence(self, sentence: str, parent_finding_id: str = "") -> List[ExtractedLead]:
        """Extracts candidate leads from a single attributable sentence."""
        raw_matches = extract_regex_matches(sentence)
        leads: List[ExtractedLead] = []
        for match in raw_matches:
            lead_id = self.compute_lead_id(parent_finding_id, match.entity_name, match.relationship_type)
            query_ext = build_query_extension(match.entity_name, match.entity_type)
            leads.append(
                ExtractedLead(
                    lead_id=lead_id,
                    parent_finding_id=parent_finding_id,
                    entity_name=match.entity_name,
                    entity_type=match.entity_type,
                    relationship_type=match.relationship_type,
                    confidence_score=match.confidence_score,
                    source_sentence=match.source_sentence,
                    proposed_query_extension=query_ext,
                    metadata={"source": "regex_catalog_fastpath"},
                )
            )
        return leads

    def extract_leads_from_text(self, text: str, parent_finding_id: str = "") -> List[ExtractedLead]:
        """Splits text into sentences and extracts deduplicated leads."""
        if not text:
            return []
        sentences = split_into_sentences(text)
        all_leads: List[ExtractedLead] = []
        for sentence in sentences:
            sentence_leads = self.extract_leads_from_sentence(sentence, parent_finding_id=parent_finding_id)
            all_leads.extend(sentence_leads)
        return self._deduplicate_leads(all_leads)

    def extract_leads_from_findings(self, findings: List[ParallelSearchFinding]) -> List[ExtractedLead]:
        """Extracts actionable IP leads across all findings with zero latency."""
        all_leads: List[ExtractedLead] = []
        for finding in findings:
            finding_id = (
                getattr(finding, "finding_id", None)
                or hashlib.sha256(finding.url.encode("utf-8")).hexdigest()[:16]
            )
            text_blocks: List[str] = []
            if finding.full_excerpt:
                text_blocks.append(finding.full_excerpt)
            for exc in finding.excerpts:
                if exc not in text_blocks:
                    text_blocks.append(exc)
            if finding.title and finding.title not in text_blocks:
                text_blocks.append(finding.title)

            combined_text = " ".join(text_blocks)
            finding_leads = self.extract_leads_from_text(combined_text, parent_finding_id=finding_id)
            all_leads.extend(finding_leads)

        return self._deduplicate_leads(all_leads)

    async def aextract_leads_from_text(self, text: str, parent_finding_id: str = "") -> List[ExtractedLead]:
        """Asynchronously extracts leads using fast regex first, with LLM fallback if empty."""
        regex_leads = self.extract_leads_from_text(text, parent_finding_id=parent_finding_id)
        if regex_leads or not self.use_llm_fallback or not self.llm_service:
            return regex_leads
        llm_leads = await self._extract_leads_via_llm(text, parent_finding_id)
        return self._deduplicate_leads(llm_leads)

    async def aextract_leads_from_findings(self, findings: List[ParallelSearchFinding]) -> List[ExtractedLead]:
        """Asynchronously extracts leads across findings with regex fast-path and LLM fallback."""
        regex_leads = self.extract_leads_from_findings(findings)
        if regex_leads or not self.use_llm_fallback or not self.llm_service:
            return regex_leads
        blocks = [f.full_excerpt or " ".join(f.excerpts) for f in findings if f.full_excerpt or f.excerpts]
        combined_text = " ".join(blocks)
        parent_id = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()[:16]
        llm_leads = await self._extract_leads_via_llm(combined_text, parent_id)
        return self._deduplicate_leads(llm_leads)

    def _deduplicate_leads(self, leads: List[ExtractedLead]) -> List[ExtractedLead]:
        """Consolidates duplicate entities, keeping the highest confidence entry."""
        best_by_key: Dict[str, ExtractedLead] = {}
        for lead in leads:
            dedup_key = f"{lead.entity_name.lower()}::{lead.relationship_type.value}"
            existing = best_by_key.get(dedup_key)
            if not existing or lead.confidence_score > existing.confidence_score:
                best_by_key[dedup_key] = lead
        return sorted(best_by_key.values(), key=lambda l: l.confidence_score, reverse=True)

    async def _extract_leads_via_llm(self, text: str, parent_finding_id: str) -> List[ExtractedLead]:
        """Invokes LLM extraction fallback when regex heuristic returns zero leads."""
        prompt = (
            f"Extract all music publishers, record labels, corporate parents, estates, and "
            f"trademark assignees from this snippet as JSON list: {text}"
        )
        try:
            if hasattr(self.llm_service, "generate_json"):
                raw_items = await self.llm_service.generate_json(prompt)
            elif callable(self.llm_service):
                raw_items = await self.llm_service(prompt)
            else:
                return []
            return self._parse_llm_items(raw_items, parent_finding_id)
        except Exception as err:
            logger.warning("LLM lead extraction fallback failed: %s", err)
            return []

    def _parse_llm_items(self, raw_items: Any, parent_finding_id: str) -> List[ExtractedLead]:
        """Parses and validates raw LLM output into ExtractedLead instances."""
        if not isinstance(raw_items, list):
            return []
        parsed: List[ExtractedLead] = []
        for item in raw_items:
            if not isinstance(item, dict) or not item.get("entity_name"):
                continue
            name = str(item["entity_name"]).strip()
            e_type = LeadEntityType(item.get("entity_type", "publisher"))
            r_type = LeadRelationshipType(item.get("relationship_type", "published_by"))
            conf = float(item.get("confidence_score", 0.75))
            sentence = str(item.get("source_sentence", ""))
            lead_id = self.compute_lead_id(parent_finding_id, name, r_type)
            parsed.append(
                ExtractedLead(
                    lead_id=lead_id,
                    parent_finding_id=parent_finding_id,
                    entity_name=name,
                    entity_type=e_type,
                    relationship_type=r_type,
                    confidence_score=min(max(conf, 0.0), 1.0),
                    source_sentence=sentence,
                    proposed_query_extension=build_query_extension(name, e_type),
                    metadata={"source": "llm_fallback"},
                )
            )
        return parsed
