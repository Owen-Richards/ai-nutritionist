"""
Affiliate Revenue Service - Manages affiliate partnerships and commission tracking
"""

import logging
import hashlib
import hmac
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode
import uuid

logger = logging.getLogger(__name__)


class AffiliatePartner:
    """Represents an affiliate partner."""
    
    def __init__(self, name: str, base_url: str, commission_rate: float, tracking_param: str = 'ref'):
        self.name = name
        self.base_url = base_url
        self.commission_rate = commission_rate  # Percentage (e.g., 0.15 for 15%)
        self.tracking_param = tracking_param


class AffiliateRevenueService:
    """Manages affiliate partnerships and commission tracking."""
    
    def __init__(self):
        # Initialize affiliate partners
        self.partners = {
            'amazon_fresh': AffiliatePartner(
                name='Amazon Fresh',
                base_url='https://www.amazon.com/fresh',
                commission_rate=0.15,  # 15% commission
                tracking_param='tag'
            ),
            'instacart': AffiliatePartner(
                name='Instacart',
                base_url='https://www.instacart.com',
                commission_rate=0.20,  # 20% commission
                tracking_param='ref'
            ),
            'hellofresh': AffiliatePartner(
                name='HelloFresh',
                base_url='https://www.hellofresh.com',
                commission_rate=0.25,  # 25% commission
                tracking_param='c'
            ),
            'blueapron': AffiliatePartner(
                name='Blue Apron',
                base_url='https://www.blueapron.com',
                commission_rate=0.22,  # 22% commission
                tracking_param='utm_source'
            ),
            'thrive_market': AffiliatePartner(
                name='Thrive Market',
                base_url='https://thrivemarket.com',
                commission_rate=0.18,  # 18% commission
                tracking_param='referrer'
            )
        }
        
        # Tracking configuration
        self.base_affiliate_id = "ai-nutritionist"
        self.click_tracking = {}
        self.conversion_tracking = {}
    
    def generate_affiliate_link(self, partner_id: str, product_keywords: List[str], 
                              user_id: str, meal_plan_id: str = None) -> Dict[str, Any]:
        """Generate affiliate link with tracking."""
        
        if partner_id not in self.partners:
            logger.error(f"Unknown affiliate partner: {partner_id}")
            return None
        
        partner = self.partners[partner_id]
        
        # Generate unique tracking ID
        tracking_id = self._generate_tracking_id(user_id, partner_id, meal_plan_id)
        
        # Build affiliate URL
        base_params = {
            partner.tracking_param: f"{self.base_affiliate_id}-{tracking_id}",
            'utm_medium': 'whatsapp',
            'utm_campaign': 'meal_planning',
            'utm_content': meal_plan_id or 'general'
        }
        
        # Add product search if applicable
        if product_keywords and partner_id in ['amazon_fresh', 'instacart']:
            base_params['k'] = '+'.join(product_keywords[:3])  # Limit to top 3 keywords
        
        affiliate_url = f"{partner.base_url}?{urlencode(base_params)}"
        
        # Track the link generation
        click_data = {
            'tracking_id': tracking_id,
            'user_id': user_id,
            'partner_id': partner_id,
            'product_keywords': product_keywords,
            'meal_plan_id': meal_plan_id,
            'generated_at': datetime.utcnow().isoformat(),
            'affiliate_url': affiliate_url,
            'commission_rate': partner.commission_rate
        }
        
        self.click_tracking[tracking_id] = click_data
        
        logger.info(f"Generated affiliate link for {partner.name}: {tracking_id}")
        
        return {
            'url': affiliate_url,
            'tracking_id': tracking_id,
            'partner_name': partner.name,
            'commission_rate': partner.commission_rate,
            'click_data': click_data
        }
    
    def _generate_tracking_id(self, user_id: str, partner_id: str, meal_plan_id: str = None) -> str:
        """Generate unique tracking ID for affiliate links."""
        timestamp = str(int(datetime.utcnow().timestamp()))
        unique_string = f"{user_id}:{partner_id}:{meal_plan_id or 'none'}:{timestamp}"
        
        # Create hash for tracking ID
        tracking_hash = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        return f"{partner_id[:3]}{tracking_hash}"
    
    def get_grocery_suggestions(self, meal_plan: Dict[str, Any], user_preferences: Dict = None) -> List[Dict]:
        """Generate grocery affiliate suggestions based on meal plan."""
        
        suggestions = []
        
        # Extract ingredients from meal plan
        ingredients = self._extract_ingredients(meal_plan)
        
        if not ingredients:
            return suggestions
        
        # Generate suggestions for different partners
        for partner_id, partner in self.partners.items():
            if partner_id in ['amazon_fresh', 'instacart', 'thrive_market']:
                
                suggestion = {
                    'partner_name': partner.name,
                    'partner_id': partner_id,
                    'description': self._get_partner_description(partner_id),
                    'estimated_savings': self._calculate_estimated_savings(partner_id, ingredients),
                    'commission_rate': partner.commission_rate,
                    'cta_text': f"Shop on {partner.name}",
                    'ingredients_count': len(ingredients)
                }
                
                suggestions.append(suggestion)
        
        # Sort by estimated savings (highest first)
        suggestions.sort(key=lambda x: x['estimated_savings'], reverse=True)
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def get_meal_kit_suggestions(self, meal_plan: Dict[str, Any]) -> List[Dict]:
        """Generate meal kit affiliate suggestions."""
        
        suggestions = []
        
        meal_kit_partners = ['hellofresh', 'blueapron']
        
        for partner_id in meal_kit_partners:
            partner = self.partners[partner_id]
            
            suggestion = {
                'partner_name': partner.name,
                'partner_id': partner_id,
                'description': self._get_meal_kit_description(partner_id, meal_plan),
                'estimated_value': self._calculate_meal_kit_value(partner_id),
                'commission_rate': partner.commission_rate,
                'cta_text': f"Try {partner.name}",
                'special_offer': self._get_special_offer(partner_id)
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _extract_ingredients(self, meal_plan: Dict[str, Any]) -> List[str]:
        """Extract ingredient keywords from meal plan."""
        ingredients = []
        
        # Extract from different meal plan structures
        if 'meals' in meal_plan:
            for meal in meal_plan['meals']:
                if 'ingredients' in meal:
                    ingredients.extend(meal['ingredients'])
                elif 'description' in meal:
                    # Extract key ingredients from description
                    ingredients.extend(self._parse_ingredients_from_text(meal['description']))
        
        elif 'shopping_list' in meal_plan:
            ingredients.extend(meal_plan['shopping_list'])
        
        # Clean and deduplicate
        cleaned_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, str):
                cleaned = ingredient.strip().lower()
                if len(cleaned) > 2 and cleaned not in cleaned_ingredients:
                    cleaned_ingredients.append(cleaned)
        
        return cleaned_ingredients[:10]  # Limit to top 10 ingredients
    
    def _parse_ingredients_from_text(self, text: str) -> List[str]:
        """Parse ingredient keywords from meal description text."""
        # Simple ingredient extraction - could be enhanced with NLP
        common_ingredients = [
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp',
            'rice', 'pasta', 'bread', 'eggs', 'milk', 'cheese',
            'tomatoes', 'onions', 'garlic', 'carrots', 'spinach',
            'broccoli', 'peppers', 'mushrooms', 'potatoes',
            'olive oil', 'butter', 'salt', 'pepper', 'herbs'
        ]
        
        found_ingredients = []
        text_lower = text.lower()
        
        for ingredient in common_ingredients:
            if ingredient in text_lower:
                found_ingredients.append(ingredient)
        
        return found_ingredients
    
    def _get_partner_description(self, partner_id: str) -> str:
        """Get marketing description for partner."""
        descriptions = {
            'amazon_fresh': "Fresh groceries delivered in as little as 2 hours",
            'instacart': "Same-day delivery from your favorite local stores",
            'thrive_market': "Organic and natural products at wholesale prices"
        }
        return descriptions.get(partner_id, "Premium grocery delivery service")
    
    def _calculate_estimated_savings(self, partner_id: str, ingredients: List[str]) -> float:
        """Calculate estimated savings for grocery orders."""
        # Simplified savings calculation
        base_savings = {
            'amazon_fresh': 12.50,
            'instacart': 8.75,
            'thrive_market': 15.25
        }
        
        base = base_savings.get(partner_id, 10.0)
        ingredient_bonus = len(ingredients) * 0.75  # $0.75 per ingredient
        
        return round(base + ingredient_bonus, 2)
    
    def _get_meal_kit_description(self, partner_id: str, meal_plan: Dict) -> str:
        """Get meal kit description based on meal plan."""
        meal_count = len(meal_plan.get('meals', []))
        
        descriptions = {
            'hellofresh': f"Fresh ingredients and chef-designed recipes for {meal_count} meals",
            'blueapron': f"Farm-fresh ingredients and step-by-step recipes for {meal_count} meals"
        }
        
        return descriptions.get(partner_id, "Premium meal kit delivery")
    
    def _calculate_meal_kit_value(self, partner_id: str) -> float:
        """Calculate estimated value of meal kit offer."""
        values = {
            'hellofresh': 79.99,
            'blueapron': 69.99
        }
        return values.get(partner_id, 74.99)
    
    def _get_special_offer(self, partner_id: str) -> str:
        """Get current special offer for partner."""
        offers = {
            'hellofresh': "Get 16 free meals + free shipping on your first box",
            'blueapron': "Get $60 off your first 3 boxes + free shipping"
        }
        return offers.get(partner_id, "Special offer for new customers")
    
    def track_click(self, tracking_id: str, user_agent: str = None, ip_address: str = None) -> bool:
        """Track affiliate link click."""
        if tracking_id not in self.click_tracking:
            logger.warning(f"Unknown tracking ID: {tracking_id}")
            return False
        
        click_data = self.click_tracking[tracking_id]
        click_data.update({
            'clicked_at': datetime.utcnow().isoformat(),
            'user_agent': user_agent,
            'ip_address': ip_address,
            'status': 'clicked'
        })
        
        logger.info(f"Affiliate click tracked: {tracking_id}")
        return True
    
    def track_conversion(self, tracking_id: str, order_value: float, commission_earned: float) -> bool:
        """Track affiliate conversion and commission."""
        if tracking_id not in self.click_tracking:
            logger.warning(f"Unknown tracking ID for conversion: {tracking_id}")
            return False
        
        conversion_data = {
            'tracking_id': tracking_id,
            'converted_at': datetime.utcnow().isoformat(),
            'order_value': order_value,
            'commission_earned': commission_earned,
            'status': 'converted'
        }
        
        self.conversion_tracking[tracking_id] = conversion_data
        
        # Update click data
        self.click_tracking[tracking_id]['status'] = 'converted'
        self.click_tracking[tracking_id]['order_value'] = order_value
        self.click_tracking[tracking_id]['commission_earned'] = commission_earned
        
        logger.info(f"Affiliate conversion tracked: {tracking_id}, ${commission_earned:.2f} commission")
        return True
    
    def get_revenue_stats(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get affiliate revenue statistics."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        stats = {
            'total_clicks': len(self.click_tracking),
            'total_conversions': len(self.conversion_tracking),
            'total_commission': sum(c.get('commission_earned', 0) for c in self.conversion_tracking.values()),
            'conversion_rate': 0,
            'partner_breakdown': {}
        }
        
        if stats['total_clicks'] > 0:
            stats['conversion_rate'] = (stats['total_conversions'] / stats['total_clicks']) * 100
        
        # Partner breakdown
        for partner_id in self.partners:
            partner_clicks = sum(1 for c in self.click_tracking.values() if c.get('partner_id') == partner_id)
            partner_conversions = sum(1 for c in self.conversion_tracking.values() 
                                    if self.click_tracking.get(c['tracking_id'], {}).get('partner_id') == partner_id)
            partner_commission = sum(c.get('commission_earned', 0) for c in self.conversion_tracking.values() 
                                   if self.click_tracking.get(c['tracking_id'], {}).get('partner_id') == partner_id)
            
            stats['partner_breakdown'][partner_id] = {
                'clicks': partner_clicks,
                'conversions': partner_conversions,
                'commission': partner_commission,
                'conversion_rate': (partner_conversions / partner_clicks * 100) if partner_clicks > 0 else 0
            }
        
        return stats
