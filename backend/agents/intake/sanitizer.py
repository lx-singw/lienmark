"""
sanitizer.py

Input sanitization, multi-encoding normalization, expanded Trojan Source Unicode
Bidi stripping, and delimiter breakout tag escaping for untrusted screenplay documents.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from typing import Tuple
from pydantic import BaseModel, Field

# Matches expanded Unicode bidirectional override & embedding control characters,
# directional isolates, zero-width joiners, invisible operators, and interlinear annotations.
BIDI_AND_STEGANO_PATTERN = re.compile(
    r"[\u200B-\u200F\uFEFF\u202A-\u202E\u2060-\u2069\u061C\uFFF9-\uFFFB]"
)

# Unprintable ASCII control characters (excluding newline \n, carriage return \r, tab \t)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Common delimiter breakout patterns targeted by prompt injection exploits
BREAKOUT_DELIMITERS = [
    re.compile(r"</?system[^>]*>", re.IGNORECASE),
    re.compile(r"</?user[^>]*>", re.IGNORECASE),
    re.compile(r"</?assistant[^>]*>", re.IGNORECASE),
    re.compile(r"\[/?INST\]", re.IGNORECASE),
]


class SanitizedPayload(BaseModel):
    """Container for sanitized script text enclosed with a cryptographic nonce."""

    sanitized_text: str = Field(
        description="Normalized script text with Bidi and control codes stripped"
    )
    wrapped_payload: str = Field(
        description="XML-fenced payload with cryptographic nonce"
    )
    nonce: str = Field(description="Unique per-request cryptographic nonce")
    chars_stripped_count: int = Field(
        default=0, description="Count of stripped invisible/Bidi characters"
    )


def normalize_encoding(text: str) -> str:
    """Normalizes Unicode text via NFKC decomposition to neutralize homoglyphs."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def strip_bidi_and_control_chars(text: str) -> Tuple[str, int]:
    """
    Normalizes multi-encoding representation, then strips Unicode bidirectional
    override characters, zero-width spaces, and unprintable ASCII control codes.
    """
    normalized = normalize_encoding(text)
    initial_len = len(normalized)
    cleaned = BIDI_AND_STEGANO_PATTERN.sub("", normalized)
    cleaned = CONTROL_CHARS_PATTERN.sub("", cleaned)
    stripped = initial_len - len(cleaned)
    return cleaned, stripped


def escape_xml_fences(text: str, tag: str = "untrusted_script_payload") -> str:
    """
    Escapes opening and closing containment boundary tags and common
    delimiter breakout patterns to prevent boundary escaping.
    """
    closing_regex = re.compile(rf"</\s*{re.escape(tag)}\s*>", re.IGNORECASE)
    opening_regex = re.compile(rf"<\s*{re.escape(tag)}[^>]*>", re.IGNORECASE)
    escaped = closing_regex.sub(f"&lt;/{tag}&gt;", text)
    escaped = opening_regex.sub(f"&lt;{tag}&gt;", escaped)
    for pattern in BREAKOUT_DELIMITERS:
        escaped = pattern.sub(
            lambda m: m.group(0).replace("<", "&lt;").replace(">", "&gt;"),
            escaped,
        )
    return escaped


def wrap_untrusted_payload(
    text: str,
    nonce: str | None = None,
    tag: str = "untrusted_script_payload",
) -> SanitizedPayload:
    """
    Sanitizes raw script text, neutralizes boundary escape tags,
    and wraps the untrusted payload inside a nonced XML isolation fence.
    """
    cleaned, stripped_count = strip_bidi_and_control_chars(text)
    escaped = escape_xml_fences(cleaned, tag=tag)
    req_nonce = nonce or secrets.token_hex(16)
    wrapped = (
        f"<{tag} nonce=\"{req_nonce}\">\n"
        f"{escaped}\n"
        f"</{tag}>"
    )
    return SanitizedPayload(
        sanitized_text=escaped,
        wrapped_payload=wrapped,
        nonce=req_nonce,
        chars_stripped_count=stripped_count,
    )
