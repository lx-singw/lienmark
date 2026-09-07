"""
backend/agents/research/subgoal_builders.py

Unified barrel facade exporting all domain-specific clearance subgoal builders.
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from backend.agents.research.subgoal_media_builders import (
    FOOTAGE_TEMPLATES,
    MUSIC_TEMPLATES,
    SAMPLE_TEMPLATE,
    build_footage_subgoals,
    build_music_subgoals,
    has_sample_or_remix_cues,
    instantiate_media_subgoal,
)
from backend.agents.research.subgoal_visual_builders import (
    ARTWORK_TEMPLATES,
    BRAND_TEMPLATES,
    GENERIC_TEMPLATES,
    build_artwork_subgoals,
    build_brand_subgoals,
    build_generic_subgoals,
    instantiate_visual_subgoal,
)

__all__ = [
    "ARTWORK_TEMPLATES",
    "BRAND_TEMPLATES",
    "FOOTAGE_TEMPLATES",
    "GENERIC_TEMPLATES",
    "MUSIC_TEMPLATES",
    "SAMPLE_TEMPLATE",
    "build_artwork_subgoals",
    "build_brand_subgoals",
    "build_footage_subgoals",
    "build_generic_subgoals",
    "build_music_subgoals",
    "has_sample_or_remix_cues",
    "instantiate_media_subgoal",
    "instantiate_visual_subgoal",
]
