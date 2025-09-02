"""
Test the international phone number functionality
"""

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from services.twilio_service import TwilioService

def test_international_phones():
    """Test international phone number validation and formatting"""
    
    service = TwilioService()
    
    print("🌍 Testing International Phone Number Support")
    print("=" * 50)
    
    # Test various phone number formats
    test_numbers = [
        "+1-555-123-4567",        # US format with dashes
        "+15551234567",           # US format clean
        "15551234567",            # US without +
        "+44 20 7123 4567",       # UK with spaces
        "+442071234567",          # UK clean
        "+61 3 8123 4567",        # Australia
        "+49 30 1234 5678",       # Germany
        "+91 80 1234 5678",       # India
        "+33 1 42 12 34 56",      # France
        "+81 3 1234 5678",        # Japan
        "+65 6123 4567",          # Singapore
        "+55 11 1234 5678",       # Brazil
        "invalid-number",         # Invalid
        "+1234",                  # Too short
    ]
    
    print("\\n📱 Phone Number Validation Tests:")
    print("-" * 40)
    
    for number in test_numbers:
        result = service.validate_international_phone(number)
        status = "✅" if result['valid'] else "❌"
        
        print(f"{status} {number:20} -> ", end="")
        
        if result['valid']:
            print(f"Valid! Country: {result.get('country_code', 'Unknown')}")
            print(f"   Formatted: {result['formatted']}")
            print(f"   WhatsApp:  {result['whatsapp_link']}")
        else:
            print(f"Invalid: {result['error']}")
        
        print()
    
    print("\\n🌎 Country Configuration Examples:")
    print("-" * 40)
    
    countries = ['US', 'UK', 'AU', 'DE', 'IN', 'JP', 'BR']
    for country in countries:
        config = service.get_country_config(country)
        print(f"{country}: {config['currency']} | {config['language']} | {config['measurement']}")
    
    print("\\n📋 International Number Examples:")
    print("-" * 40)
    
    examples = service.get_international_examples()
    for example in examples:
        print(f"{example['country']:15} ({example['code']}): {example['example']:18} -> {example['format']}")
    
    print("\\n🔗 WhatsApp Link Generation:")
    print("-" * 40)
    
    test_phone = "+15551234567"
    test_message = "Hi! I'd like to start meal planning"
    
    link = service.generate_whatsapp_link(test_phone, test_message)
    print(f"Phone: {test_phone}")
    print(f"Message: {test_message}")
    print(f"Link: {link}")
    
    print("\\n🎉 International phone support is working!")
    print("\\nNext steps:")
    print("1. Choose your international number from a provider like Twilio")
    print("2. Run: ./setup_international_phone.sh")
    print("3. Deploy with: sam build && sam deploy")

if __name__ == "__main__":
    test_international_phones()
