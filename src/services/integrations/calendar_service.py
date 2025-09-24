"""Calendar integration service for Track D1.

Handles Google Calendar and Outlook OAuth, event creation for meal prep/cooking,
and calendar_event_id storage.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import asyncio
from urllib.parse import urlencode

import httpx
from dataclasses import asdict

from ...models.integrations import (
    CalendarEvent,
    CalendarProvider,
    EventType,
    OAuthCredentials,
    ReminderType
)


logger = logging.getLogger(__name__)


class CalendarAuthService:
    """Handles OAuth authentication for calendar providers."""
    
    def __init__(self):
        # OAuth configuration (would be loaded from environment/config)
        self.oauth_configs = {
            CalendarProvider.GOOGLE: {
                "client_id": "your-google-client-id",
                "client_secret": "your-google-client-secret", 
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scope": "https://www.googleapis.com/auth/calendar"
            },
            CalendarProvider.OUTLOOK: {
                "client_id": "your-outlook-client-id",
                "client_secret": "your-outlook-client-secret",
                "auth_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                "scope": "https://graph.microsoft.com/calendars.readwrite"
            }
        }
    
    def get_authorization_url(self, provider: CalendarProvider, user_id: UUID, 
                            redirect_uri: str) -> str:
        """Generate OAuth authorization URL."""
        config = self.oauth_configs[provider]
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": config["scope"],
            "response_type": "code",
            "state": f"{user_id}:{provider.value}",  # Include user context
            "access_type": "offline" if provider == CalendarProvider.GOOGLE else None
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        return f"{config['auth_uri']}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, provider: CalendarProvider, 
                                     code: str, redirect_uri: str) -> OAuthCredentials:
        """Exchange authorization code for access/refresh tokens."""
        config = self.oauth_configs[provider]
        
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(config["token_uri"], data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            return OAuthCredentials(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be set by caller
                provider=provider,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expires_at=(
                    datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
                    if token_data.get("expires_in") else None
                ),
                scope=token_data.get("scope", "").split() if token_data.get("scope") else []
            )
    
    async def refresh_access_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """Refresh expired access token."""
        if not credentials.refresh_token:
            raise ValueError("No refresh token available")
        
        config = self.oauth_configs[credentials.provider]
        
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": credentials.refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(config["token_uri"], data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Create updated credentials
            updated_credentials = OAuthCredentials(
                user_id=credentials.user_id,
                provider=credentials.provider,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", credentials.refresh_token),
                token_expires_at=(
                    datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
                    if token_data.get("expires_in") else None
                ),
                scope=credentials.scope,
                provider_user_id=credentials.provider_user_id,
                provider_email=credentials.provider_email,
                created_at=credentials.created_at,
                updated_at=datetime.now(),
                is_active=True
            )
            
            return updated_credentials


class CalendarEventService:
    """Manages calendar events for meal preparation and cooking."""
    
    def __init__(self, auth_service: CalendarAuthService):
        self.auth_service = auth_service
        
        # Event templates for different meal activities
        self.event_templates = {
            EventType.MEAL_PREP: {
                "title": "🥗 Meal Prep - {meal_name}",
                "description": "Prepare ingredients and components for {meal_name}.\n\nEstimated time: {duration} minutes\n\nRecipe: {recipe_url}",
                "default_duration": 30
            },
            EventType.COOKING: {
                "title": "👨‍🍳 Cook - {meal_name}",
                "description": "Cook {meal_name}.\n\nEstimated cooking time: {duration} minutes\n\nRecipe: {recipe_url}",
                "default_duration": 45
            },
            EventType.GROCERY_SHOPPING: {
                "title": "🛒 Grocery Shopping",
                "description": "Weekly grocery shopping for meal plan.\n\nEstimated items: {item_count}\n\nBudget: ${budget}",
                "default_duration": 60
            },
            EventType.MEAL_TIME: {
                "title": "🍽️ {meal_name}",
                "description": "Enjoy {meal_name}!\n\nNutrition: {calories} calories, {protein}g protein",
                "default_duration": 30
            }
        }
    
    async def create_calendar_event(self, credentials: OAuthCredentials, 
                                  event: CalendarEvent) -> CalendarEvent:
        """Create event in external calendar."""
        # Refresh token if needed
        if credentials.needs_refresh():
            credentials = await self.auth_service.refresh_access_token(credentials)
        
        if event.provider == CalendarProvider.GOOGLE:
            return await self._create_google_event(credentials, event)
        elif event.provider == CalendarProvider.OUTLOOK:
            return await self._create_outlook_event(credentials, event)
        else:
            raise ValueError(f"Unsupported provider: {event.provider}")
    
    async def _create_google_event(self, credentials: OAuthCredentials, 
                                 event: CalendarEvent) -> CalendarEvent:
        """Create event in Google Calendar."""
        headers = {
            "Authorization": f"Bearer {credentials.access_token}",
            "Content-Type": "application/json"
        }
        
        # Convert reminders to Google format
        reminders = []
        for minutes in event.reminder_minutes:
            reminders.append({
                "method": "popup",
                "minutes": minutes
            })
        
        event_data = {
            "summary": event.title,
            "description": event.description,
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": event.end_time.isoformat(), 
                "timeZone": "UTC"
            },
            "reminders": {
                "useDefault": False,
                "overrides": reminders
            }
        }
        
        # Add recurrence if specified
        if event.is_recurring and event.recurrence_pattern:
            event_data["recurrence"] = [event.recurrence_pattern]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers=headers,
                json=event_data
            )
            response.raise_for_status()
            
            google_event = response.json()
            
            # Update event with external ID
            return CalendarEvent(
                event_id=event.event_id,
                user_id=event.user_id,
                provider=event.provider,
                external_event_id=google_event["id"],
                title=event.title,
                description=event.description,
                start_time=event.start_time,
                end_time=event.end_time,
                event_type=event.event_type,
                meal_plan_id=event.meal_plan_id,
                recipe_id=event.recipe_id,
                reminders=event.reminders,
                reminder_minutes=event.reminder_minutes,
                is_recurring=event.is_recurring,
                recurrence_pattern=event.recurrence_pattern,
                created_at=event.created_at,
                updated_at=datetime.now()
            )
    
    async def _create_outlook_event(self, credentials: OAuthCredentials,
                                  event: CalendarEvent) -> CalendarEvent:
        """Create event in Outlook Calendar."""
        headers = {
            "Authorization": f"Bearer {credentials.access_token}",
            "Content-Type": "application/json"
        }
        
        # Convert reminders to Outlook format
        reminder_minutes = min(event.reminder_minutes) if event.reminder_minutes else 15
        
        event_data = {
            "subject": event.title,
            "body": {
                "contentType": "text",
                "content": event.description
            },
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": "UTC"
            },
            "isReminderOn": True,
            "reminderMinutesBeforeStart": reminder_minutes
        }
        
        # Add recurrence if specified  
        if event.is_recurring and event.recurrence_pattern:
            # Convert RRULE to Outlook format (simplified)
            event_data["recurrence"] = {
                "pattern": {"type": "weekly"},
                "range": {"type": "noEnd"}
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://graph.microsoft.com/v1.0/me/events",
                headers=headers,
                json=event_data
            )
            response.raise_for_status()
            
            outlook_event = response.json()
            
            # Update event with external ID
            return CalendarEvent(
                event_id=event.event_id,
                user_id=event.user_id,
                provider=event.provider,
                external_event_id=outlook_event["id"],
                title=event.title,
                description=event.description,
                start_time=event.start_time,
                end_time=event.end_time,
                event_type=event.event_type,
                meal_plan_id=event.meal_plan_id,
                recipe_id=event.recipe_id,
                reminders=event.reminders,
                reminder_minutes=event.reminder_minutes,
                is_recurring=event.is_recurring,
                recurrence_pattern=event.recurrence_pattern,
                created_at=event.created_at,
                updated_at=datetime.now()
            )
    
    async def update_calendar_event(self, credentials: OAuthCredentials,
                                  event: CalendarEvent) -> CalendarEvent:
        """Update existing calendar event."""
        if not event.external_event_id:
            raise ValueError("Cannot update event without external_event_id")
        
        # Refresh token if needed
        if credentials.needs_refresh():
            credentials = await self.auth_service.refresh_access_token(credentials)
        
        if event.provider == CalendarProvider.GOOGLE:
            return await self._update_google_event(credentials, event)
        elif event.provider == CalendarProvider.OUTLOOK:
            return await self._update_outlook_event(credentials, event)
        else:
            raise ValueError(f"Unsupported provider: {event.provider}")
    
    async def delete_calendar_event(self, credentials: OAuthCredentials,
                                  event: CalendarEvent) -> bool:
        """Delete calendar event."""
        if not event.external_event_id:
            return False
        
        # Refresh token if needed
        if credentials.needs_refresh():
            credentials = await self.auth_service.refresh_access_token(credentials)
        
        headers = {
            "Authorization": f"Bearer {credentials.access_token}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                if event.provider == CalendarProvider.GOOGLE:
                    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event.external_event_id}"
                elif event.provider == CalendarProvider.OUTLOOK:
                    url = f"https://graph.microsoft.com/v1.0/me/events/{event.external_event_id}"
                else:
                    return False
                
                response = await client.delete(url, headers=headers)
                return response.status_code in [200, 204, 404]  # 404 means already deleted
                
        except Exception as e:
            logger.error(f"Failed to delete calendar event {event.external_event_id}: {e}")
            return False
    
    def generate_meal_prep_events(self, meal_plan_id: UUID, user_id: UUID,
                                provider: CalendarProvider, 
                                meals: List[Dict]) -> List[CalendarEvent]:
        """Generate calendar events for meal preparation."""
        events = []
        base_time = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)  # 6 PM today
        
        for i, meal in enumerate(meals):
            # Prep event
            prep_start = base_time + timedelta(days=i)
            prep_duration = meal.get("prep_time_minutes", 30)
            prep_end = prep_start + timedelta(minutes=prep_duration)
            
            prep_event = CalendarEvent(
                event_id=f"prep_{meal_plan_id}_{i}",
                user_id=user_id,
                provider=provider,
                title=self.event_templates[EventType.MEAL_PREP]["title"].format(
                    meal_name=meal.get("name", "Meal")
                ),
                description=self.event_templates[EventType.MEAL_PREP]["description"].format(
                    meal_name=meal.get("name", "Meal"),
                    duration=prep_duration,
                    recipe_url=meal.get("recipe_url", "")
                ),
                start_time=prep_start,
                end_time=prep_end,
                event_type=EventType.MEAL_PREP,
                meal_plan_id=meal_plan_id,
                recipe_id=meal.get("recipe_id"),
                reminder_minutes=[15, 60]
            )
            events.append(prep_event)
            
            # Cook event (next day)
            cook_start = prep_start + timedelta(days=1, hours=-1)  # 1 hour earlier next day
            cook_duration = meal.get("cook_time_minutes", 45)
            cook_end = cook_start + timedelta(minutes=cook_duration)
            
            cook_event = CalendarEvent(
                event_id=f"cook_{meal_plan_id}_{i}",
                user_id=user_id,
                provider=provider,
                title=self.event_templates[EventType.COOKING]["title"].format(
                    meal_name=meal.get("name", "Meal")
                ),
                description=self.event_templates[EventType.COOKING]["description"].format(
                    meal_name=meal.get("name", "Meal"),
                    duration=cook_duration,
                    recipe_url=meal.get("recipe_url", "")
                ),
                start_time=cook_start,
                end_time=cook_end,
                event_type=EventType.COOKING,
                meal_plan_id=meal_plan_id,
                recipe_id=meal.get("recipe_id"),
                reminder_minutes=[10, 30]
            )
            events.append(cook_event)
        
        return events


class CalendarService:
    """Main calendar integration service for Track D1."""
    
    def __init__(self):
        self.auth_service = CalendarAuthService()
        self.event_service = CalendarEventService(self.auth_service)
        
        # In-memory storage for demo (would use database in production)
        self.credentials_store: Dict[UUID, OAuthCredentials] = {}
        self.events_store: Dict[str, CalendarEvent] = {}
    
    async def connect_calendar(self, user_id: UUID, provider: CalendarProvider,
                             authorization_code: str, redirect_uri: str) -> OAuthCredentials:
        """Connect user's calendar account."""
        # Exchange code for tokens
        credentials = await self.auth_service.exchange_code_for_tokens(
            provider, authorization_code, redirect_uri
        )
        
        # Update with user ID and store
        credentials = OAuthCredentials(
            user_id=user_id,
            provider=credentials.provider,
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            token_expires_at=credentials.token_expires_at,
            scope=credentials.scope
        )
        
        self.credentials_store[user_id] = credentials
        return credentials
    
    async def create_meal_plan_events(self, user_id: UUID, meal_plan_id: UUID,
                                    meals: List[Dict]) -> List[CalendarEvent]:
        """Create calendar events for a meal plan."""
        if user_id not in self.credentials_store:
            raise ValueError("Calendar not connected for user")
        
        credentials = self.credentials_store[user_id]
        
        # Generate events
        events = self.event_service.generate_meal_prep_events(
            meal_plan_id, user_id, credentials.provider, meals
        )
        
        # Create in external calendar
        created_events = []
        for event in events:
            try:
                created_event = await self.event_service.create_calendar_event(
                    credentials, event
                )
                self.events_store[created_event.event_id] = created_event
                created_events.append(created_event)
            except Exception as e:
                logger.error(f"Failed to create calendar event {event.event_id}: {e}")
        
        return created_events
    
    async def update_meal_event(self, user_id: UUID, event_id: str,
                              **updates) -> Optional[CalendarEvent]:
        """Update a meal-related calendar event."""
        if event_id not in self.events_store:
            return None
        
        if user_id not in self.credentials_store:
            raise ValueError("Calendar not connected for user")
        
        credentials = self.credentials_store[user_id]
        event = self.events_store[event_id]
        
        # Update event fields
        updated_event = CalendarEvent(
            event_id=event.event_id,
            user_id=event.user_id,
            provider=event.provider,
            external_event_id=event.external_event_id,
            title=updates.get("title", event.title),
            description=updates.get("description", event.description),
            start_time=updates.get("start_time", event.start_time),
            end_time=updates.get("end_time", event.end_time),
            event_type=event.event_type,
            meal_plan_id=event.meal_plan_id,
            recipe_id=event.recipe_id,
            reminders=updates.get("reminders", event.reminders),
            reminder_minutes=updates.get("reminder_minutes", event.reminder_minutes),
            is_recurring=updates.get("is_recurring", event.is_recurring),
            recurrence_pattern=updates.get("recurrence_pattern", event.recurrence_pattern),
            created_at=event.created_at,
            updated_at=datetime.now()
        )
        
        # Update in external calendar
        try:
            updated_event = await self.event_service.update_calendar_event(
                credentials, updated_event
            )
            self.events_store[event_id] = updated_event
            return updated_event
        except Exception as e:
            logger.error(f"Failed to update calendar event {event_id}: {e}")
            return None
    
    async def delete_meal_plan_events(self, user_id: UUID, meal_plan_id: UUID) -> int:
        """Delete all events for a meal plan."""
        if user_id not in self.credentials_store:
            return 0
        
        credentials = self.credentials_store[user_id]
        deleted_count = 0
        
        # Find events for this meal plan
        events_to_delete = [
            event for event in self.events_store.values()
            if event.meal_plan_id == meal_plan_id and event.user_id == user_id
        ]
        
        for event in events_to_delete:
            try:
                success = await self.event_service.delete_calendar_event(
                    credentials, event
                )
                if success:
                    del self.events_store[event.event_id]
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete calendar event {event.event_id}: {e}")
        
        return deleted_count
    
    def get_user_events(self, user_id: UUID, meal_plan_id: Optional[UUID] = None) -> List[CalendarEvent]:
        """Get user's calendar events, optionally filtered by meal plan."""
        events = [
            event for event in self.events_store.values()
            if event.user_id == user_id
        ]
        
        if meal_plan_id:
            events = [event for event in events if event.meal_plan_id == meal_plan_id]
        
        return sorted(events, key=lambda e: e.start_time)
    
    def get_authorization_url(self, user_id: UUID, provider: CalendarProvider,
                            redirect_uri: str) -> str:
        """Get OAuth authorization URL for calendar provider."""
        return self.auth_service.get_authorization_url(provider, user_id, redirect_uri)


# Export the main service
__all__ = ["CalendarService", "CalendarAuthService", "CalendarEventService"]
