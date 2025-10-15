"""Feature flag administration and lifecycle management."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .models import (
    FeatureFlagDefinition,
    FlagAuditEvent,
    FlagCleanupRule,
    FlagStatus,
    FlagUsageMetrics,
)
from .service import FeatureFlagService


logger = logging.getLogger(__name__)


class FlagAdminService:
    """Administrative interface for feature flag management."""
    
    def __init__(
        self,
        flag_service: FeatureFlagService,
        audit_storage: Optional['AuditStorage'] = None,
    ):
        self.flag_service = flag_service
        self.audit_storage = audit_storage or InMemoryAuditStorage()
        self._admin_users: Set[str] = set()
    
    def add_admin_user(self, user_id: str) -> None:
        """Add user to admin list."""
        self._admin_users.add(user_id)
    
    def remove_admin_user(self, user_id: str) -> None:
        """Remove user from admin list."""
        self._admin_users.discard(user_id)
    
    def is_admin(self, user_id: str) -> bool:
        """Check if user is admin."""
        return user_id in self._admin_users
    
    async def create_flag(
        self,
        flag: FeatureFlagDefinition,
        admin_user_id: str,
        reason: Optional[str] = None,
    ) -> FeatureFlagDefinition:
        """Create a new feature flag."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to create flags")
        
        # Register flag
        await self.flag_service.register_flag(flag)
        
        # Log audit event
        await self.audit_storage.log_event(
            FlagAuditEvent(
                flag_key=flag.key,
                event_type="created",
                user_id=admin_user_id,
                new_value=flag.model_dump(),
                environment=flag.environment,
                reason=reason,
            )
        )
        
        logger.info(f"Flag created: {flag.key} by {admin_user_id}")
        return flag
    
    async def update_flag(
        self,
        flag_key: str,
        updates: Dict[str, Any],
        admin_user_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """Update an existing feature flag."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to update flags")
        
        # Get current flag for audit
        current_flag = self.flag_service._flags.get(flag_key)
        if not current_flag:
            raise ValueError(f"Flag {flag_key} not found")
        
        previous_value = current_flag.model_dump()
        
        # Update flag
        await self.flag_service.update_flag(flag_key, updates)
        
        # Get updated flag
        updated_flag = self.flag_service._flags[flag_key]
        new_value = updated_flag.model_dump()
        
        # Log audit event
        await self.audit_storage.log_event(
            FlagAuditEvent(
                flag_key=flag_key,
                event_type="updated",
                user_id=admin_user_id,
                previous_value=previous_value,
                new_value=new_value,
                environment=updated_flag.environment,
                reason=reason,
            )
        )
        
        logger.info(f"Flag updated: {flag_key} by {admin_user_id}")
    
    async def toggle_flag(
        self,
        flag_key: str,
        admin_user_id: str,
        reason: Optional[str] = None,
    ) -> FlagStatus:
        """Toggle flag status between active and inactive."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to toggle flags")
        
        current_flag = self.flag_service._flags.get(flag_key)
        if not current_flag:
            raise ValueError(f"Flag {flag_key} not found")
        
        # Toggle status
        new_status = (
            FlagStatus.INACTIVE 
            if current_flag.status == FlagStatus.ACTIVE 
            else FlagStatus.ACTIVE
        )
        
        await self.update_flag(
            flag_key,
            {"status": new_status},
            admin_user_id,
            reason or f"Toggled to {new_status}",
        )
        
        return new_status
    
    async def enable_kill_switch(
        self,
        flag_key: str,
        admin_user_id: str,
        reason: str,
    ) -> None:
        """Enable emergency kill switch for a flag."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to enable kill switch")
        
        await self.update_flag(
            flag_key,
            {"kill_switch": True},
            admin_user_id,
            f"Kill switch enabled: {reason}",
        )
        
        logger.warning(f"Kill switch enabled for {flag_key} by {admin_user_id}: {reason}")
    
    async def disable_kill_switch(
        self,
        flag_key: str,
        admin_user_id: str,
        reason: str,
    ) -> None:
        """Disable emergency kill switch for a flag."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to disable kill switch")
        
        await self.update_flag(
            flag_key,
            {"kill_switch": False},
            admin_user_id,
            f"Kill switch disabled: {reason}",
        )
        
        logger.info(f"Kill switch disabled for {flag_key} by {admin_user_id}: {reason}")
    
    async def archive_flag(
        self,
        flag_key: str,
        admin_user_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """Archive a feature flag."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to archive flags")
        
        await self.update_flag(
            flag_key,
            {"status": FlagStatus.ARCHIVED},
            admin_user_id,
            reason or "Flag archived",
        )
        
        logger.info(f"Flag archived: {flag_key} by {admin_user_id}")
    
    async def get_flag_audit_history(
        self,
        flag_key: str,
        limit: int = 100,
    ) -> List[FlagAuditEvent]:
        """Get audit history for a flag."""
        return await self.audit_storage.get_flag_history(flag_key, limit)
    
    async def get_user_audit_history(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[FlagAuditEvent]:
        """Get audit history for a user."""
        return await self.audit_storage.get_user_history(user_id, limit)
    
    async def bulk_update_flags(
        self,
        updates: Dict[str, Dict[str, Any]],
        admin_user_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Bulk update multiple flags."""
        if not self.is_admin(admin_user_id):
            raise PermissionError("User is not authorized to bulk update flags")
        
        results = {}
        
        for flag_key, flag_updates in updates.items():
            try:
                await self.update_flag(flag_key, flag_updates, admin_user_id, reason)
                results[flag_key] = True
            except Exception as e:
                logger.error(f"Bulk update failed for {flag_key}: {e}")
                results[flag_key] = False
        
        return results


class FlagLifecycleManager:
    """Manages feature flag lifecycle and automated transitions."""
    
    def __init__(
        self,
        admin_service: FlagAdminService,
        metrics_storage: Optional['MetricsStorage'] = None,
    ):
        self.admin_service = admin_service
        self.metrics_storage = metrics_storage or InMemoryMetricsStorage()
        self._lifecycle_rules: List[Dict[str, Any]] = []
    
    def add_lifecycle_rule(
        self,
        name: str,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        description: Optional[str] = None,
    ) -> None:
        """Add a lifecycle rule."""
        rule = {
            "id": str(uuid4()),
            "name": name,
            "description": description,
            "conditions": conditions,
            "actions": actions,
            "created_at": datetime.utcnow(),
        }
        self._lifecycle_rules.append(rule)
        logger.info(f"Lifecycle rule added: {name}")
    
    async def check_lifecycle_rules(self, admin_user_id: str) -> Dict[str, List[str]]:
        """Check and apply lifecycle rules."""
        results = {"applied": [], "failed": []}
        
        for rule in self._lifecycle_rules:
            try:
                flags_to_process = await self._find_flags_matching_conditions(
                    rule["conditions"]
                )
                
                for flag_key in flags_to_process:
                    await self._apply_lifecycle_actions(
                        flag_key, rule["actions"], admin_user_id, rule["name"]
                    )
                    results["applied"].append(f"{flag_key}: {rule['name']}")
                
            except Exception as e:
                logger.error(f"Lifecycle rule failed: {rule['name']}: {e}")
                results["failed"].append(f"{rule['name']}: {str(e)}")
        
        return results
    
    async def _find_flags_matching_conditions(
        self, conditions: Dict[str, Any]
    ) -> List[str]:
        """Find flags matching lifecycle conditions."""
        matching_flags = []
        
        for flag_key, flag in self.admin_service.flag_service._flags.items():
            if await self._flag_matches_conditions(flag, conditions):
                matching_flags.append(flag_key)
        
        return matching_flags
    
    async def _flag_matches_conditions(
        self, flag: FeatureFlagDefinition, conditions: Dict[str, Any]
    ) -> bool:
        """Check if flag matches lifecycle conditions."""
        # Check age condition
        if "age_days" in conditions:
            age_days = (datetime.utcnow() - flag.created_at).days
            if age_days < conditions["age_days"]:
                return False
        
        # Check status condition
        if "status" in conditions:
            if flag.status != FlagStatus(conditions["status"]):
                return False
        
        # Check last evaluation condition
        if "last_evaluation_days" in conditions:
            metrics = await self.metrics_storage.get_flag_metrics(flag.key)
            if metrics and metrics.last_evaluated:
                days_since_eval = (datetime.utcnow() - metrics.last_evaluated).days
                if days_since_eval < conditions["last_evaluation_days"]:
                    return False
        
        # Check tags condition
        if "tags" in conditions:
            required_tags = set(conditions["tags"])
            flag_tags = set(flag.tags)
            if not required_tags.issubset(flag_tags):
                return False
        
        return True
    
    async def _apply_lifecycle_actions(
        self,
        flag_key: str,
        actions: Dict[str, Any],
        admin_user_id: str,
        rule_name: str,
    ) -> None:
        """Apply lifecycle actions to a flag."""
        reason = f"Automated by lifecycle rule: {rule_name}"
        
        if actions.get("archive"):
            await self.admin_service.archive_flag(flag_key, admin_user_id, reason)
        
        if actions.get("deactivate"):
            await self.admin_service.update_flag(
                flag_key, {"status": FlagStatus.INACTIVE}, admin_user_id, reason
            )
        
        if "update" in actions:
            await self.admin_service.update_flag(
                flag_key, actions["update"], admin_user_id, reason
            )


class FlagCleanupService:
    """Service for automated flag cleanup."""
    
    def __init__(
        self,
        admin_service: FlagAdminService,
        lifecycle_manager: FlagLifecycleManager,
    ):
        self.admin_service = admin_service
        self.lifecycle_manager = lifecycle_manager
        self._cleanup_rules: List[FlagCleanupRule] = []
        self._cleanup_running = False
    
    def add_cleanup_rule(self, rule: FlagCleanupRule) -> None:
        """Add a cleanup rule."""
        self._cleanup_rules.append(rule)
        logger.info(f"Cleanup rule added: {rule.name}")
    
    async def run_cleanup(self, admin_user_id: str) -> Dict[str, Any]:
        """Run cleanup process."""
        if self._cleanup_running:
            return {"status": "already_running"}
        
        self._cleanup_running = True
        results = {
            "started_at": datetime.utcnow(),
            "rules_processed": 0,
            "flags_affected": [],
            "notifications_sent": [],
            "errors": [],
        }
        
        try:
            for rule in self._cleanup_rules:
                if not rule.enabled:
                    continue
                
                try:
                    rule_results = await self._process_cleanup_rule(rule, admin_user_id)
                    results["rules_processed"] += 1
                    results["flags_affected"].extend(rule_results.get("flags_affected", []))
                    results["notifications_sent"].extend(rule_results.get("notifications", []))
                    
                except Exception as e:
                    logger.error(f"Cleanup rule failed: {rule.name}: {e}")
                    results["errors"].append(f"{rule.name}: {str(e)}")
            
            results["completed_at"] = datetime.utcnow()
            results["status"] = "completed"
            
        finally:
            self._cleanup_running = False
        
        return results
    
    async def _process_cleanup_rule(
        self, rule: FlagCleanupRule, admin_user_id: str
    ) -> Dict[str, Any]:
        """Process a single cleanup rule."""
        results = {"flags_affected": [], "notifications": []}
        
        # Find flags matching rule conditions
        matching_flags = []
        
        for flag_key, flag in self.admin_service.flag_service._flags.items():
            if await self._flag_matches_cleanup_rule(flag, rule):
                matching_flags.append(flag)
        
        # Send notifications if configured
        if rule.notify_users and matching_flags:
            for user_id in rule.notify_users:
                await self._send_cleanup_notification(
                    user_id, rule, matching_flags
                )
                results["notifications"].append(user_id)
        
        # Apply cleanup action
        for flag in matching_flags:
            reason = f"Automated cleanup: {rule.name}"
            
            if rule.action == "archive":
                await self.admin_service.archive_flag(
                    flag.key, admin_user_id, reason
                )
                results["flags_affected"].append(f"archived:{flag.key}")
            
            elif rule.action == "delete":
                # Note: Implement delete functionality if needed
                logger.warning(f"Delete action not implemented for {flag.key}")
            
            elif rule.action == "notify":
                # Already handled above
                pass
        
        return results
    
    async def _flag_matches_cleanup_rule(
        self, flag: FeatureFlagDefinition, rule: FlagCleanupRule
    ) -> bool:
        """Check if flag matches cleanup rule conditions."""
        # Check age
        if rule.flag_age_days:
            age_days = (datetime.utcnow() - flag.created_at).days
            if age_days < rule.flag_age_days:
                return False
        
        # Check status
        if rule.flag_status and flag.status != rule.flag_status:
            return False
        
        # Check last evaluation
        if rule.last_evaluation_days:
            metrics = await self.lifecycle_manager.metrics_storage.get_flag_metrics(
                flag.key
            )
            if metrics and metrics.last_evaluated:
                days_since_eval = (datetime.utcnow() - metrics.last_evaluated).days
                if days_since_eval < rule.last_evaluation_days:
                    return False
            elif not metrics:
                # No metrics means never evaluated, consider for cleanup
                pass
        
        # Check tags
        if rule.tags:
            flag_tags = set(flag.tags)
            rule_tags = set(rule.tags)
            if not rule_tags.intersection(flag_tags):
                return False
        
        return True
    
    async def _send_cleanup_notification(
        self,
        user_id: str,
        rule: FlagCleanupRule,
        flags: List[FeatureFlagDefinition],
    ) -> None:
        """Send cleanup notification to user."""
        # Implement notification sending (email, Slack, etc.)
        message = f"""
        Cleanup Rule: {rule.name}
        
        The following flags match cleanup criteria:
        {', '.join([flag.key for flag in flags])}
        
        Action: {rule.action}
        Description: {rule.description or 'No description'}
        """
        
        logger.info(f"Cleanup notification sent to {user_id}: {len(flags)} flags")


# Storage interfaces

class AuditStorage:
    """Interface for audit event storage."""
    
    async def log_event(self, event: FlagAuditEvent) -> None:
        """Log an audit event."""
        raise NotImplementedError
    
    async def get_flag_history(
        self, flag_key: str, limit: int = 100
    ) -> List[FlagAuditEvent]:
        """Get audit history for a flag."""
        raise NotImplementedError
    
    async def get_user_history(
        self, user_id: str, limit: int = 100
    ) -> List[FlagAuditEvent]:
        """Get audit history for a user."""
        raise NotImplementedError


class InMemoryAuditStorage(AuditStorage):
    """In-memory implementation of audit storage."""
    
    def __init__(self):
        self._events: List[FlagAuditEvent] = []
    
    async def log_event(self, event: FlagAuditEvent) -> None:
        """Log an audit event."""
        self._events.append(event)
    
    async def get_flag_history(
        self, flag_key: str, limit: int = 100
    ) -> List[FlagAuditEvent]:
        """Get audit history for a flag."""
        flag_events = [
            event for event in self._events 
            if event.flag_key == flag_key
        ]
        return sorted(flag_events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    async def get_user_history(
        self, user_id: str, limit: int = 100
    ) -> List[FlagAuditEvent]:
        """Get audit history for a user."""
        user_events = [
            event for event in self._events 
            if event.user_id == user_id
        ]
        return sorted(user_events, key=lambda e: e.timestamp, reverse=True)[:limit]


class MetricsStorage:
    """Interface for metrics storage."""
    
    async def store_flag_metrics(self, metrics: FlagUsageMetrics) -> None:
        """Store flag usage metrics."""
        raise NotImplementedError
    
    async def get_flag_metrics(self, flag_key: str) -> Optional[FlagUsageMetrics]:
        """Get flag usage metrics."""
        raise NotImplementedError


class InMemoryMetricsStorage(MetricsStorage):
    """In-memory implementation of metrics storage."""
    
    def __init__(self):
        self._metrics: Dict[str, FlagUsageMetrics] = {}
    
    async def store_flag_metrics(self, metrics: FlagUsageMetrics) -> None:
        """Store flag usage metrics."""
        self._metrics[metrics.flag_key] = metrics
    
    async def get_flag_metrics(self, flag_key: str) -> Optional[FlagUsageMetrics]:
        """Get flag usage metrics."""
        return self._metrics.get(flag_key)
