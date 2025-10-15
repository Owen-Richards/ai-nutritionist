"""
Caching decorators for easy integration with existing code.
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Awaitable
from .cache_manager import get_cache_manager
from .keys import get_cache_key_builder

logger = logging.getLogger(__name__)

T = TypeVar('T')


def cached(
    ttl: Optional[int] = None,
    profile: str = "default",
    key_template: Optional[str] = None,
    tags: Optional[List[str]] = None,
    condition: Optional[Callable] = None,
    serializer: Optional[Callable] = None,
    deserializer: Optional[Callable] = None
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        profile: Cache profile name
        key_template: Custom key template with {arg} placeholders
        tags: Tags for cache invalidation
        condition: Function to determine if result should be cached
        serializer: Custom serialization function
        deserializer: Custom deserialization function
    
    Usage:
        @cached(ttl=3600, profile="user_data", tags=["user"])
        async def get_user_profile(user_id: str):
            return await load_user_from_db(user_id)
        
        @cached(key_template="recipe:search:{query}:{filters}")
        async def search_recipes(query: str, filters: dict):
            return await search_api(query, filters)
    """
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache_manager = get_cache_manager()
        key_builder = get_cache_key_builder()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Build cache key
            cache_key = _build_cache_key(
                func, args, kwargs, key_template, key_builder
            )
            
            # Check condition if provided
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)
            
            # Try to get from cache
            value, hit = await cache_manager.get(
                cache_key, 
                profile=profile,
                loader_func=lambda: func(*args, **kwargs)
            )
            
            if hit:
                # Deserialize if needed
                if deserializer:
                    value = deserializer(value)
                return value
            
            # Cache miss - execute function
            result = await func(*args, **kwargs)
            
            # Cache result if condition is met
            if result is not None and (not condition or condition(*args, **kwargs)):
                # Serialize if needed
                cache_value = serializer(result) if serializer else result
                
                await cache_manager.set(
                    cache_key, 
                    cache_value, 
                    ttl=ttl,
                    profile=profile,
                    tags=tags
                )
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For sync functions, we need to handle caching differently
            cache_key = _build_cache_key(
                func, args, kwargs, key_template, key_builder
            )
            
            # Check condition if provided
            if condition and not condition(*args, **kwargs):
                return func(*args, **kwargs)
            
            # Try to get from cache (sync)
            try:
                loop = asyncio.get_event_loop()
                value, hit = loop.run_until_complete(
                    cache_manager.get(cache_key, profile=profile)
                )
                
                if hit:
                    if deserializer:
                        value = deserializer(value)
                    return value
            except Exception as e:
                logger.warning(f"Error getting cache for sync function: {e}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None and (not condition or condition(*args, **kwargs)):
                try:
                    cache_value = serializer(result) if serializer else result
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        cache_manager.set(
                            cache_key, 
                            cache_value, 
                            ttl=ttl,
                            profile=profile,
                            tags=tags
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error setting cache for sync function: {e}")
            
            return result
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(
    pattern: Optional[str] = None,
    tags: Optional[List[str]] = None,
    keys: Optional[List[str]] = None
):
    """
    Decorator for cache invalidation after function execution.
    
    Args:
        pattern: Key pattern to invalidate
        tags: Tags to invalidate
        keys: Specific keys to invalidate
    
    Usage:
        @invalidate_cache(tags=["user"])
        async def update_user_profile(user_id: str, data: dict):
            return await save_user_to_db(user_id, data)
        
        @invalidate_cache(pattern="recipe:search:*")
        async def add_new_recipe(recipe: dict):
            return await save_recipe(recipe)
    """
    
    def decorator(func: Callable) -> Callable:
        cache_manager = get_cache_manager()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)
            
            # Then invalidate cache
            try:
                await _invalidate_cache_entries(
                    cache_manager, pattern, tags, keys, func, args, kwargs
                )
            except Exception as e:
                logger.error(f"Error invalidating cache: {e}")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Execute function first
            result = func(*args, **kwargs)
            
            # Then invalidate cache
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    _invalidate_cache_entries(
                        cache_manager, pattern, tags, keys, func, args, kwargs
                    )
                )
            except Exception as e:
                logger.error(f"Error invalidating cache: {e}")
            
            return result
        
        # Return appropriate wrapper
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_result(
    key: str,
    ttl: Optional[int] = None,
    profile: str = "default",
    tags: Optional[List[str]] = None
):
    """
    Simple decorator for caching with a fixed key.
    
    Args:
        key: Fixed cache key
        ttl: Time to live in seconds
        profile: Cache profile name
        tags: Tags for cache invalidation
    
    Usage:
        @cache_result("system:config", ttl=3600)
        async def get_system_config():
            return await load_config()
    """
    
    def decorator(func: Callable) -> Callable:
        cache_manager = get_cache_manager()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Try cache first
            value, hit = await cache_manager.get(key, profile=profile)
            
            if hit:
                return value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache_manager.set(key, result, ttl=ttl, profile=profile, tags=tags)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                loop = asyncio.get_event_loop()
                value, hit = loop.run_until_complete(
                    cache_manager.get(key, profile=profile)
                )
                
                if hit:
                    return value
            except Exception as e:
                logger.warning(f"Error getting cache: {e}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        cache_manager.set(key, result, ttl=ttl, profile=profile, tags=tags)
                    )
                except Exception as e:
                    logger.warning(f"Error setting cache: {e}")
            
            return result
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def conditional_cache(condition_func: Callable, **cache_kwargs):
    """
    Decorator for conditional caching based on runtime conditions.
    
    Args:
        condition_func: Function that returns True if caching should be used
        **cache_kwargs: Arguments passed to @cached decorator
    
    Usage:
        @conditional_cache(
            lambda user_id: user_id != "admin",
            ttl=1800,
            profile="user_data"
        )
        async def get_user_data(user_id: str):
            return await load_user_data(user_id)
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check condition
            if condition_func(*args, **kwargs):
                # Apply caching
                cached_func = cached(**cache_kwargs)(func)
                return await cached_func(*args, **kwargs)
            else:
                # No caching
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check condition
            if condition_func(*args, **kwargs):
                # Apply caching
                cached_func = cached(**cache_kwargs)(func)
                return cached_func(*args, **kwargs)
            else:
                # No caching
                return func(*args, **kwargs)
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def memoize(maxsize: int = 128, ttl: Optional[int] = None):
    """
    Simple memoization decorator with LRU eviction.
    
    Args:
        maxsize: Maximum number of cached results
        ttl: Time to live in seconds
    
    Usage:
        @memoize(maxsize=100, ttl=300)
        def expensive_calculation(x, y):
            return x ** y + complex_math(x, y)
    """
    
    def decorator(func: Callable) -> Callable:
        cache = {}
        access_order = []
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = _make_key(args, kwargs)
            current_time = asyncio.get_event_loop().time()
            
            # Check cache
            if key in cache:
                value, timestamp = cache[key]
                
                # Check TTL
                if ttl is None or (current_time - timestamp) < ttl:
                    # Move to end (most recently used)
                    access_order.remove(key)
                    access_order.append(key)
                    return value
                else:
                    # Expired
                    del cache[key]
                    access_order.remove(key)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache[key] = (result, current_time)
            access_order.append(key)
            
            # Evict if necessary
            while len(cache) > maxsize:
                lru_key = access_order.pop(0)
                del cache[lru_key]
            
            return result
        
        # Add cache management methods
        wrapper.cache_clear = lambda: cache.clear() or access_order.clear()
        wrapper.cache_info = lambda: {
            'hits': 0,  # Would need tracking
            'misses': 0,
            'maxsize': maxsize,
            'currsize': len(cache)
        }
        
        return wrapper
    
    return decorator


def _build_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_template: Optional[str],
    key_builder
) -> str:
    """Build cache key for function call."""
    if key_template:
        # Use custom template
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        try:
            return key_template.format(**bound_args.arguments)
        except KeyError as e:
            logger.warning(f"Key template missing argument: {e}")
            # Fallback to automatic key generation
    
    # Automatic key generation
    func_name = f"{func.__module__}.{func.__name__}"
    params = {}
    
    # Add positional args
    if args:
        params['args'] = args
    
    # Add keyword args
    if kwargs:
        params['kwargs'] = kwargs
    
    return key_builder.build_key("function", func_name, params)


async def _invalidate_cache_entries(
    cache_manager,
    pattern: Optional[str],
    tags: Optional[List[str]],
    keys: Optional[List[str]],
    func: Callable,
    args: tuple,
    kwargs: dict
):
    """Invalidate cache entries based on provided criteria."""
    if pattern:
        await cache_manager.invalidate_by_pattern(pattern)
    
    if tags:
        for tag in tags:
            await cache_manager.invalidate_by_tag(tag)
    
    if keys:
        for key in keys:
            await cache_manager.delete(key)


def _make_key(args: tuple, kwargs: dict) -> str:
    """Create a simple key from function arguments."""
    import hashlib
    import json
    
    key_data = {"args": args, "kwargs": kwargs}
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]
