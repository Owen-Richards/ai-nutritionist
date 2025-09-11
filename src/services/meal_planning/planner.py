"""
Meal Planning Service - Core meal plan generation logic
Consolidates: adaptive_meal_planning_service.py, meal_planning_service.py
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

# Import consolidated AI service
from ..consolidated_ai_nutrition_service import ConsolidatedAINutritionService

logger = logging.getLogger(__name__)

class MealPlanningService:
    """
    Core meal planning service that generates personalized meal plans
    based on user preferences, health goals, and dietary constraints.
    """
    
    def __init__(self):
        self.ai_service = ConsolidatedAINutritionService()
        self.logger = logging.getLogger(__name__)
    
    def generate_meal_plan(
        self, 
        user_profile: Dict[str, Any], 
        time_period: str = "week",
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized meal plan for a user
        
        Args:
            user_profile: User's health profile and preferences
            time_period: Planning period (day, week, month)
            preferences: Additional meal preferences
            
        Returns:
            Comprehensive meal plan with recipes and nutrition data
        """
        try:
            self.logger.info(f"Generating {time_period} meal plan for user")
            
            # Extract user requirements
            dietary_restrictions = user_profile.get('dietary_restrictions', [])
            health_goals = user_profile.get('health_goals', [])
            calorie_target = user_profile.get('daily_calories', 2000)
            
            # Use consolidated AI service for intelligent meal planning
            meal_plan_request = {
                "user_profile": user_profile,
                "time_period": time_period,
                "preferences": preferences or {},
                "dietary_restrictions": dietary_restrictions,
                "health_goals": health_goals,
                "calorie_target": calorie_target
            }
            
            # Generate intelligent meal plan
            meal_plan = self.ai_service.generate_intelligent_meal_plan(meal_plan_request)
            
            # Add planning metadata
            meal_plan.update({
                "generated_at": datetime.now().isoformat(),
                "time_period": time_period,
                "user_id": user_profile.get('user_id'),
                "version": "2.0"
            })
            
            self.logger.info(f"Successfully generated meal plan with {len(meal_plan.get('meals', []))} meals")
            return meal_plan
            
        except Exception as e:
            self.logger.error(f"Error generating meal plan: {str(e)}")
            return self._get_fallback_meal_plan(user_profile, time_period)
    
    def adapt_meal_plan(
        self, 
        existing_plan: Dict[str, Any], 
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adapt an existing meal plan based on user feedback
        
        Args:
            existing_plan: Current meal plan
            feedback: User feedback and preferences
            
        Returns:
            Adapted meal plan
        """
        try:
            self.logger.info("Adapting meal plan based on user feedback")
            
            # Use AI service for intelligent adaptation
            adaptation_request = {
                "existing_plan": existing_plan,
                "feedback": feedback,
                "adaptation_type": "user_feedback"
            }
            
            adapted_plan = self.ai_service.adapt_meal_plan(adaptation_request)
            
            # Update metadata
            adapted_plan.update({
                "adapted_at": datetime.now().isoformat(),
                "adaptation_reason": "user_feedback",
                "version": str(float(existing_plan.get('version', '1.0')) + 0.1)
            })
            
            return adapted_plan
            
        except Exception as e:
            self.logger.error(f"Error adapting meal plan: {str(e)}")
            return existing_plan
    
    def validate_meal_plan(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a meal plan for nutritional completeness and safety
        
        Args:
            meal_plan: Meal plan to validate
            
        Returns:
            Validation results with recommendations
        """
        try:
            validation_results = {
                "is_valid": True,
                "warnings": [],
                "recommendations": [],
                "nutrition_analysis": {}
            }
            
            # Use AI service for comprehensive validation
            nutrition_analysis = self.ai_service.analyze_meal_plan_nutrition(meal_plan)
            validation_results["nutrition_analysis"] = nutrition_analysis
            
            # Check for basic requirements
            meals = meal_plan.get('meals', [])
            if len(meals) == 0:
                validation_results["is_valid"] = False
                validation_results["warnings"].append("No meals found in plan")
            
            # Validate daily nutrition targets
            daily_calories = nutrition_analysis.get('daily_calories', 0)
            if daily_calories < 1200:
                validation_results["warnings"].append("Daily calories below recommended minimum")
            elif daily_calories > 3000:
                validation_results["warnings"].append("Daily calories above typical maximum")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating meal plan: {str(e)}")
            return {
                "is_valid": False,
                "error": str(e),
                "warnings": ["Validation failed"],
                "recommendations": ["Please regenerate meal plan"]
            }
    
    def get_meal_alternatives(
        self, 
        meal: Dict[str, Any], 
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get alternative meals for a specific meal in the plan
        
        Args:
            meal: Original meal to find alternatives for
            user_profile: User's profile and preferences
            
        Returns:
            List of alternative meals
        """
        try:
            # Use AI service to find nutritionally similar alternatives
            alternatives_request = {
                "original_meal": meal,
                "user_profile": user_profile,
                "criteria": ["similar_nutrition", "dietary_compatible", "variety"]
            }
            
            alternatives = self.ai_service.find_meal_alternatives(alternatives_request)
            
            return alternatives.get('alternatives', [])
            
        except Exception as e:
            self.logger.error(f"Error finding meal alternatives: {str(e)}")
            return []
    
    def _get_fallback_meal_plan(
        self, 
        user_profile: Dict[str, Any], 
        time_period: str
    ) -> Dict[str, Any]:
        """
        Generate a basic fallback meal plan when AI service fails
        """
        days = 1 if time_period == "day" else 7 if time_period == "week" else 30
        
        fallback_plan = {
            "meals": [],
            "time_period": time_period,
            "days": days,
            "generated_at": datetime.now().isoformat(),
            "is_fallback": True,
            "message": "Basic meal plan generated due to service limitations"
        }
        
        # Generate simple balanced meals
        for day in range(days):
            daily_meals = {
                "day": day + 1,
                "date": (datetime.now() + timedelta(days=day)).isoformat()[:10],
                "breakfast": {
                    "name": "Oatmeal with fruits",
                    "calories": 300,
                    "protein": 8,
                    "carbs": 54,
                    "fat": 6
                },
                "lunch": {
                    "name": "Grilled chicken salad",
                    "calories": 400,
                    "protein": 35,
                    "carbs": 15,
                    "fat": 22
                },
                "dinner": {
                    "name": "Baked salmon with vegetables",
                    "calories": 450,
                    "protein": 40,
                    "carbs": 20,
                    "fat": 25
                }
            }
            fallback_plan["meals"].append(daily_meals)
        
        return fallback_plan
