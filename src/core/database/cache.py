"""
Query result caching for improved performance.
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import pickle

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Different caching strategies."""
    
    WRITE_THROUGH = "write_through"      # Write to cache and DB simultaneously
    WRITE_BEHIND = "write_behind"        # Write to cache first, DB later
    CACHE_ASIDE = "cache_aside"          # Application manages cache manually
    READ_THROUGH = "read_through"        # Cache loads from DB on miss


@dataclass
class CacheConfig:
    """Configuration for query cache."""
    
    # Cache settings
    default_ttl: int = 3600  # Default TTL in seconds
    max_size: int = 10000    # Maximum number of cached items
    compression_enabled: bool = True
    
    # Memory cache settings
    enable_memory_cache: bool = True
    memory_cache_size: int = 1000
    
    # Performance settings
    cache_timeout: float = 0.1  # Timeout for cache operations
    background_refresh: bool = True
    refresh_threshold: float = 0.8  # Refresh when TTL is 80% expired
    
    # Monitoring
    enable_metrics: bool = True


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    errors: int = 0
    total_operations: int = 0
    avg_hit_time_ms: float = 0.0
    avg_miss_time_ms: float = 0.0
    hit_ratio: float = 0.0
    memory_usage_bytes: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def update_hit_ratio(self):
        """Update hit ratio calculation."""
        total = self.hits + self.misses
        self.hit_ratio = self.hits / total if total > 0 else 0.0


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""
    
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    @property
    def time_to_expiry(self) -> float:
        """Get time until expiry in seconds."""
        return (self.expires_at - datetime.utcnow()).total_seconds()
    
    def should_refresh(self, threshold: float = 0.8) -> bool:
        """Check if entry should be refreshed based on threshold."""
        if self.is_expired:
            return True
        
        total_ttl = (self.expires_at - self.created_at).total_seconds()
        remaining_ttl = self.time_to_expiry
        
        return (remaining_ttl / total_ttl) < (1.0 - threshold)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def get_size(self) -> int:
        """Get current cache size."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from memory cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                # Update access tracking
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                
                # Move to end of access order (most recently used)
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                
                return entry
            elif entry:
                # Entry exists but is expired
                await self._remove_entry(key)
            
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in memory cache."""
        async with self._lock:
            try:
                # Create cache entry
                now = datetime.utcnow()
                expires_at = now + timedelta(seconds=ttl)
                
                # Estimate size (rough approximation)
                size_bytes = len(pickle.dumps(value)) if value else 0
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=now,
                    expires_at=expires_at,
                    size_bytes=size_bytes
                )
                
                # Check if we need to evict entries
                if len(self._cache) >= self.max_size:
                    await self._evict_lru()
                
                # Store entry
                self._cache[key] = entry
                
                # Update access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                
                return True
                
            except Exception as e:
                logger.error(f"Error setting cache entry {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        async with self._lock:
            return await self._remove_entry(key)
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            return True
    
    async def get_size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self._cache)
    
    async def _remove_entry(self, key: str) -> bool:
        """Remove entry from cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False
    
    async def _evict_lru(self):
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order[0]
            await self._remove_entry(lru_key)


class QueryCache:
    """
    Multi-tier query result cache with performance optimization.
    
    Features:
    - Memory + DynamoDB caching
    - Automatic cache warming
    - Background refresh
    - Performance monitoring
    - LRU eviction
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.metrics = CacheMetrics()
        
        # Initialize backends
        self.backends: List[CacheBackend] = []
        
        if config.enable_memory_cache:
            self.backends.append(MemoryCacheBackend(config.memory_cache_size))
        
        # Background tasks
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        if config.background_refresh:
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())
    
    async def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache.
        
        Returns:
            Tuple of (value, was_cache_hit)
        """
        start_time = time.time()
        
        try:
            # Try each backend in order (memory first, then distributed)
            for i, backend in enumerate(self.backends):
                entry = await backend.get(key)
                if entry:
                    # Update metrics
                    self.metrics.hits += 1
                    self.metrics.total_operations += 1
                    
                    hit_time = (time.time() - start_time) * 1000
                    self.metrics.avg_hit_time_ms = (
                        (self.metrics.avg_hit_time_ms * (self.metrics.hits - 1) + hit_time) / 
                        self.metrics.hits
                    )
                    
                    # Check if entry needs refresh
                    if entry.should_refresh(self.config.refresh_threshold):
                        await self._schedule_refresh(key)
                    
                    self.metrics.update_hit_ratio()
                    return entry.value, True
            
            # Cache miss
            self.metrics.misses += 1
            self.metrics.total_operations += 1
            
            miss_time = (time.time() - start_time) * 1000
            self.metrics.avg_miss_time_ms = (
                (self.metrics.avg_miss_time_ms * (self.metrics.misses - 1) + miss_time) / 
                self.metrics.misses
            )
            
            self.metrics.update_hit_ratio()
            return None, False
            
        except Exception as e:
            logger.error(f"Error getting cache entry {key}: {e}")
            self.metrics.errors += 1
            return None, False
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH
    ) -> bool:
        """Set value in cache with specified strategy."""
        ttl = ttl or self.config.default_ttl
        
        try:
            if strategy == CacheStrategy.WRITE_THROUGH:
                # Write to all backends simultaneously
                tasks = [backend.set(key, value, ttl) for backend in self.backends]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return all(isinstance(r, bool) and r for r in results)
            
            elif strategy == CacheStrategy.WRITE_BEHIND:
                # Write to memory cache first, then background write to others
                if self.backends:
                    success = await self.backends[0].set(key, value, ttl)
                    return success
            
            elif strategy == CacheStrategy.CACHE_ASIDE:
                # Application managed - just store in first backend
                if self.backends:
                    return await self.backends[0].set(key, value, ttl)
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting cache entry {key}: {e}")
            self.metrics.errors += 1
            return False
    
    def create_cache_key(
        self, 
        operation: str, 
        table_name: str, 
        params: Dict[str, Any]
    ) -> str:
        """Create standardized cache key."""
        # Sort parameters for consistent keys
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        
        # Create hash-based key
        key_data = f"{operation}:{table_name}:{sorted_params}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        
        return f"query:{operation}:{table_name}:{key_hash}"
    
    @staticmethod
    def make_key(statement: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Legacy method for backward compatibility."""
        data = json.dumps({"statement": statement, "params": params or {}}, sort_keys=True)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    
    async def _schedule_refresh(self, key: str):
        """Schedule background refresh for expiring cache entry."""
        if key not in self._refresh_tasks:
            self._refresh_tasks[key] = asyncio.create_task(
                self._refresh_entry(key)
            )
    
    async def _refresh_entry(self, key: str):
        """Refresh cache entry in background."""
        # This would need to be implemented by the application
        # as it requires knowledge of how to reload the data
        pass
    
    async def _cleanup_worker(self):
        """Background worker to clean up expired entries and completed tasks."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Clean up completed refresh tasks
                completed_tasks = [
                    key for key, task in self._refresh_tasks.items()
                    if task.done()
                ]
                
                for key in completed_tasks:
                    del self._refresh_tasks[key]
                
                logger.debug(f"Cleaned up {len(completed_tasks)} completed refresh tasks")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup worker: {e}")


# Global cache instance
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    global _query_cache
    
    if _query_cache is None:
        config = CacheConfig()
        _query_cache = QueryCache(config)
    
    return _query_cache

    def set(self, key: str, payload: Any, *, ttl: Optional[float] = None) -> None:
        expires = time.time() + (ttl if ttl is not None else self._ttl)
        with self._lock:
            self._store[key] = CacheEntry(payload=payload, expires_at=expires)

    def invalidate(self, key: Optional[str] = None, *, predicate: Optional[Callable[[str, CacheEntry], bool]] = None) -> None:
        with self._lock:
            if key is not None:
                self._store.pop(key, None)
                return
            if predicate:
                keys = [candidate for candidate, entry in self._store.items() if predicate(candidate, entry)]
                for candidate in keys:
                    self._store.pop(candidate, None)
                return
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            valid = [entry for entry in self._store.values() if not entry.expired()]
        return {
            "strategy": self._strategy.value,
            "entries": len(valid),
            "avg_hits": sum(entry.hit_count for entry in valid) / len(valid) if valid else 0,
        }

