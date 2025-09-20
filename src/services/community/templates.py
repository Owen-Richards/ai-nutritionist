"""SMS template engine for community engagement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlencode

from .models import Crew, CrewType, PulseMetric


class TemplateType(Enum):
    """Types of SMS templates for community engagement."""
    
    DAILY_PULSE = "daily_pulse"
    WEEKLY_CHALLENGE = "weekly_challenge"
    REFLECTION_PROMPT = "reflection_prompt"
    CREW_WELCOME = "crew_welcome"
    PULSE_SUMMARY = "pulse_summary"
    CHALLENGE_REMINDER = "challenge_reminder"
    MILESTONE_CELEBRATION = "milestone_celebration"


@dataclass
class SMSTemplate:
    """SMS message template with variable substitution."""
    
    template_id: str
    template_type: TemplateType
    crew_type: Optional[CrewType]
    message_text: str
    variables: List[str]
    web_card_url_template: Optional[str] = None
    max_length: int = 160
    
    def render(self, context: Dict[str, str], base_url: str = "https://app.ainutritionist.com") -> "RenderedSMS":
        """Render template with context variables."""
        message = self.message_text
        
        # Substitute variables
        for var in self.variables:
            if var in context:
                message = message.replace(f"{{{var}}}", context[var])
        
        # Generate web card URL if template exists
        web_url = None
        if self.web_card_url_template:
            web_path = self.web_card_url_template.format(**context)
            query_params = {
                "template": self.template_id,
                "crew": context.get("crew_id", ""),
                "utm_source": "sms",
                "utm_medium": "community"
            }
            web_url = f"{base_url}{web_path}?{urlencode(query_params)}"
            
            # Append short URL to message if it fits
            if len(message) + len(web_url) + 1 <= self.max_length:
                message = f"{message} {web_url}"
        
        return RenderedSMS(
            message=message,
            web_url=web_url,
            template_id=self.template_id,
            estimated_length=len(message)
        )


@dataclass
class RenderedSMS:
    """Rendered SMS message ready for delivery."""
    
    message: str
    web_url: Optional[str]
    template_id: str
    estimated_length: int
    
    def is_valid(self) -> bool:
        """Check if rendered message is valid for SMS delivery."""
        return 0 < self.estimated_length <= 160 and bool(self.message.strip())


class SMSTemplateEngine:
    """Template engine for generating personalized community SMS messages."""
    
    def __init__(self) -> None:
        self._templates: Dict[str, SMSTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self) -> None:
        """Load default SMS templates for community features."""
        
        # Daily pulse templates
        self.register_template(SMSTemplate(
            template_id="daily_pulse_general",
            template_type=TemplateType.DAILY_PULSE,
            crew_type=None,
            message_text="🌟 How are you feeling today, {first_name}? Rate your energy (1-5) and share with your {crew_name} crew!",
            variables=["first_name", "crew_name"],
            web_card_url_template="/pulse/{crew_id}/checkin"
        ))
        
        self.register_template(SMSTemplate(
            template_id="daily_pulse_weight_loss",
            template_type=TemplateType.DAILY_PULSE,
            crew_type=CrewType.WEIGHT_LOSS,
            message_text="💪 {first_name}, how did yesterday's meals make you feel? Your {crew_name} crew wants to know!",
            variables=["first_name", "crew_name"],
            web_card_url_template="/pulse/{crew_id}/checkin"
        ))
        
        # Weekly challenge templates
        self.register_template(SMSTemplate(
            template_id="weekly_challenge_general",
            template_type=TemplateType.WEEKLY_CHALLENGE,
            crew_type=None,
            message_text="🎯 This week's {crew_name} challenge: {challenge_title}. {completion_rate}% of crew completed!",
            variables=["crew_name", "challenge_title", "completion_rate"],
            web_card_url_template="/challenges/{challenge_id}"
        ))
        
        # Reflection prompts
        self.register_template(SMSTemplate(
            template_id="reflection_prompt_weekly",
            template_type=TemplateType.REFLECTION_PROMPT,
            crew_type=None,
            message_text="📝 Weekly reflection time! What's one nutrition win from this week? Share with {crew_name}",
            variables=["crew_name"],
            web_card_url_template="/reflections/weekly/{crew_id}"
        ))
        
        # Crew welcome
        self.register_template(SMSTemplate(
            template_id="crew_welcome",
            template_type=TemplateType.CREW_WELCOME,
            crew_type=None,
            message_text="🎉 Welcome to {crew_name}, {first_name}! You're now part of {member_count} people supporting each other.",
            variables=["crew_name", "first_name", "member_count"],
            web_card_url_template="/crews/{crew_id}/welcome"
        ))
        
        # Pulse summary
        self.register_template(SMSTemplate(
            template_id="pulse_summary",
            template_type=TemplateType.PULSE_SUMMARY,
            crew_type=None,
            message_text="📊 {crew_name} weekly pulse: {avg_energy}/5 energy, {adherence_rate}% meal plan adherence. You're doing great!",
            variables=["crew_name", "avg_energy", "adherence_rate"],
            web_card_url_template="/crews/{crew_id}/pulse"
        ))
    
    def register_template(self, template: SMSTemplate) -> None:
        """Register a new SMS template."""
        self._templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> Optional[SMSTemplate]:
        """Retrieve template by ID."""
        return self._templates.get(template_id)
    
    def get_templates_by_type(self, template_type: TemplateType) -> List[SMSTemplate]:
        """Get all templates of a specific type."""
        return [t for t in self._templates.values() if t.template_type == template_type]
    
    def render_daily_pulse(
        self, 
        user_name: str, 
        crew: Crew,
        member_count: int
    ) -> RenderedSMS:
        """Render daily pulse message for a user."""
        
        # Select appropriate template based on crew type
        template_id = f"daily_pulse_{crew.crew_type.value}" if crew.crew_type else "daily_pulse_general"
        template = self.get_template(template_id) or self.get_template("daily_pulse_general")
        
        context = {
            "first_name": user_name,
            "crew_name": crew.name,
            "crew_id": crew.crew_id,
            "member_count": str(member_count)
        }
        
        return template.render(context)
    
    def render_weekly_challenge(
        self,
        crew: Crew,
        challenge_title: str,
        completion_rate: float,
        challenge_id: str
    ) -> RenderedSMS:
        """Render weekly challenge message."""
        
        template = self.get_template("weekly_challenge_general")
        
        context = {
            "crew_name": crew.name,
            "challenge_title": challenge_title,
            "completion_rate": str(int(completion_rate * 100)),
            "challenge_id": challenge_id,
            "crew_id": crew.crew_id
        }
        
        return template.render(context)
    
    def render_reflection_prompt(self, crew: Crew) -> RenderedSMS:
        """Render reflection prompt message."""
        
        template = self.get_template("reflection_prompt_weekly")
        
        context = {
            "crew_name": crew.name,
            "crew_id": crew.crew_id
        }
        
        return template.render(context)
    
    def render_crew_welcome(
        self,
        user_name: str,
        crew: Crew,
        member_count: int
    ) -> RenderedSMS:
        """Render welcome message for new crew member."""
        
        template = self.get_template("crew_welcome")
        
        context = {
            "first_name": user_name,
            "crew_name": crew.name,
            "member_count": str(member_count),
            "crew_id": crew.crew_id
        }
        
        return template.render(context)
    
    def render_pulse_summary(
        self,
        crew: Crew,
        avg_energy: float,
        adherence_rate: float
    ) -> RenderedSMS:
        """Render crew pulse summary message."""
        
        template = self.get_template("pulse_summary")
        
        context = {
            "crew_name": crew.name,
            "avg_energy": f"{avg_energy:.1f}",
            "adherence_rate": str(int(adherence_rate * 100)),
            "crew_id": crew.crew_id
        }
        
        return template.render(context)


__all__ = [
    "TemplateType",
    "SMSTemplate",
    "RenderedSMS", 
    "SMSTemplateEngine",
]
