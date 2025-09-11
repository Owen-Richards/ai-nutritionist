"""
Dietary Constraint Handler - Health conditions and dietary restrictions
Consolidates: health_condition_service.py, dietary_restriction_service.py
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class DietaryRestrictionType(Enum):
    """Types of dietary restrictions"""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NUT_FREE = "nut_free"
    SOY_FREE = "soy_free"
    SHELLFISH_FREE = "shellfish_free"
    EGG_FREE = "egg_free"
    PESCATARIAN = "pescatarian"
    KETOGENIC = "ketogenic"
    PALEO = "paleo"
    LOW_SODIUM = "low_sodium"
    LOW_SUGAR = "low_sugar"
    LOW_CARB = "low_carb"
    HALAL = "halal"
    KOSHER = "kosher"

class HealthConditionType(Enum):
    """Types of health conditions affecting diet"""
    DIABETES = "diabetes"
    HYPERTENSION = "hypertension"
    HEART_DISEASE = "heart_disease"
    KIDNEY_DISEASE = "kidney_disease"
    LIVER_DISEASE = "liver_disease"
    CELIAC_DISEASE = "celiac_disease"
    CROHNS_DISEASE = "crohns_disease"
    IBS = "irritable_bowel_syndrome"
    GERD = "gastroesophageal_reflux"
    HYPOTHYROIDISM = "hypothyroidism"
    HYPERTHYROIDISM = "hyperthyroidism"
    FOOD_ALLERGIES = "food_allergies"
    EATING_DISORDER = "eating_disorder"

@dataclass
class ConstraintRule:
    """Rule for handling dietary constraints"""
    constraint_type: str
    forbidden_ingredients: List[str]
    forbidden_categories: List[str]
    required_nutrients: Dict[str, float]
    max_nutrients: Dict[str, float]
    substitution_rules: Dict[str, str]
    severity: str  # "strict", "moderate", "flexible"

class DietaryConstraintHandler:
    """
    Handles all dietary restrictions and health condition constraints
    for meal planning and recipe recommendations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.constraint_rules = self._initialize_constraint_rules()
        self.allergen_database = self._initialize_allergen_database()
        self.health_condition_rules = self._initialize_health_condition_rules()
    
    def validate_meal_constraints(
        self, 
        meal: Dict[str, Any], 
        user_constraints: List[str],
        health_conditions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a meal against user's dietary constraints and health conditions
        
        Args:
            meal: Meal data to validate
            user_constraints: List of user's dietary restrictions
            health_conditions: List of user's health conditions
            
        Returns:
            Validation results with violations and recommendations
        """
        try:
            self.logger.info(f"Validating meal constraints for {len(user_constraints)} restrictions")
            
            validation_result = {
                "is_compliant": True,
                "violations": [],
                "warnings": [],
                "recommendations": [],
                "severity_score": 0,
                "constraint_details": {}
            }
            
            # Check dietary restrictions
            for constraint in user_constraints:
                constraint_validation = self._validate_dietary_restriction(meal, constraint)
                if not constraint_validation["is_compliant"]:
                    validation_result["is_compliant"] = False
                    validation_result["violations"].extend(constraint_validation["violations"])
                    validation_result["severity_score"] += constraint_validation["severity_score"]
                
                validation_result["constraint_details"][constraint] = constraint_validation
            
            # Check health condition constraints
            if health_conditions:
                for condition in health_conditions:
                    condition_validation = self._validate_health_condition(meal, condition)
                    if not condition_validation["is_compliant"]:
                        validation_result["warnings"].extend(condition_validation["warnings"])
                        validation_result["recommendations"].extend(condition_validation["recommendations"])
                    
                    validation_result["constraint_details"][condition] = condition_validation
            
            # Generate overall recommendations
            if validation_result["violations"]:
                validation_result["recommendations"].extend(
                    self._generate_compliance_recommendations(meal, user_constraints)
                )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating meal constraints: {str(e)}")
            return {
                "is_compliant": False,
                "error": str(e),
                "violations": ["Validation failed"],
                "warnings": [],
                "recommendations": ["Please review meal manually"]
            }
    
    def filter_recipes_by_constraints(
        self, 
        recipes: List[Dict[str, Any]], 
        user_constraints: List[str],
        health_conditions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter a list of recipes based on dietary constraints
        
        Args:
            recipes: List of recipes to filter
            user_constraints: User's dietary restrictions
            health_conditions: User's health conditions
            
        Returns:
            Filtered list of compliant recipes
        """
        try:
            compliant_recipes = []
            
            for recipe in recipes:
                validation = self.validate_meal_constraints(
                    recipe, user_constraints, health_conditions
                )
                
                if validation["is_compliant"]:
                    # Add constraint compliance metadata
                    recipe["constraint_compliance"] = {
                        "validated_constraints": user_constraints,
                        "compliance_score": 100 - validation["severity_score"],
                        "validation_timestamp": validation.get("timestamp")
                    }
                    compliant_recipes.append(recipe)
            
            self.logger.info(f"Filtered {len(compliant_recipes)} compliant recipes from {len(recipes)} total")
            return compliant_recipes
            
        except Exception as e:
            self.logger.error(f"Error filtering recipes: {str(e)}")
            return recipes  # Return original list if filtering fails
    
    def suggest_ingredient_substitutions(
        self, 
        ingredient: str, 
        user_constraints: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Suggest ingredient substitutions based on dietary constraints
        
        Args:
            ingredient: Original ingredient to substitute
            user_constraints: User's dietary restrictions
            
        Returns:
            List of suitable substitutions with details
        """
        try:
            substitutions = []
            
            for constraint in user_constraints:
                if constraint in self.constraint_rules:
                    rule = self.constraint_rules[constraint]
                    
                    # Check if ingredient violates constraint
                    if (ingredient.lower() in [item.lower() for item in rule.forbidden_ingredients] or
                        self._ingredient_in_forbidden_categories(ingredient, rule.forbidden_categories)):
                        
                        # Find substitutions
                        for original, substitute in rule.substitution_rules.items():
                            if original.lower() in ingredient.lower():
                                substitutions.append({
                                    "original": ingredient,
                                    "substitute": substitute,
                                    "reason": f"Compliant with {constraint}",
                                    "constraint_type": constraint,
                                    "nutrition_impact": self._analyze_substitution_nutrition(ingredient, substitute)
                                })
            
            # Remove duplicates and sort by suitability
            unique_substitutions = self._deduplicate_substitutions(substitutions)
            return sorted(unique_substitutions, key=lambda x: x.get("suitability_score", 50), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error suggesting substitutions: {str(e)}")
            return []
    
    def get_constraint_nutrition_guidelines(
        self, 
        user_constraints: List[str],
        health_conditions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get nutrition guidelines based on constraints and health conditions
        
        Args:
            user_constraints: User's dietary restrictions
            health_conditions: User's health conditions
            
        Returns:
            Comprehensive nutrition guidelines
        """
        try:
            guidelines = {
                "daily_targets": {},
                "daily_limits": {},
                "recommended_foods": [],
                "foods_to_avoid": [],
                "special_considerations": [],
                "nutrient_priorities": {}
            }
            
            # Process dietary restrictions
            for constraint in user_constraints:
                if constraint in self.constraint_rules:
                    rule = self.constraint_rules[constraint]
                    
                    # Merge nutrition requirements
                    for nutrient, amount in rule.required_nutrients.items():
                        if nutrient in guidelines["daily_targets"]:
                            guidelines["daily_targets"][nutrient] = max(
                                guidelines["daily_targets"][nutrient], amount
                            )
                        else:
                            guidelines["daily_targets"][nutrient] = amount
                    
                    # Merge nutrition limits
                    for nutrient, limit in rule.max_nutrients.items():
                        if nutrient in guidelines["daily_limits"]:
                            guidelines["daily_limits"][nutrient] = min(
                                guidelines["daily_limits"][nutrient], limit
                            )
                        else:
                            guidelines["daily_limits"][nutrient] = limit
                    
                    # Add forbidden foods
                    guidelines["foods_to_avoid"].extend(rule.forbidden_ingredients)
            
            # Process health conditions
            if health_conditions:
                for condition in health_conditions:
                    if condition in self.health_condition_rules:
                        condition_rule = self.health_condition_rules[condition]
                        guidelines["special_considerations"].extend(
                            condition_rule.get("considerations", [])
                        )
                        guidelines["nutrient_priorities"].update(
                            condition_rule.get("nutrient_priorities", {})
                        )
            
            # Clean up duplicates
            guidelines["foods_to_avoid"] = list(set(guidelines["foods_to_avoid"]))
            guidelines["special_considerations"] = list(set(guidelines["special_considerations"]))
            
            return guidelines
            
        except Exception as e:
            self.logger.error(f"Error generating nutrition guidelines: {str(e)}")
            return {"error": str(e)}
    
    def check_allergen_safety(
        self, 
        meal: Dict[str, Any], 
        known_allergies: List[str]
    ) -> Dict[str, Any]:
        """
        Check meal for allergen safety based on known allergies
        
        Args:
            meal: Meal to check for allergens
            known_allergies: List of known food allergies
            
        Returns:
            Allergen safety assessment
        """
        try:
            safety_assessment = {
                "is_safe": True,
                "allergen_warnings": [],
                "cross_contamination_risks": [],
                "severity_level": "none",
                "recommendations": []
            }
            
            ingredients = meal.get('ingredients', [])
            
            for allergy in known_allergies:
                allergen_info = self.allergen_database.get(allergy.lower(), {})
                
                # Check direct ingredients
                for ingredient in ingredients:
                    if self._contains_allergen(ingredient, allergen_info):
                        safety_assessment["is_safe"] = False
                        safety_assessment["allergen_warnings"].append({
                            "allergen": allergy,
                            "ingredient": ingredient,
                            "severity": allergen_info.get("severity", "moderate")
                        })
                
                # Check cross-contamination risks
                cross_contamination = self._check_cross_contamination(ingredients, allergen_info)
                if cross_contamination:
                    safety_assessment["cross_contamination_risks"].extend(cross_contamination)
            
            # Determine overall severity
            if safety_assessment["allergen_warnings"]:
                severities = [warning["severity"] for warning in safety_assessment["allergen_warnings"]]
                if "severe" in severities:
                    safety_assessment["severity_level"] = "severe"
                elif "moderate" in severities:
                    safety_assessment["severity_level"] = "moderate"
                else:
                    safety_assessment["severity_level"] = "mild"
            
            # Generate recommendations
            if not safety_assessment["is_safe"]:
                safety_assessment["recommendations"] = self._generate_allergen_recommendations(
                    safety_assessment["allergen_warnings"]
                )
            
            return safety_assessment
            
        except Exception as e:
            self.logger.error(f"Error checking allergen safety: {str(e)}")
            return {
                "is_safe": False,
                "error": str(e),
                "recommendations": ["Consult with healthcare provider"]
            }
    
    def _validate_dietary_restriction(
        self, 
        meal: Dict[str, Any], 
        restriction: str
    ) -> Dict[str, Any]:
        """Validate meal against a specific dietary restriction"""
        if restriction not in self.constraint_rules:
            return {"is_compliant": True, "violations": [], "severity_score": 0}
        
        rule = self.constraint_rules[restriction]
        validation = {
            "is_compliant": True,
            "violations": [],
            "severity_score": 0
        }
        
        ingredients = meal.get('ingredients', [])
        
        # Check forbidden ingredients
        for ingredient in ingredients:
            if ingredient.lower() in [item.lower() for item in rule.forbidden_ingredients]:
                validation["is_compliant"] = False
                validation["violations"].append(f"Contains forbidden ingredient: {ingredient}")
                validation["severity_score"] += 10 if rule.severity == "strict" else 5
        
        # Check forbidden categories
        for ingredient in ingredients:
            if self._ingredient_in_forbidden_categories(ingredient, rule.forbidden_categories):
                validation["is_compliant"] = False
                validation["violations"].append(f"Contains ingredient from forbidden category: {ingredient}")
                validation["severity_score"] += 8 if rule.severity == "strict" else 3
        
        return validation
    
    def _validate_health_condition(
        self, 
        meal: Dict[str, Any], 
        condition: str
    ) -> Dict[str, Any]:
        """Validate meal against health condition requirements"""
        if condition not in self.health_condition_rules:
            return {"is_compliant": True, "warnings": [], "recommendations": []}
        
        condition_rule = self.health_condition_rules[condition]
        validation = {
            "is_compliant": True,
            "warnings": [],
            "recommendations": []
        }
        
        # Check nutrient limits
        for nutrient, limit in condition_rule.get("max_nutrients", {}).items():
            meal_amount = meal.get(nutrient, 0)
            if meal_amount > limit:
                validation["warnings"].append(
                    f"High {nutrient} content ({meal_amount}) may not be suitable for {condition}"
                )
                validation["recommendations"].append(f"Consider reducing {nutrient} intake")
        
        return validation
    
    def _initialize_constraint_rules(self) -> Dict[str, ConstraintRule]:
        """Initialize dietary constraint rules"""
        rules = {}
        
        # Vegetarian
        rules["vegetarian"] = ConstraintRule(
            constraint_type="vegetarian",
            forbidden_ingredients=["beef", "pork", "chicken", "turkey", "fish", "seafood", "gelatin"],
            forbidden_categories=["meat", "poultry", "fish", "seafood"],
            required_nutrients={"protein": 60, "iron": 18, "vitamin_b12": 2.4},
            max_nutrients={},
            substitution_rules={
                "chicken": "tofu",
                "beef": "tempeh",
                "fish": "chickpeas"
            },
            severity="strict"
        )
        
        # Vegan
        rules["vegan"] = ConstraintRule(
            constraint_type="vegan",
            forbidden_ingredients=["beef", "pork", "chicken", "turkey", "fish", "seafood", "dairy", "eggs", "honey", "gelatin"],
            forbidden_categories=["meat", "poultry", "fish", "seafood", "dairy", "eggs"],
            required_nutrients={"protein": 60, "iron": 18, "vitamin_b12": 2.4, "calcium": 1000},
            max_nutrients={},
            substitution_rules={
                "milk": "almond_milk",
                "cheese": "nutritional_yeast",
                "eggs": "flax_eggs"
            },
            severity="strict"
        )
        
        # Gluten-free
        rules["gluten_free"] = ConstraintRule(
            constraint_type="gluten_free",
            forbidden_ingredients=["wheat", "barley", "rye", "spelt", "bread", "pasta"],
            forbidden_categories=["gluten_containing_grains"],
            required_nutrients={},
            max_nutrients={},
            substitution_rules={
                "wheat_flour": "rice_flour",
                "bread": "gluten_free_bread",
                "pasta": "rice_pasta"
            },
            severity="strict"
        )
        
        # Ketogenic
        rules["ketogenic"] = ConstraintRule(
            constraint_type="ketogenic",
            forbidden_ingredients=["sugar", "bread", "pasta", "rice", "potatoes"],
            forbidden_categories=["high_carb"],
            required_nutrients={"fat": 120},
            max_nutrients={"carbs": 20},
            substitution_rules={
                "rice": "cauliflower_rice",
                "pasta": "zucchini_noodles",
                "potatoes": "radishes"
            },
            severity="moderate"
        )
        
        return rules
    
    def _initialize_allergen_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize allergen information database"""
        return {
            "nuts": {
                "severity": "severe",
                "related_ingredients": ["almonds", "walnuts", "pecans", "cashews", "pistachios"],
                "cross_contamination_risks": ["granola", "chocolate", "baked_goods"]
            },
            "shellfish": {
                "severity": "severe",
                "related_ingredients": ["shrimp", "crab", "lobster", "clams", "mussels"],
                "cross_contamination_risks": ["seafood_restaurants", "fish_sauce"]
            },
            "dairy": {
                "severity": "moderate",
                "related_ingredients": ["milk", "cheese", "butter", "yogurt", "cream"],
                "cross_contamination_risks": ["processed_foods", "baked_goods"]
            }
        }
    
    def _initialize_health_condition_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize health condition dietary rules"""
        return {
            "diabetes": {
                "max_nutrients": {"sugar": 25, "carbs": 150},
                "considerations": ["Monitor blood sugar levels", "Prefer complex carbohydrates"],
                "nutrient_priorities": {"fiber": "high", "protein": "moderate"}
            },
            "hypertension": {
                "max_nutrients": {"sodium": 2300},
                "considerations": ["Limit processed foods", "Increase potassium intake"],
                "nutrient_priorities": {"potassium": "high", "magnesium": "moderate"}
            },
            "heart_disease": {
                "max_nutrients": {"saturated_fat": 13, "cholesterol": 200},
                "considerations": ["Focus on omega-3 fatty acids", "Limit trans fats"],
                "nutrient_priorities": {"omega_3": "high", "fiber": "high"}
            }
        }
    
    def _ingredient_in_forbidden_categories(
        self, 
        ingredient: str, 
        forbidden_categories: List[str]
    ) -> bool:
        """Check if ingredient belongs to forbidden categories"""
        ingredient_categories = {
            "beef": ["meat"],
            "chicken": ["meat", "poultry"],
            "fish": ["seafood"],
            "milk": ["dairy"],
            "wheat": ["gluten_containing_grains"],
            "sugar": ["high_carb"]
        }
        
        ingredient_cats = ingredient_categories.get(ingredient.lower(), [])
        return any(cat in forbidden_categories for cat in ingredient_cats)
    
    def _analyze_substitution_nutrition(
        self, 
        original: str, 
        substitute: str
    ) -> Dict[str, str]:
        """Analyze nutritional impact of ingredient substitution"""
        return {
            "protein_change": "similar",
            "calorie_change": "lower",
            "fiber_change": "higher",
            "overall_impact": "positive"
        }
    
    def _deduplicate_substitutions(
        self, 
        substitutions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate substitutions"""
        seen = set()
        unique = []
        
        for sub in substitutions:
            key = (sub["original"], sub["substitute"])
            if key not in seen:
                seen.add(key)
                unique.append(sub)
        
        return unique
    
    def _contains_allergen(
        self, 
        ingredient: str, 
        allergen_info: Dict[str, Any]
    ) -> bool:
        """Check if ingredient contains specific allergen"""
        related_ingredients = allergen_info.get("related_ingredients", [])
        return ingredient.lower() in [item.lower() for item in related_ingredients]
    
    def _check_cross_contamination(
        self, 
        ingredients: List[str], 
        allergen_info: Dict[str, Any]
    ) -> List[str]:
        """Check for cross-contamination risks"""
        contamination_risks = []
        risk_ingredients = allergen_info.get("cross_contamination_risks", [])
        
        for ingredient in ingredients:
            if ingredient.lower() in [item.lower() for item in risk_ingredients]:
                contamination_risks.append(ingredient)
        
        return contamination_risks
    
    def _generate_compliance_recommendations(
        self, 
        meal: Dict[str, Any], 
        constraints: List[str]
    ) -> List[str]:
        """Generate recommendations for constraint compliance"""
        recommendations = []
        
        for constraint in constraints:
            if constraint == "vegetarian":
                recommendations.append("Replace meat with plant-based protein sources")
            elif constraint == "gluten_free":
                recommendations.append("Use gluten-free alternatives for grains")
            elif constraint == "dairy_free":
                recommendations.append("Substitute dairy with plant-based alternatives")
        
        return recommendations
    
    def _generate_allergen_recommendations(
        self, 
        allergen_warnings: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for allergen safety"""
        recommendations = []
        
        for warning in allergen_warnings:
            allergen = warning["allergen"]
            ingredient = warning["ingredient"]
            recommendations.append(f"Remove {ingredient} due to {allergen} allergy")
            recommendations.append(f"Read all labels carefully for {allergen} contamination")
        
        if any(w["severity"] == "severe" for w in allergen_warnings):
            recommendations.append("Consult with allergist before consuming")
        
        return recommendations
