# Tests Directory

This directory contains the complete test suite for the AI Nutritionist application, organized by test type for better maintainability and faster execution.

## 📁 Structure

```
tests/
├── unit/                     # Unit tests (fast, isolated)
├── integration/              # Integration tests (with external services)
├── fixtures/                 # Test data and mock objects
└── conftest.py              # Pytest configuration (coming soon)
```

## 🧪 Test Categories

### Unit Tests (`tests/unit/`)
Fast, isolated tests that test individual components without external dependencies.

- **test_ai_service.py** - AI service prompt generation and response parsing
- **test_subscription_service.py** - Subscription management and billing logic
- **test_nutrition_tracking.py** - Nutrition calculation and tracking
- **test_multi_goal_functionality.py** - Multi-goal meal planning features
- **test_multi_user_privacy.py** - Family sharing and privacy controls
- **test_spam_protection.py** - Anti-spam and security measures

### Integration Tests (`tests/integration/`)
Tests that verify interaction between components and external services.

- **test_edamam_integration.py** - Edamam nutrition API integration
- **test_edamam_basic.py** - Basic Edamam API functionality
- **test_aws_sms.py** - AWS SMS service integration
- **test_international_phone.py** - International phone number handling

### Test Fixtures (`tests/fixtures/`)
Reusable test data and mock objects (to be organized here).

## 🚀 Running Tests

### Run All Tests
```bash
# Run everything
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/
```

### Run Specific Test Types
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_ai_service.py

# Specific test function
pytest tests/unit/test_ai_service.py::TestAIService::test_generate_meal_plan
```

### Run Tests by Markers (coming soon)
```bash
# Fast tests only
pytest -m "not slow"

# Integration tests requiring external APIs
pytest -m "integration"

# Tests requiring AWS credentials
pytest -m "aws"
```

## 🔧 Test Configuration

### Environment Setup
Tests use environment-specific configuration:

- **Development**: Uses test database and mock services
- **CI/CD**: Uses containerized test environment  
- **Local**: Can use either real or mock external services

### Required Environment Variables
```bash
# For integration tests
export EDAMAM_APP_ID="test_app_id"
export EDAMAM_APP_KEY="test_app_key"
export AWS_REGION="us-east-1"

# For comprehensive testing
export TWILIO_ACCOUNT_SID="test_sid"
export TWILIO_AUTH_TOKEN="test_token"
```

## 📊 Test Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| Core Services | 65% | 90% |
| Models | 45% | 85% |
| Handlers | 40% | 80% |
| Utilities | 80% | 95% |
| **Overall** | **58%** | **85%** |

## 🐛 Known Issues (Being Fixed)

### Import Errors
- Services are being consolidated, causing temporary import issues
- Will be resolved when service layer consolidation is complete

### Configuration Errors  
- Some tests need AWS region configuration
- Fixed by using centralized settings module

### Mock Issues
- Some mocks need updating for new service interfaces
- Being addressed with service consolidation

## 🔄 Test Improvement Plan

### Phase 1: Fix Import Issues ✅
- ✅ Reorganize test files into unit/integration structure
- 🔄 Update imports for new directory structure
- 🔄 Add proper test configuration

### Phase 2: Service Mock Updates
- 🔄 Update mocks for consolidated services
- 🔄 Add fixtures for common test data
- 🔄 Standardize test patterns

### Phase 3: Coverage & Performance
- 📋 Add missing test cases for new features
- 📋 Add performance benchmarks
- 📋 Add contract tests for external APIs

## 🏃‍♂️ Quick Start

1. **Install test dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set up test environment:**
   ```bash
   cp .env.template .env.test
   # Edit .env.test with test values
   ```

3. **Run fast tests:**
   ```bash
   pytest tests/unit/ -v
   ```

4. **Run full test suite:**
   ```bash
   pytest tests/ --cov=src/ --cov-report=html
   ```

## 📚 Writing New Tests

### Test Naming Convention
- File names: `test_<module_name>.py`
- Class names: `Test<ClassName>`  
- Method names: `test_<what_it_tests>`

### Example Test Structure
```python
import pytest
from unittest.mock import Mock, patch

from src.services.example_service import ExampleService


class TestExampleService:
    """Test cases for ExampleService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = ExampleService()
    
    def test_example_functionality(self):
        """Test that example functionality works correctly"""
        # Arrange
        input_data = {"test": "data"}
        
        # Act
        result = self.service.process(input_data)
        
        # Assert
        assert result is not None
        assert result["processed"] is True
    
    @pytest.mark.integration
    def test_external_api_integration(self):
        """Test integration with external API"""
        # Integration test code here
        pass
```

## 📈 Test Metrics

Track test health with these metrics:
- **Execution Time**: Unit tests < 2s, Integration tests < 30s
- **Flakiness**: < 1% test failure rate
- **Coverage**: > 85% line coverage
- **Maintainability**: Tests updated with code changes

---

For questions about testing, see the main project documentation or create an issue.
