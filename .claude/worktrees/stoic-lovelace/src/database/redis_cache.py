"""
MARTA Platform - Redis Caching Strategies
High-performance caching layer for hot data with intelligent cache invalidation
"""
import json
import pickle
import hashlib
import time
import asyncio
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
from contextlib import asynccontextmanager
import threading

import redis
import aioredis
import pandas as pd
import structlog
from pydantic import BaseModel

from config.settings import settings

# Configure logging
logger = structlog.get_logger(__name__)

class CacheConfig(BaseModel):
    """Redis cache configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    connection_pool_max_connections: int = 50
    retry_on_timeout: bool = True
    health_check_interval: int = 30

class CacheMetrics:
    """Cache performance metrics"""
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_time = 0.0
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def record_hit(self, execution_time: float = 0):
        with self._lock:
            self.hits += 1
            self.total_time += execution_time
    
    def record_miss(self, execution_time: float = 0):
        with self._lock:
            self.misses += 1
            self.total_time += execution_time
    
    def record_set(self, execution_time: float = 0):
        with self._lock:
            self.sets += 1
            self.total_time += execution_time
    
    def record_delete(self, execution_time: float = 0):
        with self._lock:
            self.deletes += 1
            self.total_time += execution_time
    
    def record_error(self, execution_time: float = 0):
        with self._lock:
            self.errors += 1
            self.total_time += execution_time
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_operations = self.hits + self.misses + self.sets + self.deletes
            uptime = time.time() - self.start_time
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'sets': self.sets,
                'deletes': self.deletes,
                'errors': self.errors,
                'hit_rate': self.hits / max(self.hits + self.misses, 1) * 100,
                'total_operations': total_operations,
                'operations_per_second': total_operations / max(uptime, 1),
                'avg_operation_time': self.total_time / max(total_operations, 1),
                'uptime_seconds': uptime
            }
    
    def reset(self):
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.sets = 0
            self.deletes = 0
            self.errors = 0
            self.total_time = 0.0
            self.start_time = time.time()

class RedisCacheManager:
    """
    High-performance Redis cache manager with intelligent caching strategies
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._redis_client: Optional[redis.Redis] = None
        self._async_redis_client: Optional[aioredis.Redis] = None
        self._metrics = CacheMetrics()
        
        # Cache key prefixes for different data types
        self.KEY_PREFIXES = {
            'vehicle_positions': 'vp',
            'trip_updates': 'tu',
            'stop_arrivals': 'sa',
            'route_performance': 'rp',
            'demand_forecast': 'df',
            'system_status': 'ss',
            'route_data': 'rd',
            'stop_data': 'sd',
            'geospatial': 'geo',
            'analytics': 'ana'
        }
        
        # Default TTL values (in seconds)
        self.DEFAULT_TTLS = {
            'vehicle_positions': 30,      # Real-time data
            'trip_updates': 60,           # Trip updates
            'stop_arrivals': 120,         # Arrival predictions
            'route_performance': 300,     # 5 minutes
            'demand_forecast': 900,       # 15 minutes
            'system_status': 60,          # System status
            'route_data': 3600,           # 1 hour (relatively static)
            'stop_data': 3600,            # 1 hour (relatively static)
            'geospatial': 7200,           # 2 hours
            'analytics': 1800             # 30 minutes
        }
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Redis clients"""
        try:
            # Synchronous client
            self._redis_client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                connection_pool_max_connections=self.config.connection_pool_max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=False  # We'll handle encoding/decoding
            )
            
            # Test connection
            self._redis_client.ping()
            
            logger.info("Redis cache manager initialized successfully",
                       host=self.config.host, port=self.config.port, db=self.config.db)
                       
        except Exception as e:
            logger.error("Failed to initialize Redis cache manager", error=str(e))
            # Continue without caching
            self._redis_client = None
    
    async def _get_async_client(self) -> Optional[aioredis.Redis]:
        """Get or create async Redis client"""
        if self._async_redis_client is None:
            try:
                self._async_redis_client = await aioredis.from_url(
                    f"redis://{self.config.host}:{self.config.port}/{self.config.db}",
                    password=self.config.password,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    max_connections=self.config.connection_pool_max_connections,
                    retry_on_timeout=self.config.retry_on_timeout
                )
                await self._async_redis_client.ping()
            except Exception as e:
                logger.error("Failed to initialize async Redis client", error=str(e))
                self._async_redis_client = None
        
        return self._async_redis_client
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key"""
        # Create a unique identifier from arguments
        key_parts = [str(arg) for arg in args]
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend([f"{k}:{v}" for k, v in sorted_kwargs])
        
        # Create hash for long keys
        key_string = ":".join(key_parts)
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return f"{prefix}:{key_string}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        if isinstance(data, pd.DataFrame):
            # For DataFrames, use more efficient serialization
            return pickle.dumps(data.to_dict('records'))
        elif isinstance(data, (dict, list)):
            # For JSON-serializable data, use JSON
            return json.dumps(data, default=str).encode('utf-8')
        else:
            # For other objects, use pickle
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis storage"""
        try:
            # Try JSON first (faster)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    def get(self, cache_type: str, *args, **kwargs) -> Optional[Any]:
        """Get data from cache"""
        if not self._redis_client:
            return None
        
        start_time = time.time()
        try:
            prefix = self.KEY_PREFIXES.get(cache_type, cache_type)
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            data = self._redis_client.get(cache_key)
            execution_time = time.time() - start_time
            
            if data:
                self._metrics.record_hit(execution_time)
                return self._deserialize_data(data)
            else:
                self._metrics.record_miss(execution_time)
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._metrics.record_error(execution_time)
            logger.error("Cache get operation failed", 
                        cache_type=cache_type, error=str(e))
            return None
    
    def set(self, cache_type: str, data: Any, ttl: Optional[int] = None, *args, **kwargs) -> bool:
        """Set data in cache"""
        if not self._redis_client:
            return False
        
        start_time = time.time()
        try:
            prefix = self.KEY_PREFIXES.get(cache_type, cache_type)
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.DEFAULT_TTLS.get(cache_type, 3600)
            
            serialized_data = self._serialize_data(data)
            result = self._redis_client.setex(cache_key, ttl, serialized_data)
            
            execution_time = time.time() - start_time
            self._metrics.record_set(execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._metrics.record_error(execution_time)
            logger.error("Cache set operation failed", 
                        cache_type=cache_type, error=str(e))
            return False
    
    def delete(self, cache_type: str, *args, **kwargs) -> bool:
        """Delete data from cache"""
        if not self._redis_client:
            return False
        
        start_time = time.time()
        try:
            prefix = self.KEY_PREFIXES.get(cache_type, cache_type)
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            result = self._redis_client.delete(cache_key) > 0
            
            execution_time = time.time() - start_time
            self._metrics.record_delete(execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._metrics.record_error(execution_time)
            logger.error("Cache delete operation failed", 
                        cache_type=cache_type, error=str(e))
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern"""
        if not self._redis_client:
            return 0
        
        try:
            keys = self._redis_client.keys(pattern)
            if keys:
                return self._redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error("Cache pattern invalidation failed", 
                        pattern=pattern, error=str(e))
            return 0
    
    async def async_get(self, cache_type: str, *args, **kwargs) -> Optional[Any]:
        """Get data from cache asynchronously"""
        client = await self._get_async_client()
        if not client:
            return None
        
        start_time = time.time()
        try:
            prefix = self.KEY_PREFIXES.get(cache_type, cache_type)
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            data = await client.get(cache_key)
            execution_time = time.time() - start_time
            
            if data:
                self._metrics.record_hit(execution_time)
                return self._deserialize_data(data)
            else:
                self._metrics.record_miss(execution_time)
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._metrics.record_error(execution_time)
            logger.error("Async cache get operation failed", 
                        cache_type=cache_type, error=str(e))
            return None
    
    async def async_set(self, cache_type: str, data: Any, ttl: Optional[int] = None, *args, **kwargs) -> bool:
        """Set data in cache asynchronously"""
        client = await self._get_async_client()
        if not client:
            return False
        
        start_time = time.time()
        try:
            prefix = self.KEY_PREFIXES.get(cache_type, cache_type)
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.DEFAULT_TTLS.get(cache_type, 3600)
            
            serialized_data = self._serialize_data(data)
            result = await client.setex(cache_key, ttl, serialized_data)
            
            execution_time = time.time() - start_time
            self._metrics.record_set(execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._metrics.record_error(execution_time)
            logger.error("Async cache set operation failed", 
                        cache_type=cache_type, error=str(e))
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get Redis cache information"""
        if not self._redis_client:
            return {'status': 'unavailable'}
        
        try:
            info = self._redis_client.info()
            return {
                'status': 'connected',
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': info.get('keyspace_hits', 0) / max(
                    info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1
                ) * 100,
                'client_metrics': self._metrics.get_stats()
            }
        except Exception as e:
            logger.error("Failed to get cache info", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check"""
        if not self._redis_client:
            return {'status': 'unavailable', 'message': 'Redis client not initialized'}
        
        try:
            start_time = time.time()
            self._redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'timestamp': datetime.now(),
                'cache_info': self.get_cache_info()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def flush_cache(self, pattern: Optional[str] = None) -> bool:
        """Flush cache data"""
        if not self._redis_client:
            return False
        
        try:
            if pattern:
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
                    logger.info("Cache pattern flushed", pattern=pattern, keys_deleted=len(keys))
            else:
                self._redis_client.flushdb()
                logger.info("Cache database flushed")
            
            return True
        except Exception as e:
            logger.error("Cache flush failed", pattern=pattern, error=str(e))
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        return self._metrics.get_stats()
    
    def reset_metrics(self):
        """Reset cache performance metrics"""
        self._metrics.reset()

# Global cache manager instance
_cache_manager: Optional[RedisCacheManager] = None

def get_cache_manager() -> RedisCacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = RedisCacheManager()
    return _cache_manager

# Caching decorators
def cached(cache_type: str, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results
    
    Args:
        cache_type: Type of cache (used for key prefix and TTL)
        ttl: Time to live in seconds (optional)
        key_func: Function to generate cache key from arguments (optional)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key_args = key_func(*args, **kwargs)
                if isinstance(cache_key_args, tuple):
                    cache_args, cache_kwargs = cache_key_args
                else:
                    cache_args, cache_kwargs = (cache_key_args,), {}
            else:
                cache_args, cache_kwargs = args, kwargs
            
            # Try to get from cache
            cached_result = cache.get(cache_type, *cache_args, **cache_kwargs)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_type, result, ttl, *cache_args, **cache_kwargs)
            
            return result
        
        return wrapper
    return decorator

def async_cached(cache_type: str, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Async decorator for caching function results
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key_args = key_func(*args, **kwargs)
                if isinstance(cache_key_args, tuple):
                    cache_args, cache_kwargs = cache_key_args
                else:
                    cache_args, cache_kwargs = (cache_key_args,), {}
            else:
                cache_args, cache_kwargs = args, kwargs
            
            # Try to get from cache
            cached_result = await cache.async_get(cache_type, *cache_args, **cache_kwargs)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.async_set(cache_type, result, ttl, *cache_args, **cache_kwargs)
            
            return result
        
        return wrapper
    return decorator

# Cache invalidation strategies
class CacheInvalidationManager:
    """Manages cache invalidation based on data changes"""
    
    def __init__(self, cache_manager: RedisCacheManager):
        self.cache = cache_manager
        
        # Define invalidation rules
        self.invalidation_rules = {
            'vehicle_positions_updated': ['vehicle_positions', 'system_status'],
            'trip_updates_updated': ['trip_updates', 'stop_arrivals', 'route_performance'],
            'route_data_updated': ['route_data', 'route_performance', 'analytics'],
            'stop_data_updated': ['stop_data', 'stop_arrivals', 'geospatial']
        }
    
    def invalidate_for_event(self, event: str, entity_id: Optional[str] = None):
        """Invalidate caches based on data change event"""
        cache_types_to_invalidate = self.invalidation_rules.get(event, [])
        
        for cache_type in cache_types_to_invalidate:
            if entity_id:
                # Invalidate specific entity caches
                pattern = f"{self.cache.KEY_PREFIXES.get(cache_type, cache_type)}:*{entity_id}*"
            else:
                # Invalidate all caches of this type
                pattern = f"{self.cache.KEY_PREFIXES.get(cache_type, cache_type)}:*"
            
            invalidated_count = self.cache.invalidate_pattern(pattern)
            logger.debug("Cache invalidated for event", 
                        event=event, cache_type=cache_type, 
                        entity_id=entity_id, invalidated_keys=invalidated_count)

# Convenience functions
def get_cached(cache_type: str, *args, **kwargs) -> Optional[Any]:
    """Get data from cache"""
    return get_cache_manager().get(cache_type, *args, **kwargs)

def set_cached(cache_type: str, data: Any, ttl: Optional[int] = None, *args, **kwargs) -> bool:
    """Set data in cache"""
    return get_cache_manager().set(cache_type, data, ttl, *args, **kwargs)

def delete_cached(cache_type: str, *args, **kwargs) -> bool:
    """Delete data from cache"""
    return get_cache_manager().delete(cache_type, *args, **kwargs)

async def get_cached_async(cache_type: str, *args, **kwargs) -> Optional[Any]:
    """Get data from cache asynchronously"""
    return await get_cache_manager().async_get(cache_type, *args, **kwargs)

async def set_cached_async(cache_type: str, data: Any, ttl: Optional[int] = None, *args, **kwargs) -> bool:
    """Set data in cache asynchronously"""
    return await get_cache_manager().async_set(cache_type, data, ttl, *args, **kwargs)

def cache_health_check() -> Dict[str, Any]:
    """Perform cache health check"""
    return get_cache_manager().health_check()

def get_cache_metrics() -> Dict[str, Any]:
    """Get cache performance metrics"""
    return get_cache_manager().get_metrics()

def flush_cache(pattern: Optional[str] = None) -> bool:
    """Flush cache data"""
    return get_cache_manager().flush_cache(pattern)