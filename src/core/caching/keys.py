"""
Cache key builder for consistent cache key generation.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class CacheKeyBuilder:
    """Builds consistent cache keys with versioning and namespacing."""
    
    def __init__(self, namespace: str = "ai_nutritionist", version: str = "v1"):
        self.namespace = namespace
        self.version = version
    
    def build_key(
        self, 
        entity: str, 
        operation: str, 
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Build a cache key with consistent format.
        
        Args:
            entity: Entity type (user, meal_plan, recipe, etc.)
            operation: Operation type (get, list, search, etc.)
            params: Parameters that affect the result
            tags: Tags for cache invalidation
            user_id: User ID for user-specific caching
            
        Returns:
            Formatted cache key string
        """
        key_parts = [self.namespace, self.version, entity, operation]
        
        # Add user context if provided
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        # Add parameter hash if provided
        if params:
            param_hash = self._hash_params(params)
            key_parts.append(f"params:{param_hash}")
        
        # Add tags if provided
        if tags:
            tag_str = ":".join(sorted(tags))
            key_parts.append(f"tags:{tag_str}")
        
        return ":".join(key_parts)
    
    def build_user_key(self, user_id: str, entity: str, operation: str = "get") -> str:
        """Build a user-specific cache key."""
        return self.build_key(entity, operation, user_id=user_id)
    
    def build_search_key(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Build a search cache key."""
        params = {"query": query}
        
        if filters:
            params["filters"] = filters
        if sort_by:
            params["sort_by"] = sort_by
        if limit:
            params["limit"] = limit
        
        return self.build_key("search", "query", params)
    
    def build_meal_plan_key(
        self, 
        user_id: str, 
        week_start: str,
        preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a meal plan cache key."""
        params = {"week_start": week_start}
        if preferences:
            params["preferences"] = preferences
        
        return self.build_key("meal_plan", "weekly", params, user_id=user_id)
    
    def build_recipe_key(
        self, 
        recipe_id: Optional[str] = None,
        search_query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a recipe cache key."""
        if recipe_id:
            return self.build_key("recipe", "get", {"id": recipe_id})
        elif search_query:
            params = {"query": search_query}
            if filters:
                params.update(filters)
            return self.build_key("recipe", "search", params)
        else:
            raise ValueError("Either recipe_id or search_query must be provided")
    
    def build_nutrition_key(self, ingredients: List[str]) -> str:
        """Build a nutrition analysis cache key."""
        # Sort ingredients for consistent key regardless of order
        sorted_ingredients = sorted(ingredients)
        params = {"ingredients": sorted_ingredients}
        return self.build_key("nutrition", "analysis", params)
    
    def build_session_key(self, session_id: str, user_id: str) -> str:
        """Build a session cache key."""
        params = {"session_id": session_id}
        return self.build_key("session", "data", params, user_id=user_id)
    
    def build_api_key(
        self, 
        service: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build an API response cache key."""
        cache_params = {"service": service, "endpoint": endpoint}
        if params:
            cache_params["params"] = params
        
        return self.build_key("api", "response", cache_params)
    
    def build_computed_key(
        self, 
        computation_type: str, 
        inputs: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Build a computed results cache key."""
        params = {
            "type": computation_type,
            "inputs": inputs
        }
        return self.build_key("computed", "result", params, user_id=user_id)
    
    def build_tag_pattern(self, tags: List[str]) -> str:
        """Build a pattern for tag-based cache invalidation."""
        return f"{self.namespace}:{self.version}:*:tags:{':'.join(sorted(tags))}*"
    
    def build_user_pattern(self, user_id: str) -> str:
        """Build a pattern for user-specific cache invalidation."""
        return f"{self.namespace}:{self.version}:*:user:{user_id}*"
    
    def build_entity_pattern(self, entity: str) -> str:
        """Build a pattern for entity-specific cache invalidation."""
        return f"{self.namespace}:{self.version}:{entity}:*"
    
    def extract_user_id(self, cache_key: str) -> Optional[str]:
        """Extract user ID from cache key if present."""
        parts = cache_key.split(":")
        for i, part in enumerate(parts):
            if part == "user" and i + 1 < len(parts):
                return parts[i + 1]
        return None
    
    def extract_entity(self, cache_key: str) -> Optional[str]:
        """Extract entity type from cache key."""
        parts = cache_key.split(":")
        if len(parts) >= 3:
            return parts[2]
        return None
    
    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Create a hash of parameters for consistent key generation."""
        # Convert to JSON string with sorted keys for consistency
        param_str = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(param_str.encode()).hexdigest()[:16]
    
    def set_version(self, version: str):
        """Update the version for cache key generation."""
        self.version = version
    
    def set_namespace(self, namespace: str):
        """Update the namespace for cache key generation."""
        self.namespace = namespace


# Global cache key builder instance
_cache_key_builder: Optional[CacheKeyBuilder] = None


def get_cache_key_builder() -> CacheKeyBuilder:
    """Get the global cache key builder instance."""
    global _cache_key_builder
    
    if _cache_key_builder is None:
        _cache_key_builder = CacheKeyBuilder()
    
    return _cache_key_builder
