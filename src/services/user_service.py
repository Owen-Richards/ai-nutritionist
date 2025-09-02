"""
User Service for managing user profiles and preferences in DynamoDB
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user data and preferences"""
    
    def __init__(self, dynamodb_resource):
        self.dynamodb = dynamodb_resource
        self.table_name = os.environ.get('DYNAMODB_TABLE', 'ai-nutritionist-users-dev')
        self.table = self.dynamodb.Table(self.table_name)
    
    def get_or_create_user(self, phone_number: str) -> Dict[str, Any]:
        """
        Get existing user or create new user profile
        """
        try:
            user_id = self._normalize_phone_number(phone_number)
            
            # Try to get existing user
            response = self.table.get_item(
                Key={
                    'user_id': user_id,
                    'plan_date': 'profile'
                }
            )
            
            if 'Item' in response:
                user_profile = response['Item']
                user_profile['is_new_user'] = False
                logger.info(f"Retrieved existing user: {user_id}")
                return user_profile
            
            # Create new user
            user_profile = self._create_new_user(user_id, phone_number)
            logger.info(f"Created new user: {user_id}")
            return user_profile
            
        except Exception as e:
            logger.error(f"Error getting/creating user {phone_number}: {str(e)}")
            # Return default profile to prevent service disruption
            return self._get_default_profile(phone_number)
    
    def update_preferences_from_message(self, user_id: str, message: str) -> bool:
        """
        Update user preferences based on natural language message
        """
        try:
            # Get current profile
            current_profile = self.get_user_profile(user_id)
            if not current_profile:
                return False
            
            # Extract preferences from message
            preferences = self._extract_preferences_from_text(message)
            
            # Update profile with new preferences
            updated_profile = {**current_profile, **preferences}
            updated_profile['last_updated'] = datetime.utcnow().isoformat()
            
            # Save to DynamoDB
            self.table.put_item(Item=updated_profile)
            
            logger.info(f"Updated preferences for user {user_id}: {preferences}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences for {user_id}: {str(e)}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by user ID
        """
        try:
            response = self.table.get_item(
                Key={
                    'user_id': user_id,
                    'plan_date': 'profile'
                }
            )
            
            return response.get('Item')
            
        except Exception as e:
            logger.error(f"Error getting profile for {user_id}: {str(e)}")
            return None
    
    def save_meal_plan(self, user_id: str, meal_plan: Dict[str, Any], plan_date: str = None) -> bool:
        """
        Save meal plan for user
        """
        try:
            if not plan_date:
                plan_date = datetime.utcnow().strftime('%Y-%m-%d')
            
            meal_plan_item = {
                'user_id': user_id,
                'plan_date': plan_date,
                'meal_plan': meal_plan,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())  # Auto-delete after 30 days
            }
            
            self.table.put_item(Item=meal_plan_item)
            logger.info(f"Saved meal plan for user {user_id}, date {plan_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving meal plan for {user_id}: {str(e)}")
            return False
    
    def get_recent_meal_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent meal plan for user
        """
        try:
            # Query for recent meal plans (last 7 days)
            start_date = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            response = self.table.query(
                KeyConditionExpression='user_id = :user_id AND plan_date >= :start_date',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':start_date': start_date
                },
                ScanIndexForward=False,  # Descending order
                Limit=1
            )
            
            if response['Items']:
                return response['Items'][0].get('meal_plan')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting recent meal plan for {user_id}: {str(e)}")
            return None
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete all user data (GDPR compliance)
        """
        try:
            # Get all items for this user
            response = self.table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            
            # Delete all items
            with self.table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={
                            'user_id': item['user_id'],
                            'plan_date': item['plan_date']
                        }
                    )
            
            logger.info(f"Deleted all data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False
    
    def get_users_for_auto_plans(self) -> List[str]:
        """
        Get list of users who have auto meal plans enabled
        """
        try:
            # Scan for users with auto_plans enabled
            response = self.table.scan(
                FilterExpression='plan_date = :profile AND auto_plans = :enabled',
                ExpressionAttributeValues={
                    ':profile': 'profile',
                    ':enabled': True
                },
                ProjectionExpression='user_id'
            )
            
            return [item['user_id'] for item in response['Items']]
            
        except Exception as e:
            logger.error(f"Error getting auto plan users: {str(e)}")
            return []
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """
        Normalize phone number for consistent storage
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone_number)
        
        # Add country code if missing (assume US)
        if len(digits) == 10:
            digits = '1' + digits
        
        return digits
    
    def _create_new_user(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """
        Create new user profile with defaults
        """
        user_profile = {
            'user_id': user_id,
            'plan_date': 'profile',
            'phone_number': phone_number,
            'created_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat(),
            'is_new_user': True,
            'dietary_restrictions': [],
            'allergies': [],
            'household_size': 2,
            'weekly_budget': 75,
            'fitness_goals': 'maintenance',
            'auto_plans': False,
            'calendar_connected': False,
            'premium_tier': 'free'
        }
        
        # Save to DynamoDB
        self.table.put_item(Item=user_profile)
        
        return user_profile
    
    def _get_default_profile(self, phone_number: str) -> Dict[str, Any]:
        """
        Get default profile in case of errors
        """
        return {
            'user_id': self._normalize_phone_number(phone_number),
            'phone_number': phone_number,
            'is_new_user': True,
            'dietary_restrictions': [],
            'allergies': [],
            'household_size': 2,
            'weekly_budget': 75,
            'fitness_goals': 'maintenance',
            'auto_plans': False,
            'calendar_connected': False,
            'premium_tier': 'free'
        }
    
    def _extract_preferences_from_text(self, message: str) -> Dict[str, Any]:
        """
        Extract dietary preferences and settings from natural language
        """
        preferences = {}
        message_lower = message.lower()
        
        # Dietary restrictions
        dietary_restrictions = []
        if any(word in message_lower for word in ['vegetarian', 'veggie']):
            dietary_restrictions.append('vegetarian')
        if 'vegan' in message_lower:
            dietary_restrictions.append('vegan')
        if any(word in message_lower for word in ['gluten-free', 'gluten free', 'celiac']):
            dietary_restrictions.append('gluten-free')
        if any(word in message_lower for word in ['keto', 'ketogenic']):
            dietary_restrictions.append('keto')
        if 'paleo' in message_lower:
            dietary_restrictions.append('paleo')
        if any(word in message_lower for word in ['dairy-free', 'dairy free', 'lactose']):
            dietary_restrictions.append('dairy-free')
        
        if dietary_restrictions:
            preferences['dietary_restrictions'] = dietary_restrictions
        
        # Allergies
        allergies = []
        if 'nut' in message_lower and 'allerg' in message_lower:
            allergies.append('nuts')
        if 'shellfish' in message_lower:
            allergies.append('shellfish')
        if 'egg' in message_lower and 'allerg' in message_lower:
            allergies.append('eggs')
        if 'soy' in message_lower and 'allerg' in message_lower:
            allergies.append('soy')
        
        if allergies:
            preferences['allergies'] = allergies
        
        # Household size
        household_match = re.search(r'(\d+)\s*(?:people|person|member)', message_lower)
        if household_match:
            preferences['household_size'] = int(household_match.group(1))
        
        # Budget
        budget_match = re.search(r'\$?(\d+)(?:\s*(?:dollar|buck|per week|weekly|week))', message_lower)
        if budget_match:
            preferences['weekly_budget'] = int(budget_match.group(1))
        
        # Fitness goals
        if any(word in message_lower for word in ['lose weight', 'weight loss', 'diet', 'cut']):
            preferences['fitness_goals'] = 'weight_loss'
        elif any(word in message_lower for word in ['gain muscle', 'build muscle', 'bulk', 'gain weight']):
            preferences['fitness_goals'] = 'muscle_gain'
        elif any(word in message_lower for word in ['maintain', 'maintenance', 'healthy']):
            preferences['fitness_goals'] = 'maintenance'
        
        # Calories
        calorie_match = re.search(r'(\d{3,4})\s*(?:calorie|cal)', message_lower)
        if calorie_match:
            preferences['daily_calories'] = int(calorie_match.group(1))
        
        return preferences
