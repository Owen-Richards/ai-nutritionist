"""Analytics API routes for Track F - Data & Analytics.

Exposes dashboard data, funnel metrics, cohort analysis, and adherence tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

try:
    from ...models.analytics import (
        EventType,
        ConsentType,
        FunnelMetrics,
        CohortMetrics,
        RevenueMetrics
    )
    from ...services.analytics.analytics_service import AnalyticsService
    from ...services.analytics.warehouse_processor import WarehouseProcessor
    from ..dependencies import get_analytics_service
except ImportError:
    # Fallback for direct imports
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from models.analytics import (
        EventType,
        ConsentType,
        FunnelMetrics,
        CohortMetrics,
        RevenueMetrics
    )
    from services.analytics.analytics_service import AnalyticsService
    from services.analytics.warehouse_processor import WarehouseProcessor
    from api.dependencies import get_analytics_service

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


# Response models

class DashboardResponse(BaseModel):
    """Main analytics dashboard response."""
    period: Dict[str, Any]
    overview: Dict[str, Any]
    activation_funnel: Dict[str, Any]
    engagement: Dict[str, Any]
    monetization: Dict[str, Any]
    events: Dict[str, Any]
    generated_at: str


class AdherenceResponse(BaseModel):
    """Adherence analysis response."""
    period: Dict[str, Any]
    total_users: int
    average_adherence: float
    median_adherence: float
    adherence_distribution: Dict[str, int]
    user_data: Dict[str, Any]


class EventSummaryResponse(BaseModel):
    """Event summary response."""
    event_counts: Dict[str, int]
    total_events: int
    period: Dict[str, Any]
    top_events: List[Dict[str, Any]]


class UserJourneyResponse(BaseModel):
    """User journey analysis response."""
    user_id: str
    registration_date: str
    total_events: int
    event_timeline: List[Dict[str, Any]]
    current_tier: Optional[str]
    ltv_usd: float
    adherence_score: Optional[float]


# Analytics endpoints

@router.get("/dashboard", response_model=DashboardResponse)
async def get_analytics_dashboard(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get comprehensive analytics dashboard data."""
    try:
        # Create warehouse processor
        processor = WarehouseProcessor(analytics_service)
        
        # Get dashboard data
        dashboard_data = await processor.get_dashboard_data(start_date, end_date)
        
        return DashboardResponse(**dashboard_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")


@router.get("/funnel", response_model=FunnelMetrics)
async def get_activation_funnel(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get activation funnel metrics."""
    try:
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        processor = WarehouseProcessor(analytics_service)
        funnel_metrics = await processor.process_activation_funnel(
            start_date, end_date, force_refresh
        )
        
        return funnel_metrics
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing funnel: {str(e)}")


@router.get("/cohorts/{cohort_month}", response_model=CohortMetrics)
async def get_cohort_analysis(
    cohort_month: str = Query(..., description="Cohort month in YYYY-MM format"),
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get cohort analysis for specific month."""
    try:
        # Validate cohort month format
        try:
            year, month = map(int, cohort_month.split('-'))
            if not (2020 <= year <= 2030) or not (1 <= month <= 12):
                raise ValueError()
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid cohort month format. Use YYYY-MM format."
            )
        
        processor = WarehouseProcessor(analytics_service)
        cohort_metrics = await processor.process_cohort_analysis(cohort_month, force_refresh)
        
        return cohort_metrics
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing cohort: {str(e)}")


@router.get("/revenue", response_model=RevenueMetrics)
async def get_revenue_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get revenue and subscription metrics."""
    try:
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        processor = WarehouseProcessor(analytics_service)
        revenue_metrics = await processor.process_revenue_metrics(
            start_date, end_date, force_refresh
        )
        
        return revenue_metrics
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing revenue: {str(e)}")


@router.get("/adherence", response_model=AdherenceResponse)
async def get_adherence_metrics(
    user_id: Optional[UUID] = Query(None, description="Specific user ID for analysis"),
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get adherence tracking metrics."""
    try:
        processor = WarehouseProcessor(analytics_service)
        adherence_data = await processor.calculate_adherence_metrics(
            user_id, start_date, end_date
        )
        
        return AdherenceResponse(**adherence_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating adherence: {str(e)}")


@router.get("/events/summary", response_model=EventSummaryResponse)
async def get_event_summary(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get event summary and counts."""
    try:
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Get event counts
        event_counts = analytics_service.get_event_counts_by_type(start_date, end_date)
        total_events = sum(event_counts.values())
        
        # Convert to string keys and sort by count
        event_counts_str = {
            event_type.value: count 
            for event_type, count in event_counts.items()
        }
        
        # Get top events
        top_events = [
            {"event_type": event_type, "count": count}
            for event_type, count in sorted(
                event_counts_str.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        ]
        
        return EventSummaryResponse(
            event_counts=event_counts_str,
            total_events=total_events,
            period={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            top_events=top_events
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting event summary: {str(e)}")


@router.get("/users/{user_id}/journey", response_model=UserJourneyResponse)
async def get_user_journey(
    user_id: UUID,
    limit: int = Query(100, description="Maximum number of events to return"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get detailed user journey analysis."""
    try:
        # Get user profile
        profile = analytics_service.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get user events
        events = analytics_service.get_events_for_user(user_id)
        events.sort(key=lambda e: e.timestamp)
        
        # Limit events if needed
        if len(events) > limit:
            events = events[-limit:]  # Get most recent events
        
        # Build event timeline
        event_timeline = []
        for event in events:
            event_data = {
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "properties": event.properties,
                "context": event.context.dict() if event.context else None
            }
            event_timeline.append(event_data)
        
        # Calculate adherence score
        adherence_score = None
        if profile.total_plans_generated > 0:
            expected_meals = profile.total_plans_generated * 7  # 7 meals per plan
            adherence_score = min(profile.total_meals_logged / expected_meals, 1.0)
        
        return UserJourneyResponse(
            user_id=str(user_id),
            registration_date=profile.created_at.isoformat(),
            total_events=len(event_timeline),
            event_timeline=event_timeline,
            current_tier=profile.current_tier,
            ltv_usd=profile.ltv_usd,
            adherence_score=adherence_score
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user journey: {str(e)}")


# Consent management endpoints

@router.post("/users/{user_id}/consent")
async def update_user_consent(
    user_id: UUID,
    consent_type: ConsentType,
    granted: bool,
    source: str = "api",
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Update user consent preferences."""
    try:
        success = await analytics_service.update_user_consent(
            user_id, consent_type, granted, source
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update consent")
        
        return {
            "user_id": str(user_id),
            "consent_type": consent_type.value,
            "granted": granted,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating consent: {str(e)}")


@router.post("/users/{user_id}/data-deletion")
async def request_data_deletion(
    user_id: UUID,
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Request user data deletion (GDPR compliance)."""
    try:
        success = await analytics_service.request_data_deletion(user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to process deletion request")
        
        return {
            "user_id": str(user_id),
            "deletion_requested": True,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "estimated_completion": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing deletion request: {str(e)}")


# Health and status endpoints

@router.get("/health")
async def analytics_health_check(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Analytics service health check."""
    try:
        total_events = len(analytics_service.events)
        total_users = len(analytics_service.user_profiles)
        
        return {
            "status": "healthy",
            "total_events": total_events,
            "total_users": total_users,
            "cache_size": len(analytics_service.consent_cache),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
