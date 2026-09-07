"""
readiness.py

FastAPI REST Router for Kubernetes Liveness (/healthz) and Deep Readiness (/readyz).
Sprint 7.3: Staging Deployment, User Acceptance Testing & Operational Cutover.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from fastapi import APIRouter, HTTPException, status

from backend.config.settings import settings
from backend.storage.repository import get_tenant_repository

readiness_router = APIRouter(tags=["health"])

_START_TIME = time.monotonic()


def _check_storage_readiness() -> Tuple[bool, str]:
    """Probes local or cloud tenant storage repository readiness."""
    try:
        repo = get_tenant_repository("org_default")
        if repo is None:
            return False, "Tenant repository failed to initialize"
        if (settings.is_production or settings.is_staging) and type(repo).__name__ == "InMemoryTenantRepository":
            return False, "Production/Staging requires persistent Firestore storage, not in-memory RAM"
        return True, "connected"
    except Exception as exc:
        return False, f"Storage connectivity error: {exc}"


def _check_credentials_readiness() -> Dict[str, str]:
    """Inspects Gemini and Parallel Search configuration state."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    parallel_key = os.getenv("PARALLEL_API_KEY", "")
    vertex_flag = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1", "yes")
    is_gcp = bool(os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT"))

    gemini_ready = "ready" if (gemini_key or vertex_flag or is_gcp or not settings.is_production) else "unconfigured"
    parallel_ready = "ready" if (parallel_key or not settings.is_production) else "unconfigured"
    return {
        "gemini": gemini_ready,
        "parallel_search": parallel_ready,
    }


@readiness_router.get("/healthz")
def liveness_probe() -> Dict[str, Any]:
    """Ultra-lightweight process liveness probe with zero network calls (<5ms)."""
    return {
        "status": "alive",
        "service": "lienmark-clearance-engine",
        "uptime_seconds": round(time.monotonic() - _START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@readiness_router.get("/readyz")
def readiness_probe() -> Dict[str, Any]:
    """Deep readiness probe verifying repository, credentials, and settings (INV-S73-02)."""
    storage_ok, storage_msg = _check_storage_readiness()
    is_ready, validation_issues = settings.validate_production_readiness()
    cred_status = _check_credentials_readiness()
    dependencies = {
        "firestore": "ready" if storage_ok else "unhealthy",
        "settings": "ready" if is_ready else "unhealthy",
        "parallel_search": cred_status.get("parallel_search", "unhealthy"),
        "gemini": cred_status.get("gemini", "unhealthy"),
    }
    failed_reasons: List[str] = list(validation_issues)
    if not storage_ok:
        failed_reasons.append(storage_msg)
    for dep, st in dependencies.items():
        if st in ("unhealthy", "degraded", "failed", "unready", "error"):
            failed_reasons.append(f"Dependency {dep} is {st}")
    if failed_reasons:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "environment": settings.environment,
                "failed_checks": failed_reasons,
                "dependencies": dependencies,
                "checks": dependencies,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return {
        "status": "ready",
        "environment": settings.environment,
        "storage": storage_msg,
        "integrations": cred_status,
        "dependencies": dependencies,
        "checks": dependencies,
        "uptime_seconds": round(time.monotonic() - _START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
