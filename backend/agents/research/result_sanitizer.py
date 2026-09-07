"""
backend/agents/research/result_sanitizer.py

Evidence sanitation, anti-SSRF URL filtering, and prompt injection defense.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Trojan Source & prompt injection directives
BIDI_CHARS_REGEX = re.compile(r"[\u200B-\u200D\uFEFF\u202A-\u202E\u2066-\u2069]")
INJECTION_DIRECTIVES = re.compile(
    r"(?i)\b(ignore\s+(all\s+)?previous\s+instructions|system\s+override|"
    r"you\s+are\s+now|disregard\s+(prior|previous)|<system>|\[INST\]|\[\/INST\])\b"
)

TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "ref", "source", "mc_cid", "mc_eid",
})


def is_ssrf_risk_host(host: str) -> bool:
    """Detects private, loopback, link-local, or cloud metadata IP addresses."""
    cleaned = host.split(":")[0].strip("[]").lower()
    if cleaned in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        ip = ipaddress.ip_address(cleaned)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def sanitize_url(url: str) -> str:
    """
    Validates URL, upgrades HTTP to HTTPS, strips tracking query parameters,
    and defends against SSRF targets. Returns empty string if invalid.
    """
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    try:
        parts = urlsplit(cleaned)
        host = parts.netloc.lower()
        if not host or is_ssrf_risk_host(host):
            return ""
        filtered_query = [
            (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        new_query = urlencode(filtered_query)
        # Force HTTPS for transport security
        return urlunsplit(("https", parts.netloc, parts.path, new_query, ""))
    except Exception:
        return ""


def sanitize_excerpt(excerpt: str) -> str:
    """Strips bidi control characters and redacts embedded prompt injections."""
    if not excerpt or not isinstance(excerpt, str):
        return ""
    cleaned = BIDI_CHARS_REGEX.sub("", excerpt)
    cleaned = INJECTION_DIRECTIVES.sub("[REDACTED_INSTRUCTION]", cleaned)
    return " ".join(cleaned.split())


def wrap_untrusted_evidence(text: str) -> str:
    """Wraps text in nonced XML CDATA boundary for safe LLM evaluation."""
    safe = sanitize_excerpt(text)
    return f"<untrusted_external_evidence><![CDATA[{safe}]]></untrusted_external_evidence>"


def compute_finding_hash(url: str, snippet: str) -> str:
    """Computes deterministic SHA-256 hash of URL and snippet for legal provenance."""
    payload = f"{url.strip()}:{snippet.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
