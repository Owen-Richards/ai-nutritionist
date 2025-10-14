#!/bin/bash

# AI Nutritionist Infrastructure Deployment Script
# This script helps deploy the Terraform infrastructure across environments

set -e

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

# Function to display usage
usage() {
    echo "Usage: $0 [COMMAND] [ENVIRONMENT] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  init      Initialize Terraform for an environment"
    echo "  plan      Plan Terraform changes"
    echo "  apply     Apply Terraform changes"
    echo "  destroy   Destroy Terraform infrastructure"
    echo "  validate  Validate Terraform configuration"
    echo "  output    Show Terraform outputs"
    echo ""
    echo "Environments:"
    echo "  dev       Development environment"
    echo "  staging   Staging environment"
    echo "  prod      Production environment"
    echo "  dr        Disaster recovery environment"
    echo ""
    echo "Options:"
    echo "  --auto-approve    Auto-approve apply/destroy (use with caution)"
    echo "  --backend-config  Specify backend configuration file"
    echo "  --var-file       Specify variables file"
    echo ""
    echo "Examples:"
    echo "  $0 init dev"
    echo "  $0 plan prod --var-file=prod.tfvars"
    echo "  $0 apply dev --auto-approve"
    echo "  $0 destroy staging"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform >= 1.5"
        exit 1
    fi
    
    # Check Terraform version
    TF_VERSION=$(terraform version -json | jq -r '.terraform_version')
    print_status "Terraform version: $TF_VERSION"
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI >= 2.0"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure'"
        exit 1
    fi
    
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    print_status "AWS Account: $AWS_ACCOUNT"
    
    print_success "Prerequisites check passed"
}

# Function to validate environment
validate_environment() {
    local env=$1
    if [[ ! "$env" =~ ^(dev|staging|prod|dr)$ ]]; then
        print_error "Invalid environment: $env"
        echo "Valid environments: dev, staging, prod, dr"
        exit 1
    fi
}

# Function to setup environment directory
setup_environment() {
    local env=$1
    local env_dir="environments/$env"
    
    if [ ! -d "$env_dir" ]; then
        print_error "Environment directory $env_dir does not exist"
        exit 1
    fi
    
    cd "$env_dir"
    print_status "Working in environment: $env ($env_dir)"
}

# Function to initialize Terraform
terraform_init() {
    local env=$1
    local backend_config=${2:-"../../backend.hcl"}
    
    print_status "Initializing Terraform for $env environment..."
    
    if [ -f "$backend_config" ]; then
        terraform init -backend-config="$backend_config"
    else
        print_warning "Backend config file not found: $backend_config"
        terraform init
    fi
    
    print_success "Terraform initialized for $env environment"
}

# Function to plan Terraform changes
terraform_plan() {
    local env=$1
    local var_file=${2:-"terraform.tfvars"}
    
    print_status "Planning Terraform changes for $env environment..."
    
    if [ -f "$var_file" ]; then
        terraform plan -var-file="$var_file" -out="$env.tfplan"
    else
        print_warning "Variables file not found: $var_file"
        print_warning "Using default variables and any existing terraform.tfvars"
        terraform plan -out="$env.tfplan"
    fi
    
    print_success "Terraform plan completed for $env environment"
    print_status "Plan saved to: $env.tfplan"
}

# Function to apply Terraform changes
terraform_apply() {
    local env=$1
    local auto_approve=$2
    
    print_status "Applying Terraform changes for $env environment..."
    
    if [ ! -f "$env.tfplan" ]; then
        print_error "No plan file found. Please run 'plan' command first."
        exit 1
    fi
    
    if [ "$auto_approve" = true ]; then
        terraform apply "$env.tfplan"
    else
        print_warning "This will apply changes to $env environment infrastructure."
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            terraform apply "$env.tfplan"
        else
            print_status "Apply cancelled"
            exit 0
        fi
    fi
    
    print_success "Terraform apply completed for $env environment"
}

# Function to destroy infrastructure
terraform_destroy() {
    local env=$1
    local auto_approve=$2
    local var_file=${3:-"terraform.tfvars"}
    
    print_warning "This will DESTROY all infrastructure in $env environment!"
    print_warning "This action cannot be undone!"
    
    if [ "$auto_approve" != true ]; then
        read -p "Are you absolutely sure you want to destroy $env environment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Destroy cancelled"
            exit 0
        fi
        
        read -p "Please type the environment name '$env' to confirm: " confirmation
        if [ "$confirmation" != "$env" ]; then
            print_error "Environment name confirmation failed"
            exit 1
        fi
    fi
    
    print_status "Destroying Terraform infrastructure for $env environment..."
    
    if [ -f "$var_file" ]; then
        if [ "$auto_approve" = true ]; then
            terraform destroy -var-file="$var_file" -auto-approve
        else
            terraform destroy -var-file="$var_file"
        fi
    else
        print_warning "Variables file not found: $var_file"
        if [ "$auto_approve" = true ]; then
            terraform destroy -auto-approve
        else
            terraform destroy
        fi
    fi
    
    print_success "Terraform destroy completed for $env environment"
}

# Function to validate Terraform configuration
terraform_validate() {
    local env=$1
    
    print_status "Validating Terraform configuration for $env environment..."
    
    terraform validate
    terraform fmt -check=true -recursive
    
    print_success "Terraform validation passed for $env environment"
}

# Function to show outputs
terraform_output() {
    local env=$1
    
    print_status "Terraform outputs for $env environment:"
    terraform output -json | jq '.'
}

# Main script logic
main() {
    local command=$1
    local environment=$2
    local auto_approve=false
    local backend_config=""
    local var_file=""
    
    # Parse additional arguments
    shift 2
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-approve)
                auto_approve=true
                shift
                ;;
            --backend-config)
                backend_config="$2"
                shift 2
                ;;
            --var-file)
                var_file="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Check if command and environment are provided
    if [ -z "$command" ] || [ -z "$environment" ]; then
        usage
        exit 1
    fi
    
    # Validate environment
    validate_environment "$environment"
    
    # Check prerequisites
    check_prerequisites
    
    # Setup environment directory
    setup_environment "$environment"
    
    # Execute command
    case $command in
        init)
            terraform_init "$environment" "$backend_config"
            ;;
        plan)
            terraform_plan "$environment" "$var_file"
            ;;
        apply)
            terraform_apply "$environment" "$auto_approve"
            ;;
        destroy)
            terraform_destroy "$environment" "$auto_approve" "$var_file"
            ;;
        validate)
            terraform_validate "$environment"
            ;;
        output)
            terraform_output "$environment"
            ;;
        *)
            print_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Check if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
