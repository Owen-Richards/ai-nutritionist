"""
Test suite for Data Quality Assurance Framework

Comprehensive tests demonstrating all data quality components:
- Schema validation and data type checking
- Cross-service consistency validation
- PII detection and privacy validation
- Data quality metrics and anomaly detection
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.data_quality import (
    DataQualityFramework, DataQualityConfig, ValidationScope,
    SchemaValidator, DataTypeValidator, ConstraintValidator,
    PIIDetector, DataMaskingValidator, EncryptionValidator,
    DataQualityMetrics, AnomalyDetector, DataLineageTracker
)
from src.services.data_quality.validators import ValidationResult
from src.models.analytics import PIILevel, ConsentType
from src.services.infrastructure.privacy_compliance import DataCategory, RetentionPolicy


class TestDataQualityFramework:
    """Test the main data quality framework."""
    
    @pytest.fixture
    def framework(self):
        """Create a data quality framework instance."""
        config = DataQualityConfig(
            validation_scopes=[ValidationScope.ALL],
            enable_real_time_monitoring=True,
            enable_anomaly_detection=True
        )
        return DataQualityFramework(config)
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return [
            {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@gmail.com",
                "phone": "555-123-4567",
                "name": "John Doe",
                "age": 30,
                "weight_kg": 75.0,
                "height_cm": 180.0,
                "dietary_preferences": ["vegetarian"],
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T15:45:00Z"
            },
            {
                "user_id": "987f6543-e21c-43d2-b654-321098765432",
                "email": "jane.smith@yahoo.com",
                "phone": "555-987-6543",
                "name": "Jane Smith",
                "age": 28,
                "weight_kg": 65.0,
                "height_cm": 165.0,
                "dietary_preferences": ["keto", "gluten_free"],
                "created_at": "2024-01-10T09:15:00Z",
                "updated_at": "2024-01-25T12:30:00Z"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_comprehensive_data_validation(self, framework, sample_user_data):
        """Test comprehensive data quality validation."""
        context = {
            'schema_name': 'user_profile',
            'type_rules': {
                'email': 'email',
                'phone': 'phone',
                'user_id': 'uuid',
                'age': 'numeric_range',
                'created_at': 'datetime'
            },
            'constraints': {
                'age': 'user_age_range',
                'weight_kg': 'weight_range_kg',
                'height_cm': 'height_range_cm'
            },
            'expected_pii_level': 'sensitive',
            'entity_name': 'user'
        }
        
        report = await framework.validate_data_quality(sample_user_data, context)
        
        # Check that validation completed
        assert report is not None
        assert isinstance(report.overall_score, float)
        assert 0 <= report.overall_score <= 100
        
        # Check validation results
        assert len(report.validation_results) > 0
        
        # Should have metrics
        assert len(report.metrics) > 0
        
        # Should have recommendations
        assert isinstance(report.recommendations, list)
        
        print(f"Overall Quality Score: {report.overall_score}")
        print(f"Validation Results: {list(report.validation_results.keys())}")
        print(f"Metrics: {report.metrics}")
        print(f"Recommendations: {report.recommendations}")
    
    @pytest.mark.asyncio
    async def test_schema_validation_scope(self, framework, sample_user_data):
        """Test schema validation scope specifically."""
        context = {
            'type_rules': {
                'email': 'email',
                'user_id': 'uuid',
                'age': 'numeric_range'
            }
        }
        
        report = await framework.validate_data_quality(
            sample_user_data, 
            context, 
            scopes=[ValidationScope.SCHEMA]
        )
        
        # Should only have schema-related validations
        schema_related = [k for k in report.validation_results.keys() 
                         if 'validation' in k or 'integrity' in k]
        assert len(schema_related) > 0
        
        print("Schema Validation Results:")
        for name, result in report.validation_results.items():
            print(f"  {name}: {'PASS' if result.is_valid else 'FAIL'}")
            if result.errors:
                print(f"    Errors: {result.errors}")
            if result.warnings:
                print(f"    Warnings: {result.warnings}")


class TestSchemaValidation:
    """Test schema validation components."""
    
    @pytest.fixture
    def validator(self):
        return SchemaValidator()
    
    def test_pydantic_model_validation(self, validator):
        """Test validation against Pydantic models."""
        # Test valid user goal data
        valid_data = {
            'goal_type': 'weight_loss',
            'priority': 5,
            'target_value': 70.0,
            'target_date': '2024-06-01T00:00:00Z',
            'constraints': {'max_calories': 1800},
            'created_at': '2024-01-01T00:00:00Z'
        }
        
        result = validator.validate_against_schema(valid_data, 'user_goal')
        assert result.is_valid
        assert len(result.errors) == 0
        
        # Test invalid data
        invalid_data = {
            'goal_type': 'invalid_goal',  # Invalid enum value
            'priority': 'high',  # Should be integer
        }
        
        result = validator.validate_against_schema(invalid_data, 'user_goal')
        assert not result.is_valid
        assert len(result.errors) > 0
        print(f"Validation errors: {result.errors}")
    
    def test_nested_structure_validation(self, validator):
        """Test nested data structure validation."""
        expected_structure = {
            'user': {
                'id': str,
                'profile': {
                    'name': str,
                    'preferences': [str]
                }
            },
            'metadata': dict
        }
        
        valid_data = {
            'user': {
                'id': '123',
                'profile': {
                    'name': 'John',
                    'preferences': ['vegetarian', 'low_sodium']
                }
            },
            'metadata': {'source': 'api'}
        }
        
        result = validator.validate_nested_structure(valid_data, expected_structure)
        assert result.is_valid
        
        # Test invalid structure
        invalid_data = {
            'user': {
                'id': '123',
                'profile': {
                    'name': 'John',
                    'preferences': 'not_a_list'  # Should be list
                }
            }
            # Missing metadata
        }
        
        result = validator.validate_nested_structure(invalid_data, expected_structure)
        assert not result.is_valid
        print(f"Structure validation errors: {result.errors}")


class TestDataTypeValidation:
    """Test data type validation components."""
    
    @pytest.fixture
    def validator(self):
        return DataTypeValidator()
    
    def test_email_validation(self, validator):
        """Test email format validation."""
        valid_emails = [
            'user@example.com',
            'test.email+tag@domain.co.uk',
            'user123@gmail.com'
        ]
        
        invalid_emails = [
            'not_an_email',
            '@domain.com',
            'user@',
            'user@domain',
            123
        ]
        
        for email in valid_emails:
            result = validator.validate_field_type(email, 'email')
            assert result.is_valid, f"Email {email} should be valid"
        
        for email in invalid_emails:
            result = validator.validate_field_type(email, 'email')
            assert not result.is_valid, f"Email {email} should be invalid"
            print(f"Invalid email {email}: {result.errors}")
    
    def test_phone_validation(self, validator):
        """Test phone number validation."""
        valid_phones = [
            '+1-555-123-4567',
            '555-123-4567',
            '(555) 123-4567',
            '5551234567'
        ]
        
        invalid_phones = [
            '123',  # Too short
            'not-a-phone',
            '+1-555-123-456789',  # Too long
            123456789
        ]
        
        for phone in valid_phones:
            result = validator.validate_field_type(phone, 'phone')
            assert result.is_valid, f"Phone {phone} should be valid"
        
        for phone in invalid_phones:
            result = validator.validate_field_type(phone, 'phone')
            assert not result.is_valid, f"Phone {phone} should be invalid"
    
    def test_numeric_range_validation(self, validator):
        """Test numeric range validation."""
        result = validator.validate_field_type(25, 'numeric_range', min_val=18, max_val=65)
        assert result.is_valid
        
        result = validator.validate_field_type(10, 'numeric_range', min_val=18, max_val=65)
        assert not result.is_valid
        assert 'below minimum' in result.errors[0]
        
        result = validator.validate_field_type(70, 'numeric_range', min_val=18, max_val=65)
        assert not result.is_valid
        assert 'above maximum' in result.errors[0]


class TestPIIDetection:
    """Test PII detection and privacy validation."""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector()
    
    def test_email_detection(self, detector):
        """Test email PII detection."""
        text = "Please contact john.doe@gmail.com for more information"
        detections = detector.detect_pii_in_text(text)
        
        assert len(detections) > 0
        email_detection = next((d for d in detections if d.pii_type.value == 'email'), None)
        assert email_detection is not None
        assert 'john.doe@gmail.com' in email_detection.value
        assert email_detection.confidence > 0.9
    
    def test_phone_detection(self, detector):
        """Test phone number PII detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        detections = detector.detect_pii_in_text(text)
        
        phone_detections = [d for d in detections if d.pii_type.value == 'phone']
        assert len(phone_detections) >= 1  # Should detect at least one phone number
        
        for detection in phone_detections:
            assert detection.confidence > 0.8
            print(f"Detected phone: {detection.value} (confidence: {detection.confidence})")
    
    def test_structured_data_pii_detection(self, detector):
        """Test PII detection in structured data."""
        data = {
            'user_info': {
                'name': 'John Smith',
                'email': 'john.smith@email.com',
                'phone': '555-123-4567'
            },
            'metadata': {
                'created_at': '2024-01-01',
                'source': 'web_form'
            }
        }
        
        detections = detector.detect_pii_in_data(data)
        
        # Should detect email, phone, and possibly name
        pii_types = {d.pii_type.value for d in detections}
        assert 'email' in pii_types
        assert 'phone' in pii_types
        
        # Check field paths
        email_detection = next((d for d in detections if d.pii_type.value == 'email'), None)
        assert 'user_info.email' in email_detection.field_path
        
        print(f"Detected PII types: {pii_types}")
        for detection in detections:
            print(f"  {detection.pii_type.value}: {detection.value} at {detection.field_path}")
    
    def test_pii_level_validation(self, detector):
        """Test PII level classification validation."""
        # Data that should be PII-free
        clean_data = {
            'user_id': 'usr_123456',
            'preferences': ['vegetarian', 'low_sodium'],
            'created_at': '2024-01-01T00:00:00Z'
        }
        
        result = detector.validate_pii_classification(clean_data, PIILevel.NONE)
        # Should pass or have low-confidence warnings only
        assert result.is_valid or len([e for e in result.errors if 'high confidence' in e.lower()]) == 0
        
        # Data that contains PII
        pii_data = {
            'email': 'user@example.com',
            'phone': '555-123-4567',
            'preferences': ['vegetarian']
        }
        
        result = detector.validate_pii_classification(pii_data, PIILevel.NONE)
        assert not result.is_valid  # Should fail because PII is present
        print(f"PII validation errors: {result.errors}")


class TestDataMasking:
    """Test data masking validation."""
    
    @pytest.fixture
    def validator(self):
        return DataMaskingValidator()
    
    def test_hash_masking_validation(self, validator):
        """Test hash-based masking validation."""
        import hashlib
        
        original_email = "user@example.com"
        hashed_email = hashlib.sha256(original_email.encode()).hexdigest()
        
        result = validator.validate_field_masking('email', original_email, hashed_email)
        assert result.is_valid
        
        # Test invalid hash
        result = validator.validate_field_masking('email', original_email, 'not_a_hash')
        assert not result.is_valid
        print(f"Hash validation error: {result.errors}")
    
    def test_substitution_masking_validation(self, validator):
        """Test substitution masking validation."""
        validator.register_masking_rule('phone', 'substitute')
        
        original_phone = "555-123-4567"
        masked_phone = "555-XXX-XXXX"
        
        result = validator.validate_field_masking('phone', original_phone, masked_phone)
        assert result.is_valid
        
        # Test unmasked data
        result = validator.validate_field_masking('phone', original_phone, original_phone)
        assert not result.is_valid
    
    def test_data_anonymization_validation(self, validator):
        """Test k-anonymity validation."""
        original_data = {
            'name': 'John Smith',
            'email': 'john@email.com',
            'age': 30,
            'gender': 'male',
            'zip_code': '12345'
        }
        
        anonymized_data = {
            'name': '***REDACTED***',
            'email': '***REDACTED***',
            'age_range': '25-35',  # Generalized
            'gender': 'male',
            'zip_code_prefix': '123'  # Truncated
        }
        
        result = validator.validate_data_anonymization(
            original_data, anonymized_data, k_anonymity=5
        )
        
        assert result.is_valid
        print(f"Anonymization summary: {result.metadata['anonymization_summary']}")


class TestDataQualityMetrics:
    """Test data quality metrics calculation."""
    
    @pytest.fixture
    def metrics_service(self):
        return DataQualityMetrics()
    
    def test_completeness_calculation(self, metrics_service):
        """Test data completeness metric."""
        # Complete data
        complete_data = [
            {'name': 'John', 'email': 'john@email.com', 'age': 30},
            {'name': 'Jane', 'email': 'jane@email.com', 'age': 25}
        ]
        
        metric = metrics_service.calculate_metric('completeness', complete_data)
        assert metric.value == 100.0
        
        # Incomplete data
        incomplete_data = [
            {'name': 'John', 'email': None, 'age': 30},
            {'name': '', 'email': 'jane@email.com', 'age': 25}
        ]
        
        metric = metrics_service.calculate_metric('completeness', incomplete_data)
        assert metric.value < 100.0
        print(f"Completeness score for incomplete data: {metric.value}")
    
    def test_validity_calculation(self, metrics_service):
        """Test data validity metric."""
        data = [
            {'email': 'valid@email.com', 'age': 25},
            {'email': 'invalid_email', 'age': 30},
            {'email': 'another@valid.com', 'age': 'not_a_number'}
        ]
        
        validation_rules = {
            'email': lambda x: '@' in str(x) and '.' in str(x),
            'age': lambda x: isinstance(x, int) and 0 <= x <= 150
        }
        
        metric = metrics_service.calculate_metric(
            'validity', data, validation_rules=validation_rules
        )
        
        # Should be less than 100% due to invalid entries
        assert metric.value < 100.0
        print(f"Validity score: {metric.value}")
    
    def test_uniqueness_calculation(self, metrics_service):
        """Test data uniqueness metric."""
        # Data with duplicates
        data = [
            {'id': 1, 'email': 'user1@email.com'},
            {'id': 2, 'email': 'user2@email.com'},
            {'id': 3, 'email': 'user1@email.com'},  # Duplicate email
            {'id': 2, 'email': 'user3@email.com'}   # Duplicate id
        ]
        
        metric = metrics_service.calculate_metric(
            'uniqueness', data, unique_fields=['id', 'email']
        )
        
        # Should be less than 100% due to duplicates
        assert metric.value < 100.0
        print(f"Uniqueness score: {metric.value}")
    
    def test_timeliness_calculation(self, metrics_service):
        """Test data timeliness metric."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        old_timestamp = (now - timedelta(hours=48)).isoformat()
        recent_timestamp = (now - timedelta(hours=1)).isoformat()
        
        data = [
            {'created_at': recent_timestamp, 'data': 'recent'},
            {'created_at': old_timestamp, 'data': 'old'},
            {'created_at': now.isoformat(), 'data': 'current'}
        ]
        
        metric = metrics_service.calculate_metric(
            'timeliness', data, timestamp_field='created_at', max_age_hours=24
        )
        
        # Should be around 66% (2 out of 3 records are timely)
        assert 50 <= metric.value <= 100
        print(f"Timeliness score: {metric.value}")


class TestAnomalyDetection:
    """Test anomaly detection capabilities."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    def test_statistical_anomaly_detection(self, detector):
        """Test statistical anomaly detection."""
        # Train baseline with normal values
        normal_values = [95.0, 96.5, 97.2, 95.8, 96.1, 97.0, 95.5, 96.8, 97.5, 96.0]
        detector.train_baseline('completeness', normal_values)
        
        # Test normal value
        result = detector.detect_statistical_anomaly('completeness', 96.5)
        assert not result['is_anomaly']
        
        # Test anomalous value
        result = detector.detect_statistical_anomaly('completeness', 85.0)
        assert result['is_anomaly']
        assert result['z_score'] > detector.anomaly_threshold
        
        print(f"Anomaly detection result: {result}")
    
    def test_volume_anomaly_detection(self, detector):
        """Test volume-based anomaly detection."""
        # Historical hourly counts
        historical_counts = [100, 105, 98, 102, 99, 101, 103, 97, 100, 104]
        
        # Normal volume
        result = detector.detect_volume_anomaly(102, historical_counts)
        assert not result['is_anomaly']
        
        # Anomalous volume
        result = detector.detect_volume_anomaly(150, historical_counts)
        assert result['is_anomaly']
        
        print(f"Volume anomaly result: {result}")


class TestDataLineage:
    """Test data lineage tracking."""
    
    @pytest.fixture
    def tracker(self):
        return DataLineageTracker()
    
    def test_lineage_tracking(self, tracker):
        """Test data lineage graph construction and traversal."""
        from src.services.data_quality.monitoring import DataLineageNode, DataLineageEdge
        
        # Create nodes
        source_node = DataLineageNode(
            id='user_input',
            name='User Input API',
            type='source',
            properties={'endpoint': '/api/users'}
        )
        
        transform_node = DataLineageNode(
            id='data_validation',
            name='Data Validation Service',
            type='transformation',
            properties={'rules': ['email_validation', 'phone_validation']}
        )
        
        dest_node = DataLineageNode(
            id='user_database',
            name='User Database',
            type='destination',
            properties={'table': 'users'}
        )
        
        # Add nodes
        tracker.add_node(source_node)
        tracker.add_node(transform_node)
        tracker.add_node(dest_node)
        
        # Add edges
        edge1 = DataLineageEdge('user_input', 'data_validation', 'validation')
        edge2 = DataLineageEdge('data_validation', 'user_database', 'insert')
        
        tracker.add_edge(edge1)
        tracker.add_edge(edge2)
        
        # Test upstream tracing
        upstream = tracker.trace_lineage_upstream('user_database')
        upstream_ids = [node.id for node in upstream]
        assert 'user_input' in upstream_ids
        assert 'data_validation' in upstream_ids
        
        # Test downstream tracing
        downstream = tracker.trace_lineage_downstream('user_input')
        downstream_ids = [node.id for node in downstream]
        assert 'data_validation' in downstream_ids
        assert 'user_database' in downstream_ids
        
        print(f"Upstream from user_database: {upstream_ids}")
        print(f"Downstream from user_input: {downstream_ids}")
    
    def test_quality_impact_analysis(self, tracker):
        """Test quality impact analysis."""
        from src.services.data_quality.monitoring import DataLineageNode, DataLineageEdge
        
        # Set up lineage (reuse from previous test)
        self.test_lineage_tracking(tracker)
        
        # Analyze impact of quality issues
        quality_issues = ['completeness', 'accuracy']
        impact = tracker.analyze_quality_impact('user_input', quality_issues)
        
        assert 'source_node' in impact
        assert impact['source_node'] == 'user_input'
        assert 'affected_downstream_nodes' in impact
        assert impact['affected_downstream_nodes'] > 0
        
        print(f"Quality impact analysis: {impact}")


@pytest.mark.asyncio
async def test_integration_scenario():
    """Integration test demonstrating complete data quality pipeline."""
    print("\n" + "="*60)
    print("COMPREHENSIVE DATA QUALITY ASSURANCE DEMONSTRATION")
    print("="*60)
    
    # Initialize framework
    config = DataQualityConfig(
        validation_scopes=[ValidationScope.ALL],
        enable_real_time_monitoring=True,
        enable_anomaly_detection=True,
        privacy_compliance_level="strict"
    )
    framework = DataQualityFramework(config)
    
    # Sample meal plan data with various quality issues
    meal_plan_data = [
        {
            "plan_id": "plan_123",
            "user_id": "user_456",  # Missing proper UUID format
            "email": "john.doe@gmail.com",  # PII present
            "phone": "555-0123",  # Invalid phone format
            "meals": [
                {
                    "meal_id": "meal_1",
                    "name": "Grilled Chicken Salad",
                    "calories": 450,
                    "protein_g": 35.0,
                    "carbs_g": None,  # Missing data
                    "fat_g": 15.0
                },
                {
                    "meal_id": "meal_2",
                    "name": "",  # Empty name
                    "calories": -100,  # Invalid negative calories
                    "protein_g": 25.0,
                    "carbs_g": 30.0,
                    "fat_g": 8.0
                }
            ],
            "created_at": "2024-01-15T10:30:00Z",
            "dietary_preferences": ["vegetarian", "low_sodium"],
            "budget_limit": 50.0
        },
        {
            "plan_id": "plan_456",
            "user_id": "user_789",
            "email": "jane.smith@yahoo.com",
            "phone": "555-987-6543",
            "meals": [
                {
                    "meal_id": "meal_3",
                    "name": "Quinoa Bowl",
                    "calories": 380,
                    "protein_g": 12.0,
                    "carbs_g": 65.0,
                    "fat_g": 8.0
                }
            ],
            "created_at": "2024-01-20T15:45:00Z",
            "dietary_preferences": ["vegan", "gluten_free"],
            "budget_limit": 75.0
        }
    ]
    
    # Define validation context
    context = {
        'schema_name': 'meal_plan',
        'type_rules': {
            'email': 'email',
            'phone': 'phone',
            'plan_id': 'string_length',
            'calories': 'numeric_range',
            'created_at': 'datetime'
        },
        'constraints': {
            'calories': 'calorie_range',
            'budget_limit': 'budget_positive'
        },
        'expected_pii_level': 'sensitive',
        'entity_name': 'meal_plan',
        'masking_fields': {
            'email': 'john.doe@gmail.com'  # Original value for masking validation
        }
    }
    
    print("\n1. RUNNING COMPREHENSIVE DATA QUALITY VALIDATION")
    print("-" * 50)
    
    # Run comprehensive validation
    report = await framework.validate_data_quality(meal_plan_data, context)
    
    print(f"Overall Quality Score: {report.overall_score:.2f}/100")
    print(f"Validation Components: {len(report.validation_results)}")
    print(f"Quality Metrics: {len(report.metrics)}")
    print(f"Alerts Generated: {len(report.alerts)}")
    print(f"Recommendations: {len(report.recommendations)}")
    
    print("\n2. DETAILED VALIDATION RESULTS")
    print("-" * 50)
    
    for validation_name, result in report.validation_results.items():
        status = "✅ PASS" if result.is_valid else "❌ FAIL"
        print(f"{validation_name}: {status}")
        
        if result.errors:
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"  ❌ {error}")
        
        if result.warnings:
            for warning in result.warnings[:2]:  # Show first 2 warnings
                print(f"  ⚠️  {warning}")
    
    print("\n3. QUALITY METRICS")
    print("-" * 50)
    
    for metric_name, value in report.metrics.items():
        print(f"{metric_name.capitalize()}: {value:.2f}%")
    
    print("\n4. DATA PRIVACY ANALYSIS")
    print("-" * 50)
    
    # Demonstrate PII detection
    pii_detector = framework.pii_detector
    all_detections = []
    
    for record in meal_plan_data:
        detections = pii_detector.detect_pii_in_data(record)
        all_detections.extend(detections)
    
    pii_summary = {}
    for detection in all_detections:
        pii_type = detection.pii_type.value
        if pii_type not in pii_summary:
            pii_summary[pii_type] = 0
        pii_summary[pii_type] += 1
    
    print("PII Detection Summary:")
    for pii_type, count in pii_summary.items():
        print(f"  {pii_type}: {count} instances detected")
    
    print("\n5. ANOMALY DETECTION")
    print("-" * 50)
    
    # Train baseline and detect anomalies
    detector = framework.anomaly_detector
    
    # Train with normal completeness values
    normal_completeness = [95.0, 96.5, 97.0, 95.8, 96.2]
    detector.train_baseline('completeness', normal_completeness)
    
    # Check current completeness
    current_completeness = report.metrics.get('completeness', 0)
    anomaly_result = detector.detect_statistical_anomaly('completeness', current_completeness)
    
    if anomaly_result['is_anomaly']:
        print(f"🚨 ANOMALY DETECTED: Completeness score {current_completeness:.2f} is anomalous")
        print(f"   Z-score: {anomaly_result['z_score']:.2f}")
    else:
        print(f"✅ Completeness score {current_completeness:.2f} is within normal range")
    
    print("\n6. RECOMMENDATIONS")
    print("-" * 50)
    
    for i, recommendation in enumerate(report.recommendations, 1):
        print(f"{i}. {recommendation}")
    
    print("\n7. DASHBOARD SUMMARY")
    print("-" * 50)
    
    dashboard_data = framework.get_dashboard_data()
    print(f"Report Timestamp: {dashboard_data['report_timestamp']}")
    print(f"Overall Score: {dashboard_data['overall_score']:.2f}")
    print(f"Total Alerts: {dashboard_data['alerts_summary']['total_alerts']}")
    print(f"Unresolved Alerts: {dashboard_data['alerts_summary']['unresolved_alerts']}")
    
    print("\n8. DATA LINEAGE DEMONSTRATION")
    print("-" * 50)
    
    # Set up sample lineage
    lineage_tracker = framework.lineage_tracker
    from src.services.data_quality.monitoring import DataLineageNode, DataLineageEdge
    
    # Add nodes for meal planning pipeline
    nodes = [
        DataLineageNode('api_input', 'User API Input', 'source'),
        DataLineageNode('validation', 'Data Validation', 'transformation'),
        DataLineageNode('meal_db', 'Meal Database', 'destination'),
        DataLineageNode('analytics', 'Analytics Engine', 'destination')
    ]
    
    for node in nodes:
        lineage_tracker.add_node(node)
    
    # Add edges
    edges = [
        DataLineageEdge('api_input', 'validation', 'validate'),
        DataLineageEdge('validation', 'meal_db', 'store'),
        DataLineageEdge('validation', 'analytics', 'analyze')
    ]
    
    for edge in edges:
        lineage_tracker.add_edge(edge)
    
    # Analyze impact
    impact = lineage_tracker.analyze_quality_impact('api_input', ['completeness', 'validity'])
    print(f"Quality Impact Analysis:")
    print(f"  Source: {impact['source_node']}")
    print(f"  Affected Downstream Nodes: {impact['affected_downstream_nodes']}")
    
    for detail in impact['impact_details']:
        print(f"  - {detail['node_name']}: {detail['impact_severity']} impact")
    
    print("\n" + "="*60)
    print("DATA QUALITY ASSURANCE DEMONSTRATION COMPLETE")
    print("="*60)
    
    # Assert overall quality
    assert report.overall_score >= 0
    assert len(report.validation_results) > 0
    assert len(report.recommendations) > 0
    
    return report


if __name__ == "__main__":
    # Run the integration test
    import asyncio
    asyncio.run(test_integration_scenario())
