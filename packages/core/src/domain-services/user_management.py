"""
Pure domain service for user management logic
Separated from infrastructure concerns following hexagonal architecture
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from packages.core.src.interfaces.repositories import UserRepository
from packages.core.src.interfaces.services import AnalyticsService
from packages.core.src.interfaces.domain import (
    UserProfile,
    UserTier,
    NutritionProfile,
    DietaryRestriction,
    HealthGoal,
    DomainService
)

logger = logging.getLogger(__name__)


class UserManagementService(DomainService):
    """Pure domain service for user management - no infrastructure dependencies"""
    
    def __init__(
        self,
        user_repo: UserRepository,
        analytics_service: AnalyticsService
    ):
        self.user_repo = user_repo
        self.analytics = analytics_service
    
    def validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Validate user-specific business rules"""
        # Validate phone number format
        if 'phone_number' in data:
            if not self._is_valid_phone_number(data['phone_number']):
                return False
        
        # Validate user tier transitions
        if 'current_tier' in data and 'new_tier' in data:
            if not self._is_valid_tier_transition(data['current_tier'], data['new_tier']):
                return False
        
        return True
    
    async def get_or_create_user(self, phone_number: str) -> Dict[str, Any]:
        """Get existing user or create new user profile using domain logic"""
        try:
            # Normalize phone number using domain rules
            normalized_phone = self._normalize_phone_number(phone_number)
            
            # Try to get existing user
            existing_user = await self.user_repo.get_user_by_phone(normalized_phone)
            
            if existing_user:
                # Update last active
                await self.user_repo.update_user(normalized_phone, {
                    'last_active': datetime.utcnow().isoformat()
                })
                
                existing_user['is_new_user'] = False
                logger.info(f"Retrieved existing user: {normalized_phone}")
                return existing_user
            
            # Create new user using domain logic
            new_user = self._create_new_user_profile(normalized_phone)
            created_user = await self.user_repo.create_user(new_user)
            
            # Track user creation event
            await self.analytics.track_user_event(
                user_id=normalized_phone,
                event='user_created',
                properties={'tier': 'free', 'source': 'direct'}
            )
            
            created_user['is_new_user'] = True
            logger.info(f"Created new user: {normalized_phone}")
            return created_user
        
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            raise
    
    async def update_user_preferences(self, phone_number: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences using domain validation"""
        try:
            # Validate preferences using domain rules
            if not self._validate_user_preferences(preferences):
                logger.warning(f"Invalid preferences for user {phone_number}")
                return False
            
            # Normalize and process preferences
            processed_preferences = self._process_user_preferences(preferences)
            
            # Update user
            success = await self.user_repo.update_user(phone_number, processed_preferences)
            
            if success:
                # Track preference update
                await self.analytics.track_user_event(
                    user_id=phone_number,
                    event='preferences_updated',
                    properties={'preferences': list(processed_preferences.keys())}
                )
            
            return success
        
        except Exception as e:
            logger.error(f"Error updating preferences for {phone_number}: {e}")
            return False
    
    async def upgrade_user_tier(self, phone_number: str, new_tier: str, subscription_data: Dict[str, Any] = None) -> bool:
        """Upgrade user tier using domain business rules"""
        try:
            # Validate tier upgrade
            current_user = await self.user_repo.get_user_by_phone(phone_number)
            if not current_user:
                logger.error(f"User not found for tier upgrade: {phone_number}")
                return False
            
            current_tier = current_user.get('premium_tier', 'free')
            
            # Check if upgrade is valid using domain rules
            if not self._is_valid_tier_transition(current_tier, new_tier):
                logger.warning(f"Invalid tier transition from {current_tier} to {new_tier}")
                return False
            
            # Prepare upgrade data
            upgrade_data = {
                'premium_tier': new_tier,
                'tier_upgraded_at': datetime.utcnow().isoformat()
            }
            
            if subscription_data:
                upgrade_data.update({
                    'subscription_id': subscription_data.get('subscription_id'),
                    'subscription_status': subscription_data.get('status', 'active'),
                    'subscription_expires': subscription_data.get('expires_at')
                })
            
            # Perform upgrade
            success = await self.user_repo.update_user(phone_number, upgrade_data)
            
            if success:
                # Track tier upgrade
                await self.analytics.track_user_event(
                    user_id=phone_number,
                    event='tier_upgraded',
                    properties={
                        'from_tier': current_tier,
                        'to_tier': new_tier,
                        'subscription_id': subscription_data.get('subscription_id') if subscription_data else None
                    }
                )
            
            return success
        
        except Exception as e:
            logger.error(f"Error upgrading tier for {phone_number}: {e}")
            return False
    
    async def get_user_analytics_profile(self, phone_number: str) -> Dict[str, Any]:
        """Get user analytics profile using domain calculations"""
        try:
            user = await self.user_repo.get_user_by_phone(phone_number)
            if not user:
                return {}
            
            # Calculate user engagement metrics using domain logic
            created_at = datetime.fromisoformat(user.get('created_at', datetime.utcnow().isoformat()))
            last_active = datetime.fromisoformat(user.get('last_active', datetime.utcnow().isoformat()))
            
            days_since_registration = (datetime.utcnow() - created_at).days
            days_since_last_active = (datetime.utcnow() - last_active).days
            
            # Calculate engagement score using domain rules
            engagement_score = self._calculate_engagement_score(user)
            
            # Calculate user lifecycle stage
            lifecycle_stage = self._determine_lifecycle_stage(user, days_since_registration, days_since_last_active)
            
            # Calculate user value score
            value_score = self._calculate_user_value_score(user)
            
            return {
                'user_id': phone_number,
                'tier': user.get('premium_tier', 'free'),
                'days_since_registration': days_since_registration,
                'days_since_last_active': days_since_last_active,
                'engagement_score': engagement_score,
                'lifecycle_stage': lifecycle_stage,
                'value_score': value_score,
                'total_meals_planned': user.get('total_meals_planned', 0),
                'preferred_cuisines': user.get('preferred_cuisines', []),
                'dietary_restrictions': user.get('dietary_restrictions', [])
            }
        
        except Exception as e:
            logger.error(f"Error getting analytics profile for {phone_number}: {e}")
            return {}
    
    def _create_new_user_profile(self, phone_number: str) -> Dict[str, Any]:
        """Create new user profile using domain defaults"""
        now = datetime.utcnow().isoformat()
        
        return {
            'user_id': phone_number,
            'plan_date': 'profile',
            'phone_number': phone_number,
            'premium_tier': 'free',
            'created_at': now,
            'last_active': now,
            'is_active': True,
            'dietary_restrictions': [],
            'health_goals': [],
            'allergies': [],
            'dislikes': [],
            'max_prep_time': 45,
            'budget_preference': 'medium',
            'preferred_cuisines': [],
            'total_meals_planned': 0,
            'total_messages_sent': 0,
            'onboarding_completed': False,
            'notification_preferences': {
                'meal_reminders': True,
                'weekly_tips': True,
                'promotional': False
            }
        }
    
    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number using domain rules"""
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Handle different country formats
        if digits_only.startswith('1') and len(digits_only) == 11:
            # US/Canada format: remove leading 1
            return digits_only[1:]
        elif len(digits_only) == 10:
            # Standard 10-digit format
            return digits_only
        else:
            # Keep as-is for international numbers
            return digits_only
    
    def _is_valid_phone_number(self, phone: str) -> bool:
        """Validate phone number format using domain rules"""
        normalized = self._normalize_phone_number(phone)
        
        # Must be at least 10 digits for valid phone number
        if len(normalized) < 10:
            return False
        
        # Must be all digits
        if not normalized.isdigit():
            return False
        
        return True
    
    def _is_valid_tier_transition(self, current_tier: str, new_tier: str) -> bool:
        """Validate tier transition using domain business rules"""
        tier_hierarchy = {
            'free': 0,
            'premium': 1,
            'family': 2,
            'enterprise': 3
        }
        
        current_level = tier_hierarchy.get(current_tier, -1)
        new_level = tier_hierarchy.get(new_tier, -1)
        
        # Cannot downgrade (except to free for cancellation)
        if new_level < current_level and new_tier != 'free':
            return False
        
        # Cannot skip levels (except for enterprise)
        if new_level - current_level > 1 and new_tier != 'enterprise':
            return False
        
        return current_level >= 0 and new_level >= 0
    
    def _validate_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Validate user preferences using domain rules"""
        # Validate dietary restrictions
        if 'dietary_restrictions' in preferences:
            valid_restrictions = [dr.value for dr in DietaryRestriction]
            for restriction in preferences['dietary_restrictions']:
                if restriction not in valid_restrictions:
                    return False
        
        # Validate health goals
        if 'health_goals' in preferences:
            valid_goals = [hg.value for hg in HealthGoal]
            for goal in preferences['health_goals']:
                if goal not in valid_goals:
                    return False
        
        # Validate prep time
        if 'max_prep_time' in preferences:
            prep_time = preferences['max_prep_time']
            if not isinstance(prep_time, int) or prep_time < 5 or prep_time > 240:
                return False
        
        return True
    
    def _process_user_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize user preferences"""
        processed = {}
        
        for key, value in preferences.items():
            if key == 'dietary_restrictions':
                # Ensure unique values
                processed[key] = list(set(value)) if isinstance(value, list) else value
            elif key == 'health_goals':
                # Ensure unique values
                processed[key] = list(set(value)) if isinstance(value, list) else value
            elif key == 'max_prep_time':
                # Ensure reasonable bounds
                processed[key] = max(5, min(240, int(value)))
            else:
                processed[key] = value
        
        return processed
    
    def _calculate_engagement_score(self, user: Dict[str, Any]) -> float:
        """Calculate user engagement score using domain logic"""
        score = 0.0
        
        # Meal planning activity (40% of score)
        meals_planned = user.get('total_meals_planned', 0)
        score += min(0.4, meals_planned * 0.01)
        
        # Profile completeness (30% of score)
        profile_fields = ['dietary_restrictions', 'health_goals', 'preferred_cuisines']
        completed_fields = sum(1 for field in profile_fields if user.get(field))
        score += (completed_fields / len(profile_fields)) * 0.3
        
        # Recent activity (30% of score)
        if user.get('last_active'):
            last_active = datetime.fromisoformat(user['last_active'])
            days_since_active = (datetime.utcnow() - last_active).days
            if days_since_active <= 7:
                score += 0.3
            elif days_since_active <= 30:
                score += 0.15
        
        return min(1.0, score)
    
    def _determine_lifecycle_stage(self, user: Dict[str, Any], days_since_registration: int, days_since_last_active: int) -> str:
        """Determine user lifecycle stage using domain rules"""
        if days_since_registration <= 7:
            return 'new'
        elif days_since_last_active <= 7:
            return 'active'
        elif days_since_last_active <= 30:
            return 'at_risk'
        elif days_since_last_active <= 90:
            return 'dormant'
        else:
            return 'churned'
    
    def _calculate_user_value_score(self, user: Dict[str, Any]) -> float:
        """Calculate user value score using domain logic"""
        score = 0.0
        
        # Tier value
        tier_values = {'free': 0.1, 'premium': 0.5, 'family': 0.7, 'enterprise': 1.0}
        score += tier_values.get(user.get('premium_tier', 'free'), 0.1)
        
        # Usage intensity
        meals_planned = user.get('total_meals_planned', 0)
        if meals_planned > 50:
            score += 0.3
        elif meals_planned > 20:
            score += 0.2
        elif meals_planned > 5:
            score += 0.1
        
        # Longevity
        if user.get('created_at'):
            created_at = datetime.fromisoformat(user['created_at'])
            days_active = (datetime.utcnow() - created_at).days
            if days_active > 365:
                score += 0.2
            elif days_active > 90:
                score += 0.1
        
        return min(1.0, score)
