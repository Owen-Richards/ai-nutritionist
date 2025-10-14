"""
Rate Limiting Strategies
=======================

Implementation of different rate limiting algorithms.
"""

import time
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .redis_backend import RedisRateLimitBackend

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None
    current_usage: int = 0
    limit: int = 0
    window_size: int = 0
    strategy: str = ""
    
    def to_headers(self, prefix: str = "X-RateLimit") -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            f"{prefix}-Limit": str(self.limit),
            f"{prefix}-Remaining": str(self.remaining),
            f"{prefix}-Reset": str(int(self.reset_time)),
            f"{prefix}-Strategy": self.strategy,
        }
        
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
            
        return headers


class RateLimitStrategy(ABC):
    """Abstract base class for rate limiting strategies."""
    
    @abstractmethod
    async def check_limit(
        self,
        key: str,
        limit: int,
        window: int,
        backend: 'RedisRateLimitBackend',
        **kwargs
    ) -> RateLimitResult:
        """Check if request is within rate limits."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass


class TokenBucketStrategy(RateLimitStrategy):
    """
    Token Bucket Algorithm
    ======================
    
    Allows bursts up to bucket capacity, then refills at a steady rate.
    Good for APIs that need to handle traffic spikes.
    """
    
    def get_strategy_name(self) -> str:
        return "token_bucket"
    
    async def check_limit(
        self,
        key: str,
        limit: int,
        window: int,
        backend: 'RedisRateLimitBackend',
        burst_capacity: int = None,
        **kwargs
    ) -> RateLimitResult:
        """Check token bucket rate limit."""
        
        if burst_capacity is None:
            burst_capacity = limit
        
        current_time = time.time()
        bucket_key = f"tb:{key}"
        
        # Lua script for atomic token bucket operation
        lua_script = """
        local bucket_key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local burst_capacity = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])
        
        -- Get current bucket state
        local bucket_data = redis.call('HMGET', bucket_key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket_data[1]) or burst_capacity
        local last_refill = tonumber(bucket_data[2]) or current_time
        
        -- Calculate tokens to add based on time elapsed
        local refill_rate = limit / window  -- tokens per second
        local time_elapsed = current_time - last_refill
        local tokens_to_add = math.floor(time_elapsed * refill_rate)
        
        -- Update token count (capped at burst capacity)
        tokens = math.min(burst_capacity, tokens + tokens_to_add)
        
        -- Check if request can be served
        local allowed = tokens >= 1
        if allowed then
            tokens = tokens - 1
        end
        
        -- Update bucket state
        redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_refill', current_time)
        redis.call('EXPIRE', bucket_key, window)
        
        -- Calculate reset time (when bucket will be full)
        local reset_time = current_time + ((burst_capacity - tokens) / refill_rate)
        
        return {allowed and 1 or 0, tokens, reset_time, burst_capacity}
        """
        
        try:
            result = await backend.execute_lua_script(
                lua_script,
                keys=[bucket_key],
                args=[limit, window, burst_capacity, current_time]
            )
            
            allowed = bool(result[0])
            remaining = int(result[1])
            reset_time = float(result[2])
            capacity = int(result[3])
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=max(1, int(reset_time - current_time)) if not allowed else None,
                current_usage=capacity - remaining,
                limit=capacity,
                window_size=window,
                strategy=self.get_strategy_name()
            )
            
        except Exception as e:
            logger.error(f"Token bucket check failed: {e}")
            # Fallback: allow request but log error
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=current_time + window,
                current_usage=1,
                limit=limit,
                window_size=window,
                strategy=self.get_strategy_name()
            )


class SlidingWindowStrategy(RateLimitStrategy):
    """
    Sliding Window Algorithm
    ========================
    
    Maintains a precise rolling window of requests.
    Most accurate but requires more memory.
    """
    
    def get_strategy_name(self) -> str:
        return "sliding_window"
    
    async def check_limit(
        self,
        key: str,
        limit: int,
        window: int,
        backend: 'RedisRateLimitBackend',
        **kwargs
    ) -> RateLimitResult:
        """Check sliding window rate limit."""
        
        current_time = time.time()
        window_key = f"sw:{key}"
        
        # Lua script for atomic sliding window operation
        lua_script = """
        local window_key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        -- Remove expired entries
        local cutoff_time = current_time - window
        redis.call('ZREMRANGEBYSCORE', window_key, 0, cutoff_time)
        
        -- Count current requests in window
        local current_count = redis.call('ZCARD', window_key)
        
        -- Check if limit exceeded
        local allowed = current_count < limit
        
        if allowed then
            -- Add current request
            redis.call('ZADD', window_key, current_time, current_time)
            current_count = current_count + 1
        end
        
        -- Set expiration
        redis.call('EXPIRE', window_key, window)
        
        -- Calculate reset time (end of current window)
        local reset_time = current_time + window
        
        return {allowed and 1 or 0, limit - current_count, reset_time, current_count}
        """
        
        try:
            result = await backend.execute_lua_script(
                lua_script,
                keys=[window_key],
                args=[limit, window, current_time]
            )
            
            allowed = bool(result[0])
            remaining = max(0, int(result[1]))
            reset_time = float(result[2])
            current_usage = int(result[3])
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=max(1, int(reset_time - current_time)) if not allowed else None,
                current_usage=current_usage,
                limit=limit,
                window_size=window,
                strategy=self.get_strategy_name()
            )
            
        except Exception as e:
            logger.error(f"Sliding window check failed: {e}")
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=current_time + window,
                current_usage=1,
                limit=limit,
                window_size=window,
                strategy=self.get_strategy_name()
            )


class FixedWindowStrategy(RateLimitStrategy):
    """
    Fixed Window Algorithm
    ======================
    
    Simple counter that resets at fixed intervals.
    Memory efficient but can have burst issues at window boundaries.
    """
    
    def get_strategy_name(self) -> str:
        return "fixed_window"
    
    async def check_limit(
        self,
        key: str,
        limit: int,
        window: int,
        backend: 'RedisRateLimitBackend',
        **kwargs
    ) -> RateLimitResult:
        """Check fixed window rate limit."""
        
        current_time = time.time()
        window_start = int(current_time // window) * window
        window_key = f"fw:{key}:{window_start}"
        
        # Lua script for atomic fixed window operation
        lua_script = """
        local window_key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        local window_start = tonumber(ARGV[4])
        
        -- Get current count
        local current_count = tonumber(redis.call('GET', window_key) or 0)
        
        -- Check if limit exceeded
        local allowed = current_count < limit
        
        if allowed then
            -- Increment counter
            current_count = redis.call('INCR', window_key)
            
            -- Set expiration for the window
            redis.call('EXPIRE', window_key, window)
        end
        
        -- Calculate reset time (end of current window)
        local reset_time = window_start + window
        
        return {allowed and 1 or 0, limit - current_count, reset_time, current_count}
        """
        
        try:
            result = await backend.execute_lua_script(
                lua_script,
                keys=[window_key],
                args=[limit, window, current_time, window_start]
            )
            
            allowed = bool(result[0])
            remaining = max(0, int(result[1]))
            reset_time = float(result[2])
            current_usage = int(result[3])
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=max(1, int(reset_time - current_time)) if not allowed else None,
                current_usage=current_usage,
                limit=limit,
                window_size=window,
                strategy=self.get_strategy_name()
            )
            
        except Exception as e:
            logger.error(f"Fixed window check failed: {e}")
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=current_time + window,
                current_usage=1,
                limit=limit,
                window_size=window,
                strategy=self.get_strategy_name()
            )


class LeakyBucketStrategy(RateLimitStrategy):
    """
    Leaky Bucket Algorithm
    ======================
    
    Smooths out traffic by processing requests at a constant rate.
    Good for protecting downstream services from spikes.
    """
    
    def get_strategy_name(self) -> str:
        return "leaky_bucket"
    
    async def check_limit(
        self,
        key: str,
        limit: int,
        window: int,
        backend: 'RedisRateLimitBackend',
        bucket_size: int = None,
        **kwargs
    ) -> RateLimitResult:
        """Check leaky bucket rate limit."""
        
        if bucket_size is None:
            bucket_size = limit
        
        current_time = time.time()
        bucket_key = f"lb:{key}"
        
        # Lua script for atomic leaky bucket operation
        lua_script = """
        local bucket_key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local bucket_size = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])
        
        -- Get current bucket state
        local bucket_data = redis.call('HMGET', bucket_key, 'level', 'last_leak')
        local level = tonumber(bucket_data[1]) or 0
        local last_leak = tonumber(bucket_data[2]) or current_time
        
        -- Calculate leak amount based on time elapsed
        local leak_rate = limit / window  -- requests per second that can leak out
        local time_elapsed = current_time - last_leak
        local leak_amount = time_elapsed * leak_rate
        
        -- Update bucket level (can't go below 0)
        level = math.max(0, level - leak_amount)
        
        -- Check if request can be added
        local allowed = level < bucket_size
        if allowed then
            level = level + 1
        end
        
        -- Update bucket state
        redis.call('HMSET', bucket_key, 'level', level, 'last_leak', current_time)
        redis.call('EXPIRE', bucket_key, window)
        
        -- Calculate when bucket will have space (if full)
        local reset_time = current_time + ((level - bucket_size + 1) / leak_rate)
        if level < bucket_size then
            reset_time = current_time
        end
        
        return {allowed and 1 or 0, bucket_size - level, reset_time, level}
        """
        
        try:
            result = await backend.execute_lua_script(
                lua_script,
                keys=[bucket_key],
                args=[limit, window, bucket_size, current_time]
            )
            
            allowed = bool(result[0])
            remaining = max(0, int(result[1]))
            reset_time = float(result[2])
            current_usage = int(result[3])
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=max(1, int(reset_time - current_time)) if not allowed else None,
                current_usage=current_usage,
                limit=bucket_size,
                window_size=window,
                strategy=self.get_strategy_name()
            )
            
        except Exception as e:
            logger.error(f"Leaky bucket check failed: {e}")
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=current_time + window,
                current_usage=1,
                limit=limit,
                window_size=window,
                strategy=self.get_strategy_name()
            )


# Strategy registry
STRATEGIES = {
    "token_bucket": TokenBucketStrategy(),
    "sliding_window": SlidingWindowStrategy(),
    "fixed_window": FixedWindowStrategy(),
    "leaky_bucket": LeakyBucketStrategy(),
}


def get_strategy(name: str) -> RateLimitStrategy:
    """Get rate limiting strategy by name."""
    strategy = STRATEGIES.get(name.lower())
    if not strategy:
        raise ValueError(f"Unknown rate limiting strategy: {name}")
    return strategy
