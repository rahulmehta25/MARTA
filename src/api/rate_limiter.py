# src/api/rate_limiter.py

import time
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import hashlib
import logging
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import json

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiting implementation with multiple strategies.
    """

    def __init__(self,
                 requests_per_minute: int = 60,
                 requests_per_hour: int = 1000,
                 requests_per_day: int = 10000,
                 use_redis: bool = False,
                 redis_url: str = None):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.use_redis = use_redis

        # In-memory storage (for development/single instance)
        self.requests = defaultdict(deque)
        self.blocked_ips = set()
        self.api_key_limits = {}

        # Redis client (for production/multi-instance)
        self.redis_client = None
        if use_redis and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis connection established for rate limiting")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.use_redis = False

    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier from request.
        """
        # Priority: API Key > User ID > IP Address
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key}"

        # Check for authenticated user
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host

        return f"ip:{client_ip}"

    def _get_limits(self, client_id: str) -> Tuple[int, int, int]:
        """
        Get rate limits for specific client.
        """
        # Check for custom API key limits
        if client_id.startswith("api:"):
            api_key = client_id[4:]
            if api_key in self.api_key_limits:
                return self.api_key_limits[api_key]

        # Default limits
        return (
            self.requests_per_minute,
            self.requests_per_hour,
            self.requests_per_day
        )

    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """
        Check if request should be rate limited.

        Returns:
            Tuple of (is_allowed, limit_info)
        """
        client_id = self._get_client_id(request)
        endpoint = request.url.path
        method = request.method

        # Check if client is blocked
        if client_id in self.blocked_ips:
            return False, {"reason": "Client is blocked"}

        # Get limits for this client
        limit_minute, limit_hour, limit_day = self._get_limits(client_id)

        if self.use_redis and self.redis_client:
            return await self._check_redis_limit(
                client_id, endpoint, limit_minute, limit_hour, limit_day
            )
        else:
            return self._check_memory_limit(
                client_id, endpoint, limit_minute, limit_hour, limit_day
            )

    def _check_memory_limit(self,
                           client_id: str,
                           endpoint: str,
                           limit_minute: int,
                           limit_hour: int,
                           limit_day: int) -> Tuple[bool, Dict]:
        """
        Check rate limit using in-memory storage.
        """
        now = time.time()
        request_times = self.requests[client_id]

        # Remove old requests
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        # Clean up old entries
        while request_times and request_times[0] < day_ago:
            request_times.popleft()

        # Count requests in different time windows
        minute_count = sum(1 for t in request_times if t > minute_ago)
        hour_count = sum(1 for t in request_times if t > hour_ago)
        day_count = len(request_times)

        # Check limits
        if minute_count >= limit_minute:
            return False, {
                "reason": "Minute rate limit exceeded",
                "limit": limit_minute,
                "reset_in": 60 - (now - request_times[-limit_minute])
            }

        if hour_count >= limit_hour:
            return False, {
                "reason": "Hourly rate limit exceeded",
                "limit": limit_hour,
                "reset_in": 3600 - (now - request_times[-limit_hour])
            }

        if day_count >= limit_day:
            return False, {
                "reason": "Daily rate limit exceeded",
                "limit": limit_day,
                "reset_in": 86400 - (now - request_times[-limit_day])
            }

        # Add current request
        request_times.append(now)

        return True, {
            "minute_remaining": limit_minute - minute_count - 1,
            "hour_remaining": limit_hour - hour_count - 1,
            "day_remaining": limit_day - day_count - 1
        }

    async def _check_redis_limit(self,
                                client_id: str,
                                endpoint: str,
                                limit_minute: int,
                                limit_hour: int,
                                limit_day: int) -> Tuple[bool, Dict]:
        """
        Check rate limit using Redis.
        """
        now = int(time.time())
        pipe = self.redis_client.pipeline()

        # Keys for different time windows
        minute_key = f"rate:{client_id}:minute:{now // 60}"
        hour_key = f"rate:{client_id}:hour:{now // 3600}"
        day_key = f"rate:{client_id}:day:{now // 86400}"

        # Increment counters
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)

        results = pipe.execute()

        minute_count = results[0]
        hour_count = results[2]
        day_count = results[4]

        # Check limits
        if minute_count > limit_minute:
            return False, {
                "reason": "Minute rate limit exceeded",
                "limit": limit_minute,
                "reset_in": 60 - (now % 60)
            }

        if hour_count > limit_hour:
            return False, {
                "reason": "Hourly rate limit exceeded",
                "limit": limit_hour,
                "reset_in": 3600 - (now % 3600)
            }

        if day_count > limit_day:
            return False, {
                "reason": "Daily rate limit exceeded",
                "limit": limit_day,
                "reset_in": 86400 - (now % 86400)
            }

        return True, {
            "minute_remaining": limit_minute - minute_count,
            "hour_remaining": limit_hour - hour_count,
            "day_remaining": limit_day - day_count
        }

    def block_client(self, client_id: str, duration_seconds: int = 3600):
        """
        Temporarily block a client.
        """
        self.blocked_ips.add(client_id)
        logger.warning(f"Client {client_id} blocked for {duration_seconds} seconds")

        # Schedule unblock
        asyncio.create_task(self._unblock_after_delay(client_id, duration_seconds))

    async def _unblock_after_delay(self, client_id: str, delay: int):
        """
        Unblock client after delay.
        """
        await asyncio.sleep(delay)
        self.blocked_ips.discard(client_id)
        logger.info(f"Client {client_id} unblocked")

    def set_api_key_limits(self, api_key: str, per_minute: int, per_hour: int, per_day: int):
        """
        Set custom limits for API key.
        """
        self.api_key_limits[api_key] = (per_minute, per_hour, per_day)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        """
        # Skip rate limiting for certain paths
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
        if request.url.path in skip_paths:
            return await call_next(request)

        # Check rate limit
        allowed, limit_info = await self.rate_limiter.check_rate_limit(request)

        if not allowed:
            # Log rate limit violation
            client_id = self.rate_limiter._get_client_id(request)
            logger.warning(f"Rate limit exceeded for {client_id}: {limit_info}")

            # Return 429 response
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": limit_info.get("reason", "Too many requests"),
                    "retry_after": limit_info.get("reset_in", 60)
                },
                headers={
                    "X-RateLimit-Limit": str(limit_info.get("limit", 60)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + limit_info.get("reset_in", 60))),
                    "Retry-After": str(int(limit_info.get("reset_in", 60)))
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Minute-Remaining"] = str(limit_info.get("minute_remaining", 0))
        response.headers["X-RateLimit-Hour-Remaining"] = str(limit_info.get("hour_remaining", 0))
        response.headers["X-RateLimit-Day-Remaining"] = str(limit_info.get("day_remaining", 0))

        return response


class EndpointRateLimiter:
    """
    Decorator for endpoint-specific rate limiting.
    """

    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(deque)

    def __call__(self, func):
        """
        Decorate endpoint function.
        """
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier
            client_ip = request.client.host
            endpoint = request.url.path
            key = f"{client_ip}:{endpoint}"

            # Check rate limit
            now = time.time()
            minute_ago = now - 60

            # Clean old requests
            while self.requests[key] and self.requests[key][0] < minute_ago:
                self.requests[key].popleft()

            # Check limit
            if len(self.requests[key]) >= self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute for this endpoint."
                )

            # Record request
            self.requests[key].append(now)

            # Execute function
            return await func(request, *args, **kwargs)

        return wrapper


# Utility functions for rate limit management
def create_rate_limiter(config: Dict[str, Any]) -> RateLimiter:
    """
    Create rate limiter from configuration.
    """
    return RateLimiter(
        requests_per_minute=config.get("requests_per_minute", 60),
        requests_per_hour=config.get("requests_per_hour", 1000),
        requests_per_day=config.get("requests_per_day", 10000),
        use_redis=config.get("use_redis", False),
        redis_url=config.get("redis_url")
    )


def get_rate_limit_config() -> Dict[str, Any]:
    """
    Get rate limit configuration from environment.
    """
    import os

    return {
        "requests_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        "requests_per_hour": int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
        "requests_per_day": int(os.getenv("RATE_LIMIT_PER_DAY", "10000")),
        "use_redis": os.getenv("REDIS_HOST") is not None,
        "redis_url": os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379/0")
    }


# Example usage in FastAPI app
if __name__ == "__main__":
    from fastapi import FastAPI

    app = FastAPI()

    # Create rate limiter
    config = get_rate_limit_config()
    rate_limiter = create_rate_limiter(config)

    # Add middleware
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

    # Endpoint with custom rate limit
    endpoint_limiter = EndpointRateLimiter(requests_per_minute=5)

    @app.get("/api/expensive-operation")
    @endpoint_limiter
    async def expensive_operation(request: Request):
        return {"message": "This endpoint has stricter rate limits"}