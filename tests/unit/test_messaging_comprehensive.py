"""
Comprehensive unit tests for messaging and communication services.

Tests cover:
- SMS and messaging service functionality
- Multi-platform communication handling
- Message templating and personalization
- Delivery tracking and analytics
- Rate limiting and compliance
- Emergency notification systems
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta, date
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, List, Optional

from src.services.messaging.sms import ConsolidatedMessagingService
from src.services.messaging.notifications import AWSMessagingService
from src.services.messaging.templates import NutritionMessagingService
from src.services.messaging.analytics import MultiUserMessagingHandler


class TestConsolidatedMessagingService:
    """Test consolidated messaging service functionality."""
    
    @pytest.fixture
    def mock_aws_client(self):
        """Mock AWS SNS/SES client."""
        client = Mock()
        client.publish.return_value = {'MessageId': 'msg_123456'}
        client.send_email.return_value = {'MessageId': 'email_123456'}
        return client
    
    @pytest.fixture
    def mock_dynamodb(self):
        """Mock DynamoDB for message tracking."""
        table_mock = Mock()
        table_mock.put_item.return_value = {}
        table_mock.get_item.return_value = {'Item': {}}
        table_mock.update_item.return_value = {}
        
        dynamodb_mock = Mock()
        dynamodb_mock.Table.return_value = table_mock
        return dynamodb_mock
    
    @pytest.fixture
    def messaging_service(self, mock_aws_client, mock_dynamodb):
        """Create messaging service with mocked dependencies."""
        with patch('boto3.client', return_value=mock_aws_client), \
             patch('boto3.resource', return_value=mock_dynamodb):
            return ConsolidatedMessagingService()
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self, messaging_service, mock_aws_client):
        """Test successful SMS sending."""
        phone_number = "+1234567890"
        message = "Your meal plan is ready! Check it out in the app."
        
        result = await messaging_service.send_sms(phone_number, message)
        
        assert result['success'] is True
        assert result['message_id'] is not None
        mock_aws_client.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, messaging_service, mock_aws_client):
        """Test successful email sending."""
        email_address = "user@example.com"
        subject = "Weekly Nutrition Report"
        body = "Here's your weekly nutrition summary..."
        
        result = await messaging_service.send_email(email_address, subject, body)
        
        assert result['success'] is True
        assert result['message_id'] is not None
        mock_aws_client.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_whatsapp_message(self, messaging_service):
        """Test WhatsApp message sending."""
        phone_number = "+1234567890"
        message = "🍎 Don't forget to log your breakfast!"
        
        # Mock WhatsApp API response
        with patch.object(messaging_service, '_send_whatsapp') as mock_whatsapp:
            mock_whatsapp.return_value = {'id': 'wa_msg_123', 'status': 'sent'}
            
            result = await messaging_service.send_whatsapp(phone_number, message)
            
            assert result['success'] is True
            assert 'wa_msg_123' in result['message_id']
    
    @pytest.mark.asyncio
    async def test_message_delivery_tracking(self, messaging_service, mock_dynamodb):
        """Test message delivery status tracking."""
        message_id = "msg_123456"
        
        # Simulate delivery status update
        delivery_status = {
            "message_id": message_id,
            "status": "delivered",
            "delivered_at": datetime.utcnow().isoformat(),
            "carrier": "verizon"
        }
        
        await messaging_service.update_delivery_status(delivery_status)
        
        mock_dynamodb.Table().update_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, messaging_service):
        """Test rate limiting for message sending."""
        phone_number = "+1234567890"
        message = "Test message"
        
        # Send messages rapidly
        results = []
        for i in range(10):
            result = await messaging_service.send_sms(phone_number, f"{message} {i}")
            results.append(result)
        
        # Some messages should be rate limited
        rate_limited = [r for r in results if r.get('rate_limited')]
        assert len(rate_limited) > 0
    
    def test_phone_number_validation(self, messaging_service):
        """Test phone number validation."""
        valid_numbers = ["+1234567890", "+44123456789", "+81123456789"]
        invalid_numbers = ["123456", "abc123", "+1abc", ""]
        
        for number in valid_numbers:
            assert messaging_service.validate_phone_number(number) is True
        
        for number in invalid_numbers:
            assert messaging_service.validate_phone_number(number) is False
    
    def test_message_character_limit_enforcement(self, messaging_service):
        """Test SMS character limit enforcement."""
        # Standard SMS limit is 160 characters
        short_message = "Short message"
        long_message = "A" * 200  # Exceeds limit
        
        assert messaging_service.check_sms_length(short_message)['valid'] is True
        
        long_check = messaging_service.check_sms_length(long_message)
        assert long_check['valid'] is False
        assert long_check['segments'] > 1
    
    @pytest.mark.asyncio
    async def test_message_retry_mechanism(self, messaging_service, mock_aws_client):
        """Test message retry on failure."""
        phone_number = "+1234567890"
        message = "Retry test message"
        
        # Mock initial failure then success
        mock_aws_client.publish.side_effect = [
            Exception("Temporary failure"),
            Exception("Another failure"),
            {'MessageId': 'msg_success'}
        ]
        
        result = await messaging_service.send_sms_with_retry(
            phone_number, message, max_retries=3
        )
        
        assert result['success'] is True
        assert mock_aws_client.publish.call_count == 3
    
    @pytest.mark.parametrize("message_type,expected_template", [
        ("meal_reminder", "meal_reminder_template"),
        ("nutrition_tip", "nutrition_tip_template"),
        ("goal_achievement", "goal_achievement_template"),
        ("weekly_summary", "weekly_summary_template")
    ])
    def test_message_template_selection(self, messaging_service, message_type, expected_template):
        """Test message template selection based on type."""
        template = messaging_service.get_message_template(message_type)
        assert expected_template in template['template_id']


class TestAWSMessagingService:
    """Test AWS-specific messaging service functionality."""
    
    @pytest.fixture
    def aws_messaging_service(self):
        """Create AWS messaging service."""
        return AWSMessagingService()
    
    @pytest.mark.asyncio
    async def test_sns_topic_management(self, aws_messaging_service):
        """Test SNS topic creation and management."""
        topic_name = "nutrition_alerts"
        
        with patch.object(aws_messaging_service, 'sns_client') as mock_sns:
            mock_sns.create_topic.return_value = {'TopicArn': 'arn:aws:sns:us-east-1:123:nutrition_alerts'}
            
            topic_arn = await aws_messaging_service.create_topic(topic_name)
            
            assert 'nutrition_alerts' in topic_arn
            mock_sns.create_topic.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscription_management(self, aws_messaging_service):
        """Test SNS subscription management."""
        topic_arn = "arn:aws:sns:us-east-1:123:nutrition_alerts"
        phone_number = "+1234567890"
        
        with patch.object(aws_messaging_service, 'sns_client') as mock_sns:
            mock_sns.subscribe.return_value = {'SubscriptionArn': 'arn:aws:sns:sub:123'}
            
            subscription_arn = await aws_messaging_service.subscribe_phone(topic_arn, phone_number)
            
            assert subscription_arn is not None
            mock_sns.subscribe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_attributes(self, aws_messaging_service):
        """Test SNS message attributes handling."""
        message = "Test message with attributes"
        attributes = {
            "priority": {"DataType": "String", "StringValue": "high"},
            "user_tier": {"DataType": "String", "StringValue": "premium"},
            "message_type": {"DataType": "String", "StringValue": "alert"}
        }
        
        with patch.object(aws_messaging_service, 'sns_client') as mock_sns:
            mock_sns.publish.return_value = {'MessageId': 'msg_with_attrs'}
            
            result = await aws_messaging_service.send_with_attributes(
                "topic_arn", message, attributes
            )
            
            assert result['success'] is True
            # Verify attributes were included in the call
            call_args = mock_sns.publish.call_args
            assert 'MessageAttributes' in call_args[1]
    
    def test_message_filtering(self, aws_messaging_service):
        """Test SNS message filtering policies."""
        filter_policy = {
            "user_tier": ["premium", "enterprise"],
            "message_type": ["alert", "reminder"],
            "priority": ["high"]
        }
        
        policy_json = aws_messaging_service.create_filter_policy(filter_policy)
        
        assert "premium" in policy_json
        assert "alert" in policy_json
        assert "high" in policy_json


class TestNutritionMessagingService:
    """Test nutrition-specific messaging and templates."""
    
    @pytest.fixture
    def nutrition_messaging(self):
        """Create nutrition messaging service."""
        return NutritionMessagingService()
    
    def test_personalized_meal_reminder(self, nutrition_messaging):
        """Test personalized meal reminder generation."""
        user_data = {
            "name": "John",
            "next_meal": "lunch",
            "preferred_cuisine": "mediterranean",
            "calorie_target": 600,
            "dietary_restrictions": ["vegetarian"]
        }
        
        reminder = nutrition_messaging.generate_meal_reminder(user_data)
        
        assert user_data['name'] in reminder
        assert user_data['next_meal'] in reminder
        assert "vegetarian" in reminder or "Mediterranean" in reminder
    
    def test_nutrition_tip_generation(self, nutrition_messaging):
        """Test personalized nutrition tip generation."""
        user_profile = {
            "health_goals": ["weight_loss", "muscle_gain"],
            "current_challenges": ["protein_intake"],
            "activity_level": "high",
            "dietary_preferences": ["whole_foods"]
        }
        
        tip = nutrition_messaging.generate_nutrition_tip(user_profile)
        
        assert any(goal in tip for goal in user_profile['health_goals'])
        assert "protein" in tip.lower()
    
    def test_goal_achievement_celebration(self, nutrition_messaging):
        """Test goal achievement celebration messages."""
        achievement = {
            "goal_type": "weekly_protein_target",
            "target_value": 150,  # grams
            "achieved_value": 155,
            "streak_days": 7,
            "user_name": "Sarah"
        }
        
        celebration = nutrition_messaging.generate_achievement_message(achievement)
        
        assert achievement['user_name'] in celebration
        assert str(achievement['streak_days']) in celebration
        assert "protein" in celebration.lower()
        assert any(word in celebration for word in ["congratulations", "awesome", "great"])
    
    def test_weekly_summary_generation(self, nutrition_messaging):
        """Test weekly nutrition summary generation."""
        weekly_data = {
            "user_name": "Mike",
            "calories_avg": 2100,
            "protein_avg": 145,
            "workouts_completed": 4,
            "meals_logged": 18,
            "top_foods": ["chicken breast", "quinoa", "broccoli"],
            "improvements": ["increased fiber intake"]
        }
        
        summary = nutrition_messaging.generate_weekly_summary(weekly_data)
        
        assert weekly_data['user_name'] in summary
        assert str(weekly_data['calories_avg']) in summary
        assert str(weekly_data['workouts_completed']) in summary
        assert weekly_data['top_foods'][0] in summary
    
    def test_emergency_alert_formatting(self, nutrition_messaging):
        """Test emergency alert message formatting."""
        alert_data = {
            "alert_type": "severe_nutrient_deficiency",
            "nutrient": "vitamin_b12",
            "severity": "high",
            "user_name": "Lisa",
            "recommended_action": "consult_healthcare_provider"
        }
        
        alert = nutrition_messaging.generate_emergency_alert(alert_data)
        
        assert alert_data['user_name'] in alert
        assert "vitamin B12" in alert or "B12" in alert
        assert "healthcare" in alert.lower() or "doctor" in alert.lower()
        assert "urgent" in alert.lower() or "important" in alert.lower()
    
    @pytest.mark.parametrize("time_of_day,expected_greeting", [
        ("06:00", "Good morning"),
        ("12:00", "Good afternoon"),
        ("18:00", "Good evening"),
        ("22:00", "Good evening")
    ])
    def test_time_based_greetings(self, nutrition_messaging, time_of_day, expected_greeting):
        """Test time-based greeting generation."""
        greeting = nutrition_messaging.get_time_based_greeting(time_of_day)
        assert expected_greeting.lower() in greeting.lower()
    
    def test_emoji_integration(self, nutrition_messaging):
        """Test emoji integration in messages."""
        message_types = ["celebration", "reminder", "tip", "alert"]
        
        for msg_type in message_types:
            message = nutrition_messaging.add_appropriate_emojis("Great job!", msg_type)
            
            # Should contain relevant emojis
            emojis = ["🎉", "👏", "💪", "🍎", "⏰", "📊", "⚠️", "🔥"]
            assert any(emoji in message for emoji in emojis)


class TestMultiUserMessagingHandler:
    """Test multi-user messaging analytics and coordination."""
    
    @pytest.fixture
    def messaging_handler(self):
        """Create messaging handler."""
        return MultiUserMessagingHandler()
    
    @pytest.mark.asyncio
    async def test_bulk_message_sending(self, messaging_handler):
        """Test bulk message sending to multiple users."""
        recipients = [
            {"phone": "+1234567890", "name": "John"},
            {"phone": "+1234567891", "name": "Jane"},
            {"phone": "+1234567892", "name": "Bob"}
        ]
        
        message_template = "Hi {name}, your weekly meal plan is ready!"
        
        with patch.object(messaging_handler, '_send_individual_message') as mock_send:
            mock_send.return_value = {'success': True, 'message_id': 'msg_123'}
            
            results = await messaging_handler.send_bulk_messages(recipients, message_template)
            
            assert len(results) == 3
            assert all(result['success'] for result in results)
            assert mock_send.call_count == 3
    
    def test_message_scheduling(self, messaging_handler):
        """Test message scheduling functionality."""
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        message_data = {
            "recipients": ["+1234567890"],
            "message": "Time for your afternoon snack!",
            "message_type": "reminder"
        }
        
        schedule_id = messaging_handler.schedule_message(scheduled_time, message_data)
        
        assert schedule_id is not None
        
        # Check scheduled messages
        scheduled = messaging_handler.get_scheduled_messages()
        assert len(scheduled) > 0
        assert any(msg['id'] == schedule_id for msg in scheduled)
    
    def test_delivery_analytics(self, messaging_handler):
        """Test message delivery analytics."""
        delivery_data = [
            {"message_id": "msg1", "status": "delivered", "delivered_at": datetime.utcnow()},
            {"message_id": "msg2", "status": "failed", "error": "invalid_number"},
            {"message_id": "msg3", "status": "delivered", "delivered_at": datetime.utcnow()},
            {"message_id": "msg4", "status": "pending"},
        ]
        
        for data in delivery_data:
            messaging_handler.record_delivery_status(data)
        
        analytics = messaging_handler.get_delivery_analytics()
        
        assert analytics['total_messages'] == 4
        assert analytics['delivered_count'] == 2
        assert analytics['failed_count'] == 1
        assert analytics['delivery_rate'] == 0.5  # 2/4
    
    def test_user_engagement_tracking(self, messaging_handler):
        """Test user engagement tracking."""
        engagement_events = [
            {"user_id": "user1", "message_id": "msg1", "event": "opened", "timestamp": datetime.utcnow()},
            {"user_id": "user1", "message_id": "msg1", "event": "clicked", "timestamp": datetime.utcnow()},
            {"user_id": "user2", "message_id": "msg2", "event": "opened", "timestamp": datetime.utcnow()},
        ]
        
        for event in engagement_events:
            messaging_handler.track_engagement(event)
        
        user1_engagement = messaging_handler.get_user_engagement("user1")
        
        assert user1_engagement['messages_opened'] == 1
        assert user1_engagement['links_clicked'] == 1
        assert user1_engagement['engagement_rate'] > 0
    
    def test_opt_out_management(self, messaging_handler):
        """Test opt-out and unsubscribe management."""
        phone_number = "+1234567890"
        
        # User opts out
        messaging_handler.process_opt_out(phone_number, "STOP")
        
        # Check opt-out status
        is_opted_out = messaging_handler.is_opted_out(phone_number)
        assert is_opted_out is True
        
        # Try to send message to opted-out user
        can_send = messaging_handler.can_send_message(phone_number)
        assert can_send is False
        
        # User opts back in
        messaging_handler.process_opt_in(phone_number, "START")
        
        can_send_again = messaging_handler.can_send_message(phone_number)
        assert can_send_again is True
    
    def test_message_frequency_control(self, messaging_handler):
        """Test message frequency control."""
        user_id = "user123"
        
        # Set frequency limits
        messaging_handler.set_frequency_limit(user_id, max_daily=3, max_weekly=10)
        
        # Send multiple messages
        for i in range(5):
            can_send = messaging_handler.check_frequency_limit(user_id)
            if can_send:
                messaging_handler.record_message_sent(user_id)
        
        # Should be blocked after limit reached
        can_send_more = messaging_handler.check_frequency_limit(user_id)
        assert can_send_more is False
    
    @pytest.mark.asyncio
    async def test_emergency_broadcast(self, messaging_handler):
        """Test emergency broadcast functionality."""
        emergency_message = {
            "message": "🚨 URGENT: System maintenance in 10 minutes. Save your work.",
            "priority": "high",
            "override_opt_out": True,
            "recipients": "all_active_users"
        }
        
        with patch.object(messaging_handler, '_get_all_active_users') as mock_users:
            mock_users.return_value = ["+1234567890", "+1234567891", "+1234567892"]
            
            with patch.object(messaging_handler, '_send_individual_message') as mock_send:
                mock_send.return_value = {'success': True}
                
                results = await messaging_handler.send_emergency_broadcast(emergency_message)
                
                assert len(results) == 3
                assert all(result['success'] for result in results)


class TestMessagingCompliance:
    """Test messaging compliance and regulatory adherence."""
    
    def test_tcpa_compliance(self):
        """Test TCPA (Telephone Consumer Protection Act) compliance."""
        from src.services.messaging.compliance import TCPACompliance
        
        compliance = TCPACompliance()
        
        # Check consent requirements
        phone_number = "+1234567890"
        message_type = "marketing"
        
        can_send = compliance.check_consent(phone_number, message_type)
        assert can_send is False  # No consent recorded
        
        # Record consent
        compliance.record_consent(phone_number, message_type, consent_method="web_form")
        
        can_send_with_consent = compliance.check_consent(phone_number, message_type)
        assert can_send_with_consent is True
    
    def test_gdpr_compliance(self):
        """Test GDPR compliance for international users."""
        from src.services.messaging.compliance import GDPRCompliance
        
        gdpr = GDPRCompliance()
        
        user_data = {
            "phone": "+44123456789",  # UK number
            "email": "user@example.com",
            "country": "UK"
        }
        
        # Check if explicit consent is required
        requires_explicit_consent = gdpr.requires_explicit_consent(user_data['country'])
        assert requires_explicit_consent is True
        
        # Record GDPR consent
        gdpr.record_gdpr_consent(user_data, consent_text="I agree to receive messages")
        
        # Check data processing rights
        rights = gdpr.get_data_rights(user_data['country'])
        assert 'right_to_erasure' in rights
        assert 'right_to_portability' in rights
    
    def test_message_content_compliance(self):
        """Test message content compliance checking."""
        from src.services.messaging.compliance import ContentCompliance
        
        compliance = ContentCompliance()
        
        # Test prohibited content
        prohibited_messages = [
            "Get rich quick scheme!",
            "Guaranteed weight loss in 7 days!",
            "This is not medical advice but...",
        ]
        
        for message in prohibited_messages:
            is_compliant = compliance.check_content(message)
            assert is_compliant is False
        
        # Test compliant content
        compliant_message = "Your weekly meal plan includes balanced nutrition options."
        is_compliant = compliance.check_content(compliant_message)
        assert is_compliant is True


# Performance tests for messaging
class TestMessagingPerformance:
    """Test performance characteristics of messaging services."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_bulk_sending_performance(self):
        """Test bulk message sending performance."""
        recipient_count = 1000
        
        start_time = datetime.utcnow()
        
        # Simulate bulk sending
        tasks = [asyncio.sleep(0.001) for _ in range(recipient_count)]
        await asyncio.gather(*tasks)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should handle 1000 messages efficiently
        assert duration < 10.0  # Complete within 10 seconds
    
    @pytest.mark.performance
    def test_template_rendering_performance(self):
        """Test message template rendering performance."""
        import time
        
        template = "Hi {name}! Your {meal_type} has {calories} calories and {protein}g protein."
        user_data = {"name": "John", "meal_type": "lunch", "calories": 550, "protein": 35}
        
        start_time = time.time()
        
        # Render template 1000 times
        for _ in range(1000):
            message = template.format(**user_data)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be very fast
        assert duration < 0.1  # Complete within 100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
