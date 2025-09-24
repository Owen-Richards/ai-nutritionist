"""Grocery list generator service for Track D2.

Handles grocery list generation, CSV export, and partner deeplinks
with no hard dependency for GA.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from urllib.parse import urlencode

from ...models.integrations import (
    GroceryItem,
    GroceryList,
    GroceryPartner,
    PartnerDeepLink
)


logger = logging.getLogger(__name__)


class GroceryListGenerator:
    """Generates grocery lists from meal plans."""
    
    def __init__(self):
        # Category mapping for better organization
        self.category_mapping = {
            # Proteins
            "chicken": "meat",
            "beef": "meat", 
            "pork": "meat",
            "fish": "meat",
            "salmon": "meat",
            "tuna": "meat",
            "eggs": "dairy",
            "tofu": "pantry",
            "beans": "pantry",
            "lentils": "pantry",
            
            # Vegetables
            "lettuce": "produce",
            "spinach": "produce", 
            "tomato": "produce",
            "onion": "produce",
            "garlic": "produce",
            "carrot": "produce",
            "broccoli": "produce",
            "bell pepper": "produce",
            "cucumber": "produce",
            "avocado": "produce",
            
            # Fruits
            "apple": "produce",
            "banana": "produce",
            "orange": "produce",
            "berries": "produce",
            "lemon": "produce",
            "lime": "produce",
            
            # Dairy
            "milk": "dairy",
            "cheese": "dairy",
            "yogurt": "dairy",
            "butter": "dairy",
            "cream": "dairy",
            
            # Pantry staples
            "rice": "pantry",
            "pasta": "pantry",
            "bread": "bakery",
            "flour": "pantry",
            "sugar": "pantry",
            "salt": "pantry",
            "pepper": "pantry",
            "oil": "pantry",
            "vinegar": "pantry",
            "spices": "pantry",
            
            # Frozen
            "frozen vegetables": "frozen",
            "frozen fruit": "frozen",
            "ice cream": "frozen"
        }
        
        # Estimated prices for cost calculation (would come from price API in production)
        self.price_estimates = {
            "chicken": Decimal("8.99"),  # per lb
            "beef": Decimal("12.99"),
            "salmon": Decimal("15.99"),
            "eggs": Decimal("3.49"),     # per dozen
            "milk": Decimal("3.99"),     # per gallon
            "bread": Decimal("2.99"),    # per loaf
            "rice": Decimal("2.49"),     # per lb
            "pasta": Decimal("1.99"),    # per box
            "tomato": Decimal("2.99"),   # per lb
            "onion": Decimal("1.49"),    # per lb
            "lettuce": Decimal("1.99"),  # per head
            "cheese": Decimal("4.99"),   # per package
            "apple": Decimal("1.99"),    # per lb
            "banana": Decimal("1.29"),   # per lb
        }
        
        # Common unit conversions
        self.unit_conversions = {
            "cup": {"to_grams": 240, "display": "cup"},
            "tbsp": {"to_grams": 15, "display": "tbsp"},
            "tsp": {"to_grams": 5, "display": "tsp"},
            "oz": {"to_grams": 28, "display": "oz"},
            "lb": {"to_grams": 454, "display": "lb"},
            "kg": {"to_grams": 1000, "display": "kg"},
            "g": {"to_grams": 1, "display": "g"},
            "piece": {"to_grams": 1, "display": "piece"},
            "item": {"to_grams": 1, "display": "item"}
        }
    
    def generate_from_meal_plan(self, user_id: UUID, meal_plan_id: UUID,
                              meals: List[Dict], pantry_items: List[str] = None) -> GroceryList:
        """Generate grocery list from meal plan."""
        pantry_items = pantry_items or []
        grocery_list = GroceryList(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            title=f"Grocery List - Week of {datetime.now().strftime('%B %d, %Y')}"
        )
        
        # Extract ingredients from all meals
        all_ingredients = []
        for meal in meals:
            if "ingredients" in meal:
                for ingredient in meal["ingredients"]:
                    all_ingredients.append({
                        "name": ingredient.get("name", ""),
                        "quantity": Decimal(str(ingredient.get("quantity", 1))),
                        "unit": ingredient.get("unit", "item"),
                        "recipe_id": meal.get("recipe_id"),
                        "meal_name": meal.get("name", "")
                    })
        
        # Group and consolidate ingredients
        consolidated_ingredients = self._consolidate_ingredients(all_ingredients)
        
        # Filter out pantry items
        filtered_ingredients = [
            ing for ing in consolidated_ingredients
            if ing["name"].lower() not in [item.lower() for item in pantry_items]
        ]
        
        # Convert to grocery items
        for ingredient in filtered_ingredients:
            grocery_item = self._create_grocery_item(ingredient, meal_plan_id)
            grocery_list.add_item(grocery_item)
        
        # Calculate total cost
        grocery_list.calculate_total_cost()
        
        return grocery_list
    
    def _consolidate_ingredients(self, ingredients: List[Dict]) -> List[Dict]:
        """Consolidate duplicate ingredients by name and unit."""
        consolidated = {}
        
        for ingredient in ingredients:
            name = ingredient["name"].lower().strip()
            unit = ingredient["unit"].lower()
            key = f"{name}_{unit}"
            
            if key in consolidated:
                # Add quantities
                consolidated[key]["quantity"] += ingredient["quantity"]
                # Keep track of recipes using this ingredient
                if "recipes" not in consolidated[key]:
                    consolidated[key]["recipes"] = []
                if ingredient.get("recipe_id"):
                    consolidated[key]["recipes"].append(ingredient["recipe_id"])
            else:
                consolidated[key] = ingredient.copy()
                consolidated[key]["recipes"] = [ingredient.get("recipe_id")] if ingredient.get("recipe_id") else []
        
        return list(consolidated.values())
    
    def _create_grocery_item(self, ingredient: Dict, meal_plan_id: UUID) -> GroceryItem:
        """Create grocery item from ingredient."""
        name = ingredient["name"].strip()
        quantity = ingredient["quantity"]
        unit = ingredient["unit"]
        
        # Determine category
        category = self._get_ingredient_category(name)
        
        # Estimate price
        estimated_price = self._estimate_price(name, quantity, unit)
        
        # Check if it's a pantry staple
        is_pantry_staple = category == "pantry" or name.lower() in [
            "salt", "pepper", "oil", "flour", "sugar", "spices", "vinegar"
        ]
        
        return GroceryItem(
            name=name,
            quantity=quantity,
            unit=unit,
            category=category,
            estimated_price=estimated_price,
            meal_plan_id=meal_plan_id,
            is_pantry_staple=is_pantry_staple,
            notes=f"For {ingredient.get('meal_name', 'meal')}" if ingredient.get("meal_name") else ""
        )
    
    def _get_ingredient_category(self, name: str) -> str:
        """Determine category for ingredient."""
        name_lower = name.lower()
        
        # Check exact matches first
        if name_lower in self.category_mapping:
            return self.category_mapping[name_lower]
        
        # Check partial matches
        for ingredient, category in self.category_mapping.items():
            if ingredient in name_lower:
                return category
        
        # Default category
        return "misc"
    
    def _estimate_price(self, name: str, quantity: Decimal, unit: str) -> Decimal:
        """Estimate price for ingredient."""
        name_lower = name.lower()
        
        # Find price estimate
        base_price = None
        for item, price in self.price_estimates.items():
            if item in name_lower:
                base_price = price
                break
        
        if not base_price:
            # Default price estimation based on category
            category = self._get_ingredient_category(name)
            base_price = {
                "meat": Decimal("10.99"),
                "produce": Decimal("2.99"),
                "dairy": Decimal("3.99"),
                "pantry": Decimal("2.49"),
                "bakery": Decimal("2.99"),
                "frozen": Decimal("3.99"),
                "misc": Decimal("4.99")
            }.get(category, Decimal("3.99"))
        
        # Adjust for quantity and unit
        if unit in ["item", "piece"]:
            return base_price * quantity
        elif unit in ["lb", "kg"]:
            return base_price * quantity
        else:
            # For cups, tbsp, etc., assume fractional quantities
            return base_price * (quantity / Decimal("4"))  # Approximate conversion


class GroceryExportService:
    """Handles grocery list exports in various formats."""
    
    def export_to_csv(self, grocery_list: GroceryList) -> str:
        """Export grocery list to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Item", "Quantity", "Unit", "Category", 
            "Estimated Price", "Notes"
        ])
        
        # Items organized by category
        items_by_category = grocery_list.get_items_by_category()
        
        for category, items in sorted(items_by_category.items()):
            # Category header
            writer.writerow([f"--- {category.upper()} ---", "", "", "", "", ""])
            
            # Items in category
            for item in sorted(items, key=lambda x: x.name):
                writer.writerow([
                    item.name,
                    str(item.quantity),
                    item.unit,
                    item.category,
                    f"${item.estimated_price:.2f}" if item.estimated_price else "",
                    item.notes
                ])
            
            # Empty row between categories
            writer.writerow(["", "", "", "", "", ""])
        
        # Total
        total_cost = grocery_list.calculate_total_cost()
        writer.writerow(["", "", "", "TOTAL:", f"${total_cost:.2f}", ""])
        
        return output.getvalue()
    
    def export_to_json(self, grocery_list: GroceryList) -> Dict:
        """Export grocery list to JSON format."""
        items_by_category = grocery_list.get_items_by_category()
        
        return {
            "list_id": str(grocery_list.list_id),
            "title": grocery_list.title,
            "created_at": grocery_list.created_at.isoformat(),
            "total_items": len(grocery_list.items),
            "total_estimated_cost": float(grocery_list.calculate_total_cost()),
            "categories": {
                category: [
                    {
                        "name": item.name,
                        "quantity": float(item.quantity),
                        "unit": item.unit,
                        "estimated_price": float(item.estimated_price) if item.estimated_price else None,
                        "notes": item.notes,
                        "is_pantry_staple": item.is_pantry_staple
                    }
                    for item in items
                ]
                for category, items in items_by_category.items()
            }
        }
    
    def export_to_markdown(self, grocery_list: GroceryList) -> str:
        """Export grocery list to Markdown format."""
        lines = [
            f"# {grocery_list.title}",
            f"*Generated on {grocery_list.created_at.strftime('%B %d, %Y at %I:%M %p')}*",
            "",
            f"**Total Items:** {len(grocery_list.items)}",
            f"**Estimated Cost:** ${grocery_list.calculate_total_cost():.2f}",
            ""
        ]
        
        items_by_category = grocery_list.get_items_by_category()
        
        for category, items in sorted(items_by_category.items()):
            lines.append(f"## {category.title()}")
            lines.append("")
            
            for item in sorted(items, key=lambda x: x.name):
                price_text = f" - ${item.estimated_price:.2f}" if item.estimated_price else ""
                notes_text = f" _{item.notes}_" if item.notes else ""
                
                lines.append(f"- [ ] **{item.name}** ({item.quantity} {item.unit}){price_text}{notes_text}")
            
            lines.append("")
        
        return "\n".join(lines)


class PartnerIntegrationService:
    """Handles partner deeplinks for grocery delivery services."""
    
    def __init__(self):
        # Partner configurations (would be loaded from environment/config)
        self.partner_configs = {
            GroceryPartner.INSTACART: {
                "base_url": "https://www.instacart.com/store/add_items",
                "item_param": "items",
                "tracking_param": "utm_source",
                "tracking_value": "ai_nutritionist"
            },
            GroceryPartner.AMAZON_FRESH: {
                "base_url": "https://www.amazon.com/gp/product",
                "search_param": "keywords",
                "tracking_param": "tag",
                "tracking_value": "ainut-20"
            },
            GroceryPartner.WALMART_GROCERY: {
                "base_url": "https://www.walmart.com/grocery/search",
                "search_param": "q",
                "tracking_param": "athcpid",
                "tracking_value": "ainutritionist"
            },
            GroceryPartner.TARGET_SHIPT: {
                "base_url": "https://www.target.com/s",
                "search_param": "searchTerm",
                "tracking_param": "lnk",
                "tracking_value": "ainut"
            }
        }
    
    def generate_partner_deeplinks(self, grocery_list: GroceryList) -> List[PartnerDeepLink]:
        """Generate deeplinks for all supported partners."""
        deeplinks = []
        
        for partner in [GroceryPartner.INSTACART, GroceryPartner.AMAZON_FRESH, 
                       GroceryPartner.WALMART_GROCERY, GroceryPartner.TARGET_SHIPT]:
            try:
                deeplink = self._generate_partner_deeplink(partner, grocery_list)
                deeplinks.append(deeplink)
            except Exception as e:
                logger.warning(f"Failed to generate deeplink for {partner.value}: {e}")
        
        return deeplinks
    
    def _generate_partner_deeplink(self, partner: GroceryPartner, 
                                 grocery_list: GroceryList) -> PartnerDeepLink:
        """Generate deeplink for specific partner."""
        config = self.partner_configs[partner]
        
        # Prepare items for the specific partner format
        if partner == GroceryPartner.INSTACART:
            # Instacart accepts comma-separated item list
            items = [f"{item.name} ({item.quantity} {item.unit})" for item in grocery_list.items[:20]]  # Limit to 20 items
            item_string = ",".join(items)
            
            params = {
                config["item_param"]: item_string,
                config["tracking_param"]: config["tracking_value"]
            }
            
        else:
            # For other partners, create a search query with top items
            top_items = grocery_list.items[:5]  # Use top 5 items for search
            search_query = " ".join([item.name for item in top_items])
            
            params = {
                config["search_param"]: search_query,
                config["tracking_param"]: config["tracking_value"]
            }
        
        deeplink_url = f"{config['base_url']}?{urlencode(params)}"
        
        # Estimate partner-specific data
        availability, delivery_time, min_order, delivery_fee = self._get_partner_estimates(partner)
        
        return PartnerDeepLink(
            partner=partner,
            deeplink_url=deeplink_url,
            tracking_params=params,
            estimated_availability=availability,
            estimated_delivery_time=delivery_time,
            minimum_order=min_order,
            delivery_fee=delivery_fee
        )
    
    def _get_partner_estimates(self, partner: GroceryPartner) -> Tuple[float, Optional[timedelta], Optional[Decimal], Optional[Decimal]]:
        """Get partner-specific estimates."""
        estimates = {
            GroceryPartner.INSTACART: (0.95, timedelta(hours=2), Decimal("35.00"), Decimal("3.99")),
            GroceryPartner.AMAZON_FRESH: (0.90, timedelta(hours=4), Decimal("50.00"), Decimal("9.95")),
            GroceryPartner.WALMART_GROCERY: (0.85, timedelta(hours=3), Decimal("35.00"), Decimal("7.95")),
            GroceryPartner.TARGET_SHIPT: (0.80, timedelta(hours=2), Decimal("35.00"), Decimal("7.99"))
        }
        
        return estimates.get(partner, (0.75, timedelta(hours=4), Decimal("35.00"), Decimal("9.99")))


class GroceryService:
    """Main grocery integration service for Track D2."""
    
    def __init__(self):
        self.generator = GroceryListGenerator()
        self.export_service = GroceryExportService()
        self.partner_service = PartnerIntegrationService()
        
        # In-memory storage for demo (would use database in production)
        self.grocery_lists: Dict[UUID, GroceryList] = {}
    
    def generate_grocery_list(self, user_id: UUID, meal_plan_id: UUID,
                            meals: List[Dict], pantry_items: List[str] = None) -> GroceryList:
        """Generate grocery list from meal plan."""
        grocery_list = self.generator.generate_from_meal_plan(
            user_id, meal_plan_id, meals, pantry_items
        )
        
        # Store the list
        self.grocery_lists[grocery_list.list_id] = grocery_list
        
        return grocery_list
    
    def get_grocery_list(self, list_id: UUID) -> Optional[GroceryList]:
        """Get grocery list by ID."""
        return self.grocery_lists.get(list_id)
    
    def update_grocery_list(self, list_id: UUID, **updates) -> Optional[GroceryList]:
        """Update grocery list."""
        if list_id not in self.grocery_lists:
            return None
        
        grocery_list = self.grocery_lists[list_id]
        
        # Update fields
        if "title" in updates:
            grocery_list.title = updates["title"]
        if "store_preference" in updates:
            grocery_list.store_preference = updates["store_preference"]
        if "dietary_filters" in updates:
            grocery_list.dietary_filters = updates["dietary_filters"]
        
        grocery_list.updated_at = datetime.now()
        
        return grocery_list
    
    def add_item_to_list(self, list_id: UUID, item: GroceryItem) -> bool:
        """Add item to grocery list."""
        if list_id not in self.grocery_lists:
            return False
        
        grocery_list = self.grocery_lists[list_id]
        grocery_list.add_item(item)
        
        return True
    
    def remove_item_from_list(self, list_id: UUID, item_id: str) -> bool:
        """Remove item from grocery list."""
        if list_id not in self.grocery_lists:
            return False
        
        grocery_list = self.grocery_lists[list_id]
        return grocery_list.remove_item(item_id)
    
    def export_grocery_list(self, list_id: UUID, format: str = "csv") -> Optional[str]:
        """Export grocery list in specified format."""
        if list_id not in self.grocery_lists:
            return None
        
        grocery_list = self.grocery_lists[list_id]
        
        if format.lower() == "csv":
            return self.export_service.export_to_csv(grocery_list)
        elif format.lower() == "json":
            return self.export_service.export_to_json(grocery_list)
        elif format.lower() == "markdown":
            return self.export_service.export_to_markdown(grocery_list)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_partner_deeplinks(self, list_id: UUID) -> List[PartnerDeepLink]:
        """Get partner deeplinks for grocery list."""
        if list_id not in self.grocery_lists:
            return []
        
        grocery_list = self.grocery_lists[list_id]
        return self.partner_service.generate_partner_deeplinks(grocery_list)
    
    def get_user_grocery_lists(self, user_id: UUID) -> List[GroceryList]:
        """Get all grocery lists for a user."""
        return [
            grocery_list for grocery_list in self.grocery_lists.values()
            if grocery_list.user_id == user_id
        ]


# Export the main service
__all__ = ["GroceryService", "GroceryListGenerator", "GroceryExportService", "PartnerIntegrationService"]
