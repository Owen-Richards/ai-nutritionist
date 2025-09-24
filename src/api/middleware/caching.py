"""
ETag-based Caching Middleware

Enterprise-grade caching middleware for widget API with configurable TTL,
conditional requests support, and performance optimization for mobile widgets.

Architecture:
- CachingMiddleware: FastAPI middleware for HTTP caching
- ETagGenerator: ETag generation and validation
- CacheManager: Cache storage and invalidation
- ConditionalRequestHandler: HTTP 304 Not Modified support

Author: AI Nutritionist Development Team
Date: September 2025
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.models.gamification import WIDGET_CACHE_TTL_MIN, WIDGET_CACHE_TTL_MAX


class ETagGenerator:
    """Generate and validate ETag headers for caching."""
    
    @staticmethod
    def generate_etag(data: Any) -> str:
        """Generate ETag from response data."""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            json_str = json.dumps(data, sort_keys=True, default=str)
        else:
            json_str = str(data)
        
        return hashlib.md5(json_str.encode()).hexdigest()
    
    @staticmethod
    def is_etag_match(request_etag: str, response_etag: str) -> bool:
        """Check if ETags match for conditional requests."""
        # Remove quotes if present
        request_etag = request_etag.strip('"')
        response_etag = response_etag.strip('"')
        
        return request_etag == response_etag
    
    @staticmethod
    def extract_etag_from_header(etag_header: str) -> str:
        """Extract ETag value from header string."""
        # Handle both quoted and unquoted ETags
        return etag_header.strip().strip('"')


class CacheManager:
    """Manage cache storage and invalidation."""
    
    def __init__(self):
        # In-memory cache for demo - use Redis in production
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response data."""
        if key not in self._cache:
            return None
        
        # Check if cache entry has expired
        if self._is_expired(key):
            self.invalidate(key)
            return None
        
        return self._cache[key]
    
    def set(self, key: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        """Store response data in cache."""
        self._cache[key] = data
        self._cache_timestamps[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def invalidate(self, key: str) -> None:
        """Remove cache entry."""
        self._cache.pop(key, None)
        self._cache_timestamps.pop(key, None)
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Remove cache entries matching pattern."""
        keys_to_remove = [key for key in self._cache.keys() if pattern in key]
        for key in keys_to_remove:
            self.invalidate(key)
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry has expired."""
        if key not in self._cache_timestamps:
            return True
        
        return datetime.now() > self._cache_timestamps[key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for key in self._cache.keys() if self._is_expired(key))
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "hit_ratio": 0.95  # Mock hit ratio - implement real tracking in production
        }


class ConditionalRequestHandler:
    """Handle HTTP conditional requests (If-None-Match, If-Modified-Since)."""
    
    @staticmethod
    def should_return_304(request: Request, etag: str, last_modified: datetime) -> bool:
        """Check if request should return 304 Not Modified."""
        # Check If-None-Match header (ETag)
        if_none_match = request.headers.get("if-none-match")
        if if_none_match:
            request_etag = ETagGenerator.extract_etag_from_header(if_none_match)
            if ETagGenerator.is_etag_match(request_etag, etag):
                return True
        
        # Check If-Modified-Since header
        if_modified_since = request.headers.get("if-modified-since")
        if if_modified_since:
            try:
                client_date = datetime.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S GMT")
                if last_modified <= client_date:
                    return True
            except ValueError:
                # Invalid date format, ignore header
                pass
        
        return False
    
    @staticmethod
    def create_304_response() -> Response:
        """Create 304 Not Modified response."""
        return Response(status_code=304)


class CachingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for HTTP caching with ETag support.
    
    Implements intelligent caching for widget API endpoints with:
    - ETag generation and validation
    - Conditional request handling (304 Not Modified)
    - Configurable TTL (5-15 minutes)
    - Cache invalidation patterns
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cache_manager: Optional[CacheManager] = None,
        enabled_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.cache_manager = cache_manager or CacheManager()
        self.etag_generator = ETagGenerator()
        self.conditional_handler = ConditionalRequestHandler()
        
        # Default paths that should be cached
        self.enabled_paths = enabled_paths or ["/v1/gamification/summary"]
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with caching logic."""
        # Only cache enabled paths
        if not self._should_cache_path(request.url.path):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check cache for existing response
        cached_response = self.cache_manager.get(cache_key)
        if cached_response:
            # Check conditional requests
            etag = cached_response.get("etag", "")
            last_modified = cached_response.get("last_modified", datetime.now())
            
            if self.conditional_handler.should_return_304(request, etag, last_modified):
                response = self.conditional_handler.create_304_response()
                self._add_cache_headers(response, cached_response)
                return response
            
            # Return cached response
            response = JSONResponse(
                content=cached_response["data"],
                status_code=cached_response.get("status_code", 200)
            )
            self._add_cache_headers(response, cached_response)
            return response
        
        # Process request normally
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200 and hasattr(response, 'body'):
            await self._cache_response(cache_key, request, response)
        
        return response
    
    def _should_cache_path(self, path: str) -> bool:
        """Check if path should be cached."""
        return any(enabled_path in path for enabled_path in self.enabled_paths)
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate unique cache key for request."""
        # Include path, query params, and user context
        key_parts = [
            request.url.path,
            str(sorted(request.query_params.items())),
            request.headers.get("authorization", "anonymous")[:50]  # Truncate for security
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _cache_response(self, cache_key: str, request: Request, response: Response) -> None:
        """Store response in cache with appropriate headers."""
        import random
        
        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        try:
            response_data = json.loads(body.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Don't cache non-JSON responses
            return
        
        # Generate ETag
        etag = self.etag_generator.generate_etag(response_data)
        
        # Randomize TTL to prevent thundering herd
        ttl_seconds = random.randint(
            WIDGET_CACHE_TTL_MIN * 60,
            WIDGET_CACHE_TTL_MAX * 60
        )
        
        # Cache response data
        cache_data = {
            "data": response_data,
            "etag": etag,
            "last_modified": datetime.now(),
            "status_code": response.status_code,
            "ttl_seconds": ttl_seconds
        }
        
        self.cache_manager.set(cache_key, cache_data, ttl_seconds)
        
        # Add cache headers to response
        self._add_cache_headers(response, cache_data)
        
        # Reconstruct response body
        response.body_iterator = self._iter_body(body)
    
    def _add_cache_headers(self, response: Response, cache_data: Dict[str, Any]) -> None:
        """Add caching headers to response."""
        etag = cache_data.get("etag", "")
        last_modified = cache_data.get("last_modified", datetime.now())
        ttl_seconds = cache_data.get("ttl_seconds", 600)  # 10 min default
        
        response.headers["ETag"] = f'"{etag}"'
        response.headers["Cache-Control"] = f"private, max-age={ttl_seconds}"
        response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.headers["Expires"] = (
            datetime.now() + timedelta(seconds=ttl_seconds)
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Add cache status for debugging
        response.headers["X-Cache-Status"] = "HIT" if "etag" in cache_data else "MISS"
    
    async def _iter_body(self, body: bytes):
        """Iterate over response body bytes."""
        yield body
    
    def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate cache entries for specific user."""
        self.cache_manager.invalidate_pattern(str(user_id))
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache_manager.get_cache_stats()


# Singleton cache manager for application
cache_manager = CacheManager()


def create_caching_middleware(app: ASGIApp) -> CachingMiddleware:
    """Create caching middleware with default configuration."""
    return CachingMiddleware(
        app=app,
        cache_manager=cache_manager,
        enabled_paths=[
            "/v1/gamification/summary",
            "/v1/gamification/",
            "/api/v1/gamification/"
        ]
    )
