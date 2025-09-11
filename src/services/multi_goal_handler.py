"""
Multi-Goal Nutrition Assistant Handler

Main handler that demonstrates the multi-goal and custom goal functionality
with example conversations and integration points.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from .multi_goal_service import MultiGoalService, GoalType
from .multi_goal_meal_planner import MultiGoalMealPlanGenerator
from .nutrition_messaging_service import NutritionMessagingService
from .user_service import UserService

logger = logging.getLogger(__name__)


class MultiGoalNutritionHandler:
    """Main handler for multi-goal nutrition conversations"""
    
    def __init__(self, dynamodb_resource, ai_service):
        # Initialize core services
        self.user_service = UserService(dynamodb_resource)
        self.multi_goal_service = MultiGoalService(self.user_service)
        
        # Initialize enhanced services with multi-goal support
        self.meal_planner = MultiGoalMealPlanGenerator(ai_service, self.multi_goal_service)
        
        # Assume nutrition_tracking_service exists
        from .nutrition_tracking_service import NutritionTrackingService
        self.nutrition_tracking = NutritionTrackingService(self.user_service, ai_service)
        
        self.messaging_service = NutritionMessagingService(
            self.nutrition_tracking, 
            self.multi_goal_service
        )
    
    def handle_user_message(self, user_id: str, message: str, platform: str = 'whatsapp') -> Dict[str, Any]:
        """
        Main entry point for handling user messages with multi-goal support
        
        Examples of supported conversations:
        - "I want to eat on a budget, build muscle, and improve gut health"
        - "skin health" (custom goal)
        - "budget is more important than muscle gain" (prioritization)
        """
        try:
            message_lower = message.lower().strip()
            
            # Detect conversation type
            conversation_type = self._detect_conversation_type(message_lower)
            
            if conversation_type == 'multi_goal_input':
                return self._handle_multi_goal_conversation(user_id, message)
            
            elif conversation_type == 'goal_prioritization':
                return self._handle_prioritization_conversation(user_id, message)
            
            elif conversation_type == 'custom_goal':
                return self._handle_custom_goal_conversation(user_id, message)
            
            elif conversation_type == 'meal_plan_request':
                return self._handle_meal_plan_generation(user_id, message)
            
            elif conversation_type == 'goal_status':
                return self._handle_goal_status_inquiry(user_id)
            
            else:
                # Fall back to existing nutrition tracking
                response = self.messaging_service.generate_contextual_response(message, user_id)
                if response:
                    return {"success": True, "message": response, "type": "nutrition_tracking"}
                else:
                    return {"success": False, "message": "I didn't understand that. Try asking about goals, meal plans, or nutrition tracking!"}
        
        except Exception as e:
            logger.error(f"Error handling user message: {str(e)}")
            return {
                "success": False, 
                "message": "Sorry, I encountered an error. Please try again!",
                "error": str(e)
            }
    
    def _detect_conversation_type(self, message: str) -> str:
        """Detect the type of conversation from user message"""
        
        # Multi-goal patterns
        multi_goal_keywords = [
            'want to', 'need to', 'goal', 'goals', 'and', '+', 'both', 'also'
        ]
        goal_indicators = [
            'budget', 'muscle', 'weight', 'energy', 'gut', 'health', 'quick', 'cheap', 'protein'
        ]
        
        # Check for multiple goal indicators
        goal_count = sum(1 for indicator in goal_indicators if indicator in message)
        has_multi_keywords = any(keyword in message for keyword in multi_goal_keywords)
        
        if goal_count >= 2 and has_multi_keywords:
            return 'multi_goal_input'
        
        # Priority patterns
        priority_keywords = [
            'more important', 'priority', 'prioritize', 'focus on', 'first', 'over'
        ]
        if any(keyword in message for keyword in priority_keywords):
            return 'goal_prioritization'
        
        # Custom goal patterns (single unusual goal)
        if goal_count == 1 and any(word in message for word in ['skin', 'sleep', 'brain', 'immune', 'bone']):
            return 'custom_goal'
        
        # Meal plan requests
        meal_plan_keywords = ['meal plan', 'plan', 'recipes', 'meals', 'what should i eat']
        if any(keyword in message for keyword in meal_plan_keywords):
            return 'meal_plan_request'
        
        # Goal status
        status_keywords = ['my goals', 'what are my', 'show goals', 'goal status']
        if any(keyword in message for keyword in status_keywords):
            return 'goal_status'
        
        return 'other'
    
    def _handle_multi_goal_conversation(self, user_id: str, message: str) -> Dict[str, Any]:
        """Handle multi-goal input conversation"""
        
        # Example: "I want to eat on a budget, build muscle, and improve gut health"
        result = self.messaging_service.handle_goal_input(user_id, message)
        
        if result.get('success') and result.get('goals_added', 0) > 1:
            # Suggest prioritization for multiple goals
            prioritization_suggestion = self.messaging_service.suggest_goal_prioritization(user_id)
            
            response_parts = [result['message']]
            if prioritization_suggestion:
                response_parts.append(prioritization_suggestion)
            
            # Offer to generate meal plan
            response_parts.append("\nReady for me to create your first multi-goal meal plan? 🍽️")
            
            return {
                "success": True,
                "message": "\n\n".join(response_parts),
                "type": "multi_goal_setup",
                "goals_added": result.get('goals_added', 0),
                "next_action": "meal_plan_generation"
            }
        
        return result
    
    def _handle_prioritization_conversation(self, user_id: str, message: str) -> Dict[str, Any]:
        """Handle goal prioritization conversation"""
        
        # Example: "budget is more important than muscle gain"
        result = self.messaging_service.handle_goal_prioritization(user_id, message)
        
        if result.get('success'):
            # Offer to regenerate meal plan with new priorities
            response_parts = [result['message']]
            response_parts.append("Want me to update your meal plan with these new priorities? 🔄")
            
            return {
                "success": True,
                "message": "\n".join(response_parts),
                "type": "prioritization_update",
                "next_action": "meal_plan_regeneration"
            }
        
        return result
    
    def _handle_custom_goal_conversation(self, user_id: str, message: str) -> Dict[str, Any]:
        """Handle custom/unknown goal conversation"""
        
        # Example: "skin health"
        result = self.multi_goal_service.handle_unknown_goal(user_id, message)
        
        if result.get('success'):
            response_parts = [result['acknowledgment']]
            
            # Explain what we'll do
            if result.get('is_new_custom_goal'):
                response_parts.append("I'll learn what works for you as we go and adapt your meal suggestions!")
            
            # Offer meal plan
            response_parts.append("Want me to create a meal plan that includes this goal? 🥗")
            
            return {
                "success": True,
                "message": "\n\n".join(response_parts),
                "type": "custom_goal_added",
                "is_new_goal_type": result.get('is_new_custom_goal', False),
                "next_action": "meal_plan_generation"
            }
        
        return result
    
    def _handle_meal_plan_generation(self, user_id: str, message: str) -> Dict[str, Any]:
        """Handle meal plan generation with multi-goal optimization"""
        
        try:
            # Parse any specific requirements from message
            days = 3  # Default
            if 'week' in message.lower():
                days = 7
            elif 'day' in message.lower():
                days = 1
            
            # Generate multi-goal meal plan
            meal_plan_result = self.meal_planner.generate_multi_goal_plan(user_id, days)
            
            if not meal_plan_result.success:
                return {
                    "success": False,
                    "message": "I couldn't generate a meal plan right now. Please try again!",
                    "type": "meal_plan_error"
                }
            
            # Generate introduction with multi-goal context
            intro = self.messaging_service.generate_multi_goal_meal_plan_intro(user_id, meal_plan_result)
            
            # Format meal plan for display
            meal_plan_text = self._format_meal_plan_for_display(meal_plan_result.meals)
            
            # Combine response
            response_parts = [intro, meal_plan_text]
            
            # Add footer with action options
            footer = """
💡 You can:
• Rate meals (1-5 stars) to improve future plans
• Ask for substitutions: "swap the salmon for chicken"
• Request priority changes: "make budget more important"
• Track your meals: "ate breakfast" or "skipped lunch"
"""
            response_parts.append(footer)
            
            return {
                "success": True,
                "message": "\n".join(response_parts),
                "type": "meal_plan_generated",
                "meal_plan": meal_plan_result.meals,
                "constraints_met": meal_plan_result.constraints_met,
                "trade_offs": meal_plan_result.trade_offs,
                "goal_satisfaction": meal_plan_result.goal_satisfaction
            }
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return {
                "success": False,
                "message": "I encountered an error generating your meal plan. Please try again!",
                "type": "meal_plan_error"
            }
    
    def _handle_goal_status_inquiry(self, user_id: str) -> Dict[str, Any]:
        """Handle inquiries about current goals"""
        
        try:
            user_profile = self.user_service.get_user_profile(user_id)
            goals = user_profile.get('goals', []) if user_profile else []
            
            if not goals:
                return {
                    "success": True,
                    "message": "You don't have any nutrition goals set yet! Tell me what you'd like to focus on - budget, muscle gain, weight loss, energy, or something else? 🎯",
                    "type": "no_goals"
                }
            
            # Format goals display
            goal_lines = ["🎯 Your current nutrition goals:\n"]
            
            # Sort by priority
            sorted_goals = sorted(goals, key=lambda g: g.get('priority', 2), reverse=True)
            
            for i, goal in enumerate(sorted_goals, 1):
                if goal['goal_type'] == 'custom':
                    goal_name = goal.get('label', 'Custom Goal')
                else:
                    goal_def = self.multi_goal_service.goal_definitions.get(goal['goal_type'], {})
                    goal_name = goal_def.get('name', goal['goal_type'])
                
                priority_text = ["", "Low", "Medium", "High", "Critical"][goal.get('priority', 2)]
                goal_lines.append(f"{i}. {goal_name} ({priority_text} priority)")
            
            # Add action suggestions
            goal_lines.append("\n💡 You can:")
            goal_lines.append("• Add more goals: 'I also want to focus on gut health'")
            goal_lines.append("• Change priorities: 'make budget more important'")
            goal_lines.append("• Generate meal plan: 'create my meal plan'")
            
            return {
                "success": True,
                "message": "\n".join(goal_lines),
                "type": "goal_status",
                "goals": goals
            }
            
        except Exception as e:
            logger.error(f"Error getting goal status: {str(e)}")
            return {
                "success": False,
                "message": "I couldn't retrieve your goals right now. Please try again!",
                "type": "goal_status_error"
            }
    
    def _format_meal_plan_for_display(self, meals: List[Dict[str, Any]]) -> str:
        """Format meal plan for WhatsApp/SMS display"""
        
        if not meals:
            return "No meals to display."
        
        # Group meals by day
        days = {}
        for meal in meals:
            day = meal['day']
            if day not in days:
                days[day] = []
            days[day].append(meal)
        
        formatted_lines = []
        
        for day_num in sorted(days.keys()):
            day_meals = days[day_num]
            formatted_lines.append(f"\n📅 **Day {day_num}**")
            
            for meal in day_meals:
                meal_type = meal['meal_type'].title()
                name = meal['name']
                cost = meal['cost_per_serving']
                prep_time = meal['prep_time']
                protein = meal['nutrition'].get('protein', 0)
                
                meal_line = f"• **{meal_type}**: {name}"
                meal_line += f" (${cost:.2f}, {prep_time}min, {protein}g protein)"
                formatted_lines.append(meal_line)
        
        return "\n".join(formatted_lines)
    
    def get_monetization_upsell_message(self, user_id: str) -> Optional[str]:
        """Generate monetization upsell based on user's goals"""
        
        try:
            user_profile = self.user_service.get_user_profile(user_id)
            goals = user_profile.get('goals', []) if user_profile else []
            premium_tier = user_profile.get('premium_tier', 'free') if user_profile else 'free'
            
            if premium_tier != 'free' or len(goals) <= 1:
                return None  # No upsell needed
            
            goal_names = []
            for goal in goals:
                if goal['goal_type'] == 'custom':
                    goal_names.append(goal.get('label', 'custom goal'))
                else:
                    goal_def = self.multi_goal_service.goal_definitions.get(goal['goal_type'], {})
                    goal_names.append(goal_def.get('name', goal['goal_type']).lower())
            
            formatted_goals = ", ".join(goal_names[:3])
            
            upsell_message = f"""🌟 **Unlock Multi-Goal Optimization**
            
You have {len(goals)} goals ({formatted_goals}). With Premium, I can:
• Create advanced meal plans that perfectly balance ALL your goals
• Provide detailed trade-off analysis and optimization
• Give you priority access to new goal types and features
• Offer personalized coaching for complex nutrition needs

Ready to maximize your {len(goals)}-goal nutrition strategy? Upgrade to Premium! 💪"""
            
            return upsell_message
            
        except Exception as e:
            logger.error(f"Error generating upsell message: {str(e)}")
            return None


# Example usage and test scenarios
def demonstrate_multi_goal_conversations():
    """Demonstrate the multi-goal conversation flow"""
    
    print("=== Multi-Goal Nutrition Assistant Demo ===\n")
    
    # Example conversations
    example_conversations = [
        {
            "user_input": "I want to eat on a budget, build muscle, and improve gut health",
            "expected_type": "multi_goal_input",
            "description": "User declares multiple goals simultaneously"
        },
        {
            "user_input": "budget is more important than muscle gain",
            "expected_type": "goal_prioritization", 
            "description": "User prioritizes among existing goals"
        },
        {
            "user_input": "skin health",
            "expected_type": "custom_goal",
            "description": "User requests unknown/custom goal"
        },
        {
            "user_input": "create my meal plan",
            "expected_type": "meal_plan_request",
            "description": "User requests meal plan generation"
        },
        {
            "user_input": "what are my current goals?",
            "expected_type": "goal_status",
            "description": "User inquires about current goals"
        }
    ]
    
    for example in example_conversations:
        print(f"Input: \"{example['user_input']}\"")
        print(f"Type: {example['expected_type']}")
        print(f"Description: {example['description']}")
        print("---")
    
    print("\n=== Key Features Demonstrated ===")
    print("✅ Multi-goal parsing and acknowledgment")
    print("✅ Custom goal handling with dietary proxies")
    print("✅ Goal prioritization with constraint merging")
    print("✅ Intelligent trade-off explanations")
    print("✅ Monetization hooks for premium features")
    print("✅ Natural language conversation flow")


if __name__ == "__main__":
    demonstrate_multi_goal_conversations()
