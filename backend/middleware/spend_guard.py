"""
Lienmark Spend Guard Subsystem
Sprint 6A / Component 2: Application-Level Cost Control & Per-Session Rate Limiting

Protects against runaway costs and protects cold judges from quota exhaustion:
1. Per-session rate limits: max 10 live drift evaluations per session.
2. Environment-wide spend counters: tracks total live API calls made in this environment.
3. Graceful fail-closed behavior: when spend allowance is reached, returns cached/sandbox
   golden fixtures with the explicit underwriter limit message:
   "Spend allowance reached for current period. Running in verified sandbox mode."

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
import uuid
import logging
from typing import Dict, Any, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger("lienmark.spend_guard")

LIMIT_EXCEEDED_MESSAGE: str = "Spend allowance reached for current period. Running in verified sandbox mode."
DEFAULT_MAX_SESSION_DRIFT_EVALUATIONS: int = 10
DEFAULT_MAX_ENVIRONMENT_API_CALLS: int = 100


class SpendGuardManager:
    """
    In-memory Spend Guard ledger tracking per-session drift evaluations
    and environment-wide live API usage counters.
    """

    def __init__(
        self,
        max_session_evaluations: int = DEFAULT_MAX_SESSION_DRIFT_EVALUATIONS,
        max_environment_calls: int = DEFAULT_MAX_ENVIRONMENT_API_CALLS,
    ):
        self.max_session_evaluations = int(
            os.environ.get("SPEND_GUARD_MAX_SESSION_EVALS", max_session_evaluations)
        )
        self.max_environment_calls = int(
            os.environ.get("SPEND_GUARD_MAX_ENV_CALLS", max_environment_calls)
        )
        self._session_evaluations: Dict[str, int] = {}
        self._environment_call_count: int = 0

    @property
    def environment_call_count(self) -> int:
        return self._environment_call_count

    def get_session_evaluations(self, session_id: str) -> int:
        return self._session_evaluations.get(session_id, 0)

    def is_session_limit_reached(self, session_id: str) -> bool:
        return self._session_evaluations.get(session_id, 0) >= self.max_session_evaluations

    def is_environment_limit_reached(self) -> bool:
        return self._environment_call_count >= self.max_environment_calls

    def is_limit_exceeded(self, session_id: str) -> bool:
        return self.is_session_limit_reached(session_id) or self.is_environment_limit_reached()

    def record_drift_evaluation(self, session_id: str) -> Tuple[bool, str]:
        """
        Records a drift evaluation attempt for session_id.
        Returns (allowed, message).
        If allowed is False, limit has been reached and system must run in sandbox mode.
        """
        if self.is_session_limit_reached(session_id):
            logger.warning(
                f"Spend Guard session rate limit reached for {session_id} "
                f"({self._session_evaluations.get(session_id, 0)}/{self.max_session_evaluations}). "
                "Gracefully failing closed to verified sandbox mode."
            )
            return False, LIMIT_EXCEEDED_MESSAGE

        if self.is_environment_limit_reached():
            logger.warning(
                f"Spend Guard environment call cap reached "
                f"({self._environment_call_count}/{self.max_environment_calls}). "
                "Gracefully failing closed to verified sandbox mode."
            )
            return False, LIMIT_EXCEEDED_MESSAGE

        # Increment counters
        self._session_evaluations[session_id] = self._session_evaluations.get(session_id, 0) + 1
        self._environment_call_count += 1
        return True, "OK"

    def record_live_api_call(self, count: int = 1) -> None:
        """Tracks generic external API call in environment spend counter."""
        self._environment_call_count += count

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "max_session_evaluations": self.max_session_evaluations,
            "max_environment_calls": self.max_environment_calls,
            "environment_call_count": self._environment_call_count,
            "active_sessions_tracked": len(self._session_evaluations),
            "limit_message": LIMIT_EXCEEDED_MESSAGE,
        }

    def reset(self) -> None:
        """Resets all session and environment counters."""
        self._session_evaluations.clear()
        self._environment_call_count = 0


spend_guard_manager = SpendGuardManager()


class SpendGuardMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette Middleware enforcing Spend Guard limits.
    1. Extracts or sets session cookie `lienmark_session_id`.
    2. When per-session or environment limit is reached on drift endpoints,
       intercepts and gracefully returns verified golden sandbox fixtures
       with the explicit underwriter limit message without raising 500.
    """

    SESSION_COOKIE_NAME = "lienmark_session_id"
    DRIFT_ENDPOINTS = {"/api/drift/compare", "/api/diff/evaluate"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or issue session id
        is_new_session = False
        session_id = getattr(request.state, "session_id", None)
        if not session_id:
            session_id = request.headers.get("X-Session-ID") or request.headers.get("X-Lienmark-Session-ID")
        if not session_id:
            raw_cookie = request.cookies.get(self.SESSION_COOKIE_NAME)
            if raw_cookie:
                session_id = raw_cookie.split(".")[0]
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            is_new_session = True
        request.state.session_id = session_id

        # Check drift evaluation endpoint rate limiting
        if request.url.path in self.DRIFT_ENDPOINTS and request.method.upper() == "POST":
            # Check spend limit
            allowed, msg = spend_guard_manager.record_drift_evaluation(session_id)
            if not allowed:
                # Graceful fail-closed into verified sandbox mode
                from backend.orchestration.workflow import LienmarkWorkflow
                from backend.services.gemini_service import GeminiService
                from backend.services.parallel_service import ParallelSearchService

                workflow = LienmarkWorkflow(
                    gemini_service=GeminiService(use_fallback=True),
                    parallel_service=ParallelSearchService(use_fallback=True),
                )
                result = await workflow.execute_drift_detection()
                result_data = result.model_dump()
                result_data["spend_guard_status"] = "LIMIT_EXCEEDED"
                result_data["spend_guard_message"] = msg
                result_data["message"] = msg

                resp = JSONResponse(
                    content=result_data,
                    status_code=200,
                    headers={
                        "X-Spend-Guard": "LIMIT_EXCEEDED",
                        "X-Spend-Guard-Fallback": "ACTIVE",
                        "X-Spend-Guard-Message": msg,
                        "X-Session-ID": session_id,
                    },
                )
                if is_new_session:
                    resp.set_cookie(
                        key=self.SESSION_COOKIE_NAME,
                        value=session_id,
                        httponly=True,
                        samesite="lax",
                        path="/",
                    )
                return resp

        response = await call_next(request)
        if is_new_session and self.SESSION_COOKIE_NAME not in response.headers.get("set-cookie", ""):
            response.set_cookie(
                key=self.SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                samesite="lax",
                path="/",
            )
        response.headers["X-Session-ID"] = session_id
        return response
