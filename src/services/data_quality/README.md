# Data Quality Assurance Framework

A comprehensive data quality assurance system for the AI Nutritionist application that provides schema validation, consistency checks, privacy compliance, and real-time monitoring.

## 🎯 Overview

The Data Quality Assurance Framework ensures data reliability, privacy compliance, and consistency across all components of the AI Nutritionist platform. It provides automated validation, monitoring, and alerting capabilities to maintain high-quality data standards.

## 🏗️ Architecture

### Core Components

1. **Data Validation**

   - Schema validation using Pydantic models
   - Data type checking and format validation
   - Business rule constraint validation
   - Referential integrity validation

2. **Data Consistency**

   - Cross-service consistency validation
   - Event sourcing integrity checks
   - Cache consistency validation
   - Database consistency monitoring

3. **Data Privacy**

   - PII detection and classification
   - Data masking verification
   - Encryption validation
   - Retention policy compliance testing

4. **Data Monitoring**
   - Real-time quality metrics calculation
   - Anomaly detection and alerting
   - Data lineage tracking
   - Interactive quality dashboards

## 🚀 Quick Start

### Basic Usage

```python
from src.services.data_quality import DataQualityFramework, DataQualityConfig

# Initialize framework
config = DataQualityConfig(enable_real_time_monitoring=True)
framework = DataQualityFramework(config)

# Validate data
data = [{"user_id": "123", "email": "user@example.com"}]
context = {"schema_name": "user_profile", "expected_pii_level": "sensitive"}

report = await framework.validate_data_quality(data, context)
print(f"Quality Score: {report.overall_score}")
```

### Advanced Configuration

```python
from src.services.data_quality.examples import DataQualityManager

# Production-ready manager
manager = DataQualityManager("production")

# Validate user data
user_data = {...}  # Your user data
result = await manager.validate_user_data(user_data)

if result['is_valid']:
    print("Data quality passed!")
else:
    print(f"Issues found: {result['recommendations']}")
```

## 📊 Features

### 1. Schema Validation

Validates data against predefined schemas and data models:

```python
# Pydantic model validation
validator = SchemaValidator()
result = validator.validate_against_schema(data, 'user_profile')

# Custom structure validation
expected_structure = {
    'user': {'id': str, 'profile': {'name': str}},
    'metadata': dict
}
result = validator.validate_nested_structure(data, expected_structure)
```

### 2. Data Type Validation

Comprehensive data type and format checking:

```python
validator = DataTypeValidator()

# Email validation
result = validator.validate_field_type("user@example.com", "email")

# Numeric range validation
result = validator.validate_field_type(25, "numeric_range", min_val=18, max_val=65)
```

### 3. PII Detection

Automatic detection and classification of personally identifiable information:

```python
detector = PIIDetector()

# Detect PII in text
detections = detector.detect_pii_in_text("Contact john.doe@gmail.com")

# Validate PII classification
result = detector.validate_pii_classification(data, PIILevel.SENSITIVE)
```

### 4. Quality Metrics

Calculate comprehensive data quality metrics:

```python
metrics = DataQualityMetrics()

# Calculate completeness
completeness = metrics.calculate_metric('completeness', data)

# Calculate accuracy with validation rules
rules = {'email': lambda x: '@' in x}
accuracy = metrics.calculate_metric('accuracy', data, validation_rules=rules)
```

### 5. Anomaly Detection

Statistical and pattern-based anomaly detection:

```python
detector = AnomalyDetector()

# Train baseline
detector.train_baseline('completeness', [95.0, 96.5, 97.0])

# Detect anomalies
result = detector.detect_statistical_anomaly('completeness', 85.0)
```

### 6. Data Lineage

Track data dependencies and impact analysis:

```python
tracker = DataLineageTracker()

# Add data pipeline nodes
source_node = DataLineageNode('api_input', 'API Input', 'source')
tracker.add_node(source_node)

# Analyze quality impact
impact = tracker.analyze_quality_impact('api_input', ['completeness'])
```

## 🔧 Configuration

### Environment Configurations

#### Development

```python
DEVELOPMENT_CONFIG = DataQualityConfig(
    validation_scopes=[ValidationScope.SCHEMA, ValidationScope.PRIVACY],
    enable_real_time_monitoring=True,
    enable_anomaly_detection=False,
    privacy_compliance_level="moderate"
)
```

#### Production

```python
PRODUCTION_CONFIG = DataQualityConfig(
    validation_scopes=[ValidationScope.ALL],
    enable_real_time_monitoring=True,
    enable_anomaly_detection=True,
    alert_thresholds={
        'completeness': 95.0,
        'accuracy': 90.0,
        'consistency': 98.0
    },
    privacy_compliance_level="strict"
)
```

### Validation Contexts

Define validation contexts for different data types:

```python
USER_PROFILE_CONTEXT = {
    'schema_name': 'user_profile',
    'type_rules': {
        'email': 'email',
        'phone': 'phone',
        'age': 'numeric_range'
    },
    'constraints': {
        'age': 'user_age_range'
    },
    'expected_pii_level': 'sensitive',
    'encryption_fields': ['email', 'phone']
}
```

## 🔒 Privacy Compliance

### GDPR Compliance Features

- **PII Detection**: Automatically detect 15+ types of PII
- **Data Masking**: Validate hash, encryption, and substitution masking
- **Retention Policies**: Test compliance with data retention requirements
- **Consent Validation**: Verify user consent for data processing

### Privacy Validation Example

```python
# Validate encryption
validator = EncryptionValidator()
validator.register_encryption_requirement('email', 'AES', 256)
result = validator.validate_field_encryption('email', encrypted_data)

# Test retention compliance
tester = RetentionPolicyTester()
result = tester.validate_retention_compliance(records, DataCategory.IDENTITY)
```

## 📈 Monitoring & Dashboards

### Real-time Monitoring

```python
# Continuous monitoring
async def monitor_data_quality():
    data_sources = {
        'user_service': get_user_data,
        'meal_service': get_meal_data
    }

    await manager.run_continuous_monitoring(data_sources)
```

### Dashboard Data

```python
# Generate dashboard
dashboard = framework.get_dashboard_data()

# Export reports
json_report = framework.export_quality_report('json')
csv_report = framework.export_quality_report('csv')
```

## 🧪 Testing

### Run Tests

```bash
# Run all data quality tests
python -m pytest tests/data_quality/

# Run specific test categories
python -m pytest tests/data_quality/test_data_quality_framework.py::TestSchemaValidation
python -m pytest tests/data_quality/test_data_quality_framework.py::TestPIIDetection

# Run integration test
python -m pytest tests/data_quality/test_data_quality_framework.py::test_integration_scenario -v
```

### Test Coverage

The test suite includes:

- ✅ Schema validation tests
- ✅ Data type validation tests
- ✅ PII detection and privacy tests
- ✅ Data masking validation tests
- ✅ Quality metrics calculation tests
- ✅ Anomaly detection tests
- ✅ Data lineage tests
- ✅ Comprehensive integration tests

## 📊 Quality Metrics

### Supported Metrics

| Metric           | Description                                   | Threshold |
| ---------------- | --------------------------------------------- | --------- |
| **Completeness** | Percentage of non-null values                 | 95%+      |
| **Accuracy**     | Percentage of values passing validation rules | 90%+      |
| **Consistency**  | Cross-system data consistency                 | 98%+      |
| **Timeliness**   | Data freshness within time windows            | 95%+      |
| **Validity**     | Format and type compliance                    | 95%+      |
| **Uniqueness**   | Absence of duplicate records                  | 99%+      |
| **Integrity**    | Referential integrity compliance              | 99%+      |

### Quality Scoring

- **90-100**: Excellent quality
- **80-89**: Good quality, minor issues
- **70-79**: Acceptable quality, needs attention
- **Below 70**: Poor quality, immediate action required

## 🔍 Examples

### API Endpoint Validation

```python
async def validate_api_request(request_data):
    manager = DataQualityManager("production")
    result = await manager.validate_user_data(request_data)

    if not result['is_valid']:
        return {"error": "Validation failed", "details": result}

    return {"status": "success"}
```

### Batch Processing Validation

```python
async def validate_batch_data(batch_records):
    results = []
    for record in batch_records:
        result = await manager.validate_meal_plan_data(record)
        results.append({
            "id": record["id"],
            "quality_score": result["overall_score"],
            "is_valid": result["is_valid"]
        })

    return results
```

### Continuous Monitoring

```python
async def setup_monitoring():
    data_sources = {
        "user_service": lambda: fetch_recent_users(),
        "meal_service": lambda: fetch_recent_meals(),
        "analytics_service": lambda: fetch_recent_events()
    }

    # Run continuous monitoring (production deployment)
    await manager.run_continuous_monitoring(data_sources)
```

## 🚨 Alerting

### Alert Types

1. **Schema Violations**: Data doesn't match expected schema
2. **Quality Degradation**: Metrics fall below thresholds
3. **Privacy Violations**: PII detected in non-PII fields
4. **Consistency Issues**: Cross-service data mismatches
5. **Anomalies**: Statistical outliers in quality metrics

### Alert Severity Levels

- **Critical**: Immediate action required (data corruption, privacy breach)
- **High**: Urgent attention needed (quality below 70%)
- **Medium**: Should be addressed (quality 70-80%)
- **Low**: Informational (quality 80-90%)

## 🔧 Customization

### Custom Validators

```python
# Register custom constraint
framework.constraint_validator.register_constraint(
    'valid_meal_calories',
    lambda calories: 50 <= calories <= 2000
)

# Register custom PII pattern
framework.pii_detector.add_custom_pattern(
    'health_record_id',
    PIIPattern(PIIType.HEALTH_DATA, re.compile(r'HR\d{8}'), 0.95, "Health Record ID")
)
```

### Custom Metrics

```python
# Register custom metric calculator
def calculate_nutrition_balance(data):
    # Custom logic for nutrition balance metric
    return balance_score

framework.metrics_service.register_metric_calculator(
    'nutrition_balance',
    calculate_nutrition_balance
)
```

## 📚 API Reference

### Core Classes

- `DataQualityFramework`: Main framework orchestrator
- `SchemaValidator`: Schema and structure validation
- `DataTypeValidator`: Type and format validation
- `PIIDetector`: Privacy and PII detection
- `DataQualityMetrics`: Quality metrics calculation
- `AnomalyDetector`: Statistical anomaly detection
- `DataLineageTracker`: Data dependency tracking

### Configuration Classes

- `DataQualityConfig`: Framework configuration
- `ValidationScope`: Validation scope enumeration
- `ConsistencyCheck`: Cross-service consistency configuration
- `PIIPattern`: PII detection pattern definition

## 🛠️ Integration Guide

### 1. Framework Setup

```python
# Initialize in your application
from src.services.data_quality.examples import DataQualityManager

# Production setup
quality_manager = DataQualityManager("production")

# Development setup
quality_manager = DataQualityManager("development")
```

### 2. Middleware Integration

```python
# FastAPI middleware example
@app.middleware("http")
async def data_quality_middleware(request: Request, call_next):
    # Validate request data
    if request.method == "POST":
        body = await request.body()
        data = json.loads(body)

        result = await quality_manager.validate_user_data(data)
        if not result['is_valid']:
            return JSONResponse(
                status_code=400,
                content={"error": "Data quality validation failed"}
            )

    response = await call_next(request)
    return response
```

### 3. Background Monitoring

```python
# Celery task example
@celery.task
async def monitor_data_quality():
    dashboard = quality_manager.get_dashboard_summary()

    # Send alerts if quality is poor
    if dashboard['overall_score'] < 80:
        send_alert(f"Data quality score: {dashboard['overall_score']}")
```

## 🤝 Contributing

1. Follow the established patterns for validators and metrics
2. Add comprehensive tests for new features
3. Update documentation and examples
4. Ensure privacy compliance for any PII-related features

## 📄 License

This data quality framework is part of the AI Nutritionist application and follows the same licensing terms.

---

**Need Help?** Check the examples in `src/services/data_quality/examples.py` or run the comprehensive test suite to see the framework in action.
