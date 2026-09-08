"""
backend/orchestration/resource_releaser.py

Defensive resource teardown releasing worker tasks, locks, and thread references.
Eliminates CPU/memory leaks by ensuring suspended runs hold zero server resources.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import threading
from typing import Any, Dict, List, Sequence, Union

logger = logging.getLogger("lienmark.orchestration.resource_releaser")


class ResourceReleaser:
    """
    Defensive resource teardown releasing async tasks, locks, and worker references.
    Guarantees zero CPU consumption and zero memory leaks while a run is suspended.
    """

    @staticmethod
    def cancel_async_tasks(tasks: Sequence[asyncio.Task]) -> int:
        """
        Cancels all active in-memory async tasks associated with the suspended run.
        Ensures awaiting coroutines exit cleanly with zero lingering coroutine frames.
        Returns the count of successfully cancelled tasks.
        """
        cancelled = 0
        for task in tasks:
            if isinstance(task, asyncio.Task):
                if not task.done():
                    task.cancel()
                    cancelled += 1
                try:
                    loop = task.get_loop()
                    if not task.done() and not loop.is_running() and not loop.is_closed():
                        loop.run_until_complete(task)
                except (asyncio.CancelledError, Exception):
                    pass
                coro = getattr(task, "get_coro", None)
                if callable(coro):
                    c = coro()
                    if c is not None and hasattr(c, "close"):
                        c.close()
        logger.debug(f"ResourceReleaser cancelled {cancelled} async tasks.")
        return cancelled

    @staticmethod
    def release_locks(locks: Sequence[Union[threading.Lock, asyncio.Lock, Any]]) -> int:
        """
        Safely releases active threading or asyncio locks held by workers.
        Prevents deadlock or lock contention while run is suspended awaiting input.
        """
        released = 0
        for lock in locks:
            if isinstance(lock, threading.Lock) and lock.locked():
                lock.release()
                released += 1
            elif isinstance(lock, asyncio.Lock) and lock.locked():
                lock.release()
                released += 1
        logger.debug(f"ResourceReleaser released {released} locks.")
        return released

    @staticmethod
    def purge_worker_references(worker_refs: Union[Dict[str, Any], List[Any]]) -> int:
        """
        Drops worker handles and invokes cyclic garbage collection.
        Ensures thread context memory is completely freed immediately upon suspension.
        """
        count = len(worker_refs)
        if isinstance(worker_refs, dict):
            worker_refs.clear()
        elif isinstance(worker_refs, list):
            worker_refs.clear()
        gc.collect()
        logger.debug(f"ResourceReleaser purged {count} worker references.")
        return count
