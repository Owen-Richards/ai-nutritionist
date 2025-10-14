# AGENTS.md - AI Agent & GitHub Copilot Guidelines

## 🎯 Repository Overview

**AI Nutritionist** - AWS serverless nutritional guidance system with SMS/WhatsApp interface, meal planning, and community features.

**Stack**: Python 3.11+, AWS Lambda, DynamoDB, Bedrock (AI), API Gateway, Amazon Pinpoint (messaging)

---

## 🏗️ Architecture Pattern

- **Clean Architecture** with dependency injection (see `packages/core/src/container/`)
- **AWS Serverless** - Lambda functions, API Gateway, DynamoDB, S3
- **Event-driven messaging** - Amazon Pinpoint for SMS/WhatsApp
- **AI-powered** - AWS Bedrock (Claude 3 Haiku, Titan models)
- **Monorepo structure** - Services, packages, infrastructure, tests

---

## 📁 Key Directory Boundaries

### **DO NOT CROSS THESE BOUNDARIES**

```
src/
├── core/              # Domain entities - STABLE PUBLIC API
├── services/          # Business logic - MAINTAIN SERVICE BOUNDARIES
│   ├── meal_planning/      # Meal plan generation
│   ├── infrastructure/     # Monitoring, caching, resilience
│   ├── business/           # Subscriptions, cost tracking
│   ├── community/          # User groups, challenges
│   ├── gamification/       # Points, achievements
│   ├── analytics/          # Usage tracking
│   └── messaging/          # Multi-channel messaging
├── adapters/          # AWS integrations - PRESERVE INTERFACES
├── api/               # FastAPI HTTP layer
├── handlers/          # Lambda function handlers
├── models/            # Pydantic data models
└── config/            # Settings and environment

packages/              # Shared libraries - PUBLIC APIs
├── core/              # Events bus, DI container
└── shared/            # Error handling, utilities

infrastructure/        # Terraform IaC - REQUIRES VALIDATION
tests/                 # Test suite - NEVER REDUCE COVERAGE
```

---

## ✅ Coding Conventions

### Python Style

- **Type hints required** for all public functions and methods
- **Pydantic models** for data validation and serialization
- **Async/await** for I/O operations (DynamoDB, Bedrock, Pinpoint)
- **Repository pattern** for data access
- **Dependency injection** via constructor parameters

### Naming

- Classes: `PascalCase` (e.g., `MealPlanningService`)
- Functions/methods: `snake_case` (e.g., `generate_meal_plan`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_ATTEMPTS`)
- Private: prefix with `_` (e.g., `_internal_helper`)

### Error Handling

```python
from src.utils.error_handling import handle_errors, retry_on_failure

@handle_errors(error_type="meal_planning")
@retry_on_failure(max_attempts=3)
async def generate_meal_plan(...):
    ...
```

### Logging

```python
from src.services.infrastructure.observability import get_logger

logger = get_logger(__name__)
logger.info("Operation started", extra={"user_id": user_id})
```

---

## 🧪 Testing Requirements

### Minimum Standards

- **Unit tests required** for new features
- **Integration tests** for AWS services (use `moto` for mocking)
- **80% coverage minimum** - do not reduce coverage
- **All tests must pass** before commit

### Test Structure

```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # AWS integration tests (mocked)
├── fixtures/       # Shared test fixtures
└── conftest.py     # pytest configuration
```

### Example

```python
import pytest
from moto import mock_dynamodb

@pytest.fixture
def mock_dynamodb_table():
    with mock_dynamodb():
        # Setup
        yield table
        # Teardown

async def test_meal_plan_creation(mock_dynamodb_table):
    service = MealPlanningService(repository)
    result = await service.generate_plan(...)
    assert result.status == "success"
```

---

## 🚫 DO NOT

1. **Break Public APIs**

   - Do not modify function signatures in `src/core/`
   - Do not change data models without deprecation path
   - Maintain backward compatibility for services

2. **Violate Service Boundaries**

   - Do not create circular dependencies
   - Use dependency injection, not direct imports
   - Keep services loosely coupled

3. **Skip Tests**

   - Do not commit without tests
   - Do not reduce test coverage
   - Do not ignore failing tests

4. **Modify Infrastructure Without Validation**

   - Always run `terraform fmt`, `terraform validate`
   - Test infrastructure changes in dev environment first
   - Do not change production settings without approval

5. **Add Dependencies Without Approval**

   - Check if functionality exists in codebase first
   - Use standard library when possible
   - Update `requirements.txt` and document purpose

6. **Delete Compliance/Security Code**

   - Privacy compliance: `src/services/infrastructure/privacy_compliance.py`
   - Security controls: `src/api/middleware/`
   - Audit logging: `src/services/infrastructure/observability.py`

7. **Hard-code Secrets**
   - Use AWS Secrets Manager: `src/services/infrastructure/secrets_manager.py`
   - Never commit API keys, credentials, or tokens
   - Use environment variables for configuration

---

## ✨ Common Tasks

### Add a New Feature

1. Start in appropriate service module (`src/services/*/`)
2. Define data models in `src/models/`
3. Add repository/adapter if data access needed
4. Write unit tests first (TDD)
5. Add integration tests for AWS services
6. Update API routes if HTTP endpoint needed
7. Document in docstrings and comments

### Fix a Bug

1. **Add regression test first** (captures the bug)
2. Fix the issue
3. Verify test passes
4. Check for similar issues elsewhere
5. Update documentation if behavior changes

### Optimize Performance

1. **Profile first** - don't guess
2. Maintain existing tests
3. Add performance benchmarks
4. Document optimization in comments
5. Consider caching strategy (`src/services/infrastructure/caching.py`)

### Add AWS Integration

1. Use adapter pattern in `src/adapters/`
2. Define interface/protocol first
3. Mock in tests using `moto`
4. Add error handling and retries
5. Log operations for observability
6. Update Terraform if infrastructure needed

---

## 🎯 Service Responsibilities

| Service            | Purpose                         | Entry Point                           |
| ------------------ | ------------------------------- | ------------------------------------- |
| **meal_planning**  | AI meal plan generation         | `plan_coordinator.py`                 |
| **infrastructure** | Monitoring, caching, resilience | `monitoring.py`, `caching.py`         |
| **business**       | Subscriptions, cost tracking    | `subscription.py`, `cost_tracking.py` |
| **community**      | User groups, challenges         | `service.py`                          |
| **gamification**   | Points, achievements            | `service.py`                          |
| **analytics**      | Usage tracking, insights        | `analytics_service.py`                |
| **messaging**      | SMS/WhatsApp communication      | `adapters/messaging_adapters.py`      |

---

## 🔒 Security Considerations

- **Input validation**: Pydantic models for all inputs
- **Authentication**: AWS Cognito integration (API Gateway)
- **Authorization**: IAM roles and policies
- **Data encryption**: KMS encryption at rest
- **Rate limiting**: API Gateway throttling + app-level limits
- **Audit logging**: CloudTrail + application logs
- **GDPR compliance**: `privacy_compliance.py` service

---

## 🚀 Deployment

### Local Development

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
pytest tests/ -v
```

### AWS Deployment

```bash
cd infrastructure/terraform
terraform init
terraform plan -var-file="dev.tfvars"
terraform apply
```

### CI/CD

- **GitHub Actions** workflows in `.github/workflows/`
- **Automated tests** on PR
- **Terraform validation** on infrastructure changes
- **Coverage reporting** enforced

---

## 📚 Documentation

- **Architecture**: `docs/architecture/`
- **API reference**: `docs/API_GUIDANCE.md`
- **Deployment**: `docs/GLOBAL_DEPLOYMENT_GUIDE.md`
- **Monitoring**: `docs/MONITORING_USAGE_GUIDE.md`
- **Quick reference**: `.codex/quick_reference.md`

---

## 🆘 Getting Help

- Check existing patterns in codebase first
- Review tests for usage examples
- Read docstrings and type hints
- Consult `docs/` directory
- Ask in team chat before making architectural changes

---

**Remember**: This is production-grade code. Maintain quality, test coverage, and documentation standards. When in doubt, ask before making breaking changes.
