"""
Comprehensive User Profile Management for AI Nutritionist
Tracks all user preferences, health data, and personalization
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict
from enum import Enum
import json


class DietaryPreference(Enum):
    OMNIVORE = "omnivore"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    KETO = "keto"
    PALEO = "paleo"
    MEDITERRANEAN = "mediterranean"
    LOW_CARB = "low_carb"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NO_DAIRY = "no-dairy"  # Alias for dairy_free


class ActivityLevel(Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"


class HealthGoal(Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MAINTAIN_WEIGHT = "maintain_weight"
    MUSCLE_GAIN = "muscle_gain"
    IMPROVE_HEALTH = "improve_health"
    MANAGE_CONDITION = "manage_condition"


@dataclass
class FoodAllergy:
    allergen: str
    severity: str  # mild, moderate, severe, life_threatening
    reactions: List[str]
    notes: Optional[str] = None


@dataclass
class HealthMetrics:
    height_cm: Optional[float] = None
    height_inches: Optional[float] = None  # For US measurements
    weight_kg: Optional[float] = None
    weight_lbs: Optional[float] = None    # For US measurements
    age: Optional[int] = None
    gender: Optional[str] = None
    bmi: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    resting_heart_rate: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    cholesterol_total: Optional[float] = None
    cholesterol_hdl: Optional[float] = None
    cholesterol_ldl: Optional[float] = None
    blood_glucose: Optional[float] = None


@dataclass
class MacroTargets:
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None


@dataclass
class FamilyMember:
    name: str
    member_id: str
    age: Optional[int] = None
    dietary_preferences: List[DietaryPreference] = None
    dietary_restrictions: List[str] = None  # For compatibility
    allergies: List[FoodAllergy] = None
    dislikes: List[str] = None
    health_conditions: List[str] = None


@dataclass
class BudgetPreferences:
    weekly_budget: Optional[float] = None
    monthly_budget: Optional[float] = None
    weekly_food_budget: Optional[float] = None  # For meal planning compatibility
    preferred_stores: List[str] = None
    coupon_preferences: bool = True
    bulk_buying: bool = False
    organic_preference: Optional[str] = None  # always, sometimes, never
    brand_preferences: Dict[str, str] = None  # category -> preferred brand


@dataclass
class CookingPreferences:
    skill_level: str = "beginner"  # beginner, intermediate, advanced
    max_prep_time: int = 30  # minutes
    max_cook_time: int = 45  # minutes
    preferred_methods: List[str] = None  # baking, grilling, stovetop, etc.
    kitchen_equipment: List[str] = None
    meal_prep_frequency: str = "weekly"  # daily, weekly, monthly
    batch_cooking: bool = False


class UserProfile:
    """Comprehensive user profile for AI nutritionist"""
    
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        
        # Basic Information
        self.name: Optional[str] = None
        self.timezone: str = "UTC"
        self.language: str = "en"
        
        # Health & Physical Data
        self.health_metrics = HealthMetrics()
        self.activity_level: Optional[ActivityLevel] = None
        self.health_goals: List[HealthGoal] = []
        self.health_conditions: List[str] = []
        self.medications: List[str] = []
        
        # Dietary Information
        self.dietary_preferences: List[DietaryPreference] = []
        self.allergies: List[FoodAllergy] = []
        self.food_dislikes: List[str] = []
        self.food_loves: List[str] = []
        self.cultural_cuisines: List[str] = []
        
        # Nutrition Targets
        self.macro_targets = MacroTargets()
        self.micro_targets: Dict[str, float] = {}  # vitamin/mineral targets
        self.hydration_target_ml: int = 2000
        
        # Family & Household
        self.household_size: int = 1
        self.family_members: List[FamilyMember] = []
        self.cooking_for_family: bool = False
        
        # Preferences & Lifestyle
        self.budget_preferences = BudgetPreferences()
        self.cooking_preferences = CookingPreferences()
        self.meal_timing: Dict[str, str] = {
            "breakfast": "07:00",
            "lunch": "12:00",
            "dinner": "18:00"
        }
        
        # AI Interaction Preferences
        self.communication_style: str = "friendly"  # formal, friendly, casual
        self.feedback_frequency: str = "weekly"
        self.reminder_preferences: Dict[str, bool] = {
            "meal_prep": True,
            "grocery_shopping": True,
            "hydration": True,
            "exercise": False
        }
        
        # Subscription & Features
        self.subscription_tier: str = "free"  # free, standard, premium
        self.premium_features: List[str] = []
        
        # Analytics & History
        self.total_conversations: int = 0
        self.favorite_recipes: List[str] = []
        self.successful_meal_plans: List[str] = []
        self.nutrition_streak: int = 0  # days following plan
        
    @property
    def dietary_info(self) -> Dict:
        """Compatibility property for tests"""
        return {
            "dietary_restrictions": [pref.value for pref in self.dietary_preferences]
        }
        
    def calculate_bmi(self) -> Optional[float]:
        """Calculate BMI from height and weight"""
        if self.health_metrics.height_inches and self.health_metrics.weight_lbs:
            # Convert to metric if needed
            height_m = self.health_metrics.height_inches * 0.0254
            weight_kg = self.health_metrics.weight_lbs * 0.453592
            bmi = weight_kg / (height_m ** 2)
            self.health_metrics.bmi = round(bmi, 1)
            return self.health_metrics.bmi
        elif self.health_metrics.height_cm and self.health_metrics.weight_kg:
            height_m = self.health_metrics.height_cm / 100
            bmi = self.health_metrics.weight_kg / (height_m ** 2)
            self.health_metrics.bmi = round(bmi, 1)
            return self.health_metrics.bmi
        return None
        
    def update_health_metrics(self, **kwargs) -> None:
        """Update health metrics"""
        for key, value in kwargs.items():
            if hasattr(self.health_metrics, key):
                setattr(self.health_metrics, key, value)
        
        # Calculate BMI if height and weight are available
        if self.health_metrics.height_cm and self.health_metrics.weight_kg:
            height_m = self.health_metrics.height_cm / 100
            self.health_metrics.bmi = self.health_metrics.weight_kg / (height_m ** 2)
        
        self.last_updated = datetime.utcnow()
    
    def add_allergy(self, allergen: str, severity: str, reactions: List[str], notes: str = None) -> None:
        """Add a food allergy"""
        allergy = FoodAllergy(
            allergen=allergen,
            severity=severity,
            reactions=reactions,
            notes=notes
        )
        self.allergies.append(allergy)
        self.last_updated = datetime.utcnow()
    
    def add_family_member(self, member_or_name, **kwargs) -> str:
        """Add a family member"""
        if isinstance(member_or_name, FamilyMember):
            # Direct FamilyMember object
            member = member_or_name
        else:
            # Create from name and kwargs
            if 'member_id' not in kwargs:
                kwargs['member_id'] = f"member_{len(self.family_members)}"
            member = FamilyMember(name=member_or_name, **kwargs)
        
        self.family_members.append(member)
        self.household_size = len(self.family_members) + 1
        self.cooking_for_family = len(self.family_members) > 0
        self.last_updated = datetime.utcnow()
        return member.member_id
    
    def update_macro_targets(self, **kwargs) -> None:
        """Update macro nutrient targets"""
        for key, value in kwargs.items():
            if hasattr(self.macro_targets, key):
                setattr(self.macro_targets, key, value)
        self.last_updated = datetime.utcnow()
    
    def calculate_calorie_needs(self) -> Optional[int]:
        """Calculate daily calorie needs using Harris-Benedict equation"""
        if not all([self.health_metrics.weight_kg, self.health_metrics.height_cm, 
                   self.health_metrics.age, self.health_metrics.gender]):
            return None
        
        # Harris-Benedict equation
        if self.health_metrics.gender.lower() == "male":
            bmr = (88.362 + (13.397 * self.health_metrics.weight_kg) + 
                   (4.799 * self.health_metrics.height_cm) - (5.677 * self.health_metrics.age))
        else:
            bmr = (447.593 + (9.247 * self.health_metrics.weight_kg) + 
                   (3.098 * self.health_metrics.height_cm) - (4.330 * self.health_metrics.age))
        
        # Activity multiplier
        activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9
        }
        
        multiplier = activity_multipliers.get(self.activity_level, 1.2)
        daily_calories = int(bmr * multiplier)
        
        # Adjust for goals
        if HealthGoal.WEIGHT_LOSS in self.health_goals:
            daily_calories -= 500  # 1 lb per week loss
        elif HealthGoal.WEIGHT_GAIN in self.health_goals:
            daily_calories += 500  # 1 lb per week gain
        
        return daily_calories
    
    def get_dietary_restrictions(self) -> List[str]:
        """Get all dietary restrictions including allergies and preferences"""
        restrictions = []
        
        # Add dietary preferences
        for pref in self.dietary_preferences:
            restrictions.append(pref.value)
        
        # Add allergies
        for allergy in self.allergies:
            restrictions.append(f"no_{allergy.allergen.lower().replace(' ', '_')}")
        
        # Add dislikes
        for dislike in self.food_dislikes:
            restrictions.append(f"avoid_{dislike.lower().replace(' ', '_')}")
        
        return list(set(restrictions))  # Remove duplicates
    
    def get_family_restrictions(self) -> List[str]:
        """Get dietary restrictions for entire family"""
        all_restrictions = self.get_dietary_restrictions()
        
        for member in self.family_members:
            if member.dietary_preferences:
                for pref in member.dietary_preferences:
                    all_restrictions.append(pref.value)
            
            if member.allergies:
                for allergy in member.allergies:
                    all_restrictions.append(f"no_{allergy.allergen.lower().replace(' ', '_')}")
            
            if member.dislikes:
                for dislike in member.dislikes:
                    all_restrictions.append(f"avoid_{dislike.lower().replace(' ', '_')}")
        
        return list(set(all_restrictions))
    
    def get_personalization_context(self) -> Dict[str, Any]:
        """Get context for AI personalization"""
        return {
            "user_profile": {
                "name": self.name,
                "dietary_preferences": [p.value for p in self.dietary_preferences],
                "allergies": [a.allergen for a in self.allergies],
                "health_goals": [g.value for g in self.health_goals],
                "household_size": self.household_size,
                "budget_weekly": self.budget_preferences.weekly_budget,
                "cooking_skill": self.cooking_preferences.skill_level,
                "max_prep_time": self.cooking_preferences.max_prep_time,
                "activity_level": self.activity_level.value if self.activity_level else None,
                "calorie_target": self.macro_targets.calories or self.calculate_calorie_needs(),
                "communication_style": self.communication_style,
                "subscription_tier": self.subscription_tier
            },
            "family_context": {
                "cooking_for_family": self.cooking_for_family,
                "family_size": len(self.family_members),
                "family_restrictions": self.get_family_restrictions()
            },
            "preferences": {
                "cuisines": self.cultural_cuisines,
                "loved_foods": self.food_loves,
                "cooking_methods": self.cooking_preferences.preferred_methods,
                "meal_timing": self.meal_timing
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for storage"""
        return {
            "phone_number": self.phone_number,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "name": self.name,
            "timezone": self.timezone,
            "language": self.language,
            "health_metrics": asdict(self.health_metrics),
            "activity_level": self.activity_level.value if self.activity_level else None,
            "health_goals": [g.value for g in self.health_goals],
            "health_conditions": self.health_conditions,
            "medications": self.medications,
            "dietary_preferences": [p.value for p in self.dietary_preferences],
            "allergies": [asdict(a) for a in self.allergies],
            "food_dislikes": self.food_dislikes,
            "food_loves": self.food_loves,
            "cultural_cuisines": self.cultural_cuisines,
            "macro_targets": asdict(self.macro_targets),
            "micro_targets": self.micro_targets,
            "hydration_target_ml": self.hydration_target_ml,
            "household_size": self.household_size,
            "family_members": [asdict(m) for m in self.family_members],
            "cooking_for_family": self.cooking_for_family,
            "budget_preferences": asdict(self.budget_preferences),
            "cooking_preferences": asdict(self.cooking_preferences),
            "meal_timing": self.meal_timing,
            "communication_style": self.communication_style,
            "feedback_frequency": self.feedback_frequency,
            "reminder_preferences": self.reminder_preferences,
            "subscription_tier": self.subscription_tier,
            "premium_features": self.premium_features,
            "total_conversations": self.total_conversations,
            "favorite_recipes": self.favorite_recipes,
            "successful_meal_plans": self.successful_meal_plans,
            "nutrition_streak": self.nutrition_streak
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create profile from dictionary"""
        profile = cls(data["phone_number"])
        
        # Basic info
        profile.name = data.get("name")
        profile.timezone = data.get("timezone", "UTC")
        profile.language = data.get("language", "en")
        
        # Dates
        if "created_at" in data:
            profile.created_at = datetime.fromisoformat(data["created_at"])
        if "last_updated" in data:
            profile.last_updated = datetime.fromisoformat(data["last_updated"])
        
        # Health metrics
        if "health_metrics" in data:
            for key, value in data["health_metrics"].items():
                if hasattr(profile.health_metrics, key) and value is not None:
                    setattr(profile.health_metrics, key, value)
        
        # Enums and lists
        if "activity_level" in data and data["activity_level"]:
            profile.activity_level = ActivityLevel(data["activity_level"])
        
        if "health_goals" in data:
            profile.health_goals = [HealthGoal(g) for g in data["health_goals"]]
        
        if "dietary_preferences" in data:
            profile.dietary_preferences = [DietaryPreference(p) for p in data["dietary_preferences"]]
        
        # Allergies
        if "allergies" in data:
            profile.allergies = [FoodAllergy(**a) for a in data["allergies"]]
        
        # Family members
        if "family_members" in data:
            profile.family_members = [FamilyMember(**m) for m in data["family_members"]]
        
        # Simple fields
        simple_fields = [
            "health_conditions", "medications", "food_dislikes", "food_loves",
            "cultural_cuisines", "micro_targets", "hydration_target_ml",
            "household_size", "cooking_for_family", "meal_timing",
            "communication_style", "feedback_frequency", "reminder_preferences",
            "subscription_tier", "premium_features", "total_conversations",
            "favorite_recipes", "successful_meal_plans", "nutrition_streak"
        ]
        
        for field in simple_fields:
            if field in data:
                setattr(profile, field, data[field])
        
        # Complex objects
        if "macro_targets" in data:
            profile.macro_targets = MacroTargets(**data["macro_targets"])
        
        if "budget_preferences" in data:
            profile.budget_preferences = BudgetPreferences(**data["budget_preferences"])
        
        if "cooking_preferences" in data:
            profile.cooking_preferences = CookingPreferences(**data["cooking_preferences"])
        
        return profile
