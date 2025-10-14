"""
Refactored Business Services - Hexagonal Architecture
This shows how to refactor existing business services to use the new clean architecture
"""

import logging
from typing import Dict, Any, Optional, List

from packages.core.src.interfaces.repositories import BusinessRepository, UserRepository, BrandRepository
from packages.core.src.interfaces.services import AnalyticsService, MonitoringService
from packages.core.src.domain_services.business_logic import BusinessLogicService

logger = logging.getLogger(__name__)


class RefactoredCostOptimizer:
    """
    Refactored version of IntelligentCostOptimizer following hexagonal architecture
    
    BEFORE: Direct DynamoDB/CloudWatch calls mixed with business logic
    AFTER: Clean separation using dependency injection and interfaces
    """
    
    def __init__(
        self,
        business_repo: BusinessRepository,
        user_repo: UserRepository,
        analytics_service: AnalyticsService,
        monitoring_service: MonitoringService
    ):
        # Dependencies injected through interfaces - no direct AWS imports!
        self.business_logic = BusinessLogicService(
            business_repo=business_repo,
            user_repo=user_repo,
            analytics_service=analytics_service,
            monitoring_service=monitoring_service
        )
    
    async def validate_request(self, user_phone: str, request_type: str, message_content: str) -> Dict[str, Any]:
        """
        Validate request for cost optimization using clean architecture
        
        REFACTORING IMPROVEMENTS:
        ✅ No direct DynamoDB calls
        ✅ No direct CloudWatch calls  
        ✅ Pure business logic in domain service
        ✅ Infrastructure concerns abstracted
        """
        result = await self.business_logic.validate_request_cost_optimization(
            user_phone, request_type, message_content
        )
        
        return {
            'is_valid': result.is_valid,
            'confidence': result.confidence,
            'reason': result.reason,
            'estimated_cost': result.estimated_cost,
            'action': result.recommended_action,
            'user_message': result.user_message,
            'metadata': result.metadata
        }
    
    async def track_revenue(self, user_phone: str, event_type: str, amount: float, metadata: Dict[str, Any] = None) -> bool:
        """
        Track revenue event using domain logic
        
        REFACTORING IMPROVEMENTS:
        ✅ Business validation in domain layer
        ✅ Repository pattern for persistence
        ✅ Analytics through interface
        """
        return await self.business_logic.track_revenue_event(user_phone, event_type, amount, metadata)


class RefactoredBrandEndorsementService:
    """
    Refactored version of BrandEndorsementService following hexagonal architecture
    
    BEFORE: Direct DynamoDB calls mixed with business logic  
    AFTER: Clean separation using dependency injection and interfaces
    """
    
    def __init__(
        self,
        brand_repo: BrandRepository,
        user_repo: UserRepository,
        business_repo: BusinessRepository,
        analytics_service: AnalyticsService
    ):
        self.brand_repo = brand_repo
        self.user_repo = user_repo
        self.business_repo = business_repo
        self.analytics = analytics_service
    
    async def generate_brand_recommendations(self, user_phone: str, meal_context: str) -> Dict[str, Any]:
        """
        Generate brand recommendations using clean architecture
        
        REFACTORING IMPROVEMENTS:
        ✅ User data through repository interface
        ✅ Brand matching logic separated from infrastructure
        ✅ Campaign data through repository pattern
        """
        try:
            # Get user preferences through repository
            user_preferences = await self.user_repo.get_user_preferences(user_phone)
            
            # Get active brand campaigns through repository
            campaigns = await self.brand_repo.get_brand_campaigns(active_only=True)
            
            # Apply domain logic for brand matching
            brand_matches = self._match_brands_to_user(user_preferences, meal_context, campaigns)
            
            if brand_matches:
                # Track impression through repository
                impression_id = await self.brand_repo.track_ad_impression({
                    'user_phone': user_phone,
                    'brand_id': brand_matches[0]['brand_id'],
                    'context': meal_context,
                    'match_score': brand_matches[0]['match_score']
                })
                
                return {
                    'recommendations': brand_matches,
                    'impression_id': impression_id
                }
            
            return {'recommendations': []}
        
        except Exception as e:
            logger.error(f"Error generating brand recommendations: {e}")
            return {'recommendations': []}
    
    async def track_ad_interaction(self, impression_id: str, interaction_type: str, conversion_value: float = None) -> Dict[str, Any]:
        """
        Track ad interaction using clean architecture
        
        REFACTORING IMPROVEMENTS:
        ✅ Repository pattern for data access
        ✅ Business logic for revenue calculation
        ✅ Analytics tracking through interface
        """
        try:
            # Get impression details through repository
            impression = await self.brand_repo.get_impression_details(impression_id)
            if not impression:
                return {'success': False, 'error': 'Impression not found'}
            
            # Calculate revenue using domain logic
            revenue = self._calculate_interaction_revenue(interaction_type, conversion_value)
            
            # Track interaction through repository
            interaction_data = {
                'interaction_type': interaction_type,
                'revenue': revenue,
                'conversion_value': conversion_value
            }
            
            success = await self.brand_repo.track_ad_interaction(impression_id, interaction_data)
            
            if success and revenue > 0:
                # Track revenue event through business service
                await self.business_repo.track_revenue_event({
                    'user_phone': impression['user_phone'],
                    'event_type': 'brand_advertising',
                    'revenue_amount': revenue,
                    'currency': 'USD',
                    'metadata': {
                        'impression_id': impression_id,
                        'interaction_type': interaction_type,
                        'brand_id': impression['brand_id']
                    }
                })
            
            return {
                'success': True,
                'revenue_generated': revenue,
                'interaction_type': interaction_type
            }
        
        except Exception as e:
            logger.error(f"Error tracking ad interaction: {e}")
            return {'success': False, 'error': str(e)}
    
    def _match_brands_to_user(self, user_preferences: Dict[str, Any], meal_context: str, campaigns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pure domain logic for brand matching"""
        matches = []
        
        dietary_restrictions = user_preferences.get('dietary_restrictions', [])
        health_goals = user_preferences.get('health_goals', [])
        
        for campaign in campaigns:
            # Calculate match score using domain logic
            match_score = 0.0
            
            # Dietary restriction matching
            campaign_dietary_match = campaign.get('dietary_match', [])
            dietary_overlap = set(dietary_restrictions).intersection(set(campaign_dietary_match))
            match_score += len(dietary_overlap) * 0.3
            
            # Health goal matching  
            campaign_target_audience = campaign.get('target_audience', [])
            goal_overlap = set(health_goals).intersection(set(campaign_target_audience))
            match_score += len(goal_overlap) * 0.4
            
            # Context matching
            if any(keyword in meal_context.lower() for keyword in campaign.get('context_keywords', [])):
                match_score += 0.3
            
            if match_score > 0.3:  # Minimum threshold
                matches.append({
                    'brand_id': campaign['brand_id'],
                    'brand_name': campaign['brand_name'],
                    'match_score': min(1.0, match_score),
                    'category': campaign['category']
                })
        
        # Sort by match score and return top 3
        return sorted(matches, key=lambda x: x['match_score'], reverse=True)[:3]
    
    def _calculate_interaction_revenue(self, interaction_type: str, conversion_value: float = None) -> float:
        """Pure domain logic for revenue calculation"""
        base_rates = {
            'impression': 0.02,
            'click': 0.25,
            'conversion': 15.0,
            'purchase': 0.05  # 5% commission
        }
        
        if interaction_type == 'purchase' and conversion_value:
            return conversion_value * base_rates['purchase']
        
        return base_rates.get(interaction_type, 0.0)


# Usage example showing dependency injection:
"""
# Infrastructure setup (done once at application startup)
from packages.infrastructure.repositories.dynamodb_repositories import (
    DynamoDBBusinessRepository,
    DynamoDBUserRepository,
    DynamoDBBrandRepository
)
from packages.infrastructure.services.aws_services import (
    CloudWatchAnalyticsService,
    CloudWatchMonitoringService
)

# Create infrastructure adapters
business_repo = DynamoDBBusinessRepository()
user_repo = DynamoDBUserRepository()
brand_repo = DynamoDBBrandRepository()
monitoring_service = CloudWatchMonitoringService()
analytics_service = CloudWatchAnalyticsService(monitoring_service)

# Inject dependencies into domain services
cost_optimizer = RefactoredCostOptimizer(
    business_repo=business_repo,
    user_repo=user_repo,
    analytics_service=analytics_service,
    monitoring_service=monitoring_service
)

brand_service = RefactoredBrandEndorsementService(
    brand_repo=brand_repo,
    user_repo=user_repo,
    business_repo=business_repo,
    analytics_service=analytics_service
)

# Use the services (business logic is now testable and infrastructure-agnostic)
validation_result = await cost_optimizer.validate_request("+1234567890", "meal_plan", "I want a healthy dinner")
brand_recommendations = await brand_service.generate_brand_recommendations("+1234567890", "vegetarian dinner")
"""
