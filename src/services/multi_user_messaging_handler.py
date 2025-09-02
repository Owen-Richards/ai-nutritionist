"""
Privacy-Compliant Multi-User Messaging Handler

Handles privacy-compliant multi-user linking commands with:
- GDPR compliance for consent and data rights
- Secure invite and verification flows  
- Family-friendly nutrition sharing
- Data separation and controlled access
- Easy unlinking and deletion

Integration with Universal Message Handler for seamless UX
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import re
from datetime import datetime

from .user_linking_service import (
    UserLinkingService, LinkingRole, DataSharingPermission, 
    ConsentStatus
)

class LinkingCommand(Enum):
    INVITE = "invite"
    ACCEPT = "accept" 
    DECLINE = "decline"
    UNLINK = "unlink"
    DELETE = "delete"
    PRIVACY = "privacy"
    PERMISSIONS = "permissions"
    FAMILY = "family"

class MultiUserMessagingHandler:
    def __init__(self, user_linking_service: UserLinkingService, 
                 user_service, messaging_service):
        self.linking_service = user_linking_service
        self.user_service = user_service
        self.messaging_service = messaging_service
        
        # Command patterns for natural language detection
        self.command_patterns = {
            LinkingCommand.INVITE: [
                r"invite\s+(\+?\d{10,15})",
                r"add\s+family\s+(\+?\d{10,15})",
                r"link\s+(\+?\d{10,15})",
                r"share\s+with\s+(\+?\d{10,15})"
            ],
            LinkingCommand.ACCEPT: [
                r"(\d{6})\s*YES",
                r"accept\s+(\d{6})",
                r"join\s+(\d{6})",
                r"YES\s+(\d{6})"
            ],
            LinkingCommand.DECLINE: [
                r"decline",
                r"no\s+thanks",
                r"not\s+interested",
                r"stop"
            ],
            LinkingCommand.UNLINK: [
                r"unlink",
                r"stop\s+sharing",
                r"disconnect",
                r"remove\s+family"
            ],
            LinkingCommand.DELETE: [
                r"delete\s+my\s+data",
                r"remove\s+me",
                r"erase\s+everything"
            ],
            LinkingCommand.PRIVACY: [
                r"privacy",
                r"my\s+rights",
                r"data\s+rights"
            ],
            LinkingCommand.FAMILY: [
                r"family\s+status",
                r"who\s+linked",
                r"shared\s+with"
            ]
        }
    
    def handle_linking_message(self, user_id: str, phone: str, message: str) -> Dict[str, Any]:
        """
        Process multi-user linking commands with privacy compliance
        
        Returns response dict with success status and message
        """
        
        message_lower = message.lower().strip()
        
        # Check for linking commands
        for command, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    return self._handle_linking_command(
                        command, user_id, phone, message, match
                    )
        
        # Check if this might be an OTP verification
        otp_match = re.search(r"\b(\d{6})\b", message)
        if otp_match:
            return self._handle_otp_verification(user_id, phone, otp_match.group(1), message)
        
        # Not a linking command
        return {"success": False, "handled": False}
    
    def _handle_linking_command(self, command: LinkingCommand, user_id: str, 
                               phone: str, message: str, match) -> Dict[str, Any]:
        """Route linking commands to appropriate handlers"""
        
        try:
            if command == LinkingCommand.INVITE:
                return self._handle_invite_command(user_id, phone, match.group(1), message)
            
            elif command == LinkingCommand.ACCEPT:
                return self._handle_accept_command(user_id, phone, match.group(1), message)
            
            elif command == LinkingCommand.DECLINE:
                return self._handle_decline_command(user_id, phone)
            
            elif command == LinkingCommand.UNLINK:
                return self._handle_unlink_command(user_id, phone, message)
            
            elif command == LinkingCommand.DELETE:
                return self._handle_delete_command(user_id, phone)
            
            elif command == LinkingCommand.PRIVACY:
                return self._handle_privacy_command(user_id, phone)
            
            elif command == LinkingCommand.FAMILY:
                return self._handle_family_status_command(user_id, phone)
            
            else:
                return {"success": False, "error": "Unknown linking command"}
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing linking command: {str(e)}"
            }
    
    def _handle_invite_command(self, user_id: str, phone: str, target_phone: str, 
                              message: str) -> Dict[str, Any]:
        """
        Handle family/partner invite command
        
        Example: "invite +1234567890" or "add family +1234567890"
        """
        
        # Clean up phone number
        target_phone = re.sub(r'[^\d+]', '', target_phone)
        if not target_phone.startswith('+'):
            target_phone = '+1' + target_phone  # Assume US if no country code
        
        # Determine role and permissions based on message context
        role, permissions = self._infer_role_and_permissions(message)
        
        # Extract invitee name if mentioned
        name_match = re.search(r"(?:invite|add|link)\s+(\w+)", message, re.IGNORECASE)
        invitee_name = name_match.group(1) if name_match else None
        
        # Send the invite
        result = self.linking_service.send_linking_invite(
            primary_user_id=user_id,
            invitee_phone=target_phone,
            role=role,
            permissions=permissions,
            invitee_name=invitee_name
        )
        
        if result["success"]:
            response = f"""✅ **INVITE SENT**

Sent nutrition sharing invite to {target_phone}

They'll receive:
• Verification code to confirm their number
• Clear explanation of what data will be shared
• Easy way to accept or decline

**Expires in 72 hours**

They can reply with the verification code + YES to join, or STOP to decline."""
            
            return {
                "success": True,
                "response": response,
                "invite_code": result["invite_code"]
            }
        else:
            return {
                "success": False,
                "response": f"❌ Couldn't send invite: {result['error']}"
            }
    
    def _handle_accept_command(self, user_id: str, phone: str, otp: str, 
                              message: str) -> Dict[str, Any]:
        """
        Handle invite acceptance with OTP verification
        
        Example: "123456 YES" or "accept 123456"
        """
        
        # Extract explicit consent confirmation
        consent_match = re.search(r"\b(YES|ACCEPT|AGREE|CONSENT)\b", message.upper())
        consent_word = consent_match.group(1) if consent_match else "YES"
        
        # Process the acceptance
        result = self.linking_service.verify_and_accept_invite(
            invitee_phone=phone,
            verification_otp=otp,
            consent_confirmation=consent_word
        )
        
        if result["success"]:
            # Welcome the new linked user
            response = f"""🎉 **WELCOME TO FAMILY NUTRITION!**

You're now linked for nutrition sharing!

**What you can do:**
• Share meal plans and grocery lists
• See family nutrition goals and progress  
• Get coordinated healthy eating suggestions
• Help each other stay on track

**Your privacy controls:**
• Text UNLINK to stop sharing anytime
• Text DELETE to remove all your data
• Text PRIVACY to see your rights

Ready to eat better together! 🥗👨‍👩‍👧‍👦"""
            
            return {"success": True, "response": response}
        else:
            return {"success": False, "response": f"❌ {result['error']}"}
    
    def _handle_decline_command(self, user_id: str, phone: str) -> Dict[str, Any]:
        """Handle invite decline"""
        
        result = self.linking_service.decline_invite(invitee_phone=phone)
        
        if result["success"]:
            response = """✅ **INVITE DECLINED**

No problem! Your decision has been recorded and no data will be shared.

If you change your mind, they can send you a new invite anytime.

Have a great day! 😊"""
            
            return {"success": True, "response": response}
        else:
            return {"success": False, "response": "No pending invite found to decline."}
    
    def _handle_unlink_command(self, user_id: str, phone: str, message: str) -> Dict[str, Any]:
        """
        Handle unlinking from family/partner sharing
        """
        
        # Get user's relationships
        relationships = self.linking_service._get_user_relationships(user_id)
        
        if not relationships:
            return {
                "success": False,
                "response": "You're not currently linked with anyone for nutrition sharing."
            }
        
        # If multiple relationships, ask which one to unlink
        if len(relationships) > 1:
            response = "**WHO TO UNLINK?**\n\n"
            for i, rel in enumerate(relationships, 1):
                other_user_id = rel["primary_user_id"] if rel["linked_user_id"] == user_id else rel["linked_user_id"]
                other_user = self.user_service.get_user(other_user_id)
                name = other_user.get("name", other_user.get("phone", "Unknown"))
                response += f"{i}. {name}\n"
            
            response += "\nReply with the number to unlink, or 'ALL' to unlink everyone."
            
            return {"success": True, "response": response, "action_needed": "select_unlink"}
        
        # Single relationship - unlink it
        rel = relationships[0]
        other_user_id = rel["primary_user_id"] if rel["linked_user_id"] == user_id else rel["linked_user_id"]
        
        result = self.linking_service.unlink_users(user_id, other_user_id)
        
        if result["success"]:
            response = """✅ **UNLINKED SUCCESSFULLY**

You've stopped sharing nutrition data. 

**What happened:**
• All data sharing has ended immediately
• Your personal data remains private and separate
• You can still use the nutrition assistant independently

If you want to link again in the future, just ask them to send a new invite! 👋"""
            
            return {"success": True, "response": response}
        else:
            return {"success": False, "response": f"❌ Couldn't unlink: {result['error']}"}
    
    def _handle_delete_command(self, user_id: str, phone: str) -> Dict[str, Any]:
        """
        Handle complete data deletion request (GDPR right to erasure)
        """
        
        # Send confirmation message first
        confirmation_response = """⚠️ **DELETE ALL DATA?**

This will **permanently delete**:
• All your nutrition data and meal plans
• Your dietary preferences and goals  
• All nutrition tracking history
• Links with family/partners (they'll be notified)

**This cannot be undone!**

To confirm deletion, reply: **DELETE CONFIRMED**

To cancel, reply anything else or just ignore this message."""
        
        return {
            "success": True,
            "response": confirmation_response,
            "action_needed": "confirm_deletion"
        }
    
    def _handle_delete_confirmation(self, user_id: str, phone: str) -> Dict[str, Any]:
        """Handle confirmed data deletion"""
        
        result = self.linking_service.delete_user_data(user_id, user_id)
        
        if result["success"]:
            response = """✅ **DATA DELETED**

All your data has been permanently deleted:
• Personal nutrition data ✓
• Meal plans and preferences ✓  
• Tracking history ✓
• Family/partner links ✓

**Your rights respected:**
This deletion complies with GDPR and privacy laws. We have no record of your personal data.

Thank you for using our nutrition assistant. Take care! 👋

*This number will no longer receive messages from us.*"""
            
            return {"success": True, "response": response, "delete_user": True}
        else:
            return {"success": False, "response": f"❌ Deletion failed: {result['error']}"}
    
    def _handle_privacy_command(self, user_id: str, phone: str) -> Dict[str, Any]:
        """Provide privacy rights information"""
        
        response = """🛡️ **YOUR PRIVACY RIGHTS**

**DATA WE COLLECT:**
• Nutrition preferences and dietary goals
• Meal plans and tracking data you provide
• Messages for improving our service

**YOUR RIGHTS (GDPR):**
✅ **Access** - See all your data (reply DATA)
✅ **Rectify** - Update incorrect information  
✅ **Erase** - Delete everything (reply DELETE)
✅ **Port** - Download your data (reply EXPORT)
✅ **Object** - Stop processing (reply UNLINK)
✅ **Withdraw** - Remove consent anytime

**DATA SHARING:**
• Only shared with people YOU invite and accept
• You control exactly what data is shared
• You can stop sharing anytime (reply UNLINK)

**SECURITY:**
• Encrypted storage and transmission
• No sale to third parties
• Minimal data retention

Full privacy policy: https://ai-nutritionist.com/privacy
Questions? Email: privacy@ai-nutritionist.com"""
        
        return {"success": True, "response": response}
    
    def _handle_family_status_command(self, user_id: str, phone: str) -> Dict[str, Any]:
        """Show family linking status"""
        
        relationships = self.linking_service._get_user_relationships(user_id)
        
        if not relationships:
            response = """👥 **FAMILY STATUS**

You're not currently linked with anyone.

**TO LINK WITH FAMILY:**
• Text: "invite +1234567890" (their phone number)
• They'll get a secure invite to accept or decline
• Only shared data they explicitly consent to

**PRIVACY PROMISE:**
• No one can link to you without your permission
• You control all data sharing
• Easy to unlink anytime"""
            
            return {"success": True, "response": response}
        
        response = "👥 **FAMILY STATUS**\n\n**LINKED WITH:**\n"
        
        for rel in relationships:
            other_user_id = rel["primary_user_id"] if rel["linked_user_id"] == user_id else rel["linked_user_id"]
            other_user = self.user_service.get_user(other_user_id)
            name = other_user.get("name", "Family Member")
            phone_display = other_user.get("phone", "Unknown")[-4:]  # Last 4 digits for privacy
            
            response += f"• {name} (...{phone_display})\n"
            response += f"  Role: {rel['relationship_type'].title()}\n"
            response += f"  Sharing: {', '.join(rel['permissions'])}\n\n"
        
        response += """**CONTROLS:**
• Text UNLINK to stop sharing with someone
• Text PERMISSIONS to modify what you share
• Text PRIVACY for your data rights"""
        
        return {"success": True, "response": response}
    
    def _handle_otp_verification(self, user_id: str, phone: str, otp: str, 
                                full_message: str) -> Dict[str, Any]:
        """Handle standalone OTP verification"""
        
        # Check if this looks like an acceptance with consent
        if re.search(r"\b(YES|ACCEPT|AGREE|CONSENT)\b", full_message.upper()):
            return self._handle_accept_command(user_id, phone, otp, full_message)
        
        # Just OTP without explicit consent
        return {
            "success": False,
            "response": f"""⚠️ **CONSENT REQUIRED**

I see your verification code: {otp}

To complete linking, please also reply **YES** to give explicit consent for data sharing.

Example: "{otp} YES"

This confirms you understand and agree to share nutrition data."""
        }
    
    def _infer_role_and_permissions(self, message: str) -> tuple[LinkingRole, List[DataSharingPermission]]:
        """
        Infer role and permissions from invite message context
        """
        
        message_lower = message.lower()
        
        # Check for child/kid mentions
        if any(word in message_lower for word in ["child", "kid", "son", "daughter", "teen"]):
            return LinkingRole.CHILD, [
                DataSharingPermission.MEAL_PLANS,
                DataSharingPermission.DIETARY_PREFERENCES,
                DataSharingPermission.HEALTH_GOALS
            ]
        
        # Check for partner/spouse mentions  
        if any(word in message_lower for word in ["partner", "spouse", "wife", "husband", "boyfriend", "girlfriend"]):
            return LinkingRole.FAMILY_MEMBER, [
                DataSharingPermission.MEAL_PLANS,
                DataSharingPermission.GROCERY_LISTS,
                DataSharingPermission.NUTRITION_TRACKING,
                DataSharingPermission.HEALTH_GOALS,
                DataSharingPermission.PROGRESS_REPORTS
            ]
        
        # Check for viewer-only mentions
        if any(word in message_lower for word in ["view", "see", "check", "monitor"]):
            return LinkingRole.VIEWER, [
                DataSharingPermission.PROGRESS_REPORTS,
                DataSharingPermission.HEALTH_GOALS
            ]
        
        # Default: family member with standard permissions
        return LinkingRole.FAMILY_MEMBER, [
            DataSharingPermission.MEAL_PLANS,
            DataSharingPermission.GROCERY_LISTS,
            DataSharingPermission.DIETARY_PREFERENCES,
            DataSharingPermission.HEALTH_GOALS
        ]
    
    def handle_action_followup(self, user_id: str, phone: str, message: str, 
                              pending_action: str) -> Dict[str, Any]:
        """
        Handle follow-up actions for multi-step linking processes
        """
        
        if pending_action == "confirm_deletion":
            if "DELETE CONFIRMED" in message.upper():
                return self._handle_delete_confirmation(user_id, phone)
            else:
                return {
                    "success": True,
                    "response": "Deletion cancelled. Your data is safe! 😊"
                }
        
        elif pending_action == "select_unlink":
            # Handle numeric selection for unlinking specific relationships
            if message.upper() == "ALL":
                # Unlink all relationships
                relationships = self.linking_service._get_user_relationships(user_id)
                for rel in relationships:
                    other_user_id = rel["primary_user_id"] if rel["linked_user_id"] == user_id else rel["linked_user_id"]
                    self.linking_service.unlink_users(user_id, other_user_id)
                
                return {
                    "success": True,
                    "response": "✅ Unlinked from everyone. All data sharing has stopped."
                }
            
            # Handle numeric selection
            try:
                selection = int(message.strip())
                relationships = self.linking_service._get_user_relationships(user_id)
                
                if 1 <= selection <= len(relationships):
                    rel = relationships[selection - 1]
                    other_user_id = rel["primary_user_id"] if rel["linked_user_id"] == user_id else rel["linked_user_id"]
                    
                    result = self.linking_service.unlink_users(user_id, other_user_id)
                    
                    if result["success"]:
                        return {
                            "success": True,
                            "response": "✅ Unlinked successfully. Data sharing stopped."
                        }
                    else:
                        return {
                            "success": False,
                            "response": f"❌ Couldn't unlink: {result['error']}"
                        }
                else:
                    return {
                        "success": False,
                        "response": "Please select a valid number from the list, or reply ALL."
                    }
                    
            except ValueError:
                return {
                    "success": False,
                    "response": "Please reply with a number from the list, or ALL to unlink everyone."
                }
        
        return {"success": False, "handled": False}
