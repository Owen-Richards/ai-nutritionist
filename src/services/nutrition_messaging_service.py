"""
Enhanced Messaging Service with Nutrition Tracking UX

Battle-tested messaging patterns for nutrition power users with
daily/weekly facts, feeling checks, and adaptive nudging.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class NutritionMessagingService:
    """
    Enhanced messaging service with nutrition-specific UX patterns.
    Provides battle-tested copy for daily nudges, recaps, and feeling checks.
    """
    
    def __init__(self, nutrition_tracking_service):
        self.nutrition_tracking = nutrition_tracking_service
        
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
