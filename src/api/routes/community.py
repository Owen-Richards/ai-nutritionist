"""Community API routes for crew management and engagement."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from services.community.service import CommunityService, JoinCrewCommand, SubmitReflectionCommand, SubmitPulseCommand, CrewJoinResult
from services.community.models import PulseMetricType

from ..dependencies import get_community_service
from ..schemas.community import (
    JoinCrewRequest,
    JoinCrewResponse,
    SubmitReflectionRequest,
    SubmitReflectionResponse,
    SubmitPulseRequest,
    SubmitPulseResponse,
    CrewPulseResponse,
    CrewPulseMetrics,
    CrewSummary,
)

router = APIRouter(prefix="/v1/crews", tags=["community"])


@router.post(
    "/join",
    response_model=JoinCrewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join a nutrition crew"
)
def join_crew(
    payload: JoinCrewRequest,
    community_service: CommunityService = Depends(get_community_service),
) -> JoinCrewResponse:
    """Add a user to a nutrition crew with proper validation and welcome messaging."""
    
    command = JoinCrewCommand(
        user_id=payload.user_id,
        crew_id=payload.crew_id,
        privacy_consent=payload.privacy_consent,
        notifications_enabled=payload.notifications_enabled
    )
    
    result = community_service.join_crew(command, payload.user_name)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message
        )
    
    # Prepare response
    response_data = {
        "success": True,
        "message": "Successfully joined crew",
        "member_id": result.member.member_id if result.member else None,
        "welcome_sms": result.welcome_message.message if result.welcome_message else None,
    }
    
    # Add crew info if available
    if result.member:
        crew = community_service._repository.get_crew(result.member.crew_id)
        if crew:
            response_data["crew_info"] = {
                "name": crew.name,
                "type": crew.crew_type.value,
                "description": crew.description
            }
    
    return JoinCrewResponse(**response_data)


@router.get(
    "/{crew_id}/pulse",
    response_model=CrewPulseResponse,
    summary="Get anonymized crew pulse data"
)
def get_crew_pulse(
    crew_id: str,
    days_back: int = 7,
    community_service: CommunityService = Depends(get_community_service),
) -> CrewPulseResponse:
    """Retrieve anonymized crew engagement and health metrics."""
    
    # Validate days_back parameter
    if days_back < 1 or days_back > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days_back must be between 1 and 30"
        )
    
    pulse = community_service.get_crew_pulse(crew_id, days_back=days_back)
    
    if not pulse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crew not found or insufficient data"
        )
    
    # Check if data was suppressed due to privacy requirements
    if pulse.total_active_members < 5:
        return CrewPulseResponse(
            crew_id=crew_id,
            pulse_date=pulse.pulse_date,
            total_active_members=pulse.total_active_members,
            engagement_score=0.0,
            metrics=[],
            recent_reflections=["Data suppressed - crew size below privacy threshold"],
            challenge_completion_rate=0.0,
            anonymization_applied=True,
            data_suppressed=True,
            suppression_reason="Crew has fewer than 5 active members"
        )
    
    # Convert metrics to response format
    metrics_list = []
    for metric_type, stats in pulse.metrics.items():
        metrics_list.append(CrewPulseMetrics(
            metric_type=metric_type,
            average=stats["avg"],
            median=stats["median"],
            count=stats["count"],
            trend="stable"  # TODO: Calculate actual trend
        ))
    
    return CrewPulseResponse(
        crew_id=crew_id,
        pulse_date=pulse.pulse_date,
        total_active_members=pulse.total_active_members,
        engagement_score=pulse.engagement_score,
        metrics=metrics_list,
        recent_reflections=pulse.recent_reflections,
        challenge_completion_rate=pulse.challenge_completion_rate,
        anonymization_applied=pulse.anonymization_applied
    )


@router.post(
    "/reflections",
    response_model=SubmitReflectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a crew reflection"
)
def submit_reflection(
    payload: SubmitReflectionRequest,
    community_service: CommunityService = Depends(get_community_service),
) -> SubmitReflectionResponse:
    """Submit a reflection or check-in for a crew with content moderation."""
    
    command = SubmitReflectionCommand(
        user_id=payload.user_id,
        crew_id=payload.crew_id,
        content=payload.content,
        reflection_type=payload.reflection_type,
        mood_score=payload.mood_score,
        progress_rating=payload.progress_rating,
        is_anonymous=payload.is_anonymous
    )
    
    result = community_service.submit_reflection(command)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message
        )
    
    return SubmitReflectionResponse(
        success=True,
        message="Reflection submitted successfully",
        reflection_id=result.reflection.reflection_id if result.reflection else None,
        pii_redacted=result.reflection.pii_redacted if result.reflection else False
    )


@router.post(
    "/pulse",
    response_model=SubmitPulseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit pulse metrics"
)
def submit_pulse_metrics(
    payload: SubmitPulseRequest,
    community_service: CommunityService = Depends(get_community_service),
) -> SubmitPulseResponse:
    """Submit daily pulse metrics for crew engagement tracking."""
    
    # Convert metrics to command format
    metrics_dict = {
        metric.metric_type: metric.value 
        for metric in payload.metrics
    }
    
    command = SubmitPulseCommand(
        user_id=payload.user_id,
        metrics=metrics_dict
    )
    
    success = community_service.submit_pulse_metrics(command)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to record pulse metrics"
        )
    
    return SubmitPulseResponse(
        success=True,
        message="Pulse metrics recorded successfully",
        metrics_recorded=len(payload.metrics)
    )


@router.get(
    "/available",
    response_model=List[CrewSummary],
    summary="List available crews for joining"
)
def list_available_crews(
    crew_type: Optional[str] = None,
    community_service: CommunityService = Depends(get_community_service),
) -> List[CrewSummary]:
    """List available crews that users can join, optionally filtered by type."""
    
    # Parse crew type if provided
    parsed_crew_type = None
    if crew_type:
        try:
            from services.community.models import CrewType
            parsed_crew_type = CrewType(crew_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid crew type: {crew_type}"
            )
    
    crews = community_service.list_available_crews(parsed_crew_type)
    
    # Convert to response format
    crew_summaries = []
    for crew in crews:
        member_count = len(community_service._repository.get_crew_members(crew.crew_id))
        
        crew_summaries.append(CrewSummary(
            crew_id=crew.crew_id,
            name=crew.name,
            crew_type=crew.crew_type,
            description=crew.description,
            member_count=member_count,
            max_members=crew.max_members,
            is_active=crew.is_active,
            created_at=crew.created_at
        ))
    
    return crew_summaries


@router.get(
    "/user/{user_id}",
    response_model=List[CrewSummary],
    summary="Get user's crews"
)
def get_user_crews(
    user_id: str,
    community_service: CommunityService = Depends(get_community_service),
) -> List[CrewSummary]:
    """Get all crews that a user belongs to."""
    
    crews = community_service.get_user_crews(user_id)
    
    # Convert to response format
    crew_summaries = []
    for crew in crews:
        member_count = len(community_service._repository.get_crew_members(crew.crew_id))
        
        crew_summaries.append(CrewSummary(
            crew_id=crew.crew_id,
            name=crew.name,
            crew_type=crew.crew_type,
            description=crew.description,
            member_count=member_count,
            max_members=crew.max_members,
            is_active=crew.is_active,
            created_at=crew.created_at
        ))
    
    return crew_summaries


__all__ = ["router"]
