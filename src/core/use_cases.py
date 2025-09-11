"""
Core application use cases.

This module contains the business logic use cases that orchestrate
interactions between different services while remaining independent
of external dependencies.
"""

from typing import Dict, Any, Optional
from ..core.interfaces import (
    UserRepositoryInterface,
    MessagingServiceInterface,
    AIServiceInterface,
    NutritionDataInterface
)
from ..models.user import User
from ..models.meal_plan import MealPlan


class NutritionChatUseCase:
    """Use case for handling nutrition chat interactions."""
    
    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        messaging_service: MessagingServiceInterface,
        ai_service: AIServiceInterface,
        nutrition_service: NutritionDataInterface
    ):
        self.user_repository = user_repository
        self.messaging_service = messaging_service
        self.ai_service = ai_service
        self.nutrition_service = nutrition_service
    
    async def handle_message(self, user_id: str, message: str) -> None:
        """Process incoming user message and respond appropriately."""
        user = await self.user_repository.get_user(user_id)
        if not user:
            user = User(id=user_id)
            await self._handle_new_user(user, message)
        else:
            await self._handle_existing_user(user, message)
    
    async def _handle_new_user(self, user: User, message: str) -> None:
        """Handle first-time user interaction."""
        # Progressive onboarding logic
        response = "Welcome! Let's start with your dietary preferences..."
        await self.messaging_service.send_message(user.id, response)
        await self.user_repository.save_user(user)
    
    async def _handle_existing_user(self, user: User, message: str) -> None:
        """Handle returning user interaction."""
        # Determine intent and route to appropriate handler
        if "meal plan" in message.lower():
            await self._handle_meal_plan_request(user)
        elif "nutrition" in message.lower():
            await self._handle_nutrition_question(user, message)
        else:
            await self._handle_general_message(user, message)


class MealPlanGenerationUseCase:
    """Use case for meal plan generation."""
    
    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        ai_service: AIServiceInterface,
        messaging_service: MessagingServiceInterface
    ):
        self.user_repository = user_repository
        self.ai_service = ai_service
        self.messaging_service = messaging_service
    
    async def generate_meal_plan(self, user_id: str) -> MealPlan:
        """Generate personalized meal plan for user."""
        user = await self.user_repository.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        meal_plan = await self.ai_service.generate_meal_plan(user.preferences)
        
        # Send meal plan to user
        plan_message = self._format_meal_plan_message(meal_plan)
        await self.messaging_service.send_message(user_id, plan_message)
        
        return meal_plan
    
    def _format_meal_plan_message(self, meal_plan: MealPlan) -> str:
        """Format meal plan for messaging."""
        return f"Here's your personalized meal plan:\n\n{meal_plan.summary}"


class FoodImageAnalysisUseCase:
    """Use case for analyzing food images."""
    
    def __init__(
        self,
        ai_service: AIServiceInterface,
        messaging_service: MessagingServiceInterface,
        user_repository: UserRepositoryInterface
    ):
        self.ai_service = ai_service
        self.messaging_service = messaging_service
        self.user_repository = user_repository
    
    async def analyze_food_image(self, user_id: str, image_url: str) -> None:
        """Analyze food image and provide feedback."""
        analysis = await self.ai_service.analyze_food_image(image_url)
        
        # Generate personalized feedback
        feedback = self._generate_feedback(analysis)
        await self.messaging_service.send_message(user_id, feedback)
        
        # Update user's meal history
        user = await self.user_repository.get_user(user_id)
        if user:
            user.add_meal_log(analysis)
            await self.user_repository.save_user(user)
    
    def _generate_feedback(self, analysis: Dict[str, Any]) -> str:
        """Generate personalized feedback based on food analysis."""
        return f"Great choice! I see {analysis['food_name']} with approximately {analysis['calories']} calories."
