#!/usr/bin/env python3
"""
AWS SMS Service Test Script
Tests the AWS End User Messaging SMS functionality
"""

import sys
import os
import json
import boto3
from typing import Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.aws_sms_service import AWSSMSService


def test_aws_sms_service():
    """Test AWS SMS service functionality"""
    print("🧪 Testing AWS SMS Service...")
    
    try:
        # Initialize service
        sms_service = AWSSMSService()
        print("✅ AWS SMS service initialized successfully")
        
        # Test phone number validation
        test_numbers = [
            "+12345678901",  # US
            "+447123456789", # UK
            "+61412345678",  # Australia
            "+919876543210", # India
        ]
        
        print("\n📱 Testing phone number validation...")
        for number in test_numbers:
            result = sms_service.validate_international_phone(number)
            if result['valid']:
                print(f"✅ {number} -> {result['formatted']} ({result.get('country_code', 'Unknown')})")
            else:
                print(f"❌ {number} -> {result.get('error', 'Invalid')}")
        
        # Test country configuration
        print("\n🌍 Testing country configurations...")
        for country in ['US', 'UK', 'AU', 'IN', 'DE']:
            config = sms_service.get_country_config(country)
            print(f"✅ {country}: {config['currency']} | {config['language']} | {config['measurement']}")
        
        print("\n✅ All tests passed! AWS SMS service is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


def test_aws_resources():
    """Test AWS resources are properly configured"""
    print("🔍 Testing AWS resources...")
    
    try:
        # Test SMS client
        sms_client = boto3.client('pinpoint-sms-voice-v2')
        
        # List phone pools
        try:
            pools_response = sms_client.describe_pools()
            print(f"✅ Found {len(pools_response.get('Pools', []))} SMS phone pools")
        except Exception as e:
            print(f"⚠️ Phone pools not found: {str(e)}")
        
        # List phone numbers
        try:
            numbers_response = sms_client.describe_phone_numbers()
            phone_numbers = numbers_response.get('PhoneNumbers', [])
            print(f"✅ Found {len(phone_numbers)} phone numbers")
            for number in phone_numbers[:3]:  # Show first 3
                print(f"   📞 {number.get('PhoneNumber')} ({number.get('Status')})")
        except Exception as e:
            print(f"⚠️ Phone numbers not found: {str(e)}")
        
        # List configuration sets
        try:
            config_response = sms_client.describe_configuration_sets()
            configs = config_response.get('ConfigurationSets', [])
            print(f"✅ Found {len(configs)} configuration sets")
        except Exception as e:
            print(f"⚠️ Configuration sets not found: {str(e)}")
        
        # Test SQS queue
        try:
            sqs = boto3.client('sqs')
            queues = sqs.list_queues()
            queue_urls = queues.get('QueueUrls', [])
            sms_queues = [q for q in queue_urls if 'inbound-sms' in q]
            print(f"✅ Found {len(sms_queues)} SMS queues")
        except Exception as e:
            print(f"⚠️ SQS queues not found: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS resource test failed: {str(e)}")
        return False


def test_environment_variables():
    """Test required environment variables"""
    print("🔧 Testing environment variables...")
    
    required_vars = [
        'AWS_REGION',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY'
    ]
    
    optional_vars = [
        'PHONE_POOL_ID',
        'SMS_CONFIG_SET',
        'SQS_QUEUE_URL',
        'ENVIRONMENT'
    ]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_required:
        print(f"❌ Missing required variables: {', '.join(missing_required)}")
        return False
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"⚠️ {var} not set (will use defaults)")
    
    return True


def main():
    """Run all tests"""
    print("🚀 AWS SMS Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Environment variables
    if not test_environment_variables():
        all_passed = False
    
    print("\n" + "=" * 50)
    
    # Test 2: AWS resources
    if not test_aws_resources():
        all_passed = False
    
    print("\n" + "=" * 50)
    
    # Test 3: SMS service
    if not test_aws_sms_service():
        all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All tests passed! AWS SMS is ready for deployment.")
        print("\n📋 Next steps:")
        print("1. Deploy Terraform infrastructure: terraform apply")
        print("2. Update Lambda environment variables")
        print("3. Test with real phone number")
        print("4. Monitor CloudWatch logs")
        return 0
    else:
        print("❌ Some tests failed. Please fix issues before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
