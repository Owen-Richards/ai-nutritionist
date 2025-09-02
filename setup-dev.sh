#!/bin/bash

# AI Nutritionist Assistant - Development Setup Script
# This script sets up the complete development environment

set -e  # Exit on any error

echo "🥗 AI Nutritionist Assistant - Development Setup"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.11+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found"
        exit 1
    fi
    
    # Check AWS CLI
    if command_exists aws; then
        print_success "AWS CLI found"
    else
        print_warning "AWS CLI not found. Installing..."
        pip install awscli
    fi
    
    # Check Docker
    if command_exists docker; then
        print_success "Docker found"
    else
        print_warning "Docker not found. Please install Docker for local testing."
    fi
    
    # Check Git
    if command_exists git; then
        print_success "Git found"
    else
        print_error "Git not found. Please install Git."
        exit 1
    fi
}

# Create virtual environment
setup_virtual_environment() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    print_success "Virtual environment activated"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    print_success "Pip upgraded"
}

# Install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Install main dependencies
    pip install -r requirements.txt
    print_success "Main dependencies installed"
    
    # Install development dependencies
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed"
    fi
    
    # Install pre-commit hooks
    if command_exists pre-commit; then
        pre-commit install
        print_success "Pre-commit hooks installed"
    fi
}

# Setup AWS configuration
setup_aws_config() {
    print_status "Checking AWS configuration..."
    
    if aws sts get-caller-identity >/dev/null 2>&1; then
        print_success "AWS credentials configured"
    else
        print_warning "AWS credentials not configured"
        echo "Please run: aws configure"
        echo "Or set environment variables:"
        echo "  export AWS_ACCESS_KEY_ID=your-access-key"
        echo "  export AWS_SECRET_ACCESS_KEY=your-secret-key"
        echo "  export AWS_DEFAULT_REGION=us-east-1"
    fi
}

# Install SAM CLI
install_sam_cli() {
    print_status "Checking AWS SAM CLI..."
    
    if command_exists sam; then
        print_success "AWS SAM CLI found"
    else
        print_status "Installing AWS SAM CLI..."
        pip install aws-sam-cli
        print_success "AWS SAM CLI installed"
    fi
}

# Create local configuration files
create_config_files() {
    print_status "Creating configuration files..."
    
    # Create local environment file
    if [ ! -f ".env.local" ]; then
        cat > .env.local << EOF
# Local development environment variables
# Copy this file and rename to .env.local
# Add your actual values (this file is gitignored)

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=your_phone_number_here

# AWS Configuration
AWS_REGION=us-east-1

# Development Settings
DEBUG=true
LOG_LEVEL=DEBUG
EOF
        print_success "Created .env.local template"
        print_warning "Please edit .env.local with your actual configuration"
    else
        print_warning ".env.local already exists"
    fi
    
    # Create VS Code settings if not exists
    if [ ! -d ".vscode" ]; then
        mkdir -p .vscode
        
        cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        ".aws-sam": true
    }
}
EOF
        print_success "Created VS Code settings"
    fi
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    if command_exists pytest; then
        pytest tests/ -v --tb=short
        print_success "Tests completed"
    else
        print_warning "pytest not found, skipping tests"
    fi
}

# Setup complete message
setup_complete() {
    print_success "🎉 Development setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env.local with your Twilio and AWS credentials"
    echo "2. Run 'sam build' to build the application"
    echo "3. Run 'sam local start-api' for local testing"
    echo "4. Run 'pytest tests/' to run tests"
    echo "5. Run 'mkdocs serve' to view documentation"
    echo ""
    echo "Available make commands:"
    echo "  make install     - Install dependencies"
    echo "  make test        - Run tests"
    echo "  make format      - Format code"
    echo "  make lint        - Run linting"
    echo "  make build       - Build SAM application"
    echo "  make local       - Start local API"
    echo "  make docs        - Serve documentation"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    setup_virtual_environment
    install_dependencies
    setup_aws_config
    install_sam_cli
    create_config_files
    run_tests
    setup_complete
}

# Run main function
main "$@"
