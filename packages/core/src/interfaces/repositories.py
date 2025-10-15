"""
Core repository interfaces for domain persistence
Following hexagonal architecture principles
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class UserRepository(ABC):
    """Repository interface for user data persistence"""
    
    @abstractmethod
    async def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        pass
    
    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user"""
        pass
    
    @abstractmethod
    async def update_user(self, phone_number: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        pass
    
    @abstractmethod
    async def get_user_preferences(self, phone_number: str) -> Dict[str, Any]:
        """Get user dietary preferences and constraints"""
        pass


class NutritionRepository(ABC):
    """Repository interface for nutrition data persistence"""
    
    @abstractmethod
    async def get_cached_recipe_search(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached recipe search results"""
        pass
    
    @abstractmethod
    async def cache_recipe_search(self, cache_key: str, data: Dict[str, Any], ttl_hours: int = 48) -> bool:
        """Cache recipe search results"""
        pass
    
    @abstractmethod
    async def track_api_usage(self, user_phone: str, api_type: str, cost: float) -> bool:
        """Track API usage for cost monitoring"""
        pass
    
    @abstractmethod
    async def get_user_usage_stats(self, user_phone: str, days: int = 30) -> Dict[str, Any]:
        """Get user API usage statistics"""
        pass


class BusinessRepository(ABC):
    """Repository interface for business data persistence"""
    
    @abstractmethod
    async def get_user_subscription(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user subscription details"""
        pass
    
    @abstractmethod
    async def track_revenue_event(self, event_data: Dict[str, Any]) -> bool:
        """Track revenue event for analytics"""
        pass
    
    @abstractmethod
    async def get_cost_optimization_patterns(self, user_phone: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get user cost optimization patterns"""
        pass
    
    @abstractmethod
    async def save_cost_optimization_pattern(self, pattern_data: Dict[str, Any]) -> bool:
        """Save cost optimization pattern"""
        pass


class BrandRepository(ABC):
    """Repository interface for brand partnership data"""
    
    @abstractmethod
    async def get_brand_campaigns(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get brand campaigns"""
        pass
    
    @abstractmethod
    async def track_ad_impression(self, impression_data: Dict[str, Any]) -> str:
        """Track ad impression and return impression_id"""
        pass
    
    @abstractmethod
    async def track_ad_interaction(self, impression_id: str, interaction_data: Dict[str, Any]) -> bool:
        """Track ad interaction"""
        pass
    
    @abstractmethod
    async def get_impression_details(self, impression_id: str) -> Optional[Dict[str, Any]]:
        """Get impression details"""
        pass


class CacheRepository(ABC):
    """Repository interface for general caching operations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
