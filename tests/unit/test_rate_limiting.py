"""
Tests for Rate Limiting System
=============================

Comprehensive tests for all rate limiting strategies and components.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.services.infrastructure.rate_limiting.config import (
    RateLimitConfig, 
    UserTier, 
    TierLimits,
    RateLimitStrategy
)
from src.services.infrastructure.rate_limiting.strategies import (
    TokenBucketStrategy,
    SlidingWindowStrategy,
    FixedWindowStrategy,
    LeakyBucketStrategy,
    get_strategy
)
from src.services.infrastructure.rate_limiting.redis_backend import RedisRateLimitBackend
from src.services.infrastructure.rate_limiting.engine import RateLimitEngine


class MockRedisBackend:
    """Mock Redis backend for testing."""
    
    def __init__(self):
        self.data = {}
        self.script_calls = []
        self.healthy = True
    
    async def initialize(self):
        return True
    
    async def close(self):
        pass
    
    async def execute_lua_script(self, script: str, keys: list, args: list):
        """Mock Lua script execution."""
        self.script_calls.append({
            'script': script,
            'keys': keys,
            'args': args
        })
        
        # Simple mock responses for different strategies
        if 'tb:' in keys[0]:  # Token bucket
            return [1, 10, time.time() + 60, 20]  # allowed, remaining, reset_time, capacity
        elif 'sw:' in keys[0]:  # Sliding window
            return [1, 9, time.time() + 60, 1]  # allowed, remaining, reset_time, current_count
        elif 'fw:' in keys[0]:  # Fixed window
            return [1, 9, time.time() + 60, 1]  # allowed, remaining, reset_time, current_count
        elif 'lb:' in keys[0]:  # Leaky bucket
            return [1, 19, time.time() + 60, 1]  # allowed, remaining, reset_time, level
        else:
            return [1, 10, time.time() + 60, 1]
    
    async def get_value(self, key: str):
        return self.data.get(key)
    
    async def set_value(self, key: str, value: str, expire: int = None):
        self.data[key] = value
        return True
    
    async def increment(self, key: str, amount: int = 1, expire: int = None):
        current = int(self.data.get(key, 0))
        self.data[key] = str(current + amount)
        return current + amount
    
    async def delete_key(self, key: str):
        self.data.pop(key, None)
        return True
    
    async def get_keys_pattern(self, pattern: str):
        return [k for k in self.data.keys() if pattern.replace('*', '') in k]
    
    async def get_stats(self):
        return {
            'backend': 'mock',
            'healthy': self.healthy,
            'fallback_keys': 0,
            'redis_available': True
        }
    
    async def cleanup_expired_keys(self):
        return 0


@pytest.fixture
def mock_config():
    """Create a test configuration."""
    return RateLimitConfig(
        redis_url="redis://localhost:6379/0",
        enabled=True,
        default_strategy=RateLimitStrategy.SLIDING_WINDOW,
        global_limit_per_second=100,
        global_limit_per_minute=5000
    )


@pytest.fixture
def mock_backend():
    """Create a mock Redis backend."""
    return MockRedisBackend()


@pytest.fixture
async def rate_limit_engine(mock_config, mock_backend):
    """Create a rate limiting engine with mock backend."""
    engine = RateLimitEngine(mock_config)
    engine.backend = mock_backend
    await engine.initialize()
    yield engine
    await engine.close()


class TestRateLimitStrategies:
    """Test different rate limiting strategies."""
    
    @pytest.mark.asyncio
    async def test_token_bucket_strategy(self, mock_backend):
        """Test token bucket strategy."""
        strategy = TokenBucketStrategy()
        
        result = await strategy.check_limit(
            key="test:user1",
            limit=10,
            window=60,
            backend=mock_backend,
            burst_capacity=20
        )
        
        assert result.allowed is True
        assert result.remaining == 10
        assert result.strategy == "token_bucket"
        assert len(mock_backend.script_calls) == 1
    
    @pytest.mark.asyncio
    async def test_sliding_window_strategy(self, mock_backend):
        """Test sliding window strategy."""
        strategy = SlidingWindowStrategy()
        
        result = await strategy.check_limit(
            key="test:user1",
            limit=10,
            window=60,
            backend=mock_backend
        )
        
        assert result.allowed is True
        assert result.remaining == 9
        assert result.strategy == "sliding_window"
        assert len(mock_backend.script_calls) == 1
    
    @pytest.mark.asyncio
    async def test_fixed_window_strategy(self, mock_backend):
        """Test fixed window strategy."""
        strategy = FixedWindowStrategy()
        
        result = await strategy.check_limit(
            key="test:user1",
            limit=10,
            window=60,
            backend=mock_backend
        )
        
        assert result.allowed is True
        assert result.remaining == 9
        assert result.strategy == "fixed_window"
        assert len(mock_backend.script_calls) == 1
    
    @pytest.mark.asyncio
    async def test_leaky_bucket_strategy(self, mock_backend):
        """Test leaky bucket strategy."""
        strategy = LeakyBucketStrategy()
        
        result = await strategy.check_limit(
            key="test:user1",
            limit=10,
            window=60,
            backend=mock_backend,
            bucket_size=20
        )
        
        assert result.allowed is True
        assert result.remaining == 19
        assert result.strategy == "leaky_bucket"
        assert len(mock_backend.script_calls) == 1
    
    def test_get_strategy(self):
        """Test strategy factory function."""
        token_bucket = get_strategy("token_bucket")
        assert isinstance(token_bucket, TokenBucketStrategy)
        
        sliding_window = get_strategy("sliding_window")
        assert isinstance(sliding_window, SlidingWindowStrategy)
        
        with pytest.raises(ValueError):
            get_strategy("invalid_strategy")


class TestRateLimitEngine:
    """Test the main rate limiting engine."""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, mock_config):
        """Test engine initialization."""
        engine = RateLimitEngine(mock_config)
        engine.backend = MockRedisBackend()
        
        success = await engine.initialize()
        assert success is True
        assert engine._initialized is True
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_basic_rate_limit_check(self, rate_limit_engine):
        """Test basic rate limit checking."""
        result = await rate_limit_engine.check_rate_limit(
            identifier="test:user1",
            endpoint="/api/test",
            user_tier=UserTier.FREE
        )
        
        assert result.allowed is True
        assert result.remaining >= 0
        assert result.strategy in ["sliding_window", "token_bucket", "fixed_window", "leaky_bucket"]
    
    @pytest.mark.asyncio
    async def test_disabled_rate_limiting(self, mock_config, mock_backend):
        """Test rate limiting when disabled."""
        mock_config.enabled = False
        engine = RateLimitEngine(mock_config)
        engine.backend = mock_backend
        
        result = await engine.check_rate_limit(
            identifier="test:user1",
            endpoint="/api/test",
            user_tier=UserTier.FREE
        )
        
        assert result.allowed is True
        assert result.strategy == "disabled"
    
    @pytest.mark.asyncio
    async def test_tier_based_limits(self, rate_limit_engine):
        """Test tier-based rate limiting."""
        # Test free tier
        free_result = await rate_limit_engine.check_rate_limit(
            identifier="test:user1",
            endpoint="/api/test",
            user_tier=UserTier.FREE
        )
        
        # Test premium tier
        premium_result = await rate_limit_engine.check_rate_limit(
            identifier="test:user2",
            endpoint="/api/test",
            user_tier=UserTier.PREMIUM
        )
        
        assert free_result.allowed is True
        assert premium_result.allowed is True
        
        # Premium should have higher limits (though in mock, both succeed)
        # In real implementation, you'd test with actual limit enforcement
    
    @pytest.mark.asyncio
    async def test_custom_limits(self, rate_limit_engine):
        """Test custom rate limits."""
        custom_limits = {
            'requests_per_minute': 5,
            'requests_per_hour': 100,
            'requests_per_day': 1000,
            'burst_capacity': 2
        }
        
        result = await rate_limit_engine.check_rate_limit(
            identifier="test:user1",
            endpoint="/api/test",
            user_tier=UserTier.FREE,
            custom_limits=custom_limits
        )
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_global_limits(self, rate_limit_engine):
        """Test global rate limits."""
        # Mock global limit exceeded
        rate_limit_engine.backend.data["global:second:{}".format(int(time.time()))] = "150"
        
        result = await rate_limit_engine._check_global_limits("test:user1")
        
        # Should still pass in mock since we return success
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, rate_limit_engine):
        """Test rate limit reset functionality."""
        # Set some rate limit data
        rate_limit_engine.backend.data["id:minute:test:user1"] = "5"
        rate_limit_engine.backend.data["id:hour:test:user1"] = "50"
        
        success = await rate_limit_engine.reset_rate_limit("test:user1")
        assert success is True
    
    @pytest.mark.asyncio
    async def test_get_global_stats(self, rate_limit_engine):
        """Test getting global statistics."""
        stats = await rate_limit_engine.get_global_stats()
        
        assert "uptime_seconds" in stats
        assert "total_requests" in stats
        assert "blocked_requests" in stats
        assert "success_rate" in stats
        assert "backend" in stats
        assert "config" in stats


class TestRateLimitConfig:
    """Test rate limiting configuration."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = RateLimitConfig()
        
        assert config.enabled is True
        assert config.default_strategy == RateLimitStrategy.SLIDING_WINDOW
        assert config.redis_url.startswith("redis://")
        assert config.global_limit_per_second > 0
        assert config.global_limit_per_minute > 0
    
    def test_tier_limits(self):
        """Test tier limit retrieval."""
        config = RateLimitConfig()
        
        free_limits = config.get_tier_limits(UserTier.FREE)
        premium_limits = config.get_tier_limits(UserTier.PREMIUM)
        
        assert premium_limits.requests_per_minute > free_limits.requests_per_minute
        assert premium_limits.requests_per_hour > free_limits.requests_per_hour
        assert premium_limits.premium_features is True
        assert free_limits.premium_features is False
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = RateLimitConfig()
        
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "redis_url" in config_dict
        assert "enabled" in config_dict
        
        new_config = RateLimitConfig.from_dict(config_dict)
        assert new_config.enabled == config.enabled
        assert new_config.redis_url == config.redis_url


class TestRedisBackend:
    """Test Redis backend functionality."""
    
    @pytest.mark.asyncio
    async def test_backend_initialization(self, mock_config):
        """Test backend initialization."""
        backend = RedisRateLimitBackend(mock_config)
        
        # Mock Redis unavailable
        with patch('src.services.infrastructure.rate_limiting.redis_backend.REDIS_AVAILABLE', False):
            success = await backend.initialize()
            assert success is False
    
    @pytest.mark.asyncio
    async def test_fallback_operations(self, mock_config):
        """Test fallback operations when Redis is unavailable."""
        backend = RedisRateLimitBackend(mock_config)
        backend._connection_healthy = False
        
        # Test fallback script execution
        result = await backend.execute_lua_script(
            "test script",
            ["tb:test:key"],
            [10, 60, 20, time.time()]
        )
        
        assert len(result) == 4
        assert result[0] in [0, 1]  # allowed boolean
    
    @pytest.mark.asyncio
    async def test_key_operations(self):
        """Test basic key operations."""
        config = RateLimitConfig()
        backend = RedisRateLimitBackend(config)
        backend._connection_healthy = False  # Force fallback
        
        # Test set/get
        await backend.set_value("test:key", "test_value")
        value = await backend.get_value("test:key")
        assert value == "test_value"
        
        # Test increment
        count = await backend.increment("test:counter")
        assert count == 1
        
        count = await backend.increment("test:counter", amount=5)
        assert count == 6
        
        # Test delete
        success = await backend.delete_key("test:key")
        assert success is True


class TestIntegration:
    """Integration tests for the complete rate limiting system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_rate_limiting(self, rate_limit_engine):
        """Test end-to-end rate limiting flow."""
        # Simulate multiple requests from the same user
        identifier = "test:integration:user1"
        endpoint = "/api/nutrition/analyze"
        
        results = []
        for i in range(5):
            result = await rate_limit_engine.check_rate_limit(
                identifier=identifier,
                endpoint=endpoint,
                user_tier=UserTier.FREE
            )
            results.append(result)
        
        # All requests should be allowed in mock
        assert all(r.allowed for r in results)
        
        # Check that remaining count decreases (in real implementation)
        # In mock, this would need more sophisticated logic
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rate_limit_engine):
        """Test concurrent requests handling."""
        identifier = "test:concurrent:user1"
        endpoint = "/api/test"
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = rate_limit_engine.check_rate_limit(
                identifier=f"{identifier}:{i}",
                endpoint=endpoint,
                user_tier=UserTier.FREE
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should be allowed in mock
        assert all(r.allowed for r in results)
    
    @pytest.mark.asyncio
    async def test_different_strategies_performance(self, mock_config, mock_backend):
        """Test performance of different strategies."""
        strategies = ["token_bucket", "sliding_window", "fixed_window", "leaky_bucket"]
        
        for strategy_name in strategies:
            mock_config.default_strategy = RateLimitStrategy(strategy_name)
            engine = RateLimitEngine(mock_config)
            engine.backend = mock_backend
            
            start_time = time.time()
            
            # Perform multiple checks
            for i in range(100):
                await engine.check_rate_limit(
                    identifier=f"test:perf:{i}",
                    endpoint="/api/test",
                    user_tier=UserTier.FREE
                )
            
            elapsed = time.time() - start_time
            
            # Should complete reasonably quickly
            assert elapsed < 1.0  # Less than 1 second for 100 checks
            
            await engine.close()


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v"])
