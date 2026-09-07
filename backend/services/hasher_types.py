"""
hasher_types.py

Domain enums, Pydantic models, and typed exceptions for streaming cryptographic
and semantic screenplay hashing services in Lienmark.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HashAlgorithm(str, Enum):
    """Supported cryptographic hash algorithms for streaming digests."""

    SHA256 = "sha256"
    BLAKE2B = "blake2b"
    BOTH = "both"


class HashDigestResult(BaseModel):
    """Result of streaming cryptographic digest computation."""

    raw_sha256: str = Field(
        ...,
        description="Hexadecimal SHA-256 digest of raw byte stream",
    )
    raw_blake2b: str = Field(
        ...,
        description="Hexadecimal BLAKE2b digest of raw byte stream",
    )
    semantic_sha256: Optional[str] = Field(
        default=None,
        description="Hexadecimal SHA-256 digest of normalized semantic screenplay text",
    )
    byte_size: int = Field(
        ...,
        ge=0,
        description="Total number of bytes processed in stream",
    )
    chunk_count: int = Field(
        ...,
        ge=0,
        description="Total number of 64KB chunks streamed",
    )


class StreamingHasherError(Exception):
    """Base exception for streaming hasher and normalization operations."""

    pass


class StreamReadError(StreamingHasherError):
    """Raised when an unrecoverable I/O error occurs reading from an input stream."""

    pass


class FileAccessError(StreamingHasherError):
    """Raised when an input file cannot be found, accessed, or read."""

    pass


class NormalizationError(StreamingHasherError):
    """Raised when text normalization or encoding fails unexpectedly."""

    pass
