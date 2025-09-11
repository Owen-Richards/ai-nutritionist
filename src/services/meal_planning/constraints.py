"""
Multi-Goal Management Service for AI Nutritionist Assistant

Handles multiple simultaneous goals and custom goal processing with intelligent
constraint merging and prioritization for personalized nutrition coaching.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class GoalType(Enum):
    """Standard goal types supported by the system"""
    BUDGET = "budget"
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    GUT_HEALTH = "gut_health"
    ENERGY = "energy"
    HEART_HEALTH = "heart_health"
    DIABETES_FRIENDLY = "diabetes_friendly"
    PLANT_FORWARD = "plant_forward"
    ANTI_INFLAMMATORY = "anti_inflammatory"
    QUICK_MEALS = "quick_meals"
    FAMILY_FRIENDLY = "family_friendly"
    CUSTOM = "custom"


class GoalPriority(Enum):
    """Goal priority levels for constraint resolution"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class UserGoal:
    """Individual goal with type, priority, and metadata"""
    goal_type: str
    priority: int = 2  # Medium priority by default
    label: Optional[str] = None  # For custom goals
    constraints: Dict[str, Any] = None
    created_at: str = None
    last_updated: str = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.last_updated is None:
            self.last_updated = self.created_at


@dataclass
class MergedConstraints:
    """Merged nutrition and lifestyle constraints from multiple goals"""
    # Nutrition targets
    daily_calories: Optional[int] = None
    protein_grams: Optional[int] = None
    fiber_grams: Optional[int] = None
    sodium_mg: Optional[int] = None
    added_sugar_grams: Optional[int] = None
    
    # Budget constraints
    max_cost_per_meal: Optional[float] = None
    weekly_budget: Optional[float] = None
    
    # Time constraints
    max_prep_time: Optional[int] = None
    quick_meal_preference: bool = False
    
    # Dietary emphasis
    emphasized_foods: List[str] = None
    avoided_foods: List[str] = None
    required_nutrients: List[str] = None
    
    # Meal characteristics
    plant_protein_percentage: Optional[float] = None
    whole_grain_preference: bool = False
    anti_inflammatory_focus: bool = False
    
    def __post_init__(self):
        if self.emphasized_foods is None:
            self.emphasized_foods = []
        if self.avoided_foods is None:
            self.avoided_foods = []
        if self.required_nutrients is None:
            self.required_nutrients = []


class MultiGoalService:
    """Service for managing multiple user goals and constraint merging"""
    
    def __init__(self, user_service):
        self.user_service = user_service
        
        # Standard goal definitions with their default constraints
        self.goal_definitions = {
            GoalType.BUDGET.value: {
                "name": "Budget-Friendly",
                "description": "Keep meal costs low while maintaining nutrition",
                "constraints": {
                    "max_cost_per_meal": 4.00,
                    "emphasized_foods": ["beans", "lentils", "rice", "oats", "seasonal_vegetables", "chicken_thighs"],
                    "avoided_foods": ["premium_cuts", "exotic_ingredients", "out_of_season"]
                }
            },
            GoalType.MUSCLE_GAIN.value: {
                "name": "Muscle Building",
                "description": "Optimize protein intake for muscle development",
                "constraints": {
                    "protein_grams": 140,
                    "daily_calories": 2400,
                    "emphasized_foods": ["lean_protein", "eggs", "Greek_yogurt", "quinoa"],
                    "required_nutrients": ["protein", "leucine", "creatine"]
                }
            },
            GoalType.WEIGHT_LOSS.value: {
                "name": "Weight Management",
                "description": "Create sustainable caloric deficit with high satiety",
                "constraints": {
                    "daily_calories": 1600,
                    "fiber_grams": 35,
                    "emphasized_foods": ["vegetables", "lean_protein", "whole_grains"],
                    "avoided_foods": ["refined_sugar", "processed_foods"]
                }
            },
            GoalType.GUT_HEALTH.value: {
                "name": "Gut Health",
                "description": "Support digestive health and microbiome",
                "constraints": {
                    "fiber_grams": 40,
                    "emphasized_foods": ["fermented_foods", "prebiotics", "diverse_vegetables"],
                    "required_nutrients": ["fiber", "probiotics", "polyphenols"]
                }
            },
            GoalType.ENERGY.value: {
                "name": "Energy Optimization",
                "description": "Stabilize blood sugar and optimize energy levels",
                "constraints": {
                    "added_sugar_grams": 25,
                    "emphasized_foods": ["complex_carbs", "healthy_fats", "steady_protein"],
                    "avoided_foods": ["refined_sugar", "high_glycemic_foods"]
                }
            },
            GoalType.HEART_HEALTH.value: {
                "name": "Heart Health",
                "description": "Support cardiovascular health through nutrition",
                "constraints": {
                    "sodium_mg": 1500,
                    "emphasized_foods": ["omega3_fish", "nuts", "olive_oil", "vegetables"],
                    "anti_inflammatory_focus": True
                }
            },
            GoalType.QUICK_MEALS.value: {
                "name": "Quick & Easy",
                "description": "Minimize prep time while maintaining nutrition",
                "constraints": {
                    "max_prep_time": 20,
                    "quick_meal_preference": True,
                    "emphasized_foods": ["one_pot_meals", "sheet_pan_recipes", "no_chop_ingredients"]
                }
            },
            GoalType.PLANT_FORWARD.value: {
                "name": "Plant-Forward",
                "description": "Emphasize plant-based nutrition",
                "constraints": {
                    "plant_protein_percentage": 60,
                    "emphasized_foods": ["legumes", "nuts", "seeds", "vegetables", "whole_grains"],
                    "whole_grain_preference": True
                }
            }
        }
        
        # Custom goal knowledge base - maps common labels to dietary proxies
        self.custom_goal_proxies = {
            "skin health": {
                "emphasized_foods": ["omega3_foods", "antioxidant_rich", "zinc_rich"],
                "required_nutrients": ["vitamin_c", "vitamin_e", "omega3", "zinc"],
                "description": "Focus on omega-3s, antioxidants, and skin-supporting nutrients"
            },
            "sleep": {
                "emphasized_foods": ["magnesium_rich", "tryptophan_rich", "herbal_teas"],
                "avoided_foods": ["caffeine_evening", "heavy_late_meals"],
                "description": "Include magnesium, avoid late caffeine, light evening meals"
            },
            "brain health": {
                "emphasized_foods": ["omega3_fish", "blueberries", "dark_leafy_greens"],
                "required_nutrients": ["omega3", "antioxidants", "choline"],
                "description": "Support cognitive function with brain-healthy nutrients"
            },
            "immune support": {
                "emphasized_foods": ["vitamin_c_rich", "zinc_rich", "garlic", "ginger"],
                "required_nutrients": ["vitamin_c", "vitamin_d", "zinc"],
                "description": "Boost immune system with key vitamins and minerals"
            },
            "bone health": {
                "emphasized_foods": ["calcium_rich", "vitamin_d_rich", "magnesium_rich"],
                "required_nutrients": ["calcium", "vitamin_d", "magnesium", "vitamin_k"],
                "description": "Support bone density with calcium, vitamin D, and cofactors"
            }
        }
    
    def add_user_goal(self, user_id: str, goal_input: str, priority: int = 2) -> Dict[str, Any]:
        """Add a new goal for the user, handling both standard and custom goals"""
        try:
            # Parse the goal input
            parsed_goal = self._parse_goal_input(goal_input)
            
            # Get current user profile
            user_profile = self.user_service.get_user_profile(user_id)
            if not user_profile:
                return {"success": False, "error": "User profile not found"}
            
            # Initialize goals if not present
            if 'goals' not in user_profile:
                user_profile['goals'] = []
            
            # Create goal object
            if parsed_goal['is_standard']:
                goal = UserGoal(
                    goal_type=parsed_goal['goal_type'],
                    priority=priority,
                    constraints=self.goal_definitions[parsed_goal['goal_type']]['constraints'].copy()
                )
            else:
                # Custom goal
                custom_constraints = self._get_custom_goal_constraints(parsed_goal['label'])
                goal = UserGoal(
                    goal_type=GoalType.CUSTOM.value,
                    priority=priority,
                    label=parsed_goal['label'],
                    constraints=custom_constraints
                )
            
            # Add to user goals
            user_profile['goals'].append(asdict(goal))
            user_profile['last_updated'] = datetime.utcnow().isoformat()
            
            # Save updated profile
            self.user_service.table.put_item(Item=user_profile)
            
            # Generate acknowledgment message
            ack_message = self._generate_goal_acknowledgment(goal, user_profile['goals'])
            
            return {
                "success": True,
                "goal": asdict(goal),
                "acknowledgment": ack_message,
                "total_goals": len(user_profile['goals'])
            }
            
        except Exception as e:
            logger.error(f"Error adding goal for user {user_id}: {str(e)}")
            return {"success": False, "error": "Failed to add goal"}
    
    def update_goal_priorities(self, user_id: str, priority_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update the priority ranking of user goals"""
        try:
            user_profile = self.user_service.get_user_profile(user_id)
            if not user_profile or 'goals' not in user_profile:
                return {"success": False, "error": "No goals found for user"}
            
            # Update priorities
            for update in priority_updates:
                goal_type = update.get('goal_type')
                new_priority = update.get('priority')
                label = update.get('label')  # For custom goals
                
                for goal in user_profile['goals']:
                    if goal['goal_type'] == goal_type:
                        if goal_type == GoalType.CUSTOM.value and goal.get('label') != label:
                            continue
                        goal['priority'] = new_priority
                        goal['last_updated'] = datetime.utcnow().isoformat()
                        break
            
            # Save updated profile
            user_profile['last_updated'] = datetime.utcnow().isoformat()
            self.user_service.table.put_item(Item=user_profile)
            
            return {"success": True, "message": "Goal priorities updated successfully"}
            
        except Exception as e:
            logger.error(f"Error updating goal priorities for user {user_id}: {str(e)}")
            return {"success": False, "error": "Failed to update priorities"}
    
    def merge_goal_constraints(self, user_id: str) -> MergedConstraints:
        """Merge all user goals into a single constraint set with priority weighting"""
        try:
            user_profile = self.user_service.get_user_profile(user_id)
            if not user_profile or 'goals' not in user_profile:
                return MergedConstraints()  # Return empty constraints
            
            goals = [UserGoal(**goal_data) for goal_data in user_profile['goals']]
            merged = MergedConstraints()
            
            # Sort goals by priority (highest first)
            goals_by_priority = sorted(goals, key=lambda g: g.priority, reverse=True)
            
            # Process constraints in priority order
            for goal in goals_by_priority:
                self._merge_single_goal_constraints(merged, goal)
            
            return merged
            
        except Exception as e:
            logger.error(f"Error merging constraints for user {user_id}: {str(e)}")
            return MergedConstraints()
    
    def generate_ai_prompt_context(self, user_id: str) -> str:
        """Generate AI prompt context including all user goals with priorities"""
        try:
            user_profile = self.user_service.get_user_profile(user_id)
            if not user_profile or 'goals' not in user_profile:
                return ""
            
            goals = [UserGoal(**goal_data) for goal_data in user_profile['goals']]
            if not goals:
                return ""
            
            # Sort by priority
            goals_by_priority = sorted(goals, key=lambda g: g.priority, reverse=True)
            
            # Build context
            context_parts = ["User's nutrition goals (in priority order):"]
            
            for i, goal in enumerate(goals_by_priority, 1):
                if goal.goal_type == GoalType.CUSTOM.value:
                    goal_name = f"Custom: {goal.label}"
                    description = goal.constraints.get('description', 'Custom nutrition goal')
                else:
                    goal_def = self.goal_definitions.get(goal.goal_type, {})
                    goal_name = goal_def.get('name', goal.goal_type)
                    description = goal_def.get('description', '')
                
                priority_text = ["", "Low", "Medium", "High", "Critical"][goal.priority]
                context_parts.append(f"{i}. {goal_name} ({priority_text} priority) - {description}")
            
            # Add constraint summary
            merged_constraints = self.merge_goal_constraints(user_id)
            constraint_summary = self._summarize_constraints(merged_constraints)
            
            if constraint_summary:
                context_parts.append("\nMerged constraints:")
                context_parts.extend([f"• {item}" for item in constraint_summary])
            
            # Add conflict resolution guidance
            if len(goals) > 1:
                context_parts.append(f"\nWhen goals conflict, prioritize in the order listed above.")
                context_parts.append("Provide transparent trade-off explanations when compromises are needed.")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error generating AI context for user {user_id}: {str(e)}")
            return ""
    
    def handle_unknown_goal(self, user_id: str, goal_text: str) -> Dict[str, Any]:
        """Handle unrecognized goals with intelligent categorization and proxy mapping"""
        try:
            # Clean and normalize the goal text
            normalized_goal = goal_text.lower().strip()
            
            # Check if it matches any known custom goal proxies
            matched_proxy = None
            for known_goal, proxy_data in self.custom_goal_proxies.items():
                if self._text_similarity(normalized_goal, known_goal) > 0.7:
                    matched_proxy = known_goal
                    break
            
            if matched_proxy:
                # Use existing proxy
                constraints = self.custom_goal_proxies[matched_proxy].copy()
                description = constraints.pop('description', 'Custom nutrition goal')
                
                acknowledgment = f"I don't have a dedicated *{goal_text}* tracker, but I can {description}."
            else:
                # Create new custom goal with basic constraints
                constraints = self._infer_constraints_from_text(goal_text)
                acknowledgment = f"I'll track *{goal_text}* as a custom goal and adapt based on your feedback."
            
            # Add the goal
            result = self.add_user_goal(user_id, goal_text, priority=2)
            if result['success']:
                result['acknowledgment'] = acknowledgment
                result['is_new_custom_goal'] = matched_proxy is None
                
                # Log for analytics if it's a new goal type
                if matched_proxy is None:
                    self._log_new_custom_goal(goal_text, constraints)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling unknown goal '{goal_text}' for user {user_id}: {str(e)}")
            return {"success": False, "error": "Failed to process custom goal"}
    
    def get_trending_custom_goals(self, min_users: int = 5) -> List[Dict[str, Any]]:
        """Get custom goals that are trending across users for potential promotion"""
        # This would require analytics tracking - placeholder implementation
        return [
            {"label": "skin health", "user_count": 12, "success_rate": 0.85},
            {"label": "sleep", "user_count": 8, "success_rate": 0.90},
            {"label": "brain health", "user_count": 6, "success_rate": 0.78}
        ]
    
    def _parse_goal_input(self, goal_input: str) -> Dict[str, Any]:
        """Parse goal input to determine if it's standard or custom"""
        goal_lower = goal_input.lower().strip()
        
        # Check for standard goal matches
        for goal_type, definition in self.goal_definitions.items():
            goal_name = definition['name'].lower()
            if goal_lower in goal_name or goal_name in goal_lower:
                return {"is_standard": True, "goal_type": goal_type}
            
            # Check common aliases
            aliases = {
                GoalType.BUDGET.value: ["cheap", "affordable", "save money", "budget"],
                GoalType.MUSCLE_GAIN.value: ["build muscle", "gain muscle", "bulk", "protein"],
                GoalType.WEIGHT_LOSS.value: ["lose weight", "diet", "cut", "slim down"],
                GoalType.GUT_HEALTH.value: ["gut health", "digestion", "microbiome"],
                GoalType.ENERGY.value: ["energy", "fatigue", "tired"],
                GoalType.QUICK_MEALS.value: ["quick", "fast", "easy", "simple", "busy"]
            }
            
            if goal_type in aliases:
                for alias in aliases[goal_type]:
                    if alias in goal_lower:
                        return {"is_standard": True, "goal_type": goal_type}
        
        # Not a standard goal - treat as custom
        return {"is_standard": False, "label": goal_input}
    
    def _get_custom_goal_constraints(self, label: str) -> Dict[str, Any]:
        """Get constraints for a custom goal, using proxies when available"""
        label_lower = label.lower()
        
        # Check for known proxies
        for known_goal, proxy_data in self.custom_goal_proxies.items():
            if self._text_similarity(label_lower, known_goal) > 0.7:
                return proxy_data.copy()
        
        # Infer constraints from text if no proxy found
        return self._infer_constraints_from_text(label)
    
    def _infer_constraints_from_text(self, text: str) -> Dict[str, Any]:
        """Infer basic constraints from goal text using keyword analysis"""
        constraints = {"description": f"Custom goal focused on {text}"}
        text_lower = text.lower()
        
        # Health-related keywords
        if any(word in text_lower for word in ["health", "wellness", "immune", "recovery"]):
            constraints["emphasized_foods"] = ["nutrient_dense", "whole_foods", "vegetables"]
        
        # Performance keywords
        if any(word in text_lower for word in ["performance", "athletic", "endurance", "strength"]):
            constraints["protein_grams"] = 120
            constraints["emphasized_foods"] = ["lean_protein", "complex_carbs"]
        
        # Beauty/appearance keywords
        if any(word in text_lower for word in ["skin", "hair", "beauty", "appearance"]):
            constraints["emphasized_foods"] = ["antioxidant_rich", "omega3_foods"]
            constraints["required_nutrients"] = ["vitamin_c", "vitamin_e", "omega3"]
        
        # Mental health keywords
        if any(word in text_lower for word in ["mood", "stress", "mental", "brain", "focus"]):
            constraints["emphasized_foods"] = ["omega3_fish", "dark_chocolate", "nuts"]
            constraints["avoided_foods"] = ["refined_sugar", "alcohol"]
        
        return constraints
    
    def _merge_single_goal_constraints(self, merged: MergedConstraints, goal: UserGoal) -> None:
        """Merge a single goal's constraints into the merged constraint set"""
        constraints = goal.constraints
        priority_weight = goal.priority / 4.0  # Normalize to 0.25-1.0
        
        # Merge numeric constraints (taking stricter values for higher priority goals)
        numeric_fields = [
            ('daily_calories', 'daily_calories'),
            ('protein_grams', 'protein_grams'),
            ('fiber_grams', 'fiber_grams'),
            ('sodium_mg', 'sodium_mg'),
            ('added_sugar_grams', 'added_sugar_grams'),
            ('max_cost_per_meal', 'max_cost_per_meal'),
            ('weekly_budget', 'weekly_budget'),
            ('max_prep_time', 'max_prep_time')
        ]
        
        for merged_field, constraint_field in numeric_fields:
            if constraint_field in constraints:
                current_value = getattr(merged, merged_field)
                new_value = constraints[constraint_field]
                
                if current_value is None:
                    setattr(merged, merged_field, new_value)
                else:
                    # For limits/maximums, take the stricter (lower) value
                    if merged_field in ['sodium_mg', 'added_sugar_grams', 'max_cost_per_meal', 'max_prep_time']:
                        setattr(merged, merged_field, min(current_value, new_value))
                    # For targets/minimums, take weighted average favoring higher priority
                    else:
                        weighted_value = (current_value * (1 - priority_weight)) + (new_value * priority_weight)
                        setattr(merged, merged_field, int(weighted_value))
        
        # Merge boolean flags (OR logic for preferences)
        boolean_fields = ['quick_meal_preference', 'whole_grain_preference', 'anti_inflammatory_focus']
        for field in boolean_fields:
            if constraints.get(field, False):
                setattr(merged, field, True)
        
        # Merge lists (union with deduplication)
        list_fields = ['emphasized_foods', 'avoided_foods', 'required_nutrients']
        for field in list_fields:
            if field in constraints:
                current_list = getattr(merged, field)
                new_items = constraints[field]
                combined = list(set(current_list + new_items))
                setattr(merged, field, combined)
        
        # Handle percentage fields
        if 'plant_protein_percentage' in constraints:
            current_pct = merged.plant_protein_percentage
            new_pct = constraints['plant_protein_percentage']
            
            if current_pct is None:
                merged.plant_protein_percentage = new_pct
            else:
                # Take weighted average
                merged.plant_protein_percentage = (current_pct * (1 - priority_weight)) + (new_pct * priority_weight)
    
    def _summarize_constraints(self, constraints: MergedConstraints) -> List[str]:
        """Generate human-readable constraint summary"""
        summary = []
        
        if constraints.daily_calories:
            summary.append(f"Target ~{constraints.daily_calories} calories daily")
        
        if constraints.protein_grams:
            summary.append(f"Aim for {constraints.protein_grams}g protein")
        
        if constraints.max_cost_per_meal:
            summary.append(f"Keep meals under ${constraints.max_cost_per_meal:.2f}")
        
        if constraints.max_prep_time:
            summary.append(f"Limit prep time to {constraints.max_prep_time} minutes")
        
        if constraints.emphasized_foods:
            foods = ", ".join(constraints.emphasized_foods[:3])
            summary.append(f"Emphasize: {foods}")
        
        if constraints.avoided_foods:
            foods = ", ".join(constraints.avoided_foods[:3])
            summary.append(f"Minimize: {foods}")
        
        return summary
    
    def _generate_goal_acknowledgment(self, goal: UserGoal, all_goals: List[Dict]) -> str:
        """Generate conversational acknowledgment for goal addition"""
        if goal.goal_type == GoalType.CUSTOM.value:
            goal_name = goal.label
        else:
            goal_name = self.goal_definitions[goal.goal_type]['name']
        
        if len(all_goals) == 1:
            return f"Got it! I'll focus on {goal_name.lower()} in your meal plans."
        
        # Multiple goals - create compound acknowledgment
        goal_names = []
        for g in all_goals:
            if g['goal_type'] == GoalType.CUSTOM.value:
                goal_names.append(g['label'])
            else:
                goal_names.append(self.goal_definitions[g['goal_type']]['name'].lower())
        
        if len(goal_names) == 2:
            return f"Perfect! I'll balance {goal_names[0]} + {goal_names[1]} in your meals."
        else:
            formatted_goals = ", ".join(goal_names[:-1]) + f", and {goal_names[-1]}"
            return f"Got it 👍 I'll optimize for {formatted_goals}. Since you have multiple goals, which should I prioritize most?"
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity score (could be enhanced with proper NLP)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _log_new_custom_goal(self, goal_text: str, constraints: Dict[str, Any]) -> None:
        """Log new custom goals for analytics and trend analysis"""
        # This would typically write to an analytics service
        logger.info(f"New custom goal logged: '{goal_text}' with constraints: {constraints}")
