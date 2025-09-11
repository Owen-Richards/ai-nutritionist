"""
AI Nutritionist - Message Formatters
Utilities for formatting messages for different platforms and contexts
"""

import json
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal

from ..config.constants import MessagePlatform, MealType, GROCERY_CATEGORIES
from ..models import MealPlan, GroceryList, Recipe, NutritionInfo

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Base message formatting utilities"""
    
    @staticmethod
    def truncate_message(message: str, max_length: int = 1600) -> str:
        """Truncate message to platform limits"""
        if len(message) <= max_length:
            return message
        
        # Try to truncate at sentence boundary
        truncated = message[:max_length - 3]
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        last_sentence = max(last_period, last_exclamation, last_question)
        
        if last_sentence > max_length * 0.7:  # If we can keep 70% while ending at sentence
            return truncated[:last_sentence + 1]
        else:
            return truncated + "..."
    
    @staticmethod
    def add_platform_formatting(message: str, platform: MessagePlatform) -> str:
        """Add platform-specific formatting"""
        if platform == MessagePlatform.WHATSAPP:
            # WhatsApp supports basic markdown
            return message
        elif platform == MessagePlatform.SMS:
            # SMS has no formatting, remove special characters
            return message.replace('*', '').replace('_', '').replace('`', '')
        else:
            return message
    
    @staticmethod
    def format_list(items: List[str], numbered: bool = True) -> str:
        """Format a list of items"""
        if not items:
            return ""
        
        formatted_items = []
        for i, item in enumerate(items, 1):
            if numbered:
                formatted_items.append(f"{i}. {item}")
            else:
                formatted_items.append(f"• {item}")
        
        return "\n".join(formatted_items)
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD") -> str:
        """Format currency amounts"""
        if currency == "USD":
            return f"${amount:.2f}"
        else:
            return f"{amount:.2f} {currency}"
    
    @staticmethod
    def format_percentage(value: float, decimal_places: int = 1) -> str:
        """Format percentage values"""
        return f"{value:.{decimal_places}f}%"


class MealPlanFormatter:
    """Format meal plans for messaging"""
    
    @staticmethod
    def format_meal_plan_summary(meal_plan: MealPlan, platform: MessagePlatform = MessagePlatform.WHATSAPP) -> str:
        """Format meal plan summary"""
        header = f"🍽️ *{meal_plan.name}*\n"
        header += f"📅 {meal_plan.start_date.strftime('%B %d')} - {meal_plan.end_date.strftime('%B %d')}\n"
        header += f"👨‍👩‍👧‍👦 For {meal_plan.household_size} people\n"
        
        if meal_plan.total_budget > 0:
            header += f"💰 Budget: {MessageFormatter.format_currency(meal_plan.total_budget)}\n"
        
        header += "\n"
        
        # Format each day
        days_text = []
        for day_plan in meal_plan.days:
            day_text = f"*{day_plan.date.strftime('%A, %B %d')}*\n"
            
            for meal in day_plan.meals:
                emoji = MealPlanFormatter._get_meal_emoji(meal.meal_type)
                day_text += f"{emoji} {meal.meal_type.value.title()}: {meal.recipe.name}\n"
            
            # Add nutrition summary
            daily_nutrition = day_plan.calculate_daily_nutrition()
            day_text += f"📊 {daily_nutrition.calories:.0f} cal, {daily_nutrition.protein_grams:.0f}g protein\n"
            
            days_text.append(day_text)
        
        full_message = header + "\n\n".join(days_text)
        
        # Add footer
        footer = f"\n\n💡 Reply 'grocery list' for shopping list"
        footer += f"\n📱 Reply 'modify' to make changes"
        
        full_message += footer
        
        return MessageFormatter.add_platform_formatting(
            MessageFormatter.truncate_message(full_message), 
            platform
        )
    
    @staticmethod
    def format_daily_meal_plan(day_plan, platform: MessagePlatform = MessagePlatform.WHATSAPP) -> str:
        """Format single day meal plan"""
        header = f"🗓️ *{day_plan.date.strftime('%A, %B %d')}*\n\n"
        
        meal_texts = []
        for meal in day_plan.meals:
            emoji = MealPlanFormatter._get_meal_emoji(meal.meal_type)
            meal_text = f"{emoji} *{meal.meal_type.value.title()}*\n"
            meal_text += f"🍳 {meal.recipe.name}\n"
            meal_text += f"⏱️ {meal.recipe.prep_time_minutes + meal.recipe.cook_time_minutes} min"
            
            if meal.recipe.estimated_cost > 0:
                meal_text += f" • {MessageFormatter.format_currency(meal.recipe.estimated_cost)}"
            
            meal_text += f"\n📊 {meal.recipe.nutrition.calories:.0f} cal"
            
            meal_texts.append(meal_text)
        
        # Daily totals
        daily_nutrition = day_plan.calculate_daily_nutrition()
        footer = f"\n*Daily Total:*\n"
        footer += f"📊 {daily_nutrition.calories:.0f} calories\n"
        footer += f"🥩 {daily_nutrition.protein_grams:.0f}g protein\n"
        footer += f"🍞 {daily_nutrition.carbs_grams:.0f}g carbs\n"
        footer += f"🥑 {daily_nutrition.fat_grams:.0f}g fat"
        
        full_message = header + "\n\n".join(meal_texts) + footer
        
        return MessageFormatter.add_platform_formatting(
            MessageFormatter.truncate_message(full_message), 
            platform
        )
    
    @staticmethod
    def format_recipe_details(recipe: Recipe, platform: MessagePlatform = MessagePlatform.WHATSAPP) -> str:
        """Format detailed recipe information"""
        header = f"👨‍🍳 *{recipe.name}*\n\n"
        
        # Basic info
        info = f"🍽️ Serves: {recipe.servings}\n"
        info += f"⏰ Prep: {recipe.prep_time_minutes} min • Cook: {recipe.cook_time_minutes} min\n"
        info += f"📊 {recipe.nutrition.calories:.0f} cal per serving\n"
        
        if recipe.difficulty:
            info += f"⭐ Difficulty: {recipe.difficulty.title()}\n"
        
        info += "\n"
        
        # Ingredients
        ingredients_text = "*Ingredients:*\n"
        ingredient_lines = []
        for ingredient in recipe.ingredients:
            line = f"• {ingredient.quantity} {ingredient.unit} {ingredient.name}"
            ingredient_lines.append(line)
        
        ingredients_text += "\n".join(ingredient_lines) + "\n\n"
        
        # Instructions
        instructions_text = "*Instructions:*\n"
        instruction_lines = []
        for i, instruction in enumerate(recipe.instructions, 1):
            instruction_lines.append(f"{i}. {instruction}")
        
        instructions_text += "\n".join(instruction_lines)
        
        # Nutrition details
        nutrition_text = f"\n\n*Nutrition per serving:*\n"
        nutrition_text += f"📊 {recipe.nutrition.calories:.0f} calories\n"
        nutrition_text += f"🥩 {recipe.nutrition.protein_grams:.1f}g protein\n"
        nutrition_text += f"🍞 {recipe.nutrition.carbs_grams:.1f}g carbs\n"
        nutrition_text += f"🥑 {recipe.nutrition.fat_grams:.1f}g fat"
        
        if recipe.nutrition.fiber_grams > 0:
            nutrition_text += f"\n🌾 {recipe.nutrition.fiber_grams:.1f}g fiber"
        
        full_message = header + info + ingredients_text + instructions_text + nutrition_text
        
        return MessageFormatter.add_platform_formatting(
            MessageFormatter.truncate_message(full_message, 3000), 
            platform
        )
    
    @staticmethod
    def _get_meal_emoji(meal_type: MealType) -> str:
        """Get emoji for meal type"""
        emoji_map = {
            MealType.BREAKFAST: "🌅",
            MealType.LUNCH: "🌞", 
            MealType.DINNER: "🌙",
            MealType.SNACK: "🍎"
        }
        return emoji_map.get(meal_type, "🍽️")


class GroceryListFormatter:
    """Format grocery lists for messaging"""
    
    @staticmethod
    def format_grocery_list(grocery_list: GroceryList, platform: MessagePlatform = MessagePlatform.WHATSAPP) -> str:
        """Format complete grocery list"""
        header = f"🛒 *{grocery_list.name}*\n"
        
        if grocery_list.estimated_total_cost > 0:
            header += f"💰 Est. Total: {MessageFormatter.format_currency(grocery_list.estimated_total_cost)}\n"
        
        header += f"📦 {len(grocery_list.items)} items\n\n"
        
        # Group by category/store section
        sections = grocery_list.organize_by_store_section()
        
        section_texts = []
        for section_name, items in sections.items():
            section_text = f"*{section_name}:*\n"
            
            item_lines = []
            for item in items:
                line = f"• {item.ingredient.quantity} {item.ingredient.unit} {item.ingredient.name}"
                
                if item.ingredient.estimated_cost:
                    cost = item.ingredient.estimated_cost * item.ingredient.quantity
                    line += f" ({MessageFormatter.format_currency(cost)})"
                
                item_lines.append(line)
            
            section_text += "\n".join(item_lines)
            section_texts.append(section_text)
        
        # Add tips
        footer = "\n\n💡 *Shopping Tips:*\n"
        footer += "• Check store sales and coupons\n"
        footer += "• Buy generic brands to save money\n"
        footer += "• Shop the perimeter first (fresh foods)\n"
        footer += "\n✅ Reply 'done shopping' when complete!"
        
        full_message = header + "\n\n".join(section_texts) + footer
        
        return MessageFormatter.add_platform_formatting(
            MessageFormatter.truncate_message(full_message, 3000), 
            platform
        )
    
    @staticmethod
    def format_grocery_list_summary(grocery_list: GroceryList, platform: MessagePlatform = MessagePlatform.WHATSAPP) -> str:
        """Format short grocery list summary"""
        header = f"🛒 *{grocery_list.name}*\n"
        header += f"📦 {len(grocery_list.items)} items"
        
        if grocery_list.estimated_total_cost > 0:
            header += f" • {MessageFormatter.format_currency(grocery_list.estimated_total_cost)}"
        
        header += "\n\n"
        
        # Show first few items as preview
        preview_items = grocery_list.items[:8]
        preview_lines = []
        
        for item in preview_items:
            line = f"• {item.ingredient.quantity} {item.ingredient.unit} {item.ingredient.name}"
            preview_lines.append(line)
        
        preview_text = "\n".join(preview_lines)
        
        if len(grocery_list.items) > 8:
            preview_text += f"\n... and {len(grocery_list.items) - 8} more items"
        
        footer = "\n\n💡 Reply 'full list' for complete details"
        
        full_message = header + preview_text + footer
        
        return MessageFormatter.add_platform_formatting(
            MessageFormatter.truncate_message(full_message), 
            platform
        )


class NutritionFormatter:
    """Format nutrition data and insights"""
    
    @staticmethod
    def format_nutrition_summary(nutrition: NutritionInfo, targets: Optional[NutritionInfo] = None) -> str:
        """Format nutrition summary with targets"""
        summary = "📊 *Nutrition Summary*\n\n"
        
        # Calories
        calories_text = f"🔥 Calories: {nutrition.calories:.0f}"
        if targets:
            calories_text += f" / {targets.calories:.0f}"
            percentage = (nutrition.calories / targets.calories) * 100
            calories_text += f" ({percentage:.0f}%)"
        summary += calories_text + "\n"
        
        # Macros
        summary += f"🥩 Protein: {nutrition.protein_grams:.1f}g"
        if targets:
            summary += f" / {targets.protein_grams:.1f}g"
        summary += "\n"
        
        summary += f"🍞 Carbs: {nutrition.carbs_grams:.1f}g"
        if targets:
            summary += f" / {targets.carbs_grams:.1f}g"
        summary += "\n"
        
        summary += f"🥑 Fat: {nutrition.fat_grams:.1f}g"
        if targets:
            summary += f" / {targets.fat_grams:.1f}g"
        summary += "\n"
        
        # Optional nutrients
        if nutrition.fiber_grams > 0:
            summary += f"🌾 Fiber: {nutrition.fiber_grams:.1f}g\n"
        
        if nutrition.sodium_mg > 0:
            summary += f"🧂 Sodium: {nutrition.sodium_mg:.0f}mg\n"
        
        return summary
    
    @staticmethod
    def format_progress_insights(current_nutrition: NutritionInfo, target_nutrition: NutritionInfo, days_logged: int) -> str:
        """Format nutrition progress insights"""
        insights = "📈 *Nutrition Progress*\n\n"
        
        # Calculate percentages
        calorie_progress = (current_nutrition.calories / target_nutrition.calories) * 100
        protein_progress = (current_nutrition.protein_grams / target_nutrition.protein_grams) * 100
        
        insights += f"📅 Data from last {days_logged} days\n\n"
        
        # Calorie insights
        if calorie_progress < 80:
            insights += "🔴 Calories are low - consider adding healthy snacks\n"
        elif calorie_progress > 120:
            insights += "🟡 Calories are high - watch portion sizes\n"
        else:
            insights += "🟢 Calories look good - keep it up!\n"
        
        # Protein insights
        if protein_progress < 80:
            insights += "🔴 Protein is low - add lean meats, eggs, or beans\n"
        elif protein_progress > 150:
            insights += "🟡 Protein is high - balance with more carbs\n"
        else:
            insights += "🟢 Protein intake looks great!\n"
        
        # Suggestions
        insights += "\n💡 *Suggestions:*\n"
        
        if calorie_progress < 90:
            insights += "• Add a healthy snack like nuts or yogurt\n"
        
        if protein_progress < 90:
            insights += "• Include protein at every meal\n"
        
        insights += "• Track consistently for better insights\n"
        insights += "• Focus on whole, unprocessed foods\n"
        
        return insights


class NotificationFormatter:
    """Format system notifications and alerts"""
    
    @staticmethod
    def format_welcome_message(user_name: Optional[str] = None) -> str:
        """Format welcome message for new users"""
        greeting = f"Hey {user_name}! 👋" if user_name else "Hey there! 👋"
        
        message = f"""{greeting} Welcome to AI Nutritionist!

I'm your personal nutrition coach. I can help you:

🍽️ Create personalized meal plans
🛒 Generate grocery lists  
📊 Track your nutrition goals
💬 Answer food and nutrition questions
🎯 Set and achieve health goals

Let's start! What's your main nutrition goal?

Examples:
• "I want to lose 15 pounds"
• "Build muscle and eat healthy"
• "Feed my family on $80/week" 
• "Meal prep for busy weekdays"

Just tell me what you're looking for! 😊"""
        
        return message
    
    @staticmethod
    def format_subscription_reminder(days_left: int, tier: str) -> str:
        """Format subscription reminder"""
        if days_left <= 0:
            return f"""⏰ Your {tier} subscription has expired!

Upgrade now to continue enjoying:
• Unlimited meal plans
• Advanced nutrition tracking
• Priority support
• Family sharing

Reply 'upgrade' to renew! 💪"""
        
        return f"""⏰ Your {tier} subscription expires in {days_left} days.

Don't miss out on your nutrition goals! 

Reply 'renew' to continue your journey. 🎯"""
    
    @staticmethod
    def format_achievement_notification(achievement: str, description: str) -> str:
        """Format achievement unlock notification"""
        return f"""🎉 Achievement Unlocked!

*{achievement}*

{description}

Keep up the great work! You're crushing your nutrition goals! 💪✨"""
    
    @staticmethod
    def format_error_message(error_type: str = "general") -> str:
        """Format user-friendly error messages"""
        error_messages = {
            "general": "Oops! Something went wrong. Let me try that again! 😅",
            "api_limit": "I'm a bit overloaded right now. Can you try again in a minute? ⏳",
            "invalid_input": "I didn't quite understand that. Could you rephrase it? 🤔",
            "subscription_limit": "You've reached your monthly limit! Upgrade for unlimited access 🚀",
            "service_unavailable": "I'm having some technical difficulties. I'll be back shortly! 🔧"
        }
        
        return error_messages.get(error_type, error_messages["general"])


def format_message_for_platform(message: str, platform: MessagePlatform, max_length: Optional[int] = None) -> str:
    """
    Format message for specific platform with appropriate limits and formatting
    
    Args:
        message: Raw message content
        platform: Target messaging platform  
        max_length: Override default platform limits
        
    Returns:
        Formatted message suitable for the platform
    """
    # Platform-specific limits
    platform_limits = {
        MessagePlatform.WHATSAPP: 4096,
        MessagePlatform.SMS: 1600,
        MessagePlatform.TELEGRAM: 4096,
        MessagePlatform.EMAIL: 10000,
    }
    
    limit = max_length or platform_limits.get(platform, 1600)
    
    # Apply platform formatting
    formatted = MessageFormatter.add_platform_formatting(message, platform)
    
    # Truncate if needed
    if len(formatted) > limit:
        formatted = MessageFormatter.truncate_message(formatted, limit)
    
    return formatted
