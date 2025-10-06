"""
Real-time User Cost Tracking Service
Monitors every API call, token usage, and service cost per user to ensure profitability
"""

import boto3
import os
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

class UserCostTracker:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.cost_table = self.dynamodb.Table('ai-nutritionist-user-costs')
        self.revenue_table = self.dynamodb.Table('ai-nutritionist-user-revenue')
        self.tokens_table = self.dynamodb.Table('ai-nutritionist-user-tokens')
        
        # Cost rates (updated Oct 2025)
        self.COST_RATES = {
            'bedrock_claude_3_haiku': 0.00025,  # per 1K input tokens
            'bedrock_claude_3_haiku_output': 0.00125,  # per 1K output tokens
            # Messaging providers (approximate, update for your account/pricing)
            'aws_end_user_messaging_whatsapp': 0.0075,   # per message (legacy)
            'twilio_default': 0.0070,      # per message (SMS/WA blended est.)
            'whatsapp_cloud': 0.0050,      # per message
            'dynamodb_read': 0.0000125,  # per read unit
            'dynamodb_write': 0.0000125,  # per write unit
            'lambda_execution': 0.000016667,  # per GB-second
            'api_gateway': 0.0000035,  # per request
            'edamam_api': 0.001,  # per recipe API call
            's3_storage': 0.000023,  # per GB-month
            'cloudwatch': 0.00000005  # per metric
        }
        
        # Revenue thresholds and limits
        self.PROFIT_THRESHOLDS = {
            'minimum_monthly_profit': Decimal('3.00'),
            'target_monthly_revenue': Decimal('5.00'),
            'maximum_monthly_cost': Decimal('2.00'),
            'free_tier_cost_limit': Decimal('0.50'),
            'warning_threshold': Decimal('1.50'),
            'restriction_threshold': Decimal('1.75'),
            'cutoff_threshold': Decimal('2.00')
        }
        
        # Token costs and limits
        self.TOKEN_SYSTEM = {
            'free_monthly_tokens': 100,
            'token_cost_usd': 0.05,  # $0.05 per token
            'token_usage_rates': {
                'simple_message': 1,
                'meal_plan': 5,
                'grocery_list': 2,
                'nutrition_analysis': 3,
                'recipe_search': 2,
                'dietary_advice': 4
            }
        }

    def track_cost_event(self, user_phone: str, event_type: str, 
                        cost_details: Dict, actual_cost: float) -> Dict:
        """Track a cost-generating event for a user"""
        try:
            timestamp = datetime.utcnow().isoformat()
            cost_decimal = Decimal(str(actual_cost))
            
            # Store detailed cost event
            cost_event = {
                'user_phone': user_phone,
                'timestamp': timestamp,
                'event_type': event_type,
                'cost_details': cost_details,
                'actual_cost': cost_decimal,
                'month': datetime.utcnow().strftime('%Y-%m'),
                'ttl': int(time.time()) + (90 * 24 * 60 * 60)  # 90 days
            }
            
            self.cost_table.put_item(Item=cost_event)
            
            # Update monthly cost totals
            monthly_cost = self.get_monthly_cost(user_phone)
            updated_cost = monthly_cost + cost_decimal
            
            # Check if user needs intervention
            intervention_needed = self.check_intervention_needed(user_phone, updated_cost)
            
            return {
                'cost_tracked': True,
                'event_cost': float(cost_decimal),
                'monthly_cost': float(updated_cost),
                'intervention_needed': intervention_needed,
                'remaining_free_allowance': max(0, float(self.PROFIT_THRESHOLDS['free_tier_cost_limit'] - updated_cost))
            }
            
        except Exception as e:
            return {
                'cost_tracked': False,
                'error': str(e),
                'monthly_cost': 0,
                'intervention_needed': {'type': 'error', 'action': 'manual_review'}
            }

    def get_monthly_cost(self, user_phone: str) -> Decimal:
        """Get total costs for user this month"""
        try:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            response = self.cost_table.query(
                KeyConditionExpression='user_phone = :phone',
                FilterExpression='month = :month',
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':month': current_month
                }
            )
            
            total_cost = Decimal('0')
            for item in response.get('Items', []):
                total_cost += item.get('actual_cost', Decimal('0'))
                
            return total_cost
            
        except Exception:
            return Decimal('0')

    def get_monthly_revenue(self, user_phone: str) -> Decimal:
        """Get total revenue from user this month"""
        try:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            response = self.revenue_table.query(
                KeyConditionExpression='user_phone = :phone',
                FilterExpression='month = :month',
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':month': current_month
                }
            )
            
            total_revenue = Decimal('0')
            for item in response.get('Items', []):
                total_revenue += item.get('revenue_amount', Decimal('0'))
                
            return total_revenue
            
        except Exception:
            return Decimal('0')

    def get_user_token_balance(self, user_phone: str) -> int:
        """Get current token balance for user"""
        try:
            response = self.tokens_table.get_item(
                Key={'user_phone': user_phone}
            )
            
            if 'Item' in response:
                return int(response['Item'].get('token_balance', 0))
            else:
                # New user gets free tokens
                free_tokens = self.TOKEN_SYSTEM['free_monthly_tokens']
                self.set_user_token_balance(user_phone, free_tokens)
                return free_tokens
                
        except Exception:
            return 0

    def set_user_token_balance(self, user_phone: str, token_balance: int):
        """Set token balance for user"""
        try:
            self.tokens_table.put_item(
                Item={
                    'user_phone': user_phone,
                    'token_balance': token_balance,
                    'last_updated': datetime.utcnow().isoformat(),
                    'month': datetime.utcnow().strftime('%Y-%m')
                }
            )
        except Exception:
            pass

    def deduct_tokens(self, user_phone: str, action_type: str) -> Dict:
        """Deduct tokens for an action and return status"""
        try:
            tokens_required = self.TOKEN_SYSTEM['token_usage_rates'].get(action_type, 1)
            current_balance = self.get_user_token_balance(user_phone)
            
            if current_balance >= tokens_required:
                new_balance = current_balance - tokens_required
                self.set_user_token_balance(user_phone, new_balance)
                
                return {
                    'tokens_deducted': True,
                    'tokens_used': tokens_required,
                    'remaining_balance': new_balance,
                    'action_allowed': True
                }
            else:
                return {
                    'tokens_deducted': False,
                    'tokens_required': tokens_required,
                    'current_balance': current_balance,
                    'action_allowed': False,
                    'payment_required': True,
                    'payment_amount': self.calculate_token_purchase_amount(tokens_required)
                }
                
        except Exception as e:
            return {
                'tokens_deducted': False,
                'error': str(e),
                'action_allowed': False
            }

    def calculate_token_purchase_amount(self, tokens_needed: int) -> float:
        """Calculate minimum purchase amount for tokens needed"""
        # Round up to next 20 tokens (minimum purchase)
        tokens_to_buy = max(20, ((tokens_needed + 19) // 20) * 20)
        return tokens_to_buy * self.TOKEN_SYSTEM['token_cost_usd']

    def check_intervention_needed(self, user_phone: str, current_cost: Decimal) -> Dict:
        """Check if user needs cost intervention"""
        monthly_revenue = self.get_monthly_revenue(user_phone)
        monthly_profit = monthly_revenue - current_cost
        
        # Check various thresholds
        if current_cost > self.PROFIT_THRESHOLDS['cutoff_threshold'] and monthly_profit < self.PROFIT_THRESHOLDS['minimum_monthly_profit']:
            return {
                'type': 'service_cutoff',
                'action': 'require_payment',
                'message': 'Service suspended. Please purchase tokens to continue.',
                'payment_required': True,
                'minimum_payment': 5.00
            }
        elif current_cost > self.PROFIT_THRESHOLDS['restriction_threshold']:
            return {
                'type': 'service_restriction',
                'action': 'affiliate_only',
                'message': 'To continue, please click on our partner recommendations.',
                'require_affiliate_interaction': True
            }
        elif current_cost > self.PROFIT_THRESHOLDS['warning_threshold']:
            return {
                'type': 'cost_warning',
                'action': 'upsell_tokens',
                'message': 'You\'re approaching your free limit. Purchase tokens for unlimited access!',
                'upsell_opportunity': True
            }
        elif current_cost > self.PROFIT_THRESHOLDS['free_tier_cost_limit']:
            return {
                'type': 'free_tier_exceeded',
                'action': 'premium_promotion',
                'message': 'Upgrade to Premium for unlimited meal plans and features!',
                'upgrade_opportunity': True
            }
        else:
            return {
                'type': 'no_intervention',
                'action': 'continue_service',
                'message': 'Service running normally'
            }

    def calculate_bedrock_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Bedrock API call"""
        input_cost = (input_tokens / 1000) * self.COST_RATES['bedrock_claude_3_haiku']
        output_cost = (output_tokens / 1000) * self.COST_RATES['bedrock_claude_3_haiku_output']
        return input_cost + output_cost

    def calculate_full_interaction_cost(self, interaction_data: Dict) -> float:
        """Calculate total cost for a complete user interaction"""
        total_cost = 0.0
        
        # API costs
        if 'bedrock_tokens' in interaction_data:
            total_cost += self.calculate_bedrock_cost(
                interaction_data['bedrock_tokens']['input'],
                interaction_data['bedrock_tokens']['output']
            )
        
        # Message costs
        if 'messages_sent' in interaction_data:
            provider = os.getenv('MESSAGING_PROVIDER', 'aws_end_user_messaging').lower()
            rate_key = 'aws_end_user_messaging_whatsapp'
            if provider == 'twilio':
                rate_key = 'twilio_default'
            elif provider == 'whatsapp_cloud':
                rate_key = 'whatsapp_cloud'
            total_cost += interaction_data['messages_sent'] * self.COST_RATES.get(rate_key, self.COST_RATES['twilio_default'])
        
        # Database costs
        if 'db_operations' in interaction_data:
            total_cost += (
                interaction_data['db_operations']['reads'] * self.COST_RATES['dynamodb_read'] +
                interaction_data['db_operations']['writes'] * self.COST_RATES['dynamodb_write']
            )
        
        # Lambda costs
        if 'lambda_duration_ms' in interaction_data:
            # Assuming 256MB memory allocation
            gb_seconds = (interaction_data['lambda_duration_ms'] / 1000) * (256 / 1024)
            total_cost += gb_seconds * self.COST_RATES['lambda_execution']
        
        # API Gateway
        total_cost += self.COST_RATES['api_gateway']
        
        return round(total_cost, 6)

    def get_user_profitability_status(self, user_phone: str) -> Dict:
        """Get comprehensive profitability status for user"""
        monthly_cost = self.get_monthly_cost(user_phone)
        monthly_revenue = self.get_monthly_revenue(user_phone)
        monthly_profit = monthly_revenue - monthly_cost
        token_balance = self.get_user_token_balance(user_phone)
        
        # Calculate metrics
        profit_margin = float((monthly_profit / monthly_revenue * 100)) if monthly_revenue > 0 else 0
        cost_efficiency = float(monthly_cost / monthly_revenue * 100) if monthly_revenue > 0 else 100
        
        return {
            'user_phone': user_phone,
            'monthly_cost': float(monthly_cost),
            'monthly_revenue': float(monthly_revenue),
            'monthly_profit': float(monthly_profit),
            'profit_margin_percent': round(profit_margin, 2),
            'cost_efficiency_percent': round(cost_efficiency, 2),
            'token_balance': token_balance,
            'is_profitable': monthly_profit >= self.PROFIT_THRESHOLDS['minimum_monthly_profit'],
            'needs_intervention': monthly_profit < self.PROFIT_THRESHOLDS['minimum_monthly_profit'],
            'status': 'profitable' if monthly_profit >= self.PROFIT_THRESHOLDS['minimum_monthly_profit'] else 'intervention_needed',
            'days_remaining_in_month': (datetime.utcnow().replace(day=28) + timedelta(days=4) - datetime.utcnow().replace(day=28)).days
        }

    def record_revenue_event(self, user_phone: str, revenue_type: str, amount: float, details: Dict = None):
        """Record a revenue event for the user"""
        try:
            timestamp = datetime.utcnow().isoformat()
            
            revenue_event = {
                'user_phone': user_phone,
                'timestamp': timestamp,
                'revenue_type': revenue_type,
                'revenue_amount': Decimal(str(amount)),
                'details': details or {},
                'month': datetime.utcnow().strftime('%Y-%m'),
                'ttl': int(time.time()) + (365 * 24 * 60 * 60)  # 1 year
            }
            
            self.revenue_table.put_item(Item=revenue_event)
            
        except Exception as e:
            print(f"Error recording revenue event: {e}")

    def get_all_users_profitability(self) -> List[Dict]:
        """Get profitability status for all users"""
        try:
            # Get all unique users from cost table
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            response = self.cost_table.scan(
                FilterExpression='month = :month',
                ExpressionAttributeValues={':month': current_month},
                ProjectionExpression='user_phone'
            )
            
            unique_users = set()
            for item in response.get('Items', []):
                unique_users.add(item['user_phone'])
            
            profitability_data = []
            for user_phone in unique_users:
                user_status = self.get_user_profitability_status(user_phone)
                profitability_data.append(user_status)
            
            return sorted(profitability_data, key=lambda x: x['monthly_profit'], reverse=True)
            
        except Exception as e:
            return []


