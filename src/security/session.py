"""
Session management for secure user sessions.

Provides comprehensive session management:
- Secure session creation and validation
- Session storage and cleanup
- Device tracking and management
- Session hijacking prevention
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel

from ..services.infrastructure.secrets_manager import SecretsManager


class SessionStatus(str, Enum):
    """Session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


class DeviceType(str, Enum):
    """Device types."""
    WEB = "web"
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    API = "api"
    UNKNOWN = "unknown"


class Session(BaseModel):
    """Session model."""
    session_id: UUID
    user_id: UUID
    session_token: str  # Hashed token for storage
    status: SessionStatus
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    device_type: DeviceType
    device_fingerprint: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    is_persistent: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class SessionActivity(BaseModel):
    """Session activity tracking."""
    session_id: UUID
    activity_type: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionValidationResult(BaseModel):
    """Session validation result."""
    is_valid: bool
    session: Optional[Session] = None
    user_id: Optional[UUID] = None
    error_message: Optional[str] = None
    requires_reauth: bool = False


class SessionManager:
    """Session management service."""
    
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
        self.session_timeout_minutes = 30
        self.persistent_session_days = 30
        self.max_sessions_per_user = 10
        
        # In-memory cache for active sessions (use Redis in production)
        self._session_cache: Dict[str, Session] = {}
        self._user_sessions: Dict[UUID, List[str]] = {}
        self._activity_log: List[SessionActivity] = []
    
    def create_session(self, user_id: UUID, ip_address: str, user_agent: str,
                      is_persistent: bool = False,
                      device_fingerprint: Optional[str] = None,
                      location: Optional[Dict[str, Any]] = None) -> tuple[Session, str]:
        """Create new user session."""
        # Generate secure session token
        session_token = self._generate_session_token()
        session_token_hash = self._hash_token(session_token)
        
        # Determine device type
        device_type = self._detect_device_type(user_agent)
        
        # Calculate expiration
        if is_persistent:
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.persistent_session_days)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.session_timeout_minutes)
        
        # Create session object
        session = Session(
            session_id=uuid4(),
            user_id=user_id,
            session_token=session_token_hash,
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            last_accessed_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            device_fingerprint=device_fingerprint,
            location=location,
            is_persistent=is_persistent
        )
        
        # Check session limits
        self._enforce_session_limits(user_id)
        
        # Store session
        self._store_session(session)
        
        # Add to caches
        self._session_cache[session_token_hash] = session
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_token_hash)
        
        # Log session creation
        self._log_session_activity(
            session.session_id,
            "session_created",
            ip_address,
            user_agent,
            metadata={"device_type": device_type.value}
        )
        
        return session, session_token
    
    def validate_session(self, session_token: str, ip_address: str,
                        user_agent: str) -> SessionValidationResult:
        """Validate session token."""
        try:
            # Hash token for lookup
            token_hash = self._hash_token(session_token)
            
            # Get session from cache or database
            session = self._session_cache.get(token_hash)
            if not session:
                session = self._get_session_by_token(token_hash)
                if session:
                    self._session_cache[token_hash] = session
            
            if not session:
                return SessionValidationResult(
                    is_valid=False,
                    error_message="Invalid session token"
                )
            
            # Check session status
            if session.status != SessionStatus.ACTIVE:
                return SessionValidationResult(
                    is_valid=False,
                    error_message=f"Session is {session.status.value}"
                )
            
            # Check expiration
            if datetime.now(timezone.utc) > session.expires_at:
                self._expire_session(session)
                return SessionValidationResult(
                    is_valid=False,
                    error_message="Session has expired"
                )
            
            # Security checks
            security_result = self._perform_security_checks(session, ip_address, user_agent)
            if not security_result["is_secure"]:
                return SessionValidationResult(
                    is_valid=False,
                    error_message=security_result["reason"],
                    requires_reauth=security_result.get("requires_reauth", False)
                )
            
            # Update session activity
            self._update_session_activity(session, ip_address, user_agent)
            
            return SessionValidationResult(
                is_valid=True,
                session=session,
                user_id=session.user_id
            )
            
        except Exception as e:
            return SessionValidationResult(
                is_valid=False,
                error_message=f"Session validation error: {str(e)}"
            )
    
    def refresh_session(self, session_token: str) -> Optional[datetime]:
        """Refresh session expiration."""
        token_hash = self._hash_token(session_token)
        session = self._session_cache.get(token_hash)
        
        if not session or session.status != SessionStatus.ACTIVE:
            return None
        
        # Extend expiration
        if session.is_persistent:
            new_expiry = datetime.now(timezone.utc) + timedelta(days=self.persistent_session_days)
        else:
            new_expiry = datetime.now(timezone.utc) + timedelta(minutes=self.session_timeout_minutes)
        
        session.expires_at = new_expiry
        session.last_accessed_at = datetime.now(timezone.utc)
        
        # Update in storage
        self._update_session(session)
        
        return new_expiry
    
    def revoke_session(self, session_token: str, reason: str = "manual_revocation") -> bool:
        """Revoke specific session."""
        token_hash = self._hash_token(session_token)
        session = self._session_cache.get(token_hash)
        
        if not session:
            session = self._get_session_by_token(token_hash)
        
        if not session:
            return False
        
        # Update status
        session.status = SessionStatus.REVOKED
        
        # Update in storage
        self._update_session(session)
        
        # Remove from cache
        if token_hash in self._session_cache:
            del self._session_cache[token_hash]
        
        # Remove from user sessions
        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id] = [
                t for t in self._user_sessions[session.user_id] if t != token_hash
            ]
        
        # Log revocation
        self._log_session_activity(
            session.session_id,
            "session_revoked",
            session.ip_address,
            session.user_agent,
            metadata={"reason": reason}
        )
        
        return True
    
    def revoke_all_user_sessions(self, user_id: UUID, except_session: Optional[str] = None,
                               reason: str = "revoke_all") -> int:
        """Revoke all sessions for a user."""
        revoked_count = 0
        
        # Get all user sessions
        user_sessions = self._get_user_sessions(user_id)
        
        for session in user_sessions:
            if except_session and session.session_token == self._hash_token(except_session):
                continue
            
            session.status = SessionStatus.REVOKED
            self._update_session(session)
            
            # Remove from caches
            if session.session_token in self._session_cache:
                del self._session_cache[session.session_token]
            
            revoked_count += 1
        
        # Clear user sessions cache
        if user_id in self._user_sessions:
            if except_session:
                except_hash = self._hash_token(except_session)
                self._user_sessions[user_id] = [except_hash]
            else:
                del self._user_sessions[user_id]
        
        # Log bulk revocation
        self._log_session_activity(
            uuid4(),  # No specific session
            "sessions_bulk_revoked",
            "",
            "",
            metadata={"user_id": str(user_id), "count": revoked_count, "reason": reason}
        )
        
        return revoked_count
    
    def get_user_sessions(self, user_id: UUID, active_only: bool = True) -> List[Session]:
        """Get all sessions for a user."""
        sessions = self._get_user_sessions(user_id)
        
        if active_only:
            sessions = [s for s in sessions if s.status == SessionStatus.ACTIVE]
        
        return sessions
    
    def get_session_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        token_hash = self._hash_token(session_token)
        session = self._session_cache.get(token_hash)
        
        if not session:
            session = self._get_session_by_token(token_hash)
        
        if not session:
            return None
        
        return {
            "session_id": str(session.session_id),
            "user_id": str(session.user_id),
            "created_at": session.created_at.isoformat(),
            "last_accessed_at": session.last_accessed_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "device_type": session.device_type.value,
            "ip_address": session.ip_address,
            "location": session.location,
            "is_persistent": session.is_persistent,
            "status": session.status.value
        }
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        cleaned_count = 0
        current_time = datetime.now(timezone.utc)
        
        # Clean from cache
        expired_tokens = []
        for token_hash, session in self._session_cache.items():
            if current_time > session.expires_at:
                expired_tokens.append(token_hash)
                cleaned_count += 1
        
        for token_hash in expired_tokens:
            session = self._session_cache[token_hash]
            session.status = SessionStatus.EXPIRED
            del self._session_cache[token_hash]
            
            # Remove from user sessions
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id] = [
                    t for t in self._user_sessions[session.user_id] if t != token_hash
                ]
        
        # Clean from database
        # Implement database cleanup
        
        return cleaned_count
    
    def _generate_session_token(self) -> str:
        """Generate cryptographically secure session token."""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash session token for storage."""
        # Use HMAC for additional security
        secret = self.secrets_manager.get_secret("session_hmac_secret", accessed_by="session_manager")
        if isinstance(secret, str):
            secret = secret.encode()
        
        return hashlib.pbkdf2_hmac('sha256', token.encode(), secret, 100000).hex()
    
    def _detect_device_type(self, user_agent: str) -> DeviceType:
        """Detect device type from user agent."""
        user_agent_lower = user_agent.lower()
        
        if any(mobile in user_agent_lower for mobile in ['mobile', 'android', 'iphone']):
            return DeviceType.MOBILE
        elif any(tablet in user_agent_lower for tablet in ['tablet', 'ipad']):
            return DeviceType.TABLET
        elif any(browser in user_agent_lower for browser in ['chrome', 'firefox', 'safari', 'edge']):
            return DeviceType.WEB
        elif 'postman' in user_agent_lower or 'curl' in user_agent_lower:
            return DeviceType.API
        else:
            return DeviceType.UNKNOWN
    
    def _perform_security_checks(self, session: Session, ip_address: str,
                               user_agent: str) -> Dict[str, Any]:
        """Perform security checks on session."""
        # Check for IP address changes
        if session.ip_address != ip_address:
            # Allow IP changes for mobile devices (cellular/wifi switching)
            if session.device_type not in [DeviceType.MOBILE, DeviceType.TABLET]:
                return {
                    "is_secure": False,
                    "reason": "IP address changed",
                    "requires_reauth": True
                }
        
        # Check for user agent changes
        if session.user_agent != user_agent:
            return {
                "is_secure": False,
                "reason": "User agent changed",
                "requires_reauth": True
            }
        
        # Check for suspicious activity patterns
        # (implement based on your security requirements)
        
        return {"is_secure": True}
    
    def _enforce_session_limits(self, user_id: UUID):
        """Enforce maximum sessions per user."""
        user_sessions = self._get_user_sessions(user_id)
        active_sessions = [s for s in user_sessions if s.status == SessionStatus.ACTIVE]
        
        if len(active_sessions) >= self.max_sessions_per_user:
            # Revoke oldest sessions
            oldest_sessions = sorted(active_sessions, key=lambda s: s.last_accessed_at)
            sessions_to_revoke = oldest_sessions[:-self.max_sessions_per_user + 1]
            
            for session in sessions_to_revoke:
                session.status = SessionStatus.REVOKED
                self._update_session(session)
                
                if session.session_token in self._session_cache:
                    del self._session_cache[session.session_token]
    
    def _update_session_activity(self, session: Session, ip_address: str, user_agent: str):
        """Update session activity."""
        session.last_accessed_at = datetime.now(timezone.utc)
        session.ip_address = ip_address
        session.user_agent = user_agent
        
        # Update in storage
        self._update_session(session)
        
        # Log activity
        self._log_session_activity(
            session.session_id,
            "session_accessed",
            ip_address,
            user_agent
        )
    
    def _expire_session(self, session: Session):
        """Mark session as expired."""
        session.status = SessionStatus.EXPIRED
        self._update_session(session)
        
        # Remove from cache
        if session.session_token in self._session_cache:
            del self._session_cache[session.session_token]
    
    def _log_session_activity(self, session_id: UUID, activity_type: str,
                            ip_address: str, user_agent: str,
                            endpoint: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None):
        """Log session activity."""
        activity = SessionActivity(
            session_id=session_id,
            activity_type=activity_type,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            metadata=metadata
        )
        
        self._activity_log.append(activity)
        
        # In production, store in database or send to logging service
    
    def _store_session(self, session: Session):
        """Store session in database."""
        # Implement database storage
        pass
    
    def _get_session_by_token(self, token_hash: str) -> Optional[Session]:
        """Get session by token hash from database."""
        # Implement database lookup
        pass
    
    def _get_user_sessions(self, user_id: UUID) -> List[Session]:
        """Get all sessions for user from database."""
        # Implement database query
        return []
    
    def _update_session(self, session: Session):
        """Update session in database."""
        # Implement database update
        pass
