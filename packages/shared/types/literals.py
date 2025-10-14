"""Literal types for the AI Nutritionist application.

This module defines literal types used throughout the application
for type safety and consistency.
"""

from __future__ import annotations

import sys
from typing import Union

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

# Authentication types
AuthChannel: TypeAlias = Literal['sms', 'email']
TokenType: TypeAlias = Literal['access', 'refresh']
AuthStatus: TypeAlias = Literal['pending', 'verified', 'expired', 'failed']

# Subscription types  
SubscriptionTier: TypeAlias = Literal['free', 'premium', 'family', 'enterprise']
SubscriptionStatus: TypeAlias = Literal['active', 'past_due', 'canceled', 'incomplete']
BillingInterval: TypeAlias = Literal['monthly', 'yearly']

# Dietary restrictions
DietaryRestriction: TypeAlias = Literal[
    'vegetarian', 'vegan', 'pescatarian', 'gluten_free', 'dairy_free',
    'nut_free', 'soy_free', 'egg_free', 'shellfish_free', 'low_carb',
    'keto', 'paleo', 'mediterranean', 'whole30', 'low_sodium', 'diabetic'
]

# Cuisine preferences
CuisineType: TypeAlias = Literal[
    'american', 'italian', 'mexican', 'chinese', 'japanese', 'indian',
    'thai', 'mediterranean', 'french', 'greek', 'spanish', 'korean',
    'vietnamese', 'middle_eastern', 'latin_american', 'african',
    'british', 'german', 'scandinavian', 'fusion'
]

# Goal types
GoalType: TypeAlias = Literal[
    'weight_loss', 'weight_gain', 'muscle_gain', 'maintain_weight',
    'improve_energy', 'better_sleep', 'gut_health', 'heart_health',
    'manage_diabetes', 'reduce_inflammation', 'immune_support',
    'sports_performance', 'general_wellness'
]

# Activity levels
ActivityLevel: TypeAlias = Literal[
    'sedentary', 'lightly_active', 'moderately_active',
    'very_active', 'extremely_active'
]

# Meal types
MealType: TypeAlias = Literal[
    'breakfast', 'lunch', 'dinner', 'snack',
    'pre_workout', 'post_workout', 'dessert'
]

# Days of week
DayOfWeek: TypeAlias = Literal[
    'monday', 'tuesday', 'wednesday', 'thursday',
    'friday', 'saturday', 'sunday'
]

# Prep time preferences
PrepTimePreference: TypeAlias = Literal['quick', 'moderate', 'elaborate']
CookingSkillLevel: TypeAlias = Literal['beginner', 'intermediate', 'advanced']

# Equipment types
CookingEquipment: TypeAlias = Literal[
    'oven', 'stovetop', 'microwave', 'slow_cooker', 'pressure_cooker',
    'air_fryer', 'grill', 'blender', 'food_processor', 'stand_mixer',
    'toaster_oven', 'rice_cooker', 'steamer', 'wok', 'cast_iron',
    'non_stick_pan', 'sheet_pan'
]

# Serving sizes
ServingSize: TypeAlias = Literal[1, 2, 3, 4, 5, 6, 7, 8]

# Rating scales
Rating: TypeAlias = Literal[1, 2, 3, 4, 5]
Difficulty: TypeAlias = Literal[1, 2, 3, 4, 5]

# Community types
CrewType: TypeAlias = Literal[
    'weight_loss', 'muscle_gain', 'healthy_eating', 'meal_prep',
    'plant_based', 'keto', 'family_nutrition', 'seniors', 'athletes'
]

ReflectionType: TypeAlias = Literal['daily', 'weekly', 'milestone', 'challenge']
MoodScore: TypeAlias = Literal[1, 2, 3, 4, 5]

# Analytics types
EventType: TypeAlias = Literal[
    'user_registered', 'plan_generated', 'meal_logged', 'feedback_submitted',
    'grocery_list_created', 'calendar_synced', 'achievement_unlocked',
    'subscription_started', 'subscription_canceled', 'app_opened',
    'meal_prepared', 'recipe_viewed', 'ingredient_substituted'
]

ConsentType: TypeAlias = Literal[
    'analytics', 'marketing', 'personalization', 'research'
]

MetricType: TypeAlias = Literal[
    'engagement', 'retention', 'conversion', 'revenue',
    'satisfaction', 'adherence', 'health_outcomes'
]

# Integration types
CalendarProvider: TypeAlias = Literal['google', 'outlook', 'apple', 'yahoo']
FitnessProvider: TypeAlias = Literal[
    'apple_health', 'google_fit', 'fitbit', 'garmin', 'polar',
    'withings', 'oura', 'whoop', 'strava', 'myfitnesspal'
]

GroceryPartner: TypeAlias = Literal[
    'instacart', 'amazon_fresh', 'walmart', 'target', 'kroger',
    'safeway', 'whole_foods', 'costco', 'aldi', 'trader_joes'
]

# Calendar event types
CalendarEventType: TypeAlias = Literal[
    'meal_prep', 'cooking', 'grocery_shopping', 'meal_time',
    'nutrition_reminder', 'water_reminder', 'supplement_reminder'
]

ReminderType: TypeAlias = Literal[
    'notification', 'sms', 'email', 'phone_call'
]

# Workout types
WorkoutType: TypeAlias = Literal[
    'cardio', 'strength', 'hiit', 'yoga', 'pilates', 'running',
    'cycling', 'swimming', 'dancing', 'sports', 'stretching'
]

WorkoutIntensity: TypeAlias = Literal['low', 'moderate', 'high', 'very_high']

# Notification types
NotificationType: TypeAlias = Literal[
    'meal_reminder', 'water_reminder', 'grocery_reminder',
    'meal_prep_reminder', 'achievement', 'challenge_update',
    'social_activity', 'health_tip', 'recipe_suggestion'
]

NotificationPriority: TypeAlias = Literal['low', 'medium', 'high', 'urgent']
NotificationChannel: TypeAlias = Literal['push', 'sms', 'email', 'in_app']

# Health metrics
HealthMetric: TypeAlias = Literal[
    'weight', 'body_fat', 'muscle_mass', 'bmi', 'blood_pressure',
    'heart_rate', 'sleep_hours', 'steps', 'calories_burned',
    'water_intake', 'mood', 'energy_level', 'stress_level'
]

# File types
FileType: TypeAlias = Literal[
    'image', 'video', 'audio', 'document', 'spreadsheet',
    'pdf', 'csv', 'json', 'xml'
]

ImageFormat: TypeAlias = Literal['jpeg', 'png', 'webp', 'gif', 'svg']
DocumentFormat: TypeAlias = Literal['pdf', 'doc', 'docx', 'txt', 'md']

# API types
HTTPMethod: TypeAlias = Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

APIVersion: TypeAlias = Literal['v1', 'v2']
ContentType: TypeAlias = Literal[
    'application/json', 'application/xml', 'text/plain',
    'text/html', 'text/csv', 'multipart/form-data',
    'application/x-www-form-urlencoded'
]

# Status types  
TaskStatus: TypeAlias = Literal['pending', 'running', 'completed', 'failed', 'canceled']
ProcessingStatus: TypeAlias = Literal['queued', 'processing', 'completed', 'error']
SyncStatus: TypeAlias = Literal['synced', 'pending', 'failed', 'partial']

# Feature flags
FeatureFlag: TypeAlias = Literal[
    'meal_planning_v2', 'ai_coach', 'social_features', 'premium_recipes',
    'family_accounts', 'grocery_integration', 'fitness_sync',
    'advanced_analytics', 'voice_assistant', 'ar_nutrition'
]

# Experiment types
ExperimentType: TypeAlias = Literal[
    'ab_test', 'multivariate', 'feature_flag', 'gradual_rollout'
]

ExperimentStatus: TypeAlias = Literal[
    'draft', 'active', 'paused', 'completed', 'archived'
]

# Error types
ErrorSeverity: TypeAlias = Literal['low', 'medium', 'high', 'critical']
ErrorCategory: TypeAlias = Literal[
    'validation', 'authentication', 'authorization', 'not_found',
    'conflict', 'rate_limit', 'external_service', 'internal_server',
    'timeout', 'network'
]

# Log levels
LogLevel: TypeAlias = Literal['debug', 'info', 'warning', 'error', 'critical']

# Environment types
Environment: TypeAlias = Literal['development', 'staging', 'production']
Region: TypeAlias = Literal['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1']

# Data types
DataFormat: TypeAlias = Literal['json', 'csv', 'parquet', 'avro']
CompressionType: TypeAlias = Literal['none', 'gzip', 'brotli', 'lz4']
EncryptionType: TypeAlias = Literal['none', 'aes256', 'rsa']

# Time units
TimeUnit: TypeAlias = Literal[
    'second', 'minute', 'hour', 'day', 'week', 'month', 'year'
]

# Currency codes (ISO 4217)
CurrencyCode: TypeAlias = Literal[
    'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR', 'BRL'
]

# Language codes (ISO 639-1)
LanguageCode: TypeAlias = Literal[
    'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi'
]

# Country codes (ISO 3166-1 alpha-2)
CountryCode: TypeAlias = Literal[
    'US', 'CA', 'GB', 'FR', 'DE', 'IT', 'ES', 'AU', 'JP', 'CN', 'IN', 'BR'
]

# Timezone identifiers (common ones)
TimezoneId: TypeAlias = Literal[
    'UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
    'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Asia/Tokyo',
    'Asia/Shanghai', 'Australia/Sydney'
]

# Union types for convenience
AnyRestriction: TypeAlias = Union[DietaryRestriction, str]
AnyCuisine: TypeAlias = Union[CuisineType, str]
AnyGoal: TypeAlias = Union[GoalType, str]
AnyEquipment: TypeAlias = Union[CookingEquipment, str]

# Export all literal types
__all__ = [
    # Authentication
    'AuthChannel', 'TokenType', 'AuthStatus',
    
    # Subscriptions
    'SubscriptionTier', 'SubscriptionStatus', 'BillingInterval',
    
    # Nutrition
    'DietaryRestriction', 'CuisineType', 'GoalType', 'ActivityLevel',
    'MealType', 'DayOfWeek', 'PrepTimePreference', 'CookingSkillLevel',
    'CookingEquipment', 'ServingSize', 'Rating', 'Difficulty',
    
    # Community
    'CrewType', 'ReflectionType', 'MoodScore',
    
    # Analytics
    'EventType', 'ConsentType', 'MetricType',
    
    # Integrations
    'CalendarProvider', 'FitnessProvider', 'GroceryPartner',
    'CalendarEventType', 'ReminderType', 'WorkoutType', 'WorkoutIntensity',
    
    # Notifications
    'NotificationType', 'NotificationPriority', 'NotificationChannel',
    
    # Health
    'HealthMetric',
    
    # Files
    'FileType', 'ImageFormat', 'DocumentFormat',
    
    # API
    'HTTPMethod', 'APIVersion', 'ContentType',
    
    # Status
    'TaskStatus', 'ProcessingStatus', 'SyncStatus',
    
    # Features
    'FeatureFlag', 'ExperimentType', 'ExperimentStatus',
    
    # Errors
    'ErrorSeverity', 'ErrorCategory', 'LogLevel',
    
    # Infrastructure
    'Environment', 'Region', 'DataFormat', 'CompressionType', 'EncryptionType',
    
    # Internationalization
    'TimeUnit', 'CurrencyCode', 'LanguageCode', 'CountryCode', 'TimezoneId',
    
    # Union types
    'AnyRestriction', 'AnyCuisine', 'AnyGoal', 'AnyEquipment',
]
