# Contributing to AI Nutritionist Assistant

Thank you for your interest in contributing to the AI Nutritionist Assistant! This guide will help you get started.

## 🤝 Code of Conduct

This project adheres to the Contributor Covenant Code of Conduct. By participating, you are expected to uphold this code.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+ installed
- AWS CLI configured
- Git installed
- Docker (for local testing)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/Owen-Richards/ai-nutritionist.git
   cd ai-nutritionist
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## 🔧 Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Development branch for features
- `feature/*` - Individual feature branches
- `hotfix/*` - Critical fixes

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests locally**
   ```bash
   pytest tests/ -v
   ```

4. **Run code quality checks**
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 Coding Standards

### Python Code Style

- **Formatter**: Black (line length: 88)
- **Linter**: Flake8
- **Type Checking**: MyPy
- **Import Sorting**: isort

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Test additions/modifications
- `chore:` - Maintenance tasks

### Code Structure

```
src/
├── handlers/          # Lambda function handlers
├── services/          # Business logic services
├── models/           # Data models
├── utils/            # Utility functions
└── tests/            # Test files
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ai_service.py

# Run tests with specific markers
pytest -m "not slow"  # Skip slow tests
```

### Test Categories

- **Unit Tests**: Test individual functions/classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows

### Writing Tests

- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Test both success and failure scenarios

Example:
```python
def test_generate_meal_plan_with_dietary_restrictions():
    # Arrange
    user_preferences = {"diet": "vegan", "budget": 50}
    
    # Act
    meal_plan = ai_service.generate_meal_plan(user_preferences)
    
    # Assert
    assert meal_plan is not None
    assert all(meal.is_vegan for meal in meal_plan.meals)
```

## 📚 Documentation

### Code Documentation

- Use Google-style docstrings
- Document all public functions and classes
- Include type hints for all parameters and return values

Example:
```python
def generate_meal_plan(
    user_preferences: Dict[str, Any],
    budget: float
) -> MealPlan:
    """Generate a personalized meal plan.
    
    Args:
        user_preferences: Dictionary containing dietary preferences
        budget: Maximum budget for the meal plan
        
    Returns:
        A MealPlan object containing recommended meals
        
    Raises:
        ValueError: If budget is negative or preferences are invalid
    """
```

### README Updates

When adding new features:
- Update the features list
- Add usage examples
- Update installation instructions if needed

## 🚀 Deployment

### Local Testing

```bash
# Start local API
sam local start-api

# Test specific function
sam local invoke MessageHandlerFunction --event events/sample-event.json
```

### Staging Deployment

Pull requests to `develop` automatically deploy to staging environment.

### Production Deployment

Merges to `main` automatically deploy to production after all checks pass.

## 🐛 Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, AWS region
6. **Logs**: Relevant error messages or logs

## 💡 Feature Requests

For new features:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: Your suggested approach
3. **Alternatives**: Other solutions you've considered
4. **Additional Context**: Screenshots, mockups, examples

## 📞 Getting Help

- **Issues**: Create a GitHub issue for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check the docs/ folder for detailed guides

## 🏆 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Special thanks in documentation

Thank you for contributing to AI Nutritionist Assistant! 🎉
