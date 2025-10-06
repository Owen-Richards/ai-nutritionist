"""Entitlement middleware for Track E2.

Provides feature access control and usage tracking based on subscription tiers.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Dict, Optional, Union
from uuid import UUID

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...models.monetization import (
    FeatureFlag,
    MonetizationConfig,
    Subscription,
    SubscriptionTier,
    TierDefinition,
    UsageTracker
)
from .billing_service import BillingService

logger = logging.getLogger(__name__)


class EntitlementCache:
    """Cache for entitlement checks to reduce database queries."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute cache
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict] = {}
    
    def _get_cache_key(self, user_id: UUID, feature: FeatureFlag) -> str:
        """Generate cache key for entitlement check."""
        return f"entitlement:{user_id}:{feature.value}"
    
    def get(self, user_id: UUID, feature: FeatureFlag) -> Optional[Dict]:
        """Get cached entitlement result."""
        key = self._get_cache_key(user_id, feature)
        cached = self._cache.get(key)
        
        if cached and cached["expires_at"] > self._current_timestamp():
            return cached["data"]
        
        # Remove expired entry
        if cached:
            del self._cache[key]
        
        return None
    
    def set(self, user_id: UUID, feature: FeatureFlag, data: Dict) -> None:
        """Cache entitlement result."""
        key = self._get_cache_key(user_id, feature)
        self._cache[key] = {
            "data": data,
            "expires_at": self._current_timestamp() + self.ttl_seconds
        }
    
    def invalidate(self, user_id: UUID, feature: Optional[FeatureFlag] = None) -> None:
        """Invalidate cache for user (all features or specific feature)."""
        if feature:
            key = self._get_cache_key(user_id, feature)
            self._cache.pop(key, None)
        else:
            # Invalidate all features for user
            keys_to_remove = [
                key for key in self._cache.keys() 
                if key.startswith(f"entitlement:{user_id}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]
    
    def _current_timestamp(self) -> int:
        """Get current timestamp."""
        from time import time
        return int(time())


class EntitlementService:
    """Service for checking feature entitlements and usage limits."""
    
    def __init__(self, billing_service: BillingService):
        self.billing_service = billing_service
        self.monetization_config = MonetizationConfig()
        self.cache = EntitlementCache()
    
    def check_feature_access(self, user_id: UUID, feature: FeatureFlag,
                           bypass_cache: bool = False) -> Dict:
        """Check if user has access to a feature."""
        
        # Check cache first
        if not bypass_cache:
            cached_result = self.cache.get(user_id, feature)
            if cached_result:
                return cached_result
        
        # Get user's subscription
        subscription = self.billing_service.get_subscription(user_id)
        if not subscription:
            # Default to free tier for users without subscription
            tier = SubscriptionTier.FREE
            is_active = True
        else:
            tier = subscription.tier
            is_active = subscription.is_active
        
        # Get tier definition
        tier_definition = self.monetization_config.get_tier_definition(tier)
        
        # Check if feature is available in tier
        entitlement = tier_definition.get_feature_entitlement(feature)
        
        result = {
            "has_access": False,
            "tier": tier.value,
            "feature": feature.value,
            "is_subscription_active": is_active,
            "limit": None,
            "usage": 0,
            "remaining": None,
            "upgrade_required": False,
            "trial_eligible": False,
            "metadata": {}
        }
        
        if not entitlement or not entitlement.enabled:
            # Feature not available in current tier
            result["upgrade_required"] = True
            result["trial_eligible"] = self._is_trial_eligible(user_id, tier)
        elif not is_active:
            # Subscription inactive
            result["upgrade_required"] = True
        else:
            # Feature is available, check usage limits
            result["has_access"] = True
            result["limit"] = entitlement.limit
            result["metadata"] = entitlement.metadata
            
            # Check usage if there's a limit
            if entitlement.limit is not None:
                usage_tracker = self.billing_service.get_usage_tracker(user_id)
                if usage_tracker:
                    current_usage = usage_tracker.get_usage(feature)
                    result["usage"] = current_usage
                    result["remaining"] = max(0, entitlement.limit - current_usage)
                    
                    # Block access if limit exceeded
                    if current_usage >= entitlement.limit:
                        result["has_access"] = False
                        result["upgrade_required"] = True
        
        # Cache the result
        if not bypass_cache:
            self.cache.set(user_id, feature, result)
        
        return result
    
    def check_usage_limit(self, user_id: UUID, feature: FeatureFlag,
                         increment_by: int = 1) -> Dict:
        """Check if user can use a feature (considering usage limits)."""
        access_check = self.check_feature_access(user_id, feature)
        
        if not access_check["has_access"]:
            return access_check
        
        # Check if increment would exceed limit
        if access_check["limit"] is not None:
            remaining = access_check["remaining"] or 0
            if increment_by > remaining:
                access_check["has_access"] = False
                access_check["upgrade_required"] = True
                access_check["error"] = f"Usage limit exceeded. {remaining} remaining."
        
        return access_check
    
    def increment_usage(self, user_id: UUID, feature: FeatureFlag,
                       amount: int = 1) -> None:
        """Increment usage counter for a feature."""
        usage_tracker = self.billing_service.get_usage_tracker(user_id)
        if usage_tracker:
            usage_tracker.increment_usage(feature, amount)
            
            # Invalidate cache for this feature
            self.cache.invalidate(user_id, feature)
    
    def get_tier_comparison(self, current_tier: SubscriptionTier) -> Dict:
        """Get comparison of features across tiers for upgrade prompts."""
        all_tiers = self.monetization_config.get_all_tiers()
        
        comparison = {
            "current_tier": current_tier.value,
            "tiers": {},
            "upgrade_options": []
        }
        
        for tier_def in all_tiers:
            tier_info = {
                "name": tier_def.name,
                "description": tier_def.description,
                "pricing": {
                    "monthly_usd": float(tier_def.pricing.monthly_price_usd),
                    "yearly_usd": float(tier_def.pricing.yearly_price_usd),
                    "yearly_discount": float(tier_def.pricing.yearly_discount_percent)
                },
                "features": []
            }
            
            for entitlement in tier_def.features:
                feature_info = {
                    "feature": entitlement.feature.value,
                    "enabled": entitlement.enabled,
                    "limit": entitlement.limit,
                    "metadata": entitlement.metadata
                }
                tier_info["features"].append(feature_info)
            
            comparison["tiers"][tier_def.tier.value] = tier_info
            
            # Add to upgrade options if higher tier
            tier_order = [SubscriptionTier.FREE, SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE]
            if tier_order.index(tier_def.tier) > tier_order.index(current_tier):
                comparison["upgrade_options"].append(tier_def.tier.value)
        
        return comparison
    
    def get_usage_summary(self, user_id: UUID) -> Dict:
        """Get comprehensive usage summary for user."""
        subscription = self.billing_service.get_subscription(user_id)
        usage_tracker = self.billing_service.get_usage_tracker(user_id)
        
        if not subscription:
            tier = SubscriptionTier.FREE
        else:
            tier = subscription.tier
        
        tier_definition = self.monetization_config.get_tier_definition(tier)
        
        summary = {
            "user_id": str(user_id),
            "tier": tier.value,
            "billing_period": None,
            "features": {}
        }
        
        if usage_tracker:
            summary["billing_period"] = {
                "start": usage_tracker.period_start.isoformat(),
                "end": usage_tracker.period_end.isoformat()
            }
        
        # Check each feature in the tier
        for entitlement in tier_definition.features:
            feature_usage = {
                "enabled": entitlement.enabled,
                "limit": entitlement.limit,
                "usage": 0,
                "remaining": None
            }
            
            if usage_tracker and entitlement.enabled:
                current_usage = usage_tracker.get_usage(entitlement.feature)
                feature_usage["usage"] = current_usage
                
                if entitlement.limit is not None:
                    feature_usage["remaining"] = max(0, entitlement.limit - current_usage)
            
            summary["features"][entitlement.feature.value] = feature_usage
        
        return summary
    
    def _is_trial_eligible(self, user_id: UUID, current_tier: SubscriptionTier) -> bool:
        """Check if user is eligible for a trial."""
        subscription = self.billing_service.get_subscription(user_id)
        
        # No trial if already has paid subscription
        if subscription and subscription.tier != SubscriptionTier.FREE:
            return False
        
        # No trial if already used trial
        if subscription and subscription.trial_used:
            return False
        
        return True


class EntitlementMiddleware:
    """FastAPI middleware for automatic entitlement checking."""
    
    def __init__(self, entitlement_service: EntitlementService):
        self.entitlement_service = entitlement_service
        self.security = HTTPBearer(auto_error=False)
    
    def require_feature(self, feature: FeatureFlag, 
                       increment_usage: bool = False,
                       usage_amount: int = 1):
        """Decorator to require feature access for endpoint."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request and user_id from function arguments
                request = None
                user_id = None
                
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if "user_id" in kwargs:
                    user_id = kwargs["user_id"]
                elif request:
                    # Try to extract user_id from request
                    user_id = await self._extract_user_id(request)
                
                if not user_id:
                    raise HTTPException(
                        status_code=401, 
                        detail="User authentication required"
                    )
                
                # Check feature access
                if increment_usage:
                    access_check = self.entitlement_service.check_usage_limit(
                        user_id, feature, usage_amount
                    )
                else:
                    access_check = self.entitlement_service.check_feature_access(
                        user_id, feature
                    )
                
                if not access_check["has_access"]:
                    if access_check["upgrade_required"]:
                        raise HTTPException(
                            status_code=402,  # Payment Required
                            detail={
                                "message": f"Feature '{feature.value}' requires subscription upgrade",
                                "feature": feature.value,
                                "current_tier": access_check["tier"],
                                "trial_eligible": access_check["trial_eligible"],
                                "upgrade_options": self.entitlement_service.get_tier_comparison(
                                    SubscriptionTier(access_check["tier"])
                                )["upgrade_options"]
                            }
                        )
                    else:
                        raise HTTPException(
                            status_code=429,  # Too Many Requests
                            detail={
                                "message": f"Usage limit exceeded for '{feature.value}'",
                                "feature": feature.value,
                                "limit": access_check["limit"],
                                "usage": access_check["usage"],
                                "remaining": access_check["remaining"]
                            }
                        )
                
                # Increment usage if requested
                if increment_usage:
                    self.entitlement_service.increment_usage(
                        user_id, feature, usage_amount
                    )
                
                # Call the original function
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def _extract_user_id(self, request: Request) -> Optional[UUID]:
        """Extract user ID from request (implementation depends on auth system)."""
        # This is a placeholder - implement based on your auth system
        user_id_header = request.headers.get("X-User-ID")
        if user_id_header:
            try:
                return UUID(user_id_header)
            except ValueError:
                return None
        
        # Could also extract from JWT token, session, etc.
        return None


# Convenience function to create middleware instance
def create_entitlement_middleware(billing_service: BillingService) -> EntitlementMiddleware:
    """Create entitlement middleware with billing service."""
    entitlement_service = EntitlementService(billing_service)
    return EntitlementMiddleware(entitlement_service)


# Export main classes
__all__ = [
    "EntitlementCache",
    "EntitlementService", 
    "EntitlementMiddleware",
    "create_entitlement_middleware"
]
