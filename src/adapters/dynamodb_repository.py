"""
AWS DynamoDB adapter for user repository.
"""

import json
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from ..core.interfaces import UserRepositoryInterface
from ..models.user import User


class DynamoDBUserRepository(UserRepositoryInterface):
    """DynamoDB implementation of user repository."""
    
    def __init__(self, table_name: str, region: str = "us-east-1"):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Retrieve user from DynamoDB."""
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            if 'Item' in response:
                return User.from_dict(response['Item'])
            return None
        except ClientError as e:
            print(f"Error retrieving user {user_id}: {e}")
            return None
    
    async def save_user(self, user: User) -> None:
        """Save user to DynamoDB."""
        try:
            self.table.put_item(Item=user.to_dict())
        except ClientError as e:
            print(f"Error saving user {user.id}: {e}")
            raise
    
    async def delete_user(self, user_id: str) -> None:
        """Delete user from DynamoDB (GDPR compliance)."""
        try:
            self.table.delete_item(Key={'user_id': user_id})
        except ClientError as e:
            print(f"Error deleting user {user_id}: {e}")
            raise
