# 🛡️ Comprehensive Security Testing Suite

This directory contains a complete security testing framework for the AI Nutritionist application, implementing industry-standard security testing practices and compliance validation.

## 📁 Directory Structure

```
tests/security/
├── vulnerability_scanning/          # Automated vulnerability detection
│   ├── test_owasp_zap_scanning.py  # OWASP ZAP web application scanning
│   └── test_dependency_vulnerabilities.py  # Dependency and code vulnerability scanning
├── penetration_testing/             # Manual and automated penetration testing
│   └── test_penetration_suite.py    # Authentication, authorization, injection testing
├── compliance/                      # Regulatory compliance testing
│   ├── test_hipaa_compliance.py     # HIPAA compliance for health data
│   └── test_gdpr_compliance.py      # GDPR compliance for personal data
├── automation/                      # Security automation and CI/CD integration
│   └── test_security_automation.py  # Secret scanning, security gates
├── reports/                         # Generated security reports
│   ├── vulnerability/               # Vulnerability scan reports
│   ├── penetration/                # Penetration test reports
│   ├── compliance/                 # Compliance assessment reports
│   ├── automation/                 # Automation and CI/CD reports
│   └── comprehensive/              # Master security reports
└── run_comprehensive_security_tests.py  # Master test runner
```

## 🔍 Vulnerability Scanning

### OWASP ZAP Integration

- **Passive Scanning**: Non-intrusive vulnerability detection
- **Active Scanning**: Comprehensive penetration testing
- **API Security Testing**: OpenAPI/Swagger specification-based testing
- **Custom Security Rules**: AI Nutritionist-specific security validations

### Dependency Vulnerability Scanning

- **Python Dependencies**: Safety and Bandit integration
- **Static Code Analysis**: Semgrep security rule enforcement
- **Container Security**: Docker image and Dockerfile security analysis
- **Infrastructure as Code**: Terraform security validation

### Usage

```python
from vulnerability_scanning.test_owasp_zap_scanning import OWASPZAPScanner
from vulnerability_scanning.test_dependency_vulnerabilities import DependencyVulnerabilityScanner

# Run OWASP ZAP scan
zap_scanner = OWASPZAPScanner()
passive_results = zap_scanner.passive_scan("http://localhost:8000")
active_results = zap_scanner.active_scan("http://localhost:8000")

# Run dependency scan
dep_scanner = DependencyVulnerabilityScanner()
vulnerability_report = dep_scanner.generate_comprehensive_report()
```

## 🎯 Penetration Testing

### Authentication Testing

- **Authentication Bypass**: SQL injection, NoSQL injection, JWT manipulation
- **Weak Authentication**: Password policy validation, multi-factor authentication
- **Session Management**: Session fixation, timeout validation, secure cookies

### Authorization Testing

- **Insecure Direct Object References (IDOR)**: Horizontal and vertical privilege escalation
- **Missing Function Level Access Control**: Admin endpoint protection
- **Business Logic Flaws**: Workflow and state management vulnerabilities

### Injection Attack Testing

- **SQL Injection**: Time-based, error-based, and blind SQL injection
- **NoSQL Injection**: MongoDB and DynamoDB injection patterns
- **XSS (Cross-Site Scripting)**: Reflected, stored, and DOM-based XSS
- **Command Injection**: OS command execution vulnerabilities

### Usage

```python
from penetration_testing.test_penetration_suite import PenetrationTester

pen_tester = PenetrationTester("http://localhost:8000")
comprehensive_report = pen_tester.generate_penetration_test_report()

# Individual test categories
auth_results = pen_tester.test_authentication_bypass()
authz_results = pen_tester.test_authorization_flaws()
injection_results = pen_tester.test_injection_attacks()
```

## 📋 Compliance Testing

### HIPAA Compliance

- **PHI Data Protection**: Encryption at rest and in transit
- **Access Controls**: User authentication and authorization
- **Audit Controls**: Comprehensive logging and monitoring
- **Business Associate Agreements**: Third-party service validation

### GDPR Compliance

- **Lawful Basis for Processing**: Consent mechanisms and transparency
- **Data Subject Rights**: Access, rectification, erasure, portability
- **Data Protection by Design**: Privacy by default, data minimization
- **Breach Notification**: Detection and notification procedures

### Usage

```python
from compliance.test_hipaa_compliance import HIPAAComplianceTester
from compliance.test_gdpr_compliance import GDPRComplianceTester

# HIPAA compliance testing
hipaa_tester = HIPAAComplianceTester("http://localhost:8000")
hipaa_report = hipaa_tester.generate_hipaa_compliance_report()

# GDPR compliance testing
gdpr_tester = GDPRComplianceTester("http://localhost:8000")
gdpr_report = gdpr_tester.generate_gdpr_compliance_report()
```

## 🤖 Security Automation

### Secret Scanning

- **Hardcoded Secrets Detection**: API keys, passwords, tokens
- **Configuration Analysis**: Environment variables, config files
- **Version Control Safety**: Pre-commit hooks and Git history scanning

### Security Linting

- **Python Security**: Bandit integration for code security issues
- **JavaScript/TypeScript**: ESLint security plugin integration
- **Custom Security Checks**: Application-specific security validations

### CI/CD Integration

- **GitHub Actions**: Automated security workflow generation
- **GitLab CI**: Security pipeline configuration
- **Security Gates**: Automated pass/fail criteria for deployments

### Usage

```python
from automation.test_security_automation import SecurityAutomation

security_automation = SecurityAutomation(".")
secrets_report = security_automation.scan_secrets()
linting_report = security_automation.run_security_linting()
pipeline_config = security_automation.create_security_pipeline()
```

## 🚀 Running Security Tests

### Comprehensive Security Test Suite

Run all security tests with the master test runner:

```bash
# Run all security tests
python tests/security/run_comprehensive_security_tests.py

# Run specific test categories
python tests/security/run_comprehensive_security_tests.py --test-type vulnerability
python tests/security/run_comprehensive_security_tests.py --test-type penetration
python tests/security/run_comprehensive_security_tests.py --test-type compliance
python tests/security/run_comprehensive_security_tests.py --test-type automation

# Specify target and output directory
python tests/security/run_comprehensive_security_tests.py \
    --base-url https://api.ai-nutritionist.com \
    --output-dir ./security-reports
```

### Individual Test Categories

Run specific security test modules:

```bash
# Vulnerability scanning
python -m pytest tests/security/vulnerability_scanning/ -v

# Penetration testing
python -m pytest tests/security/penetration_testing/ -v

# Compliance testing
python -m pytest tests/security/compliance/ -v

# Security automation
python -m pytest tests/security/automation/ -v
```

### CI/CD Integration

Add to your CI/CD pipeline:

```yaml
# GitHub Actions (.github/workflows/security.yml)
name: Security Testing
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Security Tests
        run: python tests/security/run_comprehensive_security_tests.py
```

## 📊 Security Reports

### Report Types Generated

1. **Vulnerability Scan Reports**

   - JSON format with detailed findings
   - HTML executive summaries
   - SARIF format for tool integration

2. **Penetration Test Reports**

   - Detailed attack scenarios and results
   - Risk assessment and remediation guidance
   - Executive summary with business impact

3. **Compliance Assessment Reports**

   - Framework-specific compliance status
   - Gap analysis and remediation roadmap
   - Regulatory requirement mapping

4. **Security Automation Reports**
   - Secret scanning results with remediation
   - Security linting findings and fixes
   - CI/CD pipeline security configuration

### Report Locations

- **Vulnerability Reports**: `tests/security/reports/vulnerability/`
- **Penetration Reports**: `tests/security/reports/penetration/`
- **Compliance Reports**: `tests/security/reports/compliance/`
- **Automation Reports**: `tests/security/reports/automation/`
- **Comprehensive Reports**: `tests/security/reports/comprehensive/`

## ⚙️ Configuration

### Security Test Configuration

Create a `security_config.json` file:

```json
{
  "vulnerability_scanning": {
    "enabled": true,
    "dependencies": true,
    "containers": true,
    "infrastructure": true,
    "owasp_zap": true
  },
  "penetration_testing": {
    "enabled": true,
    "authentication_bypass": true,
    "authorization_flaws": true,
    "injection_attacks": true,
    "session_management": true
  },
  "compliance_testing": {
    "enabled": true,
    "hipaa": true,
    "gdpr": true,
    "pci_dss": false,
    "sox": false
  },
  "security_automation": {
    "enabled": true,
    "secret_scanning": true,
    "security_linting": true,
    "ci_cd_integration": true
  }
}
```

### Security Gates Configuration

Define security quality gates for CI/CD:

```json
{
  "security_gates": {
    "critical_vulnerabilities": 0,
    "high_vulnerabilities": 3,
    "secrets_found": 0,
    "compliance_violations": 0,
    "total_issues_threshold": 50
  }
}
```

## 🛠️ Dependencies

### Required Python Packages

```
# Core testing
pytest>=7.0.0
requests>=2.31.0

# Vulnerability scanning
safety>=2.3.0
bandit>=1.7.5
semgrep>=1.30.0

# Web application security
zapv2>=0.0.21  # OWASP ZAP API client (optional)

# Penetration testing
PyJWT>=2.8.0

# Compliance testing
cryptography>=41.0.0

# Security automation
pyyaml>=6.0
```

### Optional Tools

- **OWASP ZAP**: For comprehensive web application security testing
- **Docker**: For container security scanning
- **Node.js**: For JavaScript/TypeScript security linting
- **Terraform**: For infrastructure security validation

## 🔒 Security Best Practices

### Test Environment Security

1. **Isolated Testing**: Run security tests in isolated environments
2. **Sensitive Data**: Use mock data, never production data
3. **Network Isolation**: Separate test networks from production
4. **Credential Management**: Use test-specific credentials

### Continuous Security

1. **Regular Scanning**: Schedule weekly comprehensive scans
2. **Dependency Updates**: Monitor and update vulnerable dependencies
3. **Security Training**: Regular team training on secure coding
4. **Incident Response**: Defined procedures for security findings

### Compliance Maintenance

1. **Regular Assessments**: Quarterly compliance reviews
2. **Documentation Updates**: Keep compliance documentation current
3. **Audit Trails**: Maintain comprehensive audit logs
4. **Third-Party Reviews**: Annual external security assessments

## 📈 Metrics and KPIs

### Security Metrics Tracked

- **Vulnerability Density**: Vulnerabilities per 1000 lines of code
- **Time to Fix**: Average time to resolve security issues
- **Security Test Coverage**: Percentage of code covered by security tests
- **Compliance Score**: Percentage of compliance requirements met

### Success Criteria

- **Zero Critical Vulnerabilities**: No critical security issues in production
- **95% Compliance**: Meet 95% of applicable regulatory requirements
- **24-Hour Fix Time**: Resolve high-severity issues within 24 hours
- **Automated Testing**: 100% automated security testing in CI/CD

## 🆘 Support and Troubleshooting

### Common Issues

1. **ZAP Connection Issues**

   ```bash
   # Start ZAP daemon manually
   zap.sh -daemon -port 8080 -config api.key=test-api-key
   ```

2. **Permission Errors**

   ```bash
   # Fix report directory permissions
   chmod -R 755 tests/security/reports/
   ```

3. **Missing Dependencies**
   ```bash
   # Install all security testing dependencies
   pip install -r requirements-dev.txt
   ```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# Run with debug output
SECURITY_TEST_DEBUG=1 python tests/security/run_comprehensive_security_tests.py
```

### Contact

For security-related questions or to report security issues:

- **Security Team**: security@ai-nutritionist.com
- **Documentation**: [Security Testing Guide](docs/security/README.md)
- **Issues**: Create a GitHub issue with the `security` label

---

**⚠️ Important**: This security testing suite is designed for testing environments only. Never run penetration tests against production systems without proper authorization and during scheduled maintenance windows.
