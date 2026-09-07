"""
test_hasher_normalization.py

Unit tests for screenplay normalization and semantic hashing.
Verifies metadata timestamp stripping, dialogue block normalization,
and semantic hash stability across screenplay re-saving and formatting shifts.
"""

from __future__ import annotations

import io
from backend.services.hasher import StreamingHasher
from backend.services.screenplay_normalizer import (
    normalize_screenplay_text,
    normalize_screenplay_stream,
)


def test_timestamp_and_metadata_stripping() -> None:
    """Verifies that ISO dates, clock times, PDF headers, and page numbers are stripped."""
    raw_script = """
%PDF-1.4
/CreationDate (D:20260907090954+02'00')
Draft Date: 2026-09-07
Page 1 of 120

SCENE 1 - INT. DETECTIVE OFFICE - NIGHT
09:15 AM
The clock ticks loudly.
    """
    normalized = normalize_screenplay_text(raw_script)
    assert "pdf-1.4" not in normalized
    assert "creationdate" not in normalized
    assert "2026-09-07" not in normalized
    assert "page 1" not in normalized
    assert "09:15" not in normalized
    assert "scene 1 - int. detective office - night" in normalized
    assert "the clock ticks loudly." in normalized


def test_dialogue_block_and_cont_normalization() -> None:
    """Verifies dialogue wrapping, CONT'D stripping, and colon normalization."""
    script_a = """
MILLER
I told you yesterday that we
cannot accept the settlement.
    """
    script_b = """
MILLER: (CONT'D)
I told you yesterday that we cannot accept the settlement.
    """
    norm_a = normalize_screenplay_text(script_a)
    norm_b = normalize_screenplay_text(script_b)

    expected = "miller: i told you yesterday that we cannot accept the settlement."
    assert norm_a == expected
    assert norm_b == expected
    assert norm_a == norm_b


def test_semantic_digest_invariance_on_resave() -> None:
    """
    Verifies that re-saving a script with different margins, blank lines,
    added export metadata, and altered casing produces an IDENTICAL semantic hash,
    while raw SHA-256 and BLAKE2b hashes differ.
    """
    hasher = StreamingHasher(chunk_size_bytes=64)

    original_script = """
SCENE 42 - INT. DETECTIVE OFFICE - NIGHT

MILLER
We received the subpoena this morning.
Check the vintage telephone records.

HARRIS
(quietly)
The line was severed at midnight.
    """

    resaved_script = """
Draft: September 7, 2026
Page 42

SCENE 42 - INT. DETECTIVE OFFICE - NIGHT

MILLER (CONT'D):
We received the subpoena this morning. Check
the vintage telephone records.


HARRIS
(quietly)
The line was severed at midnight.
/ModDate (D:20260907101500)
    """

    res_orig = hasher.digest_bytes(original_script.encode("utf-8"), compute_semantic=True)
    res_resaved = hasher.digest_bytes(resaved_script.encode("utf-8"), compute_semantic=True)

    # Raw bytes are physically different
    assert res_orig.raw_sha256 != res_resaved.raw_sha256
    assert res_orig.raw_blake2b != res_resaved.raw_blake2b

    # Semantic hashes MUST be identical
    assert res_orig.semantic_sha256 is not None
    assert res_orig.semantic_sha256 == res_resaved.semantic_sha256


def test_semantic_digest_changes_on_text_alteration() -> None:
    """Verifies that altering dialogue text produces a different semantic hash."""
    hasher = StreamingHasher()

    script_baseline = """
MILLER
We cannot accept the settlement terms.
    """
    script_altered = """
MILLER
We WILL accept the settlement terms.
    """

    res_base = hasher.digest_bytes(script_baseline.encode("utf-8"), compute_semantic=True)
    res_alt = hasher.digest_bytes(script_altered.encode("utf-8"), compute_semantic=True)

    assert res_base.semantic_sha256 != res_alt.semantic_sha256


def test_stream_and_string_digest_parity() -> None:
    """Verifies streaming digest matches compute_semantic_digest bit-for-bit."""
    hasher = StreamingHasher(chunk_size_bytes=16)

    text = """
SCENE 10 - EXT. ALLEY - DAWN

MILLER
The trail ends here.
    """
    semantic_from_text = hasher.compute_semantic_digest(text)
    stream_res = hasher.digest_stream(
        io.BytesIO(text.encode("utf-8")),
        compute_semantic=True,
    )

    assert stream_res.semantic_sha256 == semantic_from_text
