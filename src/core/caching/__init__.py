"""
Comprehensive caching system for AI Nutritionist application.

This module provides a multi-tier caching system with:
- Application-level (in-memory) caching
- Redis distributed caching
- CDN caching support
- Database query caching
- Multiple cache strategies and invalidation patterns
"""

from .cache_manager import CacheManager, get_cache_manager
from .strategies import CacheStrategy, InvalidationStrategy
from .backends import (
    MemoryCacheBackend,
    RedisCacheBackend,
    CDNCacheBackend,
    DatabaseCacheBackend
)
from .decorators import cached, invalidate_cache, cache_result, conditional_cache, memoize
from .keys import CacheKeyBuilder, get_cache_key_builder
from .config import CacheConfig, CacheTier, CacheMetrics, CACHE_PROFILES
from .application import (
    user_data_cache,
    meal_plan_cache,
    recipe_cache,
    nutrition_cache,
    session_cache,
    computed_results_cache,
    api_response_cache,
    smart_preloader
)

__all__ = [
    # Core classes
    'CacheManager',
    'get_cache_manager',
    'CacheStrategy',
    'InvalidationStrategy',
    
    # Backends
    'MemoryCacheBackend',
    'RedisCacheBackend',
    'CDNCacheBackend',
    'DatabaseCacheBackend',
    
    # Decorators
    'cached',
    'invalidate_cache',
    'cache_result',
    'conditional_cache',
    'memoize',
    
    # Key building
    'CacheKeyBuilder',
    'get_cache_key_builder',
    
    # Configuration
    'CacheConfig',
    'CacheTier',
    'CacheMetrics',
    'CACHE_PROFILES',
    
    # Application-specific caches
    'user_data_cache',
    'meal_plan_cache',
    'recipe_cache',
    'nutrition_cache',
    'session_cache',
    'computed_results_cache',
    'api_response_cache',
    'smart_preloader'
]
