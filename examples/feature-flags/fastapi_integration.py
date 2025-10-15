"""Example: FastAPI integration with feature flags."""

import asyncio
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, Depends, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    print("FastAPI not available. Install with: pip install fastapi uvicorn")
    FASTAPI_AVAILABLE = False
    FastAPI = None
    Depends = None
    HTTPException = None
    Request = None
    JSONResponse = None
    BaseModel = None

if FASTAPI_AVAILABLE:
    from packages.shared.feature_flags import (
        FeatureFlagService,
        FeatureFlagClient,
        FastAPIFeatureFlagMiddleware,
        FeatureFlagDependency,
        flag_required,
        feature_gate,
        FlagContext,
        FeatureFlagDefinition,
        FlagVariant,
        FlagStatus,
        CacheConfig,
    )


# Global feature flag client
flag_client: Optional[FeatureFlagClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global flag_client
    
    # Initialize feature flags on startup
    print("🚀 Initializing feature flag service...")
    
    cache_config = CacheConfig(
        ttl_seconds=300,
        enable_local_cache=True,
    )
    
    service = FeatureFlagService(cache_config=cache_config)
    flag_client = FeatureFlagClient(service)
    
    # Register demo flags
    demo_flags = [
        FeatureFlagDefinition(
            key="api_v2",
            name="API V2",
            description="Enable new API endpoints",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="v1", value="v1", percentage=70),
                FlagVariant(key="v2", value="v2", percentage=30),
            ],
            default_variant="v1",
            fallback_variant="v1",
            created_by="api-team",
            tags=["api", "version"],
        ),
        FeatureFlagDefinition(
            key="enhanced_meal_plans",
            name="Enhanced Meal Plans",
            description="Enable enhanced meal planning features",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="off", value=False),
                FlagVariant(key="on", value=True),
            ],
            default_variant="off",
            fallback_variant="off",
            created_by="product-team",
            tags=["meal-planning", "premium"],
        ),
        FeatureFlagDefinition(
            key="ui_theme",
            name="UI Theme",
            description="UI theme selection",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="classic", value="classic", percentage=40),
                FlagVariant(key="modern", value="modern", percentage=60),
            ],
            default_variant="classic",
            fallback_variant="classic",
            created_by="design-team",
            tags=["ui", "theme"],
        ),
    ]
    
    for flag in demo_flags:
        await service.register_flag(flag)
    
    print("✅ Feature flags initialized")
    
    yield  # Application runs here
    
    print("🔄 Shutting down feature flag service...")


if FASTAPI_AVAILABLE:
    # Create FastAPI app
    app = FastAPI(
        title="AI Nutritionist API with Feature Flags",
        description="Demo API showing feature flag integration",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Add feature flag middleware
    async def extract_user_context(request: Request) -> FlagContext:
        """Extract user context from request."""
        # In a real app, you'd extract from JWT, session, etc.
        user_id = request.headers.get("X-User-ID", "anonymous")
        subscription_tier = request.headers.get("X-Subscription-Tier", "free")
        country = request.headers.get("X-Country", "US")
        
        return FlagContext(
            user_id=user_id,
            subscription_tier=subscription_tier,
            country=country,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    
    # Add middleware
    middleware = FastAPIFeatureFlagMiddleware(
        flag_client=flag_client,
        context_extractor=extract_user_context,
    )
    app.middleware("http")(middleware)
    
    # Dependency for injecting feature flags
    flag_dependency = FeatureFlagDependency(flag_client)
    
    
    # Pydantic models
    class MealPlan(BaseModel):
        id: str
        name: str
        meals: list[str]
        enhanced: bool = False
    
    
    class UserProfile(BaseModel):
        user_id: str
        subscription_tier: str
        preferences: Dict[str, Any]
    
    
    # Routes
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "AI Nutritionist API with Feature Flags", "version": "1.0.0"}
    
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "feature_flags": "enabled"}
    
    
    @app.get("/api/meal-plans")
    @flag_required("enhanced_meal_plans", default_value=False)
    async def get_meal_plans(
        request: Request,
        flags: Dict[str, Any] = Depends(flag_dependency),
    ) -> list[MealPlan]:
        """Get meal plans - requires enhanced meal plans feature."""
        flag_client = flags["flag_client"]
        context = flags["flag_context"]
        
        # Check if enhanced features are enabled
        enhanced_enabled = await flag_client.is_enabled(
            "enhanced_meal_plans", context, False
        )
        
        # Return different meal plans based on feature flag
        if enhanced_enabled:
            return [
                MealPlan(
                    id="plan_1",
                    name="Enhanced Meal Plan",
                    meals=["breakfast", "lunch", "dinner", "snacks"],
                    enhanced=True,
                ),
                MealPlan(
                    id="plan_2", 
                    name="Premium Meal Plan",
                    meals=["gourmet_breakfast", "healthy_lunch", "chef_dinner"],
                    enhanced=True,
                ),
            ]
        else:
            return [
                MealPlan(
                    id="basic_plan",
                    name="Basic Meal Plan", 
                    meals=["breakfast", "lunch", "dinner"],
                    enhanced=False,
                )
            ]
    
    
    @app.get("/api/profile")
    async def get_user_profile(
        request: Request,
        flags: Dict[str, Any] = Depends(flag_dependency),
    ) -> UserProfile:
        """Get user profile with feature flag context."""
        context = flags["flag_context"]
        
        return UserProfile(
            user_id=context.user_id or "anonymous",
            subscription_tier=context.subscription_tier or "free",
            preferences={
                "country": context.country,
                "segments": context.user_segments,
            },
        )
    
    
    @app.get("/api/ui-config")
    async def get_ui_config(
        request: Request,
        flags: Dict[str, Any] = Depends(flag_dependency),
    ) -> Dict[str, Any]:
        """Get UI configuration based on feature flags."""
        flag_client = flags["flag_client"]
        context = flags["flag_context"]
        
        # Get UI theme variant
        theme = await flag_client.get_variant("ui_theme", context, "classic")
        
        # Get API version
        api_version = await flag_client.get_variant("api_v2", context, "v1")
        
        config = {
            "theme": theme,
            "api_version": api_version,
            "features": {
                "enhanced_meal_plans": await flag_client.is_enabled(
                    "enhanced_meal_plans", context, False
                ),
            }
        }
        
        # Track UI config request
        await flag_client.track_event(
            "ui_config_requested",
            context,
            {"theme": theme, "api_version": api_version},
        )
        
        return config
    
    
    # Demonstrate feature gate decorator
    async def classic_algorithm(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classic meal planning algorithm."""
        return {
            "algorithm": "classic",
            "plan_type": "standard",
            "features": ["basic_macros"],
            "data": user_data,
        }
    
    
    async def enhanced_algorithm(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced meal planning algorithm."""
        return {
            "algorithm": "enhanced_ai",
            "plan_type": "personalized",
            "features": ["advanced_macros", "ai_recommendations", "preference_learning"],
            "data": user_data,
        }
    
    
    @app.post("/api/generate-meal-plan")
    @feature_gate(
        "enhanced_meal_plans",
        variants={
            "off": classic_algorithm,
            "on": enhanced_algorithm,
        },
        default_variant="off",
    )
    async def generate_meal_plan(
        user_data: Dict[str, Any],
        request: Request,
        flags: Dict[str, Any] = Depends(flag_dependency),
    ) -> Dict[str, Any]:
        """Generate meal plan using feature-gated algorithms."""
        # This will automatically route to the correct algorithm
        # based on the feature flag value
        pass
    
    
    @app.get("/admin/flags")
    async def list_flags(
        request: Request,
        flags: Dict[str, Any] = Depends(flag_dependency),
    ) -> Dict[str, Any]:
        """Admin endpoint to list all feature flags."""
        flag_client = flags["flag_client"]
        
        # In a real app, you'd check admin permissions here
        admin_user = request.headers.get("X-Admin-User")
        if not admin_user:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get flag information
        service = flag_client.service
        flags_info = {}
        
        for flag_key, flag_def in service._flags.items():
            flags_info[flag_key] = {
                "name": flag_def.name,
                "description": flag_def.description,
                "status": flag_def.status,
                "variants": [v.key for v in flag_def.variants],
                "default_variant": flag_def.default_variant,
                "tags": flag_def.tags,
            }
        
        return {
            "flags": flags_info,
            "total_count": len(flags_info),
        }
    
    
    @app.get("/admin/flag/{flag_key}/metrics")
    async def get_flag_metrics(
        flag_key: str,
        request: Request,
        flags: Dict[str, Any] = Depends(flag_dependency),
    ) -> Dict[str, Any]:
        """Get metrics for a specific flag."""
        admin_user = request.headers.get("X-Admin-User")
        if not admin_user:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        flag_client = flags["flag_client"]
        service = flag_client.service
        
        # Get evaluation metrics
        metrics = await service.get_evaluation_metrics(flag_key)
        
        if not metrics:
            raise HTTPException(status_code=404, detail="Flag not found or no metrics")
        
        return {
            "flag_key": flag_key,
            "metrics": metrics,
        }
    
    
    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Exception",
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
        )
    
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred",
                "type": type(exc).__name__,
            },
        )


# Demo client for testing
async def demo_requests():
    """Demo requests to test the API."""
    import httpx
    
    print("\n🌐 Testing FastAPI Feature Flag Integration")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test different user types
    test_users = [
        {
            "name": "Premium User",
            "headers": {
                "X-User-ID": "premium_user_001",
                "X-Subscription-Tier": "premium",
                "X-Country": "US",
            }
        },
        {
            "name": "Free User",
            "headers": {
                "X-User-ID": "free_user_002", 
                "X-Subscription-Tier": "free",
                "X-Country": "CA",
            }
        },
        {
            "name": "Anonymous User",
            "headers": {
                "X-Country": "UK",
            }
        },
    ]
    
    async with httpx.AsyncClient() as client:
        for user in test_users:
            print(f"\n👤 Testing as: {user['name']}")
            print("-" * 30)
            
            # Test UI config
            response = await client.get(
                f"{base_url}/api/ui-config",
                headers=user["headers"]
            )
            if response.status_code == 200:
                config = response.json()
                print(f"UI Config: {config}")
            
            # Test profile
            response = await client.get(
                f"{base_url}/api/profile",
                headers=user["headers"]
            )
            if response.status_code == 200:
                profile = response.json()
                print(f"Profile: {profile}")
            
            # Test meal plans (may fail if feature not enabled)
            response = await client.get(
                f"{base_url}/api/meal-plans",
                headers=user["headers"]
            )
            if response.status_code == 200:
                plans = response.json()
                print(f"Meal Plans: {len(plans)} plans")
            else:
                print(f"Meal Plans: Not available ({response.status_code})")


if __name__ == "__main__":
    if not FASTAPI_AVAILABLE:
        print("❌ FastAPI not available. Install with: pip install fastapi uvicorn")
        exit(1)
    
    print("🚀 Starting FastAPI Feature Flag Demo")
    print("=" * 40)
    print("Run with: uvicorn fastapi_integration:app --reload")
    print("Then visit: http://localhost:8000/docs")
    print("\nOr run demo client:")
    
    # Run demo client
    asyncio.run(demo_requests())
