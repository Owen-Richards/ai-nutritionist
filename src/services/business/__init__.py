"""
Business Domain Package

This package contains all business logic and revenue services:
- subscription.py: Subscription management and billing (SubscriptionService)
- revenue.py: Affiliate revenue optimization (AffiliateRevenueService)
- compliance.py: Premium features and compliance (PremiumFeaturesService)
- partnerships.py: Grocery partnerships (AffiliateGroceryService)
- cost_tracking.py: User cost monitoring (UserCostTracker)
- profit_enforcement.py: Profit enforcement (ProfitEnforcementService)
- profit_guarantee.py: Guaranteed profit service (ProfitEnforcementService)
- brand_endorsement.py: Brand partnerships (BrandEndorsementService)
- revenue_integration.py: Revenue integration (RevenueIntegrationHandler)
"""

from .subscription import SubscriptionService
from .revenue import AffiliateRevenueService as RevenueOptimizationService
from .compliance import PremiumFeaturesService as ComplianceSecurityService
from .partnerships import AffiliateGroceryService as PartnershipService
from .cost_tracking import UserCostTracker
from .profit_enforcement import ProfitEnforcementService
from .profit_guarantee import ProfitEnforcementService as ProfitGuaranteeService
from .brand_endorsement import BrandEndorsementService
from .revenue_integration import RevenueIntegrationHandler

__all__ = [
    'SubscriptionService',
    'RevenueOptimizationService',
    'ComplianceSecurityService',
    'PartnershipService',
    'UserCostTracker',
    'ProfitEnforcementService',
    'ProfitGuaranteeService',
    'BrandEndorsementService',
    'RevenueIntegrationHandler'
]
