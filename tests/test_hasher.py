"""
test_hasher.py

Comprehensive test suite for StreamingHasher and screenplay semantic normalizer.
Validates O(1) memory chunk streaming, multi-hash single-pass accuracy,
and rename/metadata invariance under Google AntiGravity architectural rules.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
from typing import BinaryIO, Iterator, List
import pytest

from backend.services.hasher import StreamingHasher
from backend.services.hasher_types import (
    FileAccessError,
    HashAlgorithm,
    HashDigestResult,
    StreamReadError,
    StreamingHasherError,
)
from backend.services.screenplay_normalizer import normalize_screenplay_text


class TrackingChunkStream(io.BytesIO):
    """Monitors chunk read sizes to verify bounded O(1) memory chunking."""

    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.chunk_sizes: List[int] = []

    def read(self, size: int = -1) -> bytes:
        chunk = super().read(size)
        if chunk:
            self.chunk_sizes.append(len(chunk))
        return chunk


class NonSeekableStream(io.RawIOBase):
    """Strictly forward-only stream verifying single-pass calculation without rewind."""

    def __init__(self, data: bytes) -> None:
        super().__init__()
        self._data = data
        self._pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        raise io.UnsupportedOperation("Stream does not support seek operations")

    def readinto(self, b: bytearray) -> int:
        if self._pos >= len(self._data):
            return 0
        end = min(self._pos + len(b), len(self._data))
        n = end - self._pos
        b[:n] = self._data[self._pos:end]
        self._pos = end
        return n


def test_streaming_chunk_digest_matches_hashlib_small_file() -> None:
    """Verifies 64KB chunk digest matches standard hashlib for small (<64KB) payload."""
    payload = b"Scene 1: Detective office encounter\n" * 200  # ~7.2 KB
    assert len(payload) < 65536

    hasher = StreamingHasher(chunk_size_bytes=65536)
    result = hasher.digest_bytes(payload, compute_semantic=False)

    expected_sha = hashlib.sha256(payload).hexdigest()
    expected_blake = hashlib.blake2b(payload).hexdigest()

    assert result.raw_sha256 == expected_sha
    assert result.raw_blake2b == expected_blake
    assert result.byte_size == len(payload)
    assert result.chunk_count == 1
    assert result.semantic_sha256 is None


def test_streaming_chunk_digest_matches_hashlib_large_file() -> None:
    """Verifies 64KB chunk digest matches standard hashlib for large (>1MB) payload."""
    chunk_unit = b"Lienmark Verifiable Provenance Ledger Block Data 2026\n" * 128  # ~6.9 KB
    repeats = (1024 * 1024 // len(chunk_unit)) + 80
    large_payload = chunk_unit * repeats
    assert len(large_payload) > 1024 * 1024  # > 1MB

    hasher = StreamingHasher(chunk_size_bytes=65536)
    result = hasher.digest_stream(io.BytesIO(large_payload), compute_semantic=False)

    expected_sha = hashlib.sha256(large_payload).hexdigest()
    expected_blake = hashlib.blake2b(large_payload).hexdigest()

    assert result.raw_sha256 == expected_sha
    assert result.raw_blake2b == expected_blake
    assert result.byte_size == len(large_payload)
    expected_chunks = (len(large_payload) + 65535) // 65536
    assert result.chunk_count == expected_chunks


def test_hasher_memory_invariance_o1_chunk_bounds() -> None:
    """Verifies that chunks read never exceed chunk_size_bytes, guaranteeing O(1) memory."""
    payload = b"A" * (200 * 1024)  # 200 KB
    stream = TrackingChunkStream(payload)
    hasher = StreamingHasher(chunk_size_bytes=65536)

    result = hasher.digest_stream(stream, compute_semantic=False)

    assert result.byte_size == len(payload)
    assert len(stream.chunk_sizes) == 4  # 64KB + 64KB + 64KB + 8KB
    for size in stream.chunk_sizes:
        assert size <= 65536


def test_sha256_and_blake2b_simultaneous_single_pass() -> None:
    """Verifies simultaneous computation in a single pass on non-seekable streams."""
    payload = b"INT. VAULT - NIGHT\nThe dual cryptographic keys are synchronized."
    stream = NonSeekableStream(payload)
    hasher = StreamingHasher(chunk_size_bytes=32)

    result = hasher.digest_stream(stream, compute_semantic=True)

    expected_sha = hashlib.sha256(payload).hexdigest()
    expected_blake = hashlib.blake2b(payload).hexdigest()

    assert result.raw_sha256 == expected_sha
    assert result.raw_blake2b == expected_blake
    assert result.semantic_sha256 is not None
    assert len(result.semantic_sha256) == 64


def test_normalize_screenplay_text_rules() -> None:
    """Verifies whitespace, character cues, and metadata stripping rules."""
    raw_script = """
%PDF-1.4
/CreationDate (D:20260907090955Z)
Draft Date: 2026-09-07
Page 1 of 120

SCENE 1 - INT. DETECTIVE OFFICE - NIGHT
09:15 AM
The rain falls.

SARAH (CONT'D)
We located the title deed.
    """
    normalized = normalize_screenplay_text(raw_script)

    assert "pdf-1.4" not in normalized
    assert "creationdate" not in normalized
    assert "2026-09-07" not in normalized
    assert "page 1" not in normalized
    assert "09:15" not in normalized
    assert "scene 1 - int. detective office - night" in normalized
    assert "sarah: we located the title deed." in normalized


def test_semantic_hash_equivalence_pdf_timestamp_delta() -> None:
    """Verifies scripts differing only in PDF timestamps produce identical semantic hashes."""
    script_v1 = (
        "%PDF-1.4\n"
        "/CreationDate (D:20260101120000Z)\n"
        "Page 1\n"
        "INT. OFFICE - DAY\n\n"
        "SARAH\n"
        "We verified the title records.\n"
    )
    script_v2 = (
        "%PDF-1.7\n"
        "/CreationDate (D:20260907090955Z)\n"
        "Page 1\n"
        "INT. OFFICE - DAY\n\n"
        "SARAH (cont'd)\n"
        "We verified the title records.\n"
    )
    hasher = StreamingHasher(chunk_size_bytes=64)
    res1 = hasher.digest_bytes(script_v1.encode("utf-8"), compute_semantic=True)
    res2 = hasher.digest_bytes(script_v2.encode("utf-8"), compute_semantic=True)

    assert res1.raw_sha256 != res2.raw_sha256
    assert res1.raw_blake2b != res2.raw_blake2b
    assert res1.semantic_sha256 is not None
    assert res1.semantic_sha256 == res2.semantic_sha256
