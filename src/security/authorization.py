"""
Role-Based Access Control (RBAC) system.

Implements comprehensive authorization following OWASP guidelines:
- Role-based permissions
- Resource-level access control
- Dynamic permission checking
- Audit logging
"""

from enum import Enum
from typing import Dict, List, Set, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..services.infrastructure.secrets_manager import SecretsManager


class Permission(str, Enum):
    """System permissions."""
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # Meal plan permissions
    PLAN_READ = "plan:read"
    PLAN_WRITE = "plan:write"
    PLAN_DELETE = "plan:delete"
    PLAN_SHARE = "plan:share"
    
    # Community permissions
    COMMUNITY_READ = "community:read"
    COMMUNITY_WRITE = "community:write"
    COMMUNITY_MODERATE = "community:moderate"
    COMMUNITY_ADMIN = "community:admin"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_WRITE = "analytics:write"
    ANALYTICS_ADMIN = "analytics:admin"
    
    # Billing permissions
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_ADMIN = "billing:admin"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_ADMIN = "system:admin"


class Role(str, Enum):
    """System roles."""
    GUEST = "guest"
    USER = "user"
    PREMIUM_USER = "premium_user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AccessRequest(BaseModel):
    """Access request for permission checking."""
    user_id: UUID
    resource: str
    action: str
    context: Optional[Dict[str, Any]] = None


class AccessResult(BaseModel):
    """Result of access check."""
    granted: bool
    reason: str
    required_permissions: List[str]
    user_permissions: List[str]


class RolePermissions:
    """Role to permission mappings."""
    
    ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
        Role.GUEST: {
            Permission.PLAN_READ,
        },
        
        Role.USER: {
            Permission.USER_READ,
            Permission.PLAN_READ,
            Permission.PLAN_WRITE,
            Permission.COMMUNITY_READ,
            Permission.COMMUNITY_WRITE,
            Permission.BILLING_READ,
        },
        
        Role.PREMIUM_USER: {
            Permission.USER_READ,
            Permission.PLAN_READ,
            Permission.PLAN_WRITE,
            Permission.PLAN_SHARE,
            Permission.COMMUNITY_READ,
            Permission.COMMUNITY_WRITE,
            Permission.ANALYTICS_READ,
            Permission.BILLING_READ,
            Permission.BILLING_WRITE,
        },
        
        Role.MODERATOR: {
            Permission.USER_READ,
            Permission.PLAN_READ,
            Permission.PLAN_WRITE,
            Permission.PLAN_SHARE,
            Permission.COMMUNITY_READ,
            Permission.COMMUNITY_WRITE,
            Permission.COMMUNITY_MODERATE,
            Permission.ANALYTICS_READ,
            Permission.BILLING_READ,
        },
        
        Role.ADMIN: {
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.USER_DELETE,
            Permission.PLAN_READ,
            Permission.PLAN_WRITE,
            Permission.PLAN_DELETE,
            Permission.PLAN_SHARE,
            Permission.COMMUNITY_READ,
            Permission.COMMUNITY_WRITE,
            Permission.COMMUNITY_MODERATE,
            Permission.COMMUNITY_ADMIN,
            Permission.ANALYTICS_READ,
            Permission.ANALYTICS_WRITE,
            Permission.BILLING_READ,
            Permission.BILLING_WRITE,
            Permission.BILLING_ADMIN,
            Permission.SYSTEM_CONFIG,
            Permission.SYSTEM_LOGS,
        },
        
        Role.SUPER_ADMIN: set(Permission),  # All permissions
    }


class PermissionManager:
    """Manages permissions and access control."""
    
    def __init__(self):
        self.role_permissions = RolePermissions.ROLE_PERMISSIONS
        self.access_logs: List[Dict[str, Any]] = []
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions for a role."""
        return self.role_permissions.get(role, set())
    
    def has_permission(self, user_role: Role, permission: Permission) -> bool:
        """Check if role has specific permission."""
        role_perms = self.get_role_permissions(user_role)
        return permission in role_perms
    
    def has_any_permission(self, user_role: Role, permissions: List[Permission]) -> bool:
        """Check if role has any of the specified permissions."""
        role_perms = self.get_role_permissions(user_role)
        return any(perm in role_perms for perm in permissions)
    
    def has_all_permissions(self, user_role: Role, permissions: List[Permission]) -> bool:
        """Check if role has all specified permissions."""
        role_perms = self.get_role_permissions(user_role)
        return all(perm in role_perms for perm in permissions)
    
    def add_custom_permission(self, role: Role, permission: Permission):
        """Add custom permission to role."""
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        self.role_permissions[role].add(permission)
    
    def remove_permission(self, role: Role, permission: Permission):
        """Remove permission from role."""
        if role in self.role_permissions:
            self.role_permissions[role].discard(permission)
    
    def log_access_attempt(self, user_id: UUID, resource: str, action: str, 
                          granted: bool, reason: str):
        """Log access attempt for auditing."""
        log_entry = {
            "timestamp": datetime.utcnow(),
            "user_id": str(user_id),
            "resource": resource,
            "action": action,
            "granted": granted,
            "reason": reason
        }
        self.access_logs.append(log_entry)
        
        # In production, log to external system
        # self._send_to_audit_log(log_entry)


class ResourceAccessControl:
    """Resource-level access control rules."""
    
    @staticmethod
    def can_access_user_data(requesting_user_id: UUID, target_user_id: UUID, 
                           user_role: Role) -> bool:
        """Check if user can access another user's data."""
        # Users can access their own data
        if requesting_user_id == target_user_id:
            return True
        
        # Admins and moderators can access other users' data
        return user_role in [Role.ADMIN, Role.SUPER_ADMIN, Role.MODERATOR]
    
    @staticmethod
    def can_modify_user_data(requesting_user_id: UUID, target_user_id: UUID, 
                           user_role: Role) -> bool:
        """Check if user can modify another user's data."""
        # Users can modify their own data
        if requesting_user_id == target_user_id:
            return True
        
        # Only admins can modify other users' data
        return user_role in [Role.ADMIN, Role.SUPER_ADMIN]
    
    @staticmethod
    def can_access_meal_plan(plan_owner_id: UUID, requesting_user_id: UUID, 
                           user_role: Role, plan_visibility: str = "private") -> bool:
        """Check if user can access a meal plan."""
        # Owner can always access
        if plan_owner_id == requesting_user_id:
            return True
        
        # Public plans can be accessed by authenticated users
        if plan_visibility == "public" and user_role != Role.GUEST:
            return True
        
        # Admins can access all plans
        return user_role in [Role.ADMIN, Role.SUPER_ADMIN]
    
    @staticmethod
    def can_access_billing_data(account_owner_id: UUID, requesting_user_id: UUID, 
                              user_role: Role) -> bool:
        """Check if user can access billing data."""
        # Account owner can access their billing data
        if account_owner_id == requesting_user_id:
            return True
        
        # Billing admins can access all billing data
        return user_role in [Role.ADMIN, Role.SUPER_ADMIN]


class RBACService:
    """Main RBAC service."""
    
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
        self.permission_manager = PermissionManager()
        self.resource_acl = ResourceAccessControl()
    
    def check_access(self, request: AccessRequest, user_role: Role) -> AccessResult:
        """Check if user has access to perform action on resource."""
        # Map resource/action to required permissions
        required_perms = self._get_required_permissions(request.resource, request.action)
        
        # Get user permissions based on role
        user_perms = self.permission_manager.get_role_permissions(user_role)
        user_perm_strings = [perm.value for perm in user_perms]
        
        # Check if user has required permissions
        has_permission = any(
            Permission(perm) in user_perms for perm in required_perms
        )
        
        # Apply resource-specific access control
        resource_access = self._check_resource_access(request, user_role)
        
        granted = has_permission and resource_access
        reason = self._generate_access_reason(has_permission, resource_access, required_perms)
        
        # Log access attempt
        self.permission_manager.log_access_attempt(
            user_id=request.user_id,
            resource=request.resource,
            action=request.action,
            granted=granted,
            reason=reason
        )
        
        return AccessResult(
            granted=granted,
            reason=reason,
            required_permissions=required_perms,
            user_permissions=user_perm_strings
        )
    
    def _get_required_permissions(self, resource: str, action: str) -> List[str]:
        """Map resource/action to required permissions."""
        permission_map = {
            # User management
            ("users", "read"): [Permission.USER_READ.value],
            ("users", "write"): [Permission.USER_WRITE.value],
            ("users", "delete"): [Permission.USER_DELETE.value],
            
            # Meal plans
            ("plans", "read"): [Permission.PLAN_READ.value],
            ("plans", "write"): [Permission.PLAN_WRITE.value],
            ("plans", "delete"): [Permission.PLAN_DELETE.value],
            ("plans", "share"): [Permission.PLAN_SHARE.value],
            
            # Community
            ("community", "read"): [Permission.COMMUNITY_READ.value],
            ("community", "write"): [Permission.COMMUNITY_WRITE.value],
            ("community", "moderate"): [Permission.COMMUNITY_MODERATE.value],
            
            # Analytics
            ("analytics", "read"): [Permission.ANALYTICS_READ.value],
            ("analytics", "write"): [Permission.ANALYTICS_WRITE.value],
            
            # Billing
            ("billing", "read"): [Permission.BILLING_READ.value],
            ("billing", "write"): [Permission.BILLING_WRITE.value],
            
            # System
            ("system", "config"): [Permission.SYSTEM_CONFIG.value],
            ("system", "logs"): [Permission.SYSTEM_LOGS.value],
        }
        
        return permission_map.get((resource, action), [])
    
    def _check_resource_access(self, request: AccessRequest, user_role: Role) -> bool:
        """Check resource-specific access rules."""
        context = request.context or {}
        
        if request.resource == "users":
            target_user_id = context.get("target_user_id")
            if target_user_id:
                if request.action in ["read"]:
                    return self.resource_acl.can_access_user_data(
                        request.user_id, UUID(target_user_id), user_role
                    )
                elif request.action in ["write", "delete"]:
                    return self.resource_acl.can_modify_user_data(
                        request.user_id, UUID(target_user_id), user_role
                    )
        
        elif request.resource == "plans":
            plan_owner_id = context.get("plan_owner_id")
            plan_visibility = context.get("plan_visibility", "private")
            if plan_owner_id:
                return self.resource_acl.can_access_meal_plan(
                    UUID(plan_owner_id), request.user_id, user_role, plan_visibility
                )
        
        elif request.resource == "billing":
            account_owner_id = context.get("account_owner_id")
            if account_owner_id:
                return self.resource_acl.can_access_billing_data(
                    UUID(account_owner_id), request.user_id, user_role
                )
        
        # Default to allowing if no specific rules
        return True
    
    def _generate_access_reason(self, has_permission: bool, resource_access: bool, 
                              required_perms: List[str]) -> str:
        """Generate human-readable access decision reason."""
        if has_permission and resource_access:
            return "Access granted"
        elif not has_permission:
            return f"Missing required permissions: {', '.join(required_perms)}"
        elif not resource_access:
            return "Resource access denied"
        else:
            return "Access denied"
    
    def get_user_permissions(self, user_role: Role) -> List[str]:
        """Get all permissions for a user role."""
        perms = self.permission_manager.get_role_permissions(user_role)
        return [perm.value for perm in perms]
    
    def audit_access_logs(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get access audit logs."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        return [
            log for log in self.permission_manager.access_logs
            if log["timestamp"] >= cutoff_time
        ]
