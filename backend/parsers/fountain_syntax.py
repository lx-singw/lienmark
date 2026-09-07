"""Fountain 1.1 syntax rules, regex matchers, and text sanitizers."""

import re
from typing import Dict, List, Optional, Tuple

HEADING_PATTERN = re.compile(
    r"^(?:(?:\.[A-Za-z0-9].*)|(?:(?:INT|EXT|INT/EXT|EXT/INT|I/E)(?:[\.\s]).*))",
    re.IGNORECASE,
)
SCENE_NUMBER_PATTERN = re.compile(r"#([\w\-]+)#\s*$")
TRANSITION_PATTERN = re.compile(r"^(?:>.*|.*TO:)$")


class FountainSyntax:
    """Encapsulates Fountain syntax classification and string sanitization."""

    @staticmethod
    def extract_metadata_and_body(text: str) -> Tuple[Dict[str, str], str]:
        """Separate title page key-value pairs from the main screenplay body."""
        lines = text.splitlines()
        meta: Dict[str, str] = {}
        idx = 0

        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                break
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip().lower()] = val.strip()
                idx += 1
            else:
                break

        return meta, "\n".join(lines[idx:])

    @staticmethod
    def strip_boneyard_and_notes(text: str) -> str:
        """Strip boneyard blocks (/* ... */) and notes ([[ ... ]])."""
        no_boneyard = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        return re.sub(r"\[\[.*?\]\]", "", no_boneyard, flags=re.DOTALL)

    @classmethod
    def is_scene_heading(cls, line: str) -> bool:
        """Determine if line matches standard or forced scene headings."""
        return bool(HEADING_PATTERN.match(line.strip()))

    @classmethod
    def is_transition(cls, line: str) -> bool:
        """Determine if line represents a screenplay transition."""
        stripped = line.strip()
        if stripped.startswith(">") and not stripped.endswith("<"):
            return True
        return bool(TRANSITION_PATTERN.match(stripped) and stripped.isupper())

    @classmethod
    def is_character_cue(cls, line: str) -> bool:
        """Determine if line represents a character speaking cue."""
        stripped = line.strip()
        if stripped.startswith("@"):
            return True
        if len(stripped) > 40 or len(stripped) < 2:
            return False
        base = re.sub(r"\s*\(.*?\)\s*", "", stripped).rstrip("^").strip()
        return bool(base and base.isupper() and re.match(r"^[A-Z0-9\s\.\-']+$", base))

    @classmethod
    def extract_scene_heading(cls, line: str) -> Tuple[str, Optional[int]]:
        """Parse clean heading text and optional embedded scene number."""
        clean = line.lstrip(".").strip()
        match = SCENE_NUMBER_PATTERN.search(clean)
        num: Optional[int] = None
        if match:
            num_digits = re.sub(r"\D", "", match.group(1))
            if num_digits:
                num = int(num_digits)
            clean = SCENE_NUMBER_PATTERN.sub("", clean).strip()
        return clean, num
