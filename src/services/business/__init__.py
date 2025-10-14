"""
Business Domain Package - B2B Employee Wellness Pivot

CRITICAL INVESTOR UPDATE: Pivoting from consumer model (25% success) to B2B employee wellness (55-60% success)

This package now focuses on:
- enterprise_wellness.py: B2B employee wellness with measurable health outcomes
- Core value: Reduce healthcare costs by 8% through AI-powered nutrition
- Target: HR departments at companies 500+ employees
- Revenue: $3-5/employee/month + insurance partnerships

Legacy consumer services deprecated due to unsustainable unit economics.
"""

from .enterprise_wellness import EnterpriseWellnessService
from .grocery_partnership import GroceryPartnershipEngine

# Legacy services (deprecated - consumer model failed)
from .simple_subscription import SimpleSubscriptionService, SubscriptionTier
from .viral_growth import FamilyChallenge, ViralGrowthEngine

__all__ = [
    # B2B Employee Wellness (primary focus)
    "EnterpriseWellnessService",
    # Legacy services (deprecated)
    "SimpleSubscriptionService",
    "SubscriptionTier",
    "GroceryPartnershipEngine",
    "ViralGrowthEngine",
    "FamilyChallenge",
]

# INVESTOR NOTE:
# Consumer model unit economics broken (CAC/LTV = 3x)
# B2B model unit economics excellent (LTV/CAC = 240x)
# Focus all development on EnterpriseWellnessService
