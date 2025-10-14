# AI Nutritionist Development Tools

Comprehensive development tooling ecosystem for the AI Nutritionist project. This toolkit provides everything needed for efficient development, testing, debugging, and documentation generation.

## 🚀 Quick Start

```bash
# Make CLI executable
chmod +x dev-tools/dev-cli.py

# Setup development environment
python dev-tools/dev-cli.py setup

# Generate a new service
python dev-tools/dev-cli.py generate service --name UserService --domain business

# Seed database with sample data
python dev-tools/dev-cli.py db seed

# Run all tests
python dev-tools/dev-cli.py test all

# Generate documentation
python dev-tools/dev-cli.py docs all
```

## 📁 Tool Organization

```
dev-tools/
├── dev-cli.py                 # Master CLI interface
├── generators/                # Code generation tools
│   ├── __init__.py
│   ├── service_generator.py   # Service layer generation
│   ├── entity_generator.py    # Domain entity generation
│   ├── repository_generator.py # Repository pattern generation
│   ├── test_generator.py      # Test code generation
│   ├── enhanced_generators.py # Specialized generators
│   ├── migration_generator.py # Database/API migrations
│   └── api_generator.py       # FastAPI endpoint generation
├── scripts/                   # Development automation
│   ├── setup_environment.py   # Environment setup
│   └── seed_database.py       # Database seeding
├── debugging/                 # Debugging utilities
│   └── request_replay.py      # HTTP request replay
├── docs/                      # Documentation generation
│   └── api_docs_generator.py  # API documentation
└── templates/                 # Code templates
    └── (various template files)
```

## 🛠️ Available Commands

### Environment Setup

```bash
# Setup complete development environment
python dev-tools/dev-cli.py setup
```

**What it does:**

- Checks system prerequisites
- Creates Python virtual environment
- Installs dependencies
- Sets up configuration files
- Configures database connections
- Sets up IDE configurations

### Code Generation

#### Service Generation

```bash
# Basic service
python dev-tools/dev-cli.py generate service --name UserService

# Service with caching and events
python dev-tools/dev-cli.py generate service --name NotificationService --with-cache --with-events

# Domain-specific service
python dev-tools/dev-cli.py generate service --name PaymentService --domain billing
```

**Generates:**

- Service class with business logic
- Repository interface and implementation
- Data transfer objects (DTOs)
- Unit and integration tests
- FastAPI route handlers
- OpenAPI documentation

#### Entity Generation

```bash
# Basic entity
python dev-tools/dev-cli.py generate entity --name Recipe

# Entity with custom fields
python dev-tools/dev-cli.py generate entity --name User --fields '{"email": "str", "age": "int", "preferences": "List[str]"}'
```

**Generates:**

- Pydantic model classes
- Database schema definitions
- Validation logic
- Serialization methods

#### Repository Generation

```bash
# Basic repository
python dev-tools/dev-cli.py generate repository --name UserRepository --entity User
```

**Generates:**

- Repository interface
- DynamoDB implementation
- CRUD operations
- Query methods
- Connection management

#### API Generation

```bash
# Basic API endpoints
python dev-tools/dev-cli.py generate api --name Recipe --path /recipes

# API with specific methods
python dev-tools/dev-cli.py generate api --name User --path /users --methods GET POST PUT DELETE

# Public API (no authentication)
python dev-tools/dev-cli.py generate api --name Health --path /health --no-auth
```

**Generates:**

- FastAPI route handlers
- Request/response models
- Authentication middleware
- Input validation
- Error handling
- OpenAPI documentation

#### Test Generation

```bash
# Unit tests
python dev-tools/dev-cli.py generate test --name UserService --type unit

# Integration tests
python dev-tools/dev-cli.py generate test --name UserAPI --type integration

# Performance tests
python dev-tools/dev-cli.py generate test --name UserLoad --type performance
```

**Generates:**

- Test classes with fixtures
- Mock implementations
- Test data factories
- Performance benchmarks

#### Migration Generation

```bash
# Database schema migration
python dev-tools/dev-cli.py generate migration --name AddUserPreferences --type schema

# Data migration
python dev-tools/dev-cli.py generate migration --name MigrateOldUsers --type data

# API migration
python dev-tools/dev-cli.py generate migration --name UpdateUserEndpoints --type api
```

**Generates:**

- Migration scripts
- Rollback procedures
- Validation checks
- Version management

### Database Operations

#### Database Seeding

```bash
# Seed development database
python dev-tools/dev-cli.py db seed --environment development

# Seed with file output
python dev-tools/dev-cli.py db seed --save-files
```

**Creates:**

- Sample users with realistic data
- Recipe database with nutritional info
- Meal plans and preferences
- Analytics and usage data
- Relationship data

#### Migration Management

```bash
# Run pending migrations
python dev-tools/dev-cli.py db migrate

# Reset database to clean state
python dev-tools/dev-cli.py db reset
```

### Testing Suite

#### Unit Tests

```bash
# Run all unit tests
python dev-tools/dev-cli.py test unit

# Run specific pattern
python dev-tools/dev-cli.py test unit --pattern "test_user"

# Run in parallel
python dev-tools/dev-cli.py test unit --parallel
```

#### Integration Tests

```bash
# Run integration tests
python dev-tools/dev-cli.py test integration
```

#### Performance Tests

```bash
# Run performance tests
python dev-tools/dev-cli.py test performance
```

#### Coverage Analysis

```bash
# Generate coverage report
python dev-tools/dev-cli.py test coverage
```

#### Complete Test Suite

```bash
# Run all test types with coverage
python dev-tools/dev-cli.py test all
```

### Debugging Tools

#### Request Replay

```bash
# Capture HTTP requests
python dev-tools/dev-cli.py debug replay capture --url http://localhost:8000/api/recipes

# Replay captured request
python dev-tools/dev-cli.py debug replay replay --request-id abc123

# Performance testing
python dev-tools/dev-cli.py debug replay performance --request-id abc123 --iterations 100

# List captured requests
python dev-tools/dev-cli.py debug replay list

# Compare requests
python dev-tools/dev-cli.py debug replay compare

# Generate analysis report
python dev-tools/dev-cli.py debug replay report
```

**Features:**

- HTTP request/response capture
- Automatic replay with validation
- Performance benchmarking
- Response comparison
- Detailed analysis reports

### Documentation Generation

#### API Documentation

```bash
# Generate all API documentation
python dev-tools/dev-cli.py docs api

# Generate specific format
python dev-tools/dev-cli.py docs api --format openapi
python dev-tools/dev-cli.py docs api --format markdown
python dev-tools/dev-cli.py docs api --format postman

# Custom output directory
python dev-tools/dev-cli.py docs api --output-dir ./api-docs
```

**Generates:**

- OpenAPI 3.0 specifications
- Interactive API documentation
- Markdown documentation
- Client code examples
- Postman collections

#### Architecture Documentation

```bash
# Generate architecture diagrams
python dev-tools/dev-cli.py docs architecture
```

#### Test Coverage Reports

```bash
# Generate coverage documentation
python dev-tools/dev-cli.py docs coverage
```

#### Complete Documentation

```bash
# Generate all documentation
python dev-tools/dev-cli.py docs all
```

### Performance Analysis

#### Load Testing

```bash
# Run load tests
python dev-tools/dev-cli.py perf load
```

#### Stress Testing

```bash
# Run stress tests
python dev-tools/dev-cli.py perf stress
```

#### Benchmarking

```bash
# Run benchmarks
python dev-tools/dev-cli.py perf benchmark
```

### Project Validation

```bash
# Validate project structure and configuration
python dev-tools/dev-cli.py validate
```

## 🧩 Individual Tool Usage

### Direct Tool Execution

You can also run tools directly without the CLI:

```bash
# Service generator
python dev-tools/generators/service_generator.py --name UserService --domain business

# Environment setup
python dev-tools/scripts/setup_environment.py

# Database seeding
python dev-tools/scripts/seed_database.py --environment development

# Request replay
python dev-tools/debugging/request_replay.py capture --url http://localhost:8000/api/users

# API documentation
python dev-tools/docs/api_docs_generator.py --format all
```

## 🎯 Common Workflows

### New Feature Development

```bash
# 1. Generate service layer
python dev-tools/dev-cli.py generate service --name FeatureService

# 2. Generate API endpoints
python dev-tools/dev-cli.py generate api --name Feature --path /features

# 3. Generate tests
python dev-tools/dev-cli.py generate test --name FeatureService --type unit
python dev-tools/dev-cli.py generate test --name FeatureAPI --type integration

# 4. Run tests
python dev-tools/dev-cli.py test all

# 5. Update documentation
python dev-tools/dev-cli.py docs api
```

### Bug Investigation

```bash
# 1. Capture problematic requests
python dev-tools/dev-cli.py debug replay capture --url http://localhost:8000/api/problematic-endpoint

# 2. Replay and analyze
python dev-tools/dev-cli.py debug replay replay --request-id captured-id

# 3. Generate debugging report
python dev-tools/dev-cli.py debug replay report
```

### Release Preparation

```bash
# 1. Run complete test suite
python dev-tools/dev-cli.py test all

# 2. Generate all documentation
python dev-tools/dev-cli.py docs all

# 3. Run performance tests
python dev-tools/dev-cli.py perf load

# 4. Validate project
python dev-tools/dev-cli.py validate
```

## 🔧 Configuration

### Environment Variables

```bash
# Database configuration
DATABASE_URL=your_database_url
DATABASE_NAME=ai_nutritionist

# API configuration
API_BASE_URL=http://localhost:8000
API_VERSION=v1

# AWS configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Development settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### Tool Configuration

Each tool supports configuration through:

- Command-line arguments
- Environment variables
- Configuration files
- Project settings

## 📊 Generated Artifacts

### Code Generation

- **Services**: Clean architecture service classes
- **Entities**: Pydantic models with validation
- **Repositories**: Database access layer
- **APIs**: FastAPI endpoints with authentication
- **Tests**: Comprehensive test suites

### Documentation

- **API Docs**: OpenAPI specs, Markdown, Postman collections
- **Architecture**: System diagrams and documentation
- **Coverage**: Test coverage reports and analysis

### Development Data

- **Sample Data**: Realistic test data for development
- **Fixtures**: Reusable test fixtures
- **Mock Data**: Development environment data

## 🚨 Troubleshooting

### Common Issues

#### Permission Errors

```bash
# Make scripts executable (Unix/Mac)
chmod +x dev-tools/dev-cli.py

# Windows: Run as administrator if needed
```

#### Python Environment Issues

```bash
# Recreate virtual environment
python dev-tools/dev-cli.py setup
```

#### Database Connection Issues

```bash
# Check environment variables
echo $DATABASE_URL

# Reset database
python dev-tools/dev-cli.py db reset
```

#### Import Errors

```bash
# Reinstall dependencies
python dev-tools/dev-cli.py setup
```

### Debug Mode

Run any command with Python debug mode:

```bash
python -u dev-tools/dev-cli.py [command] [args]
```

### Getting Help

```bash
# General help
python dev-tools/dev-cli.py --help

# Command-specific help
python dev-tools/dev-cli.py generate --help
python dev-tools/dev-cli.py test --help
python dev-tools/dev-cli.py debug --help
```

## 🔄 Tool Updates

The development tools are designed to be:

- **Self-documenting**: Generated code includes comments and documentation
- **Extensible**: Easy to add new generators and tools
- **Maintainable**: Clear separation of concerns
- **Testable**: Tools themselves are tested

### Adding New Tools

1. Create tool in appropriate directory (`generators/`, `scripts/`, `debugging/`, `docs/`)
2. Add command to `dev-cli.py`
3. Update this documentation
4. Add tests for the new tool

## 🎉 Benefits

### Developer Experience

- **Consistent Code**: All generated code follows project patterns
- **Reduced Boilerplate**: Automatic generation of repetitive code
- **Fast Development**: Quick scaffolding of new features
- **Quality Assurance**: Built-in testing and validation

### Project Maintenance

- **Documentation**: Always up-to-date API documentation
- **Testing**: Comprehensive test coverage
- **Debugging**: Powerful debugging and analysis tools
- **Performance**: Built-in performance monitoring

### Team Productivity

- **Standardization**: Consistent development practices
- **Onboarding**: Easy environment setup for new developers
- **Automation**: Reduced manual tasks
- **Quality**: Higher code quality through tooling

---

_This development toolkit is designed to scale with your project and team. Each tool is independently useful but works together to create a comprehensive development experience._
