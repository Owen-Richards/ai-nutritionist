"""
Nutrition Calculator - Advanced nutrition calculations and analysis
Consolidates: nutrition_calculation_service.py, macro_calculator_service.py
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)

@dataclass
class MacroTargets:
    """Macro nutrient targets"""
    calories: float
    protein_g: float
    protein_percent: float
    carbs_g: float
    carbs_percent: float
    fat_g: float
    fat_percent: float

@dataclass
class NutritionAnalysis:
    """Comprehensive nutrition analysis"""
    macro_breakdown: Dict[str, float]
    micronutrient_adequacy: Dict[str, float]
    nutrition_quality_score: float
    recommendations: List[str]
    deficiencies: List[str]
    excesses: List[str]

class NutritionCalculator:
    """
    Advanced nutrition calculator for macro/micro calculations,
    BMR, TDEE, and nutritional analysis.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rda_values = self._initialize_rda_values()
        self.activity_multipliers = self._initialize_activity_multipliers()
    
    def calculate_bmr(
        self, 
        weight_kg: float, 
        height_cm: float, 
        age_years: int, 
        sex: str
    ) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor equation
        
        Args:
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            age_years: Age in years
            sex: 'male' or 'female'
            
        Returns:
            BMR in calories per day
        """
        try:
            if sex.lower() == 'male':
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years) + 5
            else:  # female
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years) - 161
            
            self.logger.info(f"Calculated BMR: {bmr:.0f} calories/day")
            return bmr
            
        except Exception as e:
            self.logger.error(f"Error calculating BMR: {str(e)}")
            return 1500  # Safe fallback
    
    def calculate_tdee(
        self, 
        bmr: float, 
        activity_level: str,
        exercise_calories: float = 0
    ) -> float:
        """
        Calculate Total Daily Energy Expenditure
        
        Args:
            bmr: Basal Metabolic Rate
            activity_level: Activity level (sedentary, light, moderate, active, very_active)
            exercise_calories: Additional exercise calories
            
        Returns:
            TDEE in calories per day
        """
        try:
            multiplier = self.activity_multipliers.get(activity_level.lower(), 1.2)
            tdee = bmr * multiplier + exercise_calories
            
            self.logger.info(f"Calculated TDEE: {tdee:.0f} calories/day")
            return tdee
            
        except Exception as e:
            self.logger.error(f"Error calculating TDEE: {str(e)}")
            return bmr * 1.5  # Safe fallback
    
    def calculate_macro_targets(
        self, 
        tdee: float, 
        goal: str = "maintain",
        protein_preference: str = "moderate",
        carb_preference: str = "moderate"
    ) -> MacroTargets:
        """
        Calculate personalized macro nutrient targets
        
        Args:
            tdee: Total Daily Energy Expenditure
            goal: 'lose_weight', 'maintain', 'gain_weight', 'muscle_gain'
            protein_preference: 'low', 'moderate', 'high'
            carb_preference: 'low', 'moderate', 'high'
            
        Returns:
            Calculated macro targets
        """
        try:
            # Adjust calories based on goal
            calorie_adjustments = {
                'lose_weight': -500,
                'maintain': 0,
                'gain_weight': 300,
                'muscle_gain': 500
            }
            
            target_calories = tdee + calorie_adjustments.get(goal, 0)
            
            # Protein targets (g per kg body weight approximated from calories)
            protein_ratios = {
                'low': 0.15,      # 15% of calories
                'moderate': 0.20,  # 20% of calories
                'high': 0.30      # 30% of calories
            }
            
            # Carb targets
            carb_ratios = {
                'low': 0.20,      # 20% of calories (keto-like)
                'moderate': 0.45,  # 45% of calories
                'high': 0.65      # 65% of calories
            }
            
            protein_percent = protein_ratios.get(protein_preference, 0.20)
            carb_percent = carb_ratios.get(carb_preference, 0.45)
            fat_percent = 1.0 - protein_percent - carb_percent
            
            # Ensure fat is at least 20% for essential fatty acids
            if fat_percent < 0.20:
                fat_percent = 0.20
                remaining = 1.0 - fat_percent
                protein_percent = protein_percent * remaining / (protein_percent + carb_percent)
                carb_percent = remaining - protein_percent
            
            # Calculate grams
            protein_g = (target_calories * protein_percent) / 4  # 4 cal/g
            carb_g = (target_calories * carb_percent) / 4       # 4 cal/g
            fat_g = (target_calories * fat_percent) / 9         # 9 cal/g
            
            targets = MacroTargets(
                calories=target_calories,
                protein_g=protein_g,
                protein_percent=protein_percent * 100,
                carbs_g=carb_g,
                carbs_percent=carb_percent * 100,
                fat_g=fat_g,
                fat_percent=fat_percent * 100
            )
            
            self.logger.info(f"Calculated macro targets: {target_calories:.0f} cal, "
                           f"{protein_g:.0f}g protein, {carb_g:.0f}g carbs, {fat_g:.0f}g fat")
            return targets
            
        except Exception as e:
            self.logger.error(f"Error calculating macro targets: {str(e)}")
            # Return safe defaults
            return MacroTargets(
                calories=2000, protein_g=150, protein_percent=30,
                carbs_g=225, carbs_percent=45, fat_g=56, fat_percent=25
            )
    
    def analyze_nutrition_quality(
        self, 
        nutrition_data: Dict[str, float],
        targets: Optional[MacroTargets] = None
    ) -> NutritionAnalysis:
        """
        Analyze nutrition quality and adequacy
        
        Args:
            nutrition_data: Actual nutrition intake data
            targets: Target nutrition values for comparison
            
        Returns:
            Comprehensive nutrition analysis
        """
        try:
            analysis = NutritionAnalysis(
                macro_breakdown={},
                micronutrient_adequacy={},
                nutrition_quality_score=0,
                recommendations=[],
                deficiencies=[],
                excesses=[]
            )
            
            # Calculate macro breakdown
            total_calories = nutrition_data.get('calories', 0)
            if total_calories > 0:
                protein_cal = nutrition_data.get('protein', 0) * 4
                carb_cal = nutrition_data.get('carbs', 0) * 4
                fat_cal = nutrition_data.get('fat', 0) * 9
                
                analysis.macro_breakdown = {
                    'protein_percent': (protein_cal / total_calories) * 100,
                    'carb_percent': (carb_cal / total_calories) * 100,
                    'fat_percent': (fat_cal / total_calories) * 100,
                    'fiber_per_1000_cal': (nutrition_data.get('fiber', 0) / total_calories) * 1000
                }
            
            # Analyze micronutrient adequacy
            analysis.micronutrient_adequacy = self._analyze_micronutrients(nutrition_data)
            
            # Calculate overall quality score
            analysis.nutrition_quality_score = self._calculate_quality_score(nutrition_data, analysis)
            
            # Generate recommendations
            analysis.recommendations = self._generate_nutrition_recommendations(
                nutrition_data, analysis, targets
            )
            
            # Identify deficiencies and excesses
            analysis.deficiencies, analysis.excesses = self._identify_imbalances(
                nutrition_data, targets
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing nutrition quality: {str(e)}")
            return NutritionAnalysis(
                macro_breakdown={}, micronutrient_adequacy={},
                nutrition_quality_score=50, recommendations=[],
                deficiencies=[], excesses=[]
            )
    
    def calculate_nutrient_density(
        self, 
        nutrition_data: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate nutrient density scores
        
        Args:
            nutrition_data: Nutrition information
            
        Returns:
            Nutrient density scores per 100 calories
        """
        try:
            calories = nutrition_data.get('calories', 1)
            if calories == 0:
                calories = 1
            
            density_scores = {}
            
            # Protein density
            protein = nutrition_data.get('protein', 0)
            density_scores['protein_density'] = (protein / calories) * 100
            
            # Fiber density
            fiber = nutrition_data.get('fiber', 0)
            density_scores['fiber_density'] = (fiber / calories) * 100
            
            # Micronutrient density (simplified)
            vitamin_c = nutrition_data.get('vitamin_c', 0)
            iron = nutrition_data.get('iron', 0)
            calcium = nutrition_data.get('calcium', 0)
            
            density_scores['micronutrient_density'] = (
                (vitamin_c + iron + calcium) / calories
            ) * 100
            
            # Overall nutrient density score
            density_scores['overall_density'] = (
                density_scores['protein_density'] * 0.4 +
                density_scores['fiber_density'] * 0.3 +
                density_scores['micronutrient_density'] * 0.3
            )
            
            return density_scores
            
        except Exception as e:
            self.logger.error(f"Error calculating nutrient density: {str(e)}")
            return {'overall_density': 50.0}
    
    def calculate_glycemic_load(
        self, 
        carbs_g: float, 
        glycemic_index: int = 55
    ) -> float:
        """
        Calculate glycemic load for carbohydrate intake
        
        Args:
            carbs_g: Grams of carbohydrates
            glycemic_index: GI of the carbohydrate source
            
        Returns:
            Glycemic load value
        """
        try:
            glycemic_load = (carbs_g * glycemic_index) / 100
            
            # Interpretation:
            # Low GL: ≤10
            # Medium GL: 11-19
            # High GL: ≥20
            
            return glycemic_load
            
        except Exception as e:
            self.logger.error(f"Error calculating glycemic load: {str(e)}")
            return 10.0  # Safe default
    
    def calculate_protein_completeness(
        self, 
        amino_acid_profile: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate protein completeness based on amino acid profile
        
        Args:
            amino_acid_profile: Essential amino acid content
            
        Returns:
            Protein quality analysis
        """
        try:
            # Essential amino acid requirements (mg per g of protein)
            eaa_requirements = {
                'histidine': 18,
                'isoleucine': 25,
                'leucine': 55,
                'lysine': 51,
                'methionine_cysteine': 25,
                'phenylalanine_tyrosine': 47,
                'threonine': 27,
                'tryptophan': 7,
                'valine': 32
            }
            
            # Calculate amino acid scores
            aa_scores = {}
            for aa, requirement in eaa_requirements.items():
                actual = amino_acid_profile.get(aa, 0)
                score = min(100, (actual / requirement) * 100)
                aa_scores[aa] = score
            
            # Protein digestibility corrected amino acid score (PDCAAS)
            limiting_aa = min(aa_scores.values()) if aa_scores else 0
            digestibility = 95  # Assume 95% digestibility for mixed protein
            pdcaas = (limiting_aa / 100) * (digestibility / 100) * 100
            
            return {
                'amino_acid_scores': aa_scores,
                'limiting_amino_acid': min(aa_scores, key=aa_scores.get) if aa_scores else None,
                'pdcaas': pdcaas,
                'protein_quality': 'high' if pdcaas >= 80 else 'moderate' if pdcaas >= 60 else 'low'
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating protein completeness: {str(e)}")
            return {'pdcaas': 70, 'protein_quality': 'moderate'}
    
    def _analyze_micronutrients(self, nutrition_data: Dict[str, float]) -> Dict[str, float]:
        """Analyze micronutrient adequacy against RDA"""
        adequacy_scores = {}
        
        for nutrient, rda_value in self.rda_values.items():
            actual_intake = nutrition_data.get(nutrient, 0)
            if rda_value > 0:
                adequacy_percent = (actual_intake / rda_value) * 100
                adequacy_scores[nutrient] = min(150, adequacy_percent)  # Cap at 150%
        
        return adequacy_scores
    
    def _calculate_quality_score(
        self, 
        nutrition_data: Dict[str, float], 
        analysis: NutritionAnalysis
    ) -> float:
        """Calculate overall nutrition quality score"""
        scores = []
        
        # Macro balance score
        macro_breakdown = analysis.macro_breakdown
        protein_percent = macro_breakdown.get('protein_percent', 0)
        carb_percent = macro_breakdown.get('carb_percent', 0)
        fat_percent = macro_breakdown.get('fat_percent', 0)
        
        # Ideal ranges: Protein 15-35%, Carbs 30-65%, Fat 20-35%
        protein_score = 100 if 15 <= protein_percent <= 35 else max(0, 100 - abs(protein_percent - 25))
        carb_score = 100 if 30 <= carb_percent <= 65 else max(0, 100 - abs(carb_percent - 47.5))
        fat_score = 100 if 20 <= fat_percent <= 35 else max(0, 100 - abs(fat_percent - 27.5))
        
        macro_score = (protein_score + carb_score + fat_score) / 3
        scores.append(macro_score * 0.4)  # 40% weight
        
        # Micronutrient adequacy score
        adequacy_scores = list(analysis.micronutrient_adequacy.values())
        if adequacy_scores:
            micro_score = sum(min(100, score) for score in adequacy_scores) / len(adequacy_scores)
            scores.append(micro_score * 0.3)  # 30% weight
        
        # Fiber adequacy
        fiber = nutrition_data.get('fiber', 0)
        calories = nutrition_data.get('calories', 1)
        fiber_per_1000 = (fiber / calories) * 1000 if calories > 0 else 0
        fiber_score = min(100, (fiber_per_1000 / 14) * 100)  # 14g per 1000 cal target
        scores.append(fiber_score * 0.2)  # 20% weight
        
        # Added sugar penalty
        sugar = nutrition_data.get('sugar', 0)
        sugar_cal = sugar * 4
        total_cal = nutrition_data.get('calories', 1)
        sugar_percent = (sugar_cal / total_cal) * 100 if total_cal > 0 else 0
        sugar_penalty = max(0, sugar_percent - 10) * 2  # Penalty for >10% sugar calories
        scores.append(max(0, 100 - sugar_penalty) * 0.1)  # 10% weight
        
        return sum(scores) if scores else 50
    
    def _generate_nutrition_recommendations(
        self, 
        nutrition_data: Dict[str, float], 
        analysis: NutritionAnalysis,
        targets: Optional[MacroTargets]
    ) -> List[str]:
        """Generate personalized nutrition recommendations"""
        recommendations = []
        
        # Protein recommendations
        protein_percent = analysis.macro_breakdown.get('protein_percent', 0)
        if protein_percent < 15:
            recommendations.append("Increase protein intake - aim for lean meats, eggs, legumes")
        elif protein_percent > 35:
            recommendations.append("Consider reducing protein intake for better macro balance")
        
        # Fiber recommendations
        fiber = nutrition_data.get('fiber', 0)
        if fiber < 25:
            recommendations.append("Increase fiber intake with vegetables, fruits, and whole grains")
        
        # Hydration (if tracked)
        if 'water_ml' in nutrition_data and nutrition_data['water_ml'] < 2000:
            recommendations.append("Increase water intake to at least 2 liters per day")
        
        # Micronutrient recommendations
        low_nutrients = [
            nutrient for nutrient, score in analysis.micronutrient_adequacy.items()
            if score < 50
        ]
        if low_nutrients:
            recommendations.append(f"Consider foods rich in: {', '.join(low_nutrients)}")
        
        return recommendations
    
    def _identify_imbalances(
        self, 
        nutrition_data: Dict[str, float], 
        targets: Optional[MacroTargets]
    ) -> Tuple[List[str], List[str]]:
        """Identify nutritional deficiencies and excesses"""
        deficiencies = []
        excesses = []
        
        if targets:
            # Check macro targets
            if nutrition_data.get('protein', 0) < targets.protein_g * 0.8:
                deficiencies.append('protein')
            elif nutrition_data.get('protein', 0) > targets.protein_g * 1.3:
                excesses.append('protein')
            
            if nutrition_data.get('calories', 0) < targets.calories * 0.8:
                deficiencies.append('calories')
            elif nutrition_data.get('calories', 0) > targets.calories * 1.2:
                excesses.append('calories')
        
        # Check micronutrients against RDA
        for nutrient, rda_value in self.rda_values.items():
            actual = nutrition_data.get(nutrient, 0)
            if actual < rda_value * 0.5:  # Less than 50% of RDA
                deficiencies.append(nutrient)
            elif actual > rda_value * 2:  # More than 200% of RDA
                excesses.append(nutrient)
        
        return deficiencies, excesses
    
    def _initialize_rda_values(self) -> Dict[str, float]:
        """Initialize RDA values for key nutrients"""
        return {
            'vitamin_c': 90,      # mg
            'vitamin_d': 15,      # mcg
            'vitamin_b12': 2.4,   # mcg
            'folate': 400,        # mcg
            'iron': 8,            # mg
            'calcium': 1000,      # mg
            'magnesium': 400,     # mg
            'zinc': 11,           # mg
            'potassium': 3500,    # mg
            'fiber': 25           # g
        }
    
    def _initialize_activity_multipliers(self) -> Dict[str, float]:
        """Initialize activity level multipliers for TDEE"""
        return {
            'sedentary': 1.2,      # Little/no exercise
            'light': 1.375,        # Light exercise 1-3 days/week
            'moderate': 1.55,      # Moderate exercise 3-5 days/week
            'active': 1.725,       # Heavy exercise 6-7 days/week
            'very_active': 1.9     # Very heavy exercise, physical job
        }
