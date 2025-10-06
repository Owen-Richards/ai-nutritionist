"""
AWS DynamoDB adapter for user repository with environment-aware configuration.
"""

import json
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from ..core.interfaces import UserRepositoryInterface
from ..models.user import User
from ..config.environment import get_table_name, config
from ..services.infrastructure.aws_optimization import get_aws_service


class DynamoDBUserRepository(UserRepositoryInterface):
    """DynamoDB implementation of user repository with environment awareness."""
    
    def __init__(self, table_name: str = None, region: str = None):
        # Use environment-specific table name if not provided
        if table_name is None:
            table_name = get_table_name('users')
        elif not table_name.endswith(f'-{config.environment}'):
            # Add environment suffix if not present
            table_name = get_table_name(table_name.replace('ai-nutritionist-', '').replace('-dev', '').replace('-stage', '').replace('-prod', ''))
        
        self.table_name = table_name
        self.region = region or config.aws_region
        
        # Use optimized connection pool
        self.dynamodb = get_aws_service('dynamodb')
        self.table = self.dynamodb.Table(self.table_name)
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Retrieve user from DynamoDB."""
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            if 'Item' in response:
                return User.from_dict(response['Item'])
            return None
        except ClientError as e:
            print(f"Error retrieving user {user_id} from {self.table_name}: {e}")
            return None
    
    async def save_user(self, user: User) -> None:
        """Save user to DynamoDB."""
        try:
            self.table.put_item(Item=user.to_dict())
        except ClientError as e:
            print(f"Error saving user {user.id} to {self.table_name}: {e}")
            raise
    
    async def delete_user(self, user_id: str) -> None:
        """Delete user from DynamoDB (GDPR compliance)."""
        try:
            self.table.delete_item(Key={'user_id': user_id})
        except ClientError as e:
            print(f"Error deleting user {user_id} from {self.table_name}: {e}")
            raise
