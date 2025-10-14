# 🛡️ Security Testing Suite - Remediation Guide

This guide provides detailed remediation steps for common security vulnerabilities found during security testing of the AI Nutritionist application.

## 🚨 Critical Vulnerabilities

### 1. SQL Injection

**Risk Level**: CRITICAL  
**CVSS Score**: 9.8

#### Description

SQL injection occurs when user input is not properly sanitized before being used in SQL queries, allowing attackers to execute arbitrary SQL commands.

#### Detection Signs

- Error messages revealing database structure
- Time delays in responses (blind SQL injection)
- Unexpected data retrieval or modification

#### Remediation Steps

**Immediate Actions:**

1. **Use Parameterized Queries**

   ```python
   # ❌ Vulnerable code
   query = f"SELECT * FROM users WHERE email = '{user_email}'"
   cursor.execute(query)

   # ✅ Secure code
   query = "SELECT * FROM users WHERE email = %s"
   cursor.execute(query, (user_email,))
   ```

2. **Input Validation**

   ```python
   import re
   from bleach import clean

   def validate_email(email):
       pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
       if not re.match(pattern, email):
           raise ValueError("Invalid email format")
       return clean(email)
   ```

3. **Database User Permissions**
   ```sql
   -- Create limited database user
   CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
   GRANT SELECT, INSERT, UPDATE ON app_database.users TO 'app_user'@'localhost';
   -- DO NOT GRANT DROP, CREATE, ALTER permissions
   ```

**Long-term Solutions:**

- Implement ORM with built-in SQL injection protection
- Regular security code reviews
- Automated SQL injection testing in CI/CD

### 2. Authentication Bypass

**Risk Level**: CRITICAL  
**CVSS Score**: 9.1

#### Description

Vulnerabilities that allow attackers to bypass authentication mechanisms and gain unauthorized access.

#### Remediation Steps

**JWT Security:**

```python
import jwt
from datetime import datetime, timedelta
import secrets

class SecureJWTManager:
    def __init__(self):
        # Use strong, random secret key
        self.secret_key = secrets.token_urlsafe(64)
        self.algorithm = "HS256"

    def create_token(self, user_id, role="user"):
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "iss": "ai-nutritionist",
            "aud": "api"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token):
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="api",
                issuer="ai-nutritionist"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
```

**Multi-Factor Authentication:**

```python
import pyotp
import qrcode
from io import BytesIO

class MFAManager:
    def setup_mfa(self, user_email):
        secret = pyotp.random_base32()
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name="AI Nutritionist"
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        return secret, qr

    def verify_mfa(self, secret, token):
        totp = pyotp.TOTP(secret)
        return totp.verify(token)
```

### 3. Hardcoded Secrets

**Risk Level**: HIGH  
**CVSS Score**: 8.2

#### Description

Sensitive information like API keys, passwords, or tokens stored directly in source code.

#### Remediation Steps

**Environment Variables:**

```python
import os
from cryptography.fernet import Fernet

class SecretManager:
    def __init__(self):
        self.encryption_key = os.environ.get('ENCRYPTION_KEY')
        if not self.encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        self.fernet = Fernet(self.encryption_key)

    def get_secret(self, key):
        encrypted_value = os.environ.get(key)
        if encrypted_value:
            return self.fernet.decrypt(encrypted_value.encode()).decode()
        return None

    def encrypt_secret(self, value):
        return self.fernet.encrypt(value.encode()).decode()
```

**AWS Secrets Manager Integration:**

```python
import boto3
from botocore.exceptions import ClientError

class AWSSecretsManager:
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client('secretsmanager', region_name=region_name)

    def get_secret(self, secret_name):
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise e

    def create_secret(self, secret_name, secret_value):
        try:
            self.client.create_secret(
                Name=secret_name,
                SecretString=secret_value
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                self.client.update_secret(
                    SecretId=secret_name,
                    SecretString=secret_value
                )
            else:
                raise e
```

## ⚠️ High Severity Vulnerabilities

### 4. Cross-Site Scripting (XSS)

**Risk Level**: HIGH  
**CVSS Score**: 7.5

#### Remediation Steps

**Input Sanitization:**

```python
import bleach
from markupsafe import Markup

# Allowed HTML tags and attributes
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
ALLOWED_ATTRIBUTES = {}

def sanitize_html(content):
    """Sanitize HTML content to prevent XSS."""
    cleaned = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    return Markup(cleaned)

def sanitize_text(text):
    """Sanitize plain text input."""
    return bleach.clean(text, tags=[], strip=True)
```

**Content Security Policy:**

```python
from flask import Flask
from flask_talisman import Talisman

app = Flask(__name__)

# Configure CSP
csp = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline'",
    'style-src': "'self' 'unsafe-inline'",
    'img-src': "'self' data: https:",
    'font-src': "'self'",
    'connect-src': "'self'",
    'frame-ancestors': "'none'"
}

Talisman(app, content_security_policy=csp)
```

### 5. Insecure Direct Object References (IDOR)

**Risk Level**: HIGH  
**CVSS Score**: 7.1

#### Remediation Steps

**Authorization Middleware:**

```python
from functools import wraps
from flask import request, current_user, abort

def require_ownership(resource_type):
    """Decorator to ensure user owns the requested resource."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resource_id = kwargs.get('id') or request.json.get('id')

            # Check resource ownership
            if not verify_resource_ownership(current_user.id, resource_type, resource_id):
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def verify_resource_ownership(user_id, resource_type, resource_id):
    """Verify that user owns the specified resource."""
    query_map = {
        'meal_plan': "SELECT user_id FROM meal_plans WHERE id = %s",
        'nutrition_data': "SELECT user_id FROM nutrition_data WHERE id = %s",
        'user_profile': "SELECT id FROM users WHERE id = %s"
    }

    query = query_map.get(resource_type)
    if not query:
        return False

    result = db.execute(query, (resource_id,))
    return result and result[0]['user_id'] == user_id

# Usage example
@app.route('/meal-plans/<int:id>')
@require_ownership('meal_plan')
def get_meal_plan(id):
    return get_user_meal_plan(id)
```

## 📋 Compliance Remediation

### HIPAA Compliance Issues

#### PHI Encryption at Rest

```python
from cryptography.fernet import Fernet
import boto3

class PHIEncryption:
    def __init__(self):
        # Use AWS KMS for key management
        self.kms_client = boto3.client('kms')
        self.key_id = os.environ.get('PHI_ENCRYPTION_KEY_ID')

    def encrypt_phi(self, data):
        """Encrypt PHI data using AWS KMS."""
        response = self.kms_client.encrypt(
            KeyId=self.key_id,
            Plaintext=data.encode()
        )
        return response['CiphertextBlob']

    def decrypt_phi(self, encrypted_data):
        """Decrypt PHI data using AWS KMS."""
        response = self.kms_client.decrypt(
            CiphertextBlob=encrypted_data
        )
        return response['Plaintext'].decode()
```

#### Audit Logging

```python
import json
from datetime import datetime
import boto3

class HITech_AuditLogger:
    def __init__(self):
        self.cloudwatch = boto3.client('logs')
        self.log_group = '/aws/lambda/phi-audit-logs'

    def log_phi_access(self, user_id, action, resource, phi_type, ip_address):
        """Log PHI access according to HITECH requirements."""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,  # CREATE, READ, UPDATE, DELETE
            'resource': resource,
            'phi_type': phi_type,  # health_data, medical_history, etc.
            'ip_address': ip_address,
            'user_agent': request.headers.get('User-Agent'),
            'outcome': 'SUCCESS',  # or 'FAILURE'
            'event_id': str(uuid.uuid4())
        }

        self.cloudwatch.put_log_events(
            logGroupName=self.log_group,
            logStreamName=f"phi-access-{datetime.utcnow().strftime('%Y-%m-%d')}",
            logEvents=[{
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'message': json.dumps(audit_entry)
            }]
        )
```

### GDPR Compliance Issues

#### Data Subject Rights Implementation

```python
class GDPRDataSubjectRights:
    def __init__(self):
        self.db = get_database_connection()

    def export_user_data(self, user_id):
        """Export all user data (Article 15 - Right of Access)."""
        user_data = {
            'personal_data': self.get_personal_data(user_id),
            'nutrition_data': self.get_nutrition_data(user_id),
            'meal_plans': self.get_meal_plans(user_id),
            'preferences': self.get_preferences(user_id),
            'audit_logs': self.get_user_audit_logs(user_id)
        }
        return user_data

    def delete_user_data(self, user_id, retention_policy=None):
        """Delete user data (Article 17 - Right to Erasure)."""
        # Soft delete with retention for legal requirements
        deletion_timestamp = datetime.utcnow()

        tables_to_delete = [
            'users', 'nutrition_data', 'meal_plans',
            'user_preferences', 'user_sessions'
        ]

        for table in tables_to_delete:
            query = f"UPDATE {table} SET deleted_at = %s WHERE user_id = %s"
            self.db.execute(query, (deletion_timestamp, user_id))

        # Schedule permanent deletion after retention period
        if retention_policy:
            self.schedule_permanent_deletion(user_id, retention_policy)

    def rectify_user_data(self, user_id, corrections):
        """Update incorrect user data (Article 16 - Right to Rectification)."""
        for field, new_value in corrections.items():
            # Log the correction for audit purposes
            self.log_data_rectification(user_id, field, new_value)

            # Update the data
            query = "UPDATE users SET {} = %s WHERE id = %s".format(field)
            self.db.execute(query, (new_value, user_id))
```

## 🔧 Security Configuration

### Web Application Firewall (WAF)

```terraform
resource "aws_wafv2_web_acl" "ai_nutritionist_waf" {
  name  = "ai-nutritionist-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Block common attack patterns
  rule {
    name     = "SQLInjectionRule"
    priority = 1

    action {
      block {}
    }

    statement {
      sqli_match_statement {
        field_to_match {
          body {}
        }
        text_transformation {
          priority = 0
          type     = "URL_DECODE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLInjectionRule"
      sampled_requests_enabled   = true
    }
  }

  # Rate limiting
  rule {
    name     = "RateLimitRule"
    priority = 2

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }
}
```

### Security Headers

```python
from flask import Flask
from flask_talisman import Talisman

app = Flask(__name__)

# Security headers configuration
security_headers = {
    'force_https': True,
    'strict_transport_security': True,
    'strict_transport_security_max_age': 31536000,
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'none'"
    },
    'referrer_policy': 'strict-origin-when-cross-origin',
    'feature_policy': {
        'geolocation': "'none'",
        'microphone': "'none'",
        'camera': "'none'"
    }
}

Talisman(app, **security_headers)
```

## 🚀 Preventive Measures

### Secure Development Lifecycle

#### 1. Pre-commit Hooks

```bash
#!/bin/sh
# .git/hooks/pre-commit

# Run secret scanning
python tests/security/automation/test_security_automation.py

# Run security linting
bandit -r src/ -f json

# Check for hardcoded passwords
grep -r "password.*=" src/ && exit 1

exit 0
```

#### 2. Security Code Review Checklist

- [ ] Input validation implemented for all user inputs
- [ ] Parameterized queries used for database operations
- [ ] Authentication and authorization checks in place
- [ ] Sensitive data encrypted at rest and in transit
- [ ] Error messages don't reveal sensitive information
- [ ] Security headers configured
- [ ] Logging implemented for security events
- [ ] Third-party dependencies updated and scanned

#### 3. Automated Security Testing

```yaml
# .github/workflows/security.yml
name: Security Testing
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Secret Scanning
        run: |
          python tests/security/automation/test_security_automation.py

      - name: Dependency Scanning
        run: |
          safety check

      - name: Static Code Analysis
        run: |
          bandit -r src/ -f json

      - name: Security Tests
        run: |
          python -m pytest tests/security/ -v
```

## 📞 Incident Response

### Security Incident Response Plan

#### 1. Detection and Analysis

- Monitor security alerts and logs
- Validate and classify security incidents
- Determine scope and impact

#### 2. Containment and Eradication

- Isolate affected systems
- Remove malicious components
- Patch vulnerabilities

#### 3. Recovery and Post-Incident

- Restore services securely
- Monitor for residual threats
- Document lessons learned

#### Emergency Contacts

- **Security Team**: security@ai-nutritionist.com
- **Infrastructure Team**: infrastructure@ai-nutritionist.com
- **Legal Team**: legal@ai-nutritionist.com

## 📚 Additional Resources

### Security Training Materials

1. [OWASP Top 10](https://owasp.org/www-project-top-ten/)
2. [SANS Security Training](https://www.sans.org/)
3. [Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)

### Compliance Resources

1. [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/)
2. [GDPR Compliance Guide](https://gdpr.eu/)
3. [PCI DSS Requirements](https://www.pcisecuritystandards.org/)

### Security Tools

1. [OWASP ZAP](https://www.zaproxy.org/)
2. [Bandit](https://bandit.readthedocs.io/)
3. [Safety](https://pypi.org/project/safety/)
4. [Semgrep](https://semgrep.dev/)

---

**⚡ Remember**: Security is an ongoing process, not a one-time implementation. Regular updates, monitoring, and testing are essential for maintaining a strong security posture.
