"""
Security headers middleware for OWASP protection.

Implements comprehensive security headers:
- CORS configuration
- Content Security Policy (CSP)
- HTTP security headers
- Request size limiting
"""

import json
from typing import Dict, List, Optional, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersConfig:
    """Security headers configuration."""
    
    def __init__(self):
        # Default security headers
        self.headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # Strict Transport Security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Cache control for sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        
        # Content Security Policy
        self.csp_directives = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'", "https://trusted-cdn.com"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:", "https:"],
            "connect-src": ["'self'", "https://api.ainutritionist.com"],
            "frame-src": ["'none'"],
            "object-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
        }
    
    def get_csp_header(self) -> str:
        """Generate CSP header value."""
        directives = []
        for directive, sources in self.csp_directives.items():
            if sources:
                directives.append(f"{directive} {' '.join(sources)}")
            else:
                directives.append(directive)
        return "; ".join(directives)
    
    def update_csp_directive(self, directive: str, sources: List[str]):
        """Update CSP directive."""
        self.csp_directives[directive] = sources
    
    def add_csp_source(self, directive: str, source: str):
        """Add source to CSP directive."""
        if directive not in self.csp_directives:
            self.csp_directives[directive] = []
        if source not in self.csp_directives[directive]:
            self.csp_directives[directive].append(source)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""
    
    def __init__(self, app, config: Optional[SecurityHeadersConfig] = None):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()
        self.max_request_size = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next):
        """Apply security headers to all responses."""
        # Check request size
        if hasattr(request, "headers"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request entity too large"}
                )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.config.headers.items():
            response.headers[header_name] = header_value
        
        # Add CSP header
        response.headers["Content-Security-Policy"] = self.config.get_csp_header()
        
        # Add security headers based on response type
        if self._is_html_response(response):
            response.headers["X-Frame-Options"] = "DENY"
        elif self._is_api_response(response):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
        
        return response
    
    def _is_html_response(self, response: Response) -> bool:
        """Check if response is HTML."""
        content_type = response.headers.get("content-type", "")
        return "text/html" in content_type
    
    def _is_api_response(self, response: Response) -> bool:
        """Check if response is API JSON."""
        content_type = response.headers.get("content-type", "")
        return "application/json" in content_type


class CORSConfig:
    """CORS configuration for security."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        
        if environment == "production":
            self.allowed_origins = [
                "https://ainutritionist.com",
                "https://app.ainutritionist.com",
                "https://api.ainutritionist.com"
            ]
            self.allow_credentials = True
            self.allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            self.allow_headers = [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "X-User-ID",
                "X-Request-ID"
            ]
        elif environment == "staging":
            self.allowed_origins = [
                "https://staging.ainutritionist.com",
                "https://staging-app.ainutritionist.com",
                "http://localhost:3000",
                "http://localhost:8080"
            ]
            self.allow_credentials = True
            self.allow_methods = ["*"]
            self.allow_headers = ["*"]
        else:  # development
            self.allowed_origins = ["*"]
            self.allow_credentials = True
            self.allow_methods = ["*"]
            self.allow_headers = ["*"]
        
        # Headers to expose to client
        self.expose_headers = [
            "X-Total-Count",
            "X-Page-Count",
            "X-Rate-Limit-Remaining",
            "X-Rate-Limit-Reset"
        ]
    
    def get_cors_middleware(self):
        """Get configured CORS middleware."""
        return CORSMiddleware(
            allow_origins=self.allowed_origins,
            allow_credentials=self.allow_credentials,
            allow_methods=self.allow_methods,
            allow_headers=self.allow_headers,
            expose_headers=self.expose_headers
        )


class RequestSizeLimiter:
    """Request size limiting middleware."""
    
    def __init__(self, max_size: int = 10485760):  # 10MB default
        self.max_size = max_size
    
    def __call__(self, request: Request) -> Optional[HTTPException]:
        """Check request size."""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request entity too large. Maximum size: {self.max_size} bytes"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header"
                )
        
        return None


class SecurityMiddlewareManager:
    """Manager for all security middleware."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.security_headers_config = SecurityHeadersConfig()
        self.cors_config = CORSConfig(environment)
        self.request_limiter = RequestSizeLimiter()
    
    def configure_security_headers(self, custom_headers: Dict[str, str] = None,
                                 custom_csp: Dict[str, List[str]] = None):
        """Configure custom security headers."""
        if custom_headers:
            self.security_headers_config.headers.update(custom_headers)
        
        if custom_csp:
            for directive, sources in custom_csp.items():
                self.security_headers_config.update_csp_directive(directive, sources)
    
    def get_security_headers_middleware(self):
        """Get security headers middleware."""
        return SecurityHeadersMiddleware(None, self.security_headers_config)
    
    def get_cors_middleware(self):
        """Get CORS middleware."""
        return self.cors_config.get_cors_middleware()
    
    def configure_for_api(self):
        """Configure for API endpoints."""
        # Stricter CSP for API
        api_csp = {
            "default-src": ["'none'"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'none'"],
            "form-action": ["'none'"],
        }
        
        for directive, sources in api_csp.items():
            self.security_headers_config.update_csp_directive(directive, sources)
        
        # API-specific headers
        api_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
        
        self.security_headers_config.headers.update(api_headers)
    
    def configure_for_widget(self):
        """Configure for widget endpoints."""
        # More permissive for widgets
        widget_csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "connect-src": ["'self'", "https://api.ainutritionist.com"],
            "frame-ancestors": ["*"],  # Allow embedding in widgets
        }
        
        for directive, sources in widget_csp.items():
            self.security_headers_config.update_csp_directive(directive, sources)
        
        # Widget-specific headers
        widget_headers = {
            "X-Frame-Options": "SAMEORIGIN",  # Allow same-origin framing
            "Cache-Control": "public, max-age=300",  # 5 minute cache
        }
        
        self.security_headers_config.headers.update(widget_headers)
    
    def get_security_info(self) -> Dict[str, Any]:
        """Get current security configuration info."""
        return {
            "environment": self.environment,
            "cors_origins": self.cors_config.allowed_origins,
            "csp_policy": self.security_headers_config.get_csp_header(),
            "security_headers": list(self.security_headers_config.headers.keys()),
            "max_request_size": self.request_limiter.max_size
        }
