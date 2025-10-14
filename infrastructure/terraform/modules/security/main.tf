# Security Module for AI Nutritionist
# Provides comprehensive security infrastructure including IAM, KMS, Secrets Manager, and security groups

locals {
  common_tags = merge(var.tags, {
    Module = "security"
  })

  # Environment-specific configurations
  environment_config = {
    dev = {
      kms_deletion_window = 7
      password_length     = 16
      secret_retention    = 7
    }
    staging = {
      kms_deletion_window = 14
      password_length     = 20
      secret_retention    = 14
    }
    prod = {
      kms_deletion_window = 30
      password_length     = 32
      secret_retention    = 30
    }
    dr = {
      kms_deletion_window = 30
      password_length     = 32
      secret_retention    = 30
    }
  }

  env_config = local.environment_config[var.environment]
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# KMS Keys for different services
resource "aws_kms_key" "main" {
  for_each = var.kms_keys

  description             = each.value.description
  deletion_window_in_days = lookup(each.value, "deletion_window_in_days", local.env_config.kms_deletion_window)
  enable_key_rotation     = lookup(each.value, "enable_key_rotation", true)
  multi_region           = lookup(each.value, "multi_region", false)

  policy = lookup(each.value, "policy", null) != null ? each.value.policy : jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for encryption/decryption"
        Effect = "Allow"
        Principal = {
          AWS = concat(
            lookup(each.value, "admin_arns", []),
            lookup(each.value, "user_arns", [])
          )
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}-kms-key"
    Type = "kms-key"
    Service = each.key
  })
}

resource "aws_kms_alias" "main" {
  for_each = var.kms_keys

  name          = "alias/${var.name_prefix}-${each.key}"
  target_key_id = aws_kms_key.main[each.key].key_id
}

# Secrets Manager Secrets
resource "aws_secretsmanager_secret" "main" {
  for_each = var.secrets

  name                    = "${var.name_prefix}-${each.key}"
  description             = each.value.description
  kms_key_id             = aws_kms_key.main["secrets"].arn
  recovery_window_in_days = lookup(each.value, "recovery_window_in_days", local.env_config.secret_retention)
  
  replica {
    region = data.aws_region.current.name
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}"
    Type = "secret"
  })
}

# Generate random passwords for secrets that need them
resource "random_password" "secrets" {
  for_each = {
    for k, v in var.secrets : k => v
    if lookup(v, "generate_password", false)
  }

  length  = lookup(each.value, "password_length", local.env_config.password_length)
  special = lookup(each.value, "include_special", true)
  upper   = lookup(each.value, "include_upper", true)
  lower   = lookup(each.value, "include_lower", true)
  numeric = lookup(each.value, "include_numeric", true)
}

# Secret versions with generated or provided values
resource "aws_secretsmanager_secret_version" "main" {
  for_each = var.secrets

  secret_id = aws_secretsmanager_secret.main[each.key].id
  secret_string = lookup(each.value, "generate_password", false) ? jsonencode({
    password = random_password.secrets[each.key].result
    username = lookup(each.value, "username", "admin")
  }) : each.value.secret_string

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# IAM Roles
resource "aws_iam_role" "main" {
  for_each = var.iam_roles

  name               = "${var.name_prefix}-${each.key}-role"
  assume_role_policy = each.value.assume_role_policy
  path               = lookup(each.value, "path", "/")
  max_session_duration = lookup(each.value, "max_session_duration", 3600)

  dynamic "inline_policy" {
    for_each = lookup(each.value, "inline_policies", {})
    content {
      name   = inline_policy.key
      policy = inline_policy.value
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}-role"
    Type = "iam-role"
  })
}

# IAM Role Policy Attachments
resource "aws_iam_role_policy_attachment" "main" {
  for_each = {
    for combo in flatten([
      for role_key, role_config in var.iam_roles : [
        for policy_arn in lookup(role_config, "policy_arns", []) : {
          role_key   = role_key
          policy_arn = policy_arn
          key        = "${role_key}_${replace(policy_arn, "/[^a-zA-Z0-9]/", "_")}"
        }
      ]
    ]) : combo.key => combo
  }

  role       = aws_iam_role.main[each.value.role_key].name
  policy_arn = each.value.policy_arn
}

# IAM Policies
resource "aws_iam_policy" "main" {
  for_each = var.iam_policies

  name        = "${var.name_prefix}-${each.key}-policy"
  description = each.value.description
  policy      = each.value.policy
  path        = lookup(each.value, "path", "/")

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}-policy"
    Type = "iam-policy"
  })
}

# IAM Groups
resource "aws_iam_group" "main" {
  for_each = var.iam_groups

  name = "${var.name_prefix}-${each.key}-group"
  path = lookup(each.value, "path", "/")
}

# IAM Group Policy Attachments
resource "aws_iam_group_policy_attachment" "main" {
  for_each = {
    for combo in flatten([
      for group_key, group_config in var.iam_groups : [
        for policy_arn in lookup(group_config, "policy_arns", []) : {
          group_key  = group_key
          policy_arn = policy_arn
          key        = "${group_key}_${replace(policy_arn, "/[^a-zA-Z0-9]/", "_")}"
        }
      ]
    ]) : combo.key => combo
  }

  group      = aws_iam_group.main[each.value.group_key].name
  policy_arn = each.value.policy_arn
}

# IAM Users
resource "aws_iam_user" "main" {
  for_each = var.iam_users

  name = "${var.name_prefix}-${each.key}-user"
  path = lookup(each.value, "path", "/")

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}-user"
    Type = "iam-user"
  })
}

# IAM User Group Memberships
resource "aws_iam_user_group_membership" "main" {
  for_each = {
    for user_key, user_config in var.iam_users : user_key => user_config
    if lookup(user_config, "groups", []) != []
  }

  user   = aws_iam_user.main[each.key].name
  groups = [
    for group in each.value.groups :
    aws_iam_group.main[group].name
  ]
}

# Security Groups
resource "aws_security_group" "main" {
  for_each = var.security_groups

  name_prefix = "${var.name_prefix}-${each.key}-"
  description = each.value.description
  vpc_id      = each.value.vpc_id

  # Ingress rules
  dynamic "ingress" {
    for_each = lookup(each.value, "ingress_rules", [])
    content {
      description      = ingress.value.description
      from_port        = ingress.value.from_port
      to_port          = ingress.value.to_port
      protocol         = ingress.value.protocol
      cidr_blocks      = lookup(ingress.value, "cidr_blocks", null)
      ipv6_cidr_blocks = lookup(ingress.value, "ipv6_cidr_blocks", null)
      security_groups  = lookup(ingress.value, "security_groups", null)
      self             = lookup(ingress.value, "self", null)
    }
  }

  # Egress rules
  dynamic "egress" {
    for_each = lookup(each.value, "egress_rules", [])
    content {
      description      = egress.value.description
      from_port        = egress.value.from_port
      to_port          = egress.value.to_port
      protocol         = egress.value.protocol
      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group Rules (for complex rule management)
resource "aws_security_group_rule" "ingress" {
  for_each = {
    for rule in flatten([
      for sg_key, sg_config in var.security_groups : [
        for idx, rule in lookup(sg_config, "complex_ingress_rules", []) : {
          sg_key = sg_key
          rule   = rule
          key    = "${sg_key}_ingress_${idx}"
        }
      ]
    ]) : rule.key => rule
  }

  type                     = "ingress"
  security_group_id        = aws_security_group.main[each.value.sg_key].id
  description              = each.value.rule.description
  from_port                = each.value.rule.from_port
  to_port                  = each.value.rule.to_port
  protocol                 = each.value.rule.protocol
  cidr_blocks              = lookup(each.value.rule, "cidr_blocks", null)
  ipv6_cidr_blocks         = lookup(each.value.rule, "ipv6_cidr_blocks", null)
  source_security_group_id = lookup(each.value.rule, "source_security_group_id", null)
  self                     = lookup(each.value.rule, "self", null)
}

resource "aws_security_group_rule" "egress" {
  for_each = {
    for rule in flatten([
      for sg_key, sg_config in var.security_groups : [
        for idx, rule in lookup(sg_config, "complex_egress_rules", []) : {
          sg_key = sg_key
          rule   = rule
          key    = "${sg_key}_egress_${idx}"
        }
      ]
    ]) : rule.key => rule
  }

  type                     = "egress"
  security_group_id        = aws_security_group.main[each.value.sg_key].id
  description              = each.value.rule.description
  from_port                = each.value.rule.from_port
  to_port                  = each.value.rule.to_port
  protocol                 = each.value.rule.protocol
  cidr_blocks              = lookup(each.value.rule, "cidr_blocks", null)
  ipv6_cidr_blocks         = lookup(each.value.rule, "ipv6_cidr_blocks", null)
  source_security_group_id = lookup(each.value.rule, "source_security_group_id", null)
  self                     = lookup(each.value.rule, "self", null)
}

# CloudWatch Log Group for Security Monitoring
resource "aws_cloudwatch_log_group" "security" {
  count = var.enable_security_logging ? 1 : 0

  name              = "/aws/security/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.main["cloudwatch"].arn

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-security-logs"
    Type = "cloudwatch-log-group"
  })
}

# CloudTrail for API logging
resource "aws_cloudtrail" "main" {
  count = var.enable_cloudtrail ? 1 : 0

  name           = "${var.name_prefix}-cloudtrail"
  s3_bucket_name = var.cloudtrail_s3_bucket_name
  s3_key_prefix  = "${var.name_prefix}/cloudtrail/"

  event_selector {
    read_write_type                 = "All"
    include_management_events       = true
    exclude_management_event_sources = ["kms.amazonaws.com", "rdsdata.amazonaws.com"]

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::${var.cloudtrail_s3_bucket_name}/*"]
    }
  }

  kms_key_id = aws_kms_key.main["cloudtrail"].arn

  cloud_watch_logs_group_arn = var.enable_security_logging ? "${aws_cloudwatch_log_group.security[0].arn}:*" : null
  cloud_watch_logs_role_arn  = var.enable_security_logging ? aws_iam_role.cloudtrail[0].arn : null

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-cloudtrail"
    Type = "cloudtrail"
  })
}

# IAM Role for CloudTrail
resource "aws_iam_role" "cloudtrail" {
  count = var.enable_cloudtrail && var.enable_security_logging ? 1 : 0

  name = "${var.name_prefix}-cloudtrail-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for CloudTrail CloudWatch Logs
resource "aws_iam_role_policy" "cloudtrail" {
  count = var.enable_cloudtrail && var.enable_security_logging ? 1 : 0

  name = "${var.name_prefix}-cloudtrail-logs-policy"
  role = aws_iam_role.cloudtrail[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "logs:CreateLogStream"
        ]
        Resource = "${aws_cloudwatch_log_group.security[0].arn}:*"
      }
    ]
  })
}
