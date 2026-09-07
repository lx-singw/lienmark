"""
backend/agents/research/parallel_client.py

Lienmark Parallel Search API agent integration client.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from backend.services.parallel_client import ParallelSearchClient
from backend.services.parallel_service import ParallelSearchService

__all__ = ["ParallelSearchClient", "ParallelSearchService", "init"]


def init() -> ParallelSearchClient:
    """Factory creating default ParallelSearchClient."""
    return ParallelSearchClient()
