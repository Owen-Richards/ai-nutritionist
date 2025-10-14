"""
AWS DynamoDB implementation of repository interfaces
Infrastructure layer - separated from domain logic
"""

import json
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from packages.core.src.interfaces.repositories import (
    UserRepository,
    NutritionRepository,
    BusinessRepository,
    BrandRepository,
    CacheRepository
)

logger = logging.getLogger(__name__)


class DynamoDBUserRepository(UserRepository):
    """DynamoDB implementation of UserRepository"""
    
    def __init__(self, dynamodb_resource: Any = None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('ai-nutritionist-users')
    
    async def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        try:
            response = self.table.get_item(
                Key={
                    'user_id': self._normalize_phone_number(phone_number),
                    'plan_date': 'profile'
                }
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting user {phone_number}: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user"""
        try:
            user_data['created_at'] = datetime.utcnow().isoformat()
            user_data['last_active'] = datetime.utcnow().isoformat()
            
            self.table.put_item(Item=user_data)
            return user_data
        except ClientError as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    async def update_user(self, phone_number: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            updates['last_active'] = datetime.utcnow().isoformat()
            
            update_expression = "SET "
            expression_values = {}
            
            for key, value in updates.items():
                update_expression += f"{key} = :{key}, "
                expression_values[f":{key}"] = value
            
            update_expression = update_expression.rstrip(", ")
            
            self.table.update_item(
                Key={
                    'user_id': self._normalize_phone_number(phone_number),
                    'plan_date': 'profile'
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating user {phone_number}: {e}")
            return False
    
    async def get_user_preferences(self, phone_number: str) -> Dict[str, Any]:
        """Get user dietary preferences and constraints"""
        user = await self.get_user_by_phone(phone_number)
        if not user:
            return {}
        
        return {
            'dietary_restrictions': user.get('dietary_restrictions', []),
            'health_goals': user.get('health_goals', []),
            'allergies': user.get('allergies', []),
            'dislikes': user.get('dislikes', []),
            'max_prep_time': user.get('max_prep_time', 45),
            'calorie_target': user.get('calorie_target'),
            'budget_preference': user.get('budget_preference', 'medium')
        }
    
    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number format"""
        return phone.replace('+', '').replace('-', '').replace(' ', '')


class DynamoDBNutritionRepository(NutritionRepository):
    """DynamoDB implementation of NutritionRepository"""
    
    def __init__(self, dynamodb_resource: Any = None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.cache_table = self.dynamodb.Table('ai-nutritionist-cache')
        self.usage_table = self.dynamodb.Table('ai-nutritionist-api-usage')
    
    async def get_cached_recipe_search(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached recipe search results"""
        try:
            response = self.cache_table.get_item(Key={'cache_key': cache_key})
            item = response.get('Item')
            
            if item and self._is_cache_valid(item):
                return item.get('data')
            return None
        except ClientError as e:
            logger.error(f"Error getting cache {cache_key}: {e}")
            return None
    
    async def cache_recipe_search(self, cache_key: str, data: Dict[str, Any], ttl_hours: int = 48) -> bool:
        """Cache recipe search results"""
        try:
            expire_time = int((datetime.utcnow() + timedelta(hours=ttl_hours)).timestamp())
            
            self.cache_table.put_item(
                Item={
                    'cache_key': cache_key,
                    'data': data,
                    'expires_at': expire_time,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error caching data {cache_key}: {e}")
            return False
    
    async def track_api_usage(self, user_phone: str, api_type: str, cost: float) -> bool:
        """Track API usage for cost monitoring"""
        try:
            self.usage_table.put_item(
                Item={
                    'user_phone': user_phone,
                    'timestamp': int(datetime.utcnow().timestamp()),
                    'api_type': api_type,
                    'cost': cost,
                    'date': datetime.utcnow().strftime('%Y-%m-%d')
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error tracking usage for {user_phone}: {e}")
            return False
    
    async def get_user_usage_stats(self, user_phone: str, days: int = 30) -> Dict[str, Any]:
        """Get user API usage statistics"""
        try:
            # Query usage for the last N days
            start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp())
            
            response = self.usage_table.query(
                KeyConditionExpression='user_phone = :phone AND #ts >= :start_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':start_time': start_time
                }
            )
            
            items = response.get('Items', [])
            
            # Aggregate statistics
            total_cost = sum(item.get('cost', 0) for item in items)
            api_counts = {}
            for item in items:
                api_type = item.get('api_type', 'unknown')
                api_counts[api_type] = api_counts.get(api_type, 0) + 1
            
            return {
                'total_cost': total_cost,
                'api_counts': api_counts,
                'total_requests': len(items),
                'period_days': days
            }
        except ClientError as e:
            logger.error(f"Error getting usage stats for {user_phone}: {e}")
            return {}
    
    def _is_cache_valid(self, cache_item: Dict[str, Any]) -> bool:
        """Check if cached item is still valid"""
        expire_time = cache_item.get('expires_at', 0)
        return int(datetime.utcnow().timestamp()) < expire_time


class DynamoDBBusinessRepository(BusinessRepository):
    """DynamoDB implementation of BusinessRepository"""
    
    def __init__(self, dynamodb_resource: Any = None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.users_table = self.dynamodb.Table('ai-nutritionist-users')
        self.revenue_table = self.dynamodb.Table('ai-nutritionist-revenue-events')
        self.patterns_table = self.dynamodb.Table('ai-nutritionist-user-patterns')
    
    async def get_user_subscription(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user subscription details"""
        try:
            response = self.users_table.get_item(
                Key={
                    'user_id': phone_number.replace('+', '').replace('-', '').replace(' ', ''),
                    'plan_date': 'profile'
                }
            )
            user = response.get('Item', {})
            return {
                'tier': user.get('premium_tier', 'free'),
                'subscription_id': user.get('subscription_id'),
                'expires_at': user.get('subscription_expires'),
                'status': user.get('subscription_status', 'active')
            }
        except ClientError as e:
            logger.error(f"Error getting subscription for {phone_number}: {e}")
            return None
    
    async def track_revenue_event(self, event_data: Dict[str, Any]) -> bool:
        """Track revenue event for analytics"""
        try:
            event_data['timestamp'] = datetime.utcnow().isoformat()
            event_data['event_id'] = f"{event_data['user_phone']}_{int(datetime.utcnow().timestamp())}"
            
            self.revenue_table.put_item(Item=event_data)
            return True
        except ClientError as e:
            logger.error(f"Error tracking revenue event: {e}")
            return False
    
    async def get_cost_optimization_patterns(self, user_phone: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get user cost optimization patterns"""
        try:
            cutoff_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
            
            response = self.patterns_table.query(
                KeyConditionExpression='user_phone = :phone',
                FilterExpression='request_timestamp > :cutoff',
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':cutoff': cutoff_time
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error getting patterns for {user_phone}: {e}")
            return []
    
    async def save_cost_optimization_pattern(self, pattern_data: Dict[str, Any]) -> bool:
        """Save cost optimization pattern"""
        try:
            pattern_data['timestamp'] = datetime.utcnow().isoformat()
            self.patterns_table.put_item(Item=pattern_data)
            return True
        except ClientError as e:
            logger.error(f"Error saving pattern: {e}")
            return False


class DynamoDBBrandRepository(BrandRepository):
    """DynamoDB implementation of BrandRepository"""
    
    def __init__(self, dynamodb_resource: Any = None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.campaigns_table = self.dynamodb.Table('ai-nutritionist-brand-campaigns')
        self.impressions_table = self.dynamodb.Table('ai-nutritionist-ad-impressions')
    
    async def get_brand_campaigns(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get brand campaigns"""
        try:
            if active_only:
                response = self.campaigns_table.scan(
                    FilterExpression='campaign_status = :status',
                    ExpressionAttributeValues={':status': 'active'}
                )
            else:
                response = self.campaigns_table.scan()
            
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error getting brand campaigns: {e}")
            return []
    
    async def track_ad_impression(self, impression_data: Dict[str, Any]) -> str:
        """Track ad impression and return impression_id"""
        try:
            impression_id = f"{impression_data['user_phone']}_{impression_data['brand_id']}_{int(datetime.utcnow().timestamp())}"
            impression_data['impression_id'] = impression_id
            impression_data['timestamp'] = datetime.utcnow().isoformat()
            
            self.impressions_table.put_item(Item=impression_data)
            return impression_id
        except ClientError as e:
            logger.error(f"Error tracking impression: {e}")
            raise
    
    async def track_ad_interaction(self, impression_id: str, interaction_data: Dict[str, Any]) -> bool:
        """Track ad interaction"""
        try:
            interaction_data['timestamp'] = datetime.utcnow().isoformat()
            
            self.impressions_table.update_item(
                Key={'impression_id': impression_id},
                UpdateExpression='SET interactions = list_append(if_not_exists(interactions, :empty_list), :interaction)',
                ExpressionAttributeValues={
                    ':empty_list': [],
                    ':interaction': [interaction_data]
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error tracking interaction {impression_id}: {e}")
            return False
    
    async def get_impression_details(self, impression_id: str) -> Optional[Dict[str, Any]]:
        """Get impression details"""
        try:
            response = self.impressions_table.get_item(
                Key={'impression_id': impression_id}
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting impression {impression_id}: {e}")
            return None


class DynamoDBCacheRepository(CacheRepository):
    """DynamoDB implementation of CacheRepository"""
    
    def __init__(self, dynamodb_resource: Any = None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.cache_table = self.dynamodb.Table('ai-nutritionist-cache')
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            response = self.cache_table.get_item(Key={'cache_key': key})
            item = response.get('Item')
            
            if item and self._is_valid(item):
                return json.loads(item.get('value', '{}'))
            return None
        except (ClientError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache"""
        try:
            expire_time = int((datetime.utcnow() + timedelta(seconds=ttl_seconds)).timestamp())
            
            self.cache_table.put_item(
                Item={
                    'cache_key': key,
                    'value': json.dumps(value),
                    'expires_at': expire_time,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            return True
        except (ClientError, TypeError) as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            self.cache_table.delete_item(Key={'cache_key': key})
            return True
        except ClientError as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            response = self.cache_table.get_item(Key={'cache_key': key})
            item = response.get('Item')
            return item is not None and self._is_valid(item)
        except ClientError as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    def _is_valid(self, cache_item: Dict[str, Any]) -> bool:
        """Check if cached item is still valid"""
        expire_time = cache_item.get('expires_at', 0)
        return int(datetime.utcnow().timestamp()) < expire_time
