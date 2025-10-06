"""Rate limiting middleware for community endpoints with distributed backend."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

# Import the distributed rate limiting with error handling
try:
    from src.services.infrastructure.distributed_rate_limiting import check_rate_limit, track_service_cost
    DISTRIBUTED_RATE_LIMITING_AVAILABLE = True
except ImportError:
    DISTRIBUTED_RATE_LIMITING_AVAILABLE = False
    
    # Fallback functions
    async def check_rate_limit(identifier: str, action: str) -> tuple:
        return True, {'remaining': 100, 'reset_time': 0}
    
    async def track_service_cost(service: str, cost: float, user_id: str = None) -> dict:
        return {'service': service, 'cost': cost}


class RateLimiter:
    """Advanced rate limiter with multiple strategies."""
    
    def __init__(self):
        # Track SMS sends per user (1 per minute limit)
        self._sms_windows: Dict[str, deque] = defaultdict(deque)
        
        # Track API calls per user (configurable limits)
        self._api_windows: Dict[str, deque] = defaultdict(deque)
        
        # Track reflection submissions (prevent spam)
        self._reflection_windows: Dict[str, deque] = defaultdict(deque)
        
        # Content moderation cache
        self._moderation_cache: Dict[str, Tuple[bool, float]] = {}
        
        # Rate limit configurations
        self.SMS_LIMIT = 1  # 1 SMS per minute
        self.SMS_WINDOW = 60  # 60 seconds
        
        self.API_LIMIT = 100  # 100 API calls per hour
        self.API_WINDOW = 3600  # 1 hour
        
        self.REFLECTION_LIMIT = 5  # 5 reflections per hour
        self.REFLECTION_WINDOW = 3600  # 1 hour
        
        # Clean up old entries periodically
        self._last_cleanup = time.time()
        self.CLEANUP_INTERVAL = 300  # 5 minutes
    
    def _cleanup_old_entries(self) -> None:
        """Remove old entries from tracking windows."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        
        # Clean SMS windows
        for user_id, window in list(self._sms_windows.items()):
            cutoff = current_time - self.SMS_WINDOW
            while window and window[0] < cutoff:
                window.popleft()
            if not window:
                del self._sms_windows[user_id]
        
        # Clean API windows
        for user_id, window in list(self._api_windows.items()):
            cutoff = current_time - self.API_WINDOW
            while window and window[0] < cutoff:
                window.popleft()
            if not window:
                del self._api_windows[user_id]
        
        # Clean reflection windows
        for user_id, window in list(self._reflection_windows.items()):
            cutoff = current_time - self.REFLECTION_WINDOW
            while window and window[0] < cutoff:
                window.popleft()
            if not window:
                del self._reflection_windows[user_id]
        
        # Clean moderation cache (keep for 1 hour)
        cache_cutoff = current_time - 3600
        for content_hash, (result, timestamp) in list(self._moderation_cache.items()):
            if timestamp < cache_cutoff:
                del self._moderation_cache[content_hash]
        
        self._last_cleanup = current_time
    
    async def check_sms_rate_limit(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Check if user can send SMS using distributed rate limiting."""
        try:
            allowed, rate_info = await check_rate_limit(user_id, 'sms_messages')
            
            if not allowed:
                retry_after = max(1, rate_info.get('reset_time', 0) - int(time.time()))
                return False, retry_after
            
            return True, None
            
        except Exception as e:
            # Fallback to local rate limiting if distributed fails
            return self._check_sms_rate_limit_local(user_id)
    
    def _check_sms_rate_limit_local(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Fallback local SMS rate limiting."""
        self._cleanup_old_entries()
        
        current_time = time.time()
        window = self._sms_windows[user_id]
        
        # Remove expired entries
        cutoff = current_time - self.SMS_WINDOW
        while window and window[0] < cutoff:
            window.popleft()
        
        # Check limit
        if len(window) >= self.SMS_LIMIT:
            # Calculate retry after
            oldest_request = window[0]
            retry_after = int(oldest_request + self.SMS_WINDOW - current_time)
            return False, max(1, retry_after)
        
        # Record this request
        window.append(current_time)
        return True, None
    
    async def check_api_rate_limit(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Check if user can make API call using distributed rate limiting."""
        try:
            allowed, rate_info = await check_rate_limit(user_id, 'api_requests')
            
            if not allowed:
                retry_after = max(1, rate_info.get('reset_time', 0) - int(time.time()))
                return False, retry_after
            
            return True, None
            
        except Exception as e:
            # Fallback to local rate limiting if distributed fails
            return self._check_api_rate_limit_local(user_id)
    
    def _check_api_rate_limit_local(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Fallback local API rate limiting."""
        self._cleanup_old_entries()
        
        current_time = time.time()
        window = self._api_windows[user_id]
        
        # Remove expired entries
        cutoff = current_time - self.API_WINDOW
        while window and window[0] < cutoff:
            window.popleft()
        
        # Check limit
        if len(window) >= self.API_LIMIT:
            # Calculate retry after
            oldest_request = window[0]
            retry_after = int(oldest_request + self.API_WINDOW - current_time)
            return False, max(1, retry_after)
        
        # Record this request
        window.append(current_time)
        return True, None
    
    def check_reflection_rate_limit(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """Check if user can submit reflection. Returns (allowed, retry_after_seconds)."""
        self._cleanup_old_entries()
        
        current_time = time.time()
        window = self._reflection_windows[user_id]
        
        # Remove expired entries
        cutoff = current_time - self.REFLECTION_WINDOW
        while window and window[0] < cutoff:
            window.popleft()
        
        # Check limit
        if len(window) >= self.REFLECTION_LIMIT:
            # Calculate retry after
            oldest_request = window[0]
            retry_after = int(oldest_request + self.REFLECTION_WINDOW - current_time)
            return False, max(1, retry_after)
        
        # Record this request
        window.append(current_time)
        return True, None
    
    def moderate_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """Basic content moderation. Returns (is_appropriate, reason)."""
        # Create hash for caching
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check cache
        current_time = time.time()
        if content_hash in self._moderation_cache:
            result, timestamp = self._moderation_cache[content_hash]
            if current_time - timestamp < 3600:  # 1 hour cache
                return result, None if result else "Content flagged by moderation"
        
        # Simple content checks (expand as needed)
        content_lower = content.lower()
        
        # Check for spam patterns
        if len(content) < 3:
            self._moderation_cache[content_hash] = (False, current_time)
            return False, "Content too short"
        
        if len(content) > 1000:
            self._moderation_cache[content_hash] = (False, current_time)
            return False, "Content too long"
        
        # Check for basic inappropriate content
        inappropriate_words = [
            "spam", "scam", "buy now", "click here", "free money",
            # Add more as needed
        ]
        
        for word in inappropriate_words:
            if word in content_lower:
                self._moderation_cache[content_hash] = (False, current_time)
                return False, f"Inappropriate content detected"
        
        # Check for excessive repetition
        words = content_lower.split()
        if len(words) > 5:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any word appears more than 30% of the time, flag as spam
            max_count = max(word_counts.values())
            if max_count / len(words) > 0.3:
                self._moderation_cache[content_hash] = (False, current_time)
                return False, "Repetitive content detected"
        
        # Content is appropriate
        self._moderation_cache[content_hash] = (True, current_time)
        return True, None


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting."""
    
    # Extract user ID from request
    user_id = None
    
    # Try to get user_id from various sources
    if request.method == "POST":
        # For POST requests, try to get from body
        try:
            body = await request.body()
            if body:
                import json
                data = json.loads(body)
                user_id = data.get("user_id")
                
                # Re-create request with body for downstream processing
                from fastapi import Request
                
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
        except (json.JSONDecodeError, Exception):
            pass
    
    # Try from query parameters
    if not user_id:
        user_id = request.query_params.get("user_id")
    
    # Try from path parameters
    if not user_id and hasattr(request, "path_params"):
        user_id = request.path_params.get("user_id")
    
    # Try from headers
    if not user_id:
        user_id = request.headers.get("X-User-ID")
    
    # If we have a user_id, apply rate limits
    if user_id:
        path = request.url.path
        
        # Apply API rate limit to all community endpoints
        if "/v1/crews" in path:
            allowed, retry_after = rate_limiter.check_api_rate_limit(user_id)
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "API rate limit exceeded",
                        "retry_after": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
                )
        
        # Apply reflection-specific rate limit
        if path == "/v1/crews/reflections" and request.method == "POST":
            allowed, retry_after = rate_limiter.check_reflection_rate_limit(user_id)
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Reflection submission rate limit exceeded",
                        "retry_after": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
                )
    
    # Process request
    response = await call_next(request)
    return response


def get_rate_limiter() -> RateLimiter:
    """Dependency injection for rate limiter."""
    return rate_limiter


__all__ = ["RateLimiter", "rate_limiter", "rate_limit_middleware", "get_rate_limiter"]
