"""Performance optimization for validation operations."""

from __future__ import annotations

import functools
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from weakref import WeakKeyDictionary

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class ValidationCache:
    """Caching system for validation results to improve performance."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, model_class: Type, data: Dict[str, Any]) -> str:
        """Generate cache key from model class and data."""
        # Create deterministic hash of the data
        data_str = str(sorted(data.items()))
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        return f"{model_class.__name__}:{data_hash}"
    
    def get(self, model_class: Type, data: Dict[str, Any]) -> Optional[T]:
        """Get cached validation result if available and not expired."""
        key = self._generate_key(model_class, data)
        
        if key in self._cache:
            result, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < self._ttl:
                self._hits += 1
                return result
            else:
                # Remove expired entry
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, model_class: Type, data: Dict[str, Any], result: T) -> None:
        """Cache validation result."""
        key = self._generate_key(model_class, data)
        
        # Ensure cache doesn't exceed max size
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        self._cache[key] = (result, datetime.utcnow())
    
    def _evict_oldest(self) -> None:
        """Evict oldest entries to make room."""
        # Remove 20% of oldest entries
        entries_to_remove = max(1, self._max_size // 5)
        
        # Sort by timestamp and remove oldest
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1][1]
        )
        
        for i in range(entries_to_remove):
            if i < len(sorted_entries):
                key = sorted_entries[i][0]
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'ttl_seconds': self._ttl.total_seconds()
        }


class LazyValidator:
    """Lazy validation that defers validation until field access."""
    
    def __init__(self, model_class: Type[T], data: Dict[str, Any]):
        self._model_class = model_class
        self._data = data
        self._validated_instance: Optional[T] = None
        self._validation_error: Optional[Exception] = None
        self._accessed_fields: set[str] = set()
    
    def __getattr__(self, name: str) -> Any:
        """Validate and return field value on access."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        
        # Trigger validation if not already done
        if self._validated_instance is None and self._validation_error is None:
            self._perform_validation()
        
        if self._validation_error:
            raise self._validation_error
        
        self._accessed_fields.add(name)
        return getattr(self._validated_instance, name)
    
    def _perform_validation(self) -> None:
        """Perform the actual validation."""
        try:
            self._validated_instance = self._model_class(**self._data)
        except Exception as e:
            self._validation_error = e
    
    def force_validation(self) -> T:
        """Force complete validation and return instance."""
        if self._validated_instance is None and self._validation_error is None:
            self._perform_validation()
        
        if self._validation_error:
            raise self._validation_error
        
        return self._validated_instance
    
    def get_accessed_fields(self) -> set[str]:
        """Get list of fields that have been accessed."""
        return self._accessed_fields.copy()


class BulkValidator:
    """Efficient validation for multiple instances of the same model."""
    
    def __init__(self, model_class: Type[T], batch_size: int = 100):
        self._model_class = model_class
        self._batch_size = batch_size
        self._validation_cache = ValidationCache()
    
    def validate_batch(self, 
                      data_list: List[Dict[str, Any]],
                      stop_on_error: bool = False,
                      use_cache: bool = True) -> List[Union[T, Exception]]:
        """Validate a batch of data instances."""
        results: List[Union[T, Exception]] = []
        
        for i in range(0, len(data_list), self._batch_size):
            batch = data_list[i:i + self._batch_size]
            batch_results = self._validate_batch_chunk(
                batch, 
                stop_on_error=stop_on_error,
                use_cache=use_cache
            )
            results.extend(batch_results)
            
            if stop_on_error and any(isinstance(r, Exception) for r in batch_results):
                break
        
        return results
    
    def _validate_batch_chunk(self,
                             batch: List[Dict[str, Any]],
                             stop_on_error: bool = False,
                             use_cache: bool = True) -> List[Union[T, Exception]]:
        """Validate a single batch chunk."""
        results: List[Union[T, Exception]] = []
        
        for data in batch:
            try:
                # Check cache first
                if use_cache:
                    cached_result = self._validation_cache.get(self._model_class, data)
                    if cached_result is not None:
                        results.append(cached_result)
                        continue
                
                # Perform validation
                instance = self._model_class(**data)
                
                # Cache successful result
                if use_cache:
                    self._validation_cache.set(self._model_class, data, instance)
                
                results.append(instance)
                
            except Exception as e:
                results.append(e)
                if stop_on_error:
                    break
        
        return results
    
    def validate_async_batch(self,
                           data_list: List[Dict[str, Any]],
                           max_workers: int = 4) -> List[Union[T, Exception]]:
        """Validate batch using thread pool for I/O-bound validation."""
        import concurrent.futures
        
        def validate_chunk(chunk: List[Dict[str, Any]]) -> List[Union[T, Exception]]:
            return self._validate_batch_chunk(chunk)
        
        # Split into chunks for parallel processing
        chunks = [
            data_list[i:i + self._batch_size] 
            for i in range(0, len(data_list), self._batch_size)
        ]
        
        results: List[Union[T, Exception]] = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(validate_chunk, chunk): chunk 
                for chunk in chunks
            }
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    chunk_results = future.result()
                    results.extend(chunk_results)
                except Exception as e:
                    # If chunk processing fails, add error for each item in chunk
                    chunk = future_to_chunk[future]
                    results.extend([e] * len(chunk))
        
        return results


class PerformanceOptimizer:
    """Performance optimization utilities for validation operations."""
    
    # Global cache instance
    _global_cache = ValidationCache(max_size=5000, ttl_seconds=600)
    
    # Model-specific caches
    _model_caches: WeakKeyDictionary = WeakKeyDictionary()
    
    @classmethod
    def get_cache(cls, model_class: Type) -> ValidationCache:
        """Get or create cache for specific model class."""
        if model_class not in cls._model_caches:
            cls._model_caches[model_class] = ValidationCache(
                max_size=1000,
                ttl_seconds=300
            )
        return cls._model_caches[model_class]
    
    @staticmethod
    def cached_validation(use_global_cache: bool = False):
        """Decorator for caching validation results."""
        def decorator(validation_func: Callable) -> Callable:
            @functools.wraps(validation_func)
            def wrapper(model_class: Type, data: Dict[str, Any], *args, **kwargs):
                cache = (PerformanceOptimizer._global_cache if use_global_cache 
                        else PerformanceOptimizer.get_cache(model_class))
                
                # Try cache first
                cached_result = cache.get(model_class, data)
                if cached_result is not None:
                    return cached_result
                
                # Perform validation
                start_time = time.time()
                result = validation_func(model_class, data, *args, **kwargs)
                validation_time = (time.time() - start_time) * 1000
                
                # Cache result
                cache.set(model_class, data, result)
                
                # Log performance metrics
                if validation_time > 100:  # Log slow validations
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Slow validation detected: {model_class.__name__}",
                        extra={
                            'validation_time_ms': validation_time,
                            'model_class': model_class.__name__,
                            'field_count': len(data)
                        }
                    )
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def validate_with_metrics(model_class: Type[T], data: Dict[str, Any]) -> tuple[T, Dict[str, Any]]:
        """Validate with detailed performance metrics."""
        start_time = time.time()
        memory_before = PerformanceOptimizer._get_memory_usage()
        
        try:
            instance = model_class(**data)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            instance = None
        
        end_time = time.time()
        memory_after = PerformanceOptimizer._get_memory_usage()
        
        metrics = {
            'validation_time_ms': (end_time - start_time) * 1000,
            'memory_delta_kb': memory_after - memory_before,
            'field_count': len(data),
            'model_class': model_class.__name__,
            'success': success,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return instance, metrics
    
    @staticmethod
    def _get_memory_usage() -> int:
        """Get current memory usage in KB."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return int(process.memory_info().rss / 1024)
        except ImportError:
            return 0
    
    @classmethod
    def get_global_stats(cls) -> Dict[str, Any]:
        """Get global performance statistics."""
        model_stats = {}
        for model_class, cache in cls._model_caches.items():
            model_stats[model_class.__name__] = cache.get_stats()
        
        return {
            'global_cache': cls._global_cache.get_stats(),
            'model_caches': model_stats,
            'total_model_caches': len(cls._model_caches)
        }
    
    @classmethod
    def clear_all_caches(cls) -> None:
        """Clear all validation caches."""
        cls._global_cache.clear()
        for cache in cls._model_caches.values():
            cache.clear()


# Convenience decorators
def cached_validation(use_global_cache: bool = False):
    """Convenience decorator for cached validation."""
    return PerformanceOptimizer.cached_validation(use_global_cache)


def performance_monitored(func: Callable) -> Callable:
    """Decorator to monitor validation performance."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            result = None
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Log performance metrics
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(
                f"Validation performance: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'success': success,
                    'error': error
                }
            )
        
        return result
    
    return wrapper
