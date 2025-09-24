"""Domain models for Track D - Integrations.

Handles Calendar, Grocery, and Fitness integrations with external services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4
from decimal import Decimal


class CalendarProvider(Enum):
    """Supported calendar providers."""
    GOOGLE = "google"
    OUTLOOK = "outlook"
    APPLE = "apple"  # For future iCloud integration


class EventType(Enum):
    """Types of calendar events."""
    MEAL_PREP = "meal_prep"
    COOKING = "cooking"
    GROCERY_SHOPPING = "grocery_shopping"
    MEAL_TIME = "meal_time"


class ReminderType(Enum):
    """Types of event reminders."""
    NOTIFICATION = "notification"
    EMAIL = "email"
    SMS = "sms"


class GroceryPartner(Enum):
    """Supported grocery delivery partners."""
    INSTACART = "instacart"
    AMAZON_FRESH = "amazon_fresh"
    WALMART_GROCERY = "walmart_grocery"
    TARGET_SHIPT = "target_shipt"
    KROGER = "kroger"
    GENERIC_CSV = "generic_csv"


class FitnessProvider(Enum):
    """Supported fitness data providers."""
    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    FITBIT = "fitbit"
    GARMIN = "garmin"
    STRAVA = "strava"
    MYFITNESSPAL = "myfitnesspal"


class WorkoutType(Enum):
    """Types of workouts for recovery meal adjustment."""
    CARDIO = "cardio"
    STRENGTH = "strength"
    HIIT = "hiit"
    YOGA = "yoga"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    WALKING = "walking"
    OTHER = "other"


@dataclass(frozen=True)
class CalendarEvent:
    """Calendar event for meal preparation and cooking."""
    
    event_id: str
    user_id: UUID
    provider: CalendarProvider
    external_event_id: Optional[str] = None
    title: str = ""
    description: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))
    event_type: EventType = EventType.MEAL_PREP
    meal_plan_id: Optional[UUID] = None
    recipe_id: Optional[UUID] = None
    reminders: List[ReminderType] = field(default_factory=list)
    reminder_minutes: List[int] = field(default_factory=lambda: [15, 60])  # 15 min, 1 hour before
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # RRULE format
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate event data."""
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        
        if len(self.reminder_minutes) != len(set(self.reminder_minutes)):
            raise ValueError("Duplicate reminder minutes not allowed")


@dataclass(frozen=True)
class OAuthCredentials:
    """OAuth credentials for external service integration."""
    
    user_id: UUID
    provider: Union[CalendarProvider, FitnessProvider]
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scope: List[str] = field(default_factory=list)
    provider_user_id: Optional[str] = None
    provider_email: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return False
        return datetime.now() >= self.token_expires_at
    
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (expires within 5 minutes)."""
        if not self.token_expires_at:
            return False
        return datetime.now() >= (self.token_expires_at - timedelta(minutes=5))


@dataclass
class GroceryItem:
    """Individual grocery list item."""
    
    item_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    quantity: Decimal = Decimal("1.0")
    unit: str = "item"  # piece, lb, oz, cup, etc.
    category: str = "misc"  # produce, dairy, meat, pantry, etc.
    estimated_price: Optional[Decimal] = None
    recipe_id: Optional[UUID] = None
    meal_plan_id: Optional[UUID] = None
    is_pantry_staple: bool = False
    brand_preference: Optional[str] = None
    notes: str = ""
    
    def __post_init__(self):
        """Validate grocery item data."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if self.estimated_price is not None and self.estimated_price < 0:
            raise ValueError("Price cannot be negative")


@dataclass
class GroceryList:
    """Generated grocery list for meal plans."""
    
    list_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    meal_plan_id: Optional[UUID] = None
    title: str = "Weekly Grocery List"
    items: List[GroceryItem] = field(default_factory=list)
    total_estimated_cost: Optional[Decimal] = None
    store_preference: Optional[str] = None
    dietary_filters: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_item(self, item: GroceryItem) -> None:
        """Add item to grocery list."""
        # Check for duplicates and merge quantities
        for existing_item in self.items:
            if (existing_item.name.lower() == item.name.lower() and 
                existing_item.unit == item.unit):
                existing_item.quantity += item.quantity
                return
        
        self.items.append(item)
        self.updated_at = datetime.now()
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from grocery list."""
        original_length = len(self.items)
        self.items = [item for item in self.items if item.item_id != item_id]
        
        if len(self.items) < original_length:
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_items_by_category(self) -> Dict[str, List[GroceryItem]]:
        """Group items by category for organized shopping."""
        categories: Dict[str, List[GroceryItem]] = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        return categories
    
    def calculate_total_cost(self) -> Decimal:
        """Calculate total estimated cost."""
        total = Decimal("0.00")
        for item in self.items:
            if item.estimated_price:
                total += item.estimated_price * item.quantity
        
        self.total_estimated_cost = total
        return total


@dataclass
class PartnerDeepLink:
    """Partner service deep link for grocery ordering."""
    
    partner: GroceryPartner
    deeplink_url: str
    tracking_params: Dict[str, str] = field(default_factory=dict)
    estimated_availability: float = 1.0  # 0.0 to 1.0
    estimated_delivery_time: Optional[timedelta] = None
    minimum_order: Optional[Decimal] = None
    delivery_fee: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FitnessData:
    """Daily fitness summary for recovery meal adjustment."""
    
    data_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    date: datetime = field(default_factory=lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    provider: FitnessProvider = FitnessProvider.APPLE_HEALTH
    
    # Activity metrics
    steps: Optional[int] = None
    distance_km: Optional[Decimal] = None
    calories_burned: Optional[int] = None
    active_minutes: Optional[int] = None
    
    # Workout data
    workouts: List['WorkoutSession'] = field(default_factory=list)
    
    # Recovery indicators
    resting_heart_rate: Optional[int] = None
    sleep_hours: Optional[Decimal] = None
    stress_level: Optional[int] = None  # 1-10 scale
    
    # Derived metrics
    activity_level: str = "moderate"  # low, moderate, high, very_high
    recovery_needed: bool = False
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def calculate_activity_level(self) -> str:
        """Calculate activity level from metrics."""
        if not self.steps and not self.workouts:
            return "low"
        
        # Basic step-based calculation
        if self.steps:
            if self.steps < 5000:
                base_level = "low"
            elif self.steps < 10000:
                base_level = "moderate" 
            elif self.steps < 15000:
                base_level = "high"
            else:
                base_level = "very_high"
        else:
            base_level = "moderate"
        
        # Adjust for intense workouts
        intense_workouts = sum(1 for w in self.workouts 
                             if w.workout_type in [WorkoutType.HIIT, WorkoutType.STRENGTH] 
                             and w.duration_minutes > 30)
        
        if intense_workouts >= 2:
            if base_level in ["low", "moderate"]:
                base_level = "high"
            elif base_level == "high":
                base_level = "very_high"
        
        return base_level
    
    def needs_recovery_nutrition(self) -> bool:
        """Determine if recovery-focused nutrition is needed."""
        # High activity or multiple intense workouts
        if self.calculate_activity_level() in ["high", "very_high"]:
            return True
        
        # Stress indicators
        if self.resting_heart_rate and self.resting_heart_rate > 70:
            return True
        
        if self.sleep_hours and self.sleep_hours < Decimal("6.5"):
            return True
        
        if self.stress_level and self.stress_level > 7:
            return True
        
        return False


@dataclass
class WorkoutSession:
    """Individual workout session data."""
    
    session_id: str = field(default_factory=lambda: str(uuid4()))
    workout_type: WorkoutType = WorkoutType.OTHER
    duration_minutes: int = 0
    calories_burned: Optional[int] = None
    intensity: str = "moderate"  # low, moderate, high
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    heart_rate_avg: Optional[int] = None
    heart_rate_max: Optional[int] = None
    notes: str = ""
    
    def __post_init__(self):
        """Validate workout session data."""
        if self.duration_minutes < 0:
            raise ValueError("Duration cannot be negative")
        
        if self.calories_burned is not None and self.calories_burned < 0:
            raise ValueError("Calories burned cannot be negative")


@dataclass
class IntegrationSettings:
    """User settings for Track D integrations."""
    
    user_id: UUID
    
    # Calendar settings
    calendar_enabled: bool = False
    calendar_provider: Optional[CalendarProvider] = None
    default_prep_duration: int = 30  # minutes
    default_cook_duration: int = 45  # minutes
    meal_reminders_enabled: bool = True
    prep_reminders_enabled: bool = True
    
    # Grocery settings  
    grocery_enabled: bool = False
    preferred_stores: List[str] = field(default_factory=list)
    grocery_partners: List[GroceryPartner] = field(default_factory=list)
    auto_generate_lists: bool = True
    include_pantry_staples: bool = False
    
    # Fitness settings
    fitness_enabled: bool = False
    fitness_provider: Optional[FitnessProvider] = None
    auto_adjust_nutrition: bool = False
    recovery_meal_preference: str = "high_protein"  # high_protein, anti_inflammatory, light
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


# Export all models
__all__ = [
    "CalendarProvider",
    "EventType", 
    "ReminderType",
    "GroceryPartner",
    "FitnessProvider",
    "WorkoutType",
    "CalendarEvent",
    "OAuthCredentials", 
    "GroceryItem",
    "GroceryList",
    "PartnerDeepLink",
    "FitnessData",
    "WorkoutSession",
    "IntegrationSettings"
]
