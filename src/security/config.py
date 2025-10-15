"""
Security configuration for AI Nutritionist application.

Centralizes all security settings and provides environment-specific configurations.
"""

import os
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseSettings, Field


class Environment(str, Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class SecurityConfig(BaseSettings):
    """Main security configuration."""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    
    # Authentication settings
    jwt_secret_key: str = Field(default="", env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Password policy
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    
    # Account security
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15
    password_history_count: int = 5
    force_password_change_days: int = 90
    
    # Session management
    session_timeout_minutes: int = 30
    persistent_session_days: int = 30
    max_sessions_per_user: int = 10
    
    # MFA settings
    mfa_issuer_name: str = "AI Nutritionist"
    mfa_backup_codes_count: int = 10
    totp_window: int = 1  # 30-second windows
    
    # API key settings
    api_key_prefix: str = "ak_"
    api_key_length: int = 32
    default_api_key_rate_limit: int = 1000  # per hour
    api_key_max_per_user: int = 10
    
    # Rate limiting
    global_rate_limit_requests: int = 1000
    global_rate_limit_period: int = 3600  # 1 hour
    api_rate_limit_requests: int = 100
    api_rate_limit_period: int = 60  # 1 minute
    auth_rate_limit_requests: int = 10
    auth_rate_limit_period: int = 300  # 5 minutes
    
    # Request limits
    max_request_size_mb: int = 10
    max_upload_size_mb: int = 50
    max_json_payload_mb: int = 1
    
    # CORS settings
    cors_allow_origins: List[str] = Field(default_factory=list)
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    cors_allow_headers: List[str] = Field(default=[
        "Authorization", "Content-Type", "X-Requested-With", "X-User-ID", "X-Request-ID"
    ])
    
    # Security headers
    enable_security_headers: bool = True
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    enable_csp: bool = True
    csp_report_only: bool = False
    
    # Encryption
    encryption_key_rotation_days: int = 90
    use_encryption_at_rest: bool = True
    use_field_level_encryption: bool = True
    
    # Logging and monitoring
    log_security_events: bool = True
    log_failed_auth_attempts: bool = True
    log_api_key_usage: bool = True
    security_alert_threshold: int = 10  # failed attempts before alert
    
    # Database security
    db_connection_ssl: bool = True
    db_query_timeout_seconds: int = 30
    enable_sql_injection_protection: bool = True
    
    # File upload security
    allowed_file_extensions: List[str] = Field(default=[
        ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".csv", ".json"
    ])
    scan_uploads_for_malware: bool = True
    quarantine_suspicious_files: bool = True
    
    # IP restrictions
    enable_ip_whitelist: bool = False
    ip_whitelist: List[str] = Field(default_factory=list)
    enable_ip_blacklist: bool = True
    ip_blacklist: List[str] = Field(default_factory=list)
    
    # Bot protection
    enable_bot_protection: bool = True
    require_user_agent: bool = True
    block_known_bad_user_agents: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class ProductionSecurityConfig(SecurityConfig):
    """Production-specific security configuration."""
    
    environment: Environment = Environment.PRODUCTION
    
    # Stricter settings for production
    access_token_expire_minutes: int = 15
    session_timeout_minutes: int = 15
    max_failed_login_attempts: int = 3
    account_lockout_minutes: int = 30
    
    # Production CORS
    cors_allow_origins: List[str] = [
        "https://ainutritionist.com",
        "https://app.ainutritionist.com",
        "https://api.ainutritionist.com"
    ]
    
    # Enhanced security
    force_password_change_days: int = 60
    password_history_count: int = 10
    encryption_key_rotation_days: int = 30
    
    # Monitoring
    security_alert_threshold: int = 5


class StagingSecurityConfig(SecurityConfig):
    """Staging-specific security configuration."""
    
    environment: Environment = Environment.STAGING
    
    # Staging CORS
    cors_allow_origins: List[str] = [
        "https://staging.ainutritionist.com",
        "https://staging-app.ainutritionist.com",
        "http://localhost:3000",
        "http://localhost:8080"
    ]
    
    # CSP in report-only mode for testing
    csp_report_only: bool = True


class DevelopmentSecurityConfig(SecurityConfig):
    """Development-specific security configuration."""
    
    environment: Environment = Environment.DEVELOPMENT
    
    # Relaxed settings for development
    access_token_expire_minutes: int = 60
    session_timeout_minutes: int = 240  # 4 hours
    max_failed_login_attempts: int = 10
    
    # Development CORS (allow all)
    cors_allow_origins: List[str] = ["*"]
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Disable some security features for easier development
    enable_ip_whitelist: bool = False
    enable_bot_protection: bool = False
    scan_uploads_for_malware: bool = False


def get_security_config() -> SecurityConfig:
    """Get security configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSecurityConfig()
    elif env == "staging":
        return StagingSecurityConfig()
    else:
        return DevelopmentSecurityConfig()


# Security headers configuration
SECURITY_HEADERS_CONFIG = {
    "development": {
        "X-Frame-Options": "SAMEORIGIN",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    },
    "staging": {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    },
    "production": {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0",
    }
}

# CSP configuration
CSP_CONFIG = {
    "development": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "*"],
        "connect-src": ["'self'", "*"],
        "font-src": ["'self'", "data:"],
        "frame-src": ["'self'"],
        "object-src": ["'none'"],
    },
    "staging": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://trusted-cdn.com"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "https://staging.ainutritionist.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "frame-src": ["'none'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
    },
    "production": {
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "https://fonts.googleapis.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "https://api.ainutritionist.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "frame-src": ["'none'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
        "upgrade-insecure-requests": [],
        "block-all-mixed-content": [],
    }
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "endpoints": {
        "/v1/auth/login": {"requests": 5, "period": 300},  # 5 requests per 5 minutes
        "/v1/auth/register": {"requests": 3, "period": 3600},  # 3 requests per hour
        "/v1/auth/refresh": {"requests": 10, "period": 3600},  # 10 requests per hour
        "/v1/plans": {"requests": 100, "period": 3600},  # 100 requests per hour
        "/v1/community": {"requests": 50, "period": 3600},  # 50 requests per hour
        "/v1/gamification": {"requests": 200, "period": 3600},  # 200 requests per hour
    },
    "global": {
        "requests": 1000,
        "period": 3600  # 1000 requests per hour
    }
}

# Input validation patterns
VALIDATION_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "phone": r"^\+[1-9]\d{1,14}$",  # E.164 format
    "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    "alphanumeric": r"^[a-zA-Z0-9]+$",
    "safe_filename": r"^[a-zA-Z0-9._-]+$",
}

# Security event types for logging
SECURITY_EVENT_TYPES = {
    "AUTH_SUCCESS": "authentication_successful",
    "AUTH_FAILED": "authentication_failed",
    "AUTH_LOCKED": "account_locked",
    "AUTH_UNLOCKED": "account_unlocked",
    "PASSWORD_CHANGED": "password_changed",
    "MFA_ENABLED": "mfa_enabled",
    "MFA_DISABLED": "mfa_disabled",
    "SESSION_CREATED": "session_created",
    "SESSION_EXPIRED": "session_expired",
    "SESSION_REVOKED": "session_revoked",
    "API_KEY_CREATED": "api_key_created",
    "API_KEY_REVOKED": "api_key_revoked",
    "RATE_LIMIT_EXCEEDED": "rate_limit_exceeded",
    "SUSPICIOUS_ACTIVITY": "suspicious_activity",
    "SECURITY_VIOLATION": "security_violation",
}
