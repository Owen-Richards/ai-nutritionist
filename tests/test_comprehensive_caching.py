"""
Comprehensive test suite for the caching system.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import the caching components
from src.core.caching import (
    CacheManager,
    CacheConfig,
    CacheTier,
    CacheStrategy,
    MemoryCacheBackend,
    cached,
    invalidate_cache,
    get_cache_key_builder,
    user_data_cache,
    meal_plan_cache,
    recipe_cache
)


class TestMemoryCacheBackend:
    """Test the memory cache backend."""
    
    @pytest.fixture
    async def cache_backend(self):
        """Create a memory cache backend for testing."""
        backend = MemoryCacheBackend(max_size=10, default_ttl=60)
        yield backend
        await backend.clear()
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_backend):
        """Test basic set and get operations."""
        # Set a value
        result = await cache_backend.set("test_key", "test_value")
        assert result is True
        
        # Get the value
        value = await cache_backend.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache_backend):
        """Test getting a non-existent key."""
        value = await cache_backend.get("nonexistent")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_backend):
        """Test TTL expiration."""
        # Set with short TTL
        await cache_backend.set("expire_key", "expire_value", ttl=1)
        
        # Should exist immediately
        value = await cache_backend.get("expire_key")
        assert value == "expire_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        value = await cache_backend.get("expire_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache_backend):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(10):
            await cache_backend.set(f"key_{i}", f"value_{i}")
        
        # Access first key to make it recently used
        await cache_backend.get("key_0")
        
        # Add one more item (should evict LRU)
        await cache_backend.set("new_key", "new_value")
        
        # First key should still exist (was recently accessed)
        value = await cache_backend.get("key_0")
        assert value == "value_0"
        
        # One of the other keys should be evicted
        # (exact behavior depends on implementation)
        size = await cache_backend.get_size()
        assert size == 10
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_backend):
        """Test delete operation."""
        await cache_backend.set("delete_key", "delete_value")
        
        # Verify it exists
        value = await cache_backend.get("delete_key")
        assert value == "delete_value"
        
        # Delete it
        result = await cache_backend.delete("delete_key")
        assert result is True
        
        # Verify it's gone
        value = await cache_backend.get("delete_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_clear(self, cache_backend):
        """Test clear operation."""
        # Add some data
        await cache_backend.set("key1", "value1")
        await cache_backend.set("key2", "value2")
        
        # Clear cache
        result = await cache_backend.clear()
        assert result is True
        
        # Verify everything is gone
        assert await cache_backend.get("key1") is None
        assert await cache_backend.get("key2") is None
        assert await cache_backend.get_size() == 0


class TestCacheKeyBuilder:
    """Test the cache key builder."""
    
    @pytest.fixture
    def key_builder(self):
        """Create a cache key builder for testing."""
        return get_cache_key_builder()
    
    def test_build_basic_key(self, key_builder):
        """Test basic key building."""
        key = key_builder.build_key("user", "get", {"id": "123"})
        assert "ai_nutritionist" in key
        assert "user" in key
        assert "get" in key
        assert "params" in key
    
    def test_build_user_key(self, key_builder):
        """Test user-specific key building."""
        key = key_builder.build_user_key("user123", "profile")
        assert "user:user123" in key
        assert "profile" in key
    
    def test_build_meal_plan_key(self, key_builder):
        """Test meal plan key building."""
        key = key_builder.build_meal_plan_key("user123", "2023-W01", {"diet": "vegan"})
        assert "user:user123" in key
        assert "2023-W01" in key
        assert "params" in key
    
    def test_build_search_key(self, key_builder):
        """Test search key building."""
        key = key_builder.build_search_key("chicken", {"diet": "keto"}, "rating", 10)
        assert "search" in key
        assert "query" in key
        assert "params" in key
    
    def test_key_consistency(self, key_builder):
        """Test that identical parameters produce identical keys."""
        key1 = key_builder.build_key("user", "get", {"id": "123", "type": "profile"})
        key2 = key_builder.build_key("user", "get", {"type": "profile", "id": "123"})
        assert key1 == key2  # Order shouldn't matter
    
    def test_extract_user_id(self, key_builder):
        """Test extracting user ID from key."""
        key = key_builder.build_user_key("user123", "profile")
        extracted_id = key_builder.extract_user_id(key)
        assert extracted_id == "user123"
    
    def test_extract_entity(self, key_builder):
        """Test extracting entity from key."""
        key = key_builder.build_key("meal_plan", "get", {"id": "123"})
        entity = key_builder.extract_entity(key)
        assert entity == "meal_plan"


class TestCacheManager:
    """Test the cache manager."""
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a cache manager for testing."""
        config = CacheConfig(
            memory_cache_size=100,
            redis_host="mock_redis"  # Won't actually connect
        )
        manager = CacheManager(config)
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_get_set_basic(self, cache_manager):
        """Test basic get/set operations."""
        # Set a value
        result = await cache_manager.set("test_key", "test_value")
        assert result is True
        
        # Get the value
        value, hit = await cache_manager.get("test_key")
        assert value == "test_value"
        assert hit is True
    
    @pytest.mark.asyncio
    async def test_cache_miss_with_loader(self, cache_manager):
        """Test cache miss with loader function."""
        loader_called = False
        
        async def loader():
            nonlocal loader_called
            loader_called = True
            return "loaded_value"
        
        # Get with loader (cache miss)
        value, hit = await cache_manager.get("missing_key", loader_func=loader)
        assert value == "loaded_value"
        assert hit is False
        assert loader_called is True
        
        # Get again (cache hit)
        loader_called = False
        value, hit = await cache_manager.get("missing_key", loader_func=loader)
        assert value == "loaded_value"
        assert hit is True
        assert loader_called is False
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """Test delete operation."""
        await cache_manager.set("delete_key", "delete_value")
        
        # Verify it exists
        value, hit = await cache_manager.get("delete_key")
        assert hit is True
        
        # Delete it
        result = await cache_manager.delete("delete_key")
        assert result is True
        
        # Verify it's gone
        value, hit = await cache_manager.get("delete_key")
        assert hit is False
    
    @pytest.mark.asyncio
    async def test_cache_profiles(self, cache_manager):
        """Test using different cache profiles."""
        # Set with user_data profile
        await cache_manager.set("user_key", "user_value", profile="user_data")
        
        # Set with api_response profile
        await cache_manager.set("api_key", "api_value", profile="api_response")
        
        # Both should be retrievable
        user_value, _ = await cache_manager.get("user_key", profile="user_data")
        api_value, _ = await cache_manager.get("api_key", profile="api_response")
        
        assert user_value == "user_value"
        assert api_value == "api_value"
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_manager):
        """Test cache warming."""
        async def loader1():
            return "value1"
        
        async def loader2():
            return "value2"
        
        keys_and_loaders = [
            ("warm_key1", loader1),
            ("warm_key2", loader2)
        ]
        
        # Warm cache
        warmed = await cache_manager.warm_cache(keys_and_loaders)
        assert warmed == 2
        
        # Verify values are cached
        value1, hit1 = await cache_manager.get("warm_key1")
        value2, hit2 = await cache_manager.get("warm_key2")
        
        assert value1 == "value1" and hit1 is True
        assert value2 == "value2" and hit2 is True
    
    @pytest.mark.asyncio
    async def test_metrics(self, cache_manager):
        """Test cache metrics tracking."""
        # Perform some operations
        await cache_manager.set("metric_key", "metric_value")
        await cache_manager.get("metric_key")  # Hit
        await cache_manager.get("nonexistent")  # Miss
        
        metrics = cache_manager.get_metrics()
        assert metrics.hits >= 1
        assert metrics.misses >= 1
        assert metrics.sets >= 1
        assert metrics.hit_ratio >= 0


class TestCacheDecorators:
    """Test caching decorators."""
    
    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test the @cached decorator."""
        call_count = 0
        
        @cached(ttl=60, profile="api_response")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return x * 2
        
        # First call - should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call - should use cache
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented
        
        # Different argument - should execute function
        result3 = await expensive_function(6)
        assert result3 == 12
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_decorator(self):
        """Test the @invalidate_cache decorator."""
        call_count = 0
        
        @cached(ttl=60, profile="user_data", tags=["user"])
        async def get_user(user_id: str) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": f"User {user_id}"}
        
        @invalidate_cache(tags=["user"])
        async def update_user(user_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        # Cache user data
        user1 = await get_user("123")
        assert call_count == 1
        
        # Get again (cached)
        user2 = await get_user("123")
        assert call_count == 1
        
        # Update user (invalidates cache)
        await update_user("123", {"name": "Updated"})
        
        # Get again (cache miss due to invalidation)
        user3 = await get_user("123")
        assert call_count == 2
    
    def test_sync_cached_decorator(self):
        """Test the @cached decorator with sync functions."""
        call_count = 0
        
        @cached(ttl=60, profile="computed_results")
        def expensive_sync_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate work
            return x * 3
        
        # First call
        result1 = expensive_sync_function(4)
        assert result1 == 12
        assert call_count == 1
        
        # Second call (cached)
        result2 = expensive_sync_function(4)
        assert result2 == 12
        assert call_count == 1


class TestApplicationCaches:
    """Test application-specific cache implementations."""
    
    @pytest.mark.asyncio
    async def test_user_data_cache(self):
        """Test user data caching."""
        user_id = "test_user_123"
        profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "preferences": {"diet": "vegetarian"}
        }
        
        # Set user profile
        result = await user_data_cache.set_user_profile(user_id, profile_data)
        assert result is True
        
        # Get user profile
        retrieved = await user_data_cache.get_user_profile(user_id)
        assert retrieved == profile_data
        
        # Invalidate user cache
        invalidated = await user_data_cache.invalidate_user_cache(user_id)
        # Note: Actual count depends on implementation
        
        # Profile should be gone after invalidation
        retrieved_after = await user_data_cache.get_user_profile(user_id)
        assert retrieved_after is None
    
    @pytest.mark.asyncio
    async def test_meal_plan_cache(self):
        """Test meal plan caching."""
        user_id = "test_user_123"
        week_start = "2023-W01"
        meal_plan_data = {
            "user_id": user_id,
            "week_start": week_start,
            "meals": [{"day": "Monday", "breakfast": "Oatmeal"}]
        }
        
        # Set meal plan
        result = await meal_plan_cache.set_meal_plan(
            user_id, week_start, meal_plan_data
        )
        assert result is True
        
        # Test invalidation
        await meal_plan_cache.invalidate_meal_plans(user_id)
    
    @pytest.mark.asyncio
    async def test_recipe_cache(self):
        """Test recipe caching."""
        recipe_id = "recipe_123"
        recipe_data = {
            "id": recipe_id,
            "name": "Test Recipe",
            "ingredients": ["ingredient1", "ingredient2"]
        }
        
        # Set recipe
        result = await recipe_cache.set_recipe(recipe_id, recipe_data)
        assert result is True


class TestCacheIntegration:
    """Integration tests for the complete caching system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test a complete end-to-end caching workflow."""
        # Simulate a user service that uses caching
        class MockUserService:
            @cached(ttl=300, profile="user_data", tags=["user"])
            async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
                # Simulate database call
                await asyncio.sleep(0.01)
                return {
                    "id": user_id,
                    "name": f"User {user_id}",
                    "created_at": "2023-01-01T00:00:00Z"
                }
            
            @invalidate_cache(tags=["user"])
            async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
                # Simulate database update
                await asyncio.sleep(0.01)
                return True
        
        service = MockUserService()
        
        # Test caching
        start_time = time.time()
        profile1 = await service.get_user_profile("123")
        first_call_time = time.time() - start_time
        
        # Second call should be faster (cached)
        start_time = time.time()
        profile2 = await service.get_user_profile("123")
        second_call_time = time.time() - start_time
        
        assert profile1 == profile2
        assert second_call_time < first_call_time  # Cache should be faster
        
        # Update should invalidate cache
        await service.update_user_profile("123", {"name": "Updated User"})
        
        # Next call should hit database again
        profile3 = await service.get_user_profile("123")
        assert profile3["name"] == "User 123"  # Original data (mock doesn't actually update)
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self):
        """Test error handling in caching operations."""
        @cached(ttl=60, profile="api_response")
        async def function_that_fails(should_fail: bool) -> str:
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Function that succeeds should be cached
        result1 = await function_that_fails(False)
        assert result1 == "success"
        
        # Function that fails should not break caching
        with pytest.raises(ValueError):
            await function_that_fails(True)
        
        # Cached result should still be available
        result2 = await function_that_fails(False)
        assert result2 == "success"


# Performance benchmarks
class TestCachePerformance:
    """Performance tests for the caching system."""
    
    @pytest.mark.asyncio
    async def test_memory_cache_performance(self):
        """Test memory cache performance."""
        backend = MemoryCacheBackend(max_size=1000)
        
        # Measure set performance
        start_time = time.time()
        for i in range(100):
            await backend.set(f"key_{i}", f"value_{i}")
        set_time = time.time() - start_time
        
        # Measure get performance
        start_time = time.time()
        for i in range(100):
            await backend.get(f"key_{i}")
        get_time = time.time() - start_time
        
        print(f"Memory cache - Set: {set_time:.4f}s, Get: {get_time:.4f}s")
        
        # Performance assertions (adjust based on expectations)
        assert set_time < 1.0  # Should be fast
        assert get_time < 0.1  # Gets should be very fast
    
    @pytest.mark.asyncio
    async def test_cache_decorator_overhead(self):
        """Test overhead of cache decorators."""
        call_count = 0
        
        @cached(ttl=60, profile="api_response")
        async def cached_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        async def uncached_function(x: int) -> int:
            return x * 2
        
        # Warm up cache
        await cached_function(1)
        
        # Measure cached function (cache hit)
        start_time = time.time()
        for i in range(100):
            await cached_function(1)
        cached_time = time.time() - start_time
        
        # Measure uncached function
        start_time = time.time()
        for i in range(100):
            await uncached_function(1)
        uncached_time = time.time() - start_time
        
        print(f"Cached: {cached_time:.4f}s, Uncached: {uncached_time:.4f}s")
        
        # Cache hits should add minimal overhead
        overhead_ratio = cached_time / uncached_time if uncached_time > 0 else 1
        assert overhead_ratio < 5.0  # Less than 5x overhead acceptable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
