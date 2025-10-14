"""
Data Quality Assurance Framework

Main framework that orchestrates all data quality components.
"""

import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from .validators import (
    SchemaValidator, DataTypeValidator, ConstraintValidator, 
    ReferentialIntegrityValidator, ValidationResult
)
from .consistency import (
    CrossServiceConsistencyValidator, EventSourcingValidator,
    CacheConsistencyValidator, DatabaseConsistencyValidator
)
from .privacy import (
    PIIDetector, DataMaskingValidator, EncryptionValidator, 
    RetentionPolicyTester
)
from .monitoring import (
    DataQualityMetrics, AnomalyDetector, DataLineageTracker, 
    QualityDashboard, MetricType, AlertSeverity
)

logger = logging.getLogger(__name__)


class ValidationScope(Enum):
    """Scope of data quality validation."""
    SCHEMA = "schema"
    CONSISTENCY = "consistency"
    PRIVACY = "privacy"
    MONITORING = "monitoring"
    ALL = "all"


@dataclass
class DataQualityConfig:
    """Configuration for data quality framework."""
    validation_scopes: List[ValidationScope] = field(default_factory=lambda: [ValidationScope.ALL])
    enable_real_time_monitoring: bool = True
    enable_anomaly_detection: bool = True
    enable_lineage_tracking: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    retention_policies: Dict[str, int] = field(default_factory=dict)
    privacy_compliance_level: str = "strict"  # strict, moderate, basic


@dataclass
class DataQualityReport:
    """Comprehensive data quality report."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    overall_score: float = 0.0
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    alerts: List[Any] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataQualityFramework:
    """Main data quality assurance framework."""
    
    def __init__(self, config: Optional[DataQualityConfig] = None):
        self.config = config or DataQualityConfig()
        
        # Initialize core components
        self.schema_validator = SchemaValidator()
        self.data_type_validator = DataTypeValidator()
        self.constraint_validator = ConstraintValidator()
        self.referential_validator = ReferentialIntegrityValidator()
        
        # Initialize consistency validators
        self.cross_service_validator = CrossServiceConsistencyValidator()
        self.event_sourcing_validator = EventSourcingValidator()
        self.cache_validator = CacheConsistencyValidator()
        self.db_validator = DatabaseConsistencyValidator()
        
        # Initialize privacy validators
        self.pii_detector = PIIDetector()
        self.masking_validator = DataMaskingValidator()
        self.encryption_validator = EncryptionValidator()
        self.retention_tester = RetentionPolicyTester()
        
        # Initialize monitoring components
        self.metrics_service = DataQualityMetrics()
        self.anomaly_detector = AnomalyDetector()
        self.lineage_tracker = DataLineageTracker()
        self.dashboard = QualityDashboard(
            self.metrics_service, 
            self.anomaly_detector, 
            self.lineage_tracker
        )
        
        # Initialize framework
        self._setup_default_configurations()
    
    def _setup_default_configurations(self):
        """Set up default configurations for the framework."""
        # Set default metric thresholds
        self.metrics_service.set_threshold('completeness', min_threshold=95.0)
        self.metrics_service.set_threshold('accuracy', min_threshold=90.0)
        self.metrics_service.set_threshold('consistency', min_threshold=98.0)
        self.metrics_service.set_threshold('timeliness', min_threshold=85.0)
        self.metrics_service.set_threshold('validity', min_threshold=95.0)
        self.metrics_service.set_threshold('uniqueness', min_threshold=99.0)
        
        # Register default constraints
        self._register_business_constraints()
        
        # Set up privacy rules
        self._setup_privacy_rules()
    
    def _register_business_constraints(self):
        """Register business-specific constraints."""
        # User-related constraints
        self.constraint_validator.register_constraint(
            'valid_email_domain',
            lambda email: email.split('@')[1] in ['gmail.com', 'yahoo.com', 'hotmail.com'] 
            if '@' in email else False
        )
        
        self.constraint_validator.register_constraint(
            'nutrition_calories_realistic',
            lambda calories: 0 <= calories <= 10000 if isinstance(calories, (int, float)) else False
        )
        
        self.constraint_validator.register_constraint(
            'meal_plan_duration_valid',
            lambda duration: 1 <= duration <= 365 if isinstance(duration, int) else False
        )
    
    def _setup_privacy_rules(self):
        """Set up privacy and compliance rules."""
        # Register PII patterns for nutrition domain
        import re
        
        self.pii_detector.add_custom_pattern(
            'health_record_id',
            {
                'pii_type': 'health_data',
                'pattern': re.compile(r'\bHR\d{8}\b'),
                'confidence': 0.95,
                'description': 'Health record ID pattern'
            }
        )
        
        # Register masking rules
        self.masking_validator.register_masking_rule('email', 'hash')
        self.masking_validator.register_masking_rule('phone', 'substitute')
        self.masking_validator.register_masking_rule('user_id', 'encrypt')
    
    async def validate_data_quality(self, data: Any, 
                                  data_context: Dict[str, Any] = None,
                                  scopes: List[ValidationScope] = None) -> DataQualityReport:
        """Perform comprehensive data quality validation."""
        scopes = scopes or self.config.validation_scopes
        data_context = data_context or {}
        
        report = DataQualityReport()
        validation_tasks = []
        
        # Schema validation
        if ValidationScope.SCHEMA in scopes or ValidationScope.ALL in scopes:
            validation_tasks.append(self._validate_schema(data, data_context))
        
        # Consistency validation
        if ValidationScope.CONSISTENCY in scopes or ValidationScope.ALL in scopes:
            validation_tasks.append(self._validate_consistency(data, data_context))
        
        # Privacy validation
        if ValidationScope.PRIVACY in scopes or ValidationScope.ALL in scopes:
            validation_tasks.append(self._validate_privacy(data, data_context))
        
        # Execute all validations
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Collect results
        for i, result in enumerate(validation_results):
            if isinstance(result, Exception):
                logger.error(f"Validation task {i} failed: {result}")
                continue
            
            if isinstance(result, dict):
                report.validation_results.update(result)
        
        # Calculate metrics if monitoring is enabled
        if ValidationScope.MONITORING in scopes or ValidationScope.ALL in scopes:
            await self._calculate_quality_metrics(data, report)
        
        # Generate overall score and recommendations
        self._calculate_overall_score(report)
        self._generate_recommendations(report)
        
        return report
    
    async def _validate_schema(self, data: Any, context: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Validate data schema and structure."""
        results = {}
        
        try:
            # Schema validation
            schema_name = context.get('schema_name')
            if schema_name:
                schema_result = self.schema_validator.validate_against_schema(data, schema_name)
                results['schema_validation'] = schema_result
            
            # Data type validation
            type_rules = context.get('type_rules', {})
            if isinstance(data, dict) and type_rules:
                type_result = ValidationResult(is_valid=True)
                for field, field_type in type_rules.items():
                    if field in data:
                        field_result = self.data_type_validator.validate_field_type(
                            data[field], field_type
                        )
                        type_result = type_result.merge(field_result)
                results['type_validation'] = type_result
            
            # Constraint validation
            constraints = context.get('constraints', {})
            if isinstance(data, dict) and constraints:
                constraint_result = self.constraint_validator.validate_multiple_constraints(
                    data, constraints
                )
                results['constraint_validation'] = constraint_result
            
            # Referential integrity
            entity_name = context.get('entity_name')
            if isinstance(data, dict) and entity_name:
                integrity_result = self.referential_validator.validate_entity_relationships(
                    entity_name, data
                )
                results['referential_integrity'] = integrity_result
        
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            results['schema_validation'] = ValidationResult(
                is_valid=False, 
                errors=[f"Schema validation failed: {str(e)}"]
            )
        
        return results
    
    async def _validate_consistency(self, data: Any, context: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Validate data consistency across services."""
        results = {}
        
        try:
            # Cross-service consistency
            consistency_checks = context.get('consistency_checks', [])
            for check_name in consistency_checks:
                entity_ids = context.get('entity_ids', [])
                consistency_result = await self.cross_service_validator.validate_cross_service_consistency(
                    check_name, entity_ids
                )
                results[f'consistency_{check_name}'] = consistency_result
            
            # Event sourcing validation
            if context.get('validate_events'):
                aggregate_id = context.get('aggregate_id')
                aggregate_type = context.get('aggregate_type')
                if aggregate_id and aggregate_type:
                    event_result = await self.event_sourcing_validator.validate_event_sequence(
                        aggregate_id, aggregate_type
                    )
                    results['event_sourcing'] = event_result
            
            # Cache consistency
            cache_name = context.get('cache_name')
            cache_keys = context.get('cache_keys', [])
            if cache_name and cache_keys:
                cache_result = await self.cache_validator.validate_cache_consistency(
                    cache_name, cache_keys
                )
                results['cache_consistency'] = cache_result
        
        except Exception as e:
            logger.error(f"Consistency validation error: {e}")
            results['consistency_validation'] = ValidationResult(
                is_valid=False,
                errors=[f"Consistency validation failed: {str(e)}"]
            )
        
        return results
    
    async def _validate_privacy(self, data: Any, context: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Validate privacy and compliance requirements."""
        results = {}
        
        try:
            # PII detection
            if isinstance(data, (dict, list, str)):
                expected_pii_level = context.get('expected_pii_level')
                if expected_pii_level:
                    from src.models.analytics import PIILevel
                    pii_result = self.pii_detector.validate_pii_classification(
                        data if isinstance(data, dict) else {'data': data},
                        PIILevel(expected_pii_level)
                    )
                    results['pii_validation'] = pii_result
            
            # Data masking validation
            masking_fields = context.get('masking_fields', {})
            if isinstance(data, dict) and masking_fields:
                masking_result = ValidationResult(is_valid=True)
                for field, original_value in masking_fields.items():
                    if field in data:
                        field_result = self.masking_validator.validate_field_masking(
                            field, original_value, data[field]
                        )
                        masking_result = masking_result.merge(field_result)
                results['masking_validation'] = masking_result
            
            # Encryption validation
            encryption_fields = context.get('encryption_fields', [])
            if isinstance(data, dict) and encryption_fields:
                encryption_result = ValidationResult(is_valid=True)
                for field in encryption_fields:
                    if field in data:
                        field_result = self.encryption_validator.validate_field_encryption(
                            field, data[field]
                        )
                        encryption_result = encryption_result.merge(field_result)
                results['encryption_validation'] = encryption_result
            
            # Retention policy testing
            if context.get('test_retention'):
                from src.services.infrastructure.privacy_compliance import DataCategory
                data_category = context.get('data_category')
                if data_category and isinstance(data, list):
                    retention_result = self.retention_tester.validate_retention_compliance(
                        data, DataCategory(data_category)
                    )
                    results['retention_validation'] = retention_result
        
        except Exception as e:
            logger.error(f"Privacy validation error: {e}")
            results['privacy_validation'] = ValidationResult(
                is_valid=False,
                errors=[f"Privacy validation failed: {str(e)}"]
            )
        
        return results
    
    async def _calculate_quality_metrics(self, data: Any, report: DataQualityReport):
        """Calculate data quality metrics."""
        try:
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Calculate core metrics
                completeness = self.metrics_service.calculate_metric('completeness', data)
                validity = self.metrics_service.calculate_metric('validity', data)
                uniqueness = self.metrics_service.calculate_metric('uniqueness', data)
                
                report.metrics.update({
                    'completeness': completeness.value,
                    'validity': validity.value,
                    'uniqueness': uniqueness.value
                })
                
                # Detect anomalies
                if self.config.enable_anomaly_detection:
                    for metric_name, metric_value in report.metrics.items():
                        anomaly_result = self.anomaly_detector.detect_statistical_anomaly(
                            metric_name, metric_value
                        )
                        if anomaly_result['is_anomaly']:
                            report.alerts.append({
                                'type': 'anomaly',
                                'metric': metric_name,
                                'severity': AlertSeverity.HIGH,
                                'details': anomaly_result
                            })
        
        except Exception as e:
            logger.error(f"Metrics calculation error: {e}")
            report.metadata['metrics_error'] = str(e)
    
    def _calculate_overall_score(self, report: DataQualityReport):
        """Calculate overall data quality score."""
        scores = []
        
        # Validation results scoring
        for validation_result in report.validation_results.values():
            if validation_result.is_valid:
                scores.append(100.0)
            else:
                error_penalty = min(len(validation_result.errors) * 10, 50)
                warning_penalty = min(len(validation_result.warnings) * 5, 25)
                scores.append(max(0, 100 - error_penalty - warning_penalty))
        
        # Metrics scoring
        metric_scores = list(report.metrics.values())
        scores.extend(metric_scores)
        
        # Calculate weighted average
        if scores:
            report.overall_score = sum(scores) / len(scores)
        else:
            report.overall_score = 0.0
    
    def _generate_recommendations(self, report: DataQualityReport):
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Analyze validation results
        for validation_name, result in report.validation_results.items():
            if not result.is_valid:
                if 'schema' in validation_name:
                    recommendations.append("Review and update data schemas to match current data structure")
                elif 'consistency' in validation_name:
                    recommendations.append("Implement cross-service data synchronization mechanisms")
                elif 'privacy' in validation_name:
                    recommendations.append("Enhance privacy controls and data protection measures")
        
        # Analyze metrics
        if report.metrics.get('completeness', 100) < 95:
            recommendations.append("Improve data collection processes to reduce missing values")
        
        if report.metrics.get('validity', 100) < 90:
            recommendations.append("Implement stronger input validation and data cleansing")
        
        if report.metrics.get('uniqueness', 100) < 99:
            recommendations.append("Review data ingestion to prevent duplicate records")
        
        # Analyze alerts
        high_severity_alerts = [a for a in report.alerts if a.get('severity') == AlertSeverity.HIGH]
        if high_severity_alerts:
            recommendations.append("Address high-severity data quality alerts immediately")
        
        # Overall score recommendations
        if report.overall_score < 70:
            recommendations.append("Data quality requires immediate attention - implement comprehensive quality improvement plan")
        elif report.overall_score < 85:
            recommendations.append("Consider implementing additional data quality controls")
        
        report.recommendations = recommendations
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        return self.dashboard.generate_summary_report()
    
    def export_quality_report(self, format_type: str = 'json') -> str:
        """Export data quality report."""
        return self.dashboard.export_dashboard_data(format_type)
    
    async def run_continuous_monitoring(self, data_source: callable, 
                                      check_interval: timedelta = timedelta(minutes=5)):
        """Run continuous data quality monitoring."""
        logger.info("Starting continuous data quality monitoring")
        
        while True:
            try:
                # Fetch fresh data
                data = await data_source()
                
                # Run quality checks
                report = await self.validate_data_quality(data)
                
                # Log results
                if report.overall_score < 80:
                    logger.warning(f"Data quality score below threshold: {report.overall_score}")
                
                # Handle alerts
                for alert in report.alerts:
                    if alert.get('severity') in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                        logger.critical(f"Critical data quality alert: {alert}")
                
                # Wait for next check
                await asyncio.sleep(check_interval.total_seconds())
            
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retry
