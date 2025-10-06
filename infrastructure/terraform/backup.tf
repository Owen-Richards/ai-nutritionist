# AWS Backup for Automated Backup and Disaster Recovery
# Best Practice: Automated backups with cross-region replication for production

# AWS Backup Vault
resource "aws_backup_vault" "main" {
  count = var.enable_aws_backup ? 1 : 0
  
  name        = "${var.project_name}-backup-vault-${var.environment}"
  kms_key_arn = aws_kms_key.backup[0].arn

  tags = merge(
    {
      Name = "${var.project_name}-backup-vault-${var.environment}"
    },
    var.additional_tags
  )
}

# KMS Key for Backup Encryption
resource "aws_kms_key" "backup" {
  count = var.enable_aws_backup ? 1 : 0
  
  description             = "KMS key for AWS Backup encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(
    {
      Name    = "${var.project_name}-backup-key-${var.environment}"
      Purpose = "AWS Backup encryption"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "backup" {
  count = var.enable_aws_backup ? 1 : 0
  
  name          = "alias/${var.project_name}-backup-${var.environment}"
  target_key_id = aws_kms_key.backup[0].key_id
}

# Backup Plan
resource "aws_backup_plan" "main" {
  count = var.enable_aws_backup ? 1 : 0
  
  name = "${var.project_name}-backup-plan-${var.environment}"

  # Daily backups for production
  rule {
    rule_name         = "daily_backups"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = var.backup_schedule

    start_window      = 60  # Start within 1 hour
    completion_window = 300 # Complete within 5 hours

    lifecycle {
      cold_storage_after = var.backup_cold_storage_after
      delete_after       = var.backup_retention_days
    }

    recovery_point_tags = merge(
      {
        BackupType = "Daily"
      },
      var.additional_tags
    )
  }

  # Weekly backups with longer retention for production
  dynamic "rule" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      rule_name         = "weekly_backups"
      target_vault_name = aws_backup_vault.main[0].name
      schedule          = "cron(0 5 ? * SUN *)" # Weekly on Sunday

      start_window      = 60
      completion_window = 300

      lifecycle {
        cold_storage_after = var.backup_cold_storage_after
        delete_after       = var.backup_retention_days * 4 # 4x longer retention
      }

      recovery_point_tags = merge(
        {
          BackupType = "Weekly"
        },
        var.additional_tags
      )
    }
  }

  tags = merge(
    {
      Name = "${var.project_name}-backup-plan-${var.environment}"
    },
    var.additional_tags
  )
}

# IAM Role for AWS Backup
resource "aws_iam_role" "backup" {
  count = var.enable_aws_backup ? 1 : 0
  
  name = "${var.project_name}-backup-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name = "${var.project_name}-backup-role-${var.environment}"
    },
    var.additional_tags
  )
}

# Attach AWS managed policies for backup
resource "aws_iam_role_policy_attachment" "backup_service_role" {
  count = var.enable_aws_backup ? 1 : 0
  
  role       = aws_iam_role.backup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "backup_restore_role" {
  count = var.enable_aws_backup ? 1 : 0
  
  role       = aws_iam_role.backup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# Backup Selection for DynamoDB Tables
resource "aws_backup_selection" "dynamodb" {
  count = var.enable_aws_backup ? 1 : 0
  
  iam_role_arn = aws_iam_role.backup[0].arn
  name         = "${var.project_name}-dynamodb-backup-selection-${var.environment}"
  plan_id      = aws_backup_plan.main[0].id

  resources = [
    aws_dynamodb_table.user_data.arn,
    aws_dynamodb_table.subscriptions.arn,
    aws_dynamodb_table.usage.arn,
    aws_dynamodb_table.prompt_cache.arn
  ]

  condition {
    string_equals {
      key   = "aws:ResourceTag/Project"
      value = var.project_name
    }
  }
}

# Cross-Region Backup for Production
resource "aws_backup_vault" "cross_region" {
  count = var.enable_aws_backup && var.environment == "prod" && var.backup_cross_region_destination != "" ? 1 : 0
  
  provider = aws.backup_region
  
  name        = "${var.project_name}-backup-vault-cross-region-${var.environment}"
  kms_key_arn = aws_kms_key.backup_cross_region[0].arn

  tags = merge(
    {
      Name = "${var.project_name}-backup-vault-cross-region-${var.environment}"
    },
    var.additional_tags
  )
}

# KMS Key for Cross-Region Backup
resource "aws_kms_key" "backup_cross_region" {
  count = var.enable_aws_backup && var.environment == "prod" && var.backup_cross_region_destination != "" ? 1 : 0
  
  provider = aws.backup_region
  
  description             = "KMS key for cross-region backup encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    {
      Name    = "${var.project_name}-backup-cross-region-key-${var.environment}"
      Purpose = "Cross-region backup encryption"
    },
    var.additional_tags
  )
}

# Cross-Region Backup Copy Rule
resource "aws_backup_plan" "cross_region" {
  count = var.enable_aws_backup && var.environment == "prod" && var.backup_cross_region_destination != "" ? 1 : 0
  
  name = "${var.project_name}-cross-region-backup-plan-${var.environment}"

  rule {
    rule_name         = "cross_region_copy"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = var.backup_schedule

    copy_action {
      destination_vault_arn = aws_backup_vault.cross_region[0].arn
      
      lifecycle {
        cold_storage_after = var.backup_cold_storage_after
        delete_after       = var.backup_retention_days * 2 # Longer retention for cross-region
      }
    }

    lifecycle {
      delete_after = var.backup_retention_days
    }
  }

  tags = merge(
    {
      Name = "${var.project_name}-cross-region-backup-plan-${var.environment}"
    },
    var.additional_tags
  )
}

# Backup Notifications
resource "aws_sns_topic" "backup_notifications" {
  count = var.enable_aws_backup && var.enable_sns_alerts ? 1 : 0
  
  name         = "${var.project_name}-backup-notifications-${var.environment}"
  display_name = "Backup Job Notifications"

  kms_master_key_id = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name = "${var.project_name}-backup-notifications-${var.environment}"
    },
    var.additional_tags
  )
}

# EventBridge Rule for Backup Job State Changes
resource "aws_cloudwatch_event_rule" "backup_jobs" {
  count = var.enable_aws_backup && var.enable_sns_alerts ? 1 : 0
  
  name        = "${var.project_name}-backup-job-events-${var.environment}"
  description = "Capture backup job state changes"

  event_pattern = jsonencode({
    source      = ["aws.backup"]
    detail-type = ["Backup Job State Change"]
    detail = {
      state = ["FAILED", "EXPIRED", "PARTIAL"]
    }
  })

  tags = merge(
    {
      Name = "${var.project_name}-backup-events-${var.environment}"
    },
    var.additional_tags
  )
}

# EventBridge Target for Backup Notifications
resource "aws_cloudwatch_event_target" "backup_sns" {
  count = var.enable_aws_backup && var.enable_sns_alerts ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.backup_jobs[0].name
  target_id = "BackupSNSTarget"
  arn       = aws_sns_topic.backup_notifications[0].arn
}

# Disaster Recovery Documentation
resource "aws_s3_object" "dr_runbook" {
  count = var.enable_aws_backup ? 1 : 0
  
  bucket       = aws_s3_bucket.web_frontend.id
  key          = "docs/disaster-recovery-runbook.md"
  content_type = "text/markdown"

  content = templatefile("${path.module}/../../docs/disaster-recovery-runbook.md.tpl", {
    project_name = var.project_name
    environment  = var.environment
    backup_vault = var.enable_aws_backup ? aws_backup_vault.main[0].name : "not-configured"
    region       = var.aws_region
  })

  server_side_encryption = "aws:kms"
  kms_key_id            = aws_kms_key.s3.arn

  tags = merge(
    {
      Name = "disaster-recovery-runbook"
      Type = "Documentation"
    },
    var.additional_tags
  )
}
