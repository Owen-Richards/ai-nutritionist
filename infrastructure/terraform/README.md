# AI Nutritionist Terraform Infrastructure

This directory contains the complete Terraform infrastructure for the AI Nutritionist application, converted from the original AWS SAM template with enhanced security, monitoring, and compliance features.

## Infrastructure Overview

### Architecture Components

- **API Gateway**: RESTful API with webhook endpoints for Twilio and Stripe
- **Lambda Functions**: Serverless compute for message handling, billing, and scheduling
- **DynamoDB**: NoSQL database for user data, subscriptions, usage tracking, and caching
- **S3 + CloudFront**: Static website hosting with global CDN
- **KMS**: Encryption keys for data protection and GDPR compliance
- **CloudWatch**: Monitoring, logging, and alerting
- **WAF**: Web Application Firewall for security
- **EventBridge**: Scheduled meal planning automation

### Key Features

- **GDPR Compliance**: Audit trails, encryption, data retention policies
- **Family Sharing**: Privacy-compliant multi-user features
- **Cost Optimization**: Prompt caching, resource rightsizing, budget alerts
- **Security**: KMS encryption, WAF protection, least-privilege IAM
- **Monitoring**: Comprehensive dashboards, alarms, and anomaly detection
- **High Availability**: Multi-AZ deployment with fault tolerance

## File Structure

```
terraform/
├── main.tf                    # Provider configuration and backend
├── variables.tf               # Input variables and validation
├── dynamodb_fixed.tf          # DynamoDB tables (corrected version)
├── kms.tf                     # KMS encryption keys
├── iam.tf                     # IAM roles and policies
├── lambda.tf                  # Lambda functions and permissions
├── api_gateway.tf             # API Gateway configuration
├── s3_cloudfront.tf           # S3 buckets and CloudFront distribution
├── monitoring.tf              # CloudWatch dashboards, alarms, and cost management
├── outputs.tf                 # Output values for reference
└── README.md                  # This file
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** v1.0+ installed
3. **AWS Account** with sufficient permissions
4. **Domain/SSL Certificate** (optional, for custom domains)
5. **Twilio Account** for SMS integration
6. **Stripe Account** for billing integration

## Quick Start

### 1. Clone and Navigate

```bash
cd infrastructure/terraform
```

### 2. Configure Variables

Create a `terraform.tfvars` file:

```hcl
# Required
project_name = "ai-nutritionist"
environment  = "prod"
aws_region   = "us-east-1"

# Optional - Monitoring
alert_email = "admin@yourdomain.com"
enable_sns_alerts = true

# Optional - Cost Management
monthly_budget_limit = "100"
enable_cost_budgets = true

# Optional - Custom Domain
custom_domain_name = "api.yourdomain.com"
ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."

# Optional - CloudFront SSL
cloudfront_ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
```

### 3. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the infrastructure
terraform apply
```

### 4. Post-Deployment Setup

After successful deployment:

1. **Configure Twilio Webhook**: Use the `webhook_url` output
2. **Configure Stripe Webhook**: Use the `billing_webhook_url` output
3. **Upload Web Content**: Deploy your frontend to the S3 bucket
4. **Set Environment Variables**: Configure Lambda environment variables
5. **Test Endpoints**: Verify API Gateway and Lambda functions

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_name` | Project identifier | - | Yes |
| `environment` | Deployment environment | - | Yes |
| `aws_region` | AWS region | - | Yes |
| `alert_email` | Email for alerts | "" | No |
| `monthly_budget_limit` | Budget limit in USD | "100" | No |

### Feature Flags

| Feature | Variable | Default | Description |
|---------|----------|---------|-------------|
| GDPR Compliance | `gdpr_compliance_enabled` | true | Audit trails and data protection |
| Family Sharing | `enable_family_sharing` | true | Multi-user privacy features |
| Cost Optimization | `enable_cost_optimization` | true | Prompt caching and budget alerts |
| WAF Protection | `enable_waf` | true | Web Application Firewall |
| CloudFront WAF | `enable_cloudfront_waf` | true | CDN protection |
| X-Ray Tracing | `enable_xray_tracing` | true | Distributed tracing |
| VPC Deployment | `enable_vpc` | false | Deploy in VPC |

### Security Configuration

- **KMS Encryption**: All data encrypted at rest
- **IAM Roles**: Least-privilege access policies
- **WAF Rules**: Protection against common attacks
- **VPC Support**: Optional private networking
- **Webhook Validation**: Signature verification

### Cost Optimization

- **Prompt Caching**: Reduces Bedrock API costs
- **DynamoDB On-Demand**: Pay-per-use pricing
- **Budget Alerts**: Automated cost monitoring
- **Anomaly Detection**: Unusual spend notifications
- **Resource Rightsizing**: Optimized configurations

## Monitoring and Alerting

### CloudWatch Dashboard

Comprehensive monitoring including:
- Lambda function metrics (duration, errors, invocations)
- DynamoDB capacity and throttling
- API Gateway latency and errors
- CloudFront request patterns
- Bedrock usage and costs

### Automated Alerts

- Lambda function errors and timeouts
- DynamoDB throttling
- API Gateway 5XX errors
- Cost budget overruns
- Anomaly detection triggers

### Log Analysis

- Structured logging with CloudWatch Insights
- Error tracking and troubleshooting queries
- Performance analysis for slow requests

## Security Best Practices

### Data Protection

- **Encryption in Transit**: TLS 1.2+ for all communications
- **Encryption at Rest**: KMS encryption for all storage
- **Key Rotation**: Automated KMS key rotation
- **Access Logging**: Comprehensive audit trails

### Access Control

- **IAM Roles**: Service-specific permissions
- **API Keys**: Secure webhook authentication
- **CORS**: Proper cross-origin policies
- **Rate Limiting**: WAF-based request throttling

### Compliance

- **GDPR Ready**: Consent tracking and data audit
- **Privacy Controls**: Family sharing with explicit consent
- **Data Retention**: Configurable lifecycle policies
- **Export Capabilities**: Data portability features

## Cost Estimation

### Monthly Cost Breakdown (Estimated)

**Development Environment (~$20-40/month):**
- Lambda: $5-10
- DynamoDB: $5-15
- API Gateway: $3-7
- CloudFront: $1-3
- S3: $1-2
- Other Services: $5-8

**Production Environment (~$50-150/month):**
- Lambda: $15-40
- DynamoDB: $15-50
- API Gateway: $10-25
- CloudFront: $5-15
- Bedrock: $10-30
- Other Services: $10-20

*Costs vary based on usage patterns and enabled features.*

## Troubleshooting

### Common Issues

1. **IAM Permission Errors**
   - Ensure AWS CLI has sufficient permissions
   - Check IAM policies and roles

2. **Resource Naming Conflicts**
   - Modify `project_name` or `environment` variables
   - Use unique S3 bucket names

3. **SSL Certificate Issues**
   - Ensure certificate is in `us-east-1` for CloudFront
   - Verify domain validation

4. **VPC Configuration**
   - Provide valid VPC ID and subnet IDs if enabling VPC

### Debug Commands

```bash
# Check Terraform state
terraform show

# Validate configuration
terraform validate

# Format configuration
terraform fmt

# View outputs
terraform output

# Destroy infrastructure (BE CAREFUL)
terraform destroy
```

## Updating Infrastructure

### Safe Update Process

1. **Backup State**: Always backup `terraform.tfstate`
2. **Plan Changes**: Use `terraform plan` to review
3. **Gradual Updates**: Update non-critical resources first
4. **Monitor Deployment**: Watch for errors during apply
5. **Rollback Plan**: Have rollback strategy ready

### Version Upgrades

- Review Terraform provider updates
- Check AWS resource deprecations
- Test in development environment first
- Update variable constraints as needed

## Support and Maintenance

### Regular Tasks

- Monitor CloudWatch dashboards
- Review cost reports and budgets
- Update Lambda function code
- Rotate KMS keys annually
- Review and update IAM policies

### Backup Strategy

- Terraform state stored in S3 backend
- DynamoDB point-in-time recovery enabled
- Regular configuration backups
- Documented disaster recovery procedures

## Contributing

When modifying the infrastructure:

1. Update variable descriptions and defaults
2. Add appropriate tags to new resources
3. Include monitoring for new services
4. Update this README with new features
5. Test in development environment first

## Additional Resources

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/)
- [GDPR Compliance on AWS](https://aws.amazon.com/compliance/gdpr-center/)

---

**Note**: This infrastructure is designed for production use with security, compliance, and cost optimization in mind. Always review and customize according to your specific requirements.
