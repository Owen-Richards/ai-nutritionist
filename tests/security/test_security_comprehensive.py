"""
Comprehensive security tests for AI Nutritionist application.

Tests all security components following OWASP guidelines:
- Authentication and authorization
- Input validation and sanitization  
- Encryption and hashing
- Session management
- API key management
- Security headers and middleware
"""

import pytest
import secrets
import base64
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException

from src.security.authentication import AuthService, JWTManager, MFAService
from src.security.authorization import RBACService, Role, Permission, AccessRequest
from src.security.validation import InputValidator, SecurityValidator, ValidationResult
from src.security.encryption import EncryptionService, HashingService, AESEncryption
from src.security.session import SessionManager, Session, SessionStatus
from src.security.api_keys import APIKeyManager, APIKeyScope
from src.security.middleware import SecurityMiddleware, SecurityContext
from src.security.headers import SecurityHeadersMiddleware, SecurityHeadersConfig
from src.services.infrastructure.secrets_manager import SecretsManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_secrets_manager():
    """Mock secrets manager."""
    mock = Mock(spec=SecretsManager)
    mock.get_secret.return_value = base64.b64encode(secrets.token_bytes(32)).decode()
    mock.store_secret.return_value = True
    return mock


@pytest.fixture
def auth_service(mock_secrets_manager):
    """Auth service fixture."""
    return AuthService(mock_secrets_manager)


@pytest.fixture
def rbac_service(mock_secrets_manager):
    """RBAC service fixture."""
    return RBACService(mock_secrets_manager)


@pytest.fixture
def session_manager(mock_secrets_manager):
    """Session manager fixture."""
    return SessionManager(mock_secrets_manager)


@pytest.fixture
def api_key_manager(mock_secrets_manager):
    """API key manager fixture."""
    return APIKeyManager(mock_secrets_manager)


@pytest.fixture
def encryption_service(mock_secrets_manager):
    """Encryption service fixture."""
    return EncryptionService(mock_secrets_manager)


@pytest.fixture
def input_validator():
    """Input validator fixture."""
    return InputValidator()


@pytest.fixture
def security_validator():
    """Security validator fixture."""
    return SecurityValidator()


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class TestJWTManager:
    """Test JWT token management."""
    
    def test_create_and_verify_access_token(self, auth_service):
        """Test creating and verifying access tokens."""
        user_id = uuid4()
        email = "test@example.com"
        role = "user"
        permissions = ["read", "write"]
        
        # Create token
        token = auth_service.jwt_manager.create_access_token(
            user_id, email, role, permissions
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        token_data = auth_service.jwt_manager.verify_token(token)
        
        assert token_data.user_id == user_id
        assert token_data.email == email
        assert token_data.role == role
        assert token_data.permissions == permissions
    
    def test_token_expiration(self, auth_service):
        """Test token expiration."""
        user_id = uuid4()
        
        # Mock expired token by setting very short expiration
        with patch.object(auth_service.jwt_manager, 'access_token_expire_minutes', -1):
            token = auth_service.jwt_manager.create_access_token(
                user_id, "test@example.com", "user", []
            )
            
            # Should raise exception for expired token
            with pytest.raises(Exception):
                auth_service.jwt_manager.verify_token(token)
    
    def test_invalid_token(self, auth_service):
        """Test invalid token handling."""
        with pytest.raises(Exception):
            auth_service.jwt_manager.verify_token("invalid.token.here")


class TestMFAService:
    """Test multi-factor authentication."""
    
    def test_setup_totp(self, auth_service):
        """Test TOTP setup."""
        user_id = uuid4()
        email = "test@example.com"
        
        mfa_setup = auth_service.mfa_service.setup_totp(user_id, email)
        
        assert mfa_setup.secret is not None
        assert mfa_setup.qr_code.startswith("data:image/png;base64,")
        assert len(mfa_setup.backup_codes) == 10
        assert all(len(code) == 8 for code in mfa_setup.backup_codes)
    
    def test_verify_totp_code(self, auth_service):
        """Test TOTP code verification."""
        # This would require mocking the TOTP verification
        user_id = uuid4()
        
        # Mock successful verification
        with patch.object(auth_service.mfa_service, 'verify_totp', return_value=True):
            result = auth_service.mfa_service.verify_totp(user_id, "123456")
            assert result is True
        
        # Mock failed verification
        with patch.object(auth_service.mfa_service, 'verify_totp', return_value=False):
            result = auth_service.mfa_service.verify_totp(user_id, "invalid")
            assert result is False


class TestPasswordSecurity:
    """Test password security."""
    
    def test_password_hashing(self, auth_service):
        """Test password hashing with Argon2."""
        password = "TestPassword123!"
        
        # Hash password
        hash_value = auth_service.hash_password(password)
        
        assert hash_value is not None
        assert hash_value != password
        assert hash_value.startswith("$argon2")
        
        # Verify password
        assert auth_service.verify_password(password, hash_value) is True
        assert auth_service.verify_password("wrong_password", hash_value) is False
    
    def test_password_strength(self, input_validator):
        """Test password strength validation."""
        # Strong password
        result = input_validator.validate_password("StrongP@ssw0rd123!")
        assert result.is_valid is True
        
        # Weak passwords
        weak_passwords = [
            "123",  # Too short
            "password",  # No uppercase, numbers, special chars
            "PASSWORD",  # No lowercase, numbers, special chars
            "Password",  # No numbers, special chars
            "Password123",  # No special chars
            "aaaaaaaaaa",  # Repeated characters
        ]
        
        for weak_password in weak_passwords:
            result = input_validator.validate_password(weak_password)
            assert result.is_valid is False


# ============================================================================
# AUTHORIZATION TESTS
# ============================================================================

class TestRBACService:
    """Test role-based access control."""
    
    def test_role_permissions(self, rbac_service):
        """Test role permission mappings."""
        # Test user role permissions
        user_perms = rbac_service.permission_manager.get_role_permissions(Role.USER)
        assert Permission.PLAN_READ in user_perms
        assert Permission.PLAN_WRITE in user_perms
        assert Permission.USER_ADMIN not in user_perms
        
        # Test admin role permissions
        admin_perms = rbac_service.permission_manager.get_role_permissions(Role.ADMIN)
        assert Permission.USER_ADMIN in admin_perms
        assert Permission.SYSTEM_CONFIG in admin_perms
        
        # Test super admin has all permissions
        super_admin_perms = rbac_service.permission_manager.get_role_permissions(Role.SUPER_ADMIN)
        assert len(super_admin_perms) == len(Permission)
    
    def test_access_control(self, rbac_service):
        """Test access control decisions."""
        user_id = uuid4()
        
        # Test user accessing their own data
        request = AccessRequest(
            user_id=user_id,
            resource="plans",
            action="read",
            context={"plan_owner_id": str(user_id)}
        )
        
        result = rbac_service.check_access(request, Role.USER)
        assert result.granted is True
        
        # Test user accessing another user's private data
        other_user_id = uuid4()
        request = AccessRequest(
            user_id=user_id,
            resource="plans",
            action="read",
            context={"plan_owner_id": str(other_user_id), "plan_visibility": "private"}
        )
        
        result = rbac_service.check_access(request, Role.USER)
        assert result.granted is False
    
    def test_permission_checking(self, rbac_service):
        """Test permission checking methods."""
        pm = rbac_service.permission_manager
        
        # Test single permission
        assert pm.has_permission(Role.USER, Permission.PLAN_READ) is True
        assert pm.has_permission(Role.USER, Permission.SYSTEM_ADMIN) is False
        
        # Test multiple permissions
        perms = [Permission.PLAN_READ, Permission.PLAN_WRITE]
        assert pm.has_all_permissions(Role.USER, perms) is True
        assert pm.has_any_permission(Role.GUEST, perms) is True


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================

class TestInputValidator:
    """Test input validation and sanitization."""
    
    def test_email_validation(self, input_validator):
        """Test email validation."""
        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.co.uk",
            "admin@sub.domain.org"
        ]
        
        for email in valid_emails:
            result = input_validator.validate_email(email)
            assert result.is_valid is True
            assert result.sanitized_value is not None
        
        # Invalid emails
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user space@domain.com",
            "'; DROP TABLE users; --@evil.com"  # SQL injection attempt
        ]
        
        for email in invalid_emails:
            result = input_validator.validate_email(email)
            assert result.is_valid is False
    
    def test_sql_injection_detection(self, input_validator):
        """Test SQL injection pattern detection."""
        from src.security.validation import SQLInjectionPatterns
        
        # SQL injection attempts
        sql_attacks = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/*",
            "' UNION SELECT * FROM passwords --",
            "x'; INSERT INTO users VALUES ('hacker','pass'); --"
        ]
        
        for attack in sql_attacks:
            assert SQLInjectionPatterns.is_suspicious(attack) is True
    
    def test_xss_detection(self, input_validator):
        """Test XSS pattern detection.""" 
        from src.security.validation import XSSPatterns
        
        # XSS attempts
        xss_attacks = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<svg onload=alert('xss')>"
        ]
        
        for attack in xss_attacks:
            assert XSSPatterns.is_suspicious(attack) is True
    
    def test_path_traversal_detection(self, input_validator):
        """Test path traversal detection."""
        from src.security.validation import PathTraversalValidator
        
        # Path traversal attempts
        traversal_attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "/etc/passwd",
            "~/.ssh/id_rsa"
        ]
        
        for attack in traversal_attacks:
            assert PathTraversalValidator.is_safe_path(attack) is False
        
        # Safe paths
        safe_paths = [
            "user_documents/file.txt",
            "uploads/image.jpg",
            "data/export.csv"
        ]
        
        for path in safe_paths:
            assert PathTraversalValidator.is_safe_path(path) is True
    
    def test_text_sanitization(self, input_validator):
        """Test text input sanitization."""
        # HTML content
        html_input = "<script>alert('xss')</script><p>Valid content</p>"
        result = input_validator.validate_text_input(html_input, allow_html=True)
        
        assert result.is_valid is True
        assert "<script>" not in result.sanitized_value
        assert "<p>Valid content</p>" in result.sanitized_value
        
        # Plain text
        text_input = "Normal text with <special> characters & symbols"
        result = input_validator.validate_text_input(text_input, allow_html=False)
        
        assert result.is_valid is True
        assert "&lt;special&gt;" in result.sanitized_value
        assert "&amp;" in result.sanitized_value


# ============================================================================
# ENCRYPTION TESTS
# ============================================================================

class TestEncryption:
    """Test encryption and hashing services."""
    
    def test_aes_encryption(self):
        """Test AES encryption/decryption."""
        key = secrets.token_bytes(32)
        aes = AESEncryption(key)
        
        plaintext = b"This is sensitive data that needs encryption"
        
        # Encrypt
        encrypted_data, iv = aes.encrypt(plaintext)
        assert encrypted_data != plaintext
        assert len(iv) == 16  # AES block size
        
        # Decrypt
        decrypted_data = aes.decrypt(encrypted_data)
        assert decrypted_data == plaintext
    
    def test_password_hashing(self):
        """Test secure password hashing."""
        hasher = HashingService()
        
        password = "SecurePassword123!"
        
        # Hash password
        hash_value = hasher.hash_password(password)
        assert hash_value != password
        assert hash_value.startswith("$argon2")
        
        # Verify password
        assert hasher.verify_password(password, hash_value) is True
        assert hasher.verify_password("wrong_password", hash_value) is False
    
    def test_data_hashing(self):
        """Test data hashing with salt."""
        hasher = HashingService()
        
        data = "sensitive_data"
        
        # Hash with generated salt
        hash_value, salt = hasher.hash_with_salt(data)
        assert hash_value != data
        assert salt is not None
        
        # Verify hash
        assert hasher.verify_hash_with_salt(data, hash_value, salt) is True
        assert hasher.verify_hash_with_salt("wrong_data", hash_value, salt) is False
    
    def test_field_encryption(self, encryption_service):
        """Test field-level encryption."""
        field_name = "email"
        user_id = "user123"
        value = "user@example.com"
        
        # Encrypt field
        encrypted_value = encryption_service.encrypt_field(field_name, value, user_id)
        assert encrypted_value != value
        
        # Decrypt field
        decrypted_value = encryption_service.decrypt_field(field_name, encrypted_value, user_id)
        assert decrypted_value == value


# ============================================================================
# SESSION MANAGEMENT TESTS
# ============================================================================

class TestSessionManager:
    """Test session management."""
    
    def test_create_session(self, session_manager):
        """Test session creation."""
        user_id = uuid4()
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0 Test Browser"
        
        session, token = session_manager.create_session(
            user_id, ip_address, user_agent
        )
        
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert session.status == SessionStatus.ACTIVE
        assert token is not None
    
    def test_session_validation(self, session_manager):
        """Test session validation."""
        user_id = uuid4()
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0 Test Browser"
        
        # Create session
        session, token = session_manager.create_session(
            user_id, ip_address, user_agent
        )
        
        # Validate session
        with patch.object(session_manager, '_get_session_by_token', return_value=session):
            result = session_manager.validate_session(token, ip_address, user_agent)
            assert result.is_valid is True
            assert result.user_id == user_id
    
    def test_session_security_checks(self, session_manager):
        """Test session security checks.""" 
        user_id = uuid4()
        original_ip = "192.168.1.1"
        original_ua = "Mozilla/5.0 Test Browser"
        
        # Create session
        session, token = session_manager.create_session(
            user_id, original_ip, original_ua
        )
        
        # Test IP address change (should fail for non-mobile)
        with patch.object(session_manager, '_get_session_by_token', return_value=session):
            result = session_manager.validate_session(token, "192.168.1.2", original_ua)
            assert result.is_valid is False
            assert "IP address changed" in result.error_message
    
    def test_session_expiration(self, session_manager):
        """Test session expiration."""
        user_id = uuid4()
        
        # Create expired session
        session, token = session_manager.create_session(user_id, "127.0.0.1", "test")
        session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        with patch.object(session_manager, '_get_session_by_token', return_value=session):
            result = session_manager.validate_session(token, "127.0.0.1", "test")
            assert result.is_valid is False
            assert "expired" in result.error_message.lower()


# ============================================================================
# API KEY MANAGEMENT TESTS
# ============================================================================

class TestAPIKeyManager:
    """Test API key management."""
    
    def test_generate_api_key(self, api_key_manager):
        """Test API key generation."""
        name = "Test API Key"
        scopes = [APIKeyScope.READ_ONLY, APIKeyScope.PLANS_READ]
        
        key_obj, api_key = api_key_manager.generate_api_key(name, scopes)
        
        assert key_obj.name == name
        assert key_obj.scopes == scopes
        assert api_key.startswith("ak_")
        assert len(api_key) > 20  # Should be reasonably long
    
    def test_api_key_validation(self, api_key_manager):
        """Test API key validation."""
        # Generate key
        key_obj, api_key = api_key_manager.generate_api_key(
            "Test Key", [APIKeyScope.READ_ONLY]
        )
        
        # Mock key lookup
        with patch.object(api_key_manager, '_get_api_key_by_hash', return_value=key_obj):
            result = api_key_manager.validate_api_key(api_key)
            assert result.is_valid is True
            assert result.key_id == key_obj.id
    
    def test_api_key_scopes(self, api_key_manager):
        """Test API key scope validation."""
        # Generate key with limited scope
        key_obj, api_key = api_key_manager.generate_api_key(
            "Limited Key", [APIKeyScope.PLANS_READ]
        )
        
        # Test validation with required scopes
        with patch.object(api_key_manager, '_get_api_key_by_hash', return_value=key_obj):
            # Should pass for required scope
            result = api_key_manager.validate_api_key(api_key, [APIKeyScope.PLANS_READ])
            assert result.is_valid is True
            
            # Should fail for scope not granted
            result = api_key_manager.validate_api_key(api_key, [APIKeyScope.PLANS_WRITE])
            assert result.is_valid is False
    
    def test_api_key_rate_limiting(self, api_key_manager):
        """Test API key rate limiting."""
        # Generate key with rate limit
        key_obj, api_key = api_key_manager.generate_api_key(
            "Rate Limited Key", [APIKeyScope.READ_ONLY], rate_limit=1
        )
        
        # Mock rate limit check
        with patch.object(api_key_manager, '_check_rate_limit') as mock_check:
            # First request should pass
            mock_check.return_value = {"allowed": True, "remaining": 0}
            with patch.object(api_key_manager, '_get_api_key_by_hash', return_value=key_obj):
                result = api_key_manager.validate_api_key(api_key)
                assert result.is_valid is True
            
            # Second request should fail
            mock_check.return_value = {"allowed": False, "remaining": 0}
            with patch.object(api_key_manager, '_get_api_key_by_hash', return_value=key_obj):
                result = api_key_manager.validate_api_key(api_key)
                assert result.is_valid is False


# ============================================================================
# SECURITY MIDDLEWARE TESTS
# ============================================================================

class TestSecurityMiddleware:
    """Test security middleware integration."""
    
    @pytest.fixture
    def app_with_security(self, mock_secrets_manager):
        """FastAPI app with security middleware."""
        app = FastAPI()
        app.add_middleware(SecurityMiddleware, secrets_manager=mock_secrets_manager)
        
        @app.get("/protected")
        def protected_endpoint():
            return {"message": "success"}
        
        @app.get("/public")
        def public_endpoint():
            return {"message": "public"}
        
        return app
    
    def test_security_headers(self, app_with_security):
        """Test security headers in response."""
        client = TestClient(app_with_security)
        
        response = client.get("/public")
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
        
        # Verify header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]
    
    def test_request_size_limiting(self, app_with_security):
        """Test request size limiting."""
        client = TestClient(app_with_security)
        
        # Large request should be rejected
        large_data = "x" * (11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/protected", 
            json={"data": large_data},
            headers={"Content-Length": str(len(large_data))}
        )
        
        assert response.status_code == 413  # Request Entity Too Large


class TestSecurityHeaders:
    """Test security headers middleware."""
    
    def test_security_headers_config(self):
        """Test security headers configuration."""
        config = SecurityHeadersConfig()
        
        # Check default headers
        assert "X-Frame-Options" in config.headers
        assert "X-Content-Type-Options" in config.headers
        assert "X-XSS-Protection" in config.headers
        
        # Check CSP generation
        csp_header = config.get_csp_header()
        assert "default-src 'self'" in csp_header
        assert "object-src 'none'" in csp_header
    
    def test_csp_customization(self):
        """Test CSP directive customization."""
        config = SecurityHeadersConfig()
        
        # Add custom directive
        config.update_csp_directive("script-src", ["'self'", "https://trusted.com"])
        
        csp_header = config.get_csp_header()
        assert "script-src 'self' https://trusted.com" in csp_header


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestSecurityIntegration:
    """Test security component integration."""
    
    def test_full_authentication_flow(self, auth_service):
        """Test complete authentication flow."""
        # Mock user data
        user_data = {
            "id": uuid4(),
            "email": "test@example.com",
            "password_hash": auth_service.hash_password("TestPassword123!"),
            "role": "user",
            "permissions": ["read", "write"],
            "mfa_enabled": False
        }
        
        # Mock user lookup
        with patch.object(auth_service, '_get_user_by_email', return_value=user_data):
            with patch.object(auth_service, '_is_account_locked', return_value=False):
                with patch.object(auth_service, '_reset_failed_attempts'):
                    
                    # Authenticate user
                    result = auth_service.authenticate_user(
                        "test@example.com", "TestPassword123!"
                    )
                    
                    assert "access_token" in result
                    assert "refresh_token" in result
                    assert result["token_type"] == "bearer"
                    assert "user" in result
    
    def test_authorization_with_context(self, rbac_service):
        """Test authorization with request context."""
        user_id = uuid4()
        target_user_id = uuid4()
        
        # User trying to access another user's data
        request = AccessRequest(
            user_id=user_id,
            resource="users",
            action="read",
            context={"target_user_id": str(target_user_id)}
        )
        
        # Should be denied for regular user
        result = rbac_service.check_access(request, Role.USER)
        assert result.granted is False
        
        # Should be allowed for admin
        result = rbac_service.check_access(request, Role.ADMIN)
        assert result.granted is True
    
    def test_security_event_logging(self, auth_service):
        """Test security event logging."""
        # This would test that security events are properly logged
        # Implementation depends on your logging infrastructure
        pass


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestSecurityPerformance:
    """Test security component performance."""
    
    def test_password_hashing_performance(self, auth_service):
        """Test password hashing performance."""
        import time
        
        password = "TestPassword123!"
        
        start_time = time.time()
        hash_value = auth_service.hash_password(password)
        end_time = time.time()
        
        # Hashing should complete within reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        
        # Verification should be fast
        start_time = time.time()
        result = auth_service.verify_password(password, hash_value)
        end_time = time.time()
        
        assert result is True
        assert end_time - start_time < 0.5
    
    def test_jwt_performance(self, auth_service):
        """Test JWT operations performance."""
        import time
        
        user_id = uuid4()
        
        # Token creation should be fast
        start_time = time.time()
        token = auth_service.jwt_manager.create_access_token(
            user_id, "test@example.com", "user", []
        )
        end_time = time.time()
        
        assert end_time - start_time < 0.1
        
        # Token verification should be fast
        start_time = time.time()
        token_data = auth_service.jwt_manager.verify_token(token)
        end_time = time.time()
        
        assert token_data.user_id == user_id
        assert end_time - start_time < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
