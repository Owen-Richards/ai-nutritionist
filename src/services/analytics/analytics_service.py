"""Analytics service for Track F - Data & Analytics.

Handles event tracking, consent management, and privacy-aware data processing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

try:
    from packages.core.src.entities.analytics import (        BaseEvent,
        EventType,
        ConsentType,
        PIILevel,
        UserConsent,
        UserProfile,
        UserPII,
        EventContext,
        # Specific events
        PlanGeneratedEvent,
        MealLoggedEvent,
        NudgeSentEvent,
        NudgeClickedEvent,
        CrewJoinedEvent,
        ReflectionSubmittedEvent,
        PaywallViewedEvent,
        SubscribeStartedEvent,
        SubscribeActivatedEvent,
        ChurnedEvent,
        StrategyReportScheduledEvent,
        RecoveryPlanCreatedEvent,
        ProgressSummaryPublishedEvent,
        MessageIngestedEvent,
        WearableSyncEvent,
        InventoryStateRecordedEvent
    )
except ImportError:
    # Fallback for direct imports when running as module
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from packages.core.src.entities.analytics import (        BaseEvent,
        EventType,
        ConsentType,
        PIILevel,
        UserConsent,
        UserProfile,
        UserPII,
        EventContext,
        PlanGeneratedEvent,
        MealLoggedEvent,
        NudgeSentEvent,
        NudgeClickedEvent,
        CrewJoinedEvent,
        ReflectionSubmittedEvent,
        PaywallViewedEvent,
        SubscribeStartedEvent,
        SubscribeActivatedEvent,
        ChurnedEvent,
        StrategyReportScheduledEvent,
        RecoveryPlanCreatedEvent,
        ProgressSummaryPublishedEvent,
        MessageIngestedEvent,
        WearableSyncEvent,
        InventoryStateRecordedEvent
    )

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Core analytics service with privacy controls."""
    
    def __init__(self):
        # In-memory storage for development (replace with database in production)
        self.events: List[BaseEvent] = []
        self.user_profiles: Dict[UUID, UserProfile] = {}
        self.user_pii: Dict[UUID, UserPII] = {}
        self.consent_cache: Dict[UUID, Dict[ConsentType, bool]] = {}
        self.event_history: Dict[UUID, Dict[EventType, datetime]] = defaultdict(dict)
        self._recent_events: Dict[UUID, deque] = defaultdict(lambda: deque(maxlen=50))
        
        # Configuration
        self.batch_size = 100
        self.flush_interval_seconds = 60
        self.consent_cache_ttl = 300  # 5 minutes
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._tasks_started = False
        # Try to start tasks during init, but don't fail if no event loop
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for event processing."""
        if self._tasks_started:
            return
            
        try:
            # Only start tasks if there's a running event loop
            loop = asyncio.get_running_loop()
            task = asyncio.create_task(self._periodic_flush())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            self._tasks_started = True
        except RuntimeError:
            # No event loop running, tasks will be started later
            pass

    @staticmethod
    def _coerce_uuid(value: Union[UUID, str, None]) -> Optional[UUID]:
        """Best-effort conversion to UUID while handling None gracefully."""
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _infer_season(timestamp: datetime, hemisphere: str = "north") -> str:
        """Infer meteorological season for enrichment."""
        month = timestamp.month
        if hemisphere.lower().startswith("south"):
            offset = (month + 6) % 12 or 12
        else:
            offset = month
        if offset in (12, 1, 2):
            return "winter"
        if offset in (3, 4, 5):
            return "spring"
        if offset in (6, 7, 8):
            return "summer"
        return "autumn"

    def build_enriched_context(
        self,
        geo: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> EventContext:
        """Construct event context enriched with geo and seasonal metadata."""

        payload: Dict[str, Any] = dict(metadata or {})
        if geo:
            payload.setdefault("geo_country", geo.get("country"))
            payload.setdefault("geo_region", geo.get("region"))
            payload.setdefault("local_timezone", geo.get("timezone"))
            hemisphere = geo.get("hemisphere", "north")
        else:
            hemisphere = "north"

        ts = timestamp or datetime.now(timezone.utc)
        payload.setdefault("season", self._infer_season(ts, hemisphere=hemisphere))

        return EventContext(**payload)

    def get_last_event_time(self, user_id: Union[UUID, str], event_type: EventType) -> Optional[datetime]:
        """Fetch the last seen timestamp for an event type."""
        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return None
        return self.event_history.get(user_uuid, {}).get(event_type)

    def get_recent_events(
        self,
        user_id: Union[UUID, str],
        event_types: Optional[List[EventType]] = None,
        limit: int = 10,
    ) -> List[BaseEvent]:
        """Return most recent tracked events for user (in-memory cache)."""

        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return []
        events = list(self._recent_events.get(user_uuid, []))
        if event_types:
            events = [event for event in events if event.event_type in event_types]
        return list(events)[-limit:]
    
    async def _periodic_flush(self):
        """Periodically flush events to warehouse."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval_seconds)
                await self._flush_events_to_warehouse()
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def track_event(
        self,
        event: BaseEvent,
        context: Optional[EventContext] = None
    ) -> bool:
        """Track an event with privacy controls."""
        try:
            # Set context if provided
            if context:
                event.context = context
            
            # Check consent if user is identified
            if event.user_id:
                if not await self._check_analytics_consent(event.user_id):
                    logger.info(f"Analytics consent not granted for user {event.user_id}")
                    return False
                
                # Update consent flags
                event.consent_flags = await self._get_user_consents(event.user_id)
            
            # Apply privacy transforms
            event = await self._apply_privacy_transforms(event)
            
            # Store event
            self.events.append(event)

            # Update user profile
            if event.user_id:
                await self._update_user_profile(event)
                self.event_history[event.user_id][event.event_type] = event.timestamp
                recent_events = self._recent_events[event.user_id]
                recent_events.append(event)

            # Batch flush if needed
            if len(self.events) >= self.batch_size:
                await self._flush_events_to_warehouse()
            
            logger.debug(f"Tracked event: {event.event_type} for user {event.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
            return False
    
    async def _check_analytics_consent(self, user_id: UUID) -> bool:
        """Check if user has granted analytics consent."""
        # Check cache first
        if user_id in self.consent_cache:
            return self.consent_cache[user_id].get(ConsentType.ANALYTICS, False)
        
        # Load from storage
        user_pii = self.user_pii.get(user_id)
        if not user_pii:
            return False  # No consent recorded
        
        has_consent = user_pii.has_consent(ConsentType.ANALYTICS)
        
        # Cache result
        if user_id not in self.consent_cache:
            self.consent_cache[user_id] = {}
        self.consent_cache[user_id][ConsentType.ANALYTICS] = has_consent
        
        return has_consent
    
    async def _get_user_consents(self, user_id: UUID) -> Dict[ConsentType, bool]:
        """Get all consent flags for user."""
        user_pii = self.user_pii.get(user_id)
        if not user_pii:
            return {}
        
        consents = {}
        for consent_type in ConsentType:
            consents[consent_type] = user_pii.has_consent(consent_type)
        
        return consents
    
    async def _apply_privacy_transforms(self, event: BaseEvent) -> BaseEvent:
        """Apply privacy transforms to event data."""
        # Hash IP addresses
        if event.context and event.context.ip_address:
            event.context.ip_address = self._hash_pii(event.context.ip_address)
        
        # Remove or hash sensitive properties based on PII level
        if event.pii_level == PIILevel.SENSITIVE:
            # Apply additional anonymization for sensitive events
            event = await self._anonymize_sensitive_event(event)
        
        return event
    
    def _hash_pii(self, data: str) -> str:
        """Hash PII data for privacy."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _anonymize_sensitive_event(self, event: BaseEvent) -> BaseEvent:
        """Anonymize sensitive event data."""
        # For reflection events, remove text content but keep metadata
        if event.event_type == EventType.REFLECTION_SUBMITTED:
            if "content" in event.properties:
                del event.properties["content"]
            if "contains_pii" not in event.properties:
                event.properties["contains_pii"] = True
        
        return event
    
    async def _update_user_profile(self, event: BaseEvent):
        """Update user behavioral profile from event."""
        if not event.user_id:
            return
        
        # Get or create profile
        profile = self.user_profiles.get(event.user_id)
        if not profile:
            profile = UserProfile(
                user_id=event.user_id,
                created_at=event.timestamp
            )
            self.user_profiles[event.user_id] = profile
        
        # Update last active
        profile.last_active_at = event.timestamp
        
        # Update event counters
        if event.event_type == EventType.PLAN_GENERATED:
            profile.total_plans_generated += 1
        elif event.event_type == EventType.MEAL_LOGGED:
            profile.total_meals_logged += 1
        elif event.event_type == EventType.NUDGE_SENT:
            profile.total_nudges_sent += 1
        elif event.event_type == EventType.NUDGE_CLICKED:
            profile.total_nudges_clicked += 1
        elif event.event_type == EventType.SUBSCRIBE_ACTIVATED:
            profile.current_tier = event.properties.get("tier")
            profile.subscription_start = event.timestamp
            if "price_usd" in event.properties:
                profile.ltv_usd += event.properties["price_usd"]
    
    async def _flush_events_to_warehouse(self):
        """Flush events to data warehouse."""
        if not self.events:
            return
        
        try:
            # Convert events to warehouse format
            warehouse_events = []
            for event in self.events:
                warehouse_data = event.to_warehouse_format()
                warehouse_events.append(warehouse_data)
            
            # In production, send to actual warehouse (BigQuery, Snowflake, etc.)
            logger.info(f"Flushing {len(warehouse_events)} events to warehouse")
            
            # For development, log sample events
            if warehouse_events:
                sample_event = warehouse_events[0]
                logger.debug(f"Sample warehouse event: {json.dumps(sample_event, indent=2)}")
            
            # Clear processed events
            self.events.clear()
            
        except Exception as e:
            logger.error(f"Error flushing events to warehouse: {e}")
    
    # Convenience methods for tracking specific events
    
    async def track_plan_generated(
        self,
        user_id: UUID,
        plan_id: UUID,
        ruleset: str = "default",
        est_cost_cents: int = 0,
        duration_ms: int = 0,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track meal plan generation."""
        event = PlanGeneratedEvent(
            user_id=user_id,
            plan_id=plan_id,
            ruleset=ruleset,
            est_cost_cents=est_cost_cents,
            duration_ms=duration_ms,
            **kwargs
        )
        return await self.track_event(event, context)
    
    async def track_meal_logged(
        self,
        user_id: UUID,
        meal_id: UUID,
        status: str,
        source: str,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track meal logging."""
        event = MealLoggedEvent(
            user_id=user_id,
            meal_id=meal_id,
            status=status,
            source=source,
            **kwargs
        )
        return await self.track_event(event, context)
    
    async def track_nudge_sent(
        self,
        user_id: UUID,
        template_id: str,
        channel: str,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track nudge/notification sent."""
        event = NudgeSentEvent(
            user_id=user_id,
            template_id=template_id,
            channel=channel,
            **kwargs
        )
        return await self.track_event(event, context)
    
    async def track_nudge_clicked(
        self,
        user_id: UUID,
        nudge_id: str,
        template_id: str,
        channel: str,
        time_to_click_seconds: int,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track nudge click."""
        event = NudgeClickedEvent(
            user_id=user_id,
            nudge_id=nudge_id,
            template_id=template_id,
            channel=channel,
            time_to_click_seconds=time_to_click_seconds,
            **kwargs
        )
        return await self.track_event(event, context)

    async def track_crew_joined(
        self,
        user_id: UUID,
        crew_id: UUID,
        crew_type: str,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track crew joining."""
        event = CrewJoinedEvent(
            user_id=user_id,
            crew_id=crew_id,
            crew_type=crew_type,
            **kwargs
        )
        return await self.track_event(event, context)

    async def track_reflection_submitted(
        self,
        user_id: UUID,
        reflection_id: UUID,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track reflection submission."""
        event = ReflectionSubmittedEvent(
            user_id=user_id,
            reflection_id=reflection_id,
            **kwargs
        )
        return await self.track_event(event, context)

    async def track_strategy_report_scheduled(
        self,
        user_id: Union[UUID, str],
        scheduled_for: datetime,
        channel: str,
        cadence: str,
        context: Optional[EventContext] = None,
        personalization_score: Optional[float] = None,
        inventory_sources: Optional[List[str]] = None,
        goal_focus: Optional[str] = None,
    ) -> bool:
        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return False
        event = StrategyReportScheduledEvent(
            user_id=user_uuid,
            scheduled_for=scheduled_for,
            channel=channel,
            cadence=cadence,
            personalization_score=personalization_score,
            inventory_sources=inventory_sources,
            goal_focus=goal_focus,
        )
        return await self.track_event(event, context)

    async def track_recovery_plan_created(
        self,
        user_id: Union[UUID, str],
        plan_id: str,
        deviation_reason: Optional[str],
        channel: str,
        scheduled_for: datetime,
        context: Optional[EventContext] = None,
    ) -> bool:
        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return False
        event = RecoveryPlanCreatedEvent(
            user_id=user_uuid,
            plan_id=plan_id,
            deviation_reason=deviation_reason,
            channel=channel,
            scheduled_for=scheduled_for,
        )
        return await self.track_event(event, context)

    async def track_progress_summary(
        self,
        user_id: Union[UUID, str],
        period_start: datetime,
        period_end: datetime,
        channel: str,
        highlights: Optional[List[str]] = None,
        context: Optional[EventContext] = None,
    ) -> bool:
        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return False
        event = ProgressSummaryPublishedEvent(
            user_id=user_uuid,
            period_start=period_start,
            period_end=period_end,
            channel=channel,
            highlights=highlights,
        )
        return await self.track_event(event, context)

    async def track_message_ingested(
        self,
        user_id: Optional[Union[UUID, str]],
        platform: str,
        tones_detected: Optional[List[str]] = None,
        token_count: Optional[int] = None,
        context: Optional[EventContext] = None,
    ) -> bool:
        user_uuid = self._coerce_uuid(user_id)
        event = MessageIngestedEvent(
            user_id=user_uuid,
            platform=platform,
            tones_detected=tones_detected,
            token_count=token_count,
        )
        return await self.track_event(event, context)

    async def track_wearable_sync(
        self,
        user_id: Union[UUID, str],
        provider: str,
        metrics: Dict[str, Any],
        synced_at: datetime,
        context: Optional[EventContext] = None,
    ) -> bool:
        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return False
        event = WearableSyncEvent(
            user_id=user_uuid,
            provider=provider,
            metrics=metrics,
            synced_at=synced_at,
        )
        return await self.track_event(event, context)

    async def track_inventory_state(
        self,
        user_id: Union[UUID, str],
        inventory_id: str,
        location: str,
        freshness_index: Optional[float] = None,
        expiring_items: Optional[int] = None,
        context: Optional[EventContext] = None,
    ) -> bool:
        user_uuid = self._coerce_uuid(user_id)
        if not user_uuid:
            return False
        event = InventoryStateRecordedEvent(
            user_id=user_uuid,
            inventory_id=inventory_id,
            location=location,
            freshness_index=freshness_index,
            expiring_items=expiring_items,
        )
        return await self.track_event(event, context)
    
    async def track_paywall_viewed(
        self,
        user_id: UUID,
        price_usd: float,
        variant: str,
        source: str,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track paywall view."""
        event = PaywallViewedEvent(
            user_id=user_id,
            price_usd=price_usd,
            variant=variant,
            source=source,
            **kwargs
        )
        return await self.track_event(event, context)
    
    async def track_subscribe_started(
        self,
        user_id: UUID,
        tier: str,
        interval: str,
        price_usd: float,
        source: str,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track subscription start."""
        event = SubscribeStartedEvent(
            user_id=user_id,
            tier=tier,
            interval=interval,
            price_usd=price_usd,
            source=source,
            **kwargs
        )
        return await self.track_event(event, context)
    
    async def track_subscribe_activated(
        self,
        user_id: UUID,
        tier: str,
        price_usd: float,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track subscription activation."""
        event = SubscribeActivatedEvent(
            user_id=user_id,
            tier=tier,
            price_usd=price_usd,
            **kwargs
        )
        return await self.track_event(event, context)
    
    async def track_churned(
        self,
        user_id: UUID,
        churn_type: str,
        previous_tier: str,
        context: Optional[EventContext] = None,
        **kwargs
    ) -> bool:
        """Track user churn."""
        event = ChurnedEvent(
            user_id=user_id,
            churn_type=churn_type,
            previous_tier=previous_tier,
            **kwargs
        )
        return await self.track_event(event, context)
    
    # Consent management
    
    async def update_user_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
        granted: bool,
        source: str = "app",
        legal_basis: Optional[str] = None
    ) -> bool:
        """Update user consent preferences."""
        try:
            # Get or create user PII record
            user_pii = self.user_pii.get(user_id)
            if not user_pii:
                user_pii = UserPII(user_id=user_id)
                self.user_pii[user_id] = user_pii
            
            # Add consent record
            consent = UserConsent(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                granted_at=datetime.now(timezone.utc),
                source=source,
                legal_basis=legal_basis
            )
            
            # Remove old consent of same type
            user_pii.consents = [
                c for c in user_pii.consents 
                if c.consent_type != consent_type
            ]
            user_pii.consents.append(consent)
            
            # Clear cache
            if user_id in self.consent_cache:
                del self.consent_cache[user_id]
            
            logger.info(f"Updated consent for user {user_id}: {consent_type} = {granted}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating consent: {e}")
            return False
    
    async def request_data_deletion(self, user_id: UUID) -> bool:
        """Request user data deletion (GDPR compliance)."""
        try:
            # Mark for deletion in PII record
            user_pii = self.user_pii.get(user_id)
            if user_pii:
                user_pii.deletion_requested = True
                user_pii.deletion_requested_at = datetime.now(timezone.utc)
                user_pii.retention_until = datetime.now(timezone.utc) + timedelta(days=30)
            
            # Clear behavioral profile (or anonymize)
            if user_id in self.user_profiles:
                # In production, anonymize rather than delete for analytics
                profile = self.user_profiles[user_id]
                # Keep aggregated metrics but remove identifiers
                # This would be handled by the warehouse deletion job
            
            logger.info(f"Data deletion requested for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error requesting data deletion: {e}")
            return False
    
    # Analytics queries
    
    def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user behavioral profile."""
        return self.user_profiles.get(user_id)
    
    def get_events_for_user(
        self,
        user_id: UUID,
        event_types: Optional[List[EventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[BaseEvent]:
        """Get events for specific user."""
        events = [
            event for event in self.events 
            if event.user_id == user_id
        ]
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return events
    
    def get_event_counts_by_type(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[EventType, int]:
        """Get event counts by type."""
        events = self.events
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        counts = {}
        for event in events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        
        return counts
    
    async def cleanup(self):
        """Cleanup resources."""
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Final flush
        await self._flush_events_to_warehouse()
        
        logger.info("Analytics service cleanup completed")
