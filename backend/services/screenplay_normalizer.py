"""
screenplay_normalizer.py

Normalizer for screenplay text in Lienmark.
Normalizes whitespace, character casing, strips PDF/file metadata timestamps,
and normalizes character dialogue blocks so re-saving a script without altering
text produces an identical semantic hash.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Iterator, List, Optional, Tuple

_PDF_METADATA_PATTERN = re.compile(
    r"^/(?:CreationDate|ModDate|Producer|Creator|Title|Author|Subject)\b.*$|"
    r"/(?:CreationDate|ModDate|Producer|Creator)\s*\([^)]*\)",
    re.IGNORECASE,
)
_PDF_HEADER_PATTERN = re.compile(r"^%pdf-\d+\.\d+|^%%[a-z]+.*$", re.IGNORECASE)
_ISO_TIMESTAMP_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"
)
_SLASH_DASH_DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_TEXT_DATE_PATTERN = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4}\b",
    re.IGNORECASE,
)
_CLOCK_TIME_PATTERN = re.compile(
    r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?\b",
    re.IGNORECASE,
)
_DRAFT_HEADER_PATTERN = re.compile(
    r"^(?:draft(?:\s+date)?|revision|revised|date|generated|exported|printed)\s*[:\-].*$",
    re.IGNORECASE,
)
_PAGE_NUMBER_PATTERN = re.compile(
    r"^(?:page\s+\d+(?:\s+of\s+\d+)?|\d+\.|\d+|\[\s*page\s+\d+\s*\])\.?$",
    re.IGNORECASE,
)
_SLUGLINE_PATTERN = re.compile(
    r"^(?:INT\.|EXT\.|INT/EXT\.|I/E\.|SCENE\s+\d+)",
    re.IGNORECASE,
)
_TRANSITION_PATTERN = re.compile(
    r"^(?:(?:[A-Z\s]+TO:)|FADE OUT\.|FADE IN:|DISSOLVE TO:|CUT TO BLACK\.)\s*$",
    re.IGNORECASE,
)
_CONT_MODIFIER_PATTERN = re.compile(
    r"^(?:cont[\'’]?d|continuing|cont)$",
    re.IGNORECASE,
)

_CHAR_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9_\-\'. ]{2,35})\s*:?(?:\s*\((?P<modifier>[^)]+)\))?\s*:?$"
)
_INLINE_DIALOGUE = re.compile(
    r"^(?P<name>[A-Za-z0-9_\-\'. ]{2,35})\s*:?(?:\s*\((?P<modifier>[^)]+)\))?\s*:\s+(?P<text>.+)$"
)


def _clean_modifier(mod_raw: Optional[str]) -> Optional[str]:
    """Cleans dialogue modifier, stripping cont'd pagination artifacts."""
    if not mod_raw:
        return None
    cleaned = mod_raw.strip().lower()
    if _CONT_MODIFIER_PATTERN.match(cleaned):
        return None
    return cleaned


def _strip_line_timestamps(line: str) -> str:
    """Strips timestamps, dates, and clock markers from a line."""
    text = _ISO_TIMESTAMP_PATTERN.sub("", line)
    text = _SLASH_DASH_DATE_PATTERN.sub("", text)
    text = _TEXT_DATE_PATTERN.sub("", text)
    text = _CLOCK_TIME_PATTERN.sub("", text)
    return " ".join(text.strip().split())


def _is_metadata_artifact(line: str) -> bool:
    """Checks whether line matches PDF headers, draft notes, or page numbers."""
    if _PDF_HEADER_PATTERN.match(line) or _PDF_METADATA_PATTERN.match(line):
        return True
    if _PAGE_NUMBER_PATTERN.match(line) or _DRAFT_HEADER_PATTERN.match(line):
        return True
    return False


def _parse_cue_line(raw_line: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Detects character cue or inline dialogue, returning (name, mod, text)."""
    s = raw_line.strip()
    if not s or _SLUGLINE_PATTERN.match(s) or _TRANSITION_PATTERN.match(s) or s.startswith("("):
        return None
    if s.endswith((".", ",", ";", "?", "!")):
        return None

    cue = _CHAR_LINE.match(s)
    if cue:
        name = cue.group("name").strip().rstrip(":")
        if any(c.isalpha() for c in name) and (name.isupper() or s.endswith(":") or len(name.split()) <= 3):
            return name, cue.group("modifier"), None

    inline = _INLINE_DIALOGUE.match(s)
    if inline:
        name = inline.group("name").strip().rstrip(":")
        text = inline.group("text").strip()
        if not (text.startswith("(") and text.endswith(")")):
            if any(c.isalpha() for c in name) and (name.isupper() or len(name.split()) <= 3):
                return name, inline.group("modifier"), text
    return None


class ScreenplayAccumulator:
    """State machine tracking and flushing dialogue and action blocks."""

    def __init__(self) -> None:
        self.active_char: Optional[str] = None
        self.active_mod: Optional[str] = None
        self.active_dialogue: List[str] = []
        self.active_action: List[str] = []

    def flush_action(self) -> Optional[str]:
        """Flushes buffered action lines into a single paragraph."""
        if not self.active_action:
            return None
        result = " ".join(self.active_action).strip().lower()
        self.active_action = []
        return result

    def flush_dialogue(self) -> Optional[str]:
        """Flushes buffered character dialogue into a canonical entry."""
        if not (self.active_char and self.active_dialogue):
            self.active_char = None
            self.active_mod = None
            self.active_dialogue = []
            return None
        text = " ".join(self.active_dialogue).strip().lower()
        char = self.active_char
        mod = self.active_mod
        self.active_char = None
        self.active_mod = None
        self.active_dialogue = []
        if mod:
            return f"{char} ({mod}): {text}"
        return f"{char}: {text}"

    def flush_all(self) -> Iterator[str]:
        """Flushes dialogue followed by action."""
        d = self.flush_dialogue()
        if d:
            yield d
        a = self.flush_action()
        if a:
            yield a

    def handle_line(self, raw_line: str) -> Iterator[str]:
        """Processes an incoming raw line through state filters."""
        normalized = unicodedata.normalize("NFKC", raw_line).strip()
        if not normalized:
            yield from self.flush_all()
            return
        if _is_metadata_artifact(normalized):
            return
        s_clean = _strip_line_timestamps(normalized)
        if not s_clean:
            return
        if _SLUGLINE_PATTERN.match(s_clean) or _TRANSITION_PATTERN.match(s_clean):
            yield from self.flush_all()
            yield s_clean.lower()
            return
        cue = _parse_cue_line(normalized)
        if cue:
            yield from self.flush_all()
            name, mod, text = cue
            self.active_char = name.lower()
            self.active_mod = _clean_modifier(mod)
            if text:
                self.active_dialogue.append(text)
            return
        if self.active_char:
            self.active_dialogue.append(s_clean)
        else:
            self.active_action.append(s_clean)


def normalize_screenplay_stream(lines_iter: Iterable[str]) -> Iterator[str]:
    """
    Streaming generator normalizing screenplay lines with $O(1)$ memory.
    Collapses dialogue blocks, strips metadata timestamps, and normalizes casing.
    """
    accumulator = ScreenplayAccumulator()
    for raw_line in lines_iter:
        yield from accumulator.handle_line(raw_line)
    yield from accumulator.flush_all()


def normalize_screenplay_text(text: str) -> str:
    """
    Returns canonical normalized screenplay text string.
    Ensures scripts re-saved with whitespace or margin deltas match semantically.
    """
    lines = text.splitlines()
    normalized_lines = list(normalize_screenplay_stream(lines))
    return "\n".join(normalized_lines)
