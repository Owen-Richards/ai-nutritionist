# Outputs for VPC Module

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_arn" {
  description = "ARN of the VPC"
  value       = aws_vpc.main.arn
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

# Public Subnets
output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "public_subnet_arns" {
  description = "ARNs of the public subnets"
  value       = aws_subnet.public[*].arn
}

output "public_subnet_cidrs" {
  description = "CIDR blocks of the public subnets"
  value       = aws_subnet.public[*].cidr_block
}

# Private App Subnets
output "private_app_subnet_ids" {
  description = "IDs of the private application subnets"
  value       = aws_subnet.private_app[*].id
}

output "private_app_subnet_arns" {
  description = "ARNs of the private application subnets"
  value       = aws_subnet.private_app[*].arn
}

output "private_app_subnet_cidrs" {
  description = "CIDR blocks of the private application subnets"
  value       = aws_subnet.private_app[*].cidr_block
}

# Private DB Subnets
output "private_db_subnet_ids" {
  description = "IDs of the private database subnets"
  value       = aws_subnet.private_db[*].id
}

output "private_db_subnet_arns" {
  description = "ARNs of the private database subnets"
  value       = aws_subnet.private_db[*].arn
}

output "private_db_subnet_cidrs" {
  description = "CIDR blocks of the private database subnets"
  value       = aws_subnet.private_db[*].cidr_block
}

# NAT Gateways
output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = var.enable_nat_gateway ? aws_nat_gateway.main[*].id : []
}

output "nat_gateway_public_ips" {
  description = "Public IPs of the NAT Gateways"
  value       = var.enable_nat_gateway ? aws_eip.nat[*].public_ip : []
}

# Route Tables
output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_app_route_table_ids" {
  description = "IDs of the private application route tables"
  value       = aws_route_table.private_app[*].id
}

output "private_db_route_table_id" {
  description = "ID of the private database route table"
  value       = aws_route_table.private_db.id
}

# Security Groups for reference
output "default_security_group_id" {
  description = "ID of the default security group"
  value       = aws_vpc.main.default_security_group_id
}

# Availability Zones
output "availability_zones" {
  description = "List of availability zones used"
  value       = var.availability_zones
}

# Network ACLs
output "public_network_acl_id" {
  description = "ID of the public network ACL"
  value       = var.enable_network_acls ? aws_network_acl.public.id : null
}

output "private_network_acl_id" {
  description = "ID of the private network ACL"
  value       = var.enable_network_acls ? aws_network_acl.private.id : null
}

# VPC Flow Logs
output "vpc_flow_log_id" {
  description = "ID of the VPC Flow Log"
  value       = var.enable_flow_logs ? aws_flow_log.vpc[0].id : null
}

output "vpc_flow_log_group_name" {
  description = "Name of the CloudWatch log group for VPC Flow Logs"
  value       = var.enable_flow_logs ? aws_cloudwatch_log_group.vpc_flow_log[0].name : null
}

# Subnet Groups for RDS and ElastiCache
output "db_subnet_group_name" {
  description = "Name for RDS subnet group (computed)"
  value       = "${var.name_prefix}-db-subnet-group"
}

output "cache_subnet_group_name" {
  description = "Name for ElastiCache subnet group (computed)"
  value       = "${var.name_prefix}-cache-subnet-group"
}

# Additional outputs for integration
output "vpc_tags" {
  description = "Tags applied to VPC resources"
  value       = merge(var.tags, {
    Module = "vpc"
  })
}
