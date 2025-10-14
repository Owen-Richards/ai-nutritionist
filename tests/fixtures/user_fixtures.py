"""User-related test fixtures"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import replace

# Import with fallbacks
try:
    from src.models.user import (
        UserProfile, UserGoal, UserPreferences, NutritionTargets,
        MedicalCaution, WearableIntegration, InventoryLink
    )
except ImportError:
    # Create fallback classes
    class UserProfile:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class UserGoal:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class UserPreferences:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class NutritionTargets:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class MedicalCaution:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class WearableIntegration:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class InventoryLink:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

try:
    from src.config.constants import SubscriptionTier, DietaryRestriction, GoalType
except ImportError:
    # Create fallback enums
    class SubscriptionTier:
        FREE = "free"
        PREMIUM = "premium"
        FAMILY = "family"
        ENTERPRISE = "enterprise"
    
    class DietaryRestriction:
        VEGETARIAN = "vegetarian"
        VEGAN = "vegan"
        GLUTEN_FREE = "gluten_free"
        KETO = "keto"
        PALEO = "paleo"
        LOW_CARB = "low_carb"
        DIABETIC_FRIENDLY = "diabetic_friendly"
    
    class GoalType:
        WEIGHT_LOSS = "weight_loss"
        WEIGHT_GAIN = "weight_gain"
        MUSCLE_GAIN = "muscle_gain"
        MAINTENANCE = "maintenance"
        FAMILY_NUTRITION = "family_nutrition"


class UserFactory:
    """Factory for creating test users with various configurations"""
    
    @staticmethod
    def base_user(
        phone: str = "+1234567890",
        user_id: Optional[str] = None,
        subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> UserProfile:
        """Create a basic test user"""
        return UserProfile(
            user_id=user_id or str(uuid4()),
            phone_number=phone,
            subscription_tier=subscription_tier,
            onboarding_completed=True,
            profile_completion_score=0.8,
            created_at=datetime.utcnow() - timedelta(days=30)
        )
    
    @staticmethod
    def premium_user(phone: str = "+1234567891") -> UserProfile:
        """Create a premium subscription user"""
        user = UserFactory.base_user(phone, subscription_tier=SubscriptionTier.PREMIUM)
        user.meal_plans_this_month = 15
        user.grocery_lists_this_month = 10
        user.ai_consultations_today = 5
        user.profile_completion_score = 1.0
        return user
    
    @staticmethod
    def family_user(
        phone: str = "+1234567892",
        family_size: int = 4,
        children_ages: List[int] = None
    ) -> UserProfile:
        """Create a family account user"""
        user = UserFactory.base_user(phone, subscription_tier=SubscriptionTier.FAMILY)
        
        # Add family-specific preferences
        user.preferences.household_size = family_size
        user.preferences.cooking_skill_level = "intermediate"
        user.preferences.prep_time_preference = 45  # minutes
        user.preferences.budget_per_meal = 12.0  # higher for family
        
        # Add family goals
        if children_ages:
            for age in children_ages:
                user.goals.append(UserGoal(
                    goal_type=GoalType.FAMILY_NUTRITION,
                    description=f"Healthy meals for child aged {age}",
                    target_value=1.0,
                    priority=8,
                    target_date=date.today() + timedelta(days=365)
                ))
        
        return user
    
    @staticmethod
    def weight_loss_user(phone: str = "+1234567893") -> UserProfile:
        """Create user with weight loss goals"""
        user = UserFactory.base_user(phone)
        
        # Set weight loss goals
        user.goals = [
            UserGoal(
                goal_type=GoalType.WEIGHT_LOSS,
                description="Lose 20 pounds",
                target_value=20.0,
                current_value=0.0,
                priority=10,
                target_date=date.today() + timedelta(days=180)
            )
        ]
        
        # Set nutrition targets for weight loss
        user.nutrition_targets = NutritionTargets(
            daily_calories=1500,
            protein_grams=120,
            carb_grams=150,
            fat_grams=50,
            fiber_grams=25,
            sodium_mg=2000
        )
        
        # Set preferences
        user.preferences.dietary_restrictions = [DietaryRestriction.LOW_CARB]
        user.preferences.cooking_skill_level = "beginner"
        user.preferences.prep_time_preference = 30
        
        return user
    
    @staticmethod
    def diabetic_user(phone: str = "+1234567894") -> UserProfile:
        """Create user with diabetes management needs"""
        user = UserFactory.base_user(phone)
        
        # Add medical caution
        user.medical_cautions = [
            MedicalCaution(
                condition="Type 2 Diabetes",
                severity="moderate",
                restrictions=["low sugar", "complex carbohydrates only"],
                notes="Monitor blood glucose after meals"
            )
        ]
        
        # Set appropriate nutrition targets
        user.nutrition_targets = NutritionTargets(
            daily_calories=1800,
            protein_grams=90,
            carb_grams=180,  # controlled carbs
            fat_grams=60,
            fiber_grams=30,
            sodium_mg=1500
        )
        
        # Set dietary restrictions
        user.preferences.dietary_restrictions = [DietaryRestriction.DIABETIC_FRIENDLY]
        
        return user


class UserProfileBuilder:
    """Builder pattern for creating customized user profiles"""
    
    def __init__(self):
        self._user = UserFactory.base_user()
    
    def with_phone(self, phone: str) -> 'UserProfileBuilder':
        self._user.phone_number = phone
        return self
    
    def with_subscription(self, tier: SubscriptionTier) -> 'UserProfileBuilder':
        self._user.subscription_tier = tier
        return self
    
    def with_goals(self, goals: List[UserGoal]) -> 'UserProfileBuilder':
        self._user.goals = goals
        return self
    
    def with_dietary_restrictions(self, restrictions: List[DietaryRestriction]) -> 'UserProfileBuilder':
        self._user.preferences.dietary_restrictions = restrictions
        return self
    
    def with_nutrition_targets(self, targets: NutritionTargets) -> 'UserProfileBuilder':
        self._user.nutrition_targets = targets
        return self
    
    def with_medical_cautions(self, cautions: List[MedicalCaution]) -> 'UserProfileBuilder':
        self._user.medical_cautions = cautions
        return self
    
    def with_wearable(self, device_type: str, device_id: str) -> 'UserProfileBuilder':
        integration = WearableIntegration(
            device_type=device_type,
            device_id=device_id,
            connected_at=datetime.utcnow(),
            last_sync=datetime.utcnow(),
            sync_frequency_hours=24,
            permissions_granted=["steps", "heart_rate", "calories"],
            auto_sync=True
        )
        self._user.wearable_integrations[device_type] = integration
        return self
    
    def with_inventory_link(self, inventory_id: str, provider: str) -> 'UserProfileBuilder':
        link = InventoryLink(
            inventory_id=inventory_id,
            provider=provider,
            connected_at=datetime.utcnow(),
            last_sync=datetime.utcnow(),
            auto_sync=True
        )
        self._user.inventory_links = getattr(self._user, 'inventory_links', [])
        self._user.inventory_links.append(link)
        return self
    
    def with_usage_stats(self, meal_plans: int = 0, grocery_lists: int = 0, consultations: int = 0) -> 'UserProfileBuilder':
        self._user.meal_plans_this_month = meal_plans
        self._user.grocery_lists_this_month = grocery_lists
        self._user.ai_consultations_today = consultations
        return self
    
    def build(self) -> UserProfile:
        return self._user


# Pytest fixtures
@pytest.fixture
def user_factory():
    """Factory fixture for creating test users"""
    return UserFactory


@pytest.fixture
def user_profile_builder():
    """Builder fixture for creating customized user profiles"""
    return UserProfileBuilder()


@pytest.fixture
def create_test_user():
    """Create a basic test user"""
    return UserFactory.base_user()


@pytest.fixture
def create_premium_user():
    """Create a premium subscription user"""
    return UserFactory.premium_user()


@pytest.fixture
def create_family_account():
    """Create a family account with multiple members"""
    return UserFactory.family_user(
        family_size=4,
        children_ages=[8, 12]
    )


@pytest.fixture
def create_weight_loss_user():
    """Create user with weight loss goals"""
    return UserFactory.weight_loss_user()


@pytest.fixture
def create_diabetic_user():
    """Create user with diabetes management needs"""
    return UserFactory.diabetic_user()


@pytest.fixture
def sample_user_goals():
    """Sample user goals for testing"""
    return [
        UserGoal(
            goal_type=GoalType.WEIGHT_LOSS,
            description="Lose 15 pounds",
            target_value=15.0,
            current_value=3.0,
            priority=9,
            target_date=date.today() + timedelta(days=120)
        ),
        UserGoal(
            goal_type=GoalType.MUSCLE_GAIN,
            description="Gain lean muscle",
            target_value=5.0,
            current_value=1.0,
            priority=7,
            target_date=date.today() + timedelta(days=180)
        )
    ]


@pytest.fixture
def sample_nutrition_targets():
    """Sample nutrition targets for testing"""
    return NutritionTargets(
        daily_calories=2000,
        protein_grams=150,
        carb_grams=200,
        fat_grams=70,
        fiber_grams=25,
        sodium_mg=2300
    )


@pytest.fixture
def sample_user_preferences():
    """Sample user preferences for testing"""
    return UserPreferences(
        dietary_restrictions=[DietaryRestriction.VEGETARIAN],
        cooking_skill_level="intermediate",
        prep_time_preference=30,
        budget_per_meal=8.50,
        household_size=2,
        favorite_cuisines=["mediterranean", "asian"],
        disliked_ingredients=["cilantro", "mushrooms"],
        kitchen_equipment=["oven", "stovetop", "blender"]
    )


@pytest.fixture
def users_collection():
    """Collection of different user types for testing"""
    return {
        'basic': UserFactory.base_user(),
        'premium': UserFactory.premium_user(),
        'family': UserFactory.family_user(),
        'weight_loss': UserFactory.weight_loss_user(),
        'diabetic': UserFactory.diabetic_user()
    }
