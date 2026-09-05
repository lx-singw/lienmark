"""
parallel_client.py

Lienmark Parallel Search API agent integration client.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
from backend.services.parallel_service import ParallelSearchService

__all__ = ["ParallelSearchService"]


def init():
    return ParallelSearchService()

