"""
Service Integration Templates

Templates and patterns for integrating the comprehensive error handling
system into existing services throughout the application.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import error handling system
from packages.shared.error_handling import (
    BaseError, DomainError, ValidationError, NotFoundError,
    InfrastructureError, AuthenticationError, AuthorizationError,
    error_handler, circuit_breaker, retry_with_backoff,
    ErrorRecoveryManager, ErrorFormatter, ErrorMetricsCollector
)

logger = logging.getLogger(__name__)


# Template 1: Update Existing Messaging Service
class EnhancedMessagingService:
    """
    Template for enhancing existing messaging service with error handling
    
    Based on: src/services/messaging/cost_aware_handler.py
    """
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.metrics_collector = ErrorMetricsCollector()
        self.error_formatter = ErrorFormatter()
    
    @error_handler(log_errors=True, collect_metrics=True)
    @retry_with_backoff(max_retries=3, retryable_exceptions=(InfrastructureError,))
    async def send_message(self, phone_number: str, message: str, message_type: str = "SMS") -> Dict[str, Any]:
        """Enhanced message sending with comprehensive error handling"""
        
        # Input validation
        if not phone_number:
            raise ValidationError(
                message="Phone number is required",
                field="phone_number",
                invalid_value=phone_number,
                validation_rules=["required", "non_empty"]
            )
        
        if not message:
            raise ValidationError(
                message="Message content is required",
                field="message",
                invalid_value=message,
                validation_rules=["required", "non_empty"]
            )
        
        # Business rule validation
        if len(message) > 1600:  # SMS limit
            raise DomainError(
                message=f"Message length {len(message)} exceeds SMS limit",
                business_rule="sms_length_limit",
                context={'max_length': 1600, 'actual_length': len(message)}
            )
        
        # Use recovery manager for external service calls
        result = await self.recovery_manager.execute_with_recovery(
            func=self._send_via_aws_pinpoint,
            operation_name="send_sms",
            fallback_type="messaging",
            phone_number=phone_number,
            message=message,
            message_type=message_type
        )
        
        if not result['success']:
            # Log and handle failure
            logger.warning(f"Message sending failed for {phone_number}, using fallback")
            return self._handle_messaging_failure(phone_number, message, result)
        
        return result['data']
    
    async def _send_via_aws_pinpoint(self, phone_number: str, message: str, message_type: str) -> Dict[str, Any]:
        """Send message via AWS Pinpoint with proper error conversion"""
        try:
            # Original AWS Pinpoint sending logic here
            import boto3
            
            client = boto3.client('pinpoint-sms-voice-v2')
            
            response = client.send_text_message(
                DestinationPhoneNumber=phone_number,
                OriginationIdentity='your-pool-id',
                MessageBody=message
            )
            
            return {
                'message_id': response['MessageId'],
                'status': 'sent',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except client.exceptions.ThrottlingException as e:
            raise InfrastructureError(
                message="AWS Pinpoint rate limit exceeded",
                service_name="aws_pinpoint",
                operation="send_text_message",
                status_code=429,
                cause=e
            )
        
        except client.exceptions.ServiceFailureException as e:
            raise InfrastructureError(
                message="AWS Pinpoint service failure",
                service_name="aws_pinpoint", 
                operation="send_text_message",
                status_code=503,
                cause=e
            )
        
        except Exception as e:
            # Convert unknown AWS errors to infrastructure errors
            raise InfrastructureError(
                message=f"AWS Pinpoint error: {str(e)}",
                service_name="aws_pinpoint",
                operation="send_text_message",
                cause=e
            )
    
    def _handle_messaging_failure(self, phone_number: str, message: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle messaging service failure with graceful degradation"""
        
        # Log the failure for manual follow-up
        logger.error(f"Failed to send message to {phone_number}: {result.get('error')}")
        
        # Queue for retry (in real implementation, use SQS)
        # self._queue_message_for_retry(phone_number, message)
        
        return {
            'message_id': f"failed_{int(datetime.utcnow().timestamp())}",
            'status': 'queued_for_retry',
            'timestamp': datetime.utcnow().isoformat(),
            'fallback': True,
            'user_message': "Your message is being processed and will be delivered shortly."
        }


# Template 2: Enhanced AI Service Integration
class EnhancedAIService:
    """
    Template for enhancing AI service with error handling
    
    Based on: src/services/infrastructure/ai.py
    """
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.metrics_collector = ErrorMetricsCollector()
    
    @circuit_breaker(failure_threshold=5, recovery_timeout=180)
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def generate_nutrition_advice(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate nutrition advice with robust error handling"""
        
        # Validate required fields
        required_fields = ['user_id', 'dietary_preferences', 'health_goals']
        for field in required_fields:
            if not user_data.get(field):
                raise ValidationError(
                    message=f"Required field '{field}' is missing",
                    field=field,
                    invalid_value=user_data.get(field),
                    validation_rules=["required"]
                )
        
        # Business validation
        age = user_data.get('age', 0)
        if age < 13 or age > 120:
            raise DomainError(
                message=f"Age {age} is outside supported range",
                business_rule="age_range_validation",
                context={'min_age': 13, 'max_age': 120, 'provided_age': age}
            )
        
        # Use recovery manager for AI service calls
        result = await self.recovery_manager.execute_with_recovery(
            func=self._call_openai_api,
            operation_name="generate_nutrition_advice",
            fallback_type="nutrition_advice",
            user_data=user_data
        )
        
        if not result['success']:
            return self._get_fallback_nutrition_advice(user_data)
        
        return result['data']
    
    async def _call_openai_api(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call OpenAI API with proper error handling"""
        try:
            # OpenAI API call logic here
            import openai
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional nutritionist."},
                    {"role": "user", "content": f"Provide nutrition advice for: {user_data}"}
                ],
                max_tokens=500
            )
            
            return {
                'advice': response.choices[0].message.content,
                'model_used': 'gpt-4',
                'tokens_used': response.usage.total_tokens,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except openai.error.RateLimitError as e:
            raise InfrastructureError(
                message="OpenAI rate limit exceeded",
                service_name="openai",
                operation="chat_completion",
                status_code=429,
                retry_after=60,
                cause=e
            )
        
        except openai.error.ServiceUnavailableError as e:
            raise InfrastructureError(
                message="OpenAI service unavailable",
                service_name="openai",
                operation="chat_completion", 
                status_code=503,
                retry_after=30,
                cause=e
            )
        
        except Exception as e:
            raise InfrastructureError(
                message=f"OpenAI API error: {str(e)}",
                service_name="openai",
                operation="chat_completion",
                cause=e
            )
    
    def _get_fallback_nutrition_advice(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback nutrition advice when AI service fails"""
        return {
            'advice': self._generate_basic_advice(user_data),
            'fallback': True,
            'note': 'This is general advice. Our AI nutritionist will provide personalized recommendations once available.',
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_basic_advice(self, user_data: Dict[str, Any]) -> str:
        """Generate basic nutrition advice based on user data"""
        advice_parts = [
            "Focus on a balanced diet with plenty of vegetables and fruits.",
            "Include lean proteins like chicken, fish, beans, and tofu.",
            "Choose whole grains over refined carbohydrates.",
            "Stay hydrated with 8+ glasses of water daily.",
            "Limit processed foods and added sugars."
        ]
        
        # Customize based on user data
        if user_data.get('health_goals') == 'weight_loss':
            advice_parts.append("Create a moderate calorie deficit through diet and exercise.")
        elif user_data.get('health_goals') == 'muscle_gain':
            advice_parts.append("Increase protein intake and focus on strength training.")
        
        return " ".join(advice_parts)


# Template 3: Enhanced Payment Service Integration
class EnhancedPaymentService:
    """
    Template for enhancing payment service with error handling
    
    Based on: src/services/payment/
    """
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.metrics_collector = ErrorMetricsCollector()
        self.error_formatter = ErrorFormatter()
    
    @error_handler(log_errors=True, collect_metrics=True)
    @circuit_breaker(failure_threshold=3, recovery_timeout=300)
    async def process_subscription_payment(
        self,
        user_id: str,
        plan_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Process subscription payment with comprehensive error handling"""
        
        # Validate inputs
        if not all([user_id, plan_id, payment_method_id]):
            missing_fields = [
                field for field, value in {
                    'user_id': user_id,
                    'plan_id': plan_id,
                    'payment_method_id': payment_method_id
                }.items() if not value
            ]
            
            raise ValidationError(
                message=f"Missing required fields: {', '.join(missing_fields)}",
                field="multiple",
                validation_rules=["required"]
            )
        
        # Get plan details
        plan_details = await self._get_plan_details(plan_id)
        if not plan_details:
            raise NotFoundError(
                message=f"Subscription plan not found",
                resource_type="subscription_plan",
                resource_id=plan_id
            )
        
        # Process payment with recovery
        result = await self.recovery_manager.execute_with_recovery(
            func=self._charge_payment_method,
            operation_name="process_subscription_payment",
            user_id=user_id,
            plan_details=plan_details,
            payment_method_id=payment_method_id
        )
        
        if not result['success']:
            # Handle payment failure
            return self._handle_payment_failure(user_id, plan_id, result)
        
        # Activate subscription
        await self._activate_subscription(user_id, plan_id, result['data'])
        
        return result['data']
    
    async def _charge_payment_method(
        self,
        user_id: str,
        plan_details: Dict[str, Any],
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Charge payment method with specific error handling"""
        try:
            # Stripe/payment processor logic here
            import stripe
            
            payment_intent = stripe.PaymentIntent.create(
                amount=int(plan_details['price'] * 100),  # Convert to cents
                currency='usd',
                customer=user_id,
                payment_method=payment_method_id,
                confirm=True
            )
            
            return {
                'payment_intent_id': payment_intent.id,
                'status': payment_intent.status,
                'amount': plan_details['price'],
                'currency': 'USD'
            }
            
        except stripe.error.CardError as e:
            # Card was declined
            from packages.shared.error_handling import PaymentError
            raise PaymentError(
                message="Card was declined",
                payment_method=payment_method_id,
                amount=plan_details['price'],
                currency="USD",
                provider_error_code=e.code,
                cause=e
            )
        
        except stripe.error.RateLimitError as e:
            raise InfrastructureError(
                message="Payment processor rate limit exceeded",
                service_name="stripe",
                operation="create_payment_intent",
                status_code=429,
                retry_after=60,
                cause=e
            )
        
        except Exception as e:
            from packages.shared.error_handling import PaymentError
            raise PaymentError(
                message=f"Payment processing failed: {str(e)}",
                payment_method=payment_method_id,
                amount=plan_details['price'],
                currency="USD",
                cause=e
            )
    
    async def _get_plan_details(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription plan details"""
        # Database lookup logic here
        plans = {
            'basic': {'price': 9.99, 'name': 'Basic Plan'},
            'premium': {'price': 19.99, 'name': 'Premium Plan'},
            'pro': {'price': 29.99, 'name': 'Pro Plan'}
        }
        return plans.get(plan_id)
    
    async def _activate_subscription(self, user_id: str, plan_id: str, payment_data: Dict[str, Any]):
        """Activate user subscription"""
        # Subscription activation logic here
        logger.info(f"Activated {plan_id} subscription for user {user_id}")
    
    def _handle_payment_failure(self, user_id: str, plan_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment failure with user-friendly response"""
        
        error_message = result.get('error', 'Payment failed')
        
        # Log for admin review
        logger.error(f"Subscription payment failed for user {user_id}, plan {plan_id}: {error_message}")
        
        return {
            'success': False,
            'error': 'payment_failed',
            'user_message': 'We were unable to process your payment. Please check your payment method and try again.',
            'details': {
                'can_retry': True,
                'suggested_actions': [
                    'Verify your payment method details',
                    'Check if your card has sufficient funds',
                    'Try a different payment method',
                    'Contact your bank if the issue persists'
                ]
            }
        }


# Template 4: Database Service Error Handling
class EnhancedDatabaseService:
    """
    Template for database operations with error handling
    """
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.metrics_collector = ErrorMetricsCollector()
    
    @retry_with_backoff(max_retries=3, retryable_exceptions=(InfrastructureError,))
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with database error handling"""
        
        if not user_id:
            raise ValidationError(
                message="User ID is required",
                field="user_id",
                invalid_value=user_id
            )
        
        try:
            # Database query logic
            result = await self._query_database(
                "SELECT * FROM user_profiles WHERE user_id = %s",
                (user_id,)
            )
            
            if not result:
                raise NotFoundError(
                    message="User profile not found",
                    resource_type="user_profile",
                    resource_id=user_id
                )
            
            return result[0]
            
        except ConnectionError as e:
            raise InfrastructureError(
                message="Database connection failed",
                service_name="postgresql",
                operation="get_user_profile",
                cause=e
            )
        
        except Exception as e:
            raise InfrastructureError(
                message=f"Database query failed: {str(e)}",
                service_name="postgresql",
                operation="get_user_profile",
                cause=e
            )
    
    async def _query_database(self, query: str, params: tuple) -> List[Dict[str, Any]]:
        """Execute database query with connection handling"""
        # Database connection and query logic here
        # This would use your actual database connection
        pass


# Template 5: Lambda Handler Integration
async def enhanced_lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Template for Lambda handlers with comprehensive error handling
    
    Based on: src/handlers/conversational_messaging_handler.py
    """
    
    error_formatter = ErrorFormatter()
    metrics_collector = ErrorMetricsCollector()
    
    try:
        # Parse request
        request_data = _parse_lambda_event(event)
        
        # Route to appropriate service
        if request_data['action'] == 'send_message':
            service = EnhancedMessagingService()
            result = await service.send_message(
                phone_number=request_data['phone_number'],
                message=request_data['message']
            )
        
        elif request_data['action'] == 'generate_advice':
            service = EnhancedAIService()
            result = await service.generate_nutrition_advice(request_data['user_data'])
        
        elif request_data['action'] == 'process_payment':
            service = EnhancedPaymentService()
            result = await service.process_subscription_payment(
                user_id=request_data['user_id'],
                plan_id=request_data['plan_id'],
                payment_method_id=request_data['payment_method_id']
            )
        
        else:
            raise ValidationError(
                message=f"Unknown action: {request_data['action']}",
                field="action",
                invalid_value=request_data['action']
            )
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            }),
            'headers': {
                'Content-Type': 'application/json',
                'X-Request-ID': context.aws_request_id
            }
        }
        
    except ValidationError as e:
        # Handle validation errors (400 Bad Request)
        response = error_formatter.format_for_api(e, include_details=True)
        return {
            'statusCode': 400,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'X-Error-ID': e.error_id
            }
        }
    
    except AuthenticationError as e:
        # Handle authentication errors (401 Unauthorized)
        response = error_formatter.format_for_api(e)
        return {
            'statusCode': 401,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'X-Error-ID': e.error_id
            }
        }
    
    except AuthorizationError as e:
        # Handle authorization errors (403 Forbidden)
        response = error_formatter.format_for_api(e)
        return {
            'statusCode': 403,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'X-Error-ID': e.error_id
            }
        }
    
    except NotFoundError as e:
        # Handle not found errors (404 Not Found)
        response = error_formatter.format_for_api(e)
        return {
            'statusCode': 404,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'X-Error-ID': e.error_id
            }
        }
    
    except BaseError as e:
        # Handle all other application errors
        metrics_collector.record_error(
            error=e,
            context={'lambda_function': context.function_name, 'request_id': context.aws_request_id}
        )
        
        response = error_formatter.format_for_api(e, include_details=True)
        status_code = 500
        
        if e.severity.value in ['critical']:
            status_code = 503  # Service Unavailable
        
        return {
            'statusCode': status_code,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'X-Error-ID': e.error_id
            }
        }
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in Lambda handler: {e}", exc_info=True)
        
        # Create BaseError for unexpected exceptions
        base_error = BaseError(
            message="Internal server error",
            cause=e,
            context={
                'lambda_function': context.function_name,
                'request_id': context.aws_request_id
            }
        )
        
        metrics_collector.record_error(base_error)
        response = error_formatter.format_for_api(base_error)
        
        return {
            'statusCode': 500,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'X-Error-ID': base_error.error_id
            }
        }


def _parse_lambda_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Lambda event data"""
    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        return body
        
    except json.JSONDecodeError as e:
        raise ValidationError(
            message="Invalid JSON in request body",
            field="body",
            cause=e
        )


# Usage Example: Retrofit Existing Service
def retrofit_existing_service():
    """
    Example of how to retrofit an existing service with error handling
    """
    
    # Original service method:
    """
    def send_message(self, phone_number, message):
        try:
            # AWS Pinpoint call
            response = self.client.send_text_message(...)
            return response
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    """
    
    # Enhanced version:
    """
    @error_handler(log_errors=True, collect_metrics=True)
    @retry_with_backoff(max_retries=3)
    async def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        # Input validation
        if not phone_number:
            raise ValidationError("Phone number is required", field="phone_number")
        
        # Use recovery manager
        result = await self.recovery_manager.execute_with_recovery(
            func=self._send_via_aws_pinpoint,
            operation_name="send_message",
            fallback_type="messaging",
            phone_number=phone_number,
            message=message
        )
        
        return result
    """
    
    print("""
    🔧 Service Retrofit Steps:
    
    1. Add error handling imports to existing service files
    2. Replace try/except blocks with @error_handler decorator
    3. Add input validation with ValidationError
    4. Convert external service calls to use ErrorRecoveryManager
    5. Add specific error types (PaymentError, InfrastructureError, etc.)
    6. Implement fallback responses for critical operations
    7. Add circuit breakers for unreliable external services
    8. Update Lambda handlers to use error formatting
    
    📁 Files to update:
    - src/services/messaging/
    - src/services/ai/
    - src/services/payment/
    - src/handlers/
    - src/api/
    """)


if __name__ == "__main__":
    retrofit_existing_service()
