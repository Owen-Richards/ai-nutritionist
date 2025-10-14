"""Caching implementation for feature flags."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None


class FeatureFlagCache(ABC):
    """Abstract base class for feature flag caching."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 300) -> None:
        """Set cached value with TTL."""
        pass
    
    @abstractmethod
    async def invalidate(self, key: str) -> None:
        """Invalidate cached value."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached values."""
        pass


class MemoryCache(FeatureFlagCache):
    """In-memory cache implementation for feature flags."""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 10000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._expiry_times: Dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None
        
        # Check if expired
        if key in self._expiry_times:
            if time.time() > self._expiry_times[key]:
                await self.invalidate(key)
                return None
        
        return self._cache[key]
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 300) -> None:
        """Set cached value with TTL."""
        # Enforce max size
        if len(self._cache) >= self.max_size:
            await self._evict_oldest()
        
        self._cache[key] = value
        self._expiry_times[key] = time.time() + ttl_seconds
    
    async def invalidate(self, key: str) -> None:
        """Remove key from cache."""
        self._cache.pop(key, None)
        self._expiry_times.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        self._expiry_times.clear()
    
    async def _evict_oldest(self) -> None:
        """Evict oldest entries to make room."""
        if not self._expiry_times:
            return
        
        # Find the oldest entry
        oldest_key = min(self._expiry_times.keys(), key=lambda k: self._expiry_times[k])
        await self.invalidate(oldest_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        expired_count = sum(
            1 for expiry_time in self._expiry_times.values()
            if expiry_time <= current_time
        )
        
        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "active_entries": len(self._cache) - expired_count,
            "max_size": self.max_size,
            "usage_percentage": (len(self._cache) / self.max_size) * 100,
        }


class RedisCache(FeatureFlagCache):
    """Redis-based cache implementation for feature flags."""
    
    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 300,
        key_prefix: str = "ff:",
        pool_size: int = 10,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.pool_size = pool_size
        self._pool = None
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None:
            self._pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.pool_size,
                decode_responses=True,
            )
            self._redis = aioredis.Redis(connection_pool=self._pool)
        
        return self._redis
    
    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value from Redis."""
        try:
            redis_client = await self._get_redis()
            redis_key = self._make_key(key)
            
            value = await redis_client.get(redis_key)
            if value is None:
                return None
            
            return json.loads(value)
            
        except Exception as e:
            # Log error but don't fail - return None for cache miss
            import logging
            logging.error(f"Redis cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 300) -> None:
        """Set cached value in Redis with TTL."""
        try:
            redis_client = await self._get_redis()
            redis_key = self._make_key(key)
            
            serialized_value = json.dumps(value, default=str)
            await redis_client.setex(redis_key, ttl_seconds, serialized_value)
            
        except Exception as e:
            # Log error but don't fail
            import logging
            logging.error(f"Redis cache set error: {e}")
    
    async def invalidate(self, key: str) -> None:
        """Remove key from Redis."""
        try:
            redis_client = await self._get_redis()
            redis_key = self._make_key(key)
            
            await redis_client.delete(redis_key)
            
        except Exception as e:
            import logging
            logging.error(f"Redis cache invalidate error: {e}")
    
    async def clear(self) -> None:
        """Clear all feature flag keys from Redis."""
        try:
            redis_client = await self._get_redis()
            pattern = f"{self.key_prefix}*"
            
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
                
        except Exception as e:
            import logging
            logging.error(f"Redis cache clear error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            redis_client = await self._get_redis()
            pattern = f"{self.key_prefix}*"
            
            keys = await redis_client.keys(pattern)
            key_count = len(keys)
            
            # Get memory usage (approximation)
            info = await redis_client.info("memory")
            used_memory = info.get("used_memory", 0)
            
            return {
                "key_count": key_count,
                "used_memory_bytes": used_memory,
                "pattern": pattern,
                "connection_pool_size": self.pool_size,
            }
            
        except Exception as e:
            import logging
            logging.error(f"Redis cache stats error: {e}")
            return {"error": str(e)}
    
    async def close(self) -> None:
        """Close Redis connections."""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            self._redis = None


class MultiLevelCache(FeatureFlagCache):
    """Multi-level cache combining memory and Redis."""
    
    def __init__(
        self,
        memory_cache: MemoryCache,
        redis_cache: RedisCache,
        write_through: bool = True,
    ):
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache
        self.write_through = write_through
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from memory first, then Redis."""
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try Redis cache
        value = await self.redis_cache.get(key)
        if value is not None:
            # Backfill memory cache
            await self.memory_cache.set(key, value, self.memory_cache.ttl_seconds)
            return value
        
        return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 300) -> None:
        """Set in both caches."""
        # Always set in memory cache
        await self.memory_cache.set(key, value, ttl_seconds)
        
        # Set in Redis if write-through enabled
        if self.write_through:
            await self.redis_cache.set(key, value, ttl_seconds)
    
    async def invalidate(self, key: str) -> None:
        """Invalidate from both caches."""
        await self.memory_cache.invalidate(key)
        await self.redis_cache.invalidate(key)
    
    async def clear(self) -> None:
        """Clear both caches."""
        await self.memory_cache.clear()
        await self.redis_cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        memory_stats = self.memory_cache.get_stats()
        redis_stats = await self.redis_cache.get_stats()
        
        return {
            "memory_cache": memory_stats,
            "redis_cache": redis_stats,
            "write_through": self.write_through,
        }


class CacheWarmer:
    """Utility for warming up feature flag cache."""
    
    def __init__(self, cache: FeatureFlagCache, flag_service):
        self.cache = cache
        self.flag_service = flag_service
    
    async def warm_common_flags(
        self,
        flag_keys: list[str],
        common_contexts: list[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Warm cache with common flag/context combinations."""
        results = {"success": 0, "errors": 0}
        
        for flag_key in flag_keys:
            for context_data in common_contexts:
                try:
                    from .models import FlagContext
                    context = FlagContext(**context_data)
                    
                    # Evaluate flag to populate cache
                    await self.flag_service.evaluate_flag(flag_key, context)
                    results["success"] += 1
                    
                except Exception as e:
                    results["errors"] += 1
                    import logging
                    logging.error(f"Cache warming error for {flag_key}: {e}")
        
        return results
    
    async def warm_user_segments(
        self,
        flag_keys: list[str],
        segments: list[str],
        sample_users_per_segment: int = 10,
    ) -> Dict[str, int]:
        """Warm cache for different user segments."""
        from .models import FlagContext
        results = {"success": 0, "errors": 0}
        
        for flag_key in flag_keys:
            for segment in segments:
                for i in range(sample_users_per_segment):
                    try:
                        context = FlagContext(
                            user_id=f"sample_user_{segment}_{i}",
                            user_segments=[segment],
                            subscription_tier=segment if segment in ["free", "premium", "enterprise"] else "free",
                        )
                        
                        await self.flag_service.evaluate_flag(flag_key, context)
                        results["success"] += 1
                        
                    except Exception as e:
                        results["errors"] += 1
                        import logging
                        logging.error(f"Segment cache warming error: {e}")
        
        return results
