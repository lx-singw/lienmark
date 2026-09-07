"""
backend/agents/research/subgoal_media_builders.py

Subgoal decomposition builders for timecode media assets (music and archival footage).
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from typing import List

from backend.agents.intake.claim_types import ExtractedClaim
from backend.agents.research.subgoal_rules import (
    FOOTAGE_REGISTRIES,
    MUSIC_REGISTRIES,
    SAMPLE_TRIGGER_KEYWORDS,
)
from backend.agents.research.subgoal_types import (
    InvestigationSubgoal,
    SubgoalPriority,
    SubgoalTemplate,
    SubgoalType,
)

MUSIC_TEMPLATES: List[SubgoalTemplate] = [
    SubgoalTemplate(
        suffix="comp",
        subgoal_type=SubgoalType.MUSIC_COMPOSITION_PUBLISHING,
        title="Composition & Publishing Rights",
        description_template="Identify ISWC, songwriter/composer publishing, and PRO share for '{desc}'.",
        required_identifiers=["ISWC", "ASCAP_BMI_WORK_ID"],
        target_registries=MUSIC_REGISTRIES["publishing"],
        suggested_query_terms=["ISWC", "publishing", "writer", "composer", "ASCAP", "BMI"],
    ),
    SubgoalTemplate(
        suffix="master",
        subgoal_type=SubgoalType.MUSIC_MASTER_RECORDING,
        title="Master Recording Rights",
        description_template="Identify ISRC, record label, and featured performer ownership for '{desc}'.",
        required_identifiers=["ISRC"],
        target_registries=MUSIC_REGISTRIES["master"],
        suggested_query_terms=["ISRC", "master rights", "record label", "performer"],
    ),
    SubgoalTemplate(
        suffix="sync",
        subgoal_type=SubgoalType.MUSIC_SYNC_SCOPE,
        title="Intended Media Synchronization Scope",
        description_template="Verify synchronization clearance scope (territory, term, media formats) for scene '{scene}'.",
        required_identifiers=["SYNC_LICENSE_SCOPE"],
        target_registries=MUSIC_REGISTRIES["sync"],
        suggested_query_terms=["sync license", "synchronization rights", "media territory"],
        priority=SubgoalPriority.HIGH,
    ),
]

SAMPLE_TEMPLATE = SubgoalTemplate(
    suffix="sample",
    subgoal_type=SubgoalType.MUSIC_SAMPLE_INTERPOLATION,
    title="Sample & Interpolation Clearances",
    description_template="Verify derivative cue, sample, and interpolation clearances for '{desc}'.",
    required_identifiers=["UNDERLYING_SAMPLE_RIGHTS"],
    target_registries=MUSIC_REGISTRIES["publishing"] + MUSIC_REGISTRIES["master"],
    suggested_query_terms=["sample clearance", "interpolation", "derivative work"],
    is_conditional=True,
    condition_trigger="Derivative cue, remix, or sample terminology detected in claim.",
)

FOOTAGE_TEMPLATES: List[SubgoalTemplate] = [
    SubgoalTemplate(
        suffix="fed_pd",
        subgoal_type=SubgoalType.FOOTAGE_PUBLIC_DOMAIN_FEDERAL,
        title="Public Domain Federal Creation",
        description_template="Verify U.S. Federal Government creation and 17 U.S.C. § 105 public domain status for '{desc}'.",
        required_identifiers=["NASA_NARA_ID", "PUBLIC_DOMAIN_NOTICE"],
        target_registries=FOOTAGE_REGISTRIES["federal"],
        suggested_query_terms=["NASA", "National Archives", "public domain", "federal work"],
    ),
    SubgoalTemplate(
        suffix="broadcast",
        subgoal_type=SubgoalType.FOOTAGE_BROADCASTER_MASTER,
        title="Private Broadcaster / Master Broadcast Rights",
        description_template="Clear private network master broadcast, commentary audio, and overlays for '{desc}'.",
        required_identifiers=["BROADCAST_ARCHIVE_ID"],
        target_registries=FOOTAGE_REGISTRIES["broadcaster"],
        suggested_query_terms=["broadcast rights", "network archive", "master footage", "commentary"],
        priority=SubgoalPriority.HIGH,
    ),
]


def has_sample_or_remix_cues(claim: ExtractedClaim) -> bool:
    """Detects whether an extracted claim indicates samples, interpolations, or remixes."""
    text_corpus = " ".join(
        filter(
            None,
            [
                claim.extracted_description,
                claim.context_snippet or "",
                claim.flagged_reason or "",
            ],
        )
    ).lower()
    return any(cue in text_corpus for cue in SAMPLE_TRIGGER_KEYWORDS)


def instantiate_media_subgoal(
    template: SubgoalTemplate, claim: ExtractedClaim
) -> InvestigationSubgoal:
    """Instantiates an InvestigationSubgoal from a template and claim context."""
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


def build_music_subgoals(claim: ExtractedClaim) -> List[InvestigationSubgoal]:
    """Decomposes music claim into publishing, master, sync, and conditional sample subgoals."""
    subgoals = [instantiate_media_subgoal(tmpl, claim) for tmpl in MUSIC_TEMPLATES]
    if has_sample_or_remix_cues(claim):
        subgoals.append(instantiate_media_subgoal(SAMPLE_TEMPLATE, claim))
    return subgoals


def build_footage_subgoals(claim: ExtractedClaim) -> List[InvestigationSubgoal]:
    """Decomposes archival footage claim into public domain federal vs private broadcaster rights."""
    return [instantiate_media_subgoal(tmpl, claim) for tmpl in FOOTAGE_TEMPLATES]
