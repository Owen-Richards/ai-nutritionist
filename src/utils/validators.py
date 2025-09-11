"""
AI Nutritionist - Input Validators
Centralized validation for user inputs and data
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from ..config.constants import (
    MEAL_PLANNING_RULES,
    RATE_LIMITS,
    SPAM_KEYWORDS,
    DEFAULT_NUTRITION_TARGETS
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class PhoneValidator:
    """Phone number validation utilities"""
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Check if phone number is valid format"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Should be 10-15 digits (international format)
        if len(digits) < 10 or len(digits) > 15:
            return False
        
        # US/Canada format check
        if len(digits) == 10:
            return digits[0] != '0' and digits[0] != '1'
        elif len(digits) == 11:
            return digits[0] == '1' and digits[1] != '0' and digits[1] != '1'
        
        return True
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number to consistent format"""
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+{digits}"
        else:
            return f"+{digits}"


class MessageValidator:
    """Message content validation"""
    
    @staticmethod
    def is_valid_message(message: str) -> bool:
        """Check if message content is valid"""
        if not message or not isinstance(message, str):
            return False
        
        # Check length
        if len(message.strip()) == 0 or len(message) > 2000:
            return False
        
        return True
    
    @staticmethod
    def contains_spam(message: str) -> bool:
        """Check if message contains spam keywords"""
        message_lower = message.lower()
        
        for spam_word in SPAM_KEYWORDS:
            if spam_word.lower() in message_lower:
                logger.warning(f"Spam keyword detected: {spam_word}")
                return True
        
        return False
    
    @staticmethod
    def extract_intent_keywords(message: str) -> List[str]:
        """Extract potential intent keywords from message"""
        # Common nutrition and meal planning keywords
        keywords = [
            'meal plan', 'meals', 'recipe', 'cook', 'food',
            'grocery', 'shopping', 'ingredients', 'list',
            'calories', 'nutrition', 'protein', 'carbs', 'fat',
            'weight loss', 'muscle gain', 'diet', 'healthy',
            'breakfast', 'lunch', 'dinner', 'snack',
            'vegetarian', 'vegan', 'keto', 'gluten free'
        ]
        
        found_keywords = []
        message_lower = message.lower()
        
        for keyword in keywords:
            if keyword in message_lower:
                found_keywords.append(keyword)
        
        return found_keywords


class NutritionValidator:
    """Nutrition data validation"""
    
    @staticmethod
    def validate_calories(calories: Union[int, float, str]) -> float:
        """Validate calorie input"""
        try:
            cal_value = float(calories)
            
            if cal_value < 0:
                raise ValidationError("Calories cannot be negative")
            
            if cal_value > 10000:
                raise ValidationError("Calories seem too high (max 10,000)")
            
            return round(cal_value, 1)
            
        except (ValueError, TypeError):
            raise ValidationError("Invalid calorie format")
    
    @staticmethod
    def validate_macros(protein: float, carbs: float, fat: float) -> Dict[str, float]:
        """Validate macronutrient values"""
        macros = {}
        
        try:
            macros['protein'] = float(protein)
            macros['carbs'] = float(carbs) 
            macros['fat'] = float(fat)
            
            # Check ranges
            for macro, value in macros.items():
                if value < 0:
                    raise ValidationError(f"{macro} cannot be negative")
                if value > 1000:
                    raise ValidationError(f"{macro} value seems too high")
            
            return macros
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid macro format: {str(e)}")
    
    @staticmethod
    def validate_nutrition_targets(targets: Dict[str, Any]) -> Dict[str, float]:
        """Validate daily nutrition targets"""
        required_fields = ['calories', 'protein_grams', 'carbs_grams', 'fat_grams']
        
        for field in required_fields:
            if field not in targets:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate calories
        calories = NutritionValidator.validate_calories(targets['calories'])
        
        # Validate macros
        macros = NutritionValidator.validate_macros(
            targets['protein_grams'],
            targets['carbs_grams'], 
            targets['fat_grams']
        )
        
        # Check macro balance (calories should roughly match macros)
        calculated_calories = (
            macros['protein'] * 4 + 
            macros['carbs'] * 4 + 
            macros['fat'] * 9
        )
        
        calorie_diff = abs(calories - calculated_calories) / calories
        if calorie_diff > 0.3:  # 30% tolerance
            logger.warning(f"Calorie/macro mismatch: {calories} vs {calculated_calories}")
        
        return {
            'calories': calories,
            'protein_grams': macros['protein'],
            'carbs_grams': macros['carbs'],
            'fat_grams': macros['fat'],
            'fiber_grams': float(targets.get('fiber_grams', 25)),
            'sodium_mg': float(targets.get('sodium_mg', 2300)),
        }


class MealPlanValidator:
    """Meal plan data validation"""
    
    @staticmethod
    def validate_household_size(size: Union[int, str]) -> int:
        """Validate household size"""
        try:
            size_int = int(size)
            
            if size_int < 1:
                raise ValidationError("Household size must be at least 1")
            
            if size_int > MEAL_PLANNING_RULES['max_household_size']:
                raise ValidationError(f"Household size too large (max {MEAL_PLANNING_RULES['max_household_size']})")
            
            return size_int
            
        except (ValueError, TypeError):
            raise ValidationError("Household size must be a number")
    
    @staticmethod
    def validate_weekly_budget(budget: Union[float, str]) -> float:
        """Validate weekly budget amount"""
        try:
            budget_float = float(budget)
            
            if budget_float < MEAL_PLANNING_RULES['min_budget_per_week']:
                raise ValidationError(f"Budget too low (min ${MEAL_PLANNING_RULES['min_budget_per_week']})")
            
            if budget_float > MEAL_PLANNING_RULES['max_budget_per_week']:
                raise ValidationError(f"Budget too high (max ${MEAL_PLANNING_RULES['max_budget_per_week']})")
            
            return round(budget_float, 2)
            
        except (ValueError, TypeError):
            raise ValidationError("Budget must be a valid amount")
    
    @staticmethod
    def validate_prep_time(prep_time: Union[int, str]) -> int:
        """Validate meal prep time preference"""
        try:
            time_int = int(prep_time)
            
            min_time = MEAL_PLANNING_RULES['min_prep_time_minutes']
            max_time = MEAL_PLANNING_RULES['max_prep_time_minutes']
            
            if time_int < min_time:
                raise ValidationError(f"Prep time too short (min {min_time} minutes)")
            
            if time_int > max_time:
                raise ValidationError(f"Prep time too long (max {max_time} minutes)")
            
            return time_int
            
        except (ValueError, TypeError):
            raise ValidationError("Prep time must be in minutes")
    
    @staticmethod
    def validate_meal_plan_dates(start_date: Union[str, date], end_date: Union[str, date]) -> tuple:
        """Validate meal plan date range"""
        try:
            if isinstance(start_date, str):
                start = date.fromisoformat(start_date)
            else:
                start = start_date
            
            if isinstance(end_date, str):
                end = date.fromisoformat(end_date)
            else:
                end = end_date
            
            # Check date order
            if end <= start:
                raise ValidationError("End date must be after start date")
            
            # Check duration (reasonable limits)
            duration = (end - start).days
            if duration > 28:  # 4 weeks max
                raise ValidationError("Meal plan duration too long (max 4 weeks)")
            
            # Check if start date is not too far in past
            today = date.today()
            if start < today:
                raise ValidationError("Start date cannot be in the past")
            
            return start, end
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid date format: {str(e)}")


class UserInputValidator:
    """User profile and preference validation"""
    
    @staticmethod
    def validate_user_goal(goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user goal data"""
        required_fields = ['goal_type', 'priority']
        
        for field in required_fields:
            if field not in goal_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate priority
        priority = goal_data['priority']
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            raise ValidationError("Priority must be between 1 and 5")
        
        # Validate target value if present
        if 'target_value' in goal_data and goal_data['target_value'] is not None:
            try:
                target = float(goal_data['target_value'])
                if target <= 0:
                    raise ValidationError("Target value must be positive")
                goal_data['target_value'] = target
            except (ValueError, TypeError):
                raise ValidationError("Target value must be a number")
        
        return goal_data
    
    @staticmethod
    def validate_dietary_restrictions(restrictions: List[str]) -> List[str]:
        """Validate dietary restrictions list"""
        valid_restrictions = [
            'vegetarian', 'vegan', 'gluten_free', 'dairy_free', 
            'nut_free', 'kosher', 'halal', 'low_sodium', 'low_carb', 'keto'
        ]
        
        validated = []
        for restriction in restrictions:
            if isinstance(restriction, str) and restriction.lower() in valid_restrictions:
                validated.append(restriction.lower())
            else:
                logger.warning(f"Invalid dietary restriction: {restriction}")
        
        return validated
    
    @staticmethod
    def validate_cuisine_preferences(cuisines: List[str]) -> List[str]:
        """Validate cuisine preference list"""
        valid_cuisines = [
            'american', 'italian', 'mexican', 'chinese', 'indian', 
            'japanese', 'thai', 'french', 'mediterranean', 'korean',
            'vietnamese', 'greek', 'spanish', 'middle_eastern'
        ]
        
        validated = []
        for cuisine in cuisines:
            if isinstance(cuisine, str) and cuisine.lower() in valid_cuisines:
                validated.append(cuisine.lower())
            else:
                logger.warning(f"Invalid cuisine preference: {cuisine}")
        
        return validated


class RateLimitValidator:
    """Rate limiting validation"""
    
    @staticmethod
    def check_message_rate_limit(user_id: str, current_count: int, time_window: str) -> bool:
        """Check if user is within message rate limits"""
        limits = {
            'minute': RATE_LIMITS['messages_per_minute'],
            'hour': RATE_LIMITS['messages_per_hour'],
            'day': RATE_LIMITS['messages_per_day'],
        }
        
        limit = limits.get(time_window)
        if limit is None:
            logger.warning(f"Unknown rate limit window: {time_window}")
            return True
        
        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for user {user_id}: {current_count}/{limit} per {time_window}")
            return False
        
        return True
    
    @staticmethod
    def check_api_rate_limit(api_name: str, current_count: int) -> bool:
        """Check API-specific rate limits"""
        api_limits = {
            'edamam': 10,  # per minute
            'openai': 50,  # per minute  
            'twilio': 100, # per minute
        }
        
        limit = api_limits.get(api_name, 60)  # default 60/minute
        
        if current_count >= limit:
            logger.warning(f"API rate limit exceeded for {api_name}: {current_count}/{limit}")
            return False
        
        return True


def validate_and_sanitize_input(data: Dict[str, Any], validation_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize input data based on rules
    
    Args:
        data: Input data to validate
        validation_rules: Dictionary of field validation rules
        
    Returns:
        Validated and sanitized data
        
    Raises:
        ValidationError: If validation fails
    """
    validated = {}
    
    for field, rules in validation_rules.items():
        value = data.get(field)
        
        # Check required fields
        if rules.get('required', False) and value is None:
            raise ValidationError(f"Field '{field}' is required")
        
        # Skip validation for optional empty fields
        if value is None:
            if 'default' in rules:
                validated[field] = rules['default']
            continue
        
        # Type validation
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            try:
                # Try to convert
                if expected_type == int:
                    value = int(value)
                elif expected_type == float:
                    value = float(value)
                elif expected_type == str:
                    value = str(value)
                else:
                    raise ValidationError(f"Invalid type for '{field}'")
            except (ValueError, TypeError):
                raise ValidationError(f"Field '{field}' must be of type {expected_type.__name__}")
        
        # Length validation for strings
        if isinstance(value, str):
            min_len = rules.get('min_length', 0)
            max_len = rules.get('max_length', float('inf'))
            
            if len(value) < min_len:
                raise ValidationError(f"Field '{field}' too short (min {min_len} characters)")
            
            if len(value) > max_len:
                raise ValidationError(f"Field '{field}' too long (max {max_len} characters)")
        
        # Range validation for numbers
        if isinstance(value, (int, float)):
            min_val = rules.get('min_value')
            max_val = rules.get('max_value')
            
            if min_val is not None and value < min_val:
                raise ValidationError(f"Field '{field}' below minimum ({min_val})")
            
            if max_val is not None and value > max_val:
                raise ValidationError(f"Field '{field}' above maximum ({max_val})")
        
        # Custom validation function
        validator_func = rules.get('validator')
        if validator_func and callable(validator_func):
            try:
                value = validator_func(value)
            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(f"Validation failed for '{field}': {str(e)}")
        
        validated[field] = value
    
    return validated
