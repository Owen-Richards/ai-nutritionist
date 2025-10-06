"""
Advanced Messaging Handler for Conversational AI Nutritionist
Handles SMS/messaging integration with enhanced AWS End User Messaging and cost optimization
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..services.conversational_ai import ConversationalNutritionistAI
from ..services.messaging.cost_aware_handler import process_nutrition_request_with_optimization
from ..models.user_profile import UserProfile


class MessageType:
    SMS = "sms"
    MMS = "mms"  # For images/photos
    VOICE = "voice"
    EMAIL = "email"


class MessageStatus:
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class ConversationalNutritionistHandler:
    """Enhanced messaging handler for conversational AI nutritionist"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ai_nutritionist = ConversationalNutritionistAI()
        
        # AWS End User Messaging client
        try:
            self.sms_client = boto3.client('pinpoint-sms-voice-v2')
            self.aws_end_user_messaging_client = boto3.client('pinpoint')
        except NoCredentialsError:
            self.logger.warning("AWS credentials not found. SMS functionality will be limited.")
            self.sms_client = None
            self.aws_end_user_messaging_client = None
        
        # Message tracking
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.origination_number = None  # Will be set from environment
        self.application_id = None  # AWS End User Messaging application ID (legacy)
        
        # Enhanced features
        self.auto_responses = {
            "help": "Hi! I'm your AI nutritionist. I can help with meal planning, food tracking, recipes, grocery lists, and health insights. What would you like to work on?",
            "stop": "You've been unsubscribed from nutrition messages. Text START to resume.",
            "start": "Welcome back! I'm here to help with your nutrition journey. How can I assist you today?"
        }
        
        # Photo analysis capabilities (for food photos)
        self.photo_analysis_enabled = True
    
    def handle_incoming_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming messages from AWS End User Messaging
        Enhanced to support multiple message types and rich interactions
        """
        try:
            # Extract message details from AWS event
            message_data = self._parse_aws_event(event)
            
            if not message_data:
                self.logger.error("Failed to parse AWS event")
                return self._create_error_response("Invalid message format")
            
            phone_number = message_data["phone_number"]
            message_body = message_data["message_body"]
            message_type = message_data.get("message_type", MessageType.SMS)
            
            # Log incoming message
            self._log_message(phone_number, message_body, "incoming", message_type)
            
            # Handle special commands first
            if message_body.lower().strip() in self.auto_responses:
                response_text = self.auto_responses[message_body.lower().strip()]
                return self._send_response(phone_number, response_text, MessageType.SMS)
            
            # Handle image messages (food photos)
            if message_type == MessageType.MMS and "media_url" in message_data:
                return self._handle_food_photo(phone_number, message_data["media_url"], message_body)
            
            # Cost-optimized request processing
            should_process, optimization_info = process_nutrition_request_with_optimization(
                user_phone=phone_number,
                message=message_body,
                request_type=self._classify_request_type(message_body),
                user_tier=self._get_user_tier(phone_number)
            )
            
            # If request is rejected by cost optimization
            if not should_process:
                user_message = optimization_info.get('user_message')
                if user_message:
                    return self._send_cost_optimized_response(phone_number, user_message, optimization_info)
                else:
                    return self._send_error_response(phone_number, "Request could not be processed at this time.")
            
            # If request has warnings (throttling, etc.)
            if optimization_info.get('warning') or optimization_info.get('processing_delay', 0) > 0:
                self._handle_optimization_warning(phone_number, optimization_info)
            
            # Process through AI nutritionist (costs have been validated)
            ai_response = self.ai_nutritionist.process_message(
                phone_number, 
                message_body, 
                metadata=optimization_info.get('metadata', {})
            )
            
            # Send response with enhanced formatting
            return self._send_enhanced_response(phone_number, ai_response, optimization_info)
            
        except Exception as e:
            self.logger.error(f"Error handling incoming message: {str(e)}")
            return self._send_error_response(phone_number if 'phone_number' in locals() else None, str(e))
    
    def _parse_aws_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse AWS End User Messaging event"""
        try:
            # Handle different AWS event formats
            if "Records" in event:
                # SNS/SQS format
                for record in event["Records"]:
                    if "Sns" in record:
                        message = json.loads(record["Sns"]["Message"])
                    elif "body" in record:
                        message = json.loads(record["body"])
                    else:
                        continue
                    
                    return self._extract_message_data(message)
            
            elif "messageBody" in event or "message" in event:
                # Direct AWS End User Messaging format
                return self._extract_message_data(event)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing AWS event: {str(e)}")
            return None
    
    def _extract_message_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from various AWS formats"""
        result = {}
        
        # Phone number extraction
        if "originationNumber" in message:
            result["phone_number"] = message["originationNumber"]
        elif "sourceNumber" in message:
            result["phone_number"] = message["sourceNumber"]
        elif "from" in message:
            result["phone_number"] = message["from"]
        
        # Message body extraction
        if "messageBody" in message:
            result["message_body"] = message["messageBody"]
        elif "message" in message:
            result["message_body"] = message["message"]
        elif "body" in message:
            result["message_body"] = message["body"]
        
        # Message type detection
        result["message_type"] = MessageType.SMS
        if "media" in message or "mediaUrl" in message:
            result["message_type"] = MessageType.MMS
            result["media_url"] = message.get("mediaUrl") or message.get("media", [{}])[0].get("url")
        
        # Additional metadata
        result["timestamp"] = message.get("timestamp", datetime.utcnow().isoformat())
        result["message_id"] = message.get("messageId", f"msg_{datetime.utcnow().timestamp()}")
        
        return result
    
    def _handle_food_photo(self, phone_number: str, media_url: str, caption: str = "") -> Dict[str, Any]:
        """Handle food photo analysis"""
        try:
            if not self.photo_analysis_enabled:
                return self._send_response(
                    phone_number, 
                    "Photo analysis is currently unavailable. Please describe what you ate instead.",
                    MessageType.SMS
                )
            
            # Placeholder for photo analysis
            # In production, this would integrate with AWS Rekognition or similar service
            food_analysis = self._analyze_food_photo(media_url)
            
            if food_analysis:
                response_text = f"📸 I can see {food_analysis['food_name']} in your photo!\n\n"
                response_text += f"Estimated: {food_analysis['calories']} calories\n"
                response_text += f"Would you like me to log this for you?"
                
                # Add to pending actions for confirmation
                self._add_pending_food_log(phone_number, food_analysis)
                
                return self._send_response(phone_number, response_text, MessageType.SMS)
            else:
                return self._send_response(
                    phone_number,
                    "I couldn't identify the food in your photo. Can you tell me what you ate?",
                    MessageType.SMS
                )
                
        except Exception as e:
            self.logger.error(f"Error handling food photo: {str(e)}")
            return self._send_response(
                phone_number,
                "I had trouble analyzing your photo. Please describe what you ate instead.",
                MessageType.SMS
            )
    
    def _analyze_food_photo(self, media_url: str) -> Optional[Dict[str, Any]]:
        """Analyze food photo using AI/ML services"""
        # Placeholder for photo analysis
        # In production, this would integrate with:
        # - AWS Rekognition for food detection
        # - Custom ML models for nutrition estimation
        # - Food database lookup
        
        return {
            "food_name": "grilled chicken breast",
            "calories": 185,
            "protein_g": 35,
            "confidence": 0.85
        }
    
    def _send_enhanced_response(self, phone_number: str, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Send enhanced response with formatting and suggestions"""
        try:
            message_text = ai_response["message"]
            
            # Add suggestions if available
            suggestions = ai_response.get("suggestions", [])
            if suggestions:
                message_text += f"\n\n💡 Quick options:\n"
                for i, suggestion in enumerate(suggestions[:3], 1):  # Limit to 3 suggestions
                    message_text += f"{i}. {suggestion}\n"
                message_text += "\nJust reply with the number or tell me what you'd like to do!"
            
            # Send main response
            response = self._send_response(phone_number, message_text, MessageType.SMS)
            
            # Send follow-up data if needed
            self._handle_follow_up_actions(phone_number, ai_response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced response: {str(e)}")
            return self._send_error_response(phone_number, str(e))
    
    def _handle_follow_up_actions(self, phone_number: str, ai_response: Dict[str, Any]) -> None:
        """Handle follow-up actions based on AI response"""
        actions = ai_response.get("actions", [])
        
        for action in actions:
            if action == "meal_plan_created":
                # Schedule reminder to check grocery list
                self._schedule_reminder(
                    phone_number,
                    "Don't forget to generate your grocery list for the week! 🛒",
                    datetime.utcnow() + timedelta(hours=2)
                )
            
            elif action == "goals_set":
                # Schedule daily check-in
                self._schedule_daily_checkin(phone_number)
            
            elif action == "food_logged":
                # Suggest water intake if it's been a while
                self._suggest_water_if_needed(phone_number)
    
    def _send_response(self, phone_number: str, message: str, message_type: str = MessageType.SMS) -> Dict[str, Any]:
        """Send response message via AWS End User Messaging"""
        try:
            if not self.sms_client or not phone_number:
                self.logger.warning("SMS client not available or phone number missing")
                return self._create_error_response("Unable to send message")
            
            # Ensure message length is within SMS limits
            if len(message) > 1600:
                message = message[:1597] + "..."
            
            # Send via AWS End User Messaging
            response = self.sms_client.send_text_message(
                DestinationPhoneNumber=phone_number,
                OriginationIdentity=self.origination_number,
                MessageBody=message,
                MessageType='TRANSACTIONAL',
                ConfigurationSetName='nutrition-ai-config'  # Optional
            )
            
            # Log outgoing message
            self._log_message(phone_number, message, "outgoing", message_type)
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Response sent successfully",
                    "messageId": response.get("MessageId"),
                    "phone_number": phone_number
                })
            }
            
        except ClientError as e:
            self.logger.error(f"AWS SMS error: {str(e)}")
            return self._create_error_response(f"Failed to send SMS: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error sending response: {str(e)}")
            return self._create_error_response(f"Unexpected error: {str(e)}")
    
    def _log_message(self, phone_number: str, message: str, direction: str, message_type: str) -> None:
        """Log message for conversation history"""
        if phone_number not in self.message_history:
            self.message_history[phone_number] = []
        
        self.message_history[phone_number].append({
            "timestamp": datetime.utcnow().isoformat(),
            "direction": direction,
            "message": message,
            "message_type": message_type
        })
        
        # Keep only last 100 messages per user
        if len(self.message_history[phone_number]) > 100:
            self.message_history[phone_number] = self.message_history[phone_number][-100:]
    
    def _schedule_reminder(self, phone_number: str, message: str, send_time: datetime) -> None:
        """Schedule a reminder message"""
        # In production, this would integrate with AWS EventBridge or similar
        self.logger.info(f"Reminder scheduled for {phone_number} at {send_time}: {message}")
    
    def _schedule_daily_checkin(self, phone_number: str) -> None:
        """Schedule daily nutrition check-in"""
        # Schedule daily reminder at 7 PM
        checkin_message = "🌟 How did your nutrition go today? Share your wins or challenges!"
        
        # This would integrate with AWS EventBridge for recurring schedules
        self.logger.info(f"Daily check-in scheduled for {phone_number}")
    
    def _suggest_water_if_needed(self, phone_number: str) -> None:
        """Suggest water intake if user hasn't logged water recently"""
        # Check last water log and suggest if needed
        # This would integrate with the health tracker
        pass
    
    def _add_pending_food_log(self, phone_number: str, food_data: Dict[str, Any]) -> None:
        """Add pending food log for user confirmation"""
        if phone_number not in self.active_conversations:
            self.active_conversations[phone_number] = {}
        
        self.active_conversations[phone_number]["pending_food_log"] = food_data
    
    def _send_error_response(self, phone_number: Optional[str], error_message: str) -> Dict[str, Any]:
        """Send error response to user"""
        if phone_number:
            error_msg = "I encountered an issue processing your request. Please try again or contact support if the problem persists."
            self._send_response(phone_number, error_msg, MessageType.SMS)
        
        return self._create_error_response(error_message)
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat()
            })
        }
    
    def send_proactive_message(self, phone_number: str, message: str, context: str = None) -> Dict[str, Any]:
        """Send proactive message (reminders, notifications, etc.)"""
        try:
            # Add context if provided
            if context:
                message = f"[{context}] {message}"
            
            return self._send_response(phone_number, message, MessageType.SMS)
            
        except Exception as e:
            self.logger.error(f"Error sending proactive message: {str(e)}")
            return self._create_error_response(str(e))
    
    def get_conversation_history(self, phone_number: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        history = self.message_history.get(phone_number, [])
        return history[-limit:] if len(history) > limit else history
    
    def get_user_engagement_stats(self, phone_number: str) -> Dict[str, Any]:
        """Get user engagement statistics"""
        history = self.message_history.get(phone_number, [])
        
        if not history:
            return {"total_messages": 0, "first_contact": None, "last_contact": None}
        
        total_messages = len(history)
        incoming_messages = len([m for m in history if m["direction"] == "incoming"])
        outgoing_messages = len([m for m in history if m["direction"] == "outgoing"])
        
        # Calculate engagement frequency
        if len(history) >= 2:
            first_time = datetime.fromisoformat(history[0]["timestamp"])
            last_time = datetime.fromisoformat(history[-1]["timestamp"])
            days_active = (last_time - first_time).days + 1
            messages_per_day = total_messages / days_active if days_active > 0 else 0
        else:
            messages_per_day = 0
        
        return {
            "total_messages": total_messages,
            "incoming_messages": incoming_messages,
            "outgoing_messages": outgoing_messages,
            "messages_per_day": round(messages_per_day, 2),
            "first_contact": history[0]["timestamp"] if history else None,
            "last_contact": history[-1]["timestamp"] if history else None
        }
    
    def handle_user_preferences(self, phone_number: str, preferences: Dict[str, Any]) -> None:
        """Update user messaging preferences"""
        # Store preferences for message frequency, time preferences, etc.
        if phone_number not in self.active_conversations:
            self.active_conversations[phone_number] = {}
        
        self.active_conversations[phone_number]["preferences"] = preferences
        
        # Update user profile with preferences
        user_profile = self.ai_nutritionist._get_user_profile(phone_number)
        user_profile.communication_preferences.update(preferences)
    
    def send_bulk_nutrition_tips(self, phone_numbers: List[str], tip: str) -> Dict[str, Any]:
        """Send nutrition tips to multiple users"""
        results = []
        
        for phone_number in phone_numbers:
            try:
                result = self.send_proactive_message(
                    phone_number,
                    f"💡 Nutrition Tip: {tip}",
                    "Weekly Tip"
                )
                results.append({
                    "phone_number": phone_number,
                    "status": "success" if result.get("statusCode") == 200 else "failed"
                })
            except Exception as e:
                results.append({
                    "phone_number": phone_number,
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "total_sent": len([r for r in results if r["status"] == "success"]),
            "total_failed": len([r for r in results if r["status"] == "failed"]),
            "results": results
        }


# AWS Lambda handler for the messaging service
def lambda_handler(event, context):
    """AWS Lambda handler for conversational nutritionist messaging"""
    
    # Initialize handler
    handler = ConversationalNutritionistHandler()
    
    # Set configuration from environment variables
    import os
    handler.origination_number = os.environ.get('ORIGINATION_NUMBER')
    handler.application_id = os.environ.get('PINPOINT_APPLICATION_ID')
    
    try:
        # Handle the incoming message
        response = handler.handle_incoming_message(event)
        
        # Log successful processing
        logging.info(f"Successfully processed message: {response}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error in lambda handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "timestamp": datetime.utcnow().isoformat()
            })
        }

    def _classify_request_type(self, message: str) -> str:
        """Classify the type of nutrition request for cost optimization"""
        message_lower = message.lower()
        
        # High-value request types
        if any(keyword in message_lower for keyword in ['meal plan', 'weekly plan', 'diet plan']):
            return 'meal_plan'
        elif any(keyword in message_lower for keyword in ['nutrition', 'calories', 'macro', 'vitamin']):
            return 'nutrition_analysis'
        elif any(keyword in message_lower for keyword in ['recipe', 'cook', 'prepare']):
            return 'recipe_search'
        elif any(keyword in message_lower for keyword in ['grocery', 'shopping', 'buy', 'list']):
            return 'grocery_list'
        elif any(keyword in message_lower for keyword in ['diet', 'weight', 'health', 'advice']):
            return 'dietary_advice'
        else:
            return 'simple_message'

    def _get_user_tier(self, phone_number: str) -> str:
        """Get user tier for cost optimization (integrate with your billing system)"""
        try:
            # This would integrate with your actual billing/subscription system
            # For now, return 'free' as default
            return 'free'
        except Exception:
            return 'free'

    def _send_cost_optimized_response(self, phone_number: str, user_message: str, optimization_info: Dict[str, Any]) -> Dict[str, Any]:
        """Send a response for cost-optimized (rejected) requests"""
        try:
            # Log the cost optimization
            self.logger.info(f"Cost optimization applied for {phone_number}: {optimization_info.get('reason')}")
            
            # Send user-friendly message
            response = self._send_response(phone_number, user_message, MessageType.SMS)
            
            # Add optimization metadata to response
            if isinstance(response, dict):
                response['cost_optimization'] = {
                    'applied': True,
                    'reason': optimization_info.get('reason'),
                    'estimated_cost_saved': optimization_info.get('estimated_cost_saved', 0),
                    'efficiency': optimization_info.get('cost_efficiency', 'unknown')
                }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error sending cost-optimized response: {str(e)}")
            return self._send_error_response(phone_number, "Unable to process request at this time.")

    def _handle_optimization_warning(self, phone_number: str, optimization_info: Dict[str, Any]):
        """Handle optimization warnings (throttling, usage warnings, etc.)"""
        try:
            warning_message = optimization_info.get('user_message')
            processing_delay = optimization_info.get('processing_delay', 0)
            
            if warning_message:
                # Send warning message first
                self._send_response(phone_number, warning_message, MessageType.SMS)
            
            if processing_delay > 0:
                # Add processing delay
                import time
                time.sleep(processing_delay)
                
        except Exception as e:
            self.logger.error(f"Error handling optimization warning: {str(e)}")

    def _send_enhanced_response(self, phone_number: str, ai_response: str, optimization_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send enhanced response with cost optimization metadata"""
        try:
            # Send the AI response
            response = self._send_response(phone_number, ai_response, MessageType.SMS)
            
            # Add cost optimization info if available
            if optimization_info and isinstance(response, dict):
                response['cost_optimization'] = {
                    'applied': optimization_info.get('optimization_applied', False),
                    'estimated_cost': optimization_info.get('estimated_cost', 0),
                    'efficiency': optimization_info.get('cost_efficiency', 'optimal'),
                    'metadata': optimization_info.get('metadata', {})
                }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced response: {str(e)}")
            return self._send_error_response(phone_number, "Unable to send response.")


# Health check endpoint
def health_check_handler(event, context):
    """Health check endpoint for the messaging service"""
    
    try:
        # Basic health checks
        checks = {
            "service": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
        
        # Check AWS services availability
        try:
            boto3.client('pinpoint-sms-voice-v2')
            checks["aws_sms"] = "healthy"
        except Exception:
            checks["aws_sms"] = "unavailable"
        
        return {
            "statusCode": 200,
            "body": json.dumps(checks)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        }
