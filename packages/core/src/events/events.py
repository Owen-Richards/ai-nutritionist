"""
Domain events for the AI Nutritionist application.

These events represent key business occurrences in the nutrition domain.
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from .base import DomainEvent


class UserRegistered(DomainEvent):
    """
    Event fired when a new user registers in the system.
    
    Contains user identification and initial profile data.
    """
    
    def __init__(
        self,
        user_id: str,
        email: str,
        timestamp: Optional[datetime] = None,
        profile_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize UserRegistered event."""
        super().__init__(
            aggregate_id=user_id,
            user_id=user_id,
            email=email,
            registration_timestamp=timestamp or datetime.utcnow(),
            profile_data=profile_data or {},
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def email(self) -> str:
        """Get user email."""
        return self.data["email"]
    
    @property
    def registration_timestamp(self) -> datetime:
        """Get registration timestamp."""
        return self.data["registration_timestamp"]
    
    @property
    def profile_data(self) -> Dict[str, Any]:
        """Get initial profile data."""
        return self.data["profile_data"]


class MealPlanCreated(DomainEvent):
    """
    Event fired when a meal plan is created for a user.
    
    Contains plan details and nutritional parameters.
    """
    
    def __init__(
        self,
        user_id: str,
        plan_id: str,
        week_start: datetime,
        plan_type: str = "weekly",
        nutritional_targets: Optional[Dict[str, float]] = None,
        meal_count: int = 21,  # 3 meals x 7 days
        **kwargs
    ):
        """Initialize MealPlanCreated event."""
        super().__init__(
            aggregate_id=plan_id,
            user_id=user_id,
            plan_id=plan_id,
            week_start=week_start,
            plan_type=plan_type,
            nutritional_targets=nutritional_targets or {},
            meal_count=meal_count,
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def plan_id(self) -> str:
        """Get plan ID."""
        return self.data["plan_id"]
    
    @property
    def week_start(self) -> datetime:
        """Get week start date."""
        return self.data["week_start"]
    
    @property
    def plan_type(self) -> str:
        """Get plan type."""
        return self.data["plan_type"]
    
    @property
    def nutritional_targets(self) -> Dict[str, float]:
        """Get nutritional targets."""
        return self.data["nutritional_targets"]


class NutritionGoalSet(DomainEvent):
    """
    Event fired when a user sets or updates a nutrition goal.
    
    Contains goal type, target value, and timeline information.
    """
    
    def __init__(
        self,
        user_id: str,
        goal_type: str,
        target_value: float,
        unit: str,
        timeline: str = "weekly",
        previous_value: Optional[float] = None,
        **kwargs
    ):
        """Initialize NutritionGoalSet event."""
        super().__init__(
            aggregate_id=user_id,
            user_id=user_id,
            goal_type=goal_type,
            target_value=target_value,
            unit=unit,
            timeline=timeline,
            previous_value=previous_value,
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def goal_type(self) -> str:
        """Get goal type (e.g., 'calories', 'protein', 'weight_loss')."""
        return self.data["goal_type"]
    
    @property
    def target_value(self) -> float:
        """Get target value."""
        return self.data["target_value"]
    
    @property
    def unit(self) -> str:
        """Get unit of measurement."""
        return self.data["unit"]
    
    @property
    def timeline(self) -> str:
        """Get timeline for the goal."""
        return self.data["timeline"]


class MealLogged(DomainEvent):
    """
    Event fired when a user logs a meal.
    
    Contains meal details, nutritional information, and timing.
    """
    
    def __init__(
        self,
        user_id: str,
        meal_id: str,
        calories: float,
        timestamp: Optional[datetime] = None,
        meal_type: str = "meal",
        nutritional_info: Optional[Dict[str, float]] = None,
        ingredients: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize MealLogged event."""
        super().__init__(
            aggregate_id=meal_id,
            user_id=user_id,
            meal_id=meal_id,
            calories=calories,
            meal_timestamp=timestamp or datetime.utcnow(),
            meal_type=meal_type,
            nutritional_info=nutritional_info or {},
            ingredients=ingredients or [],
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def meal_id(self) -> str:
        """Get meal ID."""
        return self.data["meal_id"]
    
    @property
    def calories(self) -> float:
        """Get calorie count."""
        return self.data["calories"]
    
    @property
    def meal_timestamp(self) -> datetime:
        """Get meal timestamp."""
        return self.data["meal_timestamp"]
    
    @property
    def nutritional_info(self) -> Dict[str, float]:
        """Get detailed nutritional information."""
        return self.data["nutritional_info"]


class PaymentProcessed(DomainEvent):
    """
    Event fired when a payment is successfully processed.
    
    Contains payment details and subscription information.
    """
    
    def __init__(
        self,
        user_id: str,
        amount: float,
        subscription_id: str,
        currency: str = "USD",
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize PaymentProcessed event."""
        super().__init__(
            aggregate_id=subscription_id,
            user_id=user_id,
            amount=amount,
            subscription_id=subscription_id,
            currency=currency,
            payment_method=payment_method,
            transaction_id=transaction_id,
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def amount(self) -> float:
        """Get payment amount."""
        return self.data["amount"]
    
    @property
    def subscription_id(self) -> str:
        """Get subscription ID."""
        return self.data["subscription_id"]
    
    @property
    def currency(self) -> str:
        """Get currency code."""
        return self.data["currency"]


class HealthDataSynced(DomainEvent):
    """
    Event fired when health data is synced from external sources.
    
    Contains health metrics and source information.
    """
    
    def __init__(
        self,
        user_id: str,
        source: str,
        metrics: Dict[str, Any],
        sync_timestamp: Optional[datetime] = None,
        data_range: Optional[Dict[str, datetime]] = None,
        **kwargs
    ):
        """Initialize HealthDataSynced event."""
        super().__init__(
            aggregate_id=user_id,
            user_id=user_id,
            source=source,
            metrics=metrics,
            sync_timestamp=sync_timestamp or datetime.utcnow(),
            data_range=data_range or {},
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def source(self) -> str:
        """Get data source (e.g., 'fitbit', 'apple_health', 'garmin')."""
        return self.data["source"]
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get synced health metrics."""
        return self.data["metrics"]
    
    @property
    def sync_timestamp(self) -> datetime:
        """Get sync timestamp."""
        return self.data["sync_timestamp"]


class CoachingSessionCompleted(DomainEvent):
    """
    Event fired when an AI coaching session is completed.
    
    Contains session details and generated insights.
    """
    
    def __init__(
        self,
        user_id: str,
        session_id: str,
        insights: List[str],
        session_duration: Optional[int] = None,
        topics_covered: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize CoachingSessionCompleted event."""
        super().__init__(
            aggregate_id=session_id,
            user_id=user_id,
            session_id=session_id,
            insights=insights,
            session_duration=session_duration,
            topics_covered=topics_covered or [],
            recommendations=recommendations or [],
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def session_id(self) -> str:
        """Get session ID."""
        return self.data["session_id"]
    
    @property
    def insights(self) -> List[str]:
        """Get generated insights."""
        return self.data["insights"]
    
    @property
    def session_duration(self) -> Optional[int]:
        """Get session duration in minutes."""
        return self.data.get("session_duration")


class WeeklyReportGenerated(DomainEvent):
    """
    Event fired when a weekly nutrition report is generated.
    
    Contains report data and key metrics summary.
    """
    
    def __init__(
        self,
        user_id: str,
        report_id: str,
        metrics: Dict[str, Any],
        week_start: datetime,
        week_end: datetime,
        goal_achievements: Optional[Dict[str, bool]] = None,
        **kwargs
    ):
        """Initialize WeeklyReportGenerated event."""
        super().__init__(
            aggregate_id=report_id,
            user_id=user_id,
            report_id=report_id,
            metrics=metrics,
            week_start=week_start,
            week_end=week_end,
            goal_achievements=goal_achievements or {},
            **kwargs
        )
    
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self.data["user_id"]
    
    @property
    def report_id(self) -> str:
        """Get report ID."""
        return self.data["report_id"]
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get weekly metrics."""
        return self.data["metrics"]
    
    @property
    def week_start(self) -> datetime:
        """Get week start date."""
        return self.data["week_start"]
    
    @property
    def week_end(self) -> datetime:
        """Get week end date."""
        return self.data["week_end"]
