#!/bin/bash

# Quick Phone Number Update Script
# Updates your web interface with your international WhatsApp number

echo "📱 Quick WhatsApp Number Update"
echo "==============================="

# Example numbers for different regions
echo ""
echo "Examples of valid international numbers:"
echo "  🇺🇸 US: +15551234567"
echo "  🇬🇧 UK: +442071234567"  
echo "  🇦🇺 AU: +61381234567"
echo "  🇩🇪 DE: +493012345678"
echo "  🇮🇳 IN: +918012345678"
echo "  🇯🇵 JP: +81312345678"
echo "  🇧🇷 BR: +551112345678"
echo ""

# Get user input
read -p "Enter your WhatsApp Business number (with +): " PHONE_NUMBER

# Validate format (basic check)
if [[ ! $PHONE_NUMBER =~ ^\+[1-9][0-9]{9,14}$ ]]; then
    echo "❌ Invalid format. Please use international format like +15551234567"
    exit 1
fi

# Extract clean number (remove +)
CLEAN_NUMBER=${PHONE_NUMBER:1}

echo ""
echo "📱 Your number: $PHONE_NUMBER"
echo "🔗 WhatsApp link format: https://wa.me/$CLEAN_NUMBER"

# Check if web file exists
if [[ ! -f "src/web/index.html" ]]; then
    echo "❌ Web interface file not found: src/web/index.html"
    echo "   Make sure you're running this from the project root directory"
    exit 1
fi

# Update the web interface
echo ""
echo "🔄 Updating web interface..."

# For Windows/bash, use sed carefully
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows bash
    cp src/web/index.html src/web/index.html.backup
    sed "s/YOUR_WHATSAPP_NUMBER/$CLEAN_NUMBER/g" src/web/index.html.backup > src/web/index.html
    echo "✅ Web interface updated! (Backup saved as index.html.backup)"
else
    # Linux/Mac
    sed -i.backup "s/YOUR_WHATSAPP_NUMBER/$CLEAN_NUMBER/g" src/web/index.html
    echo "✅ Web interface updated! (Backup saved as index.html.backup)"
fi

# Show the changes
echo ""
echo "📋 Updated WhatsApp links in your web interface:"
echo "---------------------------------------------------"
grep -n "wa.me" src/web/index.html | head -3

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. 🌐 Test the web interface: open src/web/index.html in your browser"
echo "2. ☁️  Deploy to AWS: sam build && sam deploy --guided"
echo "3. 🔧 Set up Twilio credentials for production messaging"
echo "4. 📱 Test with a real WhatsApp message!"

echo ""
echo "🔗 Test your WhatsApp link:"
echo "   https://wa.me/$CLEAN_NUMBER?text=Hi! I'd like to start meal planning"

# Create a simple HTML test file
cat > test_whatsapp_link.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Test WhatsApp Link</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
        .whatsapp-btn { 
            background: #25d366; 
            color: white; 
            padding: 15px 30px; 
            text-decoration: none; 
            border-radius: 25px; 
            font-size: 18px;
            display: inline-block;
            margin: 20px;
        }
        .whatsapp-btn:hover { background: #128c7e; }
    </style>
</head>
<body>
    <h1>🥗 AI Nutritionist Test</h1>
    <p>Click below to test your WhatsApp integration:</p>
    
    <a href="https://wa.me/$CLEAN_NUMBER?text=Hi! I'd like to start meal planning" class="whatsapp-btn">
        📱 Test WhatsApp Link
    </a>
    
    <p><strong>Your number:</strong> $PHONE_NUMBER</p>
    <p><strong>Link format:</strong> https://wa.me/$CLEAN_NUMBER</p>
    
    <h3>🌍 International Ready!</h3>
    <p>This link will work for users worldwide to contact your AI nutritionist.</p>
</body>
</html>
EOF

echo ""
echo "📄 Created test file: test_whatsapp_link.html"
echo "   Open this file in your browser to test the WhatsApp link!"
