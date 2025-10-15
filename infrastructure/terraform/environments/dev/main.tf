# Development Environment Configuration
# terraform/environments/dev/main.tf

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure these values in backend.hcl or via CLI
    # bucket         = "ai-nutritionist-terraform-state-dev"
    # key            = "dev/terraform.tfstate"
    # region         = "us-east-1"
    # encrypt        = true
    # dynamodb_table = "terraform-state-lock-dev"
  }
}

# Use the root module
module "ai_nutritionist_dev" {
  source = "../../"

  # Environment Configuration
  project_name = "ai-nutritionist"
  environment  = "dev"
  aws_region   = "us-east-1"

  # Required variables with dev-specific values
  openai_api_key    = var.openai_api_key
  nutrition_api_key = var.nutrition_api_key
  owner_email       = var.owner_email

  # Cost Management (lower limits for dev)
  enable_cost_monitoring = true
  monthly_budget_limit   = "50"
  budget_notification_emails = [
    "dev-team@ainutrition.com"
  ]

  # Development-specific overrides
  enable_enhanced_monitoring = false
  enable_auto_scaling       = false
  force_single_nat_gateway  = true

  # Database Configuration (minimal for dev)
  db_allocated_storage = 20
  ecs_desired_count   = 1
  ecs_min_capacity    = 1
  ecs_max_capacity    = 2

  # Security Configuration (relaxed for dev)
  enable_waf                    = false
  enable_cross_region_backup    = false
  rds_performance_insights_enabled = false
  elasticache_snapshot_retention_limit = 1

  # Application Configuration
  container_image = "ai-nutritionist:dev-latest"
  allowed_origins = ["*"]

  # Feature Flags
  enable_container_insights = false
  enable_xray_tracing      = false

  # Development-specific tags
  global_tags = {
    Project     = "AI-Nutritionist"
    Environment = "Development"
    Repository  = "ai-nutritionalist"
    Team        = "AI-Development"
    CostCenter  = "Development"
    Owner       = "dev-team@ainutrition.com"
  }
}

# Development-specific outputs
output "dev_environment_info" {
  description = "Development environment connection information"
  value = {
    api_endpoint     = module.ai_nutritionist_dev.api_gateway_endpoint
    database_endpoint = module.ai_nutritionist_dev.rds_endpoint
    cache_endpoint   = module.ai_nutritionist_dev.elasticache_primary_endpoint
    ecs_cluster      = module.ai_nutritionist_dev.ecs_cluster_name
    vpc_id          = module.ai_nutritionist_dev.vpc_id
  }
  sensitive = true
}

output "dev_quick_access" {
  description = "Quick access information for developers"
  value = {
    ssh_bastion_command = "# No bastion host in dev environment"
    database_tunnel     = "# Connect directly via VPN or AWS Session Manager"
    api_test_url       = "${module.ai_nutritionist_dev.api_gateway_endpoint}/health"
    cloudwatch_logs    = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups"
  }
}
