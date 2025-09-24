"""Minimal FastAPI app to test Track C gamification endpoints."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.gamification import router as gamification_router
from .middleware.caching import CachingMiddleware


def create_minimal_app() -> FastAPI:
    """Create minimal FastAPI app with just gamification routes."""
    
    app = FastAPI(
        title="AI Nutritionalist API - Track C Testing",
        version="1.0.0",
        description="Minimal API for testing Track C gamification widgets",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add caching middleware
    app.add_middleware(CachingMiddleware)

    # Include gamification routes
    app.include_router(gamification_router, prefix="/v1")

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "ai-nutritionalist-track-c"}

    return app


# Create the app instance
app = create_minimal_app()
