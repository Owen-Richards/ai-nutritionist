"""
Domain model interfaces and abstract base classes
Following hexagonal architecture principles
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    FAMILY = "family"
    ENTERPRISE = "enterprise"


class DietaryRestriction(Enum):
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    LOW_SODIUM = "low_sodium"
    HALAL = "halal"
    KOSHER = "kosher"


class HealthGoal(Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_BUILDING = "muscle_building"
    GENERAL_HEALTH = "general_health"
    ATHLETIC_PERFORMANCE = "athletic_performance"
    DISEASE_MANAGEMENT = "disease_management"


@dataclass
class NutritionProfile:
    """User's nutritional profile and preferences"""
    dietary_restrictions: List[DietaryRestriction]
    health_goals: List[HealthGoal]
    calorie_target: Optional[int]
    protein_target: Optional[int]
    carb_target: Optional[int]
    fat_target: Optional[int]
    allergies: List[str]
    dislikes: List[str]
    max_prep_time: int  # minutes
    budget_preference: str  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dietary_restrictions': [dr.value for dr in self.dietary_restrictions],
            'health_goals': [hg.value for hg in self.health_goals],
            'calorie_target': self.calorie_target,
            'protein_target': self.protein_target,
            'carb_target': self.carb_target,
            'fat_target': self.fat_target,
            'allergies': self.allergies,
            'dislikes': self.dislikes,
            'max_prep_time': self.max_prep_time,
            'budget_preference': self.budget_preference
        }


@dataclass
class UserProfile:
    """Complete user profile domain model"""
    phone_number: str
    user_tier: UserTier
    nutrition_profile: NutritionProfile
    created_at: datetime
    last_active: datetime
    is_active: bool = True
    
    def can_access_premium_features(self) -> bool:
        """Check if user can access premium features"""
        return self.user_tier in [UserTier.PREMIUM, UserTier.FAMILY, UserTier.ENTERPRISE]
    
    def get_daily_message_limit(self) -> int:
        """Get daily message limit based on tier"""
        limits = {
            UserTier.FREE: 5,
            UserTier.PREMIUM: 50,
            UserTier.FAMILY: 100,
            UserTier.ENTERPRISE: -1  # unlimited
        }
        return limits.get(self.user_tier, 5)


@dataclass
class Recipe:
    """Recipe domain model"""
    id: str
    name: str
    ingredients: List[str]
    instructions: List[str]
    prep_time: int  # minutes
    cook_time: int  # minutes
    servings: int
    calories_per_serving: int
    nutrition_info: Dict[str, float]
    dietary_tags: List[str]
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    
    @property
    def total_time(self) -> int:
        return self.prep_time + self.cook_time
    
    def matches_dietary_restrictions(self, restrictions: List[DietaryRestriction]) -> bool:
        """Check if recipe matches dietary restrictions"""
        restriction_tags = [r.value for r in restrictions]
        return all(tag in self.dietary_tags for tag in restriction_tags)


@dataclass
class MealPlan:
    """Meal plan domain model"""
    id: str
    user_phone: str
    plan_date: str  # YYYY-MM-DD
    meals: Dict[str, List[Recipe]]  # breakfast, lunch, dinner, snacks
    total_calories: int
    total_nutrition: Dict[str, float]
    created_at: datetime
    
    def get_meal_count(self) -> int:
        """Get total number of meals in plan"""
        return sum(len(recipes) for recipes in self.meals.values())
    
    def meets_calorie_target(self, target_calories: int, tolerance: float = 0.1) -> bool:
        """Check if plan meets calorie target within tolerance"""
        lower_bound = target_calories * (1 - tolerance)
        upper_bound = target_calories * (1 + tolerance)
        return lower_bound <= self.total_calories <= upper_bound


@dataclass
class CostOptimizationResult:
    """Result of cost optimization analysis"""
    is_valid: bool
    confidence: float
    reason: str
    estimated_cost: float
    recommended_action: str
    user_message: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class BrandMatch:
    """Brand matching result for endorsements"""
    brand_id: str
    brand_name: str
    match_score: float  # 0.0 to 1.0
    category: str
    reason: str
    estimated_revenue: float


@dataclass
class RevenueEvent:
    """Revenue tracking event"""
    event_id: str
    user_phone: str
    event_type: str  # subscription, affiliate, marketplace, etc.
    revenue_amount: float
    currency: str
    metadata: Dict[str, Any]
    timestamp: datetime


class DomainService(ABC):
    """Base class for domain services"""
    
    @abstractmethod
    def validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Validate domain-specific business rules"""
        pass


class NutritionDomainService(DomainService):
    """Domain service for nutrition-related business logic"""
    
    def validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Validate nutrition-specific business rules"""
        # Implement nutrition-specific validation
        return True
    
    @abstractmethod
    def calculate_nutrition_score(self, meal_plan: MealPlan, profile: NutritionProfile) -> float:
        """Calculate how well a meal plan matches nutrition profile"""
        pass
    
    @abstractmethod
    def suggest_recipe_alternatives(self, recipe: Recipe, restrictions: List[DietaryRestriction]) -> List[Recipe]:
        """Suggest alternative recipes that meet restrictions"""
        pass


class BusinessDomainService(DomainService):
    """Domain service for business logic"""
    
    def validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Validate business-specific rules"""
        # Implement business-specific validation
        return True
    
    @abstractmethod
    def calculate_user_value(self, user_profile: UserProfile, usage_data: Dict[str, Any]) -> float:
        """Calculate user lifetime value"""
        pass
    
    @abstractmethod
    def determine_optimal_pricing(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Determine optimal pricing strategy for user"""
        pass
