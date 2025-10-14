"""Feature flag service implementation with LaunchDarkly integration."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

try:
    import ldclient
    from ldclient import Context as LDContext
    LAUNCHDARKLY_AVAILABLE = True
except ImportError:
    LAUNCHDARKLY_AVAILABLE = False
    ldclient = None
    LDContext = None

from .models import (
    FeatureFlagDefinition,
    FlagContext,
    FlagEvaluationResult,
    FlagStatus,
    LaunchDarklyConfig,
    RolloutStrategy,
    TargetingRule,
)
from .cache import FeatureFlagCache, MemoryCache


logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration for feature flags."""
    
    def __init__(
        self,
        ttl_seconds: int = 300,
        max_size: int = 10000,
        enable_local_cache: bool = True,
        enable_distributed_cache: bool = False,
        redis_url: Optional[str] = None,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.enable_local_cache = enable_local_cache
        self.enable_distributed_cache = enable_distributed_cache
        self.redis_url = redis_url


class FeatureFlagService:
    """Core feature flag service with caching and fallbacks."""
    
    def __init__(
        self,
        cache_config: Optional[CacheConfig] = None,
        fallback_provider: Optional['FallbackProvider'] = None,
    ):
        self.cache_config = cache_config or CacheConfig()
        self.cache = self._initialize_cache()
        self.fallback_provider = fallback_provider
        self._flags: Dict[str, FeatureFlagDefinition] = {}
        self._evaluation_metrics: Dict[str, Dict] = {}
        
    def _initialize_cache(self) -> FeatureFlagCache:
        """Initialize cache based on configuration."""
        if self.cache_config.enable_distributed_cache and self.cache_config.redis_url:
            from .cache import RedisCache
            return RedisCache(
                redis_url=self.cache_config.redis_url,
                ttl_seconds=self.cache_config.ttl_seconds,
            )
        else:
            return MemoryCache(
                ttl_seconds=self.cache_config.ttl_seconds,
                max_size=self.cache_config.max_size,
            )
    
    async def register_flag(self, flag: FeatureFlagDefinition) -> None:
        """Register a feature flag definition."""
        self._flags[flag.key] = flag
        await self.cache.invalidate(f"flag:{flag.key}")
        logger.info(f"Registered feature flag: {flag.key}")
    
    async def update_flag(self, flag_key: str, updates: Dict[str, Any]) -> None:
        """Update a feature flag."""
        if flag_key not in self._flags:
            raise ValueError(f"Flag {flag_key} not found")
        
        flag = self._flags[flag_key]
        for key, value in updates.items():
            if hasattr(flag, key):
                setattr(flag, key, value)
        
        flag.updated_at = datetime.utcnow()
        await self.cache.invalidate(f"flag:{flag_key}")
        logger.info(f"Updated feature flag: {flag_key}")
    
    async def evaluate_flag(
        self,
        flag_key: str,
        context: FlagContext,
        default_value: Any = None,
    ) -> FlagEvaluationResult:
        """Evaluate a feature flag for the given context."""
        start_time = datetime.utcnow()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(flag_key, context)
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                return FlagEvaluationResult(**cached_result)
            
            # Get flag definition
            flag = await self._get_flag_definition(flag_key)
            if not flag:
                return self._create_fallback_result(flag_key, default_value, "flag_not_found")
            
            # Check if flag is active
            if flag.status != FlagStatus.ACTIVE or flag.kill_switch:
                variant_key = flag.emergency_fallback or flag.fallback_variant
                variant = self._get_variant_by_key(flag, variant_key)
                result = FlagEvaluationResult(
                    flag_key=flag_key,
                    variant_key=variant_key,
                    value=variant.value if variant else default_value,
                    reason="flag_inactive_or_kill_switch",
                    is_default=True,
                )
            else:
                # Evaluate targeting rules
                result = await self._evaluate_targeting(flag, context)
            
            # Cache the result
            await self.cache.set(
                cache_key,
                result.model_dump(),
                ttl_seconds=self.cache_config.ttl_seconds,
            )
            
            # Track metrics
            self._track_evaluation_metrics(flag_key, result, start_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating flag {flag_key}: {e}")
            return self._create_fallback_result(flag_key, default_value, f"evaluation_error: {str(e)}")
    
    async def evaluate_flags(
        self,
        flag_keys: List[str],
        context: FlagContext,
        default_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, FlagEvaluationResult]:
        """Evaluate multiple feature flags."""
        default_values = default_values or {}
        
        # Evaluate flags concurrently
        tasks = [
            self.evaluate_flag(flag_key, context, default_values.get(flag_key))
            for flag_key in flag_keys
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            flag_keys[i]: result if not isinstance(result, Exception) 
            else self._create_fallback_result(flag_keys[i], default_values.get(flag_keys[i]), f"evaluation_exception: {str(result)}")
            for i, result in enumerate(results)
        }
    
    async def is_flag_enabled(
        self,
        flag_key: str,
        context: FlagContext,
        default: bool = False,
    ) -> bool:
        """Check if a boolean feature flag is enabled."""
        result = await self.evaluate_flag(flag_key, context, default)
        return bool(result.value)
    
    async def get_flag_variant(
        self,
        flag_key: str,
        context: FlagContext,
        default: str = "control",
    ) -> str:
        """Get the variant key for a feature flag."""
        result = await self.evaluate_flag(flag_key, context, default)
        return result.variant_key
    
    async def track_flag_usage(
        self,
        flag_key: str,
        context: FlagContext,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track flag usage event for analytics."""
        try:
            event_data = {
                "flag_key": flag_key,
                "user_id": context.user_id,
                "event_name": event_name,
                "properties": properties or {},
                "timestamp": datetime.utcnow().isoformat(),
                "context": context.model_dump(),
            }
            
            # Store event for analytics (implement based on your analytics system)
            logger.info(f"Flag usage tracked: {flag_key} - {event_name}")
            
        except Exception as e:
            logger.error(f"Error tracking flag usage: {e}")
    
    async def get_evaluation_metrics(self, flag_key: str) -> Dict[str, Any]:
        """Get evaluation metrics for a flag."""
        return self._evaluation_metrics.get(flag_key, {})
    
    async def _get_flag_definition(self, flag_key: str) -> Optional[FeatureFlagDefinition]:
        """Get flag definition from local store or fallback provider."""
        flag = self._flags.get(flag_key)
        
        if not flag and self.fallback_provider:
            flag = await self.fallback_provider.get_flag(flag_key)
        
        return flag
    
    async def _evaluate_targeting(
        self,
        flag: FeatureFlagDefinition,
        context: FlagContext,
    ) -> FlagEvaluationResult:
        """Evaluate targeting rules for a flag."""
        # Check targeting rules in priority order
        for rule in sorted(flag.targeting_rules, key=lambda r: r.priority, reverse=True):
            if await self._evaluate_targeting_rule(rule, context):
                variant = self._get_variant_by_key(flag, rule.variant)
                
                # Check percentage rollout for this rule
                if rule.percentage < 100:
                    user_hash = self._get_user_hash(context.user_id or "", flag.key)
                    if user_hash >= rule.percentage:
                        continue
                
                return FlagEvaluationResult(
                    flag_key=flag.key,
                    variant_key=rule.variant,
                    value=variant.value if variant else None,
                    reason=f"targeting_rule:{rule.id}",
                    rule_id=rule.id,
                )
        
        # Check rollout rules
        for rollout_rule in flag.rollout_rules:
            result = await self._evaluate_rollout_rule(flag, rollout_rule, context)
            if result:
                return result
        
        # Return default variant
        variant = self._get_variant_by_key(flag, flag.default_variant)
        return FlagEvaluationResult(
            flag_key=flag.key,
            variant_key=flag.default_variant,
            value=variant.value if variant else None,
            reason="default_variant",
            is_default=True,
        )
    
    async def _evaluate_targeting_rule(
        self,
        rule: TargetingRule,
        context: FlagContext,
    ) -> bool:
        """Evaluate if a targeting rule matches the context."""
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                return False
        return True
    
    def _evaluate_condition(self, condition: Dict[str, Any], context: FlagContext) -> bool:
        """Evaluate a single targeting condition."""
        attribute = condition.get("attribute")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if not attribute or not operator:
            return False
        
        # Get attribute value from context
        context_value = self._get_context_attribute(context, attribute)
        
        # Evaluate based on operator
        if operator == "equals":
            return context_value == value
        elif operator == "not_equals":
            return context_value != value
        elif operator == "in":
            return context_value in (value if isinstance(value, list) else [value])
        elif operator == "not_in":
            return context_value not in (value if isinstance(value, list) else [value])
        elif operator == "contains":
            return str(value) in str(context_value)
        elif operator == "starts_with":
            return str(context_value).startswith(str(value))
        elif operator == "ends_with":
            return str(context_value).endswith(str(value))
        elif operator == "greater_than":
            return float(context_value) > float(value)
        elif operator == "less_than":
            return float(context_value) < float(value)
        elif operator == "regex":
            import re
            return bool(re.match(value, str(context_value)))
        
        return False
    
    def _get_context_attribute(self, context: FlagContext, attribute: str) -> Any:
        """Get attribute value from context."""
        if attribute == "user_id":
            return context.user_id
        elif attribute == "subscription_tier":
            return context.subscription_tier
        elif attribute == "country":
            return context.country
        elif attribute == "user_segments":
            return context.user_segments
        elif attribute.startswith("custom."):
            custom_attr = attribute[7:]  # Remove "custom." prefix
            return context.custom_attributes.get(custom_attr)
        else:
            return getattr(context, attribute, None)
    
    async def _evaluate_rollout_rule(
        self,
        flag: FeatureFlagDefinition,
        rollout_rule,
        context: FlagContext,
    ) -> Optional[FlagEvaluationResult]:
        """Evaluate a rollout rule."""
        if rollout_rule.strategy == RolloutStrategy.PERCENTAGE:
            if rollout_rule.percentage is None:
                return None
            
            user_hash = self._get_user_hash(context.user_id or "", flag.key)
            if user_hash < rollout_rule.percentage:
                # User is in the rollout
                variant = self._get_variant_by_key(flag, flag.default_variant)
                return FlagEvaluationResult(
                    flag_key=flag.key,
                    variant_key=flag.default_variant,
                    value=variant.value if variant else None,
                    reason=f"percentage_rollout:{rollout_rule.percentage}%",
                )
        
        elif rollout_rule.strategy == RolloutStrategy.USER_LIST:
            if rollout_rule.user_ids and context.user_id in rollout_rule.user_ids:
                variant = self._get_variant_by_key(flag, flag.default_variant)
                return FlagEvaluationResult(
                    flag_key=flag.key,
                    variant_key=flag.default_variant,
                    value=variant.value if variant else None,
                    reason="user_list",
                )
        
        elif rollout_rule.strategy == RolloutStrategy.SEGMENT:
            if rollout_rule.segments:
                user_segments = set(context.user_segments)
                target_segments = set(rollout_rule.segments)
                if user_segments.intersection(target_segments):
                    variant = self._get_variant_by_key(flag, flag.default_variant)
                    return FlagEvaluationResult(
                        flag_key=flag.key,
                        variant_key=flag.default_variant,
                        value=variant.value if variant else None,
                        reason="segment_match",
                    )
        
        return None
    
    def _get_variant_by_key(self, flag: FeatureFlagDefinition, variant_key: str):
        """Get variant by key from flag definition."""
        for variant in flag.variants:
            if variant.key == variant_key:
                return variant
        return None
    
    def _get_user_hash(self, user_id: str, flag_key: str) -> float:
        """Get consistent hash for user and flag combination."""
        hash_input = f"{user_id}:{flag_key}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        # Convert to percentage (0-100)
        return (int(hash_value[:8], 16) % 10000) / 100.0
    
    def _get_cache_key(self, flag_key: str, context: FlagContext) -> str:
        """Generate cache key for flag evaluation."""
        context_hash = hashlib.md5(
            json.dumps(context.model_dump(), sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"flag:{flag_key}:context:{context_hash}"
    
    def _create_fallback_result(
        self,
        flag_key: str,
        default_value: Any,
        reason: str,
    ) -> FlagEvaluationResult:
        """Create fallback result when flag evaluation fails."""
        return FlagEvaluationResult(
            flag_key=flag_key,
            variant_key="fallback",
            value=default_value,
            reason=reason,
            is_default=True,
        )
    
    def _track_evaluation_metrics(
        self,
        flag_key: str,
        result: FlagEvaluationResult,
        start_time: datetime,
    ) -> None:
        """Track evaluation metrics for monitoring."""
        if flag_key not in self._evaluation_metrics:
            self._evaluation_metrics[flag_key] = {
                "evaluation_count": 0,
                "variant_counts": {},
                "avg_latency_ms": 0.0,
                "last_evaluated": None,
            }
        
        metrics = self._evaluation_metrics[flag_key]
        metrics["evaluation_count"] += 1
        metrics["variant_counts"][result.variant_key] = metrics["variant_counts"].get(result.variant_key, 0) + 1
        metrics["last_evaluated"] = datetime.utcnow()
        
        # Calculate average latency
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        current_avg = metrics["avg_latency_ms"]
        count = metrics["evaluation_count"]
        metrics["avg_latency_ms"] = ((current_avg * (count - 1)) + latency_ms) / count


class LaunchDarklyService(FeatureFlagService):
    """Feature flag service with LaunchDarkly integration."""
    
    def __init__(
        self,
        config: LaunchDarklyConfig,
        cache_config: Optional[CacheConfig] = None,
        fallback_provider: Optional['FallbackProvider'] = None,
    ):
        if not LAUNCHDARKLY_AVAILABLE:
            raise ImportError("LaunchDarkly SDK not available. Install with: pip install launchdarkly-server-sdk")
        
        super().__init__(cache_config, fallback_provider)
        self.config = config
        self.client = self._initialize_client()
        
    def _initialize_client(self):
        """Initialize LaunchDarkly client."""
        ld_config = ldclient.Config(
            sdk_key=self.config.sdk_key,
            base_uri=self.config.base_uri,
            events_uri=self.config.events_uri,
            stream_uri=self.config.stream_uri,
            send_events=self.config.send_events,
            events_capacity=self.config.events_capacity,
            events_flush_interval=self.config.events_flush_interval_seconds,
            offline=self.config.offline,
            use_ldd=self.config.use_ldd,
        )
        
        client = ldclient.LDClient(config=ld_config)
        
        if not client.is_initialized():
            logger.warning("LaunchDarkly client failed to initialize")
        
        return client
    
    async def evaluate_flag(
        self,
        flag_key: str,
        context: FlagContext,
        default_value: Any = None,
    ) -> FlagEvaluationResult:
        """Evaluate flag using LaunchDarkly."""
        try:
            # Convert context to LaunchDarkly context
            ld_context = self._convert_context(context)
            
            # Evaluate with LaunchDarkly
            if isinstance(default_value, bool):
                value = self.client.variation(flag_key, ld_context, default_value)
            else:
                value = self.client.variation(flag_key, ld_context, default_value)
            
            # Get evaluation details for more information
            detail = self.client.variation_detail(flag_key, ld_context, default_value)
            
            return FlagEvaluationResult(
                flag_key=flag_key,
                variant_key=detail.variation_index if detail.variation_index is not None else "default",
                value=value,
                reason=detail.reason.kind if detail.reason else "unknown",
                is_default=detail.is_default_value(),
            )
            
        except Exception as e:
            logger.error(f"LaunchDarkly evaluation error for {flag_key}: {e}")
            # Fallback to local evaluation
            return await super().evaluate_flag(flag_key, context, default_value)
    
    def _convert_context(self, context: FlagContext):
        """Convert FlagContext to LaunchDarkly Context."""
        ld_context = LDContext.builder(context.user_id or "anonymous")
        
        if context.user_id:
            ld_context.set("user_id", context.user_id)
        
        if context.subscription_tier:
            ld_context.set("subscription_tier", context.subscription_tier)
        
        if context.country:
            ld_context.set("country", context.country)
        
        if context.user_segments:
            ld_context.set("segments", context.user_segments)
        
        # Add custom attributes
        for key, value in context.custom_attributes.items():
            ld_context.set(key, value)
        
        return ld_context.build()
    
    async def track_event(
        self,
        event_name: str,
        context: FlagContext,
        data: Optional[Dict[str, Any]] = None,
        metric_value: Optional[float] = None,
    ) -> None:
        """Track custom event with LaunchDarkly."""
        try:
            ld_context = self._convert_context(context)
            
            if metric_value is not None:
                self.client.track(event_name, ld_context, data, metric_value)
            else:
                self.client.track(event_name, ld_context, data)
                
        except Exception as e:
            logger.error(f"LaunchDarkly track event error: {e}")
    
    def close(self) -> None:
        """Close LaunchDarkly client."""
        if self.client:
            self.client.close()


class FallbackProvider:
    """Interface for fallback flag providers."""
    
    async def get_flag(self, flag_key: str) -> Optional[FeatureFlagDefinition]:
        """Get flag definition from fallback source."""
        raise NotImplementedError


class LocalFileFallbackProvider(FallbackProvider):
    """Fallback provider that reads flags from local JSON file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._flags_cache: Optional[Dict[str, FeatureFlagDefinition]] = None
        self._last_modified: Optional[float] = None
    
    async def get_flag(self, flag_key: str) -> Optional[FeatureFlagDefinition]:
        """Get flag from local file."""
        flags = await self._load_flags()
        return flags.get(flag_key)
    
    async def _load_flags(self) -> Dict[str, FeatureFlagDefinition]:
        """Load flags from file with caching."""
        import os
        
        if not os.path.exists(self.file_path):
            return {}
        
        current_modified = os.path.getmtime(self.file_path)
        
        if self._flags_cache is None or current_modified != self._last_modified:
            try:
                with open(self.file_path, 'r') as f:
                    flags_data = json.load(f)
                
                self._flags_cache = {
                    key: FeatureFlagDefinition(**flag_data)
                    for key, flag_data in flags_data.items()
                }
                self._last_modified = current_modified
                
            except Exception as e:
                logger.error(f"Error loading flags from {self.file_path}: {e}")
                return {}
        
        return self._flags_cache or {}
