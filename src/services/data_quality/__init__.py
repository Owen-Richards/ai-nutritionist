"""
Data Quality Assurance Framework

Comprehensive data quality, consistency, privacy, and monitoring system
for the AI Nutritionist application.

Components:
- Schema validation and data type checking
- Cross-service consistency validation
- PII detection and privacy validation
- Data quality metrics and anomaly detection
- Data lineage tracking and quality dashboards
"""

from .validators import (
    SchemaValidator,
    DataTypeValidator,
    ConstraintValidator,
    ReferentialIntegrityValidator
)
from .consistency import (
    CrossServiceConsistencyValidator,
    EventSourcingValidator,
    CacheConsistencyValidator,
    DatabaseConsistencyValidator
)
from .privacy import (
    PIIDetector,
    DataMaskingValidator,
    EncryptionValidator,
    RetentionPolicyTester
)
from .monitoring import (
    DataQualityMetrics,
    AnomalyDetector,
    DataLineageTracker,
    QualityDashboard
)
from .framework import DataQualityFramework

__all__ = [
    'SchemaValidator',
    'DataTypeValidator', 
    'ConstraintValidator',
    'ReferentialIntegrityValidator',
    'CrossServiceConsistencyValidator',
    'EventSourcingValidator',
    'CacheConsistencyValidator',
    'DatabaseConsistencyValidator',
    'PIIDetector',
    'DataMaskingValidator',
    'EncryptionValidator',
    'RetentionPolicyTester',
    'DataQualityMetrics',
    'AnomalyDetector',
    'DataLineageTracker',
    'QualityDashboard',
    'DataQualityFramework'
]
