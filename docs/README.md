# 🥗 AI Nutritionist Assistant - Complete Documentation

## 📖 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Development Guide](#development)
- [Deployment](#deployment)
- [Privacy & Security](#privacy--security)
- [Monetization](#monetization)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured
- Git installed

### Local Development Setup
```bash
# Clone and setup
git clone <repository-url>
cd ai-nutritionalist
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your credentials

# Run tests
pytest tests/ -v

# Start local development
sam build && sam local start-api
```

---

## 🏗️ Architecture

### System Overview
The AI Nutritionist Assistant is built on a serverless, event-driven architecture that prioritizes cost efficiency, scalability, and user experience.

### Core Design Principles
- **Progressive Personalization**: Start simple, learn gradually
- **Event-Driven Architecture**: Decoupled, scalable services
- **Cost-Conscious Design**: Usage tracking and intelligent caching

### Service Domains
```
src/services/
├── nutrition/           # Nutrition analysis, tracking, insights
├── personalization/     # User profiling, adaptive learning
├── meal_planning/       # Advanced meal planning with multi-goal
├── messaging/           # Multi-platform communication
├── business/            # Revenue, subscriptions, partnerships
└── infrastructure/      # Technical foundation, AI services
```

### Request Flow
```
WhatsApp/SMS → API Gateway → Lambda Handler → Service Layer → Business Logic → Response
```

---

## 📡 API Reference

### Base URL
```
https://your-api-gateway-url/
```

### Core Endpoints

#### Multi-Goal Management
- **POST** `/user/{user_id}/goals` - Add nutrition goal
- **GET** `/user/{user_id}/goals` - Get user goals
- **PUT** `/user/{user_id}/goals/{goal_id}` - Update goal priority
- **DELETE** `/user/{user_id}/goals/{goal_id}` - Remove goal

#### Meal Planning
- **POST** `/user/{user_id}/meal-plan` - Generate meal plan
- **GET** `/user/{user_id}/meal-plan/{plan_id}` - Get meal plan
- **POST** `/user/{user_id}/meal-plan/{plan_id}/feedback` - Rate meal plan

#### User Management
- **GET** `/user/{user_id}` - Get user profile
- **PUT** `/user/{user_id}` - Update user preferences
- **DELETE** `/user/{user_id}` - Delete user account (GDPR)

#### Messaging Webhooks
- **POST** `/webhook/whatsapp` - WhatsApp message webhook
- **POST** `/webhook/sms` - SMS message webhook

---

## 🛠️ Development Guide

### Project Structure
```
ai-nutritionalist/
├── src/                 # Source code
│   ├── handlers/        # Lambda entry points
│   ├── services/        # Business logic (domain-organized)
│   ├── models/          # Data models
│   ├── utils/           # Shared utilities
│   └── config/          # Configuration
├── tests/               # Test suite
├── infrastructure/      # AWS SAM templates
├── docs/                # Documentation
└── requirements.txt     # Dependencies
```

### Testing Strategy
```bash
# Unit tests (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Validation tests
pytest tests/test_project_validation.py -v

# With coverage
pytest tests/ --cov=src/ --cov-report=html
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

---

## 🚀 Deployment

### Production Deployment
```bash
# Build and deploy
sam build
sam deploy --guided

# Or use production script
./deploy-production.sh
```

### Environment Configuration
Set required environment variables in AWS Systems Manager Parameter Store:
- `/prod/edamam/app-id` - Edamam API credentials
- `/prod/twilio/account-sid` - Twilio credentials
- `/prod/stripe/secret-key` - Stripe payment processing

### Infrastructure Components
- **AWS Lambda**: Message processing and AI inference
- **API Gateway**: REST API endpoints and webhook handling
- **DynamoDB**: User profiles, meal plans, tracking data
- **AWS End User Messaging**: SMS and WhatsApp messaging
- **S3 + CloudFront**: Static asset hosting and CDN

---

## 🔒 Privacy & Security

### Data Protection
- **Encryption at Rest**: All user data encrypted in DynamoDB
- **Encryption in Transit**: TLS 1.3 for all communications
- **Access Controls**: IAM policies with least privilege
- **Data Retention**: Automatic deletion per GDPR requirements

### GDPR Compliance
- **Right to Access**: User data export functionality
- **Right to Deletion**: Complete account deletion
- **Data Minimization**: Collect only necessary data
- **Consent Management**: Explicit opt-in for data processing

### Security Measures
- **WAF Protection**: Web Application Firewall enabled
- **Rate Limiting**: Per-user and per-endpoint limits
- **Input Validation**: Strict validation on all inputs
- **Audit Logging**: All API calls logged via CloudTrail

---

## 💰 Monetization

### Business Model
- **Freemium Model**: Basic features free, premium features paid
- **Progressive Value Delivery**: Immediate value, upgrade for advanced features
- **Multiple Revenue Streams**: Subscriptions, affiliates, partnerships

### Revenue Streams
1. **Subscription Revenue** ($9.99/month premium tier)
2. **Affiliate Commissions** (grocery delivery integration)
3. **Partnership Revenue** (meal kit services, supplement brands)
4. **Premium Features** (advanced analytics, family plans)

### Cost Structure
- **AWS Infrastructure**: $0.10-0.50 per user per month
- **AI Processing**: $0.05-0.20 per conversation
- **Third-party APIs**: $0.02-0.10 per user per month
- **Target Margin**: 70%+ gross profit

---

## 🤝 Contributing

### Development Workflow
1. Fork and clone the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks
5. Submit pull request

### Code Standards
- **Formatter**: Black (line length: 100)
- **Linter**: Flake8
- **Type Checking**: MyPy
- **Testing**: pytest with 80%+ coverage

### Commit Convention
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Owen-Richards/ai-nutritionist/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Owen-Richards/ai-nutritionist/discussions)
- **Security**: security@ai-nutritionist.com

---

*Last Updated: September 11, 2025*
