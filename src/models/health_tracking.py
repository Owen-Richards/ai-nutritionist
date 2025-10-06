"""
Health Tracking and Analytics System
Tracks health metrics, nutrition goals, eating patterns, and provides insights
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import statistics


class ActivityLevel(Enum):
    SEDENTARY = "sedentary"         # Little to no exercise
    LIGHTLY_ACTIVE = "lightly_active"  # Light exercise 1-3 days/week
    MODERATELY_ACTIVE = "moderately_active"  # Moderate exercise 3-5 days/week
    VERY_ACTIVE = "very_active"     # Hard exercise 6-7 days/week
    EXTREMELY_ACTIVE = "extremely_active"  # Very hard exercise, physical job


class HealthGoal(Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    ATHLETIC_PERFORMANCE = "athletic_performance"
    GENERAL_HEALTH = "general_health"
    DISEASE_MANAGEMENT = "disease_management"


class MealCategory(Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    BEVERAGE = "beverage"


@dataclass
class BodyMeasurement:
    date: date
    weight_lbs: Optional[float] = None
    height_inches: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    muscle_mass_lbs: Optional[float] = None
    waist_inches: Optional[float] = None
    chest_inches: Optional[float] = None
    arm_inches: Optional[float] = None
    thigh_inches: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class VitalSigns:
    date: date
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    blood_sugar_mg_dl: Optional[float] = None
    cholesterol_total: Optional[float] = None
    cholesterol_ldl: Optional[float] = None
    cholesterol_hdl: Optional[float] = None
    triglycerides: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class FoodEntry:
    timestamp: datetime
    food_name: str
    quantity: float
    unit: str
    meal_category: MealCategory
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    recipe_id: Optional[str] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    mood_before: Optional[int] = None  # 1-5 scale
    mood_after: Optional[int] = None   # 1-5 scale
    hunger_before: Optional[int] = None  # 1-5 scale
    satisfaction_after: Optional[int] = None  # 1-5 scale


@dataclass
class WaterIntake:
    timestamp: datetime
    amount_oz: float
    notes: Optional[str] = None


@dataclass
class ExerciseEntry:
    timestamp: datetime
    activity_type: str
    duration_minutes: int
    calories_burned: Optional[float] = None
    intensity: Optional[str] = None  # low, moderate, high
    notes: Optional[str] = None


@dataclass
class SleepEntry:
    date: date
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    hours_slept: Optional[float] = None
    sleep_quality: Optional[int] = None  # 1-5 scale
    notes: Optional[str] = None


@dataclass
class DailyNutritionGoals:
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    water_oz: Optional[float] = None
    
    # Micronutrients
    vitamin_a_mcg: Optional[float] = None
    vitamin_c_mg: Optional[float] = None
    vitamin_d_iu: Optional[float] = None
    vitamin_e_mg: Optional[float] = None
    vitamin_k_mcg: Optional[float] = None
    thiamin_mg: Optional[float] = None
    riboflavin_mg: Optional[float] = None
    niacin_mg: Optional[float] = None
    vitamin_b6_mg: Optional[float] = None
    folate_mcg: Optional[float] = None
    vitamin_b12_mcg: Optional[float] = None
    calcium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    magnesium_mg: Optional[float] = None
    phosphorus_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    zinc_mg: Optional[float] = None


@dataclass
class HealthInsight:
    date: datetime
    category: str  # nutrition, activity, sleep, weight, etc.
    insight_type: str  # trend, recommendation, alert, achievement
    title: str
    description: str
    data_points: List[float] = None
    confidence_score: float = 0.8
    action_items: List[str] = None
    
    def __post_init__(self):
        if self.data_points is None:
            self.data_points = []
        if self.action_items is None:
            self.action_items = []


class NutritionCalculator:
    """Calculates nutritional needs based on personal metrics"""
    
    @staticmethod
    def calculate_bmr(weight_lbs: float, height_inches: float, age: int, sex: str) -> float:
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation"""
        # Convert to metric
        weight_kg = weight_lbs * 0.453592
        height_cm = height_inches * 2.54
        
        if sex.lower() == 'male':
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        
        return bmr
    
    @staticmethod
    def calculate_tdee(bmr: float, activity_level: ActivityLevel) -> float:
        """Calculate Total Daily Energy Expenditure"""
        multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9
        }
        
        return bmr * multipliers.get(activity_level, 1.2)
    
    @staticmethod
    def calculate_calorie_goal(tdee: float, health_goal: HealthGoal) -> float:
        """Calculate daily calorie goal based on health objective"""
        adjustments = {
            HealthGoal.WEIGHT_LOSS: -500,  # 1 lb/week loss
            HealthGoal.WEIGHT_GAIN: 500,   # 1 lb/week gain
            HealthGoal.MUSCLE_GAIN: 300,   # Moderate surplus
            HealthGoal.MAINTENANCE: 0,
            HealthGoal.ATHLETIC_PERFORMANCE: 200,
            HealthGoal.GENERAL_HEALTH: 0,
            HealthGoal.DISEASE_MANAGEMENT: 0
        }
        
        return tdee + adjustments.get(health_goal, 0)
    
    @staticmethod
    def calculate_macro_goals(calories: float, 
                            health_goal: HealthGoal,
                            weight_lbs: float) -> Tuple[float, float, float]:
        """Calculate macronutrient goals (protein, carbs, fat in grams)"""
        weight_kg = weight_lbs * 0.453592
        
        # Protein goals (g/kg body weight)
        protein_ratios = {
            HealthGoal.WEIGHT_LOSS: 1.6,
            HealthGoal.WEIGHT_GAIN: 1.4,
            HealthGoal.MUSCLE_GAIN: 2.0,
            HealthGoal.MAINTENANCE: 1.2,
            HealthGoal.ATHLETIC_PERFORMANCE: 1.8,
            HealthGoal.GENERAL_HEALTH: 1.0,
            HealthGoal.DISEASE_MANAGEMENT: 1.2
        }
        
        protein_g = weight_kg * protein_ratios.get(health_goal, 1.2)
        protein_calories = protein_g * 4
        
        # Fat: 20-35% of calories
        fat_percentage = 0.25 if health_goal == HealthGoal.WEIGHT_LOSS else 0.30
        fat_calories = calories * fat_percentage
        fat_g = fat_calories / 9
        
        # Carbs: remaining calories
        carb_calories = calories - protein_calories - fat_calories
        carb_g = max(0, carb_calories / 4)
        
        return protein_g, carb_g, fat_g


class HealthTracker:
    """Tracks and analyzes health data"""
    
    def __init__(self, user_phone: str):
        self.user_phone = user_phone
        self.body_measurements: List[BodyMeasurement] = []
        self.vital_signs: List[VitalSigns] = []
        self.food_entries: List[FoodEntry] = []
        self.water_intake: List[WaterIntake] = []
        self.exercise_entries: List[ExerciseEntry] = []
        self.sleep_entries: List[SleepEntry] = []
        self.nutrition_goals: Optional[DailyNutritionGoals] = None
        self.health_goals: List[HealthGoal] = []
        self.insights: List[HealthInsight] = []
        self.last_updated = datetime.utcnow()
    
    def add_body_measurement(self, measurement: BodyMeasurement) -> None:
        """Add body measurement"""
        # Remove existing measurement for the same date
        self.body_measurements = [m for m in self.body_measurements if m.date != measurement.date]
        self.body_measurements.append(measurement)
        self.body_measurements.sort(key=lambda x: x.date)
        self.last_updated = datetime.utcnow()
    
    def add_vital_signs(self, vitals: VitalSigns) -> None:
        """Add vital signs"""
        self.vital_signs = [v for v in self.vital_signs if v.date != vitals.date]
        self.vital_signs.append(vitals)
        self.vital_signs.sort(key=lambda x: x.date)
        self.last_updated = datetime.utcnow()
    
    def log_food(self, food_entry: FoodEntry) -> None:
        """Log food consumption"""
        self.food_entries.append(food_entry)
        self.food_entries.sort(key=lambda x: x.timestamp)
        self.last_updated = datetime.utcnow()
    
    def log_water(self, water_entry: WaterIntake) -> None:
        """Log water intake"""
        self.water_intake.append(water_entry)
        self.water_intake.sort(key=lambda x: x.timestamp)
        self.last_updated = datetime.utcnow()
    
    def log_exercise(self, exercise_entry: ExerciseEntry) -> None:
        """Log exercise"""
        self.exercise_entries.append(exercise_entry)
        self.exercise_entries.sort(key=lambda x: x.timestamp)
        self.last_updated = datetime.utcnow()
    
    def log_sleep(self, sleep_entry: SleepEntry) -> None:
        """Log sleep"""
        self.sleep_entries = [s for s in self.sleep_entries if s.date != sleep_entry.date]
        self.sleep_entries.append(sleep_entry)
        self.sleep_entries.sort(key=lambda x: x.date)
        self.last_updated = datetime.utcnow()
    
    def get_daily_nutrition_summary(self, target_date: date) -> Dict[str, Any]:
        """Get nutrition summary for a specific date"""
        day_entries = [
            entry for entry in self.food_entries
            if entry.timestamp.date() == target_date
        ]
        
        # Calculate totals
        total_calories = sum(entry.calories or 0 for entry in day_entries)
        total_protein = sum(entry.protein_g or 0 for entry in day_entries)
        total_carbs = sum(entry.carbs_g or 0 for entry in day_entries)
        total_fat = sum(entry.fat_g or 0 for entry in day_entries)
        total_fiber = sum(entry.fiber_g or 0 for entry in day_entries)
        total_sugar = sum(entry.sugar_g or 0 for entry in day_entries)
        total_sodium = sum(entry.sodium_mg or 0 for entry in day_entries)
        
        # Water intake
        day_water = [
            entry for entry in self.water_intake
            if entry.timestamp.date() == target_date
        ]
        total_water = sum(entry.amount_oz for entry in day_water)
        
        # Calculate progress vs goals
        progress = {}
        if self.nutrition_goals:
            progress = {
                "calories": {
                    "consumed": total_calories,
                    "goal": self.nutrition_goals.calories,
                    "percentage": (total_calories / self.nutrition_goals.calories) * 100 if self.nutrition_goals.calories > 0 else 0
                },
                "protein": {
                    "consumed": total_protein,
                    "goal": self.nutrition_goals.protein_g,
                    "percentage": (total_protein / self.nutrition_goals.protein_g) * 100 if self.nutrition_goals.protein_g > 0 else 0
                },
                "carbs": {
                    "consumed": total_carbs,
                    "goal": self.nutrition_goals.carbs_g,
                    "percentage": (total_carbs / self.nutrition_goals.carbs_g) * 100 if self.nutrition_goals.carbs_g > 0 else 0
                },
                "fat": {
                    "consumed": total_fat,
                    "goal": self.nutrition_goals.fat_g,
                    "percentage": (total_fat / self.nutrition_goals.fat_g) * 100 if self.nutrition_goals.fat_g > 0 else 0
                },
                "water": {
                    "consumed": total_water,
                    "goal": self.nutrition_goals.water_oz or 64,
                    "percentage": (total_water / (self.nutrition_goals.water_oz or 64)) * 100
                }
            }
        
        # Meal breakdown
        meals = {}
        for category in MealCategory:
            category_entries = [e for e in day_entries if e.meal_category == category]
            meals[category.value] = {
                "calories": sum(e.calories or 0 for e in category_entries),
                "protein": sum(e.protein_g or 0 for e in category_entries),
                "carbs": sum(e.carbs_g or 0 for e in category_entries),
                "fat": sum(e.fat_g or 0 for e in category_entries),
                "entries": len(category_entries)
            }
        
        return {
            "date": target_date.isoformat(),
            "totals": {
                "calories": total_calories,
                "protein_g": total_protein,
                "carbs_g": total_carbs,
                "fat_g": total_fat,
                "fiber_g": total_fiber,
                "sugar_g": total_sugar,
                "sodium_mg": total_sodium,
                "water_oz": total_water
            },
            "progress": progress,
            "meals": meals,
            "entry_count": len(day_entries)
        }
    
    def get_weight_trend(self, days: int = 30) -> Dict[str, Any]:
        """Get weight trend over specified days"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        relevant_measurements = [
            m for m in self.body_measurements
            if start_date <= m.date <= end_date and m.weight_lbs is not None
        ]
        
        if len(relevant_measurements) < 2:
            return {"error": "Not enough weight data for trend analysis"}
        
        weights = [m.weight_lbs for m in relevant_measurements]
        dates = [m.date for m in relevant_measurements]
        
        # Calculate trend
        first_weight = weights[0]
        last_weight = weights[-1]
        weight_change = last_weight - first_weight
        
        # Calculate average weekly change
        days_elapsed = (dates[-1] - dates[0]).days
        weekly_change = (weight_change / days_elapsed) * 7 if days_elapsed > 0 else 0
        
        # Determine trend direction
        if abs(weekly_change) < 0.1:
            trend = "stable"
        elif weekly_change > 0:
            trend = "gaining"
        else:
            trend = "losing"
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "start_weight": first_weight,
            "current_weight": last_weight,
            "total_change": round(weight_change, 1),
            "weekly_change": round(weekly_change, 1),
            "trend": trend,
            "data_points": len(relevant_measurements)
        }
    
    def get_nutrition_adherence(self, days: int = 7) -> Dict[str, Any]:
        """Calculate nutrition goal adherence over period"""
        if not self.nutrition_goals:
            return {"error": "No nutrition goals set"}
        
        end_date = date.today()
        adherence_data = []
        
        for i in range(days):
            check_date = end_date - timedelta(days=i)
            daily_summary = self.get_daily_nutrition_summary(check_date)
            
            if daily_summary["entry_count"] > 0:
                progress = daily_summary["progress"]
                adherence = {
                    "date": check_date.isoformat(),
                    "calories_adherence": min(100, progress.get("calories", {}).get("percentage", 0)),
                    "protein_adherence": min(100, progress.get("protein", {}).get("percentage", 0)),
                    "overall_score": 0
                }
                
                # Calculate overall adherence score
                scores = [
                    adherence["calories_adherence"],
                    adherence["protein_adherence"]
                ]
                adherence["overall_score"] = sum(scores) / len(scores)
                adherence_data.append(adherence)
        
        if not adherence_data:
            return {"error": "No nutrition data for the specified period"}
        
        # Calculate averages
        avg_calories = statistics.mean([d["calories_adherence"] for d in adherence_data])
        avg_protein = statistics.mean([d["protein_adherence"] for d in adherence_data])
        avg_overall = statistics.mean([d["overall_score"] for d in adherence_data])
        
        return {
            "period_days": days,
            "average_adherence": {
                "calories": round(avg_calories, 1),
                "protein": round(avg_protein, 1),
                "overall": round(avg_overall, 1)
            },
            "daily_data": adherence_data,
            "adherence_grade": self._get_adherence_grade(avg_overall)
        }
    
    def _get_adherence_grade(self, score: float) -> str:
        """Convert adherence score to grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def generate_health_insights(self) -> List[HealthInsight]:
        """Generate health insights based on tracked data"""
        insights = []
        now = datetime.utcnow()
        
        # Weight trend insight
        weight_trend = self.get_weight_trend(30)
        if "error" not in weight_trend:
            if weight_trend["trend"] == "losing" and HealthGoal.WEIGHT_LOSS in self.health_goals:
                insights.append(HealthInsight(
                    date=now,
                    category="weight",
                    insight_type="achievement",
                    title="Weight Loss Progress",
                    description=f"Great job! You've lost {abs(weight_trend['total_change'])} lbs in the last 30 days.",
                    data_points=[weight_trend["total_change"]],
                    action_items=["Keep up the good work!", "Stay consistent with your nutrition plan"]
                ))
            elif abs(weight_trend["weekly_change"]) > 2:
                insights.append(HealthInsight(
                    date=now,
                    category="weight",
                    insight_type="alert",
                    title="Rapid Weight Change",
                    description=f"You're changing weight rapidly ({weight_trend['weekly_change']} lbs/week). Consider consulting a healthcare provider.",
                    confidence_score=0.9,
                    action_items=["Consult with a healthcare provider", "Review your current diet plan"]
                ))
        
        # Nutrition adherence insight
        adherence = self.get_nutrition_adherence(7)
        if "error" not in adherence:
            overall_score = adherence["average_adherence"]["overall"]
            if overall_score >= 85:
                insights.append(HealthInsight(
                    date=now,
                    category="nutrition",
                    insight_type="achievement",
                    title="Excellent Nutrition Adherence",
                    description=f"You've maintained {overall_score:.1f}% adherence to your nutrition goals this week!",
                    action_items=["Keep up the excellent work!"]
                ))
            elif overall_score < 60:
                insights.append(HealthInsight(
                    date=now,
                    category="nutrition",
                    insight_type="recommendation",
                    title="Nutrition Goal Opportunity",
                    description=f"Your nutrition adherence is at {overall_score:.1f}%. Let's work on improving consistency.",
                    action_items=[
                        "Try meal prepping on weekends",
                        "Set reminders to log your food",
                        "Focus on hitting protein goals first"
                    ]
                ))
        
        # Hydration insight
        recent_water = [
            entry for entry in self.water_intake
            if entry.timestamp.date() >= date.today() - timedelta(days=3)
        ]
        if recent_water:
            daily_avg = sum(e.amount_oz for e in recent_water) / 3
            if daily_avg < 50:
                insights.append(HealthInsight(
                    date=now,
                    category="hydration",
                    insight_type="recommendation",
                    title="Increase Water Intake",
                    description=f"You're averaging {daily_avg:.1f} oz of water daily. Aim for at least 64 oz.",
                    action_items=[
                        "Carry a water bottle with you",
                        "Set hourly water reminders",
                        "Add lemon or cucumber for flavor"
                    ]
                ))
        
        self.insights.extend(insights)
        return insights
    
    def set_nutrition_goals(self, 
                          weight_lbs: float,
                          height_inches: float,
                          age: int,
                          sex: str,
                          activity_level: ActivityLevel,
                          health_goal: HealthGoal) -> DailyNutritionGoals:
        """Set personalized nutrition goals"""
        calculator = NutritionCalculator()
        
        bmr = calculator.calculate_bmr(weight_lbs, height_inches, age, sex)
        tdee = calculator.calculate_tdee(bmr, activity_level)
        calories = calculator.calculate_calorie_goal(tdee, health_goal)
        protein_g, carbs_g, fat_g = calculator.calculate_macro_goals(calories, health_goal, weight_lbs)
        
        # Set fiber goal (14g per 1000 calories)
        fiber_g = (calories / 1000) * 14
        
        # Set water goal (half body weight in ounces)
        water_oz = weight_lbs / 2
        
        self.nutrition_goals = DailyNutritionGoals(
            calories=round(calories),
            protein_g=round(protein_g, 1),
            carbs_g=round(carbs_g, 1),
            fat_g=round(fat_g, 1),
            fiber_g=round(fiber_g, 1),
            water_oz=round(water_oz)
        )
        
        self.last_updated = datetime.utcnow()
        return self.nutrition_goals
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "user_phone": self.user_phone,
            "body_measurements": [asdict(m) for m in self.body_measurements],
            "vital_signs": [asdict(v) for v in self.vital_signs],
            "food_entries": [asdict(f) for f in self.food_entries],
            "water_intake": [asdict(w) for w in self.water_intake],
            "exercise_entries": [asdict(e) for e in self.exercise_entries],
            "sleep_entries": [asdict(s) for s in self.sleep_entries],
            "nutrition_goals": asdict(self.nutrition_goals) if self.nutrition_goals else None,
            "health_goals": [goal.value for goal in self.health_goals],
            "insights": [asdict(i) for i in self.insights],
            "last_updated": self.last_updated.isoformat()
        }
