"""
MARTA Platform - Multi-Layer Cache Management System
Implements Redis, in-memory, CDN, and browser caching strategies
"""
import os
import json
import hashlib
import pickle
import time
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Callable, Union
from functools import wraps, lru_cache
from collections import OrderedDict, defaultdict
import logging
import redis
import redis.asyncio as aioredis
from redis.sentinel import Sentinel
import memcache
import diskcache
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache hierarchy levels"""
    L1_MEMORY = "l1_memory"      # In-process memory cache
    L2_SHARED = "l2_shared"       # Shared memory cache (Redis)
    L3_DISK = "l3_disk"          # Disk cache
    CDN = "cdn"                   # CDN cache headers
    BROWSER = "browser"           # Browser cache headers


@dataclass
class CacheConfig:
    """Cache configuration"""
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    redis_pool_size: int = 50
    
    memcached_servers: List[str] = ["localhost:11211"]
    
    l1_max_size: int = 1000  # Max items in L1 cache
    l1_ttl: int = 300  # 5 minutes
    
    l2_ttl: int = 3600  # 1 hour
    l2_max_connections: int = 100
    
    l3_size_limit: int = 10 * 1024 * 1024 * 1024  # 10GB
    l3_ttl: int = 86400  # 24 hours
    
    cdn_max_age: int = 3600  # 1 hour
    browser_max_age: int = 300  # 5 minutes
    
    enable_compression: bool = True
    compression_threshold: int = 1024  # Compress if > 1KB
    
    enable_metrics: bool = True
    enable_warming: bool = True


class CacheManager:
    """Multi-layer cache management system"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        
        # Initialize cache layers
        self._init_l1_cache()
        self._init_l2_cache()
        self._init_l3_cache()
        
        # Cache statistics
        self.stats = defaultdict(lambda: {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'total_size': 0,
            'avg_latency': 0
        })
        
        # Cache warming queue
        self.warming_queue = asyncio.Queue() if self.config.enable_warming else None
        
    def _init_l1_cache(self):
        """Initialize L1 in-memory cache"""
        self.l1_cache = TTLCache(
            max_size=self.config.l1_max_size,
            ttl=self.config.l1_ttl
        )
        
    def _init_l2_cache(self):
        """Initialize L2 Redis cache"""
        try:
            # Redis connection pool
            self.redis_pool = redis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                max_connections=self.config.redis_pool_size,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Async Redis client
            self.async_redis_pool = aioredis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                max_connections=self.config.redis_pool_size
            )
            self.async_redis_client = aioredis.Redis(connection_pool=self.async_redis_pool)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Using fallback memory cache.")
            self.redis_client = None
            self.async_redis_client = None
            
    def _init_l3_cache(self):
        """Initialize L3 disk cache"""
        try:
            cache_dir = os.path.join(os.getcwd(), '.cache', 'disk')
            os.makedirs(cache_dir, exist_ok=True)
            
            self.disk_cache = diskcache.Cache(
                cache_dir,
                size_limit=self.config.l3_size_limit,
                disk_min_file_size=1024  # 1KB minimum
            )
            logger.info("Disk cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Disk cache initialization failed: {e}")
            self.disk_cache = None
            
    def _generate_key(self, key: str, prefix: str = "") -> str:
        """Generate cache key with optional prefix"""
        if prefix:
            return f"{prefix}:{key}"
        return key
        
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for caching"""
        if isinstance(value, (pd.DataFrame, pd.Series)):
            return pickle.dumps(value.to_dict())
        elif isinstance(value, np.ndarray):
            return pickle.dumps(value.tolist())
        else:
            return pickle.dumps(value)
            
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize cached value"""
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None
            
    def _should_compress(self, data: bytes) -> bool:
        """Check if data should be compressed"""
        return (
            self.config.enable_compression and 
            len(data) > self.config.compression_threshold
        )
        
    def _compress(self, data: bytes) -> bytes:
        """Compress data for storage"""
        if self._should_compress(data):
            import zlib
            return zlib.compress(data, level=6)
        return data
        
    def _decompress(self, data: bytes) -> bytes:
        """Decompress cached data"""
        if self.config.enable_compression:
            try:
                import zlib
                return zlib.decompress(data)
            except:
                return data  # Not compressed
        return data
        
    # L1 Cache Operations
    def l1_get(self, key: str) -> Optional[Any]:
        """Get from L1 cache"""
        start = time.time()
        value = self.l1_cache.get(key)
        
        if value is not None:
            self.stats['l1']['hits'] += 1
        else:
            self.stats['l1']['misses'] += 1
            
        self.stats['l1']['avg_latency'] = (time.time() - start) * 1000
        return value
        
    def l1_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set in L1 cache"""
        ttl = ttl or self.config.l1_ttl
        self.l1_cache.set(key, value, ttl)
        self.stats['l1']['sets'] += 1
        
    # L2 Cache Operations (Redis)
    def l2_get(self, key: str) -> Optional[Any]:
        """Get from L2 cache"""
        if not self.redis_client:
            return None
            
        try:
            start = time.time()
            data = self.redis_client.get(key)
            
            if data:
                self.stats['l2']['hits'] += 1
                data = self._decompress(data)
                value = self._deserialize(data)
                
                # Promote to L1
                self.l1_set(key, value)
                
                self.stats['l2']['avg_latency'] = (time.time() - start) * 1000
                return value
            else:
                self.stats['l2']['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"L2 cache get error: {e}")
            self.stats['l2']['errors'] += 1
            return None
            
    def l2_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set in L2 cache"""
        if not self.redis_client:
            return
            
        try:
            ttl = ttl or self.config.l2_ttl
            data = self._serialize(value)
            data = self._compress(data)
            
            self.redis_client.setex(key, ttl, data)
            self.stats['l2']['sets'] += 1
            
        except Exception as e:
            logger.error(f"L2 cache set error: {e}")
            self.stats['l2']['errors'] += 1
            
    async def l2_get_async(self, key: str) -> Optional[Any]:
        """Async get from L2 cache"""
        if not self.async_redis_client:
            return None
            
        try:
            data = await self.async_redis_client.get(key)
            if data:
                self.stats['l2']['hits'] += 1
                data = self._decompress(data)
                return self._deserialize(data)
            else:
                self.stats['l2']['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"L2 async cache get error: {e}")
            self.stats['l2']['errors'] += 1
            return None
            
    async def l2_set_async(self, key: str, value: Any, ttl: Optional[int] = None):
        """Async set in L2 cache"""
        if not self.async_redis_client:
            return
            
        try:
            ttl = ttl or self.config.l2_ttl
            data = self._serialize(value)
            data = self._compress(data)
            
            await self.async_redis_client.setex(key, ttl, data)
            self.stats['l2']['sets'] += 1
            
        except Exception as e:
            logger.error(f"L2 async cache set error: {e}")
            self.stats['l2']['errors'] += 1
            
    # L3 Cache Operations (Disk)
    def l3_get(self, key: str) -> Optional[Any]:
        """Get from L3 cache"""
        if not self.disk_cache:
            return None
            
        try:
            start = time.time()
            value = self.disk_cache.get(key)
            
            if value is not None:
                self.stats['l3']['hits'] += 1
                
                # Promote to L2 and L1
                self.l2_set(key, value)
                self.l1_set(key, value)
                
                self.stats['l3']['avg_latency'] = (time.time() - start) * 1000
                return value
            else:
                self.stats['l3']['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"L3 cache get error: {e}")
            self.stats['l3']['errors'] += 1
            return None
            
    def l3_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set in L3 cache"""
        if not self.disk_cache:
            return
            
        try:
            ttl = ttl or self.config.l3_ttl
            self.disk_cache.set(key, value, expire=ttl)
            self.stats['l3']['sets'] += 1
            
        except Exception as e:
            logger.error(f"L3 cache set error: {e}")
            self.stats['l3']['errors'] += 1
            
    # Multi-layer Operations
    def get(self, key: str, cache_levels: Optional[List[CacheLevel]] = None) -> Optional[Any]:
        """Get from cache hierarchy"""
        cache_levels = cache_levels or [CacheLevel.L1_MEMORY, CacheLevel.L2_SHARED, CacheLevel.L3_DISK]
        
        for level in cache_levels:
            value = None
            
            if level == CacheLevel.L1_MEMORY:
                value = self.l1_get(key)
            elif level == CacheLevel.L2_SHARED:
                value = self.l2_get(key)
            elif level == CacheLevel.L3_DISK:
                value = self.l3_get(key)
                
            if value is not None:
                return value
                
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_levels: Optional[List[CacheLevel]] = None):
        """Set in cache hierarchy"""
        cache_levels = cache_levels or [CacheLevel.L1_MEMORY, CacheLevel.L2_SHARED]
        
        for level in cache_levels:
            if level == CacheLevel.L1_MEMORY:
                self.l1_set(key, value, ttl)
            elif level == CacheLevel.L2_SHARED:
                self.l2_set(key, value, ttl)
            elif level == CacheLevel.L3_DISK:
                self.l3_set(key, value, ttl)
                
    def delete(self, key: str):
        """Delete from all cache levels"""
        # L1
        self.l1_cache.delete(key)
        self.stats['l1']['deletes'] += 1
        
        # L2
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                self.stats['l2']['deletes'] += 1
            except:
                pass
                
        # L3
        if self.disk_cache:
            try:
                del self.disk_cache[key]
                self.stats['l3']['deletes'] += 1
            except:
                pass
                
    def clear_all(self):
        """Clear all cache levels"""
        self.l1_cache.clear()
        
        if self.redis_client:
            self.redis_client.flushdb()
            
        if self.disk_cache:
            self.disk_cache.clear()
            
    # Cache Warming
    async def warm_cache(self, keys: List[str], loader_func: Callable):
        """Warm cache with pre-loaded data"""
        if not self.config.enable_warming:
            return
            
        for key in keys:
            try:
                value = await loader_func(key) if asyncio.iscoroutinefunction(loader_func) else loader_func(key)
                if value is not None:
                    self.set(key, value)
                    logger.debug(f"Cache warmed for key: {key}")
            except Exception as e:
                logger.error(f"Cache warming failed for {key}: {e}")
                
    # Cache Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_stats = {
            'total_hits': sum(s['hits'] for s in self.stats.values()),
            'total_misses': sum(s['misses'] for s in self.stats.values()),
            'total_sets': sum(s['sets'] for s in self.stats.values()),
            'total_deletes': sum(s['deletes'] for s in self.stats.values()),
            'total_errors': sum(s['errors'] for s in self.stats.values()),
        }
        
        # Calculate hit rate
        total_requests = total_stats['total_hits'] + total_stats['total_misses']
        if total_requests > 0:
            total_stats['hit_rate'] = (total_stats['total_hits'] / total_requests) * 100
        else:
            total_stats['hit_rate'] = 0
            
        # Add per-level stats
        total_stats['levels'] = dict(self.stats)
        
        # Add Redis info if available
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
                total_stats['redis'] = {
                    'used_memory': redis_info.get('used_memory_human'),
                    'connected_clients': redis_info.get('connected_clients'),
                    'total_connections_received': redis_info.get('total_connections_received'),
                    'instantaneous_ops_per_sec': redis_info.get('instantaneous_ops_per_sec')
                }
            except:
                pass
                
        return total_stats
        
    def reset_stats(self):
        """Reset cache statistics"""
        for level in self.stats:
            self.stats[level] = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0,
                'errors': 0,
                'total_size': 0,
                'avg_latency': 0
            }


class TTLCache:
    """Thread-safe TTL cache implementation"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self.cache:
                # Check TTL
                if time.time() - self.timestamps[key] > self.ttl:
                    del self.cache[key]
                    del self.timestamps[key]
                    return None
                    
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        with self._lock:
            # Remove oldest if at capacity
            if key not in self.cache and len(self.cache) >= self.max_size:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                del self.timestamps[oldest]
                
            self.cache[key] = value
            self.timestamps[key] = time.time()
            self.cache.move_to_end(key)
            
    def delete(self, key: str):
        """Delete from cache"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
                
    def clear(self):
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()


# Cache decorators
def cache(ttl: int = 300, cache_levels: Optional[List[CacheLevel]] = None, 
          key_prefix: str = "", cache_manager: Optional[CacheManager] = None):
    """Decorator for automatic caching"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Get cache manager
            cm = cache_manager or get_cache_manager()
            
            # Try to get from cache
            cached_value = cm.get(cache_key, cache_levels)
            if cached_value is not None:
                return cached_value
                
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cm.set(cache_key, result, ttl, cache_levels)
            
            return result
        return wrapper
    return decorator


def async_cache(ttl: int = 300, cache_levels: Optional[List[CacheLevel]] = None,
                key_prefix: str = "", cache_manager: Optional[CacheManager] = None):
    """Decorator for automatic async caching"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Get cache manager
            cm = cache_manager or get_cache_manager()
            
            # Try to get from cache
            cached_value = await cm.l2_get_async(cache_key)
            if cached_value is not None:
                return cached_value
                
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cm.l2_set_async(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# CDN cache headers
def cdn_cache_headers(max_age: int = 3600, s_maxage: int = 86400, 
                      stale_while_revalidate: int = 60):
    """Generate CDN cache headers"""
    return {
        'Cache-Control': f'public, max-age={max_age}, s-maxage={s_maxage}, stale-while-revalidate={stale_while_revalidate}',
        'Vary': 'Accept-Encoding',
        'X-Cache-TTL': str(max_age)
    }


# Browser cache headers  
def browser_cache_headers(max_age: int = 300, must_revalidate: bool = True):
    """Generate browser cache headers"""
    directives = [f'max-age={max_age}']
    
    if must_revalidate:
        directives.append('must-revalidate')
    else:
        directives.append('immutable')
        
    return {
        'Cache-Control': ', '.join(directives),
        'ETag': f'"{hashlib.md5(str(time.time()).encode()).hexdigest()}"',
        'Last-Modified': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }


# Global cache manager
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

def invalidate_cache(pattern: str = "*"):
    """Invalidate cache by pattern"""
    cm = get_cache_manager()
    if cm.redis_client:
        for key in cm.redis_client.scan_iter(pattern):
            cm.delete(key.decode() if isinstance(key, bytes) else key)