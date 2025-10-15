"""Mock external services for testing"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Optional, Any
import json
import random
from datetime import datetime, timedelta


class MockTwilioService:
    """Mock Twilio SMS service"""
    
    def __init__(self):
        self.sent_messages = []
        self.should_fail = False
        self.failure_rate = 0.0
    
    def send_sms(self, to: str, body: str, from_: str = None) -> Dict[str, Any]:
        """Mock SMS sending"""
        if self.should_fail or random.random() < self.failure_rate:
            return {
                'success': False,
                'error': 'Mock SMS failure',
                'error_code': 30007
            }
        
        message_id = f"SM{random.randint(10000000000000000000000000000000, 99999999999999999999999999999999):032x}"
        
        message = {
            'sid': message_id,
            'to': to,
            'from': from_ or '+15551234567',
            'body': body,
            'status': 'sent',
            'direction': 'outbound-api',
            'created_at': datetime.utcnow().isoformat(),
            'price': '-0.0075',
            'price_unit': 'USD'
        }
        
        self.sent_messages.append(message)
        
        return {
            'success': True,
            'message_sid': message_id,
            'status': 'sent'
        }
    
    def get_message_status(self, message_sid: str) -> str:
        """Get status of a sent message"""
        for message in self.sent_messages:
            if message['sid'] == message_sid:
                return message['status']
        return 'unknown'
    
    def set_failure_rate(self, rate: float):
        """Set failure rate for testing error scenarios"""
        self.failure_rate = rate


class MockWhatsAppAPI:
    """Mock WhatsApp Business API"""
    
    def __init__(self):
        self.sent_messages = []
        self.should_fail = False
        self.webhook_events = []
    
    def send_message(self, to: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Mock WhatsApp message sending"""
        if self.should_fail:
            return {
                'success': False,
                'error': {
                    'code': 131026,
                    'message': 'Message undeliverable'
                }
            }
        
        message_id = f"wamid.{random.randint(1000000000000000000, 9999999999999999999)}"
        
        sent_message = {
            'id': message_id,
            'to': to,
            'type': message.get('type', 'text'),
            'content': message,
            'status': 'sent',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.sent_messages.append(sent_message)
        
        return {
            'success': True,
            'message_id': message_id,
            'status': 'sent'
        }
    
    def send_template_message(self, to: str, template_name: str, parameters: List[str]) -> Dict[str, Any]:
        """Send template message"""
        message = {
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': 'en'},
                'components': [
                    {
                        'type': 'body',
                        'parameters': [{'type': 'text', 'text': param} for param in parameters]
                    }
                ]
            }
        }
        return self.send_message(to, message)
    
    def get_message_status(self, message_id: str) -> str:
        """Get message status"""
        for message in self.sent_messages:
            if message['id'] == message_id:
                return message['status']
        return 'unknown'
    
    def simulate_webhook_event(self, event_type: str, message_id: str, data: Dict[str, Any] = None):
        """Simulate webhook events"""
        event = {
            'type': event_type,
            'message_id': message_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data or {}
        }
        self.webhook_events.append(event)


class MockStripeService:
    """Mock Stripe payment service"""
    
    def __init__(self):
        self.customers = {}
        self.subscriptions = {}
        self.payment_methods = {}
        self.invoices = {}
        self.webhook_events = []
        self.should_fail_payments = False
    
    def create_customer(self, email: str, metadata: Dict[str, str] = None) -> Dict[str, Any]:
        """Create Stripe customer"""
        customer_id = f"cus_{random.randint(1000000000000000, 9999999999999999):016x}"
        
        customer = {
            'id': customer_id,
            'email': email,
            'created': int(datetime.utcnow().timestamp()),
            'metadata': metadata or {},
            'default_source': None,
            'subscriptions': {'data': []}
        }
        
        self.customers[customer_id] = customer
        return customer
    
    def create_subscription(self, customer_id: str, price_id: str, payment_method_id: str = None) -> Dict[str, Any]:
        """Create subscription"""
        if self.should_fail_payments:
            return {
                'error': {
                    'type': 'card_error',
                    'code': 'card_declined',
                    'message': 'Your card was declined.'
                }
            }
        
        subscription_id = f"sub_{random.randint(1000000000000000, 9999999999999999):016x}"
        
        subscription = {
            'id': subscription_id,
            'customer': customer_id,
            'status': 'active',
            'current_period_start': int(datetime.utcnow().timestamp()),
            'current_period_end': int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            'items': {
                'data': [{'price': {'id': price_id}}]
            },
            'default_payment_method': payment_method_id,
            'trial_end': None,
            'cancel_at_period_end': False
        }
        
        self.subscriptions[subscription_id] = subscription
        return subscription
    
    def create_payment_method(self, type_: str = 'card', card_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create payment method"""
        pm_id = f"pm_{random.randint(1000000000000000, 9999999999999999):016x}"
        
        payment_method = {
            'id': pm_id,
            'type': type_,
            'created': int(datetime.utcnow().timestamp()),
        }
        
        if type_ == 'card':
            payment_method['card'] = card_data or {
                'brand': 'visa',
                'last4': '4242',
                'exp_month': 12,
                'exp_year': 2025,
                'funding': 'credit'
            }
        
        self.payment_methods[pm_id] = payment_method
        return payment_method
    
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel subscription"""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id]['cancel_at_period_end'] = at_period_end
            if not at_period_end:
                self.subscriptions[subscription_id]['status'] = 'canceled'
            return self.subscriptions[subscription_id]
        return {'error': 'Subscription not found'}
    
    def simulate_webhook(self, event_type: str, data: Dict[str, Any]):
        """Simulate Stripe webhook"""
        event = {
            'id': f"evt_{random.randint(1000000000000000, 9999999999999999):016x}",
            'type': event_type,
            'data': {'object': data},
            'created': int(datetime.utcnow().timestamp())
        }
        self.webhook_events.append(event)
        return event


class MockEdamamAPI:
    """Mock Edamam nutrition API"""
    
    def __init__(self):
        self.request_count = 0
        self.should_fail = False
        self.rate_limited = False
    
    def search_recipes(self, query: str, diet: str = None, health: str = None, max_results: int = 10) -> Dict[str, Any]:
        """Mock recipe search"""
        self.request_count += 1
        
        if self.rate_limited:
            return {
                'error': 'Rate limit exceeded',
                'status_code': 429
            }
        
        if self.should_fail:
            return {
                'error': 'API error',
                'status_code': 500
            }
        
        # Generate mock recipes
        recipes = []
        for i in range(min(max_results, 5)):
            recipe = {
                'uri': f"http://www.edamam.com/ontologies/edamam.owl#recipe_{random.randint(1000000, 9999999)}",
                'label': f"Mock Recipe {i+1} for {query}",
                'image': 'https://example.com/recipe-image.jpg',
                'source': 'Mock Source',
                'url': 'https://example.com/recipe',
                'yield': random.randint(2, 8),
                'dietLabels': [diet] if diet else [],
                'healthLabels': [health] if health else ['Sugar-Conscious'],
                'ingredientLines': [
                    f"Mock ingredient {j+1}" for j in range(random.randint(3, 8))
                ],
                'calories': random.randint(200, 800),
                'totalTime': random.randint(15, 120),
                'cuisineType': ['american'],
                'mealType': ['lunch'],
                'dishType': ['main course'],
                'totalNutrients': {
                    'ENERC_KCAL': {'quantity': random.randint(200, 800), 'unit': 'kcal'},
                    'PROCNT': {'quantity': random.randint(10, 50), 'unit': 'g'},
                    'CHOCDF': {'quantity': random.randint(20, 100), 'unit': 'g'},
                    'FAT': {'quantity': random.randint(5, 30), 'unit': 'g'}
                }
            }
            recipes.append(recipe)
        
        return {
            'hits': [{'recipe': recipe} for recipe in recipes],
            'count': len(recipes)
        }
    
    def get_nutrition_analysis(self, ingredients: List[str]) -> Dict[str, Any]:
        """Mock nutrition analysis"""
        self.request_count += 1
        
        if self.should_fail:
            return {'error': 'Analysis failed'}
        
        return {
            'calories': random.randint(100, 500),
            'totalWeight': random.randint(100, 1000),
            'totalNutrients': {
                'ENERC_KCAL': {'quantity': random.randint(100, 500), 'unit': 'kcal'},
                'PROCNT': {'quantity': random.randint(5, 25), 'unit': 'g'},
                'CHOCDF': {'quantity': random.randint(10, 50), 'unit': 'g'},
                'FAT': {'quantity': random.randint(2, 15), 'unit': 'g'}
            },
            'ingredients': [
                {
                    'text': ingredient,
                    'parsed': [{'foodMatch': ingredient}]
                } for ingredient in ingredients
            ]
        }


class MockAWSServices:
    """Mock AWS services"""
    
    def __init__(self):
        self.dynamodb_data = {}
        self.s3_objects = {}
        self.ses_emails = []
        self.lambda_invocations = []
    
    def create_dynamodb_mock(self):
        """Create DynamoDB mock"""
        mock_dynamodb = Mock()
        
        def get_item(TableName, Key):
            table_data = self.dynamodb_data.get(TableName, {})
            key_str = str(Key)
            if key_str in table_data:
                return {'Item': table_data[key_str]}
            return {}
        
        def put_item(TableName, Item):
            if TableName not in self.dynamodb_data:
                self.dynamodb_data[TableName] = {}
            key_str = str(Item.get('user_id', Item.get('plan_id', random.randint(1000, 9999))))
            self.dynamodb_data[TableName][key_str] = Item
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        def update_item(TableName, Key, UpdateExpression, ExpressionAttributeValues):
            table_data = self.dynamodb_data.get(TableName, {})
            key_str = str(Key)
            if key_str in table_data:
                # Simulate update
                table_data[key_str].update({'updated_at': datetime.utcnow().isoformat()})
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        mock_dynamodb.get_item = Mock(side_effect=get_item)
        mock_dynamodb.put_item = Mock(side_effect=put_item)
        mock_dynamodb.update_item = Mock(side_effect=update_item)
        
        return mock_dynamodb
    
    def create_s3_mock(self):
        """Create S3 mock"""
        mock_s3 = Mock()
        
        def put_object(Bucket, Key, Body):
            bucket_data = self.s3_objects.get(Bucket, {})
            bucket_data[Key] = Body
            self.s3_objects[Bucket] = bucket_data
            return {'ETag': f'"{random.randint(1000000, 9999999)}"'}
        
        def get_object(Bucket, Key):
            bucket_data = self.s3_objects.get(Bucket, {})
            if Key in bucket_data:
                return {'Body': Mock(read=Mock(return_value=bucket_data[Key]))}
            raise Exception('NoSuchKey')
        
        mock_s3.put_object = Mock(side_effect=put_object)
        mock_s3.get_object = Mock(side_effect=get_object)
        
        return mock_s3
    
    def create_ses_mock(self):
        """Create SES mock"""
        mock_ses = Mock()
        
        def send_email(Source, Destination, Message):
            email = {
                'source': Source,
                'destination': Destination,
                'subject': Message['Subject']['Data'],
                'body': Message['Body'].get('Text', {}).get('Data', ''),
                'sent_at': datetime.utcnow().isoformat(),
                'message_id': f"ses_{random.randint(1000000000000, 9999999999999)}"
            }
            self.ses_emails.append(email)
            return {'MessageId': email['message_id']}
        
        mock_ses.send_email = Mock(side_effect=send_email)
        return mock_ses


# Pytest fixtures
@pytest.fixture
def mock_twilio():
    """Mock Twilio service"""
    return MockTwilioService()


@pytest.fixture
def mock_whatsapp():
    """Mock WhatsApp API"""
    return MockWhatsAppAPI()


@pytest.fixture
def mock_stripe():
    """Mock Stripe service"""
    return MockStripeService()


@pytest.fixture
def mock_edamam():
    """Mock Edamam API"""
    return MockEdamamAPI()


@pytest.fixture
def mock_aws_services():
    """Mock AWS services"""
    return MockAWSServices()


@pytest.fixture
def mock_dynamodb(mock_aws_services):
    """Mock DynamoDB client"""
    return mock_aws_services.create_dynamodb_mock()


@pytest.fixture
def mock_s3(mock_aws_services):
    """Mock S3 client"""
    return mock_aws_services.create_s3_mock()


@pytest.fixture
def mock_ses(mock_aws_services):
    """Mock SES client"""
    return mock_aws_services.create_ses_mock()


@pytest.fixture
def mock_external_services():
    """All external service mocks"""
    return {
        'twilio': MockTwilioService(),
        'whatsapp': MockWhatsAppAPI(),
        'stripe': MockStripeService(),
        'edamam': MockEdamamAPI(),
        'aws': MockAWSServices()
    }


# Context managers for patching
@pytest.fixture
def patch_twilio():
    """Patch Twilio client"""
    with patch('src.services.messaging.twilio_service.TwilioService') as mock:
        mock_service = MockTwilioService()
        mock.return_value = mock_service
        yield mock_service


@pytest.fixture
def patch_stripe():
    """Patch Stripe client"""
    with patch('stripe.Customer'), \
         patch('stripe.Subscription'), \
         patch('stripe.PaymentMethod'), \
         patch('stripe.Invoice'):
        mock_service = MockStripeService()
        yield mock_service


@pytest.fixture
def patch_aws():
    """Patch AWS services"""
    aws_mocks = MockAWSServices()
    
    with patch('boto3.client') as mock_client:
        def client_factory(service_name, **kwargs):
            if service_name == 'dynamodb':
                return aws_mocks.create_dynamodb_mock()
            elif service_name == 's3':
                return aws_mocks.create_s3_mock()
            elif service_name == 'ses':
                return aws_mocks.create_ses_mock()
            return Mock()
        
        mock_client.side_effect = client_factory
        yield aws_mocks


@pytest.fixture
def isolated_test_environment(mock_twilio, mock_stripe, mock_aws_services, mock_edamam):
    """Completely isolated test environment with all external dependencies mocked"""
    return {
        'twilio': mock_twilio,
        'stripe': mock_stripe,
        'aws': mock_aws_services,
        'edamam': mock_edamam
    }
