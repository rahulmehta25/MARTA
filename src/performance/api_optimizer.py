"""
MARTA Platform - API Performance Optimizer
Implements pagination, lazy loading, request batching, debouncing, and rate limiting
"""
import asyncio
import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from functools import wraps
from collections import defaultdict, deque
import logging
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Request, Response, Query, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
import aioredis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("asc", regex="^(asc|desc)$", description="Sort order")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
        
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel):
    """Standard paginated response"""
    data: List[Any]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int]
    previous_page: Optional[int]


class BatchRequest(BaseModel):
    """Batch request model"""
    requests: List[Dict[str, Any]]
    parallel: bool = True
    continue_on_error: bool = True


class BatchResponse(BaseModel):
    """Batch response model"""
    responses: List[Dict[str, Any]]
    errors: List[Optional[str]]
    execution_time: float
    successful: int
    failed: int


class RateLimitConfig:
    """Rate limiting configuration"""
    def __init__(
        self,
        requests_per_second: int = 100,
        requests_per_minute: int = 1000,
        requests_per_hour: int = 10000,
        burst_size: int = 20
    ):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size


class APIOptimizer:
    """Main API optimization manager"""
    
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis_client = redis_client
        self.request_batches = defaultdict(list)
        self.batch_timers = {}
        self.rate_limiters = {}
        self.debounce_timers = {}
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'batched_requests': 0,
            'cached_responses': 0,
            'rate_limited_requests': 0,
            'paginated_requests': 0
        }
        
    async def paginate_query(
        self,
        query_func: Callable,
        params: PaginationParams,
        count_func: Optional[Callable] = None
    ) -> PaginatedResponse:
        """Apply pagination to a database query"""
        start_time = time.time()
        
        # Get total count
        if count_func:
            total_items = await count_func()
        else:
            # Estimate if count not provided
            total_items = 10000
            
        # Calculate pages
        total_pages = (total_items + params.page_size - 1) // params.page_size
        
        # Execute paginated query
        data = await query_func(
            offset=params.offset,
            limit=params.limit,
            sort_by=params.sort_by,
            sort_order=params.sort_order
        )
        
        # Update stats
        self.stats['paginated_requests'] += 1
        
        return PaginatedResponse(
            data=data,
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
            next_page=params.page + 1 if params.page < total_pages else None,
            previous_page=params.page - 1 if params.page > 1 else None
        )
        
    async def cursor_paginate(
        self,
        query_func: Callable,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Cursor-based pagination for real-time data"""
        # Decode cursor
        if cursor:
            try:
                cursor_data = json.loads(
                    base64.b64decode(cursor).decode('utf-8')
                )
                last_id = cursor_data.get('last_id')
                last_timestamp = cursor_data.get('last_timestamp')
            except:
                last_id = None
                last_timestamp = None
        else:
            last_id = None
            last_timestamp = None
            
        # Execute query with cursor
        data = await query_func(
            last_id=last_id,
            last_timestamp=last_timestamp,
            limit=limit + 1  # Get one extra to check if there's more
        )
        
        # Check if there's more data
        has_more = len(data) > limit
        if has_more:
            data = data[:limit]
            
        # Generate next cursor
        next_cursor = None
        if data and has_more:
            import base64
            last_item = data[-1]
            cursor_data = {
                'last_id': last_item.get('id'),
                'last_timestamp': last_item.get('timestamp')
            }
            next_cursor = base64.b64encode(
                json.dumps(cursor_data).encode('utf-8')
            ).decode('utf-8')
            
        return {
            'data': data,
            'cursor': next_cursor,
            'has_more': has_more
        }
        
    async def batch_requests(
        self,
        batch_request: BatchRequest,
        execute_func: Callable
    ) -> BatchResponse:
        """Process batched requests"""
        start_time = time.time()
        responses = []
        errors = []
        
        if batch_request.parallel:
            # Execute requests in parallel
            tasks = []
            for req in batch_request.requests:
                task = asyncio.create_task(self._execute_single_request(
                    req, execute_func, batch_request.continue_on_error
                ))
                tasks.append(task)
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    responses.append(None)
                    errors.append(str(result))
                else:
                    responses.append(result)
                    errors.append(None)
        else:
            # Execute requests sequentially
            for req in batch_request.requests:
                try:
                    result = await self._execute_single_request(
                        req, execute_func, batch_request.continue_on_error
                    )
                    responses.append(result)
                    errors.append(None)
                except Exception as e:
                    if not batch_request.continue_on_error:
                        raise
                    responses.append(None)
                    errors.append(str(e))
                    
        # Update stats
        self.stats['batched_requests'] += len(batch_request.requests)
        
        execution_time = time.time() - start_time
        successful = sum(1 for e in errors if e is None)
        failed = len(errors) - successful
        
        return BatchResponse(
            responses=responses,
            errors=errors,
            execution_time=execution_time,
            successful=successful,
            failed=failed
        )
        
    async def _execute_single_request(
        self,
        request: Dict[str, Any],
        execute_func: Callable,
        continue_on_error: bool
    ) -> Any:
        """Execute a single request from a batch"""
        try:
            return await execute_func(request)
        except Exception as e:
            if not continue_on_error:
                raise
            logger.error(f"Batch request failed: {e}")
            raise
            
    def debounce(
        self,
        key: str,
        func: Callable,
        delay: float = 0.5
    ):
        """Debounce function calls"""
        # Cancel existing timer
        if key in self.debounce_timers:
            self.debounce_timers[key].cancel()
            
        # Create new timer
        async def delayed_execution():
            await asyncio.sleep(delay)
            await func()
            del self.debounce_timers[key]
            
        task = asyncio.create_task(delayed_execution())
        self.debounce_timers[key] = task
        
    def throttle(
        self,
        key: str,
        func: Callable,
        min_interval: float = 1.0
    ):
        """Throttle function calls"""
        current_time = time.time()
        
        if key not in self._last_execution:
            self._last_execution[key] = 0
            
        if current_time - self._last_execution[key] >= min_interval:
            self._last_execution[key] = current_time
            return func()
        return None
        
    async def lazy_load(
        self,
        data_generator: Callable,
        chunk_size: int = 100
    ):
        """Lazy load data in chunks"""
        async for chunk in self._chunk_generator(data_generator, chunk_size):
            yield chunk
            
    async def _chunk_generator(self, data_generator, chunk_size):
        """Generate data in chunks"""
        chunk = []
        async for item in data_generator():
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
            
    async def stream_response(
        self,
        data_generator: Callable,
        content_type: str = "application/json"
    ) -> StreamingResponse:
        """Stream large responses"""
        async def generate():
            yield b'{"data": ['
            first = True
            
            async for item in data_generator():
                if not first:
                    yield b','
                first = False
                yield json.dumps(item).encode('utf-8')
                
            yield b']}'
            
        return StreamingResponse(
            generate(),
            media_type=content_type
        )


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, config: RateLimitConfig, redis_client: Optional[aioredis.Redis] = None):
        self.config = config
        self.redis_client = redis_client
        self.local_buckets = defaultdict(lambda: {
            'tokens': config.burst_size,
            'last_refill': time.time()
        })
        
    async def check_rate_limit(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""
        if self.redis_client:
            return await self._check_redis_rate_limit(key)
        else:
            return self._check_local_rate_limit(key)
            
    def _check_local_rate_limit(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using local storage"""
        bucket = self.local_buckets[key]
        current_time = time.time()
        
        # Refill tokens
        time_passed = current_time - bucket['last_refill']
        tokens_to_add = time_passed * self.config.requests_per_second
        bucket['tokens'] = min(
            self.config.burst_size,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = current_time
        
        # Check if request allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            allowed = True
        else:
            allowed = False
            
        # Calculate headers
        headers = {
            'X-RateLimit-Limit': str(self.config.requests_per_second),
            'X-RateLimit-Remaining': str(int(bucket['tokens'])),
            'X-RateLimit-Reset': str(int(current_time + 1))
        }
        
        return allowed, headers
        
    async def _check_redis_rate_limit(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""
        # Use Redis for distributed rate limiting
        script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        local current = redis.call('GET', key)
        if current == false then
            redis.call('SET', key, 1)
            redis.call('EXPIRE', key, window)
            return {1, limit - 1}
        else
            current = tonumber(current)
            if current < limit then
                redis.call('INCR', key)
                return {1, limit - current - 1}
            else
                return {0, 0}
            end
        end
        """
        
        result = await self.redis_client.eval(
            script,
            keys=[f"rate_limit:{key}"],
            args=[
                self.config.requests_per_minute,
                60,
                int(time.time())
            ]
        )
        
        allowed = result[0] == 1
        remaining = result[1]
        
        headers = {
            'X-RateLimit-Limit': str(self.config.requests_per_minute),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(int(time.time() + 60))
        }
        
        return allowed, headers


class CompressionMiddleware(BaseHTTPMiddleware):
    """Response compression middleware"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if client accepts compression
        accept_encoding = request.headers.get('accept-encoding', '')
        
        if 'gzip' in accept_encoding and response.status_code == 200:
            # Compress response
            import gzip
            
            # Read response body
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
                
            # Compress
            compressed = gzip.compress(body)
            
            # Only use compression if it reduces size
            if len(compressed) < len(body):
                return Response(
                    content=compressed,
                    status_code=response.status_code,
                    headers={
                        **dict(response.headers),
                        'content-encoding': 'gzip',
                        'content-length': str(len(compressed))
                    },
                    media_type=response.media_type
                )
                
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Cache control headers middleware"""
    
    def __init__(self, app, default_max_age: int = 300):
        super().__init__(app)
        self.default_max_age = default_max_age
        
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add cache headers for GET requests
        if request.method == "GET" and response.status_code == 200:
            # Check if endpoint has custom cache settings
            cache_control = response.headers.get('cache-control')
            
            if not cache_control:
                # Add default cache headers
                if '/data/' in str(request.url):
                    # Static data - longer cache
                    response.headers['cache-control'] = f'public, max-age=3600'
                elif '/vehicles/live' in str(request.url) or '/trips/updates' in str(request.url):
                    # Real-time data - no cache
                    response.headers['cache-control'] = 'no-cache, no-store, must-revalidate'
                else:
                    # Default cache
                    response.headers['cache-control'] = f'public, max-age={self.default_max_age}'
                    
                # Add ETag for cache validation
                import hashlib
                content_hash = hashlib.md5(response.body).hexdigest()
                response.headers['etag'] = f'"{content_hash}"'
                
        return response


# Decorators for easy integration
def paginate(count_func: Optional[Callable] = None):
    """Decorator for automatic pagination"""
    def decorator(func):
        @wraps(func)
        async def wrapper(
            params: PaginationParams = Depends(),
            *args,
            **kwargs
        ):
            optimizer = get_api_optimizer()
            return await optimizer.paginate_query(
                lambda **p: func(*args, **kwargs, **p),
                params,
                count_func
            )
        return wrapper
    return decorator


def rate_limit(
    requests_per_second: int = 100,
    requests_per_minute: int = 1000
):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier
            client_id = request.client.host or "anonymous"
            
            # Check rate limit
            limiter = RateLimiter(RateLimitConfig(
                requests_per_second=requests_per_second,
                requests_per_minute=requests_per_minute
            ))
            
            allowed, headers = await limiter.check_rate_limit(client_id)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers=headers
                )
                
            # Execute function
            response = await func(request, *args, **kwargs)
            
            # Add rate limit headers
            if isinstance(response, Response):
                for key, value in headers.items():
                    response.headers[key] = value
                    
            return response
        return wrapper
    return decorator


def cache_response(ttl: int = 300):
    """Decorator for response caching"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Try to get from cache
            from .cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            
            cached = cache_manager.get(cache_key)
            if cached is not None:
                return cached
                
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Global optimizer instance
_api_optimizer: Optional[APIOptimizer] = None

def get_api_optimizer() -> APIOptimizer:
    """Get or create global API optimizer"""
    global _api_optimizer
    if _api_optimizer is None:
        _api_optimizer = APIOptimizer()
    return _api_optimizer