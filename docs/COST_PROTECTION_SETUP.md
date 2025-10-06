# 🛡️ Cost Protection Setup Guide for Solo Testing

This guide will help you set up strict cost controls and access restrictions to prevent unexpected AWS charges while testing your AI Nutritionist with a small group.

## 🚨 **CRITICAL: Do This FIRST**

### 1. **Set Your Budget Hard Cap**

```bash
# Edit cost-control.tfvars
monthly_budget_hard_cap = 25    # Your comfort zone (will auto-shutdown at 95%)
owner_email = "your-email@example.com"  # You'll get ALL alerts here
```

### 2. **Whitelist Only Authorized Users**

```bash
phone_number_whitelist = {
  "owner" = {
    phone_number = "+1234567890"    # ← CHANGE TO YOUR NUMBER
    daily_limit  = 25               # You get more usage
    monthly_limit = 200
  }
  "friend1" = {
    phone_number = "+1987654321"    # ← Friend's number
    daily_limit  = 10               # Limited usage
    monthly_limit = 50
  }
  # Add up to 8 more friends (max 10 total for cost control)
}
```

## 💰 **Cost Protection Features**

### **Hard Budget Limits**

- ✅ **Monthly Cap**: $25 (configurable)
- ✅ **Daily Limit**: $2 per day
- ✅ **Emergency Shutdown**: Auto-disables services at 95% budget
- ✅ **Real-time Alerts**: Email notifications for budget status

### **Usage Restrictions**

- ✅ **Phone Whitelist**: Only authorized numbers can use the service
- ✅ **Message Limits**: 15 messages/day per person, 300/month total
- ✅ **Feature Limits**: Control which features each person can access
- ✅ **Service Quotas**: AWS-level limits on Lambda, API Gateway usage

### **Automatic Cost Optimization**

- ✅ **Testing Mode**: Disables expensive features automatically
- ✅ **Minimal Resources**: Uses smallest possible Lambda memory/timeout
- ✅ **Pay-per-Request**: No provisioned capacity charges
- ✅ **Regional Only**: No global/multi-region features

## 🚀 **Quick Setup**

### **Step 1: Copy Configuration**

```bash
# Copy the example configuration
cp cost-control.tfvars.example cost-control.tfvars

# Edit with your details
nano cost-control.tfvars
```

### **Step 2: Deploy with Cost Controls**

```bash
# Deploy with strict cost controls
terraform apply -var-file="cost-control.tfvars"

# Confirm deployment
terraform output cost_protection_summary
```

### **Step 3: Test Authorization**

```bash
# Test that only whitelisted numbers work
curl -X POST your-api-endpoint \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "message": "test"}'  # ← Your number (should work)

curl -X POST your-api-endpoint \
  -H "Content-Type: application/json"
  -d '{"phone": "+1999888777", "message": "test"}'  # ← Random number (should be blocked)
```

## 📊 **Expected Costs**

### **Minimum Configuration (Testing Mode)**

```
Lambda (256MB, minimal usage):     $2-5/month
DynamoDB (pay-per-request):        $1-3/month
API Gateway (low volume):          $3-6/month
Bedrock AI (limited tokens):       $5-15/month
CloudWatch/Monitoring:             $1-2/month
SNS/SQS (alerts):                  $0.50/month
──────────────────────────────────────────────
TOTAL ESTIMATED:                   $12-32/month
```

### **If You Hit Budget Limits**

- **80% Budget ($20)**: Automatic cost reduction (smaller Lambda memory, etc.)
- **95% Budget ($24)**: **EMERGENCY SHUTDOWN** - all services minimized
- **100% Budget ($25)**: **HARD STOP** - you get alerts to take manual action

## 🔔 **Alert System**

You'll receive **immediate email alerts** for:

### **Budget Alerts**

- 📊 **Daily Budget Exceeded**: If you spend >$2 in one day
- ⚠️ **80% Monthly Budget**: Warning with automatic cost reduction
- 🚨 **95% Monthly Budget**: Emergency shutdown triggered
- 💸 **Cost Anomaly**: Unexpected spending spike ($3+)

### **Security Alerts**

- 🛡️ **Unauthorized Access**: Someone not on whitelist tries to use service
- 📈 **Usage Spike**: Unusual message volume from authorized users
- 🔒 **Rate Limit Hit**: Someone exceeding daily message limits

### **System Alerts**

- ⚡ **Emergency Actions**: What was shut down and why
- 📉 **Cost Reduction**: What optimizations were applied
- 💰 **Monthly Summary**: Total spend and usage breakdown

## 🛠️ **Managing Your Test Group**

### **Add a New Friend**

```bash
# Edit cost-control.tfvars
"friend3" = {
  phone_number     = "+1555987654"
  user_name        = "New Friend"
  daily_limit      = 5              # Start conservative
  monthly_limit    = 25
  features_enabled = ["meal_planning"]  # Basic features only
}

# Redeploy
terraform apply -var-file="cost-control.tfvars"
```

### **Remove Someone**

```bash
# Simply delete their entry from phone_number_whitelist
# Then redeploy - they'll be blocked immediately
terraform apply -var-file="cost-control.tfvars"
```

### **Adjust Limits**

```bash
# Increase someone's limits if needed
"friend1" = {
  phone_number = "+1987654321"
  daily_limit  = 20        # ← Increased from 10
  monthly_limit = 100      # ← Increased from 50
}

terraform apply -var-file="cost-control.tfvars"
```

## ⚡ **Emergency Procedures**

### **If You Get Budget Alert**

1. **Check AWS Cost Explorer** immediately
2. **Review CloudWatch logs** for unusual activity
3. **Check authorized users table** for unexpected usage
4. **Adjust limits** or **remove users** if needed

### **Manual Emergency Shutdown**

```bash
# If you need to shut down everything immediately
terraform destroy -var-file="cost-control.tfvars"

# This removes ALL resources and stops ALL charges
```

### **Reset Budget Mid-Month**

```bash
# If you want to reset budget tracking
aws budgets delete-budget --account-id YOUR_ACCOUNT_ID --budget-name ai-nutritionist-monthly-hard-cap-dev

# Then redeploy
terraform apply -var-file="cost-control.tfvars"
```

## 🎯 **Best Practices for Solo Testing**

### **Start Small**

- Begin with 2-3 friends maximum
- Set low daily limits (5-10 messages)
- Monitor costs daily for first week

### **Monitor Usage**

- Check AWS Cost Explorer weekly
- Review DynamoDB usage tracking table
- Watch CloudWatch metrics

### **Scale Gradually**

- Increase limits only after understanding costs
- Add new users one at a time
- Track cost per user

### **Emergency Planning**

- Keep owner_email monitored 24/7
- Have terraform destroy ready as nuclear option
- Know how to check AWS Cost Explorer quickly

## 🔒 **Security Notes**

### **Whitelist is ENFORCED at Multiple Levels**

1. **WAF Rules**: Block unauthorized IPs
2. **API Gateway Authorizer**: Validate phone numbers
3. **Lambda Authorization**: Check usage limits
4. **DynamoDB**: Track all usage

### **Data Protection**

- All authorized numbers stored encrypted
- Usage tracking has automatic cleanup (90 days)
- No sensitive data logged in CloudWatch

### **Cost Transparency**

- All costs tagged with Project=AI-Nutritionist
- Usage tracked per phone number
- Cost anomaly detection enabled

With these protections, you can safely test with friends while keeping costs under control! 🚀

## 📞 **Need Help?**

If you get stuck or costs seem high:

1. Check your cost-control.tfvars configuration
2. Review AWS Cost Explorer for detailed breakdown
3. Check CloudWatch logs for unusual activity
4. Consider reducing daily/monthly limits
5. Remove unused friends from whitelist

**Remember**: It's better to start with limits too low and increase them than to get surprised by a big bill! 💰
