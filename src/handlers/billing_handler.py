"""
Stripe Billing Webhook Handler
Processes Stripe webhook events for subscription management.
"""

import json
import logging
import os
import boto3
import stripe
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize services
ssm = boto3.client('ssm')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Stripe billing webhooks
    """
    correlation_id = context.aws_request_id
    logger.info(f"Billing webhook received - ID: {correlation_id}")
    
    try:
        # Get Stripe webhook secret from Parameter Store
        webhook_secret = ssm.get_parameter(
            Name='/ai-nutritionist/stripe/webhook-secret',
            WithDecryption=True
        )['Parameter']['Value']
        
        # Verify webhook signature
        payload = event.get('body', '')
        sig_header = event['headers'].get('stripe-signature', '')
        
        try:
            stripe_event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid payload'})
            }
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        
        # Import subscription service
        import sys
        sys.path.append('/opt/python')
        sys.path.append(os.path.join(os.path.dirname(__file__), '../services'))
        
        from subscription_service import get_subscription_service
        subscription_service = get_subscription_service()
        
        # Process the webhook event
        event_type = stripe_event['type']
        event_data = stripe_event['data']
        
        logger.info(f"Processing Stripe event: {event_type}")
        
        success = subscription_service.handle_webhook(event_type, event_data)
        
        if success:
            logger.info(f"Successfully processed webhook event: {event_type}")
            return {
                'statusCode': 200,
                'body': json.dumps({'received': True})
            }
        else:
            logger.error(f"Failed to process webhook event: {event_type}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Processing failed'})
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in billing webhook: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'correlation_id': correlation_id
            })
        }


if __name__ == "__main__":
    # Local testing
    test_event = {
        'body': '{"type": "customer.subscription.created"}',
        'headers': {
            'stripe-signature': 'test_signature'
        }
    }
    
    class MockContext:
        aws_request_id = 'test-request-id'
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
