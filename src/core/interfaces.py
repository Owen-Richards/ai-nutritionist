"""
Core application interfaces and base classes.

This module defines the core business interfaces that external adapters
implement, ensuring clean separation between business logic and infrastructure.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.user import UserProfile
from ..models.meal_planning import GeneratedMealPlan


class UserRepositoryInterface(ABC):
    """Interface for user data persistence."""
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve user by ID."""
        pass
    
    @abstractmethod
    async def save_user(self, user: UserProfile) -> None:
        """Save user data."""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete user data (GDPR compliance)."""
        pass


class MessagingServiceInterface(ABC):
    """Interface for messaging services."""
    
    @abstractmethod
    async def send_message(self, to: str, message: str) -> bool:
        """Send message to user."""
        pass
    
    @abstractmethod
    async def send_media(self, to: str, media_url: str, caption: str) -> bool:
        """Send media message to user."""
        pass


class AIServiceInterface(ABC):
    """Interface for AI processing services."""
    
    @abstractmethod
    async def generate_meal_plan(self, user_preferences: Dict[str, Any]) -> GeneratedMealPlan:
        """Generate personalized meal plan."""
        pass
    
    @abstractmethod
    async def analyze_food_image(self, image_url: str) -> Dict[str, Any]:
        """Analyze food image for nutrition information."""
        pass


class NutritionDataInterface(ABC):
    """Interface for nutrition data services."""
    
    @abstractmethod
    async def get_nutrition_info(self, food_item: str) -> Dict[str, Any]:
        """Get nutrition information for food item."""
        pass
    
    @abstractmethod
    async def search_recipes(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search recipes based on criteria."""
        pass
