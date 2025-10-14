#!/bin/bash

# ===== AI NUTRITIONIST COST OPTIMIZATION DEPLOYMENT SCRIPT =====
# This script deploys the complete cost optimization infrastructure

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
REGION="us-east-1"
CONFIG_FILE=""
DRY_RUN=false
SKIP_VALIDATION=false

# Print colored output
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

# Print banner
print_banner() {
    echo ""
    echo "================================================================================================"
    echo "  AI NUTRITIONIST COST OPTIMIZATION DEPLOYMENT"
    echo "================================================================================================"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region:      $REGION"
    echo "  Config:      ${CONFIG_FILE:-"Using defaults"}"
    echo "  Dry Run:     $DRY_RUN"
    echo "================================================================================================"
    echo ""
}

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy cost optimization infrastructure for AI Nutritionist"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV     Deployment environment (dev|staging|prod) [default: dev]"
    echo "  -r, --region REGION       AWS region [default: us-east-1]"
    echo "  -c, --config FILE         Cost optimization config file"
    echo "  -d, --dry-run             Show what would be deployed without applying"
    echo "  -s, --skip-validation     Skip pre-deployment validation"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --environment prod --region us-west-2"
    echo "  $0 --config cost-optimization-prod.tfvars --dry-run"
    echo "  $0 --environment staging --skip-validation"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validation
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "infrastructure/terraform/main.tf" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check for required tools
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v terraform &> /dev/null; then
        missing_deps+=("terraform")
    fi
    
    if ! command -v aws &> /dev/null; then
        missing_deps+=("aws-cli")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install the missing tools and try again"
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Validate AWS credentials
validate_aws_credentials() {
    print_status "Validating AWS credentials..."
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        print_error "Please run 'aws configure' or set AWS environment variables"
        exit 1
    fi
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local current_region=$(aws configure get region 2>/dev/null || echo "not-set")
    
    print_success "AWS credentials validated"
    print_status "Account ID: $account_id"
    print_status "Configured region: $current_region"
    
    if [[ "$current_region" != "$REGION" ]]; then
        print_warning "AWS CLI region ($current_region) differs from deployment region ($REGION)"
        print_warning "Using deployment region: $REGION"
    fi
}

# Generate cost optimization configuration
generate_config() {
    print_status "Generating cost optimization configuration..."
    
    local config_file="infrastructure/terraform/cost-optimization-${ENVIRONMENT}.tfvars"
    
    if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
        config_file="$CONFIG_FILE"
        print_status "Using provided config file: $config_file"
    elif [[ -f "$config_file" ]]; then
        print_status "Using existing config file: $config_file"
    else
        print_status "Creating new config file: $config_file"
        
        # Create environment-specific configuration
        case $ENVIRONMENT in
            dev)
                cat > "$config_file" << EOF
# Development Environment Cost Optimization Configuration
monthly_budget_limit             = 50
lambda_daily_cost_threshold      = 5
dynamodb_daily_cost_threshold    = 8
api_gateway_daily_cost_threshold = 3

# Contact Information
owner_email = "admin@ai-nutritionist.com"

# Cost Allocation
cost_center   = "AI-Nutritionist-Dev"
billing_group = "Development"

# Automation (aggressive for dev)
enable_auto_scaling          = true
enable_automated_cleanup     = true
enable_cost_anomaly_detection = true

# Resource Settings
cloudwatch_log_retention_days        = 7
lambda_version_retention_count       = 2
unused_resource_grace_period_days    = 1

# Performance vs Cost Trade-offs
enable_lambda_provisioned_concurrency = false
api_gateway_caching_enabled          = false
cloudfront_price_class               = "PriceClass_100"
EOF
                ;;
            staging)
                cat > "$config_file" << EOF
# Staging Environment Cost Optimization Configuration
monthly_budget_limit             = 100
lambda_daily_cost_threshold      = 10
dynamodb_daily_cost_threshold    = 15
api_gateway_daily_cost_threshold = 5

# Contact Information
owner_email = "admin@ai-nutritionist.com"

# Cost Allocation
cost_center   = "AI-Nutritionist-Staging"
billing_group = "Staging"

# Automation
enable_auto_scaling          = true
enable_automated_cleanup     = true
enable_cost_anomaly_detection = true

# Resource Settings
cloudwatch_log_retention_days        = 14
lambda_version_retention_count       = 3
unused_resource_grace_period_days    = 3

# Performance vs Cost Trade-offs
enable_lambda_provisioned_concurrency = false
api_gateway_caching_enabled          = true
api_gateway_cache_cluster_size       = "0.5"
cloudfront_price_class               = "PriceClass_100"
EOF
                ;;
            prod)
                cat > "$config_file" << EOF
# Production Environment Cost Optimization Configuration
monthly_budget_limit             = 200
lambda_daily_cost_threshold      = 20
dynamodb_daily_cost_threshold    = 30
api_gateway_daily_cost_threshold = 10

# Contact Information
owner_email = "admin@ai-nutritionist.com"

# Cost Allocation
cost_center   = "AI-Nutritionist-Production"
billing_group = "Production"

# Automation (conservative for prod)
enable_auto_scaling          = true
enable_automated_cleanup     = false  # Manual approval for prod
enable_cost_anomaly_detection = true

# Resource Settings
cloudwatch_log_retention_days        = 90
lambda_version_retention_count       = 5
unused_resource_grace_period_days    = 7

# Performance vs Cost Trade-offs
enable_lambda_provisioned_concurrency = true
lambda_provisioned_concurrency_limit  = 15
api_gateway_caching_enabled          = true
api_gateway_cache_cluster_size       = "6.1"
cloudfront_price_class               = "PriceClass_200"

# Business Hours Optimization
enable_business_hours_scaling = false  # Disable for 24/7 availability
EOF
                ;;
        esac
        
        print_success "Generated configuration file: $config_file"
    fi
    
    echo "$config_file"
}

# Calculate cost savings
calculate_savings() {
    print_status "Calculating potential cost savings..."
    
    if [[ -f "scripts/cost_optimization_calculator.py" ]]; then
        local profile="medium"
        case $ENVIRONMENT in
            dev) profile="small" ;;
            staging) profile="medium" ;;
            prod) profile="large" ;;
        esac
        
        print_status "Running cost calculation for $profile usage profile..."
        python3 scripts/cost_optimization_calculator.py --profile "$profile"
    else
        print_warning "Cost calculator script not found, skipping savings calculation"
    fi
}

# Initialize Terraform
terraform_init() {
    print_status "Initializing Terraform..."
    
    cd infrastructure/terraform
    
    if ! terraform init -input=false; then
        print_error "Terraform initialization failed"
        exit 1
    fi
    
    print_success "Terraform initialized successfully"
    cd - > /dev/null
}

# Validate Terraform configuration
terraform_validate() {
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        print_warning "Skipping Terraform validation"
        return
    fi
    
    print_status "Validating Terraform configuration..."
    
    cd infrastructure/terraform
    
    if ! terraform validate; then
        print_error "Terraform validation failed"
        exit 1
    fi
    
    print_success "Terraform configuration is valid"
    cd - > /dev/null
}

# Plan Terraform deployment
terraform_plan() {
    print_status "Planning Terraform deployment..."
    
    cd infrastructure/terraform
    
    local plan_args=()
    plan_args+=("-var=environment=$ENVIRONMENT")
    plan_args+=("-var=aws_region=$REGION")
    
    if [[ -n "$CONFIG_FILE" ]]; then
        plan_args+=("-var-file=../../$CONFIG_FILE")
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "DRY RUN: Showing planned changes..."
    fi
    
    if ! terraform plan "${plan_args[@]}" -out=tfplan; then
        print_error "Terraform planning failed"
        exit 1
    fi
    
    print_success "Terraform plan completed successfully"
    cd - > /dev/null
}

# Apply Terraform deployment
terraform_apply() {
    if [[ "$DRY_RUN" == "true" ]]; then
        print_success "DRY RUN: Deployment plan completed successfully"
        print_status "Run without --dry-run to apply changes"
        return
    fi
    
    print_status "Applying Terraform deployment..."
    
    cd infrastructure/terraform
    
    if ! terraform apply -input=false tfplan; then
        print_error "Terraform deployment failed"
        exit 1
    fi
    
    print_success "Terraform deployment completed successfully"
    cd - > /dev/null
}

# Show deployment outputs
show_outputs() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return
    fi
    
    print_status "Retrieving deployment outputs..."
    
    cd infrastructure/terraform
    
    echo ""
    echo "================================================================================================"
    echo "  DEPLOYMENT OUTPUTS"
    echo "================================================================================================"
    
    # Cost optimization summary
    if terraform output cost_optimization_summary &> /dev/null; then
        echo ""
        echo "Cost Optimization Summary:"
        terraform output -json cost_optimization_summary | python3 -m json.tool
    fi
    
    # Dashboard URL
    if terraform output cost_monitoring_dashboard_url &> /dev/null; then
        echo ""
        echo "Cost Monitoring Dashboard:"
        terraform output -raw cost_monitoring_dashboard_url
    fi
    
    # Budget information
    echo ""
    echo "Budget Configuration:"
    echo "  Monthly Limit: \$$monthly_budget_limit"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region: $REGION"
    
    cd - > /dev/null
}

# Post-deployment verification
verify_deployment() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return
    fi
    
    print_status "Verifying deployment..."
    
    # Check if cost anomaly detectors are created
    local detectors=$(aws ce describe-anomaly-detectors --region "$REGION" --query 'AnomalyDetectors[?contains(AnomalyDetectorArn, `ai-nutritionist`)]' --output text 2>/dev/null | wc -l)
    
    if [[ $detectors -gt 0 ]]; then
        print_success "Cost anomaly detectors deployed successfully"
    else
        print_warning "Cost anomaly detectors not found (may take a few minutes to appear)"
    fi
    
    # Check if budgets are created
    local budgets=$(aws budgets describe-budgets --account-id "$(aws sts get-caller-identity --query Account --output text)" --query 'Budgets[?contains(BudgetName, `ai-nutritionist`)]' --output text 2>/dev/null | wc -l)
    
    if [[ $budgets -gt 0 ]]; then
        print_success "Cost budgets deployed successfully"
    else
        print_warning "Cost budgets not found (may take a few minutes to appear)"
    fi
    
    print_success "Deployment verification completed"
}

# Cleanup function
cleanup() {
    if [[ -f "infrastructure/terraform/tfplan" ]]; then
        rm -f infrastructure/terraform/tfplan
    fi
}

# Main execution function
main() {
    trap cleanup EXIT
    
    print_banner
    
    # Pre-deployment checks
    check_dependencies
    validate_aws_credentials
    
    # Generate configuration
    CONFIG_FILE=$(generate_config)
    
    # Calculate potential savings
    if [[ "$SKIP_VALIDATION" != "true" ]]; then
        calculate_savings
        echo ""
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deployment cancelled by user"
            exit 0
        fi
    fi
    
    # Terraform deployment
    terraform_init
    terraform_validate
    terraform_plan
    terraform_apply
    
    # Post-deployment
    show_outputs
    verify_deployment
    
    echo ""
    echo "================================================================================================"
    echo "  DEPLOYMENT COMPLETE"
    echo "================================================================================================"
    print_success "Cost optimization infrastructure deployed successfully!"
    echo ""
    print_status "Next Steps:"
    echo "  1. Check your email for budget alert confirmations"
    echo "  2. Review the cost monitoring dashboard"
    echo "  3. Monitor cost anomaly detection alerts"
    echo "  4. Implement the recommended optimizations"
    echo ""
    echo "📊 Dashboard: $(cd infrastructure/terraform && terraform output -raw cost_monitoring_dashboard_url 2>/dev/null || echo 'Check Terraform outputs')"
    echo "💰 Monthly Budget: \$$monthly_budget_limit"
    echo "🎯 Environment: $ENVIRONMENT"
    echo ""
    echo "================================================================================================"
}

# Run main function
main "$@"
