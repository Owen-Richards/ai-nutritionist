# Outputs for Security Module

# KMS Keys
output "kms_key_ids" {
  description = "Map of KMS key IDs"
  value = {
    for k, v in aws_kms_key.main : k => v.key_id
  }
}

output "kms_key_arns" {
  description = "Map of KMS key ARNs"
  value = {
    for k, v in aws_kms_key.main : k => v.arn
  }
}

output "kms_aliases" {
  description = "Map of KMS alias names"
  value = {
    for k, v in aws_kms_alias.main : k => v.name
  }
}

# Secrets Manager
output "secret_arns" {
  description = "Map of Secrets Manager secret ARNs"
  value = {
    for k, v in aws_secretsmanager_secret.main : k => v.arn
  }
}

output "secret_names" {
  description = "Map of Secrets Manager secret names"
  value = {
    for k, v in aws_secretsmanager_secret.main : k => v.name
  }
}

# IAM Roles
output "iam_role_arns" {
  description = "Map of IAM role ARNs"
  value = {
    for k, v in aws_iam_role.main : k => v.arn
  }
}

output "iam_role_names" {
  description = "Map of IAM role names"
  value = {
    for k, v in aws_iam_role.main : k => v.name
  }
}

# IAM Policies
output "iam_policy_arns" {
  description = "Map of IAM policy ARNs"
  value = {
    for k, v in aws_iam_policy.main : k => v.arn
  }
}

# IAM Groups
output "iam_group_names" {
  description = "Map of IAM group names"
  value = {
    for k, v in aws_iam_group.main : k => v.name
  }
}

output "iam_group_arns" {
  description = "Map of IAM group ARNs"
  value = {
    for k, v in aws_iam_group.main : k => v.arn
  }
}

# IAM Users
output "iam_user_names" {
  description = "Map of IAM user names"
  value = {
    for k, v in aws_iam_user.main : k => v.name
  }
}

output "iam_user_arns" {
  description = "Map of IAM user ARNs"
  value = {
    for k, v in aws_iam_user.main : k => v.arn
  }
}

# Security Groups
output "security_group_ids" {
  description = "Map of security group IDs"
  value = {
    for k, v in aws_security_group.main : k => v.id
  }
}

output "security_group_arns" {
  description = "Map of security group ARNs"
  value = {
    for k, v in aws_security_group.main : k => v.arn
  }
}

# CloudWatch Log Group
output "security_log_group_name" {
  description = "Name of the security CloudWatch log group"
  value       = var.enable_security_logging ? aws_cloudwatch_log_group.security[0].name : null
}

output "security_log_group_arn" {
  description = "ARN of the security CloudWatch log group"
  value       = var.enable_security_logging ? aws_cloudwatch_log_group.security[0].arn : null
}

# CloudTrail
output "cloudtrail_arn" {
  description = "ARN of the CloudTrail"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].arn : null
}

output "cloudtrail_home_region" {
  description = "Home region of the CloudTrail"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].home_region : null
}

# Common outputs for integration
output "encryption_keys" {
  description = "Encryption keys for different services"
  value = {
    for service in ["rds", "s3", "lambda", "ecs", "secrets", "cloudwatch", "cloudtrail"] :
    service => contains(keys(aws_kms_key.main), service) ? aws_kms_key.main[service].arn : null
  }
}

output "security_configuration" {
  description = "Security configuration summary"
  value = {
    kms_keys_created        = length(aws_kms_key.main)
    secrets_created         = length(aws_secretsmanager_secret.main)
    iam_roles_created       = length(aws_iam_role.main)
    iam_policies_created    = length(aws_iam_policy.main)
    security_groups_created = length(aws_security_group.main)
    cloudtrail_enabled      = var.enable_cloudtrail
    security_logging_enabled = var.enable_security_logging
  }
}
