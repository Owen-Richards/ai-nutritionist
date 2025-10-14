"""
Comprehensive cache manager coordinating multiple cache backends and strategies.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import CacheConfig, CacheMetrics, CacheTier, CACHE_PROFILES
from .backends import (
    CacheBackend, 
    MemoryCacheBackend, 
    RedisCacheBackend, 
    DatabaseCacheBackend,
    CDNCacheBackend
)
from .strategies import (
    CacheStrategy,
    CacheStrategyHandler,
    CacheAsideStrategy,
    WriteThroughStrategy,
    WriteBehindStrategy,
    RefreshAheadStrategy,
    InvalidationHandler
)
from .keys import CacheKeyBuilder, get_cache_key_builder

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    
    value: Any
    key: str
    created_at: float
    expires_at: float
    tags: List[str]
    tier: CacheTier
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return time.time() - self.created_at
    
    @property
    def ttl_remaining(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.expires_at - time.time())


class CacheManager:
    """
    Comprehensive cache manager with multiple tiers and strategies.
    
    Features:
    - Multi-tier caching (Memory, Redis, Database, CDN)
    - Multiple cache strategies (cache-aside, write-through, etc.)
    - Intelligent cache invalidation
    - Performance monitoring
    - Background refresh
    - Cache warming
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.metrics = CacheMetrics()
        self.key_builder = get_cache_key_builder()
        
        # Initialize backends
        self.backends: Dict[CacheTier, CacheBackend] = {}
        self._init_backends()
        
        # Initialize strategies
        self.strategies: Dict[CacheStrategy, CacheStrategyHandler] = {}
        self._init_strategies()
        
        # Initialize invalidation handler
        self.invalidation = InvalidationHandler(self)
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._start_background_tasks()
    
    def _init_backends(self):
        """Initialize cache backends based on configuration."""
        try:
            # Memory cache (always available)
            self.backends[CacheTier.MEMORY] = MemoryCacheBackend(
                max_size=self.config.memory_cache_size,
                default_ttl=self.config.memory_cache_ttl
            )
            
            # Redis cache (if available)
            try:
                self.backends[CacheTier.REDIS] = RedisCacheBackend(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    password=self.config.redis_password,
                    db=self.config.redis_db,
                    cluster_mode=self.config.redis_cluster_mode,
                    connection_pool_size=self.config.redis_connection_pool_size,
                    timeout=self.config.timeout_seconds
                )
                logger.info("Redis cache backend initialized")
            except Exception as e:
                logger.warning(f"Redis cache backend not available: {e}")
            
            # Database cache (if available)
            try:
                self.backends[CacheTier.DATABASE] = DatabaseCacheBackend(
                    table_name=self.config.db_cache_table
                )
                logger.info("Database cache backend initialized")
            except Exception as e:
                logger.warning(f"Database cache backend not available: {e}")
            
            # CDN cache (if configured)
            if self.config.cdn_enabled and self.config.cdn_base_url:
                try:
                    self.backends[CacheTier.CDN] = CDNCacheBackend(
                        base_url=self.config.cdn_base_url,
                        cache_control=self.config.cdn_cache_control
                    )
                    logger.info("CDN cache backend initialized")
                except Exception as e:
                    logger.warning(f"CDN cache backend not available: {e}")
            
        except Exception as e:
            logger.error(f"Error initializing cache backends: {e}")
    
    def _init_strategies(self):
        """Initialize cache strategies."""
        try:
            # Get default backends for strategies
            memory_backend = self.backends.get(CacheTier.MEMORY)
            redis_backend = self.backends.get(CacheTier.REDIS)
            db_backend = self.backends.get(CacheTier.DATABASE)
            
            # Cache-aside strategy (default)
            primary_backend = redis_backend or memory_backend
            if primary_backend:
                self.strategies[CacheStrategy.CACHE_ASIDE] = CacheAsideStrategy(
                    cache_backend=primary_backend
                )
            
            # Write-through strategy
            if redis_backend and db_backend:
                self.strategies[CacheStrategy.WRITE_THROUGH] = WriteThroughStrategy(
                    cache_backend=redis_backend,
                    data_store=db_backend
                )
            
            # Write-behind strategy
            if redis_backend:
                self.strategies[CacheStrategy.WRITE_BEHIND] = WriteBehindStrategy(
                    cache_backend=redis_backend,
                    data_store=db_backend
                )
            
            # Refresh-ahead strategy
            if redis_backend:
                self.strategies[CacheStrategy.REFRESH_AHEAD] = RefreshAheadStrategy(
                    cache_backend=redis_backend,
                    data_store=db_backend,
                    refresh_threshold=self.config.refresh_threshold
                )
            
        except Exception as e:
            logger.error(f"Error initializing cache strategies: {e}")
    
    async def get(
        self, 
        key: str, 
        profile: str = "default",
        loader_func: Optional[Callable] = None
    ) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache with fallback loading.
        
        Args:
            key: Cache key
            profile: Cache profile name (from CACHE_PROFILES)
            loader_func: Function to load data on cache miss
            
        Returns:
            Tuple of (value, was_cache_hit)
        """
        start_time = time.time()
        
        try:
            # Get cache profile configuration
            cache_config = CACHE_PROFILES.get(profile, {})
            tier = cache_config.get('tier', CacheTier.MEMORY)
            strategy = cache_config.get('strategy', CacheStrategy.CACHE_ASIDE)
            
            # Try multi-tier lookup for HYBRID
            if tier == CacheTier.HYBRID:
                value, hit = await self._hybrid_get(key, loader_func)
            else:
                # Use specific tier and strategy
                backend = self.backends.get(tier)
                strategy_handler = self.strategies.get(strategy)
                
                if backend and strategy_handler:
                    value = await strategy_handler.get(key, loader_func)
                    hit = value is not None
                elif backend:
                    value = await backend.get(key)
                    hit = value is not None
                    
                    # If miss and loader provided, load and cache
                    if not hit and loader_func:
                        value = await loader_func()
                        if value is not None:
                            await self.set(key, value, profile=profile)
                        hit = False
                else:
                    value, hit = None, False
            
            # Update metrics
            if hit:
                self.metrics.hits += 1
                if tier == CacheTier.MEMORY:
                    self.metrics.memory_hits += 1
                elif tier == CacheTier.REDIS:
                    self.metrics.redis_hits += 1
                elif tier == CacheTier.DATABASE:
                    self.metrics.db_hits += 1
            else:
                self.metrics.misses += 1
            
            # Update timing metrics
            operation_time = (time.time() - start_time) * 1000
            if hit:
                self.metrics.avg_get_time_ms = (
                    (self.metrics.avg_get_time_ms * self.metrics.hits + operation_time) /
                    (self.metrics.hits + 1)
                )
            
            return value, hit
            
        except Exception as e:
            logger.error(f"Error getting cache entry {key}: {e}")
            self.metrics.errors += 1
            return None, False
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        profile: str = "default",
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Set value in cache using profile configuration.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            profile: Cache profile name
            tags: Tags for invalidation
            
        Returns:
            Success status
        """
        start_time = time.time()
        
        try:
            # Get cache profile configuration
            cache_config = CACHE_PROFILES.get(profile, {})
            tier = cache_config.get('tier', CacheTier.MEMORY)
            strategy = cache_config.get('strategy', CacheStrategy.CACHE_ASIDE)
            default_ttl = cache_config.get('ttl', self.config.default_ttl)
            
            ttl = ttl or default_ttl
            tags = tags or cache_config.get('tags', [])
            
            # Register tags for invalidation
            if tags:
                self.invalidation.register_tag(key, tags)
            
            # Set using appropriate tier and strategy
            if tier == CacheTier.HYBRID:
                success = await self._hybrid_set(key, value, ttl)
            else:
                backend = self.backends.get(tier)
                strategy_handler = self.strategies.get(strategy)
                
                if strategy_handler:
                    success = await strategy_handler.set(key, value, ttl)
                elif backend:
                    success = await backend.set(key, value, ttl)
                else:
                    success = False
            
            # Update metrics
            self.metrics.sets += 1
            operation_time = (time.time() - start_time) * 1000
            self.metrics.avg_set_time_ms = (
                (self.metrics.avg_set_time_ms * (self.metrics.sets - 1) + operation_time) /
                self.metrics.sets
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting cache entry {key}: {e}")
            self.metrics.errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from all cache tiers."""
        try:
            success = False
            
            # Remove from all backends
            for backend in self.backends.values():
                if await backend.delete(key):
                    success = True
            
            # Unregister from tag mappings
            self.invalidation.unregister_key(key)
            
            # Update metrics
            if success:
                self.metrics.deletes += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting cache entry {key}: {e}")
            self.metrics.errors += 1
            return False
    
    async def exists(self, key: str, tier: Optional[CacheTier] = None) -> bool:
        """Check if key exists in cache."""
        try:
            if tier:
                backend = self.backends.get(tier)
                return await backend.exists(key) if backend else False
            else:
                # Check all tiers
                for backend in self.backends.values():
                    if await backend.exists(key):
                        return True
                return False
                
        except Exception as e:
            logger.error(f"Error checking cache key existence {key}: {e}")
            return False
    
    async def clear(self, tier: Optional[CacheTier] = None) -> bool:
        """Clear cache entries."""
        try:
            if tier:
                backend = self.backends.get(tier)
                return await backend.clear() if backend else False
            else:
                # Clear all tiers
                success = True
                for backend in self.backends.values():
                    if not await backend.clear():
                        success = False
                return success
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag."""
        return await self.invalidation.invalidate_by_tag(tag)
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        return await self.invalidation.invalidate_by_pattern(pattern)
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a specific user."""
        pattern = self.key_builder.build_user_pattern(user_id)
        return await self.invalidate_by_pattern(pattern)
    
    async def warm_cache(
        self, 
        keys_and_loaders: List[Tuple[str, Callable]], 
        profile: str = "default"
    ) -> int:
        """
        Warm cache with pre-loaded data.
        
        Args:
            keys_and_loaders: List of (key, loader_function) tuples
            profile: Cache profile to use
            
        Returns:
            Number of successfully warmed entries
        """
        success_count = 0
        
        for key, loader_func in keys_and_loaders:
            try:
                value = await loader_func()
                if value is not None and await self.set(key, value, profile=profile):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error warming cache key {key}: {e}")
        
        logger.info(f"Cache warming completed: {success_count}/{len(keys_and_loaders)} entries")
        return success_count
    
    async def _hybrid_get(self, key: str, loader_func: Optional[Callable]) -> Tuple[Optional[Any], bool]:
        """Get value using hybrid multi-tier lookup."""
        # Try memory cache first
        if CacheTier.MEMORY in self.backends:
            value = await self.backends[CacheTier.MEMORY].get(key)
            if value is not None:
                return value, True
        
        # Try Redis cache
        if CacheTier.REDIS in self.backends:
            value = await self.backends[CacheTier.REDIS].get(key)
            if value is not None:
                # Store in memory cache for faster future access
                if CacheTier.MEMORY in self.backends:
                    await self.backends[CacheTier.MEMORY].set(key, value, 300)  # 5 min
                return value, True
        
        # Try database cache
        if CacheTier.DATABASE in self.backends:
            value = await self.backends[CacheTier.DATABASE].get(key)
            if value is not None:
                # Store in upper tiers
                if CacheTier.REDIS in self.backends:
                    await self.backends[CacheTier.REDIS].set(key, value)
                if CacheTier.MEMORY in self.backends:
                    await self.backends[CacheTier.MEMORY].set(key, value, 300)
                return value, True
        
        # Cache miss - use loader if provided
        if loader_func:
            value = await loader_func()
            if value is not None:
                # Store in all available tiers
                await self._hybrid_set(key, value, self.config.default_ttl)
            return value, False
        
        return None, False
    
    async def _hybrid_set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in hybrid multi-tier setup."""
        success = False
        
        # Store in all available tiers
        for tier, backend in self.backends.items():
            try:
                tier_ttl = ttl
                
                # Adjust TTL for different tiers
                if tier == CacheTier.MEMORY:
                    tier_ttl = min(ttl, 300)  # Max 5 minutes for memory
                
                if await backend.set(key, value, tier_ttl):
                    success = True
            except Exception as e:
                logger.error(f"Error setting value in {tier} cache: {e}")
        
        return success
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        if self.config.enable_background_refresh:
            self._background_tasks.append(
                asyncio.create_task(self._metrics_reporter())
            )
            self._background_tasks.append(
                asyncio.create_task(self._cleanup_worker())
            )
    
    async def _metrics_reporter(self):
        """Background task to report cache metrics."""
        while True:
            try:
                await asyncio.sleep(self.config.metrics_interval)
                
                if self.config.enable_metrics:
                    logger.info(
                        f"Cache metrics - "
                        f"Hit ratio: {self.metrics.hit_ratio:.2%}, "
                        f"Hits: {self.metrics.hits}, "
                        f"Misses: {self.metrics.misses}, "
                        f"Errors: {self.metrics.errors}"
                    )
                
            except Exception as e:
                logger.error(f"Error in metrics reporter: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_worker(self):
        """Background task for cache maintenance."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Cleanup expired entries from memory cache
                if CacheTier.MEMORY in self.backends:
                    # This would need implementation in the backend
                    pass
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(60)
    
    def get_metrics(self) -> CacheMetrics:
        """Get current cache metrics."""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get cache system status."""
        return {
            "backends": list(self.backends.keys()),
            "strategies": list(self.strategies.keys()),
            "metrics": {
                "hit_ratio": self.metrics.hit_ratio,
                "total_operations": self.metrics.total_operations,
                "errors": self.metrics.errors
            },
            "background_tasks": len([t for t in self._background_tasks if not t.done()])
        }
    
    async def close(self):
        """Close cache manager and cleanup resources."""
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Close Redis connections
        if CacheTier.REDIS in self.backends:
            redis_backend = self.backends[CacheTier.REDIS]
            if hasattr(redis_backend, 'close'):
                await redis_backend.close()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager
