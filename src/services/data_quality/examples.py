"""
Data Quality Configuration and Examples

Configuration files and example implementations demonstrating
how to use the data quality assurance framework.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import timedelta

from src.services.data_quality import (
    DataQualityFramework, DataQualityConfig, ValidationScope
)
from src.services.data_quality.consistency import ConsistencyCheck, ConsistencyLevel
from src.services.data_quality.monitoring import MetricType
from src.models.analytics import PIILevel
from src.services.infrastructure.privacy_compliance import DataCategory, RetentionPolicy


# Configuration for different environments
DEVELOPMENT_CONFIG = DataQualityConfig(
    validation_scopes=[ValidationScope.SCHEMA, ValidationScope.PRIVACY],
    enable_real_time_monitoring=True,
    enable_anomaly_detection=False,  # Disabled in dev
    enable_lineage_tracking=True,
    alert_thresholds={
        'completeness': 90.0,
        'accuracy': 85.0,
        'consistency': 95.0
    },
    privacy_compliance_level="moderate"
)

PRODUCTION_CONFIG = DataQualityConfig(
    validation_scopes=[ValidationScope.ALL],
    enable_real_time_monitoring=True,
    enable_anomaly_detection=True,
    enable_lineage_tracking=True,
    alert_thresholds={
        'completeness': 95.0,
        'accuracy': 90.0,
        'consistency': 98.0,
        'timeliness': 95.0,
        'validity': 95.0,
        'uniqueness': 99.0
    },
    privacy_compliance_level="strict"
)

# Example validation contexts for different data types
USER_PROFILE_CONTEXT = {
    'schema_name': 'user_profile',
    'type_rules': {
        'email': 'email',
        'phone': 'phone',
        'user_id': 'uuid',
        'age': 'numeric_range',
        'weight_kg': 'numeric_range',
        'height_cm': 'numeric_range',
        'created_at': 'datetime'
    },
    'constraints': {
        'age': 'user_age_range',
        'weight_kg': 'weight_range_kg',
        'height_cm': 'height_range_cm'
    },
    'expected_pii_level': PIILevel.SENSITIVE.value,
    'entity_name': 'user',
    'consistency_checks': ['user_profile_consistency'],
    'encryption_fields': ['email', 'phone'],
    'data_category': DataCategory.IDENTITY.value,
    'test_retention': True
}

MEAL_PLAN_CONTEXT = {
    'schema_name': 'meal_plan',
    'type_rules': {
        'plan_id': 'uuid',
        'user_id': 'uuid',
        'calories': 'numeric_range',
        'protein_g': 'numeric_range',
        'carbs_g': 'numeric_range',
        'fat_g': 'numeric_range',
        'created_at': 'datetime'
    },
    'constraints': {
        'calories': 'calorie_range',
        'protein_g': 'numeric_range',
        'carbs_g': 'numeric_range',
        'fat_g': 'numeric_range'
    },
    'expected_pii_level': PIILevel.PSEUDONYMIZED.value,
    'entity_name': 'meal_plan',
    'consistency_checks': ['meal_nutrition_consistency'],
    'data_category': DataCategory.HEALTH.value
}

ANALYTICS_EVENT_CONTEXT = {
    'schema_name': 'base_event',
    'type_rules': {
        'event_id': 'uuid',
        'event_type': 'string_length',
        'timestamp': 'datetime',
        'user_id': 'uuid'
    },
    'expected_pii_level': PIILevel.NONE.value,
    'entity_name': 'analytics_event',
    'validate_events': True,
    'data_category': DataCategory.BEHAVIORAL.value
}


class DataQualityManager:
    """
    Manager class for configuring and running data quality checks
    across the AI Nutritionist application.
    """
    
    def __init__(self, environment: str = "development"):
        """Initialize with environment-specific configuration."""
        if environment == "production":
            self.config = PRODUCTION_CONFIG
        else:
            self.config = DEVELOPMENT_CONFIG
        
        self.framework = DataQualityFramework(self.config)
        self._setup_custom_configurations()
    
    def _setup_custom_configurations(self):
        """Set up custom configurations for the nutrition domain."""
        
        # Register nutrition-specific constraints
        self.framework.constraint_validator.register_constraint(
            'macro_balance_valid',
            self._validate_macro_balance
        )
        
        self.framework.constraint_validator.register_constraint(
            'dietary_preference_valid',
            lambda prefs: all(pref in [
                'vegetarian', 'vegan', 'keto', 'paleo', 'mediterranean',
                'low_carb', 'gluten_free', 'dairy_free'
            ] for pref in prefs) if isinstance(prefs, list) else False
        )
        
        # Register consistency checks
        user_profile_check = ConsistencyCheck(
            name='user_profile_consistency',
            source_service='user_service',
            target_service='nutrition_service',
            key_field='user_id',
            comparison_fields=['dietary_preferences', 'allergens', 'health_goals'],
            consistency_level=ConsistencyLevel.STRONG,
            critical=True
        )
        
        meal_nutrition_check = ConsistencyCheck(
            name='meal_nutrition_consistency',
            source_service='meal_service',
            target_service='nutrition_db',
            key_field='meal_id',
            comparison_fields=['calories', 'protein_g', 'carbs_g', 'fat_g'],
            consistency_level=ConsistencyLevel.EVENTUAL,
            tolerance_seconds=300
        )
        
        self.framework.cross_service_validator.register_consistency_check(user_profile_check)
        self.framework.cross_service_validator.register_consistency_check(meal_nutrition_check)
        
        # Set up retention policies
        from src.services.infrastructure.privacy_compliance import DataCategory, RetentionPolicy
        
        self.framework.retention_tester.register_retention_policy(
            DataCategory.IDENTITY, RetentionPolicy.LONG_TERM, 2555  # 7 years
        )
        
        self.framework.retention_tester.register_retention_policy(
            DataCategory.HEALTH, RetentionPolicy.MEDIUM_TERM, 365  # 1 year
        )
        
        self.framework.retention_tester.register_retention_policy(
            DataCategory.BEHAVIORAL, RetentionPolicy.SHORT_TERM, 90  # 90 days
        )
    
    def _validate_macro_balance(self, nutrition_data: Dict[str, Any]) -> bool:
        """Validate that macronutrient percentages are reasonable."""
        try:
            calories = nutrition_data.get('calories', 0)
            protein_g = nutrition_data.get('protein_g', 0)
            carbs_g = nutrition_data.get('carbs_g', 0)
            fat_g = nutrition_data.get('fat_g', 0)
            
            if calories <= 0:
                return False
            
            # Calculate percentages
            protein_cal = protein_g * 4
            carbs_cal = carbs_g * 4
            fat_cal = fat_g * 9
            
            total_macro_cal = protein_cal + carbs_cal + fat_cal
            
            # Allow 15% tolerance
            return abs(total_macro_cal - calories) / calories <= 0.15
        
        except (TypeError, ZeroDivisionError):
            return False
    
    async def validate_user_data(self, user_data: Any) -> Dict[str, Any]:
        """Validate user profile data."""
        report = await self.framework.validate_data_quality(
            user_data, USER_PROFILE_CONTEXT
        )
        return self._format_report(report)
    
    async def validate_meal_plan_data(self, meal_plan_data: Any) -> Dict[str, Any]:
        """Validate meal plan data."""
        report = await self.framework.validate_data_quality(
            meal_plan_data, MEAL_PLAN_CONTEXT
        )
        return self._format_report(report)
    
    async def validate_analytics_data(self, analytics_data: Any) -> Dict[str, Any]:
        """Validate analytics event data."""
        report = await self.framework.validate_data_quality(
            analytics_data, ANALYTICS_EVENT_CONTEXT
        )
        return self._format_report(report)
    
    def _format_report(self, report) -> Dict[str, Any]:
        """Format validation report for API consumption."""
        return {
            'overall_score': report.overall_score,
            'is_valid': report.overall_score >= 80.0,  # Threshold for acceptance
            'validation_summary': {
                name: {
                    'status': 'pass' if result.is_valid else 'fail',
                    'error_count': len(result.errors),
                    'warning_count': len(result.warnings)
                }
                for name, result in report.validation_results.items()
            },
            'metrics': report.metrics,
            'alerts': [
                {
                    'type': alert.get('type', 'unknown'),
                    'severity': alert.get('severity', 'medium'),
                    'message': str(alert)
                }
                for alert in report.alerts
            ],
            'recommendations': report.recommendations,
            'timestamp': report.timestamp.isoformat()
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary data."""
        return self.framework.get_dashboard_data()
    
    async def run_continuous_monitoring(self, data_sources: Dict[str, callable]):
        """Run continuous monitoring for multiple data sources."""
        import asyncio
        
        async def monitor_source(source_name: str, source_func: callable):
            """Monitor a single data source."""
            while True:
                try:
                    data = await source_func()
                    
                    # Choose validation context based on source
                    if 'user' in source_name.lower():
                        context = USER_PROFILE_CONTEXT
                    elif 'meal' in source_name.lower():
                        context = MEAL_PLAN_CONTEXT
                    elif 'analytics' in source_name.lower():
                        context = ANALYTICS_EVENT_CONTEXT
                    else:
                        context = {}
                    
                    report = await self.framework.validate_data_quality(data, context)
                    
                    # Log quality issues
                    if report.overall_score < 80:
                        print(f"Quality alert for {source_name}: Score {report.overall_score:.2f}")
                    
                    # Sleep for monitoring interval
                    await asyncio.sleep(300)  # 5 minutes
                
                except Exception as e:
                    print(f"Error monitoring {source_name}: {e}")
                    await asyncio.sleep(60)
        
        # Start monitoring tasks for all sources
        tasks = [
            monitor_source(name, func) 
            for name, func in data_sources.items()
        ]
        
        await asyncio.gather(*tasks)


# Example usage and integration patterns
class DataQualityIntegrationExamples:
    """Examples of how to integrate data quality checks."""
    
    @staticmethod
    async def api_endpoint_validation():
        """Example: Validate data at API endpoints."""
        manager = DataQualityManager("production")
        
        # Simulate API request data
        request_data = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "user@example.com",
            "age": 30,
            "dietary_preferences": ["vegetarian", "gluten_free"]
        }
        
        # Validate before processing
        validation_result = await manager.validate_user_data(request_data)
        
        if not validation_result['is_valid']:
            return {
                "error": "Data validation failed",
                "details": validation_result,
                "status_code": 400
            }
        
        return {"status": "success", "quality_score": validation_result['overall_score']}
    
    @staticmethod
    async def batch_processing_validation():
        """Example: Validate data in batch processing."""
        manager = DataQualityManager("production")
        
        # Simulate batch of meal plans
        meal_plans = [
            {
                "plan_id": "plan_1",
                "user_id": "user_1",
                "meals": [
                    {"calories": 400, "protein_g": 30, "carbs_g": 45, "fat_g": 12}
                ]
            },
            {
                "plan_id": "plan_2",
                "user_id": "user_2",
                "meals": [
                    {"calories": 350, "protein_g": 25, "carbs_g": 40, "fat_g": 10}
                ]
            }
        ]
        
        # Validate batch
        results = []
        for plan in meal_plans:
            result = await manager.validate_meal_plan_data(plan)
            results.append({
                "plan_id": plan["plan_id"],
                "quality_score": result["overall_score"],
                "is_valid": result["is_valid"]
            })
        
        return results
    
    @staticmethod
    async def data_pipeline_monitoring():
        """Example: Monitor data quality in processing pipeline."""
        manager = DataQualityManager("production")
        
        # Mock data sources
        async def get_user_data():
            return [{"user_id": "123", "email": "test@example.com"}]
        
        async def get_meal_data():
            return [{"meal_id": "456", "calories": 500}]
        
        data_sources = {
            "user_service": get_user_data,
            "meal_service": get_meal_data
        }
        
        # This would run continuously in production
        # await manager.run_continuous_monitoring(data_sources)
        
        # For demonstration, just show dashboard
        dashboard = manager.get_dashboard_summary()
        return dashboard


# Quality metrics configuration for different use cases
QUALITY_PROFILES = {
    "strict": {
        "completeness": {"min": 98.0},
        "accuracy": {"min": 95.0},
        "consistency": {"min": 99.0},
        "timeliness": {"min": 95.0},
        "validity": {"min": 98.0},
        "uniqueness": {"min": 99.5}
    },
    "standard": {
        "completeness": {"min": 95.0},
        "accuracy": {"min": 90.0},
        "consistency": {"min": 95.0},
        "timeliness": {"min": 90.0},
        "validity": {"min": 95.0},
        "uniqueness": {"min": 99.0}
    },
    "lenient": {
        "completeness": {"min": 90.0},
        "accuracy": {"min": 85.0},
        "consistency": {"min": 90.0},
        "timeliness": {"min": 80.0},
        "validity": {"min": 90.0},
        "uniqueness": {"min": 95.0}
    }
}


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        print("Data Quality Configuration Examples")
        print("=" * 40)
        
        # Example 1: API validation
        print("\n1. API Endpoint Validation:")
        api_result = await DataQualityIntegrationExamples.api_endpoint_validation()
        print(f"Result: {api_result}")
        
        # Example 2: Batch processing
        print("\n2. Batch Processing Validation:")
        batch_results = await DataQualityIntegrationExamples.batch_processing_validation()
        for result in batch_results:
            print(f"Plan {result['plan_id']}: {result['quality_score']:.2f} ({'PASS' if result['is_valid'] else 'FAIL'})")
        
        # Example 3: Dashboard
        print("\n3. Dashboard Summary:")
        dashboard = await DataQualityIntegrationExamples.data_pipeline_monitoring()
        print(f"Dashboard keys: {list(dashboard.keys())}")
    
    asyncio.run(main())
