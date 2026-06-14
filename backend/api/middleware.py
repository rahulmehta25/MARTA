"""
Middleware for MARTA API: Rate limiting, CORS, logging.
"""
import time
import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, Optional

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.core.config import settings
from backend.api.core.logging import get_logger, RequestIdMiddleware

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.

    Limits requests per client IP with configurable window and burst.
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        burst_limit: int = 20,
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit
        self._buckets: Dict[str, dict] = defaultdict(
            lambda: {"tokens": burst_limit, "last_update": time.time()}
        )
        self._lock = asyncio.Lock()

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get real IP from proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Check for API key (give separate bucket to authenticated clients)
        api_key = request.headers.get(settings.api_key_header)
        if api_key:
            return f"apikey:{api_key[:16]}"

        return request.client.host if request.client else "unknown"

    async def _check_rate_limit(self, client_id: str) -> tuple[bool, dict]:
        """Check if request is within rate limit."""
        async with self._lock:
            now = time.time()
            bucket = self._buckets[client_id]

            # Refill tokens based on time elapsed
            elapsed = now - bucket["last_update"]
            refill_rate = self.requests_per_window / self.window_seconds
            new_tokens = min(
                self.burst_limit,
                bucket["tokens"] + elapsed * refill_rate
            )
            bucket["tokens"] = new_tokens
            bucket["last_update"] = now

            # Check if request can proceed
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True, {
                    "remaining": int(bucket["tokens"]),
                    "limit": self.requests_per_window,
                    "reset": int(now + self.window_seconds),
                }
            else:
                retry_after = (1 - bucket["tokens"]) / refill_rate
                return False, {
                    "remaining": 0,
                    "limit": self.requests_per_window,
                    "reset": int(now + retry_after),
                    "retry_after": int(retry_after) + 1,
                }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/live", "/health/ready"]:
            return await call_next(request)

        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_id = self._get_client_id(request)
        allowed, info = await self._check_rate_limit(client_id)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=request.url.path,
            )
            response = Response(
                content='{"detail": "Rate limit exceeded. Please slow down."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
            )
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
            response.headers["Retry-After"] = str(info["retry_after"])
            return response

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client=request.client.host if request.client else None,
        )

        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""

    # CORS middleware (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Response-Time",
        ],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID tracking
    app.add_middleware(RequestIdMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_window=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            burst_limit=settings.rate_limit_burst,
        )

    logger.info("Middleware configured")
