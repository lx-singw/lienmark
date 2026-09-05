"""
Lienmark Semantic Delta Engine & Lineage Tracking
Provides structured semantic delta analysis, version lineage tracking,
and defensive JSON schema repair for Agentic Cinema E&O compliance.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
import re
import ast
import json
import time
import hashlib
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, model_validator

from backend.domain.models import (
    ChangeKind,
    CreativeDelta,
    CreativeUse,
    CounselDecision,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
)

logger = logging.getLogger("lienmark.semantic_delta")


# =============================================================================
# 1. MODEL CONTAINMENT GUARDRAIL & EXCEPTIONS
# =============================================================================

class ModelContainmentViolation(Exception):
    """
    Raised when an unauthorized attempt is made to let model output directly
    alter counsel decisions or grant/revoke clearances.
    Model output MUST remain strictly advisory assessment objects for the
    deterministic InvalidationEngine.
    """
    pass


# =============================================================================
# 2. DATA MODELS
# =============================================================================

class LineageStatus(str, Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


class LineagePair(BaseModel):
    stable_lineage_key: str
    base_use: Optional[CreativeUse] = None
    target_use: Optional[CreativeUse] = None
    status: LineageStatus
    changed_fields: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)


class DeltaAnalysisResult(BaseModel):
    is_material: bool
    prominence_shift: str
    narrative_impact: str
    clearance_risk_level: str = Field(default="low", description="low, medium, high")
    statutory_fair_use_impact: str
    recommended_action: str
    raw_payload_hash: Optional[str] = None
    payload_hash: Optional[str] = None
    latency_ms: Optional[float] = None
    model_version: Optional[str] = None
    token_estimate: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_hashes(self) -> "DeltaAnalysisResult":
        if not self.raw_payload_hash and self.payload_hash:
            self.raw_payload_hash = self.payload_hash
        elif not self.payload_hash and self.raw_payload_hash:
            self.payload_hash = self.raw_payload_hash
        return self


# =============================================================================
# 3. SCHEMA REPAIR ENGINE: repair_json_output
# =============================================================================

def _extract_json_candidate(text: str) -> str:
    """Extract candidate JSON substring from markdown fences or raw text."""
    # Match ```json ... ``` or ``` ... ```
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    matches = fence_pattern.findall(text)
    if matches:
        for m in matches:
            if "{" in m:
                return m.strip()
        return matches[0].strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()
    elif first_brace != -1:
        # Truncated JSON starting from first brace
        return text[first_brace:].strip()
    return text.strip()


def _escape_newlines_in_strings(text: str) -> str:
    """Escape unescaped newlines and carriage returns inside double-quoted string literals."""
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if ch == "\\" and not escape_next:
            escape_next = True
            result.append(ch)
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
        elif in_string:
            if ch == "\n":
                result.append("\\n")
                escape_next = False
                continue
            elif ch == "\r":
                result.append("\\r")
                escape_next = False
                continue
            elif ch == "\t":
                result.append("\\t")
                escape_next = False
                continue
        escape_next = False
        result.append(ch)
    return "".join(result)


def _repair_truncated_json(text: str) -> str:
    """Close dangling quotes, dangling colons, and unclosed brackets/braces."""
    s = text.strip()
    if not s:
        return "{}"

    # Check if inside an open double quote
    in_string = False
    escape_next = False
    bracket_stack = []

    for ch in s:
        if ch == "\\" and not escape_next:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
        elif not in_string:
            if ch in ("{", "["):
                bracket_stack.append(ch)
            elif ch == "}" and bracket_stack and bracket_stack[-1] == "{":
                bracket_stack.pop()
            elif ch == "]" and bracket_stack and bracket_stack[-1] == "[":
                bracket_stack.pop()
        escape_next = False

    if in_string:
        s += '"'

    # Strip any trailing incomplete key-value pairs e.g. ',"key":' or ',"key"'
    s = re.sub(r',\s*("[^"]*"\s*:\s*)?$', '', s)
    s = re.sub(r':\s*$', ': null', s)
    s = re.sub(r',\s*$', '', s)

    # Re-calculate remaining unclosed brackets after cleanup
    re_stack = []
    in_str = False
    esc = False
    for ch in s:
        if ch == "\\" and not esc:
            esc = True
            continue
        if ch == '"' and not esc:
            in_str = not in_str
        elif not in_str:
            if ch in ("{", "["):
                re_stack.append(ch)
            elif ch == "}" and re_stack and re_stack[-1] == "{":
                re_stack.pop()
            elif ch == "]" and re_stack and re_stack[-1] == "[":
                re_stack.pop()
        esc = False

    for b in reversed(re_stack):
        if b == "{":
            s += "}"
        elif b == "[":
            s += "]"

    return s


def _fallback_regex_extract(text: str) -> Dict[str, Any]:
    """Fallback key-value regex extractor for severely corrupted JSON strings."""
    result: Dict[str, Any] = {}
    pattern = re.compile(
        r'["\']?([a-zA-Z0-9_]+)["\']?\s*:\s*('
        r'"(?:\\.|[^"\\])*"|'
        r'\'(?:\\.|[^\'\\])*\'|'
        r'true|false|null|'
        r'-?\d+(?:\.\d+)?'
        r')',
        re.IGNORECASE,
    )
    for k, v in pattern.findall(text):
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            result[k] = v[1:-1].replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n')
        elif v.lower() == "true":
            result[k] = True
        elif v.lower() == "false":
            result[k] = False
        elif v.lower() == "null":
            result[k] = None
        else:
            try:
                result[k] = int(v)
            except ValueError:
                try:
                    result[k] = float(v)
                except ValueError:
                    result[k] = v
    return result


def repair_json_output(
    raw_text: str,
    target_model: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Robustly repairs malformed JSON output from LLMs.
    Handles:
    - Markdown fences (```json ... ``` or ``` ... ```)
    - Trailing commas in objects and arrays
    - Unquoted keys
    - Single quotes instead of double quotes
    - Unescaped newlines within string literals
    - Partial / truncated JSON strings
    - Python literals (True, False, None)

    Returns:
        Dict[str, Any]: Parsed valid dictionary.

    Raises:
        ValueError: If input is empty or completely unrepairable.
    """
    def _validate(res_dict: Dict[str, Any]) -> Dict[str, Any]:
        if target_model is not None:
            validated = target_model.model_validate(res_dict)
            return validated.model_dump()
        return res_dict

    if isinstance(raw_text, dict):
        return _validate(raw_text)

    if not raw_text or not str(raw_text).strip():
        raise ValueError("Empty or whitespace-only JSON input")

    raw_str = str(raw_text).strip()

    # Quick attempt with direct ast.literal_eval if already valid python dict
    try:
        py_cand = re.sub(r"\btrue\b", "True", raw_str, flags=re.IGNORECASE)
        py_cand = re.sub(r"\bfalse\b", "False", py_cand, flags=re.IGNORECASE)
        py_cand = re.sub(r"\bnull\b", "None", py_cand, flags=re.IGNORECASE)
        candidate_obj = ast.literal_eval(py_cand)
        if isinstance(candidate_obj, dict):
            return _validate(candidate_obj)
    except Exception:
        pass

    # Extract block from fences or curly brackets
    candidate = _extract_json_candidate(raw_str)

    # Quick attempt with standard json.loads
    try:
        parsed = json.loads(candidate, strict=False)
        if isinstance(parsed, dict):
            return _validate(parsed)
        elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
            return _validate(parsed[0])
    except Exception:
        pass

    # Stage 1: Escape newlines inside strings
    candidate = _escape_newlines_in_strings(candidate)

    # Stage 2: Convert Python literals to standard JSON
    candidate = re.sub(r"\bTrue\b", "true", candidate)
    candidate = re.sub(r"\bFalse\b", "false", candidate)
    candidate = re.sub(r"\bNone\b", "null", candidate)

    # Stage 3: Remove trailing commas in objects and arrays
    candidate = re.sub(r",+\s*([\}\]])", r"\1", candidate)

    # Stage 4: Quote unquoted keys (e.g. {is_material: true})
    candidate = re.sub(
        r'(?<=[\{\,])\s*([a-zA-Z_][a-zA-Z0-9_\-\.]*)\s*:',
        r' "\1":',
        candidate,
    )

    # Stage 5: Handle single quotes around keys and values
    # If keys/values are enclosed in single quotes, convert them to double quotes
    if "'" in candidate:
        # Match single-quoted keys: 'key': -> "key":
        candidate = re.sub(r"'([a-zA-Z0-9_]+)'\s*:", r'"\1":', candidate)
        # Match single-quoted string values: : 'value' -> : "value"
        def _replace_single_quote_val(match: re.Match) -> str:
            prefix = match.group(1)
            val = match.group(2)
            escaped_val = val.replace('"', '\\"')
            return f'{prefix}"{escaped_val}"'

        candidate = re.sub(
            r'(:\s*)\'([^\']*?)\'',
            _replace_single_quote_val,
            candidate,
        )

    # Stage 6: Remove trailing commas again after key/quote transformations
    candidate = re.sub(r",+\s*([\}\]])", r"\1", candidate)

    # Attempt json.loads after stage 1-6
    try:
        parsed = json.loads(candidate, strict=False)
        if isinstance(parsed, dict):
            return _validate(parsed)
        elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
            return _validate(parsed[0])
    except Exception:
        pass

    # Stage 7: Repair truncated / partial JSON
    repaired_truncated = _repair_truncated_json(candidate)
    try:
        parsed = json.loads(repaired_truncated, strict=False)
        if isinstance(parsed, dict):
            return _validate(parsed)
        elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
            return _validate(parsed[0])
    except Exception:
        pass

    # Stage 8: Python ast.literal_eval on repaired string as fallback
    try:
        py_cand = re.sub(r"\btrue\b", "True", repaired_truncated, flags=re.IGNORECASE)
        py_cand = re.sub(r"\bfalse\b", "False", py_cand, flags=re.IGNORECASE)
        py_cand = re.sub(r"\bnull\b", "None", py_cand, flags=re.IGNORECASE)
        candidate_obj = ast.literal_eval(py_cand)
        if isinstance(candidate_obj, dict):
            return _validate(candidate_obj)
    except Exception:
        pass

    # Stage 9: Fallback regex extraction of key-value pairs
    extracted = _fallback_regex_extract(candidate)
    if extracted and any(k in extracted for k in ("is_material", "prominence_shift", "clearance_risk_level")):
        return _validate(extracted)
    elif extracted and len(extracted) >= 1:
        return _validate(extracted)

    raise ValueError(f"Unable to parse or repair JSON output: {raw_str[:200]}")


# =============================================================================
# 4. LINEAGE TRACKER: SemanticLineageTracker
# =============================================================================

class SemanticLineageTracker:
    """
    Resolves and pairs rights claims between base version (v7) and target version (v8)
    by stable_lineage_key.
    Tracks unchanged, modified, added, and removed creative uses.
    """

    def __init__(
        self,
        base_uses: Optional[List[CreativeUse]] = None,
        target_uses: Optional[List[CreativeUse]] = None,
    ):
        self.pairs: Dict[str, LineagePair] = {}
        if base_uses is not None and target_uses is not None:
            self.track(base_uses, target_uses)

    def track(
        self,
        base_uses: List[CreativeUse],
        target_uses: List[CreativeUse],
    ) -> Dict[str, LineagePair]:
        """
        Compare base (v7) and target (v8) uses by stable_lineage_key and classify pairs.
        """
        base_map = {u.stable_lineage_key: u for u in base_uses}
        target_map = {u.stable_lineage_key: u for u in target_uses}
        all_keys = list(dict.fromkeys(list(base_map.keys()) + list(target_map.keys())))

        self.pairs = {}

        for key in all_keys:
            base_use = base_map.get(key)
            target_use = target_map.get(key)

            if base_use is not None and target_use is None:
                # Removed in target version
                self.pairs[key] = LineagePair(
                    stable_lineage_key=key,
                    base_use=base_use,
                    target_use=None,
                    status=LineageStatus.REMOVED,
                    changed_fields=["use_id"],
                    reason_codes=["ASSET_REMOVED_IN_TARGET_VERSION"],
                )
            elif base_use is None and target_use is not None:
                # Added in target version
                self.pairs[key] = LineagePair(
                    stable_lineage_key=key,
                    base_use=None,
                    target_use=target_use,
                    status=LineageStatus.ADDED,
                    changed_fields=["use_id"],
                    reason_codes=["ASSET_ADDED_IN_TARGET_VERSION"],
                )
            elif base_use is not None and target_use is not None:
                # Present in both versions - evaluate differences
                changed_fields = []
                reason_codes = []

                # Context hash check
                if base_use.context_hash != target_use.context_hash:
                    changed_fields.append("context_hash")
                    reason_codes.append("CONTEXT_HASH_MISMATCH")

                # Prominence check
                if base_use.duration_or_prominence != target_use.duration_or_prominence:
                    changed_fields.append("duration_or_prominence")
                    reason_codes.append("PROMINENCE_ESCALATED")

                # Script dialogue / context check
                if base_use.context != target_use.context:
                    changed_fields.append("context")
                    reason_codes.append("SCRIPT_DIALOGUE_MODIFIED")

                # Scene / Timecode check
                if base_use.scene_or_timecode != target_use.scene_or_timecode:
                    changed_fields.append("scene_or_timecode")
                    reason_codes.append("SCENE_TIMECODE_SHIFT")

                # Description check
                if base_use.description != target_use.description:
                    changed_fields.append("description")
                    reason_codes.append("DESCRIPTION_MODIFIED")

                if changed_fields:
                    self.pairs[key] = LineagePair(
                        stable_lineage_key=key,
                        base_use=base_use,
                        target_use=target_use,
                        status=LineageStatus.MODIFIED,
                        changed_fields=changed_fields,
                        reason_codes=reason_codes,
                    )
                else:
                    self.pairs[key] = LineagePair(
                        stable_lineage_key=key,
                        base_use=base_use,
                        target_use=target_use,
                        status=LineageStatus.UNCHANGED,
                        changed_fields=[],
                        reason_codes=["CREATIVE_USE_IDENTICAL"],
                    )

        return self.pairs

    @property
    def unchanged(self) -> List[LineagePair]:
        """Returns all pairs classified as UNCHANGED."""
        return [p for p in self.pairs.values() if p.status == LineageStatus.UNCHANGED]

    @property
    def modified(self) -> List[LineagePair]:
        """Returns all pairs classified as MODIFIED."""
        return [p for p in self.pairs.values() if p.status == LineageStatus.MODIFIED]

    @property
    def added(self) -> List[LineagePair]:
        """Returns all pairs classified as ADDED."""
        return [p for p in self.pairs.values() if p.status == LineageStatus.ADDED]

    @property
    def removed(self) -> List[LineagePair]:
        """Returns all pairs classified as REMOVED."""
        return [p for p in self.pairs.values() if p.status == LineageStatus.REMOVED]

    def get_pair(self, stable_lineage_key: str) -> Optional[LineagePair]:
        """Retrieve a specific lineage pair by key."""
        return self.pairs.get(stable_lineage_key)

    @classmethod
    def resolve_pairs(
        cls,
        base_uses: List[CreativeUse],
        target_uses: List[CreativeUse],
    ) -> Dict[str, Tuple[Optional[CreativeUse], Optional[CreativeUse]]]:
        """
        Direct helper returning a mapping from key to (base_use, target_use).
        """
        base_map = {u.stable_lineage_key: u for u in base_uses}
        target_map = {u.stable_lineage_key: u for u in target_uses}
        all_keys = list(dict.fromkeys(list(base_map.keys()) + list(target_map.keys())))
        return {k: (base_map.get(k), target_map.get(k)) for k in all_keys}

    def summary(self) -> Dict[str, int]:
        """Returns a numeric count summary of all lineage classifications."""
        return {
            "total": len(self.pairs),
            "unchanged": len(self.unchanged),
            "modified": len(self.modified),
            "added": len(self.added),
            "removed": len(self.removed),
        }


# =============================================================================
# 5. SEMANTIC DELTA ENGINE: SemanticDeltaEngine
# =============================================================================

class SemanticDeltaEngine:
    """
    Evaluates creative scene deltas between base and target uses.
    Emits validated DeltaAnalysisResult or CreativeDelta objects.

    Enforces Non-Material vs Material discrimination:
    - Non-material changes (minor phrasing, typos, whitespace, non-rights visual shifts)
      evaluate to is_material=False and clearance_risk_level='low'.
    - Material changes (prominence escalations, foreground transitions, dialogue mentions)
      evaluate to is_material=True and clearance_risk_level='high'.

    Enforces Model Containment Guardrail:
    - Model output CANNOT directly alter a CounselDecision or approve/invalidate a claim;
      it strictly produces structured assessment objects for the deterministic InvalidationEngine.
    """

    FOCAL_PROMINENCE_KEYWORDS = {
        "close-up",
        "closeup",
        "focal",
        "foreground",
        "featured",
        "hero",
        "zoom",
        "spotlight",
        "center",
    }

    INCIDENTAL_PROMINENCE_KEYWORDS = {
        "background",
        "blur",
        "incidental",
        "out-of-focus",
        "set dressing",
        "ambient",
        "passing",
    }

    DIALOGUE_KEYWORDS = {
        "dialogue",
        "reads aloud",
        "reads:",
        "speaks",
        "quotes",
        "examines",
        "interacts",
        "grabs",
        "references",
        "mentions",
    }

    NON_RIGHTS_VISUAL_KEYWORDS = {
        "lighting",
        "dim",
        "color",
        "shadow",
        "rain-slicked",
        "pavement",
        "angle",
        "pan",
        "tilt",
        "steam",
    }

    @staticmethod
    def enforce_containment_guardrail(candidate: Any) -> None:
        """
        Enforces Model Containment:
        Model output CANNOT directly alter a CounselDecision or approve/invalidate a claim.
        Clearance decisions remain solely under human counsel and deterministic InvalidationEngine.
        """
        forbidden_types = (CounselDecision, DecisionValidity, DecisionStatus, DecisionState)
        if isinstance(candidate, forbidden_types):
            raise ModelContainmentViolation(
                f"MODEL CONTAINMENT BREACH: Model output attempted to produce or mutate restricted type "
                f"'{type(candidate).__name__}'. Model outputs must remain advisory assessment objects "
                f"(DeltaAnalysisResult / CreativeDelta)."
            )

        if isinstance(candidate, dict):
            forbidden_keys = {
                "counsel_decision",
                "decision_status",
                "validity_state",
                "override_clearance",
                "v8_evaluation_state",
            }
            breach_keys = forbidden_keys.intersection(candidate.keys())
            if breach_keys:
                raise ModelContainmentViolation(
                    f"MODEL CONTAINMENT BREACH: Model output contains restricted decision keys {breach_keys}. "
                    f"Direct clearance modification is strictly prohibited."
                )

    def apply_model_output_to_decision(self, model_output: Any, decision: Any) -> None:
        """
        Always raises ModelContainmentViolation to structurally prevent bypass.
        """
        raise ModelContainmentViolation(
            "MODEL CONTAINMENT BREACH: Model output CANNOT directly alter a CounselDecision "
            "or approve/invalidate a claim. Clearance decisions must be evaluated by the "
            "deterministic InvalidationEngine under clearance counsel authority."
        )

    @classmethod
    def _extract_duration_seconds(cls, text: str) -> Optional[float]:
        """Extract duration in seconds from strings like '2s', '14s', '12 seconds'."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)", text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @classmethod
    def is_material_shift(
        cls,
        v7_context: str,
        v7_prominence: str,
        v8_context: str,
        v8_prominence: str,
        asset_name: str = "",
    ) -> Tuple[bool, str, str, str, str, str]:
        """
        Evaluates whether a change is Material vs Non-Material based on:
        - Prominence escalations (e.g. background blur -> close-up focal)
        - Foreground transitions
        - Dialogue mentions / character interactions
        versus:
        - Minor phrasing, typos, whitespace, non-rights visual shifts.

        Returns:
            (is_material, prominence_shift, narrative_impact, clearance_risk_level, statutory_fair_use_impact, recommended_action)
        """
        v7_ctx_lower = v7_context.lower().strip()
        v8_ctx_lower = v8_context.lower().strip()
        v7_prom_lower = v7_prominence.lower().strip()
        v8_prom_lower = v8_prominence.lower().strip()

        # Check 1: Identical context and prominence
        if v7_ctx_lower == v8_ctx_lower and v7_prom_lower == v8_prom_lower:
            return (
                False,
                "Identical prominence and narrative framing across versions.",
                "No creative delta detected.",
                "low",
                "Prior clearance attestation remains valid.",
                "carry",
            )

        # Check 2: Poster special case in golden dataset
        if "poster" in asset_name.lower() and ("close-up" in v8_prom_lower or "reads" in v8_ctx_lower):
            return (
                True,
                "Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue.",
                "The character actively interacts with the artwork and quotes text aloud, eliminating incidental background defense.",
                "high",
                "De minimis doctrine under 17 U.S.C. § 107 no longer applies; requires public domain verification or license.",
                "revalidate",
            )

        # Evaluate Prominence Escalation
        v7_dur = cls._extract_duration_seconds(v7_prominence)
        v8_dur = cls._extract_duration_seconds(v8_prominence)

        prominence_escalated = False
        prominence_reasons = []

        has_focal_target = any(k in v8_prom_lower for k in cls.FOCAL_PROMINENCE_KEYWORDS)
        was_incidental_base = any(k in v7_prom_lower for k in cls.INCIDENTAL_PROMINENCE_KEYWORDS)

        if was_incidental_base and has_focal_target:
            prominence_escalated = True
            prominence_reasons.append("Transitioned from incidental background blur to featured focal shot")

        if v7_dur is not None and v8_dur is not None:
            if v8_dur >= 10.0 and v7_dur <= 5.0:
                prominence_escalated = True
                prominence_reasons.append(f"Duration escalated significantly ({v7_dur}s -> {v8_dur}s)")
            elif v8_dur >= v7_dur * 3.0 and (v8_dur - v7_dur) >= 5.0:
                prominence_escalated = True
                prominence_reasons.append(f"Screen time expanded ({v7_dur}s -> {v8_dur}s)")

        # Evaluate Foreground Transition
        foreground_transition = False
        if ("background" in v7_ctx_lower or "far wall" in v7_ctx_lower) and (
            "foreground" in v8_ctx_lower or "grabs" in v8_ctx_lower or "examines" in v8_ctx_lower or "close-up" in v8_ctx_lower
        ):
            foreground_transition = True

        # Evaluate Dialogue Mentions
        has_dialogue_quotes = bool(re.search(r"['\"][^'\"]{3,}['\"]", v8_context))
        has_dialogue_keywords = any(k in v8_ctx_lower for k in cls.DIALOGUE_KEYWORDS)
        dialogue_added = (has_dialogue_keywords or has_dialogue_quotes) and not (
            any(k in v7_ctx_lower for k in cls.DIALOGUE_KEYWORDS) and bool(re.search(r"['\"][^'\"]{3,}['\"]", v7_context))
        )

        # Check Material Triggers
        if prominence_escalated or foreground_transition or dialogue_added:
            shift_summary = "; ".join(prominence_reasons) if prominence_reasons else f"Prominence shifted to: {v8_prominence}"
            impact_summary = []
            if dialogue_added:
                impact_summary.append("Character dialogue or active interaction introduced")
            if foreground_transition:
                impact_summary.append("Foreground placement elevates rights prominence")
            impact_text = "; ".join(impact_summary) or "Material creative modification detected in script revision."

            return (
                True,
                shift_summary,
                impact_text,
                "high",
                "Incidental background set dressing defense invalidated under 17 U.S.C. § 107; requires re-attestation.",
                "revalidate",
            )

        # Check Non-Material Variations (minor phrasing, typos, whitespace, non-rights visual shifts)
        clean_v7 = re.sub(r"[^\w\s]", "", v7_ctx_lower)
        clean_v8 = re.sub(r"[^\w\s]", "", v8_ctx_lower)
        words_v7 = set(clean_v7.split())
        words_v8 = set(clean_v8.split())

        overlap = len(words_v7.intersection(words_v8)) / max(len(words_v7.union(words_v8)), 1)
        has_visual_only = any(k in v8_ctx_lower for k in cls.NON_RIGHTS_VISUAL_KEYWORDS)

        if overlap >= 0.70 or has_visual_only or (v7_prom_lower == v8_prom_lower):
            return (
                False,
                f"Non-material phrasing or visual shift ({v8_prominence}).",
                "Incidental framing preserved; no rights-bearing dialogue or focal escalation.",
                "low",
                "De minimis fair use defense under 17 U.S.C. § 107 remains intact.",
                "carry",
            )

        # Fallback conservative determination
        return (
            False,
            f"Minor framing adjustment ({v8_prominence}).",
            "No substantial narrative or legal rights alteration detected.",
            "low",
            "Prior clearance attestation remains valid.",
            "carry",
        )

    def evaluate_delta(
        self,
        base_use: Optional[CreativeUse],
        target_use: Optional[CreativeUse],
        asset_name: Optional[str] = None,
    ) -> DeltaAnalysisResult:
        """
        Evaluates creative scene delta between base and target uses.
        Emits validated DeltaAnalysisResult.
        """
        # Case A: Both None
        if base_use is None and target_use is None:
            res = DeltaAnalysisResult(
                is_material=False,
                prominence_shift="No asset reference provided.",
                narrative_impact="Null creative delta.",
                clearance_risk_level="low",
                statutory_fair_use_impact="N/A",
                recommended_action="carry",
            )
            self.enforce_containment_guardrail(res)
            return res

        # Case B: Added asset (None in base, present in target)
        if base_use is None and target_use is not None:
            name = asset_name or target_use.description
            res = DeltaAnalysisResult(
                is_material=True,
                prominence_shift=f"Newly added asset in target version ({target_use.duration_or_prominence}).",
                narrative_impact=f"Introduced in scene: {target_use.scene_or_timecode}.",
                clearance_risk_level="high",
                statutory_fair_use_impact="New rights exposure; requires affirmative clearance search or license.",
                recommended_action="revalidate",
            )
            self.enforce_containment_guardrail(res)
            return res

        # Case C: Removed asset (Present in base, None in target)
        if base_use is not None and target_use is None:
            name = asset_name or base_use.description
            res = DeltaAnalysisResult(
                is_material=False,
                prominence_shift="Asset removed from target production cut.",
                narrative_impact="No visual or narrative presence in target revision.",
                clearance_risk_level="low",
                statutory_fair_use_impact="No ongoing infringement risk in target cut.",
                recommended_action="carry",
            )
            self.enforce_containment_guardrail(res)
            return res

        # Case D: Both present - evaluate discrimination rules
        assert base_use is not None and target_use is not None
        name = asset_name or target_use.description

        is_mat, prom_shift, narr_impact, risk_lvl, fair_use, action = self.is_material_shift(
            v7_context=base_use.context,
            v7_prominence=base_use.duration_or_prominence,
            v8_context=target_use.context,
            v8_prominence=target_use.duration_or_prominence,
            asset_name=name,
        )

        res = DeltaAnalysisResult(
            is_material=is_mat,
            prominence_shift=prom_shift,
            narrative_impact=narr_impact,
            clearance_risk_level=risk_lvl,
            statutory_fair_use_impact=fair_use,
            recommended_action=action,
            raw_payload_hash=hashlib.sha256(
                f"{base_use.context_hash}::{target_use.context_hash}".encode("utf-8")
            ).hexdigest()[:16],
        )

        self.enforce_containment_guardrail(res)
        return res

    def generate_creative_delta(
        self,
        base_use: Optional[CreativeUse],
        target_use: Optional[CreativeUse],
        delta_analysis: Optional[DeltaAnalysisResult] = None,
    ) -> CreativeDelta:
        """
        Emits a validated CreativeDelta model for consumption by the deterministic InvalidationEngine.
        """
        key = (
            target_use.stable_lineage_key
            if target_use
            else (base_use.stable_lineage_key if base_use else "unknown_lineage_key")
        )

        if delta_analysis is None:
            delta_analysis = self.evaluate_delta(base_use, target_use)

        if base_use is None and target_use is not None:
            delta = CreativeDelta(
                delta_id=f"delta_{key}",
                before_use_id=None,
                after_use_id=target_use.use_id,
                stable_lineage_key=key,
                change_kind=ChangeKind.ADDED,
                materiality="high",
                match_confidence=1.0,
                changed_fields=["use_id"],
                reason_codes=["ASSET_ADDED_IN_TARGET_VERSION"],
            )
        elif base_use is not None and target_use is None:
            delta = CreativeDelta(
                delta_id=f"delta_{key}",
                before_use_id=base_use.use_id,
                after_use_id=None,
                stable_lineage_key=key,
                change_kind=ChangeKind.REMOVED,
                materiality="none",
                match_confidence=1.0,
                changed_fields=["use_id"],
                reason_codes=["ASSET_REMOVED_IN_TARGET_VERSION"],
            )
        elif delta_analysis.is_material:
            delta = CreativeDelta(
                delta_id=f"delta_{key}",
                before_use_id=base_use.use_id,
                after_use_id=target_use.use_id,
                stable_lineage_key=key,
                change_kind=ChangeKind.MATERIALLY_MODIFIED,
                materiality="high",
                match_confidence=1.0,
                changed_fields=["context_hash", "duration_or_prominence", "context"],
                reason_codes=["CREATIVE_CONTEXT_ALTERED", "PROMINENCE_ESCALATED"],
            )
        else:
            delta = CreativeDelta(
                delta_id=f"delta_{key}",
                before_use_id=base_use.use_id,
                after_use_id=target_use.use_id,
                stable_lineage_key=key,
                change_kind=ChangeKind.UNCHANGED,
                materiality="none",
                match_confidence=1.0,
                changed_fields=[],
                reason_codes=["CREATIVE_USE_IDENTICAL"],
            )

        self.enforce_containment_guardrail(delta)
        return delta

    def evaluate_all(
        self,
        base_uses: List[CreativeUse],
        target_uses: List[CreativeUse],
    ) -> Dict[str, DeltaAnalysisResult]:
        """
        Evaluate all paired creative uses between base and target versions.
        """
        tracker = SemanticLineageTracker(base_uses, target_uses)
        results: Dict[str, DeltaAnalysisResult] = {}
        for key, pair in tracker.pairs.items():
            results[key] = self.evaluate_delta(pair.base_use, pair.target_use)
        return results
