"""
User Preferences Management Service

Handles dietary preferences, restrictions, and food preferences with intelligent
learning and adaptation capabilities for personalized nutrition recommendations.

Consolidates functionality from:
- personalization_service.py
- preference_learning_service.py
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DietaryRestriction(Enum):
    """Standard dietary restrictions with validation rules."""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NUT_FREE = "nut_free"
    SHELLFISH_FREE = "shellfish_free"
    KOSHER = "kosher"
    HALAL = "halal"
    KETO = "keto"
    PALEO = "paleo"
    LOW_SODIUM = "low_sodium"
    DIABETIC = "diabetic"


class PreferenceStrength(Enum):
    """Strength levels for food preferences."""
    LOVE = 5
    LIKE = 4
    NEUTRAL = 3
    DISLIKE = 2
    HATE = 1


@dataclass
class FoodPreference:
    """Individual food preference with learning metadata."""
    food_item: str
    strength: PreferenceStrength
    category: str
    last_updated: datetime
    confidence_score: float = 0.5
    interaction_count: int = 0
    learned: bool = False


@dataclass
class DietaryProfile:
    """Complete dietary profile for a user."""
    user_id: str
    restrictions: Set[DietaryRestriction]
    allergies: List[str]
    preferences: Dict[str, FoodPreference]
    cuisine_preferences: Dict[str, float]
    macro_preferences: Dict[str, float]
    meal_timing_preferences: Dict[str, Any]
    cultural_dietary_needs: List[str]
    health_conditions: List[str]
    created_at: datetime
    last_updated: datetime


class UserPreferencesService:
    """
    Advanced user preferences management with machine learning capabilities.
    
    Features:
    - Dietary restriction validation and conflict detection
    - Intelligent preference learning from user interactions
    - Cultural and health-based dietary adaptations
    - Preference confidence scoring and recommendation weighting
    """

    def __init__(self):
        self.preference_cache: Dict[str, DietaryProfile] = {}
        self.restriction_conflicts = self._build_restriction_conflicts()
        self.cultural_mappings = self._build_cultural_mappings()

    def get_user_profile(self, user_id: str) -> Optional[DietaryProfile]:
        """
        Retrieve complete dietary profile for user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Complete dietary profile or None if not found
        """
        try:
            if user_id in self.preference_cache:
                return self.preference_cache[user_id]
            
            # Load from persistent storage (would be database in production)
            profile = self._load_profile_from_storage(user_id)
            if profile:
                self.preference_cache[user_id] = profile
            
            return profile
            
        except Exception as e:
            logger.error(f"Error retrieving user profile {user_id}: {e}")
            return None

    def create_user_profile(
        self,
        user_id: str,
        initial_restrictions: Optional[List[str]] = None,
        initial_allergies: Optional[List[str]] = None,
        cultural_background: Optional[str] = None,
        health_conditions: Optional[List[str]] = None
    ) -> DietaryProfile:
        """
        Create new user dietary profile with intelligent defaults.
        
        Args:
            user_id: Unique user identifier
            initial_restrictions: Initial dietary restrictions
            initial_allergies: Known allergies
            cultural_background: Cultural dietary background
            health_conditions: Relevant health conditions
            
        Returns:
            Newly created dietary profile
        """
        try:
            now = datetime.utcnow()
            
            # Convert restrictions to enum
            restrictions = set()
            if initial_restrictions:
                for restriction in initial_restrictions:
                    try:
                        restrictions.add(DietaryRestriction(restriction.lower()))
                    except ValueError:
                        logger.warning(f"Unknown dietary restriction: {restriction}")
            
            # Validate restriction conflicts
            conflicts = self._detect_restriction_conflicts(restrictions)
            if conflicts:
                logger.warning(f"Detected restriction conflicts for {user_id}: {conflicts}")
            
            # Apply cultural defaults
            cultural_preferences = self._get_cultural_defaults(cultural_background)
            
            profile = DietaryProfile(
                user_id=user_id,
                restrictions=restrictions,
                allergies=initial_allergies or [],
                preferences={},
                cuisine_preferences=cultural_preferences,
                macro_preferences=self._get_default_macro_preferences(),
                meal_timing_preferences=self._get_default_timing_preferences(),
                cultural_dietary_needs=self._get_cultural_dietary_needs(cultural_background),
                health_conditions=health_conditions or [],
                created_at=now,
                last_updated=now
            )
            
            self.preference_cache[user_id] = profile
            self._save_profile_to_storage(profile)
            
            logger.info(f"Created dietary profile for user {user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Error creating user profile {user_id}: {e}")
            raise

    def update_food_preference(
        self,
        user_id: str,
        food_item: str,
        preference_strength: int,
        category: str = "general",
        learned: bool = False
    ) -> bool:
        """
        Update or create food preference with learning metadata.
        
        Args:
            user_id: User identifier
            food_item: Food item name
            preference_strength: Strength (1-5)
            category: Food category
            learned: Whether preference was learned automatically
            
        Returns:
            Success status
        """
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                logger.error(f"Profile not found for user {user_id}")
                return False
            
            strength = PreferenceStrength(preference_strength)
            now = datetime.utcnow()
            
            # Update existing or create new preference
            if food_item in profile.preferences:
                existing = profile.preferences[food_item]
                existing.strength = strength
                existing.last_updated = now
                existing.interaction_count += 1
                existing.learned = learned
                # Increase confidence with more interactions
                existing.confidence_score = min(1.0, existing.confidence_score + 0.1)
            else:
                profile.preferences[food_item] = FoodPreference(
                    food_item=food_item,
                    strength=strength,
                    category=category,
                    last_updated=now,
                    confidence_score=0.8 if learned else 0.6,
                    interaction_count=1,
                    learned=learned
                )
            
            profile.last_updated = now
            self._save_profile_to_storage(profile)
            
            logger.info(f"Updated preference for {user_id}: {food_item} -> {strength.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating food preference: {e}")
            return False

    def learn_preferences_from_feedback(
        self,
        user_id: str,
        meal_feedback: Dict[str, Any]
    ) -> int:
        """
        Learn user preferences from meal feedback using ML algorithms.
        
        Args:
            user_id: User identifier
            meal_feedback: Feedback data with ratings and comments
            
        Returns:
            Number of preferences learned
        """
        try:
            learned_count = 0
            profile = self.get_user_profile(user_id)
            if not profile:
                return 0
            
            # Extract preferences from feedback
            rating = meal_feedback.get('rating', 3)
            ingredients = meal_feedback.get('ingredients', [])
            cuisine = meal_feedback.get('cuisine', '')
            
            # Learn ingredient preferences
            for ingredient in ingredients:
                if ingredient and len(ingredient) > 2:
                    # Convert rating to preference strength
                    if rating >= 4:
                        strength = PreferenceStrength.LIKE
                    elif rating <= 2:
                        strength = PreferenceStrength.DISLIKE
                    else:
                        strength = PreferenceStrength.NEUTRAL
                    
                    if self.update_food_preference(
                        user_id, ingredient, strength.value, "ingredient", learned=True
                    ):
                        learned_count += 1
            
            # Learn cuisine preferences
            if cuisine:
                current_score = profile.cuisine_preferences.get(cuisine, 0.5)
                adjustment = (rating - 3) * 0.1  # Scale rating to adjustment
                new_score = max(0.0, min(1.0, current_score + adjustment))
                profile.cuisine_preferences[cuisine] = new_score
                learned_count += 1
            
            logger.info(f"Learned {learned_count} preferences from feedback for {user_id}")
            return learned_count
            
        except Exception as e:
            logger.error(f"Error learning preferences from feedback: {e}")
            return 0

    def get_recommendation_weights(self, user_id: str) -> Dict[str, float]:
        """
        Generate recommendation weights based on user preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of food items and their recommendation weights
        """
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return {}
            
            weights = {}
            
            # Convert preferences to weights
            for food_item, preference in profile.preferences.items():
                # Base weight from preference strength
                base_weight = preference.strength.value / 5.0
                
                # Adjust by confidence score
                confidence_adjustment = preference.confidence_score
                
                # Boost recently updated preferences
                days_old = (datetime.utcnow() - preference.last_updated).days
                recency_boost = max(0.1, 1.0 - (days_old / 365.0))
                
                final_weight = base_weight * confidence_adjustment * recency_boost
                weights[food_item] = final_weight
            
            return weights
            
        except Exception as e:
            logger.error(f"Error generating recommendation weights: {e}")
            return {}

    def validate_meal_against_restrictions(
        self,
        user_id: str,
        meal_ingredients: List[str],
        nutritional_info: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate meal against user's dietary restrictions and allergies.
        
        Args:
            user_id: User identifier
            meal_ingredients: List of meal ingredients
            nutritional_info: Nutritional information
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return True, []
            
            violations = []
            
            # Check allergies
            for allergen in profile.allergies:
                for ingredient in meal_ingredients:
                    if allergen.lower() in ingredient.lower():
                        violations.append(f"Contains allergen: {allergen}")
            
            # Check dietary restrictions
            for restriction in profile.restrictions:
                violation = self._check_restriction_violation(
                    restriction, meal_ingredients, nutritional_info
                )
                if violation:
                    violations.append(violation)
            
            # Check health condition restrictions
            for condition in profile.health_conditions:
                violation = self._check_health_condition_restriction(
                    condition, nutritional_info
                )
                if violation:
                    violations.append(violation)
            
            is_valid = len(violations) == 0
            return is_valid, violations
            
        except Exception as e:
            logger.error(f"Error validating meal restrictions: {e}")
            return False, [f"Validation error: {e}"]

    def _build_restriction_conflicts(self) -> Dict[DietaryRestriction, List[DietaryRestriction]]:
        """Build map of conflicting dietary restrictions."""
        return {
            DietaryRestriction.VEGAN: [DietaryRestriction.KETO],
            DietaryRestriction.KETO: [DietaryRestriction.VEGAN],
            DietaryRestriction.PALEO: [DietaryRestriction.VEGETARIAN, DietaryRestriction.VEGAN]
        }

    def _build_cultural_mappings(self) -> Dict[str, Dict[str, float]]:
        """Build cultural cuisine preference mappings."""
        return {
            "mediterranean": {"mediterranean": 0.9, "italian": 0.7, "greek": 0.8},
            "asian": {"chinese": 0.8, "japanese": 0.7, "thai": 0.6, "korean": 0.7},
            "latin": {"mexican": 0.8, "spanish": 0.7, "brazilian": 0.6},
            "middle_eastern": {"lebanese": 0.8, "turkish": 0.7, "persian": 0.6},
            "indian": {"indian": 0.9, "thai": 0.5, "pakistani": 0.7}
        }

    def _detect_restriction_conflicts(self, restrictions: Set[DietaryRestriction]) -> List[str]:
        """Detect conflicts between dietary restrictions."""
        conflicts = []
        for restriction in restrictions:
            if restriction in self.restriction_conflicts:
                for conflicting in self.restriction_conflicts[restriction]:
                    if conflicting in restrictions:
                        conflicts.append(f"{restriction.value} conflicts with {conflicting.value}")
        return conflicts

    def _get_cultural_defaults(self, cultural_background: Optional[str]) -> Dict[str, float]:
        """Get default cuisine preferences based on cultural background."""
        if not cultural_background or cultural_background not in self.cultural_mappings:
            return {"american": 0.5, "international": 0.5}
        return self.cultural_mappings[cultural_background].copy()

    def _get_default_macro_preferences(self) -> Dict[str, float]:
        """Get default macro preference ratios."""
        return {
            "protein_preference": 0.3,
            "carb_preference": 0.4,
            "fat_preference": 0.3,
            "fiber_importance": 0.8,
            "sugar_tolerance": 0.3
        }

    def _get_default_timing_preferences(self) -> Dict[str, Any]:
        """Get default meal timing preferences."""
        return {
            "breakfast_time": "07:00",
            "lunch_time": "12:00",
            "dinner_time": "18:00",
            "snack_frequency": 2,
            "eating_window": 12,  # hours
            "late_night_eating": False
        }

    def _get_cultural_dietary_needs(self, cultural_background: Optional[str]) -> List[str]:
        """Get specific dietary needs based on cultural background."""
        cultural_needs = {
            "mediterranean": ["olive_oil_preference", "fresh_herbs"],
            "asian": ["rice_staple", "soy_products", "seafood_preference"],
            "indian": ["spice_tolerance", "vegetarian_options", "dairy_products"],
            "latin": ["beans_legumes", "corn_products", "spicy_tolerance"],
            "middle_eastern": ["lamb_preference", "nuts_seeds", "dried_fruits"]
        }
        return cultural_needs.get(cultural_background, [])

    def _check_restriction_violation(
        self,
        restriction: DietaryRestriction,
        ingredients: List[str],
        nutrition: Dict[str, Any]
    ) -> Optional[str]:
        """Check if meal violates specific dietary restriction."""
        ingredient_text = " ".join(ingredients).lower()
        
        violations = {
            DietaryRestriction.VEGETARIAN: ["meat", "chicken", "beef", "pork", "fish"],
            DietaryRestriction.VEGAN: ["meat", "dairy", "egg", "honey", "cheese", "milk"],
            DietaryRestriction.GLUTEN_FREE: ["wheat", "gluten", "barley", "rye"],
            DietaryRestriction.DAIRY_FREE: ["milk", "cheese", "yogurt", "butter", "cream"],
            DietaryRestriction.NUT_FREE: ["nuts", "almond", "peanut", "walnut", "cashew"],
            DietaryRestriction.SHELLFISH_FREE: ["shrimp", "lobster", "crab", "shellfish"]
        }
        
        if restriction in violations:
            for forbidden in violations[restriction]:
                if forbidden in ingredient_text:
                    return f"Contains {forbidden} (violates {restriction.value})"
        
        # Check nutritional restrictions
        if restriction == DietaryRestriction.LOW_SODIUM:
            sodium = nutrition.get("sodium", 0)
            if sodium > 1500:  # mg per serving
                return f"High sodium content: {sodium}mg (violates low sodium)"
        
        if restriction == DietaryRestriction.KETO:
            carbs = nutrition.get("carbohydrates", 0)
            if carbs > 20:  # grams per serving
                return f"High carb content: {carbs}g (violates keto)"
        
        return None

    def _check_health_condition_restriction(
        self,
        condition: str,
        nutrition: Dict[str, Any]
    ) -> Optional[str]:
        """Check nutritional restrictions based on health conditions."""
        condition_limits = {
            "diabetes": {"sugar": 25, "carbohydrates": 45},
            "hypertension": {"sodium": 1200},
            "heart_disease": {"saturated_fat": 13, "cholesterol": 200},
            "kidney_disease": {"protein": 50, "sodium": 1000, "potassium": 2000}
        }
        
        if condition.lower() in condition_limits:
            limits = condition_limits[condition.lower()]
            for nutrient, limit in limits.items():
                value = nutrition.get(nutrient, 0)
                if value > limit:
                    return f"High {nutrient}: {value} (limit: {limit} for {condition})"
        
        return None

    def _load_profile_from_storage(self, user_id: str) -> Optional[DietaryProfile]:
        """Load profile from persistent storage (placeholder for database)."""
        # In production, this would query a database
        # For now, return None to indicate not found
        return None

    def _save_profile_to_storage(self, profile: DietaryProfile) -> bool:
        """Save profile to persistent storage (placeholder for database)."""
        # In production, this would save to a database
        # For now, just log the save operation
        logger.info(f"Saved profile for user {profile.user_id}")
        return True
