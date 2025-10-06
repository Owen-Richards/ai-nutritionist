"""
Premium Features Service - Manages premium feature access and upselling
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PremiumFeature(Enum):
    """Premium features available to users."""
    UNLIMITED_PLANS = "unlimited_plans"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    FAMILY_COORDINATION = "family_coordination"
    VOICE_PLANNING = "voice_planning"
    CALENDAR_SYNC = "calendar_sync"
    GROCERY_INTEGRATION = "grocery_integration"
    ADVANCED_ANALYTICS = "advanced_analytics"


class PremiumFeaturesService:
    """Manages premium feature access and upselling."""
    
    def __init__(self):
        self.feature_limits = {
            'free': {
                'meal_plans_per_month': 3,
                'nutrition_analysis': False,
                'family_coordination': False,
                'voice_planning': False,
                'calendar_sync': False,
                'grocery_integration': False,
                'advanced_analytics': False
            },
            'premium': {
                'meal_plans_per_month': None,  # Unlimited
                'nutrition_analysis': True,
                'family_coordination': True,
                'voice_planning': True,
                'calendar_sync': True,
                'grocery_integration': True,
                'advanced_analytics': False
            },
            'enterprise': {
                'meal_plans_per_month': None,  # Unlimited
                'nutrition_analysis': True,
                'family_coordination': True,
                'voice_planning': True,
                'calendar_sync': True,
                'grocery_integration': True,
                'advanced_analytics': True
            }
        }
    
    def check_feature_access(self, user_tier: str, feature: str) -> bool:
        """Check if user has access to a premium feature."""
        tier_features = self.feature_limits.get(user_tier.lower(), self.feature_limits['free'])
        return tier_features.get(feature, False)
    
    def get_usage_limit(self, user_tier: str, feature: str) -> Optional[int]:
        """Get usage limit for a feature."""
        tier_features = self.feature_limits.get(user_tier.lower(), self.feature_limits['free'])
        return tier_features.get(feature)
    
    def generate_upsell_message(self, feature: str, user_tier: str = 'free') -> str:
        """Generate upsell message for a premium feature."""
        
        feature_messages = {
            'unlimited_plans': {
                'title': '🔓 Unlock Unlimited Meal Plans',
                'description': 'Create as many meal plans as you want with Premium',
                'cta': 'Upgrade to Premium for $7.99/month'
            },
            'nutrition_analysis': {
                'title': '📊 Advanced Nutrition Analysis',
                'description': 'Get detailed nutritional breakdowns, macro tracking, and health insights',
                'cta': 'Upgrade to Premium for $7.99/month'
            },
            'family_coordination': {
                'title': '👨‍👩‍👧‍👦 Family Meal Coordination',
                'description': 'Plan meals for your whole family with shared calendars and preferences',
                'cta': 'Upgrade to Premium for $7.99/month'
            },
            'voice_planning': {
                'title': '🎤 Voice Meal Planning',
                'description': 'Plan meals hands-free with voice commands and smart suggestions',
                'cta': 'Upgrade to Premium for $7.99/month'
            },
            'calendar_sync': {
                'title': '📅 Calendar Integration',
                'description': 'Sync meal plans with Google Calendar and Outlook',
                'cta': 'Upgrade to Premium for $7.99/month'
            },
            'grocery_integration': {
                'title': '🛒 Smart Grocery Integration',
                'description': 'Auto-generate shopping lists and order ingredients online',
                'cta': 'Upgrade to Premium for $7.99/month'
            },
            'advanced_analytics': {
                'title': '📈 Advanced Analytics & API',
                'description': 'Get detailed insights and API access for your team',
                'cta': 'Upgrade to Enterprise for $99/month'
            }
        }
        
        feature_info = feature_messages.get(feature, feature_messages['unlimited_plans'])
        
        return f"""
{feature_info['title']}

{feature_info['description']}

✨ {feature_info['cta']}

Reply 'upgrade' to get started!
"""
    
    def get_available_upgrades(self, current_tier: str) -> List[str]:
        """Get list of features available with upgrade."""
        current_features = self.feature_limits.get(current_tier.lower(), self.feature_limits['free'])
        
        upgrade_features = []
        
        if current_tier.lower() == 'free':
            premium_features = self.feature_limits['premium']
            for feature, enabled in premium_features.items():
                if enabled and not current_features.get(feature, False):
                    upgrade_features.append(feature)
        
        elif current_tier.lower() == 'premium':
            enterprise_features = self.feature_limits['enterprise']
            for feature, enabled in enterprise_features.items():
                if enabled and not current_features.get(feature, False):
                    upgrade_features.append(feature)
        
        return upgrade_features
    
    def track_feature_usage(self, user_id: str, feature: str) -> Dict[str, Any]:
        """Track premium feature usage for analytics."""
        usage_event = {
            'user_id': user_id,
            'feature': feature,
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'feature_access_attempt'
        }
        
        # In production, send to analytics service
        logger.info(f"Feature usage tracked: {usage_event}")
        
        return usage_event
    
    def should_show_upsell(self, user_tier: str, feature: str, usage_count: int = 0) -> bool:
        """Determine if upsell should be shown to user."""
        
        # Don't show upsells to enterprise users
        if user_tier.lower() == 'enterprise':
            return False
        
        # Show upsell if feature is not available in current tier
        if not self.check_feature_access(user_tier, feature):
            return True
        
        # Show upsell if user is approaching limits
        limit = self.get_usage_limit(user_tier, feature)
        if limit is not None and usage_count >= limit * 0.8:
            return True
        
        return False
