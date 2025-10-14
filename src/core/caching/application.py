"""
Application-specific caching implementations for AI Nutritionist.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .cache_manager import get_cache_manager
from .keys import get_cache_key_builder
from .decorators import cached, invalidate_cache
from .config import CacheTier

logger = logging.getLogger(__name__)


@dataclass
class UserCacheEntry:
    """User-specific cache entry with metadata."""
    
    user_id: str
    profile_data: Dict[str, Any]
    preferences: Dict[str, Any]
    last_meal_plan: Optional[Dict[str, Any]] = None
    nutrition_targets: Optional[Dict[str, Any]] = None
    session_data: Optional[Dict[str, Any]] = None
    cached_at: datetime = None
    
    def __post_init__(self):
        if self.cached_at is None:
            self.cached_at = datetime.utcnow()


class UserDataCache:
    """Specialized cache for user data with intelligent prefetching."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile with caching."""
        key = self.key_builder.build_user_key(user_id, "profile")
        value, hit = await self.cache_manager.get(key, profile="user_data")
        return value
    
    async def set_user_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any]
    ) -> bool:
        """Set user profile in cache."""
        key = self.key_builder.build_user_key(user_id, "profile")
        return await self.cache_manager.set(
            key, 
            profile_data, 
            profile="user_data",
            tags=["user", f"user:{user_id}"]
        )
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences with caching."""
        key = self.key_builder.build_user_key(user_id, "preferences")
        value, hit = await self.cache_manager.get(key, profile="user_data")
        return value
    
    async def set_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> bool:
        """Set user preferences in cache."""
        key = self.key_builder.build_user_key(user_id, "preferences")
        return await self.cache_manager.set(
            key, 
            preferences, 
            profile="user_data",
            tags=["user", "preferences", f"user:{user_id}"]
        )
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        return await self.cache_manager.invalidate_user_cache(user_id)
    
    async def warm_user_cache(
        self, 
        user_id: str, 
        data_loaders: Dict[str, callable]
    ) -> int:
        """Warm cache for a user with pre-loaded data."""
        keys_and_loaders = []
        
        for data_type, loader in data_loaders.items():
            key = self.key_builder.build_user_key(user_id, data_type)
            keys_and_loaders.append((key, loader))
        
        return await self.cache_manager.warm_cache(keys_and_loaders, "user_data")


class MealPlanCache:
    """Specialized cache for meal plans with versioning."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    @cached(ttl=3600, profile="meal_plan", tags=["meal_plan"])
    async def get_meal_plan(
        self, 
        user_id: str, 
        week_start: str,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached meal plan for user and week."""
        # This is just the cache decorator - actual loading would be done
        # by the caller's loader function
        return None
    
    async def set_meal_plan(
        self, 
        user_id: str, 
        week_start: str, 
        meal_plan: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Set meal plan in cache."""
        key = self.key_builder.build_meal_plan_key(user_id, week_start, preferences)
        return await self.cache_manager.set(
            key, 
            meal_plan, 
            profile="meal_plan",
            tags=["meal_plan", f"user:{user_id}", f"week:{week_start}"]
        )
    
    async def get_latest_meal_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent meal plan for a user."""
        # This would require a separate index or scanning
        # For now, implement as a direct cache lookup
        current_week = datetime.utcnow().strftime('%Y-W%U')
        key = self.key_builder.build_meal_plan_key(user_id, current_week)
        value, hit = await self.cache_manager.get(key, profile="meal_plan")
        return value
    
    @invalidate_cache(tags=["meal_plan"])
    async def invalidate_meal_plans(self, user_id: Optional[str] = None):
        """Invalidate meal plan caches."""
        if user_id:
            await self.cache_manager.invalidate_by_tag(f"user:{user_id}")
        # The decorator will handle tag-based invalidation


class RecipeCache:
    """Specialized cache for recipes and search results."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    @cached(ttl=86400, profile="computed_results", tags=["recipe"])
    async def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get cached recipe by ID."""
        return None
    
    @cached(ttl=3600, profile="api_response", tags=["recipe", "search"])
    async def search_recipes(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached recipe search results."""
        return None
    
    async def set_recipe(self, recipe_id: str, recipe_data: Dict[str, Any]) -> bool:
        """Set recipe in cache."""
        key = self.key_builder.build_recipe_key(recipe_id=recipe_id)
        return await self.cache_manager.set(
            key, 
            recipe_data, 
            profile="computed_results",
            tags=["recipe", f"recipe:{recipe_id}"]
        )
    
    @invalidate_cache(tags=["recipe", "search"])
    async def add_new_recipe(self, recipe_data: Dict[str, Any]):
        """Add new recipe and invalidate search caches."""
        # The decorator will handle invalidation
        pass


class NutritionCache:
    """Specialized cache for nutrition analysis and calculations."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    @cached(ttl=86400, profile="computed_results", tags=["nutrition"])
    async def get_nutrition_analysis(
        self, 
        ingredients: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get cached nutrition analysis for ingredients."""
        return None
    
    async def set_nutrition_analysis(
        self, 
        ingredients: List[str], 
        nutrition_data: Dict[str, Any]
    ) -> bool:
        """Set nutrition analysis in cache."""
        key = self.key_builder.build_nutrition_key(ingredients)
        return await self.cache_manager.set(
            key, 
            nutrition_data, 
            profile="computed_results",
            tags=["nutrition", "analysis"]
        )
    
    @cached(ttl=1800, profile="api_response", tags=["nutrition", "external"])
    async def get_external_nutrition_data(
        self, 
        food_item: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached external nutrition API data."""
        return None


class SessionCache:
    """Specialized cache for user sessions and conversation state."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    async def get_session_data(
        self, 
        session_id: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached session data."""
        key = self.key_builder.build_session_key(session_id, user_id)
        value, hit = await self.cache_manager.get(key, profile="session_data")
        return value
    
    async def set_session_data(
        self, 
        session_id: str, 
        user_id: str, 
        session_data: Dict[str, Any]
    ) -> bool:
        """Set session data in cache."""
        key = self.key_builder.build_session_key(session_id, user_id)
        return await self.cache_manager.set(
            key, 
            session_data, 
            profile="session_data",
            tags=["session", f"user:{user_id}"]
        )
    
    async def extend_session(self, session_id: str, user_id: str) -> bool:
        """Extend session TTL."""
        key = self.key_builder.build_session_key(session_id, user_id)
        data = await self.get_session_data(session_id, user_id)
        
        if data:
            return await self.set_session_data(session_id, user_id, data)
        
        return False
    
    async def invalidate_session(self, session_id: str, user_id: str) -> bool:
        """Invalidate a specific session."""
        key = self.key_builder.build_session_key(session_id, user_id)
        return await self.cache_manager.delete(key)


class ComputedResultsCache:
    """Cache for expensive computations and ML model results."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    @cached(ttl=86400, profile="computed_results", tags=["ml", "computation"])
    async def get_computed_result(
        self, 
        computation_type: str, 
        inputs: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[Any]:
        """Get cached computation result."""
        return None
    
    async def set_computed_result(
        self, 
        computation_type: str, 
        inputs: Dict[str, Any], 
        result: Any,
        user_id: Optional[str] = None
    ) -> bool:
        """Set computation result in cache."""
        key = self.key_builder.build_computed_key(computation_type, inputs, user_id)
        tags = ["computation", f"type:{computation_type}"]
        
        if user_id:
            tags.append(f"user:{user_id}")
        
        return await self.cache_manager.set(
            key, 
            result, 
            profile="computed_results",
            tags=tags
        )
    
    @invalidate_cache(tags=["computation"])
    async def invalidate_computations_by_type(self, computation_type: str):
        """Invalidate all computations of a specific type."""
        await self.cache_manager.invalidate_by_tag(f"type:{computation_type}")


class APIResponseCache:
    """Cache for external API responses."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.key_builder = get_cache_key_builder()
    
    @cached(ttl=1800, profile="api_response", tags=["api", "external"])
    async def get_api_response(
        self, 
        service: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get cached API response."""
        return None
    
    async def set_api_response(
        self, 
        service: str, 
        endpoint: str, 
        response: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Set API response in cache."""
        key = self.key_builder.build_api_key(service, endpoint, params)
        return await self.cache_manager.set(
            key, 
            response, 
            ttl=ttl,
            profile="api_response",
            tags=["api", f"service:{service}"]
        )
    
    @invalidate_cache(tags=["api"])
    async def invalidate_api_cache(self, service: Optional[str] = None):
        """Invalidate API response caches."""
        if service:
            await self.cache_manager.invalidate_by_tag(f"service:{service}")


class SmartCachePreloader:
    """Intelligent cache preloading based on usage patterns."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.user_cache = UserDataCache()
        self.meal_plan_cache = MealPlanCache()
        self.recipe_cache = RecipeCache()
        
    async def preload_user_context(
        self, 
        user_id: str, 
        data_loaders: Dict[str, callable]
    ) -> Dict[str, bool]:
        """Preload common user data into cache."""
        results = {}
        
        # Preload user profile
        if 'profile' in data_loaders:
            try:
                profile = await data_loaders['profile']()
                results['profile'] = await self.user_cache.set_user_profile(user_id, profile)
            except Exception as e:
                logger.error(f"Error preloading user profile: {e}")
                results['profile'] = False
        
        # Preload preferences
        if 'preferences' in data_loaders:
            try:
                preferences = await data_loaders['preferences']()
                results['preferences'] = await self.user_cache.set_user_preferences(user_id, preferences)
            except Exception as e:
                logger.error(f"Error preloading user preferences: {e}")
                results['preferences'] = False
        
        # Preload current meal plan
        if 'meal_plan' in data_loaders:
            try:
                meal_plan = await data_loaders['meal_plan']()
                current_week = datetime.utcnow().strftime('%Y-W%U')
                results['meal_plan'] = await self.meal_plan_cache.set_meal_plan(
                    user_id, current_week, meal_plan
                )
            except Exception as e:
                logger.error(f"Error preloading meal plan: {e}")
                results['meal_plan'] = False
        
        return results
    
    async def preload_popular_recipes(
        self, 
        recipe_loader: callable,
        recipe_ids: List[str]
    ) -> int:
        """Preload popular recipes into cache."""
        success_count = 0
        
        for recipe_id in recipe_ids:
            try:
                recipe = await recipe_loader(recipe_id)
                if recipe and await self.recipe_cache.set_recipe(recipe_id, recipe):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error preloading recipe {recipe_id}: {e}")
        
        return success_count
    
    async def refresh_expiring_entries(self) -> int:
        """Refresh cache entries that are about to expire."""
        # This would require backend-specific implementation
        # to scan for entries with low TTL
        refreshed = 0
        
        # Implementation would scan cache tiers for entries
        # with TTL < refresh_threshold and refresh them
        
        return refreshed


# Global instances for easy access
user_data_cache = UserDataCache()
meal_plan_cache = MealPlanCache()
recipe_cache = RecipeCache()
nutrition_cache = NutritionCache()
session_cache = SessionCache()
computed_results_cache = ComputedResultsCache()
api_response_cache = APIResponseCache()
smart_preloader = SmartCachePreloader()
