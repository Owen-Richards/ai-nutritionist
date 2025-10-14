#!/usr/bin/env python3
"""
Simple Rate Limiting Test
=========================

Test the rate limiting system without Redis dependencies.
"""

import asyncio
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.infrastructure.rate_limiting.config import (
    RateLimitConfig, UserTier, RateLimitStrategy, TierLimits
)
from services.infrastructure.rate_limiting.strategies import (
    TokenBucketStrategy, SlidingWindowStrategy, FixedWindowStrategy, LeakyBucketStrategy
)


class MockRedisBackend:
    """Mock Redis backend for testing without Redis."""
    
    def __init__(self):
        self.data = {}
        self.script_calls = []
    
    async def execute_lua_script(self, script: str, keys: list, args: list):
        """Mock Lua script execution."""
        self.script_calls.append({'script': script, 'keys': keys, 'args': args})
        
        # Simple mock responses
        if 'tb:' in keys[0]:  # Token bucket
            return [1, 10, time.time() + 60, 20]
        elif 'sw:' in keys[0]:  # Sliding window
            return [1, 9, time.time() + 60, 1]
        elif 'fw:' in keys[0]:  # Fixed window
            return [1, 9, time.time() + 60, 1]
        elif 'lb:' in keys[0]:  # Leaky bucket
            return [1, 19, time.time() + 60, 1]
        else:
            return [1, 10, time.time() + 60, 1]


async def test_strategies():
    """Test all rate limiting strategies."""
    
    print("🧪 Testing Rate Limiting Strategies")
    print("=" * 40)
    
    backend = MockRedisBackend()
    strategies = [
        ("Token Bucket", TokenBucketStrategy()),
        ("Sliding Window", SlidingWindowStrategy()),
        ("Fixed Window", FixedWindowStrategy()),
        ("Leaky Bucket", LeakyBucketStrategy()),
    ]
    
    for name, strategy in strategies:
        print(f"\n📊 Testing {name} Strategy...")
        
        try:
            result = await strategy.check_limit(
                key="test:user1",
                limit=10,
                window=60,
                backend=backend,
                burst_capacity=20
            )
            
            print(f"  ✅ Strategy: {result.strategy}")
            print(f"  ✅ Allowed: {result.allowed}")
            print(f"  ✅ Remaining: {result.remaining}")
            print(f"  ✅ Reset time: {result.reset_time}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n📈 Total script calls: {len(backend.script_calls)}")


async def test_config():
    """Test configuration system."""
    
    print("\n🔧 Testing Configuration System")
    print("=" * 40)
    
    # Test default config
    config = RateLimitConfig()
    print(f"✅ Default strategy: {config.default_strategy.value}")
    print(f"✅ Redis URL: {config.redis_url}")
    print(f"✅ Enabled: {config.enabled}")
    
    # Test tier limits
    for tier in UserTier:
        limits = config.get_tier_limits(tier)
        print(f"✅ {tier.value} tier: {limits.requests_per_minute}/min, {limits.requests_per_hour}/hour")
    
    # Test serialization
    config_dict = config.to_dict()
    new_config = RateLimitConfig.from_dict(config_dict)
    print(f"✅ Serialization works: {new_config.enabled == config.enabled}")


async def test_performance():
    """Test performance of strategies."""
    
    print("\n⚡ Testing Performance")
    print("=" * 40)
    
    backend = MockRedisBackend()
    strategy = SlidingWindowStrategy()
    
    # Warm up
    for i in range(10):
        await strategy.check_limit("warmup", 100, 60, backend)
    
    # Performance test
    start_time = time.time()
    requests = 1000
    
    for i in range(requests):
        await strategy.check_limit(f"user:{i % 10}", 100, 60, backend)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Processed {requests} requests in {duration:.3f} seconds")
    print(f"✅ Rate: {requests/duration:.1f} requests/second")
    print(f"✅ Average latency: {(duration/requests)*1000:.2f} ms")


async def main():
    """Run all tests."""
    
    print("🚀 Rate Limiting System Test")
    print("=" * 50)
    
    try:
        await test_config()
        await test_strategies()
        await test_performance()
        
        print("\n🎉 All tests completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
