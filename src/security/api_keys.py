"""
API key management for secure service authentication.

Provides comprehensive API key management:
- API key generation and validation
- Key rotation and revocation
- Usage tracking and rate limiting
- Scope-based permissions
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel

from ..services.infrastructure.secrets_manager import SecretsManager


class APIKeyScope(str, Enum):
    """API key scopes/permissions."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    
    # Specific service scopes
    PLANS_READ = "plans:read"
    PLANS_WRITE = "plans:write"
    COMMUNITY_READ = "community:read"
    COMMUNITY_WRITE = "community:write"
    ANALYTICS_READ = "analytics:read"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"


class APIKeyStatus(str, Enum):
    """API key status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class APIKey(BaseModel):
    """API key model."""
    id: UUID
    name: str
    key_hash: str  # Store hash, not actual key
    scopes: List[APIKeyScope]
    status: APIKeyStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    rate_limit: Optional[int] = None  # requests per minute
    created_by: str
    description: Optional[str] = None


class APIKeyUsage(BaseModel):
    """API key usage tracking."""
    key_id: UUID
    endpoint: str
    method: str
    timestamp: datetime
    response_code: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class APIKeyValidationResult(BaseModel):
    """API key validation result."""
    is_valid: bool
    key_id: Optional[UUID] = None
    scopes: List[APIKeyScope] = []
    rate_limit_remaining: Optional[int] = None
    error_message: Optional[str] = None


class APIKeyManager:
    """API key management service."""
    
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
        self.key_prefix = "ak_"
        self.key_length = 32
        
        # In-memory cache for performance (in production, use Redis)
        self._key_cache: Dict[str, APIKey] = {}
        self._usage_cache: Dict[UUID, List[APIKeyUsage]] = {}
        self._rate_limit_cache: Dict[UUID, Dict[str, Any]] = {}
    
    def generate_api_key(self, name: str, scopes: List[APIKeyScope],
                        expires_in_days: Optional[int] = None,
                        rate_limit: Optional[int] = None,
                        created_by: str = "system",
                        description: Optional[str] = None) -> tuple[APIKey, str]:
        """Generate new API key."""
        # Generate secure random key
        key_bytes = secrets.token_bytes(self.key_length)
        api_key = f"{self.key_prefix}{secrets.token_urlsafe(self.key_length)}"
        
        # Hash the key for storage
        key_hash = self._hash_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create API key object
        key_obj = APIKey(
            id=uuid4(),
            name=name,
            key_hash=key_hash,
            scopes=scopes,
            status=APIKeyStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            rate_limit=rate_limit,
            created_by=created_by,
            description=description
        )
        
        # Store in database (implement with your storage backend)
        self._store_api_key(key_obj)
        
        # Cache for performance
        self._key_cache[key_hash] = key_obj
        
        return key_obj, api_key
    
    def validate_api_key(self, api_key: str, required_scopes: List[APIKeyScope] = None) -> APIKeyValidationResult:
        """Validate API key and check permissions."""
        try:
            # Hash the provided key
            key_hash = self._hash_key(api_key)
            
            # Get key from cache or database
            key_obj = self._key_cache.get(key_hash)
            if not key_obj:
                key_obj = self._get_api_key_by_hash(key_hash)
                if key_obj:
                    self._key_cache[key_hash] = key_obj
            
            if not key_obj:
                return APIKeyValidationResult(
                    is_valid=False,
                    error_message="Invalid API key"
                )
            
            # Check if key is active
            if key_obj.status != APIKeyStatus.ACTIVE:
                return APIKeyValidationResult(
                    is_valid=False,
                    error_message=f"API key is {key_obj.status.value}"
                )
            
            # Check expiration
            if key_obj.expires_at and datetime.now(timezone.utc) > key_obj.expires_at:
                # Mark as expired
                self._update_key_status(key_obj.id, APIKeyStatus.EXPIRED)
                return APIKeyValidationResult(
                    is_valid=False,
                    error_message="API key has expired"
                )
            
            # Check rate limiting
            rate_limit_result = self._check_rate_limit(key_obj)
            if not rate_limit_result["allowed"]:
                return APIKeyValidationResult(
                    is_valid=False,
                    error_message="Rate limit exceeded",
                    rate_limit_remaining=0
                )
            
            # Check required scopes
            if required_scopes:
                if not self._has_required_scopes(key_obj.scopes, required_scopes):
                    return APIKeyValidationResult(
                        is_valid=False,
                        error_message="Insufficient permissions",
                        key_id=key_obj.id,
                        scopes=key_obj.scopes
                    )
            
            # Update usage
            self._record_usage(key_obj)
            
            return APIKeyValidationResult(
                is_valid=True,
                key_id=key_obj.id,
                scopes=key_obj.scopes,
                rate_limit_remaining=rate_limit_result.get("remaining")
            )
            
        except Exception as e:
            return APIKeyValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    def revoke_api_key(self, key_id: UUID, revoked_by: str = "system") -> bool:
        """Revoke API key."""
        success = self._update_key_status(key_id, APIKeyStatus.REVOKED)
        
        if success:
            # Remove from cache
            for key_hash, key_obj in list(self._key_cache.items()):
                if key_obj.id == key_id:
                    del self._key_cache[key_hash]
                    break
            
            # Log revocation
            self._log_key_event(key_id, "revoked", {"revoked_by": revoked_by})
        
        return success
    
    def rotate_api_key(self, key_id: UUID, rotated_by: str = "system") -> tuple[Optional[APIKey], Optional[str]]:
        """Rotate API key (generate new key, revoke old one)."""
        # Get existing key
        old_key = self._get_api_key_by_id(key_id)
        if not old_key:
            return None, None
        
        # Generate new key with same settings
        new_key_obj, new_api_key = self.generate_api_key(
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_in_days=None if not old_key.expires_at else 
                           (old_key.expires_at - datetime.now(timezone.utc)).days,
            rate_limit=old_key.rate_limit,
            created_by=rotated_by,
            description=f"Rotated from {old_key.name}"
        )
        
        # Revoke old key
        self.revoke_api_key(key_id, rotated_by)
        
        # Log rotation
        self._log_key_event(
            new_key_obj.id, 
            "rotated", 
            {"old_key_id": str(key_id), "rotated_by": rotated_by}
        )
        
        return new_key_obj, new_api_key
    
    def list_api_keys(self, created_by: Optional[str] = None,
                     status: Optional[APIKeyStatus] = None) -> List[APIKey]:
        """List API keys with optional filtering."""
        # Implement database query
        return self._query_api_keys(created_by=created_by, status=status)
    
    def get_key_usage(self, key_id: UUID, hours_back: int = 24) -> List[APIKeyUsage]:
        """Get usage statistics for API key."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # Get from cache or database
        usage_records = self._usage_cache.get(key_id, [])
        
        # Filter by time
        recent_usage = [
            usage for usage in usage_records
            if usage.timestamp >= cutoff_time
        ]
        
        return recent_usage
    
    def get_usage_stats(self, key_id: UUID) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        key_obj = self._get_api_key_by_id(key_id)
        if not key_obj:
            return {}
        
        usage_24h = self.get_key_usage(key_id, 24)
        usage_7d = self.get_key_usage(key_id, 24 * 7)
        
        return {
            "key_id": str(key_id),
            "total_usage": key_obj.usage_count,
            "last_used": key_obj.last_used_at.isoformat() if key_obj.last_used_at else None,
            "usage_24h": len(usage_24h),
            "usage_7d": len(usage_7d),
            "rate_limit": key_obj.rate_limit,
            "status": key_obj.status.value,
            "created_at": key_obj.created_at.isoformat(),
            "expires_at": key_obj.expires_at.isoformat() if key_obj.expires_at else None
        }
    
    def _hash_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        # Use HMAC for additional security
        secret = self.secrets_manager.get_secret("api_key_hmac_secret", accessed_by="api_key_manager")
        if isinstance(secret, str):
            secret = secret.encode()
        
        return hmac.new(secret, api_key.encode(), hashlib.sha256).hexdigest()
    
    def _has_required_scopes(self, key_scopes: List[APIKeyScope], 
                           required_scopes: List[APIKeyScope]) -> bool:
        """Check if key has required scopes."""
        key_scope_set = set(key_scopes)
        
        # Admin scope grants all permissions
        if APIKeyScope.ADMIN in key_scope_set:
            return True
        
        # Read-write includes read-only
        if APIKeyScope.READ_WRITE in key_scope_set and APIKeyScope.READ_ONLY in required_scopes:
            return True
        
        # Check specific scopes
        return all(scope in key_scope_set for scope in required_scopes)
    
    def _check_rate_limit(self, key_obj: APIKey) -> Dict[str, Any]:
        """Check rate limiting for API key."""
        if not key_obj.rate_limit:
            return {"allowed": True, "remaining": None}
        
        # Get current usage from cache
        current_minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        cache_key = f"{key_obj.id}:{current_minute.isoformat()}"
        
        if key_obj.id not in self._rate_limit_cache:
            self._rate_limit_cache[key_obj.id] = {}
        
        current_count = self._rate_limit_cache[key_obj.id].get(cache_key, 0)
        
        if current_count >= key_obj.rate_limit:
            return {"allowed": False, "remaining": 0}
        
        return {
            "allowed": True,
            "remaining": key_obj.rate_limit - current_count
        }
    
    def _record_usage(self, key_obj: APIKey):
        """Record API key usage."""
        # Update last used time
        key_obj.last_used_at = datetime.now(timezone.utc)
        key_obj.usage_count += 1
        
        # Update rate limit cache
        current_minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        cache_key = f"{key_obj.id}:{current_minute.isoformat()}"
        
        if key_obj.id not in self._rate_limit_cache:
            self._rate_limit_cache[key_obj.id] = {}
        
        self._rate_limit_cache[key_obj.id][cache_key] = \
            self._rate_limit_cache[key_obj.id].get(cache_key, 0) + 1
        
        # Store usage record
        # Implement with your database
    
    def _store_api_key(self, key_obj: APIKey):
        """Store API key in database."""
        # Implement database storage
        pass
    
    def _get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash from database."""
        # Implement database lookup
        pass
    
    def _get_api_key_by_id(self, key_id: UUID) -> Optional[APIKey]:
        """Get API key by ID from database."""
        # Implement database lookup
        pass
    
    def _update_key_status(self, key_id: UUID, status: APIKeyStatus) -> bool:
        """Update API key status in database."""
        # Implement database update
        return True
    
    def _query_api_keys(self, created_by: Optional[str] = None,
                       status: Optional[APIKeyStatus] = None) -> List[APIKey]:
        """Query API keys from database."""
        # Implement database query
        return []
    
    def _log_key_event(self, key_id: UUID, event_type: str, metadata: Dict[str, Any]):
        """Log API key events for auditing."""
        # Implement audit logging
        pass
