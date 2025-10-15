"""
Example implementation of structured logging for domain services.

Demonstrates:
- Business logic logging
- Domain event tracking
- Performance monitoring
- Error handling
- Data validation logging
"""

import time
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone

from packages.shared.monitoring import (
    get_logger, get_tracer, get_business_metrics,
    LogLevel, EventType, performance_monitor, audit_log
)


@dataclass
class NutritionData:
    """Nutrition data domain object."""
    food_id: str
    name: str
    calories_per_100g: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate nutrition data."""
        logger = get_logger()
        
        if self.calories_per_100g < 0:
            logger.error(
                "Invalid nutrition data: negative calories",
                extra={
                    "food_id": self.food_id,
                    "calories": float(self.calories_per_100g)
                }
            )
            raise ValueError("Calories cannot be negative")
        
        if any(value < 0 for value in [self.protein_g, self.carbs_g, self.fat_g]):
            logger.error(
                "Invalid nutrition data: negative macronutrients",
                extra={
                    "food_id": self.food_id,
                    "protein": float(self.protein_g),
                    "carbs": float(self.carbs_g),
                    "fat": float(self.fat_g)
                }
            )
            raise ValueError("Macronutrients cannot be negative")


@dataclass
class FoodItem:
    """Food item with quantity."""
    nutrition_data: NutritionData
    quantity_g: Decimal
    
    def calculate_calories(self) -> Decimal:
        """Calculate total calories for this food item."""
        return (self.nutrition_data.calories_per_100g * self.quantity_g) / 100


@dataclass
class MealAnalysis:
    """Complete meal analysis result."""
    meal_id: str
    food_items: List[FoodItem]
    total_calories: Decimal
    total_protein_g: Decimal
    total_carbs_g: Decimal
    total_fat_g: Decimal
    analysis_timestamp: datetime
    recommendations: List[str]


class NutritionService:
    """Domain service for nutrition analysis."""
    
    def __init__(self):
        self.logger = get_logger()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
    
    @performance_monitor("nutrition_analysis")
    @audit_log(EventType.BUSINESS_EVENT, "nutrition", "analyze_meal")
    async def analyze_meal(
        self, 
        food_items: List[FoodItem], 
        user_id: str,
        meal_type: str = "general"
    ) -> MealAnalysis:
        """Analyze a complete meal."""
        meal_id = f"meal_{int(time.time())}_{user_id}"
        
        self.logger.info(
            "Starting meal analysis",
            extra={
                "meal_id": meal_id,
                "user_id": user_id,
                "meal_type": meal_type,
                "food_items_count": len(food_items)
            }
        )
        
        # Log business event
        self.logger.business_event(
            event_type=EventType.BUSINESS_EVENT,
            entity_type="meal_analysis",
            entity_id=meal_id,
            action="started",
            metadata={
                "user_id": user_id,
                "meal_type": meal_type,
                "food_items": [item.nutrition_data.name for item in food_items]
            }
        )
        
        with self.tracer.trace("meal_analysis", tags={"user_id": user_id, "meal_type": meal_type}) as span:
            try:
                # Validate input
                await self._validate_food_items(food_items, span)
                
                # Calculate nutritional totals
                totals = await self._calculate_totals(food_items, span)
                
                # Generate recommendations
                recommendations = await self._generate_recommendations(totals, meal_type, span)
                
                # Create analysis result
                analysis = MealAnalysis(
                    meal_id=meal_id,
                    food_items=food_items,
                    total_calories=totals["calories"],
                    total_protein_g=totals["protein"],
                    total_carbs_g=totals["carbs"],
                    total_fat_g=totals["fat"],
                    analysis_timestamp=datetime.now(timezone.utc),
                    recommendations=recommendations
                )
                
                # Log successful completion
                self.logger.info(
                    "Meal analysis completed successfully",
                    extra={
                        "meal_id": meal_id,
                        "total_calories": float(analysis.total_calories),
                        "recommendations_count": len(recommendations)
                    }
                )
                
                # Log business event
                self.logger.business_event(
                    event_type=EventType.BUSINESS_EVENT,
                    entity_type="meal_analysis",
                    entity_id=meal_id,
                    action="completed",
                    metadata={
                        "total_calories": float(analysis.total_calories),
                        "total_protein": float(analysis.total_protein_g),
                        "total_carbs": float(analysis.total_carbs_g),
                        "total_fat": float(analysis.total_fat_g),
                        "recommendations_count": len(recommendations)
                    }
                )
                
                # Track business metrics
                if self.business_metrics:
                    self.business_metrics.track_business_kpi(
                        "meal_calories_avg",
                        float(analysis.total_calories),
                        tags={"meal_type": meal_type, "user_id": user_id}
                    )
                    
                    self.business_metrics.track_user_action(
                        "meal_analyzed",
                        user_id,
                        success=True
                    )
                
                span.add_tag("analysis.total_calories", str(analysis.total_calories))
                span.add_tag("analysis.status", "success")
                
                return analysis
                
            except Exception as e:
                self.logger.error(
                    "Meal analysis failed",
                    error=e,
                    extra={
                        "meal_id": meal_id,
                        "user_id": user_id,
                        "food_items_count": len(food_items)
                    }
                )
                
                # Log business event for failure
                self.logger.business_event(
                    event_type=EventType.ERROR_EVENT,
                    entity_type="meal_analysis",
                    entity_id=meal_id,
                    action="failed",
                    metadata={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "user_id": user_id
                    },
                    level=LogLevel.ERROR
                )
                
                # Track failure metrics
                if self.business_metrics:
                    self.business_metrics.track_user_action(
                        "meal_analyzed",
                        user_id,
                        success=False
                    )
                
                span.add_tag("analysis.status", "failed")
                span.add_tag("error.type", type(e).__name__)
                
                raise
    
    async def _validate_food_items(self, food_items: List[FoodItem], span) -> None:
        """Validate food items."""
        span.add_log("Starting food items validation")
        
        if not food_items:
            self.logger.warn("Empty food items list provided for analysis")
            raise ValueError("At least one food item is required")
        
        invalid_items = []
        for item in food_items:
            if item.quantity_g <= 0:
                invalid_items.append({
                    "food_id": item.nutrition_data.food_id,
                    "name": item.nutrition_data.name,
                    "quantity": float(item.quantity_g)
                })
        
        if invalid_items:
            self.logger.error(
                "Invalid food items with zero or negative quantities",
                extra={"invalid_items": invalid_items}
            )
            raise ValueError("All food items must have positive quantities")
        
        self.logger.debug(
            "Food items validation completed",
            extra={"validated_items_count": len(food_items)}
        )
        
        span.add_log("Food items validation completed", items_count=len(food_items))
    
    async def _calculate_totals(self, food_items: List[FoodItem], span) -> Dict[str, Decimal]:
        """Calculate nutritional totals."""
        span.add_log("Starting nutritional calculations")
        
        totals = {
            "calories": Decimal(0),
            "protein": Decimal(0),
            "carbs": Decimal(0),
            "fat": Decimal(0)
        }
        
        for item in food_items:
            item_calories = item.calculate_calories()
            multiplier = item.quantity_g / 100
            
            totals["calories"] += item_calories
            totals["protein"] += item.nutrition_data.protein_g * multiplier
            totals["carbs"] += item.nutrition_data.carbs_g * multiplier
            totals["fat"] += item.nutrition_data.fat_g * multiplier
            
            self.logger.debug(
                "Calculated nutrition for food item",
                extra={
                    "food_id": item.nutrition_data.food_id,
                    "food_name": item.nutrition_data.name,
                    "quantity_g": float(item.quantity_g),
                    "calories": float(item_calories),
                    "protein_g": float(item.nutrition_data.protein_g * multiplier),
                    "carbs_g": float(item.nutrition_data.carbs_g * multiplier),
                    "fat_g": float(item.nutrition_data.fat_g * multiplier)
                }
            )
        
        self.logger.info(
            "Nutritional totals calculated",
            extra={
                "total_calories": float(totals["calories"]),
                "total_protein_g": float(totals["protein"]),
                "total_carbs_g": float(totals["carbs"]),
                "total_fat_g": float(totals["fat"])
            }
        )
        
        span.add_log(
            "Nutritional calculations completed",
            total_calories=float(totals["calories"])
        )
        
        return totals
    
    async def _generate_recommendations(
        self, 
        totals: Dict[str, Decimal], 
        meal_type: str, 
        span
    ) -> List[str]:
        """Generate nutritional recommendations."""
        span.add_log("Starting recommendations generation")
        
        recommendations = []
        
        # Calorie recommendations
        if totals["calories"] > 800:
            recommendations.append("Consider reducing portion sizes - this meal is quite high in calories")
            self.logger.info("High calorie recommendation generated", extra={"calories": float(totals["calories"])})
        elif totals["calories"] < 200:
            recommendations.append("This meal is quite low in calories - consider adding more nutritious foods")
            self.logger.info("Low calorie recommendation generated", extra={"calories": float(totals["calories"])})
        
        # Protein recommendations
        protein_percentage = (totals["protein"] * 4) / totals["calories"] * 100 if totals["calories"] > 0 else 0
        if protein_percentage < 15:
            recommendations.append("Consider adding more protein sources like lean meats, fish, or legumes")
            self.logger.info("Low protein recommendation generated", extra={"protein_percentage": float(protein_percentage)})
        elif protein_percentage > 35:
            recommendations.append("You have excellent protein content in this meal")
            self.logger.info("High protein positive feedback generated", extra={"protein_percentage": float(protein_percentage)})
        
        # Carb recommendations
        carb_percentage = (totals["carbs"] * 4) / totals["calories"] * 100 if totals["calories"] > 0 else 0
        if carb_percentage > 60:
            recommendations.append("Consider balancing with more protein and healthy fats")
            self.logger.info("High carb recommendation generated", extra={"carb_percentage": float(carb_percentage)})
        
        # Fat recommendations
        fat_percentage = (totals["fat"] * 9) / totals["calories"] * 100 if totals["calories"] > 0 else 0
        if fat_percentage < 20:
            recommendations.append("Consider adding healthy fats like avocado, nuts, or olive oil")
            self.logger.info("Low fat recommendation generated", extra={"fat_percentage": float(fat_percentage)})
        
        # Meal type specific recommendations
        if meal_type == "breakfast":
            if carb_percentage < 40:
                recommendations.append("Breakfast could benefit from more complex carbohydrates for sustained energy")
        elif meal_type == "dinner":
            if totals["calories"] > 600:
                recommendations.append("Consider a lighter dinner for better sleep quality")
        
        self.logger.info(
            "Recommendations generated",
            extra={
                "recommendations_count": len(recommendations),
                "meal_type": meal_type,
                "recommendations": recommendations
            }
        )
        
        # Log business event for recommendations
        self.logger.business_event(
            event_type=EventType.BUSINESS_EVENT,
            entity_type="recommendations",
            action="generated",
            metadata={
                "count": len(recommendations),
                "meal_type": meal_type,
                "categories": ["calories", "protein", "carbs", "fat"]
            }
        )
        
        span.add_log(
            "Recommendations generation completed",
            recommendations_count=len(recommendations)
        )
        
        return recommendations


class UserProfileService:
    """Service for managing user nutrition profiles."""
    
    def __init__(self):
        self.logger = get_logger()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
    
    @performance_monitor("update_user_profile")
    @audit_log(EventType.AUDIT_EVENT, "user_profile", "update")
    async def update_nutrition_goals(
        self, 
        user_id: str, 
        goals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's nutrition goals."""
        self.logger.info(
            "Updating user nutrition goals",
            extra={
                "user_id": user_id,
                "goals": goals
            }
        )
        
        # Log GDPR-compliant audit event
        self.logger.business_event(
            event_type=EventType.AUDIT_EVENT,
            entity_type="user_data",
            entity_id=user_id,
            action="nutrition_goals_updated",
            metadata={
                "updated_fields": list(goals.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        with self.tracer.trace("update_nutrition_goals", tags={"user_id": user_id}) as span:
            try:
                # Validate goals
                await self._validate_nutrition_goals(goals, span)
                
                # Simulate database update
                await asyncio.sleep(0.01)
                
                # Track business metrics
                if self.business_metrics:
                    self.business_metrics.track_user_action(
                        "profile_updated",
                        user_id,
                        success=True
                    )
                
                self.logger.info(
                    "User nutrition goals updated successfully",
                    extra={"user_id": user_id}
                )
                
                return {"status": "success", "user_id": user_id}
                
            except Exception as e:
                self.logger.error(
                    "Failed to update user nutrition goals",
                    error=e,
                    extra={"user_id": user_id}
                )
                
                if self.business_metrics:
                    self.business_metrics.track_user_action(
                        "profile_updated",
                        user_id,
                        success=False
                    )
                
                raise
    
    async def _validate_nutrition_goals(self, goals: Dict[str, Any], span) -> None:
        """Validate nutrition goals."""
        span.add_log("Validating nutrition goals")
        
        required_fields = ["daily_calories", "protein_percentage", "carb_percentage", "fat_percentage"]
        missing_fields = [field for field in required_fields if field not in goals]
        
        if missing_fields:
            self.logger.error(
                "Missing required fields in nutrition goals",
                extra={"missing_fields": missing_fields}
            )
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Validate percentages sum to approximately 100%
        total_percentage = goals["protein_percentage"] + goals["carb_percentage"] + goals["fat_percentage"]
        if abs(total_percentage - 100) > 5:  # Allow 5% tolerance
            self.logger.error(
                "Macronutrient percentages do not sum to 100%",
                extra={
                    "protein_percentage": goals["protein_percentage"],
                    "carb_percentage": goals["carb_percentage"],
                    "fat_percentage": goals["fat_percentage"],
                    "total": total_percentage
                }
            )
            raise ValueError("Macronutrient percentages must sum to approximately 100%")
        
        span.add_log("Nutrition goals validation completed")


# Example usage
async def example_usage():
    """Example of how to use the nutrition service."""
    logger = get_logger()
    
    logger.info("Starting nutrition service example")
    
    # Create sample food items
    chicken_data = NutritionData(
        food_id="chicken_breast",
        name="Chicken Breast",
        calories_per_100g=Decimal("165"),
        protein_g=Decimal("31"),
        carbs_g=Decimal("0"),
        fat_g=Decimal("3.6")
    )
    
    rice_data = NutritionData(
        food_id="brown_rice",
        name="Brown Rice",
        calories_per_100g=Decimal("111"),
        protein_g=Decimal("2.6"),
        carbs_g=Decimal("23"),
        fat_g=Decimal("0.9")
    )
    
    food_items = [
        FoodItem(chicken_data, Decimal("150")),  # 150g chicken
        FoodItem(rice_data, Decimal("100"))      # 100g rice
    ]
    
    # Analyze meal
    nutrition_service = NutritionService()
    
    try:
        analysis = await nutrition_service.analyze_meal(
            food_items=food_items,
            user_id="user_123",
            meal_type="lunch"
        )
        
        logger.info(
            "Example meal analysis completed",
            extra={
                "meal_id": analysis.meal_id,
                "total_calories": float(analysis.total_calories)
            }
        )
        
    except Exception as e:
        logger.error("Example failed", error=e)


if __name__ == "__main__":
    # Setup monitoring
    from packages.shared.monitoring.setup import setup_service_monitoring
    monitoring = setup_service_monitoring("nutrition-service")
    
    # Run example
    asyncio.run(example_usage())
