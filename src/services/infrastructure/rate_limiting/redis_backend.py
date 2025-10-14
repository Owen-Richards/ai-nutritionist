"""
Redis Backend for Rate Limiting
==============================

Redis-based distributed rate limiting backend with connection pooling,
error handling, and fallback mechanisms.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from .config import RateLimitConfig

logger = logging.getLogger(__name__)


class RedisRateLimitBackend:
    """Redis backend for distributed rate limiting."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._redis_pool = None
        self._redis_client = None
        self._memory_fallback = {}
        self._connection_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using memory fallback")
    
    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            return False
            
        try:
            # Create connection pool
            self._redis_pool = redis.ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_pool_size,
                socket_timeout=self.config.redis_timeout,
                socket_connect_timeout=self.config.redis_timeout,
                decode_responses=True,
                retry_on_timeout=True
            )
            
            # Create Redis client
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)
            
            # Test connection
            await self._redis_client.ping()
            self._connection_healthy = True
            self._last_health_check = time.time()
            
            logger.info("Redis rate limiting backend initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis backend: {e}")
            self._connection_healthy = False
            return False
    
    async def close(self):
        """Close Redis connections."""
        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
        
        if self._redis_pool:
            try:
                await self._redis_pool.disconnect()
            except Exception as e:
                logger.error(f"Error closing Redis pool: {e}")
    
    async def _check_health(self) -> bool:
        """Check Redis connection health."""
        current_time = time.time()
        
        # Only check periodically
        if current_time - self._last_health_check < self._health_check_interval:
            return self._connection_healthy
        
        if not self._redis_client:
            return False
        
        try:
            await asyncio.wait_for(self._redis_client.ping(), timeout=2.0)
            self._connection_healthy = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._connection_healthy = False
        
        self._last_health_check = current_time
        return self._connection_healthy
    
    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.config.redis_key_prefix}{key}"
    
    async def execute_lua_script(
        self,
        script: str,
        keys: List[str],
        args: List[Union[str, int, float]]
    ) -> List[Any]:
        """Execute Lua script atomically."""
        
        # Check Redis health first
        if not await self._check_health():
            return await self._execute_fallback_script(script, keys, args)
        
        try:
            # Prefix keys
            prefixed_keys = [self._make_key(key) for key in keys]
            
            # Execute script
            script_hash = hashlib.sha1(script.encode()).hexdigest()
            
            try:
                # Try to execute by hash first (more efficient)
                result = await self._redis_client.evalsha(script_hash, len(prefixed_keys), *prefixed_keys, *args)
            except redis.ResponseError as e:
                if "NOSCRIPT" in str(e):
                    # Script not cached, send full script
                    result = await self._redis_client.eval(script, len(prefixed_keys), *prefixed_keys, *args)
                else:
                    raise
            
            return result
            
        except Exception as e:
            logger.error(f"Lua script execution failed: {e}")
            return await self._execute_fallback_script(script, keys, args)
    
    async def _execute_fallback_script(
        self,
        script: str,
        keys: List[str],
        args: List[Union[str, int, float]]
    ) -> List[Any]:
        """Execute fallback logic when Redis is unavailable."""
        
        # Simple in-memory fallback for basic operations
        if not self.config.fallback_to_memory:
            raise RuntimeError("Redis unavailable and fallback disabled")
        
        logger.warning("Using memory fallback for rate limiting")
        
        # Basic token bucket fallback
        if "tb:" in keys[0]:
            return await self._fallback_token_bucket(keys[0], args)
        # Basic fixed window fallback
        elif "fw:" in keys[0]:
            return await self._fallback_fixed_window(keys[0], args)
        # Default: allow request
        else:
            limit = int(args[0]) if args else 100
            return [1, limit - 1, time.time() + 3600, 1]
    
    async def _fallback_token_bucket(self, key: str, args: List) -> List[Any]:
        """Memory fallback for token bucket."""
        limit = int(args[0])
        window = int(args[1])
        burst_capacity = int(args[2])
        current_time = float(args[3])
        
        # Get or create bucket
        if key not in self._memory_fallback:
            self._memory_fallback[key] = {
                'tokens': burst_capacity,
                'last_refill': current_time
            }
        
        bucket = self._memory_fallback[key]
        
        # Calculate refill
        refill_rate = limit / window
        time_elapsed = current_time - bucket['last_refill']
        tokens_to_add = int(time_elapsed * refill_rate)
        
        bucket['tokens'] = min(burst_capacity, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = current_time
        
        # Check if request allowed
        allowed = bucket['tokens'] >= 1
        if allowed:
            bucket['tokens'] -= 1
        
        reset_time = current_time + ((burst_capacity - bucket['tokens']) / refill_rate)
        
        return [1 if allowed else 0, bucket['tokens'], reset_time, burst_capacity]
    
    async def _fallback_fixed_window(self, key: str, args: List) -> List[Any]:
        """Memory fallback for fixed window."""
        limit = int(args[0])
        window = int(args[1])
        current_time = float(args[2])
        
        # Clean expired entries
        current_time_int = int(current_time)
        expired_keys = [
            k for k, v in self._memory_fallback.items()
            if v.get('expires', 0) < current_time_int
        ]
        for k in expired_keys:
            del self._memory_fallback[k]
        
        # Get or create counter
        if key not in self._memory_fallback:
            self._memory_fallback[key] = {
                'count': 0,
                'expires': current_time_int + window
            }
        
        counter = self._memory_fallback[key]
        
        # Check limit
        allowed = counter['count'] < limit
        if allowed:
            counter['count'] += 1
        
        reset_time = counter['expires']
        remaining = limit - counter['count']
        
        return [1 if allowed else 0, remaining, reset_time, counter['count']]
    
    async def get_value(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not await self._check_health():
            return self._memory_fallback.get(self._make_key(key))
        
        try:
            return await self._redis_client.get(self._make_key(key))
        except Exception as e:
            logger.error(f"Redis GET failed: {e}")
            return None
    
    async def set_value(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis."""
        if not await self._check_health():
            self._memory_fallback[self._make_key(key)] = value
            return True
        
        try:
            if expire:
                await self._redis_client.setex(self._make_key(key), expire, value)
            else:
                await self._redis_client.set(self._make_key(key), value)
            return True
        except Exception as e:
            logger.error(f"Redis SET failed: {e}")
            return False
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
        expire: Optional[int] = None
    ) -> Optional[int]:
        """Increment value in Redis."""
        if not await self._check_health():
            redis_key = self._make_key(key)
            current = int(self._memory_fallback.get(redis_key, 0))
            self._memory_fallback[redis_key] = current + amount
            return current + amount
        
        try:
            result = await self._redis_client.incr(self._make_key(key), amount)
            if expire:
                await self._redis_client.expire(self._make_key(key), expire)
            return result
        except Exception as e:
            logger.error(f"Redis INCR failed: {e}")
            return None
    
    async def delete_key(self, key: str) -> bool:
        """Delete key from Redis."""
        if not await self._check_health():
            self._memory_fallback.pop(self._make_key(key), None)
            return True
        
        try:
            await self._redis_client.delete(self._make_key(key))
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed: {e}")
            return False
    
    async def get_keys_pattern(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        if not await self._check_health():
            # Simple pattern matching for memory fallback
            prefix = self._make_key(pattern.replace('*', ''))
            return [k for k in self._memory_fallback.keys() if k.startswith(prefix)]
        
        try:
            keys = await self._redis_client.keys(self._make_key(pattern))
            # Remove prefix from keys
            prefix_len = len(self.config.redis_key_prefix)
            return [key[prefix_len:] for key in keys]
        except Exception as e:
            logger.error(f"Redis KEYS failed: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis backend statistics."""
        stats = {
            "backend": "redis",
            "healthy": self._connection_healthy,
            "fallback_keys": len(self._memory_fallback),
            "redis_available": REDIS_AVAILABLE,
        }
        
        if self._redis_client and self._connection_healthy:
            try:
                info = await self._redis_client.info()
                stats.update({
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory"),
                    "used_memory_human": info.get("used_memory_human"),
                    "total_commands_processed": info.get("total_commands_processed"),
                })
            except Exception as e:
                logger.error(f"Failed to get Redis stats: {e}")
        
        return stats
    
    async def cleanup_expired_keys(self) -> int:
        """Clean up expired keys (for memory fallback)."""
        if self._connection_healthy:
            return 0  # Redis handles expiration automatically
        
        current_time = time.time()
        expired_keys = []
        
        for key, value in self._memory_fallback.items():
            if isinstance(value, dict) and 'expires' in value:
                if value['expires'] < current_time:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory_fallback[key]
        
        return len(expired_keys)
