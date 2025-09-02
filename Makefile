# AI Nutritionist Assistant - Makefile
# Simplifies common development tasks

.PHONY: help install test format lint build local docs clean deploy security

# Default target
help:
	@echo "🥗 AI Nutritionist Assistant - Available Commands"
	@echo "================================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install dependencies and setup environment"
	@echo "  make setup       Run complete development setup"
	@echo ""
	@echo "Development:"
	@echo "  make test        Run all tests"
	@echo "  make test-unit   Run unit tests only"
	@echo "  make test-cov    Run tests with coverage report"
	@echo "  make format      Format code with Black and isort"
	@echo "  make lint        Run all linting checks"
	@echo "  make security    Run security scans"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build       Build SAM application"
	@echo "  make local       Start local API server"
	@echo "  make deploy-dev  Deploy to development environment"
	@echo "  make deploy-prod Deploy to production environment"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        Serve documentation locally"
	@echo "  make docs-build  Build documentation"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       Clean up build artifacts"
	@echo "  make docker      Build and run with Docker"
	@echo "  make performance Run performance tests"

# Installation and setup
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

setup:
	@echo "🚀 Running development setup..."
	chmod +x setup-dev.sh
	./setup-dev.sh

# Testing
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/ -v -m "not integration"

test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-watch:
	@echo "👀 Running tests in watch mode..."
	pytest-watch tests/ -- -v

# Code quality
format:
	@echo "🎨 Formatting code..."
	black src/ tests/
	isort src/ tests/

lint:
	@echo "🔍 Running linting checks..."
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports
	black --check src/ tests/
	isort --check-only src/ tests/

security:
	@echo "🔒 Running security scans..."
	bandit -r src/ -f json -o bandit-report.json
	safety check --json --output safety-report.json

# Build and deployment
build:
	@echo "🏗️ Building SAM application..."
	sam build

local:
	@echo "🏃 Starting local API server..."
	sam local start-api --port 3000

deploy-dev:
	@echo "🚀 Deploying to development..."
	sam deploy --config-env dev --no-confirm-changeset

deploy-prod:
	@echo "🚀 Deploying to production..."
	sam deploy --config-env prod --no-confirm-changeset

# Documentation
docs:
	@echo "📚 Serving documentation..."
	mkdocs serve

docs-build:
	@echo "📚 Building documentation..."
	mkdocs build

# Docker
docker:
	@echo "🐳 Building and running with Docker..."
	docker-compose up --build

docker-test:
	@echo "🐳 Running tests in Docker..."
	docker-compose run --rm ai-nutritionist-dev pytest tests/ -v

# Performance testing
performance:
	@echo "⚡ Running performance tests..."
	locust -f performance/locustfile.py --host=http://localhost:3000

# Utilities
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .aws-sam/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf site/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete

# Git hooks
pre-commit:
	@echo "🪝 Running pre-commit hooks..."
	pre-commit run --all-files

# Environment management
env-create:
	@echo "🐍 Creating virtual environment..."
	python -m venv .venv

env-activate:
	@echo "🐍 Activating virtual environment..."
	@echo "Run: source .venv/bin/activate"

# AWS operations
aws-config:
	@echo "☁️ Configuring AWS..."
	aws configure

sam-init:
	@echo "🏗️ Initializing SAM application..."
	sam init

# Database operations
db-local:
	@echo "💾 Starting local DynamoDB..."
	docker run -p 8001:8000 amazon/dynamodb-local

# Monitoring
logs:
	@echo "📋 Tailing CloudWatch logs..."
	sam logs -n MessageHandlerFunction --stack-name ai-nutritionist-prod --tail

# Quick development commands
dev: install format lint test
	@echo "✅ Development checks complete!"

ci: lint test security
	@echo "✅ CI checks complete!"

# Version management
version:
	@echo "📋 Current version information:"
	@grep version pyproject.toml
	@python --version
	@sam --version
