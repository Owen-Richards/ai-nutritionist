"""API routes for Track D integrations: Calendar, Grocery, and Fitness."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...models.integrations import (
    CalendarProvider, 
    FitnessProvider,
    GroceryExportFormat,
    CalendarEvent,
    GroceryList,
    FitnessData
)
from ...services.integrations.calendar_service import CalendarService
from ...services.integrations.grocery_service import GroceryService
from ...services.integrations.fitness_service import FitnessService

logger = logging.getLogger(__name__)

# Initialize services
calendar_service = CalendarService()
grocery_service = GroceryService()
fitness_service = FitnessService()

# Create router
integrations_router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CalendarAuthRequest(BaseModel):
    provider: CalendarProvider
    redirect_uri: str

class CalendarAuthResponse(BaseModel):
    authorization_url: str
    state: str

class CalendarCallbackRequest(BaseModel):
    provider: CalendarProvider
    code: str
    state: str
    redirect_uri: str

class CalendarEventRequest(BaseModel):
    meal_plan_id: UUID
    prep_time_minutes: int = 30
    cook_time_minutes: int = 45
    send_reminders: bool = True

class CalendarEventResponse(BaseModel):
    prep_event: CalendarEvent
    cook_event: CalendarEvent
    calendar_event_ids: List[str]

class GroceryGenerateRequest(BaseModel):
    meal_plan_id: UUID
    servings: int = 4
    consolidate_similar: bool = True

class GroceryExportRequest(BaseModel):
    grocery_list_id: UUID
    format: GroceryExportFormat
    include_quantities: bool = True
    include_categories: bool = True

class PartnerDeeplinksRequest(BaseModel):
    grocery_list_id: UUID
    preferred_partners: Optional[List[str]] = None

class PartnerDeeplinksResponse(BaseModel):
    deeplinks: Dict[str, str]
    estimated_total: Optional[float] = None

class FitnessAuthRequest(BaseModel):
    provider: FitnessProvider
    redirect_uri: str

class FitnessAuthResponse(BaseModel):
    authorization_url: str
    state: str

class FitnessCallbackRequest(BaseModel):
    provider: FitnessProvider
    code: str
    state: str
    redirect_uri: str

class FitnessSyncRequest(BaseModel):
    date: Optional[datetime] = None

class NutritionAdjustmentRequest(BaseModel):
    date: datetime
    preference: str = "high_protein"

class WeeklyActivitySummaryResponse(BaseModel):
    total_steps: int
    total_calories: int
    total_workouts: int
    average_sleep_hours: float
    high_activity_days: int
    recovery_days_needed: int
    weekly_consistency: float
    recommendations: List[str]


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_current_user_id(request: Request) -> UUID:
    """Extract user ID from request. In production, use proper authentication."""
    # Placeholder - in production, extract from JWT token or session
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


# ============================================================================
# CALENDAR INTEGRATION ROUTES
# ============================================================================

@integrations_router.post("/calendar/auth", response_model=CalendarAuthResponse)
async def initiate_calendar_auth(
    request: CalendarAuthRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Initiate OAuth flow for calendar provider."""
    try:
        auth_url = calendar_service.get_authorization_url(
            user_id, request.provider, request.redirect_uri
        )
        
        return CalendarAuthResponse(
            authorization_url=auth_url,
            state=f"{user_id}:{request.provider.value}"
        )
    except Exception as e:
        logger.error(f"Calendar auth initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate calendar authentication")


@integrations_router.post("/calendar/callback")
async def handle_calendar_callback(
    request: CalendarCallbackRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Handle OAuth callback for calendar provider."""
    try:
        credentials = await calendar_service.connect_calendar_provider(
            user_id, request.provider, request.code, request.redirect_uri
        )
        
        return {
            "success": True,
            "provider": request.provider.value,
            "scope": credentials.scope
        }
    except Exception as e:
        logger.error(f"Calendar callback failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to connect calendar")


@integrations_router.post("/calendar/events", response_model=CalendarEventResponse)
async def create_meal_prep_events(
    request: CalendarEventRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Create meal prep and cooking events in calendar."""
    try:
        prep_event, cook_event = await calendar_service.create_meal_prep_events(
            user_id=user_id,
            meal_plan_id=request.meal_plan_id,
            prep_time_minutes=request.prep_time_minutes,
            cook_time_minutes=request.cook_time_minutes,
            send_reminders=request.send_reminders
        )
        
        return CalendarEventResponse(
            prep_event=prep_event,
            cook_event=cook_event,
            calendar_event_ids=[prep_event.calendar_event_id, cook_event.calendar_event_id]
        )
    except Exception as e:
        logger.error(f"Failed to create calendar events: {e}")
        raise HTTPException(status_code=500, detail="Failed to create calendar events")


@integrations_router.get("/calendar/events")
async def get_calendar_events(
    user_id: UUID = Depends(get_current_user_id),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get calendar events for date range."""
    try:
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)
        
        events = await calendar_service.get_events_in_range(user_id, start_date, end_date)
        return {"events": [event.dict() for event in events]}
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve calendar events")


# ============================================================================
# GROCERY INTEGRATION ROUTES
# ============================================================================

@integrations_router.post("/grocery/generate")
async def generate_grocery_list(
    request: GroceryGenerateRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Generate grocery list from meal plan."""
    try:
        grocery_list = await grocery_service.generate_grocery_list(
            user_id=user_id,
            meal_plan_id=request.meal_plan_id,
            servings=request.servings,
            consolidate_similar=request.consolidate_similar
        )
        
        return {
            "grocery_list_id": grocery_list.id,
            "total_items": len(grocery_list.items),
            "categories": list(set(item.category for item in grocery_list.items)),
            "estimated_cost": grocery_list.estimated_total_cost
        }
    except Exception as e:
        logger.error(f"Failed to generate grocery list: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate grocery list")


@integrations_router.get("/grocery/export")
async def export_grocery_list(
    grocery_list_id: UUID,
    format: GroceryExportFormat = Query(GroceryExportFormat.CSV),
    include_quantities: bool = Query(True),
    include_categories: bool = Query(True),
    user_id: UUID = Depends(get_current_user_id)
):
    """Export grocery list in various formats."""
    try:
        export_data = await grocery_service.export_grocery_list(
            user_id=user_id,
            grocery_list_id=grocery_list_id,
            format=format,
            include_quantities=include_quantities,
            include_categories=include_categories
        )
        
        # Determine content type and filename
        if format == GroceryExportFormat.CSV:
            content_type = "text/csv"
            filename = f"grocery_list_{grocery_list_id}.csv"
        elif format == GroceryExportFormat.JSON:
            content_type = "application/json"
            filename = f"grocery_list_{grocery_list_id}.json"
        elif format == GroceryExportFormat.MARKDOWN:
            content_type = "text/markdown"
            filename = f"grocery_list_{grocery_list_id}.md"
        else:
            content_type = "text/plain"
            filename = f"grocery_list_{grocery_list_id}.txt"
        
        # Return as downloadable file
        return StreamingResponse(
            iter([export_data.encode("utf-8")]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Failed to export grocery list: {e}")
        raise HTTPException(status_code=500, detail="Failed to export grocery list")


@integrations_router.post("/grocery/partner-links", response_model=PartnerDeeplinksResponse)
async def get_partner_deeplinks(
    request: PartnerDeeplinksRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get partner deeplinks for grocery list."""
    try:
        deeplinks = await grocery_service.generate_partner_deeplinks(
            user_id=user_id,
            grocery_list_id=request.grocery_list_id,
            preferred_partners=request.preferred_partners or ["instacart", "amazon_fresh"]
        )
        
        # Calculate estimated total (placeholder logic)
        estimated_total = 45.50  # Would calculate from actual grocery list
        
        return PartnerDeeplinksResponse(
            deeplinks=deeplinks,
            estimated_total=estimated_total
        )
    except Exception as e:
        logger.error(f"Failed to generate partner deeplinks: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate partner links")


@integrations_router.get("/grocery/lists")
async def get_grocery_lists(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Get user's grocery lists."""
    try:
        # Placeholder - would query database in production
        return {
            "lists": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get grocery lists: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve grocery lists")


# ============================================================================
# FITNESS INTEGRATION ROUTES
# ============================================================================

@integrations_router.get("/fitness/enabled")
async def check_fitness_enabled():
    """Check if fitness integration is enabled via feature flag."""
    return {"enabled": fitness_service.is_enabled()}


@integrations_router.post("/fitness/auth", response_model=FitnessAuthResponse)
async def initiate_fitness_auth(
    request: FitnessAuthRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Initiate OAuth flow for fitness provider."""
    try:
        if not fitness_service.is_enabled():
            raise HTTPException(status_code=503, detail="Fitness integration is disabled")
        
        auth_url = fitness_service.get_authorization_url(
            user_id, request.provider, request.redirect_uri
        )
        
        return FitnessAuthResponse(
            authorization_url=auth_url,
            state=f"{user_id}:{request.provider.value}"
        )
    except Exception as e:
        logger.error(f"Fitness auth initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate fitness authentication")


@integrations_router.post("/fitness/callback")
async def handle_fitness_callback(
    request: FitnessCallbackRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Handle OAuth callback for fitness provider."""
    try:
        if not fitness_service.is_enabled():
            raise HTTPException(status_code=503, detail="Fitness integration is disabled")
        
        credentials = await fitness_service.connect_fitness_provider(
            user_id, request.provider, request.code, request.redirect_uri
        )
        
        return {
            "success": True,
            "provider": request.provider.value,
            "scope": credentials.scope
        }
    except Exception as e:
        logger.error(f"Fitness callback failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to connect fitness provider")


@integrations_router.post("/fitness/sync")
async def sync_fitness_data(
    request: FitnessSyncRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Sync fitness data for a specific date."""
    try:
        if not fitness_service.is_enabled():
            raise HTTPException(status_code=503, detail="Fitness integration is disabled")
        
        sync_date = request.date or datetime.now()
        fitness_data = await fitness_service.sync_daily_fitness_data(user_id, sync_date)
        
        if not fitness_data:
            raise HTTPException(status_code=404, detail="No fitness data available")
        
        return {
            "success": True,
            "date": sync_date.isoformat(),
            "provider": fitness_data.provider.value,
            "steps": fitness_data.steps,
            "calories_burned": fitness_data.calories_burned,
            "activity_level": fitness_data.activity_level,
            "recovery_needed": fitness_data.recovery_needed,
            "workouts": len(fitness_data.workouts)
        }
    except Exception as e:
        logger.error(f"Fitness sync failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync fitness data")


@integrations_router.post("/fitness/nutrition-adjustments")
async def get_nutrition_adjustments(
    request: NutritionAdjustmentRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get nutrition adjustments based on fitness data."""
    try:
        if not fitness_service.is_enabled():
            raise HTTPException(status_code=503, detail="Fitness integration is disabled")
        
        adjustments = fitness_service.get_nutrition_adjustments(
            user_id, request.date, request.preference
        )
        
        if not adjustments:
            raise HTTPException(status_code=404, detail="No fitness data available for adjustments")
        
        return adjustments
    except Exception as e:
        logger.error(f"Failed to get nutrition adjustments: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate nutrition adjustments")


@integrations_router.get("/fitness/history")
async def get_fitness_history(
    user_id: UUID = Depends(get_current_user_id),
    days: int = Query(7, ge=1, le=30)
):
    """Get fitness data history for a user."""
    try:
        if not fitness_service.is_enabled():
            raise HTTPException(status_code=503, detail="Fitness integration is disabled")
        
        history = fitness_service.get_user_fitness_history(user_id, days)
        
        return {
            "history": [
                {
                    "date": data.date.isoformat(),
                    "provider": data.provider.value,
                    "steps": data.steps,
                    "calories_burned": data.calories_burned,
                    "activity_level": data.activity_level,
                    "recovery_needed": data.recovery_needed,
                    "workouts": len(data.workouts),
                    "sleep_hours": float(data.sleep_hours) if data.sleep_hours else None
                }
                for data in history
            ],
            "total_days": len(history)
        }
    except Exception as e:
        logger.error(f"Failed to get fitness history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fitness history")


@integrations_router.get("/fitness/weekly-summary", response_model=WeeklyActivitySummaryResponse)
async def get_weekly_activity_summary(
    user_id: UUID = Depends(get_current_user_id)
):
    """Get weekly activity summary with recommendations."""
    try:
        if not fitness_service.is_enabled():
            raise HTTPException(status_code=503, detail="Fitness integration is disabled")
        
        summary = fitness_service.calculate_weekly_activity_summary(user_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="No fitness data available for weekly summary")
        
        return WeeklyActivitySummaryResponse(**summary)
    except Exception as e:
        logger.error(f"Failed to get weekly summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate weekly activity summary")


# ============================================================================
# INTEGRATION STATUS ROUTES
# ============================================================================

@integrations_router.get("/status")
async def get_integration_status(
    user_id: UUID = Depends(get_current_user_id)
):
    """Get overall integration status for user."""
    try:
        # Check connected providers
        calendar_connected = user_id in calendar_service.credentials_store
        fitness_connected = user_id in fitness_service.credentials_store if fitness_service.is_enabled() else False
        
        return {
            "calendar": {
                "connected": calendar_connected,
                "provider": calendar_service.credentials_store[user_id].provider.value if calendar_connected else None
            },
            "grocery": {
                "enabled": True,
                "recent_lists": 0  # Would query database
            },
            "fitness": {
                "enabled": fitness_service.is_enabled(),
                "connected": fitness_connected,
                "provider": fitness_service.credentials_store[user_id].provider.value if fitness_connected else None
            }
        }
    except Exception as e:
        logger.error(f"Failed to get integration status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve integration status")


# Export router
__all__ = ["integrations_router"]
