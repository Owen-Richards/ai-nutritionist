"""
Service Migration Mapping

This file documents the mapping from old scattered services to new domain-organized services.
Used for updating import paths throughout the codebase.
"""

# Domain Service Mapping
SERVICE_MIGRATION_MAP = {
    # OLD SERVICE -> NEW DOMAIN SERVICE
    
    # User & Profile Services
    "user_service.UserService": "personalization.preferences.UserPreferenceService",
    "seamless_profiling_service.SeamlessUserProfileService": "personalization.preferences.UserPreferenceService", 
    
    # AI & Nutrition Services
    "ai_service.AIService": "nutrition.insights.NutritionInsightsService",
    "consolidated_ai_nutrition_service.ConsolidatedAINutritionService": "nutrition.insights.NutritionInsightsService",
    "edamam_service.EdamamService": "nutrition.calculator.NutritionCalculatorService",
    "nutrition_tracking_service.NutritionTrackingService": "nutrition.tracker.NutritionTrackerService",
    
    # Meal Planning Services  
    "meal_plan_service.MealPlanService": "meal_planning.planner.MealPlannerService",
    "adaptive_meal_planning_service.AdaptiveMealPlanningService": "meal_planning.planner.MealPlannerService",
    "multi_goal_meal_planner.MultiGoalMealPlanGenerator": "meal_planning.optimizer.MealOptimizationService",
    
    # Messaging Services
    "messaging_service.ConsolidatedMessagingService": "messaging.sms.SMSService",  
    "messaging_service.UniversalMessagingService": "messaging.sms.SMSService",
    "aws_sms_service.AWSMessagingService": "messaging.sms.SMSService",
    "nutrition_messaging_service.NutritionMessagingService": "messaging.templates.MessageTemplateService",
    
    # Business Services
    "subscription_service.SubscriptionService": "business.subscription.SubscriptionService", 
    "affiliate_revenue_service.AffiliateRevenueService": "business.revenue.RevenueOptimizationService",
    "brand_endorsement_service.BrandEndorsementService": "business.partnerships.PartnershipService",
    
    # Specialized Services
    "user_linking_service.UserLinkingService": "personalization.behavior.BehaviorAnalyticsService",
    "multi_user_messaging_handler.MultiUserMessagingHandler": "messaging.notifications.NotificationService",
    "multi_goal_service.MultiGoalService": "personalization.goals.GoalManagementService",
}

# Factory Function Mapping
FACTORY_FUNCTION_MAP = {
    "get_subscription_service": "business.subscription.SubscriptionService",
    "get_messaging_service": "messaging.sms.SMSService", 
    "get_sms_service": "messaging.sms.SMSService",
    "get_brand_endorsement_service": "business.partnerships.PartnershipService",
    "get_profit_enforcement_service": "business.revenue.RevenueOptimizationService",
}

# Import Path Updates
NEW_IMPORT_PATHS = {
    # Nutrition Domain
    "nutrition.insights": "services.nutrition.insights.NutritionInsightsService",
    "nutrition.calculator": "services.nutrition.calculator.NutritionCalculatorService", 
    "nutrition.tracker": "services.nutrition.tracker.NutritionTrackerService",
    "nutrition.goals": "services.nutrition.goals.NutritionGoalService",
    
    # Meal Planning Domain
    "meal_planning.planner": "services.meal_planning.planner.MealPlannerService",
    "meal_planning.optimizer": "services.meal_planning.optimizer.MealOptimizationService",
    "meal_planning.constraints": "services.meal_planning.constraints.DietaryConstraintService", 
    "meal_planning.variety": "services.meal_planning.variety.MealVarietyService",
    
    # Personalization Domain
    "personalization.preferences": "services.personalization.preferences.UserPreferenceService",
    "personalization.behavior": "services.personalization.behavior.BehaviorAnalyticsService",
    "personalization.learning": "services.personalization.learning.AdaptiveLearningService",
    "personalization.goals": "services.personalization.goals.GoalManagementService",
    
    # Messaging Domain  
    "messaging.sms": "services.messaging.sms.SMSService",
    "messaging.templates": "services.messaging.templates.MessageTemplateService",
    "messaging.notifications": "services.messaging.notifications.NotificationService",
    "messaging.analytics": "services.messaging.analytics.CommunicationAnalyticsService",
    
    # Business Domain
    "business.subscription": "services.business.subscription.SubscriptionService",
    "business.revenue": "services.business.revenue.RevenueOptimizationService", 
    "business.compliance": "services.business.compliance.ComplianceService",
    "business.partnerships": "services.business.partnerships.PartnershipService",
}
