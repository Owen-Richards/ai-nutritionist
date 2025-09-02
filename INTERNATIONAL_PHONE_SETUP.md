# International WhatsApp Phone Number Setup Guide

## 🌍 Setting Up Your AI Nutritionist for Global Users

This guide shows you how to configure your AI nutritionist WhatsApp bot with an international phone number that works for users worldwide.

## 📱 Phone Number Options

### Option 1: Twilio WhatsApp Business API (Recommended)
**Best for: Professional deployment with global reach**

#### Step 1: Get Twilio WhatsApp Number
```bash
# 1. Sign up at https://www.twilio.com/console
# 2. Apply for WhatsApp Business API approval
# 3. Get your WhatsApp-enabled phone number
```

#### Step 2: Configure International Format
```python
# Example international numbers for different regions:
PHONE_NUMBERS = {
    'US': '+1555123XXXX',           # United States
    'UK': '+44207123XXXX',          # United Kingdom  
    'AU': '+61383123XXXX',          # Australia
    'CA': '+1416123XXXX',           # Canada
    'IN': '+91807123XXXX',          # India
    'BR': '+551234567XXX',          # Brazil
    'DE': '+4930123XXXXX',          # Germany
    'FR': '+33142123XXX',           # France
    'JP': '+81312341XXX',           # Japan
    'SG': '+6565123XXX',            # Singapore
}
```

### Option 2: WhatsApp Cloud API (Meta)
**Best for: Direct integration with Meta**

```python
# Using Meta's WhatsApp Cloud API
WHATSAPP_CLOUD_CONFIG = {
    'phone_number_id': 'YOUR_PHONE_NUMBER_ID',
    'access_token': 'YOUR_ACCESS_TOKEN',
    'webhook_verify_token': 'YOUR_WEBHOOK_TOKEN',
    'business_account_id': 'YOUR_BUSINESS_ACCOUNT_ID'
}
```

## 🔧 Implementation Steps

### 1. Update Environment Configuration

Create or update your environment variables:

```bash
# AWS Parameter Store (Production)
aws ssm put-parameter \
    --name "/ai-nutritionist/twilio/phone-number" \
    --value "+1555XXXXXXX" \
    --type "String"

aws ssm put-parameter \
    --name "/ai-nutritionist/twilio/account-sid" \
    --value "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" \
    --type "String"

aws ssm put-parameter \
    --name "/ai-nutritionist/twilio/auth-token" \
    --value "your-auth-token" \
    --type "SecureString"
```

### 2. Update Web Interface

Replace the placeholder in `src/web/index.html`:

```html
<!-- Before: -->
<a href="https://wa.me/YOUR_WHATSAPP_NUMBER?text=Hi! I'd like to start meal planning">

<!-- After: -->
<a href="https://wa.me/15551234567?text=Hi! I'd like to start meal planning">
```

### 3. Configure International Phone Number Validation

```python
# Add to your message handler
import phonenumbers
from phonenumbers import NumberParseException

def validate_international_phone(phone_number: str) -> Dict[str, Any]:
    """Validate and format international phone numbers"""
    try:
        # Parse the number
        parsed = phonenumbers.parse(phone_number, None)
        
        # Check if valid
        if not phonenumbers.is_valid_number(parsed):
            return {'valid': False, 'error': 'Invalid phone number'}
        
        # Format for different uses
        international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        
        # Get country info
        country_code = phonenumbers.region_code_for_number(parsed)
        carrier = phonenumbers.carrier.name_for_number(parsed, 'en')
        
        return {
            'valid': True,
            'international': international,  # +1 555-123-4567
            'e164': e164,                   # +15551234567
            'national': national,           # (555) 123-4567
            'country_code': country_code,   # US
            'carrier': carrier
        }
        
    except NumberParseException as e:
        return {'valid': False, 'error': str(e)}
```

## 🌐 Country-Specific Considerations

### Time Zones & Business Hours
```python
import pytz
from datetime import datetime

COUNTRY_TIMEZONES = {
    'US': 'America/New_York',
    'UK': 'Europe/London',
    'AU': 'Australia/Sydney',
    'IN': 'Asia/Kolkata',
    'BR': 'America/Sao_Paulo',
    'DE': 'Europe/Berlin',
    'FR': 'Europe/Paris',
    'JP': 'Asia/Tokyo',
    'SG': 'Asia/Singapore'
}

def get_local_time(country_code: str) -> datetime:
    """Get local time for country"""
    timezone = COUNTRY_TIMEZONES.get(country_code, 'UTC')
    tz = pytz.timezone(timezone)
    return datetime.now(tz)

def is_business_hours(country_code: str) -> bool:
    """Check if it's business hours in the user's country"""
    local_time = get_local_time(country_code)
    hour = local_time.hour
    return 8 <= hour <= 22  # 8 AM to 10 PM local time
```

### Language & Currency Support
```python
COUNTRY_CONFIGS = {
    'US': {'currency': 'USD', 'language': 'en', 'measurement': 'imperial'},
    'UK': {'currency': 'GBP', 'language': 'en', 'measurement': 'metric'},
    'AU': {'currency': 'AUD', 'language': 'en', 'measurement': 'metric'},
    'CA': {'currency': 'CAD', 'language': 'en', 'measurement': 'metric'},
    'IN': {'currency': 'INR', 'language': 'en', 'measurement': 'metric'},
    'BR': {'currency': 'BRL', 'language': 'pt', 'measurement': 'metric'},
    'DE': {'currency': 'EUR', 'language': 'de', 'measurement': 'metric'},
    'FR': {'currency': 'EUR', 'language': 'fr', 'measurement': 'metric'},
    'JP': {'currency': 'JPY', 'language': 'ja', 'measurement': 'metric'},
    'SG': {'currency': 'SGD', 'language': 'en', 'measurement': 'metric'}
}

def get_country_config(country_code: str) -> Dict:
    """Get localized configuration for country"""
    return COUNTRY_CONFIGS.get(country_code, COUNTRY_CONFIGS['US'])
```

## 🚀 Quick Setup Commands

### For US Number (Most Common)
```bash
# Set your actual Twilio WhatsApp number
export WHATSAPP_NUMBER="+15551234567"

# Update web interface
sed -i "s/YOUR_WHATSAPP_NUMBER/${WHATSAPP_NUMBER:1}/g" src/web/index.html

# Deploy to AWS
sam build && sam deploy --guided
```

### For International Number
```bash
# Example: UK number
export WHATSAPP_NUMBER="+447123456789"

# Update web interface (remove + for wa.me links)
sed -i "s/YOUR_WHATSAPP_NUMBER/${WHATSAPP_NUMBER:1}/g" src/web/index.html
```

## 📊 Recommended International Numbers

### High-Volume Countries
1. **United States**: `+1-555-XXX-XXXX` (Twilio)
2. **United Kingdom**: `+44-20-7XXX-XXXX` (Twilio)
3. **Canada**: `+1-416-XXX-XXXX` (Twilio)
4. **Australia**: `+61-3-8XXX-XXXX` (Twilio)

### Growing Markets
1. **India**: `+91-80XXX-XXXXX` (Local provider recommended)
2. **Brazil**: `+55-11-XXXX-XXXX` (Local compliance required)
3. **Germany**: `+49-30-XXXX-XXXX` (GDPR compliant)
4. **Singapore**: `+65-6XXX-XXXX` (Asia-Pacific hub)

## 🔐 Compliance & Regulations

### GDPR (Europe)
```python
# Add consent tracking for EU users
GDPR_COUNTRIES = ['DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'PL', 'SE', 'DK']

def requires_gdpr_consent(country_code: str) -> bool:
    return country_code in GDPR_COUNTRIES

def get_gdpr_consent_message() -> str:
    return (
        "🇪🇺 *Privacy Notice*\n"
        "By using this service, you consent to processing of your data "
        "for personalized nutrition advice. You can withdraw consent anytime by typing 'STOP'.\n\n"
        "Full privacy policy: https://yoursite.com/privacy"
    )
```

### WhatsApp Business Policy
- ✅ Clearly identify as automated service
- ✅ Provide opt-out mechanism
- ✅ Respect business hours
- ✅ Don't spam users
- ✅ Maintain conversation quality

## 🎯 Testing Your International Setup

```python
# Test different country formats
test_numbers = [
    "+1-555-123-4567",     # US
    "+44-20-7123-4567",    # UK  
    "+61-3-8123-4567",     # AU
    "+49-30-1234-5678",    # DE
    "+91-80-1234-5678",    # IN
]

for number in test_numbers:
    result = validate_international_phone(number)
    print(f"{number}: {result}")
```

## 📱 WhatsApp Link Generator

```python
def generate_whatsapp_link(phone_number: str, message: str = None) -> str:
    """Generate WhatsApp link for any international number"""
    # Remove + and format for wa.me
    clean_number = phone_number.replace('+', '').replace('-', '').replace(' ', '')
    
    base_url = f"https://wa.me/{clean_number}"
    
    if message:
        encoded_message = urllib.parse.quote(message)
        return f"{base_url}?text={encoded_message}"
    
    return base_url

# Example usage
us_link = generate_whatsapp_link("+1-555-123-4567", "Hi! I'd like to start meal planning")
uk_link = generate_whatsapp_link("+44-20-7123-4567", "Hello! I'd like nutrition advice")
```

## 🚀 Next Steps

1. **Choose your number** from a reputable provider (Twilio recommended)
2. **Update configuration** with your actual phone number
3. **Test international access** from different countries
4. **Configure compliance** features for your target markets
5. **Monitor usage** and optimize for peak hours

## 💡 Pro Tips

- **Use Twilio's Global Infrastructure** for best international delivery
- **Set up multiple numbers** for different regions if high volume
- **Monitor delivery rates** by country and adjust accordingly
- **Provide multiple contact methods** (WhatsApp + SMS + web chat)
- **Consider local partnerships** in major markets

## 🔗 Useful Resources

- [Twilio WhatsApp API](https://www.twilio.com/whatsapp)
- [WhatsApp Business API](https://business.whatsapp.com/products/business-api)
- [International Phone Number Formats](https://en.wikipedia.org/wiki/E.164)
- [Country Calling Codes](https://countrycode.org/)

---

Your AI nutritionist is now ready to serve users worldwide! 🌍🥗
