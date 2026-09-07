"""
hasher.py

Memory-bounded streaming chunk hasher and screenplay semantic normalizer.
Computes SHA-256 and BLAKE2b digests across arbitrary data streams with $O(1)$ memory.
"""

from __future__ import annotations

import codecs
import hashlib
import io
import os
from typing import BinaryIO, Iterator, Optional

from backend.services.hasher_types import (
    FileAccessError,
    HashDigestResult,
    StreamReadError,
    StreamingHasherError,
)
from backend.services.screenplay_normalizer import (
    normalize_screenplay_stream,
    normalize_screenplay_text as _normalize_text,
)


class StreamingHasher:
    """
    High-performance memory-bounded streaming hasher.
    Reads streams in 64KB chunks to guarantee strictly O(1) memory overhead.
    """

    DEFAULT_CHUNK_SIZE_BYTES: int = 65536  # 64 KB

    def __init__(self, chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES) -> None:
        if chunk_size_bytes <= 0:
            raise ValueError(f"chunk_size_bytes must be > 0, got {chunk_size_bytes}")
        self.chunk_size_bytes = chunk_size_bytes

    def _read_raw_chunks(
        self,
        stream: BinaryIO,
        sha256_hasher: hashlib._Hash,
        blake2b_hasher: hashlib._Hash,
    ) -> tuple[int, int]:
        """Reads raw chunks, updating raw hashes with O(1) memory."""
        byte_size = 0
        chunk_count = 0
        while True:
            try:
                chunk = stream.read(self.chunk_size_bytes)
            except OSError as err:
                raise StreamReadError(f"I/O error during stream read: {err}") from err
            if not chunk:
                break
            byte_size += len(chunk)
            chunk_count += 1
            sha256_hasher.update(chunk)
            blake2b_hasher.update(chunk)
        return byte_size, chunk_count

    def _stream_lines_and_hash(
        self,
        stream: BinaryIO,
        sha256_hasher: hashlib._Hash,
        blake2b_hasher: hashlib._Hash,
        stats: list[int],
    ) -> Iterator[str]:
        """Generator yielding decoded lines while updating raw hash states."""
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        buffer = ""
        while True:
            try:
                chunk = stream.read(self.chunk_size_bytes)
            except OSError as err:
                raise StreamReadError(f"I/O error during stream read: {err}") from err
            if not chunk:
                break
            stats[0] += len(chunk)
            stats[1] += 1
            sha256_hasher.update(chunk)
            blake2b_hasher.update(chunk)
            text = decoder.decode(chunk, final=False)
            buffer += text
            lines = buffer.split("\n")
            for line in lines[:-1]:
                yield line
            buffer = lines[-1]
        buffer += decoder.decode(b"", final=True)
        if buffer:
            for line in buffer.split("\n"):
                yield line

    def _consume_semantic_stream(
        self,
        stream: BinaryIO,
        sha256_hasher: hashlib._Hash,
        blake2b_hasher: hashlib._Hash,
    ) -> tuple[int, int, str]:
        """Consumes stream in single pass, computing raw and semantic hashes."""
        stats = [0, 0]  # [byte_size, chunk_count]
        semantic_hasher = hashlib.sha256()
        line_iter = self._stream_lines_and_hash(
            stream, sha256_hasher, blake2b_hasher, stats
        )
        is_first = True
        for norm_line in normalize_screenplay_stream(line_iter):
            if is_first:
                semantic_hasher.update(norm_line.encode("utf-8"))
                is_first = False
            else:
                semantic_hasher.update(f"\n{norm_line}".encode("utf-8"))
        return stats[0], stats[1], semantic_hasher.hexdigest()

    def digest_stream(
        self,
        stream: BinaryIO,
        compute_semantic: bool = False,
        file_extension: Optional[str] = None,
    ) -> HashDigestResult:
        """
        Streams binary data in 64KB chunks, computing SHA-256 and BLAKE2b digests.
        Memory footprint is strictly O(1) throughout stream lifecycle.
        """
        if stream is None or not hasattr(stream, "read"):
            raise StreamingHasherError("Stream must be a valid readable BinaryIO object")

        sha256_hasher = hashlib.sha256()
        blake2b_hasher = hashlib.blake2b()

        if compute_semantic:
            byte_size, chunk_count, semantic_sha = self._consume_semantic_stream(
                stream, sha256_hasher, blake2b_hasher
            )
            return HashDigestResult(
                raw_sha256=sha256_hasher.hexdigest(),
                raw_blake2b=blake2b_hasher.hexdigest(),
                semantic_sha256=semantic_sha,
                byte_size=byte_size,
                chunk_count=chunk_count,
            )

        byte_size, chunk_count = self._read_raw_chunks(
            stream, sha256_hasher, blake2b_hasher
        )
        return HashDigestResult(
            raw_sha256=sha256_hasher.hexdigest(),
            raw_blake2b=blake2b_hasher.hexdigest(),
            semantic_sha256=None,
            byte_size=byte_size,
            chunk_count=chunk_count,
        )

    def digest_bytes(
        self,
        data: bytes,
        compute_semantic: bool = False,
    ) -> HashDigestResult:
        """Computes hash digest result for in-memory byte buffer."""
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(f"data must be bytes or bytearray, got {type(data).__name__}")
        stream = io.BytesIO(data)
        return self.digest_stream(stream, compute_semantic=compute_semantic)

    def digest_file(
        self,
        file_path: str,
        compute_semantic: bool = False,
    ) -> HashDigestResult:
        """Streams and hashes local filesystem file with O(1) memory bound."""
        if not os.path.exists(file_path):
            raise FileAccessError(f"Target file does not exist: {file_path}")
        if os.path.isdir(file_path):
            raise FileAccessError(f"Target path is a directory: {file_path}")

        _, ext = os.path.splitext(file_path)
        try:
            with open(file_path, "rb") as file_stream:
                return self.digest_stream(
                    file_stream,
                    compute_semantic=compute_semantic,
                    file_extension=ext,
                )
        except OSError as err:
            raise FileAccessError(f"Failed opening file {file_path}: {err}") from err

    @staticmethod
    def normalize_screenplay_text(text: str) -> str:
        """Normalizes whitespace, casing, metadata timestamps, and dialogue blocks."""
        return _normalize_text(text)

    @staticmethod
    def compute_semantic_digest(raw_text: str) -> str:
        """Returns SHA-256 hex digest of normalized screenplay text stream."""
        normalized = _normalize_text(raw_text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# Module-level aliases for direct function imports
normalize_screenplay_text = StreamingHasher.normalize_screenplay_text
compute_semantic_digest = StreamingHasher.compute_semantic_digest
