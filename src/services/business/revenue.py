"""
Affiliate Revenue Service - High-Value Partnership Integration
Handles affiliate links, commissions, and revenue tracking for grocery delivery,
meal kits, supplements, and local marketplace partnerships
"""

import boto3
import logging
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


class AffiliateRevenueService:
    """Manages affiliate partnerships and commission tracking"""
    
    # High-commission affiliate partners
    AFFILIATE_PARTNERS = {
        'instacart': {
            'name': 'Instacart',
            'commission_rate': 0.15,  # 15%
            'base_url': 'https://www.instacart.com',
            'tracking_param': 'af_id',
            'min_order': 35.00,
            'categories': ['grocery_delivery']
        },
        'amazon_fresh': {
            'name': 'Amazon Fresh',
            'commission_rate': 0.08,  # 8%
            'base_url': 'https://www.amazon.com/alm/storefront',
            'tracking_param': 'tag',
            'min_order': 25.00,
            'categories': ['grocery_delivery', 'bulk_items']
        },
        'blue_apron': {
            'name': 'Blue Apron',
            'commission_rate': 0.20,  # 20%
            'base_url': 'https://www.blueapron.com',
            'tracking_param': 'cvosrc',
            'min_order': 0,
            'categories': ['meal_kits']
        },
        'hellofresh': {
            'name': 'HelloFresh',
            'commission_rate': 0.25,  # 25%
            'base_url': 'https://www.hellofresh.com',
            'tracking_param': 'c',
            'min_order': 0,
            'categories': ['meal_kits']
        },
        'vitamins_com': {
            'name': 'Vitamins.com',
            'commission_rate': 0.25,  # 25%
            'base_url': 'https://www.vitamins.com',
            'tracking_param': 'aff_id',
            'min_order': 0,
            'categories': ['supplements', 'health']
        },
        'thrive_market': {
            'name': 'Thrive Market',
            'commission_rate': 0.18,  # 18%
            'base_url': 'https://thrivemarket.com',
            'tracking_param': 'aid',
            'min_order': 49.00,
            'categories': ['organic', 'bulk_items']
        },
        'williams_sonoma': {
            'name': 'Williams Sonoma',
            'commission_rate': 0.08,  # 8%
            'base_url': 'https://www.williams-sonoma.com',
            'tracking_param': 'cm_mmc',
            'min_order': 0,
            'categories': ['kitchen_appliances', 'cookware']
        }
    }
    
    # Local marketplace categories
    LOCAL_MARKETPLACE = {
        'farmers_market': {
            'commission_rate': 0.08,  # 8%
            'category': 'local_produce',
            'min_order': 20.00
        },
        'local_restaurants': {
            'commission_rate': 0.12,  # 12%
            'category': 'prepared_meals',
            'min_order': 15.00
        },
        'bulk_buying_groups': {
            'commission_rate': 0.05,  # 5%
            'category': 'community_orders',
            'min_order': 100.00
        }
    }
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.affiliate_table = self.dynamodb.Table('ai-nutritionist-affiliates')
        self.commission_table = self.dynamodb.Table('ai-nutritionist-commissions')
        self.partner_id = "ai_nutritionist_2025"  # Your unique affiliate ID
        
    def generate_affiliate_link(self, partner: str, user_phone: str, 
                              products: List[str] = None, 
                              meal_plan_id: str = None) -> Dict[str, Any]:
        """Generate trackable affiliate link with commission tracking"""
        try:
            if partner not in self.AFFILIATE_PARTNERS:
                return {'error': f'Partner {partner} not found'}
            
            partner_info = self.AFFILIATE_PARTNERS[partner]
            
            # Create unique tracking ID
            tracking_data = f"{user_phone}_{partner}_{meal_plan_id}_{datetime.utcnow().isoformat()}"
            tracking_id = hashlib.md5(tracking_data.encode()).hexdigest()[:12]
            
            # Build affiliate URL
            base_url = partner_info['base_url']
            tracking_param = partner_info['tracking_param']
            
            # Add products if specified
            if products:
                product_params = self._format_products_for_partner(partner, products)
            else:
                product_params = ""
            
            affiliate_url = f"{base_url}?{tracking_param}={self.partner_id}_{tracking_id}{product_params}"
            
            # Store tracking info
            self._store_affiliate_tracking(
                tracking_id, user_phone, partner, products, meal_plan_id
            )
            
            return {
                'success': True,
                'affiliate_url': affiliate_url,
                'tracking_id': tracking_id,
                'partner': partner_info['name'],
                'commission_rate': partner_info['commission_rate'],
                'min_order': partner_info['min_order'],
                'estimated_commission': self._estimate_commission(partner, products)
            }
            
        except Exception as e:
            logger.error(f"Error generating affiliate link: {e}")
            return {'error': str(e)}
    
    def process_affiliate_conversion(self, tracking_id: str, order_value: float, 
                                   order_id: str = None) -> Dict[str, Any]:
        """Process affiliate conversion and calculate commission"""
        try:
            # Get tracking info
            tracking_info = self._get_tracking_info(tracking_id)
            if not tracking_info:
                return {'error': 'Tracking ID not found'}
            
            partner = tracking_info['partner']
            user_phone = tracking_info['user_phone']
            partner_info = self.AFFILIATE_PARTNERS[partner]
            
            # Calculate commission
            commission_rate = partner_info['commission_rate']
            commission_amount = order_value * commission_rate
            
            # Check minimum order requirement
            if order_value < partner_info['min_order']:
                return {
                    'error': f'Order below minimum: ${order_value} < ${partner_info["min_order"]}'
                }
            
            # Record commission
            commission_record = {
                'commission_id': f"{tracking_id}_{order_id or 'unknown'}",
                'tracking_id': tracking_id,
                'user_phone': user_phone,
                'partner': partner,
                'order_value': Decimal(str(order_value)),
                'commission_rate': Decimal(str(commission_rate)),
                'commission_amount': Decimal(str(commission_amount)),
                'order_id': order_id,
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'month': datetime.utcnow().strftime('%Y-%m')
            }
            
            self.commission_table.put_item(Item=commission_record)
            
            logger.info(f"Commission recorded: ${commission_amount} from {partner} order ${order_value}")
            
            return {
                'success': True,
                'commission_amount': commission_amount,
                'order_value': order_value,
                'partner': partner_info['name'],
                'tracking_id': tracking_id
            }
            
        except Exception as e:
            logger.error(f"Error processing affiliate conversion: {e}")
            return {'error': str(e)}
    
    def get_smart_product_recommendations(self, meal_plan: Dict, user_preferences: Dict = None) -> List[Dict]:
        """Generate smart affiliate product recommendations based on meal plan"""
        try:
            recommendations = []
            
            # Extract ingredients from meal plan
            all_ingredients = []
            if 'meals' in meal_plan:
                for meal in meal_plan['meals']:
                    if 'ingredients' in meal:
                        all_ingredients.extend(meal['ingredients'])
            
            # Generate grocery delivery recommendations
            if len(all_ingredients) >= 10:
                grocery_partner = 'instacart'
                if user_preferences and user_preferences.get('prefers_amazon'):
                    grocery_partner = 'amazon_fresh'
                
                grocery_link = self.generate_affiliate_link(
                    grocery_partner, 
                    user_preferences.get('phone', 'unknown'),
                    all_ingredients[:20],  # Top 20 ingredients
                    meal_plan.get('id')
                )
                
                if grocery_link.get('success'):
                    recommendations.append({
                        'type': 'grocery_delivery',
                        'title': f"🛒 Get all ingredients delivered",
                        'description': f"Order from {grocery_link['partner']} and save time!",
                        'url': grocery_link['affiliate_url'],
                        'estimated_savings': f"${grocery_link['estimated_commission']:.2f} towards your next meal plan",
                        'priority': 'high'
                    })
            
            # Meal kit recommendations for busy users
            if user_preferences and user_preferences.get('time_constraint') == 'busy':
                meal_kit_partner = 'hellofresh'  # Higher commission
                meal_kit_link = self.generate_affiliate_link(
                    meal_kit_partner,
                    user_preferences.get('phone', 'unknown'),
                    meal_plan_id=meal_plan.get('id')
                )
                
                if meal_kit_link.get('success'):
                    recommendations.append({
                        'type': 'meal_kit',
                        'title': f"⏰ Save time with meal kits",
                        'description': f"Pre-portioned ingredients delivered to your door",
                        'url': meal_kit_link['affiliate_url'],
                        'estimated_savings': f"${meal_kit_link['estimated_commission']:.2f} commission earned",
                        'priority': 'medium'
                    })
            
            # Supplement recommendations for health goals
            if user_preferences and user_preferences.get('health_goals'):
                supplement_link = self.generate_affiliate_link(
                    'vitamins_com',
                    user_preferences.get('phone', 'unknown'),
                    meal_plan_id=meal_plan.get('id')
                )
                
                if supplement_link.get('success'):
                    recommendations.append({
                        'type': 'supplements',
                        'title': f"💊 Boost your nutrition",
                        'description': f"Supplements to support your health goals",
                        'url': supplement_link['affiliate_url'],
                        'estimated_savings': f"25% commission on all purchases",
                        'priority': 'low'
                    })
            
            # Kitchen appliance recommendations
            cooking_tools = self._extract_cooking_tools_needed(meal_plan)
            if cooking_tools:
                appliance_link = self.generate_affiliate_link(
                    'williams_sonoma',
                    user_preferences.get('phone', 'unknown'),
                    cooking_tools,
                    meal_plan.get('id')
                )
                
                if appliance_link.get('success'):
                    recommendations.append({
                        'type': 'kitchen_appliances',
                        'title': f"🍳 Upgrade your kitchen",
                        'description': f"Tools to make cooking easier: {', '.join(cooking_tools[:3])}",
                        'url': appliance_link['affiliate_url'],
                        'estimated_savings': f"8% commission on all purchases",
                        'priority': 'low'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating product recommendations: {e}")
            return []
    
    def generate_local_marketplace_opportunities(self, user_location: str, 
                                               meal_plan: Dict) -> List[Dict]:
        """Generate local marketplace revenue opportunities"""
        try:
            opportunities = []
            
            # Farmers market opportunities
            seasonal_ingredients = self._get_seasonal_ingredients(meal_plan)
            if seasonal_ingredients:
                opportunities.append({
                    'type': 'farmers_market',
                    'title': f"🥕 Support local farmers",
                    'description': f"Get fresh {', '.join(seasonal_ingredients[:3])} from local farmers",
                    'commission_rate': self.LOCAL_MARKETPLACE['farmers_market']['commission_rate'],
                    'estimated_order': 25.00,
                    'estimated_commission': 25.00 * 0.08,
                    'benefits': ['Fresher produce', 'Support local economy', 'Lower carbon footprint']
                })
            
            # Local restaurant partnerships
            cuisine_type = meal_plan.get('cuisine_preferences', ['american'])[0]
            opportunities.append({
                'type': 'local_restaurants',
                'title': f"🍽️ Order {cuisine_type.title()} food locally",
                'description': f"Support local {cuisine_type} restaurants",
                'commission_rate': self.LOCAL_MARKETPLACE['local_restaurants']['commission_rate'],
                'estimated_order': 35.00,
                'estimated_commission': 35.00 * 0.12,
                'benefits': ['Support local business', 'Skip cooking tonight', 'Discover new flavors']
            })
            
            # Bulk buying groups
            if meal_plan.get('household_size', 1) >= 3:
                opportunities.append({
                    'type': 'bulk_buying',
                    'title': f"🏘️ Join community bulk buying",
                    'description': f"Save money with neighborhood group orders",
                    'commission_rate': self.LOCAL_MARKETPLACE['bulk_buying_groups']['commission_rate'],
                    'estimated_order': 150.00,
                    'estimated_commission': 150.00 * 0.05,
                    'benefits': ['Lower prices', 'Reduce packaging', 'Community connection']
                })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error generating local marketplace opportunities: {e}")
            return []
    
    def get_revenue_analytics(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get affiliate revenue analytics"""
        try:
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
            if not end_date:
                end_date = datetime.utcnow().isoformat()
            
            # This would use proper DynamoDB queries in production
            analytics = {
                'period': f"{start_date} to {end_date}",
                'total_commissions': 0,
                'total_orders_referred': 0,
                'top_partners': [],
                'conversion_rate': 0,
                'partner_breakdown': {}
            }
            
            # Calculate metrics for each partner
            for partner_key, partner_info in self.AFFILIATE_PARTNERS.items():
                analytics['partner_breakdown'][partner_key] = {
                    'name': partner_info['name'],
                    'commission_rate': partner_info['commission_rate'],
                    'total_commissions': 0,  # Would calculate from database
                    'orders_referred': 0,    # Would calculate from database
                    'conversion_rate': 0     # Would calculate from database
                }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return {'error': str(e)}
    
    def _store_affiliate_tracking(self, tracking_id: str, user_phone: str, 
                                partner: str, products: List[str], meal_plan_id: str):
        """Store affiliate tracking information"""
        try:
            tracking_record = {
                'tracking_id': tracking_id,
                'user_phone': user_phone,
                'partner': partner,
                'products': products or [],
                'meal_plan_id': meal_plan_id,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'active',
                'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())  # 30-day expiry
            }
            
            self.affiliate_table.put_item(Item=tracking_record)
            
        except Exception as e:
            logger.error(f"Error storing tracking info: {e}")
    
    def _get_tracking_info(self, tracking_id: str) -> Optional[Dict]:
        """Retrieve affiliate tracking information"""
        try:
            response = self.affiliate_table.get_item(
                Key={'tracking_id': tracking_id}
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting tracking info: {e}")
            return None
    
    def _format_products_for_partner(self, partner: str, products: List[str]) -> str:
        """Format products for specific partner URL structure"""
        if partner == 'instacart':
            # Instacart product search
            product_query = "+".join(products[:5])  # Top 5 products
            return f"&search={urllib.parse.quote(product_query)}"
        elif partner == 'amazon_fresh':
            # Amazon search
            product_query = " ".join(products[:3])
            return f"&field-keywords={urllib.parse.quote(product_query)}"
        else:
            return ""
    
    def _estimate_commission(self, partner: str, products: List[str] = None) -> float:
        """Estimate commission based on partner and products"""
        partner_info = self.AFFILIATE_PARTNERS[partner]
        
        # Average order values by partner
        avg_orders = {
            'instacart': 85.00,
            'amazon_fresh': 65.00,
            'blue_apron': 60.00,
            'hellofresh': 70.00,
            'vitamins_com': 45.00,
            'thrive_market': 80.00,
            'williams_sonoma': 120.00
        }
        
        estimated_order = avg_orders.get(partner, 50.00)
        return estimated_order * partner_info['commission_rate']
    
    def _extract_cooking_tools_needed(self, meal_plan: Dict) -> List[str]:
        """Extract cooking tools/appliances mentioned in meal plan"""
        tools = []
        
        # Look for cooking methods that suggest specific tools
        cooking_methods = []
        if 'meals' in meal_plan:
            for meal in meal_plan['meals']:
                instructions = meal.get('instructions', '').lower()
                if 'air fry' in instructions or 'air fryer' in instructions:
                    tools.append('air fryer')
                if 'blend' in instructions or 'smoothie' in instructions:
                    tools.append('blender')
                if 'pressure cook' in instructions or 'instant pot' in instructions:
                    tools.append('pressure cooker')
                if 'grill' in instructions:
                    tools.append('grill pan')
                if 'food processor' in instructions:
                    tools.append('food processor')
        
        return list(set(tools))  # Remove duplicates
    
    def _get_seasonal_ingredients(self, meal_plan: Dict) -> List[str]:
        """Extract seasonal ingredients that might be available locally"""
        seasonal_now = {
            1: ['cabbage', 'carrots', 'potatoes', 'onions'],      # January
            2: ['cabbage', 'carrots', 'potatoes', 'onions'],      # February  
            3: ['asparagus', 'peas', 'lettuce', 'spinach'],       # March
            4: ['asparagus', 'peas', 'lettuce', 'spinach'],       # April
            5: ['strawberries', 'peas', 'lettuce', 'radishes'],   # May
            6: ['strawberries', 'tomatoes', 'zucchini', 'beans'], # June
            7: ['tomatoes', 'corn', 'zucchini', 'berries'],       # July
            8: ['tomatoes', 'corn', 'zucchini', 'berries'],       # August
            9: ['apples', 'squash', 'pumpkins', 'peppers'],       # September
            10: ['apples', 'squash', 'pumpkins', 'peppers'],      # October
            11: ['cabbage', 'carrots', 'potatoes', 'onions'],     # November
            12: ['cabbage', 'carrots', 'potatoes', 'onions']      # December
        }
        
        current_month = datetime.utcnow().month
        seasonal_ingredients = seasonal_now.get(current_month, [])
        
        # Find overlap with meal plan ingredients
        meal_ingredients = []
        if 'meals' in meal_plan:
            for meal in meal_plan['meals']:
                if 'ingredients' in meal:
                    meal_ingredients.extend([ing.lower() for ing in meal['ingredients']])
        
        # Return seasonal ingredients that are in the meal plan
        return [ing for ing in seasonal_ingredients if any(ing in meal_ing for meal_ing in meal_ingredients)]
