"""
Tests for Subscription Service
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import boto3
from moto import mock_aws

from src.services.subscription_service import SubscriptionService, get_subscription_service


@mock_aws
class TestSubscriptionService:
    """Test subscription management functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Create mock DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Subscriptions table
        self.subscriptions_table = dynamodb.create_table(
            TableName='ai-nutritionist-subscriptions',
            KeySchema=[
                {'AttributeName': 'user_phone', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_phone', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Usage table
        self.usage_table = dynamodb.create_table(
            TableName='ai-nutritionist-usage',
            KeySchema=[
                {'AttributeName': 'user_phone', 'KeyType': 'HASH'},
                {'AttributeName': 'month', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_phone', 'AttributeType': 'S'},
                {'AttributeName': 'month', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock SSM
        self.mock_ssm = Mock()
        self.mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'test_stripe_key'}
        }
        
        with patch('boto3.client') as mock_client:
            mock_client.return_value = self.mock_ssm
            self.service = SubscriptionService()
    
    def test_new_user_gets_free_tier(self):
        """Test that new users get free tier status"""
        status = self.service.get_subscription_status('+1234567890')
        
        assert status['tier'] == 'free'
        assert status['status'] == 'active'
        assert status['plan_limit'] == 3
        assert status['plans_used_this_month'] == 0
        assert status['premium_features'] is False
    
    def test_free_user_usage_limits(self):
        """Test usage limit checking for free users"""
        user_phone = '+1234567890'
        
        # New user should be able to generate
        usage_check = self.service.check_usage_limit(user_phone)
        assert usage_check['can_generate'] is True
        assert usage_check['plans_remaining'] == 3
        
        # Use up the free plans
        for i in range(3):
            self.service.increment_usage(user_phone)
        
        # Should now be blocked
        usage_check = self.service.check_usage_limit(user_phone)
        assert usage_check['can_generate'] is False
        assert usage_check['reason'] == 'usage_limit'
        assert usage_check['plans_remaining'] == 0
    
    def test_premium_user_unlimited_access(self):
        """Test that premium users have unlimited access"""
        user_phone = '+1234567890'
        
        # Set user as premium
        self.subscriptions_table.put_item(
            Item={
                'user_phone': user_phone,
                'tier': 'premium',
                'status': 'active',
                'premium_features': True,
                'plan_limit': 999999
            }
        )
        
        usage_check = self.service.check_usage_limit(user_phone)
        assert usage_check['can_generate'] is True
        assert usage_check['reason'] == 'unlimited_access'
        assert usage_check['plans_remaining'] == 'unlimited'
    
    def test_increment_usage_tracking(self):
        """Test usage increment functionality"""
        user_phone = '+1234567890'
        current_month = datetime.utcnow().strftime('%Y-%m')
        
        # Increment usage
        result = self.service.increment_usage(user_phone)
        assert result is True
        
        # Check that usage was recorded
        response = self.usage_table.get_item(
            Key={'user_phone': user_phone, 'month': current_month}
        )
        
        assert 'Item' in response
        assert response['Item']['plans_generated'] == 1
    
    @patch('stripe.Customer.create')
    def test_create_stripe_customer(self, mock_stripe_customer):
        """Test Stripe customer creation"""
        mock_stripe_customer.return_value = Mock(id='cus_test123')
        
        user_phone = '+1234567890'
        customer_id = self.service.create_stripe_customer(user_phone, {})
        
        assert customer_id == 'cus_test123'
        
        # Check that subscription record was created
        response = self.subscriptions_table.get_item(
            Key={'user_phone': user_phone}
        )
        
        assert 'Item' in response
        assert response['Item']['stripe_customer_id'] == 'cus_test123'
        assert response['Item']['tier'] == 'free'
    
    def test_upgrade_message_generation(self):
        """Test upgrade message for users hitting limits"""
        user_phone = '+1234567890'
        
        # Use up all free plans
        for i in range(3):
            self.service.increment_usage(user_phone)
        
        message = self.service.get_upgrade_message(user_phone)
        
        assert 'Upgrade to Premium' in message
        assert '$4.99/month' in message
        assert 'unlimited meal plans' in message.lower()
    
    def test_pricing_info(self):
        """Test pricing information message"""
        pricing = self.service.get_pricing_info()
        
        assert 'Free Plan' in pricing
        assert 'Premium Plan' in pricing
        assert 'Enterprise Plan' in pricing
        assert '$4.99/month' in pricing
        assert '$9.99/month' in pricing
    
    def test_webhook_subscription_cancelled(self):
        """Test handling subscription cancellation webhook"""
        user_phone = '+1234567890'
        
        # Create premium subscription
        self.subscriptions_table.put_item(
            Item={
                'user_phone': user_phone,
                'tier': 'premium',
                'status': 'active',
                'premium_features': True
            }
        )
        
        # Simulate cancellation webhook
        event_data = {
            'object': {
                'metadata': {'user_phone': user_phone}
            }
        }
        
        result = self.service.handle_webhook(
            'customer.subscription.deleted', 
            event_data
        )
        
        assert result is True
        
        # Check that user was downgraded
        status = self.service.get_subscription_status(user_phone)
        assert status['tier'] == 'free'
        assert status['status'] == 'cancelled'
        assert status['premium_features'] is False


def test_get_subscription_service():
    """Test factory function"""
    with patch('boto3.resource'), patch('boto3.client'):
        service = get_subscription_service()
        assert isinstance(service, SubscriptionService)


class TestSubscriptionIntegration:
    """Integration tests for subscription flow"""
    
    @patch('stripe.api_key')
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_end_to_end_subscription_flow(self, mock_client, mock_resource, mock_stripe):
        """Test complete subscription workflow"""
        # This would test the full flow from free user to premium
        # In a real implementation, you'd use test Stripe keys
        pass


if __name__ == '__main__':
    pytest.main([__file__])
