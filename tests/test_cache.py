"""
Tests for Redis cache service.
"""
import pytest
import json
from unittest.mock import Mock, patch
from src.services.cache import CacheService, cached


class TestCacheService:
    """Test cache service functionality."""
    
    @patch('src.services.cache.redis.Redis')
    def test_cache_initialization_success(self, mock_redis):
        """Test successful cache initialization."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        cache = CacheService()
        assert cache.enabled is True
        assert cache.redis_client is not None
    
    @patch('src.services.cache.redis.Redis')
    def test_cache_initialization_failure(self, mock_redis):
        """Test cache initialization when Redis unavailable."""
        mock_redis.side_effect = Exception("Connection failed")
        
        cache = CacheService()
        assert cache.enabled is False
        assert cache.redis_client is None
    
    @patch('src.services.cache.redis.Redis')
    def test_cache_get_json(self, mock_redis):
        """Test getting JSON value from cache."""
        mock_client = Mock()
        test_data = {"key": "value"}
        mock_client.get.return_value = json.dumps(test_data).encode()
        mock_redis.return_value = mock_client
        
        cache = CacheService()
        cache.redis_client = mock_client
        cache.enabled = True
        
        result = cache.get("test_key")
        assert result == test_data
    
    @patch('src.services.cache.redis.Redis')
    def test_cache_set_json(self, mock_redis):
        """Test setting JSON value in cache."""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        
        cache = CacheService()
        cache.redis_client = mock_client
        cache.enabled = True
        
        test_data = {"key": "value"}
        result = cache.set("test_key", test_data, ttl=60)
        
        assert result is True
        mock_client.setex.assert_called_once()
    
    @patch('src.services.cache.redis.Redis')
    def test_cache_delete(self, mock_redis):
        """Test deleting key from cache."""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        
        cache = CacheService()
        cache.redis_client = mock_client
        cache.enabled = True
        
        result = cache.delete("test_key")
        assert result is True
        mock_client.delete.assert_called_once_with("test_key")
    
    @patch('src.services.cache.redis.Redis')
    def test_cache_clear_pattern(self, mock_redis):
        """Test clearing keys by pattern."""
        mock_client = Mock()
        mock_client.keys.return_value = [b"key1", b"key2", b"key3"]
        mock_client.delete.return_value = 3
        mock_redis.return_value = mock_client
        
        cache = CacheService()
        cache.redis_client = mock_client
        cache.enabled = True
        
        result = cache.clear_pattern("test:*")
        assert result == 3
        mock_client.keys.assert_called_once_with("test:*")


@pytest.mark.asyncio
class TestCacheDecorator:
    """Test cache decorator functionality."""
    
    @patch('src.services.cache.cache')
    async def test_cached_decorator_hit(self, mock_cache):
        """Test cache decorator with cache hit."""
        mock_cache.get.return_value = {"cached": "data"}
        
        @cached("test", ttl=60)
        async def test_function():
            return {"new": "data"}
        
        result = await test_function()
        assert result == {"cached": "data"}
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_not_called()
    
    @patch('src.services.cache.cache')
    async def test_cached_decorator_miss(self, mock_cache):
        """Test cache decorator with cache miss."""
        mock_cache.get.return_value = None
        
        @cached("test", ttl=60)
        async def test_function():
            return {"new": "data"}
        
        result = await test_function()
        assert result == {"new": "data"}
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()