"""HTTP application factory."""

from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.plan import router as plan_router
from src.api.routes.community import router as community_router
from src.api.routes.gamification import router as gamification_router
from src.api.routes.monetization import monetization_router
from src.api.routes.security import security_router
from src.api.middleware.rate_limiting import rate_limit_middleware
from src.api.middleware.caching import CachingMiddleware
from src.security.middleware import SecurityMiddleware
from src.security.headers import SecurityMiddlewareManager
from src.services.infrastructure.secrets_manager import SecretsManager


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")
    
    app = FastAPI(
        title="AI Nutritionalist API",
        version="1.0.0",
        description="Public API for meal planning, feedback, and community features with comprehensive security",
        docs_url="/docs" if environment != "production" else None,
        redoc_url="/redoc" if environment != "production" else None,
    )
    
    # Initialize secrets manager
    secrets_manager = SecretsManager()
    
    # Initialize security middleware manager
    security_middleware_manager = SecurityMiddlewareManager(environment)
    
    # Configure security for API
    security_middleware_manager.configure_for_api()
    
    # Add CORS middleware (configured based on environment)
    cors_middleware = security_middleware_manager.get_cors_middleware()
    app.add_middleware(cors_middleware.__class__, **cors_middleware.__dict__)
    
    # Add comprehensive security middleware
    app.add_middleware(SecurityMiddleware, secrets_manager=secrets_manager, environment=environment)
    
    # Add rate limiting middleware
    app.middleware("http")(rate_limit_middleware)
    
    # Add caching middleware for widget endpoints
    app.add_middleware(
        CachingMiddleware,
        enabled_paths=["/v1/gamification/summary"]
    )
    
    # Include routers
    app.include_router(security_router)  # Security routes first
    app.include_router(plan_router)
    app.include_router(community_router)
    app.include_router(gamification_router)
    app.include_router(monetization_router)  # CRITICAL: Mount revenue routes
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": environment,
            "security": "enabled",
            "timestamp": "2025-10-12T00:00:00Z"
        }
    
    # Security information endpoint (development/staging only)
    if environment in ["development", "staging"]:
        @app.get("/security-info")
        async def security_info():
            """Get security configuration information."""
            return security_middleware_manager.get_security_info()
    
    return app


app = create_app()

__all__ = ["create_app", "app"]
