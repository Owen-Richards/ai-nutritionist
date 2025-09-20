"""Community service layer for crew management and engagement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from .models import (
    Crew, CrewMember, Reflection, PulseMetric, CrewPulse, Challenge,
    CrewType, PulseMetricType, ReflectionType, MembershipStatus
)
from .repository import CommunityRepository
from .anonymization import AnonymizationService
from .templates import SMSTemplateEngine, RenderedSMS


@dataclass
class JoinCrewCommand:
    """Command for joining a crew."""
    
    user_id: str
    crew_id: str
    privacy_consent: bool
    notifications_enabled: bool = True


@dataclass
class LeaveCrewCommand:
    """Command for leaving a crew."""
    
    user_id: str
    crew_id: str
    reason: Optional[str] = None


@dataclass
class SubmitReflectionCommand:
    """Command for submitting a reflection."""
    
    user_id: str
    crew_id: str
    content: str
    reflection_type: ReflectionType
    mood_score: Optional[int] = None
    progress_rating: Optional[int] = None
    is_anonymous: bool = False


@dataclass
class SubmitPulseCommand:
    """Command for submitting pulse metrics."""
    
    user_id: str
    metrics: Dict[PulseMetricType, float]  # metric_type -> value


@dataclass
class CrewJoinResult:
    """Result of joining a crew."""
    
    success: bool
    member: Optional[CrewMember]
    welcome_message: Optional[RenderedSMS]
    error_message: Optional[str] = None


@dataclass
class ReflectionResult:
    """Result of submitting a reflection."""
    
    success: bool
    reflection: Optional[Reflection]
    error_message: Optional[str] = None


class CommunityService:
    """Service for managing community features and crew interactions."""
    
    def __init__(
        self,
        repository: CommunityRepository,
        anonymization_service: AnonymizationService,
        template_engine: SMSTemplateEngine = None
    ) -> None:
        self._repository = repository
        self._anonymization = anonymization_service
        self._templates = template_engine or SMSTemplateEngine()
    
    def join_crew(self, command: JoinCrewCommand, user_name: str) -> CrewJoinResult:
        """Add a user to a crew with proper validation and welcome message."""
        
        # Validate crew exists and is active
        crew = self._repository.get_crew(command.crew_id)
        if not crew:
            return CrewJoinResult(
                success=False,
                member=None,
                welcome_message=None,
                error_message="Crew not found"
            )
        
        if not crew.is_active:
            return CrewJoinResult(
                success=False,
                member=None,
                welcome_message=None,
                error_message="Crew is no longer active"
            )
        
        # Check if crew is at capacity
        current_members = self._repository.get_crew_members(command.crew_id)
        if len(current_members) >= crew.max_members:
            return CrewJoinResult(
                success=False,
                member=None,
                welcome_message=None,
                error_message="Crew is at maximum capacity"
            )
        
        # Check if user is already a member
        existing_member = next(
            (m for m in current_members if m.user_id == command.user_id),
            None
        )
        
        if existing_member and existing_member.is_active:
            return CrewJoinResult(
                success=False,
                member=None,
                welcome_message=None,
                error_message="Already a member of this crew"
            )
        
        # Create new membership
        member = CrewMember(
            member_id="",  # Will be auto-generated
            crew_id=command.crew_id,
            user_id=command.user_id,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
            notifications_enabled=command.notifications_enabled,
            privacy_consent=command.privacy_consent,
            consent_timestamp=datetime.now(timezone.utc) if command.privacy_consent else None
        )
        
        self._repository.add_crew_member(member)
        
        # Generate welcome message
        member_count = len(current_members) + 1
        welcome_message = self._templates.render_crew_welcome(
            user_name=user_name,
            crew=crew,
            member_count=member_count
        )
        
        return CrewJoinResult(
            success=True,
            member=member,
            welcome_message=welcome_message
        )
    
    def submit_reflection(self, command: SubmitReflectionCommand) -> ReflectionResult:
        """Submit a user reflection with content validation and PII protection."""
        
        # Validate user is crew member
        crew_members = self._repository.get_crew_members(command.crew_id)
        is_member = any(m.user_id == command.user_id and m.is_active for m in crew_members)
        
        if not is_member:
            return ReflectionResult(
                success=False,
                reflection=None,
                error_message="Must be an active crew member to submit reflections"
            )
        
        # Content validation
        if not command.content.strip():
            return ReflectionResult(
                success=False,
                reflection=None,
                error_message="Reflection content cannot be empty"
            )
        
        if len(command.content) > 1000:
            return ReflectionResult(
                success=False,
                reflection=None,
                error_message="Reflection content must be under 1000 characters"
            )
        
        # Apply PII redaction if needed
        content = command.content
        pii_redacted = False
        
        if not command.is_anonymous:
            # Check for PII and redact if found
            redacted_content = self._anonymization.redact_user_content(content)
            if redacted_content != content:
                content = redacted_content
                pii_redacted = True
        
        # Create reflection
        try:
            reflection = Reflection(
                reflection_id=uuid4().hex,
                user_id=command.user_id,
                crew_id=command.crew_id,
                reflection_type=command.reflection_type,
                content=content,
                mood_score=command.mood_score,
                progress_rating=command.progress_rating,
                created_at=datetime.now(),
                is_anonymous=command.is_anonymous,
                pii_redacted=pii_redacted
            )
            
            self._repository.save_reflection(reflection)
            
            return ReflectionResult(success=True, reflection=reflection)
            
        except ValueError as e:
            return ReflectionResult(
                success=False,
                reflection=None,
                error_message=str(e)
            )
    
    def submit_pulse_metrics(self, command: SubmitPulseCommand) -> bool:
        """Submit pulse metrics for a user."""
        
        timestamp = datetime.now()
        
        for metric_type, value in command.metrics.items():
            # Validate metric value
            if not 1.0 <= value <= 5.0:
                continue  # Skip invalid values
            
            metric = PulseMetric(
                metric_type=metric_type,
                value=value,
                user_id=command.user_id,
                timestamp=timestamp,
                is_anonymous=True  # Always anonymize pulse metrics
            )
            
            self._repository.save_pulse_metric(metric)
        
        return True
    
    def get_crew_pulse(self, crew_id: str, days_back: int = 7) -> Optional[CrewPulse]:
        """Get anonymized crew pulse data."""
        
        # Get crew to validate it exists
        crew = self._repository.get_crew(crew_id)
        if not crew:
            return None
        
        # Get recent data
        since = datetime.now() - timedelta(days=days_back)
        metrics = self._repository.get_crew_pulse_metrics(crew_id, since=since)
        reflections = self._repository.get_crew_reflections(crew_id, since=since, limit=20)
        
        # Apply anonymization
        return self._anonymization.anonymize_crew_pulse(crew_id, metrics, reflections)
    
    def get_user_crews(self, user_id: str) -> List[Crew]:
        """Get all crews a user belongs to."""
        return self._repository.get_user_crews(user_id)
    
    def list_available_crews(self, crew_type: Optional[CrewType] = None) -> List[Crew]:
        """List available crews for joining."""
        
        if crew_type:
            crews = self._repository.list_crews_by_type(crew_type)
        else:
            # In a real implementation, this would get all active crews
            # For now, return empty list as this needs proper implementation
            crews = []
        
        # Filter crews that aren't at capacity
        available_crews = []
        for crew in crews:
            member_count = len(self._repository.get_crew_members(crew.crew_id))
            if member_count < crew.max_members:
                available_crews.append(crew)
        
        return available_crews
    
    def generate_daily_pulse_message(self, user_id: str, crew_id: str, user_name: str) -> Optional[RenderedSMS]:
        """Generate daily pulse SMS for a user."""
        
        crew = self._repository.get_crew(crew_id)
        if not crew:
            return None
        
        # Check if user is crew member
        members = self._repository.get_crew_members(crew_id)
        is_member = any(m.user_id == user_id and m.is_active for m in members)
        
        if not is_member:
            return None
        
        return self._templates.render_daily_pulse(
            user_name=user_name,
            crew=crew,
            member_count=len(members)
        )
    
    def generate_weekly_summary(self, crew_id: str) -> Optional[RenderedSMS]:
        """Generate weekly summary message for a crew."""
        
        crew = self._repository.get_crew(crew_id)
        if not crew:
            return None
        
        # Get pulse data for summary
        pulse = self.get_crew_pulse(crew_id, days_back=7)
        if not pulse:
            return None
        
        # Extract key metrics for summary
        avg_energy = 3.5  # Default
        adherence_rate = 0.7  # Default
        
        if PulseMetricType.ENERGY_LEVEL in pulse.metrics:
            avg_energy = pulse.metrics[PulseMetricType.ENERGY_LEVEL].get("avg", 3.5)
        
        if PulseMetricType.ADHERENCE in pulse.metrics:
            adherence_rate = pulse.metrics[PulseMetricType.ADHERENCE].get("avg", 0.7) / 5.0
        
        return self._templates.render_pulse_summary(
            crew=crew,
            avg_energy=avg_energy,
            adherence_rate=adherence_rate
        )
    
    def create_crew(
        self,
        name: str,
        crew_type: CrewType,
        description: str,
        cohort_key: str,
        max_members: int = 50
    ) -> Crew:
        """Create a new crew."""
        
        crew = Crew(
            crew_id=uuid4().hex,
            name=name,
            crew_type=crew_type,
            description=description,
            cohort_key=cohort_key,
            created_at=datetime.now(),
            max_members=max_members,
            is_active=True
        )
        
        self._repository.save_crew(crew)
        return crew
    
    def leave_crew(self, command: LeaveCrewCommand) -> bool:
        """Handle user leaving a crew."""
        # Get user's membership
        membership = self._repository.get_user_membership(command.user_id, command.crew_id)
        if not membership:
            return False
        
        # Update status to LEFT
        from .models import MembershipStatus
        success = self._repository.update_member_status(membership.member_id, MembershipStatus.LEFT)
        
        # Log the departure reason if provided
        if success and command.reason:
            # Could log to analytics or audit trail
            pass
        
        return success
    
    def update_notification_preferences(self, user_id: str, crew_id: str, notifications_enabled: bool) -> bool:
        """Update user's notification preferences for a crew."""
        membership = self._repository.get_user_membership(user_id, crew_id)
        if not membership:
            return False
        
        return self._repository.update_member_preferences(
            membership.member_id, 
            notifications_enabled=notifications_enabled
        )
    
    def withdraw_privacy_consent(self, user_id: str, crew_id: str) -> bool:
        """Handle privacy consent withdrawal."""
        membership = self._repository.get_user_membership(user_id, crew_id)
        if not membership:
            return False
        
        # Update privacy consent
        success = self._repository.update_member_preferences(
            membership.member_id, 
            privacy_consent=False
        )
        
        if success:
            # Log consent change
            self._repository.log_consent_change(user_id, crew_id, "privacy_consent", False)
            
            # Anonymize user data
            self._anonymization_service.anonymize_user_data(user_id)
        
        return success
    
    def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (GDPR compliance)."""
        # Delete from repository
        repo_success = self._repository.delete_user_data(user_id)
        
        # Delete from anonymization service
        anon_success = self._anonymization_service.delete_user_data(user_id)
        
        return repo_success and anon_success


__all__ = [
    "JoinCrewCommand",
    "SubmitReflectionCommand", 
    "SubmitPulseCommand",
    "CrewJoinResult",
    "ReflectionResult",
    "CommunityService",
]
