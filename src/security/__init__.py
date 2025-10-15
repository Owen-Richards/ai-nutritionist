"""
Security module for AI Nutritionist application.

This module provides comprehensive security features following OWASP guidelines:
- Authentication & Authorization
- Input validation & sanitization
- Encryption & secret management
- Rate limiting & abuse prevention
- Security headers & CORS
"""

from .authentication import AuthService, JWTManager, MFAService
from .authorization import RBACService, PermissionManager
from .encryption import EncryptionService, HashingService
from .validation import InputValidator, SecurityValidator
from .headers import SecurityHeadersMiddleware
from .rate_limiting import AdvancedRateLimiter
from .api_keys import APIKeyManager
from .session import SessionManager

__all__ = [
    "AuthService",
    "JWTManager", 
    "MFAService",
    "RBACService",
    "PermissionManager",
    "EncryptionService",
    "HashingService",
    "InputValidator",
    "SecurityValidator",
    "SecurityHeadersMiddleware",
    "AdvancedRateLimiter",
    "APIKeyManager",
    "SessionManager",
]
