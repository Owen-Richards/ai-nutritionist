#!/bin/bash

# International Phone Number Configuration Script
# This script helps you set up your AI nutritionist with an international WhatsApp number

echo "🌍 AI Nutritionist International Phone Setup"
echo "============================================="

# Function to validate phone number format
validate_phone() {
    local phone=$1
    if [[ $phone =~ ^\\+[1-9][0-9]{9,14}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to update web interface
update_web_interface() {
    local phone_number=$1
    local clean_number=${phone_number:1}  # Remove the +
    
    echo "📱 Updating web interface with number: $phone_number"
    
    # Update index.html
    sed -i "s/YOUR_WHATSAPP_NUMBER/$clean_number/g" src/web/index.html
    
    echo "✅ Web interface updated!"
}

# Function to set AWS parameters
set_aws_parameters() {
    local phone_number=$1
    local account_sid=$2
    local auth_token=$3
    
    echo "☁️ Setting AWS Parameter Store values..."
    
    # Set phone number
    aws ssm put-parameter \
        --name "/ai-nutritionist/twilio/phone-number" \
        --value "$phone_number" \
        --type "String" \
        --overwrite
    
    # Set account SID
    if [ ! -z "$account_sid" ]; then
        aws ssm put-parameter \
            --name "/ai-nutritionist/twilio/account-sid" \
            --value "$account_sid" \
            --type "String" \
            --overwrite
    fi
    
    # Set auth token
    if [ ! -z "$auth_token" ]; then
        aws ssm put-parameter \
            --name "/ai-nutritionist/twilio/auth-token" \
            --value "$auth_token" \
            --type "SecureString" \
            --overwrite
    fi
    
    echo "✅ AWS parameters set!"
}

# Function to test phone number
test_phone_number() {
    local phone_number=$1
    
    echo "🧪 Testing phone number: $phone_number"
    
    # Test with Python script
    python3 -c "
import sys
sys.path.append('src')
from services.twilio_service import TwilioService

service = TwilioService()
result = service.validate_international_phone('$phone_number')
print(f'Validation result: {result}')

if result['valid']:
    print(f'✅ Valid number!')
    print(f'Formatted: {result[\"formatted\"]}')
    print(f'Country: {result.get(\"country_code\", \"Unknown\")}')
    print(f'WhatsApp link: {result[\"whatsapp_link\"]}')
else:
    print(f'❌ Invalid: {result[\"error\"]}')
"
}

# Main setup process
echo ""
echo "Please choose your setup option:"
echo "1. Quick setup with phone number only"
echo "2. Full Twilio setup (phone + credentials)"
echo "3. Test existing phone number"
echo "4. Show example numbers"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📱 Quick Phone Number Setup"
        echo "==========================="
        echo ""
        echo "Examples of valid international numbers:"
        echo "  US: +15551234567"
        echo "  UK: +442071234567"
        echo "  AU: +61381234567"
        echo "  DE: +493012345678"
        echo ""
        
        read -p "Enter your WhatsApp Business number (with +): " phone_number
        
        if validate_phone "$phone_number"; then
            echo "✅ Valid phone number format!"
            update_web_interface "$phone_number"
            test_phone_number "$phone_number"
            
            echo ""
            echo "🎉 Quick setup complete!"
            echo "Your WhatsApp number: $phone_number"
            echo "Clean number for wa.me: ${phone_number:1}"
            echo ""
            echo "Next steps:"
            echo "1. Test the web interface: open src/web/index.html"
            echo "2. Deploy to AWS: sam build && sam deploy"
            echo "3. Set up Twilio credentials for production"
        else
            echo "❌ Invalid phone number format. Please use international format like +15551234567"
        fi
        ;;
        
    2)
        echo ""
        echo "🔐 Full Twilio Setup"
        echo "==================="
        echo ""
        
        read -p "Enter your WhatsApp Business number (with +): " phone_number
        read -p "Enter your Twilio Account SID: " account_sid
        read -s -p "Enter your Twilio Auth Token: " auth_token
        echo ""
        
        if validate_phone "$phone_number"; then
            echo "✅ Valid phone number format!"
            update_web_interface "$phone_number"
            set_aws_parameters "$phone_number" "$account_sid" "$auth_token"
            test_phone_number "$phone_number"
            
            echo ""
            echo "🎉 Full setup complete!"
            echo "Ready for production deployment!"
        else
            echo "❌ Invalid phone number format. Please use international format like +15551234567"
        fi
        ;;
        
    3)
        echo ""
        read -p "Enter phone number to test (with +): " phone_number
        test_phone_number "$phone_number"
        ;;
        
    4)
        echo ""
        echo "📋 Example International Phone Numbers"
        echo "====================================="
        echo ""
        python3 -c "
import sys
sys.path.append('src')
from services.twilio_service import TwilioService

service = TwilioService()
examples = service.get_international_examples()

for example in examples:
    print(f'{example[\"country\"]:15} ({example[\"code\"]}): {example[\"example\"]:18} Format: {example[\"format\"]}')
"
        echo ""
        echo "Choose a number from your preferred country and run this script again with option 1 or 2."
        ;;
        
    *)
        echo "❌ Invalid choice. Please run the script again."
        ;;
esac

echo ""
echo "📚 For more information, see INTERNATIONAL_PHONE_SETUP.md"
echo "🚀 To deploy: sam build && sam deploy --guided"
