"""
Enhanced Messaging Service with Nutrition Tracking UX

Battle-tested messaging patterns for nutrition power users with
daily/weekly facts, feeling checks, and adaptive nudging.
Enhanced with multi-goal support and custom goal handling.
"""

import logging
import os
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse
from typing import Dict, List, Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class NutritionMessagingService:
    """
    Enhanced messaging service with nutrition-specific UX patterns.
    Provides battle-tested copy for daily nudges, recaps, and feeling checks.
    Enhanced with multi-goal support and intelligent goal handling.
    """
    
    def __init__(self, nutrition_tracking_service, multi_goal_service=None):
        self.nutrition_tracking = nutrition_tracking_service
        self.multi_goal_service = multi_goal_service
        
        # Template snack buttons for quick tracking
        self.snack_templates = {
            'fruit': '🍎 Fruit',
            'yogurt': '🥛 Yogurt', 
            'protein_bar': '🍫 Protein Bar',
            'nuts': '🥜 Nuts',
            'custom': '✍️ Custom'
        }
        
        # Portion multiplier options
        self.portion_options = {
            '0.5': '½x',
            '1.0': '1x', 
            '1.5': '1.5x',
            '2.0': '2x'
        }
        
        # Feeling check emojis
        self.feeling_scales = {
            'mood': ['😞', '😐', '🙂', '😄'],
            'energy': ['💤', '⚡'],
            'digestion': ['😣', '🙂', '👍'],
            'sleep': ['😴', '😴😴', '😴😴😴']
        }
    
    def generate_morning_nudge(self, user_id: str) -> str:
        """Generate morning goal reminder with personalized targets"""
        try:
            targets = self.nutrition_tracking._get_user_targets(user_id)
            
            return f"""Good morning! 🌅

**Goal today:** **{targets['protein']:.0f}g protein**, **{targets['fiber']:.0f}g fiber**, water **{targets['water_cups']:.0f} cups**. I'll pace your meals to make that easy.

Ready for your first meal? 🍳"""
            
        except Exception as e:
            logger.error(f"Error generating morning nudge: {e}")
            return "Good morning! Ready to fuel your day right? 🌅"
    
    def generate_pre_dinner_reminder(self, user_id: str) -> str:
        """Generate pre-dinner nudge if behind on targets"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            day_nutrition = self.nutrition_tracking._get_day_nutrition(user_id, today)
            targets = self.nutrition_tracking._get_user_targets(user_id)
            
            protein_gap = targets['protein'] - day_nutrition.protein
            fiber_gap = targets['fiber'] - day_nutrition.fiber
            
            if protein_gap > 15 or fiber_gap > 10:
                suggestions = []
                if protein_gap > 15:
                    suggestions.append(f"protein ({protein_gap:.0f}g to go)")
                if fiber_gap > 10:
                    suggestions.append(f"fiber ({fiber_gap:.0f}g to go)")
                
                suggestion_text = " and ".join(suggestions)
                return f"You're at {day_nutrition.protein:.0f}g protein, {day_nutrition.fiber:.0f}g fiber — adding lentils or a yogurt dessert would hit {suggestion_text}. 🎯"
            
            return None  # No reminder needed
            
        except Exception as e:
            logger.error(f"Error generating pre-dinner reminder: {e}")
            return None
    
    def generate_meal_tracking_buttons(self, meal_name: str) -> Dict[str, Any]:
        """Generate quick meal tracking interface"""
        return {
            'message': f"How was your **{meal_name}**?",
            'buttons': [
                {'text': 'Ate it ✅', 'action': f'track_meal:{meal_name}:ate'},
                {'text': 'Skipped ❌', 'action': f'track_meal:{meal_name}:skipped'},
                {'text': 'Modified ✍️', 'action': f'track_meal:{meal_name}:modified'}
            ],
            'follow_up': "Portion size?",
            'portion_buttons': [
                {'text': '½x', 'action': f'portion:{meal_name}:0.5'},
                {'text': '1x', 'action': f'portion:{meal_name}:1.0'},
                {'text': '1.5x', 'action': f'portion:{meal_name}:1.5'},
                {'text': '2x', 'action': f'portion:{meal_name}:2.0'}
            ]
        }
    
    def generate_snack_buttons(self) -> Dict[str, Any]:
        """Generate snack tracking interface"""
        return {
            'message': "Add a snack?",
            'buttons': [
                {'text': '🍎 Fruit', 'action': 'track_snack:fruit'},
                {'text': '🥛 Yogurt', 'action': 'track_snack:yogurt'},
                {'text': '🍫 Protein Bar', 'action': 'track_snack:protein_bar'},
                {'text': '🥜 Nuts', 'action': 'track_snack:nuts'},
                {'text': '✍️ Custom', 'action': 'track_snack:custom'}
            ]
        }
    
    def generate_feeling_check_interface(self) -> Dict[str, Any]:
        """Generate gentle feeling check interface (2 taps, optional)"""
        return {
            'message': "How did you feel today? (totally optional! 😊)",
            'sections': [
                {
                    'label': 'Mood',
                    'buttons': [
                        {'text': '😞', 'action': 'feeling:mood:😞'},
                        {'text': '😐', 'action': 'feeling:mood:😐'},
                        {'text': '🙂', 'action': 'feeling:mood:🙂'},
                        {'text': '😄', 'action': 'feeling:mood:😄'}
                    ]
                },
                {
                    'label': 'Energy',
                    'buttons': [
                        {'text': '💤', 'action': 'feeling:energy:💤'},
                        {'text': '⚡', 'action': 'feeling:energy:⚡'}
                    ]
                },
                {
                    'label': 'Digestion',
                    'buttons': [
                        {'text': '😣', 'action': 'feeling:digestion:😣'},
                        {'text': '🙂', 'action': 'feeling:digestion:🙂'},
                        {'text': '👍', 'action': 'feeling:digestion:👍'}
                    ]
                }
            ],
            'footer': "Thanks for sharing! This helps me give you better suggestions. 💙"
        }
    
    def generate_low_energy_suggestions(self, user_id: str) -> str:
        """Generate suggestions when energy is low 2+ days"""
        return """I noticed energy's been low. Want to try one of these?

💪 **+15–25g protein earlier in the day**
🥣 **Higher-fiber breakfast (oats/berries) to stabilize appetite**
⏰ **Shift dinner lighter & earlier (time-restricted window)**
💧 **Hydration nudge: +2 cups water before 2pm**
🌾 **Swap refined carbs at lunch → whole grain/legume base**

Pick what feels doable! 😊"""
    
    def generate_good_streak_message(self, user_id: str) -> str:
        """Generate encouragement when feeling good 2-3 days"""
        return """Nice streak! Lock it in? 🌟

✅ **Keep current timing window (e.g., 16:8) for another week**
🍽️ **Repeat top 2 high-satisfaction dinners next week**
🦠 **Introduce one new gut-friendly add-on (kefir/kimchi) 2×**

You're on a roll! 🎯"""
    
    def format_daily_stats_response(self, user_id: str) -> str:
        """Format 'stats today' response with traffic lights"""
        try:
            recap = self.nutrition_tracking.generate_daily_recap(user_id)
            
            # Add traffic light indicators
            today = datetime.now().strftime('%Y-%m-%d')
            day_nutrition = self.nutrition_tracking._get_day_nutrition(user_id, today)
            targets = self.nutrition_tracking._get_user_targets(user_id)
            
            indicators = []
            
            # Protein indicator
            protein_pct = day_nutrition.protein / targets['protein'] * 100
            if protein_pct >= 90:
                indicators.append("🟢 Protein")
            elif protein_pct >= 70:
                indicators.append("🟡 Protein")
            else:
                indicators.append("🔴 Protein")
            
            # Fiber indicator
            fiber_pct = day_nutrition.fiber / targets['fiber'] * 100
            if fiber_pct >= 90:
                indicators.append("🟢 Fiber")
            elif fiber_pct >= 70:
                indicators.append("🟡 Fiber")
            else:
                indicators.append("🔴 Fiber")
            
            # Water indicator
            water_pct = day_nutrition.water_cups / targets['water_cups'] * 100
            if water_pct >= 90:
                indicators.append("🟢 Water")
            elif water_pct >= 70:
                indicators.append("🟡 Water")
            else:
                indicators.append("🔴 Water")
            
            return f"{recap}\n\n**Quick status:** {' | '.join(indicators)}"
            
        except Exception as e:
            logger.error(f"Error formatting daily stats: {e}")
            return "Having trouble with your stats right now. Try again? 📊"
    
    def format_how_can_i_feel_better_response(self, user_id: str) -> str:
        """Format personalized feeling-better suggestions"""
        try:
            suggestions = self.nutrition_tracking.get_adaptation_suggestions(user_id)
            
            if not suggestions:
                return """Here are some quick wins to feel better:

💪 **Add 15g protein to breakfast** (Greek yogurt, eggs)
💧 **Drink 2 cups water before 2pm** 
🌾 **Swap refined carbs for whole grains at lunch**

Small changes, big impact! ✨"""
            
            # Format personalized suggestions
            formatted_suggestions = []
            for i, suggestion in enumerate(suggestions[:3], 1):
                formatted_suggestions.append(f"**{i}.** {suggestion}")
            
            return f"""Based on your recent data, try these:\n\n{chr(10).join(formatted_suggestions)}\n\nPick what feels most doable right now! 😊"""
            
        except Exception as e:
            logger.error(f"Error generating feel better response: {e}")
            return "Let's focus on small wins: more protein, more water, better timing! 💪"
    
    def generate_water_tracking_prompts(self) -> Dict[str, Any]:
        """Generate water tracking interface"""
        return {
            'message': "Log your water intake:",
            'quick_buttons': [
                {'text': '1 cup', 'action': 'water:1:cups'},
                {'text': '2 cups', 'action': 'water:2:cups'},
                {'text': '16 oz', 'action': 'water:16:oz'},
                {'text': '500ml', 'action': 'water:500:ml'}
            ],
            'custom_input': "Or type amount (cups/oz/ml)"
        }
    
    def generate_strategy_suggestions(self, user_id: str, strategy_type: str) -> str:
        """Generate evidence-informed strategy suggestions (opt-in)"""
        suggestions = {
            'intermittent_fasting': """**Time-Restricted Eating Options:**

🕘 **12:12** → Eat 8am-8pm (gentle start)
🕙 **14:10** → Eat 10am-8pm (skip breakfast)  
🕚 **16:8** → Eat 12pm-8pm (classic approach)

Start gradually! Always framed as options. 💡""",
            
            'protein_timing': """**Protein Timing Strategy:**

🌅 **Breakfast:** 25-40g to boost satiety & energy
🌞 **Lunch:** 25-30g to avoid afternoon crashes
🌙 **Dinner:** 20-25g for recovery

Front-loading protein = all-day energy! 💪""",
            
            'gut_friendly': """**Gut-Friendly Rotation:**

🦠 **Prebiotics:** Onion, garlic, oats, bananas, legumes
🥛 **Fermented:** Kefir, kimchi, yogurt, sauerkraut

Aim for 2-4× per week. Your gut will thank you! 🌱""",
            
            'plant_forward': """**Plant-Forward Swaps:**

🌱 **1-3 dinners/week:** Legumes or tofu as protein
🍄 **Keep bold flavors:** Spices, herbs, umami
🥗 **Add variety:** Different beans, grains, vegetables

Delicious and sustainable! 🌍"""
        }
        
        footer = "\n\n*General wellness guidance, not medical advice. Consult a clinician for specific conditions.*"
        
        return suggestions.get(strategy_type, "Strategy not found.") + footer
    
    def format_adaptation_playbook_response(self, issue_type: str, user_id: str) -> str:
        """Format automatic adaptation responses based on detected issues"""
        playbooks = {
            'protein_low': """**Protein Boost Plan:**
• Add 1 easy protein snack/day (Greek yogurt, edamame, tuna packet)
• Include protein at every meal
• Try: protein smoothie, hard-boiled eggs, string cheese 💪""",
            
            'fiber_low': """**Fiber Ramp Plan:**
• Oats/berries breakfast 2×
• Legume lunch 2×  
• Extra vegetables at dinner
• Easy add: 1 tbsp chia seeds (+5g) 🌾""",
            
            'sodium_high': """**Sodium Trim Plan:**
• Swap canned for low-sodium versions
• Boost citrus/herbs/umami instead of salt
• Cut 1 processed item
• Rinse canned beans/vegetables 🧂""",
            
            'energy_crashes': """**Energy Stabilizer Plan:**
• Reduce refined carbs at lunch
• Add protein + crunch + acid
• Increase water intake
• Try: hummus + veggies, apple + almond butter ⚡""",
            
            'evening_hunger': """**Evening Balance Plan:**
• Shift more calories to earlier meals
• Add volume (veg/soup/salad) to dinner
• Try: larger lunch, lighter dinner
• Include: fiber + protein at each meal 🕐""",
            
            'bloating': """**Digestive Comfort Plan:**
• Reduce sugar alcohols/carbonation temporarily
• Try low-FODMAP swaps if needed
• Increase walking post-meal
• Consider: smaller, more frequent meals 🚶"""
        }
        
        response = playbooks.get(issue_type, "Let's work on optimizing your nutrition! 🎯")
        return f"{response}\n\nTry for 3-5 days and let me know how you feel! 😊"
    
    def format_family_cooking_message(self, household_size: int) -> str:
        """Generate household nutrition coverage for family cooks"""
        return f"""**Household Nutrition Coverage** (family of {household_size}):

🥩 **Protein targets:** {household_size * 25}g+ per meal
🌾 **Fiber boost:** Add beans/lentils to 2 meals
👶 **Kid-friendly:** Hidden vegetables in sauces
💡 **Prep tip:** Batch cook proteins & grains

Feeding everyone well! 👨‍👩‍👧‍👦"""
    
    def format_dinner_party_mode(self) -> str:
        """Format message for special entertaining weeks"""
        return """**Dinner Party Week Mode Activated!** 🎉

• Daily stats paused (enjoy your guests!)
• Monday reset plan ready
• Lighter meals prep available
• Hydration reminders only

Have fun entertaining! I'll help you reset smoothly after. 🥂"""
    
    def parse_user_input_for_tracking(self, message: str) -> Dict[str, Any]:
        """Parse natural language for nutrition tracking"""
        message_lower = message.lower()
        
        # Water tracking patterns
        water_patterns = [
            r'(\d+)\s*(cups?|cup)\s*(water|h2o)?',
            r'(\d+)\s*(oz|ounces?)\s*(water|h2o)?',
            r'(\d+)\s*(ml|milliliters?)\s*(water|h2o)?'
        ]
        
        for pattern in water_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount = float(match.group(1))
                unit = 'cups' if 'cup' in match.group(2) else ('oz' if 'oz' in match.group(2) else 'ml')
                return {'type': 'water', 'amount': amount, 'unit': unit}
        
        # Meal tracking patterns
        meal_patterns = [
            r'(ate|had|finished)\s+(.+)',
            r'(skipped|missed)\s+(.+)',
            r'(modified|changed)\s+(.+)'
        ]
        
        for pattern in meal_patterns:
            match = re.search(pattern, message_lower)
            if match:
                status = 'ate' if 'ate' in match.group(1) or 'had' in match.group(1) or 'finished' in match.group(1) else \
                        'skipped' if 'skipped' in match.group(1) or 'missed' in match.group(1) else 'modified'
                meal = match.group(2).strip()
                return {'type': 'meal', 'meal': meal, 'status': status}
        
        # Feeling patterns
        feeling_keywords = {
            'tired': {'energy': '💤'},
            'energetic': {'energy': '⚡'},
            'low energy': {'energy': '💤'},
            'high energy': {'energy': '⚡'},
            'bloated': {'digestion': '😣'},
            'good digestion': {'digestion': '👍'},
            'happy': {'mood': '😄'},
            'sad': {'mood': '😞'},
            'okay': {'mood': '😐'},
            'good': {'mood': '🙂'}
        }
        
        for keyword, feeling in feeling_keywords.items():
            if keyword in message_lower:
                return {'type': 'feeling', **feeling}
        
        return {'type': 'unknown'}
    
    def generate_contextual_response(self, user_input: str, user_id: str) -> str:
        """Generate contextual response based on user input parsing"""
        try:
            parsed = self.parse_user_input_for_tracking(user_input)
            
            if parsed['type'] == 'water':
                result = self.nutrition_tracking.track_water(
                    user_id, parsed['amount'], parsed['unit']
                )
                return result['message']
            
            elif parsed['type'] == 'meal':
                result = self.nutrition_tracking.track_meal_simple(
                    user_id, parsed['meal'], parsed['status']
                )
                return result['message']
            
            elif parsed['type'] == 'feeling':
                feeling_data = {k: v for k, v in parsed.items() if k != 'type'}
                result = self.nutrition_tracking.feeling_check(user_id, **feeling_data)
                return result['message']
            
            else:
                # Default responses for common queries
                if 'stats' in user_input.lower():
                    return self.format_daily_stats_response(user_id)
                elif 'feel better' in user_input.lower():
                    return self.format_how_can_i_feel_better_response(user_id)
                elif 'weekly' in user_input.lower() or 'week' in user_input.lower():
                    return self.nutrition_tracking.generate_weekly_report(user_id)
                else:
                    return None  # Let other handlers take over
                    
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return None
    
    def get_privacy_footer(self) -> str:
        """Standard privacy and safety footer"""
        return "\n\n*General wellness guidance, not medical advice.*"
    
    # ===== MULTI-GOAL CONVERSATION METHODS =====
    
    def handle_goal_input(self, user_id: str, message: str) -> Dict[str, Any]:
        """Handle user input about nutrition goals with multi-goal support"""
        try:
            if not self.multi_goal_service:
                return {"success": False, "error": "Multi-goal service not available"}
            
            # Parse for multiple goals in a single message
            goals = self._parse_multiple_goals(message)
            
            if not goals:
                # Try to handle as unknown/custom goal
                return self.multi_goal_service.handle_unknown_goal(user_id, message)
            
            results = []
            total_success = True
            
            # Add each parsed goal
            for goal_text in goals:
                result = self.multi_goal_service.add_user_goal(user_id, goal_text)
                results.append(result)
                if not result.get('success', False):
                    total_success = False
            
            # Generate combined response
            if total_success and len(goals) > 1:
                response = self._generate_multi_goal_acknowledgment(goals, results)
            elif total_success and len(goals) == 1:
                response = results[0].get('acknowledgment', 'Goal added successfully!')
            else:
                response = "I had trouble understanding some of your goals. Can you clarify?"
            
            return {
                "success": total_success,
                "message": response,
                "goals_added": len([r for r in results if r.get('success')]),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error handling goal input for user {user_id}: {str(e)}")
            return {"success": False, "error": "Failed to process goals"}
    
    def handle_goal_prioritization(self, user_id: str, message: str) -> Dict[str, Any]:
        """Handle user input about goal prioritization"""
        try:
            if not self.multi_goal_service:
                return {"success": False, "error": "Multi-goal service not available"}
            
            # Parse priority preferences from message
            priority_updates = self._parse_priority_preferences(message)
            
            if not priority_updates:
                return {
                    "success": False,
                    "message": "I didn't understand your priority preferences. Try saying something like 'budget is more important than muscle gain'"
                }
            
            # Update priorities
            result = self.multi_goal_service.update_goal_priorities(user_id, priority_updates)
            
            if result.get('success'):
                response = self._generate_priority_confirmation(priority_updates)
                return {"success": True, "message": response}
            else:
                return {"success": False, "message": "Failed to update goal priorities"}
                
        except Exception as e:
            logger.error(f"Error handling goal prioritization for user {user_id}: {str(e)}")
            return {"success": False, "error": "Failed to update priorities"}
    
    def generate_multi_goal_meal_plan_intro(self, user_id: str, meal_plan_result) -> str:
        """Generate introduction for multi-goal meal plans with trade-off explanations"""
        try:
            if not self.multi_goal_service:
                return "Here's your personalized meal plan!"
            
            # Get user goals for context
            user_profile = self.multi_goal_service.user_service.get_user_profile(user_id)
            goals = user_profile.get('goals', []) if user_profile else []
            
            if not goals:
                return "Here's a balanced meal plan to get you started! 🥗"
            
            # Create introduction based on goals and results
            intro_parts = []
            
            # Goal acknowledgment
            goal_names = []
            for goal in goals:
                if goal['goal_type'] == 'custom':
                    goal_names.append(goal.get('label', 'custom goal'))
                else:
                    goal_def = self.multi_goal_service.goal_definitions.get(goal['goal_type'], {})
                    goal_names.append(goal_def.get('name', goal['goal_type']).lower())
            
            if len(goal_names) == 1:
                intro_parts.append(f"🎯 Here's your {goal_names[0]} meal plan!")
            elif len(goal_names) == 2:
                intro_parts.append(f"🎯 Here's your {goal_names[0]} + {goal_names[1]} meal plan!")
            else:
                formatted_goals = ", ".join(goal_names[:-1]) + f", and {goal_names[-1]}"
                intro_parts.append(f"🎯 Here's your multi-goal plan balancing {formatted_goals}!")
            
            # Add cost summary if budget is a goal
            if any(goal['goal_type'] == 'budget' for goal in goals):
                if hasattr(meal_plan_result, 'cost_breakdown'):
                    total_cost = meal_plan_result.cost_breakdown.get('total_cost', 0)
                    daily_cost = meal_plan_result.cost_breakdown.get('daily_cost', 0)
                    intro_parts.append(f"💰 Total cost: ${total_cost:.2f} (~${daily_cost:.2f}/day)")
            
            # Add trade-off explanations
            if hasattr(meal_plan_result, 'trade_offs') and meal_plan_result.trade_offs:
                intro_parts.append("\n💡 Smart trade-offs made:")
                for trade_off in meal_plan_result.trade_offs[:2]:  # Limit to top 2
                    intro_parts.append(f"• {trade_off}")
            
            # Add goal satisfaction summary
            if hasattr(meal_plan_result, 'goal_satisfaction'):
                high_satisfaction = [goal for goal, score in meal_plan_result.goal_satisfaction.items() if score > 0.8]
                if high_satisfaction:
                    intro_parts.append(f"\n✅ Strongly optimized for: {', '.join(high_satisfaction)}")
            
            return "\n".join(intro_parts)
            
        except Exception as e:
            logger.error(f"Error generating multi-goal intro for user {user_id}: {str(e)}")
            return "Here's your personalized meal plan!"
    
    def suggest_goal_prioritization(self, user_id: str) -> Optional[str]:
        """Suggest goal prioritization when user has multiple goals"""
        try:
            if not self.multi_goal_service:
                return None
            
            user_profile = self.multi_goal_service.user_service.get_user_profile(user_id)
            goals = user_profile.get('goals', []) if user_profile else []
            
            if len(goals) <= 2:
                return None  # No need for prioritization
            
            # Generate prioritization suggestion
            goal_names = []
            for goal in goals:
                if goal['goal_type'] == 'custom':
                    goal_names.append(goal.get('label', 'custom goal'))
                else:
                    goal_def = self.multi_goal_service.goal_definitions.get(goal['goal_type'], {})
                    goal_names.append(goal_def.get('name', goal['goal_type']).lower())
            
            formatted_goals = ", ".join(goal_names)
            
            return f"""Since you have multiple goals ({formatted_goals}), which should I prioritize most strongly?
            
You can say something like:
• "Budget is most important"
• "Muscle gain first, then budget"
• "All equally important"

This helps me make better trade-offs in your meal plans! 🎯"""
            
        except Exception as e:
            logger.error(f"Error suggesting goal prioritization for user {user_id}: {str(e)}")
            return None
    
    def _parse_multiple_goals(self, message: str) -> List[str]:
        """Parse multiple goals from a single message"""
        message_lower = message.lower()
        
        # Common multi-goal patterns
        goal_patterns = [
            r'want to (.+?) and (.+?)(?:\s|$)',
            r'(.+?),\s*(.+?),?\s*and (.+)',
            r'(.+?)\s*\+\s*(.+)',
            r'both (.+?) and (.+)',
            r'(.+?) but also (.+)'
        ]
        
        for pattern in goal_patterns:
            match = re.search(pattern, message_lower)
            if match:
                goals = [goal.strip() for goal in match.groups()]
                return [goal for goal in goals if goal]  # Remove empty strings
        
        # Single goal fallback
        goal_keywords = [
            'budget', 'cheap', 'save money', 'affordable',
            'muscle', 'protein', 'build muscle', 'gain muscle',
            'lose weight', 'weight loss', 'diet',
            'gut health', 'digestion', 'gut',
            'energy', 'fatigue', 'tired',
            'quick', 'fast', 'easy', 'simple'
        ]
        
        for keyword in goal_keywords:
            if keyword in message_lower:
                return [keyword]
        
        return []
    
    def _generate_multi_goal_acknowledgment(self, goals: List[str], results: List[Dict]) -> str:
        """Generate acknowledgment for multiple goals"""
        successful_goals = [goals[i] for i, result in enumerate(results) if result.get('success')]
        
        if len(successful_goals) == 2:
            return f"Got it 👍 {successful_goals[0]} + {successful_goals[1]}. I'll balance both in your meal plans!"
        else:
            formatted_goals = ", ".join(successful_goals[:-1]) + f", and {successful_goals[-1]}"
            return f"Perfect! I'll optimize for {formatted_goals}. Since you have multiple goals, which should I prioritize most strongly?"
    
    def _parse_priority_preferences(self, message: str) -> List[Dict[str, Any]]:
        """Parse priority preferences from user message"""
        message_lower = message.lower()
        
        # Priority patterns
        priority_patterns = [
            r'(.+?)\s+(?:is\s+)?(?:more\s+important|priority|first)',
            r'prioritize\s+(.+?)(?:\s|$)',
            r'(.+?)\s+over\s+(.+)',
            r'focus\s+on\s+(.+?)(?:\s|$)'
        ]
        
        updates = []
        for pattern in priority_patterns:
            match = re.search(pattern, message_lower)
            if match:
                high_priority_goal = match.group(1).strip()
                
                # Map to goal type (simplified)
                goal_mapping = {
                    'budget': 'budget',
                    'muscle': 'muscle_gain',
                    'protein': 'muscle_gain',
                    'weight': 'weight_loss',
                    'energy': 'energy',
                    'quick': 'quick_meals',
                    'gut': 'gut_health'
                }
                
                for keyword, goal_type in goal_mapping.items():
                    if keyword in high_priority_goal:
                        updates.append({
                            'goal_type': goal_type,
                            'priority': 4  # High priority
                        })
                        break
        
        return updates
    
    def _generate_priority_confirmation(self, priority_updates: List[Dict]) -> str:
        """Generate confirmation message for priority updates"""
        if not priority_updates:
            return "Priority updated!"
        
        high_priority_goals = []
        for update in priority_updates:
            goal_type = update['goal_type']
            if hasattr(self.multi_goal_service, 'goal_definitions') and goal_type in self.multi_goal_service.goal_definitions:
                goal_name = self.multi_goal_service.goal_definitions[goal_type]['name']
                high_priority_goals.append(goal_name.lower())
        
        if len(high_priority_goals) == 1:
            return f"Got it! I'll prioritize {high_priority_goals[0]} in your meal plans. 🎯"
        else:
            formatted_goals = ", ".join(high_priority_goals)
            return f"Perfect! I'll give top priority to: {formatted_goals} 🎯"


# ---------------------------------------------------------------------------
# Unified orchestration helpers
# ---------------------------------------------------------------------------


def build_deep_link(path: str, channel: str, journey: str, locale: str) -> str:
    """Build a deep link with standardized UTM parameters."""
    base_url = os.getenv("DEEP_LINK_BASE_URL", "https://ai.health")
    normalized_path = path if path.startswith("/") else f"/{path}"
    absolute = urljoin(base_url, normalized_path)
    parsed = urlparse(absolute)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_params.update({
        "utm_source": channel,
        "utm_campaign": journey,
        "locale": locale,
    })
    updated = parsed._replace(query=urlencode(query_params))
    return updated.geturl()


class UnifiedMessageRenderer:
    """Render channel-specific messaging for NBA decisions."""

    def render(
        self,
        decision: Dict[str, Any],
        *,
        channel: str,
        locale: str,
        timezone: str,
    ) -> Dict[str, Any]:
        metadata = dict(decision.get("metadata", {}))
        metadata.setdefault("journey", decision.get("journey"))
        deep_link = decision.get("deep_link")
        primary = decision.get("primary_message", "")
        cta_label = decision.get("cta_label", "")
        is_rtl = self._is_rtl(locale)
        tz = self._resolve_timezone(timezone)
        local_date = self._format_local_date(locale, tz)
        builder = {
            "sms": self._render_sms,
            "whatsapp": self._render_whatsapp,
            "app": self._render_app,
            "web": self._render_web,
        }
        renderer = builder.get(channel, self._render_fallback)
        text = renderer(primary, cta_label, deep_link, locale=locale, metadata=metadata, date_line=local_date)
        render_metadata = {
            "locale": locale,
            "timezone": timezone,
            "rtl": is_rtl,
            "aria_label": f"{cta_label} action",
        }
        return {
            "channel": channel,
            "text": text,
            "primary_message": primary,
            "cta": {"label": cta_label, "deep_link": deep_link},
            "metadata": {**metadata, "render": render_metadata},
        }

    def _render_sms(
        self,
        message: str,
        label: str,
        link: str,
        *,
        locale: str,
        metadata: Dict[str, Any],
        date_line: str,
    ) -> str:
        opt_out = " Reply STOP to opt out"
        base = f"{message} {label}: {link}"
        candidate = f"{base}{opt_out}"
        if len(candidate) <= 160:
            return candidate
        available = max(20, 160 - len(opt_out) - len(label) - len(link) - 2)
        truncated = message[:available].rstrip()
        if len(truncated) < len(message):
            truncated = truncated.rstrip("., !") + "…"
        return f"{truncated} {label}: {link}{opt_out}"

    def _render_whatsapp(
        self,
        message: str,
        label: str,
        link: str,
        *,
        locale: str,
        metadata: Dict[str, Any],
        date_line: str,
    ) -> str:
        bullets = _WHATSAPP_BULLETS.get(metadata.get("journey"), _WHATSAPP_BULLETS.get("default"))
        localized = bullets.get(self._language(locale), bullets.get("en"))
        lines = [message]
        lines.extend(f"• {item}" for item in localized)
        lines.append(f"{label}: {link}")
        return "
".join(lines)

    def _render_app(
        self,
        message: str,
        label: str,
        link: str,
        *,
        locale: str,
        metadata: Dict[str, Any],
        date_line: str,
    ) -> str:
        return f"{date_line}
{message}
{label} → {link}"

    def _render_web(
        self,
        message: str,
        label: str,
        link: str,
        *,
        locale: str,
        metadata: Dict[str, Any],
        date_line: str,
    ) -> str:
        return (
            f"{message}
Primary action: {label} (link: {link})
"
            f"Screen reader label: {label} button"
        )

    def _render_fallback(
        self,
        message: str,
        label: str,
        link: str,
        *,
        locale: str,
        metadata: Dict[str, Any],
        date_line: str,
    ) -> str:
        return f"{message} {label}: {link}"

    def _resolve_timezone(self, name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            return ZoneInfo("UTC")

    def _format_local_date(self, locale: str, tz: ZoneInfo) -> str:
        now = datetime.now(tz)
        lang = self._language(locale)
        region = locale.split("-")[1].upper() if "-" in locale else ""
        if region == "US" or (lang == "en" and region in {"US", "CA"}):
            pattern = "%b %d"
        else:
            pattern = "%d %b"
        return now.strftime(pattern)

    @staticmethod
    def _language(locale: str) -> str:
        return (locale or "en").split("-")[0].lower()

    @staticmethod
    def _is_rtl(locale: str) -> bool:
        return UnifiedMessageRenderer._language(locale) in {"ar", "he", "fa"}


class MessageTemplatesService:
    """Helper to render orchestration responses per channel."""

    def __init__(
        self,
        renderer: Optional[UnifiedMessageRenderer] = None,
        base: Optional[NutritionMessagingService] = None,
    ) -> None:
        self.renderer = renderer or UnifiedMessageRenderer()
        self._base = base

    def render_next_best_action(
        self,
        decision: Dict[str, Any],
        *,
        channel: str,
        locale: str,
        timezone: str,
    ) -> Dict[str, Any]:
        payload = self.renderer.render(decision, channel=channel, locale=locale, timezone=timezone)
        payload.setdefault("metadata", {})["journey"] = decision.get("journey")
        return payload

    def __getattr__(self, item: str) -> Any:
        if self._base and hasattr(self._base, item):
            return getattr(self._base, item)
        raise AttributeError(f"{self.__class__.__name__} has no attribute {item}")


_WHATSAPP_BULLETS: Dict[str, Dict[str, List[str]]] = {
    "quick_log": {
        "en": ["2 taps to track", "Offline queue ready"],
        "es": ["2 toques para registrar", "Funciona sin conexión"],
        "fr": ["2 gestes pour suivre", "File d'attente hors ligne"],
    },
    "groceries": {
        "en": ["Items grouped", "5 min to verify"],
        "es": ["Artículos agrupados", "5 min para revisar"],
        "fr": ["Articles groupés", "5 min pour vérifier"],
    },
    "smart_swaps": {
        "en": ["Fits time & budget", "Tap once to replace"],
        "es": ["Ajustado a tiempo y presupuesto", "Un toque para reemplazar"],
        "fr": ["Respecte temps et budget", "Un appui pour remplacer"],
    },
    "recovery": {
        "en": ["Small wins count", "Gentle restart"],
        "es": ["Los pequeños logros cuentan", "Reinicio suave"],
        "fr": ["Les petits succès comptent", "Reprise en douceur"],
    },
    "default": {
        "en": ["Stay on track", "We've queued updates"],
    },
}
