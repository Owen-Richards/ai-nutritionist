"""
Message Templates Service

Manages message templates, personalization, and intelligent content generation
for various communication types and user segments.

Consolidates functionality from:
- message_personalization_service.py
- template_management_service.py
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import re
import random
from collections import defaultdict

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Types of message templates."""
    WELCOME = "welcome"
    MEAL_PLAN_DELIVERY = "meal_plan_delivery"
    GOAL_PROGRESS = "goal_progress"
    REMINDER = "reminder"
    FEEDBACK_REQUEST = "feedback_request"
    NUTRITION_TIP = "nutrition_tip"
    CONGRATULATIONS = "congratulations"
    ENCOURAGEMENT = "encouragement"
    WEEKLY_SUMMARY = "weekly_summary"
    SEASONAL_CONTENT = "seasonal_content"
    PROMOTIONAL = "promotional"
    SYSTEM_NOTIFICATION = "system_notification"


class PersonalizationLevel(Enum):
    """Levels of message personalization."""
    BASIC = "basic"          # Name only
    MODERATE = "moderate"    # Name + preferences
    ADVANCED = "advanced"    # Full context + behavior
    DYNAMIC = "dynamic"      # Real-time adaptation


class MessageTone(Enum):
    """Tone options for messages."""
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    ENCOURAGING = "encouraging"
    CASUAL = "casual"
    MOTIVATIONAL = "motivational"
    EDUCATIONAL = "educational"


@dataclass
class TemplateVariable:
    """Variable placeholder in message templates."""
    name: str
    variable_type: str  # text, number, date, list, conditional
    default_value: Any
    required: bool = True
    description: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageTemplate:
    """Comprehensive message template definition."""
    template_id: str
    name: str
    template_type: TemplateType
    content: str
    variables: List[TemplateVariable]
    personalization_level: PersonalizationLevel
    tone: MessageTone
    target_audience: List[str]
    usage_context: List[str]
    character_limit: int
    language: str = "en"
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    success_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class PersonalizationContext:
    """Context data for message personalization."""
    user_id: str
    user_name: Optional[str]
    preferences: Dict[str, Any]
    goals: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    behavioral_data: Dict[str, Any]
    location_data: Optional[Dict[str, Any]]
    time_context: Dict[str, Any]
    relationship_stage: str  # new, active, returning, at_risk


@dataclass
class GeneratedMessage:
    """Generated message with metadata."""
    message_id: str
    template_id: str
    user_id: str
    content: str
    personalization_level: PersonalizationLevel
    variables_used: Dict[str, Any]
    tone_adjustments: List[str]
    character_count: int
    generated_at: datetime = field(default_factory=datetime.utcnow)
    sent: bool = False
    engagement_predicted: Optional[float] = None


class MessageTemplatesService:
    """
    Advanced message templates service with AI-powered personalization.
    
    Features:
    - Dynamic template management with version control
    - Multi-level personalization (basic to advanced)
    - Contextual content adaptation based on user behavior
    - A/B testing framework for template optimization
    - Intelligent variable substitution and validation
    - Tone adaptation based on user preferences and relationship stage
    - Template performance analytics and optimization recommendations
    """

    def __init__(self):
        self.templates: Dict[str, MessageTemplate] = {}
        self.template_versions: Dict[str, List[MessageTemplate]] = defaultdict(list)
        self.personalization_cache: Dict[str, PersonalizationContext] = {}
        self.generated_messages: Dict[str, GeneratedMessage] = {}
        self.tone_adaptations = self._initialize_tone_adaptations()
        self.seasonal_content = self._initialize_seasonal_content()
        
        # Load default templates
        self._load_default_templates()

    def create_template(
        self,
        name: str,
        template_type: str,
        content: str,
        variables: List[Dict[str, Any]],
        personalization_level: str = "moderate",
        tone: str = "friendly",
        target_audience: Optional[List[str]] = None,
        usage_context: Optional[List[str]] = None,
        character_limit: int = 160
    ) -> Optional[MessageTemplate]:
        """
        Create new message template with validation and optimization.
        
        Args:
            name: Template name
            template_type: Type of template
            content: Template content with variables
            variables: Variable definitions
            personalization_level: Level of personalization
            tone: Message tone
            target_audience: Target audience segments
            usage_context: Usage contexts
            character_limit: Maximum character limit
            
        Returns:
            Created template or None if creation failed
        """
        try:
            # Generate template ID
            template_id = f"{template_type}_{name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
            
            # Parse and validate variables
            template_variables = []
            for var_data in variables:
                variable = TemplateVariable(
                    name=var_data['name'],
                    variable_type=var_data.get('type', 'text'),
                    default_value=var_data.get('default', ''),
                    required=var_data.get('required', True),
                    description=var_data.get('description', ''),
                    validation_rules=var_data.get('validation', {})
                )
                template_variables.append(variable)
            
            # Validate template content
            if not self._validate_template_content(content, template_variables):
                logger.error(f"Template content validation failed for {name}")
                return None
            
            # Create template
            template = MessageTemplate(
                template_id=template_id,
                name=name,
                template_type=TemplateType(template_type.lower()),
                content=content,
                variables=template_variables,
                personalization_level=PersonalizationLevel(personalization_level.lower()),
                tone=MessageTone(tone.lower()),
                target_audience=target_audience or ["general"],
                usage_context=usage_context or ["general"],
                character_limit=character_limit
            )
            
            # Store template
            self.templates[template_id] = template
            self.template_versions[name].append(template)
            
            logger.info(f"Created template: {name} ({template_id})")
            return template
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return None

    def generate_personalized_message(
        self,
        template_id: str,
        user_id: str,
        context_data: Optional[Dict[str, Any]] = None,
        override_variables: Optional[Dict[str, Any]] = None
    ) -> Optional[GeneratedMessage]:
        """
        Generate personalized message from template with advanced context adaptation.
        
        Args:
            template_id: Template identifier
            user_id: User identifier
            context_data: Additional context data
            override_variables: Variable overrides
            
        Returns:
            Generated personalized message
        """
        try:
            template = self.templates.get(template_id)
            if not template or not template.active:
                logger.error(f"Template not found or inactive: {template_id}")
                return None
            
            # Get or create personalization context
            personalization_context = self._get_personalization_context(user_id, context_data)
            
            # Generate variable values
            variable_values = self._generate_variable_values(
                template, personalization_context, override_variables
            )
            
            # Apply tone adjustments
            adjusted_content, tone_adjustments = self._apply_tone_adjustments(
                template.content, template.tone, personalization_context
            )
            
            # Substitute variables
            final_content = self._substitute_variables(adjusted_content, variable_values)
            
            # Apply personalization enhancements
            enhanced_content = self._apply_personalization_enhancements(
                final_content, template.personalization_level, personalization_context
            )
            
            # Validate character limit
            if len(enhanced_content) > template.character_limit:
                enhanced_content = self._optimize_content_length(
                    enhanced_content, template.character_limit
                )
            
            # Generate message ID
            message_id = f"{user_id}_{template_id}_{int(datetime.utcnow().timestamp())}"
            
            # Predict engagement
            engagement_prediction = self._predict_engagement(
                template, personalization_context, enhanced_content
            )
            
            # Create generated message
            generated_message = GeneratedMessage(
                message_id=message_id,
                template_id=template_id,
                user_id=user_id,
                content=enhanced_content,
                personalization_level=template.personalization_level,
                variables_used=variable_values,
                tone_adjustments=tone_adjustments,
                character_count=len(enhanced_content),
                engagement_predicted=engagement_prediction
            )
            
            # Cache generated message
            self.generated_messages[message_id] = generated_message
            
            # Update template usage
            template.usage_count += 1
            template.updated_at = datetime.utcnow()
            
            logger.info(f"Generated personalized message for user {user_id}")
            return generated_message
            
        except Exception as e:
            logger.error(f"Error generating personalized message: {e}")
            return None

    def get_optimal_template(
        self,
        template_type: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[MessageTemplate]:
        """
        Select optimal template based on user context and performance metrics.
        
        Args:
            template_type: Type of template needed
            user_id: User identifier
            context: Additional context for selection
            
        Returns:
            Optimal template for the user and context
        """
        try:
            # Get templates of the requested type
            candidate_templates = [
                t for t in self.templates.values()
                if t.template_type.value == template_type.lower() and t.active
            ]
            
            if not candidate_templates:
                return None
            
            # Get user context for scoring
            personalization_context = self._get_personalization_context(user_id, context)
            
            # Score templates based on multiple factors
            template_scores = []
            for template in candidate_templates:
                score = self._calculate_template_score(template, personalization_context, context)
                template_scores.append((template, score))
            
            # Sort by score and return best template
            template_scores.sort(key=lambda x: x[1], reverse=True)
            best_template = template_scores[0][0]
            
            logger.info(f"Selected optimal template: {best_template.name} for {template_type}")
            return best_template
            
        except Exception as e:
            logger.error(f"Error selecting optimal template: {e}")
            return None

    def analyze_template_performance(
        self,
        template_id: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze template performance and provide optimization recommendations.
        
        Args:
            template_id: Specific template to analyze (None for all)
            days_back: Number of days to analyze
            
        Returns:
            Performance analysis and recommendations
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Filter messages by criteria
            relevant_messages = []
            for message in self.generated_messages.values():
                if message.generated_at < cutoff_date:
                    continue
                if template_id and message.template_id != template_id:
                    continue
                relevant_messages.append(message)
            
            if not relevant_messages:
                return {"error": "No messages found for analysis"}
            
            # Calculate performance metrics
            analysis = {
                "total_messages": len(relevant_messages),
                "templates_analyzed": len(set(m.template_id for m in relevant_messages)),
                "average_character_count": sum(m.character_count for m in relevant_messages) / len(relevant_messages),
                "personalization_distribution": {},
                "tone_usage": {},
                "engagement_metrics": {},
                "optimization_recommendations": []
            }
            
            # Personalization level distribution
            personalization_counts = defaultdict(int)
            for message in relevant_messages:
                personalization_counts[message.personalization_level.value] += 1
            analysis["personalization_distribution"] = dict(personalization_counts)
            
            # Tone adjustments analysis
            tone_counts = defaultdict(int)
            for message in relevant_messages:
                for tone_adj in message.tone_adjustments:
                    tone_counts[tone_adj] += 1
            analysis["tone_usage"] = dict(tone_counts)
            
            # Engagement predictions
            if any(m.engagement_predicted for m in relevant_messages):
                engagement_scores = [m.engagement_predicted for m in relevant_messages if m.engagement_predicted]
                analysis["engagement_metrics"] = {
                    "average_predicted_engagement": sum(engagement_scores) / len(engagement_scores),
                    "high_engagement_percentage": len([s for s in engagement_scores if s > 0.7]) / len(engagement_scores) * 100
                }
            
            # Generate recommendations
            recommendations = self._generate_optimization_recommendations(relevant_messages)
            analysis["optimization_recommendations"] = recommendations
            
            logger.info(f"Analyzed performance for {len(relevant_messages)} messages")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing template performance: {e}")
            return {"error": str(e)}

    def update_template_performance(
        self,
        message_id: str,
        engagement_metrics: Dict[str, Any]
    ) -> bool:
        """
        Update template performance metrics based on actual engagement.
        
        Args:
            message_id: Generated message identifier
            engagement_metrics: Actual engagement data
            
        Returns:
            Success status
        """
        try:
            message = self.generated_messages.get(message_id)
            if not message:
                return False
            
            template = self.templates.get(message.template_id)
            if not template:
                return False
            
            # Update template success metrics
            click_rate = engagement_metrics.get('click_rate', 0)
            response_rate = engagement_metrics.get('response_rate', 0)
            sentiment_score = engagement_metrics.get('sentiment_score', 0.5)
            
            # Update or initialize metrics
            if not template.success_metrics:
                template.success_metrics = {}
            
            # Running average of metrics
            current_usage = template.usage_count
            if current_usage > 1:
                # Update running averages
                template.success_metrics['click_rate'] = (
                    (template.success_metrics.get('click_rate', 0) * (current_usage - 1) + click_rate) / current_usage
                )
                template.success_metrics['response_rate'] = (
                    (template.success_metrics.get('response_rate', 0) * (current_usage - 1) + response_rate) / current_usage
                )
                template.success_metrics['sentiment_score'] = (
                    (template.success_metrics.get('sentiment_score', 0.5) * (current_usage - 1) + sentiment_score) / current_usage
                )
            else:
                template.success_metrics['click_rate'] = click_rate
                template.success_metrics['response_rate'] = response_rate
                template.success_metrics['sentiment_score'] = sentiment_score
            
            template.updated_at = datetime.utcnow()
            
            logger.info(f"Updated performance metrics for template {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating template performance: {e}")
            return False

    def _validate_template_content(self, content: str, variables: List[TemplateVariable]) -> bool:
        """Validate template content and variable references."""
        try:
            # Find all variable placeholders in content
            variable_pattern = r'\{([^}]+)\}'
            found_variables = set(re.findall(variable_pattern, content))
            
            # Check that all referenced variables are defined
            defined_variables = set(var.name for var in variables)
            
            undefined_variables = found_variables - defined_variables
            if undefined_variables:
                logger.error(f"Undefined variables in template: {undefined_variables}")
                return False
            
            # Check for required variables
            required_variables = set(var.name for var in variables if var.required)
            missing_required = required_variables - found_variables
            if missing_required:
                logger.warning(f"Required variables not used in template: {missing_required}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating template content: {e}")
            return False

    def _get_personalization_context(
        self,
        user_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> PersonalizationContext:
        """Get or create personalization context for user."""
        try:
            # Check cache first
            if user_id in self.personalization_cache:
                context = self.personalization_cache[user_id]
                # Update with additional context if provided
                if additional_context:
                    context.preferences.update(additional_context.get('preferences', {}))
                    context.recent_activity.extend(additional_context.get('recent_activity', []))
                return context
            
            # Create new context (in production, this would fetch from user service)
            context = PersonalizationContext(
                user_id=user_id,
                user_name=additional_context.get('user_name') if additional_context else None,
                preferences=additional_context.get('preferences', {}) if additional_context else {},
                goals=additional_context.get('goals', []) if additional_context else [],
                recent_activity=additional_context.get('recent_activity', []) if additional_context else [],
                behavioral_data=additional_context.get('behavioral_data', {}) if additional_context else {},
                location_data=additional_context.get('location_data') if additional_context else None,
                time_context={
                    'current_time': datetime.utcnow(),
                    'timezone': 'UTC',
                    'day_of_week': datetime.utcnow().weekday(),
                    'hour_of_day': datetime.utcnow().hour
                },
                relationship_stage=additional_context.get('relationship_stage', 'active') if additional_context else 'active'
            )
            
            # Cache context
            self.personalization_cache[user_id] = context
            return context
            
        except Exception as e:
            logger.error(f"Error getting personalization context: {e}")
            # Return minimal context
            return PersonalizationContext(
                user_id=user_id,
                user_name=None,
                preferences={},
                goals=[],
                recent_activity=[],
                behavioral_data={},
                location_data=None,
                time_context={'current_time': datetime.utcnow()},
                relationship_stage='active'
            )

    def _generate_variable_values(
        self,
        template: MessageTemplate,
        context: PersonalizationContext,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate values for template variables based on context."""
        values = {}
        
        for variable in template.variables:
            # Check for override first
            if overrides and variable.name in overrides:
                values[variable.name] = overrides[variable.name]
                continue
            
            # Generate contextual value
            if variable.name == 'user_name':
                values[variable.name] = context.user_name or "there"
            elif variable.name == 'time_of_day':
                hour = context.time_context.get('hour_of_day', 12)
                if hour < 12:
                    values[variable.name] = "morning"
                elif hour < 17:
                    values[variable.name] = "afternoon"
                else:
                    values[variable.name] = "evening"
            elif variable.name == 'goal_type':
                if context.goals:
                    values[variable.name] = context.goals[0].get('type', 'health')
                else:
                    values[variable.name] = 'health'
            elif variable.name == 'progress_percentage':
                if context.goals:
                    values[variable.name] = context.goals[0].get('progress', 50)
                else:
                    values[variable.name] = 50
            elif variable.name == 'cuisine_preference':
                values[variable.name] = context.preferences.get('cuisine', 'Mediterranean')
            elif variable.name == 'weekly_streak':
                values[variable.name] = context.behavioral_data.get('weekly_streak', 3)
            else:
                # Use default value
                values[variable.name] = variable.default_value
        
        return values

    def _apply_tone_adjustments(
        self,
        content: str,
        tone: MessageTone,
        context: PersonalizationContext
    ) -> Tuple[str, List[str]]:
        """Apply tone adjustments based on user context and preferences."""
        adjusted_content = content
        adjustments = []
        
        # Get tone-specific adjustments
        tone_rules = self.tone_adaptations.get(tone.value, {})
        
        # Apply relationship stage adjustments
        if context.relationship_stage == "new":
            # More formal and explanatory for new users
            adjusted_content = self._make_more_explanatory(adjusted_content)
            adjustments.append("new_user_friendly")
        elif context.relationship_stage == "at_risk":
            # More encouraging and supportive
            adjusted_content = self._make_more_encouraging(adjusted_content)
            adjustments.append("encouraging_tone")
        
        # Apply time-based adjustments
        hour = context.time_context.get('hour_of_day', 12)
        if hour < 8 or hour > 20:
            # More gentle messaging outside normal hours
            adjusted_content = self._make_more_gentle(adjusted_content)
            adjustments.append("off_hours_gentle")
        
        # Apply preference-based adjustments
        if context.preferences.get('communication_style') == 'brief':
            adjusted_content = self._make_more_concise(adjusted_content)
            adjustments.append("concise_style")
        
        return adjusted_content, adjustments

    def _substitute_variables(self, content: str, variable_values: Dict[str, Any]) -> str:
        """Substitute variable placeholders with actual values."""
        try:
            for variable_name, value in variable_values.items():
                placeholder = f"{{{variable_name}}}"
                content = content.replace(placeholder, str(value))
            
            return content
            
        except Exception as e:
            logger.error(f"Error substituting variables: {e}")
            return content

    def _apply_personalization_enhancements(
        self,
        content: str,
        level: PersonalizationLevel,
        context: PersonalizationContext
    ) -> str:
        """Apply personalization enhancements based on level."""
        if level == PersonalizationLevel.BASIC:
            return content  # Already has basic substitutions
        
        enhanced_content = content
        
        if level in [PersonalizationLevel.MODERATE, PersonalizationLevel.ADVANCED, PersonalizationLevel.DYNAMIC]:
            # Add contextual elements
            if context.recent_activity:
                recent_activity = context.recent_activity[-1]
                activity_type = recent_activity.get('type', '')
                if activity_type == 'meal_plan_request':
                    enhanced_content = self._add_meal_plan_context(enhanced_content, recent_activity)
        
        if level in [PersonalizationLevel.ADVANCED, PersonalizationLevel.DYNAMIC]:
            # Add behavioral insights
            if context.behavioral_data:
                enhanced_content = self._add_behavioral_context(enhanced_content, context.behavioral_data)
        
        if level == PersonalizationLevel.DYNAMIC:
            # Real-time adaptations
            enhanced_content = self._apply_dynamic_adaptations(enhanced_content, context)
        
        return enhanced_content

    def _optimize_content_length(self, content: str, max_length: int) -> str:
        """Optimize content to fit within character limit."""
        if len(content) <= max_length:
            return content
        
        # Try to preserve important parts while trimming
        # 1. Remove unnecessary words
        content = re.sub(r'\b(very|really|quite|actually)\b', '', content)
        
        # 2. Shorten common phrases
        content = content.replace('you are', "you're")
        content = content.replace('we are', "we're")
        content = content.replace('it is', "it's")
        content = content.replace('that is', "that's")
        
        # 3. If still too long, truncate with ellipsis
        if len(content) > max_length:
            content = content[:max_length-3] + "..."
        
        return content

    def _predict_engagement(
        self,
        template: MessageTemplate,
        context: PersonalizationContext,
        content: str
    ) -> float:
        """Predict engagement score for generated message."""
        try:
            score = 0.5  # Base score
            
            # Template performance factor
            if template.success_metrics:
                template_score = template.success_metrics.get('click_rate', 0.3)
                score += template_score * 0.3
            
            # Personalization factor
            personalization_bonus = {
                PersonalizationLevel.BASIC: 0.0,
                PersonalizationLevel.MODERATE: 0.1,
                PersonalizationLevel.ADVANCED: 0.15,
                PersonalizationLevel.DYNAMIC: 0.2
            }
            score += personalization_bonus.get(template.personalization_level, 0)
            
            # Time context factor
            hour = context.time_context.get('hour_of_day', 12)
            if 9 <= hour <= 17:  # Business hours
                score += 0.1
            elif 18 <= hour <= 21:  # Evening engagement peak
                score += 0.15
            
            # Content length factor (sweet spot around 120 characters)
            content_length = len(content)
            if 80 <= content_length <= 140:
                score += 0.1
            elif content_length > 160:
                score -= 0.1
            
            # User relationship stage factor
            relationship_bonus = {
                'new': 0.05,
                'active': 0.1,
                'returning': 0.15,
                'at_risk': -0.05
            }
            score += relationship_bonus.get(context.relationship_stage, 0)
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error predicting engagement: {e}")
            return 0.5

    def _calculate_template_score(
        self,
        template: MessageTemplate,
        context: PersonalizationContext,
        selection_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate score for template selection."""
        score = 0.0
        
        # Performance metrics weight (40%)
        if template.success_metrics:
            performance_score = (
                template.success_metrics.get('click_rate', 0.3) * 0.5 +
                template.success_metrics.get('response_rate', 0.2) * 0.3 +
                template.success_metrics.get('sentiment_score', 0.5) * 0.2
            )
            score += performance_score * 0.4
        else:
            score += 0.3 * 0.4  # Default performance score
        
        # Personalization compatibility (30%)
        personalization_fit = self._calculate_personalization_fit(template, context)
        score += personalization_fit * 0.3
        
        # Usage frequency (negative factor to promote variety) (20%)
        usage_penalty = min(0.2, template.usage_count / 1000.0)
        score += (0.2 - usage_penalty) * 0.2
        
        # Context relevance (10%)
        context_relevance = self._calculate_context_relevance(template, selection_context)
        score += context_relevance * 0.1
        
        return score

    def _calculate_personalization_fit(self, template: MessageTemplate, context: PersonalizationContext) -> float:
        """Calculate how well template fits user's personalization needs."""
        # Check if user prefers high personalization
        high_engagement_user = len(context.recent_activity) > 10
        
        if high_engagement_user and template.personalization_level in [PersonalizationLevel.ADVANCED, PersonalizationLevel.DYNAMIC]:
            return 1.0
        elif not high_engagement_user and template.personalization_level in [PersonalizationLevel.BASIC, PersonalizationLevel.MODERATE]:
            return 1.0
        else:
            return 0.6

    def _calculate_context_relevance(self, template: MessageTemplate, context: Optional[Dict[str, Any]]) -> float:
        """Calculate template relevance to current context."""
        if not context:
            return 0.5
        
        relevance = 0.5
        
        # Check target audience match
        user_segment = context.get('user_segment', 'general')
        if user_segment in template.target_audience:
            relevance += 0.3
        
        # Check usage context match
        current_context = context.get('usage_context', 'general')
        if current_context in template.usage_context:
            relevance += 0.2
        
        return min(1.0, relevance)

    def _generate_optimization_recommendations(self, messages: List[GeneratedMessage]) -> List[str]:
        """Generate optimization recommendations based on message analysis."""
        recommendations = []
        
        # Analyze character count distribution
        char_counts = [m.character_count for m in messages]
        avg_chars = sum(char_counts) / len(char_counts)
        
        if avg_chars > 140:
            recommendations.append("Consider shorter templates - average character count is high")
        elif avg_chars < 80:
            recommendations.append("Templates might be too brief - consider adding more context")
        
        # Analyze personalization usage
        personalization_counts = defaultdict(int)
        for message in messages:
            personalization_counts[message.personalization_level.value] += 1
        
        basic_percentage = personalization_counts.get('basic', 0) / len(messages) * 100
        if basic_percentage > 60:
            recommendations.append("Increase personalization levels - too many basic messages")
        
        # Analyze tone adjustments
        all_adjustments = []
        for message in messages:
            all_adjustments.extend(message.tone_adjustments)
        
        if len(all_adjustments) / len(messages) < 0.5:
            recommendations.append("Consider more tone adaptations based on user context")
        
        return recommendations

    def _load_default_templates(self) -> None:
        """Load default message templates."""
        default_templates = [
            {
                "name": "Welcome New User",
                "template_type": "welcome",
                "content": "Hi {user_name}! Welcome to your personalized nutrition journey. We're excited to help you achieve your {goal_type} goals! 🎯",
                "variables": [
                    {"name": "user_name", "type": "text", "default": "there", "required": True},
                    {"name": "goal_type", "type": "text", "default": "health", "required": True}
                ],
                "personalization_level": "moderate",
                "tone": "friendly",
                "target_audience": ["new_users"],
                "usage_context": ["onboarding"]
            },
            {
                "name": "Meal Plan Delivery",
                "template_type": "meal_plan_delivery",
                "content": "Good {time_of_day} {user_name}! Your {cuisine_preference} meal plan is ready. Let's make today delicious and nutritious! 🍽️",
                "variables": [
                    {"name": "user_name", "type": "text", "default": "there", "required": True},
                    {"name": "time_of_day", "type": "text", "default": "day", "required": True},
                    {"name": "cuisine_preference", "type": "text", "default": "healthy", "required": True}
                ],
                "personalization_level": "advanced",
                "tone": "encouraging",
                "target_audience": ["active_users"],
                "usage_context": ["meal_planning"]
            },
            {
                "name": "Goal Progress Update",
                "template_type": "goal_progress",
                "content": "Amazing work {user_name}! You're {progress_percentage}% towards your goal. Keep up the fantastic momentum! 💪",
                "variables": [
                    {"name": "user_name", "type": "text", "default": "there", "required": True},
                    {"name": "progress_percentage", "type": "number", "default": 50, "required": True}
                ],
                "personalization_level": "moderate",
                "tone": "motivational",
                "target_audience": ["active_users"],
                "usage_context": ["progress_tracking"]
            },
            {
                "name": "Weekly Streak Celebration",
                "template_type": "congratulations",
                "content": "🎉 Incredible {user_name}! You've maintained your {weekly_streak}-week streak. You're building amazing healthy habits!",
                "variables": [
                    {"name": "user_name", "type": "text", "default": "there", "required": True},
                    {"name": "weekly_streak", "type": "number", "default": 1, "required": True}
                ],
                "personalization_level": "advanced",
                "tone": "congratulatory",
                "target_audience": ["consistent_users"],
                "usage_context": ["milestone_celebration"]
            }
        ]
        
        for template_data in default_templates:
            self.create_template(**template_data)

    def _initialize_tone_adaptations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize tone adaptation rules."""
        return {
            "friendly": {
                "greeting_words": ["Hi", "Hello", "Hey"],
                "enthusiasm_level": "moderate",
                "emoji_usage": "moderate"
            },
            "professional": {
                "greeting_words": ["Hello", "Good morning", "Good evening"],
                "enthusiasm_level": "low",
                "emoji_usage": "minimal"
            },
            "encouraging": {
                "greeting_words": ["Great", "Awesome", "Amazing"],
                "enthusiasm_level": "high",
                "emoji_usage": "moderate"
            },
            "motivational": {
                "greeting_words": ["You've got this", "Let's go", "Time to shine"],
                "enthusiasm_level": "very_high",
                "emoji_usage": "high"
            }
        }

    def _initialize_seasonal_content(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize seasonal content variations."""
        return {
            "spring": {
                "themes": ["fresh starts", "renewal", "growth"],
                "food_focus": ["fresh vegetables", "lighter meals", "seasonal produce"]
            },
            "summer": {
                "themes": ["energy", "outdoor activities", "hydration"],
                "food_focus": ["grilled foods", "salads", "refreshing drinks"]
            },
            "fall": {
                "themes": ["preparation", "comfort", "harvest"],
                "food_focus": ["warming spices", "hearty meals", "seasonal flavors"]
            },
            "winter": {
                "themes": ["warmth", "comfort", "maintenance"],
                "food_focus": ["warming foods", "immune support", "comfort meals"]
            }
        }

    def _make_more_explanatory(self, content: str) -> str:
        """Make content more explanatory for new users."""
        # Add brief explanations for concepts
        if "meal plan" in content.lower():
            content = content.replace("meal plan", "personalized meal plan (tailored just for you)")
        return content

    def _make_more_encouraging(self, content: str) -> str:
        """Make content more encouraging and supportive."""
        encouraging_phrases = [
            "You're doing great!",
            "Every step counts!",
            "We're here to support you!",
            "You've got this!"
        ]
        # Add an encouraging phrase
        return content + " " + random.choice(encouraging_phrases)

    def _make_more_gentle(self, content: str) -> str:
        """Make content more gentle for off-hours messaging."""
        # Soften urgent language
        content = content.replace("!", ".")
        content = content.replace("Let's", "When you're ready, let's")
        return content

    def _make_more_concise(self, content: str) -> str:
        """Make content more concise for users who prefer brief messages."""
        # Remove filler words and phrases
        concise_content = re.sub(r'\b(just|really|very|quite|actually|basically)\b\s*', '', content)
        concise_content = re.sub(r'\s+', ' ', concise_content).strip()
        return concise_content

    def _add_meal_plan_context(self, content: str, activity: Dict[str, Any]) -> str:
        """Add context based on recent meal plan activity."""
        if "cuisine" in activity:
            cuisine = activity["cuisine"]
            return content + f" (Based on your love for {cuisine} cuisine)"
        return content

    def _add_behavioral_context(self, content: str, behavioral_data: Dict[str, Any]) -> str:
        """Add context based on behavioral patterns."""
        if behavioral_data.get("preferred_time") == "morning":
            return content.replace("today", "this morning")
        elif behavioral_data.get("preferred_time") == "evening":
            return content.replace("today", "tonight")
        return content

    def _apply_dynamic_adaptations(self, content: str, context: PersonalizationContext) -> str:
        """Apply real-time dynamic adaptations."""
        # Weather-based adaptations (placeholder)
        if context.location_data and context.location_data.get("weather") == "cold":
            content = content.replace("refreshing", "warming")
            content = content.replace("salad", "soup")
        
        return content
