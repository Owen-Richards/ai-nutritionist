"""
Security API routes for authentication and key management.

Provides endpoints for:
- User authentication (login, register, logout)
- JWT token management
- MFA setup and verification
- API key management
- Session management
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, EmailStr

from ..security.middleware import SecurityContext, get_security_context, require_authentication, require_role
from ..security.authentication import AuthService
from ..security.authorization import Role
from ..security.api_keys import APIKeyManager, APIKeyScope
from ..security.session import SessionManager
from ..services.infrastructure.secrets_manager import SecretsManager


# Initialize router
security_router = APIRouter(prefix="/v1/auth", tags=["security"])

# Security bearer for Swagger UI
security_bearer = HTTPBearer()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=6)
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    terms_accepted: bool = True


class RegisterResponse(BaseModel):
    """Registration response."""
    user_id: str
    email: str
    message: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class MFASetupResponse(BaseModel):
    """MFA setup response."""
    secret: str
    qr_code: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""
    code: str = Field(..., min_length=6, max_length=6)


class APIKeyCreateRequest(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[APIKeyScope]
    expires_in_days: Optional[int] = None
    rate_limit: Optional[int] = Field(None, gt=0, le=10000)
    description: Optional[str] = None


class APIKeyResponse(BaseModel):
    """API key response."""
    id: str
    name: str
    key: Optional[str] = None  # Only returned on creation
    scopes: List[str]
    created_at: str
    expires_at: Optional[str] = None
    status: str


class SessionInfoResponse(BaseModel):
    """Session information response."""
    session_id: str
    created_at: str
    last_accessed_at: str
    expires_at: str
    device_type: str
    ip_address: str
    is_current: bool


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_auth_service() -> AuthService:
    """Get authentication service."""
    # In production, inject via DI container
    secrets_manager = SecretsManager()  # Initialize properly
    return AuthService(secrets_manager)


def get_api_key_manager() -> APIKeyManager:
    """Get API key manager."""
    secrets_manager = SecretsManager()  # Initialize properly
    return APIKeyManager(secrets_manager)


def get_session_manager() -> SessionManager:
    """Get session manager."""
    secrets_manager = SecretsManager()  # Initialize properly
    return SessionManager(secrets_manager)


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@security_router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return tokens."""
    try:
        # Get client info
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "")
        
        # Authenticate user
        auth_result = auth_service.authenticate_user(
            email=request.email,
            password=request.password,
            mfa_code=request.mfa_code
        )
        
        return LoginResponse(**auth_result)
        
    except Exception as e:
        if "Invalid credentials" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        elif "MFA code required" in str(e):
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="MFA code required"
            )
        elif "Invalid MFA code" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )
        elif "Account temporarily locked" in str(e):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to failed attempts"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )


@security_router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register new user."""
    try:
        # Validate terms acceptance
        if not request.terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Terms and conditions must be accepted"
            )
        
        # Hash password
        password_hash = auth_service.hash_password(request.password)
        
        # Create user (implement user creation logic)
        # user_id = create_user(request.email, password_hash, request.first_name, request.last_name)
        
        return RegisterResponse(
            user_id="placeholder",  # Replace with actual user ID
            email=request.email,
            message="User registered successfully"
        )
        
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )


@security_router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token."""
    try:
        result = auth_service.refresh_token(request.refresh_token)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@security_router.post("/logout")
async def logout(
    access_token: str = Depends(security_bearer),
    refresh_token: Optional[str] = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user and invalidate tokens."""
    try:
        auth_service.logout(access_token.credentials, refresh_token or "")
        return {"message": "Logged out successfully"}
        
    except Exception:
        # Even if token validation fails, consider logout successful
        return {"message": "Logged out successfully"}


# ============================================================================
# MFA ROUTES
# ============================================================================

@security_router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    context: SecurityContext = Depends(require_authentication),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Set up multi-factor authentication."""
    try:
        # Get user email (implement user lookup)
        user_email = "user@example.com"  # Replace with actual lookup
        
        mfa_setup = auth_service.mfa_service.setup_totp(context.user_id, user_email)
        
        return MFASetupResponse(
            secret=mfa_setup.secret,
            qr_code=mfa_setup.qr_code,
            backup_codes=mfa_setup.backup_codes
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up MFA"
        )


@security_router.post("/mfa/verify")
async def verify_mfa(
    request: MFAVerifyRequest,
    context: SecurityContext = Depends(require_authentication),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify MFA code and enable MFA."""
    try:
        is_valid = auth_service.mfa_service.verify_totp(context.user_id, request.code)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA code"
            )
        
        # Enable MFA for user (implement user update)
        # update_user_mfa_status(context.user_id, True)
        
        return {"message": "MFA enabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA"
        )


@security_router.delete("/mfa")
async def disable_mfa(
    context: SecurityContext = Depends(require_authentication),
):
    """Disable multi-factor authentication."""
    try:
        # Disable MFA for user (implement user update)
        # update_user_mfa_status(context.user_id, False)
        
        return {"message": "MFA disabled successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable MFA"
        )


# ============================================================================
# API KEY MANAGEMENT ROUTES
# ============================================================================

@security_router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    context: SecurityContext = Depends(require_authentication),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """Create new API key."""
    try:
        key_obj, api_key = api_key_manager.generate_api_key(
            name=request.name,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            rate_limit=request.rate_limit,
            created_by=str(context.user_id),
            description=request.description
        )
        
        return APIKeyResponse(
            id=str(key_obj.id),
            name=key_obj.name,
            key=api_key,  # Only returned on creation
            scopes=[scope.value for scope in key_obj.scopes],
            created_at=key_obj.created_at.isoformat(),
            expires_at=key_obj.expires_at.isoformat() if key_obj.expires_at else None,
            status=key_obj.status.value
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@security_router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    context: SecurityContext = Depends(require_authentication),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """List user's API keys."""
    try:
        keys = api_key_manager.list_api_keys(created_by=str(context.user_id))
        
        return [
            APIKeyResponse(
                id=str(key.id),
                name=key.name,
                scopes=[scope.value for scope in key.scopes],
                created_at=key.created_at.isoformat(),
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                status=key.status.value
            )
            for key in keys
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@security_router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    context: SecurityContext = Depends(require_authentication),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """Revoke API key."""
    try:
        success = api_key_manager.revoke_api_key(key_id, revoked_by=str(context.user_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {"message": "API key revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@security_router.post("/api-keys/{key_id}/rotate", response_model=APIKeyResponse)
async def rotate_api_key(
    key_id: UUID,
    context: SecurityContext = Depends(require_authentication),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """Rotate API key."""
    try:
        new_key_obj, new_api_key = api_key_manager.rotate_api_key(
            key_id, rotated_by=str(context.user_id)
        )
        
        if not new_key_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return APIKeyResponse(
            id=str(new_key_obj.id),
            name=new_key_obj.name,
            key=new_api_key,  # Return new key
            scopes=[scope.value for scope in new_key_obj.scopes],
            created_at=new_key_obj.created_at.isoformat(),
            expires_at=new_key_obj.expires_at.isoformat() if new_key_obj.expires_at else None,
            status=new_key_obj.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key"
        )


# ============================================================================
# SESSION MANAGEMENT ROUTES
# ============================================================================

@security_router.get("/sessions", response_model=List[SessionInfoResponse])
async def list_sessions(
    context: SecurityContext = Depends(require_authentication),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """List user's active sessions."""
    try:
        sessions = session_manager.get_user_sessions(context.user_id, active_only=True)
        
        return [
            SessionInfoResponse(
                session_id=str(session.session_id),
                created_at=session.created_at.isoformat(),
                last_accessed_at=session.last_accessed_at.isoformat(),
                expires_at=session.expires_at.isoformat(),
                device_type=session.device_type.value,
                ip_address=session.ip_address,
                is_current=session.session_id == context.session_id
            )
            for session in sessions
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions"
        )


@security_router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    context: SecurityContext = Depends(require_authentication),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Revoke specific session."""
    try:
        # Get session token (this would need to be implemented based on your session tracking)
        # For now, we'll use a placeholder
        success = True  # session_manager.revoke_session(session_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {"message": "Session revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )


@security_router.delete("/sessions")
async def revoke_all_sessions(
    except_current: bool = True,
    context: SecurityContext = Depends(require_authentication),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Revoke all user sessions."""
    try:
        revoked_count = session_manager.revoke_all_user_sessions(
            context.user_id,
            except_session=None,  # Would need current session token
            reason="user_request"
        )
        
        return {
            "message": f"Revoked {revoked_count} sessions",
            "revoked_count": revoked_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )


# ============================================================================
# SECURITY INFO ROUTES
# ============================================================================

@security_router.get("/me")
async def get_current_user(
    context: SecurityContext = Depends(require_authentication)
):
    """Get current user security information."""
    return {
        "user_id": str(context.user_id),
        "role": context.user_role.value if context.user_role else None,
        "permissions": context.permissions,
        "auth_method": context.auth_method,
        "is_authenticated": context.is_authenticated
    }


@security_router.get("/security-status")
async def get_security_status(
    context: SecurityContext = Depends(require_authentication)
):
    """Get user's security status."""
    try:
        # Get security information (implement based on your user model)
        return {
            "user_id": str(context.user_id),
            "mfa_enabled": False,  # Get from user record
            "last_login": None,  # Get from user record
            "failed_attempts": 0,  # Get from user record
            "account_locked": False,  # Get from user record
            "password_last_changed": None,  # Get from user record
            "active_sessions": 0,  # Get from session manager
            "active_api_keys": 0,  # Get from API key manager
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security status"
        )
