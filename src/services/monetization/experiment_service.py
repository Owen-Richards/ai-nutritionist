"""Monetization experiments framework for Track E4.

Handles price point testing, trial length variations, nudge frequency optimization.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ...models.monetization import BillingInterval, SubscriptionTier

logger = logging.getLogger(__name__)


class ExperimentType(str, Enum):
    """Types of monetization experiments."""
    PRICE_TESTING = "price_testing"
    TRIAL_LENGTH = "trial_length"
    NUDGE_FREQUENCY = "nudge_frequency"
    DISCOUNT_TESTING = "discount_testing"
    PAYWALL_COPY = "paywall_copy"
    ONBOARDING_FLOW = "onboarding_flow"


class ExperimentStatus(str, Enum):
    """Experiment lifecycle states."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GuardrailType(str, Enum):
    """Types of experiment guardrails."""
    MIN_CONVERSION_RATE = "min_conversion_rate"
    MAX_CHURN_RATE = "max_churn_rate"
    MIN_REVENUE_PER_USER = "min_revenue_per_user"
    MAX_SMS_FREQUENCY = "max_sms_frequency"
    MIN_TRIAL_DAYS = "min_trial_days"
    MAX_PRICE_INCREASE = "max_price_increase"


class ExperimentGuardrail(BaseModel):
    """Guardrail for experiment safety."""
    type: GuardrailType
    threshold: float
    description: str
    active: bool = True
    
    def check_violation(self, metric_value: float) -> bool:
        """Check if metric violates guardrail."""
        if not self.active:
            return False
        
        if self.type in [GuardrailType.MIN_CONVERSION_RATE, 
                        GuardrailType.MIN_REVENUE_PER_USER,
                        GuardrailType.MIN_TRIAL_DAYS]:
            return metric_value < self.threshold
        else:  # MAX thresholds
            return metric_value > self.threshold


class ExperimentVariant(BaseModel):
    """Experiment variant configuration."""
    id: str
    name: str
    description: str
    traffic_allocation: float = Field(ge=0, le=1)  # 0.0 to 1.0
    
    # Configuration specific to experiment type
    config: Dict = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    is_control: bool = False


class ExperimentConfig(BaseModel):
    """Complete experiment configuration."""
    id: str = Field(default_factory=lambda: f"exp_{uuid4().hex[:8]}")
    name: str
    description: str
    type: ExperimentType
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Experiment design
    variants: List[ExperimentVariant]
    guardrails: List[ExperimentGuardrail] = Field(default_factory=list)
    
    # Targeting
    target_user_segments: List[str] = Field(default_factory=list)
    target_subscription_tiers: List[SubscriptionTier] = Field(default_factory=list)
    
    # Traffic control
    traffic_percentage: float = Field(default=1.0, ge=0, le=1)  # Overall experiment traffic
    
    # Timeline
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    
    # Success metrics
    primary_metric: str = "conversion_rate"
    secondary_metrics: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "system"
    
    def get_control_variant(self) -> Optional[ExperimentVariant]:
        """Get the control variant."""
        for variant in self.variants:
            if variant.is_control:
                return variant
        return None
    
    def get_variant_by_id(self, variant_id: str) -> Optional[ExperimentVariant]:
        """Get variant by ID."""
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        return None


class ExperimentResult(BaseModel):
    """Results for an experiment variant."""
    experiment_id: str
    variant_id: str
    
    # Sample size
    users_assigned: int = 0
    users_completed: int = 0
    
    # Primary metrics
    conversions: int = 0
    conversion_rate: float = 0.0
    
    # Revenue metrics
    total_revenue: float = 0.0
    revenue_per_user: float = 0.0
    
    # Engagement metrics
    retention_d7: float = 0.0
    retention_d30: float = 0.0
    churn_rate: float = 0.0
    
    # Time-based metrics
    time_to_conversion_hours: Optional[float] = None
    
    # Statistical significance
    confidence_level: float = 0.95
    is_significant: bool = False
    p_value: Optional[float] = None
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)


class ExperimentService:
    """Service for managing monetization experiments."""
    
    def __init__(self):
        # In-memory storage for demo (use database in production)
        self.experiments: Dict[str, ExperimentConfig] = {}
        self.results: Dict[str, List[ExperimentResult]] = {}
        self.user_assignments: Dict[UUID, Dict[str, str]] = {}  # user_id -> {experiment_id: variant_id}
        
        # Initialize default experiments
        self._initialize_default_experiments()
    
    def _initialize_default_experiments(self) -> None:
        """Initialize default monetization experiments."""
        
        # Price testing experiment
        price_experiment = ExperimentConfig(
            id="price_test_q4_2024",
            name="Plus Tier Price Testing Q4 2024",
            description="Test optimal pricing for Plus tier to maximize revenue",
            type=ExperimentType.PRICE_TESTING,
            variants=[
                ExperimentVariant(
                    id="price_control",
                    name="Control - $12.99",
                    description="Current pricing",
                    traffic_allocation=0.4,
                    is_control=True,
                    config={
                        "monthly_price_usd": 12.99,
                        "yearly_price_usd": 129.90,
                        "discount_percent": 17
                    }
                ),
                ExperimentVariant(
                    id="price_low",
                    name="Lower Price - $9.99",
                    description="25% price reduction to test demand elasticity",
                    traffic_allocation=0.3,
                    config={
                        "monthly_price_usd": 9.99,
                        "yearly_price_usd": 99.90,
                        "discount_percent": 17
                    }
                ),
                ExperimentVariant(
                    id="price_high",
                    name="Higher Price - $14.99",
                    description="Premium positioning test",
                    traffic_allocation=0.3,
                    config={
                        "monthly_price_usd": 14.99,
                        "yearly_price_usd": 149.90,
                        "discount_percent": 17
                    }
                )
            ],
            guardrails=[
                ExperimentGuardrail(
                    type=GuardrailType.MIN_CONVERSION_RATE,
                    threshold=0.03,  # Minimum 3% conversion rate
                    description="Stop experiment if conversion drops below 3%"
                ),
                ExperimentGuardrail(
                    type=GuardrailType.MAX_CHURN_RATE,
                    threshold=0.15,  # Maximum 15% churn rate
                    description="Stop experiment if churn exceeds 15%"
                )
            ],
            target_subscription_tiers=[SubscriptionTier.FREE],
            primary_metric="revenue_per_user",
            secondary_metrics=["conversion_rate", "retention_d30"]
        )
        
        # Trial length experiment
        trial_experiment = ExperimentConfig(
            id="trial_length_2024",
            name="Trial Length Optimization",
            description="Compare 7-day vs 14-day trial periods",
            type=ExperimentType.TRIAL_LENGTH,
            variants=[
                ExperimentVariant(
                    id="trial_7_days",
                    name="7-Day Trial",
                    description="Standard 7-day trial period",
                    traffic_allocation=0.5,
                    is_control=True,
                    config={"trial_days": 7}
                ),
                ExperimentVariant(
                    id="trial_14_days",
                    name="14-Day Trial",
                    description="Extended 14-day trial period",
                    traffic_allocation=0.5,
                    config={"trial_days": 14}
                )
            ],
            guardrails=[
                ExperimentGuardrail(
                    type=GuardrailType.MIN_TRIAL_DAYS,
                    threshold=7,
                    description="Minimum trial period"
                )
            ],
            target_subscription_tiers=[SubscriptionTier.FREE],
            primary_metric="conversion_rate",
            secondary_metrics=["time_to_conversion_hours", "retention_d7"]
        )
        
        # Nudge frequency experiment
        nudge_experiment = ExperimentConfig(
            id="nudge_frequency_2024",
            name="SMS Nudge Frequency Optimization",
            description="Optimize nudge frequency for engagement vs. fatigue",
            type=ExperimentType.NUDGE_FREQUENCY,
            variants=[
                ExperimentVariant(
                    id="nudge_low",
                    name="Conservative - 2/week",
                    description="Low frequency to minimize fatigue",
                    traffic_allocation=0.33,
                    config={"nudges_per_week": 2, "max_daily": 1}
                ),
                ExperimentVariant(
                    id="nudge_medium",
                    name="Moderate - 3/week",
                    description="Current frequency",
                    traffic_allocation=0.34,
                    is_control=True,
                    config={"nudges_per_week": 3, "max_daily": 1}
                ),
                ExperimentVariant(
                    id="nudge_high",
                    name="Aggressive - 5/week",
                    description="Higher frequency for engagement",
                    traffic_allocation=0.33,
                    config={"nudges_per_week": 5, "max_daily": 1}
                )
            ],
            guardrails=[
                ExperimentGuardrail(
                    type=GuardrailType.MAX_SMS_FREQUENCY,
                    threshold=1.0,  # Maximum 1 SMS per day
                    description="Never exceed 1 SMS per day per user"
                ),
                ExperimentGuardrail(
                    type=GuardrailType.MAX_CHURN_RATE,
                    threshold=0.10,  # 10% churn threshold
                    description="Stop if churn exceeds 10%"
                )
            ],
            target_subscription_tiers=[SubscriptionTier.FREE, SubscriptionTier.PREMIUM],
            primary_metric="retention_d7",
            secondary_metrics=["conversion_rate", "churn_rate"]
        )
        
        self.experiments[price_experiment.id] = price_experiment
        self.experiments[trial_experiment.id] = trial_experiment
        self.experiments[nudge_experiment.id] = nudge_experiment
    
    def assign_user_to_experiment(self, user_id: UUID, experiment_id: str) -> Optional[str]:
        """Assign user to experiment variant."""
        experiment = self.experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.ACTIVE:
            return None
        
        # Check if user already assigned
        if user_id in self.user_assignments:
            existing_assignment = self.user_assignments[user_id].get(experiment_id)
            if existing_assignment:
                return existing_assignment
        
        # Check if user is in experiment traffic
        if not self._is_user_in_experiment_traffic(user_id, experiment):
            return None
        
        # Assign variant using deterministic hashing
        variant_id = self._assign_variant(user_id, experiment)
        
        # Store assignment
        if user_id not in self.user_assignments:
            self.user_assignments[user_id] = {}
        self.user_assignments[user_id][experiment_id] = variant_id
        
        logger.info(f"Assigned user {user_id} to experiment {experiment_id}, variant {variant_id}")
        return variant_id
    
    def get_user_variant(self, user_id: UUID, experiment_id: str) -> Optional[str]:
        """Get user's assigned variant for experiment."""
        if user_id in self.user_assignments:
            return self.user_assignments[user_id].get(experiment_id)
        return None
    
    def get_experiment_config_for_user(self, user_id: UUID, 
                                     experiment_type: ExperimentType) -> Optional[Dict]:
        """Get experiment configuration for user."""
        # Find active experiment of given type
        active_experiment = None
        for exp in self.experiments.values():
            if exp.type == experiment_type and exp.status == ExperimentStatus.ACTIVE:
                active_experiment = exp
                break
        
        if not active_experiment:
            return None
        
        # Get user's variant
        variant_id = self.assign_user_to_experiment(user_id, active_experiment.id)
        if not variant_id:
            return None
        
        variant = active_experiment.get_variant_by_id(variant_id)
        if not variant:
            return None
        
        return {
            "experiment_id": active_experiment.id,
            "variant_id": variant_id,
            "config": variant.config
        }
    
    def track_experiment_event(self, user_id: UUID, experiment_id: str,
                             event_type: str, event_data: Optional[Dict] = None) -> None:
        """Track experiment event for analysis."""
        variant_id = self.get_user_variant(user_id, experiment_id)
        if not variant_id:
            return
        
        event = {
            "user_id": str(user_id),
            "experiment_id": experiment_id,
            "variant_id": variant_id,
            "event_type": event_type,
            "event_data": event_data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Experiment event: {json.dumps(event)}")
        # In production, send to analytics pipeline
    
    def check_guardrails(self, experiment_id: str) -> List[Dict]:
        """Check experiment guardrails and return violations."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return []
        
        violations = []
        results = self.results.get(experiment_id, [])
        
        for guardrail in experiment.guardrails:
            if not guardrail.active:
                continue
            
            # Calculate current metric value (simplified)
            current_value = self._calculate_guardrail_metric(guardrail.type, results)
            
            if guardrail.check_violation(current_value):
                violations.append({
                    "guardrail_type": guardrail.type.value,
                    "threshold": guardrail.threshold,
                    "current_value": current_value,
                    "description": guardrail.description,
                    "severity": "high" if current_value > guardrail.threshold * 1.5 else "medium"
                })
        
        return violations
    
    def pause_experiment(self, experiment_id: str, reason: str) -> bool:
        """Pause experiment (usually due to guardrail violations)."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return False
        
        experiment.status = ExperimentStatus.PAUSED
        
        logger.warning(f"Paused experiment {experiment_id}: {reason}")
        # In production, send alerts to team
        return True
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        """Get comprehensive experiment results."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return {"error": "Experiment not found"}
        
        results = self.results.get(experiment_id, [])
        guardrail_violations = self.check_guardrails(experiment_id)
        
        # Calculate statistical significance (simplified)
        significance_results = self._calculate_statistical_significance(results)
        
        return {
            "experiment": {
                "id": experiment.id,
                "name": experiment.name,
                "type": experiment.type.value,
                "status": experiment.status.value,
                "start_date": experiment.start_date.isoformat() if experiment.start_date else None,
                "primary_metric": experiment.primary_metric
            },
            "variants": [
                {
                    "id": variant.id,
                    "name": variant.name,
                    "is_control": variant.is_control,
                    "traffic_allocation": variant.traffic_allocation,
                    "config": variant.config
                }
                for variant in experiment.variants
            ],
            "results": [result.dict() for result in results],
            "guardrail_violations": guardrail_violations,
            "statistical_significance": significance_results,
            "recommendation": self._generate_recommendation(experiment, results, significance_results)
        }
    
    def _is_user_in_experiment_traffic(self, user_id: UUID, 
                                     experiment: ExperimentConfig) -> bool:
        """Check if user is in experiment traffic percentage."""
        import hashlib
        
        # Use deterministic hashing for consistent assignment
        hash_input = f"{experiment.id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        hash_ratio = (hash_value % 10000) / 10000.0  # 0.0000 to 0.9999
        
        return hash_ratio < experiment.traffic_percentage
    
    def _assign_variant(self, user_id: UUID, experiment: ExperimentConfig) -> str:
        """Assign variant using traffic allocation."""
        import hashlib
        
        # Use different hash for variant assignment
        hash_input = f"{experiment.id}:variant:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        hash_ratio = (hash_value % 10000) / 10000.0
        
        cumulative_allocation = 0.0
        for variant in experiment.variants:
            cumulative_allocation += variant.traffic_allocation
            if hash_ratio < cumulative_allocation:
                return variant.id
        
        # Fallback to control variant
        control = experiment.get_control_variant()
        return control.id if control else experiment.variants[0].id
    
    def _calculate_guardrail_metric(self, guardrail_type: GuardrailType,
                                  results: List[ExperimentResult]) -> float:
        """Calculate current value for guardrail metric."""
        if not results:
            return 0.0
        
        # Get non-control results for comparison
        non_control_results = [r for r in results if not self._is_control_variant(r.variant_id)]
        if not non_control_results:
            return 0.0
        
        if guardrail_type == GuardrailType.MIN_CONVERSION_RATE:
            return min(r.conversion_rate for r in non_control_results)
        elif guardrail_type == GuardrailType.MAX_CHURN_RATE:
            return max(r.churn_rate for r in non_control_results)
        elif guardrail_type == GuardrailType.MIN_REVENUE_PER_USER:
            return min(r.revenue_per_user for r in non_control_results)
        else:
            return 0.0
    
    def _is_control_variant(self, variant_id: str) -> bool:
        """Check if variant is a control variant."""
        for exp in self.experiments.values():
            variant = exp.get_variant_by_id(variant_id)
            if variant:
                return variant.is_control
        return False
    
    def _calculate_statistical_significance(self, results: List[ExperimentResult]) -> Dict:
        """Calculate statistical significance (simplified)."""
        if len(results) < 2:
            return {"is_significant": False, "reason": "Insufficient variants"}
        
        # Placeholder for proper statistical testing
        # In production, use proper statistical tests (t-test, chi-square, etc.)
        control_result = None
        test_results = []
        
        for result in results:
            if self._is_control_variant(result.variant_id):
                control_result = result
            else:
                test_results.append(result)
        
        if not control_result or not test_results:
            return {"is_significant": False, "reason": "Missing control or test variants"}
        
        # Simplified significance check (placeholder)
        significant_variants = []
        for test_result in test_results:
            # Simple threshold-based check (replace with proper statistical test)
            if abs(test_result.conversion_rate - control_result.conversion_rate) > 0.01:
                significant_variants.append({
                    "variant_id": test_result.variant_id,
                    "improvement": test_result.conversion_rate - control_result.conversion_rate,
                    "confidence": 0.95  # Placeholder
                })
        
        return {
            "is_significant": len(significant_variants) > 0,
            "significant_variants": significant_variants,
            "control_variant": control_result.variant_id,
            "method": "simplified_threshold"  # Placeholder
        }
    
    def _generate_recommendation(self, experiment: ExperimentConfig,
                               results: List[ExperimentResult],
                               significance: Dict) -> str:
        """Generate experiment recommendation."""
        if not significance.get("is_significant"):
            return "Continue experiment - no significant differences detected yet"
        
        if experiment.type == ExperimentType.PRICE_TESTING:
            # Find best performing variant by revenue
            best_variant = max(results, key=lambda r: r.revenue_per_user)
            return f"Recommend implementing variant '{best_variant.variant_id}' - highest revenue per user"
        
        elif experiment.type == ExperimentType.TRIAL_LENGTH:
            # Find best conversion rate
            best_variant = max(results, key=lambda r: r.conversion_rate)
            return f"Recommend implementing variant '{best_variant.variant_id}' - highest conversion rate"
        
        else:
            return "Review results with product team for implementation decision"


# Export main classes
__all__ = [
    "ExperimentType",
    "ExperimentStatus",
    "GuardrailType",
    "ExperimentGuardrail",
    "ExperimentVariant", 
    "ExperimentConfig",
    "ExperimentResult",
    "ExperimentService"
]
