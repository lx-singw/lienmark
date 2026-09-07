"""
test_hasher_types_and_files.py

Unit tests for HashAlgorithm, HashDigestResult, StreamingHasher file operations,
and exception hierarchies.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError

from backend.services.hasher import StreamingHasher
from backend.services.hasher_types import (
    FileAccessError,
    HashAlgorithm,
    HashDigestResult,
    StreamReadError,
    StreamingHasherError,
)


def test_hash_algorithm_enum_variants() -> None:
    """Verifies HashAlgorithm enum values."""
    assert HashAlgorithm.SHA256.value == "sha256"
    assert HashAlgorithm.BLAKE2B.value == "blake2b"
    assert HashAlgorithm.BOTH.value == "both"


def test_hash_digest_result_model_contract() -> None:
    """Verifies HashDigestResult validation and field constraints."""
    res = HashDigestResult(
        raw_sha256="sha256_hex_value",
        raw_blake2b="blake2b_hex_value",
        byte_size=2048,
        chunk_count=2,
    )
    assert res.semantic_sha256 is None
    assert res.byte_size == 2048
    assert res.chunk_count == 2

    with pytest.raises(ValidationError):
        HashDigestResult(
            raw_sha256="hash",
            raw_blake2b="hash",
            byte_size=-5,
            chunk_count=1,
        )


def test_streaming_hasher_chunk_size_validation() -> None:
    """Verifies ValueError when non-positive chunk_size_bytes is provided."""
    with pytest.raises(ValueError, match="chunk_size_bytes must be > 0"):
        StreamingHasher(chunk_size_bytes=0)
    with pytest.raises(ValueError, match="chunk_size_bytes must be > 0"):
        StreamingHasher(chunk_size_bytes=-1024)


def test_digest_bytes_type_validation() -> None:
    """Verifies TypeError when non-bytes data is passed to digest_bytes."""
    hasher = StreamingHasher()
    with pytest.raises(TypeError, match="data must be bytes or bytearray"):
        hasher.digest_bytes(12345)  # type: ignore[arg-type]


def test_digest_stream_error_handling() -> None:
    """Verifies StreamReadError and StreamingHasherError on stream issues."""
    hasher = StreamingHasher()
    with pytest.raises(StreamingHasherError, match="Stream must be a valid readable"):
        hasher.digest_stream(None)  # type: ignore[arg-type]

    failing_stream = MagicMock()
    failing_stream.read.side_effect = OSError("Read pipe broke")
    with pytest.raises(StreamReadError, match="I/O error during stream read"):
        hasher.digest_stream(failing_stream)


def test_digest_file_operations() -> None:
    """Verifies digest_file on normal file, non-existent path, and directory."""
    hasher = StreamingHasher(chunk_size_bytes=64)
    sample_content = b"Lienmark Version 8 Production Locked Screenplay PDF"

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(sample_content)
        tmp_path = tmp.name

    try:
        res = hasher.digest_file(tmp_path, compute_semantic=False)
        assert res.raw_sha256 == hashlib.sha256(sample_content).hexdigest()
        assert res.byte_size == len(sample_content)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    with pytest.raises(FileAccessError, match="Target file does not exist"):
        hasher.digest_file("/non/existent/screenplay/path.pdf")

    temp_dir = tempfile.gettempdir()
    with pytest.raises(FileAccessError, match="Target path is a directory"):
        hasher.digest_file(temp_dir)
