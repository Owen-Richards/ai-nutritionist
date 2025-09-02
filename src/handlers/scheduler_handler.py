"""
Scheduler Handler for automatic weekly meal plan generation
Triggered by EventBridge cron schedule
"""

import json
import logging
import os
from typing import Dict, Any

import boto3

# Import our services
from services.ai_service import AIService
from services.user_service import UserService
from services.meal_plan_service import MealPlanService
from services.twilio_service import TwilioService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Initialize services
user_service = UserService(dynamodb)
ai_service = AIService()
meal_plan_service = MealPlanService(dynamodb, ai_service)
twilio_service = TwilioService()

# Set up service dependencies
meal_plan_service.set_user_service(user_service)


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for scheduled meal plan generation
    Runs weekly to generate meal plans for users with auto-plans enabled
    """
    try:
        logger.info("Starting scheduled meal plan generation")
        
        # Get users who have auto meal plans enabled
        auto_plan_users = user_service.get_users_for_auto_plans()
        logger.info(f"Found {len(auto_plan_users)} users with auto plans enabled")
        
        successful_plans = 0
        failed_plans = 0
        
        for user_id in auto_plan_users:
            try:
                # Get user profile
                user_profile = user_service.get_user_profile(user_id)
                if not user_profile:
                    logger.warning(f"Could not find profile for user {user_id}")
                    failed_plans += 1
                    continue
                
                # Generate new meal plan
                meal_plan = meal_plan_service.generate_meal_plan(user_profile, force_new=True)
                
                if meal_plan:
                    # Send meal plan to user
                    success = send_meal_plan_to_user(user_profile, meal_plan)
                    
                    if success:
                        successful_plans += 1
                        logger.info(f"Successfully generated and sent meal plan to user {user_id}")
                    else:
                        failed_plans += 1
                        logger.error(f"Failed to send meal plan to user {user_id}")
                else:
                    failed_plans += 1
                    logger.error(f"Failed to generate meal plan for user {user_id}")
                    
            except Exception as e:
                failed_plans += 1
                logger.error(f"Error processing user {user_id}: {str(e)}")
        
        # Log summary
        logger.info(f"Scheduled meal plan generation complete: {successful_plans} successful, {failed_plans} failed")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scheduled meal plan generation completed',
                'successful_plans': successful_plans,
                'failed_plans': failed_plans,
                'total_users': len(auto_plan_users)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in scheduled meal plan generation: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to complete scheduled meal plan generation',
                'message': str(e)
            })
        }


def send_meal_plan_to_user(user_profile: Dict[str, Any], meal_plan: Dict[str, Any]) -> bool:
    """
    Send generated meal plan to user via their preferred channel
    """
    try:
        phone_number = user_profile.get('phone_number')
        if not phone_number:
            logger.error(f"No phone number for user {user_profile.get('user_id')}")
            return False
        
        # Format meal plan message
        message = format_weekly_meal_plan_message(meal_plan)
        
        # Send via WhatsApp first, fallback to SMS
        success = twilio_service.send_whatsapp_message(phone_number, message)
        
        if not success:
            # Fallback to SMS
            success = twilio_service.send_sms(phone_number, message)
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending meal plan to user: {str(e)}")
        return False


def format_weekly_meal_plan_message(meal_plan: Dict[str, Any]) -> str:
    """
    Format meal plan for messaging (optimized for auto-generated plans)
    """
    try:
        message = "🍽️ **Your Weekly Meal Plan is Ready!**\n\n"
        
        days = meal_plan.get('days', [])
        for day_data in days:
            day_name = day_data.get('day', 'Unknown')
            message += f"**{day_name}:**\n"
            
            if 'breakfast' in day_data:
                message += f"🥐 {day_data['breakfast']}\n"
            if 'lunch' in day_data:
                message += f"🥙 {day_data['lunch']}\n"
            if 'dinner' in day_data:
                message += f"🍽️ {day_data['dinner']}\n"
            
            message += "\n"
        
        # Add helpful information
        if 'estimated_cost' in meal_plan:
            message += f"💰 Estimated cost: ${meal_plan['estimated_cost']}\n\n"
        
        message += "Reply 'grocery list' for shopping list! 🛒\n"
        message += "Have questions? Just ask! Reply 'help' for options."
        
        # Ensure message isn't too long for SMS/WhatsApp
        if len(message) > 1500:
            # Truncate and add continuation note
            message = message[:1400] + "...\n\nReply 'full plan' for complete details!"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting meal plan message: {str(e)}")
        return "Your weekly meal plan is ready! Reply 'meal plan' to see it."


def send_summary_notification(successful_plans: int, failed_plans: int, total_users: int):
    """
    Send summary notification to admin (optional feature)
    """
    try:
        # This could send an admin notification via email or Slack
        # For now, just log the summary
        logger.info(
            f"Weekly meal plan generation summary: "
            f"{successful_plans}/{total_users} successful "
            f"({failed_plans} failed)"
        )
        
        # In production, you might want to send this to CloudWatch metrics
        # or an admin notification channel
        
    except Exception as e:
        logger.error(f"Error sending summary notification: {str(e)}")


def cleanup_old_meal_plans():
    """
    Optional: Clean up old meal plans to save storage costs
    DynamoDB TTL should handle this automatically, but this is a backup
    """
    try:
        # This could scan for and delete very old meal plans
        # But since we're using DynamoDB TTL, this is optional
        logger.info("Cleanup would run here if needed")
        
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")


# Additional utility functions for scheduled operations

def generate_nutrition_tips_broadcast():
    """
    Optional: Send weekly nutrition tips to all users
    """
    try:
        # This could be another scheduled function to send
        # weekly nutrition tips or healthy eating reminders
        logger.info("Nutrition tips broadcast would run here")
        
    except Exception as e:
        logger.error(f"Error in nutrition tips broadcast: {str(e)}")


def analyze_user_engagement():
    """
    Optional: Analyze user engagement patterns for optimization
    """
    try:
        # This could analyze which users are most/least engaged
        # and adjust auto-plan frequency or content accordingly
        logger.info("User engagement analysis would run here")
        
    except Exception as e:
        logger.error(f"Error in engagement analysis: {str(e)}")
