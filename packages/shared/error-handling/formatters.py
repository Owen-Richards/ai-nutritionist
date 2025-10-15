"""
Error Formatters and User-Friendly Messages

Provides consistent error formatting and user-friendly messages
across all services and interfaces.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .exceptions import BaseError, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)


class UserFriendlyMessages:
    """
    Repository of user-friendly error messages
    
    Provides contextual, helpful messages that don't expose
    technical details to end users.
    """
    
    # General error messages
    GENERAL_MESSAGES = {
        'default': "I'm having trouble processing your request right now. Please try again in a moment! 😅",
        'temporary': "I'm experiencing some temporary difficulties. Please try again shortly! 🔧",
        'maintenance': "I'm currently undergoing maintenance. I'll be back soon! ⚡",
        'overloaded': "I'm a bit overloaded right now. Please give me a moment and try again! ⏳"
    }
    
    # Category-specific messages
    CATEGORY_MESSAGES = {
        ErrorCategory.VALIDATION: {
            'default': "There seems to be an issue with your input. Could you check and try again? 🤔",
            'missing_field': "It looks like some required information is missing. Could you provide more details?",
            'invalid_format': "The format doesn't look quite right. Could you try a different format?",
            'out_of_range': "That value seems to be outside the expected range. Could you adjust it?"
        },
        
        ErrorCategory.AUTHENTICATION: {
            'default': "I need you to log in first. Please sign in and try again! 🔐",
            'expired': "Your session has expired. Please log in again to continue.",
            'invalid_credentials': "Those credentials don't look right. Please check and try again.",
            'locked_account': "Your account has been temporarily locked for security. Please contact support."
        },
        
        ErrorCategory.AUTHORIZATION: {
            'default': "You don't have permission to do that. If you think this is an error, please contact support! 🚫",
            'insufficient_plan': "This feature requires a premium plan. Would you like to upgrade? 🚀",
            'feature_restricted': "This feature isn't available on your current plan.",
            'admin_required': "This action requires administrator privileges."
        },
        
        ErrorCategory.RATE_LIMITING: {
            'default': "You're making requests too quickly! Please slow down and try again in a moment. ⏱️",
            'quota_exceeded': "You've reached your daily limit. Upgrade your plan for more requests! 📈",
            'burst_limit': "Too many requests at once! Please wait a moment and try again.",
            'monthly_limit': "You've used up your monthly allowance. It resets next month or upgrade now!"
        },
        
        ErrorCategory.PAYMENT: {
            'default': "There was an issue with your payment. Please check your payment method and try again! 💳",
            'card_declined': "Your card was declined. Please try a different payment method.",
            'insufficient_funds': "It looks like there aren't enough funds. Please try a different card.",
            'expired_card': "Your card has expired. Please update your payment information.",
            'processing_error': "The payment processor is having issues. Please try again later."
        },
        
        ErrorCategory.INFRASTRUCTURE: {
            'default': "I'm having some technical difficulties on my end. Please try again in a moment! 🔧",
            'service_unavailable': "One of my services is temporarily down. I'm working to fix it!",
            'timeout': "That took longer than expected. Please try again!",
            'connection_error': "I'm having trouble connecting to my services. Please try again shortly.",
            'database_error': "I'm having database issues. Please try again in a moment."
        },
        
        ErrorCategory.BUSINESS_LOGIC: {
            'default': "I can't complete that request right now. Please try something else or contact support! 🤖",
            'invalid_operation': "That operation isn't allowed in the current state.",
            'resource_conflict': "There's a conflict with your request. Please try again.",
            'business_rule': "That action violates one of my business rules.",
            'workflow_error': "There's an issue with the workflow. Please start over."
        }
    }
    
    # Context-specific messages for nutrition app
    NUTRITION_MESSAGES = {
        'meal_plan_error': "I couldn't generate your meal plan right now. Here's a basic plan to get you started! 🍽️",
        'calorie_calculation_error': "I had trouble calculating calories. Let me give you a rough estimate! 📊",
        'ingredient_not_found': "I couldn't find that ingredient in my database. Could you try a similar one? 🔍",
        'recipe_generation_error': "I couldn't create a custom recipe, but here are some popular options! 👨‍🍳",
        'nutrition_analysis_error': "I couldn't analyze the nutrition right now, but I can give you general advice! 📈",
        'diet_restriction_error': "I had trouble processing your dietary restrictions. Let me know your main concerns! 🥗"
    }
    
    # Helpful suggestions
    SUGGESTIONS = {
        'retry': "Try again in a few moments",
        'contact_support': "Contact our support team if this continues",
        'check_connection': "Check your internet connection",
        'try_different': "Try a different approach or input",
        'upgrade_plan': "Consider upgrading your plan for more features",
        'check_input': "Double-check your input for any errors"
    }
    
    @classmethod
    def get_message(
        cls,
        error: BaseError,
        context: Optional[str] = None,
        include_suggestions: bool = True
    ) -> str:
        """
        Get user-friendly message for error
        
        Args:
            error: The error to format
            context: Additional context (e.g., 'meal_plan', 'payment')
            include_suggestions: Whether to include helpful suggestions
        
        Returns:
            User-friendly error message
        """
        # Check for nutrition-specific context first
        if context and context in cls.NUTRITION_MESSAGES:
            message = cls.NUTRITION_MESSAGES[context]
        # Check category-specific messages
        elif error.category in cls.CATEGORY_MESSAGES:
            category_messages = cls.CATEGORY_MESSAGES[error.category]
            message = category_messages.get(context, category_messages['default'])
        # Fall back to general messages
        else:
            message = cls.GENERAL_MESSAGES.get(context, cls.GENERAL_MESSAGES['default'])
        
        # Add suggestions if requested and error is recoverable
        if include_suggestions and error.recoverable:
            suggestions = cls._get_suggestions(error)
            if suggestions:
                message += f" {suggestions}"
        
        return message
    
    @classmethod
    def _get_suggestions(cls, error: BaseError) -> str:
        """Get helpful suggestions based on error type"""
        suggestions = []
        
        if error.category == ErrorCategory.RATE_LIMITING:
            if error.retry_after:
                suggestions.append(f"Try again in {error.retry_after} seconds")
            else:
                suggestions.append(cls.SUGGESTIONS['retry'])
        elif error.category == ErrorCategory.VALIDATION:
            suggestions.append(cls.SUGGESTIONS['check_input'])
        elif error.category == ErrorCategory.INFRASTRUCTURE:
            suggestions.append(cls.SUGGESTIONS['retry'])
            if error.severity == ErrorSeverity.CRITICAL:
                suggestions.append(cls.SUGGESTIONS['contact_support'])
        elif error.category == ErrorCategory.AUTHORIZATION:
            suggestions.append(cls.SUGGESTIONS['upgrade_plan'])
        elif error.severity == ErrorSeverity.CRITICAL:
            suggestions.append(cls.SUGGESTIONS['contact_support'])
        
        return " ".join(suggestions) if suggestions else ""


class ErrorFormatter:
    """
    Comprehensive error formatting for different output formats
    
    Supports JSON, HTML, plain text, and structured logging formats.
    """
    
    def __init__(self, include_debug_info: bool = False):
        self.include_debug_info = include_debug_info
    
    def format_for_api(self, error: BaseError, include_details: bool = False) -> Dict[str, Any]:
        """
        Format error for API response
        
        Args:
            error: Error to format
            include_details: Whether to include technical details
        
        Returns:
            Dictionary suitable for JSON API response
        """
        response = {
            'error': True,
            'error_id': error.error_id,
            'error_code': error.error_code,
            'message': error.user_message,
            'timestamp': error.timestamp.isoformat(),
            'recoverable': error.recoverable
        }
        
        if error.retry_after:
            response['retry_after'] = error.retry_after
        
        if include_details or self.include_debug_info:
            response['details'] = {
                'severity': error.severity.value,
                'category': error.category.value,
                'technical_message': error.message,
                'context': error.context
            }
            
            if error.cause:
                response['details']['cause'] = str(error.cause)
        
        return response
    
    def format_for_user(self, error: BaseError, context: Optional[str] = None) -> str:
        """
        Format error for end-user display
        
        Args:
            error: Error to format
            context: Additional context for message selection
        
        Returns:
            User-friendly error message
        """
        return UserFriendlyMessages.get_message(error, context)
    
    def format_for_logging(self, error: BaseError, additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format error for structured logging
        
        Args:
            error: Error to format
            additional_context: Additional context to include
        
        Returns:
            Dictionary suitable for structured logging
        """
        log_data = error.to_dict()
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        # Add formatted user message
        log_data['user_message_formatted'] = self.format_for_user(error)
        
        return log_data
    
    def format_for_monitoring(self, error: BaseError) -> Dict[str, Any]:
        """
        Format error for monitoring and alerting systems
        
        Args:
            error: Error to format
        
        Returns:
            Dictionary with monitoring-relevant data
        """
        return {
            'error_id': error.error_id,
            'error_code': error.error_code,
            'severity': error.severity.value,
            'category': error.category.value,
            'timestamp': error.timestamp.isoformat(),
            'recoverable': error.recoverable,
            'message': error.message,
            'context': error.context,
            'tags': self._generate_tags(error)
        }
    
    def format_for_html(self, error: BaseError, context: Optional[str] = None) -> str:
        """
        Format error for HTML display
        
        Args:
            error: Error to format
            context: Additional context for message selection
        
        Returns:
            HTML-formatted error message
        """
        severity_icons = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️", 
            ErrorSeverity.HIGH: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }
        
        icon = severity_icons.get(error.severity, "⚠️")
        message = self.format_for_user(error, context)
        
        html = f"""
        <div class="error-message error-{error.severity.value}" data-error-id="{error.error_id}">
            <span class="error-icon">{icon}</span>
            <span class="error-text">{message}</span>
            {f'<span class="error-retry">Retry in {error.retry_after}s</span>' if error.retry_after else ''}
        </div>
        """
        
        return html.strip()
    
    def format_batch_errors(self, errors: List[BaseError]) -> Dict[str, Any]:
        """
        Format multiple errors for batch operations
        
        Args:
            errors: List of errors to format
        
        Returns:
            Dictionary with batch error information
        """
        if not errors:
            return {'has_errors': False, 'error_count': 0}
        
        error_summary = {
            'has_errors': True,
            'error_count': len(errors),
            'errors': [self.format_for_api(error) for error in errors],
            'summary': self._create_error_summary(errors),
            'most_severe': max(errors, key=lambda e: self._severity_weight(e.severity)).severity.value,
            'total_recoverable': sum(1 for e in errors if e.recoverable)
        }
        
        return error_summary
    
    def _generate_tags(self, error: BaseError) -> List[str]:
        """Generate tags for monitoring and filtering"""
        tags = [
            f"severity:{error.severity.value}",
            f"category:{error.category.value}",
            f"recoverable:{error.recoverable}"
        ]
        
        # Add context-based tags
        if 'service_name' in error.context:
            tags.append(f"service:{error.context['service_name']}")
        
        if 'operation' in error.context:
            tags.append(f"operation:{error.context['operation']}")
        
        return tags
    
    def _create_error_summary(self, errors: List[BaseError]) -> Dict[str, Any]:
        """Create summary of multiple errors"""
        categories = {}
        severities = {}
        
        for error in errors:
            category = error.category.value
            severity = error.severity.value
            
            categories[category] = categories.get(category, 0) + 1
            severities[severity] = severities.get(severity, 0) + 1
        
        return {
            'by_category': categories,
            'by_severity': severities,
            'most_common_category': max(categories, key=categories.get),
            'dominant_severity': max(severities, key=severities.get)
        }
    
    def _severity_weight(self, severity: ErrorSeverity) -> int:
        """Get numeric weight for severity comparison"""
        weights = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        return weights.get(severity, 2)


# Utility functions
def format_error_for_chat(error: BaseError) -> str:
    """Format error for chat/messaging interfaces"""
    formatter = ErrorFormatter()
    message = formatter.format_for_user(error)
    
    # Add emoji and conversational tone for chat
    if error.category == ErrorCategory.RATE_LIMITING:
        return f"Whoa there! 🐌 {message}"
    elif error.category == ErrorCategory.PAYMENT:
        return f"Oops! 💳 {message}"
    elif error.severity == ErrorSeverity.CRITICAL:
        return f"Uh oh! 😅 {message}"
    else:
        return f"Hmm... 🤔 {message}"


def format_error_for_email(error: BaseError, user_name: Optional[str] = None) -> Dict[str, str]:
    """Format error for email notifications"""
    greeting = f"Hi {user_name}," if user_name else "Hello,"
    
    subject = f"Issue with your request - {error.error_code}"
    
    if error.severity == ErrorSeverity.CRITICAL:
        subject = f"🚨 Critical Issue - {error.error_code}"
    elif error.severity == ErrorSeverity.HIGH:
        subject = f"⚠️ Important - {error.error_code}"
    
    formatter = ErrorFormatter()
    user_message = formatter.format_for_user(error)
    
    body = f"""
{greeting}

{user_message}

If you continue to experience issues, please don't hesitate to contact our support team with reference ID: {error.error_id}

Best regards,
The AI Nutritionist Team
    """.strip()
    
    return {
        'subject': subject,
        'body': body,
        'error_id': error.error_id
    }
