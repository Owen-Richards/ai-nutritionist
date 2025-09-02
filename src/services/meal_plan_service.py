"""
Meal Plan Service for generating and managing meal plans
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MealPlanService:
    """Service for meal plan generation and management"""
    
    def __init__(self, dynamodb_resource, ai_service):
        self.dynamodb = dynamodb_resource
        self.ai_service = ai_service
        self.user_service = None  # Will be injected to avoid circular imports
    
    def set_user_service(self, user_service):
        """Set user service reference (dependency injection)"""
        self.user_service = user_service
    
    def generate_meal_plan(self, user_profile: Dict[str, Any], force_new: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generate or retrieve cached meal plan for user
        """
        try:
            user_id = user_profile['user_id']
            
            # Check for existing plan this week (unless forcing new)
            if not force_new:
                existing_plan = self._get_current_week_plan(user_id)
                if existing_plan:
                    logger.info(f"Returning cached meal plan for user {user_id}")
                    return existing_plan
            
            # Generate new meal plan using AI
            logger.info(f"Generating new meal plan for user {user_id}")
            meal_plan = self.ai_service.generate_meal_plan(user_profile)
            
            if meal_plan:
                # Enhance meal plan with additional data
                enhanced_plan = self._enhance_meal_plan(meal_plan, user_profile)
                
                # Save to database
                plan_date = datetime.utcnow().strftime('%Y-%m-%d')
                if self.user_service:
                    self.user_service.save_meal_plan(user_id, enhanced_plan, plan_date)
                
                return enhanced_plan
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return None
    
    def get_grocery_list(self, user_id: str) -> Optional[List[Dict[str, str]]]:
        """
        Get grocery list for user's current meal plan
        """
        try:
            # Get current meal plan
            meal_plan = self._get_current_week_plan(user_id)
            if not meal_plan:
                return None
            
            # Check if grocery list already exists
            if 'grocery_list' in meal_plan:
                return meal_plan['grocery_list']
            
            # Generate grocery list using AI
            grocery_list = self.ai_service.generate_grocery_list(meal_plan)
            
            # Cache the grocery list
            if grocery_list and self.user_service:
                meal_plan['grocery_list'] = grocery_list
                plan_date = datetime.utcnow().strftime('%Y-%m-%d')
                self.user_service.save_meal_plan(user_id, meal_plan, plan_date)
            
            return grocery_list
            
        except Exception as e:
            logger.error(f"Error getting grocery list for {user_id}: {str(e)}")
            return None
    
    def customize_meal_plan(self, user_id: str, customization: str) -> Optional[Dict[str, Any]]:
        """
        Customize existing meal plan based on user feedback
        """
        try:
            # Get current meal plan
            current_plan = self._get_current_week_plan(user_id)
            if not current_plan:
                return None
            
            # Use AI to modify the plan
            modified_plan = self._apply_customization(current_plan, customization)
            
            if modified_plan and self.user_service:
                # Save updated plan
                plan_date = datetime.utcnow().strftime('%Y-%m-%d')
                self.user_service.save_meal_plan(user_id, modified_plan, plan_date)
            
            return modified_plan
            
        except Exception as e:
            logger.error(f"Error customizing meal plan for {user_id}: {str(e)}")
            return None
    
    def get_meal_suggestions(self, user_profile: Dict[str, Any], meal_type: str = 'dinner') -> List[str]:
        """
        Get quick meal suggestions for a specific meal type
        """
        try:
            # Create a simplified prompt for quick suggestions
            suggestions_prompt = self._build_suggestions_prompt(user_profile, meal_type)
            
            response = self.ai_service._invoke_model(suggestions_prompt, max_tokens=300)
            if response:
                return self._parse_meal_suggestions(response)
            
            return self._get_fallback_suggestions(meal_type)
            
        except Exception as e:
            logger.error(f"Error getting meal suggestions: {str(e)}")
            return self._get_fallback_suggestions(meal_type)
    
    def calculate_nutrition_summary(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate basic nutrition summary for meal plan
        """
        try:
            # This is a simplified calculation
            # In production, you'd integrate with a nutrition API
            
            days = meal_plan.get('days', [])
            total_meals = len(days) * 3  # 3 meals per day
            
            # Estimate based on typical meal calories
            estimated_daily_calories = self._estimate_daily_calories(meal_plan)
            
            return {
                'estimated_daily_calories': estimated_daily_calories,
                'total_meals': total_meals,
                'weekly_calories': estimated_daily_calories * 7,
                'nutrition_score': self._calculate_nutrition_score(meal_plan)
            }
            
        except Exception as e:
            logger.error(f"Error calculating nutrition summary: {str(e)}")
            return {
                'estimated_daily_calories': 2000,
                'total_meals': total_meals if 'total_meals' in locals() else 21,
                'weekly_calories': 14000,
                'nutrition_score': 'Good'
            }
    
    def _get_current_week_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get meal plan for current week
        """
        try:
            if not self.user_service:
                return None
            
            # Check for plans from this week
            start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
            plan_date = start_of_week.strftime('%Y-%m-%d')
            
            # Try to get plan from this week
            response = self.user_service.table.query(
                KeyConditionExpression='user_id = :user_id AND plan_date >= :start_date',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':start_date': plan_date
                },
                ScanIndexForward=False,
                Limit=1
            )
            
            if response['Items']:
                return response['Items'][0].get('meal_plan')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current week plan: {str(e)}")
            return None
    
    def _enhance_meal_plan(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance meal plan with additional metadata
        """
        try:
            enhanced_plan = meal_plan.copy()
            
            # Add nutrition summary
            enhanced_plan['nutrition_summary'] = self.calculate_nutrition_summary(meal_plan)
            
            # Add user context
            enhanced_plan['user_preferences'] = {
                'dietary_restrictions': user_profile.get('dietary_restrictions', []),
                'household_size': user_profile.get('household_size', 2),
                'weekly_budget': user_profile.get('weekly_budget', 75)
            }
            
            # Add generation timestamp
            enhanced_plan['generated_at'] = datetime.utcnow().isoformat()
            
            # Add cooking tips based on user preferences
            enhanced_plan['cooking_tips'] = self._generate_cooking_tips(user_profile)
            
            return enhanced_plan
            
        except Exception as e:
            logger.error(f"Error enhancing meal plan: {str(e)}")
            return meal_plan
    
    def _apply_customization(self, meal_plan: Dict[str, Any], customization: str) -> Optional[Dict[str, Any]]:
        """
        Apply customization to existing meal plan using AI
        """
        try:
            customization_prompt = f"""
            Modify this meal plan based on the user's request:
            
            Current Meal Plan:
            {json.dumps(meal_plan, indent=2)}
            
            User Request: "{customization}"
            
            Please provide the updated meal plan in the same JSON format, making only the requested changes while keeping the overall structure and other meals intact.
            
            Updated meal plan:
            """
            
            response = self.ai_service._invoke_model(customization_prompt, max_tokens=2000)
            if response:
                return self.ai_service._parse_meal_plan_response(response)
            
            return None
            
        except Exception as e:
            logger.error(f"Error applying customization: {str(e)}")
            return None
    
    def _build_suggestions_prompt(self, user_profile: Dict[str, Any], meal_type: str) -> str:
        """
        Build prompt for quick meal suggestions
        """
        dietary_restrictions = user_profile.get('dietary_restrictions', [])
        budget = user_profile.get('weekly_budget', 75)
        
        return f"""
        Suggest 3 quick and easy {meal_type} ideas that are:
        - Budget-friendly (weekly budget: ${budget})
        - {', '.join(dietary_restrictions) if dietary_restrictions else 'No dietary restrictions'}
        - Quick to prepare (30 minutes or less)
        - Nutritious and balanced
        
        Format as a simple list:
        1. [Meal name] - [brief description]
        2. [Meal name] - [brief description]  
        3. [Meal name] - [brief description]
        
        Suggestions:
        """
    
    def _parse_meal_suggestions(self, response: str) -> List[str]:
        """
        Parse meal suggestions from AI response
        """
        suggestions = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                # Clean up the suggestion
                clean_suggestion = line.lstrip('123456789.•- ').strip()
                if clean_suggestion:
                    suggestions.append(clean_suggestion)
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _get_fallback_suggestions(self, meal_type: str) -> List[str]:
        """
        Provide fallback suggestions if AI fails
        """
        fallback_suggestions = {
            'breakfast': [
                "Oatmeal with banana and honey",
                "Scrambled eggs with toast",
                "Greek yogurt with berries"
            ],
            'lunch': [
                "Turkey and avocado sandwich",
                "Chicken salad with mixed greens",
                "Vegetable soup with bread"
            ],
            'dinner': [
                "Baked chicken with roasted vegetables",
                "Spaghetti with marinara sauce",
                "Rice bowl with beans and vegetables"
            ]
        }
        
        return fallback_suggestions.get(meal_type, fallback_suggestions['dinner'])
    
    def _estimate_daily_calories(self, meal_plan: Dict[str, Any]) -> int:
        """
        Estimate daily calories based on meal types and descriptions
        """
        # Simple estimation based on typical meal calories
        base_calories = {
            'breakfast': 400,
            'lunch': 600,
            'dinner': 800
        }
        
        # Adjust based on keywords in meal descriptions
        total_calories = sum(base_calories.values())  # Base: 1800 calories
        
        days = meal_plan.get('days', [])
        if days:
            # Look for high/low calorie indicators
            meal_text = str(meal_plan).lower()
            
            if any(word in meal_text for word in ['salad', 'soup', 'light']):
                total_calories -= 200
            if any(word in meal_text for word in ['pasta', 'rice', 'bread', 'heavy']):
                total_calories += 200
            if any(word in meal_text for word in ['fried', 'cheese', 'cream']):
                total_calories += 300
        
        return max(1500, min(2500, total_calories))  # Reasonable range
    
    def _calculate_nutrition_score(self, meal_plan: Dict[str, Any]) -> str:
        """
        Calculate simple nutrition score
        """
        try:
            meal_text = str(meal_plan).lower()
            score = 0
            
            # Positive indicators
            if 'vegetable' in meal_text or 'veggie' in meal_text:
                score += 2
            if 'fruit' in meal_text:
                score += 1
            if any(word in meal_text for word in ['lean', 'grilled', 'baked']):
                score += 2
            if any(word in meal_text for word in ['whole grain', 'brown rice', 'quinoa']):
                score += 1
            if 'fish' in meal_text:
                score += 1
            
            # Negative indicators
            if any(word in meal_text for word in ['fried', 'processed', 'fast food']):
                score -= 2
            if 'soda' in meal_text or 'candy' in meal_text:
                score -= 1
            
            # Convert to rating
            if score >= 5:
                return 'Excellent'
            elif score >= 3:
                return 'Good'
            elif score >= 1:
                return 'Fair'
            else:
                return 'Needs Improvement'
                
        except Exception:
            return 'Good'
    
    def _generate_cooking_tips(self, user_profile: Dict[str, Any]) -> List[str]:
        """
        Generate cooking tips based on user profile
        """
        tips = []
        
        household_size = user_profile.get('household_size', 2)
        budget = user_profile.get('weekly_budget', 75)
        
        if household_size > 3:
            tips.append("Consider batch cooking on weekends to save time during the week")
        
        if budget < 60:
            tips.append("Buy generic brands and seasonal produce to stretch your budget")
            tips.append("Cook with dried beans and lentils for affordable protein")
        
        if 'vegetarian' in user_profile.get('dietary_restrictions', []):
            tips.append("Combine rice and beans for complete protein")
        
        if not tips:
            tips.append("Meal prep ingredients on Sunday for easier weekday cooking")
        
        return tips
