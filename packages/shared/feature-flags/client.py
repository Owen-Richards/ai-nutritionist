"""Feature flag client implementations."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .models import FlagContext, FlagEvaluationResult, LaunchDarklyConfig
from .service import FeatureFlagService, LaunchDarklyService, CacheConfig
from .cache import FeatureFlagCache, MemoryCache


logger = logging.getLogger(__name__)


class FeatureFlagClient:
    """High-level client for feature flag operations."""
    
    def __init__(
        self,
        service: FeatureFlagService,
        default_context: Optional[FlagContext] = None,
    ):
        self.service = service
        self.default_context = default_context or FlagContext()
    
    async def is_enabled(
        self,
        flag_key: str,
        context: Optional[FlagContext] = None,
        default: bool = False,
    ) -> bool:
        """Check if a feature flag is enabled."""
        context = context or self.default_context
        return await self.service.is_flag_enabled(flag_key, context, default)
    
    async def get_variant(
        self,
        flag_key: str,
        context: Optional[FlagContext] = None,
        default: str = "control",
    ) -> str:
        """Get feature flag variant."""
        context = context or self.default_context
        return await self.service.get_flag_variant(flag_key, context, default)
    
    async def get_value(
        self,
        flag_key: str,
        context: Optional[FlagContext] = None,
        default: Any = None,
    ) -> Any:
        """Get feature flag value."""
        context = context or self.default_context
        result = await self.service.evaluate_flag(flag_key, context, default)
        return result.value
    
    async def evaluate(
        self,
        flag_key: str,
        context: Optional[FlagContext] = None,
        default: Any = None,
    ) -> FlagEvaluationResult:
        """Evaluate feature flag and get detailed result."""
        context = context or self.default_context
        return await self.service.evaluate_flag(flag_key, context, default)
    
    async def evaluate_all(
        self,
        flag_keys: List[str],
        context: Optional[FlagContext] = None,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, FlagEvaluationResult]:
        """Evaluate multiple feature flags."""
        context = context or self.default_context
        return await self.service.evaluate_flags(flag_keys, context, defaults)
    
    async def track_event(
        self,
        event_name: str,
        context: Optional[FlagContext] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track custom event for analytics."""
        context = context or self.default_context
        await self.service.track_flag_usage(
            flag_key="", # Empty flag key for custom events
            context=context,
            event_name=event_name,
            properties=properties,
        )
    
    def create_context(
        self,
        user_id: Optional[str] = None,
        subscription_tier: Optional[str] = None,
        country: Optional[str] = None,
        user_segments: Optional[List[str]] = None,
        custom_attributes: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> FlagContext:
        """Create a new flag context."""
        return FlagContext(
            user_id=user_id,
            subscription_tier=subscription_tier,
            country=country,
            user_segments=user_segments or [],
            custom_attributes=custom_attributes or {},
            **kwargs,
        )
    
    def with_context(self, context: FlagContext) -> 'FeatureFlagClient':
        """Create a new client with different default context."""
        return FeatureFlagClient(self.service, context)


class LaunchDarklyClient(FeatureFlagClient):
    """LaunchDarkly-specific feature flag client."""
    
    def __init__(
        self,
        config: LaunchDarklyConfig,
        cache_config: Optional[CacheConfig] = None,
        default_context: Optional[FlagContext] = None,
    ):
        service = LaunchDarklyService(config, cache_config)
        super().__init__(service, default_context)
        self.ld_service = service
    
    async def track_metric(
        self,
        metric_name: str,
        value: float,
        context: Optional[FlagContext] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track custom metric with LaunchDarkly."""
        context = context or self.default_context
        await self.ld_service.track_event(
            event_name=metric_name,
            context=context,
            data=data,
            metric_value=value,
        )
    
    def close(self) -> None:
        """Close LaunchDarkly client."""
        self.ld_service.close()


class BatchEvaluationClient:
    """Client for batch flag evaluations."""
    
    def __init__(self, service: FeatureFlagService):
        self.service = service
    
    async def evaluate_for_users(
        self,
        flag_keys: List[str],
        user_contexts: List[FlagContext],
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, FlagEvaluationResult]]:
        """Evaluate flags for multiple users."""
        results = {}
        
        # Evaluate for each user
        tasks = []
        for context in user_contexts:
            user_id = context.user_id or "anonymous"
            task = self.service.evaluate_flags(flag_keys, context, defaults)
            tasks.append((user_id, task))
        
        # Wait for all evaluations
        for user_id, task in tasks:
            try:
                user_results = await task
                results[user_id] = user_results
            except Exception as e:
                logger.error(f"Batch evaluation error for user {user_id}: {e}")
                # Create fallback results
                results[user_id] = {
                    flag_key: FlagEvaluationResult(
                        flag_key=flag_key,
                        variant_key="error",
                        value=defaults.get(flag_key) if defaults else None,
                        reason=f"batch_evaluation_error: {str(e)}",
                        is_default=True,
                    )
                    for flag_key in flag_keys
                }
        
        return results
    
    async def evaluate_for_segments(
        self,
        flag_keys: List[str],
        segments: List[str],
        sample_size: int = 100,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Evaluate flags for user segments."""
        results = {}
        
        for segment in segments:
            segment_results = {}
            
            # Generate sample contexts for segment
            contexts = self._generate_segment_contexts(segment, sample_size)
            
            # Evaluate for segment
            segment_evaluations = await self.evaluate_for_users(
                flag_keys, contexts, defaults
            )
            
            # Aggregate results by flag
            for flag_key in flag_keys:
                flag_results = {
                    user_id: eval_result.value
                    for user_id, user_flags in segment_evaluations.items()
                    for eval_result in [user_flags.get(flag_key)]
                    if eval_result
                }
                
                # Calculate distribution
                variant_counts = {}
                for value in flag_results.values():
                    variant_counts[str(value)] = variant_counts.get(str(value), 0) + 1
                
                segment_results[flag_key] = {
                    "sample_size": len(flag_results),
                    "variant_distribution": variant_counts,
                    "sample_values": list(flag_results.values())[:10],  # First 10 samples
                }
            
            results[segment] = segment_results
        
        return results
    
    def _generate_segment_contexts(
        self, 
        segment: str, 
        sample_size: int
    ) -> List[FlagContext]:
        """Generate sample contexts for a segment."""
        contexts = []
        
        for i in range(sample_size):
            context = FlagContext(
                user_id=f"sample_{segment}_{i}",
                user_segments=[segment],
                subscription_tier=segment if segment in ["free", "premium", "enterprise"] else "free",
                custom_attributes={
                    "segment": segment,
                    "sample_index": i,
                }
            )
            contexts.append(context)
        
        return contexts


class PerformanceOptimizedClient:
    """Client optimized for high-performance flag evaluations."""
    
    def __init__(
        self,
        service: FeatureFlagService,
        preload_flags: Optional[List[str]] = None,
        cache_duration: int = 60,
    ):
        self.service = service
        self.preload_flags = preload_flags or []
        self.cache_duration = cache_duration
        self._local_cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, datetime] = {}
        
        # Start preloading if flags specified
        if self.preload_flags:
            asyncio.create_task(self._preload_flags())
    
    async def is_enabled_fast(
        self,
        flag_key: str,
        user_id: str,
        use_cache: bool = True,
    ) -> bool:
        """Fast boolean flag evaluation with minimal context."""
        if use_cache:
            cached_value = self._get_cached_value(flag_key, user_id)
            if cached_value is not None:
                return cached_value
        
        # Create minimal context
        context = FlagContext(user_id=user_id)
        result = await self.service.is_flag_enabled(flag_key, context, False)
        
        if use_cache:
            self._cache_value(flag_key, user_id, result)
        
        return result
    
    async def get_variant_fast(
        self,
        flag_key: str,
        user_id: str,
        use_cache: bool = True,
    ) -> str:
        """Fast variant evaluation with minimal context."""
        if use_cache:
            cached_value = self._get_cached_value(flag_key, user_id)
            if cached_value is not None:
                return cached_value
        
        context = FlagContext(user_id=user_id)
        result = await self.service.get_flag_variant(flag_key, context, "control")
        
        if use_cache:
            self._cache_value(flag_key, user_id, result)
        
        return result
    
    async def batch_is_enabled(
        self,
        flag_keys: List[str],
        user_id: str,
        use_cache: bool = True,
    ) -> Dict[str, bool]:
        """Fast batch boolean evaluation."""
        results = {}
        uncached_flags = []
        
        if use_cache:
            for flag_key in flag_keys:
                cached_value = self._get_cached_value(flag_key, user_id)
                if cached_value is not None:
                    results[flag_key] = cached_value
                else:
                    uncached_flags.append(flag_key)
        else:
            uncached_flags = flag_keys
        
        if uncached_flags:
            context = FlagContext(user_id=user_id)
            defaults = {flag_key: False for flag_key in uncached_flags}
            
            evaluations = await self.service.evaluate_flags(
                uncached_flags, context, defaults
            )
            
            for flag_key, evaluation in evaluations.items():
                value = bool(evaluation.value)
                results[flag_key] = value
                
                if use_cache:
                    self._cache_value(flag_key, user_id, value)
        
        return results
    
    def _get_cached_value(self, flag_key: str, user_id: str) -> Optional[Any]:
        """Get value from local cache if not expired."""
        cache_key = f"{flag_key}:{user_id}"
        
        if cache_key not in self._local_cache:
            return None
        
        cache_time = self._cache_times.get(cache_key)
        if cache_time and (datetime.utcnow() - cache_time).total_seconds() > self.cache_duration:
            # Expired
            del self._local_cache[cache_key]
            del self._cache_times[cache_key]
            return None
        
        return self._local_cache[cache_key]
    
    def _cache_value(self, flag_key: str, user_id: str, value: Any) -> None:
        """Cache value locally."""
        cache_key = f"{flag_key}:{user_id}"
        self._local_cache[cache_key] = value
        self._cache_times[cache_key] = datetime.utcnow()
    
    async def _preload_flags(self) -> None:
        """Preload common flags into cache."""
        try:
            # Create sample contexts for preloading
            sample_contexts = [
                FlagContext(user_id=f"preload_user_{i}")
                for i in range(10)
            ]
            
            for context in sample_contexts:
                for flag_key in self.preload_flags:
                    try:
                        await self.service.evaluate_flag(flag_key, context)
                    except Exception as e:
                        logger.error(f"Preload error for {flag_key}: {e}")
            
            logger.info(f"Preloaded {len(self.preload_flags)} flags")
            
        except Exception as e:
            logger.error(f"Flag preloading failed: {e}")
    
    def clear_cache(self) -> None:
        """Clear local cache."""
        self._local_cache.clear()
        self._cache_times.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = datetime.utcnow()
        expired_count = sum(
            1 for cache_time in self._cache_times.values()
            if (current_time - cache_time).total_seconds() > self.cache_duration
        )
        
        return {
            "total_entries": len(self._local_cache),
            "expired_entries": expired_count,
            "cache_duration": self.cache_duration,
            "preload_flags": len(self.preload_flags),
        }
