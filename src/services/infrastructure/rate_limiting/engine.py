"""
Rate Limiting Engine
===================

Main engine that coordinates rate limiting strategies, tiers, and backends.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta

from .config import RateLimitConfig, UserTier, TierLimits, RateLimitStrategy
from .strategies import get_strategy, RateLimitResult
from .redis_backend import RedisRateLimitBackend

logger = logging.getLogger(__name__)


class RateLimitEngine:
    """Main rate limiting engine."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.backend = RedisRateLimitBackend(config)
        self._global_stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'start_time': time.time()
        }
        self._cleanup_task = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the rate limiting engine."""
        if self._initialized:
            return True
        
        try:
            # Initialize backend
            await self.backend.initialize()
            
            # Start cleanup task
            if self.config.cleanup_interval > 0:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._initialized = True
            logger.info("Rate limiting engine initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting engine: {e}")
            return False
    
    async def close(self):
        """Close the rate limiting engine."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.backend.close()
        logger.info("Rate limiting engine closed")
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "/",
        user_tier: UserTier = UserTier.FREE,
        user_id: Optional[str] = None,
        custom_limits: Optional[Dict[str, int]] = None,
        strategy_override: Optional[RateLimitStrategy] = None
    ) -> RateLimitResult:
        """
        Check rate limits for a request.
        
        Args:
            identifier: Unique identifier (IP, user ID, API key)
            endpoint: API endpoint being accessed
            user_tier: User's subscription tier
            user_id: Optional user ID for user-specific tracking
            custom_limits: Optional custom rate limits
            strategy_override: Optional strategy override
            
        Returns:
            RateLimitResult with details about the rate limit check
        """
        
        if not self.config.enabled:
            return RateLimitResult(
                allowed=True,
                remaining=1000,
                reset_time=time.time() + 3600,
                strategy="disabled"
            )
        
        # Update global stats
        self._global_stats['total_requests'] += 1
        
        try:
            # Check global rate limits first
            global_result = await self._check_global_limits(identifier)
            if not global_result.allowed:
                self._global_stats['blocked_requests'] += 1
                return global_result
            
            # Get endpoint configuration
            endpoint_config = self.config.get_endpoint_config(endpoint)
            
            # Determine strategy and limits
            if strategy_override:
                strategy_name = strategy_override.value
            elif endpoint_config:
                strategy_name = endpoint_config.strategy.value
            else:
                strategy_name = self.config.default_strategy.value
            
            # Get tier limits
            if custom_limits:
                tier_limits = self._create_custom_limits(custom_limits)
            elif endpoint_config and user_tier in endpoint_config.limits:
                tier_limits = endpoint_config.limits[user_tier]
            else:
                tier_limits = self.config.get_tier_limits(user_tier)
            
            # Check multiple rate limit dimensions
            results = await self._check_multi_dimensional_limits(
                identifier=identifier,
                endpoint=endpoint,
                user_tier=user_tier,
                user_id=user_id,
                tier_limits=tier_limits,
                strategy_name=strategy_name
            )
            
            # Find the most restrictive result
            most_restrictive = min(results, key=lambda r: r.remaining if r.allowed else -1)
            
            if not most_restrictive.allowed:
                self._global_stats['blocked_requests'] += 1
            
            return most_restrictive
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            
            # Fail open or closed based on configuration
            if self.config.allow_on_error:
                return RateLimitResult(
                    allowed=True,
                    remaining=100,
                    reset_time=time.time() + 3600,
                    strategy="error_fallback"
                )
            else:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=time.time() + 300,
                    retry_after=300,
                    strategy="error_block"
                )
    
    async def _check_global_limits(self, identifier: str) -> RateLimitResult:
        """Check global rate limits."""
        
        current_time = time.time()
        
        # Check per-second global limit
        if self.config.global_limit_per_second > 0:
            second_key = f"global:second:{int(current_time)}"
            count = await self.backend.increment(second_key, expire=1)
            
            if count and count > self.config.global_limit_per_second:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + 1,
                    retry_after=1,
                    limit=self.config.global_limit_per_second,
                    strategy="global_limit"
                )
        
        # Check per-minute global limit
        if self.config.global_limit_per_minute > 0:
            minute_key = f"global:minute:{int(current_time // 60)}"
            count = await self.backend.increment(minute_key, expire=60)
            
            if count and count > self.config.global_limit_per_minute:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + 60,
                    retry_after=60,
                    limit=self.config.global_limit_per_minute,
                    strategy="global_limit"
                )
        
        return RateLimitResult(
            allowed=True,
            remaining=1000,
            reset_time=current_time + 60,
            strategy="global_check"
        )
    
    async def _check_multi_dimensional_limits(
        self,
        identifier: str,
        endpoint: str,
        user_tier: UserTier,
        user_id: Optional[str],
        tier_limits: TierLimits,
        strategy_name: str
    ) -> List[RateLimitResult]:
        """Check rate limits across multiple dimensions."""
        
        strategy = get_strategy(strategy_name)
        results = []
        
        # 1. Per-identifier limits (IP/API key)
        identifier_result = await self._check_dimension_limits(
            key=f"id:{identifier}",
            limits=tier_limits,
            strategy=strategy,
            prefix="identifier"
        )
        results.append(identifier_result)
        
        # 2. Per-endpoint limits
        endpoint_result = await self._check_dimension_limits(
            key=f"endpoint:{endpoint}:{identifier}",
            limits=tier_limits,
            strategy=strategy,
            prefix="endpoint"
        )
        results.append(endpoint_result)
        
        # 3. Per-user limits (if user_id provided)
        if user_id:
            user_result = await self._check_dimension_limits(
                key=f"user:{user_id}",
                limits=tier_limits,
                strategy=strategy,
                prefix="user"
            )
            results.append(user_result)
        
        # 4. Per-tier limits (global tier tracking)
        tier_result = await self._check_dimension_limits(
            key=f"tier:{user_tier.value}:{identifier}",
            limits=tier_limits,
            strategy=strategy,
            prefix="tier"
        )
        results.append(tier_result)
        
        return results
    
    async def _check_dimension_limits(
        self,
        key: str,
        limits: TierLimits,
        strategy,
        prefix: str
    ) -> RateLimitResult:
        """Check rate limits for a specific dimension."""
        
        # Check minute limit
        minute_result = await strategy.check_limit(
            key=f"{prefix}:min:{key}",
            limit=limits.requests_per_minute,
            window=60,
            backend=self.backend,
            burst_capacity=limits.burst_capacity
        )
        
        if not minute_result.allowed:
            return minute_result
        
        # Check hour limit
        hour_result = await strategy.check_limit(
            key=f"{prefix}:hour:{key}",
            limit=limits.requests_per_hour,
            window=3600,
            backend=self.backend,
            burst_capacity=limits.burst_capacity
        )
        
        if not hour_result.allowed:
            return hour_result
        
        # Check day limit
        day_result = await strategy.check_limit(
            key=f"{prefix}:day:{key}",
            limit=limits.requests_per_day,
            window=86400,
            backend=self.backend,
            burst_capacity=limits.burst_capacity
        )
        
        return day_result
    
    def _create_custom_limits(self, custom_limits: Dict[str, int]) -> TierLimits:
        """Create TierLimits from custom limit dictionary."""
        return TierLimits(
            requests_per_minute=custom_limits.get('requests_per_minute', 60),
            requests_per_hour=custom_limits.get('requests_per_hour', 1000),
            requests_per_day=custom_limits.get('requests_per_day', 10000),
            burst_capacity=custom_limits.get('burst_capacity', 10),
            concurrent_requests=custom_limits.get('concurrent_requests', 10),
            ai_requests_per_hour=custom_limits.get('ai_requests_per_hour', 100),
            meal_plans_per_day=custom_limits.get('meal_plans_per_day', 5)
        )
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        user_tier: UserTier = UserTier.FREE,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current rate limit status for an identifier."""
        
        tier_limits = self.config.get_tier_limits(user_tier)
        
        status = {
            'identifier': identifier,
            'user_tier': user_tier.value,
            'limits': {
                'requests_per_minute': tier_limits.requests_per_minute,
                'requests_per_hour': tier_limits.requests_per_hour,
                'requests_per_day': tier_limits.requests_per_day,
                'burst_capacity': tier_limits.burst_capacity,
            },
            'usage': {},
            'reset_times': {}
        }
        
        # Get usage for different time windows
        for window, seconds in [('minute', 60), ('hour', 3600), ('day', 86400)]:
            key = f"id:{window}:{identifier}"
            
            try:
                # Get current count (this is simplified - real implementation would need strategy-specific logic)
                count = await self.backend.get_value(f"fw:{key}:*")
                count = int(count) if count else 0
                
                status['usage'][window] = count
                status['reset_times'][window] = time.time() + seconds
                
            except Exception as e:
                logger.error(f"Failed to get usage for {window}: {e}")
                status['usage'][window] = 0
                status['reset_times'][window] = time.time() + seconds
        
        return status
    
    async def reset_rate_limit(
        self,
        identifier: str,
        scope: str = "all"
    ) -> bool:
        """Reset rate limits for an identifier."""
        
        try:
            if scope == "all":
                # Reset all keys for this identifier
                patterns = [
                    f"*:{identifier}",
                    f"*:{identifier}:*"
                ]
            else:
                patterns = [f"{scope}:*:{identifier}"]
            
            deleted_count = 0
            for pattern in patterns:
                keys = await self.backend.get_keys_pattern(pattern)
                for key in keys:
                    await self.backend.delete_key(key)
                    deleted_count += 1
            
            logger.info(f"Reset {deleted_count} rate limit keys for {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limits for {identifier}: {e}")
            return False
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics."""
        
        backend_stats = await self.backend.get_stats()
        
        uptime = time.time() - self._global_stats['start_time']
        
        stats = {
            'uptime_seconds': uptime,
            'total_requests': self._global_stats['total_requests'],
            'blocked_requests': self._global_stats['blocked_requests'],
            'success_rate': 1 - (self._global_stats['blocked_requests'] / max(1, self._global_stats['total_requests'])),
            'requests_per_second': self._global_stats['total_requests'] / max(1, uptime),
            'backend': backend_stats,
            'config': {
                'enabled': self.config.enabled,
                'default_strategy': self.config.default_strategy.value,
                'global_limits': {
                    'per_second': self.config.global_limit_per_second,
                    'per_minute': self.config.global_limit_per_minute,
                }
            }
        }
        
        return stats
    
    async def _cleanup_loop(self):
        """Background task to clean up expired data."""
        
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                
                # Clean up expired keys in memory fallback
                cleaned = await self.backend.cleanup_expired_keys()
                if cleaned > 0:
                    logger.debug(f"Cleaned up {cleaned} expired rate limit keys")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    async def update_config(self, new_config: RateLimitConfig):
        """Update configuration dynamically."""
        
        if not self.config.dynamic_limits_enabled:
            raise ValueError("Dynamic configuration updates are disabled")
        
        old_config = self.config
        self.config = new_config
        
        logger.info("Rate limiting configuration updated")
        
        # Reinitialize backend if Redis settings changed
        if (old_config.redis_url != new_config.redis_url or 
            old_config.redis_pool_size != new_config.redis_pool_size):
            
            await self.backend.close()
            self.backend = RedisRateLimitBackend(new_config)
            await self.backend.initialize()
            
            logger.info("Redis backend reinitialized with new configuration")


# Global engine instance
_engine_instance: Optional[RateLimitEngine] = None


async def get_rate_limit_engine(config: Optional[RateLimitConfig] = None) -> RateLimitEngine:
    """Get or create the global rate limiting engine."""
    global _engine_instance
    
    if _engine_instance is None:
        from .config import default_config
        config = config or default_config
        _engine_instance = RateLimitEngine(config)
        await _engine_instance.initialize()
    
    return _engine_instance


async def close_rate_limit_engine():
    """Close the global rate limiting engine."""
    global _engine_instance
    
    if _engine_instance:
        await _engine_instance.close()
        _engine_instance = None
