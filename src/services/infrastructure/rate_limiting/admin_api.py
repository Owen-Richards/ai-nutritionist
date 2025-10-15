"""
Rate Limiting Admin API
======================

Admin endpoints for managing rate limits, viewing stats, and configuration.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional, List
import logging

from .config import RateLimitConfig, UserTier
from .engine import get_rate_limit_engine
from .middleware import get_rate_limit_status_manual

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/admin/rate-limits", tags=["Rate Limiting Admin"])


async def verify_admin_token(token: str = Depends(security)):
    """Verify admin token for rate limit management."""
    # This should be implemented with proper admin authentication
    # For now, just check for a simple admin token
    if not token or token.credentials != "admin-rate-limit-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
    return token


@router.get("/stats")
async def get_global_stats(admin_token: str = Depends(verify_admin_token)):
    """Get global rate limiting statistics."""
    
    try:
        engine = await get_rate_limit_engine()
        stats = await engine.get_global_stats()
        return {"status": "success", "data": stats}
        
    except Exception as e:
        logger.error(f"Failed to get global stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/status/{identifier}")
async def get_rate_limit_status(
    identifier: str,
    user_tier: UserTier = Query(UserTier.FREE),
    user_id: Optional[str] = Query(None),
    admin_token: str = Depends(verify_admin_token)
):
    """Get rate limit status for a specific identifier."""
    
    try:
        engine = await get_rate_limit_engine()
        status = await engine.get_rate_limit_status(
            identifier=identifier,
            user_tier=user_tier,
            user_id=user_id
        )
        return {"status": "success", "data": status}
        
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit status"
        )


@router.post("/reset/{identifier}")
async def reset_rate_limit(
    identifier: str,
    scope: str = Query("all", description="Scope to reset: all, minute, hour, day"),
    admin_token: str = Depends(verify_admin_token)
):
    """Reset rate limits for a specific identifier."""
    
    try:
        engine = await get_rate_limit_engine()
        success = await engine.reset_rate_limit(identifier, scope)
        
        if success:
            return {
                "status": "success",
                "message": f"Rate limits reset for {identifier} (scope: {scope})"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset rate limits"
            )
            
    except Exception as e:
        logger.error(f"Failed to reset rate limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset rate limits"
        )


@router.get("/config")
async def get_rate_limit_config(admin_token: str = Depends(verify_admin_token)):
    """Get current rate limiting configuration."""
    
    try:
        engine = await get_rate_limit_engine()
        config_dict = engine.config.to_dict()
        return {"status": "success", "data": config_dict}
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.put("/config")
async def update_rate_limit_config(
    config_update: Dict[str, Any],
    admin_token: str = Depends(verify_admin_token)
):
    """Update rate limiting configuration."""
    
    try:
        engine = await get_rate_limit_engine()
        
        # Create new config from current config and updates
        current_config = engine.config.to_dict()
        current_config.update(config_update)
        
        new_config = RateLimitConfig.from_dict(current_config)
        await engine.update_config(new_config)
        
        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "data": new_config.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.get("/backend/health")
async def get_backend_health(admin_token: str = Depends(verify_admin_token)):
    """Get backend health status."""
    
    try:
        engine = await get_rate_limit_engine()
        backend_stats = await engine.backend.get_stats()
        
        return {
            "status": "success",
            "data": {
                "backend_type": backend_stats.get("backend"),
                "healthy": backend_stats.get("healthy"),
                "redis_available": backend_stats.get("redis_available"),
                "fallback_keys": backend_stats.get("fallback_keys"),
                "details": backend_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get backend health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve backend health"
        )


@router.post("/test")
async def test_rate_limit(
    identifier: str = Query(..., description="Test identifier"),
    endpoint: str = Query("/api/test", description="Test endpoint"),
    user_tier: UserTier = Query(UserTier.FREE),
    requests: int = Query(5, description="Number of test requests"),
    admin_token: str = Depends(verify_admin_token)
):
    """Test rate limiting with multiple requests."""
    
    try:
        engine = await get_rate_limit_engine()
        results = []
        
        for i in range(requests):
            result = await engine.check_rate_limit(
                identifier=f"test:{identifier}",
                endpoint=endpoint,
                user_tier=user_tier
            )
            
            results.append({
                "request": i + 1,
                "allowed": result.allowed,
                "remaining": result.remaining,
                "reset_time": result.reset_time,
                "strategy": result.strategy
            })
        
        return {
            "status": "success",
            "data": {
                "test_identifier": f"test:{identifier}",
                "endpoint": endpoint,
                "user_tier": user_tier.value,
                "total_requests": requests,
                "results": results
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to test rate limiting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test rate limiting"
        )


@router.get("/leaderboard")
async def get_usage_leaderboard(
    limit: int = Query(10, description="Number of top users to return"),
    time_window: str = Query("hour", description="Time window: minute, hour, day"),
    admin_token: str = Depends(verify_admin_token)
):
    """Get leaderboard of highest rate limit usage."""
    
    try:
        engine = await get_rate_limit_engine()
        
        # This would require additional tracking in Redis
        # For now, return a placeholder response
        
        leaderboard = {
            "time_window": time_window,
            "top_users": [
                {
                    "identifier": "ip:192.168.1.100",
                    "requests": 500,
                    "tier": "premium",
                    "blocked_requests": 5
                },
                {
                    "identifier": "api:user123",
                    "requests": 350,
                    "tier": "free",
                    "blocked_requests": 12
                }
            ],
            "total_tracked": 250
        }
        
        return {"status": "success", "data": leaderboard}
        
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage leaderboard"
        )


@router.post("/cleanup")
async def cleanup_expired_data(admin_token: str = Depends(verify_admin_token)):
    """Manually trigger cleanup of expired rate limiting data."""
    
    try:
        engine = await get_rate_limit_engine()
        cleaned_count = await engine.backend.cleanup_expired_keys()
        
        return {
            "status": "success",
            "message": f"Cleanup completed. Removed {cleaned_count} expired keys.",
            "data": {"cleaned_keys": cleaned_count}
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired data"
        )


@router.get("/tiers")
async def get_tier_configurations(admin_token: str = Depends(verify_admin_token)):
    """Get all tier configurations."""
    
    try:
        engine = await get_rate_limit_engine()
        
        tiers = {}
        for tier in UserTier:
            limits = engine.config.get_tier_limits(tier)
            tiers[tier.value] = {
                "requests_per_minute": limits.requests_per_minute,
                "requests_per_hour": limits.requests_per_hour,
                "requests_per_day": limits.requests_per_day,
                "burst_capacity": limits.burst_capacity,
                "concurrent_requests": limits.concurrent_requests,
                "ai_requests_per_hour": limits.ai_requests_per_hour,
                "meal_plans_per_day": limits.meal_plans_per_day,
                "premium_features": limits.premium_features,
                "priority_support": limits.priority_support
            }
        
        return {"status": "success", "data": tiers}
        
    except Exception as e:
        logger.error(f"Failed to get tier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tier configurations"
        )
