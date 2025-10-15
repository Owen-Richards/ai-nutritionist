"""Nutrition-related test fixtures"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
import random

# Import from correct models
try:
    from src.models.meal_plan import (
        MealPlan, DayPlan, Meal, Recipe, Ingredient, 
        NutritionInfo, GroceryList, GroceryListItem
    )
except ImportError:
    # Fallback structure if models don't exist
    class MealPlan:
        def __init__(self, plan_id=None, user_id=None, name="", start_date=None,
                     end_date=None, days=None, total_budget=0.0, household_size=2,
                     generated_at=None, goals_considered=None, dietary_restrictions=None,
                     **kwargs):
            self.plan_id = plan_id or str(uuid4())
            self.user_id = user_id
            self.name = name
            self.start_date = start_date
            self.end_date = end_date
            self.days = days or []
            self.total_budget = total_budget
            self.household_size = household_size
            self.generated_at = generated_at or datetime.utcnow()
            self.goals_considered = goals_considered or []
            self.dietary_restrictions = dietary_restrictions or []
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class DayPlan:
        def __init__(self, date=None, meals=None, daily_nutrition_target=None,
                     notes=None, **kwargs):
            self.date = date
            self.meals = meals or []
            self.daily_nutrition_target = daily_nutrition_target
            self.notes = notes
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class Meal:
        def __init__(self, meal_type=None, recipe=None, scheduled_date=None,
                     notes=None, completed=False, **kwargs):
            self.meal_type = meal_type
            self.recipe = recipe
            self.scheduled_date = scheduled_date
            self.notes = notes
            self.completed = completed
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class Recipe:
        def __init__(self, name, ingredients=None, instructions=None, servings=1, 
                     prep_time_minutes=0, cook_time_minutes=0, nutrition=None, 
                     cuisine_type="american", difficulty="easy", tags=None, 
                     source_url=None, image_url=None, **kwargs):
            self.name = name
            self.ingredients = ingredients or []
            self.instructions = instructions or []
            self.servings = servings
            self.prep_time_minutes = prep_time_minutes
            self.cook_time_minutes = cook_time_minutes
            self.nutrition = nutrition
            self.cuisine_type = cuisine_type
            self.difficulty = difficulty
            self.tags = tags or []
            self.source_url = source_url
            self.image_url = image_url
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        @property
        def total_time_minutes(self):
            return self.prep_time_minutes + self.cook_time_minutes
        
        @property 
        def estimated_cost(self):
            total = 0.0
            for ingredient in self.ingredients:
                if hasattr(ingredient, 'estimated_cost') and ingredient.estimated_cost:
                    total += ingredient.estimated_cost * getattr(ingredient, 'quantity', 1)
            return round(total, 2)
    
    class Ingredient:
        def __init__(self, name, quantity, unit, category="other", estimated_cost=None, 
                     nutrition_per_unit=None, **kwargs):
            self.name = name
            self.quantity = quantity  
            self.unit = unit
            self.category = category
            self.estimated_cost = estimated_cost
            self.nutrition_per_unit = nutrition_per_unit or {}
            # Handle legacy fields
            self.amount = quantity
            self.cost_per_unit = estimated_cost
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class NutritionInfo:
        def __init__(self, calories=0, protein_grams=0, carbs_grams=0, fat_grams=0, 
                     fiber_grams=0, sugar_grams=0, sodium_mg=0, **kwargs):
            self.calories = calories
            self.protein_grams = protein_grams  
            self.carbs_grams = carbs_grams
            self.fat_grams = fat_grams
            self.fiber_grams = fiber_grams
            self.sugar_grams = sugar_grams
            self.sodium_mg = sodium_mg
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class GroceryList:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class GroceryListItem:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

# Import enums with fallbacks
try:
    from src.models.meal_planning import (
        MealType, DifficultyLevel, CookingMethod,
        NutritionFacts, MealPlanEntry, Recipe as RecipeV2
    )
except ImportError:
    # Create enum fallbacks
    class MealType:
        BREAKFAST = "breakfast"
        LUNCH = "lunch"
        DINNER = "dinner"
        SNACK = "snack"
    
    class DifficultyLevel:
        BEGINNER = "beginner"
        INTERMEDIATE = "intermediate"
        ADVANCED = "advanced"
        EXPERT = "expert"
    
    class CookingMethod:
        BAKING = "baking"
        GRILLING = "grilling"
        STOVETOP = "stovetop"
    
    class NutritionFacts:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class MealPlanEntry:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    RecipeV2 = Recipe

try:
    from src.models.user import NutritionTargets
except ImportError:
    class NutritionTargets:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

try:
    from src.utils.datetime_utils import utc_now
except ImportError:
    def utc_now():
        return datetime.utcnow()


class IngredientFactory:
    """Factory for creating test ingredients"""
    
    @staticmethod
    def create(
        name: str = "Test Ingredient",
        quantity: float = 1.0,
        unit: str = "cup",
        category: str = "produce",
        estimated_cost: float = 2.50
    ) -> Ingredient:
        return Ingredient(
            name=name,
            quantity=quantity,
            unit=unit,
            category=category,
            estimated_cost=estimated_cost,
            nutrition_per_unit={
                'calories': 50,
                'protein_grams': 2.0,
                'carbs_grams': 10.0,
                'fat_grams': 1.0,
                'fiber_grams': 2.0,
                'sugar_grams': 5.0,
                'sodium_mg': 100
            }
        )
    
    @staticmethod
    def protein_source(name: str = "Chicken Breast") -> Ingredient:
        return IngredientFactory.create(
            name=name,
            quantity=6.0,
            unit="oz",
            category="protein",
            estimated_cost=4.50
        )
    
    @staticmethod
    def vegetable(name: str = "Broccoli") -> Ingredient:
        return IngredientFactory.create(
            name=name,
            quantity=1.0,
            unit="cup",
            category="vegetable",
            estimated_cost=1.50
        )
    
    @staticmethod
    def grain(name: str = "Brown Rice") -> Ingredient:
        return IngredientFactory.create(
            name=name,
            quantity=0.5,
            unit="cup",
            category="grain",
            estimated_cost=1.00
        )


class RecipeFactory:
    """Factory for creating test recipes"""
    
    @staticmethod
    def create(
        name: str = "Test Recipe",
        meal_type: MealType = MealType.DINNER,
        prep_time: int = 20,
        cook_time: int = 30,
        servings: int = 4,
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        ingredients: List[Ingredient] = None
    ) -> Recipe:
        if ingredients is None:
            ingredients = [
                IngredientFactory.protein_source(),
                IngredientFactory.vegetable(),
                IngredientFactory.grain()
            ]
        
        total_calories = sum(
            ing.nutrition_per_unit.get('calories', 0) * ing.quantity 
            for ing in ingredients
        )
        total_cost = sum(
            (ing.estimated_cost or 0) * ing.quantity 
            for ing in ingredients
        )
        
        return Recipe(
            name=name,
            ingredients=ingredients,
            instructions=[
                "Prepare all ingredients",
                "Cook according to directions",
                "Serve hot"
            ],
            servings=servings,
            prep_time_minutes=prep_time,
            cook_time_minutes=cook_time,
            nutrition=NutritionInfo(
                calories=int(total_calories / servings),
                protein_grams=25.0,
                carbs_grams=30.0,
                fat_grams=10.0,
                fiber_grams=5.0,
                sugar_grams=8.0,
                sodium_mg=600
            ),
            cuisine_type="american",
            difficulty=difficulty.value if hasattr(difficulty, 'value') else str(difficulty),
            tags=["healthy"],
            source_url=None,
            image_url=None
        )
    
    @staticmethod
    def breakfast_recipe() -> Recipe:
        ingredients = [
            IngredientFactory.create("Oats", 0.5, "cup", "grain", 0.50),
            IngredientFactory.create("Blueberries", 0.5, "cup", "fruit", 2.00),
            IngredientFactory.create("Almonds", 0.25, "cup", "nuts", 3.00)
        ]
        return RecipeFactory.create(
            name="Berry Oatmeal",
            meal_type=MealType.BREAKFAST,
            prep_time=5,
            cook_time=10,
            servings=2,
            ingredients=ingredients
        )
    
    @staticmethod
    def lunch_recipe() -> Recipe:
        ingredients = [
            IngredientFactory.create("Quinoa", 0.5, "cup", "grain", 2.00),
            IngredientFactory.create("Chickpeas", 0.5, "cup", "legume", 1.50),
            IngredientFactory.create("Spinach", 2.0, "cups", "vegetable", 1.00)
        ]
        return RecipeFactory.create(
            name="Quinoa Power Bowl",
            meal_type=MealType.LUNCH,
            prep_time=15,
            cook_time=20,
            servings=2,
            ingredients=ingredients
        )
    
    @staticmethod
    def dinner_recipe() -> Recipe:
        ingredients = [
            IngredientFactory.protein_source("Salmon"),
            IngredientFactory.vegetable("Asparagus"),
            IngredientFactory.create("Sweet Potato", 1.0, "medium", "vegetable", 1.25)
        ]
        return RecipeFactory.create(
            name="Grilled Salmon Dinner",
            meal_type=MealType.DINNER,
            prep_time=15,
            cook_time=25,
            servings=4,
            ingredients=ingredients
        )
    
    @staticmethod
    def snack_recipe() -> Recipe:
        ingredients = [
            IngredientFactory.create("Greek Yogurt", 1.0, "cup", "dairy", 1.50),
            IngredientFactory.create("Honey", 1.0, "tbsp", "sweetener", 0.75)
        ]
        return RecipeFactory.create(
            name="Honey Greek Yogurt",
            meal_type=MealType.SNACK,
            prep_time=2,
            cook_time=0,
            servings=1,
            ingredients=ingredients
        )


class MealPlanFactory:
    """Factory for creating test meal plans"""
    
    @staticmethod
    def create(
        user_id: str = None,
        plan_name: str = "Weekly Meal Plan",
        start_date: date = None,
        duration_days: int = 7,
        household_size: int = 2,
        budget: float = 150.0
    ) -> MealPlan:
        if user_id is None:
            user_id = str(uuid4())
        if start_date is None:
            start_date = date.today()
        
        end_date = start_date + timedelta(days=duration_days - 1)
        
        # Create daily meal plans
        days = []
        recipes = [
            RecipeFactory.breakfast_recipe(),
            RecipeFactory.lunch_recipe(),
            RecipeFactory.dinner_recipe(),
            RecipeFactory.snack_recipe()
        ]
        
        for i in range(duration_days):
            current_date = start_date + timedelta(days=i)
            
            # Create meals for each day
            meals = []
            for j, (meal_type, recipe) in enumerate(zip([MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACK], recipes)):
                meal = Meal(
                    meal_type=meal_type,
                    recipe=recipe,
                    scheduled_date=current_date,
                    notes=f"Day {i+1} {meal_type.value if hasattr(meal_type, 'value') else meal_type}",
                    completed=False
                )
                meals.append(meal)
            
            day_plan = DayPlan(
                date=current_date,
                meals=meals,
                daily_nutrition_target={'calories': 2000, 'protein': 150},
                notes=f"Day {i+1} meal plan"
            )
            days.append(day_plan)
        
        return MealPlan(
            plan_id=str(uuid4()),
            user_id=user_id,
            name=plan_name,
            start_date=start_date,
            end_date=end_date,
            days=days,
            total_budget=budget,
            household_size=household_size,
            generated_at=datetime.utcnow(),
            goals_considered=["healthy_eating", "budget_friendly"],
            dietary_restrictions=[]
        )
    
    @staticmethod
    def vegetarian_plan(user_id: str = None) -> MealPlan:
        plan = MealPlanFactory.create(user_id=user_id, plan_name="Vegetarian Weekly Plan")
        plan.dietary_restrictions = ["vegetarian"]
        plan.goals_considered = ["vegetarian", "healthy_eating"]
        return plan
    
    @staticmethod
    def weight_loss_plan(user_id: str = None) -> MealPlan:
        plan = MealPlanFactory.create(
            user_id=user_id, 
            plan_name="Weight Loss Plan",
            budget=120.0
        )
        # Adjust calories for weight loss
        for day in plan.days:
            day.daily_calories_target = 1500
        plan.goals_considered = ["weight_loss", "calorie_deficit"]
        return plan
    
    @staticmethod
    def family_plan(user_id: str = None) -> MealPlan:
        return MealPlanFactory.create(
            user_id=user_id,
            plan_name="Family Meal Plan",
            household_size=4,
            budget=250.0
        )


class NutritionGoalsFactory:
    """Factory for creating nutrition goals"""
    
    @staticmethod
    def weight_loss_goals() -> NutritionTargets:
        return NutritionTargets(
            daily_calories=1500,
            protein_grams=120,
            carb_grams=150,
            fat_grams=50,
            fiber_grams=25,
            sodium_mg=2000
        )
    
    @staticmethod
    def muscle_gain_goals() -> NutritionTargets:
        return NutritionTargets(
            daily_calories=2500,
            protein_grams=200,
            carb_grams=300,
            fat_grams=85,
            fiber_grams=30,
            sodium_mg=2500
        )
    
    @staticmethod
    def maintenance_goals() -> NutritionTargets:
        return NutritionTargets(
            daily_calories=2000,
            protein_grams=150,
            carb_grams=250,
            fat_grams=70,
            fiber_grams=25,
            sodium_mg=2300
        )
    
    @staticmethod
    def diabetic_goals() -> NutritionTargets:
        return NutritionTargets(
            daily_calories=1800,
            protein_grams=90,
            carb_grams=180,
            fat_grams=60,
            fiber_grams=30,
            sodium_mg=1500
        )


class FoodItemsFactory:
    """Factory for creating food items and ingredients"""
    
    @staticmethod
    def protein_foods() -> List[Dict[str, Any]]:
        return [
            {"name": "Chicken Breast", "category": "poultry", "protein_per_100g": 31, "calories_per_100g": 165},
            {"name": "Salmon", "category": "fish", "protein_per_100g": 25, "calories_per_100g": 208},
            {"name": "Tofu", "category": "plant_protein", "protein_per_100g": 8, "calories_per_100g": 76},
            {"name": "Lentils", "category": "legumes", "protein_per_100g": 9, "calories_per_100g": 116},
            {"name": "Greek Yogurt", "category": "dairy", "protein_per_100g": 10, "calories_per_100g": 59}
        ]
    
    @staticmethod
    def vegetables() -> List[Dict[str, Any]]:
        return [
            {"name": "Broccoli", "category": "cruciferous", "fiber_per_100g": 2.6, "calories_per_100g": 34},
            {"name": "Spinach", "category": "leafy_green", "fiber_per_100g": 2.2, "calories_per_100g": 23},
            {"name": "Bell Peppers", "category": "nightshade", "fiber_per_100g": 2.5, "calories_per_100g": 31},
            {"name": "Carrots", "category": "root", "fiber_per_100g": 2.8, "calories_per_100g": 41},
            {"name": "Zucchini", "category": "squash", "fiber_per_100g": 1.0, "calories_per_100g": 17}
        ]
    
    @staticmethod
    def grains() -> List[Dict[str, Any]]:
        return [
            {"name": "Quinoa", "category": "whole_grain", "carbs_per_100g": 64, "calories_per_100g": 368},
            {"name": "Brown Rice", "category": "whole_grain", "carbs_per_100g": 77, "calories_per_100g": 370},
            {"name": "Oats", "category": "whole_grain", "carbs_per_100g": 66, "calories_per_100g": 389},
            {"name": "Whole Wheat Pasta", "category": "pasta", "carbs_per_100g": 75, "calories_per_100g": 371}
        ]


# Pytest fixtures
@pytest.fixture
def ingredient_factory():
    """Factory fixture for creating ingredients"""
    return IngredientFactory


@pytest.fixture
def recipe_factory():
    """Factory fixture for creating recipes"""
    return RecipeFactory


@pytest.fixture
def meal_plan_factory():
    """Factory fixture for creating meal plans"""
    return MealPlanFactory


@pytest.fixture
def create_meal_plan():
    """Create a basic meal plan"""
    return MealPlanFactory.create()


@pytest.fixture
def create_nutrition_goals():
    """Create nutrition goals"""
    return NutritionGoalsFactory.maintenance_goals()


@pytest.fixture
def create_food_items():
    """Create food items collection"""
    return {
        'proteins': FoodItemsFactory.protein_foods(),
        'vegetables': FoodItemsFactory.vegetables(),
        'grains': FoodItemsFactory.grains()
    }


@pytest.fixture
def sample_recipes():
    """Collection of sample recipes"""
    return {
        'breakfast': RecipeFactory.breakfast_recipe(),
        'lunch': RecipeFactory.lunch_recipe(),
        'dinner': RecipeFactory.dinner_recipe(),
        'snack': RecipeFactory.snack_recipe()
    }


@pytest.fixture
def sample_ingredients():
    """Collection of sample ingredients"""
    return [
        IngredientFactory.protein_source("Chicken"),
        IngredientFactory.vegetable("Spinach"),
        IngredientFactory.grain("Quinoa"),
        IngredientFactory.create("Olive Oil", 2.0, "tbsp", "fat", 0.50)
    ]


@pytest.fixture
def nutrition_goals_collection():
    """Collection of different nutrition goal types"""
    return {
        'weight_loss': NutritionGoalsFactory.weight_loss_goals(),
        'muscle_gain': NutritionGoalsFactory.muscle_gain_goals(),
        'maintenance': NutritionGoalsFactory.maintenance_goals(),
        'diabetic': NutritionGoalsFactory.diabetic_goals()
    }


@pytest.fixture
def meal_plans_collection():
    """Collection of different meal plan types"""
    user_id = str(uuid4())
    return {
        'standard': MealPlanFactory.create(user_id=user_id),
        'vegetarian': MealPlanFactory.vegetarian_plan(user_id=user_id),
        'weight_loss': MealPlanFactory.weight_loss_plan(user_id=user_id),
        'family': MealPlanFactory.family_plan(user_id=user_id)
    }


@pytest.fixture
def grocery_list():
    """Create a sample grocery list"""
    items = [
        GroceryListItem(
            name="Chicken Breast",
            quantity=2.0,
            unit="lbs",
            category="meat",
            estimated_cost=8.50,
            purchased=False
        ),
        GroceryListItem(
            name="Broccoli",
            quantity=1.0,
            unit="head",
            category="produce",
            estimated_cost=2.50,
            purchased=False
        ),
        GroceryListItem(
            name="Brown Rice",
            quantity=1.0,
            unit="bag",
            category="pantry",
            estimated_cost=3.00,
            purchased=False
        )
    ]
    
    return GroceryList(
        list_id=str(uuid4()),
        user_id=str(uuid4()),
        plan_id=str(uuid4()),
        items=items,
        created_at=datetime.utcnow(),
        total_estimated_cost=14.00,
        store_preferences=["whole_foods", "safeway"]
    )
