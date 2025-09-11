"""
AI Nutritionist - AI Prompt Templates
Centralized prompt templates for AI service interactions
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from ..config.constants import GoalType, DietaryRestriction, MealType
from ..models import UserProfile, UserGoal


class PromptTemplate:
    """Base class for AI prompt templates"""
    
    def __init__(self, template: str):
        self.template = template
    
    def format(self, **kwargs) -> str:
        """Format template with provided variables"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required template variable: {e}")


class MealPlanningPrompts:
    """Prompts for meal plan generation"""
    
    GENERATE_MEAL_PLAN = PromptTemplate("""
You are an expert nutritionist creating a personalized {duration}-day meal plan. Generate a practical, balanced meal plan based on these requirements:

USER PROFILE:
- Household size: {household_size} people
- Weekly budget: ${weekly_budget}
- Dietary restrictions: {dietary_restrictions}
- Cuisine preferences: {cuisine_preferences}
- Cooking skill level: {cooking_skill}
- Max prep time per meal: {max_prep_time} minutes
- Primary goals: {primary_goals}

NUTRITION TARGETS (per person per day):
- Calories: {target_calories}
- Protein: {target_protein}g
- Carbs: {target_carbs}g  
- Fat: {target_fat}g

REQUIREMENTS:
1. Stay within budget (${weekly_budget} total for {household_size} people)
2. Respect all dietary restrictions: {dietary_restrictions}
3. Include variety across cuisines: {cuisine_preferences}
4. Keep prep time under {max_prep_time} minutes per meal
5. Balance nutrition to meet daily targets
6. Use seasonal, affordable ingredients
7. Include 3 meals per day: breakfast, lunch, dinner

OUTPUT FORMAT:
Provide a JSON response with this exact structure:
{{
  "meal_plan": {{
    "name": "Personalized {duration}-Day Plan",
    "total_estimated_cost": 0.00,
    "days": [
      {{
        "date": "2024-01-01", 
        "meals": [
          {{
            "meal_type": "breakfast",
            "recipe": {{
              "name": "Recipe Name",
              "servings": {household_size},
              "prep_time_minutes": 15,
              "cook_time_minutes": 10,
              "ingredients": [
                {{"name": "eggs", "quantity": 4, "unit": "large", "estimated_cost": 1.00}},
                {{"name": "spinach", "quantity": 2, "unit": "cups", "estimated_cost": 0.50}}
              ],
              "instructions": [
                "Step 1: Crack eggs into bowl",
                "Step 2: Add spinach and mix"
              ],
              "nutrition": {{
                "calories": 300,
                "protein_grams": 24,
                "carbs_grams": 6,
                "fat_grams": 20,
                "fiber_grams": 2
              }},
              "cuisine_type": "american",
              "difficulty": "easy"
            }}
          }}
        ]
      }}
    ]
  }}
}}

Generate the complete {duration}-day meal plan now:
""")

    MODIFY_MEAL_PLAN = PromptTemplate("""
The user wants to modify their existing meal plan. Here's what they said:
"{user_request}"

CURRENT MEAL PLAN:
{current_meal_plan}

USER CONSTRAINTS:
- Budget: ${weekly_budget}
- Dietary restrictions: {dietary_restrictions}
- Household size: {household_size}

Please modify the meal plan according to their request while maintaining:
1. Budget constraints
2. Nutritional balance
3. Dietary restrictions
4. Cooking time preferences

Provide the updated meal plan in the same JSON format.
""")

    SUBSTITUTE_RECIPE = PromptTemplate("""
The user needs a substitute for this recipe due to: {reason}

ORIGINAL RECIPE:
{original_recipe}

USER CONSTRAINTS:
- Dietary restrictions: {dietary_restrictions}
- Budget per serving: ${max_cost_per_serving}
- Max prep time: {max_prep_time} minutes
- Cuisine preferences: {cuisine_preferences}

Create a suitable substitute recipe that:
1. Meets the same meal type and timing
2. Has similar nutritional profile (±20% calories)
3. Respects dietary restrictions
4. Stays within budget
5. Uses similar or simpler cooking methods

Provide the substitute recipe in JSON format.
""")


class NutritionAdvicePrompts:
    """Prompts for nutrition advice and coaching"""
    
    GENERAL_NUTRITION_ADVICE = PromptTemplate("""
You are a helpful, knowledgeable nutritionist. A user asked: "{user_question}"

USER CONTEXT:
- Current goals: {user_goals}
- Dietary restrictions: {dietary_restrictions}
- Activity level: {activity_level}
- Current challenges: {current_challenges}

Provide practical, evidence-based nutrition advice that:
1. Directly answers their question
2. Considers their personal goals and restrictions
3. Offers actionable steps they can take today
4. Is encouraging and supportive
5. Mentions specific foods or meal ideas when relevant

Keep your response conversational, under 200 words, and include 2-3 specific actionable tips.
""")

    ANALYZE_FOOD_LOG = PromptTemplate("""
Analyze this user's food log and provide insights:

FOOD LOG (last {days} days):
{food_log_data}

USER TARGETS:
- Calories: {target_calories} per day
- Protein: {target_protein}g per day
- Goals: {user_goals}

ANALYSIS NEEDED:
1. How close are they to meeting their targets?
2. What nutrients might they be missing?
3. What patterns do you notice (good and concerning)?
4. What 2-3 specific improvements would have the biggest impact?

Provide encouraging feedback with specific, actionable recommendations.
""")

    MEAL_TIMING_ADVICE = PromptTemplate("""
The user asked about meal timing: "{user_question}"

THEIR CONTEXT:
- Wake up time: {wake_time}
- Work schedule: {work_schedule}
- Workout time: {workout_time}
- Current goals: {user_goals}
- Current eating pattern: {current_pattern}

Provide personalized meal timing advice that:
1. Fits their schedule realistically
2. Supports their fitness goals
3. Optimizes energy levels throughout the day
4. Is practical for their lifestyle

Include specific timing suggestions (e.g., "eat breakfast within 1 hour of waking").
""")


class ConversationPrompts:
    """Prompts for natural conversation and user engagement"""
    
    FRIENDLY_RESPONSE = PromptTemplate("""
Respond to this user message in a friendly, helpful way: "{user_message}"

USER CONTEXT:
- Name: {user_name}
- Subscription: {subscription_tier}
- Recent activity: {recent_activity}
- Current goals: {current_goals}

RESPONSE GUIDELINES:
1. Be warm, encouraging, and conversational
2. Address their message directly
3. Offer relevant help or suggestions
4. Use appropriate emojis (2-3 max)
5. Keep response under 150 words
6. Include a follow-up question or suggestion

If they're asking for features beyond their subscription, gently mention upgrade options.
""")

    GOAL_SETTING_CONVERSATION = PromptTemplate("""
The user wants to set a new goal: "{user_message}"

CURRENT USER GOALS:
{existing_goals}

Help them:
1. Clarify their specific goal if it's vague
2. Set realistic timeframes
3. Identify potential obstacles
4. Suggest first steps
5. Connect it to meal planning

Ask 1-2 follow-up questions to better understand their goal and how to help them achieve it.
Keep the tone supportive and motivating.
""")

    ONBOARDING_CONVERSATION = PromptTemplate("""
This is a new user in the onboarding process. They said: "{user_message}"

ONBOARDING STAGE: {onboarding_stage}
INFORMATION COLLECTED SO FAR:
{collected_info}

NEXT INFORMATION NEEDED:
{needed_info}

Guide them through onboarding by:
1. Acknowledging what they shared
2. Asking for the next piece of information in a natural way
3. Explaining why this information helps their meal plans
4. Being encouraging about their goals

Keep it conversational, not like a form. Make them excited about their personalized nutrition plan.
""")


class GroceryListPrompts:
    """Prompts for grocery list optimization"""
    
    OPTIMIZE_GROCERY_LIST = PromptTemplate("""
Optimize this grocery list for budget and nutrition:

MEAL PLAN INGREDIENTS:
{meal_plan_ingredients}

USER CONSTRAINTS:
- Total budget: ${total_budget}
- Store preference: {store_preference}
- Household size: {household_size}
- Dietary needs: {dietary_needs}

OPTIMIZATION GOALS:
1. Stay within budget
2. Minimize food waste
3. Suggest bulk purchases where cost-effective
4. Recommend generic brands
5. Group items by store section
6. Identify multi-use ingredients

Provide an optimized shopping list with:
- Items grouped by store section
- Quantity recommendations
- Cost estimates
- Money-saving tips
- Substitution suggestions for expensive items
""")

    SEASONAL_SUBSTITUTIONS = PromptTemplate("""
Suggest seasonal substitutions for these ingredients to save money:

INGREDIENTS:
{ingredients_list}

CURRENT SEASON: {current_season}
LOCATION: {user_location}
BUDGET CONSTRAINT: ${max_budget}

For each ingredient, provide:
1. In-season alternatives that are cheaper
2. Frozen/canned options if fresh is expensive  
3. How to modify recipes with substitutions
4. Expected cost savings

Focus on maintaining nutrition while reducing costs.
""")


def format_user_profile_for_prompt(user_profile: UserProfile) -> Dict[str, str]:
    """Convert user profile to prompt-friendly format"""
    
    # Extract goals
    goals_text = "None specified"
    if user_profile.goals:
        goal_descriptions = []
        for goal in user_profile.goals:
            if goal.is_active:
                goal_descriptions.append(f"{goal.goal_type.value} (priority {goal.priority})")
        goals_text = ", ".join(goal_descriptions) if goal_descriptions else "None specified"
    
    # Extract dietary restrictions
    restrictions_text = "None"
    if user_profile.preferences.dietary_restrictions:
        restrictions_text = ", ".join([dr.value for dr in user_profile.preferences.dietary_restrictions])
    
    # Extract cuisine preferences
    cuisine_text = ", ".join(user_profile.preferences.cuisine_preferences) if user_profile.preferences.cuisine_preferences else "No preference"
    
    return {
        "user_id": user_profile.user_id,
        "household_size": str(user_profile.preferences.household_size),
        "weekly_budget": str(user_profile.preferences.weekly_budget),
        "dietary_restrictions": restrictions_text,
        "cuisine_preferences": cuisine_text,
        "cooking_skill": user_profile.preferences.cooking_skill,
        "max_prep_time": str(user_profile.preferences.max_prep_time),
        "primary_goals": goals_text,
        "subscription_tier": user_profile.subscription_tier.value,
    }


def create_nutrition_targets_text(user_profile: UserProfile) -> Dict[str, str]:
    """Create nutrition targets text for prompts"""
    
    # Calculate or get nutrition targets
    if user_profile.nutrition_targets:
        targets = user_profile.nutrition_targets
    else:
        targets = user_profile.calculate_nutrition_targets()
    
    return {
        "target_calories": str(int(targets.calories)),
        "target_protein": str(int(targets.protein_grams)),
        "target_carbs": str(int(targets.carbs_grams)),
        "target_fat": str(int(targets.fat_grams)),
    }


def get_prompt_for_intent(intent: str, **kwargs) -> str:
    """Get appropriate prompt template for user intent"""
    
    prompt_map = {
        "meal_plan_generation": MealPlanningPrompts.GENERATE_MEAL_PLAN,
        "meal_plan_modification": MealPlanningPrompts.MODIFY_MEAL_PLAN,
        "recipe_substitution": MealPlanningPrompts.SUBSTITUTE_RECIPE,
        "nutrition_advice": NutritionAdvicePrompts.GENERAL_NUTRITION_ADVICE,
        "food_log_analysis": NutritionAdvicePrompts.ANALYZE_FOOD_LOG,
        "meal_timing": NutritionAdvicePrompts.MEAL_TIMING_ADVICE,
        "friendly_chat": ConversationPrompts.FRIENDLY_RESPONSE,
        "goal_setting": ConversationPrompts.GOAL_SETTING_CONVERSATION,
        "onboarding": ConversationPrompts.ONBOARDING_CONVERSATION,
        "grocery_optimization": GroceryListPrompts.OPTIMIZE_GROCERY_LIST,
        "seasonal_substitutions": GroceryListPrompts.SEASONAL_SUBSTITUTIONS,
    }
    
    template = prompt_map.get(intent)
    if not template:
        raise ValueError(f"No prompt template found for intent: {intent}")
    
    return template.format(**kwargs)
