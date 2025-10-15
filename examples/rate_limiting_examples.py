"""
Rate Limiting Usage Examples
===========================

Comprehensive examples showing how to use the rate limiting system.
"""

import asyncio
import time
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any

from src.services.infrastructure.rate_limiting import (
    RateLimitConfig,
    RateLimitEngine, 
    RateLimitMiddleware,
    UserTier,
    RateLimitStrategy,
    TierLimits,
    EndpointConfig,
    rate_limit,
    check_rate_limit_manual,
    get_rate_limit_status_manual
)
from src.services.infrastructure.rate_limiting.admin_api import router as admin_router


def create_custom_config() -> RateLimitConfig:
    """Create a custom rate limiting configuration."""
    
    config = RateLimitConfig(
        # Redis configuration
        redis_url="redis://localhost:6379/0",
        redis_key_prefix="app:rl:",
        redis_pool_size=20,
        
        # Global settings
        enabled=True,
        default_strategy=RateLimitStrategy.SLIDING_WINDOW,
        
        # Global limits (emergency brake)
        global_limit_per_second=1000,
        global_limit_per_minute=50000,
        
        # Headers
        include_headers=True,
        header_prefix="X-RateLimit",
        
        # Fallback
        allow_on_error=True,
        fallback_to_memory=True
    )
    
    # Add custom endpoint configurations
    config.add_endpoint_config(EndpointConfig(
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
    ))
    
    config.add_endpoint_config(EndpointConfig(
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
    ))
    
    return config


def create_app_with_rate_limiting() -> FastAPI:
    """Create FastAPI app with rate limiting middleware."""
    
    app = FastAPI(title="AI Nutritionist API")
    
    # Custom identifier function (extract from API key or IP)
    def get_identifier(request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            import hashlib
            return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        
        # Fall back to IP
        return f"ip:{request.client.host}"
    
    # Custom tier function (extract from JWT or headers)
    def get_user_tier(request: Request) -> UserTier:
        tier_header = request.headers.get("X-User-Tier")
        if tier_header:
            try:
                return UserTier(tier_header.lower())
            except ValueError:
                pass
        
        # Check for premium API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key.startswith("premium_"):
            return UserTier.PREMIUM
        elif api_key.startswith("enterprise_"):
            return UserTier.ENTERPRISE
        
        return UserTier.FREE
    
    # Custom user ID function
    def get_user_id(request: Request) -> str:
        return request.headers.get("X-User-ID")
    
    # Custom skip function
    def should_skip(request: Request) -> bool:
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        return request.url.path in skip_paths
    
    # Add rate limiting middleware
    config = create_custom_config()
    middleware = RateLimitMiddleware(
        app=app,
        config=config,
        identifier_func=get_identifier,
        tier_func=get_user_tier,
        user_id_func=get_user_id,
        skip_func=should_skip
    )
    app.middleware("http")(middleware)
    
    # Include admin API
    app.include_router(admin_router)
    
    return app


# Example endpoints with different rate limiting strategies
app = create_app_with_rate_limiting()


@app.get("/health")
async def health_check():
    """Health check endpoint (no rate limiting)."""
    return {"status": "healthy", "timestamp": time.time()}


@app.post("/api/auth/login")
async def login(request: Request):
    """Login endpoint with strict rate limiting."""
    # This endpoint uses configuration from EndpointConfig
    return {"message": "Login successful", "timestamp": time.time()}


@app.post("/api/nutrition/analyze")
@rate_limit(
    requests_per_minute=10,
    requests_per_hour=100,
    strategy="token_bucket",
    burst_capacity=20
)
async def analyze_nutrition(request: Request):
    """Nutrition analysis with token bucket rate limiting."""
    return {
        "analysis": "Nutritional data here...",
        "timestamp": time.time()
    }


@app.get("/api/meal-plans/generate")
async def generate_meal_plan(request: Request):
    """Meal plan generation with manual rate limit checking."""
    
    # Manual rate limit check with custom limits
    result = await check_rate_limit_manual(
        request=request,
        custom_limits={
            'requests_per_minute': 2,
            'requests_per_hour': 10,
            'requests_per_day': 5,
            'burst_capacity': 1
        }
    )
    
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": result.retry_after,
                "limit": result.limit,
                "remaining": result.remaining
            },
            headers=result.to_headers()
        )
    
    return {
        "meal_plan": "Generated meal plan here...",
        "timestamp": time.time(),
        "rate_limit": {
            "remaining": result.remaining,
            "reset_time": result.reset_time
        }
    }


@app.get("/api/user/rate-limit-status")
async def get_rate_limit_status(request: Request):
    """Get current rate limit status for the user."""
    
    status = await get_rate_limit_status_manual(request)
    return {"status": "success", "data": status}


# Example usage functions
async def example_basic_usage():
    """Example of basic rate limiting usage."""
    
    config = RateLimitConfig()
    engine = RateLimitEngine(config)
    await engine.initialize()
    
    try:
        # Check rate limit
        result = await engine.check_rate_limit(
            identifier="user123",
            endpoint="/api/test",
            user_tier=UserTier.FREE
        )
        
        print(f"Request allowed: {result.allowed}")
        print(f"Remaining requests: {result.remaining}")
        print(f"Reset time: {result.reset_time}")
        print(f"Strategy used: {result.strategy}")
        
        # Get status
        status = await engine.get_rate_limit_status("user123", UserTier.FREE)
        print(f"Current status: {status}")
        
    finally:
        await engine.close()


async def example_multiple_strategies():
    """Example using different strategies."""
    
    strategies = [
        RateLimitStrategy.TOKEN_BUCKET,
        RateLimitStrategy.SLIDING_WINDOW,
        RateLimitStrategy.FIXED_WINDOW,
        RateLimitStrategy.LEAKY_BUCKET
    ]
    
    config = RateLimitConfig()
    engine = RateLimitEngine(config)
    await engine.initialize()
    
    try:
        for strategy in strategies:
            print(f"\nTesting {strategy.value} strategy:")
            
            for i in range(5):
                result = await engine.check_rate_limit(
                    identifier=f"test_user_{strategy.value}",
                    endpoint="/api/test",
                    user_tier=UserTier.FREE,
                    strategy_override=strategy
                )
                
                print(f"  Request {i+1}: allowed={result.allowed}, remaining={result.remaining}")
                
                # Small delay between requests
                await asyncio.sleep(0.1)
    
    finally:
        await engine.close()


async def example_tier_differences():
    """Example showing differences between user tiers."""
    
    config = RateLimitConfig()
    engine = RateLimitEngine(config)
    await engine.initialize()
    
    try:
        tiers = [UserTier.FREE, UserTier.PREMIUM, UserTier.ENTERPRISE]
        
        for tier in tiers:
            print(f"\nTesting {tier.value} tier:")
            
            # Get tier limits
            limits = config.get_tier_limits(tier)
            print(f"  Limits: {limits.requests_per_minute}/min, {limits.requests_per_hour}/hour")
            
            # Test a few requests
            for i in range(3):
                result = await engine.check_rate_limit(
                    identifier=f"user_{tier.value}",
                    endpoint="/api/test",
                    user_tier=tier
                )
                
                print(f"  Request {i+1}: allowed={result.allowed}, remaining={result.remaining}")
    
    finally:
        await engine.close()


async def example_admin_operations():
    """Example of admin operations."""
    
    config = RateLimitConfig()
    engine = RateLimitEngine(config)
    await engine.initialize()
    
    try:
        # Get global stats
        stats = await engine.get_global_stats()
        print("Global statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Blocked requests: {stats['blocked_requests']}")
        print(f"  Success rate: {stats['success_rate']:.2%}")
        
        # Reset rate limits for a user
        user_id = "test_user_admin"
        
        # Generate some requests first
        for i in range(5):
            await engine.check_rate_limit(
                identifier=user_id,
                endpoint="/api/test",
                user_tier=UserTier.FREE
            )
        
        # Reset limits
        success = await engine.reset_rate_limit(user_id)
        print(f"\nRate limit reset successful: {success}")
        
        # Get backend health
        backend_stats = await engine.backend.get_stats()
        print(f"\nBackend health:")
        print(f"  Healthy: {backend_stats.get('healthy')}")
        print(f"  Backend type: {backend_stats.get('backend')}")
        
    finally:
        await engine.close()


async def example_load_testing():
    """Example of load testing the rate limiting system."""
    
    config = RateLimitConfig()
    engine = RateLimitEngine(config)
    await engine.initialize()
    
    try:
        print("Running load test...")
        
        # Create multiple concurrent users
        users = [f"load_test_user_{i}" for i in range(10)]
        requests_per_user = 20
        
        async def user_requests(user_id: str):
            results = []
            for i in range(requests_per_user):
                result = await engine.check_rate_limit(
                    identifier=user_id,
                    endpoint="/api/test",
                    user_tier=UserTier.FREE
                )
                results.append(result)
                await asyncio.sleep(0.01)  # Small delay
            return results
        
        # Run concurrent requests
        start_time = time.time()
        all_results = await asyncio.gather(*[user_requests(user) for user in users])
        end_time = time.time()
        
        # Analyze results
        total_requests = len(users) * requests_per_user
        allowed_requests = sum(1 for user_results in all_results 
                             for result in user_results if result.allowed)
        blocked_requests = total_requests - allowed_requests
        
        print(f"\nLoad test results:")
        print(f"  Total requests: {total_requests}")
        print(f"  Allowed requests: {allowed_requests}")
        print(f"  Blocked requests: {blocked_requests}")
        print(f"  Success rate: {allowed_requests/total_requests:.2%}")
        print(f"  Duration: {end_time - start_time:.2f} seconds")
        print(f"  Requests per second: {total_requests/(end_time - start_time):.2f}")
    
    finally:
        await engine.close()


if __name__ == "__main__":
    # Run examples
    print("=== Basic Usage Example ===")
    asyncio.run(example_basic_usage())
    
    print("\n=== Multiple Strategies Example ===")
    asyncio.run(example_multiple_strategies())
    
    print("\n=== Tier Differences Example ===")
    asyncio.run(example_tier_differences())
    
    print("\n=== Admin Operations Example ===")
    asyncio.run(example_admin_operations())
    
    print("\n=== Load Testing Example ===")
    asyncio.run(example_load_testing())
