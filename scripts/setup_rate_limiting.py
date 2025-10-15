#!/usr/bin/env python3
"""
Rate Limiting Setup Script
==========================

This script helps set up and configure the comprehensive rate limiting system.
"""

import asyncio
import os
import sys
import json
import argparse
from typing import Dict, Any
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from services.infrastructure.rate_limiting import (
        RateLimitConfig,
        RateLimitEngine,
        UserTier,
        RateLimitStrategy,
        TierLimits,
        EndpointConfig
    )
    from services.infrastructure.rate_limiting.redis_backend import RedisRateLimitBackend
except ImportError as e:
    print(f"Error importing rate limiting modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_default_config() -> RateLimitConfig:
    """Create a default rate limiting configuration."""
    
    config = RateLimitConfig(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        enabled=True,
        default_strategy=RateLimitStrategy.SLIDING_WINDOW,
        global_limit_per_second=1000,
        global_limit_per_minute=50000,
        include_headers=True,
        allow_on_error=True,
        fallback_to_memory=True
    )
    
    # Add default endpoint configurations
    default_endpoints = [
        EndpointConfig(
            path="/api/auth/login",
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            limits={
                UserTier.FREE: TierLimits(
                    requests_per_minute=5,
                    requests_per_hour=20,
                    requests_per_day=100,
                    burst_capacity=2
                ),
                UserTier.PREMIUM: TierLimits(
                    requests_per_minute=10,
                    requests_per_hour=50,
                    requests_per_day=500,
                    burst_capacity=5
                ),
            }
        ),
        EndpointConfig(
            path="/api/nutrition/analyze",
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            limits={
                UserTier.FREE: TierLimits(
                    requests_per_minute=10,
                    requests_per_hour=100,
                    requests_per_day=500,
                    burst_capacity=20,
                    ai_requests_per_hour=50
                ),
                UserTier.PREMIUM: TierLimits(
                    requests_per_minute=50,
                    requests_per_hour=1000,
                    requests_per_day=10000,
                    burst_capacity=100,
                    ai_requests_per_hour=500
                ),
            }
        ),
        EndpointConfig(
            path="/api/meal-plans/generate",
            strategy=RateLimitStrategy.LEAKY_BUCKET,
            limits={
                UserTier.FREE: TierLimits(
                    requests_per_minute=2,
                    requests_per_hour=10,
                    requests_per_day=3,
                    burst_capacity=1,
                    meal_plans_per_day=3
                ),
                UserTier.PREMIUM: TierLimits(
                    requests_per_minute=10,
                    requests_per_hour=100,
                    requests_per_day=20,
                    burst_capacity=5,
                    meal_plans_per_day=20
                ),
            }
        )
    ]
    
    for endpoint_config in default_endpoints:
        config.add_endpoint_config(endpoint_config)
    
    return config


async def test_redis_connection(redis_url: str) -> bool:
    """Test Redis connection."""
    
    print(f"Testing Redis connection to {redis_url}...")
    
    config = RateLimitConfig(redis_url=redis_url)
    backend = RedisRateLimitBackend(config)
    
    try:
        success = await backend.initialize()
        if success:
            print("✅ Redis connection successful")
            
            # Test basic operations
            await backend.set_value("test:key", "test_value", 10)
            value = await backend.get_value("test:key")
            
            if value == "test_value":
                print("✅ Redis read/write operations working")
            else:
                print("❌ Redis read/write operations failed")
                return False
            
            # Cleanup
            await backend.delete_key("test:key")
            await backend.close()
            
            return True
        else:
            print("❌ Redis connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False


async def test_rate_limiting(config: RateLimitConfig) -> bool:
    """Test rate limiting functionality."""
    
    print("Testing rate limiting functionality...")
    
    engine = RateLimitEngine(config)
    
    try:
        await engine.initialize()
        
        # Test basic rate limit check
        result = await engine.check_rate_limit(
            identifier="test:setup:user",
            endpoint="/api/test",
            user_tier=UserTier.FREE
        )
        
        if result.allowed:
            print("✅ Basic rate limit check working")
        else:
            print("❌ Basic rate limit check failed")
            return False
        
        # Test multiple strategies
        strategies = [
            RateLimitStrategy.TOKEN_BUCKET,
            RateLimitStrategy.SLIDING_WINDOW,
            RateLimitStrategy.FIXED_WINDOW,
            RateLimitStrategy.LEAKY_BUCKET
        ]
        
        for strategy in strategies:
            result = await engine.check_rate_limit(
                identifier=f"test:setup:{strategy.value}",
                endpoint="/api/test",
                user_tier=UserTier.FREE,
                strategy_override=strategy
            )
            
            if result.allowed:
                print(f"✅ {strategy.value} strategy working")
            else:
                print(f"❌ {strategy.value} strategy failed")
                return False
        
        # Test global stats
        stats = await engine.get_global_stats()
        if stats['total_requests'] > 0:
            print("✅ Statistics collection working")
        else:
            print("❌ Statistics collection failed")
            return False
        
        await engine.close()
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test error: {e}")
        await engine.close()
        return False


def save_config(config: RateLimitConfig, filename: str):
    """Save configuration to file."""
    
    config_dict = config.to_dict()
    
    # Convert enums to strings for JSON serialization
    if 'default_strategy' in config_dict:
        config_dict['default_strategy'] = config_dict['default_strategy']
    
    with open(filename, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    print(f"✅ Configuration saved to {filename}")


def load_config(filename: str) -> RateLimitConfig:
    """Load configuration from file."""
    
    with open(filename, 'r') as f:
        config_dict = json.load(f)
    
    # Convert strategy string back to enum
    if 'default_strategy' in config_dict:
        config_dict['default_strategy'] = RateLimitStrategy(config_dict['default_strategy'])
    
    return RateLimitConfig.from_dict(config_dict)


async def setup_monitoring():
    """Set up monitoring and alerting."""
    
    print("Setting up monitoring...")
    
    # Create monitoring configuration
    monitoring_config = {
        "metrics": {
            "rate_limit_requests_total": {
                "type": "counter",
                "description": "Total number of rate limit checks"
            },
            "rate_limit_blocked_total": {
                "type": "counter", 
                "description": "Total number of blocked requests"
            },
            "rate_limit_backend_healthy": {
                "type": "gauge",
                "description": "Rate limit backend health status"
            }
        },
        "alerts": {
            "high_block_rate": {
                "condition": "rate(rate_limit_blocked_total[5m]) > 10",
                "duration": "2m",
                "severity": "warning",
                "message": "High rate limit block rate"
            },
            "backend_unhealthy": {
                "condition": "rate_limit_backend_healthy == 0",
                "duration": "1m",
                "severity": "critical",
                "message": "Rate limit backend unhealthy"
            }
        }
    }
    
    # Save monitoring configuration
    with open("monitoring/rate_limiting_alerts.json", "w") as f:
        json.dump(monitoring_config, f, indent=2)
    
    print("✅ Monitoring configuration created")


def create_environment_file():
    """Create environment file with rate limiting configuration."""
    
    env_content = """# Rate Limiting Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Rate Limiting Settings
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STRATEGY=sliding_window
RATE_LIMIT_GLOBAL_PER_SECOND=1000
RATE_LIMIT_GLOBAL_PER_MINUTE=50000

# Headers
RATE_LIMIT_INCLUDE_HEADERS=true
RATE_LIMIT_HEADER_PREFIX=X-RateLimit

# Fallback
RATE_LIMIT_ALLOW_ON_ERROR=true
RATE_LIMIT_FALLBACK_TO_MEMORY=true

# Admin
RATE_LIMIT_ADMIN_TOKEN=admin-rate-limit-token
"""
    
    with open(".env.rate_limiting", "w") as f:
        f.write(env_content)
    
    print("✅ Environment file created: .env.rate_limiting")


async def run_benchmark(config: RateLimitConfig, requests: int = 1000):
    """Run performance benchmark."""
    
    print(f"Running benchmark with {requests} requests...")
    
    engine = RateLimitEngine(config)
    await engine.initialize()
    
    try:
        import time
        
        start_time = time.time()
        
        # Run concurrent requests
        tasks = []
        for i in range(requests):
            task = engine.check_rate_limit(
                identifier=f"benchmark:user:{i % 10}",  # 10 different users
                endpoint="/api/test",
                user_tier=UserTier.FREE
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        allowed_count = sum(1 for r in results if r.allowed)
        blocked_count = requests - allowed_count
        
        print(f"\n📊 Benchmark Results:")
        print(f"  Total requests: {requests}")
        print(f"  Allowed requests: {allowed_count}")
        print(f"  Blocked requests: {blocked_count}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Requests per second: {requests/duration:.2f}")
        print(f"  Average latency: {(duration/requests)*1000:.2f} ms")
        
    finally:
        await engine.close()


async def main():
    """Main setup function."""
    
    parser = argparse.ArgumentParser(description="Rate Limiting Setup Script")
    parser.add_argument("--test-redis", action="store_true", help="Test Redis connection")
    parser.add_argument("--test-system", action="store_true", help="Test rate limiting system")
    parser.add_argument("--create-config", action="store_true", help="Create default configuration")
    parser.add_argument("--save-config", help="Save configuration to file")
    parser.add_argument("--load-config", help="Load configuration from file")
    parser.add_argument("--setup-monitoring", action="store_true", help="Set up monitoring")
    parser.add_argument("--create-env", action="store_true", help="Create environment file")
    parser.add_argument("--benchmark", type=int, help="Run benchmark with N requests")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0", help="Redis URL")
    
    args = parser.parse_args()
    
    print("🚀 Rate Limiting Setup Script")
    print("=" * 40)
    
    config = None
    
    if args.load_config:
        print(f"Loading configuration from {args.load_config}...")
        config = load_config(args.load_config)
        print("✅ Configuration loaded")
    
    if args.create_config or config is None:
        print("Creating default configuration...")
        config = create_default_config()
        if args.redis_url:
            config.redis_url = args.redis_url
        print("✅ Default configuration created")
    
    if args.test_redis:
        success = await test_redis_connection(config.redis_url)
        if not success:
            print("❌ Redis test failed. Please check your Redis configuration.")
            return 1
    
    if args.test_system:
        success = await test_rate_limiting(config)
        if not success:
            print("❌ System test failed. Please check your configuration.")
            return 1
    
    if args.save_config:
        save_config(config, args.save_config)
    
    if args.setup_monitoring:
        await setup_monitoring()
    
    if args.create_env:
        create_environment_file()
    
    if args.benchmark:
        await run_benchmark(config, args.benchmark)
    
    print("\n✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Review the configuration file")
    print("2. Set up monitoring and alerting")
    print("3. Test with your application")
    print("4. Monitor performance and adjust limits as needed")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
