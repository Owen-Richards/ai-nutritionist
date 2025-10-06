"""
API routes for Track G - Reliability, Security, Compliance services.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, Field

# Import Track G services
from ..services.infrastructure.observability import observability, REDMetrics, SLOMetric
from ..services.infrastructure.rate_limiter import rate_limiter, RateLimitType, ActionType, RequestContext
from ..services.infrastructure.secrets_manager import secrets_manager, SecretType, SecretMetadata
from ..services.infrastructure.privacy_compliance import privacy_service, ConsentType, DataCategory, DSARType
from ..services.infrastructure.incident_management import incident_manager, IncidentSeverity, IncidentStatus, Incident

# Create router
router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])

# Request/Response models
class ObservabilityMetricsResponse(BaseModel):
    """Response for observability metrics."""
    red_metrics: Dict[str, Dict[str, Any]]
    slo_status: Dict[str, Dict[str, Any]]
    health_metrics: Dict[str, Any]
    timestamp: str

class RateLimitStatusResponse(BaseModel):
    """Response for rate limit status."""
    identifier: str
    blocked: bool
    blocked_until: Optional[str] = None
    rules: Dict[str, Dict[str, Any]]
    timestamp: str

class SecretCreateRequest(BaseModel):
    """Request to create/store secret."""
    name: str
    value: str
    secret_type: SecretType = SecretType.API_KEY
    rotation_interval_days: Optional[int] = None
    tags: Optional[Dict[str, str]] = None

class ConsentRequest(BaseModel):
    """Request to record user consent."""
    user_id: str
    consent_type: ConsentType
    granted: bool
    ip_address: Optional[str] = None

class DSARRequest(BaseModel):
    """Data Subject Access Request."""
    user_id: str
    request_type: DSARType
    requester_email: str = ""

class IncidentCreateRequest(BaseModel):
    """Request to create incident."""
    title: str
    description: str
    severity: IncidentSeverity
    service_affected: Optional[str] = None
    customer_impact: Optional[str] = None

class IncidentUpdateRequest(BaseModel):
    """Request to update incident."""
    status: Optional[IncidentStatus] = None
    notes: Optional[str] = None
    root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None


# G1 - Observability endpoints
@router.get("/observability/metrics", response_model=ObservabilityMetricsResponse)
async def get_observability_metrics(
    operation: Optional[str] = None
):
    """Get observability metrics including RED metrics and SLO status."""
    try:
        red_metrics = observability.get_red_metrics(operation)
        slo_status = observability.get_slo_status()
        health_metrics = observability.get_health_metrics()
        
        # Convert RED metrics to serializable format
        red_metrics_dict = {}
        for endpoint, metrics in red_metrics.items():
            red_metrics_dict[endpoint] = {
                "service": metrics.service,
                "endpoint": metrics.endpoint,
                "rate_per_minute": metrics.rate_per_minute,
                "error_rate_percentage": metrics.error_rate_percentage,
                "p50_duration_ms": metrics.p50_duration_ms,
                "p95_duration_ms": metrics.p95_duration_ms,
                "p99_duration_ms": metrics.p99_duration_ms,
                "timestamp": metrics.timestamp.isoformat()
            }
        
        # Convert SLO metrics
        slo_status_dict = {}
        for name, slo in slo_status.items():
            slo_status_dict[name] = {
                "name": slo.name,
                "target_percentage": slo.target_percentage,
                "current_percentage": slo.current_percentage,
                "breaches_count": slo.breaches_count,
                "last_breach": slo.last_breach.isoformat() if slo.last_breach else None
            }
        
        return ObservabilityMetricsResponse(
            red_metrics=red_metrics_dict,
            slo_status=slo_status_dict,
            health_metrics=health_metrics,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get observability metrics: {e}")

@router.get("/observability/prometheus")
async def get_prometheus_metrics():
    """Get Prometheus-formatted metrics."""
    try:
        metrics = observability.export_prometheus_metrics()
        return Response(content=metrics, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Prometheus metrics: {e}")

@router.post("/observability/slo")
async def register_slo(
    name: str,
    target_percentage: float,
    measurement_window_hours: int = 24
):
    """Register a new SLO for monitoring."""
    try:
        observability.register_slo(name, target_percentage, measurement_window_hours)
        return {"message": f"SLO {name} registered successfully", "target": target_percentage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register SLO: {e}")


# G2 - Rate limiting endpoints
@router.get("/rate-limit/status/{identifier}", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(identifier: str, rule_name: Optional[str] = None):
    """Get rate limit status for identifier."""
    try:
        status = rate_limiter.get_rate_limit_status(identifier, rule_name)
        return RateLimitStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rate limit status: {e}")

@router.get("/rate-limit/abuse-stats")
async def get_abuse_statistics():
    """Get abuse detection statistics."""
    try:
        stats = rate_limiter.get_abuse_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get abuse statistics: {e}")

@router.post("/rate-limit/check")
async def check_rate_limit_endpoint(
    ip_address: str,
    user_id: Optional[str] = None,
    endpoint: str = "/",
    method: str = "GET"
):
    """Check if request should be rate limited."""
    try:
        context = RequestContext(
            ip_address=ip_address,
            user_id=user_id,
            endpoint=endpoint,
            method=method
        )
        
        is_allowed, reason, retry_after = await rate_limiter.check_rate_limit(context)
        
        return {
            "allowed": is_allowed,
            "reason": reason,
            "retry_after_seconds": retry_after,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check rate limit: {e}")


# G3 - Secrets management endpoints
@router.post("/secrets")
async def store_secret_endpoint(request: SecretCreateRequest):
    """Store a new secret."""
    try:
        success = secrets_manager.store_secret(
            name=request.name,
            value=request.value,
            secret_type=request.secret_type,
            rotation_interval_days=request.rotation_interval_days,
            tags=request.tags,
            accessed_by="api_user"
        )
        
        if success:
            return {"message": f"Secret {request.name} stored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store secret")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store secret: {e}")

@router.get("/secrets/{name}")
async def get_secret_endpoint(name: str):
    """Get secret value (be very careful with this endpoint in production)."""
    try:
        # In production, this should have strong authentication and authorization
        value = secrets_manager.get_secret(name, accessed_by="api_user")
        
        if value:
            # Never return the actual secret value in production
            return {
                "name": name,
                "exists": True,
                "message": "Secret exists (value not returned for security)"
            }
        else:
            raise HTTPException(status_code=404, detail="Secret not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get secret: {e}")

@router.get("/secrets")
async def list_secrets_endpoint():
    """List all secret names."""
    try:
        secrets = secrets_manager.list_secrets(accessed_by="api_user")
        return {"secrets": secrets, "count": len(secrets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list secrets: {e}")

@router.post("/secrets/{name}/rotate")
async def rotate_secret_endpoint(name: str):
    """Rotate a secret."""
    try:
        success = secrets_manager.rotate_secret(name, accessed_by="api_user")
        
        if success:
            return {"message": f"Secret {name} rotated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to rotate secret")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rotate secret: {e}")

@router.get("/secrets/audit-logs")
async def get_secrets_audit_logs(
    secret_name: Optional[str] = None,
    accessed_by: Optional[str] = None,
    hours_back: int = 24
):
    """Get secrets access audit logs."""
    try:
        logs = secrets_manager.get_audit_logs(secret_name, accessed_by, hours_back)
        
        # Convert to serializable format
        log_data = []
        for log in logs:
            log_data.append({
                "secret_name": log.secret_name,
                "accessed_by": log.accessed_by,
                "access_type": log.access_type,
                "timestamp": log.timestamp.isoformat(),
                "success": log.success,
                "error_message": log.error_message
            })
        
        return {"logs": log_data, "count": len(log_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {e}")


# G4 - Privacy compliance endpoints
@router.post("/privacy/consent")
async def record_consent_endpoint(request: ConsentRequest):
    """Record user consent for data processing."""
    try:
        success = privacy_service.record_user_consent(
            user_id=request.user_id,
            consent_type=request.consent_type,
            granted=request.granted,
            ip_address=request.ip_address
        )
        
        if success:
            return {"message": "Consent recorded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to record consent")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record consent: {e}")

@router.get("/privacy/consent/{user_id}")
async def get_user_consent(user_id: str):
    """Get all consents for a user."""
    try:
        consents = privacy_service.consent_manager.get_all_consents(user_id)
        
        # Convert enum keys to strings for JSON serialization
        consent_data = {consent_type.value: granted for consent_type, granted in consents.items()}
        
        return {
            "user_id": user_id,
            "consents": consent_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user consent: {e}")

@router.post("/privacy/dsar")
async def submit_dsar_request(request: DSARRequest):
    """Submit Data Subject Access Request."""
    try:
        request_id = privacy_service.submit_data_request(
            user_id=request.user_id,
            request_type=request.request_type,
            requester_email=request.requester_email
        )
        
        return {
            "request_id": request_id,
            "message": "DSAR request submitted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit DSAR request: {e}")

@router.get("/privacy/dsar/{request_id}")
async def get_dsar_status(request_id: str):
    """Get DSAR request status."""
    try:
        status = privacy_service.get_request_status(request_id)
        
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="DSAR request not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get DSAR status: {e}")

@router.get("/privacy/data-summary/{user_id}")
async def get_user_data_summary(user_id: str):
    """Get summary of user's data and privacy status."""
    try:
        summary = privacy_service.get_data_summary(user_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data summary: {e}")

@router.post("/privacy/data-deletion/{user_id}")
async def schedule_data_deletion(user_id: str, reason: str = "user_request"):
    """Schedule user data for deletion."""
    try:
        privacy_service.schedule_data_deletion(user_id, reason)
        return {"message": f"Data deletion scheduled for user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule data deletion: {e}")


# G5 - Incident management endpoints
@router.post("/incidents")
async def create_incident_endpoint(request: IncidentCreateRequest):
    """Create a new incident."""
    try:
        incident = incident_manager.create_incident(
            title=request.title,
            description=request.description,
            severity=request.severity,
            created_by="api_user",
            service_affected=request.service_affected,
            customer_impact=request.customer_impact
        )
        
        return {
            "incident_id": incident.incident_id,
            "message": "Incident created successfully",
            "severity": incident.severity.value,
            "assigned_to": incident.assigned_to
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create incident: {e}")

@router.get("/incidents/{incident_id}")
async def get_incident_endpoint(incident_id: str):
    """Get incident details."""
    try:
        incident = incident_manager.get_incident(incident_id)
        
        if incident:
            return incident.to_dict()
        else:
            raise HTTPException(status_code=404, detail="Incident not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get incident: {e}")

@router.put("/incidents/{incident_id}")
async def update_incident_endpoint(incident_id: str, request: IncidentUpdateRequest):
    """Update incident."""
    try:
        incident = incident_manager.update_incident(
            incident_id=incident_id,
            updated_by="api_user",
            status=request.status,
            notes=request.notes,
            root_cause=request.root_cause,
            resolution_notes=request.resolution_notes
        )
        
        if incident:
            return {"message": "Incident updated successfully", "status": incident.status.value}
        else:
            raise HTTPException(status_code=404, detail="Incident not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update incident: {e}")

@router.get("/incidents")
async def list_incidents_endpoint(
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
    hours_back: int = 24
):
    """List incidents with optional filtering."""
    try:
        incidents = incident_manager.list_incidents(status, severity, hours_back)
        
        # Convert to serializable format
        incident_data = [incident.to_dict() for incident in incidents]
        
        return {
            "incidents": incident_data,
            "count": len(incident_data),
            "filters": {
                "status": status.value if status else None,
                "severity": severity.value if severity else None,
                "hours_back": hours_back
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list incidents: {e}")

@router.post("/incidents/{incident_id}/escalate")
async def escalate_incident_endpoint(incident_id: str):
    """Escalate incident to next level."""
    try:
        success = incident_manager.escalate_incident(incident_id, escalated_by="api_user")
        
        if success:
            return {"message": "Incident escalated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Incident not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to escalate incident: {e}")

@router.get("/runbooks")
async def list_runbooks_endpoint(category: Optional[str] = None):
    """List available runbooks."""
    try:
        runbooks = incident_manager.runbook_manager.list_runbooks(category)
        
        runbook_data = []
        for runbook in runbooks:
            runbook_data.append({
                "name": runbook.name,
                "description": runbook.description,
                "category": runbook.category,
                "steps_count": len(runbook.steps),
                "estimated_duration": runbook.estimated_duration,
                "author": runbook.author,
                "created_at": runbook.created_at.isoformat(),
                "updated_at": runbook.updated_at.isoformat()
            })
        
        return {"runbooks": runbook_data, "count": len(runbook_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list runbooks: {e}")

@router.get("/runbooks/{name}")
async def get_runbook_endpoint(name: str):
    """Get detailed runbook."""
    try:
        runbook = incident_manager.get_runbook(name)
        
        if runbook:
            return {
                "name": runbook.name,
                "description": runbook.description,
                "category": runbook.category,
                "steps": runbook.steps,
                "prerequisites": runbook.prerequisites,
                "estimated_duration": runbook.estimated_duration,
                "author": runbook.author,
                "created_at": runbook.created_at.isoformat(),
                "updated_at": runbook.updated_at.isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Runbook not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get runbook: {e}")

@router.get("/disaster-recovery")
async def list_recovery_plans():
    """List disaster recovery plans."""
    try:
        plans = incident_manager.dr_manager.list_recovery_plans()
        return {"recovery_plans": plans, "count": len(plans)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list recovery plans: {e}")

@router.get("/disaster-recovery/{disaster_type}")
async def get_recovery_plan_endpoint(disaster_type: str):
    """Get disaster recovery plan."""
    try:
        plan = incident_manager.get_recovery_plan(disaster_type)
        
        if plan:
            return plan
        else:
            raise HTTPException(status_code=404, detail="Recovery plan not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recovery plan: {e}")

@router.get("/incidents/{incident_id}/report")
async def generate_incident_report(incident_id: str):
    """Generate incident report."""
    try:
        report = incident_manager.generate_incident_report(incident_id)
        
        if report:
            return report
        else:
            raise HTTPException(status_code=404, detail="Incident not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate incident report: {e}")


# Health check endpoint for Track G services
@router.get("/health")
async def infrastructure_health_check():
    """Health check for all Track G infrastructure services."""
    try:
        health_status = {
            "observability": observability.get_health_metrics(),
            "rate_limiter": rate_limiter.get_abuse_statistics(),  # Using abuse stats as health indicator
            "secrets_manager": secrets_manager.health_check(),
            "privacy_service": privacy_service.health_check(),
            "incident_manager": incident_manager.health_check(),
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return health_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")
