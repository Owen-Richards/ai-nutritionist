# AI Nutritionist Assistant - Makefile
# Essential development commands

.PHONY: help install test format lint build local deploy clean

# Default target
help:
	@echo "🥗 AI Nutritionist Assistant - Available Commands"
	@echo "================================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install dependencies and setup environment"
	@echo "  make setup       Complete development setup"
	@echo ""
	@echo "Development:"
	@echo "  make test        Run all tests"
	@echo "  make format      Format code with Black and isort"
	@echo "  make lint        Run linting checks"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build       Build SAM application"
	@echo "  make local       Start local API server"
	@echo "  make deploy      Deploy to AWS"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       Clean build artifacts"

# Installation and setup
install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup: install
	pre-commit install
	@echo "✅ Development environment ready!"

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src/ --cov-report=html --cov-report=term

# Regression testing
test-regression-pre-commit:
	python -m tests.regression.cli pre-commit

test-regression-pr:
	python -m tests.regression.cli pull-request --max-duration 1800

test-regression-nightly:
	python -m tests.regression.cli nightly

test-regression-flaky:
	python -m tests.regression.cli flaky-detection --runs-per-test 10

test-regression-analyze:
	python -m tests.regression.cli analyze --top-flaky 10 --top-slow 10

test-regression-demo:
	python tests/regression/demo.py

# Install regression testing hooks
install-test-hooks:
	python -m tests.regression.cli install-hooks

# Setup CI integration
setup-ci:
	python -m tests.regression.cli setup-ci --provider github

# Code quality
format:
	black src/ tests/
	isort src/ tests/

lint:
	flake8 src/ tests/
	mypy src/
	bandit -r src/

# Build and deployment
build:
	sam build

local: build
	sam local start-api

deploy: build
	sam deploy

# Utilities
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .mypy_cache/

# Quick development workflow
dev: format lint test

# CI pipeline
ci: lint test
