"""HTTP application factory."""

from __future__ import annotations

from fastapi import FastAPI

from .routes.plan import router as plan_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="AI Nutritionalist API",
        version="1.0.0",
        description="Public API for meal planning and feedback",
    )
    app.include_router(plan_router)
    return app


app = create_app()

__all__ = ["create_app", "app"]
