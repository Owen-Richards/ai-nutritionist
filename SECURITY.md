# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please follow these steps:

### 1. DO NOT Create a Public Issue

Security vulnerabilities should not be reported through public GitHub issues.

### 2. Send a Private Report

Email security details to: **security@ai-nutritionist.com**

Include:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if you have one)

### 3. Response Timeline

- **Initial Response**: Within 24 hours
- **Status Update**: Within 72 hours
- **Resolution**: Depends on severity (1-30 days)

## Security Measures

### Data Protection

- **Encryption at Rest**: All user data encrypted in DynamoDB
- **Encryption in Transit**: TLS 1.3 for all communications
- **Access Controls**: IAM policies with least privilege
- **Data Retention**: Automatic deletion per GDPR requirements

### Infrastructure Security

- **AWS Security Groups**: Restrictive network access
- **WAF Protection**: Web Application Firewall enabled
- **VPC Configuration**: Private subnets for sensitive resources
- **Secrets Management**: AWS Parameter Store/Secrets Manager

### Code Security

- **Dependency Scanning**: Automated vulnerability detection
- **Static Analysis**: Bandit security linting
- **Input Validation**: Strict validation on all inputs
- **Output Sanitization**: XSS protection measures

### Monitoring

- **CloudTrail**: All API calls logged
- **CloudWatch**: Real-time monitoring and alerts
- **Anomaly Detection**: Unusual activity patterns
- **Incident Response**: Automated alerting system

## Security Best Practices

### For Contributors

1. **Keep Dependencies Updated**: Regular security patches
2. **Secure Coding**: Follow OWASP guidelines
3. **Secret Management**: Never commit credentials
4. **Code Review**: Security-focused peer reviews

### For Users

1. **Environment Variables**: Use for sensitive configuration
2. **Access Keys**: Rotate regularly
3. **Monitoring**: Enable CloudWatch logging
4. **Updates**: Keep deployment up to date

## Common Vulnerabilities

### Prevented by Design

- **SQL Injection**: Using DynamoDB with parameter binding
- **XSS**: Input sanitization and output encoding
- **CSRF**: Stateless API design with JWT tokens
- **Data Exposure**: Minimal data collection and encryption

### Known Limitations

- **Message Content**: Twilio message content is not end-to-end encrypted
- **AI Responses**: AWS Bedrock processes meal plan requests
- **Logs**: CloudWatch logs may contain anonymized usage patterns

## Compliance

- **GDPR**: Data subject rights implementation
- **HIPAA**: No PHI collection or processing
- **SOC 2**: AWS infrastructure compliance
- **ISO 27001**: AWS data center standards

## Security Contacts

- **General Security**: security@ai-nutritionist.com
- **Privacy Officer**: privacy@ai-nutritionist.com
- **Incident Response**: incident@ai-nutritionist.com

## Bug Bounty

We currently do not offer a formal bug bounty program, but we appreciate responsible disclosure and will recognize contributors in our security acknowledgments.

---

**Remember**: When in doubt about security implications, reach out to our security team before making changes or disclosures.
