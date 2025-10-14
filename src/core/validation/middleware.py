"""Validation middleware for automatic request/response validation in FastAPI."""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Type
from uuid import uuid4

from fastapi import Request, Response, HTTPException, status
from fastapi.routing import APIRoute
from pydantic import BaseModel, ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.core.validation.base import APIRequestModel, APIResponseModel
from src.core.validation.errors import ValidationErrorFormatter
from src.services.validation_service import get_validation_service

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request/response validation and monitoring."""
    
    def __init__(self, 
                 app,
                 enable_request_validation: bool = True,
                 enable_response_validation: bool = False,
                 enable_logging: bool = True,
                 enable_metrics: bool = True,
                 validation_error_handler: Optional[Callable] = None):
        super().__init__(app)
        self.enable_request_validation = enable_request_validation
        self.enable_response_validation = enable_response_validation
        self.enable_logging = enable_logging
        self.enable_metrics = enable_metrics
        self.validation_error_handler = validation_error_handler
        self.validation_service = get_validation_service()
        
        logger.info("ValidationMiddleware initialized", extra={
            'request_validation': enable_request_validation,
            'response_validation': enable_response_validation,
            'logging': enable_logging,
            'metrics': enable_metrics
        })
    
    async def dispatch(self, request: Request, call_next):
        """Process request and response with validation."""
        request_id = str(uuid4())
        start_time = datetime.utcnow()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        try:
            # Validate request if enabled
            if self.enable_request_validation:
                await self._validate_request(request, request_id)
            
            # Process request
            response = await call_next(request)
            
            # Validate response if enabled
            if self.enable_response_validation:
                response = await self._validate_response(response, request_id)
            
            # Log successful request
            if self.enable_logging:
                self._log_request_success(request, response, request_id, start_time)
            
            return response
        
        except HTTPException as e:
            # Handle validation errors
            if self.enable_logging:
                self._log_validation_error(request, e, request_id, start_time)
            raise e
        
        except Exception as e:
            # Handle unexpected errors
            if self.enable_logging:
                self._log_unexpected_error(request, e, request_id, start_time)
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def _validate_request(self, request: Request, request_id: str) -> None:
        """Validate incoming request data."""
        if request.method not in ["POST", "PUT", "PATCH"]:
            return
        
        try:
            # Get request body
            if hasattr(request, '_body'):
                body = request._body
            else:
                body = await request.body()
                request._body = body
            
            if not body:
                return
            
            # Parse JSON body
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                return  # Skip validation for non-JSON requests
            
            # Skip validation if data is empty
            if not data:
                return
            
            # Determine validation model based on endpoint
            validation_model = self._get_validation_model_for_request(request)
            if not validation_model:
                return
            
            # Perform validation
            self.validation_service.validate_model(
                validation_model,
                data,
                user_friendly_errors=True
            )
            
            logger.debug(
                f"Request validation successful: {request.url.path}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'validation_model': validation_model.__name__
                }
            )
        
        except ValidationError as e:
            # Format validation error
            formatted_error = ValidationErrorFormatter.format_for_user(e)
            
            logger.warning(
                f"Request validation failed: {request.url.path}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'validation_errors': formatted_error.get('errors', [])
                }
            )
            
            # Use custom error handler if provided
            if self.validation_error_handler:
                self.validation_error_handler(e, request, request_id)
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Request validation failed",
                    "errors": formatted_error.get("errors", []),
                    "field_errors": formatted_error.get("field_errors", {}),
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def _validate_response(self, response: Response, request_id: str) -> Response:
        """Validate outgoing response data."""
        # Only validate JSON responses
        if not response.headers.get("content-type", "").startswith("application/json"):
            return response
        
        try:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            if not body:
                return response
            
            # Parse JSON response
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                return response
            
            # Validate against APIResponseModel if it matches the structure
            if isinstance(data, dict) and all(key in data for key in ['success', 'data', 'timestamp']):
                self.validation_service.validate_model(
                    APIResponseModel,
                    data,
                    user_friendly_errors=False
                )
            
            logger.debug(
                f"Response validation successful",
                extra={
                    'request_id': request_id,
                    'status_code': response.status_code
                }
            )
            
            # Recreate response with validated body
            response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except ValidationError as e:
            logger.error(
                f"Response validation failed",
                extra={
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'validation_error': str(e)
                }
            )
            
            # Don't fail the response, just log the error
            # In production, you might want to handle this differently
        
        return response
    
    def _get_validation_model_for_request(self, request: Request) -> Optional[Type[BaseModel]]:
        """Determine the appropriate validation model for a request."""
        path = request.url.path
        method = request.method
        
        # Simple path-based routing for validation models
        # In a real application, you might use more sophisticated routing
        validation_mapping = {
            ("/api/v1/users", "POST"): "UserCreateRequest",
            ("/api/v1/users", "PATCH"): "UserUpdateRequest",
            ("/api/v1/meal-plans", "POST"): "MealPlanCreateRequest",
            ("/api/v1/recipes", "POST"): "RecipeCreateRequest",
            ("/api/v1/subscriptions", "POST"): "SubscriptionCreateRequest",
        }
        
        # Handle parameterized paths
        for (pattern, req_method), model_name in validation_mapping.items():
            if method == req_method and self._path_matches(path, pattern):
                return self._get_model_class(model_name)
        
        return None
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern (simple implementation)."""
        # Handle exact matches
        if path == pattern:
            return True
        
        # Handle parameterized paths like /api/v1/users/{user_id}
        path_parts = path.split('/')
        pattern_parts = pattern.split('/')
        
        if len(path_parts) != len(pattern_parts):
            return False
        
        for path_part, pattern_part in zip(path_parts, pattern_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue  # Parameter match
            if path_part != pattern_part:
                return False
        
        return True
    
    def _get_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
        """Get model class by name."""
        try:
            if model_name == "UserCreateRequest":
                from src.models.validation.user_models import UserCreateRequest
                return UserCreateRequest
            elif model_name == "UserUpdateRequest":
                from src.models.validation.user_models import UserUpdateRequest
                return UserUpdateRequest
            elif model_name == "MealPlanCreateRequest":
                from src.models.validation.meal_planning_models import MealPlanCreateRequest
                return MealPlanCreateRequest
            elif model_name == "RecipeCreateRequest":
                from src.models.validation.meal_planning_models import RecipeCreateRequest
                return RecipeCreateRequest
            elif model_name == "SubscriptionCreateRequest":
                from src.models.validation.monetization_models import SubscriptionCreateRequest
                return SubscriptionCreateRequest
        except ImportError:
            logger.warning(f"Could not import model class: {model_name}")
        
        return None
    
    def _log_request_success(self, request: Request, response: Response, 
                           request_id: str, start_time: datetime) -> None:
        """Log successful request processing."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Request processed successfully: {request.method} {request.url.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'user_agent': request.headers.get('user-agent'),
                'client_ip': request.client.host if request.client else None
            }
        )
    
    def _log_validation_error(self, request: Request, error: HTTPException,
                            request_id: str, start_time: datetime) -> None:
        """Log validation errors."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.warning(
            f"Validation error: {request.method} {request.url.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': error.status_code,
                'duration_ms': duration_ms,
                'error_detail': error.detail
            }
        )
    
    def _log_unexpected_error(self, request: Request, error: Exception,
                            request_id: str, start_time: datetime) -> None:
        """Log unexpected errors."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.error(
            f"Unexpected error: {request.method} {request.url.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'duration_ms': duration_ms,
                'error_type': type(error).__name__,
                'error_message': str(error)
            },
            exc_info=True
        )


class RouteValidationWrapper:
    """Wrapper for FastAPI routes to add automatic validation."""
    
    def __init__(self, route_class: Type[APIRoute] = APIRoute):
        self.route_class = route_class
    
    def __call__(self, *args, **kwargs):
        """Create route with validation wrapper."""
        original_endpoint = kwargs.get('endpoint')
        if original_endpoint:
            kwargs['endpoint'] = self._wrap_endpoint(original_endpoint)
        
        return self.route_class(*args, **kwargs)
    
    def _wrap_endpoint(self, endpoint: Callable):
        """Wrap endpoint with validation logic."""
        async def wrapped_endpoint(*args, **kwargs):
            # Add request validation logic here if needed
            # This is called per-route, so you can add route-specific validation
            
            try:
                result = await endpoint(*args, **kwargs)
                return result
            except ValidationError as e:
                # Handle Pydantic validation errors
                formatted_error = ValidationErrorFormatter.format_for_user(e)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=formatted_error
                )
        
        return wrapped_endpoint


# Utility functions for FastAPI app setup
def setup_validation_middleware(app, 
                              enable_request_validation: bool = True,
                              enable_response_validation: bool = False,
                              enable_logging: bool = True,
                              enable_metrics: bool = True):
    """Setup validation middleware for FastAPI app."""
    middleware = ValidationMiddleware(
        app,
        enable_request_validation=enable_request_validation,
        enable_response_validation=enable_response_validation,
        enable_logging=enable_logging,
        enable_metrics=enable_metrics
    )
    
    app.add_middleware(ValidationMiddleware,
                      enable_request_validation=enable_request_validation,
                      enable_response_validation=enable_response_validation,
                      enable_logging=enable_logging,
                      enable_metrics=enable_metrics)
    
    return middleware


def create_validation_route():
    """Create APIRoute class with validation wrapper."""
    return RouteValidationWrapper()


# Custom exception handlers
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Global exception handler for Pydantic ValidationError."""
    formatted_error = ValidationErrorFormatter.format_for_user(exc)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation failed",
            "errors": formatted_error.get("errors", []),
            "field_errors": formatted_error.get("field_errors", {}),
            "request_id": getattr(request.state, 'request_id', str(uuid4())),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with request tracking."""
    content = {
        "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
        "status_code": exc.status_code,
        "request_id": getattr(request.state, 'request_id', str(uuid4())),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Include additional details if exc.detail is a dict
    if isinstance(exc.detail, dict):
        content.update(exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


# Export key components
__all__ = [
    'ValidationMiddleware',
    'RouteValidationWrapper',
    'setup_validation_middleware',
    'create_validation_route',
    'validation_exception_handler',
    'http_exception_handler'
]
