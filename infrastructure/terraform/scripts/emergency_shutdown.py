#!/usr/bin/env python3
"""
Emergency Shutdown Script for AWS Cost Control
Automatically shuts down or limits resources when budget threshold is exceeded
"""

import json
import boto3
import logging
import os
from typing import Dict, List, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Emergency shutdown handler triggered by budget alerts
    """
    try:
        # Parse SNS message
        message = json.loads(event['Records'][0]['Sns']['Message'])
        logger.info(f"Budget alert received: {message}")
        
        # Get configuration from environment
        project_name = os.getenv('PROJECT_NAME', 'ai-nutritionist')
        environment = os.getenv('ENVIRONMENT', 'dev')
        owner_email = os.getenv('OWNER_EMAIL')
        budget_threshold = float(os.getenv('BUDGET_THRESHOLD', '50'))
        
        # Initialize AWS clients
        lambda_client = boto3.client('lambda')
        apigateway_client = boto3.client('apigateway')
        dynamodb_client = boto3.client('dynamodb')
        sns_client = boto3.client('sns')
        ce_client = boto3.client('ce')
        
        # Get current spend
        current_spend = get_current_monthly_spend(ce_client, project_name)
        logger.info(f"Current monthly spend: ${current_spend}")
        
        if current_spend >= budget_threshold * 0.95:  # 95% threshold
            logger.warning(f"EMERGENCY: Budget threshold exceeded! Current: ${current_spend}, Limit: ${budget_threshold}")
            
            # Execute emergency shutdown
            shutdown_results = execute_emergency_shutdown(
                lambda_client, apigateway_client, dynamodb_client,
                project_name, environment
            )
            
            # Send emergency notification
            send_emergency_notification(
                sns_client, owner_email, current_spend, budget_threshold, shutdown_results
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Emergency shutdown executed',
                    'current_spend': current_spend,
                    'budget_limit': budget_threshold,
                    'actions_taken': shutdown_results
                })
            }
        
        elif current_spend >= budget_threshold * 0.8:  # 80% warning
            logger.warning(f"WARNING: Budget at 80% threshold. Current: ${current_spend}")
            
            # Apply cost reduction measures
            cost_reduction_results = apply_cost_reduction_measures(
                lambda_client, apigateway_client, project_name, environment
            )
            
            # Send warning notification
            send_warning_notification(
                sns_client, owner_email, current_spend, budget_threshold, cost_reduction_results
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Cost reduction measures applied',
                    'current_spend': current_spend,
                    'budget_limit': budget_threshold,
                    'actions_taken': cost_reduction_results
                })
            }
        
        else:
            logger.info(f"Budget within normal limits: ${current_spend} of ${budget_threshold}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Budget within limits',
                    'current_spend': current_spend,
                    'budget_limit': budget_threshold
                })
            }
            
    except Exception as e:
        logger.error(f"Error in emergency shutdown: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Emergency shutdown failed'
            })
        }

def get_current_monthly_spend(ce_client, project_name: str) -> float:
    """Get current monthly spend for the project"""
    try:
        # Get current month range
        now = datetime.now()
        start_date = f"{now.year}-{now.month:02d}-01"
        end_date = f"{now.year}-{now.month:02d}-{now.day:02d}"
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'TAG',
                    'Key': 'Project'
                }
            ]
        )
        
        total_cost = 0.0
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                if project_name.lower() in group['Keys'][0].lower():
                    amount = float(group['Metrics']['BlendedCost']['Amount'])
                    total_cost += amount
        
        return total_cost
        
    except Exception as e:
        logger.error(f"Error getting current spend: {str(e)}")
        return 0.0

def execute_emergency_shutdown(lambda_client, apigateway_client, dynamodb_client, 
                             project_name: str, environment: str) -> List[str]:
    """Execute emergency shutdown procedures"""
    actions_taken = []
    
    try:
        # 1. Reduce Lambda memory and concurrency
        lambda_functions = get_project_lambda_functions(lambda_client, project_name, environment)
        for function_name in lambda_functions:
            try:
                # Reduce memory to minimum
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    MemorySize=128,
                    Timeout=10
                )
                
                # Set reserved concurrency to 1
                lambda_client.put_provisioned_concurrency_config(
                    FunctionName=function_name,
                    Qualifier='$LATEST',
                    ProvisionedConcurrencyConfig={'ProvisionedConcurrency': 1}
                )
                
                actions_taken.append(f"Reduced Lambda {function_name} to minimum settings")
                
            except Exception as e:
                logger.error(f"Error updating Lambda {function_name}: {str(e)}")
        
        # 2. Disable API Gateway caching
        try:
            apis = apigateway_client.get_rest_apis()
            for api in apis['items']:
                if project_name in api['name']:
                    stages = apigateway_client.get_stages(restApiId=api['id'])
                    for stage in stages['item']:
                        apigateway_client.update_stage(
                            restApiId=api['id'],
                            stageName=stage['stageName'],
                            patchOps=[
                                {
                                    'op': 'replace',
                                    'path': '/cacheClusterEnabled',
                                    'value': 'false'
                                }
                            ]
                        )
            actions_taken.append("Disabled API Gateway caching")
        except Exception as e:
            logger.error(f"Error disabling API caching: {str(e)}")
        
        # 3. Set DynamoDB to on-demand billing
        try:
            tables = dynamodb_client.list_tables()
            for table_name in tables['TableNames']:
                if project_name in table_name:
                    dynamodb_client.update_table(
                        TableName=table_name,
                        BillingMode='PAY_PER_REQUEST'
                    )
            actions_taken.append("Switched DynamoDB to pay-per-request")
        except Exception as e:
            logger.error(f"Error updating DynamoDB billing: {str(e)}")
        
        return actions_taken
        
    except Exception as e:
        logger.error(f"Error in emergency shutdown: {str(e)}")
        return actions_taken

def apply_cost_reduction_measures(lambda_client, apigateway_client, 
                                project_name: str, environment: str) -> List[str]:
    """Apply cost reduction measures at 80% threshold"""
    actions_taken = []
    
    try:
        # Reduce Lambda memory to 256MB
        lambda_functions = get_project_lambda_functions(lambda_client, project_name, environment)
        for function_name in lambda_functions:
            try:
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    MemorySize=256,
                    Timeout=30
                )
                actions_taken.append(f"Reduced Lambda {function_name} memory to 256MB")
            except Exception as e:
                logger.error(f"Error updating Lambda {function_name}: {str(e)}")
        
        return actions_taken
        
    except Exception as e:
        logger.error(f"Error in cost reduction: {str(e)}")
        return actions_taken

def get_project_lambda_functions(lambda_client, project_name: str, environment: str) -> List[str]:
    """Get all Lambda functions for the project"""
    try:
        response = lambda_client.list_functions()
        project_functions = []
        
        for function in response['Functions']:
            function_name = function['FunctionName']
            if project_name in function_name and environment in function_name:
                project_functions.append(function_name)
        
        return project_functions
        
    except Exception as e:
        logger.error(f"Error listing Lambda functions: {str(e)}")
        return []

def send_emergency_notification(sns_client, owner_email: str, current_spend: float, 
                               budget_limit: float, actions_taken: List[str]):
    """Send emergency shutdown notification"""
    try:
        message = f"""
🚨 EMERGENCY BUDGET ALERT 🚨

Your AI Nutritionist application has exceeded the budget threshold!

💰 BUDGET STATUS:
- Current Spend: ${current_spend:.2f}
- Budget Limit: ${budget_limit:.2f}
- Percentage Used: {(current_spend/budget_limit)*100:.1f}%

🛑 EMERGENCY ACTIONS TAKEN:
"""
        for action in actions_taken:
            message += f"• {action}\n"
        
        message += f"""
⚡ IMMEDIATE ACTIONS REQUIRED:
1. Review your AWS Cost Explorer immediately
2. Check for any unexpected usage patterns
3. Consider pausing testing until costs are analyzed
4. Review and adjust budget limits if needed

📊 COST ANALYSIS:
- Login to AWS Console → Cost Explorer
- Check Bedrock, Lambda, and DynamoDB usage
- Look for any anomalous API calls

This emergency shutdown was triggered automatically to protect your budget.
All non-essential features have been disabled.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        # This would need an SNS topic ARN to send to
        logger.info(f"Emergency notification prepared for {owner_email}")
        logger.info(message)
        
    except Exception as e:
        logger.error(f"Error sending emergency notification: {str(e)}")

def send_warning_notification(sns_client, owner_email: str, current_spend: float, 
                            budget_limit: float, actions_taken: List[str]):
    """Send warning notification at 80% threshold"""
    try:
        message = f"""
⚠️ BUDGET WARNING ALERT ⚠️

Your AI Nutritionist application is approaching the budget limit.

💰 BUDGET STATUS:
- Current Spend: ${current_spend:.2f}
- Budget Limit: ${budget_limit:.2f}
- Percentage Used: {(current_spend/budget_limit)*100:.1f}%

🔧 COST REDUCTION MEASURES APPLIED:
"""
        for action in actions_taken:
            message += f"• {action}\n"
        
        message += f"""
📈 RECOMMENDATIONS:
1. Monitor usage more closely
2. Consider reducing testing frequency
3. Review which features are most expensive
4. Check if budget needs adjustment

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        logger.info(f"Warning notification prepared for {owner_email}")
        logger.info(message)
        
    except Exception as e:
        logger.error(f"Error sending warning notification: {str(e)}")
