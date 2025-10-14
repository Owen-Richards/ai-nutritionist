"""Middleware and decorators for feature flag integration."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime

try:
    from fastapi import HTTPException, Request, Response
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    HTTPException = None
    Request = None
    Response = None
    JSONResponse = None

try:
    from flask import Flask, g, request, jsonify, abort
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None
    g = None
    request = None
    jsonify = None
    abort = None

from .models import FlagContext
from .client import FeatureFlagClient


logger = logging.getLogger(__name__)


class FeatureFlagMiddleware:
    """Base middleware for feature flag integration."""
    
    def __init__(
        self,
        flag_client: FeatureFlagClient,
        context_extractor: Optional[Callable] = None,
        error_handler: Optional[Callable] = None,
    ):
        self.flag_client = flag_client
        self.context_extractor = context_extractor or self._default_context_extractor
        self.error_handler = error_handler or self._default_error_handler
    
    def _default_context_extractor(self, request_data: Any) -> FlagContext:
        """Default context extraction logic."""
        return FlagContext()
    
    def _default_error_handler(self, error: Exception, flag_key: str) -> Any:
        """Default error handling logic."""
        logger.error(f"Feature flag error for {flag_key}: {error}")
        return False  # Safe default


class FastAPIFeatureFlagMiddleware(FeatureFlagMiddleware):
    """FastAPI middleware for feature flags."""
    
    def __init__(self, *args, **kwargs):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI not available")
        super().__init__(*args, **kwargs)
    
    async def __call__(self, request, call_next):
        """Middleware call method."""
        # Extract context from request
        context = await self._extract_context_from_request(request)
        
        # Store context in request state for use in endpoints
        request.state.flag_context = context
        request.state.flag_client = self.flag_client
        
        # Process request
        response = await call_next(request)
        
        return response
    
    async def _extract_context_from_request(self, request) -> FlagContext:
        """Extract flag context from FastAPI request."""
        try:
            # Get user information from request
            user_id = None
            subscription_tier = None
            custom_attributes = {}
            
            # Try to get user from JWT or session
            if hasattr(request.state, 'user'):
                user = request.state.user
                user_id = getattr(user, 'id', None)
                subscription_tier = getattr(user, 'subscription_tier', None)
            
            # Get additional context from headers
            country = request.headers.get('cf-ipcountry')  # Cloudflare country header
            user_agent = request.headers.get('user-agent')
            
            # Get custom attributes from query params or headers
            if hasattr(request, 'query_params'):
                for key, value in request.query_params.items():
                    if key.startswith('ff_'):
                        custom_attributes[key[3:]] = value
            
            return FlagContext(
                user_id=str(user_id) if user_id else None,
                subscription_tier=subscription_tier,
                country=country,
                user_agent=user_agent,
                ip_address=request.client.host if request.client else None,
                custom_attributes=custom_attributes,
            )
            
        except Exception as e:
            logger.error(f"Error extracting context from request: {e}")
            return FlagContext()


class FlaskFeatureFlagMiddleware(FeatureFlagMiddleware):
    """Flask middleware for feature flags."""
    
    def __init__(self, app=None, *args, **kwargs):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask not available")
        
        super().__init__(*args, **kwargs)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.before_request(self._before_request)
        app.teardown_appcontext(self._teardown)
    
    def _before_request(self):
        """Before request handler."""
        try:
            context = self._extract_context_from_request()
            g.flag_context = context
            g.flag_client = self.flag_client
        except Exception as e:
            logger.error(f"Error in Flask feature flag middleware: {e}")
            g.flag_context = FlagContext()
            g.flag_client = self.flag_client
    
    def _teardown(self, exception):
        """Teardown handler."""
        pass
    
    def _extract_context_from_request(self) -> FlagContext:
        """Extract flag context from Flask request."""
        try:
            # Get user information
            user_id = None
            subscription_tier = None
            
            # Try to get user from session or JWT
            if hasattr(g, 'current_user'):
                user = g.current_user
                user_id = getattr(user, 'id', None)
                subscription_tier = getattr(user, 'subscription_tier', None)
            
            # Get additional context
            country = request.headers.get('CF-IPCountry')
            user_agent = request.headers.get('User-Agent')
            
            # Get custom attributes from query params
            custom_attributes = {}
            for key, value in request.args.items():
                if key.startswith('ff_'):
                    custom_attributes[key[3:]] = value
            
            return FlagContext(
                user_id=str(user_id) if user_id else None,
                subscription_tier=subscription_tier,
                country=country,
                user_agent=user_agent,
                ip_address=request.environ.get('REMOTE_ADDR'),
                custom_attributes=custom_attributes,
            )
            
        except Exception as e:
            logger.error(f"Error extracting context from Flask request: {e}")
            return FlagContext()


# Decorators

def flag_required(
    flag_key: str,
    default_value: Any = False,
    context_key: str = "flag_context",
    client_key: str = "flag_client",
    error_response: Optional[Any] = None,
):
    """Decorator to require a feature flag to be enabled."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # Get context and client from request state or kwargs
                context = None
                client = None
                
                # Try to get from FastAPI request state
                if args and hasattr(args[0], 'state'):
                    request_obj = args[0]
                    context = getattr(request_obj.state, context_key, None)
                    client = getattr(request_obj.state, client_key, None)
                
                # Try to get from Flask g object
                elif FLASK_AVAILABLE and g:
                    context = getattr(g, context_key, None)
                    client = getattr(g, client_key, None)
                
                # Try to get from kwargs
                if not context:
                    context = kwargs.get(context_key)
                if not client:
                    client = kwargs.get(client_key)
                
                if not client or not context:
                    logger.warning(f"Feature flag client or context not available for {flag_key}")
                    if error_response:
                        return error_response
                    return default_value
                
                # Evaluate flag
                is_enabled = await client.is_enabled(flag_key, context, default_value)
                
                if not is_enabled:
                    if error_response:
                        return error_response
                    
                    # Return appropriate error response for framework
                    if FASTAPI_AVAILABLE and HTTPException:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Feature '{flag_key}' is not enabled"
                        )
                    elif FLASK_AVAILABLE and abort:
                        abort(403, f"Feature '{flag_key}' is not enabled")
                    else:
                        raise PermissionError(f"Feature '{flag_key}' is not enabled")
                
                # Track flag usage
                await client.track_event(
                    f"flag_access_{flag_key}",
                    context,
                    {"flag_key": flag_key, "enabled": True}
                )
                
                return await func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in flag_required decorator: {e}")
                if error_response:
                    return error_response
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, we can't use async flag evaluation
            # This is a simplified version that might not work with all backends
            logger.warning(f"Synchronous flag evaluation for {flag_key} - limited functionality")
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def feature_gate(
    flag_key: str,
    variants: Dict[str, Callable],
    default_variant: str = "control",
    context_key: str = "flag_context",
    client_key: str = "flag_client",
):
    """Decorator to gate different code paths based on feature flag variants."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # Get context and client (similar to flag_required)
                context = None
                client = None
                
                if args and hasattr(args[0], 'state'):
                    request_obj = args[0]
                    context = getattr(request_obj.state, context_key, None)
                    client = getattr(request_obj.state, client_key, None)
                elif FLASK_AVAILABLE and g:
                    context = getattr(g, context_key, None)
                    client = getattr(g, client_key, None)
                
                if not client or not context:
                    variant = default_variant
                else:
                    variant = await client.get_variant(flag_key, context, default_variant)
                
                # Get the appropriate function for the variant
                variant_func = variants.get(variant, variants.get(default_variant))
                
                if not variant_func:
                    logger.error(f"No function found for variant '{variant}' or default '{default_variant}'")
                    return await func(*args, **kwargs)
                
                # Track variant usage
                if client and context:
                    await client.track_event(
                        f"variant_access_{flag_key}",
                        context,
                        {"flag_key": flag_key, "variant": variant}
                    )
                
                return await variant_func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in feature_gate decorator: {e}")
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Simplified synchronous version
            variant_func = variants.get(default_variant, func)
            return variant_func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Utility functions for framework integration

async def get_flag_context(request_obj: Any = None) -> FlagContext:
    """Get flag context from request object."""
    if request_obj and hasattr(request_obj, 'state'):
        # FastAPI
        return getattr(request_obj.state, 'flag_context', FlagContext())
    elif FLASK_AVAILABLE and g:
        # Flask
        return getattr(g, 'flag_context', FlagContext())
    else:
        return FlagContext()


async def get_flag_client(request_obj: Any = None) -> Optional[FeatureFlagClient]:
    """Get flag client from request object."""
    if request_obj and hasattr(request_obj, 'state'):
        # FastAPI
        return getattr(request_obj.state, 'flag_client', None)
    elif FLASK_AVAILABLE and g:
        # Flask
        return getattr(g, 'flag_client', None)
    else:
        return None


class FeatureFlagDependency:
    """FastAPI dependency for feature flag operations."""
    
    def __init__(self, flag_client: FeatureFlagClient):
        self.flag_client = flag_client
    
    async def __call__(self, request) -> Dict[str, Any]:
        """Return flag client and context for dependency injection."""
        context = await get_flag_context(request)
        return {
            "flag_client": self.flag_client,
            "flag_context": context,
        }


# Context managers

class FeatureFlagContext:
    """Context manager for feature flag operations."""
    
    def __init__(
        self,
        flag_client: FeatureFlagClient,
        context: FlagContext,
        track_usage: bool = True,
    ):
        self.flag_client = flag_client
        self.context = context
        self.track_usage = track_usage
        self._start_time = None
        self._flags_evaluated = []
    
    async def __aenter__(self):
        """Enter async context."""
        self._start_time = datetime.utcnow()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.track_usage and self._flags_evaluated:
            # Track session metrics
            session_duration = (datetime.utcnow() - self._start_time).total_seconds()
            
            await self.flag_client.track_event(
                "flag_session_end",
                self.context,
                {
                    "flags_evaluated": self._flags_evaluated,
                    "session_duration_seconds": session_duration,
                }
            )
    
    async def is_enabled(self, flag_key: str, default: bool = False) -> bool:
        """Check if flag is enabled in this context."""
        self._flags_evaluated.append(flag_key)
        return await self.flag_client.is_enabled(flag_key, self.context, default)
    
    async def get_variant(self, flag_key: str, default: str = "control") -> str:
        """Get flag variant in this context."""
        self._flags_evaluated.append(flag_key)
        return await self.flag_client.get_variant(flag_key, self.context, default)


# Import protection
import asyncio
