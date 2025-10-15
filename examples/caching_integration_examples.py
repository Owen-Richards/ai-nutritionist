"""
Integration examples showing how to use the comprehensive caching system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.core.caching import (
    cached, 
    invalidate_cache,
    user_data_cache,
    meal_plan_cache,
    recipe_cache,
    nutrition_cache,
    session_cache,
    api_response_cache,
    get_cache_manager
)

logger = logging.getLogger(__name__)


class CachedUserService:
    """Example of integrating user service with caching."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
    
    @cached(ttl=1800, profile="user_data", tags=["user"], key_template="user:profile:{user_id}")
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile with automatic caching."""
        logger.info(f"Loading user profile from database for {user_id}")
        
        # Simulate database call
        await asyncio.sleep(0.1)
        
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "preferences": {
                "dietary_restrictions": ["vegetarian"],
                "cuisine_preferences": ["italian", "mexican"]
            },
            "nutrition_targets": {
                "daily_calories": 2000,
                "protein_grams": 150
            }
        }
    
    @invalidate_cache(tags=["user"])
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile and invalidate cache."""
        logger.info(f"Updating user profile for {user_id}")
        
        # Simulate database update
        await asyncio.sleep(0.05)
        
        return True
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences using application cache."""
        return await user_data_cache.get_user_preferences(user_id)
    
    async def set_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Set user preferences using application cache."""
        return await user_data_cache.set_user_preferences(user_id, preferences)


class CachedMealPlanService:
    """Example of integrating meal plan service with caching."""
    
    @cached(
        ttl=3600, 
        profile="meal_plan", 
        tags=["meal_plan"],
        key_template="meal_plan:{user_id}:{week_start}"
    )
    async def generate_meal_plan(
        self, 
        user_id: str, 
        week_start: str,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate meal plan with caching."""
        logger.info(f"Generating meal plan for user {user_id}, week {week_start}")
        
        # Simulate AI meal plan generation (expensive operation)
        await asyncio.sleep(2.0)
        
        return {
            "user_id": user_id,
            "week_start": week_start,
            "meals": [
                {
                    "day": "Monday",
                    "breakfast": "Oatmeal with berries",
                    "lunch": "Caesar salad",
                    "dinner": "Grilled salmon with vegetables"
                },
                # ... more meals
            ],
            "grocery_list": ["oats", "berries", "lettuce", "salmon"],
            "total_calories": 1850,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    @invalidate_cache(tags=["meal_plan"])
    async def customize_meal_plan(
        self, 
        user_id: str, 
        week_start: str, 
        customizations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Customize meal plan and invalidate old cache."""
        logger.info(f"Customizing meal plan for user {user_id}")
        
        # Load current plan
        current_plan = await self.generate_meal_plan(user_id, week_start)
        
        # Apply customizations
        current_plan.update(customizations)
        current_plan["customized_at"] = datetime.utcnow().isoformat()
        
        return current_plan


class CachedRecipeService:
    """Example of integrating recipe service with caching."""
    
    @cached(
        ttl=86400, 
        profile="computed_results", 
        tags=["recipe"],
        key_template="recipe:{recipe_id}"
    )
    async def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get recipe with long-term caching."""
        logger.info(f"Loading recipe {recipe_id} from database")
        
        # Simulate database call
        await asyncio.sleep(0.2)
        
        return {
            "recipe_id": recipe_id,
            "name": f"Recipe {recipe_id}",
            "ingredients": ["ingredient1", "ingredient2"],
            "instructions": ["Step 1", "Step 2"],
            "nutrition": {
                "calories": 350,
                "protein": 25,
                "carbs": 30,
                "fat": 15
            }
        }
    
    @cached(
        ttl=3600, 
        profile="api_response", 
        tags=["recipe", "search"],
        key_template="recipe:search:{query}:{filters_hash}"
    )
    async def search_recipes(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search recipes with caching."""
        logger.info(f"Searching recipes for: {query}")
        
        # Simulate external API call
        await asyncio.sleep(1.0)
        
        return [
            {
                "recipe_id": f"recipe_{i}",
                "name": f"Recipe matching {query} #{i}",
                "score": 0.9 - (i * 0.1)
            }
            for i in range(5)
        ]
    
    @invalidate_cache(tags=["recipe", "search"])
    async def add_recipe(self, recipe_data: Dict[str, Any]) -> str:
        """Add new recipe and invalidate search caches."""
        logger.info("Adding new recipe")
        
        # Simulate database insert
        await asyncio.sleep(0.1)
        
        recipe_id = f"recipe_{datetime.utcnow().timestamp()}"
        return recipe_id


class CachedNutritionService:
    """Example of integrating nutrition service with caching."""
    
    @cached(
        ttl=86400, 
        profile="computed_results", 
        tags=["nutrition"],
        key_template="nutrition:analysis:{ingredients_hash}"
    )
    async def analyze_nutrition(self, ingredients: List[str]) -> Dict[str, Any]:
        """Analyze nutrition with long-term caching."""
        logger.info(f"Analyzing nutrition for {len(ingredients)} ingredients")
        
        # Simulate expensive nutrition calculation
        await asyncio.sleep(1.5)
        
        return {
            "total_calories": sum(len(ing) * 10 for ing in ingredients),
            "protein": sum(len(ing) * 2 for ing in ingredients),
            "carbs": sum(len(ing) * 5 for ing in ingredients),
            "fat": sum(len(ing) * 1 for ing in ingredients),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    @cached(
        ttl=1800, 
        profile="api_response", 
        tags=["nutrition", "external"],
        key_template="nutrition:external:{food_item}"
    )
    async def get_external_nutrition(self, food_item: str) -> Dict[str, Any]:
        """Get nutrition data from external API with caching."""
        logger.info(f"Fetching external nutrition data for: {food_item}")
        
        # Simulate external API call
        await asyncio.sleep(0.8)
        
        return {
            "food_item": food_item,
            "calories_per_100g": 200,
            "protein_per_100g": 20,
            "source": "external_api",
            "fetched_at": datetime.utcnow().isoformat()
        }


class CachedSessionService:
    """Example of session management with caching."""
    
    async def create_session(self, user_id: str) -> str:
        """Create new session with caching."""
        session_id = f"session_{datetime.utcnow().timestamp()}"
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "conversation_state": {},
            "context": {}
        }
        
        await session_cache.set_session_data(session_id, user_id, session_data)
        return session_id
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from cache."""
        return await session_cache.get_session_data(session_id, user_id)
    
    async def update_session(
        self, 
        session_id: str, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update session data in cache."""
        current_data = await session_cache.get_session_data(session_id, user_id)
        
        if current_data:
            current_data.update(updates)
            current_data["updated_at"] = datetime.utcnow().isoformat()
            
            return await session_cache.set_session_data(session_id, user_id, current_data)
        
        return False
    
    async def end_session(self, session_id: str, user_id: str) -> bool:
        """End session and remove from cache."""
        return await session_cache.invalidate_session(session_id, user_id)


class CacheIntegrationExample:
    """Example showing various caching patterns and integration."""
    
    def __init__(self):
        self.user_service = CachedUserService()
        self.meal_plan_service = CachedMealPlanService()
        self.recipe_service = CachedRecipeService()
        self.nutrition_service = CachedNutritionService()
        self.session_service = CachedSessionService()
        self.cache_manager = get_cache_manager()
    
    async def demo_user_workflow(self, user_id: str):
        """Demonstrate a complete user workflow with caching."""
        print(f"\n=== Demo User Workflow for {user_id} ===")
        
        # 1. Get user profile (will be cached)
        print("1. Getting user profile...")
        profile = await self.user_service.get_user_profile(user_id)
        print(f"   Profile loaded: {profile['name']}")
        
        # 2. Get user profile again (cache hit)
        print("2. Getting user profile again (should be cached)...")
        profile2 = await self.user_service.get_user_profile(user_id)
        print(f"   Profile cached: {profile2['name']}")
        
        # 3. Generate meal plan (expensive operation, will be cached)
        print("3. Generating meal plan...")
        week_start = datetime.utcnow().strftime('%Y-W%U')
        meal_plan = await self.meal_plan_service.generate_meal_plan(user_id, week_start)
        print(f"   Meal plan generated with {len(meal_plan['meals'])} meals")
        
        # 4. Get meal plan again (cache hit)
        print("4. Getting meal plan again (should be cached)...")
        meal_plan2 = await self.meal_plan_service.generate_meal_plan(user_id, week_start)
        print(f"   Meal plan cached: {meal_plan2['generated_at']}")
        
        # 5. Search recipes (will be cached)
        print("5. Searching recipes...")
        recipes = await self.recipe_service.search_recipes("chicken")
        print(f"   Found {len(recipes)} recipes")
        
        # 6. Analyze nutrition (expensive operation, will be cached)
        print("6. Analyzing nutrition...")
        ingredients = ["chicken breast", "broccoli", "rice"]
        nutrition = await self.nutrition_service.analyze_nutrition(ingredients)
        print(f"   Nutrition analysis: {nutrition['total_calories']} calories")
        
        # 7. Update user profile (will invalidate cache)
        print("7. Updating user profile (will invalidate cache)...")
        await self.user_service.update_user_profile(user_id, {"last_login": datetime.utcnow().isoformat()})
        print("   Profile updated")
        
        # 8. Get user profile again (cache miss, will reload)
        print("8. Getting user profile after update (cache miss)...")
        profile3 = await self.user_service.get_user_profile(user_id)
        print(f"   Profile reloaded: {profile3['name']}")
    
    async def demo_cache_strategies(self):
        """Demonstrate different cache strategies and features."""
        print("\n=== Demo Cache Strategies ===")
        
        # 1. Cache warming
        print("1. Cache warming...")
        keys_and_loaders = [
            ("recipe:1", lambda: self.recipe_service.get_recipe("1")),
            ("recipe:2", lambda: self.recipe_service.get_recipe("2")),
            ("recipe:3", lambda: self.recipe_service.get_recipe("3"))
        ]
        warmed = await self.cache_manager.warm_cache(keys_and_loaders, "computed_results")
        print(f"   Warmed {warmed} cache entries")
        
        # 2. Tag-based invalidation
        print("2. Tag-based invalidation...")
        invalidated = await self.cache_manager.invalidate_by_tag("recipe")
        print(f"   Invalidated {invalidated} recipe cache entries")
        
        # 3. Pattern-based invalidation
        print("3. Pattern-based invalidation...")
        # Add some test data first
        await api_response_cache.set_api_response("edamam", "search", {"test": "data"})
        await api_response_cache.set_api_response("spoonacular", "recipes", {"test": "data"})
        
        invalidated = await self.cache_manager.invalidate_by_pattern("*api*edamam*")
        print(f"   Invalidated {invalidated} API cache entries")
        
        # 4. Cache metrics
        print("4. Cache metrics...")
        metrics = self.cache_manager.get_metrics()
        print(f"   Hit ratio: {metrics.hit_ratio:.2%}")
        print(f"   Total operations: {metrics.total_operations}")
        print(f"   Errors: {metrics.errors}")
        
        # 5. Cache status
        print("5. Cache status...")
        status = self.cache_manager.get_status()
        print(f"   Available backends: {status['backends']}")
        print(f"   Available strategies: {status['strategies']}")
    
    async def demo_session_management(self, user_id: str):
        """Demonstrate session management with caching."""
        print(f"\n=== Demo Session Management for {user_id} ===")
        
        # Create session
        session_id = await self.session_service.create_session(user_id)
        print(f"1. Created session: {session_id}")
        
        # Update session
        await self.session_service.update_session(
            session_id, 
            user_id, 
            {"current_conversation": "meal planning"}
        )
        print("2. Updated session with conversation state")
        
        # Get session
        session = await self.session_service.get_session(session_id, user_id)
        print(f"3. Retrieved session: {session['current_conversation']}")
        
        # End session
        await self.session_service.end_session(session_id, user_id)
        print("4. Ended session")
        
        # Try to get ended session
        session = await self.session_service.get_session(session_id, user_id)
        print(f"5. Session after end: {session}")


async def run_caching_examples():
    """Run all caching integration examples."""
    example = CacheIntegrationExample()
    
    # Run demos
    await example.demo_user_workflow("user123")
    await example.demo_cache_strategies()
    await example.demo_session_management("user123")
    
    print("\n=== Caching Examples Complete ===")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    asyncio.run(run_caching_examples())
