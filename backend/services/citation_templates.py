"""
backend/services/citation_templates.py

Attorney citation suggestion engine and pre-formatted legal citation templates.
Sprint 4.3 - Autonomous clearance decision acceleration.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CitationCategory(str, Enum):
    """Categorical classification of vetted legal clearance citations."""
    FAIR_USE_107 = "FAIR_USE_107"
    PUBLIC_DOMAIN_304 = "PUBLIC_DOMAIN_304"
    RINGGOLD_DE_MINIMIS = "RINGGOLD_DE_MINIMIS"
    SYNC_WARRANTY = "SYNC_WARRANTY"
    MASTER_WARRANTY = "MASTER_WARRANTY"
    TRADEMARK_NOMINATIVE = "TRADEMARK_NOMINATIVE"


class LegalCitationTemplate(BaseModel):
    """Pre-formatted, legally vetted statutory or contractual citation template."""
    model_config = ConfigDict(frozen=True)

    citation_id: str = Field(..., description="Canonical template identifier")
    category: CitationCategory = Field(..., description="Citation classification category")
    title: str = Field(..., description="Human-readable citation title")
    statute_or_case: str = Field(..., description="Statutory section or case law authority")
    template_text: str = Field(..., description="Vetted legal citation text with placeholders")
    applicable_claim_categories: List[str] = Field(
        default_factory=list, description="Claim categories where this citation applies"
    )
    confidence_weight: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Relevance and confidence weighting for ranking"
    )
    template_id: Optional[str] = Field(default=None, description="Legacy API template ID")

    def substitute(self, variables: Dict[str, Any]) -> LegalCitationTemplate:
        """Substitute [VARIABLE] or {variable} placeholders with concrete values."""
        text = self.template_text
        for key, val in variables.items():
            for ph in (f"[{key.upper()}]", f"[{key}]", f"{{{key}}}", f"{{{key.upper()}}}"):
                text = text.replace(ph, str(val))
        return self.model_copy(update={"template_text": text})

    def format_citation(self, **kwargs: Any) -> str:
        """Convenience method to return formatted text using keyword arguments."""
        return self.substitute(kwargs).template_text


_RAW_TEMPLATES = [
    (
        "cit_fair_use_107", "tmpl_fair_use_incidental", CitationCategory.FAIR_USE_107,
        "17 U.S.C. § 107 Fair Use", "17 U.S.C. § 107",
        "Use is transformative under 17 U.S.C. § 107; secondary work serves documentary purpose with minimal qualitative excerpt and zero market substitution.",
        ["artwork", "footage", "music", "brand", "historical_figure", "real_person", "synthetic_ai", "other"], 0.75,
    ),
    (
        "cit_public_domain_304", "tmpl_public_domain_pre1928", CitationCategory.PUBLIC_DOMAIN_304,
        "17 U.S.C. § 304 Public Domain", "17 U.S.C. § 304",
        "Work published prior to 1931; copyright protection expired pursuant to 17 U.S.C. § 304 and is in the public domain in the United States.",
        ["artwork", "music", "footage", "historical_figure", "other"], 0.80,
    ),
    (
        "cit_ringgold_de_minimis", "tmpl_ringgold_de_minimis", CitationCategory.RINGGOLD_DE_MINIMIS,
        "Ringgold De Minimis", "Ringgold v. Black Entertainment Television (126 F.3d 70)",
        "Visual display qualifies as de minimis non-infringing use under Ringgold v. Black Entertainment Television (126 F.3d 70); duration < 3 seconds, out of focus and fleeting.",
        ["artwork", "brand", "footage", "other"], 0.85,
    ),
    (
        "cit_sync_warranty", "tmpl_sync_standard_warranty", CitationCategory.SYNC_WARRANTY,
        "Synchronized Music Warranty", "Executed Synchronization License Agreement",
        "Clearance satisfied pursuant to Executed Synchronization License dated [DATE] by and between [LICENSOR] and [LICENSEE] for worldwide perpetual exploitation in all media.",
        ["music"], 0.90,
    ),
    (
        "cit_master_warranty", "tmpl_master_use_warranty", CitationCategory.MASTER_WARRANTY,
        "Master Use License Warranty", "Master Use Agreement",
        "Master recording clearance satisfied pursuant to Master Use Agreement dated [DATE] from [LABEL] for worldwide perpetual synchronization.",
        ["music"], 0.90,
    ),
    (
        "cit_trademark_nominative", "tmpl_trademark_nominative", CitationCategory.TRADEMARK_NOMINATIVE,
        "Trademark Nominative Fair Use", "New Kids on the Block v. News America (971 F.2d 302)",
        "Incidental background appearance qualifies as nominative fair use under New Kids on the Block v. News America (971 F.2d 302); mark is used solely to identify the product without implying endorsement or affiliation.",
        ["brand", "trademark", "other"], 0.90,
    ),
]

_DEFAULT_TEMPLATES: List[LegalCitationTemplate] = [
    LegalCitationTemplate(
        citation_id=r[0], template_id=r[1], category=r[2], title=r[3],
        statute_or_case=r[4], template_text=r[5], applicable_claim_categories=r[6], confidence_weight=r[7],
    )
    for r in _RAW_TEMPLATES
]

_CATEGORY_KEYWORDS: Dict[CitationCategory, List[str]] = {
    CitationCategory.FAIR_USE_107: ["transformative", "fair use", "documentary", "parody", "commentary", "excerpt"],
    CitationCategory.PUBLIC_DOMAIN_304: ["public domain", "1931", "pre-1931", "expired", "304", "archival", "historical"],
    CitationCategory.RINGGOLD_DE_MINIMIS: ["de minimis", "ringgold", "fleeting", "out of focus", "seconds", "blur"],
    CitationCategory.SYNC_WARRANTY: ["synchronization", "sync", "sync license", "licensor", "licensee", "publisher"],
    CitationCategory.MASTER_WARRANTY: ["master", "sound recording", "label", "master use", "record label"],
    CitationCategory.TRADEMARK_NOMINATIVE: ["nominative", "trademark", "brand", "new kids", "endorsement", "logo"],
}


class CitationSuggestionEngine:
    """Intelligent citation suggestion and ranking engine for attorney clearance review."""

    def __init__(self, templates: Optional[List[LegalCitationTemplate]] = None) -> None:
        self._templates = list(templates) if templates is not None else list(_DEFAULT_TEMPLATES)

    def get_templates(self) -> List[LegalCitationTemplate]:
        """Return all registered citation templates."""
        return list(self._templates)

    def get_template(self, category_or_id: str | CitationCategory) -> Optional[LegalCitationTemplate]:
        """Retrieve a specific template by category enum or citation ID."""
        cat_val = category_or_id.value if isinstance(category_or_id, CitationCategory) else str(category_or_id)
        return next(
            (t for t in self._templates if cat_val in (t.citation_id, t.category.value, t.template_id)), None
        )

    def substitute_template(
        self, template: LegalCitationTemplate, variables: Dict[str, Any]
    ) -> LegalCitationTemplate:
        """Substitute variable mappings into the provided template."""
        return template.substitute(variables)

    def _normalize_claim_type(self, claim_type: str) -> str:
        """Map heterogeneous claim type strings to standard taxonomy keys."""
        c = str(claim_type).strip().lower()
        mapping = {
            "music": "music", "soundtrack": "music", "song": "music", "audio": "music",
            "brand": "brand", "trademark": "brand", "logo": "brand", "product": "brand",
            "artwork": "artwork", "art": "artwork", "painting": "artwork", "poster": "artwork",
            "footage": "footage", "clip": "footage", "video": "footage", "film": "footage",
            "historical_figure": "historical_figure", "real_person": "real_person", "synthetic_ai": "synthetic_ai",
        }
        return mapping.get(c, "other")

    def _parse_evidence(self, findings: Optional[List[Any]]) -> tuple[str, Dict[str, str]]:
        """Flatten findings into a lowercase search string and extracted variable dict."""
        if not findings:
            return "", {}
        texts, variables = [], {}
        for item in findings:
            src = item if isinstance(item, dict) else (getattr(item, "__dict__", None) or {})
            if isinstance(src, dict) and src:
                for k, v in src.items():
                    variables[str(k)] = str(v)
                    texts.append(f"{k} {v}")
            else:
                texts.append(str(item))
        return " ".join(texts).lower(), variables

    def _compute_confidence(
        self, template: LegalCitationTemplate, claim_key: str, evidence_text: str, jurisdiction: str
    ) -> float:
        """Calculate dynamic relevance confidence score based on claim, evidence, and jurisdiction."""
        is_direct = claim_key in template.applicable_claim_categories
        score = template.confidence_weight if is_direct else (template.confidence_weight * 0.70)
        keywords = _CATEGORY_KEYWORDS.get(template.category, [])
        score += min(0.15, sum(1 for kw in keywords if kw in evidence_text) * 0.04)

        if jurisdiction.upper() != "US" and template.category not in (
            CitationCategory.SYNC_WARRANTY, CitationCategory.MASTER_WARRANTY
        ):
            score *= 0.35

        return max(0.05, min(1.0, round(score, 2)))

    def _build_schema_response(self, claim_id: str, right_category: Optional[str]) -> Any:
        """Helper to build API schema response for decisions router."""
        from backend.api.routes.decision_schemas import (
            CitationSuggestionResponse, LegalCitationTemplate as ApiTmpl,
        )
        norm = (right_category or "").strip().lower()
        exact = [t for t in self._templates if norm and norm in t.applicable_claim_categories]
        rest = [t for t in self._templates if not norm or norm not in t.applicable_claim_categories]
        ordered = exact + rest if exact else list(self._templates)
        api_list = [
            ApiTmpl(
                template_id=t.template_id or t.citation_id,
                citation_type="statutory" if "107" in t.citation_id or "304" in t.citation_id else "contractual",
                title=t.title,
                statutory_reference=t.statute_or_case,
                citation_text=t.template_text,
                applicable_right=t.applicable_claim_categories[0] if t.applicable_claim_categories else None,
                conditions=[],
            )
            for t in ordered
        ]
        return CitationSuggestionResponse(claim_id=claim_id, suggestions=api_list)

    def suggest_citations(
        self,
        claim_type: Optional[str] = None,
        evidence_findings: Optional[List[Any]] = None,
        jurisdiction: str = "US",
        *,
        claim_id: Optional[str] = None,
        right_category: Optional[str] = None,
    ) -> Any:
        """Suggest, populate, and rank legal citation templates for a given claim."""
        if claim_id is not None:
            return self._build_schema_response(claim_id, right_category or claim_type)

        claim_key = self._normalize_claim_type(claim_type or "other")
        evidence_text, variables = self._parse_evidence(evidence_findings)
        suggested: List[LegalCitationTemplate] = []

        for tmpl in self._templates:
            if claim_key not in tmpl.applicable_claim_categories and "other" not in tmpl.applicable_claim_categories:
                continue
            conf = self._compute_confidence(tmpl, claim_key, evidence_text, jurisdiction)
            populated = tmpl.substitute(variables) if variables else tmpl
            suggested.append(populated.model_copy(update={"confidence_weight": conf}))

        return sorted(suggested, key=lambda t: t.confidence_weight, reverse=True)


_default_engine: Optional[CitationSuggestionEngine] = None


def get_citation_engine() -> CitationSuggestionEngine:
    """Dependency provider returning singleton CitationSuggestionEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = CitationSuggestionEngine()
    return _default_engine
