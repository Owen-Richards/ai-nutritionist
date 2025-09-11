"""Prompts package initialization"""

from .templates import (
    PromptTemplate,
    MealPlanningPrompts,
    NutritionAdvicePrompts,
    ConversationPrompts,
    GroceryListPrompts,
    format_user_profile_for_prompt,
    create_nutrition_targets_text,
    get_prompt_for_intent
)

__all__ = [
    'PromptTemplate',
    'MealPlanningPrompts',
    'NutritionAdvicePrompts', 
    'ConversationPrompts',
    'GroceryListPrompts',
    'format_user_profile_for_prompt',
    'create_nutrition_targets_text',
    'get_prompt_for_intent',
]
