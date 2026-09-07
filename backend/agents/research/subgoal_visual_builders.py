"""
backend/agents/research/subgoal_visual_builders.py

Subgoal decomposition builders for visual assets (trademark, artwork, likeness, generic).
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from typing import List

from backend.agents.intake.claim_types import ExtractedClaim
from backend.agents.research.subgoal_rules import (
    ARTWORK_REGISTRIES,
    BRAND_REGISTRIES,
)
from backend.agents.research.subgoal_types import (
    InvestigationSubgoal,
    SubgoalPriority,
    SubgoalTemplate,
    SubgoalType,
)

BRAND_TEMPLATES: List[SubgoalTemplate] = [
    SubgoalTemplate(
        suffix="wordmark",
        subgoal_type=SubgoalType.BRAND_WORD_MARK,
        title="Word Mark Registration",
        description_template="Verify word mark status, active registration, and owner for '{desc}'.",
        required_identifiers=["USPTO_REG_NO", "USPTO_SERIAL_NO"],
        target_registries=BRAND_REGISTRIES["word_mark"],
        suggested_query_terms=["trademark", "registration", "serial number", "owner"],
    ),
    SubgoalTemplate(
        suffix="logo",
        subgoal_type=SubgoalType.BRAND_LOGO_STYLIZED,
        title="Logo & Stylized Mark Protection",
        description_template="Investigate stylized logo, trade dress, and visual mark registration for '{desc}'.",
        required_identifiers=["DESIGN_SEARCH_CODE"],
        target_registries=BRAND_REGISTRIES["logo_stylized"],
        suggested_query_terms=["logo", "stylized mark", "design code", "trade dress"],
        priority=SubgoalPriority.HIGH,
    ),
    SubgoalTemplate(
        suffix="classes",
        subgoal_type=SubgoalType.BRAND_GOODS_SERVICES,
        title="Goods & Services Classification",
        description_template="Map Nice classification classes (e.g. Class 32, 33, 25) for '{desc}'.",
        required_identifiers=["NICE_CLASS"],
        target_registries=BRAND_REGISTRIES["goods_services"],
        suggested_query_terms=["Nice classification", "International Class", "goods and services"],
        priority=SubgoalPriority.HIGH,
    ),
]

ARTWORK_TEMPLATES: List[SubgoalTemplate] = [
    SubgoalTemplate(
        suffix="orig_art",
        subgoal_type=SubgoalType.ARTWORK_ORIGINAL_COPYRIGHT,
        title="Original Illustration Copyright",
        description_template="Verify underlying visual art copyright and artist authorship for '{desc}'.",
        required_identifiers=["COPYRIGHT_REG_NO"],
        target_registries=ARTWORK_REGISTRIES["original"],
        suggested_query_terms=["copyright registration", "artist", "authorship", "VARA"],
    ),
    SubgoalTemplate(
        suffix="periodical",
        subgoal_type=SubgoalType.ARTWORK_PERIODICAL_PUBLICATION,
        title="Publication & Periodical Rights",
        description_template="Clear publication rights, magazine issue copyright, or periodical contribution for '{desc}'.",
        required_identifiers=["PERIODICAL_ISSUE_ID"],
        target_registries=ARTWORK_REGISTRIES["periodical"],
        suggested_query_terms=["magazine", "periodical", "issue copyright", "publication date"],
        priority=SubgoalPriority.HIGH,
    ),
    SubgoalTemplate(
        suffix="renewal",
        subgoal_type=SubgoalType.ARTWORK_RENEWAL_STATUS,
        title="Renewal Status & Copyright Act Regime",
        description_template="Determine Copyright Act regime (1909 vs 1976 Act) and 28-year renewal status for '{desc}'.",
        required_identifiers=["RENEWAL_REG_NO"],
        target_registries=ARTWORK_REGISTRIES["renewal"],
        suggested_query_terms=["copyright renewal", "1909 Act", "28-year renewal", "public domain status"],
    ),
]

GENERIC_TEMPLATES: List[SubgoalTemplate] = [
    SubgoalTemplate(
        suffix="prop_title",
        subgoal_type=SubgoalType.GENERAL_TITLE_OWNERSHIP,
        title="Proprietary Rights & Title Ownership",
        description_template="Investigate core title ownership and primary rights for '{desc}'.",
        required_identifiers=["PRIMARY_RIGHTSHOLDER"],
        target_registries=["site:cocatalog.loc.gov", "site:wipo.int"],
        suggested_query_terms=["owner", "clearance", "license", "rights"],
    ),
    SubgoalTemplate(
        suffix="third_party",
        subgoal_type=SubgoalType.GENERAL_THIRD_PARTY_RIGHTS,
        title="Third-Party Encumbrances & Permissions",
        description_template="Verify secondary encumbrances, likeness consent, or contractual limits for '{desc}'.",
        required_identifiers=["THIRD_PARTY_CONSENT"],
        target_registries=[],
        suggested_query_terms=["consent", "release", "encumbrance"],
        priority=SubgoalPriority.HIGH,
    ),
]


def instantiate_visual_subgoal(
    template: SubgoalTemplate, claim: ExtractedClaim
) -> InvestigationSubgoal:
    """Instantiates an InvestigationSubgoal from a visual template and claim context."""
    desc = template.description_template.format(
        desc=claim.extracted_description,
        scene=claim.scene_or_timecode,
    )
    return InvestigationSubgoal(
        subgoal_id=f"sub_{claim.claim_id}_{template.suffix}",
        claim_id=claim.claim_id,
        category=claim.category,
        subgoal_type=template.subgoal_type,
        title=template.title,
        description=desc,
        required_identifiers=list(template.required_identifiers),
        target_registries=list(template.target_registries),
        suggested_query_terms=list(template.suggested_query_terms),
        priority=template.priority,
        is_conditional=template.is_conditional,
        condition_trigger=template.condition_trigger,
    )


def build_brand_subgoals(claim: ExtractedClaim) -> List[InvestigationSubgoal]:
    """Decomposes trademark/brand claim into word mark, stylized logo, and goods/services subgoals."""
    return [instantiate_visual_subgoal(tmpl, claim) for tmpl in BRAND_TEMPLATES]


def build_artwork_subgoals(claim: ExtractedClaim) -> List[InvestigationSubgoal]:
    """Decomposes artwork claim into original illustration copyright, periodical rights, and renewal."""
    return [instantiate_visual_subgoal(tmpl, claim) for tmpl in ARTWORK_TEMPLATES]


def build_generic_subgoals(claim: ExtractedClaim) -> List[InvestigationSubgoal]:
    """Fallback decomposition for likeness, synthetic AI, or other IP claims."""
    return [instantiate_visual_subgoal(tmpl, claim) for tmpl in GENERIC_TEMPLATES]
