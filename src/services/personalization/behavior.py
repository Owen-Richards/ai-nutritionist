"""
Privacy-Compliant Multi-User Linking Service

Implements GDPR-compliant user linking with:
- Double opt-in process for explicit consent
- Identity verification via OTP
- Data separation and controlled sharing
- Right to unlink and data deletion
- Audit trails for compliance

Key Features:
- Send secure invites with explicit consent language
- OTP verification for phone number ownership
- Role-based access control (Admin, Family Member, Child)
- Granular data sharing permissions
- Easy unlinking and data deletion
- Compliance audit logging
"""

import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

class LinkingRole(Enum):
    ADMIN = "admin"          # Full access to linked accounts
    FAMILY_MEMBER = "family" # Standard family member access
    CHILD = "child"          # Limited access, requires parental consent
    VIEWER = "viewer"        # Read-only access to shared data

class ConsentStatus(Enum):
    PENDING = "pending"      # Invite sent, awaiting response
    ACCEPTED = "accepted"    # User confirmed via OTP
    DECLINED = "declined"    # User explicitly declined
    EXPIRED = "expired"      # Invite expired (3 days)
    REVOKED = "revoked"      # User later revoked consent

class DataSharingPermission(Enum):
    MEAL_PLANS = "meal_plans"
    NUTRITION_TRACKING = "nutrition_tracking" 
    GROCERY_LISTS = "grocery_lists"
    DIETARY_PREFERENCES = "dietary_preferences"
    HEALTH_GOALS = "health_goals"
    PROGRESS_REPORTS = "progress_reports"

class UserLinkingService:
    def __init__(self, user_service, messaging_service, audit_service=None):
        self.user_service = user_service
        self.messaging_service = messaging_service
        self.audit_service = audit_service
        
        # Invite expiration time (3 days as per best practices)
        self.INVITE_EXPIRY_HOURS = 72
        
        # Rate limiting for invites (prevent abuse)
        self.MAX_INVITES_PER_DAY = 5
        
    def send_linking_invite(self, primary_user_id: str, invitee_phone: str, 
                          role: LinkingRole, permissions: List[DataSharingPermission],
                          invitee_name: str = None) -> Dict[str, Any]:
        """
        Send privacy-compliant linking invite with explicit consent language
        
        Implements GDPR Article 7 requirements:
        - Freely given, specific, informed, unambiguous consent
        - Clear affirmative action required
        - Withdrawal information provided
        """
        
        # Rate limiting check
        if not self._check_invite_rate_limit(primary_user_id):
            return {
                "success": False,
                "error": "Daily invite limit reached. Please try again tomorrow.",
                "code": "RATE_LIMITED"
            }
        
        # Generate secure invite code and verification OTP
        invite_code = self._generate_invite_code()
        verification_otp = self._generate_otp()
        
        # Get primary user info for transparency
        primary_user = self.user_service.get_user(primary_user_id)
        primary_name = primary_user.get('name', 'A user')
        primary_phone = primary_user.get('phone', 'Unknown')
        
        # Create invite record with full audit trail
        invite_data = {
            "invite_code": invite_code,
            "verification_otp": verification_otp,
            "primary_user_id": primary_user_id,
            "primary_phone": primary_phone,
            "primary_name": primary_name,
            "invitee_phone": invitee_phone,
            "invitee_name": invitee_name,
            "role": role.value,
            "permissions": [p.value for p in permissions],
            "status": ConsentStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=self.INVITE_EXPIRY_HOURS)).isoformat(),
            "consent_language_version": "1.0",  # Track which consent text was shown
            "gdpr_lawful_basis": "consent",     # GDPR Article 6(1)(a)
            "data_subject_rights_provided": True
        }
        
        # Store invite securely
        self._store_invite(invite_code, invite_data)
        
        # Prepare GDPR-compliant consent message
        consent_message = self._build_consent_message(
            primary_name, primary_phone, role, permissions, 
            invite_code, verification_otp, invitee_name
        )
        
        # Send invite via WhatsApp/SMS with privacy notice
        message_result = self.messaging_service.send_message(
            to_phone=invitee_phone,
            message=consent_message,
            message_type="linking_invite"
        )
        
        if message_result.get("success"):
            # Log compliance audit trail
            self._log_consent_action(
                invite_code, "invite_sent", invitee_phone,
                {"primary_user": primary_user_id, "consent_version": "1.0"}
            )
            
            return {
                "success": True,
                "invite_code": invite_code,
                "expires_at": invite_data["expires_at"],
                "message": f"Invite sent to {invitee_phone}. They have 72 hours to accept."
            }
        else:
            return {
                "success": False,
                "error": "Failed to send invite message",
                "details": message_result.get("error")
            }
    
    def verify_and_accept_invite(self, invitee_phone: str, verification_otp: str, 
                               consent_confirmation: str = "YES") -> Dict[str, Any]:
        """
        Verify phone ownership and process explicit consent
        
        Implements secure identity verification + explicit consent capture
        """
        
        # Find pending invite by phone and OTP
        invite = self._find_invite_by_phone_and_otp(invitee_phone, verification_otp)
        
        if not invite:
            return {
                "success": False,
                "error": "Invalid verification code or no pending invite found",
                "code": "INVALID_VERIFICATION"
            }
        
        # Check if invite expired
        if datetime.fromisoformat(invite["expires_at"]) < datetime.utcnow():
            self._update_invite_status(invite["invite_code"], ConsentStatus.EXPIRED)
            return {
                "success": False,
                "error": "Invite has expired. Please request a new invitation.",
                "code": "INVITE_EXPIRED"
            }
        
        # Validate explicit consent (must be clear affirmative action)
        if not self._validate_consent_response(consent_confirmation):
            return {
                "success": False,
                "error": "Please reply 'YES' to give explicit consent for data sharing",
                "code": "CONSENT_REQUIRED"
            }
        
        # Check for special handling if invitee is a minor
        if invite["role"] == LinkingRole.CHILD.value:
            # For minors, we need additional parental consent verification
            # This could be enhanced with additional verification steps
            pass
        
        # Create or update invitee's user profile
        invitee_user_data = {
            "phone": invitee_phone,
            "name": invite.get("invitee_name"),
            "role": invite["role"],
            "linked_to": invite["primary_user_id"],
            "permissions": invite["permissions"],
            "consent_date": datetime.utcnow().isoformat(),
            "consent_method": "sms_verification",
            "consent_ip": None,  # Could capture if web-based
            "consent_version": invite["consent_language_version"],
            "gdpr_rights_acknowledged": True
        }
        
        # Create separate user profile (data separation principle)
        invitee_user_id = self.user_service.create_or_update_user(invitee_user_data)
        
        # Create linking relationship with controlled access
        linking_relationship = {
            "primary_user_id": invite["primary_user_id"],
            "linked_user_id": invitee_user_id,
            "relationship_type": invite["role"],
            "permissions": invite["permissions"],
            "created_at": datetime.utcnow().isoformat(),
            "consent_audit_trail": {
                "invite_code": invite["invite_code"],
                "consent_timestamp": datetime.utcnow().isoformat(),
                "verification_method": "sms_otp",
                "consent_language_version": invite["consent_language_version"]
            }
        }
        
        # Store relationship
        self._create_linking_relationship(linking_relationship)
        
        # Update invite status to accepted
        self._update_invite_status(invite["invite_code"], ConsentStatus.ACCEPTED)
        
        # Log compliance audit
        self._log_consent_action(
            invite["invite_code"], "consent_accepted", invitee_phone,
            {"user_id": invitee_user_id, "verification_method": "sms_otp"}
        )
        
        # Send confirmation to both parties
        self._send_linking_confirmations(invite, invitee_user_id)
        
        return {
            "success": True,
            "user_id": invitee_user_id,
            "relationship_id": f"{invite['primary_user_id']}_{invitee_user_id}",
            "permissions": invite["permissions"],
            "message": "Successfully linked! You can now share nutrition data."
        }
    
    def decline_invite(self, invitee_phone: str, verification_otp: str = None) -> Dict[str, Any]:
        """
        Process explicit consent decline
        """
        
        invite = self._find_invite_by_phone_and_otp(invitee_phone, verification_otp) if verification_otp else self._find_invite_by_phone(invitee_phone)
        
        if not invite:
            return {"success": False, "error": "No pending invite found"}
        
        # Update status and log
        self._update_invite_status(invite["invite_code"], ConsentStatus.DECLINED)
        self._log_consent_action(invite["invite_code"], "consent_declined", invitee_phone, {})
        
        # Clean up invite data (data minimization)
        self._delete_invite_data(invite["invite_code"])
        
        # Notify primary user
        self.messaging_service.send_message(
            to_phone=invite["primary_phone"],
            message=f"Your linking invite to {invitee_phone} was declined. No data will be shared.",
            message_type="invite_declined"
        )
        
        return {
            "success": True,
            "message": "Invite declined. No data will be shared."
        }
    
    def unlink_users(self, requesting_user_id: str, target_user_id: str) -> Dict[str, Any]:
        """
        Remove linking relationship and stop data sharing
        
        Implements right to withdraw consent (GDPR Article 7(3))
        """
        
        # Find the relationship
        relationship = self._find_relationship(requesting_user_id, target_user_id)
        
        if not relationship:
            return {"success": False, "error": "No linking relationship found"}
        
        # Verify user has permission to unlink
        if not self._can_user_unlink(requesting_user_id, relationship):
            return {"success": False, "error": "Not authorized to unlink this relationship"}
        
        # Log the unlinking action
        self._log_consent_action(
            relationship.get("id", "unknown"), "relationship_unlinked", 
            requesting_user_id, {"target_user": target_user_id}
        )
        
        # Remove relationship
        self._delete_relationship(relationship["id"])
        
        # Clean up any shared data views (data separation)
        self._clean_shared_data_access(requesting_user_id, target_user_id)
        
        # Notify both parties
        self._send_unlink_notifications(relationship)
        
        return {
            "success": True,
            "message": "Users unlinked successfully. Data sharing has stopped."
        }
    
    def delete_user_data(self, user_id: str, requesting_user_id: str = None) -> Dict[str, Any]:
        """
        Delete user data while preserving other users' data
        
        Implements right to erasure (GDPR Article 17)
        """
        
        # Verify authorization
        if requesting_user_id and requesting_user_id != user_id:
            if not self._is_authorized_for_deletion(requesting_user_id, user_id):
                return {"success": False, "error": "Not authorized to delete this user's data"}
        
        # Get all relationships for this user
        relationships = self._get_user_relationships(user_id)
        
        # Notify linked users about data deletion
        for rel in relationships:
            other_user_id = rel["primary_user_id"] if rel["linked_user_id"] == user_id else rel["linked_user_id"]
            self._notify_user_deletion(other_user_id, user_id)
        
        # Remove user from all relationships
        for rel in relationships:
            self._delete_relationship(rel["id"])
        
        # Delete user's personal data
        deletion_result = self.user_service.delete_user_completely(user_id)
        
        # Log deletion for compliance
        self._log_consent_action(
            f"user_deletion_{user_id}", "data_deleted", user_id,
            {"deletion_timestamp": datetime.utcnow().isoformat(),
             "requesting_user": requesting_user_id}
        )
        
        return {
            "success": True,
            "message": "User data deleted successfully. All linked relationships removed.",
            "details": deletion_result
        }
    
    def get_shared_data(self, requesting_user_id: str, target_user_id: str, 
                       data_type: DataSharingPermission) -> Dict[str, Any]:
        """
        Get shared data with permission checking
        """
        
        # Check if users are linked and permission exists
        if not self._has_sharing_permission(requesting_user_id, target_user_id, data_type):
            return {
                "success": False,
                "error": "No permission to access this data type",
                "code": "PERMISSION_DENIED"
            }
        
        # Get filtered data based on permissions
        shared_data = self._get_filtered_user_data(target_user_id, data_type)
        
        return {
            "success": True,
            "data": shared_data,
            "data_type": data_type.value,
            "shared_from": target_user_id
        }
    
    def _build_consent_message(self, primary_name: str, primary_phone: str, 
                              role: LinkingRole, permissions: List[DataSharingPermission],
                              invite_code: str, verification_otp: str, 
                              invitee_name: str = None) -> str:
        """
        Build GDPR-compliant consent message with all required elements
        """
        
        greeting = f"Hi {invitee_name}! " if invitee_name else "Hi there! "
        
        # Main consent message
        message = f"""{greeting}

🔗 **NUTRITION SHARING INVITE**

**{primary_name}** ({primary_phone}) invites you to share nutrition data on AI Nutritionist.

**WHAT WILL BE SHARED:**
"""
        
        # List specific data types
        for perm in permissions:
            message += f"• {perm.value.replace('_', ' ').title()}\n"
        
        message += f"""
**YOUR RIGHTS:**
✅ You control what data you share
✅ You can stop sharing anytime (text UNLINK)
✅ You can delete your data anytime (text DELETE)
✅ View our privacy policy: https://ai-nutritionist.com/privacy

**TO ACCEPT:**
1. Reply with this code: **{verification_otp}**
2. Then reply: **YES**

This confirms you consent to data sharing. Standard msg rates apply.

Expires in 72 hours. Reply STOP to decline.

---
*Required by GDPR: This message documents your explicit consent to data processing. You can withdraw consent anytime.*"""
        
        return message
    
    def _generate_invite_code(self) -> str:
        """Generate secure invite code"""
        return secrets.token_urlsafe(16)
    
    def _generate_otp(self) -> str:
        """Generate 6-digit OTP for verification"""
        return f"{secrets.randbelow(1000000):06d}"
    
    def _check_invite_rate_limit(self, user_id: str) -> bool:
        """Check if user hasn't exceeded daily invite limit"""
        # Implementation would check database for invite count in last 24 hours
        # For now, return True (implement based on your storage system)
        return True
    
    def _store_invite(self, invite_code: str, invite_data: Dict[str, Any]):
        """Store invite securely with encryption"""
        # Implementation depends on your storage system
        # Should encrypt sensitive data and set TTL
        pass
    
    def _find_invite_by_phone_and_otp(self, phone: str, otp: str) -> Optional[Dict[str, Any]]:
        """Find invite by phone number and OTP"""
        # Implementation depends on your storage system
        return None
    
    def _find_invite_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find pending invite by phone number"""
        # Implementation depends on your storage system
        return None
    
    def _validate_consent_response(self, response: str) -> bool:
        """Validate that response is explicit consent"""
        valid_responses = ["YES", "Y", "ACCEPT", "AGREE", "CONSENT"]
        return response.upper().strip() in valid_responses
    
    def _update_invite_status(self, invite_code: str, status: ConsentStatus):
        """Update invite status"""
        # Implementation depends on your storage system
        pass
    
    def _create_linking_relationship(self, relationship_data: Dict[str, Any]):
        """Create linking relationship in database"""
        # Implementation depends on your storage system
        pass
    
    def _log_consent_action(self, invite_code: str, action: str, user_identifier: str, 
                           metadata: Dict[str, Any]):
        """Log consent actions for GDPR compliance audit trail"""
        audit_record = {
            "invite_code": invite_code,
            "action": action,
            "user_identifier": hashlib.sha256(user_identifier.encode()).hexdigest(),  # Hash for privacy
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata,
            "compliance_framework": "GDPR"
        }
        
        if self.audit_service:
            self.audit_service.log_compliance_event(audit_record)
    
    def _send_linking_confirmations(self, invite: Dict[str, Any], invitee_user_id: str):
        """Send confirmation messages to both parties"""
        
        # Confirm to invitee
        invitee_message = f"""✅ **LINKED SUCCESSFULLY**

You're now linked with {invite['primary_name']} for nutrition sharing.

**Data being shared:**
{chr(10).join([f"• {p.replace('_', ' ').title()}" for p in invite['permissions']])}

**Your controls:**
• Text UNLINK to stop sharing
• Text DELETE to remove all your data
• Text PRIVACY for your rights

Welcome to better nutrition together! 🥗"""
        
        self.messaging_service.send_message(
            to_phone=invite["invitee_phone"],
            message=invitee_message,
            message_type="linking_confirmed"
        )
        
        # Confirm to primary user
        primary_message = f"""✅ **{invite.get('invitee_name', invite['invitee_phone'])} JOINED**

They accepted your nutrition sharing invite!

**Shared access:**
{chr(10).join([f"• {p.replace('_', ' ').title()}" for p in invite['permissions']])}

You can now coordinate meal plans and nutrition goals together. 👥"""
        
        self.messaging_service.send_message(
            to_phone=invite["primary_phone"],
            message=primary_message,
            message_type="linking_confirmed"
        )
    
    def _delete_invite_data(self, invite_code: str):
        """Delete invite data after processing (data minimization)"""
        # Implementation depends on your storage system
        pass
    
    def _find_relationship(self, user1_id: str, user2_id: str) -> Optional[Dict[str, Any]]:
        """Find relationship between two users"""
        # Implementation depends on your storage system
        return None
    
    def _can_user_unlink(self, requesting_user_id: str, relationship: Dict[str, Any]) -> bool:
        """Check if user can unlink the relationship"""
        # Users can unlink if they're part of the relationship
        return (requesting_user_id == relationship["primary_user_id"] or 
                requesting_user_id == relationship["linked_user_id"])
    
    def _delete_relationship(self, relationship_id: str):
        """Delete linking relationship"""
        # Implementation depends on your storage system
        pass
    
    def _clean_shared_data_access(self, user1_id: str, user2_id: str):
        """Remove any cached shared data access"""
        # Implementation depends on your caching system
        pass
    
    def _send_unlink_notifications(self, relationship: Dict[str, Any]):
        """Notify both users about unlinking"""
        # Implementation to send notifications
        pass
    
    def _get_user_relationships(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a user"""
        # Implementation depends on your storage system
        return []
    
    def _is_authorized_for_deletion(self, requesting_user_id: str, target_user_id: str) -> bool:
        """Check if user is authorized to delete target user's data"""
        # Only allow self-deletion or parent deleting child data
        return requesting_user_id == target_user_id
    
    def _notify_user_deletion(self, user_id: str, deleted_user_id: str):
        """Notify user that a linked user's data was deleted"""
        # Implementation to send notification
        pass
    
    def _has_sharing_permission(self, requesting_user_id: str, target_user_id: str, 
                              data_type: DataSharingPermission) -> bool:
        """Check if user has permission to access specific data type"""
        # Implementation depends on your storage system
        return False
    
    def _get_filtered_user_data(self, user_id: str, data_type: DataSharingPermission) -> Dict[str, Any]:
        """Get user data filtered by permission type"""
        # Implementation depends on your data model
        return {}
