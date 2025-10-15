# VPC Endpoints for AWS Services
# Reduces NAT Gateway costs and improves security

locals {
  vpc_endpoint_services = {
    s3 = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.s3"
      route_table_ids = concat(
        [aws_route_table.private_db.id],
        aws_route_table.private_app[*].id
      )
      policy = null
      type   = "Gateway"
    }
    
    dynamodb = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
      route_table_ids = concat(
        [aws_route_table.private_db.id],
        aws_route_table.private_app[*].id
      )
      policy = null
      type   = "Gateway"
    }

    ec2 = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.ec2"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    ecr_api = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    ecr_dkr = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    logs = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.logs"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    monitoring = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.monitoring"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    ssm = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.ssm"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    ssmmessages = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.ssmmessages"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    ec2messages = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.ec2messages"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    kms = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.kms"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }

    secretsmanager = {
      service_name = "com.amazonaws.${data.aws_region.current.name}.secretsmanager"
      subnet_ids   = aws_subnet.private_app[*].id
      type         = "Interface"
    }
  }

  # Filter services based on user configuration
  enabled_services = {
    for service, config in local.vpc_endpoint_services :
    service => config
    if contains(var.vpc_endpoint_services, service)
  }
}

# Data source for current region
data "aws_region" "current" {}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  count = var.enable_vpc_endpoints ? 1 : 0

  name_prefix = "${var.name_prefix}-vpc-endpoints-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-vpc-endpoints-sg"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Gateway Endpoints (S3, DynamoDB)
resource "aws_vpc_endpoint" "gateway" {
  for_each = var.enable_vpc_endpoints ? {
    for service, config in local.enabled_services :
    service => config
    if config.type == "Gateway"
  } : {}

  vpc_id              = aws_vpc.main.id
  service_name        = each.value.service_name
  vpc_endpoint_type   = "Gateway"
  route_table_ids     = each.value.route_table_ids
  policy              = each.value.policy

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}-endpoint"
    Type = "vpc-endpoint"
    Service = each.key
  })
}

# Interface Endpoints (EC2, ECR, Logs, etc.)
resource "aws_vpc_endpoint" "interface" {
  for_each = var.enable_vpc_endpoints ? {
    for service, config in local.enabled_services :
    service => config
    if config.type == "Interface"
  } : {}

  vpc_id              = aws_vpc.main.id
  service_name        = each.value.service_name
  vpc_endpoint_type   = "Interface"
  subnet_ids          = each.value.subnet_ids
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  
  private_dns_enabled = true
  policy              = lookup(each.value, "policy", null)

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-${each.key}-endpoint"
    Type = "vpc-endpoint"
    Service = each.key
  })
}

# CloudWatch Log Group for VPC Endpoint monitoring
resource "aws_cloudwatch_log_group" "vpc_endpoints" {
  count = var.enable_vpc_endpoints && var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/endpoints/${var.name_prefix}"
  retention_in_days = var.flow_log_retention_days

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-vpc-endpoints-logs"
    Type = "cloudwatch-log-group"
  })
}
