"""
AI Nutritionist - User Data Models
Defines user profile, preferences, and related data structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from ..config.constants import SubscriptionTier, DietaryRestriction, GoalType


@dataclass
class UserGoal:
    """Individual user goal with constraints and priority"""
    goal_type: GoalType
    priority: int  # 1-5, where 5 is highest priority
    target_value: Optional[float] = None  # Target weight, budget, etc.
    target_date: Optional[datetime] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'goal_type': self.goal_type.value,
            'priority': self.priority,
            'target_value': self.target_value,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'constraints': self.constraints,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserGoal':
        return cls(
            goal_type=GoalType(data['goal_type']),
            priority=data['priority'],
            target_value=data.get('target_value'),
            target_date=datetime.fromisoformat(data['target_date']) if data.get('target_date') else None,
            constraints=data.get('constraints', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            is_active=data.get('is_active', True),
        )


@dataclass
class NutritionTargets:
    """Daily nutrition targets for user"""
    calories: int
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    fiber_grams: float = 25
    sodium_mg: float = 2300
    sugar_grams: float = 50
    
    # Calculated properties
    @property
    def protein_percent(self) -> float:
        return (self.protein_grams * 4) / self.calories * 100
    
    @property
    def carbs_percent(self) -> float:
        return (self.carbs_grams * 4) / self.calories * 100
    
    @property
    def fat_percent(self) -> float:
        return (self.fat_grams * 9) / self.calories * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'calories': self.calories,
            'protein_grams': self.protein_grams,
            'carbs_grams': self.carbs_grams,
            'fat_grams': self.fat_grams,
            'fiber_grams': self.fiber_grams,
            'sodium_mg': self.sodium_mg,
            'sugar_grams': self.sugar_grams,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NutritionTargets':
        return cls(**data)


@dataclass
class UserPreferences:
    """User cooking and dietary preferences"""
    household_size: int = 2
    weekly_budget: float = 75.0
    dietary_restrictions: List[DietaryRestriction] = field(default_factory=list)
    cuisine_preferences: List[str] = field(default_factory=lambda: ["american", "italian"])
    cooking_skill: str = "beginner"  # beginner, intermediate, advanced
    max_prep_time: int = 30  # minutes
    kitchen_equipment: List[str] = field(default_factory=lambda: ["stove", "oven", "microwave"])
    allergens: List[str] = field(default_factory=list)
    favorite_ingredients: List[str] = field(default_factory=list)
    disliked_ingredients: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'household_size': self.household_size,
            'weekly_budget': self.weekly_budget,
            'dietary_restrictions': [dr.value for dr in self.dietary_restrictions],
            'cuisine_preferences': self.cuisine_preferences,
            'cooking_skill': self.cooking_skill,
            'max_prep_time': self.max_prep_time,
            'kitchen_equipment': self.kitchen_equipment,
            'allergens': self.allergens,
            'favorite_ingredients': self.favorite_ingredients,
            'disliked_ingredients': self.disliked_ingredients,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        return cls(
            household_size=data.get('household_size', 2),
            weekly_budget=data.get('weekly_budget', 75.0),
            dietary_restrictions=[DietaryRestriction(dr) for dr in data.get('dietary_restrictions', [])],
            cuisine_preferences=data.get('cuisine_preferences', ["american", "italian"]),
            cooking_skill=data.get('cooking_skill', "beginner"),
            max_prep_time=data.get('max_prep_time', 30),
            kitchen_equipment=data.get('kitchen_equipment', ["stove", "oven", "microwave"]),
            allergens=data.get('allergens', []),
            favorite_ingredients=data.get('favorite_ingredients', []),
            disliked_ingredients=data.get('disliked_ingredients', []),
        )


@dataclass 
class UserProfile:
    """Complete user profile with all preferences and settings"""
    user_id: str
    phone_number: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    goals: List[UserGoal] = field(default_factory=list)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    nutrition_targets: Optional[NutritionTargets] = None
    
    # Profile completion tracking
    onboarding_completed: bool = False
    profile_completion_score: float = 0.0  # 0-1 scale
    
    # Usage tracking
    meal_plans_this_month: int = 0
    grocery_lists_this_month: int = 0
    ai_consultations_today: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None
    timezone: str = "UTC"
    language: str = "en"
    
    # Linked accounts (family sharing)
    linked_users: List[str] = field(default_factory=list)
    primary_account: bool = True
    
    def get_primary_goal(self) -> Optional[UserGoal]:
        """Get the highest priority active goal"""
        active_goals = [g for g in self.goals if g.is_active]
        if not active_goals:
            return None
        return max(active_goals, key=lambda g: g.priority)
    
    def add_goal(self, goal: UserGoal) -> None:
        """Add a new goal to the user's profile"""
        self.goals.append(goal)
        self.last_updated = datetime.utcnow()
        self._update_profile_completion()
    
    def remove_goal(self, goal_type: GoalType) -> bool:
        """Remove a goal by type"""
        initial_count = len(self.goals)
        self.goals = [g for g in self.goals if g.goal_type != goal_type]
        if len(self.goals) < initial_count:
            self.last_updated = datetime.utcnow()
            self._update_profile_completion()
            return True
        return False
    
    def update_subscription(self, new_tier: SubscriptionTier) -> None:
        """Update subscription tier"""
        self.subscription_tier = new_tier
        self.last_updated = datetime.utcnow()
    
    def calculate_nutrition_targets(self) -> NutritionTargets:
        """Calculate personalized nutrition targets based on goals"""
        # Base calorie calculation (simplified)
        base_calories = 1800  # Default
        
        # Adjust based on goals
        primary_goal = self.get_primary_goal()
        if primary_goal:
            if primary_goal.goal_type == GoalType.WEIGHT_LOSS:
                base_calories -= 300
            elif primary_goal.goal_type == GoalType.MUSCLE_GAIN:
                base_calories += 400
        
        # Adjust for household size (more cooking = more sampling)
        if self.preferences.household_size > 2:
            base_calories += 100
        
        # Calculate macros (standard distribution)
        protein_grams = base_calories * 0.25 / 4  # 25% protein
        carbs_grams = base_calories * 0.45 / 4    # 45% carbs
        fat_grams = base_calories * 0.30 / 9      # 30% fat
        
        return NutritionTargets(
            calories=int(base_calories),
            protein_grams=round(protein_grams, 1),
            carbs_grams=round(carbs_grams, 1),
            fat_grams=round(fat_grams, 1),
        )
    
    def _update_profile_completion(self) -> None:
        """Update profile completion score"""
        score = 0.0
        
        # Basic info (20%)
        if self.phone_number:
            score += 0.2
        
        # Goals (30%)
        if self.goals:
            score += 0.3
        
        # Preferences (30%)
        if self.preferences.dietary_restrictions:
            score += 0.1
        if self.preferences.cuisine_preferences:
            score += 0.1  
        if self.preferences.weekly_budget > 0:
            score += 0.1
        
        # Nutrition targets (20%)
        if self.nutrition_targets:
            score += 0.2
        
        self.profile_completion_score = min(score, 1.0)
        
        # Mark onboarding complete if score > 80%
        if score >= 0.8:
            self.onboarding_completed = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'phone_number': self.phone_number,
            'subscription_tier': self.subscription_tier.value,
            'goals': [goal.to_dict() for goal in self.goals],
            'preferences': self.preferences.to_dict(),
            'nutrition_targets': self.nutrition_targets.to_dict() if self.nutrition_targets else None,
            'onboarding_completed': self.onboarding_completed,
            'profile_completion_score': self.profile_completion_score,
            'meal_plans_this_month': self.meal_plans_this_month,
            'grocery_lists_this_month': self.grocery_lists_this_month,
            'ai_consultations_today': self.ai_consultations_today,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'timezone': self.timezone,
            'language': self.language,
            'linked_users': self.linked_users,
            'primary_account': self.primary_account,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create from dictionary"""
        goals = [UserGoal.from_dict(g) for g in data.get('goals', [])]
        preferences = UserPreferences.from_dict(data.get('preferences', {}))
        nutrition_targets = None
        if data.get('nutrition_targets'):
            nutrition_targets = NutritionTargets.from_dict(data['nutrition_targets'])
        
        return cls(
            user_id=data['user_id'],
            phone_number=data['phone_number'],
            subscription_tier=SubscriptionTier(data.get('subscription_tier', 'free')),
            goals=goals,
            preferences=preferences,
            nutrition_targets=nutrition_targets,
            onboarding_completed=data.get('onboarding_completed', False),
            profile_completion_score=data.get('profile_completion_score', 0.0),
            meal_plans_this_month=data.get('meal_plans_this_month', 0),
            grocery_lists_this_month=data.get('grocery_lists_this_month', 0),
            ai_consultations_today=data.get('ai_consultations_today', 0),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.utcnow().isoformat())),
            last_active=datetime.fromisoformat(data['last_active']) if data.get('last_active') else None,
            timezone=data.get('timezone', 'UTC'),
            language=data.get('language', 'en'),
            linked_users=data.get('linked_users', []),
            primary_account=data.get('primary_account', True),
        )
