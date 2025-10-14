"""
Error Handling Examples and Usage Patterns

This module demonstrates how to use the comprehensive error handling
system across different services and scenarios.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import our error handling system
from packages.shared.error_handling import (
    BaseError, DomainError, ValidationError, NotFoundError,
    InfrastructureError, PaymentError, RateLimitError,
    ErrorHandlingMiddleware, error_handler, circuit_breaker,
    retry_with_backoff, ErrorRecoveryManager, ErrorFormatter,
    ErrorMetricsCollector
)

logger = logging.getLogger(__name__)


# Example 1: Service-Level Error Handling
class NutritionService:
    """Example nutrition service with comprehensive error handling"""
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.metrics_collector = ErrorMetricsCollector()
        self.error_formatter = ErrorFormatter()
    
    @error_handler(log_errors=True, collect_metrics=True, reraise=True)
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def generate_meal_plan(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate meal plan with comprehensive error handling"""
        
        # Validate input
        if not user_id:
            raise ValidationError(
                message="User ID is required",
                field="user_id",
                invalid_value=user_id,
                validation_rules=["required", "non_empty"]
            )
        
        if not preferences.get('calories'):
            raise ValidationError(
                message="Calorie target is required",
                field="calories", 
                invalid_value=preferences.get('calories'),
                validation_rules=["required", "positive_number"]
            )
        
        # Business logic validation
        calories = preferences.get('calories', 0)
        if calories < 800 or calories > 5000:
            raise DomainError(
                message=f"Calorie target {calories} is outside healthy range (800-5000)",
                business_rule="healthy_calorie_range",
                context={'min_calories': 800, 'max_calories': 5000, 'requested': calories}
            )
        
        # Use recovery manager for external API calls
        result = await self.recovery_manager.execute_with_recovery(
            func=self._call_ai_service,
            operation_name="generate_meal_plan",
            fallback_type="meal_plan",
            user_id=user_id,
            preferences=preferences
        )
        
        if not result['success']:
            # Log error and return fallback
            logger.warning(f"Meal plan generation failed for user {user_id}, using fallback")
            return self._get_fallback_meal_plan(preferences)
        
        return result['data']
    
    async def _call_ai_service(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate calling external AI service"""
        # This would normally call OpenAI, etc.
        # Simulating potential failures
        import random
        
        if random.random() < 0.2:  # 20% failure rate for demo
            raise InfrastructureError(
                message="AI service timeout",
                service_name="openai",
                operation="generate_meal_plan",
                status_code=503
            )
        
        # Simulate successful response
        return {
            'meal_plan': {
                'breakfast': {'name': 'Oatmeal', 'calories': 300},
                'lunch': {'name': 'Salad', 'calories': 400},
                'dinner': {'name': 'Grilled Chicken', 'calories': 500}
            },
            'total_calories': 1200,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _get_fallback_meal_plan(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback meal plan when AI service fails"""
        return {
            'meal_plan': {
                'breakfast': {'name': 'Oatmeal with Berries', 'calories': 300},
                'lunch': {'name': 'Turkey Sandwich', 'calories': 400},
                'dinner': {'name': 'Baked Salmon', 'calories': 450}
            },
            'total_calories': 1150,
            'fallback': True,
            'note': 'This is a basic meal plan. Our AI service will be back soon for personalized recommendations!'
        }


# Example 2: Payment Service with Specific Error Types
class PaymentService:
    """Example payment service with payment-specific error handling"""
    
    def __init__(self):
        self.metrics_collector = ErrorMetricsCollector()
    
    @circuit_breaker(failure_threshold=5, recovery_timeout=120)
    @error_handler(log_errors=True, collect_metrics=True)
    async def process_payment(
        self, 
        user_id: str, 
        amount: float, 
        payment_method: str,
        transaction_id: str
    ) -> Dict[str, Any]:
        """Process payment with specialized error handling"""
        
        # Validate payment amount
        if amount <= 0:
            raise ValidationError(
                message="Payment amount must be positive",
                field="amount",
                invalid_value=amount,
                validation_rules=["positive", "greater_than_zero"]
            )
        
        if amount > 10000:  # $10k limit
            raise DomainError(
                message=f"Payment amount ${amount} exceeds maximum limit",
                business_rule="payment_limit",
                context={'max_amount': 10000, 'requested_amount': amount}
            )
        
        try:
            # Simulate payment processing
            result = await self._process_with_provider(amount, payment_method, transaction_id)
            
            # Record successful payment
            self.metrics_collector.record_success("process_payment", 500.0)  # 500ms
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'amount': amount,
                'status': 'completed'
            }
            
        except Exception as e:
            # Convert to specific payment error
            if "insufficient funds" in str(e).lower():
                raise PaymentError(
                    message="Insufficient funds for this transaction",
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    amount=amount,
                    currency="USD",
                    provider_error_code="INSUFFICIENT_FUNDS"
                )
            elif "card declined" in str(e).lower():
                raise PaymentError(
                    message="Card was declined by the issuer",
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    amount=amount,
                    currency="USD",
                    provider_error_code="CARD_DECLINED"
                )
            else:
                raise PaymentError(
                    message=f"Payment processing failed: {str(e)}",
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    amount=amount,
                    currency="USD",
                    cause=e
                )
    
    async def _process_with_provider(self, amount: float, payment_method: str, transaction_id: str):
        """Simulate payment provider API call"""
        import random
        
        # Simulate various payment failures
        failure_type = random.random()
        
        if failure_type < 0.1:  # 10% insufficient funds
            raise Exception("Insufficient funds")
        elif failure_type < 0.15:  # 5% card declined
            raise Exception("Card declined")
        elif failure_type < 0.2:  # 5% network timeout
            raise Exception("Network timeout")
        
        # Success
        return {"status": "success", "provider_transaction_id": f"txn_{transaction_id}"}


# Example 3: API Handler with Middleware
class APIHandler:
    """Example API handler using error handling middleware"""
    
    def __init__(self):
        self.nutrition_service = NutritionService()
        self.payment_service = PaymentService()
        self.error_formatter = ErrorFormatter()
    
    async def handle_meal_plan_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle meal plan API request"""
        try:
            user_id = request_data.get('user_id')
            preferences = request_data.get('preferences', {})
            
            # Generate meal plan
            meal_plan = await self.nutrition_service.generate_meal_plan(user_id, preferences)
            
            return {
                'success': True,
                'data': meal_plan,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except BaseError as e:
            # Format error for API response
            return self.error_formatter.format_for_api(e, include_details=True)
        
        except Exception as e:
            # Handle unexpected errors
            error = BaseError(
                message="Unexpected error occurred",
                cause=e,
                context={'endpoint': 'meal_plan', 'request_data': request_data}
            )
            return self.error_formatter.format_for_api(error)
    
    async def handle_payment_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment API request"""
        try:
            result = await self.payment_service.process_payment(
                user_id=request_data['user_id'],
                amount=request_data['amount'],
                payment_method=request_data['payment_method'],
                transaction_id=request_data['transaction_id']
            )
            
            return {
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except PaymentError as e:
            # Special handling for payment errors
            response = self.error_formatter.format_for_api(e, include_details=True)
            
            # Add payment-specific context
            response['payment_context'] = {
                'transaction_id': e.transaction_id,
                'amount': e.amount,
                'payment_method': e.payment_method,
                'can_retry': e.recoverable
            }
            
            return response
            
        except BaseError as e:
            return self.error_formatter.format_for_api(e)


# Example 4: Chat/Messaging Error Handling
class ChatHandler:
    """Example chat handler with user-friendly error messages"""
    
    def __init__(self):
        self.nutrition_service = NutritionService()
        self.error_formatter = ErrorFormatter()
    
    async def handle_chat_message(self, user_id: str, message: str) -> str:
        """Handle chat message with user-friendly error responses"""
        try:
            # Parse user intent
            if "meal plan" in message.lower():
                preferences = self._extract_preferences(message)
                meal_plan = await self.nutrition_service.generate_meal_plan(user_id, preferences)
                return self._format_meal_plan_response(meal_plan)
            
            # Handle other intents...
            return "I can help you with meal planning! Just ask for a meal plan."
            
        except ValidationError as e:
            # User-friendly validation messages
            return self.error_formatter.format_for_user(e, context="chat")
        
        except RateLimitError as e:
            # Special handling for rate limits in chat
            return f"Whoa there! 🐌 You're sending messages too quickly. Please wait {e.retry_after} seconds and try again."
        
        except BaseError as e:
            # Generic user-friendly message
            return self.error_formatter.format_for_user(e, context="chat")
        
        except Exception as e:
            # Handle unexpected errors gracefully
            logger.error(f"Unexpected error in chat handler: {e}")
            return "Oops! Something went wrong. Let me try that again! 😅"
    
    def _extract_preferences(self, message: str) -> Dict[str, Any]:
        """Extract preferences from chat message"""
        # Simple extraction logic for demo
        preferences = {'calories': 1800}  # Default
        
        if "1500" in message:
            preferences['calories'] = 1500
        elif "2000" in message:
            preferences['calories'] = 2000
        
        return preferences
    
    def _format_meal_plan_response(self, meal_plan: Dict[str, Any]) -> str:
        """Format meal plan for chat response"""
        if meal_plan.get('fallback'):
            return "I'm having some technical difficulties, but here's a basic meal plan to get you started! 🍽️\n\n" + \
                   f"• Breakfast: {meal_plan['meal_plan']['breakfast']['name']}\n" + \
                   f"• Lunch: {meal_plan['meal_plan']['lunch']['name']}\n" + \
                   f"• Dinner: {meal_plan['meal_plan']['dinner']['name']}"
        
        return f"Here's your personalized meal plan! 🎉\n\n" + \
               f"• Breakfast: {meal_plan['meal_plan']['breakfast']['name']}\n" + \
               f"• Lunch: {meal_plan['meal_plan']['lunch']['name']}\n" + \
               f"• Dinner: {meal_plan['meal_plan']['dinner']['name']}"


# Example 5: Background Job Error Handling
class BackgroundJobProcessor:
    """Example background job processor with error recovery"""
    
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.metrics_collector = ErrorMetricsCollector()
    
    @retry_with_backoff(
        max_retries=5,
        base_delay=2.0,
        max_delay=300.0,
        retryable_exceptions=(InfrastructureError, ConnectionError)
    )
    async def process_nutrition_analysis_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process nutrition analysis background job"""
        
        job_id = job_data.get('job_id')
        user_id = job_data.get('user_id')
        
        try:
            # Execute with recovery
            result = await self.recovery_manager.execute_with_recovery(
                func=self._analyze_nutrition,
                operation_name="nutrition_analysis_job",
                fallback_type="nutrition_analysis",
                job_data=job_data
            )
            
            if result['success']:
                logger.info(f"Job {job_id} completed successfully")
                return result['data']
            else:
                # Job failed but we have fallback
                logger.warning(f"Job {job_id} failed, using fallback result")
                await self._queue_for_retry(job_data)
                return result
                
        except Exception as e:
            # Handle job failure
            logger.error(f"Job {job_id} failed completely: {e}")
            
            # Record failure metric
            self.metrics_collector.record_critical_failure("nutrition_analysis_job", e, 1)
            
            # Notify user of failure
            await self._notify_user_of_failure(user_id, job_id, str(e))
            
            raise
    
    async def _analyze_nutrition(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform nutrition analysis"""
        # Simulate analysis work
        import random
        
        if random.random() < 0.3:  # 30% failure rate for demo
            raise InfrastructureError(
                message="Nutrition database unavailable",
                service_name="nutrition_db",
                operation="analyze_nutrition"
            )
        
        return {
            'analysis': {
                'calories': 1850,
                'protein': 120,
                'carbs': 200,
                'fat': 65,
                'fiber': 25
            },
            'recommendations': [
                'Increase vegetable intake',
                'Consider more lean protein',
                'Stay hydrated'
            ]
        }
    
    async def _queue_for_retry(self, job_data: Dict[str, Any]):
        """Queue job for retry"""
        # In real implementation, would use SQS or similar
        logger.info(f"Queuing job {job_data['job_id']} for retry")
    
    async def _notify_user_of_failure(self, user_id: str, job_id: str, error_message: str):
        """Notify user of job failure"""
        # In real implementation, would send notification
        logger.info(f"Notifying user {user_id} of job {job_id} failure")


# Example 6: Health Check with Error Monitoring
class HealthCheckService:
    """Health check service that reports on error conditions"""
    
    def __init__(self):
        self.metrics_collector = ErrorMetricsCollector()
        self.recovery_manager = ErrorRecoveryManager()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including error metrics"""
        try:
            # Get error analytics
            error_analytics = self.metrics_collector.get_error_analytics(time_window_hours=1)
            
            # Get circuit breaker status
            circuit_breaker_status = self.recovery_manager.get_circuit_breaker_status()
            
            # Determine overall health
            health_status = "healthy"
            issues = []
            
            if error_analytics['total_errors'] > 50:
                health_status = "degraded"
                issues.append("High error rate detected")
            
            if error_analytics.get('severity_distribution', {}).get('critical', 0) > 0:
                health_status = "unhealthy"
                issues.append("Critical errors present")
            
            # Check circuit breakers
            open_breakers = [
                name for name, status in circuit_breaker_status.items()
                if status['state'] == 'open'
            ]
            
            if open_breakers:
                health_status = "degraded"
                issues.append(f"Circuit breakers open: {', '.join(open_breakers)}")
            
            return {
                'status': health_status,
                'timestamp': datetime.utcnow().isoformat(),
                'issues': issues,
                'error_summary': {
                    'total_errors_1h': error_analytics['total_errors'],
                    'error_rate': error_analytics['error_rate'],
                    'critical_errors': error_analytics.get('severity_distribution', {}).get('critical', 0)
                },
                'circuit_breakers': circuit_breaker_status,
                'recommendations': error_analytics.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unknown',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }


# Example Usage
async def main():
    """Example usage of the error handling system"""
    
    # Create services
    nutrition_service = NutritionService()
    payment_service = PaymentService()
    api_handler = APIHandler()
    chat_handler = ChatHandler()
    
    print("🚀 Error Handling System Examples\n")
    
    # Example 1: Successful meal plan generation
    print("1. Generating meal plan...")
    try:
        meal_plan = await nutrition_service.generate_meal_plan(
            user_id="user123",
            preferences={'calories': 1800, 'diet': 'balanced'}
        )
        print(f"✅ Success: {meal_plan.get('total_calories', 'N/A')} calories")
    except BaseError as e:
        print(f"❌ Error: {e.user_message}")
    
    # Example 2: Payment processing with error
    print("\n2. Processing payment...")
    try:
        result = await payment_service.process_payment(
            user_id="user123",
            amount=29.99,
            payment_method="card_123",
            transaction_id="txn_456"
        )
        print(f"✅ Payment successful: {result['transaction_id']}")
    except PaymentError as e:
        print(f"💳 Payment failed: {e.user_message}")
    
    # Example 3: Chat interaction
    print("\n3. Chat interaction...")
    response = await chat_handler.handle_chat_message(
        user_id="user123",
        message="Can you create a 1500 calorie meal plan?"
    )
    print(f"🤖 Bot: {response}")
    
    # Example 4: API request handling
    print("\n4. API request...")
    api_response = await api_handler.handle_meal_plan_request({
        'user_id': 'user123',
        'preferences': {'calories': 2000}
    })
    print(f"📡 API Response: {'Success' if api_response.get('success') else 'Error'}")
    
    # Example 5: Health check
    print("\n5. Health check...")
    health_service = HealthCheckService()
    health_status = await health_service.get_health_status()
    print(f"🏥 System Health: {health_status['status']}")
    
    print("\n✨ Error handling examples completed!")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
