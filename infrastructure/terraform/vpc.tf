# VPC Infrastructure for Enhanced Security and Network Isolation
# Best Practice: Deploy Lambda functions in private subnets with NAT Gateway for outbound internet access

# Main VPC
resource "aws_vpc" "main" {
  count = var.enable_vpc ? 1 : 0
  
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    {
      Name = "${var.project_name}-vpc-${var.environment}"
      Type = "VPC"
    },
    var.additional_tags
  )
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id = aws_vpc.main[0].id

  tags = merge(
    {
      Name = "${var.project_name}-igw-${var.environment}"
    },
    var.additional_tags
  )
}

# Public Subnets (for NAT Gateways and Load Balancers)
resource "aws_subnet" "public" {
  count = var.enable_vpc ? length(var.public_subnet_cidrs) : 0
  
  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    {
      Name = "${var.project_name}-public-subnet-${count.index + 1}-${var.environment}"
      Type = "Public"
      Tier = "Public"
    },
    var.additional_tags
  )
}

# Private Subnets (for Lambda functions)
resource "aws_subnet" "private" {
  count = var.enable_vpc ? length(var.private_subnet_cidrs) : 0
  
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(
    {
      Name = "${var.project_name}-private-subnet-${count.index + 1}-${var.environment}"
      Type = "Private"
      Tier = "Application"
    },
    var.additional_tags
  )
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count = var.enable_vpc ? length(var.public_subnet_cidrs) : 0
  
  domain = "vpc"
  
  depends_on = [aws_internet_gateway.main]

  tags = merge(
    {
      Name = "${var.project_name}-nat-eip-${count.index + 1}-${var.environment}"
    },
    var.additional_tags
  )
}

# NAT Gateways (High Availability)
resource "aws_nat_gateway" "main" {
  count = var.enable_vpc ? length(var.public_subnet_cidrs) : 0
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    {
      Name = "${var.project_name}-nat-gateway-${count.index + 1}-${var.environment}"
    },
    var.additional_tags
  )

  depends_on = [aws_internet_gateway.main]
}

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = merge(
    {
      Name = "${var.project_name}-public-rt-${var.environment}"
    },
    var.additional_tags
  )
}

# Route Tables for Private Subnets (one per AZ for HA)
resource "aws_route_table" "private" {
  count = var.enable_vpc ? length(var.private_subnet_cidrs) : 0
  
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(
    {
      Name = "${var.project_name}-private-rt-${count.index + 1}-${var.environment}"
    },
    var.additional_tags
  )
}

# Route Table Associations - Public
resource "aws_route_table_association" "public" {
  count = var.enable_vpc ? length(var.public_subnet_cidrs) : 0
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

# Route Table Associations - Private
resource "aws_route_table_association" "private" {
  count = var.enable_vpc ? length(var.private_subnet_cidrs) : 0
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# VPC Endpoints for AWS Services (Cost Optimization & Security)
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id       = aws_vpc.main[0].id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  
  route_table_ids = concat(
    aws_route_table.private[*].id,
    [aws_route_table.public[0].id]
  )

  tags = merge(
    {
      Name = "${var.project_name}-s3-endpoint-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_vpc_endpoint" "dynamodb" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id       = aws_vpc.main[0].id
  service_name = "com.amazonaws.${var.aws_region}.dynamodb"
  
  route_table_ids = concat(
    aws_route_table.private[*].id,
    [aws_route_table.public[0].id]
  )

  tags = merge(
    {
      Name = "${var.project_name}-dynamodb-endpoint-${var.environment}"
    },
    var.additional_tags
  )
}

# Security Group for Lambda Functions
resource "aws_security_group" "lambda_enhanced" {
  count = var.enable_vpc ? 1 : 0
  
  name_prefix = "${var.project_name}-lambda-${var.environment}-"
  vpc_id      = aws_vpc.main[0].id

  # Outbound rules for AWS services
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS to AWS services"
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP for package downloads"
  }

  # DNS
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS resolution"
  }

  tags = merge(
    {
      Name = "${var.project_name}-lambda-sg-${var.environment}"
    },
    var.additional_tags
  )

  lifecycle {
    create_before_destroy = true
  }
}

# VPC Flow Logs for Security Monitoring
resource "aws_flow_log" "vpc" {
  count = var.enable_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  iam_role_arn    = aws_iam_role.flow_log[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main[0].id
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.enable_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  name              = "/aws/vpc/flowlogs/${var.project_name}-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name = "${var.project_name}-vpc-flowlogs-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_iam_role" "flow_log" {
  count = var.enable_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  name = "${var.project_name}-flowlog-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name = "${var.project_name}-flowlog-role-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy" "flow_log" {
  count = var.enable_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  name = "${var.project_name}-flowlog-policy-${var.environment}"
  role = aws_iam_role.flow_log[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}
