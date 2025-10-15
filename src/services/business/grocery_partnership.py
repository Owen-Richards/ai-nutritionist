"""
Grocery Store Partnership Engine - The REAL business model

This is the moat. Affiliate commissions + data insights = sustainable revenue.
Consumer app is just proof of concept for B2B2C distribution.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GroceryPartnershipEngine:
    """
    Build partnerships with grocery stores for:
    1. Affiliate commissions (2-4% of purchase)
    2. Sponsored product placements ($0.10-0.50 per placement)
    3. Anonymized data insights sales ($2/user/month from stores)

    This is where real money comes from - not just subscriptions
    """

    def __init__(self):
        self.partnerships = self._load_partnerships()
        self.commission_rates = {
            "kroger": Decimal("0.035"),  # 3.5% commission
            "walmart": Decimal("0.025"),  # 2.5% commission
            "target": Decimal("0.030"),  # 3.0% commission
            "whole_foods": Decimal("0.040"),  # 4.0% commission
            "aldi": Decimal("0.020"),  # 2.0% commission (but lower prices)
        }

    def _load_partnerships(self) -> Dict:
        """Load active partnership agreements"""
        # In production, this would come from database
        return {
            "kroger": {
                "active": False,  # Target for Month 2
                "commission_rate": 0.035,
                "sponsored_placement_rate": 0.25,
                "data_insights_rate": 2.00,
            },
            "walmart": {
                "active": False,
                "commission_rate": 0.025,
                "sponsored_placement_rate": 0.15,
                "data_insights_rate": 0.00,  # Walmart doesn't pay for data
            },
            "regional_chains": {
                "active": False,
                "commission_rate": 0.040,  # Higher commission for regional
                "sponsored_placement_rate": 0.30,
                "data_insights_rate": 3.00,  # More desperate for data
            },
        }

    def generate_affiliate_shopping_list(
        self, meal_plan: Dict, user_location: str, user_preferences: Optional[Dict] = None
    ) -> Dict:
        """
        Generate shopping list optimized for commission revenue

        Balance user savings with commission potential
        We save users money AND earn commission - win-win
        """
        user_preferences = user_preferences or {}

        # Find available stores in user's area
        available_stores = self._find_stores_in_area(user_location)

        # Select primary store (highest commission + good prices)
        primary_store = self._select_primary_store(available_stores, user_preferences)

        # Build shopping list with affiliate links
        shopping_list = []
        estimated_commission = Decimal("0.00")
        sponsored_items = []

        for item in meal_plan.get("ingredients", []):
            # Find item at primary store with affiliate link
            store_item = self._find_item_at_store(item, primary_store)
            shopping_list.append(store_item)

            # Calculate commission
            item_commission = store_item["price"] * self.commission_rates.get(
                primary_store, Decimal("0.03")
            )
            estimated_commission += item_commission

            # Check for sponsored alternatives
            sponsored = self._get_sponsored_alternative(item, primary_store)
            if sponsored:
                sponsored_items.append(sponsored)

        total_cost = sum(item["price"] for item in shopping_list)

        return {
            "primary_store": primary_store,
            "backup_store": self._select_backup_store(available_stores, primary_store),
            "shopping_list": shopping_list,
            "total_cost": float(total_cost),
            "estimated_commission": float(estimated_commission),
            "sponsored_items": sponsored_items,
            "affiliate_url": self._generate_affiliate_url(primary_store, shopping_list),
            "commission_rate": float(self.commission_rates.get(primary_store, Decimal("0.03"))),
            "user_savings": f"${float(meal_plan.get('savings', 0)):.2f} vs dining out",
            "our_revenue": float(estimated_commission + len(sponsored_items) * Decimal("0.25")),
        }

    def _find_stores_in_area(self, user_location: str) -> List[str]:
        """Find grocery stores in user's area"""
        # In production, use Google Places API or similar
        # For now, return common chains
        return ["kroger", "walmart", "target", "aldi"]

    def _select_primary_store(self, available_stores: List[str], user_preferences: Dict) -> str:
        """
        Select primary store balancing:
        1. User price sensitivity
        2. Commission potential
        3. Product availability
        """
        # If user is price-sensitive, prefer Aldi/Walmart (lower commission but better retention)
        if user_preferences.get("price_priority", "medium") == "high":
            if "aldi" in available_stores:
                return "aldi"
            if "walmart" in available_stores:
                return "walmart"

        # Otherwise, prefer higher commission stores
        if "kroger" in available_stores:
            return "kroger"  # Good balance of commission + prices
        if "target" in available_stores:
            return "target"
        if "walmart" in available_stores:
            return "walmart"

        return available_stores[0] if available_stores else "walmart"

    def _select_backup_store(self, available_stores: List[str], primary: str) -> str:
        """Select backup store if items unavailable at primary"""
        backup_options = [s for s in available_stores if s != primary]
        return backup_options[0] if backup_options else "walmart"

    def _find_item_at_store(self, item: Dict, store: str) -> Dict:
        """Find item at specific store with pricing"""
        # In production, use store APIs or web scraping
        base_price = item.get("price", 5.00)

        # Store-specific pricing adjustments
        price_adjustments = {
            "aldi": 0.80,  # 20% cheaper
            "walmart": 0.90,  # 10% cheaper
            "kroger": 1.00,  # baseline
            "target": 1.05,  # 5% more expensive
            "whole_foods": 1.30,  # 30% more expensive
        }

        adjusted_price = Decimal(str(base_price)) * Decimal(str(price_adjustments.get(store, 1.00)))

        return {
            "name": item.get("name", "Unknown"),
            "quantity": item.get("quantity", "1"),
            "unit": item.get("unit", "each"),
            "price": adjusted_price,
            "store": store,
            "affiliate_link": f"https://{store}.com/aff/nutritionist/{item.get('id', 'item')}",
            "in_stock": True,  # In production, check actual inventory
        }

    def _get_sponsored_alternative(self, item: Dict, store: str) -> Optional[Dict]:
        """
        Get sponsored product alternative (if applicable)

        Example: User needs "pasta" -> suggest Barilla (sponsored) instead of generic
        We earn $0.25 placement fee, user still gets good product
        """
        # In production, this comes from partnership database
        # Only suggest sponsored items if they're comparable quality/price
        sponsored_categories = ["pasta", "cereal", "bread", "yogurt", "snacks"]

        if item.get("category") in sponsored_categories:
            return {
                "original_item": item.get("name"),
                "sponsored_item": f"Premium {item.get('name')}",
                "price_difference": "+$0.50",
                "placement_fee": 0.25,
                "reason": "Higher quality, minimal price difference",
            }

        return None

    def _generate_affiliate_url(self, store: str, shopping_list: List[Dict]) -> str:
        """Generate affiliate tracking URL for store"""
        item_ids = ",".join(
            [item.get("affiliate_link", "").split("/")[-1] for item in shopping_list]
        )
        return f"https://{store}.com/aff/nutritionist/cart?items={item_ids}"

    def calculate_b2b2c_revenue(self, monthly_active_users: int) -> Dict:
        """
        Calculate revenue from B2B2C partnerships

        This is the REAL pitch to investors:
        - Consumer app = proof of concept
        - B2B2C = actual business model
        """
        # Conservative estimates
        avg_grocery_shops_per_user = Decimal("4")  # per month
        avg_basket_size = Decimal("75.00")
        avg_commission_rate = Decimal("0.03")  # 3%
        data_insights_per_user = Decimal("2.00")  # Stores pay for anonymized data

        # Revenue calculations
        monthly_transactions = monthly_active_users * avg_grocery_shops_per_user
        transaction_volume = monthly_transactions * avg_basket_size
        commission_revenue = transaction_volume * avg_commission_rate
        data_insights_revenue = monthly_active_users * data_insights_per_user

        total_b2b2c_revenue = commission_revenue + data_insights_revenue

        return {
            "monthly_active_users": monthly_active_users,
            "monthly_transactions": int(monthly_transactions),
            "transaction_volume": float(transaction_volume),
            "commission_revenue": float(commission_revenue),
            "data_insights_revenue": float(data_insights_revenue),
            "total_b2b2c_revenue": float(total_b2b2c_revenue),
            "revenue_per_user": float(total_b2b2c_revenue / monthly_active_users),
            "comparison": {
                "consumer_subscription_only": f"${monthly_active_users * Decimal('9.99'):.2f}",
                "with_b2b2c": f"${float(total_b2b2c_revenue):.2f}",
                "revenue_multiplier": f"{float(total_b2b2c_revenue / (monthly_active_users * Decimal('9.99'))):.1f}x",
            },
        }

    def get_partnership_pitch(self) -> Dict:
        """
        Generate pitch for grocery store partnerships

        Use this to approach regional chains first (easier to close)
        """
        return {
            "value_props": [
                "Drive customers to your stores with personalized meal plans",
                "Increase basket size by 15-20% with optimized shopping lists",
                "Access anonymized nutrition trend data for category management",
                "Sponsored product placement opportunities",
                "Digital-native customer acquisition (younger demographics)",
            ],
            "pricing_models": [
                {
                    "model": "Commission-only",
                    "rate": "2-4% of purchase",
                    "risk": "Zero upfront cost",
                },
                {
                    "model": "Flat fee + commission",
                    "rate": "$2/user/month + 1% commission",
                    "benefit": "Predictable revenue for us",
                },
                {
                    "model": "Data insights subscription",
                    "rate": "$5,000-15,000/month",
                    "benefit": "Enterprise nutrition trend data",
                },
            ],
            "target_partners": [
                {
                    "tier": "Regional chains",
                    "examples": "Wegmans, Publix, H-E-B",
                    "why": "Easier to close, higher commission rates, hungry for data",
                    "timeline": "Month 2-3",
                },
                {
                    "tier": "National chains",
                    "examples": "Kroger, Target",
                    "why": "Scale, established affiliate programs",
                    "timeline": "Month 6-9",
                },
                {
                    "tier": "Premium",
                    "examples": "Whole Foods, Sprouts",
                    "why": "High basket size, quality-conscious customers",
                    "timeline": "Month 12+",
                },
            ],
        }
