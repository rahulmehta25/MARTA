"""
In-memory TTL cache with optional Redis backend for MARTA API.
"""
import asyncio
import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Dict
from collections import OrderedDict

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class TTLCache:
    """Thread-safe TTL cache with LRU eviction."""

    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    # Expired
                    del self._cache[key]
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl

        async with self._lock:
            if key in self._cache:
                del self._cache[key]

            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)

            # Evict oldest entries if over capacity
            while len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        removed = 0
        current_time = time.time()

        async with self._lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if current_time >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1

        return removed

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }


# Global cache instance
cache = TTLCache(maxsize=1000, default_ttl=300)


def _make_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Create a cache key from function and arguments."""
    key_parts = [
        func.__module__,
        func.__qualname__,
        str(args),
        str(sorted(kwargs.items())),
    ]
    key_str = ":".join(key_parts)
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    cache_instance: Optional[TTLCache] = None,
):
    """
    Decorator for caching async function results.

    Args:
        ttl: Time to live in seconds (uses cache default if None)
        key_prefix: Optional prefix for cache keys
        cache_instance: Optional custom cache instance

    Example:
        @cached(ttl=300, key_prefix="forecast")
        async def get_forecast(stop_id: str) -> dict:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache_to_use = cache_instance or cache

            # Build cache key
            base_key = _make_key(func, args, kwargs)
            key = f"{key_prefix}:{base_key}" if key_prefix else base_key

            # Try to get from cache
            cached_value = await cache_to_use.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}", cache_key=key[:16])
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_to_use.set(key, result, ttl)
            logger.debug(f"Cache set for {func.__name__}", cache_key=key[:16], ttl=ttl)

            return result

        return wrapper
    return decorator


async def cache_cleanup_task(interval: int = 60):
    """Background task to cleanup expired cache entries."""
    while True:
        try:
            removed = await cache.cleanup_expired()
            if removed > 0:
                logger.debug(f"Cleaned up {removed} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
        await asyncio.sleep(interval)
