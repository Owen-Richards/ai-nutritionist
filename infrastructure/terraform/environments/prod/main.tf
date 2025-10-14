# Production Environment Configuration
# terraform/environments/prod/main.tf

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
    # bucket         = "ai-nutritionist-terraform-state-prod"
    # key            = "prod/terraform.tfstate"
    # region         = "us-east-1"
    # encrypt        = true
    # dynamodb_table = "terraform-state-lock-prod"
  }
}

# Use the root module
module "ai_nutritionist_prod" {
  source = "../../"

  # Environment Configuration
  project_name = "ai-nutritionist"
  environment  = "prod"
  aws_region   = "us-east-1"
  dr_region    = "us-west-2"

  # Required variables with production values
  openai_api_key    = var.openai_api_key
  nutrition_api_key = var.nutrition_api_key
  owner_email       = var.owner_email

  # Cost Management (higher limits for production)
  enable_cost_monitoring = true
  monthly_budget_limit   = "1000"
  budget_notification_emails = [
    "production-alerts@ainutrition.com",
    "finance@ainutrition.com",
    "devops@ainutrition.com"
  ]

  # Production-specific overrides
  enable_enhanced_monitoring = true
  enable_auto_scaling       = true
  force_single_nat_gateway  = false

  # Database Configuration (production-grade)
  db_allocated_storage = 100
  ecs_desired_count   = 3
  ecs_min_capacity    = 2
  ecs_max_capacity    = 20

  # Security Configuration (maximum security)
  enable_waf                    = true
  enable_cross_region_backup    = true
  cross_region_backup_destination = "us-west-2"
  rds_performance_insights_enabled = true
  elasticache_snapshot_retention_limit = 30
  enforce_ssl_only             = true
  enable_encryption_at_rest    = true
  enable_encryption_in_transit = true

  # Application Configuration
  container_image = "ai-nutritionist:prod-${var.app_version}"
  allowed_origins = [
    "https://app.ainutrition.com",
    "https://api.ainutrition.com",
    "https://www.ainutrition.com"
  ]

  # API Gateway Configuration
  api_domain_name     = "api.ainutrition.com"
  api_certificate_arn = var.api_certificate_arn

  # Feature Flags (all enabled for production)
  enable_container_insights = true
  enable_xray_tracing      = true
  enable_backup_automation = true

  # Advanced Configuration
  lambda_reserved_concurrency = 100
  data_retention_days        = 365
  compliance_framework       = "SOC2"

  # IP Whitelist for management access
  ip_whitelist = var.management_ip_whitelist

  # KMS Configuration
  kms_admin_arns = var.kms_admin_arns
  kms_user_arns  = var.kms_user_arns

  # Production-specific tags
  global_tags = {
    Project     = "AI-Nutritionist"
    Environment = "Production"
    Repository  = "ai-nutritionalist"
    Team        = "AI-Development"
    CostCenter  = "Production"
    Owner       = "production@ainutrition.com"
    Compliance  = "SOC2"
    Backup      = "Required"
    Monitoring  = "Critical"
  }
}

# Production-specific outputs
output "prod_environment_info" {
  description = "Production environment connection information"
  value = {
    api_endpoint      = module.ai_nutritionist_prod.api_gateway_endpoint
    api_custom_domain = module.ai_nutritionist_prod.api_gateway_custom_domain
    database_endpoint = module.ai_nutritionist_prod.rds_endpoint
    cache_endpoint    = module.ai_nutritionist_prod.elasticache_primary_endpoint
    ecs_cluster       = module.ai_nutritionist_prod.ecs_cluster_name
    vpc_id           = module.ai_nutritionist_prod.vpc_id
    load_balancer_dns = module.ai_nutritionist_prod.load_balancer_dns_name
  }
  sensitive = true
}

output "prod_monitoring_dashboards" {
  description = "Production monitoring and alerting information"
  value = {
    cloudwatch_dashboards = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:"
    cloudwatch_alarms     = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:"
    cloudwatch_logs       = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups"
    xray_traces          = "https://console.aws.amazon.com/xray/home?region=us-east-1#/traces"
    budget_alerts        = module.ai_nutritionist_prod.budget_name
  }
}

output "prod_security_info" {
  description = "Production security and compliance information"
  value = {
    cloudtrail_logs     = "CloudTrail logging enabled"
    encryption_at_rest  = "All services encrypted at rest"
    encryption_in_transit = "All services encrypted in transit"
    waf_enabled        = "WAF protection enabled on API Gateway"
    vpc_flow_logs      = "VPC flow logs enabled"
    compliance_framework = "SOC2"
  }
}
