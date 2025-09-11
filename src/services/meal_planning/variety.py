"""
Multi-Goal Meal Plan Generator

Generates personalized meal plans that satisfy multiple user goals with
intelligent constraint merging and trade-off explanations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import random
from datetime import datetime, timedelta

from .constraints import MultiGoalService, MergedConstraints, GoalType

logger = logging.getLogger(__name__)


@dataclass
class MealPlanResult:
    """Result of meal plan generation with explanation"""
    meals: List[Dict[str, Any]]
    constraints_met: Dict[str, bool]
    trade_offs: List[str]
    cost_breakdown: Dict[str, float]
    nutrition_summary: Dict[str, float]
    goal_satisfaction: Dict[str, float]
    success: bool = True
    message: str = ""


class MultiGoalMealPlanGenerator:
    """Enhanced meal plan generator supporting multiple goals"""
    
    def __init__(self, ai_service, multi_goal_service: MultiGoalService):
        self.ai_service = ai_service
        self.multi_goal_service = multi_goal_service
        
        # Enhanced recipe database with goal-specific tagging
        self.recipe_database = {
            "budget_protein_bowl": {
                "name": "Lentil & Egg Power Bowl",
                "cost_per_serving": 2.50,
                "prep_time": 15,
                "nutrition": {"calories": 380, "protein": 22, "fiber": 12, "sodium": 450},
                "tags": ["budget", "protein", "quick", "vegetarian"],
                "goal_compatibility": {
                    GoalType.BUDGET.value: 0.9,
                    GoalType.MUSCLE_GAIN.value: 0.7,
                    GoalType.QUICK_MEALS.value: 0.8
                },
                "ingredients": ["lentils", "eggs", "spinach", "brown_rice"],
                "anti_inflammatory_score": 0.6
            },
            "premium_salmon": {
                "name": "Miso-Glazed Salmon with Vegetables",
                "cost_per_serving": 8.50,
                "prep_time": 25,
                "nutrition": {"calories": 420, "protein": 35, "fiber": 8, "sodium": 680},
                "tags": ["premium", "omega3", "anti_inflammatory"],
                "goal_compatibility": {
                    GoalType.MUSCLE_GAIN.value: 0.9,
                    GoalType.HEART_HEALTH.value: 0.95,
                    GoalType.BUDGET.value: 0.2
                },
                "ingredients": ["salmon", "miso", "broccoli", "brown_rice"],
                "anti_inflammatory_score": 0.9
            },
            "budget_muscle_meal": {
                "name": "Chicken Thigh & Bean Skillet",
                "cost_per_serving": 3.25,
                "prep_time": 20,
                "nutrition": {"calories": 450, "protein": 32, "fiber": 10, "sodium": 520},
                "tags": ["budget", "protein", "one_pot"],
                "goal_compatibility": {
                    GoalType.BUDGET.value: 0.8,
                    GoalType.MUSCLE_GAIN.value: 0.85,
                    GoalType.QUICK_MEALS.value: 0.7
                },
                "ingredients": ["chicken_thighs", "black_beans", "bell_peppers"],
                "anti_inflammatory_score": 0.5
            },
            "gut_health_bowl": {
                "name": "Fermented Veggie & Quinoa Bowl",
                "cost_per_serving": 4.75,
                "prep_time": 10,
                "nutrition": {"calories": 340, "protein": 14, "fiber": 18, "sodium": 380},
                "tags": ["gut_health", "fermented", "fiber", "plant_based"],
                "goal_compatibility": {
                    GoalType.GUT_HEALTH.value: 0.95,
                    GoalType.PLANT_FORWARD.value: 0.9,
                    GoalType.QUICK_MEALS.value: 0.9
                },
                "ingredients": ["quinoa", "sauerkraut", "kimchi", "avocado"],
                "anti_inflammatory_score": 0.8
            },
            "energy_stabilizer": {
                "name": "Balanced Power Breakfast",
                "cost_per_serving": 3.50,
                "prep_time": 8,
                "nutrition": {"calories": 320, "protein": 18, "fiber": 8, "sodium": 200},
                "tags": ["breakfast", "balanced", "quick", "energy"],
                "goal_compatibility": {
                    GoalType.ENERGY.value: 0.9,
                    GoalType.QUICK_MEALS.value: 0.95,
                    GoalType.BUDGET.value: 0.7
                },
                "ingredients": ["oats", "Greek_yogurt", "berries", "almond_butter"],
                "anti_inflammatory_score": 0.7
            },
            "family_friendly": {
                "name": "Hidden Veggie Mac & Cheese",
                "cost_per_serving": 2.75,
                "prep_time": 25,
                "nutrition": {"calories": 380, "protein": 16, "fiber": 6, "sodium": 580},
                "tags": ["family", "comfort", "hidden_veggies"],
                "goal_compatibility": {
                    GoalType.FAMILY_FRIENDLY.value: 0.9,
                    GoalType.BUDGET.value: 0.8,
                    GoalType.QUICK_MEALS.value: 0.6
                },
                "ingredients": ["whole_wheat_pasta", "cheese", "cauliflower", "milk"],
                "anti_inflammatory_score": 0.4
            }
        }
        
        # Food cost database (per serving estimates)
        self.ingredient_costs = {
            "lentils": 0.30, "eggs": 0.50, "chicken_thighs": 1.50, "salmon": 4.50,
            "quinoa": 0.75, "brown_rice": 0.25, "oats": 0.20, "Greek_yogurt": 1.00,
            "vegetables_mix": 1.00, "beans": 0.40, "cheese": 0.80
        }
    
    def generate_multi_goal_plan(self, user_id: str, days: int = 3) -> MealPlanResult:
        """Generate meal plan satisfying multiple user goals"""
        try:
            # Get merged constraints for the user
            constraints = self.multi_goal_service.merge_goal_constraints(user_id)
            
            # Get user goals for context
            user_profile = self.multi_goal_service.user_service.get_user_profile(user_id)
            goals = user_profile.get('goals', []) if user_profile else []
            
            if not goals:
                return self._generate_default_plan(days)
            
            # Score all recipes against merged constraints
            recipe_scores = self._score_recipes_for_constraints(constraints, goals)
            
            # Select optimal recipe combination
            selected_meals = self._select_optimal_meals(recipe_scores, constraints, days)
            
            # Analyze constraints satisfaction
            constraints_analysis = self._analyze_constraint_satisfaction(selected_meals, constraints)
            
            # Identify trade-offs and generate explanations
            trade_offs = self._identify_trade_offs(selected_meals, goals, constraints)
            
            # Calculate goal satisfaction scores
            goal_satisfaction = self._calculate_goal_satisfaction(selected_meals, goals)
            
            # Generate meal plan with rich metadata
            meal_plan = self._format_meal_plan(selected_meals, constraints_analysis, trade_offs)
            
            return MealPlanResult(
                meals=meal_plan,
                constraints_met=constraints_analysis['constraints_met'],
                trade_offs=trade_offs,
                cost_breakdown=constraints_analysis['cost_breakdown'],
                nutrition_summary=constraints_analysis['nutrition_summary'],
                goal_satisfaction=goal_satisfaction,
                success=True,
                message=self._generate_plan_explanation(goals, trade_offs)
            )
            
        except Exception as e:
            logger.error(f"Error generating multi-goal meal plan for user {user_id}: {str(e)}")
            return MealPlanResult(
                meals=[],
                constraints_met={},
                trade_offs=[],
                cost_breakdown={},
                nutrition_summary={},
                goal_satisfaction={},
                success=False,
                message="Failed to generate meal plan"
            )
    
    def _score_recipes_for_constraints(self, constraints: MergedConstraints, goals: List[Dict]) -> Dict[str, float]:
        """Score each recipe against the merged constraints"""
        recipe_scores = {}
        
        for recipe_id, recipe in self.recipe_database.items():
            score = 0.0
            factors = 0
            
            # Cost scoring
            if constraints.max_cost_per_meal:
                cost_score = min(1.0, constraints.max_cost_per_meal / recipe['cost_per_serving'])
                score += cost_score
                factors += 1
            
            # Time scoring
            if constraints.max_prep_time:
                time_score = min(1.0, constraints.max_prep_time / recipe['prep_time'])
                score += time_score
                factors += 1
            
            # Nutrition scoring
            if constraints.protein_grams:
                protein_ratio = recipe['nutrition']['protein'] / (constraints.protein_grams / 3)  # Assume 3 meals/day
                protein_score = min(1.0, protein_ratio)
                score += protein_score
                factors += 1
            
            # Goal compatibility scoring
            for goal in goals:
                goal_type = goal['goal_type']
                priority_weight = goal['priority'] / 4.0
                
                if goal_type in recipe['goal_compatibility']:
                    compatibility = recipe['goal_compatibility'][goal_type]
                    weighted_compatibility = compatibility * priority_weight
                    score += weighted_compatibility
                    factors += priority_weight
            
            # Emphasized foods bonus
            if constraints.emphasized_foods:
                ingredient_matches = sum(1 for ingredient in recipe['ingredients'] 
                                       if any(emp_food in ingredient for emp_food in constraints.emphasized_foods))
                emphasis_score = min(1.0, ingredient_matches / len(constraints.emphasized_foods))
                score += emphasis_score
                factors += 1
            
            # Anti-inflammatory scoring
            if constraints.anti_inflammatory_focus:
                score += recipe['anti_inflammatory_score']
                factors += 1
            
            # Normalize score
            recipe_scores[recipe_id] = score / max(factors, 1)
        
        return recipe_scores
    
    def _select_optimal_meals(self, recipe_scores: Dict[str, float], constraints: MergedConstraints, days: int) -> List[Dict[str, Any]]:
        """Select optimal combination of meals for the plan"""
        # Sort recipes by score
        sorted_recipes = sorted(recipe_scores.items(), key=lambda x: x[1], reverse=True)
        
        selected_meals = []
        total_cost = 0.0
        total_nutrition = {"calories": 0, "protein": 0, "fiber": 0, "sodium": 0}
        
        meals_per_day = 3
        total_meals_needed = days * meals_per_day
        
        # Select top recipes, ensuring variety and constraints
        used_recipes = set()
        
        for _ in range(total_meals_needed):
            best_recipe = None
            best_score = -1
            
            for recipe_id, score in sorted_recipes:
                # Skip if we've used this recipe too much
                if used_recipes.count(recipe_id) >= max(1, days // 2):
                    continue
                
                recipe = self.recipe_database[recipe_id]
                
                # Check budget constraint
                if constraints.max_cost_per_meal and recipe['cost_per_serving'] > constraints.max_cost_per_meal:
                    continue
                
                # Check time constraint
                if constraints.max_prep_time and recipe['prep_time'] > constraints.max_prep_time:
                    continue
                
                if score > best_score:
                    best_score = score
                    best_recipe = recipe_id
            
            # Add the best recipe
            if best_recipe:
                recipe = self.recipe_database[best_recipe]
                selected_meals.append({
                    "recipe_id": best_recipe,
                    "recipe": recipe,
                    "score": best_score
                })
                used_recipes.add(best_recipe)
                
                # Update totals
                total_cost += recipe['cost_per_serving']
                for nutrient in total_nutrition:
                    total_nutrition[nutrient] += recipe['nutrition'].get(nutrient, 0)
            else:
                # Fallback to any available recipe
                fallback_recipe = sorted_recipes[0][0]
                recipe = self.recipe_database[fallback_recipe]
                selected_meals.append({
                    "recipe_id": fallback_recipe,
                    "recipe": recipe,
                    "score": 0.5
                })
        
        return selected_meals
    
    def _analyze_constraint_satisfaction(self, selected_meals: List[Dict], constraints: MergedConstraints) -> Dict[str, Any]:
        """Analyze how well the selected meals satisfy constraints"""
        total_cost = sum(meal['recipe']['cost_per_serving'] for meal in selected_meals)
        avg_cost_per_meal = total_cost / len(selected_meals)
        
        total_nutrition = {"calories": 0, "protein": 0, "fiber": 0, "sodium": 0}
        for meal in selected_meals:
            for nutrient in total_nutrition:
                total_nutrition[nutrient] += meal['recipe']['nutrition'].get(nutrient, 0)
        
        daily_nutrition = {k: v / (len(selected_meals) / 3) for k, v in total_nutrition.items()}
        
        constraints_met = {}
        
        # Check cost constraint
        if constraints.max_cost_per_meal:
            constraints_met['cost'] = avg_cost_per_meal <= constraints.max_cost_per_meal
        
        # Check nutrition constraints
        if constraints.daily_calories:
            constraints_met['calories'] = abs(daily_nutrition['calories'] - constraints.daily_calories) <= constraints.daily_calories * 0.1
        
        if constraints.protein_grams:
            constraints_met['protein'] = daily_nutrition['protein'] >= constraints.protein_grams * 0.8
        
        if constraints.fiber_grams:
            constraints_met['fiber'] = daily_nutrition['fiber'] >= constraints.fiber_grams * 0.8
        
        if constraints.sodium_mg:
            constraints_met['sodium'] = daily_nutrition['sodium'] <= constraints.sodium_mg
        
        return {
            'constraints_met': constraints_met,
            'cost_breakdown': {
                'total_cost': total_cost,
                'avg_cost_per_meal': avg_cost_per_meal,
                'daily_cost': total_cost / (len(selected_meals) / 3)
            },
            'nutrition_summary': daily_nutrition
        }
    
    def _identify_trade_offs(self, selected_meals: List[Dict], goals: List[Dict], constraints: MergedConstraints) -> List[str]:
        """Identify and explain trade-offs made in meal selection"""
        trade_offs = []
        
        # Analyze goal conflicts
        goal_types = [goal['goal_type'] for goal in goals]
        
        # Budget vs. Premium ingredients
        if GoalType.BUDGET.value in goal_types and GoalType.MUSCLE_GAIN.value in goal_types:
            avg_cost = sum(meal['recipe']['cost_per_serving'] for meal in selected_meals) / len(selected_meals)
            if avg_cost < 4.0:
                trade_offs.append("Budget focus may limit premium protein sources, but I've maximized affordable high-protein options like chicken thighs and lentils")
        
        # Quick meals vs. Nutrition optimization
        if GoalType.QUICK_MEALS.value in goal_types:
            complex_meals = [meal for meal in selected_meals if meal['recipe']['prep_time'] > 20]
            if complex_meals:
                trade_offs.append(f"Quick meal preference limits some nutrient-dense options, but {len(complex_meals)} recipes can be meal-prepped")
        
        # Multiple goals general trade-off
        if len(goals) > 2:
            trade_offs.append("With multiple goals, some recipes may be good-but-not-perfect for each individual goal, but optimal for your overall needs")
        
        # Constraint satisfaction trade-offs
        analysis = self._analyze_constraint_satisfaction(selected_meals, constraints)
        
        if constraints.max_cost_per_meal and analysis['cost_breakdown']['avg_cost_per_meal'] > constraints.max_cost_per_meal * 0.9:
            trade_offs.append("Staying within budget while meeting nutrition goals required choosing some lower-cost ingredients")
        
        return trade_offs
    
    def _calculate_goal_satisfaction(self, selected_meals: List[Dict], goals: List[Dict]) -> Dict[str, float]:
        """Calculate how well the meal plan satisfies each individual goal"""
        goal_satisfaction = {}
        
        for goal in goals:
            goal_type = goal['goal_type']
            satisfaction_score = 0.0
            
            # Calculate average compatibility score for this goal
            for meal in selected_meals:
                recipe = meal['recipe']
                if goal_type in recipe['goal_compatibility']:
                    satisfaction_score += recipe['goal_compatibility'][goal_type]
            
            # Normalize by number of meals
            if selected_meals:
                satisfaction_score /= len(selected_meals)
            
            # Store with goal identifier
            if goal_type == GoalType.CUSTOM.value:
                goal_key = f"custom_{goal.get('label', 'unknown')}"
            else:
                goal_key = goal_type
            
            goal_satisfaction[goal_key] = satisfaction_score
        
        return goal_satisfaction
    
    def _format_meal_plan(self, selected_meals: List[Dict], constraints_analysis: Dict, trade_offs: List[str]) -> List[Dict[str, Any]]:
        """Format the meal plan with rich metadata"""
        formatted_meals = []
        
        for i, meal_data in enumerate(selected_meals):
            recipe = meal_data['recipe']
            
            formatted_meal = {
                "meal_number": i + 1,
                "day": (i // 3) + 1,
                "meal_type": ["breakfast", "lunch", "dinner"][i % 3],
                "name": recipe['name'],
                "recipe_id": meal_data['recipe_id'],
                "cost_per_serving": recipe['cost_per_serving'],
                "prep_time": recipe['prep_time'],
                "nutrition": recipe['nutrition'],
                "ingredients": recipe['ingredients'],
                "tags": recipe['tags'],
                "goal_score": meal_data['score'],
                "anti_inflammatory_score": recipe['anti_inflammatory_score']
            }
            
            formatted_meals.append(formatted_meal)
        
        return formatted_meals
    
    def _generate_plan_explanation(self, goals: List[Dict], trade_offs: List[str]) -> str:
        """Generate human-readable explanation of the meal plan"""
        if not goals:
            return "Generated a balanced meal plan for general nutrition."
        
        # Summarize goals
        goal_names = []
        for goal in goals:
            if goal['goal_type'] == GoalType.CUSTOM.value:
                goal_names.append(goal.get('label', 'custom goal'))
            else:
                goal_def = self.multi_goal_service.goal_definitions.get(goal['goal_type'], {})
                goal_names.append(goal_def.get('name', goal['goal_type']).lower())
        
        if len(goal_names) == 1:
            explanation = f"Optimized meal plan for {goal_names[0]}."
        elif len(goal_names) == 2:
            explanation = f"Balanced meal plan combining {goal_names[0]} and {goal_names[1]}."
        else:
            formatted_goals = ", ".join(goal_names[:-1]) + f", and {goal_names[-1]}"
            explanation = f"Multi-goal meal plan balancing {formatted_goals}."
        
        # Add trade-off explanations
        if trade_offs:
            explanation += " " + " ".join(trade_offs)
        
        return explanation
    
    def _generate_default_plan(self, days: int) -> MealPlanResult:
        """Generate a default meal plan when no goals are specified"""
        # Select a balanced variety of meals
        default_recipes = ["energy_stabilizer", "budget_muscle_meal", "gut_health_bowl"]
        
        selected_meals = []
        for i in range(days * 3):
            recipe_id = default_recipes[i % len(default_recipes)]
            recipe = self.recipe_database[recipe_id]
            selected_meals.append({
                "recipe_id": recipe_id,
                "recipe": recipe,
                "score": 0.8
            })
        
        formatted_meals = self._format_meal_plan(selected_meals, {}, [])
        
        return MealPlanResult(
            meals=formatted_meals,
            constraints_met={},
            trade_offs=[],
            cost_breakdown={"total_cost": sum(meal['cost_per_serving'] for meal in formatted_meals)},
            nutrition_summary={},
            goal_satisfaction={},
            success=True,
            message="Generated balanced meal plan. Add goals to personalize further!"
        )
