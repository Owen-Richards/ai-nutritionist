"""
AI Nutritionist - Meal Plan Data Models
Defines meal plan, recipe, and grocery list structures
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum

from ..config.constants import MealType


@dataclass
class Ingredient:
    """Individual ingredient with quantity and unit"""
    name: str
    quantity: float
    unit: str
    category: str = "other"  # produce, meat, dairy, etc.
    estimated_cost: Optional[float] = None
    nutrition_per_unit: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'quantity': self.quantity,
            'unit': self.unit,
            'category': self.category,
            'estimated_cost': self.estimated_cost,
            'nutrition_per_unit': self.nutrition_per_unit,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Ingredient':
        return cls(
            name=data['name'],
            quantity=data['quantity'],
            unit=data['unit'],
            category=data.get('category', 'other'),
            estimated_cost=data.get('estimated_cost'),
            nutrition_per_unit=data.get('nutrition_per_unit', {}),
        )


@dataclass
class NutritionInfo:
    """Nutritional information for a meal or recipe"""
    calories: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    fiber_grams: float = 0.0
    sodium_mg: float = 0.0
    sugar_grams: float = 0.0
    
    # Additional micronutrients (optional)
    vitamin_c_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    calcium_mg: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'calories': self.calories,
            'protein_grams': self.protein_grams,
            'carbs_grams': self.carbs_grams,
            'fat_grams': self.fat_grams,
            'fiber_grams': self.fiber_grams,
            'sodium_mg': self.sodium_mg,
            'sugar_grams': self.sugar_grams,
            'vitamin_c_mg': self.vitamin_c_mg,
            'iron_mg': self.iron_mg,
            'calcium_mg': self.calcium_mg,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NutritionInfo':
        return cls(
            calories=data['calories'],
            protein_grams=data['protein_grams'],
            carbs_grams=data['carbs_grams'],
            fat_grams=data['fat_grams'],
            fiber_grams=data.get('fiber_grams', 0.0),
            sodium_mg=data.get('sodium_mg', 0.0),
            sugar_grams=data.get('sugar_grams', 0.0),
            vitamin_c_mg=data.get('vitamin_c_mg'),
            iron_mg=data.get('iron_mg'),
            calcium_mg=data.get('calcium_mg'),
        )


@dataclass
class Recipe:
    """Individual recipe with instructions and nutrition"""
    name: str
    ingredients: List[Ingredient]
    instructions: List[str]
    servings: int
    prep_time_minutes: int
    cook_time_minutes: int
    nutrition: NutritionInfo
    cuisine_type: str = "american"
    difficulty: str = "easy"  # easy, medium, hard
    tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    
    @property
    def total_time_minutes(self) -> int:
        return self.prep_time_minutes + self.cook_time_minutes
    
    @property
    def estimated_cost(self) -> float:
        """Calculate estimated cost from ingredients"""
        total = 0.0
        for ingredient in self.ingredients:
            if ingredient.estimated_cost:
                total += ingredient.estimated_cost * ingredient.quantity
        return round(total, 2)
    
    def scale_recipe(self, new_servings: int) -> 'Recipe':
        """Scale recipe to different serving size"""
        scale_factor = new_servings / self.servings
        
        scaled_ingredients = []
        for ingredient in self.ingredients:
            scaled_ingredients.append(Ingredient(
                name=ingredient.name,
                quantity=ingredient.quantity * scale_factor,
                unit=ingredient.unit,
                category=ingredient.category,
                estimated_cost=ingredient.estimated_cost,
                nutrition_per_unit=ingredient.nutrition_per_unit,
            ))
        
        scaled_nutrition = NutritionInfo(
            calories=self.nutrition.calories * scale_factor,
            protein_grams=self.nutrition.protein_grams * scale_factor,
            carbs_grams=self.nutrition.carbs_grams * scale_factor,
            fat_grams=self.nutrition.fat_grams * scale_factor,
            fiber_grams=self.nutrition.fiber_grams * scale_factor,
            sodium_mg=self.nutrition.sodium_mg * scale_factor,
            sugar_grams=self.nutrition.sugar_grams * scale_factor,
        )
        
        return Recipe(
            name=self.name,
            ingredients=scaled_ingredients,
            instructions=self.instructions,
            servings=new_servings,
            prep_time_minutes=self.prep_time_minutes,
            cook_time_minutes=self.cook_time_minutes,
            nutrition=scaled_nutrition,
            cuisine_type=self.cuisine_type,
            difficulty=self.difficulty,
            tags=self.tags.copy(),
            source_url=self.source_url,
            image_url=self.image_url,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'ingredients': [ing.to_dict() for ing in self.ingredients],
            'instructions': self.instructions,
            'servings': self.servings,
            'prep_time_minutes': self.prep_time_minutes,
            'cook_time_minutes': self.cook_time_minutes,
            'nutrition': self.nutrition.to_dict(),
            'cuisine_type': self.cuisine_type,
            'difficulty': self.difficulty,
            'tags': self.tags,
            'source_url': self.source_url,
            'image_url': self.image_url,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Recipe':
        return cls(
            name=data['name'],
            ingredients=[Ingredient.from_dict(ing) for ing in data['ingredients']],
            instructions=data['instructions'],
            servings=data['servings'],
            prep_time_minutes=data['prep_time_minutes'],
            cook_time_minutes=data['cook_time_minutes'],
            nutrition=NutritionInfo.from_dict(data['nutrition']),
            cuisine_type=data.get('cuisine_type', 'american'),
            difficulty=data.get('difficulty', 'easy'),
            tags=data.get('tags', []),
            source_url=data.get('source_url'),
            image_url=data.get('image_url'),
        )


@dataclass
class Meal:
    """Single meal in a meal plan"""
    meal_type: MealType
    recipe: Recipe
    scheduled_date: date
    notes: Optional[str] = None
    completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'meal_type': self.meal_type.value,
            'recipe': self.recipe.to_dict(),
            'scheduled_date': self.scheduled_date.isoformat(),
            'notes': self.notes,
            'completed': self.completed,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Meal':
        return cls(
            meal_type=MealType(data['meal_type']),
            recipe=Recipe.from_dict(data['recipe']),
            scheduled_date=date.fromisoformat(data['scheduled_date']),
            notes=data.get('notes'),
            completed=data.get('completed', False),
        )


@dataclass
class DayPlan:
    """All meals for a single day"""
    date: date
    meals: List[Meal] = field(default_factory=list)
    daily_nutrition_target: Optional[Dict[str, float]] = None
    notes: Optional[str] = None
    
    def get_meal(self, meal_type: MealType) -> Optional[Meal]:
        """Get specific meal by type"""
        for meal in self.meals:
            if meal.meal_type == meal_type:
                return meal
        return None
    
    def add_meal(self, meal: Meal) -> None:
        """Add meal to day (replace if same type exists)"""
        # Remove existing meal of same type
        self.meals = [m for m in self.meals if m.meal_type != meal.meal_type]
        self.meals.append(meal)
        self.meals.sort(key=lambda m: list(MealType).index(m.meal_type))
    
    def calculate_daily_nutrition(self) -> NutritionInfo:
        """Calculate total nutrition for the day"""
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        total_sodium = 0.0
        total_sugar = 0.0
        
        for meal in self.meals:
            nutrition = meal.recipe.nutrition
            total_calories += nutrition.calories
            total_protein += nutrition.protein_grams
            total_carbs += nutrition.carbs_grams
            total_fat += nutrition.fat_grams
            total_fiber += nutrition.fiber_grams
            total_sodium += nutrition.sodium_mg
            total_sugar += nutrition.sugar_grams
        
        return NutritionInfo(
            calories=total_calories,
            protein_grams=total_protein,
            carbs_grams=total_carbs,
            fat_grams=total_fat,
            fiber_grams=total_fiber,
            sodium_mg=total_sodium,
            sugar_grams=total_sugar,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'meals': [meal.to_dict() for meal in self.meals],
            'daily_nutrition_target': self.daily_nutrition_target,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DayPlan':
        return cls(
            date=date.fromisoformat(data['date']),
            meals=[Meal.from_dict(meal) for meal in data.get('meals', [])],
            daily_nutrition_target=data.get('daily_nutrition_target'),
            notes=data.get('notes'),
        )


@dataclass
class MealPlan:
    """Complete meal plan for multiple days"""
    plan_id: str
    user_id: str
    name: str
    start_date: date
    end_date: date
    days: List[DayPlan] = field(default_factory=list)
    
    # Plan metadata
    total_budget: float = 0.0
    household_size: int = 2
    generated_at: datetime = field(default_factory=datetime.utcnow)
    goals_considered: List[str] = field(default_factory=list)
    dietary_restrictions: List[str] = field(default_factory=list)
    
    # Status
    is_active: bool = True
    completion_percentage: float = 0.0
    
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1
    
    @property
    def estimated_cost_per_day(self) -> float:
        if not self.days:
            return 0.0
        total_cost = sum(
            sum(meal.recipe.estimated_cost for meal in day.meals)
            for day in self.days
        )
        return total_cost / len(self.days)
    
    def get_day_plan(self, target_date: date) -> Optional[DayPlan]:
        """Get meal plan for specific date"""
        for day in self.days:
            if day.date == target_date:
                return day
        return None
    
    def add_day_plan(self, day_plan: DayPlan) -> None:
        """Add or update day plan"""
        # Remove existing plan for same date
        self.days = [d for d in self.days if d.date != day_plan.date]
        self.days.append(day_plan)
        self.days.sort(key=lambda d: d.date)
    
    def calculate_weekly_nutrition(self) -> NutritionInfo:
        """Calculate average daily nutrition across the plan"""
        if not self.days:
            return NutritionInfo(0, 0, 0, 0)
        
        total_nutrition = NutritionInfo(0, 0, 0, 0)
        
        for day in self.days:
            day_nutrition = day.calculate_daily_nutrition()
            total_nutrition.calories += day_nutrition.calories
            total_nutrition.protein_grams += day_nutrition.protein_grams
            total_nutrition.carbs_grams += day_nutrition.carbs_grams
            total_nutrition.fat_grams += day_nutrition.fat_grams
            total_nutrition.fiber_grams += day_nutrition.fiber_grams
            total_nutrition.sodium_mg += day_nutrition.sodium_mg
            total_nutrition.sugar_grams += day_nutrition.sugar_grams
        
        # Return average per day
        num_days = len(self.days)
        return NutritionInfo(
            calories=total_nutrition.calories / num_days,
            protein_grams=total_nutrition.protein_grams / num_days,
            carbs_grams=total_nutrition.carbs_grams / num_days,
            fat_grams=total_nutrition.fat_grams / num_days,
            fiber_grams=total_nutrition.fiber_grams / num_days,
            sodium_mg=total_nutrition.sodium_mg / num_days,
            sugar_grams=total_nutrition.sugar_grams / num_days,
        )
    
    def update_completion(self) -> None:
        """Update completion percentage based on completed meals"""
        if not self.days:
            self.completion_percentage = 0.0
            return
        
        total_meals = sum(len(day.meals) for day in self.days)
        completed_meals = sum(
            len([meal for meal in day.meals if meal.completed])
            for day in self.days
        )
        
        self.completion_percentage = (completed_meals / total_meals * 100) if total_meals > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan_id': self.plan_id,
            'user_id': self.user_id,
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'days': [day.to_dict() for day in self.days],
            'total_budget': self.total_budget,
            'household_size': self.household_size,
            'generated_at': self.generated_at.isoformat(),
            'goals_considered': self.goals_considered,
            'dietary_restrictions': self.dietary_restrictions,
            'is_active': self.is_active,
            'completion_percentage': self.completion_percentage,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MealPlan':
        meal_plan = cls(
            plan_id=data['plan_id'],
            user_id=data['user_id'],
            name=data['name'],
            start_date=date.fromisoformat(data['start_date']),
            end_date=date.fromisoformat(data['end_date']),
            days=[DayPlan.from_dict(day) for day in data.get('days', [])],
            total_budget=data.get('total_budget', 0.0),
            household_size=data.get('household_size', 2),
            generated_at=datetime.fromisoformat(data.get('generated_at', datetime.utcnow().isoformat())),
            goals_considered=data.get('goals_considered', []),
            dietary_restrictions=data.get('dietary_restrictions', []),
            is_active=data.get('is_active', True),
            completion_percentage=data.get('completion_percentage', 0.0),
        )
        return meal_plan


@dataclass
class GroceryListItem:
    """Individual item on grocery list"""
    ingredient: Ingredient
    recipes_used_in: List[str] = field(default_factory=list)
    purchased: bool = False
    store_section: Optional[str] = None
    priority: int = 1  # 1-5, 5 is highest
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ingredient': self.ingredient.to_dict(),
            'recipes_used_in': self.recipes_used_in,
            'purchased': self.purchased,
            'store_section': self.store_section,
            'priority': self.priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroceryListItem':
        return cls(
            ingredient=Ingredient.from_dict(data['ingredient']),
            recipes_used_in=data.get('recipes_used_in', []),
            purchased=data.get('purchased', False),
            store_section=data.get('store_section'),
            priority=data.get('priority', 1),
        )


@dataclass
class GroceryList:
    """Complete grocery shopping list"""
    list_id: str
    user_id: str
    meal_plan_id: str
    name: str
    items: List[GroceryListItem] = field(default_factory=list)
    estimated_total_cost: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    shopping_completed: bool = False
    store_preference: Optional[str] = None
    
    @property
    def completion_percentage(self) -> float:
        if not self.items:
            return 0.0
        purchased_count = len([item for item in self.items if item.purchased])
        return (purchased_count / len(self.items)) * 100
    
    def add_item(self, item: GroceryListItem) -> None:
        """Add item to grocery list, combining duplicates"""
        # Check for existing item with same name
        for existing_item in self.items:
            if (existing_item.ingredient.name.lower() == item.ingredient.name.lower() and
                existing_item.ingredient.unit == item.ingredient.unit):
                # Combine quantities
                existing_item.ingredient.quantity += item.ingredient.quantity
                existing_item.recipes_used_in.extend(item.recipes_used_in)
                return
        
        # Add new item
        self.items.append(item)
    
    def organize_by_store_section(self) -> Dict[str, List[GroceryListItem]]:
        """Group items by store section"""
        sections = {}
        for item in self.items:
            section = item.store_section or item.ingredient.category or "Other"
            if section not in sections:
                sections[section] = []
            sections[section].append(item)
        return sections
    
    def calculate_total_cost(self) -> float:
        """Calculate total estimated cost"""
        total = 0.0
        for item in self.items:
            if item.ingredient.estimated_cost:
                total += item.ingredient.estimated_cost * item.ingredient.quantity
        self.estimated_total_cost = round(total, 2)
        return self.estimated_total_cost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'list_id': self.list_id,
            'user_id': self.user_id,
            'meal_plan_id': self.meal_plan_id,
            'name': self.name,
            'items': [item.to_dict() for item in self.items],
            'estimated_total_cost': self.estimated_total_cost,
            'created_at': self.created_at.isoformat(),
            'shopping_completed': self.shopping_completed,
            'store_preference': self.store_preference,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroceryList':
        return cls(
            list_id=data['list_id'],
            user_id=data['user_id'],
            meal_plan_id=data['meal_plan_id'],
            name=data['name'],
            items=[GroceryListItem.from_dict(item) for item in data.get('items', [])],
            estimated_total_cost=data.get('estimated_total_cost', 0.0),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            shopping_completed=data.get('shopping_completed', False),
            store_preference=data.get('store_preference'),
        )
