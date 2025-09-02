# AI Nutritionist Assistant - AWS Infrastructure
# Terraform configuration for production-ready deployment

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
  }

  # Backend configuration for state management
  backend "s3" {
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
    tags = {
      Project     = "AI-Nutritionist"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "AI-Nutritionist-Team"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}
