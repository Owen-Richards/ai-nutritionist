"""
Input validation and sanitization following OWASP guidelines.

Provides comprehensive input validation for:
- SQL injection prevention
- XSS prevention  
- Command injection prevention
- Path traversal prevention
- Data validation
"""

import re
import os
import html
import bleach
import validators
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, unquote
from pydantic import BaseModel, ValidationError, validator
from fastapi import HTTPException, status

from ..core.exceptions import ValidationError as AppValidationError


class ValidationResult(BaseModel):
    """Validation result."""
    is_valid: bool
    errors: List[str] = []
    sanitized_value: Any = None


class SQLInjectionPatterns:
    """SQL injection detection patterns."""
    
    PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)",
        r"(--|#|/\*|\*/)",
        r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT|ONLOAD|ONERROR)\b)",
        r"(\x00|\x1a)",  # Null bytes
        r"(\b(CHAR|NCHAR|VARCHAR|NVARCHAR)\s*\(\s*\d+\s*\))",
        r"(\b(WAITFOR|DELAY)\b)",
        r"(\b(INFORMATION_SCHEMA|SYS\.)\b)",
    ]
    
    @classmethod
    def is_suspicious(cls, value: str) -> bool:
        """Check if value contains SQL injection patterns."""
        value_upper = value.upper()
        for pattern in cls.PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False


class XSSPatterns:
    """XSS detection patterns."""
    
    PATTERNS = [
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"<iframe\b[^>]*>",
        r"<object\b[^>]*>",
        r"<embed\b[^>]*>",
        r"<applet\b[^>]*>",
        r"<meta\b[^>]*http-equiv",
        r"<link\b[^>]*>",
    ]
    
    @classmethod
    def is_suspicious(cls, value: str) -> bool:
        """Check if value contains XSS patterns."""
        for pattern in cls.PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False


class PathTraversalValidator:
    """Path traversal validation."""
    
    DANGEROUS_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"\.\.",
        r"~",
        r"/etc/",
        r"/proc/",
        r"/sys/",
        r"\\windows\\",
        r"\\system32\\",
    ]
    
    @classmethod
    def is_safe_path(cls, path: str, allowed_base_paths: List[str] = None) -> bool:
        """Check if path is safe from traversal attacks."""
        # Normalize the path
        normalized_path = os.path.normpath(unquote(path))
        
        # Check for dangerous patterns
        path_lower = normalized_path.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, path_lower, re.IGNORECASE):
                return False
        
        # Check if path is within allowed base paths
        if allowed_base_paths:
            resolved_path = Path(normalized_path).resolve()
            for base_path in allowed_base_paths:
                try:
                    resolved_path.relative_to(Path(base_path).resolve())
                    return True
                except ValueError:
                    continue
            return False
        
        return True


class CommandInjectionValidator:
    """Command injection validation."""
    
    DANGEROUS_CHARS = [
        ";", "&", "|", "`", "$", "(", ")", "<", ">", 
        "\\", "'", "\"", "\n", "\r", "\t"
    ]
    
    DANGEROUS_COMMANDS = [
        "rm", "del", "format", "fdisk", "mkfs", "dd",
        "wget", "curl", "nc", "netcat", "telnet", "ssh",
        "python", "perl", "php", "ruby", "bash", "sh",
        "powershell", "cmd", "exec", "eval", "system"
    ]
    
    @classmethod
    def is_safe_command_input(cls, value: str) -> bool:
        """Check if input is safe from command injection."""
        # Check for dangerous characters
        for char in cls.DANGEROUS_CHARS:
            if char in value:
                return False
        
        # Check for dangerous commands
        value_lower = value.lower()
        for cmd in cls.DANGEROUS_COMMANDS:
            if cmd in value_lower:
                return False
        
        return True


class InputValidator:
    """Main input validation service."""
    
    def __init__(self):
        # Configure bleach for HTML sanitization
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
        ]
        self.allowed_attributes = {
            '*': ['class'],
        }
    
    def validate_email(self, email: str) -> ValidationResult:
        """Validate email address."""
        errors = []
        
        if not email:
            errors.append("Email is required")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Basic format validation
        if not validators.email(email):
            errors.append("Invalid email format")
        
        # Length check
        if len(email) > 254:
            errors.append("Email too long")
        
        # Check for SQL injection patterns
        if SQLInjectionPatterns.is_suspicious(email):
            errors.append("Email contains suspicious patterns")
        
        # Sanitize
        sanitized = html.escape(email.strip().lower())
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=sanitized
        )
    
    def validate_password(self, password: str) -> ValidationResult:
        """Validate password strength."""
        errors = []
        
        if not password:
            errors.append("Password is required")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Length requirements
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if len(password) > 128:
            errors.append("Password too long")
        
        # Complexity requirements
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain lowercase letters")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain uppercase letters")
        if not re.search(r"\d", password):
            errors.append("Password must contain numbers")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain special characters")
        
        # Check for common patterns
        if re.search(r"(.)\1{3,}", password):
            errors.append("Password contains too many repeated characters")
        
        # Check for SQL injection
        if SQLInjectionPatterns.is_suspicious(password):
            errors.append("Password contains suspicious patterns")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=password  # Don't sanitize passwords
        )
    
    def validate_text_input(self, text: str, max_length: int = 1000, 
                          allow_html: bool = False) -> ValidationResult:
        """Validate general text input."""
        errors = []
        
        if text is None:
            return ValidationResult(is_valid=True, sanitized_value="")
        
        # Length check
        if len(text) > max_length:
            errors.append(f"Text too long (max {max_length} characters)")
        
        # Check for SQL injection
        if SQLInjectionPatterns.is_suspicious(text):
            errors.append("Text contains suspicious SQL patterns")
        
        # Check for XSS
        if XSSPatterns.is_suspicious(text):
            errors.append("Text contains suspicious script patterns")
        
        # Check for command injection
        if not CommandInjectionValidator.is_safe_command_input(text):
            errors.append("Text contains suspicious command patterns")
        
        # Sanitize
        if allow_html:
            sanitized = bleach.clean(
                text,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                strip=True
            )
        else:
            sanitized = html.escape(text.strip())
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=sanitized
        )
    
    def validate_file_path(self, path: str, allowed_base_paths: List[str] = None) -> ValidationResult:
        """Validate file path for traversal attacks."""
        errors = []
        
        if not path:
            errors.append("Path is required")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Check path traversal
        if not PathTraversalValidator.is_safe_path(path, allowed_base_paths):
            errors.append("Path contains directory traversal patterns")
        
        # Length check
        if len(path) > 260:  # Windows MAX_PATH
            errors.append("Path too long")
        
        # Sanitize
        sanitized = os.path.normpath(path.strip())
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=sanitized
        )
    
    def validate_url(self, url: str) -> ValidationResult:
        """Validate URL."""
        errors = []
        
        if not url:
            errors.append("URL is required")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Basic validation
        if not validators.url(url):
            errors.append("Invalid URL format")
        
        # Parse URL for additional checks
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                errors.append("URL must use HTTP or HTTPS")
            
            # Check for suspicious patterns
            if any(char in url for char in ['<', '>', '"', "'"]):
                errors.append("URL contains suspicious characters")
            
        except Exception:
            errors.append("Failed to parse URL")
        
        # Sanitize
        sanitized = html.escape(url.strip())
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=sanitized
        )
    
    def validate_numeric_input(self, value: Union[str, int, float], 
                             min_value: Optional[float] = None,
                             max_value: Optional[float] = None) -> ValidationResult:
        """Validate numeric input."""
        errors = []
        
        # Convert to number
        try:
            if isinstance(value, str):
                # Check for SQL injection patterns first
                if SQLInjectionPatterns.is_suspicious(value):
                    errors.append("Value contains suspicious patterns")
                    return ValidationResult(is_valid=False, errors=errors)
                
                numeric_value = float(value)
            else:
                numeric_value = float(value)
        except (ValueError, TypeError):
            errors.append("Invalid numeric value")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Range checks
        if min_value is not None and numeric_value < min_value:
            errors.append(f"Value must be at least {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            errors.append(f"Value must be at most {max_value}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=numeric_value
        )
    
    def validate_phone_number(self, phone: str) -> ValidationResult:
        """Validate phone number."""
        errors = []
        
        if not phone:
            errors.append("Phone number is required")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Remove common formatting
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check for SQL injection
        if SQLInjectionPatterns.is_suspicious(phone):
            errors.append("Phone number contains suspicious patterns")
        
        # Basic format validation (international format)
        if not re.match(r'^\+[1-9]\d{1,14}$', cleaned):
            errors.append("Invalid phone number format (use international format)")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=cleaned
        )


class SecurityValidator:
    """High-level security validation."""
    
    def __init__(self):
        self.input_validator = InputValidator()
    
    def validate_api_request(self, data: Dict[str, Any], 
                           schema: Optional[BaseModel] = None) -> ValidationResult:
        """Validate complete API request."""
        errors = []
        sanitized_data = {}
        
        # Validate against Pydantic schema if provided
        if schema:
            try:
                validated = schema(**data)
                sanitized_data = validated.dict()
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    errors.append(f"{field}: {error['msg']}")
                return ValidationResult(is_valid=False, errors=errors)
        
        # Additional security validation
        for key, value in data.items():
            if isinstance(value, str):
                # Check for common injection patterns
                if SQLInjectionPatterns.is_suspicious(value):
                    errors.append(f"Field '{key}' contains suspicious SQL patterns")
                
                if XSSPatterns.is_suspicious(value):
                    errors.append(f"Field '{key}' contains suspicious script patterns")
                
                # Sanitize string values
                if key not in sanitized_data:
                    result = self.input_validator.validate_text_input(value)
                    if not result.is_valid:
                        errors.extend([f"{key}: {error}" for error in result.errors])
                    else:
                        sanitized_data[key] = result.sanitized_value
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=sanitized_data
        )
    
    def validate_file_upload(self, filename: str, content: bytes, 
                           allowed_extensions: List[str] = None,
                           max_size: int = 10485760) -> ValidationResult:  # 10MB default
        """Validate file upload."""
        errors = []
        
        # Validate filename
        path_result = self.input_validator.validate_file_path(filename)
        if not path_result.is_valid:
            errors.extend(path_result.errors)
        
        # Check file extension
        if allowed_extensions:
            ext = Path(filename).suffix.lower()
            if ext not in allowed_extensions:
                errors.append(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")
        
        # Check file size
        if len(content) > max_size:
            errors.append(f"File too large (max {max_size} bytes)")
        
        # Check for suspicious content
        content_str = content[:1024].decode('utf-8', errors='ignore')
        if XSSPatterns.is_suspicious(content_str):
            errors.append("File contains suspicious script content")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value={"filename": path_result.sanitized_value, "content": content}
        )
    
    def create_validation_exception(self, result: ValidationResult) -> HTTPException:
        """Create HTTP exception from validation result."""
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Validation failed",
                "errors": result.errors
            }
        )
