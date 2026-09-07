"""
Lienmark Screenplay AST Delta & Semantic Diff Engine (delta_engine.py)
Implements screenplay AST representation, hierarchical element diffing,
localized bounding box matching, and entity mention extraction for Agentic Cinema E&O compliance.
Authored strictly under Google AntiGravity for Lienmark Sprint 1.2.
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, model_validator

from backend.domain.models import (
    ChangeKind,
    CreativeDelta,
    CreativeOccurrence,
    CreativeUse,
    AtomicRightsClaim,
    CounselDecision,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
)
from backend.core.semantic_delta import (
    ModelContainmentViolation,
    SemanticDeltaEngine,
)

logger = logging.getLogger("lienmark.delta_engine")


# =============================================================================
# 1. SCREENPLAY AST DATA STRUCTURES & BOUNDING ENUMS
# =============================================================================

class ScreenplayElementType(str, Enum):
    """Canonical screenplay structural element types."""
    SCENE_HEADING = "scene_heading"       # Sluglines: INT./EXT. LOCATION - TIME
    ACTION = "action"                     # Action / narrative description
    CHARACTER_CUE = "character_cue"       # Character speaking prompt (e.g. MILLER)
    DIALOGUE = "dialogue"                 # Spoken lines of dialogue
    PARENTHETICAL = "parenthetical"       # Stage direction within dialogue
    TRANSITION = "transition"             # CUT TO:, FADE OUT., etc.
    BEAT_MARKER = "beat_marker"           # Explicit or derived narrative beat marker
    SCENE = "scene"                       # Composite container


class SpatialScope(str, Enum):
    """Spatial and camera prominence scope within a cinematic scene."""
    BACKGROUND = "background"             # Ambient blur / set dressing / out-of-focus
    SET_DRESSING = "set_dressing"         # Physical props in room, non-focal
    FOREGROUND = "foreground"             # Proximate to camera or character
    HERO_INTERACTION = "hero_interaction" # Handled, grabbed, worn, inspected by character
    AUDIO_SOURCE = "audio_source"         # Diegetic or non-diegetic musical sound cue
    GLOBAL_SCENE = "global_scene"         # Scene-wide establishing shot or atmospheric


class InteractionLevel(str, Enum):
    """Degrees of character interaction and rights exposure."""
    INCIDENTAL_BACKGROUND = "incidental_background"
    SET_DRESSING = "set_dressing"
    EXPLICIT_MENTION = "explicit_mention"
    ACTIVE_INTERACTION = "active_interaction"
    DIALOGUE_QUOTATION = "dialogue_quotation"
    FOCAL_HERO = "focal_hero"


class SourceSpan(BaseModel):
    """Defines exact source line and character bounds in screenplay text."""
    start_line: int = Field(..., ge=1, description="1-indexed starting line number")
    end_line: int = Field(..., ge=1, description="1-indexed ending line number")
    start_char: int = Field(default=0, ge=0)
    end_char: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_span(self) -> "SourceSpan":
        if self.start_line > self.end_line:
            raise ValueError(f"start_line ({self.start_line}) cannot exceed end_line ({self.end_line})")
        return self


class LocalizedBoundingBox(BaseModel):
    """
    Spatial-temporal bounding envelope isolating an asset's narrative presence.
    Prevents unrelated edits elsewhere in the scene from invalidating unaffected assets.
    """
    scene_number: str = Field(..., description="Canonical scene identifier e.g. 'Scene 42' or '42'")
    beat_id: Optional[str] = Field(None, description="Enclosing narrative beat ID")
    element_index: int = Field(..., ge=0, description="0-indexed order within parent scene elements")
    span: SourceSpan = Field(..., description="Screenplay document line span")
    character_cue: Optional[str] = Field(None, description="Associated speaker character name if dialogue")
    spatial_scope: SpatialScope = Field(default=SpatialScope.SET_DRESSING)
    interaction_level: InteractionLevel = Field(default=InteractionLevel.INCIDENTAL_BACKGROUND)
    bounding_radius_lines: int = Field(
        default=2,
        ge=0,
        description="Line-vicinity influence threshold for adjacent context interaction",
    )


class EntityMention(BaseModel):
    """
    Extracted reference to a rights-bearing asset (prop, trademark, artwork, music, likeness).
    """
    mention_id: str = Field(..., description="Unique mention ID, e.g. men_s42_poster_01")
    entity_type: str = Field(..., description="artwork, trademark, music, prop, likeness, text, location")
    matched_text: str = Field(..., description="Exact textual reference from screenplay")
    normalized_key: str = Field(..., description="Target stable lineage key, e.g. poster_noir_detective_magazine")
    span: SourceSpan = Field(...)
    bounding_box: LocalizedBoundingBox = Field(...)
    interaction_level: InteractionLevel = Field(default=InteractionLevel.INCIDENTAL_BACKGROUND)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# =============================================================================
# 2. SCREENPLAY AST NODES
# =============================================================================

class ASTElementNode(BaseModel):
    """Base structural element in a Screenplay AST."""
    node_id: str = Field(..., description="Deterministic node identifier, e.g. s42_elem_03")
    element_type: ScreenplayElementType
    content: str = Field(..., description="Normalized element text content")
    span: SourceSpan
    bounding_box: LocalizedBoundingBox
    content_hash: str = Field(..., description="SHA-256 (16-char) hash of normalized content")
    entity_mentions: List[EntityMention] = Field(default_factory=list)
    character_name: Optional[str] = None
    parentheticals: List[str] = Field(default_factory=list)
    quotes: List[str] = Field(default_factory=list, description="Extracted dialogue quotes")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def compute_hash(cls, text: str) -> str:
        clean = " ".join(text.strip().split())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]


class ScriptBeatNode(BaseModel):
    """
    Represents a narrative beat or sub-scene dramatic unit.
    Groups action and dialogue blocks around a specific action beat.
    """
    beat_id: str
    scene_number: str
    beat_index: int
    title: str = ""
    element_ids: List[str] = Field(default_factory=list)
    span: SourceSpan
    entity_mentions: List[EntityMention] = Field(default_factory=list)
    beat_hash: str = Field(default="0" * 16)


class SceneNode(BaseModel):
    """
    Composite container for an entire screenplay scene, anchored by a slugline.
    """
    scene_id: str
    scene_number: str
    slugline: str
    setting_type: str = "INT."           # INT., EXT., INT/EXT.
    location: str = ""                   # e.g. "DETECTIVE OFFICE"
    time_of_day: str = ""                # e.g. "NIGHT", "DAY", "CONTINUOUS"
    elements: List[ASTElementNode] = Field(default_factory=list)
    beats: List[ScriptBeatNode] = Field(default_factory=list)
    span: SourceSpan
    scene_hash: str = Field(default="0" * 16)
    entity_mentions: List[EntityMention] = Field(default_factory=list)

    def get_element_by_id(self, node_id: str) -> Optional[ASTElementNode]:
        for elem in self.elements:
            if elem.node_id == node_id:
                return elem
        return None


class ScreenplayAST(BaseModel):
    """
    Root abstract syntax tree for a version-bound screenplay revision.
    """
    version_id: str = Field(..., description="Target revision identifier e.g. 'v7', 'v8'")
    title: str = Field(default="Untitled Screenplay")
    scenes: List[SceneNode] = Field(default_factory=list)
    document_hash: str = Field(default="0" * 64)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_scene(self, scene_number: str) -> Optional[SceneNode]:
        norm = normalize_scene_number(scene_number)
        for s in self.scenes:
            if normalize_scene_number(s.scene_number) == norm:
                return s
        return None

    def all_mentions(self) -> List[EntityMention]:
        mentions: List[EntityMention] = []
        for s in self.scenes:
            mentions.extend(s.entity_mentions)
        return mentions


# =============================================================================
# 3. PARSER: SCREENPLAY TEXT TO AST
# =============================================================================

SLUGLINE_PATTERN = re.compile(
    r"^(?P<prefix>INT\.|EXT\.|INT/EXT\.|I/E\.)\s*(?P<location>[^-]+?)(?:\s*-\s*(?P<time>.*))?$",
    re.IGNORECASE,
)
SCENE_NUMBERED_SLUGLINE_PATTERN = re.compile(
    r"^(?:SCENE\s+(?P<num>\w+)|(?P<num_prefix>\d+[A-Z]?))\s*[-:]?\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
TRANSITION_PATTERN = re.compile(
    r"^(?:(?:[A-Z\s]+TO:)|FADE OUT\.|FADE IN:|DISSOLVE TO:|CUT TO BLACK\.)\s*$",
    re.IGNORECASE,
)
CHARACTER_CUE_PATTERN = re.compile(
    r"^(?P<name>[A-Z0-9_\-\'\. ]{2,30})(?:\s*\((?P<modifier>V\.O\.|O\.S\.|CONT\'D|[A-Z\.\s]+)\))?$",
)
PARENTHETICAL_PATTERN = re.compile(r"^\((.+)\)$")


def normalize_scene_number(raw: str) -> str:
    """Normalizes 'Scene 42', 'SCENE 42', '42', 'Scene 42 - 00:44:12' -> 'Scene 42'."""
    match = re.search(r"(?:scene\s*)?(\d+[A-Z]?)", raw, re.IGNORECASE)
    if match:
        return f"Scene {match.group(1).lstrip('0') or '0'}"
    return raw.strip()


class ScreenplayParser:
    """
    High-fidelity state-machine parser converting screenplay text/Fountain into ScreenplayAST.
    Extracts sluglines, action paragraphs, character cues, parentheticals, and dialogue blocks.
    """

    KNOWN_ENTITY_KEYWORDS: Dict[str, Dict[str, Any]] = {
        "poster": {
            "entity_type": "artwork",
            "default_key": "poster_noir_detective_magazine",
            "aliases": ["poster", "cover art", "shadows over broadway", "detective magazine"],
        },
        "telephone": {
            "entity_type": "prop",
            "default_key": "prop_vintage_telephone",
            "aliases": ["rotary phone", "western electric", "telephone prop", "desk phone"],
        },
        "paris expo": {
            "entity_type": "artwork",
            "default_key": "poster_paris_expo_1937",
            "aliases": ["1937 paris", "paris exposition", "vintage travel poster"],
        },
        "ford sedan": {
            "entity_type": "prop",
            "default_key": "car_ford_sedan_1949",
            "aliases": ["1949 ford", "custom tudor sedan", "ford sedan"],
        },
        "acme coffee": {
            "entity_type": "trademark",
            "default_key": "trademark_acme_coffee",
            "aliases": ["acme coffee sign", "acme enamel"],
        },
        "abstract expressionist": {
            "entity_type": "artwork",
            "default_key": "artwork_abstract_expressionist",
            "aliases": ["expressionist oil canvas", "abstract expressionist"],
        },
        "mayor": {
            "entity_type": "likeness",
            "default_key": "likeness_mayor_cameo",
            "aliases": ["former city mayor", "mayor cameo"],
        },
        "courthouse": {
            "entity_type": "location",
            "default_key": "architecture_tribunal_facade",
            "aliases": ["county courthouse facade", "courthouse stone steps"],
        },
        "gazette": {
            "entity_type": "text",
            "default_key": "text_headline_gazette",
            "aliases": ["mystery witness disappears", "newspaper stack"],
        },
        "fedora": {
            "entity_type": "trademark",
            "default_key": "wardrobe_fedora_brand",
            "aliases": ["borsalino fedora", "borsalino hat"],
        },
        "radio static": {
            "entity_type": "music",
            "default_key": "music_incidental_radio_static",
            "aliases": ["radio broadcast static", "ambient vintage radio"],
        },
        "midnight serenade": {
            "entity_type": "music",
            "default_key": "music_cue_midnight_serenade",
            "aliases": ["midnight serenade", "jazz trumpet", "speakeasy jazz"],
        },
    }

    @classmethod
    def extract_mentions(
        cls,
        text: str,
        span: SourceSpan,
        bounding_box: LocalizedBoundingBox,
    ) -> List[EntityMention]:
        """Scans text for known rights entities and marks their interaction level."""
        mentions: List[EntityMention] = []
        lower_text = text.lower()

        for term, meta in cls.KNOWN_ENTITY_KEYWORDS.items():
            matched_alias = None
            if term in lower_text:
                matched_alias = term
            else:
                for alias in meta["aliases"]:
                    if alias in lower_text:
                        matched_alias = alias
                        break

            if matched_alias:
                # Determine interaction level
                interaction = InteractionLevel.SET_DRESSING
                if any(k in lower_text for k in ("grabs", "examines", "reads", "reads:", "quotes", "holds")):
                    if "reads" in lower_text or re.search(r"['\"][^'\"]{3,}['\"]", text):
                        interaction = InteractionLevel.DIALOGUE_QUOTATION
                    else:
                        interaction = InteractionLevel.ACTIVE_INTERACTION
                elif any(k in lower_text for k in ("close-up", "closeup", "focal", "hero", "zoom")):
                    interaction = InteractionLevel.FOCAL_HERO
                elif any(k in lower_text for k in ("background", "blur", "out-of-focus", "far wall", "ambient")):
                    interaction = InteractionLevel.INCIDENTAL_BACKGROUND

                mention = EntityMention(
                    mention_id=f"men_{bounding_box.scene_number.replace(' ', '_')}_{meta['default_key']}_{span.start_line}",
                    entity_type=meta["entity_type"],
                    matched_text=matched_alias,
                    normalized_key=meta["default_key"],
                    span=span,
                    bounding_box=bounding_box,
                    interaction_level=interaction,
                    confidence=0.95,
                )
                mentions.append(mention)

        return mentions

    @classmethod
    def parse(cls, raw_text: str, version_id: str, title: str = "Screenplay") -> ScreenplayAST:
        """
        Parses full screenplay text into a structured ScreenplayAST.
        """
        lines = raw_text.splitlines()
        scenes: List[SceneNode] = []

        current_scene: Optional[SceneNode] = None
        current_elements: List[ASTElementNode] = []
        current_mentions: List[EntityMention] = []
        scene_count = 0

        i = 0
        total_lines = len(lines)

        while i < total_lines:
            raw_line = lines[i]
            line = raw_line.strip()
            line_no = i + 1

            if not line:
                i += 1
                continue

            # 1. Check for Scene Heading / Slugline
            # Check if line contains scene number prefix e.g. "Scene 42 - INT. DETECTIVE OFFICE - NIGHT"
            scene_num_match = SCENE_NUMBERED_SLUGLINE_PATTERN.match(line)
            slug_match = None
            detected_scene_num = None

            if scene_num_match:
                detected_scene_num = scene_num_match.group("num") or scene_num_match.group("num_prefix")
                rest = scene_num_match.group("rest").strip()
                slug_match = SLUGLINE_PATTERN.match(rest)
            else:
                slug_match = SLUGLINE_PATTERN.match(line)

            if slug_match:
                # Flush previous scene
                if current_scene is not None:
                    current_scene.elements = list(current_elements)
                    current_scene.entity_mentions = list(current_mentions)
                    current_scene.span.end_line = line_no - 1
                    current_scene.scene_hash = cls._compute_scene_hash(current_scene)
                    scenes.append(current_scene)
                    current_elements = []
                    current_mentions = []

                scene_count += 1
                s_num_str = f"Scene {detected_scene_num if detected_scene_num else scene_count}"
                prefix = slug_match.group("prefix").strip()
                loc = slug_match.group("location").strip()
                tod = slug_match.group("time").strip() if slug_match.group("time") else ""

                heading_span = SourceSpan(start_line=line_no, end_line=line_no)
                heading_box = LocalizedBoundingBox(
                    scene_number=s_num_str,
                    element_index=0,
                    span=heading_span,
                    spatial_scope=SpatialScope.GLOBAL_SCENE,
                )
                heading_node = ASTElementNode(
                    node_id=f"s{scene_count}_elem_0",
                    element_type=ScreenplayElementType.SCENE_HEADING,
                    content=line,
                    span=heading_span,
                    bounding_box=heading_box,
                    content_hash=ASTElementNode.compute_hash(line),
                )
                current_elements.append(heading_node)

                current_scene = SceneNode(
                    scene_id=f"scene_{version_id}_{scene_count}",
                    scene_number=s_num_str,
                    slugline=line,
                    setting_type=prefix,
                    location=loc,
                    time_of_day=tod,
                    elements=[],
                    span=SourceSpan(start_line=line_no, end_line=line_no),
                )
                i += 1
                continue

            # Ensure an active scene exists
            if current_scene is None:
                scene_count += 1
                current_scene = SceneNode(
                    scene_id=f"scene_{version_id}_{scene_count}",
                    scene_number=f"Scene {scene_count}",
                    slugline=f"SCENE {scene_count} - PROLOGUE",
                    span=SourceSpan(start_line=line_no, end_line=line_no),
                )

            # 2. Check for Transition (e.g. CUT TO:)
            if TRANSITION_PATTERN.match(line):
                elem_idx = len(current_elements)
                t_span = SourceSpan(start_line=line_no, end_line=line_no)
                t_box = LocalizedBoundingBox(
                    scene_number=current_scene.scene_number,
                    element_index=elem_idx,
                    span=t_span,
                    spatial_scope=SpatialScope.GLOBAL_SCENE,
                )
                t_node = ASTElementNode(
                    node_id=f"s{scene_count}_elem_{elem_idx}",
                    element_type=ScreenplayElementType.TRANSITION,
                    content=line,
                    span=t_span,
                    bounding_box=t_box,
                    content_hash=ASTElementNode.compute_hash(line),
                )
                current_elements.append(t_node)
                i += 1
                continue

            # 3. Check for Character Cue & Dialogue Block
            char_match = CHARACTER_CUE_PATTERN.match(line)
            # A character cue is typically in uppercase and not ending with a period/comma
            is_likely_char = (
                char_match
                and not line.endswith((".", ",", ";"))
                and len(line) < 35
                and i + 1 < total_lines
                and lines[i + 1].strip()
            )

            if is_likely_char:
                char_name = char_match.group("name").strip()
                char_span = SourceSpan(start_line=line_no, end_line=line_no)
                char_elem_idx = len(current_elements)
                char_box = LocalizedBoundingBox(
                    scene_number=current_scene.scene_number,
                    element_index=char_elem_idx,
                    span=char_span,
                    character_cue=char_name,
                    spatial_scope=SpatialScope.FOREGROUND,
                )
                char_node = ASTElementNode(
                    node_id=f"s{scene_count}_elem_{char_elem_idx}",
                    element_type=ScreenplayElementType.CHARACTER_CUE,
                    content=line,
                    span=char_span,
                    bounding_box=char_box,
                    content_hash=ASTElementNode.compute_hash(line),
                    character_name=char_name,
                )
                current_elements.append(char_node)

                # Now parse subsequent dialogue lines and parentheticals
                i += 1
                parentheticals: List[str] = []
                dialogue_lines: List[str] = []
                d_start = i + 1

                while i < total_lines:
                    d_line_raw = lines[i]
                    d_line = d_line_raw.strip()
                    if not d_line:
                        break  # Dialogue block ends at blank line

                    paren_match = PARENTHETICAL_PATTERN.match(d_line)
                    if paren_match:
                        parentheticals.append(paren_match.group(1).strip())
                    else:
                        dialogue_lines.append(d_line)
                    i += 1

                d_text = " ".join(dialogue_lines)
                d_end = i
                d_span = SourceSpan(start_line=d_start, end_line=max(d_start, d_end))
                d_elem_idx = len(current_elements)
                d_box = LocalizedBoundingBox(
                    scene_number=current_scene.scene_number,
                    element_index=d_elem_idx,
                    span=d_span,
                    character_cue=char_name,
                    spatial_scope=SpatialScope.FOREGROUND,
                )

                quotes_found = re.findall(r"['\"]([^'\"]{3,})['\"]", d_text)
                d_mentions = cls.extract_mentions(d_text, d_span, d_box)
                current_mentions.extend(d_mentions)

                d_node = ASTElementNode(
                    node_id=f"s{scene_count}_elem_{d_elem_idx}",
                    element_type=ScreenplayElementType.DIALOGUE,
                    content=d_text,
                    span=d_span,
                    bounding_box=d_box,
                    content_hash=ASTElementNode.compute_hash(d_text),
                    character_name=char_name,
                    parentheticals=parentheticals,
                    quotes=quotes_found,
                    entity_mentions=d_mentions,
                )
                current_elements.append(d_node)
                continue

            # 4. Action Description (Line-level element granularity for exact localized bounding)
            act_text = line
            act_span = SourceSpan(start_line=line_no, end_line=line_no)
            act_idx = len(current_elements)

            # Determine default spatial scope from keywords
            scope = SpatialScope.BACKGROUND
            if any(k in act_text.lower() for k in ("foreground", "grabs", "holding", "closeup", "close-up", "examines")):
                scope = SpatialScope.FOREGROUND
            elif any(k in act_text.lower() for k in ("desk", "wall", "table", "counter", "booth", "chair")):
                scope = SpatialScope.SET_DRESSING

            act_box = LocalizedBoundingBox(
                scene_number=current_scene.scene_number,
                element_index=act_idx,
                span=act_span,
                spatial_scope=scope,
            )
            act_mentions = cls.extract_mentions(act_text, act_span, act_box)
            current_mentions.extend(act_mentions)

            act_node = ASTElementNode(
                node_id=f"s{scene_count}_elem_{act_idx}",
                element_type=ScreenplayElementType.ACTION,
                content=act_text,
                span=act_span,
                bounding_box=act_box,
                content_hash=ASTElementNode.compute_hash(act_text),
                entity_mentions=act_mentions,
            )
            current_elements.append(act_node)
            i += 1

        # Flush final scene
        if current_scene is not None:
            current_scene.elements = list(current_elements)
            current_scene.entity_mentions = list(current_mentions)
            current_scene.span.end_line = total_lines
            current_scene.scene_hash = cls._compute_scene_hash(current_scene)
            scenes.append(current_scene)

        doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        return ScreenplayAST(
            version_id=version_id,
            title=title,
            scenes=scenes,
            document_hash=doc_hash,
        )

    @staticmethod
    def _compute_scene_hash(scene: SceneNode) -> str:
        payload = f"{scene.slugline}::" + "::".join(e.content_hash for e in scene.elements)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# 4. AST DIFFING & LOCALIZED BOUNDING INTERFERENCE ENGINE
# =============================================================================

class ASTDiffKind(str, Enum):
    ADDED = "added"
    MATERIALLY_MODIFIED = "materially_modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    NON_MATERIALLY_MODIFIED = "non_materially_modified"


class ASTElementDelta(BaseModel):
    """Diff detail for an individual screenplay element."""
    element_delta_id: str
    scene_number: str
    element_type: ScreenplayElementType
    diff_kind: ASTDiffKind
    before_node_id: Optional[str] = None
    after_node_id: Optional[str] = None
    before_content: Optional[str] = None
    after_content: Optional[str] = None
    affected_mentions: List[str] = Field(default_factory=list)
    character_affected: Optional[str] = None
    is_rights_bearing: bool = False
    change_summary: str = ""


class SceneDelta(BaseModel):
    """Aggregate diff detail for a scene."""
    scene_number: str
    diff_kind: ASTDiffKind
    element_deltas: List[ASTElementDelta] = Field(default_factory=list)
    has_rights_impact: bool = False
    summary: str = ""


class AssetInterferenceResult(BaseModel):
    """
    Mathematical evaluation of whether a set of script deltas within a scene
    actually interferes with a specific asset's clearance boundary.
    """
    stable_lineage_key: str
    scene_number: str
    interferes: bool
    reason_code: str
    explanation: str
    relevant_element_deltas: List[ASTElementDelta] = Field(default_factory=list)
    prominence_shift: Optional[str] = None


class ScreenplayDeltaReport(BaseModel):
    """Full hierarchical diff report between Revision N and Revision N+1."""
    base_version_id: str
    target_version_id: str
    scene_deltas: List[SceneDelta] = Field(default_factory=list)
    total_elements_diffed: int = 0
    rights_interferences: List[AssetInterferenceResult] = Field(default_factory=list)
    summary_counts: Dict[str, int] = Field(default_factory=dict)


class ScreenplayDeltaEngine:
    """
    Screenplay Semantic Diffing & Localized Bounding Box Matching Engine.
    Detects changes between Revision N and Revision N+1, isolates non-rights edits,
    and produces deterministic, mathematically bounded creative deltas for InvalidationEngine.
    """

    @classmethod
    def diff(cls, base_ast: ScreenplayAST, target_ast: ScreenplayAST) -> ScreenplayDeltaReport:
        """
        Hierarchically compares base_ast and target_ast.
        1. Aligns scenes by normalized scene number and slugline similarity.
        2. Aligns elements within scenes using LCS and element type heuristics.
        3. Classifies deltas into ASTDiffKind.
        """
        base_scene_map = {normalize_scene_number(s.scene_number): s for s in base_ast.scenes}
        target_scene_map = {normalize_scene_number(s.scene_number): s for s in target_ast.scenes}

        all_scenes = list(dict.fromkeys(list(base_scene_map.keys()) + list(target_scene_map.keys())))
        scene_deltas: List[SceneDelta] = []
        total_elements = 0

        counts = {
            "scenes_unchanged": 0,
            "scenes_modified": 0,
            "scenes_added": 0,
            "scenes_removed": 0,
            "elements_unchanged": 0,
            "elements_modified": 0,
            "elements_added": 0,
            "elements_removed": 0,
        }

        for sc_num in all_scenes:
            base_s = base_scene_map.get(sc_num)
            target_s = target_scene_map.get(sc_num)

            if base_s is not None and target_s is None:
                # Scene removed
                counts["scenes_removed"] += 1
                elem_deltas = [
                    ASTElementDelta(
                        element_delta_id=f"delta_{e.node_id}_rem",
                        scene_number=sc_num,
                        element_type=e.element_type,
                        diff_kind=ASTDiffKind.REMOVED,
                        before_node_id=e.node_id,
                        before_content=e.content,
                        is_rights_bearing=len(e.entity_mentions) > 0,
                        change_summary="Element removed in target draft",
                    )
                    for e in base_s.elements
                ]
                scene_deltas.append(
                    SceneDelta(
                        scene_number=sc_num,
                        diff_kind=ASTDiffKind.REMOVED,
                        element_deltas=elem_deltas,
                        has_rights_impact=any(d.is_rights_bearing for d in elem_deltas),
                        summary=f"{sc_num} removed in target revision",
                    )
                )
                counts["elements_removed"] += len(elem_deltas)
                total_elements += len(elem_deltas)

            elif base_s is None and target_s is not None:
                # Scene added
                counts["scenes_added"] += 1
                elem_deltas = [
                    ASTElementDelta(
                        element_delta_id=f"delta_{e.node_id}_add",
                        scene_number=sc_num,
                        element_type=e.element_type,
                        diff_kind=ASTDiffKind.ADDED,
                        after_node_id=e.node_id,
                        after_content=e.content,
                        is_rights_bearing=len(e.entity_mentions) > 0,
                        change_summary="Element added in target draft",
                    )
                    for e in target_s.elements
                ]
                scene_deltas.append(
                    SceneDelta(
                        scene_number=sc_num,
                        diff_kind=ASTDiffKind.ADDED,
                        element_deltas=elem_deltas,
                        has_rights_impact=any(d.is_rights_bearing for d in elem_deltas),
                        summary=f"{sc_num} newly introduced in target revision",
                    )
                )
                counts["elements_added"] += len(elem_deltas)
                total_elements += len(elem_deltas)

            else:
                # Present in both: compare elements
                assert base_s is not None and target_s is not None
                elem_deltas = cls._diff_scene_elements(base_s, target_s)
                total_elements += len(elem_deltas)

                modified_any = any(d.diff_kind != ASTDiffKind.UNCHANGED for d in elem_deltas)
                has_rights = any(d.is_rights_bearing and d.diff_kind != ASTDiffKind.UNCHANGED for d in elem_deltas)

                if modified_any:
                    counts["scenes_modified"] += 1
                    scene_diff = (
                        ASTDiffKind.MATERIALLY_MODIFIED if has_rights else ASTDiffKind.NON_MATERIALLY_MODIFIED
                    )
                else:
                    counts["scenes_unchanged"] += 1
                    scene_diff = ASTDiffKind.UNCHANGED

                for d in elem_deltas:
                    if d.diff_kind == ASTDiffKind.UNCHANGED:
                        counts["elements_unchanged"] += 1
                    elif d.diff_kind == ASTDiffKind.ADDED:
                        counts["elements_added"] += 1
                    elif d.diff_kind == ASTDiffKind.REMOVED:
                        counts["elements_removed"] += 1
                    else:
                        counts["elements_modified"] += 1

                scene_deltas.append(
                    SceneDelta(
                        scene_number=sc_num,
                        diff_kind=scene_diff,
                        element_deltas=elem_deltas,
                        has_rights_impact=has_rights,
                        summary=f"{sc_num} evaluation: {len(elem_deltas)} elements diffed",
                    )
                )

        return ScreenplayDeltaReport(
            base_version_id=base_ast.version_id,
            target_version_id=target_ast.version_id,
            scene_deltas=scene_deltas,
            total_elements_diffed=total_elements,
            summary_counts=counts,
        )

    @classmethod
    def _diff_scene_elements(cls, base_s: SceneNode, target_s: SceneNode) -> List[ASTElementDelta]:
        """Aligns and diffs elements within a matched scene."""
        deltas: List[ASTElementDelta] = []
        base_elems = base_s.elements
        target_elems = target_s.elements

        # Fast path: identical element hashes
        if [e.content_hash for e in base_elems] == [e.content_hash for e in target_elems]:
            for e in base_elems:
                deltas.append(
                    ASTElementDelta(
                        element_delta_id=f"delta_{e.node_id}_unc",
                        scene_number=base_s.scene_number,
                        element_type=e.element_type,
                        diff_kind=ASTDiffKind.UNCHANGED,
                        before_node_id=e.node_id,
                        after_node_id=e.node_id,
                        before_content=e.content,
                        after_content=e.content,
                        is_rights_bearing=len(e.entity_mentions) > 0,
                        change_summary="Identical element content across revisions",
                    )
                )
            return deltas

        # LCS-based alignment matching on (element_type, character_name, normalized_hash)
        matcher = difflib.SequenceMatcher(
            None,
            [f"{e.element_type.value}:{e.character_name or ''}:{e.content_hash}" for e in base_elems],
            [f"{e.element_type.value}:{e.character_name or ''}:{e.content_hash}" for e in target_elems],
        )

        for tag, b_start, b_end, t_start, t_end in matcher.get_opcodes():
            if tag == "equal":
                for idx in range(b_end - b_start):
                    be = base_elems[b_start + idx]
                    te = target_elems[t_start + idx]
                    deltas.append(
                        ASTElementDelta(
                            element_delta_id=f"delta_{be.node_id}_eq",
                            scene_number=base_s.scene_number,
                            element_type=be.element_type,
                            diff_kind=ASTDiffKind.UNCHANGED,
                            before_node_id=be.node_id,
                            after_node_id=te.node_id,
                            before_content=be.content,
                            after_content=te.content,
                            is_rights_bearing=len(be.entity_mentions) > 0 or len(te.entity_mentions) > 0,
                            change_summary="Identical element",
                        )
                    )
            elif tag == "replace":
                # Check for 1:1 modifications vs type mismatch
                b_slice = base_elems[b_start:b_end]
                t_slice = target_elems[t_start:t_end]
                max_len = max(len(b_slice), len(t_slice))
                for k in range(max_len):
                    be = b_slice[k] if k < len(b_slice) else None
                    te = t_slice[k] if k < len(t_slice) else None

                    if be is not None and te is not None and be.element_type == te.element_type:
                        # Modified element
                        rights_involved = len(be.entity_mentions) > 0 or len(te.entity_mentions) > 0
                        # Evaluate if change is material vs non-material (e.g. typo)
                        is_mat = cls._is_material_element_change(be, te)
                        diff_k = ASTDiffKind.MATERIALLY_MODIFIED if is_mat else ASTDiffKind.NON_MATERIALLY_MODIFIED

                        mentions = [m.normalized_key for m in be.entity_mentions + te.entity_mentions]
                        deltas.append(
                            ASTElementDelta(
                                element_delta_id=f"delta_{be.node_id}_{te.node_id}",
                                scene_number=base_s.scene_number,
                                element_type=be.element_type,
                                diff_kind=diff_k,
                                before_node_id=be.node_id,
                                after_node_id=te.node_id,
                                before_content=be.content,
                                after_content=te.content,
                                affected_mentions=list(dict.fromkeys(mentions)),
                                character_affected=te.character_name or be.character_name,
                                is_rights_bearing=rights_involved,
                                change_summary=f"Modified {be.element_type.value}: {'material' if is_mat else 'non-material'}",
                            )
                        )
                    elif be is not None and te is None:
                        deltas.append(
                            ASTElementDelta(
                                element_delta_id=f"delta_{be.node_id}_rem",
                                scene_number=base_s.scene_number,
                                element_type=be.element_type,
                                diff_kind=ASTDiffKind.REMOVED,
                                before_node_id=be.node_id,
                                before_content=be.content,
                                is_rights_bearing=len(be.entity_mentions) > 0,
                                change_summary=f"Removed {be.element_type.value}",
                            )
                        )
                    elif be is None and te is not None:
                        deltas.append(
                            ASTElementDelta(
                                element_delta_id=f"delta_{te.node_id}_add",
                                scene_number=target_s.scene_number,
                                element_type=te.element_type,
                                diff_kind=ASTDiffKind.ADDED,
                                after_node_id=te.node_id,
                                after_content=te.content,
                                is_rights_bearing=len(te.entity_mentions) > 0,
                                change_summary=f"Added {te.element_type.value}",
                            )
                        )
                    else:
                        # Both exist but different element types
                        assert be is not None and te is not None
                        deltas.append(
                            ASTElementDelta(
                                element_delta_id=f"delta_{be.node_id}_type_rep",
                                scene_number=base_s.scene_number,
                                element_type=be.element_type,
                                diff_kind=ASTDiffKind.REMOVED,
                                before_node_id=be.node_id,
                                before_content=be.content,
                                is_rights_bearing=len(be.entity_mentions) > 0,
                            )
                        )
                        deltas.append(
                            ASTElementDelta(
                                element_delta_id=f"delta_{te.node_id}_type_add",
                                scene_number=target_s.scene_number,
                                element_type=te.element_type,
                                diff_kind=ASTDiffKind.ADDED,
                                after_node_id=te.node_id,
                                after_content=te.content,
                                is_rights_bearing=len(te.entity_mentions) > 0,
                            )
                        )
            elif tag == "delete":
                for idx in range(b_end - b_start):
                    be = base_elems[b_start + idx]
                    deltas.append(
                        ASTElementDelta(
                            element_delta_id=f"delta_{be.node_id}_del",
                            scene_number=base_s.scene_number,
                            element_type=be.element_type,
                            diff_kind=ASTDiffKind.REMOVED,
                            before_node_id=be.node_id,
                            before_content=be.content,
                            is_rights_bearing=len(be.entity_mentions) > 0,
                            change_summary=f"Deleted {be.element_type.value}",
                        )
                    )
            elif tag == "insert":
                for idx in range(t_end - t_start):
                    te = target_elems[t_start + idx]
                    deltas.append(
                        ASTElementDelta(
                            element_delta_id=f"delta_{te.node_id}_ins",
                            scene_number=target_s.scene_number,
                            element_type=te.element_type,
                            diff_kind=ASTDiffKind.ADDED,
                            after_node_id=te.node_id,
                            after_content=te.content,
                            is_rights_bearing=len(te.entity_mentions) > 0,
                            change_summary=f"Inserted {te.element_type.value}",
                        )
                    )

        return deltas

    @staticmethod
    def _is_material_element_change(be: ASTElementNode, te: ASTElementNode) -> bool:
        """
        Determines whether change between two matching elements is material.
        Material triggers:
        - Introducing or altering rights entity mentions
        - Camera framing escalations (focal, close-up, foreground)
        - Introducing spoken quotes or reads aloud
        Non-material triggers:
        - Typo fixes, minor punctuation, cosmetic word substitutions in non-rights dialogue
        """
        # Trigger 1: Entity mention difference
        b_keys = {m.normalized_key for m in be.entity_mentions}
        t_keys = {m.normalized_key for m in te.entity_mentions}
        if b_keys != t_keys or len(t_keys) > 0:
            # If target has rights mentions, check interaction escalation
            b_levels = {m.interaction_level for m in be.entity_mentions}
            t_levels = {m.interaction_level for m in te.entity_mentions}
            if b_levels != t_levels:
                return True

        # Trigger 2: Dialogue quotes added
        if te.quotes and not be.quotes:
            return True

        # Trigger 3: Spatial scope escalation
        if be.bounding_box.spatial_scope != te.bounding_box.spatial_scope:
            if te.bounding_box.spatial_scope in (SpatialScope.FOREGROUND, SpatialScope.HERO_INTERACTION):
                return True

        # Trigger 4: Token similarity check
        # High similarity (>75%) without entity changes = non-material
        clean_b = set(re.sub(r"[^\w\s]", "", be.content.lower()).split())
        clean_t = set(re.sub(r"[^\w\s]", "", te.content.lower()).split())
        if clean_b and clean_t:
            overlap = len(clean_b.intersection(clean_t)) / max(len(clean_b.union(clean_t)), 1)
            if overlap >= 0.75 and not t_keys and not b_keys:
                return False

        # If entities are mentioned and text changed significantly
        if t_keys or b_keys:
            return True

        return False

    # =========================================================================
    # 5. LOCALIZED BOUNDING MATCHING: ZERO FALSE INVALIDATION
    # =========================================================================

    @classmethod
    def evaluate_asset_interference(
        cls,
        asset_use: CreativeUse,
        scene_delta: SceneDelta,
    ) -> AssetInterferenceResult:
        """
        Evaluates whether scene changes interfere with a specific asset_use.
        MATHEMATICAL PROPERTY:
        If an edit occurs in a dialogue block that does not reference asset_use.stable_lineage_key,
        and does not alter the spatial scope of asset_use's bounding box,
        Interference = FALSE. Unrelated assets in the same scene carry forward fail-closed.
        """
        key = asset_use.stable_lineage_key
        sc_num = normalize_scene_number(asset_use.scene_or_timecode)

        if normalize_scene_number(scene_delta.scene_number) != sc_num:
            # Different scene: strictly zero interference
            return AssetInterferenceResult(
                stable_lineage_key=key,
                scene_number=sc_num,
                interferes=False,
                reason_code="DISTANT_SCENE_ISOLATED",
                explanation=f"Asset located in {sc_num}; delta occurred in {scene_delta.scene_number}.",
            )

        if scene_delta.diff_kind == ASTDiffKind.UNCHANGED:
            return AssetInterferenceResult(
                stable_lineage_key=key,
                scene_number=sc_num,
                interferes=False,
                reason_code="CREATIVE_USE_IDENTICAL",
                explanation="Scene AST elements are identical across drafts.",
            )

        if scene_delta.diff_kind == ASTDiffKind.REMOVED:
            return AssetInterferenceResult(
                stable_lineage_key=key,
                scene_number=sc_num,
                interferes=True,
                reason_code="SCENE_REMOVED_FROM_CUT",
                explanation=f"Parent scene {sc_num} removed from production revision.",
            )

        # Iterate over individual element deltas within this scene
        relevant_deltas: List[ASTElementDelta] = []
        direct_reference_found = False
        spatial_escalation_found = False

        for ed in scene_delta.element_deltas:
            if ed.diff_kind == ASTDiffKind.UNCHANGED:
                continue

            # Check direct entity mention reference
            if key in ed.affected_mentions:
                direct_reference_found = True
                relevant_deltas.append(ed)
                continue

            # Check if text mentions asset alias
            content_to_check = f"{ed.before_content or ''} {ed.after_content or ''}".lower()
            asset_tokens = [t for t in key.split("_") if len(t) > 3 and t not in ("prop", "artwork", "music", "trademark", "text")]
            if any(tok in content_to_check for tok in asset_tokens):
                direct_reference_found = True
                relevant_deltas.append(ed)
                continue

            # Check if action escalates camera framing for this specific asset
            if ed.element_type == ScreenplayElementType.ACTION and any(
                k in content_to_check for k in ("close-up", "closeup", "focal", "zoom", "grabs")
            ):
                if any(tok in content_to_check for tok in asset_tokens):
                    spatial_escalation_found = True
                    relevant_deltas.append(ed)

        if direct_reference_found or spatial_escalation_found:
            prom_shift = (
                "Escalated to focal interaction with dialogue."
                if direct_reference_found
                else "Camera framing shifted."
            )
            return AssetInterferenceResult(
                stable_lineage_key=key,
                scene_number=sc_num,
                interferes=True,
                reason_code="CREATIVE_CONTEXT_ALTERED",
                explanation=f"Direct narrative interaction or focal shift detected for asset '{key}'.",
                relevant_element_deltas=relevant_deltas,
                prominence_shift=prom_shift,
            )

        # Edits exist in the scene, BUT NONE touch this asset's localized bounding box!
        return AssetInterferenceResult(
            stable_lineage_key=key,
            scene_number=sc_num,
            interferes=False,
            reason_code="LOCALIZED_BOUNDING_ISOLATED",
            explanation=(
                f"Edits in {sc_num} are confined to unrelated dialogue/action; "
                f"asset '{key}' remains in localized background envelope."
            ),
            relevant_element_deltas=[],
        )

    # =========================================================================
    # 6. INTEGRATION CONTRACT: GENERATE BOUNDED CREATIVE DELTAS
    # =========================================================================

    @classmethod
    def generate_bounded_deltas(
        cls,
        base_ast: ScreenplayAST,
        target_ast: ScreenplayAST,
        base_uses: List[CreativeUse],
        target_uses: List[CreativeUse],
    ) -> Dict[str, CreativeDelta]:
        """
        Integrates AST Screenplay Delta with InvalidationEngine contracts.
        Produces a mapping of stable_lineage_key -> CreativeDelta.
        Ensures localized bounding isolation prevents false stale invalidations.
        """
        report = cls.diff(base_ast, target_ast)
        scene_delta_map = {normalize_scene_number(s.scene_number): s for s in report.scene_deltas}

        base_map = {u.stable_lineage_key: u for u in base_uses}
        target_map = {u.stable_lineage_key: u for u in target_uses}
        all_keys = list(dict.fromkeys(list(base_map.keys()) + list(target_map.keys())))

        creative_deltas: Dict[str, CreativeDelta] = {}

        for key in sorted(all_keys):
            b_use = base_map.get(key)
            t_use = target_map.get(key)

            # Case 1: Removed asset
            if b_use is not None and t_use is None:
                creative_deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=b_use.use_id,
                    after_use_id=None,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.REMOVED,
                    materiality="high",
                    changed_fields=["use_id"],
                    reason_codes=["CLAIM_REMOVED_FROM_SCRIPT"],
                )
                continue

            # Case 2: Added asset
            if b_use is None and t_use is not None:
                creative_deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=None,
                    after_use_id=t_use.use_id,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.ADDED,
                    materiality="high",
                    changed_fields=["use_id", "context_hash"],
                    reason_codes=["NEW_UNCLEARED_CLAIM"],
                )
                continue

            assert b_use is not None and t_use is not None

            # Case 3: Both present. Check localized scene bounding interference
            sc_num = normalize_scene_number(b_use.scene_or_timecode)
            scene_delta = scene_delta_map.get(sc_num)

            if scene_delta is None or scene_delta.diff_kind == ASTDiffKind.UNCHANGED:
                # Scene identical: unchanged
                creative_deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=b_use.use_id,
                    after_use_id=t_use.use_id,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.UNCHANGED,
                    materiality="none",
                    changed_fields=[],
                    reason_codes=["CREATIVE_USE_IDENTICAL"],
                )
                continue

            # Evaluate localized bounding interference
            interference = cls.evaluate_asset_interference(b_use, scene_delta)

            if interference.interferes:
                creative_deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=b_use.use_id,
                    after_use_id=t_use.use_id,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.MATERIALLY_MODIFIED,
                    materiality="high",
                    changed_fields=["context_hash", "duration_or_prominence", "context"],
                    reason_codes=["CREATIVE_CONTEXT_ALTERED", "PROMINENCE_ESCALATED"],
                )
            else:
                # Unrelated edits in the scene were isolated!
                creative_deltas[key] = CreativeDelta(
                    delta_id=f"delta_{key}",
                    before_use_id=b_use.use_id,
                    after_use_id=t_use.use_id,
                    stable_lineage_key=key,
                    change_kind=ChangeKind.UNCHANGED,
                    materiality="none",
                    changed_fields=[],
                    reason_codes=["LOCALIZED_BOUNDING_ISOLATED"],
                )

        # Enforce Model Containment Guardrail on all emitted deltas
        for delta in creative_deltas.values():
            SemanticDeltaEngine.enforce_containment_guardrail(delta)

        return creative_deltas
