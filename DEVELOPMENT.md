# AI Nutritionist Development Guide

## Prerequisites

Before you begin development, ensure you have:

- **Python 3.11+** installed 
- **AWS CLI** configured with appropriate credentials
- **Git** for version control
- **Docker** (optional, for local testing)
- **VS Code** with Python extension (recommended)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ai-nutritionalist
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# API Keys (get from respective services)
EDAMAM_APP_ID=your_edamam_app_id
EDAMAM_APP_KEY=your_edamam_app_key
OPENAI_API_KEY=your_openai_api_key

# Database
DYNAMODB_TABLE_PREFIX=ai-nutritionist-dev

# Messaging
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_ACCESS_TOKEN=your_access_token
```

### 4. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_project_validation.py -v
python -m pytest tests/test_ai_service.py -v
```

## Project Architecture

```
src/
├── handlers/          # AWS Lambda handlers & webhook endpoints
├── services/          # Core business logic services
├── models/           # Data models and schemas  
├── utils/            # Utility functions and helpers
├── prompts/          # AI prompts and templates
└── config/           # Configuration and settings

tests/
├── unit/             # Unit tests for individual components
├── integration/      # Integration tests with external services
└── fixtures/         # Test data and mocks
```

### Key Services

- **ConsolidatedMessagingService**: Unified messaging across WhatsApp/SMS/AWS
- **AIService**: AI-powered meal planning and nutrition advice
- **EdamamService**: Nutrition data and recipe integration
- **UserService**: User management and preferences
- **SubscriptionService**: Billing and premium features

## Testing Strategy

### Unit Tests
- Test individual service methods
- Mock external dependencies
- Focus on business logic validation

### Integration Tests  
- Test service interactions
- Validate API integrations
- End-to-end workflow testing

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html

# Specific test file
python -m pytest tests/test_ai_service.py -v

# Run tests matching pattern
python -m pytest tests/ -k "test_messaging" -v
```

## Development Workflow

### 1. Feature Development
1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD approach)
3. Implement feature code
4. Run tests: `python -m pytest tests/ -v`
5. Format code: `python -m black src/ tests/`
6. Commit and push changes

### 2. Code Quality
- **Black**: Code formatting
- **pytest**: Testing framework
- **Type hints**: Use throughout codebase
- **Docstrings**: Document all public methods

### 3. Service Development Guidelines
- Keep services focused and single-purpose
- Use dependency injection for external services
- Implement proper error handling and logging
- Add comprehensive test coverage

## Debugging Guide

### Common Issues

**AWS Region Errors**
```bash
# Set AWS region explicitly
export AWS_DEFAULT_REGION=us-east-1
export AWS_REGION=us-east-1
```

**Import Errors**
```bash
# Ensure you're in the project root and virtual environment is activated
python -c "import sys; print(sys.path)"
```

**Test Failures**
```bash
# Run with verbose output and stop on first failure
python -m pytest tests/ -v -x

# Debug specific test
python -m pytest tests/test_ai_service.py::TestAIService::test_init -v -s
```

### Debugging Services
- Use `logging` module for debug output
- Mock external dependencies in tests
- Use `breakpoint()` for interactive debugging
- Check AWS CloudWatch logs for Lambda issues

## Performance Monitoring

### Local Development
- Use `pytest-benchmark` for performance testing
- Monitor memory usage with `memory_profiler`
- Profile code with `cProfile`

### Production Monitoring
- AWS CloudWatch metrics and logs
- Custom metrics in DynamoDB
- Error tracking and alerting

## Deployment

See `DEPLOYMENT.md` for complete deployment instructions.

### Local Testing
```bash
# Install SAM CLI
pip install aws-sam-cli

# Build application
sam build

# Test locally
sam local start-api
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Write tests for your changes**
4. **Ensure all tests pass**
5. **Submit a pull request**

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Keep functions focused and small
- Document complex logic

### Commit Messages
- Use descriptive commit messages
- Reference issue numbers when applicable
- Follow conventional commit format

## Resources

### Documentation
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [pytest Documentation](https://docs.pytest.org/)

### APIs
- [Edamam Nutrition API](https://developer.edamam.com/edamam-docs-nutrition-api)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [OpenAI API](https://platform.openai.com/docs)

## Best Practices

1. **Always write tests first** (TDD)
2. **Keep services stateless** for scalability
3. **Use environment variables** for configuration
4. **Implement proper error handling** with meaningful messages
5. **Log important events** for debugging and monitoring
6. **Use type hints** for better code documentation
7. **Keep functions small** and focused on single responsibilities
8. **Mock external dependencies** in tests
9. **Use semantic versioning** for releases
10. **Document public APIs** with comprehensive docstrings

---

Happy coding! ��� If you have questions, check the documentation or reach out to the development team.
