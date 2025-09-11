"""
Nutrition Tracking Service

Comprehensive nutrition tracking with daily/weekly facts, feeling checks,
and adaptive nudging system based on battle-tested framework.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class DayNutrition:
    """Daily nutrition and wellness tracking"""
    date: str
    kcal: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    sodium: float = 0
    sugar_added: float = 0
    water_cups: float = 0
    steps: Optional[int] = None
    mood: Optional[str] = None  # 😞 😐 🙂 😄
    energy: Optional[str] = None  # 💤 ⚡
    digestion: Optional[str] = None  # 😣 🙂 👍
    sleep_quality: Optional[str] = None  # 😴😴😴
    
    # Meal tracking
    meals_ate: List[str] = None
    meals_skipped: List[str] = None
    meals_modified: List[str] = None
    snacks: List[str] = None
    
    def __post_init__(self):
        if self.meals_ate is None:
            self.meals_ate = []
        if self.meals_skipped is None:
            self.meals_skipped = []
        if self.meals_modified is None:
            self.meals_modified = []
        if self.snacks is None:
            self.snacks = []

@dataclass
class WeekSummary:
    """Weekly nutrition summary and insights"""
    week_start: str
    avg_kcal: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    avg_fiber: float
    avg_sodium: float
    avg_sugar_added: float
    avg_water: float
    
    wins: List[str] = None
    tweaks: List[str] = None
    top_liked_meals: List[Dict] = None
    protein_delta: float = 0
    fiber_delta: float = 0
    
    def __post_init__(self):
        if self.wins is None:
            self.wins = []
        if self.tweaks is None:
            self.tweaks = []
        if self.top_liked_meals is None:
            self.top_liked_meals = []

@dataclass
class UserFlags:
    """User wellness flags for adaptive responses"""
    low_energy_streak: int = 0
    high_sodium_week: bool = False
    fiber_gap: bool = False
    late_eating_pattern: bool = False
    good_streak: int = 0
    protein_below_target_days: int = 0
    afternoon_crashes: int = 0
    evening_hunger_spikes: int = 0
    bloating_flagged: bool = False

class NutritionTrackingService:
    """
    Battle-tested nutrition tracking service for power users.
    Tracks meals, nutrients, feelings, and provides adaptive nudging.
    """
    
    def __init__(self, user_service, ai_service):
        self.user_service = user_service
        self.ai_service = ai_service
        
        # Nutrition targets (can be personalized per user)
        self.default_targets = {
            'kcal': 2000,
            'protein': 120,
            'fiber': 30,
            'sodium': 2000,
            'water_cups': 8
        }
        
        # Recipe nutrition database (simplified)
        self.recipe_nutrition_db = {
            # This would be expanded with actual recipe data
            'miso_ginger_salmon': {
                'kcal': 380, 'protein': 32, 'carbs': 8, 'fat': 24, 
                'fiber': 2, 'sodium': 680, 'omega_3': 1.8
            },
            'harissa_chickpeas': {
                'kcal': 285, 'protein': 12, 'carbs': 45, 'fat': 8,
                'fiber': 11, 'sodium': 420, 'plant_protein_pct': 100
            }
        }
    
    def track_meal_simple(self, user_id: str, meal_name: str, status: str, 
                         portion_multiplier: float = 1.0) -> Dict[str, Any]:
        """
        Simple meal tracking: Ate it ✅ / Skipped ❌ / Modified ✍️
        """
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Get or create today's nutrition data
            day_nutrition = self._get_day_nutrition(user_id, today)
            
            # Track meal status
            if status == 'ate':
                if meal_name not in day_nutrition.meals_ate:
                    day_nutrition.meals_ate.append(meal_name)
                # Add nutrition from meal
                nutrition = self._get_meal_nutrition(meal_name, portion_multiplier)
                self._add_nutrition_to_day(day_nutrition, nutrition)
                
            elif status == 'skipped':
                if meal_name not in day_nutrition.meals_skipped:
                    day_nutrition.meals_skipped.append(meal_name)
                    
            elif status == 'modified':
                if meal_name not in day_nutrition.meals_modified:
                    day_nutrition.meals_modified.append(meal_name)
                # Would need modification details for accurate nutrition
                
            # Save updated nutrition data
            self._save_day_nutrition(user_id, day_nutrition)
            
            return {
                'success': True,
                'message': f"Got it! Marked {meal_name} as {status}.",
                'current_nutrition': self._get_nutrition_summary(day_nutrition)
            }
            
        except Exception as e:
            logger.error(f"Error tracking meal: {e}")
            return {'success': False, 'message': "Had trouble tracking that meal. Try again?"}
    
    def track_snack(self, user_id: str, snack_type: str) -> Dict[str, Any]:
        """Track optional snacks with template buttons"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            day_nutrition = self._get_day_nutrition(user_id, today)
            
            # Add snack
            day_nutrition.snacks.append(snack_type)
            
            # Add nutrition (simplified estimates)
            snack_nutrition = {
                'fruit': {'kcal': 80, 'carbs': 20, 'fiber': 3},
                'yogurt': {'kcal': 150, 'protein': 15, 'carbs': 8},
                'protein_bar': {'kcal': 200, 'protein': 20, 'carbs': 15},
                'nuts': {'kcal': 160, 'protein': 6, 'fat': 14, 'fiber': 3}
            }
            
            nutrition = snack_nutrition.get(snack_type, {'kcal': 100})
            self._add_nutrition_to_day(day_nutrition, nutrition)
            
            self._save_day_nutrition(user_id, day_nutrition)
            
            return {
                'success': True,
                'message': f"Added {snack_type} snack! 🍎",
                'current_nutrition': self._get_nutrition_summary(day_nutrition)
            }
            
        except Exception as e:
            logger.error(f"Error tracking snack: {e}")
            return {'success': False, 'message': "Had trouble adding that snack."}
    
    def track_water(self, user_id: str, amount: float, unit: str = 'cups') -> Dict[str, Any]:
        """Track water intake"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            day_nutrition = self._get_day_nutrition(user_id, today)
            
            # Convert to cups if needed
            if unit == 'oz':
                amount = amount / 8
            elif unit == 'ml':
                amount = amount / 240
            
            day_nutrition.water_cups += amount
            self._save_day_nutrition(user_id, day_nutrition)
            
            target = self.default_targets['water_cups']
            progress = min(day_nutrition.water_cups / target * 100, 100)
            
            return {
                'success': True,
                'message': f"Hydration logged! {day_nutrition.water_cups:.1f}/{target} cups ({progress:.0f}%) 💧"
            }
            
        except Exception as e:
            logger.error(f"Error tracking water: {e}")
            return {'success': False, 'message': "Had trouble logging water."}
    
    def feeling_check(self, user_id: str, mood: str = None, energy: str = None, 
                     digestion: str = None, sleep: str = None) -> Dict[str, Any]:
        """
        Gentle feeling check with emoji scale
        Mood: 😞 😐 🙂 😄 | Energy: 💤 ⚡ | Digestion: 😣 🙂 👍 | Sleep: 😴😴😴
        """
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            day_nutrition = self._get_day_nutrition(user_id, today)
            
            # Update feelings
            if mood:
                day_nutrition.mood = mood
            if energy:
                day_nutrition.energy = energy
            if digestion:
                day_nutrition.digestion = digestion
            if sleep:
                day_nutrition.sleep_quality = sleep
            
            self._save_day_nutrition(user_id, day_nutrition)
            
            # Check for adaptation triggers
            adaptation_message = self._check_feeling_adaptations(user_id, day_nutrition)
            
            response = "Thanks for checking in! 😊"
            if adaptation_message:
                response += f" {adaptation_message}"
            
            return {
                'success': True,
                'message': response
            }
            
        except Exception as e:
            logger.error(f"Error in feeling check: {e}")
            return {'success': False, 'message': "Thanks for sharing how you're feeling!"}
    
    def generate_daily_recap(self, user_id: str, date: str = None) -> str:
        """
        Generate daily nutrition recap (auto at 8-9pm local)
        Format: "Today: 1,840 kcal • 124g protein • 31g fiber • 1,850mg sodium
                ✅ Hit protein 🎯; ⚠️ Fiber a bit low vs 35g goal."
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            day_nutrition = self._get_day_nutrition(user_id, date)
            targets = self._get_user_targets(user_id)
            
            # Build main stats line
            recap = f"Today: **{day_nutrition.kcal:,.0f} kcal** • **{day_nutrition.protein:.0f}g protein** • **{day_nutrition.fiber:.0f}g fiber** • **{day_nutrition.sodium:,.0f}mg sodium**\n"
            
            # Add target analysis with emojis
            analyses = []
            
            # Protein analysis
            protein_pct = day_nutrition.protein / targets['protein'] * 100
            if protein_pct >= 90:
                analyses.append("✅ Hit protein 🎯")
            elif protein_pct >= 75:
                analyses.append("🟡 Close on protein")
            else:
                analyses.append(f"🔴 Protein low ({day_nutrition.protein:.0f}g vs {targets['protein']:.0f}g goal)")
            
            # Fiber analysis
            fiber_pct = day_nutrition.fiber / targets['fiber'] * 100
            if fiber_pct >= 90:
                analyses.append("✅ Great fiber!")
            elif fiber_pct >= 70:
                analyses.append(f"⚠️ Fiber a bit low vs {targets['fiber']:.0f}g goal")
            else:
                analyses.append(f"🔴 Need more fiber ({day_nutrition.fiber:.0f}g vs {targets['fiber']:.0f}g)")
            
            recap += "; ".join(analyses) + ".\n"
            
            # Add lifestyle factors if tracked
            lifestyle = []
            if day_nutrition.water_cups > 0:
                lifestyle.append(f"Water: {day_nutrition.water_cups:.0f} cups")
            if day_nutrition.steps:
                lifestyle.append(f"Steps: ~{day_nutrition.steps/1000:.0f}k")
            if day_nutrition.mood:
                lifestyle.append(f"Mood: {day_nutrition.mood}")
            if day_nutrition.energy:
                lifestyle.append(f"Energy: {day_nutrition.energy}")
            if day_nutrition.digestion:
                lifestyle.append(f"Digestion: {day_nutrition.digestion}")
            
            if lifestyle:
                recap += " | ".join(lifestyle)
            
            return recap
            
        except Exception as e:
            logger.error(f"Error generating daily recap: {e}")
            return "Had trouble with your daily recap - try asking again?"
    
    def generate_weekly_report(self, user_id: str, week_start: str = None) -> str:
        """
        Generate comprehensive weekly nutrition report
        """
        try:
            if not week_start:
                # Get Monday of current week
                today = datetime.now()
                days_since_monday = today.weekday()
                week_start = (today - timedelta(days=days_since_monday)).strftime('%Y-%m-%d')
            
            # Get week's nutrition data
            week_data = self._get_week_nutrition_data(user_id, week_start)
            if not week_data:
                return "Need a few more days of tracking to generate your weekly report! 📊"
            
            summary = self._calculate_week_summary(week_data, user_id)
            
            # Build report
            report = f"**This week avg:** **{summary.avg_kcal:,.0f} kcal/d**, **{summary.avg_protein:.0f}g protein/d**, **{summary.avg_fiber:.0f}g fiber/d**, **{summary.avg_sodium:,.0f}mg sodium/d**\n\n"
            
            # Wins section
            if summary.wins:
                report += "**Wins:** " + ", ".join(summary.wins) + "\n\n"
            
            # Tweaks section
            if summary.tweaks:
                report += "**Tweaks:** " + ", ".join(summary.tweaks) + "\n\n"
            
            # Top meals
            if summary.top_liked_meals:
                meals_text = ", ".join([f"{meal['name']} ({meal['rating']}⭐)" for meal in summary.top_liked_meals])
                report += f"**Highlights you loved:** {meals_text}\n\n"
            
            # Next week suggestions
            suggestions = self._generate_next_week_suggestions(summary, user_id)
            if suggestions:
                report += f"**Next week plan:** {suggestions}"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return "Having trouble with your weekly report - try again later? 📊"
    
    def handle_stats_command(self, user_id: str, command: str) -> str:
        """Handle on-demand nutrition commands"""
        try:
            command_lower = command.lower()
            
            if 'today' in command_lower:
                return self.generate_daily_recap(user_id)
            elif 'weekly' in command_lower or 'week' in command_lower:
                return self.generate_weekly_report(user_id)
            elif 'macro' in command_lower:
                return self._generate_macro_breakdown(user_id)
            elif 'fiber' in command_lower:
                return self._generate_fiber_sources(user_id)
            elif 'sodium' in command_lower:
                return self._generate_sodium_swaps(user_id)
            else:
                return self.generate_daily_recap(user_id)
                
        except Exception as e:
            logger.error(f"Error handling stats command: {e}")
            return "Which stats would you like? Try 'stats today' or 'weekly report'! 📊"
    
    def get_adaptation_suggestions(self, user_id: str) -> List[str]:
        """Get personalized adaptation suggestions based on recent data"""
        try:
            # Get recent nutrition data
            recent_data = self._get_recent_nutrition_data(user_id, days=7)
            if not recent_data:
                return []
            
            suggestions = []
            flags = self._analyze_user_flags(user_id, recent_data)
            
            # Protein adaptation
            if flags.protein_below_target_days >= 3:
                suggestions.append("Add 1 easy protein snack/day (Greek yogurt, edamame, tuna packet)")
            
            # Fiber adaptation
            avg_fiber = sum(day.fiber for day in recent_data) / len(recent_data)
            if avg_fiber < 25:
                suggestions.append("Oats/berries breakfast 2×, legume lunch 2×, veg add-on at dinner")
            
            # Sodium adaptation
            avg_sodium = sum(day.sodium for day in recent_data) / len(recent_data)
            if avg_sodium > 2300:
                suggestions.append("Swap canned for low-sodium, boost citrus/herbs/umami; cut 1 processed item")
            
            # Energy/mood adaptations
            if flags.low_energy_streak >= 2:
                suggestions.extend([
                    "+15–25g protein earlier in the day",
                    "Higher-fiber breakfast (oats/berries) to stabilize appetite",
                    "Shift dinner lighter & earlier (time-restricted window)",
                    "Hydration nudge: +2 cups water before 2pm"
                ])
            
            return suggestions[:3]  # Limit to top 3 suggestions
            
        except Exception as e:
            logger.error(f"Error getting adaptation suggestions: {e}")
            return []
    
    # Helper methods
    
    def _get_day_nutrition(self, user_id: str, date: str) -> DayNutrition:
        """Get or create nutrition data for a specific day"""
        try:
            nutrition_data = self.user_service.get_user_data(user_id, f'nutrition_{date}')
            if nutrition_data:
                return DayNutrition(**nutrition_data)
            else:
                return DayNutrition(date=date)
        except:
            return DayNutrition(date=date)
    
    def _save_day_nutrition(self, user_id: str, day_nutrition: DayNutrition):
        """Save nutrition data for a day"""
        self.user_service.save_user_data(user_id, f'nutrition_{day_nutrition.date}', asdict(day_nutrition))
    
    def _get_meal_nutrition(self, meal_name: str, portion_multiplier: float = 1.0) -> Dict[str, float]:
        """Get nutrition data for a meal (from recipe DB or estimation)"""
        # Clean meal name for lookup
        clean_name = meal_name.lower().replace(' ', '_').replace('-', '_')
        
        if clean_name in self.recipe_nutrition_db:
            nutrition = self.recipe_nutrition_db[clean_name].copy()
            # Apply portion multiplier
            for key, value in nutrition.items():
                if isinstance(value, (int, float)):
                    nutrition[key] = value * portion_multiplier
            return nutrition
        else:
            # Fallback estimation (would be more sophisticated in real implementation)
            return {
                'kcal': 400 * portion_multiplier,
                'protein': 25 * portion_multiplier,
                'carbs': 35 * portion_multiplier,
                'fat': 15 * portion_multiplier,
                'fiber': 8 * portion_multiplier,
                'sodium': 600 * portion_multiplier
            }
    
    def _add_nutrition_to_day(self, day_nutrition: DayNutrition, nutrition: Dict[str, float]):
        """Add nutrition values to daily totals"""
        day_nutrition.kcal += nutrition.get('kcal', 0)
        day_nutrition.protein += nutrition.get('protein', 0)
        day_nutrition.carbs += nutrition.get('carbs', 0)
        day_nutrition.fat += nutrition.get('fat', 0)
        day_nutrition.fiber += nutrition.get('fiber', 0)
        day_nutrition.sodium += nutrition.get('sodium', 0)
        day_nutrition.sugar_added += nutrition.get('sugar_added', 0)
    
    def _get_nutrition_summary(self, day_nutrition: DayNutrition) -> Dict[str, float]:
        """Get current day's nutrition summary"""
        return {
            'kcal': day_nutrition.kcal,
            'protein': day_nutrition.protein,
            'fiber': day_nutrition.fiber,
            'sodium': day_nutrition.sodium,
            'water': day_nutrition.water_cups
        }
    
    def _get_user_targets(self, user_id: str) -> Dict[str, float]:
        """Get personalized nutrition targets for user"""
        user_profile = self.user_service.get_user_profile(user_id)
        
        # Start with defaults and personalize based on profile
        targets = self.default_targets.copy()
        
        # Adjust based on user profile (simplified)
        if user_profile:
            height = user_profile.get('height')
            weight = user_profile.get('weight')
            activity_level = user_profile.get('activity_level', 'moderate')
            
            # Basic adjustments (would be more sophisticated)
            if weight and weight > 180:
                targets['protein'] = 140
                targets['kcal'] = 2200
            elif weight and weight < 140:
                targets['protein'] = 100
                targets['kcal'] = 1800
        
        return targets
    
    def _check_feeling_adaptations(self, user_id: str, day_nutrition: DayNutrition) -> Optional[str]:
        """Check if feelings trigger any immediate adaptations"""
        # Get recent feelings to detect patterns
        recent_days = self._get_recent_nutrition_data(user_id, days=3)
        if len(recent_days) < 2:
            return None
        
        # Check for low energy streak
        low_energy_count = sum(1 for day in recent_days[-2:] if day.energy == '💤')
        if low_energy_count >= 2:
            return "I noticed energy's been low. Want to try adding +15-25g protein earlier in the day? 💪"
        
        # Check for good streak
        good_mood_count = sum(1 for day in recent_days[-3:] if day.mood in ['🙂', '😄'])
        if good_mood_count >= 2:
            return "Nice streak! Keep current timing and repeat your top dinners next week? 🌟"
        
        return None
    
    def _get_week_nutrition_data(self, user_id: str, week_start: str) -> List[DayNutrition]:
        """Get nutrition data for a week"""
        week_data = []
        start_date = datetime.strptime(week_start, '%Y-%m-%d')
        
        for i in range(7):
            date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            day_nutrition = self._get_day_nutrition(user_id, date)
            if day_nutrition.kcal > 0:  # Only include days with data
                week_data.append(day_nutrition)
        
        return week_data
    
    def _calculate_week_summary(self, week_data: List[DayNutrition], user_id: str) -> WeekSummary:
        """Calculate weekly summary from daily data"""
        if not week_data:
            return WeekSummary(week_start='', avg_kcal=0, avg_protein=0, avg_carbs=0, 
                             avg_fat=0, avg_fiber=0, avg_sodium=0, avg_sugar_added=0, avg_water=0)
        
        days = len(week_data)
        targets = self._get_user_targets(user_id)
        
        summary = WeekSummary(
            week_start=week_data[0].date,
            avg_kcal=sum(day.kcal for day in week_data) / days,
            avg_protein=sum(day.protein for day in week_data) / days,
            avg_carbs=sum(day.carbs for day in week_data) / days,
            avg_fat=sum(day.fat for day in week_data) / days,
            avg_fiber=sum(day.fiber for day in week_data) / days,
            avg_sodium=sum(day.sodium for day in week_data) / days,
            avg_sugar_added=sum(day.sugar_added for day in week_data) / days,
            avg_water=sum(day.water_cups for day in week_data) / days
        )
        
        # Calculate wins and tweaks
        summary.protein_delta = summary.avg_protein - targets['protein']
        summary.fiber_delta = summary.avg_fiber - targets['fiber']
        
        if summary.protein_delta > 5:
            summary.wins.append(f"+{summary.protein_delta:.0f}g protein over goal")
        if summary.avg_fiber >= targets['fiber']:
            summary.wins.append("hit fiber targets")
        if summary.avg_sodium <= targets['sodium']:
            summary.wins.append("great sodium control")
        
        # Generate tweaks
        if summary.avg_fiber < targets['fiber']:
            summary.tweaks.append(f"Fiber +{targets['fiber'] - summary.avg_fiber:.0f}g/day")
        if summary.avg_sodium > targets['sodium']:
            summary.tweaks.append("reduce added sodium")
        
        return summary
    
    def _generate_next_week_suggestions(self, summary: WeekSummary, user_id: str) -> str:
        """Generate suggestions for next week based on this week's data"""
        suggestions = []
        
        if summary.protein_delta > 0:
            suggestions.append("keep protein")
        if summary.avg_fiber < 30:
            suggestions.append("add berries/oats breakfast 2×")
        if summary.avg_sodium > 2000:
            suggestions.append("swap one dessert for fruit + yogurt")
        
        return "; ".join(suggestions) + "."
    
    def _get_recent_nutrition_data(self, user_id: str, days: int = 7) -> List[DayNutrition]:
        """Get recent nutrition data for analysis"""
        recent_data = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            day_nutrition = self._get_day_nutrition(user_id, date)
            if day_nutrition.kcal > 0:
                recent_data.append(day_nutrition)
        
        return recent_data
    
    def _analyze_user_flags(self, user_id: str, recent_data: List[DayNutrition]) -> UserFlags:
        """Analyze recent data to set user flags for adaptations"""
        flags = UserFlags()
        targets = self._get_user_targets(user_id)
        
        # Count consecutive low energy days
        for day in reversed(recent_data[-7:]):
            if day.energy == '💤':
                flags.low_energy_streak += 1
            else:
                break
        
        # Count protein below target days
        flags.protein_below_target_days = sum(
            1 for day in recent_data if day.protein < targets['protein'] * 0.8
        )
        
        # Check for good streak
        for day in reversed(recent_data[-3:]):
            if day.mood in ['🙂', '😄'] and day.energy == '⚡':
                flags.good_streak += 1
            else:
                break
        
        return flags
    
    def _generate_macro_breakdown(self, user_id: str) -> str:
        """Generate detailed macro breakdown for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        day_nutrition = self._get_day_nutrition(user_id, today)
        
        if day_nutrition.kcal == 0:
            return "No meals tracked today yet. Start logging to see your macro breakdown! 📊"
        
        # Calculate percentages
        total_kcal = day_nutrition.kcal
        protein_kcal = day_nutrition.protein * 4
        carb_kcal = day_nutrition.carbs * 4
        fat_kcal = day_nutrition.fat * 9
        
        protein_pct = (protein_kcal / total_kcal * 100) if total_kcal > 0 else 0
        carb_pct = (carb_kcal / total_kcal * 100) if total_kcal > 0 else 0
        fat_pct = (fat_kcal / total_kcal * 100) if total_kcal > 0 else 0
        
        return f"""**Today's Macro Breakdown:**
🥩 Protein: {day_nutrition.protein:.0f}g ({protein_pct:.0f}%)
🍞 Carbs: {day_nutrition.carbs:.0f}g ({carb_pct:.0f}%)
🥑 Fat: {day_nutrition.fat:.0f}g ({fat_pct:.0f}%)
🌾 Fiber: {day_nutrition.fiber:.0f}g
🧂 Sodium: {day_nutrition.sodium:,.0f}mg
💧 Water: {day_nutrition.water_cups:.1f} cups"""
    
    def _generate_fiber_sources(self, user_id: str) -> str:
        """Suggest fiber sources based on user preferences"""
        return """**Great Fiber Sources:**
🥣 Breakfast: Oats with berries (+8g)
🥗 Lunch: Add chickpeas or lentils (+7g)
🥕 Snacks: Apple with skin (+4g)
🍽️ Dinner: Extra vegetables (+3-5g)
🌰 Easy add: 1 tbsp chia seeds (+5g)

Aim for 30-35g total daily! 🎯"""
    
    def _generate_sodium_swaps(self, user_id: str) -> str:
        """Suggest low-sodium swaps"""
        return """**Low-Sodium Swaps:**
🥫 Canned → Low-sodium or rinse before use
🧂 Salt → Herbs, lemon, garlic, umami paste
🍞 Regular bread → Lower sodium options
🧀 Processed cheese → Fresh mozzarella
🥩 Deli meat → Fresh cooked proteins
🥗 Dressing → Olive oil + vinegar + herbs

Target: Under 2,000mg daily! 🎯"""
