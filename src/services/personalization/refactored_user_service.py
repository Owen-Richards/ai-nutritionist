"""
Refactored User Service - Hexagonal Architecture
This shows how to refactor existing services to use the new clean architecture
"""

import logging
from typing import Dict, Any, Optional

from packages.core.src.interfaces.repositories import UserRepository
from packages.core.src.interfaces.services import AnalyticsService
from packages.core.src.domain_services.user_management import UserManagementService

logger = logging.getLogger(__name__)


class RefactoredUserService:
    """
    Refactored version of UserService following hexagonal architecture
    
    BEFORE: Direct DynamoDB calls mixed with business logic
    AFTER: Clean separation using dependency injection and interfaces
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        analytics_service: AnalyticsService
    ):
        # Dependencies injected through interfaces - no direct AWS imports!
        self.user_management = UserManagementService(
            user_repo=user_repo,
            analytics_service=analytics_service
        )
    
    async def get_or_create_user(self, phone_number: str) -> Dict[str, Any]:
        """
        Get or create user using clean architecture
        
        REFACTORING IMPROVEMENTS:
        ✅ No direct DynamoDB calls
        ✅ Domain logic separated from infrastructure
        ✅ Business rules in domain service
        ✅ Analytics tracking through interface
        """
        return await self.user_management.get_or_create_user(phone_number)
    
    async def update_user_preferences(self, phone_number: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences using domain validation
        
        REFACTORING IMPROVEMENTS:
        ✅ Domain validation for preferences
        ✅ Business rules for dietary restrictions
        ✅ Infrastructure abstracted away
        """
        return await self.user_management.update_user_preferences(phone_number, preferences)
    
    async def upgrade_user_tier(self, phone_number: str, new_tier: str, subscription_data: Dict[str, Any] = None) -> bool:
        """
        Upgrade user tier using business rules
        
        REFACTORING IMPROVEMENTS:
        ✅ Tier transition validation in domain
        ✅ Business logic for upgrade eligibility
        ✅ Event tracking through analytics interface
        """
        return await self.user_management.upgrade_user_tier(phone_number, new_tier, subscription_data)


# Usage example showing dependency injection:
"""
# Infrastructure setup (done once at application startup)
from packages.infrastructure.repositories.dynamodb_repositories import DynamoDBUserRepository
from packages.infrastructure.services.aws_services import CloudWatchAnalyticsService, CloudWatchMonitoringService

# Create infrastructure adapters
user_repo = DynamoDBUserRepository()
monitoring_service = CloudWatchMonitoringService()
analytics_service = CloudWatchAnalyticsService(monitoring_service)

# Inject dependencies into domain service
user_service = RefactoredUserService(
    user_repo=user_repo,
    analytics_service=analytics_service
)

# Use the service (business logic is now testable and infrastructure-agnostic)
user = await user_service.get_or_create_user("+1234567890")
success = await user_service.update_user_preferences("+1234567890", {"dietary_restrictions": ["vegan"]})
"""
