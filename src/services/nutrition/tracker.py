"""
Nutrition Tracker - Track and log nutrition data
Consolidates: nutrition_tracking_service.py, nutrition_logging_service.py
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)

@dataclass
class NutritionEntry:
    """Single nutrition entry"""
    timestamp: str
    meal_type: str  # breakfast, lunch, dinner, snack
    food_item: str
    portion_size: float
    unit: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    sodium: float
    user_id: str
    source: str = "manual"  # manual, app, api
    
@dataclass
class DailyNutritionSummary:
    """Daily nutrition summary"""
    date: str
    user_id: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    total_sugar: float
    total_sodium: float
    meals_logged: int
    goal_adherence_score: float
    notes: Optional[str] = None

class NutritionTracker:
    """
    Comprehensive nutrition tracking service that logs food intake,
    calculates daily totals, and provides nutrition analysis.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nutrition_database = self._initialize_nutrition_database()
        self.daily_summaries = {}  # In-memory storage for demo
        self.nutrition_entries = []  # In-memory storage for demo
    
    def log_food_intake(
        self, 
        user_id: str, 
        food_item: str, 
        portion_size: float, 
        unit: str,
        meal_type: str = "snack",
        nutrition_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Log a food intake entry for a user
        
        Args:
            user_id: User identifier
            food_item: Name of the food item
            portion_size: Size of the portion consumed
            unit: Unit of measurement (grams, cups, pieces, etc.)
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            nutrition_data: Optional nutrition data, will lookup if not provided
            
        Returns:
            Logged entry with nutrition analysis
        """
        try:
            self.logger.info(f"Logging food intake: {food_item} for user {user_id}")
            
            # Get nutrition data
            if not nutrition_data:
                nutrition_data = self._lookup_nutrition_data(food_item, portion_size, unit)
            
            # Create nutrition entry
            entry = NutritionEntry(
                timestamp=datetime.now().isoformat(),
                meal_type=meal_type,
                food_item=food_item,
                portion_size=portion_size,
                unit=unit,
                calories=nutrition_data.get('calories', 0),
                protein=nutrition_data.get('protein', 0),
                carbs=nutrition_data.get('carbs', 0),
                fat=nutrition_data.get('fat', 0),
                fiber=nutrition_data.get('fiber', 0),
                sugar=nutrition_data.get('sugar', 0),
                sodium=nutrition_data.get('sodium', 0),
                user_id=user_id,
                source="manual"
            )
            
            # Store entry
            self.nutrition_entries.append(entry)
            
            # Update daily summary
            self._update_daily_summary(user_id, entry)
            
            # Return entry with additional analysis
            entry_dict = asdict(entry)
            entry_dict.update({
                "logged_at": entry.timestamp,
                "nutrition_density": self._calculate_nutrition_density(nutrition_data),
                "meal_contribution": self._calculate_meal_contribution(user_id, entry)
            })
            
            self.logger.info(f"Successfully logged {food_item} - {nutrition_data.get('calories', 0)} calories")
            return entry_dict
            
        except Exception as e:
            self.logger.error(f"Error logging food intake: {str(e)}")
            return {"error": str(e), "success": False}
    
    def get_daily_summary(
        self, 
        user_id: str, 
        date: str = None
    ) -> DailyNutritionSummary:
        """
        Get daily nutrition summary for a user
        
        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format, defaults to today
            
        Returns:
            Daily nutrition summary
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            summary_key = f"{user_id}_{date}"
            
            if summary_key in self.daily_summaries:
                return self.daily_summaries[summary_key]
            
            # Calculate summary from entries
            daily_entries = self._get_entries_for_date(user_id, date)
            summary = self._calculate_daily_summary(user_id, date, daily_entries)
            
            self.daily_summaries[summary_key] = summary
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting daily summary: {str(e)}")
            return DailyNutritionSummary(
                date=date or datetime.now().strftime('%Y-%m-%d'),
                user_id=user_id,
                total_calories=0, total_protein=0, total_carbs=0,
                total_fat=0, total_fiber=0, total_sugar=0,
                total_sodium=0, meals_logged=0, goal_adherence_score=0
            )
    
    def get_nutrition_trends(
        self, 
        user_id: str, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get nutrition trends over a specified period
        
        Args:
            user_id: User identifier
            days: Number of days to analyze
            
        Returns:
            Nutrition trends and analysis
        """
        try:
            self.logger.info(f"Analyzing nutrition trends for {days} days")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days-1)
            
            trends = {
                "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "daily_averages": {},
                "trends": {},
                "consistency_scores": {},
                "recommendations": []
            }
            
            # Collect daily summaries
            daily_data = []
            for i in range(days):
                current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                summary = self.get_daily_summary(user_id, current_date)
                daily_data.append(summary)
            
            # Calculate averages
            if daily_data:
                trends["daily_averages"] = {
                    "calories": sum(d.total_calories for d in daily_data) / len(daily_data),
                    "protein": sum(d.total_protein for d in daily_data) / len(daily_data),
                    "carbs": sum(d.total_carbs for d in daily_data) / len(daily_data),
                    "fat": sum(d.total_fat for d in daily_data) / len(daily_data),
                    "fiber": sum(d.total_fiber for d in daily_data) / len(daily_data)
                }
                
                # Calculate trends
                trends["trends"] = self._calculate_nutrient_trends(daily_data)
                
                # Calculate consistency
                trends["consistency_scores"] = self._calculate_consistency_scores(daily_data)
                
                # Generate recommendations
                trends["recommendations"] = self._generate_trend_recommendations(trends)
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting nutrition trends: {str(e)}")
            return {"error": str(e)}
    
    def track_hydration(
        self, 
        user_id: str, 
        amount_ml: float, 
        beverage_type: str = "water"
    ) -> Dict[str, Any]:
        """
        Track hydration intake
        
        Args:
            user_id: User identifier
            amount_ml: Amount in milliliters
            beverage_type: Type of beverage
            
        Returns:
            Hydration tracking result
        """
        try:
            hydration_entry = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "amount_ml": amount_ml,
                "beverage_type": beverage_type,
                "calories": self._get_beverage_calories(beverage_type, amount_ml)
            }
            
            # Get daily hydration total
            today = datetime.now().strftime('%Y-%m-%d')
            daily_hydration = self._get_daily_hydration(user_id, today)
            daily_hydration += amount_ml
            
            # Hydration goals (2000ml baseline)
            hydration_goal = 2000
            progress_percentage = min(100, (daily_hydration / hydration_goal) * 100)
            
            result = {
                "entry": hydration_entry,
                "daily_total_ml": daily_hydration,
                "goal_ml": hydration_goal,
                "progress_percentage": progress_percentage,
                "remaining_ml": max(0, hydration_goal - daily_hydration),
                "status": "adequate" if daily_hydration >= hydration_goal else "needs_more"
            }
            
            self.logger.info(f"Tracked {amount_ml}ml of {beverage_type} - daily total: {daily_hydration}ml")
            return result
            
        except Exception as e:
            self.logger.error(f"Error tracking hydration: {str(e)}")
            return {"error": str(e)}
    
    def log_supplement_intake(
        self, 
        user_id: str, 
        supplement_name: str, 
        dosage: float, 
        unit: str
    ) -> Dict[str, Any]:
        """
        Log supplement intake
        
        Args:
            user_id: User identifier
            supplement_name: Name of the supplement
            dosage: Dosage amount
            unit: Unit of dosage
            
        Returns:
            Supplement logging result
        """
        try:
            supplement_entry = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "supplement_name": supplement_name,
                "dosage": dosage,
                "unit": unit,
                "nutrition_contribution": self._get_supplement_nutrition(supplement_name, dosage)
            }
            
            # Track supplement adherence
            adherence_data = self._track_supplement_adherence(user_id, supplement_name)
            
            result = {
                "entry": supplement_entry,
                "adherence_data": adherence_data,
                "recommendations": self._get_supplement_recommendations(supplement_name)
            }
            
            self.logger.info(f"Logged supplement: {supplement_name} {dosage}{unit}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error logging supplement: {str(e)}")
            return {"error": str(e)}
    
    def get_meal_timing_analysis(
        self, 
        user_id: str, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze meal timing patterns
        
        Args:
            user_id: User identifier
            days: Number of days to analyze
            
        Returns:
            Meal timing analysis
        """
        try:
            # Get recent entries
            recent_entries = self._get_recent_entries(user_id, days)
            
            # Group by meal type and analyze timing
            meal_times = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
            
            for entry in recent_entries:
                meal_type = entry.meal_type
                entry_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                hour_minute = entry_time.strftime('%H:%M')
                meal_times[meal_type].append(hour_minute)
            
            # Calculate timing patterns
            timing_analysis = {
                "meal_timing_patterns": {},
                "consistency_scores": {},
                "recommendations": []
            }
            
            for meal_type, times in meal_times.items():
                if times:
                    # Calculate average timing and consistency
                    avg_time, consistency = self._calculate_timing_stats(times)
                    timing_analysis["meal_timing_patterns"][meal_type] = {
                        "average_time": avg_time,
                        "consistency_score": consistency,
                        "frequency": len(times)
                    }
            
            # Generate timing recommendations
            timing_analysis["recommendations"] = self._generate_timing_recommendations(
                timing_analysis["meal_timing_patterns"]
            )
            
            return timing_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing meal timing: {str(e)}")
            return {"error": str(e)}
    
    def _lookup_nutrition_data(
        self, 
        food_item: str, 
        portion_size: float, 
        unit: str
    ) -> Dict[str, float]:
        """Lookup nutrition data for a food item"""
        # Normalize food item name
        food_key = food_item.lower().replace(' ', '_')
        
        # Get base nutrition per 100g
        base_nutrition = self.nutrition_database.get(food_key, {
            'calories': 200, 'protein': 10, 'carbs': 25, 'fat': 8,
            'fiber': 3, 'sugar': 5, 'sodium': 300
        })
        
        # Calculate portion multiplier
        portion_multiplier = self._calculate_portion_multiplier(portion_size, unit)
        
        # Scale nutrition data
        scaled_nutrition = {}
        for nutrient, value in base_nutrition.items():
            scaled_nutrition[nutrient] = value * portion_multiplier
        
        return scaled_nutrition
    
    def _calculate_portion_multiplier(self, portion_size: float, unit: str) -> float:
        """Calculate multiplier for portion size"""
        # Base conversions to 100g equivalent
        unit_conversions = {
            'grams': 0.01,
            'cups': 2.4,  # Approximate for mixed foods
            'pieces': 0.5,
            'tablespoons': 0.15,
            'teaspoons': 0.05,
            'ounces': 0.28
        }
        
        return portion_size * unit_conversions.get(unit.lower(), 1.0)
    
    def _update_daily_summary(self, user_id: str, entry: NutritionEntry):
        """Update daily summary with new entry"""
        date = entry.timestamp[:10]  # Extract date part
        summary_key = f"{user_id}_{date}"
        
        if summary_key not in self.daily_summaries:
            self.daily_summaries[summary_key] = DailyNutritionSummary(
                date=date, user_id=user_id,
                total_calories=0, total_protein=0, total_carbs=0,
                total_fat=0, total_fiber=0, total_sugar=0,
                total_sodium=0, meals_logged=0, goal_adherence_score=0
            )
        
        summary = self.daily_summaries[summary_key]
        summary.total_calories += entry.calories
        summary.total_protein += entry.protein
        summary.total_carbs += entry.carbs
        summary.total_fat += entry.fat
        summary.total_fiber += entry.fiber
        summary.total_sugar += entry.sugar
        summary.total_sodium += entry.sodium
        summary.meals_logged += 1
    
    def _get_entries_for_date(self, user_id: str, date: str) -> List[NutritionEntry]:
        """Get all nutrition entries for a specific date"""
        return [
            entry for entry in self.nutrition_entries
            if entry.user_id == user_id and entry.timestamp.startswith(date)
        ]
    
    def _calculate_daily_summary(
        self, 
        user_id: str, 
        date: str, 
        entries: List[NutritionEntry]
    ) -> DailyNutritionSummary:
        """Calculate daily summary from entries"""
        total_calories = sum(entry.calories for entry in entries)
        total_protein = sum(entry.protein for entry in entries)
        total_carbs = sum(entry.carbs for entry in entries)
        total_fat = sum(entry.fat for entry in entries)
        total_fiber = sum(entry.fiber for entry in entries)
        total_sugar = sum(entry.sugar for entry in entries)
        total_sodium = sum(entry.sodium for entry in entries)
        
        return DailyNutritionSummary(
            date=date,
            user_id=user_id,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            total_fiber=total_fiber,
            total_sugar=total_sugar,
            total_sodium=total_sodium,
            meals_logged=len(entries),
            goal_adherence_score=self._calculate_goal_adherence(
                total_calories, total_protein, total_carbs, total_fat
            )
        )
    
    def _calculate_nutrition_density(self, nutrition_data: Dict[str, float]) -> float:
        """Calculate nutrition density score"""
        calories = nutrition_data.get('calories', 1)
        protein = nutrition_data.get('protein', 0)
        fiber = nutrition_data.get('fiber', 0)
        
        if calories == 0:
            return 0
        
        # Higher protein and fiber relative to calories = better density
        density_score = ((protein * 4) + (fiber * 2)) / calories * 100
        return min(100, density_score)
    
    def _calculate_meal_contribution(self, user_id: str, entry: NutritionEntry) -> Dict[str, float]:
        """Calculate how much this entry contributes to daily goals"""
        # Simplified daily goals
        daily_goals = {
            'calories': 2000,
            'protein': 150,
            'carbs': 250,
            'fat': 67
        }
        
        contribution = {}
        for nutrient in ['calories', 'protein', 'carbs', 'fat']:
            entry_value = getattr(entry, nutrient)
            goal_value = daily_goals[nutrient]
            contribution[f"{nutrient}_percentage"] = (entry_value / goal_value) * 100
        
        return contribution
    
    def _calculate_nutrient_trends(self, daily_data: List[DailyNutritionSummary]) -> Dict[str, str]:
        """Calculate trends for each nutrient"""
        trends = {}
        
        if len(daily_data) < 2:
            return trends
        
        # Calculate simple trend direction
        for nutrient in ['total_calories', 'total_protein', 'total_carbs', 'total_fat']:
            values = [getattr(day, nutrient) for day in daily_data]
            
            # Simple trend calculation
            first_half = sum(values[:len(values)//2]) / (len(values)//2)
            second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            
            if second_half > first_half * 1.1:
                trends[nutrient] = "increasing"
            elif second_half < first_half * 0.9:
                trends[nutrient] = "decreasing"
            else:
                trends[nutrient] = "stable"
        
        return trends
    
    def _calculate_consistency_scores(self, daily_data: List[DailyNutritionSummary]) -> Dict[str, float]:
        """Calculate consistency scores for nutrients"""
        consistency = {}
        
        if len(daily_data) < 2:
            return consistency
        
        for nutrient in ['total_calories', 'total_protein', 'total_carbs', 'total_fat']:
            values = [getattr(day, nutrient) for day in daily_data]
            
            if values:
                mean_value = sum(values) / len(values)
                variance = sum((x - mean_value) ** 2 for x in values) / len(values)
                coefficient_of_variation = (variance ** 0.5) / mean_value if mean_value > 0 else 1
                
                # Convert to consistency score (lower variation = higher consistency)
                consistency[nutrient] = max(0, 100 - (coefficient_of_variation * 100))
        
        return consistency
    
    def _generate_trend_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on trends"""
        recommendations = []
        
        # Check calorie trends
        calorie_trend = trends.get("trends", {}).get("total_calories")
        if calorie_trend == "decreasing":
            recommendations.append("Consider increasing calorie intake to meet daily goals")
        elif calorie_trend == "increasing":
            recommendations.append("Monitor calorie intake to avoid exceeding daily targets")
        
        # Check protein trends
        protein_trend = trends.get("trends", {}).get("total_protein")
        if protein_trend == "decreasing":
            recommendations.append("Include more protein-rich foods in your meals")
        
        # Check consistency
        consistency_scores = trends.get("consistency_scores", {})
        low_consistency = [k for k, v in consistency_scores.items() if v < 60]
        if low_consistency:
            recommendations.append(f"Try to be more consistent with: {', '.join(low_consistency)}")
        
        return recommendations
    
    def _get_daily_hydration(self, user_id: str, date: str) -> float:
        """Get daily hydration total (placeholder)"""
        # This would query hydration entries from database
        return 1200  # Placeholder value
    
    def _get_beverage_calories(self, beverage_type: str, amount_ml: float) -> float:
        """Get calories for beverage"""
        calorie_per_100ml = {
            'water': 0,
            'coffee': 2,
            'tea': 1,
            'juice': 45,
            'soda': 42,
            'milk': 42
        }
        
        return (calorie_per_100ml.get(beverage_type.lower(), 0) * amount_ml) / 100
    
    def _get_supplement_nutrition(self, supplement_name: str, dosage: float) -> Dict[str, float]:
        """Get nutrition contribution from supplement"""
        # Simplified supplement nutrition database
        supplement_data = {
            'vitamin_d': {'vitamin_d': dosage},
            'vitamin_c': {'vitamin_c': dosage},
            'omega_3': {'omega_3': dosage},
            'protein_powder': {'protein': dosage * 0.8, 'calories': dosage * 4}
        }
        
        return supplement_data.get(supplement_name.lower(), {})
    
    def _track_supplement_adherence(self, user_id: str, supplement_name: str) -> Dict[str, Any]:
        """Track supplement adherence (placeholder)"""
        return {
            "daily_adherence": 85.0,
            "weekly_adherence": 80.0,
            "streak_days": 5
        }
    
    def _get_supplement_recommendations(self, supplement_name: str) -> List[str]:
        """Get recommendations for supplement"""
        recommendations = {
            'vitamin_d': ["Take with fatty meal for better absorption"],
            'vitamin_c': ["Take away from iron supplements"],
            'omega_3': ["Store in refrigerator", "Take with meals"]
        }
        
        return recommendations.get(supplement_name.lower(), [])
    
    def _get_recent_entries(self, user_id: str, days: int) -> List[NutritionEntry]:
        """Get recent nutrition entries"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        return [
            entry for entry in self.nutrition_entries
            if entry.user_id == user_id and entry.timestamp > cutoff_str
        ]
    
    def _calculate_timing_stats(self, times: List[str]) -> Tuple[str, float]:
        """Calculate average time and consistency for meal timing"""
        if not times:
            return "00:00", 0.0
        
        # Convert times to minutes for calculation
        minutes = []
        for time_str in times:
            hour, minute = map(int, time_str.split(':'))
            minutes.append(hour * 60 + minute)
        
        # Calculate average
        avg_minutes = sum(minutes) / len(minutes)
        avg_hour = int(avg_minutes // 60)
        avg_minute = int(avg_minutes % 60)
        avg_time = f"{avg_hour:02d}:{avg_minute:02d}"
        
        # Calculate consistency (lower variance = higher consistency)
        if len(minutes) > 1:
            variance = sum((m - avg_minutes) ** 2 for m in minutes) / len(minutes)
            consistency = max(0, 100 - (variance ** 0.5) / 60 * 100)  # Scale to 0-100
        else:
            consistency = 100.0
        
        return avg_time, consistency
    
    def _generate_timing_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate meal timing recommendations"""
        recommendations = []
        
        for meal_type, data in patterns.items():
            consistency = data.get('consistency_score', 0)
            if consistency < 70:
                recommendations.append(f"Try to eat {meal_type} at more consistent times")
        
        # Check for missing meals
        if 'breakfast' not in patterns:
            recommendations.append("Consider adding breakfast to your routine")
        
        return recommendations
    
    def _calculate_goal_adherence(
        self, 
        calories: float, 
        protein: float, 
        carbs: float, 
        fat: float
    ) -> float:
        """Calculate goal adherence score"""
        # Simplified goal adherence calculation
        goals = {'calories': 2000, 'protein': 150, 'carbs': 250, 'fat': 67}
        
        adherence_scores = []
        for nutrient, goal in goals.items():
            actual = locals()[nutrient]
            # Calculate how close to goal (penalty for being too far over or under)
            ratio = actual / goal if goal > 0 else 0
            if 0.8 <= ratio <= 1.2:  # Within 20% of goal
                score = 100
            elif 0.6 <= ratio <= 1.4:  # Within 40% of goal
                score = 75
            else:
                score = 50
            adherence_scores.append(score)
        
        return sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0
    
    def _initialize_nutrition_database(self) -> Dict[str, Dict[str, float]]:
        """Initialize nutrition database with common foods"""
        return {
            # Proteins
            'chicken_breast': {'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6, 'fiber': 0, 'sugar': 0, 'sodium': 74},
            'salmon': {'calories': 208, 'protein': 22, 'carbs': 0, 'fat': 12, 'fiber': 0, 'sugar': 0, 'sodium': 59},
            'eggs': {'calories': 155, 'protein': 13, 'carbs': 1.1, 'fat': 11, 'fiber': 0, 'sugar': 1.1, 'sodium': 124},
            'tofu': {'calories': 76, 'protein': 8, 'carbs': 1.9, 'fat': 4.8, 'fiber': 0.3, 'sugar': 0.6, 'sodium': 7},
            
            # Carbohydrates
            'brown_rice': {'calories': 111, 'protein': 2.6, 'carbs': 23, 'fat': 0.9, 'fiber': 1.8, 'sugar': 0.4, 'sodium': 5},
            'quinoa': {'calories': 120, 'protein': 4.4, 'carbs': 22, 'fat': 1.9, 'fiber': 2.8, 'sugar': 0.9, 'sodium': 7},
            'oatmeal': {'calories': 68, 'protein': 2.4, 'carbs': 12, 'fat': 1.4, 'fiber': 1.7, 'sugar': 0.3, 'sodium': 49},
            'sweet_potato': {'calories': 86, 'protein': 1.6, 'carbs': 20, 'fat': 0.1, 'fiber': 3, 'sugar': 4.2, 'sodium': 7},
            
            # Vegetables
            'broccoli': {'calories': 34, 'protein': 2.8, 'carbs': 7, 'fat': 0.4, 'fiber': 2.6, 'sugar': 1.5, 'sodium': 33},
            'spinach': {'calories': 23, 'protein': 2.9, 'carbs': 3.6, 'fat': 0.4, 'fiber': 2.2, 'sugar': 0.4, 'sodium': 79},
            'carrots': {'calories': 41, 'protein': 0.9, 'carbs': 10, 'fat': 0.2, 'fiber': 2.8, 'sugar': 4.7, 'sodium': 69},
            'bell_peppers': {'calories': 31, 'protein': 1, 'carbs': 7, 'fat': 0.3, 'fiber': 2.5, 'sugar': 4.2, 'sodium': 4},
            
            # Fruits
            'apple': {'calories': 52, 'protein': 0.3, 'carbs': 14, 'fat': 0.2, 'fiber': 2.4, 'sugar': 10, 'sodium': 1},
            'banana': {'calories': 89, 'protein': 1.1, 'carbs': 23, 'fat': 0.3, 'fiber': 2.6, 'sugar': 12, 'sodium': 1},
            'berries': {'calories': 57, 'protein': 0.7, 'carbs': 14, 'fat': 0.3, 'fiber': 2.4, 'sugar': 10, 'sodium': 1},
            
            # Nuts and seeds
            'almonds': {'calories': 579, 'protein': 21, 'carbs': 22, 'fat': 50, 'fiber': 12, 'sugar': 4.3, 'sodium': 1},
            'walnuts': {'calories': 654, 'protein': 15, 'carbs': 14, 'fat': 65, 'fiber': 6.7, 'sugar': 2.6, 'sodium': 2},
            'chia_seeds': {'calories': 486, 'protein': 17, 'carbs': 42, 'fat': 31, 'fiber': 34, 'sugar': 0, 'sodium': 16}
        }
