"""
Cache strategy implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import asyncio
import logging

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for different use cases."""
    
    CACHE_ASIDE = "cache_aside"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    
    TTL = "ttl"
    EVENT_BASED = "event_based"
    VERSIONED = "versioned"
    TAG_BASED = "tag_based"


class CacheStrategyHandler(ABC):
    """Abstract base class for cache strategy implementations."""
    
    @abstractmethod
    async def get(self, key: str, loader_func: Optional[callable] = None) -> Any:
        """Get value from cache using this strategy."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache using this strategy."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache using this strategy."""
        pass


class CacheAsideStrategy(CacheStrategyHandler):
    """
    Cache-aside (lazy loading) strategy.
    Application manages cache explicitly.
    """
    
    def __init__(self, cache_backend, data_store=None):
        self.cache_backend = cache_backend
        self.data_store = data_store
    
    async def get(self, key: str, loader_func: Optional[callable] = None) -> Any:
        """
        Get value from cache, load from store if miss.
        
        Args:
            key: Cache key
            loader_func: Function to load data on cache miss
            
        Returns:
            Cached or loaded value
        """
        # Try cache first
        value = await self.cache_backend.get(key)
        
        if value is not None:
            return value
        
        # Cache miss - load from source
        if loader_func:
            try:
                value = await loader_func()
                if value is not None:
                    # Store in cache for future use
                    await self.cache_backend.set(key, value)
                return value
            except Exception as e:
                logger.error(f"Error loading data for key {key}: {e}")
                return None
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache only."""
        return await self.cache_backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache only."""
        return await self.cache_backend.delete(key)


class WriteThroughStrategy(CacheStrategyHandler):
    """
    Write-through strategy.
    Writes go to cache and data store simultaneously.
    """
    
    def __init__(self, cache_backend, data_store):
        self.cache_backend = cache_backend
        self.data_store = data_store
    
    async def get(self, key: str, loader_func: Optional[callable] = None) -> Any:
        """Get value from cache, load from store if miss."""
        # Try cache first
        value = await self.cache_backend.get(key)
        
        if value is not None:
            return value
        
        # Cache miss - load from data store
        if hasattr(self.data_store, 'get'):
            try:
                value = await self.data_store.get(key)
                if value is not None:
                    # Store in cache
                    await self.cache_backend.set(key, value)
                return value
            except Exception as e:
                logger.error(f"Error loading from data store for key {key}: {e}")
        
        # Fallback to loader function
        if loader_func:
            try:
                value = await loader_func()
                if value is not None:
                    await self.cache_backend.set(key, value)
                return value
            except Exception as e:
                logger.error(f"Error loading data for key {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in both cache and data store."""
        try:
            # Write to both cache and store simultaneously
            cache_task = self.cache_backend.set(key, value, ttl)
            store_task = None
            
            if hasattr(self.data_store, 'set'):
                store_task = self.data_store.set(key, value)
            
            if store_task:
                cache_result, store_result = await asyncio.gather(
                    cache_task, store_task, return_exceptions=True
                )
                
                # Both must succeed for write-through
                if isinstance(cache_result, Exception):
                    logger.error(f"Cache write failed: {cache_result}")
                    return False
                if isinstance(store_result, Exception):
                    logger.error(f"Store write failed: {store_result}")
                    return False
                
                return cache_result and store_result
            else:
                return await cache_task
            
        except Exception as e:
            logger.error(f"Error in write-through for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete from both cache and data store."""
        try:
            cache_task = self.cache_backend.delete(key)
            store_task = None
            
            if hasattr(self.data_store, 'delete'):
                store_task = self.data_store.delete(key)
            
            if store_task:
                cache_result, store_result = await asyncio.gather(
                    cache_task, store_task, return_exceptions=True
                )
                
                # Return true if either succeeds
                cache_success = not isinstance(cache_result, Exception) and cache_result
                store_success = not isinstance(store_result, Exception) and store_result
                
                return cache_success or store_success
            else:
                return await cache_task
            
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False


class WriteBehindStrategy(CacheStrategyHandler):
    """
    Write-behind (write-back) strategy.
    Writes go to cache immediately, data store updated asynchronously.
    """
    
    def __init__(self, cache_backend, data_store, batch_size: int = 100):
        self.cache_backend = cache_backend
        self.data_store = data_store
        self.batch_size = batch_size
        self.write_queue: Set[str] = set()
        self.write_task: Optional[asyncio.Task] = None
    
    async def get(self, key: str, loader_func: Optional[callable] = None) -> Any:
        """Get value from cache first, then data store."""
        # Try cache first
        value = await self.cache_backend.get(key)
        
        if value is not None:
            return value
        
        # Cache miss - load from data store
        if hasattr(self.data_store, 'get'):
            try:
                value = await self.data_store.get(key)
                if value is not None:
                    # Store in cache
                    await self.cache_backend.set(key, value)
                return value
            except Exception as e:
                logger.error(f"Error loading from data store for key {key}: {e}")
        
        # Fallback to loader function
        if loader_func:
            try:
                value = await loader_func()
                if value is not None:
                    await self.cache_backend.set(key, value)
                return value
            except Exception as e:
                logger.error(f"Error loading data for key {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache immediately, queue for data store write."""
        try:
            # Write to cache immediately
            cache_result = await self.cache_backend.set(key, value, ttl)
            
            if cache_result:
                # Queue for background write to data store
                self.write_queue.add(key)
                
                # Start background writer if not already running
                if not self.write_task or self.write_task.done():
                    self.write_task = asyncio.create_task(self._background_writer())
            
            return cache_result
            
        except Exception as e:
            logger.error(f"Error in write-behind for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete from cache immediately, queue for data store delete."""
        try:
            # Remove from write queue if present
            self.write_queue.discard(key)
            
            # Delete from cache
            cache_result = await self.cache_backend.delete(key)
            
            # Delete from data store if it has delete method
            if hasattr(self.data_store, 'delete'):
                asyncio.create_task(self.data_store.delete(key))
            
            return cache_result
            
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False
    
    async def _background_writer(self):
        """Background task to write cached data to data store."""
        while self.write_queue:
            try:
                # Process batch of writes
                batch = list(self.write_queue)[:self.batch_size]
                
                for key in batch:
                    try:
                        # Get value from cache
                        value = await self.cache_backend.get(key)
                        
                        if value is not None and hasattr(self.data_store, 'set'):
                            await self.data_store.set(key, value)
                        
                        # Remove from queue after successful write
                        self.write_queue.discard(key)
                        
                    except Exception as e:
                        logger.error(f"Error writing key {key} to data store: {e}")
                        # Keep in queue for retry
                
                # Brief pause before next batch
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in background writer: {e}")
                await asyncio.sleep(1)


class RefreshAheadStrategy(CacheStrategyHandler):
    """
    Refresh-ahead strategy.
    Proactively refreshes cache entries before they expire.
    """
    
    def __init__(self, cache_backend, data_store, refresh_threshold: float = 0.8):
        self.cache_backend = cache_backend
        self.data_store = data_store
        self.refresh_threshold = refresh_threshold
        self.refresh_tasks: Dict[str, asyncio.Task] = {}
    
    async def get(self, key: str, loader_func: Optional[callable] = None) -> Any:
        """Get value and schedule refresh if needed."""
        # Try cache first
        value = await self.cache_backend.get(key)
        
        if value is not None:
            # Check if refresh is needed
            if await self._should_refresh(key):
                await self._schedule_refresh(key, loader_func)
            
            return value
        
        # Cache miss - load from source
        if loader_func:
            try:
                value = await loader_func()
                if value is not None:
                    await self.cache_backend.set(key, value)
                return value
            except Exception as e:
                logger.error(f"Error loading data for key {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        return await self.cache_backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache and cancel any refresh tasks."""
        # Cancel refresh task if running
        if key in self.refresh_tasks:
            self.refresh_tasks[key].cancel()
            del self.refresh_tasks[key]
        
        return await self.cache_backend.delete(key)
    
    async def _should_refresh(self, key: str) -> bool:
        """Check if cache entry should be refreshed."""
        # This would need to be implemented based on cache backend capabilities
        # For now, return False
        return False
    
    async def _schedule_refresh(self, key: str, loader_func: Optional[callable]):
        """Schedule background refresh for cache entry."""
        if key not in self.refresh_tasks or self.refresh_tasks[key].done():
            self.refresh_tasks[key] = asyncio.create_task(
                self._refresh_cache_entry(key, loader_func)
            )
    
    async def _refresh_cache_entry(self, key: str, loader_func: Optional[callable]):
        """Refresh cache entry in background."""
        try:
            if loader_func:
                value = await loader_func()
                if value is not None:
                    await self.cache_backend.set(key, value)
        except Exception as e:
            logger.error(f"Error refreshing cache entry {key}: {e}")
        finally:
            # Clean up task reference
            if key in self.refresh_tasks:
                del self.refresh_tasks[key]


class InvalidationHandler:
    """Handles cache invalidation using various strategies."""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.tag_mappings: Dict[str, Set[str]] = {}  # tag -> set of keys
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag."""
        if tag in self.tag_mappings:
            keys_to_invalidate = self.tag_mappings[tag].copy()
            count = 0
            
            for key in keys_to_invalidate:
                if await self.cache_manager.delete(key):
                    count += 1
            
            # Clear tag mapping
            del self.tag_mappings[tag]
            return count
        
        return 0
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        # This would need backend-specific implementation
        # Redis supports pattern-based deletion
        if hasattr(self.cache_manager, 'delete_by_pattern'):
            return await self.cache_manager.delete_by_pattern(pattern)
        
        return 0
    
    def register_tag(self, key: str, tags: List[str]):
        """Register tags for a cache key."""
        for tag in tags:
            if tag not in self.tag_mappings:
                self.tag_mappings[tag] = set()
            self.tag_mappings[tag].add(key)
    
    def unregister_key(self, key: str):
        """Remove key from all tag mappings."""
        for tag_set in self.tag_mappings.values():
            tag_set.discard(key)
