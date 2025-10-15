# AI Nutritionist Infrastructure - Root Module
# Complete Infrastructure as Code for multi-environment deployment

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
  }

  # Backend configuration for state management
  backend "s3" {
    # Configure these values in your terraform.tfvars or backend config
    # bucket         = "your-terraform-state-bucket"
    # key            = "ai-nutritionist/terraform.tfstate"
    # region         = "us-east-1"
    # encrypt        = true
    # dynamodb_table = "terraform-state-lock"
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = local.common_tags
  }
}

# Local values
locals {
  # Common tags for all resources
  common_tags = merge(var.global_tags, {
    Project     = "AI-Nutritionist"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = "AI-Nutritionist-Team"
    CreatedAt   = timestamp()
  })

  # Environment-specific configurations
  environment_config = {
    dev = {
      vpc_cidr                = "10.0.0.0/16"
      availability_zones      = ["${var.aws_region}a", "${var.aws_region}b"]
      enable_nat_gateway      = false
      single_nat_gateway      = true
      instance_types          = {
        rds        = "db.t3.micro"
        cache      = "cache.t3.micro"
        ecs        = "t3.micro"
        lambda_memory = 256
      }
      auto_scaling            = false
      backup_retention        = 7
      monitoring_enabled      = true
      multi_az               = false
    }
    staging = {
      vpc_cidr                = "10.1.0.0/16"
      availability_zones      = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
      enable_nat_gateway      = true
      single_nat_gateway      = false
      instance_types          = {
        rds        = "db.t3.small"
        cache      = "cache.t3.small"
        ecs        = "t3.small"
        lambda_memory = 512
      }
      auto_scaling            = true
      backup_retention        = 14
      monitoring_enabled      = true
      multi_az               = true
    }
    prod = {
      vpc_cidr                = "10.2.0.0/16"
      availability_zones      = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
      enable_nat_gateway      = true
      single_nat_gateway      = false
      instance_types          = {
        rds        = "db.r5.large"
        cache      = "cache.r5.large"
        ecs        = "c5.large"
        lambda_memory = 1024
      }
      auto_scaling            = true
      backup_retention        = 30
      monitoring_enabled      = true
      multi_az               = true
    }
    dr = {
      vpc_cidr                = "10.3.0.0/16"
      availability_zones      = ["${var.dr_region}a", "${var.dr_region}b"]
      enable_nat_gateway      = true
      single_nat_gateway      = true
      instance_types          = {
        rds        = "db.r5.large"
        cache      = "cache.r5.large"
        ecs        = "c5.large"
        lambda_memory = 1024
      }
      auto_scaling            = false
      backup_retention        = 30
      monitoring_enabled      = true
      multi_az               = true
    }
  }

  env_config = local.environment_config[var.environment]
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Generate unique suffix for resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# 1. VPC and Networking
module "vpc" {
  source = "./modules/vpc"

  name_prefix             = "${var.project_name}-${var.environment}"
  vpc_cidr               = local.env_config.vpc_cidr
  availability_zones     = local.env_config.availability_zones
  enable_nat_gateway     = local.env_config.enable_nat_gateway
  single_nat_gateway     = local.env_config.single_nat_gateway
  enable_flow_logs       = var.enable_vpc_flow_logs
  enable_vpc_endpoints   = var.enable_vpc_endpoints
  management_cidr        = var.management_cidr

  tags = merge(local.common_tags, {
    Component = "networking"
  })

  environment = var.environment
}

# 2. Security Infrastructure
module "security" {
  source = "./modules/security"

  name_prefix  = "${var.project_name}-${var.environment}"
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  vpc_cidr     = module.vpc.vpc_cidr_block

  # KMS Keys for different services
  kms_keys = {
    rds = {
      description = "KMS key for RDS encryption"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
    s3 = {
      description = "KMS key for S3 encryption"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
    lambda = {
      description = "KMS key for Lambda encryption"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
    ecs = {
      description = "KMS key for ECS encryption"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
    secrets = {
      description = "KMS key for Secrets Manager"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
    cloudwatch = {
      description = "KMS key for CloudWatch logs"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
    cloudtrail = {
      description = "KMS key for CloudTrail logs"
      admin_arns  = var.kms_admin_arns
      user_arns   = var.kms_user_arns
    }
  }

  # Secrets for application
  secrets = merge(
    {
      database = {
        description       = "Database connection credentials"
        generate_password = true
        username         = "ainutrition_admin"
      }
      api_keys = {
        description   = "External API keys"
        secret_string = jsonencode({
          openai_api_key    = var.openai_api_key
          nutrition_api_key = var.nutrition_api_key
        })
      }
    },
    var.additional_secrets
  )

  # Security Groups
  security_groups = {
    alb = {
      description = "Security group for Application Load Balancer"
      vpc_id     = module.vpc.vpc_id
      ingress_rules = [
        {
          description = "HTTP"
          from_port   = 80
          to_port     = 80
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        },
        {
          description = "HTTPS"
          from_port   = 443
          to_port     = 443
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
      egress_rules = [
        {
          description = "All outbound"
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    ecs_tasks = {
      description = "Security group for ECS tasks"
      vpc_id     = module.vpc.vpc_id
      ingress_rules = [
        {
          description = "HTTP from ALB"
          from_port   = 8080
          to_port     = 8080
          protocol    = "tcp"
          self        = true
        }
      ]
      egress_rules = [
        {
          description = "All outbound"
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    database = {
      description = "Security group for database"
      vpc_id     = module.vpc.vpc_id
      ingress_rules = [
        {
          description = "PostgreSQL from app layer"
          from_port   = 5432
          to_port     = 5432
          protocol    = "tcp"
          cidr_blocks = [module.vpc.vpc_cidr_block]
        }
      ]
    }
    cache = {
      description = "Security group for cache"
      vpc_id     = module.vpc.vpc_id
      ingress_rules = [
        {
          description = "Redis from app layer"
          from_port   = 6379
          to_port     = 6379
          protocol    = "tcp"
          cidr_blocks = [module.vpc.vpc_cidr_block]
        }
      ]
    }
  }

  enable_security_logging = var.enable_security_logging
  enable_cloudtrail      = var.enable_cloudtrail
  cloudtrail_s3_bucket_name = var.cloudtrail_s3_bucket_name

  tags = merge(local.common_tags, {
    Component = "security"
  })
}

# 3. RDS Database
module "rds" {
  source = "./modules/rds"

  identifier      = "${var.project_name}-${var.environment}-db"
  engine_type     = "postgres"
  instance_class  = local.env_config.instance_types.rds
  allocated_storage = var.db_allocated_storage

  database_name    = var.db_name
  master_username  = var.db_username
  master_password  = var.db_password

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_db_subnet_ids
  allowed_security_groups = [module.security.security_group_ids["ecs_tasks"]]

  multi_az                = local.env_config.multi_az
  backup_retention_period = local.env_config.backup_retention
  kms_key_id             = module.security.kms_key_arns["rds"]
  
  create_read_replica = var.environment == "prod"
  
  tags = merge(local.common_tags, {
    Component = "database"
  })

  environment = var.environment
}

# 4. ElastiCache
module "elasticache" {
  source = "./modules/elasticache"

  cluster_id     = "${var.project_name}-${var.environment}-cache"
  engine        = "redis"
  node_type     = local.env_config.instance_types.cache
  num_cache_clusters = local.env_config.multi_az ? 2 : 1

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_app_subnet_ids
  allowed_security_groups = [module.security.security_group_ids["ecs_tasks"]]

  automatic_failover_enabled = local.env_config.multi_az
  multi_az_enabled          = local.env_config.multi_az
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                = module.security.kms_key_arns["cache"]

  tags = merge(local.common_tags, {
    Component = "cache"
  })

  environment = var.environment
}

# 5. ECS Cluster
module "ecs" {
  source = "./modules/ecs"

  cluster_name           = "${var.project_name}-${var.environment}"
  task_definition_family = "${var.project_name}-${var.environment}-app"
  service_name          = "${var.project_name}-${var.environment}-service"
  container_name        = "ai-nutritionist-app"
  container_image       = var.container_image
  container_port        = 8080

  vpc_id                 = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_app_subnet_ids
  allowed_security_groups = [module.security.security_group_ids["alb"]]

  fargate_cpu           = 512
  fargate_memory        = local.env_config.instance_types.lambda_memory
  service_desired_count = var.ecs_desired_count

  enable_auto_scaling           = local.env_config.auto_scaling
  auto_scaling_min_capacity     = var.ecs_min_capacity
  auto_scaling_max_capacity     = var.ecs_max_capacity

  environment_variables = {
    ENVIRONMENT        = var.environment
    DATABASE_URL      = "postgresql://${module.rds.db_instance_username}@${module.rds.db_instance_endpoint}/${module.rds.db_instance_database_name}"
    REDIS_URL         = "redis://${module.elasticache.primary_endpoint_address}:${module.elasticache.port}"
    AWS_REGION        = data.aws_region.current.name
  }

  secrets_manager_arns = [
    module.security.secret_arns["database"],
    module.security.secret_arns["api_keys"]
  ]

  tags = merge(local.common_tags, {
    Component = "compute"
  })

  environment = var.environment
}

# 6. API Gateway
module "api_gateway" {
  source = "./modules/api-gateway"

  api_name        = "${var.project_name}-${var.environment}-api"
  api_description = "AI Nutritionist API - ${var.environment}"
  api_type        = "HTTP"
  
  stage_name  = var.environment
  environment = var.environment

  # CORS configuration
  cors_configuration = {
    allow_credentials = false
    allow_headers     = ["content-type", "x-amz-date", "authorization", "x-api-key"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = var.allowed_origins
    max_age          = 300
  }

  # Custom domain (if provided)
  domain_name     = var.api_domain_name
  certificate_arn = var.api_certificate_arn

  tags = merge(local.common_tags, {
    Component = "api"
  })
}

# 7. Lambda Functions
module "lambda_nutrition_processor" {
  source = "./modules/lambda"

  function_name        = "${var.project_name}-${var.environment}-nutrition-processor"
  runtime             = "python3.11"
  handler             = "index.handler"
  memory_size         = local.env_config.instance_types.lambda_memory
  timeout             = 30

  source_code_path = "${path.module}/../services/nutrition-processor"

  vpc_config = {
    vpc_id             = module.vpc.vpc_id
    subnet_ids         = module.vpc.private_app_subnet_ids
    security_group_ids = [module.security.security_group_ids["ecs_tasks"]]
  }

  environment_variables = {
    ENVIRONMENT     = var.environment
    DATABASE_URL    = "postgresql://${module.rds.db_instance_username}@${module.rds.db_instance_endpoint}/${module.rds.db_instance_database_name}"
    REDIS_URL       = "redis://${module.elasticache.primary_endpoint_address}:${module.elasticache.port}"
  }

  kms_key_arn = module.security.kms_key_arns["lambda"]

  api_gateway_execution_arn = module.api_gateway.http_api_execution_arn

  tags = merge(local.common_tags, {
    Component = "serverless"
    Function  = "nutrition-processor"
  })

  environment = var.environment
}

# Monitoring Module (placeholder - would be implemented similarly)
# module "monitoring" {
#   source = "./modules/monitoring"
#   ...
# }

# Cost Optimization Resources
resource "aws_budgets_budget" "main" {
  count = var.enable_cost_monitoring ? 1 : 0

  name         = "${var.project_name}-${var.environment}-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "Tag"
    values = ["Project:AI-Nutritionist"]
  }

  cost_filter {
    name   = "Tag"
    values = ["Environment:${var.environment}"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_notification_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_notification_emails
  }

  tags = local.common_tags
}
