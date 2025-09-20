"""Anonymization service for crew data privacy and k-anonymity."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from statistics import mean, median

from .models import CrewPulse, PulseMetric, PulseMetricType, Reflection


@dataclass
class AnonymizationConfig:
    """Configuration for anonymization policies."""
    
    min_bucket_size: int = 5  # k-anonymity threshold
    max_reflection_length: int = 50  # Characters for reflection excerpts
    pii_patterns: List[str] = None
    
    def __post_init__(self) -> None:
        """Initialize default PII patterns."""
        if self.pii_patterns is None:
            self.pii_patterns = [
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
                r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Full names (basic pattern)
            ]


class AnonymizationService:
    """Service for applying privacy protection and k-anonymity to crew data."""
    
    def __init__(self, config: Optional[AnonymizationConfig] = None) -> None:
        self._config = config or AnonymizationConfig()
        self._compiled_patterns = [re.compile(pattern) for pattern in self._config.pii_patterns]
    
    def anonymize_crew_pulse(
        self, 
        crew_id: str,
        metrics: List[PulseMetric],
        reflections: List[Reflection]
    ) -> CrewPulse:
        """Create anonymized crew pulse with k-anonymity protection."""
        
        # Check if we have enough data for anonymization
        unique_users = len(set(metric.user_id for metric in metrics))
        if unique_users < self._config.min_bucket_size:
            # Not enough users for safe anonymization
            return self._create_suppressed_pulse(crew_id, unique_users)
        
        # Aggregate metrics by type
        aggregated_metrics = self._aggregate_metrics(metrics)
        
        # Anonymize reflections
        anonymized_reflections = self._anonymize_reflections(reflections)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(metrics, reflections)
        
        # Calculate challenge completion rate (placeholder)
        challenge_completion_rate = 0.0  # TODO: Implement when challenges are tracked
        
        return CrewPulse(
            crew_id=crew_id,
            pulse_date=metrics[0].timestamp if metrics else None,
            total_active_members=unique_users,
            metrics=aggregated_metrics,
            engagement_score=engagement_score,
            recent_reflections=anonymized_reflections,
            challenge_completion_rate=challenge_completion_rate,
            anonymization_applied=True
        )
    
    def _create_suppressed_pulse(self, crew_id: str, member_count: int) -> CrewPulse:
        """Create suppressed pulse for crews below k-anonymity threshold."""
        from datetime import datetime
        
        return CrewPulse(
            crew_id=crew_id,
            pulse_date=datetime.now(),
            total_active_members=member_count,
            metrics={},  # Suppressed due to low member count
            engagement_score=0.0,
            recent_reflections=["Data suppressed - crew size below privacy threshold"],
            challenge_completion_rate=0.0,
            anonymization_applied=True
        )
    
    def _aggregate_metrics(self, metrics: List[PulseMetric]) -> Dict[PulseMetricType, Dict[str, float]]:
        """Aggregate metrics by type with statistical measures."""
        
        aggregated = {}
        
        # Group metrics by type
        metrics_by_type: Dict[PulseMetricType, List[float]] = {}
        for metric in metrics:
            if metric.metric_type not in metrics_by_type:
                metrics_by_type[metric.metric_type] = []
            metrics_by_type[metric.metric_type].append(metric.value)
        
        # Calculate statistics for each metric type
        for metric_type, values in metrics_by_type.items():
            if len(values) >= self._config.min_bucket_size:
                aggregated[metric_type] = {
                    "avg": round(mean(values), 2),
                    "median": round(median(values), 2),
                    "count": len(values),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2)
                }
            # Skip metrics with insufficient data points
        
        return aggregated
    
    def _anonymize_reflections(self, reflections: List[Reflection]) -> List[str]:
        """Anonymize and excerpt recent reflections."""
        
        if len(reflections) < self._config.min_bucket_size:
            return ["Reflections suppressed - insufficient data for anonymization"]
        
        anonymized = []
        
        for reflection in reflections[-10:]:  # Take last 10 reflections
            # Redact PII
            cleaned_content = self._redact_pii(reflection.content)
            
            # Create excerpt
            excerpt = self._create_excerpt(cleaned_content)
            
            # Add to anonymized list
            if excerpt and len(excerpt.strip()) > 10:  # Ensure meaningful content
                anonymized.append(excerpt)
        
        # Shuffle to prevent temporal correlation
        import random
        random.shuffle(anonymized)
        
        return anonymized[:5]  # Return max 5 excerpts
    
    def _redact_pii(self, text: str) -> str:
        """Remove personally identifiable information from text."""
        
        cleaned = text
        
        # Apply PII pattern redaction
        for pattern in self._compiled_patterns:
            cleaned = pattern.sub("[REDACTED]", cleaned)
        
        # Additional manual redactions
        cleaned = re.sub(r'\bI\b', 'Someone', cleaned)  # Replace first person
        cleaned = re.sub(r'\bmy\b', 'their', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bme\b', 'them', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _create_excerpt(self, text: str) -> str:
        """Create a short excerpt from reflection text."""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        if len(text) <= self._config.max_reflection_length:
            return text
        
        # Try to cut at sentence boundary
        sentences = text.split('.')
        excerpt = ""
        
        for sentence in sentences:
            if len(excerpt + sentence + ".") <= self._config.max_reflection_length:
                excerpt += sentence + "."
            else:
                break
        
        if excerpt:
            return excerpt
        
        # Fall back to character limit with ellipsis
        return text[:self._config.max_reflection_length - 3] + "..."
    
    def _calculate_engagement_score(
        self, 
        metrics: List[PulseMetric], 
        reflections: List[Reflection]
    ) -> float:
        """Calculate composite engagement score (0-100)."""
        
        if not metrics and not reflections:
            return 0.0
        
        score_components = []
        
        # Metrics participation score (0-40 points)
        if metrics:
            unique_metric_users = len(set(m.user_id for m in metrics))
            metrics_score = min(40, unique_metric_users * 8)  # 8 points per user, max 40
            score_components.append(metrics_score)
        
        # Reflection participation score (0-30 points)
        if reflections:
            unique_reflection_users = len(set(r.user_id for r in reflections))
            reflection_score = min(30, unique_reflection_users * 6)  # 6 points per user, max 30
            score_components.append(reflection_score)
        
        # Consistency bonus (0-30 points) - placeholder for future implementation
        consistency_score = 20  # Default moderate consistency
        score_components.append(consistency_score)
        
        return min(100.0, sum(score_components))
    
    def is_safe_to_share(
        self, 
        user_count: int, 
        data_points: int
    ) -> bool:
        """Check if data meets k-anonymity requirements for sharing."""
        
        return (
            user_count >= self._config.min_bucket_size and
            data_points >= self._config.min_bucket_size
        )
    
    def redact_user_content(self, content: str) -> str:
        """Redact PII from user-generated content."""
        return self._redact_pii(content)


__all__ = [
    "AnonymizationConfig",
    "AnonymizationService",
]
