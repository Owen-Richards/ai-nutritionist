"""Configuration file for LaunchDarkly integration."""

import os
from typing import Dict, Any, List, Optional

from packages.shared.feature_flags import LaunchDarklyConfig, CacheConfig


# Environment-specific configurations
ENVIRONMENTS = {
    "development": {
        "sdk_key": os.getenv("LAUNCHDARKLY_DEV_SDK_KEY", "sdk-dev-key-placeholder"),
        "base_uri": "https://sdk.launchdarkly.com",
        "events_uri": "https://events.launchdarkly.com",
        "stream_uri": "https://stream.launchdarkly.com",
        "send_events": True,
        "offline": False,
    },
    "staging": {
        "sdk_key": os.getenv("LAUNCHDARKLY_STAGING_SDK_KEY", "sdk-staging-key-placeholder"),
        "base_uri": "https://sdk.launchdarkly.com",
        "events_uri": "https://events.launchdarkly.com", 
        "stream_uri": "https://stream.launchdarkly.com",
        "send_events": True,
        "offline": False,
    },
    "production": {
        "sdk_key": os.getenv("LAUNCHDARKLY_PROD_SDK_KEY", "sdk-prod-key-placeholder"),
        "base_uri": "https://sdk.launchdarkly.com",
        "events_uri": "https://events.launchdarkly.com",
        "stream_uri": "https://stream.launchdarkly.com",
        "send_events": True,
        "offline": False,
    },
    "test": {
        "sdk_key": "test-key",
        "offline": True,  # Offline mode for tests
        "send_events": False,
    }
}


def get_launchdarkly_config(environment: str = "development") -> LaunchDarklyConfig:
    """Get LaunchDarkly configuration for environment."""
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {environment}")
    
    config_data = ENVIRONMENTS[environment]
    
    return LaunchDarklyConfig(
        sdk_key=config_data["sdk_key"],
        base_uri=config_data.get("base_uri"),
        events_uri=config_data.get("events_uri"),
        stream_uri=config_data.get("stream_uri"),
        send_events=config_data.get("send_events", True),
        offline=config_data.get("offline", False),
        environment=environment,
        
        # Performance settings
        cache_ttl_seconds=300,
        start_wait_seconds=5,
        events_capacity=10000,
        events_flush_interval_seconds=5,
    )


def get_cache_config(environment: str = "development") -> CacheConfig:
    """Get cache configuration for environment."""
    
    if environment == "production":
        # Production: Use Redis for distributed caching
        return CacheConfig(
            ttl_seconds=300,
            max_size=50000,
            enable_local_cache=True,
            enable_distributed_cache=True,
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        )
    
    elif environment == "staging":
        # Staging: Use Redis if available, fallback to memory
        redis_url = os.getenv("REDIS_URL")
        return CacheConfig(
            ttl_seconds=300,
            max_size=10000,
            enable_local_cache=True,
            enable_distributed_cache=bool(redis_url),
            redis_url=redis_url,
        )
    
    else:
        # Development/Test: Use memory cache only
        return CacheConfig(
            ttl_seconds=60,  # Shorter TTL for development
            max_size=1000,
            enable_local_cache=True,
            enable_distributed_cache=False,
        )


# Feature flag definitions for AI Nutritionist
FEATURE_FLAG_DEFINITIONS = {
    # Core Application Features
    "enhanced_meal_planning": {
        "name": "Enhanced Meal Planning",
        "description": "Enable AI-powered enhanced meal planning algorithm",
        "variants": [
            {"key": "off", "value": False, "percentage": 0},
            {"key": "basic", "value": "basic", "percentage": 30},
            {"key": "advanced", "value": "advanced", "percentage": 70},
        ],
        "default_variant": "basic",
        "fallback_variant": "off",
        "tags": ["core", "meal-planning", "ai"],
        "targeting_rules": [
            {
                "name": "Premium Users Get Advanced",
                "conditions": [
                    {"attribute": "subscription_tier", "operator": "in", "value": ["premium", "enterprise"]}
                ],
                "variant": "advanced",
                "percentage": 100.0,
                "priority": 10,
            }
        ],
    },
    
    "fitness_integration_v2": {
        "name": "Fitness Integration V2",
        "description": "New fitness data integration with Apple Health/Google Fit",
        "variants": [
            {"key": "off", "value": False, "percentage": 50},
            {"key": "on", "value": True, "percentage": 50},
        ],
        "default_variant": "off",
        "fallback_variant": "off",
        "tags": ["fitness", "integration", "health"],
        "rollout_rules": [
            {
                "strategy": "percentage",
                "percentage": 25.0,  # 25% gradual rollout
            }
        ],
    },
    
    "smart_nutrition_analysis": {
        "name": "Smart Nutrition Analysis",
        "description": "AI-powered nutrition analysis and recommendations",
        "variants": [
            {"key": "disabled", "value": False, "percentage": 0},
            {"key": "basic", "value": "basic", "percentage": 40},
            {"key": "advanced", "value": "advanced", "percentage": 60},
        ],
        "default_variant": "basic",
        "fallback_variant": "disabled",
        "tags": ["ai", "nutrition", "analysis"],
    },
    
    # UI/UX Features
    "new_dashboard_design": {
        "name": "New Dashboard Design",
        "description": "Updated dashboard with modern UI",
        "variants": [
            {"key": "classic", "value": "classic", "percentage": 60},
            {"key": "modern", "value": "modern", "percentage": 40},
        ],
        "default_variant": "classic",
        "fallback_variant": "classic",
        "tags": ["ui", "dashboard", "design"],
        "ab_test": {
            "name": "Dashboard Design A/B Test",
            "traffic_allocation": 100.0,
            "primary_metric": "user_engagement",
            "secondary_metrics": ["session_duration", "feature_usage"],
        },
    },
    
    "mobile_app_redesign": {
        "name": "Mobile App Redesign",
        "description": "New mobile app interface design",
        "variants": [
            {"key": "current", "value": "current", "percentage": 70},
            {"key": "redesign", "value": "redesign", "percentage": 30},
        ],
        "default_variant": "current",
        "fallback_variant": "current",
        "tags": ["mobile", "ui", "redesign"],
    },
    
    # API Features
    "api_v2": {
        "name": "API Version 2",
        "description": "New API endpoints and improved performance",
        "variants": [
            {"key": "v1", "value": "v1", "percentage": 80},
            {"key": "v2", "value": "v2", "percentage": 20},
        ],
        "default_variant": "v1",
        "fallback_variant": "v1",
        "tags": ["api", "version", "performance"],
        "targeting_rules": [
            {
                "name": "Beta API Users",
                "conditions": [
                    {"attribute": "user_segments", "operator": "contains", "value": "api_beta"}
                ],
                "variant": "v2",
                "percentage": 100.0,
                "priority": 10,
            }
        ],
    },
    
    "graphql_api": {
        "name": "GraphQL API",
        "description": "Enable GraphQL API endpoints",
        "variants": [
            {"key": "disabled", "value": False, "percentage": 90},
            {"key": "enabled", "value": True, "percentage": 10},
        ],
        "default_variant": "disabled",
        "fallback_variant": "disabled",
        "tags": ["api", "graphql", "experimental"],
    },
    
    # Monetization Features
    "premium_features": {
        "name": "Premium Features",
        "description": "Access to premium subscription features",
        "variants": [
            {"key": "basic", "value": "basic", "percentage": 0},
            {"key": "premium", "value": "premium", "percentage": 100},
        ],
        "default_variant": "basic",
        "fallback_variant": "basic",
        "tags": ["monetization", "premium", "subscription"],
        "targeting_rules": [
            {
                "name": "Premium Subscribers",
                "conditions": [
                    {"attribute": "subscription_tier", "operator": "in", "value": ["premium", "enterprise"]}
                ],
                "variant": "premium",
                "percentage": 100.0,
                "priority": 10,
            }
        ],
    },
    
    "paywall_experiment": {
        "name": "Paywall Experiment",
        "description": "Test different paywall presentations",
        "variants": [
            {"key": "control", "value": "standard", "percentage": 50},
            {"key": "variant_a", "value": "aggressive", "percentage": 25},
            {"key": "variant_b", "value": "soft", "percentage": 25},
        ],
        "default_variant": "control",
        "fallback_variant": "control",
        "tags": ["monetization", "paywall", "experiment"],
        "ab_test": {
            "name": "Paywall Optimization",
            "traffic_allocation": 100.0,
            "primary_metric": "conversion_rate",
            "secondary_metrics": ["revenue_per_user", "churn_rate"],
        },
    },
    
    # Performance Features
    "advanced_caching": {
        "name": "Advanced Caching",
        "description": "Enable advanced caching mechanisms",
        "variants": [
            {"key": "off", "value": False, "percentage": 20},
            {"key": "on", "value": True, "percentage": 80},
        ],
        "default_variant": "on",
        "fallback_variant": "off",
        "tags": ["performance", "caching", "optimization"],
    },
    
    "cdn_optimization": {
        "name": "CDN Optimization",
        "description": "Use optimized CDN configuration",
        "variants": [
            {"key": "standard", "value": "standard", "percentage": 30},
            {"key": "optimized", "value": "optimized", "percentage": 70},
        ],
        "default_variant": "optimized",
        "fallback_variant": "standard",
        "tags": ["performance", "cdn", "optimization"],
    },
    
    # Experimental Features
    "ai_chat_assistant": {
        "name": "AI Chat Assistant",
        "description": "AI-powered chat assistant for nutrition questions",
        "variants": [
            {"key": "disabled", "value": False, "percentage": 80},
            {"key": "enabled", "value": True, "percentage": 20},
        ],
        "default_variant": "disabled",
        "fallback_variant": "disabled",
        "tags": ["experimental", "ai", "chat", "assistant"],
        "targeting_rules": [
            {
                "name": "Beta Users Only",
                "conditions": [
                    {"attribute": "user_segments", "operator": "contains", "value": "beta_user"}
                ],
                "variant": "enabled",
                "percentage": 100.0,
                "priority": 10,
            }
        ],
    },
    
    "voice_commands": {
        "name": "Voice Commands",
        "description": "Voice command interface for meal logging",
        "variants": [
            {"key": "off", "value": False, "percentage": 95},
            {"key": "on", "value": True, "percentage": 5},
        ],
        "default_variant": "off",
        "fallback_variant": "off",
        "tags": ["experimental", "voice", "accessibility"],
    },
}


def get_feature_flag_config(environment: str = "development") -> Dict[str, Any]:
    """Get feature flag configuration for environment."""
    
    # Adjust rollout percentages based on environment
    if environment == "production":
        # More conservative rollouts in production
        adjustments = {
            "fitness_integration_v2": {"rollout_percentage": 10.0},
            "ai_chat_assistant": {"enabled_percentage": 5.0},
            "voice_commands": {"enabled_percentage": 1.0},
        }
    elif environment == "staging":
        # Moderate rollouts in staging
        adjustments = {
            "fitness_integration_v2": {"rollout_percentage": 50.0},
            "ai_chat_assistant": {"enabled_percentage": 30.0},
            "voice_commands": {"enabled_percentage": 10.0},
        }
    else:
        # Full rollouts in development
        adjustments = {
            "fitness_integration_v2": {"rollout_percentage": 100.0},
            "ai_chat_assistant": {"enabled_percentage": 100.0},
            "voice_commands": {"enabled_percentage": 50.0},
        }
    
    # Apply environment-specific adjustments
    config = FEATURE_FLAG_DEFINITIONS.copy()
    
    for flag_key, adjustment in adjustments.items():
        if flag_key in config:
            flag_config = config[flag_key]
            
            # Adjust rollout percentage
            if "rollout_percentage" in adjustment and "rollout_rules" in flag_config:
                for rule in flag_config["rollout_rules"]:
                    if rule["strategy"] == "percentage":
                        rule["percentage"] = adjustment["rollout_percentage"]
            
            # Adjust enabled percentage for variants
            if "enabled_percentage" in adjustment:
                for variant in flag_config["variants"]:
                    if variant["value"] is True:
                        variant["percentage"] = adjustment["enabled_percentage"]
                    elif variant["value"] is False:
                        variant["percentage"] = 100.0 - adjustment["enabled_percentage"]
    
    return config


# User segments for targeting
USER_SEGMENTS = {
    "beta_user": {
        "name": "Beta Users",
        "description": "Users opted into beta testing",
        "conditions": [
            {"attribute": "custom.beta_opt_in", "operator": "equals", "value": True}
        ],
    },
    "power_user": {
        "name": "Power Users",
        "description": "Highly engaged users",
        "conditions": [
            {"attribute": "custom.daily_active_days", "operator": "greater_than", "value": 20},
            {"attribute": "custom.features_used", "operator": "greater_than", "value": 5},
        ],
    },
    "new_user": {
        "name": "New Users",
        "description": "Users who signed up within last 30 days",
        "conditions": [
            {"attribute": "custom.days_since_signup", "operator": "less_than", "value": 30}
        ],
    },
    "premium_subscriber": {
        "name": "Premium Subscribers",
        "description": "Users with premium subscription",
        "conditions": [
            {"attribute": "subscription_tier", "operator": "in", "value": ["premium", "enterprise"]}
        ],
    },
    "mobile_user": {
        "name": "Mobile Users",
        "description": "Users primarily using mobile app",
        "conditions": [
            {"attribute": "custom.primary_platform", "operator": "equals", "value": "mobile"}
        ],
    },
    "api_user": {
        "name": "API Users",
        "description": "Users accessing via API",
        "conditions": [
            {"attribute": "custom.access_method", "operator": "equals", "value": "api"}
        ],
    },
}


# Cleanup rules for flag management
CLEANUP_RULES = [
    {
        "name": "Archive Old Experimental Flags",
        "description": "Archive experimental flags older than 90 days",
        "flag_age_days": 90,
        "tags": ["experimental"],
        "action": "archive",
        "notify_users": ["product@ainutritionist.com"],
    },
    {
        "name": "Notify About Unused Flags",
        "description": "Notify about flags with no evaluations in 30 days",
        "last_evaluation_days": 30,
        "action": "notify",
        "notify_users": ["engineering@ainutritionist.com"],
    },
    {
        "name": "Archive Inactive Legacy Flags",
        "description": "Archive inactive legacy flags older than 180 days",
        "flag_age_days": 180,
        "flag_status": "inactive",
        "tags": ["legacy"],
        "action": "archive",
        "notify_users": ["admin@ainutritionist.com"],
    },
]


def get_admin_users(environment: str = "development") -> List[str]:
    """Get list of admin users for environment."""
    
    base_admins = [
        "admin@ainutritionist.com",
        "engineering-lead@ainutritionist.com",
    ]
    
    if environment == "production":
        return base_admins + [
            "cto@ainutritionist.com",
            "product-manager@ainutritionist.com",
        ]
    elif environment == "staging":
        return base_admins + [
            "qa-lead@ainutritionist.com",
            "product-manager@ainutritionist.com",
        ]
    else:
        return base_admins + [
            "developer@ainutritionist.com",
            "product@ainutritionist.com",
        ]
