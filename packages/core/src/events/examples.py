"""
Example event handlers demonstrating event-driven architecture usage.

These handlers show how to implement business logic in response to domain events.
"""

import logging
from typing import Dict, List
from .base import Event
from .events import (
    UserRegistered,
    MealPlanCreated,
    NutritionGoalSet,
    MealLogged,
    PaymentProcessed,
    HealthDataSynced,
    CoachingSessionCompleted,
    WeeklyReportGenerated,
)
from .handlers import EventHandler, AsyncEventHandler, event_handler

logger = logging.getLogger(__name__)


@event_handler(UserRegistered)
class UserWelcomeHandler(EventHandler):
    """
    Send welcome email and setup initial user preferences.
    """
    
    def handle(self, event: Event) -> None:
        """Handle user registration."""
        if not isinstance(event, UserRegistered):
            return
        
        logger.info(f"Welcoming new user: {event.email}")
        
        # Simulate sending welcome email
        self._send_welcome_email(event.email, event.user_id)
        
        # Setup default preferences
        self._setup_default_preferences(event.user_id, event.profile_data)
    
    def _send_welcome_email(self, email: str, user_id: str) -> None:
        """Send welcome email to new user."""
        logger.info(f"Sending welcome email to {email} (user: {user_id})")
        # Implementation would integrate with email service
        
    def _setup_default_preferences(self, user_id: str, profile_data: Dict) -> None:
        """Setup default user preferences."""
        logger.info(f"Setting up default preferences for user {user_id}")
        # Implementation would create default nutrition goals, preferences, etc.


@event_handler(MealPlanCreated)
class MealPlanNotificationHandler(EventHandler):
    """
    Notify user about new meal plan and schedule reminders.
    """
    
    def handle(self, event: Event) -> None:
        """Handle meal plan creation."""
        if not isinstance(event, MealPlanCreated):
            return
        
        logger.info(f"Processing new meal plan {event.plan_id} for user {event.user_id}")
        
        # Send notification
        self._send_meal_plan_notification(event.user_id, event.plan_id)
        
        # Schedule meal reminders
        self._schedule_meal_reminders(event.user_id, event.week_start, event.meal_count)
    
    def _send_meal_plan_notification(self, user_id: str, plan_id: str) -> None:
        """Send notification about new meal plan."""
        logger.info(f"Sending meal plan notification to user {user_id} for plan {plan_id}")
        
    def _schedule_meal_reminders(self, user_id: str, week_start, meal_count: int) -> None:
        """Schedule meal reminders for the week."""
        logger.info(f"Scheduling {meal_count} meal reminders for user {user_id} starting {week_start}")


@event_handler(NutritionGoalSet, MealLogged)
class ProgressTrackingHandler(EventHandler):
    """
    Track user progress towards nutrition goals.
    """
    
    def handle(self, event: Event) -> None:
        """Handle nutrition-related events."""
        if isinstance(event, NutritionGoalSet):
            self._handle_goal_set(event)
        elif isinstance(event, MealLogged):
            self._handle_meal_logged(event)
    
    def _handle_goal_set(self, event: NutritionGoalSet) -> None:
        """Handle goal setting."""
        logger.info(f"User {event.user_id} set {event.goal_type} goal: {event.target_value} {event.unit}")
        
        # Update progress tracking system
        self._initialize_goal_tracking(event.user_id, event.goal_type, event.target_value)
    
    def _handle_meal_logged(self, event: MealLogged) -> None:
        """Handle meal logging."""
        logger.info(f"User {event.user_id} logged meal with {event.calories} calories")
        
        # Update daily progress
        self._update_daily_progress(event.user_id, event.calories, event.nutritional_info)
        
        # Check if goals are met
        self._check_goal_achievement(event.user_id)
    
    def _initialize_goal_tracking(self, user_id: str, goal_type: str, target_value: float) -> None:
        """Initialize goal tracking for user."""
        logger.info(f"Initializing {goal_type} tracking for user {user_id}")
        
    def _update_daily_progress(self, user_id: str, calories: float, nutritional_info: Dict) -> None:
        """Update daily nutrition progress."""
        logger.info(f"Updating daily progress for user {user_id}: +{calories} calories")
        
    def _check_goal_achievement(self, user_id: str) -> None:
        """Check if user has achieved their daily goals."""
        logger.info(f"Checking goal achievement for user {user_id}")


@event_handler(PaymentProcessed)
class SubscriptionHandler(AsyncEventHandler):
    """
    Handle subscription updates and billing events.
    """
    
    async def handle(self, event: Event) -> None:
        """Handle payment processing."""
        if not isinstance(event, PaymentProcessed):
            return
        
        logger.info(f"Processing payment of {event.amount} {event.currency} for user {event.user_id}")
        
        # Update subscription status
        await self._update_subscription_status(event.user_id, event.subscription_id)
        
        # Send receipt
        await self._send_payment_receipt(event.user_id, event.amount, event.currency)
        
        # Unlock premium features if applicable
        await self._unlock_premium_features(event.user_id, event.subscription_id)
    
    async def _update_subscription_status(self, user_id: str, subscription_id: str) -> None:
        """Update subscription status in database."""
        logger.info(f"Updating subscription {subscription_id} for user {user_id}")
        # Async database operation
        
    async def _send_payment_receipt(self, user_id: str, amount: float, currency: str) -> None:
        """Send payment receipt to user."""
        logger.info(f"Sending receipt for {amount} {currency} to user {user_id}")
        # Async email service call
        
    async def _unlock_premium_features(self, user_id: str, subscription_id: str) -> None:
        """Unlock premium features for user."""
        logger.info(f"Unlocking premium features for user {user_id}")


@event_handler(HealthDataSynced)
class HealthDataAnalysisHandler(AsyncEventHandler):
    """
    Analyze synced health data and generate insights.
    """
    
    async def handle(self, event: Event) -> None:
        """Handle health data sync."""
        if not isinstance(event, HealthDataSynced):
            return
        
        logger.info(f"Analyzing health data from {event.source} for user {event.user_id}")
        
        # Analyze the health metrics
        insights = await self._analyze_health_metrics(event.metrics, event.source)
        
        # Update user health profile
        await self._update_health_profile(event.user_id, event.metrics, insights)
        
        # Generate recommendations if needed
        if self._should_generate_recommendations(insights):
            await self._generate_health_recommendations(event.user_id, insights)
    
    async def _analyze_health_metrics(self, metrics: Dict, source: str) -> Dict:
        """Analyze health metrics and extract insights."""
        logger.info(f"Analyzing metrics from {source}: {list(metrics.keys())}")
        
        # Simulate AI analysis
        insights = {
            "trends": "improving",
            "notable_changes": [],
            "recommendations": [],
        }
        
        return insights
    
    async def _update_health_profile(self, user_id: str, metrics: Dict, insights: Dict) -> None:
        """Update user's health profile."""
        logger.info(f"Updating health profile for user {user_id}")
    
    def _should_generate_recommendations(self, insights: Dict) -> bool:
        """Determine if recommendations should be generated."""
        return len(insights.get("recommendations", [])) > 0
    
    async def _generate_health_recommendations(self, user_id: str, insights: Dict) -> None:
        """Generate personalized health recommendations."""
        logger.info(f"Generating health recommendations for user {user_id}")


@event_handler(CoachingSessionCompleted)
class CoachingInsightsHandler(EventHandler):
    """
    Process coaching session insights and update user profile.
    """
    
    def handle(self, event: Event) -> None:
        """Handle coaching session completion."""
        if not isinstance(event, CoachingSessionCompleted):
            return
        
        logger.info(f"Processing coaching session {event.session_id} for user {event.user_id}")
        
        # Store insights
        self._store_coaching_insights(event.user_id, event.insights)
        
        # Update coaching progress
        self._update_coaching_progress(event.user_id, event.session_id)
        
        # Schedule follow-up if needed
        if self._should_schedule_followup(event.insights):
            self._schedule_followup_session(event.user_id)
    
    def _store_coaching_insights(self, user_id: str, insights: List[str]) -> None:
        """Store coaching insights for future reference."""
        logger.info(f"Storing {len(insights)} insights for user {user_id}")
    
    def _update_coaching_progress(self, user_id: str, session_id: str) -> None:
        """Update user's coaching progress."""
        logger.info(f"Updating coaching progress for user {user_id}")
    
    def _should_schedule_followup(self, insights: List[str]) -> bool:
        """Determine if follow-up session should be scheduled."""
        return len(insights) > 3  # Example logic
    
    def _schedule_followup_session(self, user_id: str) -> None:
        """Schedule follow-up coaching session."""
        logger.info(f"Scheduling follow-up session for user {user_id}")


@event_handler(WeeklyReportGenerated)
class WeeklyReportHandler(AsyncEventHandler):
    """
    Process weekly reports and send to users.
    """
    
    async def handle(self, event: Event) -> None:
        """Handle weekly report generation."""
        if not isinstance(event, WeeklyReportGenerated):
            return
        
        logger.info(f"Processing weekly report {event.report_id} for user {event.user_id}")
        
        # Format report for different channels
        email_report = await self._format_email_report(event.metrics, event.goal_achievements)
        app_summary = await self._format_app_summary(event.metrics)
        
        # Send via multiple channels
        await self._send_email_report(event.user_id, email_report)
        await self._update_app_dashboard(event.user_id, app_summary)
        
        # Update long-term trends
        await self._update_long_term_trends(event.user_id, event.metrics)
    
    async def _format_email_report(self, metrics: Dict, achievements: Dict) -> Dict:
        """Format report for email delivery."""
        logger.info("Formatting email report")
        return {
            "summary": "Weekly nutrition summary",
            "metrics": metrics,
            "achievements": achievements,
        }
    
    async def _format_app_summary(self, metrics: Dict) -> Dict:
        """Format summary for app dashboard."""
        logger.info("Formatting app summary")
        return {
            "key_metrics": metrics,
            "progress_charts": [],
        }
    
    async def _send_email_report(self, user_id: str, report: Dict) -> None:
        """Send weekly report via email."""
        logger.info(f"Sending weekly report email to user {user_id}")
    
    async def _update_app_dashboard(self, user_id: str, summary: Dict) -> None:
        """Update app dashboard with weekly summary."""
        logger.info(f"Updating app dashboard for user {user_id}")
    
    async def _update_long_term_trends(self, user_id: str, metrics: Dict) -> None:
        """Update long-term trend analysis."""
        logger.info(f"Updating long-term trends for user {user_id}")


# Multi-event handler example
class ComprehensiveAnalyticsHandler(AsyncEventHandler):
    """
    Handler that processes multiple event types for comprehensive analytics.
    """
    
    @property
    def event_types(self) -> List:
        """Specify which events this handler processes."""
        return [
            MealLogged,
            NutritionGoalSet,
            HealthDataSynced,
            CoachingSessionCompleted,
            WeeklyReportGenerated,
        ]
    
    async def handle(self, event: Event) -> None:
        """Handle multiple event types for analytics."""
        logger.info(f"Processing {event.event_name} for analytics")
        
        # Extract data based on event type
        analytics_data = self._extract_analytics_data(event)
        
        # Update analytics database
        await self._update_analytics(event.metadata.user_id, analytics_data)
        
        # Trigger insights generation if threshold reached
        await self._check_insights_trigger(event.metadata.user_id)
    
    def _extract_analytics_data(self, event: Event) -> Dict:
        """Extract relevant analytics data from event."""
        if isinstance(event, MealLogged):
            return {
                "event_type": "meal_logged",
                "calories": event.calories,
                "timestamp": event.meal_timestamp,
            }
        elif isinstance(event, NutritionGoalSet):
            return {
                "event_type": "goal_set",
                "goal_type": event.goal_type,
                "target_value": event.target_value,
            }
        # Add other event types as needed
        
        return {"event_type": event.event_name}
    
    async def _update_analytics(self, user_id: str, data: Dict) -> None:
        """Update analytics database."""
        logger.info(f"Updating analytics for user {user_id}")
    
    async def _check_insights_trigger(self, user_id: str) -> None:
        """Check if we should trigger insights generation."""
        logger.info(f"Checking insights trigger for user {user_id}")


# Handler registration helper
def register_all_handlers(dispatcher):
    """
    Register all example handlers with the dispatcher.
    
    Args:
        dispatcher: The event dispatcher to register handlers with
    """
    handlers = [
        UserWelcomeHandler(),
        MealPlanNotificationHandler(),
        ProgressTrackingHandler(),
        SubscriptionHandler(),
        HealthDataAnalysisHandler(),
        CoachingInsightsHandler(),
        WeeklyReportHandler(),
        ComprehensiveAnalyticsHandler(),
    ]
    
    for handler in handlers:
        # Auto-register based on event_types property
        for event_type in handler.event_types:
            async_handler = isinstance(handler, AsyncEventHandler)
            dispatcher.subscribe(event_type, handler, async_handler)
    
    logger.info(f"Registered {len(handlers)} event handlers")
