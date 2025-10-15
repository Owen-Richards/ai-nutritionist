"""
Refactored Nutrition Calculator Service - Hexagonal Architecture
This shows how to refactor existing services to use the new clean architecture
"""

import logging
from typing import Dict, Any, List, Optional

from packages.core.src.interfaces.repositories import NutritionRepository, CacheRepository
from packages.core.src.interfaces.services import NutritionAPIService, ConfigurationService
from packages.core.src.domain_services.nutrition_calculation import NutritionCalculationService

logger = logging.getLogger(__name__)


class RefactoredEdamamService:
    """
    Refactored version of EdamamService following hexagonal architecture
    
    BEFORE: Direct AWS/DynamoDB dependencies mixed with business logic
    AFTER: Clean separation using dependency injection and interfaces
    """
    
    def __init__(
        self,
        nutrition_api: NutritionAPIService,
        nutrition_repo: NutritionRepository,
        cache_repo: CacheRepository,
        config_service: ConfigurationService
    ):
        # Dependencies injected through interfaces - no direct AWS imports!
        self.nutrition_calculation = NutritionCalculationService(
            nutrition_api=nutrition_api,
            nutrition_repo=nutrition_repo,
            cache_repo=cache_repo,
            config_service=config_service
        )
    
    async def enhanced_recipe_search(self, meal_name: str, user_profile: Dict) -> Dict:
        """
        Enhanced recipe search using clean architecture
        
        REFACTORING IMPROVEMENTS:
        ✅ No direct boto3/DynamoDB calls
        ✅ No direct SSM parameter access
        ✅ No direct HTTP requests
        ✅ Pure business logic through domain service
        ✅ Infrastructure concerns handled by adapters
        """
        return await self.nutrition_calculation.enhanced_recipe_search(meal_name, user_profile)
    
    async def analyze_nutrition(self, ingredients: List[str]) -> Dict[str, Any]:
        """
        Nutrition analysis using clean architecture
        
        REFACTORING IMPROVEMENTS:
        ✅ Domain validation through business rules
        ✅ External API calls through interfaces
        ✅ Caching through repository pattern
        """
        return await self.nutrition_calculation.analyze_nutrition_content(ingredients)
    
    async def get_daily_nutrition_goals(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate daily nutrition goals using domain logic
        
        REFACTORING IMPROVEMENTS:
        ✅ Pure domain calculations
        ✅ No infrastructure dependencies
        ✅ Testable business logic
        """
        return await self.nutrition_calculation.calculate_daily_nutrition_goals(user_profile)


# Usage example showing dependency injection:
"""
# Infrastructure setup (done once at application startup)
from packages.infrastructure.repositories.dynamodb_repositories import (
    DynamoDBNutritionRepository,
    DynamoDBCacheRepository
)
from packages.infrastructure.services.aws_services import (
    EdamamAPIService,
    AWSConfigurationService
)

# Create infrastructure adapters
config_service = AWSConfigurationService()
nutrition_api = EdamamAPIService(config_service)
nutrition_repo = DynamoDBNutritionRepository()
cache_repo = DynamoDBCacheRepository()

# Inject dependencies into domain service
edamam_service = RefactoredEdamamService(
    nutrition_api=nutrition_api,
    nutrition_repo=nutrition_repo,
    cache_repo=cache_repo,
    config_service=config_service
)

# Use the service (business logic is now testable and infrastructure-agnostic)
result = await edamam_service.enhanced_recipe_search("chicken salad", user_profile)
"""
