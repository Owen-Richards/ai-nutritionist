# E2E Test Suite Documentation

## 🎯 Overview

This comprehensive End-to-End (E2E) test suite provides automated testing for the AI Nutritionist application across multiple channels, user journeys, and performance scenarios.

## 🏗️ Architecture

```
tests/e2e/
├── framework/          # Core testing framework
│   ├── __init__.py
│   └── base.py        # Base test classes and utilities
├── user_journeys/     # Critical user journey tests
│   └── test_critical_flows.py
├── channels/          # Multi-channel testing
│   └── test_multi_channel.py
├── performance/       # Performance and load testing
│   └── test_performance_scenarios.py
├── utils/            # Testing utilities and automation
│   └── automation.py
├── fixtures/         # Test fixtures and data
│   └── test_fixtures.py
├── config.py         # Configuration management
├── test_runner.py    # Main test runner
└── README.md        # This documentation
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Chrome/Firefox** browsers installed
3. **Local development environment** running (for local tests)

### Installation

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Setup E2E test environment
python run_e2e_tests.py setup
```

### Running Tests

```bash
# Quick smoke tests
python run_e2e_tests.py smoke

# Full test suite
python run_e2e_tests.py all

# Specific test categories
python run_e2e_tests.py user-journeys
python run_e2e_tests.py multi-channel
python run_e2e_tests.py performance

# Cross-browser testing
python run_e2e_tests.py cross-browser

# Different environments
python run_e2e_tests.py all --environment staging
```

## 📋 Test Categories

### 1. User Journey Tests

Critical end-to-end user workflows:

- **Registration → First Meal Plan**: Complete onboarding flow
- **Daily Meal Tracking**: Logging meals through messaging
- **Payment Subscription Flow**: Upgrade to premium subscription
- **Family Account Setup**: Adding and managing family members
- **Health Data Sync**: Integrating external health data

```bash
# Run user journey tests
python run_e2e_tests.py user-journeys --environment local
```

### 2. Multi-Channel Tests

Testing across different communication channels:

- **WhatsApp Conversation Flow**: Complete bot interactions
- **SMS Interaction Flow**: SMS-specific features and limitations
- **Web App Flow**: Web interface functionality
- **Cross-Channel Consistency**: Data sync across channels
- **Channel-Specific Features**: Platform-specific capabilities

```bash
# Run multi-channel tests
python run_e2e_tests.py multi-channel --environment staging
```

### 3. Performance Tests

Comprehensive performance validation:

- **Load Testing**: Normal usage patterns (10-200 users)
- **Stress Testing**: Finding breaking points (up to 1000+ users)
- **Spike Testing**: Sudden traffic increases
- **Endurance Testing**: Long-term stability (2+ hours)

```bash
# Run performance tests
python run_e2e_tests.py performance --environment staging
```

## 🛠️ Framework Components

### Base Test Classes

```python
from tests.e2e.framework import (
    BaseE2ETest,        # Base class for all E2E tests
    WebE2ETest,         # Selenium-based web testing
    APIE2ETest,         # API testing utilities
    MessagingE2ETest,   # Messaging channel testing
    PerformanceE2ETest  # Performance testing base
)
```

### Test Automation Utilities

```python
from tests.e2e.utils.automation import (
    SeleniumAutomation,           # Advanced Selenium utilities
    APIAutomation,                # HTTP API testing
    MessageSimulationAutomation,  # Message simulation
    DatabaseVerificationAutomation # Database validation
)
```

### Test Fixtures

```python
# Available fixtures
@pytest.fixture
def test_user():
    """Single test user"""

@pytest.fixture
def test_users():
    """Multiple test users"""

@pytest.fixture
def premium_test_user():
    """Premium subscription user"""

@pytest.fixture
def family_test_user():
    """User with family members"""
```

## 🔧 Configuration

### Environment Configuration

Tests can run against different environments:

```python
# Environment settings
ENVIRONMENTS = {
    'local': {
        'web_app_url': 'http://localhost:3000',
        'api_base_url': 'http://localhost:8000',
        'mock_services': True
    },
    'staging': {
        'web_app_url': 'https://staging.ai-nutritionist.com',
        'api_base_url': 'https://staging-api.ai-nutritionist.com',
        'mock_services': False
    }
}
```

### Browser Configuration

```python
# Browser settings
BROWSER_CONFIGS = {
    'chrome': {
        'headless': True,
        'window_size': (1920, 1080),
        'options': ['--no-sandbox', '--disable-dev-shm-usage']
    },
    'firefox': {
        'headless': True,
        'window_size': (1920, 1080)
    }
}
```

### Performance Configuration

```python
# Performance test settings
PERFORMANCE_CONFIG = {
    'load_test': {
        'users': [10, 50, 100, 200],
        'duration_minutes': [5, 10, 15]
    },
    'stress_test': {
        'max_users': 1000,
        'breaking_point_threshold': {
            'error_rate': 0.05,
            'response_time_p95': 5.0
        }
    }
}
```

## 📊 Test Reporting

### HTML Reports

Generated automatically for each test run:

```
tests/e2e/reports/
├── user_journeys_local.html
├── multi_channel_staging.html
├── performance_staging.html
└── summary.html
```

### JSON Reports

Machine-readable reports for CI/CD integration:

```json
{
  "test_suite": "AI Nutritionist E2E Tests",
  "environment": "staging",
  "overall_summary": {
    "total_tests": 25,
    "passed": 23,
    "failed": 2,
    "success_rate": 92.0
  },
  "recommendations": [
    "⚠️ Multi-channel tests have 88% success rate - needs attention"
  ]
}
```

## 🎭 Test Examples

### User Journey Test

```python
class RegistrationToFirstMealPlanJourney(WebE2ETest):
    async def execute(self) -> TestResult:
        # Navigate to landing page
        self.driver.get(self.environment.web_app_url)

        # Fill registration form
        user = self.create_test_user()
        await self._fill_registration_form(user)

        # Complete onboarding
        await self._complete_onboarding(user)

        # Verify meal plan generation
        meal_plan = await self._verify_first_meal_plan()

        return TestResult(
            test_name="RegistrationToFirstMealPlan",
            status="passed",
            duration=self._get_duration(),
            metrics={'meal_plan_generation_time': 3.0}
        )
```

### Multi-Channel Test

```python
class WhatsAppConversationFlow(MessagingE2ETest):
    async def execute(self) -> TestResult:
        user = self.create_test_user()

        # Test conversation scenarios
        await self._test_onboarding_flow(user)
        await self._test_meal_logging_flow(user)
        await self._test_recipe_request_flow(user)

        return TestResult(
            test_name="WhatsAppConversationFlow",
            status="passed",
            metrics={'average_response_time': 2.5}
        )
```

### Performance Test

```python
class LoadTestingScenarios(PerformanceE2ETest):
    async def execute(self) -> TestResult:
        # Execute different load scenarios
        baseline = await self._execute_baseline_load_test()
        normal = await self._execute_normal_load_test()
        peak = await self._execute_peak_load_test()

        return TestResult(
            test_name="LoadTestingScenarios",
            status="passed",
            metrics={
                'peak_throughput': peak.throughput,
                'max_error_rate': max(s.error_rate for s in [baseline, normal, peak])
            }
        )
```

## 🔍 Debugging Tests

### Running in Debug Mode

```bash
# Run with visible browser (no headless)
python run_e2e_tests.py user-journeys --no-headless

# Run single test with verbose output
pytest tests/e2e/user_journeys/test_critical_flows.py::RegistrationToFirstMealPlanJourney -v -s
```

### Screenshots and Logs

- Screenshots automatically captured on failures
- Detailed logs in `tests/e2e/logs/`
- Browser console logs captured
- Network request/response logs

### Environment Health Check

```bash
# Check if environment is ready for testing
python run_e2e_tests.py health-check --environment local
```

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [staging]
        browser: [chrome, firefox]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          python run_e2e_tests.py setup

      - name: Run E2E tests
        run: python run_e2e_tests.py all --environment ${{ matrix.environment }}
        env:
          E2E_BROWSER: ${{ matrix.browser }}
          E2E_HEADLESS: "true"

      - name: Upload test reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-reports-${{ matrix.environment }}-${{ matrix.browser }}
          path: tests/e2e/reports/
```

## 📈 Performance Benchmarks

### Expected Performance Metrics

| Metric                  | Baseline | Good    | Excellent |
| ----------------------- | -------- | ------- | --------- |
| API Response Time (P95) | < 2s     | < 1s    | < 500ms   |
| Web Page Load (P95)     | < 5s     | < 3s    | < 2s      |
| Throughput              | 50 RPS   | 100 RPS | 200+ RPS  |
| Error Rate              | < 5%     | < 1%    | < 0.1%    |
| Concurrent Users        | 100      | 500     | 1000+     |

### Load Test Scenarios

1. **Baseline Load** (10 users, 5 minutes)
2. **Normal Load** (100 users, 15 minutes)
3. **Peak Load** (500 users, 10 minutes)
4. **Stress Load** (Progressive to 1000+ users)

## 🛡️ Best Practices

### Test Design

1. **Independent Tests**: Each test should be self-contained
2. **Test Data Isolation**: Use unique test data for each run
3. **Cleanup**: Always clean up test data after execution
4. **Idempotent**: Tests should produce same results on repeated runs

### Performance Testing

1. **Gradual Load Increase**: Ramp up users gradually
2. **Monitor System Resources**: Track CPU, memory, database
3. **Realistic Scenarios**: Mirror actual user behavior
4. **Baseline Establishment**: Always compare against known baselines

### Debugging

1. **Screenshots on Failure**: Capture state when tests fail
2. **Detailed Logging**: Log all significant actions and responses
3. **Environment Consistency**: Use consistent test environments
4. **Data Validation**: Verify database state changes

## 🔮 Advanced Features

### Cross-Browser Testing

Automatically test across multiple browsers:

```bash
python run_e2e_tests.py cross-browser --environment staging
```

### Mobile Testing

Test responsive design on mobile devices:

```python
# Mobile device configurations available
MOBILE_CONFIGS = {
    'iPhone_12': {'width': 390, 'height': 844},
    'iPad_Pro': {'width': 1024, 'height': 1366},
    'Samsung_Galaxy': {'width': 360, 'height': 800}
}
```

### Database Verification

Verify database state changes:

```python
# Verify data in database
await database_verification.verify_user_created(user_id)
await database_verification.verify_meal_logged(user_id, meal_data)
await database_verification.verify_subscription_updated(user_id, "premium")
```

### Message Simulation

Simulate messaging across channels:

```python
# Simulate WhatsApp message
await message_simulation.simulate_whatsapp_message(
    from_number="+1234567890",
    message="I want to track my breakfast"
)

# Wait for bot response
response = await message_simulation.wait_for_outbound_message()
```

## 🆘 Troubleshooting

### Common Issues

1. **WebDriver Issues**

   ```bash
   # Reinstall webdrivers
   python run_e2e_tests.py setup
   ```

2. **Environment Not Ready**

   ```bash
   # Check environment health
   python run_e2e_tests.py health-check
   ```

3. **Test Data Conflicts**

   ```bash
   # Clean test database
   pytest tests/e2e/ --cleanup-data
   ```

4. **Performance Test Timeouts**
   - Increase timeout values in config
   - Check system resources
   - Verify network connectivity

### Getting Help

1. Check test logs in `tests/e2e/logs/`
2. Review screenshots in `tests/e2e/screenshots/`
3. Run health check: `python run_e2e_tests.py health-check`
4. Check environment configuration in `tests/e2e/config.py`

## 📞 Support

For issues with the E2E test suite:

1. **Documentation**: Check this README and inline code documentation
2. **Logs**: Review detailed logs in the output directory
3. **Health Check**: Run environment health checks
4. **Configuration**: Verify environment and browser configurations

---

**Happy Testing! 🎉**

The E2E test suite ensures the AI Nutritionist application works flawlessly across all user journeys, communication channels, and performance scenarios.
