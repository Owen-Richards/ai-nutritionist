"""HTTP application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.plan import router as plan_router
from src.api.routes.community import router as community_router
from src.api.routes.gamification import router as gamification_router
from src.api.routes.monetization import monetization_router
from src.api.middleware.rate_limiting import rate_limit_middleware
from src.api.middleware.caching import CachingMiddleware


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
    app.include_router(monetization_router)  # CRITICAL: Mount revenue routes
    
    return app


app = create_app()

__all__ = ["create_app", "app"]
