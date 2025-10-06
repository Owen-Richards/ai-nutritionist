"""
Calendar Integration and Scheduling System
Manages meal scheduling, cooking reminders, grocery shopping, and calendar integration
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, date, timedelta, time
from dataclasses import dataclass, asdict
from enum import Enum
import json


class EventType(Enum):
    MEAL_PREP = "meal_prep"
    COOKING = "cooking"
    GROCERY_SHOPPING = "grocery_shopping"
    MEAL_TIME = "meal_time"
    NUTRITION_REMINDER = "nutrition_reminder"
    WATER_REMINDER = "water_reminder"
    SUPPLEMENT_REMINDER = "supplement_reminder"
    EXERCISE = "exercise"
    HEALTH_CHECKUP = "health_checkup"
    FAMILY_MEAL = "family_meal"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ReminderType(Enum):
    NOTIFICATION = "notification"
    SMS = "sms"
    EMAIL = "email"
    PHONE_CALL = "phone_call"


@dataclass
class CalendarEvent:
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    event_type: EventType
    priority: Priority = Priority.MEDIUM
    location: Optional[str] = None
    reminder_minutes: List[int] = None  # Minutes before event to remind
    recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, monthly
    attendees: List[str] = None  # Family member IDs
    meal_plan_id: Optional[str] = None
    recipe_id: Optional[str] = None
    grocery_list_id: Optional[str] = None
    notes: Optional[str] = None
    event_id: Optional[str] = None
    external_calendar_id: Optional[str] = None  # Google Calendar, Outlook, etc.
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.reminder_minutes is None:
            self.reminder_minutes = [15]  # Default 15 minutes
        if self.attendees is None:
            self.attendees = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class MealSchedule:
    family_member_id: str
    breakfast_time: Optional[time] = None
    lunch_time: Optional[time] = None
    dinner_time: Optional[time] = None
    snack_times: List[time] = None
    timezone: str = "UTC"
    
    def __post_init__(self):
        if self.snack_times is None:
            self.snack_times = []


@dataclass
class CookingSession:
    recipe_id: str
    scheduled_start: datetime
    estimated_duration_minutes: int
    assigned_cook: Optional[str] = None  # Family member ID
    prep_tasks: List[str] = None
    shopping_completed: bool = False
    prep_completed: bool = False
    cooking_completed: bool = False
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.prep_tasks is None:
            self.prep_tasks = []


@dataclass
class Reminder:
    reminder_id: str
    title: str
    message: str
    scheduled_time: datetime
    reminder_type: ReminderType
    recipient: str  # Phone number or email
    event_id: Optional[str] = None
    sent: bool = False
    sent_at: Optional[datetime] = None
    response_received: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class CalendarManager:
    """Manages calendar events and scheduling for nutrition activities"""
    
    def __init__(self, user_phone: str):
        self.user_phone = user_phone
        self.events: Dict[str, CalendarEvent] = {}
        self.meal_schedules: Dict[str, MealSchedule] = {}  # family_member_id -> schedule
        self.cooking_sessions: List[CookingSession] = []
        self.reminders: List[Reminder] = []
        self.default_meal_times = {
            "breakfast": time(7, 0),
            "lunch": time(12, 0),
            "dinner": time(18, 0)
        }
        self.last_updated = datetime.utcnow()
    
    def add_event(self, event: CalendarEvent) -> str:
        """Add calendar event"""
        if not event.event_id:
            event.event_id = f"event_{len(self.events)}_{datetime.utcnow().timestamp()}"
        
        self.events[event.event_id] = event
        
        # Create reminders for the event
        self._create_reminders_for_event(event)
        
        self.last_updated = datetime.utcnow()
        return event.event_id
    
    def update_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update calendar event"""
        if event_id not in self.events:
            return False
        
        event = self.events[event_id]
        
        # Update event attributes
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        # Update reminders if timing changed
        if 'start_time' in updates or 'reminder_minutes' in updates:
            self._update_reminders_for_event(event)
        
        self.last_updated = datetime.utcnow()
        return True
    
    def delete_event(self, event_id: str) -> bool:
        """Delete calendar event"""
        if event_id not in self.events:
            return False
        
        # Remove associated reminders
        self.reminders = [r for r in self.reminders if r.event_id != event_id]
        
        del self.events[event_id]
        self.last_updated = datetime.utcnow()
        return True
    
    def get_events_for_date(self, target_date: date) -> List[CalendarEvent]:
        """Get all events for a specific date"""
        events = []
        
        for event in self.events.values():
            if event.start_time.date() == target_date:
                events.append(event)
        
        # Sort by start time
        events.sort(key=lambda e: e.start_time)
        return events
    
    def get_events_for_week(self, start_date: date) -> Dict[str, List[CalendarEvent]]:
        """Get events organized by day for a week"""
        week_events = {}
        
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            day_name = current_date.strftime("%A")
            week_events[day_name] = self.get_events_for_date(current_date)
        
        return week_events
    
    def schedule_meal_prep_from_plan(self, 
                                   meal_plan: List[Dict[str, Any]],
                                   prep_day: date = None,
                                   prep_time: time = None) -> List[str]:
        """Schedule meal prep events from meal plan"""
        if prep_day is None:
            prep_day = date.today() + timedelta(days=1)  # Tomorrow
        
        if prep_time is None:
            prep_time = time(10, 0)  # 10 AM default
        
        event_ids = []
        
        # Group recipes by prep requirements
        prep_recipes = []
        for meal_entry in meal_plan:
            if not meal_entry.get("prepared", False):
                recipe = meal_entry.get("recipe")
                if recipe and recipe.get("prep_time_minutes", 0) > 10:
                    prep_recipes.append(meal_entry)
        
        if not prep_recipes:
            return event_ids
        
        # Create meal prep session
        total_prep_time = sum(
            recipe.get("recipe", {}).get("prep_time_minutes", 30) 
            for recipe in prep_recipes
        )
        
        prep_start = datetime.combine(prep_day, prep_time)
        prep_end = prep_start + timedelta(minutes=total_prep_time)
        
        prep_event = CalendarEvent(
            title=f"Meal Prep Session - {len(prep_recipes)} recipes",
            description=f"Prep meals for the week: {', '.join([r.get('recipe', {}).get('name', 'Unknown') for r in prep_recipes])}",
            start_time=prep_start,
            end_time=prep_end,
            event_type=EventType.MEAL_PREP,
            priority=Priority.MEDIUM,
            reminder_minutes=[60, 15],
            notes=f"Prep {len(prep_recipes)} recipes for the week"
        )
        
        event_id = self.add_event(prep_event)
        event_ids.append(event_id)
        
        return event_ids
    
    def schedule_cooking_sessions(self, 
                                meal_plan: List[Dict[str, Any]],
                                family_schedules: Dict[str, MealSchedule] = None) -> List[str]:
        """Schedule individual cooking sessions"""
        event_ids = []
        
        for meal_entry in meal_plan:
            recipe = meal_entry.get("recipe")
            meal_date = meal_entry.get("date")
            meal_type = meal_entry.get("meal_type")
            
            if not recipe or not meal_date:
                continue
            
            # Get appropriate meal time
            meal_time = self._get_meal_time(meal_type, family_schedules)
            
            # Calculate cooking start time (cooking time before meal time)
            cook_time_minutes = recipe.get("cook_time_minutes", 30)
            meal_datetime = datetime.combine(meal_date, meal_time)
            cook_start = meal_datetime - timedelta(minutes=cook_time_minutes)
            cook_end = meal_datetime
            
            cooking_event = CalendarEvent(
                title=f"Cook {recipe.get('name', 'Meal')}",
                description=f"Cooking {recipe.get('name')} for {meal_type}",
                start_time=cook_start,
                end_time=cook_end,
                event_type=EventType.COOKING,
                priority=Priority.MEDIUM,
                recipe_id=recipe.get("recipe_id"),
                reminder_minutes=[30, 10],
                notes=f"Serves {meal_entry.get('servings_planned', 1)}"
            )
            
            event_id = self.add_event(cooking_event)
            event_ids.append(event_id)
        
        return event_ids
    
    def schedule_grocery_shopping(self, 
                                grocery_list: List[Dict[str, Any]],
                                preferred_day: str = "Saturday",
                                preferred_time: time = None) -> str:
        """Schedule grocery shopping trip"""
        if preferred_time is None:
            preferred_time = time(9, 0)  # 9 AM default
        
        # Find next occurrence of preferred day
        today = date.today()
        days_ahead = 0
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        if preferred_day in day_names:
            target_weekday = day_names.index(preferred_day)
            days_ahead = target_weekday - today.weekday()
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
        
        shopping_date = today + timedelta(days=days_ahead)
        shopping_start = datetime.combine(shopping_date, preferred_time)
        
        # Estimate shopping duration based on list size
        item_count = len(grocery_list)
        estimated_minutes = max(30, min(120, item_count * 3))  # 3 minutes per item, 30-120 min range
        shopping_end = shopping_start + timedelta(minutes=estimated_minutes)
        
        shopping_event = CalendarEvent(
            title=f"Grocery Shopping - {item_count} items",
            description=f"Shopping for {item_count} items",
            start_time=shopping_start,
            end_time=shopping_end,
            event_type=EventType.GROCERY_SHOPPING,
            priority=Priority.MEDIUM,
            reminder_minutes=[120, 30],  # 2 hours and 30 minutes before
            notes=f"Don't forget reusable bags!"
        )
        
        return self.add_event(shopping_event)
    
    def schedule_family_meals(self, 
                            meal_plan: List[Dict[str, Any]],
                            family_members: List[str]) -> List[str]:
        """Schedule family meal times"""
        event_ids = []
        
        for meal_entry in meal_plan:
            recipe = meal_entry.get("recipe")
            meal_date = meal_entry.get("date")
            meal_type = meal_entry.get("meal_type")
            
            if not recipe or not meal_date:
                continue
            
            # Only schedule family meals for dinner (or specifically marked family meals)
            if meal_type != "dinner" and not meal_entry.get("family_meal", False):
                continue
            
            meal_time = self._get_meal_time(meal_type)
            meal_datetime = datetime.combine(meal_date, meal_time)
            meal_end = meal_datetime + timedelta(minutes=60)  # 1 hour for family meal
            
            family_event = CalendarEvent(
                title=f"Family {meal_type.title()} - {recipe.get('name')}",
                description=f"Family meal featuring {recipe.get('name')}",
                start_time=meal_datetime,
                end_time=meal_end,
                event_type=EventType.FAMILY_MEAL,
                priority=Priority.HIGH,
                attendees=family_members,
                recipe_id=recipe.get("recipe_id"),
                reminder_minutes=[60, 15]
            )
            
            event_id = self.add_event(family_event)
            event_ids.append(event_id)
        
        return event_ids
    
    def set_meal_schedule(self, family_member_id: str, schedule: MealSchedule) -> None:
        """Set meal schedule for family member"""
        self.meal_schedules[family_member_id] = schedule
        self.last_updated = datetime.utcnow()
    
    def schedule_recurring_reminders(self) -> List[str]:
        """Set up recurring health and nutrition reminders"""
        event_ids = []
        
        # Daily water reminders
        for hour in [9, 12, 15, 18]:  # 9 AM, 12 PM, 3 PM, 6 PM
            reminder_time = time(hour, 0)
            today = date.today()
            
            water_event = CalendarEvent(
                title="Water Reminder",
                description="Time to drink some water! Stay hydrated 💧",
                start_time=datetime.combine(today, reminder_time),
                end_time=datetime.combine(today, reminder_time) + timedelta(minutes=5),
                event_type=EventType.WATER_REMINDER,
                priority=Priority.LOW,
                recurring=True,
                recurrence_pattern="daily",
                reminder_minutes=[0]  # Immediate reminder
            )
            
            event_id = self.add_event(water_event)
            event_ids.append(event_id)
        
        # Weekly meal planning reminder
        planning_day = time(19, 0)  # 7 PM Sunday
        sunday = date.today() + timedelta(days=(6 - date.today().weekday()) % 7)
        
        planning_event = CalendarEvent(
            title="Weekly Meal Planning",
            description="Time to plan next week's meals and create grocery list",
            start_time=datetime.combine(sunday, planning_day),
            end_time=datetime.combine(sunday, planning_day) + timedelta(minutes=30),
            event_type=EventType.NUTRITION_REMINDER,
            priority=Priority.MEDIUM,
            recurring=True,
            recurrence_pattern="weekly",
            reminder_minutes=[60, 15]
        )
        
        event_id = self.add_event(planning_event)
        event_ids.append(event_id)
        
        return event_ids
    
    def get_upcoming_events(self, days_ahead: int = 7) -> List[CalendarEvent]:
        """Get upcoming events within specified days"""
        end_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        upcoming = []
        for event in self.events.values():
            if datetime.utcnow() <= event.start_time <= end_date:
                upcoming.append(event)
        
        # Sort by start time
        upcoming.sort(key=lambda e: e.start_time)
        return upcoming
    
    def get_today_schedule(self) -> Dict[str, Any]:
        """Get today's complete schedule"""
        today = date.today()
        today_events = self.get_events_for_date(today)
        
        # Organize by event type
        schedule = {
            "date": today.isoformat(),
            "meals": [],
            "cooking": [],
            "shopping": [],
            "reminders": [],
            "other": []
        }
        
        for event in today_events:
            if event.event_type == EventType.MEAL_TIME or event.event_type == EventType.FAMILY_MEAL:
                schedule["meals"].append(event)
            elif event.event_type == EventType.COOKING or event.event_type == EventType.MEAL_PREP:
                schedule["cooking"].append(event)
            elif event.event_type == EventType.GROCERY_SHOPPING:
                schedule["shopping"].append(event)
            elif "REMINDER" in event.event_type.value:
                schedule["reminders"].append(event)
            else:
                schedule["other"].append(event)
        
        return schedule
    
    def _get_meal_time(self, meal_type: str, family_schedules: Dict[str, MealSchedule] = None) -> time:
        """Get appropriate meal time based on meal type and family schedules"""
        if family_schedules:
            # Find earliest meal time among family members
            earliest_time = None
            
            for schedule in family_schedules.values():
                if meal_type == "breakfast" and schedule.breakfast_time:
                    time_to_check = schedule.breakfast_time
                elif meal_type == "lunch" and schedule.lunch_time:
                    time_to_check = schedule.lunch_time
                elif meal_type == "dinner" and schedule.dinner_time:
                    time_to_check = schedule.dinner_time
                else:
                    continue
                
                if earliest_time is None or time_to_check < earliest_time:
                    earliest_time = time_to_check
            
            if earliest_time:
                return earliest_time
        
        # Fall back to default times
        return self.default_meal_times.get(meal_type, time(12, 0))
    
    def _create_reminders_for_event(self, event: CalendarEvent) -> None:
        """Create reminders for an event"""
        for minutes_before in event.reminder_minutes:
            reminder_time = event.start_time - timedelta(minutes=minutes_before)
            
            if reminder_time > datetime.utcnow():  # Only create future reminders
                reminder = Reminder(
                    reminder_id=f"reminder_{event.event_id}_{minutes_before}",
                    title=f"Upcoming: {event.title}",
                    message=f"{event.title} starts in {minutes_before} minutes",
                    scheduled_time=reminder_time,
                    reminder_type=ReminderType.SMS,
                    recipient=self.user_phone,
                    event_id=event.event_id
                )
                
                self.reminders.append(reminder)
    
    def _update_reminders_for_event(self, event: CalendarEvent) -> None:
        """Update reminders when event timing changes"""
        # Remove old reminders for this event
        self.reminders = [r for r in self.reminders if r.event_id != event.event_id]
        
        # Create new reminders
        self._create_reminders_for_event(event)
    
    def get_pending_reminders(self) -> List[Reminder]:
        """Get reminders that need to be sent"""
        now = datetime.utcnow()
        
        pending = [
            reminder for reminder in self.reminders
            if not reminder.sent and reminder.scheduled_time <= now
        ]
        
        return pending
    
    def mark_reminder_sent(self, reminder_id: str) -> bool:
        """Mark reminder as sent"""
        for reminder in self.reminders:
            if reminder.reminder_id == reminder_id:
                reminder.sent = True
                reminder.sent_at = datetime.utcnow()
                return True
        return False
    
    def get_calendar_summary(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get calendar summary for next period"""
        upcoming = self.get_upcoming_events(days_ahead)
        
        # Count by event type
        event_counts = {}
        for event in upcoming:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Find next important events
        next_meal = None
        next_cooking = None
        next_shopping = None
        
        for event in upcoming:
            if not next_meal and event.event_type in [EventType.MEAL_TIME, EventType.FAMILY_MEAL]:
                next_meal = event
            elif not next_cooking and event.event_type in [EventType.COOKING, EventType.MEAL_PREP]:
                next_cooking = event
            elif not next_shopping and event.event_type == EventType.GROCERY_SHOPPING:
                next_shopping = event
            
            if next_meal and next_cooking and next_shopping:
                break
        
        return {
            "total_events": len(upcoming),
            "event_counts": event_counts,
            "next_events": {
                "meal": asdict(next_meal) if next_meal else None,
                "cooking": asdict(next_cooking) if next_cooking else None,
                "shopping": asdict(next_shopping) if next_shopping else None
            },
            "pending_reminders": len(self.get_pending_reminders())
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "user_phone": self.user_phone,
            "events": {key: asdict(event) for key, event in self.events.items()},
            "meal_schedules": {key: asdict(schedule) for key, schedule in self.meal_schedules.items()},
            "cooking_sessions": [asdict(session) for session in self.cooking_sessions],
            "reminders": [asdict(reminder) for reminder in self.reminders],
            "default_meal_times": {key: time_obj.isoformat() for key, time_obj in self.default_meal_times.items()},
            "last_updated": self.last_updated.isoformat()
        }
