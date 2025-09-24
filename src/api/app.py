"""HTTP application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.plan import router as plan_router
from .routes.community import router as community_router
from .routes.gamification import router as gamification_router
from .middleware.rate_limiting import rate_limit_middleware
from .middleware.caching import CachingMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="AI Nutritionalist API",
        version="1.0.0",
        description="Public API for meal planning, feedback, and community features",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add rate limiting middleware
    app.middleware("http")(rate_limit_middleware)
    
    # Add caching middleware for widget endpoints
    app.add_middleware(
        CachingMiddleware,
        enabled_paths=["/v1/gamification/summary"]
    )
    
    # Include routers
    app.include_router(plan_router)
    app.include_router(community_router)
    app.include_router(gamification_router)
    
    return app


app = create_app()

__all__ = ["create_app", "app"]
