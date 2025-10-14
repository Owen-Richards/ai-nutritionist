"""
Rate Limiting Middleware
=======================

FastAPI middleware for automatic rate limiting with proper headers and responses.
"""

import time
import logging
from typing import Optional, Callable, Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import ipaddress

from .config import UserTier, RateLimitConfig
from .engine import get_rate_limit_engine
from .strategies import RateLimitResult

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""
    
    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        identifier_func: Optional[Callable[[Request], str]] = None,
        tier_func: Optional[Callable[[Request], UserTier]] = None,
        user_id_func: Optional[Callable[[Request], Optional[str]]] = None,
        skip_func: Optional[Callable[[Request], bool]] = None
    ):
        self.app = app
        self.config = config
        self.identifier_func = identifier_func or self._default_identifier
        self.tier_func = tier_func or self._default_tier
        self.user_id_func = user_id_func or self._default_user_id
        self.skip_func = skip_func or self._default_skip
        
    async def __call__(self, request: Request, call_next):
        """Process request through rate limiting."""
        
        # Skip rate limiting if disabled or for certain requests
        if self.skip_func(request):
            return await call_next(request)
        
        try:
            # Get rate limiting engine
            engine = await get_rate_limit_engine(self.config)
            
            # Extract request information
            identifier = self.identifier_func(request)
            user_tier = self.tier_func(request)
            user_id = self.user_id_func(request)
            endpoint = request.url.path
            
            # Check rate limits
            result = await engine.check_rate_limit(
                identifier=identifier,
                endpoint=endpoint,
                user_tier=user_tier,
                user_id=user_id
            )
            
            # Add rate limit headers to request state for response processing
            request.state.rate_limit_result = result
            
            # Block request if rate limited
            if not result.allowed:
                return self._create_rate_limit_response(result)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            self._add_rate_limit_headers(response, result)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            
            # Fail open - allow request but log error
            return await call_next(request)
    
    def _default_identifier(self, request: Request) -> str:
        """Default identifier extraction (IP address or API key)."""
        
        # Try to get API key from headers
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if api_key:
            # Use hash of API key as identifier
            import hashlib
            return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        
        # Fall back to IP address
        return self._get_client_ip(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            ip = forwarded_for.split(",")[0].strip()
            return f"ip:{ip}"
        
        # Check for other proxy headers
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return f"ip:{real_ip}"
        
        # Fall back to direct client IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _default_tier(self, request: Request) -> UserTier:
        """Default tier extraction."""
        
        # Try to get tier from headers or JWT token
        tier_header = request.headers.get("X-User-Tier")
        if tier_header:
            try:
                return UserTier(tier_header.lower())
            except ValueError:
                pass
        
        # Try to extract from Authorization header (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This would normally decode JWT and extract tier
                # For now, return premium for authenticated users
                return UserTier.PREMIUM
            except Exception:
                pass
        
        # Default to free tier
        return UserTier.FREE
    
    def _default_user_id(self, request: Request) -> Optional[str]:
        """Default user ID extraction."""
        
        # Try to get user ID from headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Try to extract from Authorization header (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This would normally decode JWT and extract user_id
                # For now, return None
                return None
            except Exception:
                pass
        
        return None
    
    def _default_skip(self, request: Request) -> bool:
        """Default skip logic for certain requests."""
        
        # Skip health checks and monitoring endpoints
        skip_paths = [
            "/health",
            "/healthz",
            "/ready",
            "/metrics",
            "/ping",
            "/favicon.ico"
        ]
        
        return request.url.path in skip_paths
    
    def _create_rate_limit_response(self, result: RateLimitResult) -> JSONResponse:
        """Create rate limit exceeded response."""
        
        headers = result.to_headers()
        
        content = {
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {result.limit} per {result.window_size}s",
            "retry_after": result.retry_after,
            "limit": result.limit,
            "remaining": result.remaining,
            "reset_time": result.reset_time,
            "strategy": result.strategy
        }
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=content,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, result: RateLimitResult):
        """Add rate limit headers to response."""
        
        if not self.config or not self.config.include_headers:
            return
        
        headers = result.to_headers(self.config.header_prefix)
        
        for key, value in headers.items():
            response.headers[key] = value


def create_rate_limit_middleware(
    config: Optional[RateLimitConfig] = None,
    identifier_func: Optional[Callable[[Request], str]] = None,
    tier_func: Optional[Callable[[Request], UserTier]] = None,
    user_id_func: Optional[Callable[[Request], Optional[str]]] = None,
    skip_func: Optional[Callable[[Request], bool]] = None
) -> Callable:
    """Create rate limiting middleware with custom configuration."""
    
    def middleware_factory(app):
        return RateLimitMiddleware(
            app=app,
            config=config,
            identifier_func=identifier_func,
            tier_func=tier_func,
            user_id_func=user_id_func,
            skip_func=skip_func
        )
    
    return middleware_factory


# Decorator for endpoint-specific rate limiting
def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    strategy: str = "sliding_window",
    burst_capacity: int = 10,
    tier_specific: bool = True
):
    """
    Decorator for endpoint-specific rate limiting.
    
    Args:
        requests_per_minute: Requests allowed per minute
        requests_per_hour: Requests allowed per hour
        strategy: Rate limiting strategy to use
        burst_capacity: Burst capacity for token bucket
        tier_specific: Whether to apply tier-specific limits
    """
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented as a dependency in FastAPI
            # For now, just call the original function
            return await func(*args, **kwargs)
        
        # Store rate limit metadata on function
        wrapper._rate_limit_config = {
            'requests_per_minute': requests_per_minute,
            'requests_per_hour': requests_per_hour,
            'strategy': strategy,
            'burst_capacity': burst_capacity,
            'tier_specific': tier_specific
        }
        
        return wrapper
    
    return decorator


# Utility functions for manual rate limit checking
async def check_rate_limit_manual(
    request: Request,
    custom_limits: Optional[Dict[str, int]] = None,
    identifier: Optional[str] = None,
    user_tier: Optional[UserTier] = None
) -> RateLimitResult:
    """Manually check rate limits for a request."""
    
    engine = await get_rate_limit_engine()
    
    # Use provided values or extract from request
    if identifier is None:
        middleware = RateLimitMiddleware(None)
        identifier = middleware._default_identifier(request)
    
    if user_tier is None:
        middleware = RateLimitMiddleware(None)
        user_tier = middleware._default_tier(request)
    
    return await engine.check_rate_limit(
        identifier=identifier,
        endpoint=request.url.path,
        user_tier=user_tier,
        custom_limits=custom_limits
    )


async def get_rate_limit_status_manual(
    request: Request,
    identifier: Optional[str] = None,
    user_tier: Optional[UserTier] = None
) -> Dict[str, Any]:
    """Get rate limit status for a request."""
    
    engine = await get_rate_limit_engine()
    
    if identifier is None:
        middleware = RateLimitMiddleware(None)
        identifier = middleware._default_identifier(request)
    
    if user_tier is None:
        middleware = RateLimitMiddleware(None)
        user_tier = middleware._default_tier(request)
    
    return await engine.get_rate_limit_status(
        identifier=identifier,
        user_tier=user_tier
    )
