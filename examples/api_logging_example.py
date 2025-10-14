"""
Example implementation of structured logging for API endpoints.

Demonstrates:
- Request/response logging
- Performance monitoring
- Error handling
- Business event tracking
- Security logging
"""

import time
import asyncio
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
import uuid

from packages.shared.monitoring import (
    get_logger, get_metrics, get_tracer, get_business_metrics,
    LogLevel, EventType, performance_monitor, audit_log
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request/response logging."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.logger = get_logger()
        self.metrics = get_metrics()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
    
    async def dispatch(self, request: Request, call_next):
        """Process request and response with logging."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Set request context
        self.logger.context.correlation_id = correlation_id
        self.logger.context.request_id = request_id
        self.logger.context.user_id = self._extract_user_id(request)
        self.logger.context.operation = f"{request.method} {request.url.path}"
        
        # Start tracing span
        with self.tracer.trace(
            f"http_request_{request.method.lower()}",
            tags={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.path": request.url.path,
                "user.id": self.logger.context.user_id or "anonymous"
            }
        ) as span:
            
            # Log incoming request
            self.logger.info(
                f"Incoming request: {request.method} {request.url.path}",
                extra={
                    "request": {
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                        "query_params": dict(request.query_params),
                        "headers": self._safe_headers(dict(request.headers)),
                        "user_agent": request.headers.get("user-agent"),
                        "remote_addr": request.client.host if request.client else None
                    }
                }
            )
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Add response tags to span
                span.add_tag("http.status_code", str(response.status_code))
                span.add_tag("http.response_size", str(len(response.body) if hasattr(response, 'body') else 0))
                
                # Log response
                log_level = LogLevel.WARN if response.status_code >= 400 else LogLevel.INFO
                self.logger._log(
                    level=log_level,
                    message=f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        "response": {
                            "status_code": response.status_code,
                            "headers": self._safe_headers(dict(response.headers)),
                            "duration_ms": duration_ms
                        }
                    }
                )
                
                # Record metrics
                if self.business_metrics:
                    self.business_metrics.track_api_request(
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=response.status_code,
                        duration_ms=duration_ms
                    )
                
                # Business event for successful requests
                if response.status_code < 400:
                    self.logger.business_event(
                        event_type=EventType.USER_ACTION,
                        entity_type="api_request",
                        action=f"{request.method.lower()}_{request.url.path.replace('/', '_').strip('_')}",
                        metadata={
                            "status_code": response.status_code,
                            "duration_ms": duration_ms,
                            "user_id": self.logger.context.user_id
                        }
                    )
                
                return response
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                self.logger.error(
                    f"Request failed: {request.method} {request.url.path}",
                    error=e,
                    extra={
                        "request": {
                            "method": request.method,
                            "path": request.url.path,
                            "duration_ms": duration_ms
                        }
                    }
                )
                
                # Record error metrics
                if self.business_metrics:
                    self.business_metrics.track_api_request(
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=500,
                        duration_ms=duration_ms
                    )
                
                # Security event for authentication errors
                if isinstance(e, HTTPException) and e.status_code == 401:
                    self.logger.business_event(
                        event_type=EventType.SECURITY_EVENT,
                        entity_type="authentication",
                        action="failed_login",
                        metadata={
                            "ip_address": request.client.host if request.client else None,
                            "user_agent": request.headers.get("user-agent"),
                            "path": request.url.path
                        },
                        level=LogLevel.WARN
                    )
                
                raise
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request (JWT token, session, etc.)."""
        # This would implement actual user ID extraction logic
        # For example, from JWT token in Authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Extract user ID from JWT token
            # This is a placeholder implementation
            return "user_123"  # Replace with actual extraction logic
        return None
    
    def _safe_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers from logging."""
        sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token"
        }
        return {
            k: v if k.lower() not in sensitive_headers else "[REDACTED]"
            for k, v in headers.items()
        }


# Example API endpoint implementations
app = FastAPI(title="AI Nutritionist API")

# Add logging middleware
app.add_middleware(LoggingMiddleware)

logger = get_logger()
business_metrics = get_business_metrics()


@app.get("/health")
@performance_monitor("health_check")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check requested")
    return {"status": "healthy", "service": "ai-nutritionist"}


@app.post("/api/v1/nutrition/analyze")
@performance_monitor("nutrition_analysis")
@audit_log(EventType.USER_ACTION, "nutrition", "analyze")
async def analyze_nutrition(request: Dict[str, Any]):
    """Analyze nutrition data."""
    logger.info("Starting nutrition analysis", extra={"request_data": request})
    
    try:
        # Simulate business logic
        food_items = request.get("food_items", [])
        
        # Log business event
        logger.business_event(
            event_type=EventType.BUSINESS_EVENT,
            entity_type="nutrition_analysis",
            action="started",
            metadata={
                "food_items_count": len(food_items),
                "user_id": logger.context.user_id
            }
        )
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(0.1)
        
        # Mock response
        response = {
            "analysis_id": str(uuid.uuid4()),
            "total_calories": 350,
            "nutrients": {
                "protein": 25,
                "carbs": 45,
                "fat": 15
            },
            "recommendations": [
                "Consider adding more vegetables",
                "Good protein balance"
            ]
        }
        
        # Log successful completion
        logger.business_event(
            event_type=EventType.BUSINESS_EVENT,
            entity_type="nutrition_analysis",
            action="completed",
            metadata={
                "analysis_id": response["analysis_id"],
                "total_calories": response["total_calories"],
                "user_id": logger.context.user_id
            }
        )
        
        # Track business KPI
        if business_metrics:
            business_metrics.track_business_kpi(
                "nutrition_analyses_daily",
                1.0,
                tags={"user_id": logger.context.user_id or "anonymous"}
            )
        
        return response
        
    except Exception as e:
        logger.error("Nutrition analysis failed", error=e)
        
        # Log business event for failure
        logger.business_event(
            event_type=EventType.ERROR_EVENT,
            entity_type="nutrition_analysis",
            action="failed",
            metadata={
                "error": str(e),
                "user_id": logger.context.user_id
            },
            level=LogLevel.ERROR
        )
        
        raise HTTPException(status_code=500, detail="Analysis failed")


@app.post("/api/v1/user/preferences")
@performance_monitor("update_preferences")
@audit_log(EventType.USER_ACTION, "user", "update_preferences")
async def update_user_preferences(preferences: Dict[str, Any]):
    """Update user preferences."""
    user_id = logger.context.user_id
    
    if not user_id:
        logger.business_event(
            event_type=EventType.SECURITY_EVENT,
            entity_type="authorization",
            action="unauthorized_access",
            metadata={"endpoint": "/api/v1/user/preferences"},
            level=LogLevel.WARN
        )
        raise HTTPException(status_code=401, detail="Authentication required")
    
    logger.info(
        "Updating user preferences",
        extra={
            "user_id": user_id,
            "preferences": preferences
        }
    )
    
    # Log GDPR-compliant audit event
    logger.business_event(
        event_type=EventType.AUDIT_EVENT,
        entity_type="user_data",
        entity_id=user_id,
        action="preferences_updated",
        metadata={
            "changed_fields": list(preferences.keys()),
            "timestamp": time.time()
        }
    )
    
    return {"status": "success", "message": "Preferences updated"}


@app.get("/api/v1/analytics/dashboard")
@performance_monitor("analytics_dashboard")
async def get_analytics_dashboard():
    """Get analytics dashboard data."""
    logger.info("Loading analytics dashboard")
    
    # Example of logging performance metrics
    with logger.operation_context("fetch_dashboard_data") as ctx:
        # Simulate database queries
        await asyncio.sleep(0.05)
        
        ctx.info("User data fetched")
        
        # Simulate aggregation processing
        await asyncio.sleep(0.03)
        
        ctx.info("Analytics aggregated")
    
    # Mock dashboard data
    dashboard_data = {
        "total_users": 1250,
        "daily_analyses": 3456,
        "avg_calories_per_user": 2100,
        "top_foods": ["chicken", "rice", "broccoli"]
    }
    
    # Log business metrics
    for metric, value in dashboard_data.items():
        if isinstance(value, (int, float)):
            if business_metrics:
                business_metrics.track_business_kpi(metric, value)
    
    return dashboard_data


# Error handlers with logging
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with logging."""
    logger.error(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return {"error": exc.detail, "status_code": exc.status_code}


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with logging."""
    logger.fatal(
        f"Unhandled exception: {str(exc)}",
        error=exc,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Log critical system event
    logger.business_event(
        event_type=EventType.SYSTEM_EVENT,
        entity_type="application",
        action="unhandled_exception",
        metadata={
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        level=LogLevel.FATAL
    )
    
    return {"error": "Internal server error", "status_code": 500}


if __name__ == "__main__":
    import uvicorn
    
    # Setup monitoring
    from packages.shared.monitoring.setup import setup_service_monitoring
    monitoring = setup_service_monitoring("ai-nutritionist-api")
    
    # Add health checks for external dependencies
    monitoring.add_external_api_health_check(
        "openai_api",
        "https://api.openai.com/v1/models",
        timeout=5.0
    )
    
    # Start the API
    uvicorn.run(app, host="0.0.0.0", port=8000)
