"""Integration of feature flags with AI Nutritionist meal planning service."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from packages.shared.feature_flags import (
    FeatureFlagService,
    FeatureFlagClient,
    FlagContext,
    FeatureFlagDefinition,
    FlagVariant,
    FlagStatus,
    CacheConfig,
)


class FeatureFlaggedMealPlanningService:
    """Enhanced meal planning service with feature flag integration."""
    
    def __init__(
        self,
        flag_client: FeatureFlagClient,
        base_meal_service: Optional[Any] = None,
    ):
        self.flag_client = flag_client
        self.base_meal_service = base_meal_service
    
    async def generate_meal_plan(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        context: Optional[FlagContext] = None,
    ) -> Dict[str, Any]:
        """Generate meal plan with feature flag-controlled algorithm selection."""
        
        if not context:
            context = await self._create_user_context(user_id, preferences)
        
        # Check which meal planning algorithm to use
        algorithm_variant = await self.flag_client.get_variant(
            "enhanced_meal_planning",
            context,
            default="basic"
        )
        
        # Route to appropriate algorithm based on feature flag
        if algorithm_variant == "advanced":
            meal_plan = await self._generate_advanced_meal_plan(user_id, preferences, context)
        elif algorithm_variant == "basic":
            meal_plan = await self._generate_basic_meal_plan(user_id, preferences, context)
        else:
            # Fallback to basic if flag is off
            meal_plan = await self._generate_basic_meal_plan(user_id, preferences, context)
        
        # Check if smart nutrition analysis is enabled
        nutrition_enabled = await self.flag_client.is_enabled(
            "smart_nutrition_analysis",
            context,
            default=False
        )
        
        if nutrition_enabled:
            nutrition_variant = await self.flag_client.get_variant(
                "smart_nutrition_analysis",
                context,
                default="basic"
            )
            meal_plan["nutrition_analysis"] = await self._add_nutrition_analysis(
                meal_plan, nutrition_variant
            )
        
        # Check if fitness integration is enabled
        fitness_enabled = await self.flag_client.is_enabled(
            "fitness_integration_v2",
            context,
            default=False
        )
        
        if fitness_enabled:
            meal_plan["fitness_integration"] = await self._add_fitness_integration(
                user_id, meal_plan, context
            )
        
        # Track usage for analytics
        await self.flag_client.track_event(
            "meal_plan_generated",
            context,
            {
                "algorithm": algorithm_variant,
                "nutrition_analysis": nutrition_enabled,
                "fitness_integration": fitness_enabled,
                "meal_count": len(meal_plan.get("meals", [])),
            }
        )
        
        return meal_plan
    
    async def _create_user_context(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> FlagContext:
        """Create flag context from user data."""
        
        # In a real implementation, you'd fetch user data from database
        user_data = await self._get_user_data(user_id)
        
        return FlagContext(
            user_id=user_id,
            subscription_tier=user_data.get("subscription_tier", "free"),
            country=user_data.get("country", "US"),
            user_segments=self._determine_user_segments(user_data, preferences),
            custom_attributes={
                "dietary_restrictions": preferences.get("dietary_restrictions", []),
                "fitness_goals": preferences.get("fitness_goals", []),
                "cooking_skill": preferences.get("cooking_skill", "beginner"),
                "meal_prep_time": preferences.get("meal_prep_time", 30),
                "days_since_signup": user_data.get("days_since_signup", 0),
                "previous_plans_count": user_data.get("previous_plans_count", 0),
            }
        )
    
    async def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Fetch user data (mock implementation)."""
        # Mock user data - in real app, fetch from database
        return {
            "subscription_tier": "premium" if user_id.endswith("_premium") else "free",
            "country": "US",
            "days_since_signup": 30,
            "previous_plans_count": 5,
            "engagement_score": 0.75,
        }
    
    def _determine_user_segments(
        self, 
        user_data: Dict[str, Any], 
        preferences: Dict[str, Any]
    ) -> List[str]:
        """Determine user segments for targeting."""
        segments = []
        
        # Engagement-based segments
        if user_data.get("engagement_score", 0) > 0.8:
            segments.append("power_user")
        
        # Tenure-based segments
        if user_data.get("days_since_signup", 0) < 30:
            segments.append("new_user")
        
        # Preference-based segments
        if "vegan" in preferences.get("dietary_restrictions", []):
            segments.append("vegan_user")
        
        if "weight_loss" in preferences.get("fitness_goals", []):
            segments.append("weight_loss_user")
        
        # Experience-based segments
        if preferences.get("cooking_skill") == "expert":
            segments.append("expert_cook")
        
        # Plan history segments
        if user_data.get("previous_plans_count", 0) > 10:
            segments.append("experienced_user")
        
        return segments
    
    async def _generate_advanced_meal_plan(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        context: FlagContext,
    ) -> Dict[str, Any]:
        """Generate meal plan using advanced AI algorithm."""
        
        # Advanced AI-powered meal planning
        meal_plan = {
            "id": f"advanced_plan_{user_id}_{int(datetime.now().timestamp())}",
            "algorithm": "advanced_ai",
            "personalization_level": "high",
            "meals": [
                {
                    "type": "breakfast",
                    "name": "AI-Optimized Protein Bowl",
                    "calories": 420,
                    "macros": {"protein": 28, "carbs": 35, "fat": 18},
                    "ingredients": ["quinoa", "eggs", "avocado", "spinach"],
                    "ai_confidence": 0.95,
                    "personalization_factors": ["protein_preference", "fiber_needs"]
                },
                {
                    "type": "lunch", 
                    "name": "Smart Mediterranean Salad",
                    "calories": 380,
                    "macros": {"protein": 22, "carbs": 28, "fat": 20},
                    "ingredients": ["chicken", "quinoa", "feta", "olive_oil"],
                    "ai_confidence": 0.92,
                    "personalization_factors": ["taste_preference", "satiety_goals"]
                },
                {
                    "type": "dinner",
                    "name": "Adaptive Salmon & Vegetables",
                    "calories": 450,
                    "macros": {"protein": 32, "carbs": 25, "fat": 22},
                    "ingredients": ["salmon", "sweet_potato", "broccoli", "olive_oil"],
                    "ai_confidence": 0.98,
                    "personalization_factors": ["omega3_needs", "cooking_skill"]
                }
            ],
            "ai_features": {
                "preference_learning": True,
                "macro_optimization": True,
                "ingredient_substitution": True,
                "cooking_time_optimization": True,
            },
            "total_calories": 1250,
            "total_macros": {"protein": 82, "carbs": 88, "fat": 60},
        }
        
        return meal_plan
    
    async def _generate_basic_meal_plan(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        context: FlagContext,
    ) -> Dict[str, Any]:
        """Generate meal plan using basic algorithm."""
        
        # Basic template-based meal planning
        meal_plan = {
            "id": f"basic_plan_{user_id}_{int(datetime.now().timestamp())}",
            "algorithm": "template_based",
            "personalization_level": "basic",
            "meals": [
                {
                    "type": "breakfast",
                    "name": "Standard Oatmeal Bowl",
                    "calories": 350,
                    "macros": {"protein": 15, "carbs": 55, "fat": 8},
                    "ingredients": ["oats", "banana", "almonds", "milk"],
                },
                {
                    "type": "lunch",
                    "name": "Basic Chicken Salad",
                    "calories": 400,
                    "macros": {"protein": 30, "carbs": 20, "fat": 15},
                    "ingredients": ["chicken", "lettuce", "tomato", "dressing"],
                },
                {
                    "type": "dinner",
                    "name": "Simple Pasta with Vegetables",
                    "calories": 500,
                    "macros": {"protein": 20, "carbs": 70, "fat": 12},
                    "ingredients": ["pasta", "tomato_sauce", "vegetables", "cheese"],
                }
            ],
            "total_calories": 1250,
            "total_macros": {"protein": 65, "carbs": 145, "fat": 35},
        }
        
        return meal_plan
    
    async def _add_nutrition_analysis(
        self,
        meal_plan: Dict[str, Any],
        variant: str,
    ) -> Dict[str, Any]:
        """Add nutrition analysis based on feature flag variant."""
        
        if variant == "advanced":
            return {
                "analysis_type": "advanced_ai",
                "micronutrient_analysis": {
                    "vitamin_c": "adequate",
                    "vitamin_d": "needs_attention", 
                    "iron": "good",
                    "calcium": "excellent",
                },
                "health_insights": [
                    "Your protein intake is well-balanced for muscle maintenance",
                    "Consider adding more colorful vegetables for antioxidants",
                    "Omega-3 levels are optimal with the salmon choice",
                ],
                "optimization_suggestions": [
                    "Add berries to breakfast for antioxidants",
                    "Consider spinach in lunch for iron boost",
                ],
                "nutrient_timing": {
                    "post_workout": "High protein breakfast recommended",
                    "evening": "Lower carb dinner supports sleep quality",
                },
                "confidence_score": 0.94,
            }
        else:
            return {
                "analysis_type": "basic",
                "macro_breakdown": meal_plan.get("total_macros", {}),
                "calorie_assessment": "within recommended range",
                "general_tips": [
                    "Drink plenty of water throughout the day",
                    "Include a variety of colors in your vegetables",
                ],
            }
    
    async def _add_fitness_integration(
        self,
        user_id: str,
        meal_plan: Dict[str, Any],
        context: FlagContext,
    ) -> Dict[str, Any]:
        """Add fitness integration data."""
        
        # Mock fitness data - in real app, fetch from fitness APIs
        fitness_data = {
            "todays_activity": {
                "steps": 8500,
                "calories_burned": 420,
                "active_minutes": 45,
                "workouts": ["30min cardio"],
            },
            "weekly_goals": {
                "target_calories_burned": 2500,
                "target_workouts": 4,
                "current_progress": 0.6,
            },
            "recovery_metrics": {
                "sleep_quality": 0.8,
                "hrv_score": 65,
                "recovery_status": "good",
            }
        }
        
        # Adjust meal plan based on fitness data
        adjustments = []
        
        if fitness_data["todays_activity"]["calories_burned"] > 400:
            adjustments.append("Increased protein for muscle recovery")
            # Increase protein in each meal by 10%
            for meal in meal_plan["meals"]:
                if "macros" in meal:
                    meal["macros"]["protein"] = int(meal["macros"]["protein"] * 1.1)
        
        if "cardio" in str(fitness_data["todays_activity"]["workouts"]):
            adjustments.append("Added complex carbs for energy replenishment")
        
        if fitness_data["recovery_metrics"]["recovery_status"] == "poor":
            adjustments.append("Emphasized anti-inflammatory foods")
        
        return {
            "fitness_data": fitness_data,
            "meal_adjustments": adjustments,
            "integration_features": [
                "Activity-based calorie adjustment",
                "Workout-informed nutrition timing",
                "Recovery-optimized food selection",
            ],
            "next_meal_timing": "Post-workout meal within 30 minutes recommended",
        }


async def demonstrate_integrated_meal_planning():
    """Demonstrate feature-flagged meal planning service."""
    
    print("🍽️  Feature-Flagged Meal Planning Service Demo")
    print("=" * 50)
    
    # Initialize feature flag service
    cache_config = CacheConfig(ttl_seconds=300, enable_local_cache=True)
    flag_service = FeatureFlagService(cache_config=cache_config)
    flag_client = FeatureFlagClient(flag_service)
    
    # Register feature flags for meal planning
    meal_planning_flags = [
        FeatureFlagDefinition(
            key="enhanced_meal_planning",
            name="Enhanced Meal Planning",
            description="AI-powered enhanced meal planning",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="basic", value="basic", percentage=50),
                FlagVariant(key="advanced", value="advanced", percentage=50),
            ],
            default_variant="basic",
            fallback_variant="basic",
            created_by="meal-team",
            tags=["meal-planning", "ai"],
        ),
        FeatureFlagDefinition(
            key="smart_nutrition_analysis",
            name="Smart Nutrition Analysis",
            description="AI nutrition analysis and insights",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="disabled", value=False, percentage=30),
                FlagVariant(key="basic", value="basic", percentage=40),
                FlagVariant(key="advanced", value="advanced", percentage=30),
            ],
            default_variant="basic",
            fallback_variant="disabled",
            created_by="nutrition-team",
            tags=["nutrition", "analysis", "ai"],
        ),
        FeatureFlagDefinition(
            key="fitness_integration_v2",
            name="Fitness Integration V2",
            description="Enhanced fitness data integration",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="off", value=False, percentage=60),
                FlagVariant(key="on", value=True, percentage=40),
            ],
            default_variant="off",
            fallback_variant="off",
            created_by="fitness-team",
            tags=["fitness", "integration"],
        ),
    ]
    
    for flag in meal_planning_flags:
        await flag_service.register_flag(flag)
    
    print("✅ Feature flags registered for meal planning")
    
    # Initialize meal planning service
    meal_service = FeatureFlaggedMealPlanningService(flag_client)
    
    # Test with different user types
    test_users = [
        {
            "user_id": "user_001_premium",
            "preferences": {
                "dietary_restrictions": ["vegetarian"],
                "fitness_goals": ["muscle_gain"],
                "cooking_skill": "intermediate",
                "meal_prep_time": 45,
            }
        },
        {
            "user_id": "user_002_free",
            "preferences": {
                "dietary_restrictions": ["gluten_free"],
                "fitness_goals": ["weight_loss"],
                "cooking_skill": "beginner",
                "meal_prep_time": 20,
            }
        },
        {
            "user_id": "user_003_premium",
            "preferences": {
                "dietary_restrictions": ["vegan"],
                "fitness_goals": ["endurance"],
                "cooking_skill": "expert",
                "meal_prep_time": 60,
            }
        },
    ]
    
    print("\n🧪 Testing meal plan generation for different users:")
    print("-" * 55)
    
    for user in test_users:
        print(f"\n👤 User: {user['user_id']}")
        print(f"   Preferences: {user['preferences']}")
        
        # Generate meal plan
        meal_plan = await meal_service.generate_meal_plan(
            user["user_id"],
            user["preferences"]
        )
        
        print(f"   Algorithm: {meal_plan['algorithm']}")
        print(f"   Personalization: {meal_plan['personalization_level']}")
        print(f"   Total calories: {meal_plan['total_calories']}")
        print(f"   Meals: {len(meal_plan['meals'])}")
        
        # Show nutrition analysis if available
        if "nutrition_analysis" in meal_plan:
            analysis = meal_plan["nutrition_analysis"]
            print(f"   Nutrition analysis: {analysis['analysis_type']}")
            if "health_insights" in analysis:
                print(f"   Health insights: {len(analysis['health_insights'])} provided")
        
        # Show fitness integration if available
        if "fitness_integration" in meal_plan:
            integration = meal_plan["fitness_integration"]
            print(f"   Fitness integration: {len(integration['meal_adjustments'])} adjustments")
        
        print()
    
    # Demonstrate A/B testing for meal algorithms
    print("📊 A/B Testing Results Simulation:")
    print("-" * 35)
    
    algorithm_results = {"basic": 0, "advanced": 0}
    
    for i in range(20):
        user_id = f"test_user_{i:03d}"
        preferences = {
            "dietary_restrictions": [],
            "fitness_goals": ["general_health"],
            "cooking_skill": "intermediate",
        }
        
        meal_plan = await meal_service.generate_meal_plan(user_id, preferences)
        algorithm_results[meal_plan["algorithm"]] += 1
    
    print(f"Algorithm distribution (20 users):")
    for algorithm, count in algorithm_results.items():
        percentage = (count / 20) * 100
        print(f"  {algorithm}: {count}/20 ({percentage}%)")
    
    print("\n✨ Meal planning integration demo completed!")


async def demonstrate_feature_flag_meal_customization():
    """Demonstrate feature flag controlled meal customization."""
    
    print("\n🎨 Feature Flag Meal Customization Demo")
    print("=" * 45)
    
    # This would integrate with the existing meal planning pipeline
    # from src.services.meal_planning.pipeline import MealPlanPipeline
    
    # Example of how to integrate feature flags into existing services
    customization_scenarios = [
        {
            "scenario": "Smart Ingredient Substitution",
            "flag": "smart_substitutions",
            "description": "AI-powered ingredient substitutions based on availability and preferences",
        },
        {
            "scenario": "Seasonal Menu Adaptation",
            "flag": "seasonal_menus",
            "description": "Automatically adapt menus based on seasonal ingredient availability",
        },
        {
            "scenario": "Cultural Cuisine Preferences",
            "flag": "cultural_adaptation",
            "description": "Adapt meal plans to cultural and regional cuisine preferences",
        },
        {
            "scenario": "Meal Timing Optimization", 
            "flag": "meal_timing",
            "description": "Optimize meal timing based on circadian rhythms and activity patterns",
        },
    ]
    
    print("🔧 Available customization features:")
    for scenario in customization_scenarios:
        print(f"  • {scenario['scenario']}")
        print(f"    Flag: {scenario['flag']}")
        print(f"    Description: {scenario['description']}")
        print()
    
    print("💡 Integration points with existing meal planning:")
    print("  • Pipeline coordination with feature flags")
    print("  • Smart swap engine with A/B testing")
    print("  • Feature logging for ML improvements")
    print("  • Preference learning with flag-controlled algorithms")


if __name__ == "__main__":
    asyncio.run(demonstrate_integrated_meal_planning())
    asyncio.run(demonstrate_feature_flag_meal_customization())
