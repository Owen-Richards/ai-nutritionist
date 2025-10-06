"""
Conversational AI Nutritionist Service
Main service that coordinates all components and handles natural language conversations
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import re

from ..models.user_profile import UserProfile, FamilyMember
from ..models.inventory import InventoryManager, FoodItem, GroceryListItem, FoodCategory, StorageLocation
from ..models.meal_planning import MealPlanManager, Recipe, MealPlanEntry, MealType
from ..models.health_tracking import HealthTracker, FoodEntry, MealCategory, HealthGoal, ActivityLevel
from ..models.calendar_integration import CalendarManager, CalendarEvent, EventType


class ConversationType(Enum):
    GREETING = "greeting"
    FOOD_LOGGING = "food_logging"
    MEAL_PLANNING = "meal_planning"
    INVENTORY_MANAGEMENT = "inventory_management"
    GROCERY_SHOPPING = "grocery_shopping"
    HEALTH_TRACKING = "health_tracking"
    RECIPE_REQUEST = "recipe_request"
    NUTRITION_ADVICE = "nutrition_advice"
    CALENDAR_SCHEDULING = "calendar_scheduling"
    FAMILY_COORDINATION = "family_coordination"
    GOAL_SETTING = "goal_setting"
    PROGRESS_TRACKING = "progress_tracking"
    QUICK_QUESTION = "quick_question"
    GOODBYE = "goodbye"


class MessageIntent(Enum):
    LOG_FOOD = "log_food"
    ASK_NUTRITION = "ask_nutrition"
    PLAN_MEALS = "plan_meals"
    CHECK_INVENTORY = "check_inventory"
    ADD_TO_GROCERY_LIST = "add_to_grocery_list"
    SCHEDULE_EVENT = "schedule_event"
    GET_RECIPE = "get_recipe"
    TRACK_PROGRESS = "track_progress"
    SET_GOALS = "set_goals"
    FAMILY_UPDATE = "family_update"
    GET_RECOMMENDATIONS = "get_recommendations"
    CHECK_STATUS = "check_status"


@dataclass
class ConversationContext:
    user_phone: str
    conversation_id: str
    last_message_time: datetime
    current_topic: Optional[ConversationType] = None
    pending_actions: List[str] = None
    user_preferences: Dict[str, Any] = None
    conversation_history: List[Dict[str, Any]] = None
    awaiting_response: Optional[str] = None  # What we're waiting for from user
    
    def __post_init__(self):
        if self.pending_actions is None:
            self.pending_actions = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.conversation_history is None:
            self.conversation_history = []


class ConversationalNutritionistAI:
    """Main AI Nutritionist service that coordinates all components"""
    
    def __init__(self):
        self.active_conversations: Dict[str, ConversationContext] = {}
        self.user_profiles: Dict[str, UserProfile] = {}
        self.inventory_managers: Dict[str, InventoryManager] = {}
        self.meal_plan_managers: Dict[str, MealPlanManager] = {}
        self.health_trackers: Dict[str, HealthTracker] = {}
        self.calendar_managers: Dict[str, CalendarManager] = {}
        
        # Intent classification patterns
        self.intent_patterns = {
            MessageIntent.LOG_FOOD: [
                r"i (ate|had|consumed|just ate)",
                r"log.*food",
                r"track.*meal",
                r"record.*eating",
                r"food diary"
            ],
            MessageIntent.ASK_NUTRITION: [
                r"is.*healthy",
                r"nutrition.*facts",
                r"how many calories",
                r"what about.*protein",
                r"nutritional.*value"
            ],
            MessageIntent.PLAN_MEALS: [
                r"meal plan",
                r"plan.*meals?",
                r"create.*plan",
                r"weekly.*plan",
                r"what.*cook",
                r"dinner ideas",
                r"weekly menu",
                r"plan.*week",
                r"this week.*plan"
            ],
            MessageIntent.CHECK_INVENTORY: [
                r"what.*have.*fridge",
                r"check.*inventory",
                r"food.*stock",
                r"what.*left",
                r"expiring.*soon",
                r"what.*in.*pantry",
                r"what.*pantry"
            ],
            MessageIntent.ADD_TO_GROCERY_LIST: [
                r"add.*grocery",
                r"shopping.*list",
                r"need.*buy",
                r"pick up.*store",
                r"out of"
            ],
            MessageIntent.SCHEDULE_EVENT: [
                r"schedule.*cooking",
                r"remind.*meal",
                r"calendar.*event",
                r"when.*cook",
                r"meal.*time"
            ],
            MessageIntent.GET_RECIPE: [
                r"recipe.*for",
                r"how.*make",
                r"cooking.*instructions",
                r"ingredient.*list",
                r"cook.*[a-zA-Z]+"
            ],
            MessageIntent.TRACK_PROGRESS: [
                r"progress.*report",
                r"how.*doing",
                r"weight.*loss",
                r"health.*stats",
                r"achievement"
            ],
            MessageIntent.SET_GOALS: [
                r"goal.*weight",
                r"target.*calories",
                r"want.*lose",
                r"fitness.*goal",
                r"nutrition.*goal"
            ]
        }
    
    def process_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Process incoming message and generate response"""
        
        # Initialize or get conversation context
        context = self._get_or_create_context(phone_number, message)
        
        # Get user components
        user_profile = self._get_user_profile(phone_number)
        inventory_manager = self._get_inventory_manager(phone_number)
        meal_planner = self._get_meal_planner(phone_number)
        health_tracker = self._get_health_tracker(phone_number)
        calendar_manager = self._get_calendar_manager(phone_number)
        
        # Classify message intent
        intent = self._classify_intent(message)
        conversation_type = self._determine_conversation_type(message, context)
        
        # Update context
        context.current_topic = conversation_type
        context.last_message_time = datetime.utcnow()
        context.conversation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": message,
            "intent": intent.value if intent else None,
            "conversation_type": conversation_type.value
        })
        
        # Generate response based on intent and context
        response = self._generate_response(
            intent, conversation_type, message, context,
            user_profile, inventory_manager, meal_planner, 
            health_tracker, calendar_manager
        )
        
        # Add AI response to history
        context.conversation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "ai_response": response["message"],
            "actions_taken": response.get("actions", [])
        })
        
        return response
    
    def _get_or_create_context(self, phone_number: str, message: str) -> ConversationContext:
        """Get existing conversation context or create new one"""
        if phone_number not in self.active_conversations:
            self.active_conversations[phone_number] = ConversationContext(
                user_phone=phone_number,
                conversation_id=f"conv_{phone_number}_{datetime.utcnow().timestamp()}",
                last_message_time=datetime.utcnow()
            )
        
        return self.active_conversations[phone_number]
    
    def _get_user_profile(self, phone_number: str) -> UserProfile:
        """Get or create user profile"""
        if phone_number not in self.user_profiles:
            self.user_profiles[phone_number] = UserProfile(phone_number)
        return self.user_profiles[phone_number]
    
    def _get_inventory_manager(self, phone_number: str) -> InventoryManager:
        """Get or create inventory manager"""
        if phone_number not in self.inventory_managers:
            self.inventory_managers[phone_number] = InventoryManager(phone_number)
        return self.inventory_managers[phone_number]
    
    def _get_meal_planner(self, phone_number: str) -> MealPlanManager:
        """Get or create meal plan manager"""
        if phone_number not in self.meal_plan_managers:
            self.meal_plan_managers[phone_number] = MealPlanManager(phone_number)
        return self.meal_plan_managers[phone_number]
    
    def _get_health_tracker(self, phone_number: str) -> HealthTracker:
        """Get or create health tracker"""
        if phone_number not in self.health_trackers:
            self.health_trackers[phone_number] = HealthTracker(phone_number)
        return self.health_trackers[phone_number]
    
    def _get_calendar_manager(self, phone_number: str) -> CalendarManager:
        """Get or create calendar manager"""
        if phone_number not in self.calendar_managers:
            self.calendar_managers[phone_number] = CalendarManager(phone_number)
        return self.calendar_managers[phone_number]
    
    def _classify_intent(self, message: str) -> Optional[MessageIntent]:
        """Classify message intent using pattern matching"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return None
    
    def _determine_conversation_type(self, message: str, context: ConversationContext) -> ConversationType:
        """Determine conversation type based on message and context"""
        message_lower = message.lower()
        
        # Check for greetings using word boundaries
        greeting_patterns = [r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgood morning\b', r'\bgood afternoon\b']
        if any(re.search(pattern, message_lower) for pattern in greeting_patterns):
            return ConversationType.GREETING
        
        # Check for goodbyes using word boundaries
        goodbye_patterns = [r'\bbye\b', r'\bgoodbye\b', r'\bsee you\b', r'\bthanks\b', r'\bthank you\b']
        if any(re.search(pattern, message_lower) for pattern in goodbye_patterns):
            return ConversationType.GOODBYE
        
        # Use intent to determine conversation type
        intent = self._classify_intent(message)
        
        intent_to_conversation = {
            MessageIntent.LOG_FOOD: ConversationType.FOOD_LOGGING,
            MessageIntent.ASK_NUTRITION: ConversationType.NUTRITION_ADVICE,
            MessageIntent.PLAN_MEALS: ConversationType.MEAL_PLANNING,
            MessageIntent.CHECK_INVENTORY: ConversationType.INVENTORY_MANAGEMENT,
            MessageIntent.ADD_TO_GROCERY_LIST: ConversationType.GROCERY_SHOPPING,
            MessageIntent.SCHEDULE_EVENT: ConversationType.CALENDAR_SCHEDULING,
            MessageIntent.GET_RECIPE: ConversationType.RECIPE_REQUEST,
            MessageIntent.TRACK_PROGRESS: ConversationType.PROGRESS_TRACKING,
            MessageIntent.SET_GOALS: ConversationType.GOAL_SETTING,
            MessageIntent.FAMILY_UPDATE: ConversationType.FAMILY_COORDINATION
        }
        
        result = intent_to_conversation.get(intent, ConversationType.QUICK_QUESTION)
        return result
    
    def _generate_response(self, 
                          intent: Optional[MessageIntent],
                          conversation_type: ConversationType,
                          message: str,
                          context: ConversationContext,
                          user_profile: UserProfile,
                          inventory_manager: InventoryManager,
                          meal_planner: MealPlanManager,
                          health_tracker: HealthTracker,
                          calendar_manager: CalendarManager) -> Dict[str, Any]:
        """Generate appropriate response based on intent and context"""
        
        response = {
            "message": "",
            "actions": [],
            "suggestions": [],
            "data": {}
        }
        
        # Handle different conversation types
        if conversation_type == ConversationType.GREETING:
            response = self._handle_greeting(user_profile, health_tracker, calendar_manager)
        
        elif conversation_type == ConversationType.FOOD_LOGGING:
            response = self._handle_food_logging(message, context, health_tracker, inventory_manager)
        
        elif conversation_type == ConversationType.MEAL_PLANNING:
            response = self._handle_meal_planning(message, user_profile, meal_planner, inventory_manager)
        
        elif conversation_type == ConversationType.INVENTORY_MANAGEMENT:
            response = self._handle_inventory_management(message, inventory_manager)
        
        elif conversation_type == ConversationType.GROCERY_SHOPPING:
            response = self._handle_grocery_shopping(message, inventory_manager, meal_planner)
        
        elif conversation_type == ConversationType.HEALTH_TRACKING:
            response = self._handle_health_tracking(message, health_tracker, user_profile)
        
        elif conversation_type == ConversationType.RECIPE_REQUEST:
            response = self._handle_recipe_request(message, meal_planner, user_profile)
        
        elif conversation_type == ConversationType.NUTRITION_ADVICE:
            response = self._handle_nutrition_advice(message, user_profile, health_tracker)
        
        elif conversation_type == ConversationType.CALENDAR_SCHEDULING:
            response = self._handle_calendar_scheduling(message, calendar_manager, meal_planner)
        
        elif conversation_type == ConversationType.PROGRESS_TRACKING:
            response = self._handle_progress_tracking(health_tracker, user_profile)
        
        elif conversation_type == ConversationType.GOAL_SETTING:
            response = self._handle_goal_setting(message, user_profile, health_tracker)
        
        elif conversation_type == ConversationType.GOODBYE:
            response = self._handle_goodbye(user_profile)
        
        else:
            response = self._handle_general_question(message, user_profile, context)
        
        return response
    
    def _handle_greeting(self, user_profile: UserProfile, health_tracker: HealthTracker, calendar_manager: CalendarManager) -> Dict[str, Any]:
        """Handle greeting messages"""
        name = user_profile.name or "there"
        
        # Get today's summary
        today = date.today()
        nutrition_summary = health_tracker.get_daily_nutrition_summary(today)
        today_schedule = calendar_manager.get_today_schedule()
        
        # Personalized greeting based on time and data
        hour = datetime.now().hour
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
        
        message = f"{time_greeting}, {name}! 👋"
        
        # Add relevant info
        suggestions = []
        
        if nutrition_summary["entry_count"] == 0:
            message += " Ready to start tracking your nutrition today?"
            suggestions.append("Log breakfast")
            suggestions.append("Check meal plan")
        
        if today_schedule["cooking"]:
            next_cooking = today_schedule["cooking"][0]
            message += f" Don't forget you have cooking scheduled: {next_cooking.title}"
            suggestions.append("View cooking schedule")
        
        if not suggestions:
            suggestions = [
                "Check today's nutrition",
                "Plan meals for the week",
                "View grocery list",
                "Track weight"
            ]
        
        return {
            "message": message,
            "actions": ["greeting_processed"],
            "suggestions": suggestions,
            "data": {
                "nutrition_summary": nutrition_summary,
                "today_schedule": today_schedule
            }
        }
    
    def _handle_food_logging(self, message: str, context: ConversationContext, health_tracker: HealthTracker, inventory_manager: InventoryManager) -> Dict[str, Any]:
        """Handle food logging requests"""
        
        # Extract food information from message
        food_info = self._extract_food_info(message)
        
        if not food_info:
            return {
                "message": "I'd love to help you log that food! Can you tell me what you ate and approximately how much?",
                "actions": [],
                "suggestions": ["I had a chicken breast", "Ate 2 slices of pizza", "Drank a protein shake"],
                "data": {}
            }
        
        # Create food entry
        food_entry = FoodEntry(
            timestamp=datetime.utcnow(),
            food_name=food_info["name"],
            quantity=food_info["quantity"],
            unit=food_info["unit"],
            meal_category=food_info["meal_category"],
            calories=food_info.get("calories"),
            protein_g=food_info.get("protein"),
            carbs_g=food_info.get("carbs"),
            fat_g=food_info.get("fat")
        )
        
        # Log the food
        health_tracker.log_food(food_entry)
        
        # Update inventory if applicable
        if food_info.get("from_inventory"):
            inventory_manager.consume_item(food_info["name"], food_info["quantity"])
        
        # Get updated nutrition summary
        today_summary = health_tracker.get_daily_nutrition_summary(date.today())
        
        message = f"✅ Logged {food_info['quantity']} {food_info['unit']} of {food_info['name']}!"
        
        if today_summary["progress"]:
            calories_progress = today_summary["progress"]["calories"]["percentage"]
            protein_progress = today_summary["progress"]["protein"]["percentage"]
            
            message += f"\n\n📊 Today's progress:\n"
            message += f"Calories: {calories_progress:.0f}% of goal\n"
            message += f"Protein: {protein_progress:.0f}% of goal"
        
        suggestions = [
            "Log another food",
            "View full nutrition summary",
            "Add water intake"
        ]
        
        return {
            "message": message,
            "actions": ["food_logged"],
            "suggestions": suggestions,
            "data": {
                "food_entry": asdict(food_entry),
                "nutrition_summary": today_summary
            }
        }
    
    def _handle_meal_planning(self, message: str, user_profile: UserProfile, meal_planner: MealPlanManager, inventory_manager: InventoryManager) -> Dict[str, Any]:
        """Handle meal planning requests"""
        
        # Check if user wants to create a new meal plan
        if any(phrase in message.lower() for phrase in ["create", "new", "generate", "plan"]):
            
            # Get user preferences
            preferences = {
                "dietary_restrictions": [pref.value for pref in user_profile.dietary_preferences],
                "allergens": [allergy.allergen for allergy in user_profile.allergies],
                "disliked_foods": user_profile.food_dislikes,
                "preferred_cuisines": user_profile.cultural_cuisines,
                "cooking_skill": user_profile.cooking_preferences.skill_level,
                "max_cook_time": user_profile.cooking_preferences.max_cook_time
            }
            
            family_size = len(user_profile.family_members) + 1  # Include user
            
            try:
                # Create meal plan
                week_id = meal_planner.create_meal_plan(
                    start_date=date.today() + timedelta(days=1),  # Start tomorrow
                    preferences=preferences,
                    family_size=family_size,
                    budget=user_profile.budget_preferences.weekly_food_budget
                )
                
                meal_plan = meal_planner.get_meal_plan(week_id)
                summary = meal_planner.get_meal_plan_summary(week_id)
                
                message = f"🍽️ Created your weekly meal plan!\n\n"
                message += f"📋 {summary['total_meals']} meals planned\n"
                message += f"💰 Estimated cost: ${summary['total_cost']}\n"
                message += f"🔥 Total calories: {summary['total_calories']:,}"
                
                # Show first few meals
                message += "\n\n📅 This week's highlights:\n"
                for i, entry in enumerate(meal_plan[:3]):
                    message += f"• {entry.date.strftime('%A')}: {entry.recipe.name} ({entry.meal_type.value})\n"
                
                if len(meal_plan) > 3:
                    message += f"... and {len(meal_plan) - 3} more meals!"
                
                suggestions = [
                    "Generate grocery list",
                    "Schedule cooking times",
                    "View full meal plan",
                    "Modify meal plan"
                ]
                
                return {
                    "message": message,
                    "actions": ["meal_plan_created"],
                    "suggestions": suggestions,
                    "data": {
                        "week_id": week_id,
                        "meal_plan_summary": summary,
                        "meal_plan": [asdict(entry) for entry in meal_plan]
                    }
                }
                
            except Exception as e:
                return {
                    "message": f"I encountered an issue creating your meal plan: {str(e)}. Let me help you set up your preferences first.",
                    "actions": [],
                    "suggestions": [
                        "Set dietary restrictions",
                        "Update cooking preferences", 
                        "View available recipes"
                    ],
                    "data": {}
                }
        
        # Show current meal plan
        current_plan = meal_planner.get_current_week_plan()
        
        if current_plan:
            message = f"📅 Your current meal plan has {len(current_plan)} meals.\n\n"
            
            # Group by day
            by_day = {}
            for entry in current_plan:
                day = entry.date.strftime("%A")
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(entry)
            
            for day, meals in list(by_day.items())[:3]:  # Show first 3 days
                message += f"**{day}:**\n"
                for meal in meals:
                    status = "✅" if meal.prepared else "⏳"
                    message += f"  {status} {meal.meal_type.value.title()}: {meal.recipe.name}\n"
                message += "\n"
            
            suggestions = [
                "Create new meal plan",
                "Generate grocery list",
                "Mark meal as prepared"
            ]
        else:
            message = "You don't have a meal plan yet. Would you like me to create one for you?"
            suggestions = [
                "Create meal plan",
                "Browse recipes",
                "Set preferences"
            ]
        
        return {
            "message": message,
            "actions": ["meal_plan_viewed"],
            "suggestions": suggestions,
            "data": {
                "current_plan": [asdict(entry) for entry in current_plan] if current_plan else []
            }
        }
    
    def _handle_inventory_management(self, message: str, inventory_manager: InventoryManager) -> Dict[str, Any]:
        """Handle inventory management requests"""
        
        message_lower = message.lower()
        
        # Check what type of inventory request
        if "expiring" in message_lower or "expire" in message_lower:
            expiring_items = inventory_manager.get_expiring_items(3)
            
            if expiring_items:
                message = f"⚠️ You have {len(expiring_items)} items expiring soon:\n\n"
                for item in expiring_items[:5]:  # Show first 5
                    days_left = item.days_until_expiration()
                    message += f"• {item.name}: {days_left} days left\n"
                
                if len(expiring_items) > 5:
                    message += f"... and {len(expiring_items) - 5} more items"
                
                suggestions = [
                    "Plan meals with expiring items",
                    "Add to grocery list",
                    "Remove expired items"
                ]
            else:
                message = "✅ Great news! No items are expiring in the next 3 days."
                suggestions = [
                    "Check full inventory",
                    "Add new items",
                    "View low stock items"
                ]
        
        elif "low" in message_lower or "running out" in message_lower:
            low_stock = inventory_manager.get_low_stock_items()
            
            if low_stock:
                message = f"📦 You're running low on {len(low_stock)} items:\n\n"
                for item in low_stock[:5]:
                    message += f"• {item.name}: {item.quantity} {item.unit} left\n"
                
                suggestions = [
                    "Add to grocery list",
                    "Update quantities",
                    "Set stock alerts"
                ]
            else:
                message = "✅ All your items are well stocked!"
                suggestions = [
                    "Check expiring items",
                    "View full inventory",
                    "Add new items"
                ]
        
        else:
            # Show general inventory summary
            summary = inventory_manager.get_inventory_summary()
            
            message = f"📋 Inventory Summary:\n\n"
            message += f"📦 Total items: {summary['total_items']}\n"
            message += f"⚠️ Expiring soon: {summary['expiring_soon']}\n"
            message += f"❌ Expired: {summary['expired']}\n"
            message += f"📉 Low stock: {summary['low_stock']}\n\n"
            
            if summary['categories']:
                message += "Categories:\n"
                for category, data in list(summary['categories'].items())[:3]:
                    message += f"• {category.title()}: {data['count']} items\n"
            
            suggestions = [
                "Check expiring items",
                "View low stock",
                "Add new food",
                "Generate grocery list"
            ]
        
        return {
            "message": message,
            "actions": ["inventory_checked"],
            "suggestions": suggestions,
            "data": {
                "inventory_summary": inventory_manager.get_inventory_summary()
            }
        }
    
    def _handle_grocery_shopping(self, message: str, inventory_manager: InventoryManager, meal_planner: MealPlanManager) -> Dict[str, Any]:
        """Handle grocery shopping requests"""
        
        message_lower = message.lower()
        
        # Check if user wants to generate grocery list from meal plan
        if "generate" in message_lower or "create" in message_lower:
            current_plan = meal_planner.get_current_week_plan()
            
            if current_plan:
                # Convert meal plan to grocery items
                needed_items = inventory_manager.generate_grocery_list_from_meal_plan(
                    [asdict(entry) for entry in current_plan]
                )
                
                if needed_items:
                    message = f"🛒 Generated grocery list from your meal plan!\n\n"
                    message += f"📝 {len(needed_items)} items needed:\n\n"
                    
                    # Group by category
                    by_category = {}
                    for item in needed_items:
                        category = item.category.value
                        if category not in by_category:
                            by_category[category] = []
                        by_category[category].append(item)
                    
                    for category, items in list(by_category.items())[:3]:
                        message += f"**{category.title()}:**\n"
                        for item in items[:3]:
                            message += f"  • {item.quantity} {item.unit} {item.name}\n"
                        message += "\n"
                    
                    estimated_cost = inventory_manager.estimate_grocery_cost()
                    if estimated_cost:
                        message += f"💰 Estimated cost: ${estimated_cost}"
                    
                    suggestions = [
                        "Schedule shopping trip",
                        "Organize by store",
                        "Add more items",
                        "View full list"
                    ]
                else:
                    message = "✅ Looks like you have everything you need for your meal plan!"
                    suggestions = [
                        "Check inventory",
                        "Add manual items",
                        "View meal plan"
                    ]
            else:
                message = "You don't have a meal plan yet. Create one first, then I can generate a grocery list!"
                suggestions = [
                    "Create meal plan",
                    "Add items manually",
                    "Check inventory"
                ]
        
        else:
            # Show current grocery list
            grocery_list = inventory_manager.grocery_list
            
            if grocery_list:
                unpurchased = [item for item in grocery_list if not item.purchased]
                
                if unpurchased:
                    message = f"🛒 Your grocery list has {len(unpurchased)} items:\n\n"
                    
                    for item in unpurchased[:8]:  # Show first 8 items
                        priority_emoji = {"high": "🔥", "medium": "📝", "low": "💡"}.get(item.priority, "📝")
                        message += f"{priority_emoji} {item.quantity} {item.unit} {item.name}\n"
                    
                    if len(unpurchased) > 8:
                        message += f"... and {len(unpurchased) - 8} more items"
                    
                    estimated_cost = inventory_manager.estimate_grocery_cost()
                    if estimated_cost:
                        message += f"\n\n💰 Estimated total: ${estimated_cost}"
                else:
                    message = "✅ All items on your grocery list are marked as purchased!"
                
                suggestions = [
                    "Add more items",
                    "Schedule shopping",
                    "Mark items purchased",
                    "Organize by store"
                ]
            else:
                message = "Your grocery list is empty. Would you like me to generate one from your meal plan or add items manually?"
                suggestions = [
                    "Generate from meal plan",
                    "Add items manually",
                    "Check what's needed"
                ]
        
        return {
            "message": message,
            "actions": ["grocery_list_processed"],
            "suggestions": suggestions,
            "data": {
                "grocery_list": [asdict(item) for item in inventory_manager.grocery_list]
            }
        }
    
    def _handle_health_tracking(self, message: str, health_tracker: HealthTracker, user_profile: UserProfile) -> Dict[str, Any]:
        """Handle health tracking requests"""
        
        # Get today's summary
        today_summary = health_tracker.get_daily_nutrition_summary(date.today())
        
        message_response = f"📊 Today's Nutrition Summary:\n\n"
        
        if today_summary["progress"]:
            for nutrient, data in today_summary["progress"].items():
                percentage = data["percentage"]
                emoji = "✅" if 80 <= percentage <= 120 else "⚠️" if percentage < 80 else "❌"
                message_response += f"{emoji} {nutrient.title()}: {percentage:.0f}% of goal\n"
        else:
            message_response += "No nutrition goals set yet. Let me help you set them up!"
        
        # Add recent insights
        insights = health_tracker.generate_health_insights()
        if insights:
            latest_insight = insights[-1]
            message_response += f"\n💡 Latest insight: {latest_insight.title}\n{latest_insight.description}"
        
        suggestions = [
            "Set nutrition goals",
            "Log more food",
            "Track weight",
            "View weekly progress"
        ]
        
        return {
            "message": message_response,
            "actions": ["health_summary_provided"],
            "suggestions": suggestions,
            "data": {
                "nutrition_summary": today_summary,
                "insights": [asdict(insight) for insight in insights]
            }
        }
    
    def _handle_recipe_request(self, message: str, meal_planner: MealPlanManager, user_profile: UserProfile) -> Dict[str, Any]:
        """Handle recipe requests"""
        
        # Extract what they're looking for
        search_query = self._extract_recipe_search(message)
        
        # Search recipes
        recipes = meal_planner.search_recipes(
            query=search_query.get("query"),
            meal_type=search_query.get("meal_type"),
            max_time=search_query.get("max_time"),
            dietary_restrictions=user_profile.dietary_info.get("dietary_restrictions", [])
        )
        
        if recipes:
            message_response = f"🍳 Found {len(recipes)} recipes"
            if search_query.get("query"):
                message_response += f" for '{search_query['query']}'"
            message_response += ":\n\n"
            
            for recipe in recipes[:3]:  # Show top 3
                message_response += f"⭐ **{recipe.name}**\n"
                message_response += f"   ⏱️ {recipe.total_time_minutes} min | "
                message_response += f"👥 {recipe.servings} servings\n"
                if recipe.rating:
                    message_response += f"   ⭐ {recipe.rating:.1f}/5.0\n"
                message_response += "\n"
            
            suggestions = [
                f"Get recipe for {recipes[0].name}",
                "See more recipes",
                "Add to meal plan",
                "Search different recipe"
            ]
            
            return {
                "message": message_response,
                "actions": ["recipes_found"],
                "suggestions": suggestions,
                "data": {
                    "recipes": [asdict(recipe) for recipe in recipes[:5]]
                }
            }
        else:
            message_response = "I couldn't find any recipes matching your criteria. "
            if user_profile.dietary_info.get("dietary_restrictions"):
                message_response += "This might be due to your dietary restrictions. "
            message_response += "Try a different search or let me suggest some popular recipes!"
            
            suggestions = [
                "Show popular recipes",
                "Try different search",
                "Browse by category",
                "Add custom recipe"
            ]
            
            return {
                "message": message_response,
                "actions": [],
                "suggestions": suggestions,
                "data": {}
            }
    
    def _handle_nutrition_advice(self, message: str, user_profile: UserProfile, health_tracker: HealthTracker) -> Dict[str, Any]:
        """Handle nutrition advice requests"""
        
        # This would integrate with the AI service for personalized advice
        # For now, provide general guidance based on user data
        
        advice = "🥗 Here's some personalized nutrition advice:\n\n"
        
        # Get recent nutrition data
        adherence = health_tracker.get_nutrition_adherence(7)
        
        if "error" not in adherence:
            overall_score = adherence["average_adherence"]["overall"]
            
            if overall_score >= 85:
                advice += "✅ You're doing great with your nutrition! Keep up the excellent work.\n\n"
            elif overall_score >= 70:
                advice += "👍 Good job on your nutrition. A few small improvements could make a big difference.\n\n"
            else:
                advice += "💪 There's room for improvement in your nutrition. Let's work on some strategies.\n\n"
            
            # Specific recommendations
            if adherence["average_adherence"]["protein"] < 80:
                advice += "🥩 Focus on increasing protein intake - try adding protein to each meal.\n"
            
            if adherence["average_adherence"]["calories"] > 120:
                advice += "🍽️ Consider smaller portions or more nutrient-dense foods.\n"
        
        # Add goals-based advice
        health_goals = [goal.value for goal in user_profile.health_goals]
        if "weight_loss" in health_goals:
            advice += "🎯 For weight loss: Focus on a caloric deficit while maintaining protein.\n"
        elif "muscle_gain" in health_goals:
            advice += "💪 For muscle gain: Ensure adequate protein (1.6-2.2g per kg body weight).\n"
        
        suggestions = [
            "Set nutrition goals",
            "Get meal recommendations",
            "Track more food",
            "View progress report"
        ]
        
        return {
            "message": advice,
            "actions": ["nutrition_advice_provided"],
            "suggestions": suggestions,
            "data": {
                "adherence_data": adherence if "error" not in adherence else None
            }
        }
    
    def _handle_calendar_scheduling(self, message: str, calendar_manager: CalendarManager, meal_planner: MealPlanManager) -> Dict[str, Any]:
        """Handle calendar scheduling requests"""
        
        # Get today's schedule
        today_schedule = calendar_manager.get_today_schedule()
        upcoming = calendar_manager.get_upcoming_events(7)
        
        message_response = f"📅 Your nutrition schedule:\n\n"
        
        if today_schedule["cooking"]:
            message_response += "🍳 **Today's Cooking:**\n"
            for event in today_schedule["cooking"]:
                time_str = event.start_time.strftime("%I:%M %p")
                message_response += f"  • {time_str}: {event.title}\n"
            message_response += "\n"
        
        if today_schedule["meals"]:
            message_response += "🍽️ **Today's Meals:**\n"
            for event in today_schedule["meals"]:
                time_str = event.start_time.strftime("%I:%M %p")
                message_response += f"  • {time_str}: {event.title}\n"
            message_response += "\n"
        
        if upcoming:
            message_response += f"📋 **Upcoming this week:** {len(upcoming)} events\n"
            for event in upcoming[:3]:
                day = event.start_time.strftime("%A")
                time_str = event.start_time.strftime("%I:%M %p")
                message_response += f"  • {day} {time_str}: {event.title}\n"
        
        if not today_schedule["cooking"] and not today_schedule["meals"] and not upcoming:
            message_response += "No nutrition events scheduled. Would you like me to schedule some based on your meal plan?"
        
        suggestions = [
            "Schedule cooking times",
            "Plan grocery shopping",
            "Set meal reminders",
            "View full calendar"
        ]
        
        return {
            "message": message_response,
            "actions": ["calendar_viewed"],
            "suggestions": suggestions,
            "data": {
                "today_schedule": today_schedule,
                "upcoming_events": [asdict(event) for event in upcoming]
            }
        }
    
    def _handle_progress_tracking(self, health_tracker: HealthTracker, user_profile: UserProfile) -> Dict[str, Any]:
        """Handle progress tracking requests"""
        
        # Get various progress metrics
        weight_trend = health_tracker.get_weight_trend(30)
        adherence = health_tracker.get_nutrition_adherence(7)
        
        message = "📈 Your Progress Report:\n\n"
        
        # Weight progress
        if "error" not in weight_trend:
            trend_emoji = {"gaining": "📈", "losing": "📉", "stable": "➡️"}.get(weight_trend["trend"], "➡️")
            message += f"⚖️ **Weight Trend (30 days):**\n"
            message += f"   {trend_emoji} {weight_trend['trend'].title()}: {weight_trend['total_change']:+.1f} lbs\n"
            message += f"   📊 Weekly rate: {weight_trend['weekly_change']:+.1f} lbs/week\n\n"
        
        # Nutrition adherence
        if "error" not in adherence:
            grade = adherence["adherence_grade"]
            grade_emoji = {"A": "🌟", "B": "✅", "C": "👍", "D": "⚠️", "F": "❌"}.get(grade, "📊")
            message += f"🥗 **Nutrition Adherence (7 days):**\n"
            message += f"   {grade_emoji} Overall Grade: {grade} ({adherence['average_adherence']['overall']:.0f}%)\n"
            message += f"   🔥 Calories: {adherence['average_adherence']['calories']:.0f}%\n"
            message += f"   💪 Protein: {adherence['average_adherence']['protein']:.0f}%\n\n"
        
        # Recent achievements/insights
        insights = health_tracker.generate_health_insights()
        achievements = [i for i in insights if i.insight_type == "achievement"]
        
        if achievements:
            message += "🏆 **Recent Achievements:**\n"
            for achievement in achievements[-2:]:  # Last 2 achievements
                message += f"   ✨ {achievement.title}\n"
        
        suggestions = [
            "Set new goals",
            "View detailed charts",
            "Get recommendations",
            "Update targets"
        ]
        
        return {
            "message": message,
            "actions": ["progress_report_generated"],
            "suggestions": suggestions,
            "data": {
                "weight_trend": weight_trend if "error" not in weight_trend else None,
                "adherence": adherence if "error" not in adherence else None,
                "insights": [asdict(insight) for insight in insights]
            }
        }
    
    def _handle_goal_setting(self, message: str, user_profile: UserProfile, health_tracker: HealthTracker) -> Dict[str, Any]:
        """Handle goal setting requests"""
        
        # Extract goal information from message
        goal_info = self._extract_goal_info(message)
        
        if goal_info:
            # Set nutrition goals based on the information
            if all(key in goal_info for key in ["weight", "height", "age", "sex"]):
                
                activity_level = ActivityLevel(goal_info.get("activity_level", "moderately_active"))
                health_goal = HealthGoal(goal_info.get("health_goal", "maintenance"))
                
                nutrition_goals = health_tracker.set_nutrition_goals(
                    weight_lbs=goal_info["weight"],
                    height_inches=goal_info["height"],
                    age=goal_info["age"],
                    sex=goal_info["sex"],
                    activity_level=activity_level,
                    health_goal=health_goal
                )
                
                message = f"🎯 Your nutrition goals have been set!\n\n"
                message += f"🔥 Daily Calories: {nutrition_goals.calories:,}\n"
                message += f"💪 Protein: {nutrition_goals.protein_g}g\n"
                message += f"🍞 Carbs: {nutrition_goals.carbs_g}g\n"
                message += f"🥑 Fat: {nutrition_goals.fat_g}g\n"
                message += f"💧 Water: {nutrition_goals.water_oz}oz\n\n"
                message += f"These goals are personalized for your {health_goal.value.replace('_', ' ')} objective!"
                
                suggestions = [
                    "Start tracking food",
                    "Create meal plan",
                    "View progress",
                    "Adjust goals"
                ]
                
                return {
                    "message": message,
                    "actions": ["goals_set"],
                    "suggestions": suggestions,
                    "data": {
                        "nutrition_goals": asdict(nutrition_goals)
                    }
                }
        
        # If we don't have enough info, ask for it
        current_goals = health_tracker.nutrition_goals
        
        if current_goals:
            message = f"📋 Your current nutrition goals:\n\n"
            message += f"🔥 Calories: {current_goals.calories:,} daily\n"
            message += f"💪 Protein: {current_goals.protein_g}g\n"
            message += f"🍞 Carbs: {current_goals.carbs_g}g\n"
            message += f"🥑 Fat: {current_goals.fat_g}g\n\n"
            message += "Would you like to update any of these goals?"
        else:
            message = "Let's set up your nutrition goals! I'll need some basic information:\n\n"
            message += "• Your current weight and height\n"
            message += "• Age and sex\n"
            message += "• Activity level\n"
            message += "• Primary health goal\n\n"
            message += "You can say something like: 'I'm 30 years old, 5'8\", 180 lbs, male, moderately active, want to lose weight'"
        
        suggestions = [
            "Update my goals",
            "I want to lose weight",
            "I want to gain muscle",
            "Maintain current weight"
        ]
        
        return {
            "message": message,
            "actions": [],
            "suggestions": suggestions,
            "data": {
                "current_goals": asdict(current_goals) if current_goals else None
            }
        }
    
    def _handle_goodbye(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Handle goodbye messages"""
        name = user_profile.name or ""
        
        goodbyes = [
            f"Goodbye{' ' + name if name else ''}! Keep up the great work with your nutrition! 🌟",
            f"See you later{' ' + name if name else ''}! Don't forget to stay hydrated! 💧",
            f"Take care{' ' + name if name else ''}! Remember, small consistent steps lead to big results! 💪",
            f"Bye{' ' + name if name else ''}! I'm here whenever you need nutrition support! 🥗"
        ]
        
        import random
        message = random.choice(goodbyes)
        
        return {
            "message": message,
            "actions": ["conversation_ended"],
            "suggestions": [],
            "data": {}
        }
    
    def _handle_general_question(self, message: str, user_profile: UserProfile, context: ConversationContext) -> Dict[str, Any]:
        """Handle general questions or unclear intents"""
        
        # Provide helpful response based on context
        message_response = "I'm here to help with your nutrition! I can assist you with:\n\n"
        message_response += "🍽️ Meal planning and recipes\n"
        message_response += "📊 Food and nutrition tracking\n"
        message_response += "🛒 Grocery list management\n"
        message_response += "📋 Inventory tracking\n"
        message_response += "📅 Meal scheduling\n"
        message_response += "📈 Health progress monitoring\n"
        message_response += "🥗 Personalized nutrition advice\n\n"
        message_response += "What would you like to work on?"
        
        suggestions = [
            "Plan this week's meals",
            "Log what I ate",
            "Check my progress",
            "Create grocery list",
            "Track my weight",
            "Get nutrition advice"
        ]
        
        return {
            "message": message_response,
            "actions": [],
            "suggestions": suggestions,
            "data": {}
        }
    
    def _extract_food_info(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract food information from natural language"""
        # This would use NLP/ML in production
        # Simple pattern matching for demo
        
        # Common patterns for food logging
        patterns = [
            r"(ate|had|consumed)\s+(\d+\.?\d*)\s+(\w+)\s+(.*)",
            r"(\d+\.?\d*)\s+(\w+)\s+of\s+(.*)",
            r"(\d+\.?\d*)\s+(.*)",
        ]
        
        message_lower = message.lower()
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                groups = match.groups()
                
                if len(groups) >= 3:
                    return {
                        "name": groups[-1].strip(),
                        "quantity": float(groups[-3]) if groups[-3].replace('.', '').isdigit() else 1,
                        "unit": groups[-2] if len(groups) > 2 else "serving",
                        "meal_category": self._guess_meal_category(),
                        "calories": None,  # Would lookup in nutrition database
                        "protein": None,
                        "carbs": None,
                        "fat": None
                    }
        
        return None
    
    def _guess_meal_category(self) -> MealCategory:
        """Guess meal category based on time of day"""
        hour = datetime.now().hour
        
        if 5 <= hour < 11:
            return MealCategory.BREAKFAST
        elif 11 <= hour < 16:
            return MealCategory.LUNCH
        elif 16 <= hour < 22:
            return MealCategory.DINNER
        else:
            return MealCategory.SNACK
    
    def _extract_recipe_search(self, message: str) -> Dict[str, Any]:
        """Extract recipe search criteria from message"""
        
        result = {"query": None, "meal_type": None, "max_time": None}
        
        # Extract meal type
        meal_types = {
            "breakfast": MealType.BREAKFAST,
            "lunch": MealType.LUNCH,
            "dinner": MealType.DINNER,
            "snack": MealType.SNACK
        }
        
        for meal_name, meal_type in meal_types.items():
            if meal_name in message.lower():
                result["meal_type"] = meal_type
                break
        
        # Extract time constraints
        time_patterns = [
            r"(\d+)\s*min",
            r"quick",
            r"fast",
            r"under\s*(\d+)"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message.lower())
            if match:
                if pattern == r"quick" or pattern == r"fast":
                    result["max_time"] = 30
                elif match.groups():
                    result["max_time"] = int(match.groups()[0])
        
        # Extract general query (food name, cuisine, etc.)
        # Remove common words and extract meaningful terms
        stop_words = {"recipe", "for", "how", "to", "make", "cook", "a", "an", "the", "i", "want", "need"}
        words = message.lower().split()
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        if meaningful_words:
            result["query"] = " ".join(meaningful_words[:3])  # Take first 3 meaningful words
        
        return result
    
    def _extract_goal_info(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract goal information from natural language"""
        
        result = {}
        
        # Extract weight
        weight_match = re.search(r"(\d+\.?\d*)\s*(lbs?|pounds?)", message.lower())
        if weight_match:
            result["weight"] = float(weight_match.groups()[0])
        
        # Extract height
        height_match = re.search(r"(\d+)'(\d+)\"?|(\d+)\s*feet?\s*(\d+)\s*inch", message.lower())
        if height_match:
            groups = height_match.groups()
            if groups[0] and groups[1]:  # 5'8" format
                result["height"] = int(groups[0]) * 12 + int(groups[1])
            elif groups[2] and groups[3]:  # 5 feet 8 inches format
                result["height"] = int(groups[2]) * 12 + int(groups[3])
        
        # Extract age
        age_match = re.search(r"(\d+)\s*(years?\s*old|yo)", message.lower())
        if age_match:
            result["age"] = int(age_match.groups()[0])
        
        # Extract sex
        if any(word in message.lower() for word in ["male", "man", "guy"]):
            result["sex"] = "male"
        elif any(word in message.lower() for word in ["female", "woman", "girl"]):
            result["sex"] = "female"
        
        # Extract activity level
        if "sedentary" in message.lower() or "no exercise" in message.lower():
            result["activity_level"] = "sedentary"
        elif "lightly active" in message.lower() or "light exercise" in message.lower():
            result["activity_level"] = "lightly_active"
        elif "very active" in message.lower() or "very hard exercise" in message.lower():
            result["activity_level"] = "very_active"
        elif "moderately active" in message.lower() or "moderate exercise" in message.lower():
            result["activity_level"] = "moderately_active"
        
        # Extract health goal
        if any(phrase in message.lower() for phrase in ["lose weight", "weight loss", "losing weight"]):
            result["health_goal"] = "weight_loss"
        elif any(phrase in message.lower() for phrase in ["gain weight", "weight gain", "gaining weight"]):
            result["health_goal"] = "weight_gain"
        elif any(phrase in message.lower() for phrase in ["gain muscle", "muscle gain", "build muscle"]):
            result["health_goal"] = "muscle_gain"
        elif "maintain" in message.lower():
            result["health_goal"] = "maintenance"
        
        return result if result else None
