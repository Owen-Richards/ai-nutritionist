# Quick Start Guide

Get your AI Nutritionist Assistant up and running in under 10 minutes!

## Prerequisites

Before you begin, ensure you have:

- ✅ **AWS Account** with CLI configured
- ✅ **Python 3.11+** installed  
- ✅ **Twilio Account** with WhatsApp Business API
- ✅ **Docker** (for local testing)

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Owen-Richards/ai-nutritionist.git
cd ai-nutritionist

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure AWS

```bash
# Configure AWS CLI (if not already done)
aws configure

# Set up required parameters
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/account-sid" \
  --value "your-twilio-sid" \
  --type "String"

aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/auth-token" \
  --value "your-twilio-token" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/phone-number" \
  --value "your-twilio-number" \
  --type "String"
```

## Step 3: Deploy Infrastructure

```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Build the application
sam build

# Deploy with guided setup
sam deploy --guided
```

During deployment, you'll be prompted for:
- **Stack Name**: `ai-nutritionist-prod`
- **AWS Region**: Your preferred region (e.g., `us-east-1`)
- **Confirm changes**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`
- **Save parameters to config file**: `Y`

## Step 4: Configure Twilio Webhook

1. Go to your [Twilio Console](https://console.twilio.com/)
2. Navigate to **Phone Numbers** → **Manage** → **Active numbers**
3. Click on your WhatsApp-enabled number
4. Set the webhook URL to: `https://your-api-gateway-url/webhook`
5. Set HTTP method to `POST`

## Step 5: Test Your Bot

Send a message to your Twilio WhatsApp number:

```
Hello! I need a meal plan for 2 people with a $60 budget. We're vegetarian.
```

You should receive an AI-generated meal plan within seconds! 🎉

## Next Steps

- [📖 Learn about available commands](../user-guide/commands.md)
- [👨‍💻 Set up local development](../developer/local-development.md)
- [🔧 Configure advanced features](configuration.md)

## Troubleshooting

### Common Issues

**"Module not found" errors**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**AWS deployment fails**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Ensure SAM CLI is installed
sam --version
```

**Twilio webhook not responding**
- Verify the webhook URL is correct
- Check CloudWatch logs for errors
- Ensure API Gateway is deployed

For more help, see our [Troubleshooting Guide](../operations/troubleshooting.md).
