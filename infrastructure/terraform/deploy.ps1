# AI Nutritionist Infrastructure Deployment Script (PowerShell)
# This script helps deploy the Terraform infrastructure across environments

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("init", "plan", "apply", "destroy", "validate", "output")]
    [string]$Command,
    
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod", "dr")]
    [string]$Environment,
    
    [switch]$AutoApprove,
    [string]$BackendConfig = "",
    [string]$VarFile = ""
)

# Color functions
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to display usage
function Show-Usage {
    Write-Host "AI Nutritionist Infrastructure Deployment Script"
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 -Command <COMMAND> -Environment <ENVIRONMENT> [OPTIONS]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  init      Initialize Terraform for an environment"
    Write-Host "  plan      Plan Terraform changes"
    Write-Host "  apply     Apply Terraform changes"
    Write-Host "  destroy   Destroy Terraform infrastructure"
    Write-Host "  validate  Validate Terraform configuration"
    Write-Host "  output    Show Terraform outputs"
    Write-Host ""
    Write-Host "Environments:"
    Write-Host "  dev       Development environment"
    Write-Host "  staging   Staging environment"
    Write-Host "  prod      Production environment"
    Write-Host "  dr        Disaster recovery environment"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -AutoApprove    Auto-approve apply/destroy (use with caution)"
    Write-Host "  -BackendConfig  Specify backend configuration file"
    Write-Host "  -VarFile       Specify variables file"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy.ps1 -Command init -Environment dev"
    Write-Host "  .\deploy.ps1 -Command plan -Environment prod -VarFile prod.tfvars"
    Write-Host "  .\deploy.ps1 -Command apply -Environment dev -AutoApprove"
    Write-Host "  .\deploy.ps1 -Command destroy -Environment staging"
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if Terraform is installed
    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        Write-Error "Terraform is not installed. Please install Terraform >= 1.5"
        exit 1
    }
    
    # Check Terraform version
    $tfVersion = (terraform version -json | ConvertFrom-Json).terraform_version
    Write-Status "Terraform version: $tfVersion"
    
    # Check if AWS CLI is installed
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error "AWS CLI is not installed. Please install AWS CLI >= 2.0"
        exit 1
    }
    
    # Check AWS credentials
    try {
        $awsAccount = (aws sts get-caller-identity --query Account --output text 2>$null)
        Write-Status "AWS Account: $awsAccount"
    }
    catch {
        Write-Error "AWS credentials not configured. Please run 'aws configure'"
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Function to setup environment directory
function Set-Environment {
    param([string]$env)
    
    $envDir = "environments\$env"
    
    if (-not (Test-Path $envDir)) {
        Write-Error "Environment directory $envDir does not exist"
        exit 1
    }
    
    Set-Location $envDir
    Write-Status "Working in environment: $env ($envDir)"
}

# Function to initialize Terraform
function Initialize-Terraform {
    param(
        [string]$env,
        [string]$backendConfig = "..\..\backend.hcl"
    )
    
    Write-Status "Initializing Terraform for $env environment..."
    
    if (Test-Path $backendConfig) {
        terraform init -backend-config="$backendConfig"
    }
    else {
        Write-Warning "Backend config file not found: $backendConfig"
        terraform init
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform initialization failed"
        exit 1
    }
    
    Write-Success "Terraform initialized for $env environment"
}

# Function to plan Terraform changes
function Plan-Terraform {
    param(
        [string]$env,
        [string]$varFile = "terraform.tfvars"
    )
    
    Write-Status "Planning Terraform changes for $env environment..."
    
    if (Test-Path $varFile) {
        terraform plan -var-file="$varFile" -out="$env.tfplan"
    }
    else {
        Write-Warning "Variables file not found: $varFile"
        Write-Warning "Using default variables and any existing terraform.tfvars"
        terraform plan -out="$env.tfplan"
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform plan failed"
        exit 1
    }
    
    Write-Success "Terraform plan completed for $env environment"
    Write-Status "Plan saved to: $env.tfplan"
}

# Function to apply Terraform changes
function Apply-Terraform {
    param(
        [string]$env,
        [bool]$autoApprove
    )
    
    Write-Status "Applying Terraform changes for $env environment..."
    
    if (-not (Test-Path "$env.tfplan")) {
        Write-Error "No plan file found. Please run 'plan' command first."
        exit 1
    }
    
    if (-not $autoApprove) {
        Write-Warning "This will apply changes to $env environment infrastructure."
        $confirmation = Read-Host "Are you sure you want to continue? (y/N)"
        if ($confirmation -notmatch '^[Yy]$') {
            Write-Status "Apply cancelled"
            exit 0
        }
    }
    
    terraform apply "$env.tfplan"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform apply failed"
        exit 1
    }
    
    Write-Success "Terraform apply completed for $env environment"
}

# Function to destroy infrastructure
function Remove-Terraform {
    param(
        [string]$env,
        [bool]$autoApprove,
        [string]$varFile = "terraform.tfvars"
    )
    
    Write-Warning "This will DESTROY all infrastructure in $env environment!"
    Write-Warning "This action cannot be undone!"
    
    if (-not $autoApprove) {
        $confirmation = Read-Host "Are you absolutely sure you want to destroy $env environment? (y/N)"
        if ($confirmation -notmatch '^[Yy]$') {
            Write-Status "Destroy cancelled"
            exit 0
        }
        
        $envConfirmation = Read-Host "Please type the environment name '$env' to confirm"
        if ($envConfirmation -ne $env) {
            Write-Error "Environment name confirmation failed"
            exit 1
        }
    }
    
    Write-Status "Destroying Terraform infrastructure for $env environment..."
    
    if (Test-Path $varFile) {
        if ($autoApprove) {
            terraform destroy -var-file="$varFile" -auto-approve
        }
        else {
            terraform destroy -var-file="$varFile"
        }
    }
    else {
        Write-Warning "Variables file not found: $varFile"
        if ($autoApprove) {
            terraform destroy -auto-approve
        }
        else {
            terraform destroy
        }
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform destroy failed"
        exit 1
    }
    
    Write-Success "Terraform destroy completed for $env environment"
}

# Function to validate Terraform configuration
function Test-Terraform {
    param([string]$env)
    
    Write-Status "Validating Terraform configuration for $env environment..."
    
    terraform validate
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform validation failed"
        exit 1
    }
    
    terraform fmt -check=true -recursive
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform formatting check failed"
        exit 1
    }
    
    Write-Success "Terraform validation passed for $env environment"
}

# Function to show outputs
function Show-TerraformOutput {
    param([string]$env)
    
    Write-Status "Terraform outputs for $env environment:"
    terraform output -json | ConvertFrom-Json | ConvertTo-Json -Depth 10
}

# Main script logic
try {
    # Check prerequisites
    Test-Prerequisites
    
    # Setup environment directory
    Set-Environment $Environment
    
    # Execute command
    switch ($Command) {
        "init" {
            Initialize-Terraform $Environment $BackendConfig
        }
        "plan" {
            Plan-Terraform $Environment $VarFile
        }
        "apply" {
            Apply-Terraform $Environment $AutoApprove
        }
        "destroy" {
            Remove-Terraform $Environment $AutoApprove $VarFile
        }
        "validate" {
            Test-Terraform $Environment
        }
        "output" {
            Show-TerraformOutput $Environment
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Usage
            exit 1
        }
    }
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    exit 1
}
