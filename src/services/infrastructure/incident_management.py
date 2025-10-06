"""
G5 - Runbooks & Incident Management
Incident severity classification, on-call procedures, rollback checklists, and disaster recovery.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
import threading
from pathlib import Path

# Try importing optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    SEV1 = "sev1"  # Critical - Service down, data loss
    SEV2 = "sev2"  # High - Major feature broken, performance degraded
    SEV3 = "sev3"  # Medium - Minor feature issues, workaround available
    SEV4 = "sev4"  # Low - Cosmetic issues, feature requests


class IncidentStatus(str, Enum):
    """Incident status states."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AlertChannel(str, Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


class ServiceStatus(str, Enum):
    """Service operational status."""
    OPERATIONAL = "operational"
    DEGRADED_PERFORMANCE = "degraded_performance"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    MAINTENANCE = "maintenance"


@dataclass
class Incident:
    """Incident record."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    created_by: str
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    service_affected: Optional[str] = None
    customer_impact: Optional[str] = None
    root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class OnCallSchedule:
    """On-call schedule entry."""
    engineer: str
    start_time: datetime
    end_time: datetime
    primary: bool = True  # Primary or backup
    contact_info: Dict[str, str] = field(default_factory=dict)  # email, phone, slack


@dataclass
class Runbook:
    """Operational runbook."""
    name: str
    description: str
    category: str  # e.g., "deployment", "incident_response", "maintenance"
    steps: List[Dict[str, Any]]
    prerequisites: List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None  # minutes
    author: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RollbackPlan:
    """Rollback plan for deployments."""
    deployment_id: str
    service_name: str
    rollback_steps: List[Dict[str, Any]]
    validation_steps: List[Dict[str, Any]]
    estimated_duration: int  # minutes
    requires_downtime: bool = False
    database_changes: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.alert_channels: Dict[AlertChannel, Dict[str, Any]] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self._configure_default_channels()
    
    def _configure_default_channels(self):
        """Configure default alert channels."""
        # Email configuration
        self.alert_channels[AlertChannel.EMAIL] = {
            "enabled": True,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "sender": "alerts@ainutritionist.com",
            "recipients": {
                "sev1": ["oncall@ainutritionist.com", "management@ainutritionist.com"],
                "sev2": ["oncall@ainutritionist.com"],
                "sev3": ["engineering@ainutritionist.com"],
                "sev4": ["engineering@ainutritionist.com"]
            }
        }
        
        # Slack configuration
        self.alert_channels[AlertChannel.SLACK] = {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
            "channels": {
                "sev1": "#incidents-critical",
                "sev2": "#incidents-high",
                "sev3": "#engineering-alerts",
                "sev4": "#engineering-alerts"
            }
        }
    
    def send_alert(
        self,
        severity: IncidentSeverity,
        title: str,
        message: str,
        channels: Optional[List[AlertChannel]] = None
    ) -> bool:
        """Send alert through configured channels."""
        if channels is None:
            channels = [AlertChannel.EMAIL, AlertChannel.SLACK]
        
        success = True
        
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email_alert(severity, title, message)
                elif channel == AlertChannel.SLACK:
                    self._send_slack_alert(severity, title, message)
                # Add other channels as needed
            except Exception as e:
                print(f"Failed to send alert via {channel}: {e}")
                success = False
        
        return success
    
    def _send_email_alert(self, severity: IncidentSeverity, title: str, message: str):
        """Send email alert."""
        # Placeholder - would integrate with actual email service
        config = self.alert_channels[AlertChannel.EMAIL]
        recipients = config["recipients"].get(severity.value, [])
        
        print(f"EMAIL ALERT [{severity.value.upper()}]: {title}")
        print(f"To: {', '.join(recipients)}")
        print(f"Message: {message}")
    
    def _send_slack_alert(self, severity: IncidentSeverity, title: str, message: str):
        """Send Slack alert."""
        # Placeholder - would integrate with actual Slack API
        config = self.alert_channels[AlertChannel.SLACK]
        channel = config["channels"].get(severity.value, "#general")
        
        print(f"SLACK ALERT [{severity.value.upper()}] to {channel}: {title}")
        print(f"Message: {message}")


class OnCallManager:
    """Manages on-call schedules and escalation."""
    
    def __init__(self):
        self.schedules: List[OnCallSchedule] = []
        self.escalation_policy: Dict[IncidentSeverity, List[str]] = {}
        self._setup_default_schedules()
        self._setup_escalation_policy()
    
    def _setup_default_schedules(self):
        """Setup default on-call schedules."""
        # Example weekly rotation
        base_time = datetime.utcnow()
        
        # Primary on-call
        self.schedules.append(OnCallSchedule(
            engineer="alice@ainutritionist.com",
            start_time=base_time,
            end_time=base_time + timedelta(days=7),
            primary=True,
            contact_info={
                "email": "alice@ainutritionist.com",
                "phone": "+1-555-0101",
                "slack": "@alice"
            }
        ))
        
        # Backup on-call
        self.schedules.append(OnCallSchedule(
            engineer="bob@ainutritionist.com",
            start_time=base_time,
            end_time=base_time + timedelta(days=7),
            primary=False,
            contact_info={
                "email": "bob@ainutritionist.com",
                "phone": "+1-555-0102",
                "slack": "@bob"
            }
        ))
    
    def _setup_escalation_policy(self):
        """Setup incident escalation policy."""
        self.escalation_policy = {
            IncidentSeverity.SEV1: [
                "primary_oncall",
                "backup_oncall",
                "engineering_manager",
                "cto"
            ],
            IncidentSeverity.SEV2: [
                "primary_oncall",
                "backup_oncall",
                "engineering_manager"
            ],
            IncidentSeverity.SEV3: [
                "primary_oncall",
                "backup_oncall"
            ],
            IncidentSeverity.SEV4: [
                "primary_oncall"
            ]
        }
    
    def get_current_oncall(self, primary: bool = True) -> Optional[OnCallSchedule]:
        """Get current on-call engineer."""
        current_time = datetime.utcnow()
        
        for schedule in self.schedules:
            if (schedule.primary == primary and 
                schedule.start_time <= current_time <= schedule.end_time):
                return schedule
        
        return None
    
    def escalate_incident(self, incident_id: str, severity: IncidentSeverity) -> List[str]:
        """Get escalation contacts for incident."""
        escalation_levels = self.escalation_policy.get(severity, ["primary_oncall"])
        
        contacts = []
        for level in escalation_levels:
            if level == "primary_oncall":
                oncall = self.get_current_oncall(primary=True)
                if oncall:
                    contacts.append(oncall.engineer)
            elif level == "backup_oncall":
                oncall = self.get_current_oncall(primary=False)
                if oncall:
                    contacts.append(oncall.engineer)
            else:
                # Would lookup from employee directory
                contacts.append(f"{level}@ainutritionist.com")
        
        return contacts


class RunbookManager:
    """Manages operational runbooks."""
    
    def __init__(self):
        self.runbooks: Dict[str, Runbook] = {}
        self._create_default_runbooks()
    
    def _create_default_runbooks(self):
        """Create default operational runbooks."""
        
        # Incident Response Runbook
        self.add_runbook(Runbook(
            name="incident_response",
            description="General incident response procedure",
            category="incident_response",
            steps=[
                {
                    "step": 1,
                    "title": "Acknowledge Incident",
                    "description": "Acknowledge the incident and notify stakeholders",
                    "actions": [
                        "Update incident status to 'acknowledged'",
                        "Send initial communication to stakeholders",
                        "Assemble incident response team if needed"
                    ]
                },
                {
                    "step": 2,
                    "title": "Assess Impact",
                    "description": "Assess the scope and impact of the incident",
                    "actions": [
                        "Check service health dashboards",
                        "Review error rates and metrics",
                        "Identify affected customers/features"
                    ]
                },
                {
                    "step": 3,
                    "title": "Mitigate",
                    "description": "Take immediate action to reduce impact",
                    "actions": [
                        "Apply temporary fixes or workarounds",
                        "Scale resources if needed",
                        "Rollback recent changes if suspected cause"
                    ]
                },
                {
                    "step": 4,
                    "title": "Investigate",
                    "description": "Find the root cause",
                    "actions": [
                        "Review logs and metrics",
                        "Check recent deployments",
                        "Analyze error patterns"
                    ]
                },
                {
                    "step": 5,
                    "title": "Resolve",
                    "description": "Fix the underlying issue",
                    "actions": [
                        "Deploy permanent fix",
                        "Verify resolution",
                        "Monitor for recurrence"
                    ]
                },
                {
                    "step": 6,
                    "title": "Post-Mortem",
                    "description": "Document lessons learned",
                    "actions": [
                        "Write incident report",
                        "Identify prevention measures",
                        "Update runbooks if needed"
                    ]
                }
            ],
            estimated_duration=60,
            author="engineering@ainutritionist.com"
        ))
        
        # Database Backup Restore Runbook
        self.add_runbook(Runbook(
            name="database_restore",
            description="Database backup and restore procedure",
            category="maintenance",
            steps=[
                {
                    "step": 1,
                    "title": "Stop Application Traffic",
                    "description": "Stop write traffic to database",
                    "actions": [
                        "Enable maintenance mode",
                        "Stop application servers",
                        "Verify no active connections"
                    ]
                },
                {
                    "step": 2,
                    "title": "Create Backup",
                    "description": "Create current database backup",
                    "actions": [
                        "Run pg_dump or equivalent",
                        "Store backup in secure location",
                        "Verify backup integrity"
                    ]
                },
                {
                    "step": 3,
                    "title": "Restore from Backup",
                    "description": "Restore database from backup",
                    "actions": [
                        "Drop current database (if safe)",
                        "Restore from backup file",
                        "Run database migrations if needed"
                    ]
                },
                {
                    "step": 4,
                    "title": "Verify Restoration",
                    "description": "Verify data integrity",
                    "actions": [
                        "Run data validation queries",
                        "Check row counts",
                        "Verify critical data"
                    ]
                },
                {
                    "step": 5,
                    "title": "Resume Operations",
                    "description": "Bring services back online",
                    "actions": [
                        "Start application servers",
                        "Disable maintenance mode",
                        "Monitor for issues"
                    ]
                }
            ],
            prerequisites=["Database admin access", "Recent backup available"],
            estimated_duration=120,
            author="dba@ainutritionist.com"
        ))
        
        # Deployment Rollback Runbook
        self.add_runbook(Runbook(
            name="deployment_rollback",
            description="Rollback failed deployment",
            category="deployment",
            steps=[
                {
                    "step": 1,
                    "title": "Stop Current Deployment",
                    "description": "Stop the failed deployment process",
                    "actions": [
                        "Cancel deployment pipeline",
                        "Stop traffic to new version",
                        "Preserve logs for analysis"
                    ]
                },
                {
                    "step": 2,
                    "title": "Rollback Code",
                    "description": "Revert to previous version",
                    "actions": [
                        "Checkout previous git commit",
                        "Deploy previous container image",
                        "Update configuration if needed"
                    ]
                },
                {
                    "step": 3,
                    "title": "Rollback Database",
                    "description": "Revert database changes if needed",
                    "actions": [
                        "Run down migrations",
                        "Restore from backup if necessary",
                        "Verify data consistency"
                    ]
                },
                {
                    "step": 4,
                    "title": "Validate Rollback",
                    "description": "Ensure services are working",
                    "actions": [
                        "Run health checks",
                        "Test critical user flows",
                        "Monitor error rates"
                    ]
                },
                {
                    "step": 5,
                    "title": "Communicate",
                    "description": "Update stakeholders",
                    "actions": [
                        "Notify deployment failure",
                        "Update status page",
                        "Schedule post-mortem"
                    ]
                }
            ],
            estimated_duration=30,
            author="devops@ainutritionist.com"
        ))
    
    def add_runbook(self, runbook: Runbook):
        """Add runbook to collection."""
        self.runbooks[runbook.name] = runbook
    
    def get_runbook(self, name: str) -> Optional[Runbook]:
        """Get runbook by name."""
        return self.runbooks.get(name)
    
    def list_runbooks(self, category: Optional[str] = None) -> List[Runbook]:
        """List runbooks, optionally filtered by category."""
        if category:
            return [rb for rb in self.runbooks.values() if rb.category == category]
        return list(self.runbooks.values())


class DisasterRecoveryManager:
    """Manages disaster recovery plans and procedures."""
    
    def __init__(self):
        self.recovery_plans: Dict[str, Dict[str, Any]] = {}
        self.recovery_objectives = {
            "RTO": 4,  # Recovery Time Objective: 4 hours
            "RPO": 1   # Recovery Point Objective: 1 hour
        }
        self._create_default_plans()
    
    def _create_default_plans(self):
        """Create default disaster recovery plans."""
        
        # Database Disaster Recovery
        self.recovery_plans["database_failure"] = {
            "name": "Database Disaster Recovery",
            "description": "Recovery plan for complete database failure",
            "triggers": [
                "Database server hardware failure",
                "Database corruption",
                "Data center outage affecting primary database"
            ],
            "steps": [
                {
                    "step": 1,
                    "title": "Activate DR Site",
                    "description": "Switch to disaster recovery database",
                    "estimated_time": 30,  # minutes
                    "actions": [
                        "Verify DR database is current",
                        "Update DNS to point to DR database",
                        "Start application servers with DR config"
                    ]
                },
                {
                    "step": 2,
                    "title": "Data Verification",
                    "description": "Verify data integrity in DR environment",
                    "estimated_time": 60,
                    "actions": [
                        "Run data consistency checks",
                        "Verify recent transactions",
                        "Check backup recency"
                    ]
                },
                {
                    "step": 3,
                    "title": "Service Restoration",
                    "description": "Restore full service functionality",
                    "estimated_time": 30,
                    "actions": [
                        "Update load balancer configuration",
                        "Test critical user flows",
                        "Monitor system performance"
                    ]
                }
            ],
            "total_estimated_time": 120,  # minutes
            "stakeholders": [
                "Database Administrator",
                "DevOps Engineer",
                "Engineering Manager"
            ]
        }
        
        # Application Server Failure
        self.recovery_plans["application_failure"] = {
            "name": "Application Server Recovery",
            "description": "Recovery from application server failures",
            "triggers": [
                "Multiple application server failures",
                "Container orchestration system failure",
                "Critical application bugs causing service unavailability"
            ],
            "steps": [
                {
                    "step": 1,
                    "title": "Scale Healthy Instances",
                    "description": "Scale up working application instances",
                    "estimated_time": 10,
                    "actions": [
                        "Increase replica count in healthy regions",
                        "Update load balancer health checks",
                        "Monitor resource utilization"
                    ]
                },
                {
                    "step": 2,
                    "title": "Deploy Previous Version",
                    "description": "Rollback to last known good version",
                    "estimated_time": 20,
                    "actions": [
                        "Deploy previous container image",
                        "Update configuration if needed",
                        "Verify deployment success"
                    ]
                },
                {
                    "step": 3,
                    "title": "Validate Recovery",
                    "description": "Ensure service is fully operational",
                    "estimated_time": 15,
                    "actions": [
                        "Run automated health checks",
                        "Test key user journeys",
                        "Monitor error rates and latency"
                    ]
                }
            ],
            "total_estimated_time": 45,
            "stakeholders": [
                "DevOps Engineer",
                "Platform Engineer",
                "Engineering Manager"
            ]
        }
    
    def get_recovery_plan(self, disaster_type: str) -> Optional[Dict[str, Any]]:
        """Get disaster recovery plan."""
        return self.recovery_plans.get(disaster_type)
    
    def list_recovery_plans(self) -> List[str]:
        """List available recovery plans."""
        return list(self.recovery_plans.keys())


class IncidentManager:
    """
    Comprehensive incident management system.
    Handles incident creation, tracking, escalation, and resolution.
    """
    
    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.alert_manager = AlertManager()
        self.oncall_manager = OnCallManager()
        self.runbook_manager = RunbookManager()
        self.dr_manager = DisasterRecoveryManager()
        self._lock = threading.Lock()
    
    def create_incident(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        created_by: str,
        service_affected: Optional[str] = None,
        customer_impact: Optional[str] = None
    ) -> Incident:
        """Create new incident."""
        with self._lock:
            incident_id = str(uuid.uuid4())
            
            incident = Incident(
                incident_id=incident_id,
                title=title,
                description=description,
                severity=severity,
                status=IncidentStatus.OPEN,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=created_by,
                service_affected=service_affected,
                customer_impact=customer_impact
            )
            
            # Add creation to timeline
            incident.timeline.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "incident_created",
                "user": created_by,
                "details": f"Incident created with severity {severity.value}"
            })
            
            self.incidents[incident_id] = incident
            
            # Auto-assign to on-call
            oncall = self.oncall_manager.get_current_oncall(primary=True)
            if oncall:
                incident.assigned_to = oncall.engineer
            
            # Send alerts
            self.alert_manager.send_alert(
                severity=severity,
                title=f"[{severity.value.upper()}] {title}",
                message=f"New incident created: {description}\nAssigned to: {incident.assigned_to or 'Unassigned'}"
            )
            
            return incident
    
    def update_incident(
        self,
        incident_id: str,
        updated_by: str,
        status: Optional[IncidentStatus] = None,
        notes: Optional[str] = None,
        root_cause: Optional[str] = None,
        resolution_notes: Optional[str] = None
    ) -> Optional[Incident]:
        """Update incident."""
        with self._lock:
            incident = self.incidents.get(incident_id)
            if not incident:
                return None
            
            # Track changes in timeline
            changes = []
            
            if status and status != incident.status:
                changes.append(f"Status: {incident.status} → {status}")
                incident.status = status
                
                if status == IncidentStatus.RESOLVED:
                    incident.resolved_at = datetime.utcnow()
            
            if notes:
                changes.append(f"Added notes: {notes}")
            
            if root_cause:
                incident.root_cause = root_cause
                changes.append(f"Root cause identified: {root_cause}")
            
            if resolution_notes:
                incident.resolution_notes = resolution_notes
                changes.append(f"Resolution notes: {resolution_notes}")
            
            # Update timestamp
            incident.updated_at = datetime.utcnow()
            
            # Add to timeline
            if changes:
                incident.timeline.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "incident_updated",
                    "user": updated_by,
                    "details": "; ".join(changes)
                })
            
            return incident
    
    def escalate_incident(self, incident_id: str, escalated_by: str) -> bool:
        """Escalate incident to next level."""
        with self._lock:
            incident = self.incidents.get(incident_id)
            if not incident:
                return False
            
            # Get escalation contacts
            contacts = self.oncall_manager.escalate_incident(incident_id, incident.severity)
            
            # Update timeline
            incident.timeline.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "incident_escalated",
                "user": escalated_by,
                "details": f"Escalated to: {', '.join(contacts)}"
            })
            
            # Send escalation alert
            self.alert_manager.send_alert(
                severity=incident.severity,
                title=f"[ESCALATED] {incident.title}",
                message=f"Incident {incident_id} has been escalated.\nContacts: {', '.join(contacts)}"
            )
            
            return True
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID."""
        return self.incidents.get(incident_id)
    
    def list_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        hours_back: int = 24
    ) -> List[Incident]:
        """List incidents with optional filtering."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        filtered_incidents = []
        for incident in self.incidents.values():
            if incident.created_at < cutoff_time:
                continue
            if status and incident.status != status:
                continue
            if severity and incident.severity != severity:
                continue
            
            filtered_incidents.append(incident)
        
        # Sort by creation time (newest first)
        return sorted(filtered_incidents, key=lambda i: i.created_at, reverse=True)
    
    def get_runbook(self, name: str) -> Optional[Runbook]:
        """Get operational runbook."""
        return self.runbook_manager.get_runbook(name)
    
    def get_recovery_plan(self, disaster_type: str) -> Optional[Dict[str, Any]]:
        """Get disaster recovery plan."""
        return self.dr_manager.get_recovery_plan(disaster_type)
    
    def generate_incident_report(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Generate incident report."""
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        # Calculate metrics
        resolution_time = None
        if incident.resolved_at:
            resolution_time = int((incident.resolved_at - incident.created_at).total_seconds() / 60)
        
        report = {
            "incident": incident.to_dict(),
            "metrics": {
                "resolution_time_minutes": resolution_time,
                "timeline_events": len(incident.timeline),
                "severity": incident.severity.value,
                "status": incident.status.value
            },
            "timeline": incident.timeline,
            "recommendations": self._generate_recommendations(incident),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self, incident: Incident) -> List[str]:
        """Generate recommendations based on incident."""
        recommendations = []
        
        # Generic recommendations based on severity
        if incident.severity == IncidentSeverity.SEV1:
            recommendations.extend([
                "Review monitoring and alerting for earlier detection",
                "Consider implementing automated recovery procedures",
                "Schedule disaster recovery drill"
            ])
        
        # Recommendations based on resolution time
        if incident.resolved_at:
            resolution_minutes = (incident.resolved_at - incident.created_at).total_seconds() / 60
            if resolution_minutes > 240:  # 4 hours
                recommendations.append("Review incident response procedures for faster resolution")
        
        # Service-specific recommendations
        if incident.service_affected:
            recommendations.append(f"Review {incident.service_affected} service architecture for resilience")
        
        return recommendations
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for incident management system."""
        open_incidents = len([i for i in self.incidents.values() if i.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]])
        
        return {
            "status": "healthy",
            "total_incidents": len(self.incidents),
            "open_incidents": open_incidents,
            "runbooks_available": len(self.runbook_manager.runbooks),
            "recovery_plans_available": len(self.dr_manager.recovery_plans),
            "current_oncall": self.oncall_manager.get_current_oncall(primary=True).engineer if self.oncall_manager.get_current_oncall(primary=True) else "None",
            "timestamp": datetime.utcnow().isoformat()
        }


# Global instance
incident_manager = IncidentManager()

# Convenience functions
def create_incident(title: str, description: str, severity: IncidentSeverity, created_by: str = "system") -> str:
    """Global function to create incident."""
    incident = incident_manager.create_incident(title, description, severity, created_by)
    return incident.incident_id

def get_runbook(name: str) -> Optional[Runbook]:
    """Global function to get runbook."""
    return incident_manager.get_runbook(name)

def escalate_incident(incident_id: str, escalated_by: str = "system") -> bool:
    """Global function to escalate incident."""
    return incident_manager.escalate_incident(incident_id, escalated_by)
