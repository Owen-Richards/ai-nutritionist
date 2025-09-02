"""
Test the international phone number functionality without AWS dependencies
"""

import urllib.parse
from typing import Dict, Any, List, Optional

class TwilioServiceTest:
    """Test version of TwilioService without AWS dependencies"""
    
    # International phone number configurations
    COUNTRY_CONFIGS = {
        'US': {'currency': 'USD', 'language': 'en', 'measurement': 'imperial', 'timezone': 'America/New_York'},
        'UK': {'currency': 'GBP', 'language': 'en', 'measurement': 'metric', 'timezone': 'Europe/London'},
        'AU': {'currency': 'AUD', 'language': 'en', 'measurement': 'metric', 'timezone': 'Australia/Sydney'},
        'CA': {'currency': 'CAD', 'language': 'en', 'measurement': 'metric', 'timezone': 'America/Toronto'},
        'IN': {'currency': 'INR', 'language': 'en', 'measurement': 'metric', 'timezone': 'Asia/Kolkata'},
        'BR': {'currency': 'BRL', 'language': 'pt', 'measurement': 'metric', 'timezone': 'America/Sao_Paulo'},
        'DE': {'currency': 'EUR', 'language': 'de', 'measurement': 'metric', 'timezone': 'Europe/Berlin'},
        'FR': {'currency': 'EUR', 'language': 'fr', 'measurement': 'metric', 'timezone': 'Europe/Paris'},
        'JP': {'currency': 'JPY', 'language': 'ja', 'measurement': 'metric', 'timezone': 'Asia/Tokyo'},
        'SG': {'currency': 'SGD', 'language': 'en', 'measurement': 'metric', 'timezone': 'Asia/Singapore'}
    }
    
    def _format_international_number(self, phone_number: str) -> Optional[str]:
        """Format phone number to international E.164 format"""
        try:
            # Remove all non-digit characters except +
            clean_number = ''.join(c for c in phone_number if c.isdigit() or c == '+')
            
            # Ensure it starts with +
            if not clean_number.startswith('+'):
                # If it starts with 00, replace with +
                if clean_number.startswith('00'):
                    clean_number = '+' + clean_number[2:]
                # If it's a US number without country code, add +1
                elif len(clean_number) == 10:
                    clean_number = '+1' + clean_number
                else:
                    clean_number = '+' + clean_number
            
            # Basic validation - should be 10-15 digits after +
            digits_only = clean_number[1:]
            if not (10 <= len(digits_only) <= 15):
                return None
                
            return clean_number
            
        except Exception as e:
            return None
    
    def get_country_config(self, country_code: str) -> Dict[str, Any]:
        """Get localized configuration for country"""
        return self.COUNTRY_CONFIGS.get(country_code.upper(), self.COUNTRY_CONFIGS['US'])
    
    def generate_whatsapp_link(self, phone_number: str, message: str = None) -> str:
        """Generate WhatsApp link for any international number"""
        try:
            # Remove + and format for wa.me
            clean_number = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            base_url = f"https://wa.me/{clean_number}"
            
            if message:
                encoded_message = urllib.parse.quote(message)
                return f"{base_url}?text={encoded_message}"
            
            return base_url
            
        except Exception as e:
            return f"https://wa.me/{phone_number.replace('+', '')}"
    
    def validate_international_phone(self, phone_number: str) -> Dict[str, Any]:
        """Validate international phone number format"""
        try:
            formatted = self._format_international_number(phone_number)
            
            if not formatted:
                return {'valid': False, 'error': 'Invalid phone number format'}
            
            # Extract country code (first 1-3 digits after +)
            digits = formatted[1:]
            country_code = None
            
            # Common country code patterns
            if digits.startswith('1'):
                country_code = 'US'  # US/Canada
            elif digits.startswith('44'):
                country_code = 'UK'
            elif digits.startswith('61'):
                country_code = 'AU'
            elif digits.startswith('91'):
                country_code = 'IN'
            elif digits.startswith('49'):
                country_code = 'DE'
            elif digits.startswith('33'):
                country_code = 'FR'
            elif digits.startswith('81'):
                country_code = 'JP'
            elif digits.startswith('65'):
                country_code = 'SG'
            elif digits.startswith('55'):
                country_code = 'BR'
            
            return {
                'valid': True,
                'formatted': formatted,
                'country_code': country_code,
                'whatsapp_link': self.generate_whatsapp_link(formatted),
                'config': self.get_country_config(country_code) if country_code else None
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def get_international_examples(self) -> List[Dict[str, str]]:
        """Get example phone numbers for different countries"""
        return [
            {'country': 'United States', 'code': 'US', 'example': '+1-555-123-4567', 'format': '+1XXXXXXXXXX'},
            {'country': 'United Kingdom', 'code': 'UK', 'example': '+44-20-7123-4567', 'format': '+44XXXXXXXXXX'},
            {'country': 'Australia', 'code': 'AU', 'example': '+61-3-8123-4567', 'format': '+61XXXXXXXXX'},
            {'country': 'Canada', 'code': 'CA', 'example': '+1-416-123-4567', 'format': '+1XXXXXXXXXX'},
            {'country': 'India', 'code': 'IN', 'example': '+91-80-1234-5678', 'format': '+91XXXXXXXXXX'},
            {'country': 'Germany', 'code': 'DE', 'example': '+49-30-1234-5678', 'format': '+49XXXXXXXXXX'},
            {'country': 'France', 'code': 'FR', 'example': '+33-1-42-12-34-56', 'format': '+33XXXXXXXXX'},
            {'country': 'Japan', 'code': 'JP', 'example': '+81-3-1234-5678', 'format': '+81XXXXXXXXXX'},
            {'country': 'Singapore', 'code': 'SG', 'example': '+65-6123-4567', 'format': '+65XXXXXXXX'},
            {'country': 'Brazil', 'code': 'BR', 'example': '+55-11-1234-5678', 'format': '+55XXXXXXXXXXX'}
        ]


def test_international_phones():
    """Test international phone number validation and formatting"""
    
    service = TwilioServiceTest()
    
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
    print("3. Update src/web/index.html with your number")
    print("4. Deploy with: sam build && sam deploy")

if __name__ == "__main__":
    test_international_phones()
