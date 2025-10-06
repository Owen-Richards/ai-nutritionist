"""
Meal Planning and Recipe Management System
Handles recipe storage, meal plan generation, family meal coordination
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import random


class MealType(Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"
    BRUNCH = "brunch"


class DifficultyLevel(Enum):
    BEGINNER = "beginner"        # 15-30 minutes
    INTERMEDIATE = "intermediate" # 30-60 minutes
    ADVANCED = "advanced"        # 60+ minutes
    EXPERT = "expert"           # Complex techniques


class CookingMethod(Enum):
    BAKING = "baking"
    GRILLING = "grilling"
    STOVETOP = "stovetop"
    SLOW_COOKER = "slow_cooker"
    INSTANT_POT = "instant_pot"
    AIR_FRYER = "air_fryer"
    MICROWAVE = "microwave"
    NO_COOK = "no_cook"
    OVEN = "oven"
    STEAMING = "steaming"


@dataclass
class Ingredient:
    name: str
    quantity: float
    unit: str
    preparation: Optional[str] = None  # "diced", "chopped", "minced"
    optional: bool = False
    substitutions: List[str] = None
    
    def __post_init__(self):
        if self.substitutions is None:
            self.substitutions = []


@dataclass
class NutritionFacts:
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    cholesterol_mg: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    vitamins: Dict[str, float] = None
    minerals: Dict[str, float] = None
    
    def __post_init__(self):
        if self.vitamins is None:
            self.vitamins = {}
        if self.minerals is None:
            self.minerals = {}


@dataclass
class Recipe:
    name: str
    description: str
    ingredients: List[Ingredient]
    instructions: List[str]
    servings: int
    prep_time_minutes: int
    cook_time_minutes: int
    difficulty: DifficultyLevel
    meal_types: List[MealType]
    cooking_methods: List[CookingMethod]
    cuisine_type: Optional[str] = None
    tags: List[str] = None
    nutrition_facts: Optional[NutritionFacts] = None
    recipe_id: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: int = 0
    dietary_restrictions: List[str] = None  # vegetarian, vegan, gluten-free, etc.
    allergens: List[str] = None
    equipment_needed: List[str] = None
    cost_per_serving: Optional[float] = None
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dietary_restrictions is None:
            self.dietary_restrictions = []
        if self.allergens is None:
            self.allergens = []
        if self.equipment_needed is None:
            self.equipment_needed = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_modified is None:
            self.last_modified = datetime.utcnow()
    
    @property
    def total_time_minutes(self) -> int:
        return self.prep_time_minutes + self.cook_time_minutes
    
    def is_quick_meal(self) -> bool:
        """Check if recipe is quick (under 30 minutes)"""
        return self.total_time_minutes <= 30
    
    def matches_dietary_restrictions(self, restrictions: List[str]) -> bool:
        """Check if recipe matches dietary restrictions"""
        if not restrictions:
            return True
        return all(restriction in self.dietary_restrictions for restriction in restrictions)
    
    def has_allergens(self, allergens: List[str]) -> bool:
        """Check if recipe contains allergens"""
        if not allergens:
            return False
        return any(allergen in self.allergens for allergen in allergens)


@dataclass
class MealPlanEntry:
    date: date
    meal_type: MealType
    recipe: Recipe
    servings_planned: int
    assigned_to: Optional[str] = None  # family member
    notes: Optional[str] = None
    prepared: bool = False
    rating: Optional[int] = None  # 1-5 stars after eating
    
    def scale_recipe(self) -> Recipe:
        """Scale recipe for planned servings"""
        if self.servings_planned == self.recipe.servings:
            return self.recipe
        
        scale_factor = self.servings_planned / self.recipe.servings
        
        # Scale ingredients
        scaled_ingredients = []
        for ingredient in self.recipe.ingredients:
            scaled_ingredient = Ingredient(
                name=ingredient.name,
                quantity=ingredient.quantity * scale_factor,
                unit=ingredient.unit,
                preparation=ingredient.preparation,
                optional=ingredient.optional,
                substitutions=ingredient.substitutions.copy()
            )
            scaled_ingredients.append(scaled_ingredient)
        
        # Create scaled recipe
        scaled_recipe = Recipe(
            name=f"{self.recipe.name} (scaled for {self.servings_planned})",
            description=self.recipe.description,
            ingredients=scaled_ingredients,
            instructions=self.recipe.instructions.copy(),
            servings=self.servings_planned,
            prep_time_minutes=self.recipe.prep_time_minutes,
            cook_time_minutes=self.recipe.cook_time_minutes,
            difficulty=self.recipe.difficulty,
            meal_types=self.recipe.meal_types.copy(),
            cooking_methods=self.recipe.cooking_methods.copy(),
            cuisine_type=self.recipe.cuisine_type,
            tags=self.recipe.tags.copy(),
            nutrition_facts=self.recipe.nutrition_facts,
            recipe_id=self.recipe.recipe_id,
            source=self.recipe.source,
            source_url=self.recipe.source_url,
            image_url=self.recipe.image_url,
            rating=self.recipe.rating,
            review_count=self.recipe.review_count,
            dietary_restrictions=self.recipe.dietary_restrictions.copy(),
            allergens=self.recipe.allergens.copy(),
            equipment_needed=self.recipe.equipment_needed.copy(),
            cost_per_serving=self.recipe.cost_per_serving
        )
        
        return scaled_recipe


class MealPlanGenerator:
    """Generates personalized meal plans"""
    
    def __init__(self, recipes: List[Recipe]):
        self.recipes = recipes
    
    def generate_weekly_plan(self, 
                           preferences: Dict[str, Any],
                           family_size: int = 1,
                           start_date: date = None,
                           budget_per_week: float = None) -> List[MealPlanEntry]:
        """Generate a weekly meal plan"""
        if start_date is None:
            start_date = date.today()
        
        plan = []
        
        # Get dietary restrictions and preferences
        dietary_restrictions = preferences.get("dietary_restrictions", [])
        allergens = preferences.get("allergens", [])
        disliked_foods = preferences.get("disliked_foods", [])
        preferred_cuisines = preferences.get("preferred_cuisines", [])
        cooking_skill = preferences.get("cooking_skill", "intermediate")
        max_cook_time = preferences.get("max_cook_time", 60)
        
        # Filter recipes based on preferences
        suitable_recipes = self._filter_recipes(
            dietary_restrictions=dietary_restrictions,
            allergens=allergens,
            disliked_foods=disliked_foods,
            preferred_cuisines=preferred_cuisines,
            max_cook_time=max_cook_time,
            cooking_skill=cooking_skill
        )
        
        if not suitable_recipes:
            raise ValueError("No suitable recipes found for the given preferences")
        
        # Generate meals for 7 days
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            
            # Plan each meal type
            for meal_type in [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER]:
                meal_recipes = [r for r in suitable_recipes if meal_type in r.meal_types]
                
                if meal_recipes:
                    # Select recipe based on day patterns and variety
                    selected_recipe = self._select_recipe_for_meal(
                        meal_recipes, current_date, meal_type, plan, preferences
                    )
                    
                    if selected_recipe:
                        meal_entry = MealPlanEntry(
                            date=current_date,
                            meal_type=meal_type,
                            recipe=selected_recipe,
                            servings_planned=family_size
                        )
                        plan.append(meal_entry)
        
        # Optimize for budget if specified
        if budget_per_week:
            plan = self._optimize_for_budget(plan, budget_per_week)
        
        return plan
    
    def _filter_recipes(self, 
                       dietary_restrictions: List[str] = None,
                       allergens: List[str] = None,
                       disliked_foods: List[str] = None,
                       preferred_cuisines: List[str] = None,
                       max_cook_time: int = None,
                       cooking_skill: str = None) -> List[Recipe]:
        """Filter recipes based on preferences"""
        filtered = []
        
        for recipe in self.recipes:
            # Check dietary restrictions
            if dietary_restrictions and not recipe.matches_dietary_restrictions(dietary_restrictions):
                continue
            
            # Check allergens
            if allergens and recipe.has_allergens(allergens):
                continue
            
            # Check disliked foods
            if disliked_foods:
                has_disliked = False
                for disliked in disliked_foods:
                    if any(disliked.lower() in ingredient.name.lower() 
                          for ingredient in recipe.ingredients):
                        has_disliked = True
                        break
                if has_disliked:
                    continue
            
            # Check cooking time
            if max_cook_time and recipe.total_time_minutes > max_cook_time:
                continue
            
            # Check cooking skill
            if cooking_skill:
                skill_levels = {
                    "beginner": [DifficultyLevel.BEGINNER],
                    "intermediate": [DifficultyLevel.BEGINNER, DifficultyLevel.INTERMEDIATE],
                    "advanced": [DifficultyLevel.BEGINNER, DifficultyLevel.INTERMEDIATE, DifficultyLevel.ADVANCED],
                    "expert": list(DifficultyLevel)
                }
                if recipe.difficulty not in skill_levels.get(cooking_skill, list(DifficultyLevel)):
                    continue
            
            # Check preferred cuisines (if specified, prefer but don't exclude)
            filtered.append(recipe)
        
        # Sort by preferred cuisines if specified
        if preferred_cuisines:
            def cuisine_score(recipe):
                if recipe.cuisine_type and recipe.cuisine_type.lower() in [c.lower() for c in preferred_cuisines]:
                    return 1
                return 0
            
            filtered.sort(key=cuisine_score, reverse=True)
        
        return filtered
    
    def _select_recipe_for_meal(self, 
                               available_recipes: List[Recipe],
                               date: date,
                               meal_type: MealType,
                               existing_plan: List[MealPlanEntry],
                               preferences: Dict[str, Any]) -> Optional[Recipe]:
        """Select the best recipe for a specific meal"""
        if not available_recipes:
            return None
        
        # Get recently used recipes to avoid repetition
        recent_recipes = set()
        for entry in existing_plan[-14:]:  # Last 2 weeks
            recent_recipes.add(entry.recipe.recipe_id or entry.recipe.name)
        
        # Filter out recently used recipes if possible
        fresh_recipes = [r for r in available_recipes 
                        if (r.recipe_id or r.name) not in recent_recipes]
        
        candidates = fresh_recipes if fresh_recipes else available_recipes
        
        # Apply meal-specific logic
        if meal_type == MealType.BREAKFAST:
            # Prefer quick breakfast options on weekdays
            if date.weekday() < 5:  # Monday-Friday
                quick_recipes = [r for r in candidates if r.is_quick_meal()]
                candidates = quick_recipes if quick_recipes else candidates
        
        elif meal_type == MealType.DINNER:
            # Prefer more elaborate dinners on weekends
            if date.weekday() >= 5:  # Saturday-Sunday
                elaborate_recipes = [r for r in candidates if not r.is_quick_meal()]
                candidates = elaborate_recipes if elaborate_recipes else candidates
        
        # Select based on rating and variety
        candidates.sort(key=lambda r: (r.rating or 0, random.random()), reverse=True)
        
        return candidates[0] if candidates else None
    
    def _optimize_for_budget(self, 
                            plan: List[MealPlanEntry], 
                            budget: float) -> List[MealPlanEntry]:
        """Optimize meal plan for budget constraints"""
        total_cost = sum(
            (entry.recipe.cost_per_serving or 5.0) * entry.servings_planned 
            for entry in plan
        )
        
        if total_cost <= budget:
            return plan
        
        # Replace expensive meals with cheaper alternatives
        plan.sort(key=lambda e: (e.recipe.cost_per_serving or 5.0) * e.servings_planned, reverse=True)
        
        optimized_plan = []
        remaining_budget = budget
        
        for entry in plan:
            meal_cost = (entry.recipe.cost_per_serving or 5.0) * entry.servings_planned
            
            if meal_cost <= remaining_budget:
                optimized_plan.append(entry)
                remaining_budget -= meal_cost
            else:
                # Find cheaper alternative
                cheaper_alternatives = [
                    r for r in self.recipes 
                    if (entry.meal_type in r.meal_types and 
                        (r.cost_per_serving or 5.0) * entry.servings_planned <= remaining_budget)
                ]
                
                if cheaper_alternatives:
                    cheaper_recipe = min(cheaper_alternatives, 
                                       key=lambda r: r.cost_per_serving or 5.0)
                    cheaper_entry = MealPlanEntry(
                        date=entry.date,
                        meal_type=entry.meal_type,
                        recipe=cheaper_recipe,
                        servings_planned=entry.servings_planned
                    )
                    optimized_plan.append(cheaper_entry)
                    remaining_budget -= (cheaper_recipe.cost_per_serving or 5.0) * entry.servings_planned
        
        return optimized_plan


class MealPlanManager:
    """Manages meal plans for a user/family"""
    
    def __init__(self, user_phone: str):
        self.user_phone = user_phone
        self.recipes: Dict[str, Recipe] = {}
        self.meal_plans: Dict[str, List[MealPlanEntry]] = {}  # week_id -> plan
        self.favorites: List[str] = []  # recipe IDs
        self.cooking_history: List[Dict[str, Any]] = []
        self.meal_plan_generator = MealPlanGenerator([])
        self.last_updated = datetime.utcnow()
    
    def add_recipe(self, recipe: Recipe) -> str:
        """Add recipe to collection"""
        if not recipe.recipe_id:
            recipe.recipe_id = f"recipe_{len(self.recipes)}_{datetime.utcnow().timestamp()}"
        
        self.recipes[recipe.recipe_id] = recipe
        self.meal_plan_generator.recipes = list(self.recipes.values())
        self.last_updated = datetime.utcnow()
        
        return recipe.recipe_id
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Get recipe by ID"""
        return self.recipes.get(recipe_id)
    
    def search_recipes(self, 
                      query: str = None,
                      meal_type: MealType = None,
                      max_time: int = None,
                      dietary_restrictions: List[str] = None) -> List[Recipe]:
        """Search recipes"""
        results = list(self.recipes.values())
        
        if query:
            query_lower = query.lower()
            results = [
                r for r in results 
                if (query_lower in r.name.lower() or 
                    query_lower in r.description.lower() or
                    any(query_lower in tag.lower() for tag in r.tags))
            ]
        
        if meal_type:
            results = [r for r in results if meal_type in r.meal_types]
        
        if max_time:
            results = [r for r in results if r.total_time_minutes <= max_time]
        
        if dietary_restrictions:
            results = [r for r in results if r.matches_dietary_restrictions(dietary_restrictions)]
        
        # Sort by rating
        results.sort(key=lambda r: r.rating or 0, reverse=True)
        
        return results
    
    def create_meal_plan(self, 
                        start_date: date,
                        preferences: Dict[str, Any],
                        family_size: int = 1,
                        budget: float = None) -> str:
        """Create a new meal plan"""
        week_id = f"week_{start_date.strftime('%Y_%m_%d')}"
        
        meal_plan = self.meal_plan_generator.generate_weekly_plan(
            preferences=preferences,
            family_size=family_size,
            start_date=start_date,
            budget_per_week=budget
        )
        
        self.meal_plans[week_id] = meal_plan
        self.last_updated = datetime.utcnow()
        
        return week_id
    
    def get_meal_plan(self, week_id: str) -> List[MealPlanEntry]:
        """Get meal plan by week ID"""
        return self.meal_plans.get(week_id, [])
    
    def get_current_week_plan(self) -> List[MealPlanEntry]:
        """Get current week's meal plan"""
        today = date.today()
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        week_id = f"week_{monday.strftime('%Y_%m_%d')}"
        return self.get_meal_plan(week_id)
    
    def mark_meal_prepared(self, week_id: str, date: date, meal_type: MealType) -> bool:
        """Mark a meal as prepared"""
        meal_plan = self.meal_plans.get(week_id, [])
        
        for entry in meal_plan:
            if entry.date == date and entry.meal_type == meal_type:
                entry.prepared = True
                self.last_updated = datetime.utcnow()
                return True
        
        return False
    
    def rate_meal(self, week_id: str, date: date, meal_type: MealType, rating: int) -> bool:
        """Rate a meal (1-5 stars)"""
        if not 1 <= rating <= 5:
            return False
        
        meal_plan = self.meal_plans.get(week_id, [])
        
        for entry in meal_plan:
            if entry.date == date and entry.meal_type == meal_type:
                entry.rating = rating
                
                # Update recipe rating
                recipe = entry.recipe
                if recipe.rating is None:
                    recipe.rating = rating
                    recipe.review_count = 1
                else:
                    total_rating = recipe.rating * recipe.review_count + rating
                    recipe.review_count += 1
                    recipe.rating = total_rating / recipe.review_count
                
                self.last_updated = datetime.utcnow()
                return True
        
        return False
    
    def add_to_favorites(self, recipe_id: str) -> bool:
        """Add recipe to favorites"""
        if recipe_id in self.recipes and recipe_id not in self.favorites:
            self.favorites.append(recipe_id)
            self.last_updated = datetime.utcnow()
            return True
        return False
    
    def remove_from_favorites(self, recipe_id: str) -> bool:
        """Remove recipe from favorites"""
        if recipe_id in self.favorites:
            self.favorites.remove(recipe_id)
            self.last_updated = datetime.utcnow()
            return True
        return False
    
    def get_favorite_recipes(self) -> List[Recipe]:
        """Get favorite recipes"""
        return [self.recipes[recipe_id] for recipe_id in self.favorites 
                if recipe_id in self.recipes]
    
    def get_meal_plan_summary(self, week_id: str) -> Dict[str, Any]:
        """Get meal plan summary"""
        meal_plan = self.meal_plans.get(week_id, [])
        
        if not meal_plan:
            return {}
        
        total_meals = len(meal_plan)
        prepared_meals = sum(1 for entry in meal_plan if entry.prepared)
        total_cost = sum(
            (entry.recipe.cost_per_serving or 5.0) * entry.servings_planned 
            for entry in meal_plan
        )
        
        # Nutrition summary
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        
        for entry in meal_plan:
            nutrition = entry.recipe.nutrition_facts
            if nutrition:
                servings = entry.servings_planned
                total_calories += (nutrition.calories or 0) * servings
                total_protein += (nutrition.protein_g or 0) * servings
                total_carbs += (nutrition.carbohydrates_g or 0) * servings
                total_fat += (nutrition.fat_g or 0) * servings
        
        return {
            "week_id": week_id,
            "total_meals": total_meals,
            "prepared_meals": prepared_meals,
            "completion_rate": prepared_meals / total_meals if total_meals > 0 else 0,
            "total_cost": round(total_cost, 2),
            "average_cost_per_meal": round(total_cost / total_meals, 2) if total_meals > 0 else 0,
            "total_calories": round(total_calories),
            "total_protein_g": round(total_protein, 1),
            "total_carbs_g": round(total_carbs, 1),
            "total_fat_g": round(total_fat, 1),
            "start_date": min(entry.date for entry in meal_plan).isoformat() if meal_plan else None,
            "end_date": max(entry.date for entry in meal_plan).isoformat() if meal_plan else None
        }
    
    def get_shopping_list_for_plan(self, week_id: str) -> List[Ingredient]:
        """Get shopping list for a meal plan"""
        meal_plan = self.meal_plans.get(week_id, [])
        
        shopping_list = {}
        
        for entry in meal_plan:
            if not entry.prepared:  # Only include unprepared meals
                scaled_recipe = entry.scale_recipe()
                
                for ingredient in scaled_recipe.ingredients:
                    key = f"{ingredient.name}_{ingredient.unit}"
                    
                    if key in shopping_list:
                        shopping_list[key].quantity += ingredient.quantity
                    else:
                        shopping_list[key] = Ingredient(
                            name=ingredient.name,
                            quantity=ingredient.quantity,
                            unit=ingredient.unit,
                            preparation=ingredient.preparation,
                            optional=ingredient.optional,
                            substitutions=ingredient.substitutions.copy()
                        )
        
        return list(shopping_list.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "user_phone": self.user_phone,
            "recipes": {key: asdict(recipe) for key, recipe in self.recipes.items()},
            "meal_plans": {
                week_id: [asdict(entry) for entry in plan] 
                for week_id, plan in self.meal_plans.items()
            },
            "favorites": self.favorites,
            "cooking_history": self.cooking_history,
            "last_updated": self.last_updated.isoformat()
        }
