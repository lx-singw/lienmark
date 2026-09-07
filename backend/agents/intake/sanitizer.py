"""
sanitizer.py

Input sanitization, Trojan Source Unicode Bidi stripping, and XML boundary
encapsulation for untrusted screenplay documents in the Intake pipeline.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import re
import secrets
from typing import Tuple
from pydantic import BaseModel, Field

# Matches Unicode bidirectional override & embedding control characters (Trojan Source)
# as well as zero-width non-rendering characters often used to conceal injection keywords.
BIDI_AND_STEGANO_PATTERN = re.compile(
    r"[\u200B-\u200D\uFEFF\u202A-\u202E\u2066-\u2069\u200E\u200F\u061C]"
)

# Unprintable ASCII control characters (excluding newline \n, carriage return \r, tab \t)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


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


def strip_bidi_and_control_chars(text: str) -> Tuple[str, int]:
    """
    Strips Unicode bidirectional override characters, zero-width spaces,
    and non-standard ASCII control characters that could conceal prompt injections.
    """
    initial_len = len(text)
    cleaned = BIDI_AND_STEGANO_PATTERN.sub("", text)
    cleaned = CONTROL_CHARS_PATTERN.sub("", cleaned)
    stripped = initial_len - len(cleaned)
    return cleaned, stripped


def escape_xml_fences(text: str, tag: str = "untrusted_script_payload") -> str:
    """
    Escapes all opening and closing XML tags matching the containment boundary
    to prevent delimiter injection or premature fence escaping.
    """
    closing_regex = re.compile(rf"</\s*{re.escape(tag)}\s*>", re.IGNORECASE)
    opening_regex = re.compile(rf"<\s*{re.escape(tag)}[^>]*>", re.IGNORECASE)
    escaped = closing_regex.sub(f"&lt;/{tag}&gt;", text)
    return opening_regex.sub(f"&lt;{tag}&gt;", escaped)


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
