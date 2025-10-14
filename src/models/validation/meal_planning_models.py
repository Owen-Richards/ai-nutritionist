"""Comprehensive Pydantic models for meal planning and nutrition services."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Annotated, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .user_models import BaseValidationModel, APIBaseModel, DietaryRestriction


class MealType(str, Enum):
    """Types of meals."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"


class CuisineType(str, Enum):
    """Cuisine types."""
    AMERICAN = "american"
    ITALIAN = "italian"
    MEXICAN = "mexican"
    CHINESE = "chinese"
    INDIAN = "indian"
    THAI = "thai"
    JAPANESE = "japanese"
    MEDITERRANEAN = "mediterranean"
    FRENCH = "french"
    GREEK = "greek"
    KOREAN = "korean"
    MIDDLE_EASTERN = "middle_eastern"
    LATIN_AMERICAN = "latin_american"
    AFRICAN = "african"
    FUSION = "fusion"


class DifficultyLevel(str, Enum):
    """Cooking difficulty levels."""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"


class MeasurementUnit(str, Enum):
    """Measurement units for ingredients."""
    # Volume
    CUP = "cup"
    TABLESPOON = "tablespoon"
    TEASPOON = "teaspoon"
    FLUID_OUNCE = "fluid_ounce"
    MILLILITER = "milliliter"
    LITER = "liter"
    
    # Weight
    OUNCE = "ounce"
    POUND = "pound"
    GRAM = "gram"
    KILOGRAM = "kilogram"
    
    # Count
    PIECE = "piece"
    ITEM = "item"
    CLOVE = "clove"
    SLICE = "slice"
    
    # Other
    PINCH = "pinch"
    DASH = "dash"
    TO_TASTE = "to_taste"


class PlanStatus(str, Enum):
    """Meal plan status."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NutritionInfo(BaseValidationModel):
    """Nutritional information for foods and meals."""
    
    calories: Annotated[float, Field(ge=0, le=10000)] = Field(
        ...,
        description="Calories per serving"
    )
    protein_g: Annotated[float, Field(ge=0, le=500)] = Field(
        ...,
        description="Protein in grams"
    )
    carbohydrates_g: Annotated[float, Field(ge=0, le=1000)] = Field(
        ...,
        description="Carbohydrates in grams"
    )
    fat_g: Annotated[float, Field(ge=0, le=500)] = Field(
        ...,
        description="Fat in grams"
    )
    fiber_g: Optional[Annotated[float, Field(ge=0, le=200)]] = Field(
        None,
        description="Fiber in grams"
    )
    sugar_g: Optional[Annotated[float, Field(ge=0, le=500)]] = Field(
        None,
        description="Sugar in grams"
    )
    sodium_mg: Optional[Annotated[float, Field(ge=0, le=10000)]] = Field(
        None,
        description="Sodium in milligrams"
    )
    cholesterol_mg: Optional[Annotated[float, Field(ge=0, le=2000)]] = Field(
        None,
        description="Cholesterol in milligrams"
    )
    vitamin_c_mg: Optional[Annotated[float, Field(ge=0, le=1000)]] = Field(
        None,
        description="Vitamin C in milligrams"
    )
    calcium_mg: Optional[Annotated[float, Field(ge=0, le=5000)]] = Field(
        None,
        description="Calcium in milligrams"
    )
    iron_mg: Optional[Annotated[float, Field(ge=0, le=100)]] = Field(
        None,
        description="Iron in milligrams"
    )
    
    @model_validator(mode='after')
    def validate_nutrition_consistency(self) -> 'NutritionInfo':
        """Validate nutritional values are consistent."""
        # Check if calories are roughly consistent with macronutrients
        if self.protein_g and self.carbohydrates_g and self.fat_g:
            calculated_calories = (
                self.protein_g * 4 +  # 4 calories per gram of protein
                self.carbohydrates_g * 4 +  # 4 calories per gram of carbs
                self.fat_g * 9  # 9 calories per gram of fat
            )
            
            # Allow 20% variance for rounding and other factors
            tolerance = self.calories * 0.2
            if abs(calculated_calories - self.calories) > tolerance:
                raise ValueError(
                    f"Calories ({self.calories}) are inconsistent with macronutrients "
                    f"(calculated: {calculated_calories:.1f})"
                )
        
        return self


class Ingredient(BaseValidationModel):
    """Individual ingredient with quantity and nutrition."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique ingredient identifier")
    name: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        ...,
        description="Ingredient name"
    )
    quantity: Annotated[float, Field(gt=0, le=1000)] = Field(
        ...,
        description="Quantity of ingredient"
    )
    unit: MeasurementUnit = Field(
        ...,
        description="Unit of measurement"
    )
    category: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        None,
        description="Ingredient category (e.g., 'vegetables', 'proteins')"
    )
    nutrition_per_unit: Optional[NutritionInfo] = Field(
        None,
        description="Nutritional information per unit"
    )
    cost_per_unit: Optional[Annotated[Decimal, Field(gt=0, le=1000)]] = Field(
        None,
        description="Cost per unit in USD"
    )
    allergens: List[str] = Field(
        default_factory=list,
        description="List of allergens present in this ingredient"
    )
    
    @field_validator('name')
    @classmethod
    def validate_ingredient_name(cls, v: str) -> str:
        """Validate and clean ingredient name."""
        # Remove any potentially harmful characters
        cleaned = ''.join(c for c in v if c.isprintable())
        return cleaned.strip()
    
    @property
    def total_nutrition(self) -> Optional[NutritionInfo]:
        """Calculate total nutrition for the ingredient quantity."""
        if not self.nutrition_per_unit:
            return None
        
        # Scale nutrition by quantity
        nutrition_dict = self.nutrition_per_unit.model_dump()
        for key, value in nutrition_dict.items():
            if value is not None and isinstance(value, (int, float)):
                nutrition_dict[key] = value * self.quantity
        
        return NutritionInfo(**nutrition_dict)


class Recipe(BaseValidationModel):
    """Recipe with ingredients, instructions, and metadata."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique recipe identifier")
    name: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        ...,
        description="Recipe name"
    )
    description: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="Recipe description"
    )
    ingredients: List[Ingredient] = Field(
        ...,
        min_length=1,
        description="List of recipe ingredients"
    )
    instructions: List[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        ...,
        min_length=1,
        description="Step-by-step cooking instructions"
    )
    servings: Annotated[int, Field(gt=0, le=20)] = Field(
        ...,
        description="Number of servings this recipe makes"
    )
    prep_time_minutes: Annotated[int, Field(ge=0, le=480)] = Field(
        ...,
        description="Preparation time in minutes"
    )
    cook_time_minutes: Annotated[int, Field(ge=0, le=480)] = Field(
        ...,
        description="Cooking time in minutes"
    )
    difficulty: DifficultyLevel = Field(
        ...,
        description="Cooking difficulty level"
    )
    cuisine_type: Optional[CuisineType] = Field(
        None,
        description="Cuisine type"
    )
    meal_types: List[MealType] = Field(
        ...,
        min_length=1,
        description="Suitable meal types for this recipe"
    )
    dietary_restrictions: List[DietaryRestriction] = Field(
        default_factory=list,
        description="Dietary restrictions this recipe accommodates"
    )
    tags: List[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list,
        description="Recipe tags for categorization"
    )
    estimated_cost: Optional[Annotated[Decimal, Field(gt=0, le=1000)]] = Field(
        None,
        description="Estimated cost to make recipe in USD"
    )
    
    @property
    def total_time_minutes(self) -> int:
        """Calculate total time required for recipe."""
        return self.prep_time_minutes + self.cook_time_minutes
    
    @property
    def nutrition_per_serving(self) -> Optional[NutritionInfo]:
        """Calculate nutrition per serving."""
        total_nutrition = {
            'calories': 0.0,
            'protein_g': 0.0,
            'carbohydrates_g': 0.0,
            'fat_g': 0.0,
            'fiber_g': 0.0,
            'sugar_g': 0.0,
            'sodium_mg': 0.0,
            'cholesterol_mg': 0.0,
            'vitamin_c_mg': 0.0,
            'calcium_mg': 0.0,
            'iron_mg': 0.0,
        }
        
        has_nutrition = False
        for ingredient in self.ingredients:
            ingredient_nutrition = ingredient.total_nutrition
            if ingredient_nutrition:
                has_nutrition = True
                for key in total_nutrition:
                    ingredient_value = getattr(ingredient_nutrition, key, 0) or 0
                    total_nutrition[key] += ingredient_value
        
        if not has_nutrition:
            return None
        
        # Calculate per serving
        for key in total_nutrition:
            total_nutrition[key] = total_nutrition[key] / self.servings
        
        return NutritionInfo(**total_nutrition)


class Meal(BaseValidationModel):
    """Individual meal in a meal plan."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique meal identifier")
    meal_type: MealType = Field(
        ...,
        description="Type of meal"
    )
    recipe: Recipe = Field(
        ...,
        description="Recipe for this meal"
    )
    scheduled_date: date = Field(
        ...,
        description="Date when meal is scheduled"
    )
    scheduled_time: Optional[time] = Field(
        None,
        description="Time when meal is scheduled"
    )
    servings_planned: Annotated[int, Field(gt=0, le=20)] = Field(
        default=1,
        description="Number of servings planned for this meal"
    )
    notes: Optional[Annotated[str, Field(max_length=500)]] = Field(
        None,
        description="Additional notes for this meal"
    )
    prepared: bool = Field(
        default=False,
        description="Whether the meal has been prepared"
    )
    consumed: bool = Field(
        default=False,
        description="Whether the meal has been consumed"
    )
    rating: Optional[Annotated[int, Field(ge=1, le=5)]] = Field(
        None,
        description="User rating for the meal (1-5 stars)"
    )
    feedback: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="User feedback about the meal"
    )
    
    @field_validator('scheduled_date')
    @classmethod
    def validate_scheduled_date(cls, v: date) -> date:
        """Validate scheduled date is reasonable."""
        today = date.today()
        if v < today - timedelta(days=30):
            raise ValueError("Scheduled date cannot be more than 30 days in the past")
        if v > today + timedelta(days=365):
            raise ValueError("Scheduled date cannot be more than 1 year in the future")
        return v
    
    @property
    def total_nutrition(self) -> Optional[NutritionInfo]:
        """Calculate total nutrition for planned servings."""
        per_serving = self.recipe.nutrition_per_serving
        if not per_serving:
            return None
        
        # Scale by planned servings
        nutrition_dict = per_serving.model_dump()
        for key, value in nutrition_dict.items():
            if value is not None and isinstance(value, (int, float)):
                nutrition_dict[key] = value * self.servings_planned
        
        return NutritionInfo(**nutrition_dict)


class MealPlan(BaseValidationModel):
    """Complete meal plan for a user."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique meal plan identifier")
    user_id: UUID = Field(
        ...,
        description="ID of the user this plan belongs to"
    )
    name: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        ...,
        description="Name of the meal plan"
    )
    description: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="Description of the meal plan"
    )
    start_date: date = Field(
        ...,
        description="Start date of the meal plan"
    )
    end_date: date = Field(
        ...,
        description="End date of the meal plan"
    )
    meals: List[Meal] = Field(
        ...,
        description="List of meals in the plan"
    )
    status: PlanStatus = Field(
        default=PlanStatus.DRAFT,
        description="Current status of the meal plan"
    )
    target_calories_per_day: Optional[Annotated[float, Field(gt=0, le=10000)]] = Field(
        None,
        description="Target calories per day"
    )
    target_macros: Optional[Dict[str, float]] = Field(
        None,
        description="Target macronutrient ratios (protein, carbs, fat percentages)"
    )
    budget_limit: Optional[Annotated[Decimal, Field(gt=0, le=10000)]] = Field(
        None,
        description="Budget limit for the meal plan in USD"
    )
    
    @model_validator(mode='after')
    def validate_meal_plan_consistency(self) -> 'MealPlan':
        """Validate meal plan consistency."""
        # Validate date range
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")
        
        # Validate plan duration (max 1 year)
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("Meal plan cannot exceed 1 year duration")
        
        # Validate target macros sum to 100%
        if self.target_macros:
            total_percentage = sum(self.target_macros.values())
            if abs(total_percentage - 100.0) > 1.0:  # Allow 1% tolerance
                raise ValueError("Target macro percentages must sum to 100%")
        
        # Validate all meals are within date range
        for meal in self.meals:
            if not (self.start_date <= meal.scheduled_date <= self.end_date):
                raise ValueError(f"Meal scheduled for {meal.scheduled_date} is outside plan date range")
        
        return self
    
    @property
    def duration_days(self) -> int:
        """Calculate plan duration in days."""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def total_estimated_cost(self) -> Optional[Decimal]:
        """Calculate total estimated cost for the meal plan."""
        total_cost = Decimal('0')
        has_costs = False
        
        for meal in self.meals:
            if meal.recipe.estimated_cost:
                has_costs = True
                cost_per_serving = meal.recipe.estimated_cost / meal.recipe.servings
                total_cost += cost_per_serving * meal.servings_planned
        
        return total_cost if has_costs else None
    
    def get_daily_nutrition(self, target_date: date) -> Optional[NutritionInfo]:
        """Get total nutrition for a specific date."""
        daily_meals = [meal for meal in self.meals if meal.scheduled_date == target_date]
        
        if not daily_meals:
            return None
        
        total_nutrition = {
            'calories': 0.0,
            'protein_g': 0.0,
            'carbohydrates_g': 0.0,
            'fat_g': 0.0,
            'fiber_g': 0.0,
            'sugar_g': 0.0,
            'sodium_mg': 0.0,
            'cholesterol_mg': 0.0,
            'vitamin_c_mg': 0.0,
            'calcium_mg': 0.0,
            'iron_mg': 0.0,
        }
        
        has_nutrition = False
        for meal in daily_meals:
            meal_nutrition = meal.total_nutrition
            if meal_nutrition:
                has_nutrition = True
                for key in total_nutrition:
                    meal_value = getattr(meal_nutrition, key, 0) or 0
                    total_nutrition[key] += meal_value
        
        return NutritionInfo(**total_nutrition) if has_nutrition else None


# API Request/Response Models

class MealPlanGenerationRequest(APIBaseModel):
    """Request model for generating a meal plan."""
    
    user_id: UUID = Field(
        ...,
        description="User ID for the meal plan"
    )
    start_date: date = Field(
        ...,
        description="Start date for the meal plan"
    )
    duration_days: Annotated[int, Field(gt=0, le=365)] = Field(
        ...,
        description="Duration of the meal plan in days"
    )
    target_calories_per_day: Optional[Annotated[float, Field(gt=0, le=10000)]] = Field(
        None,
        description="Target calories per day"
    )
    dietary_restrictions: List[DietaryRestriction] = Field(
        default_factory=list,
        description="Dietary restrictions to consider"
    )
    cuisine_preferences: List[CuisineType] = Field(
        default_factory=list,
        description="Preferred cuisine types"
    )
    excluded_ingredients: List[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
        description="Ingredients to exclude"
    )
    budget_limit: Optional[Annotated[Decimal, Field(gt=0, le=10000)]] = Field(
        None,
        description="Budget limit in USD"
    )
    meal_types: List[MealType] = Field(
        default_factory=lambda: [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER],
        description="Types of meals to include"
    )


class MealPlanUpdateRequest(APIBaseModel):
    """Request model for updating a meal plan."""
    
    name: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None
    description: Optional[Annotated[str, Field(max_length=1000)]] = None
    status: Optional[PlanStatus] = None
    target_calories_per_day: Optional[Annotated[float, Field(gt=0, le=10000)]] = None
    target_macros: Optional[Dict[str, float]] = None
    budget_limit: Optional[Annotated[Decimal, Field(gt=0, le=10000)]] = None


class MealFeedbackRequest(APIBaseModel):
    """Request model for meal feedback."""
    
    meal_id: UUID = Field(
        ...,
        description="ID of the meal to provide feedback for"
    )
    rating: Annotated[int, Field(ge=1, le=5)] = Field(
        ...,
        description="Rating from 1-5 stars"
    )
    feedback: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="Written feedback about the meal"
    )
    consumed: bool = Field(
        default=True,
        description="Whether the meal was consumed"
    )
    modifications: Optional[Annotated[str, Field(max_length=500)]] = Field(
        None,
        description="Any modifications made to the recipe"
    )


class MealPlanResponse(APIBaseModel):
    """Response model for meal plan data."""
    
    meal_plan: MealPlan = Field(
        ...,
        description="Complete meal plan data"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracing"
    )


class MealPlanListResponse(APIBaseModel):
    """Response model for meal plan list operations."""
    
    meal_plans: List[MealPlan] = Field(
        ...,
        description="List of meal plans"
    )
    total_count: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total number of meal plans"
    )
    page: Annotated[int, Field(gt=0)] = Field(
        ...,
        description="Current page number"
    )
    page_size: Annotated[int, Field(gt=0, le=100)] = Field(
        ...,
        description="Number of items per page"
    )


class NutritionSummaryResponse(APIBaseModel):
    """Response model for nutrition summary data."""
    
    date_range: Dict[str, date] = Field(
        ...,
        description="Date range for the summary"
    )
    daily_averages: NutritionInfo = Field(
        ...,
        description="Average daily nutrition values"
    )
    total_nutrition: NutritionInfo = Field(
        ...,
        description="Total nutrition for the period"
    )
    target_compliance: Optional[Dict[str, float]] = Field(
        None,
        description="Compliance with nutrition targets (percentages)"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Nutritional recommendations based on data"
    )
