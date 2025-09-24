"""
Gamification API Routes

RESTful API endpoints for widget gamification features with ETag caching,
rate limiting, and mobile-optimized responses.

Endpoints:
- GET /v1/gamification/summary - Complete gamification data for widgets
- GET /v1/gamification/health - Service health check

Author: AI Nutritionist Development Team
Date: September 2025
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from src.api.schemas.gamification import (
    GamificationSummarySchema,
    ErrorSchema,
    WidgetContractSchema
)
from src.services.gamification.service import GamificationService
from src.api.middleware.caching import cache_manager


# Create router
router = APIRouter(prefix="/v1/gamification", tags=["gamification"])


# Dependency for gamification service
def get_gamification_service() -> GamificationService:
    """Get gamification service instance."""
    return GamificationService()


@router.get(
    "/summary",
    response_model=GamificationSummarySchema,
    summary="Get Gamification Summary",
    description="Get complete gamification data optimized for mobile widget display with ETag caching support (5-15 min TTL)",
    responses={
        200: {"description": "Gamification summary retrieved successfully"},
        304: {"description": "Not Modified - cached version is still valid"},
        400: {"description": "Invalid user ID format"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_gamification_summary(
    user_id: UUID,
    request: Request,
    response: Response,
    gamification_service: GamificationService = Depends(get_gamification_service)
) -> Dict[str, Any]:
    """
    Get complete gamification summary for widget display.
    
    Optimized for mobile widget consumption with:
    - ETag-based caching (5-15 minute TTL)
    - Conditional request support (304 Not Modified)
    - Compact data format for bandwidth efficiency
    - Deep links for app navigation
    
    Args:
        user_id: User identifier
        request: FastAPI request object
        response: FastAPI response object
        gamification_service: Injected gamification service
    
    Returns:
        Complete gamification summary with caching headers
    """
    try:
        # Get gamification summary
        summary = await gamification_service.get_gamification_summary(user_id)
        
        # Get cache headers from service
        cache_headers = await gamification_service.get_cache_headers(summary)
        
        # Check conditional requests (handled by middleware, but also check here)
        if_none_match = request.headers.get("if-none-match", "").strip('"')
        if if_none_match == summary.cache_key:
            # Return 304 Not Modified
            response.status_code = 304
            for header_name, header_value in cache_headers.items():
                response.headers[header_name] = header_value
            return {}
        
        # Convert to dict for JSON response
        summary_dict = {
            "user_id": str(summary.user_id),
            "adherence_ring": {
                "percentage": summary.adherence_ring.percentage,
                "level": summary.adherence_ring.level.value,
                "trend": summary.adherence_ring.trend,
                "days_tracked": summary.adherence_ring.days_tracked,
                "target_percentage": summary.adherence_ring.target_percentage,
                "ring_color": summary.adherence_ring.ring_color
            },
            "current_streak": {
                "current_count": summary.current_streak.current_count,
                "best_count": summary.current_streak.best_count,
                "milestone_reached": summary.current_streak.milestone_reached,
                "next_milestone": summary.current_streak.next_milestone,
                "streak_type": summary.current_streak.streak_type,
                "is_active": summary.current_streak.is_active,
                "motivation_message": summary.current_streak.motivation_message
            },
            "active_challenge": None,
            "total_points": summary.total_points,
            "level": summary.level,
            "level_progress": summary.level_progress,
            "last_updated": summary.last_updated.isoformat(),
            "cache_key": summary.cache_key,
            "widget_deep_link": summary.widget_deep_link,
            "compact_message": summary.compact_message,
            "primary_metric": summary.primary_metric,
            "secondary_metrics": summary.secondary_metrics
        }
        
        # Add challenge data if present
        if summary.active_challenge:
            summary_dict["active_challenge"] = {
                "id": str(summary.active_challenge.id),
                "title": summary.active_challenge.title,
                "description": summary.active_challenge.description,
                "challenge_type": summary.active_challenge.challenge_type.value,
                "status": summary.active_challenge.status.value,
                "progress": summary.active_challenge.progress,
                "target_value": summary.active_challenge.target_value,
                "current_value": summary.active_challenge.current_value,
                "expires_at": summary.active_challenge.expires_at.isoformat(),
                "reward_points": summary.active_challenge.reward_points,
                "difficulty_level": summary.active_challenge.difficulty_level
            }
        
        # Add cache headers
        for header_name, header_value in cache_headers.items():
            response.headers[header_name] = header_value
        
        # Add widget-specific headers
        response.headers["X-Widget-Version"] = "1.0"
        response.headers["X-Deep-Link-Scheme"] = "ainutritionist"
        
        return summary_dict
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while retrieving gamification data",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/health",
    summary="Gamification Service Health Check",
    description="Check health status of gamification service components",
    response_model=Dict[str, Any]
)
async def get_health(
    gamification_service: GamificationService = Depends(get_gamification_service)
) -> Dict[str, Any]:
    """
    Health check endpoint for gamification service.
    
    Returns:
        Service health status and component information
    """
    try:
        health_status = await gamification_service.health_check()
        
        # Add cache statistics
        cache_stats = cache_manager.get_cache_stats()
        health_status["cache"] = cache_stats
        
        return health_status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "health_check_failed",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/contract",
    response_model=WidgetContractSchema,
    summary="Widget Contract Specification",
    description="Get widget API contract for mobile app integration testing"
)
async def get_widget_contract() -> Dict[str, Any]:
    """
    Get widget API contract specification for integration testing.
    
    Returns:
        Widget contract with required fields, caching requirements, and schema information
    """
    contract = {
        "schema_version": "1.0",
        "required_fields": [
            "user_id",
            "adherence_ring",
            "current_streak",
            "compact_message",
            "widget_deep_link",
            "last_updated",
            "cache_key"
        ],
        "optional_fields": [
            "active_challenge",
            "secondary_metrics"
        ],
        "cache_requirements": {
            "etag_required": True,
            "cache_control_required": True,
            "min_ttl_minutes": 5,
            "max_ttl_minutes": 15,
            "conditional_requests_supported": True
        },
        "deep_link_format": "ainutritionist://dashboard?user_id={user_id}",
        "response_format": {
            "content_type": "application/json",
            "max_response_size_kb": 10,
            "compact_message_max_length": 50
        },
        "rate_limits": {
            "requests_per_minute": 60,
            "burst_limit": 10
        }
    }
    
    return contract


@router.post(
    "/cache/invalidate",
    summary="Invalidate User Cache",
    description="Invalidate cached gamification data for specific user (admin endpoint)"
)
async def invalidate_user_cache(
    user_id: UUID,
    gamification_service: GamificationService = Depends(get_gamification_service)
) -> Dict[str, Any]:
    """
    Invalidate cached gamification data for specific user.
    
    Use when user data changes and cache needs immediate refresh.
    
    Args:
        user_id: User identifier
        gamification_service: Injected gamification service
    
    Returns:
        Cache invalidation confirmation
    """
    try:
        # Invalidate service-level cache
        await gamification_service.invalidate_user_cache(user_id)
        
        # Invalidate middleware cache
        cache_manager.invalidate_pattern(str(user_id))
        
        return {
            "success": True,
            "user_id": str(user_id),
            "invalidated_at": datetime.now().isoformat(),
            "message": "User cache invalidated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cache_invalidation_failed",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Error handlers would be added to the main FastAPI app, not the router
