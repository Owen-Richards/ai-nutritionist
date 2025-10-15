"""
Security middleware integration for FastAPI application.

Provides comprehensive security middleware that integrates:
- Authentication and authorization
- Input validation and sanitization
- Rate limiting
- Security headers
- Session management
"""

import time
import json
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .authentication import AuthService, TokenData, AuthenticationError
from .authorization import RBACService, AccessRequest, Role
from .validation import SecurityValidator, ValidationResult
from .headers import SecurityMiddlewareManager
from .session import SessionManager
from .api_keys import APIKeyManager, APIKeyScope
from ..services.infrastructure.secrets_manager import SecretsManager


class SecurityContext:
    """Security context for the current request."""
    
    def __init__(self):
        self.user_id: Optional[UUID] = None
        self.user_role: Optional[Role] = None
        self.permissions: List[str] = []
        self.session_id: Optional[UUID] = None
        self.api_key_id: Optional[UUID] = None
        self.is_authenticated: bool = False
        self.auth_method: Optional[str] = None  # "jwt", "api_key", "session"
        self.request_id: str = ""
        self.ip_address: str = ""
        self.user_agent: str = ""


class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware."""
    
    def __init__(self, app, secrets_manager: SecretsManager, environment: str = "development"):
        super().__init__(app)
        self.secrets_manager = secrets_manager
        self.environment = environment
        
        # Initialize security services
        self.auth_service = AuthService(secrets_manager)
        self.rbac_service = RBACService(secrets_manager)
        self.session_manager = SessionManager(secrets_manager)
        self.api_key_manager = APIKeyManager(secrets_manager)
        self.validator = SecurityValidator()
        
        # Initialize middleware manager
        self.middleware_manager = SecurityMiddlewareManager(environment)
        
        # Security configuration
        self.rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        
        # Paths that don't require authentication
        self.public_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/v1/auth/login",
            "/v1/auth/register",
            "/v1/auth/refresh"
        ]
        
        # Paths that require API key authentication
        self.api_key_paths = [
            "/v1/api/",
            "/v1/webhooks/"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Main security middleware dispatch."""
        start_time = time.time()
        
        try:
            # Initialize security context
            security_context = SecurityContext()
            security_context.request_id = self._generate_request_id()
            security_context.ip_address = self._get_client_ip(request)
            security_context.user_agent = request.headers.get("user-agent", "")
            
            # Store context in request state
            request.state.security_context = security_context
            
            # Validate request
            validation_result = await self._validate_request(request)
            if not validation_result.is_valid:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Request validation failed", "errors": validation_result.errors}
                )
            
            # Check authentication if required
            auth_result = await self._check_authentication(request)
            if auth_result["error"]:
                return JSONResponse(
                    status_code=auth_result["status_code"],
                    content={"detail": auth_result["error"]}
                )
            
            # Update security context with auth info
            if auth_result["user_id"]:
                security_context.user_id = auth_result["user_id"]
                security_context.user_role = auth_result["role"]
                security_context.permissions = auth_result["permissions"]
                security_context.is_authenticated = True
                security_context.auth_method = auth_result["auth_method"]
            
            # Check authorization
            if security_context.is_authenticated:
                authz_result = await self._check_authorization(request, security_context)
                if not authz_result["allowed"]:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": authz_result["reason"]}
                    )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response = self._add_security_headers(response)
            
            # Log security event
            processing_time = time.time() - start_time
            await self._log_security_event(request, security_context, response, processing_time)
            
            return response
            
        except Exception as e:
            # Log security error
            await self._log_security_error(request, str(e))
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal security error"}
            )
    
    async def _validate_request(self, request: Request) -> ValidationResult:
        """Validate incoming request."""
        errors = []
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10485760:  # 10MB
            errors.append("Request too large")
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type:
                errors.append("Content-Type header required")
            elif not any(ct in content_type for ct in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]):
                errors.append("Unsupported Content-Type")
        
        # Validate headers
        user_agent = request.headers.get("user-agent", "")
        if not user_agent:
            errors.append("User-Agent header required")
        
        # Check for suspicious patterns in headers
        for header_name, header_value in request.headers.items():
            if isinstance(header_value, str):
                header_validation = self.validator.input_validator.validate_text_input(
                    header_value, max_length=1000, allow_html=False
                )
                if not header_validation.is_valid:
                    errors.extend([f"Header {header_name}: {error}" for error in header_validation.errors])
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    async def _check_authentication(self, request: Request) -> Dict[str, Any]:
        """Check request authentication."""
        path = request.url.path
        
        # Skip authentication for public paths
        if any(public_path in path for public_path in self.public_paths):
            return {"error": None, "user_id": None, "role": None, "permissions": [], "auth_method": None}
        
        # Check for API key authentication
        if any(api_path in path for api_path in self.api_key_paths):
            return await self._authenticate_api_key(request)
        
        # Check for JWT authentication
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return await self._authenticate_jwt(auth_header)
        
        # Check for session authentication
        session_token = request.cookies.get("session_token")
        if session_token:
            return await self._authenticate_session(request, session_token)
        
        # No authentication provided but required
        return {
            "error": "Authentication required",
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "user_id": None,
            "role": None,
            "permissions": [],
            "auth_method": None
        }
    
    async def _authenticate_jwt(self, auth_header: str) -> Dict[str, Any]:
        """Authenticate using JWT token."""
        try:
            token = auth_header.split(" ")[1]
            token_data = self.auth_service.jwt_manager.verify_token(token)
            
            # Check if token is blacklisted
            if self.auth_service.jwt_manager.is_token_blacklisted(token_data.jti):
                return {
                    "error": "Token is blacklisted",
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "user_id": None,
                    "role": None,
                    "permissions": [],
                    "auth_method": None
                }
            
            return {
                "error": None,
                "user_id": token_data.user_id,
                "role": Role(token_data.role),
                "permissions": token_data.permissions,
                "auth_method": "jwt"
            }
            
        except AuthenticationError as e:
            return {
                "error": str(e),
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "user_id": None,
                "role": None,
                "permissions": [],
                "auth_method": None
            }
    
    async def _authenticate_session(self, request: Request, session_token: str) -> Dict[str, Any]:
        """Authenticate using session token."""
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        validation_result = self.session_manager.validate_session(
            session_token, ip_address, user_agent
        )
        
        if not validation_result.is_valid:
            return {
                "error": validation_result.error_message,
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "user_id": None,
                "role": None,
                "permissions": [],
                "auth_method": None
            }
        
        # Get user role and permissions (implement user lookup)
        user_role = Role.USER  # Default role
        user_permissions = self.rbac_service.get_user_permissions(user_role)
        
        return {
            "error": None,
            "user_id": validation_result.user_id,
            "role": user_role,
            "permissions": user_permissions,
            "auth_method": "session"
        }
    
    async def _authenticate_api_key(self, request: Request) -> Dict[str, Any]:
        """Authenticate using API key."""
        # Check header
        api_key = request.headers.get("X-API-Key")
        
        # Check query parameter (less secure, discouraged)
        if not api_key:
            api_key = request.query_params.get("api_key")
        
        if not api_key:
            return {
                "error": "API key required",
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "user_id": None,
                "role": None,
                "permissions": [],
                "auth_method": None
            }
        
        # Validate API key
        validation_result = self.api_key_manager.validate_api_key(api_key)
        
        if not validation_result.is_valid:
            return {
                "error": validation_result.error_message,
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "user_id": None,
                "role": None,
                "permissions": [],
                "auth_method": None
            }
        
        # Convert API key scopes to role
        user_role = self._api_scopes_to_role(validation_result.scopes)
        user_permissions = [scope.value for scope in validation_result.scopes]
        
        return {
            "error": None,
            "user_id": None,  # API keys don't have user IDs
            "role": user_role,
            "permissions": user_permissions,
            "auth_method": "api_key"
        }
    
    async def _check_authorization(self, request: Request, context: SecurityContext) -> Dict[str, Any]:
        """Check request authorization."""
        # Parse resource and action from request
        resource, action = self._parse_resource_action(request)
        
        # Create access request
        access_request = AccessRequest(
            user_id=context.user_id or UUID("00000000-0000-0000-0000-000000000000"),
            resource=resource,
            action=action,
            context=self._build_access_context(request)
        )
        
        # Check access
        access_result = self.rbac_service.check_access(access_request, context.user_role)
        
        return {
            "allowed": access_result.granted,
            "reason": access_result.reason
        }
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        # Get headers from middleware manager
        headers_config = self.middleware_manager.security_headers_config
        
        for header_name, header_value in headers_config.headers.items():
            response.headers[header_name] = header_value
        
        # Add CSP header
        response.headers["Content-Security-Policy"] = headers_config.get_csp_header()
        
        return response
    
    def _parse_resource_action(self, request: Request) -> tuple[str, str]:
        """Parse resource and action from request path and method."""
        path = request.url.path
        method = request.method.lower()
        
        # Map HTTP methods to actions
        method_action_map = {
            "get": "read",
            "post": "write",
            "put": "write",
            "patch": "write",
            "delete": "delete"
        }
        
        action = method_action_map.get(method, "read")
        
        # Parse resource from path
        if "/v1/plans" in path:
            return "plans", action
        elif "/v1/community" in path:
            return "community", action
        elif "/v1/users" in path:
            return "users", action
        elif "/v1/analytics" in path:
            return "analytics", action
        elif "/v1/billing" in path:
            return "billing", action
        else:
            return "general", action
    
    def _build_access_context(self, request: Request) -> Dict[str, Any]:
        """Build context for access control decisions."""
        context = {}
        
        # Add query parameters that might affect access
        if "user_id" in request.query_params:
            context["target_user_id"] = request.query_params["user_id"]
        
        # Add path parameters
        path_parts = request.url.path.split("/")
        if len(path_parts) > 3:
            context["resource_id"] = path_parts[3]
        
        return context
    
    def _api_scopes_to_role(self, scopes: List[APIKeyScope]) -> Role:
        """Convert API key scopes to user role."""
        if APIKeyScope.ADMIN in scopes:
            return Role.ADMIN
        elif any(scope.value.endswith(":write") for scope in scopes):
            return Role.PREMIUM_USER
        else:
            return Role.USER
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return getattr(request.client, "host", "unknown")
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import secrets
        return secrets.token_urlsafe(16)
    
    async def _log_security_event(self, request: Request, context: SecurityContext,
                                response: Response, processing_time: float):
        """Log security event."""
        event = {
            "timestamp": time.time(),
            "request_id": context.request_id,
            "method": request.method,
            "path": request.url.path,
            "user_id": str(context.user_id) if context.user_id else None,
            "ip_address": context.ip_address,
            "user_agent": context.user_agent,
            "auth_method": context.auth_method,
            "status_code": response.status_code,
            "processing_time": processing_time
        }
        
        # In production, send to logging service
        # logger.info("Security event", extra=event)
    
    async def _log_security_error(self, request: Request, error: str):
        """Log security error."""
        error_event = {
            "timestamp": time.time(),
            "method": request.method,
            "path": request.url.path,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "error": error
        }
        
        # In production, send to logging service
        # logger.error("Security error", extra=error_event)


# FastAPI dependencies for authentication and authorization

def get_security_context(request: Request) -> SecurityContext:
    """Get security context from request."""
    return getattr(request.state, "security_context", SecurityContext())


def require_authentication(context: SecurityContext = Depends(get_security_context)) -> SecurityContext:
    """Require authentication."""
    if not context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return context


def require_role(required_role: Role):
    """Require specific role."""
    def role_checker(context: SecurityContext = Depends(require_authentication)) -> SecurityContext:
        if context.user_role != required_role and context.user_role != Role.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required"
            )
        return context
    return role_checker


def require_permission(required_permission: str):
    """Require specific permission."""
    def permission_checker(context: SecurityContext = Depends(require_authentication)) -> SecurityContext:
        if required_permission not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        return context
    return permission_checker
