"""
Inventory and Grocery Management System
Tracks food inventory, generates grocery lists, manages expiration dates
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json


class FoodCategory(Enum):
    PRODUCE = "produce"
    MEAT_SEAFOOD = "meat_seafood"
    DAIRY = "dairy"
    GRAINS = "grains"
    PANTRY = "pantry"
    FROZEN = "frozen"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    CONDIMENTS = "condiments"
    SPICES = "spices"
    BAKING = "baking"
    SUPPLEMENTS = "supplements"


class StorageLocation(Enum):
    REFRIGERATOR = "refrigerator"
    FREEZER = "freezer"
    PANTRY = "pantry"
    COUNTER = "counter"
    SPICE_RACK = "spice_rack"
    WINE_CELLAR = "wine_cellar"


class ItemStatus(Enum):
    FRESH = "fresh"
    EXPIRING_SOON = "expiring_soon"  # Within 3 days
    EXPIRED = "expired"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


@dataclass
class NutritionInfo:
    calories_per_100g: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    vitamins: Dict[str, float] = None
    minerals: Dict[str, float] = None


@dataclass
class FoodItem:
    name: str
    category: FoodCategory
    quantity: float
    unit: str  # cups, oz, lbs, pieces, etc.
    storage_location: StorageLocation
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None
    cost: Optional[float] = None
    brand: Optional[str] = None
    organic: bool = False
    nutrition_info: Optional[NutritionInfo] = None
    barcode: Optional[str] = None
    notes: Optional[str] = None
    minimum_stock_level: float = 0
    
    def get_status(self) -> ItemStatus:
        """Get current status of the item"""
        if self.quantity <= 0:
            return ItemStatus.OUT_OF_STOCK
        elif self.quantity <= self.minimum_stock_level:
            return ItemStatus.LOW_STOCK
        elif self.expiration_date:
            days_to_expire = (self.expiration_date - date.today()).days
            if days_to_expire < 0:
                return ItemStatus.EXPIRED
            elif days_to_expire <= 3:
                return ItemStatus.EXPIRING_SOON
        return ItemStatus.FRESH
    
    def days_until_expiration(self) -> Optional[int]:
        """Get days until expiration"""
        if self.expiration_date:
            return (self.expiration_date - date.today()).days
        return None
    
    def is_low_stock(self) -> bool:
        """Check if item is low stock"""
        return self.quantity <= self.minimum_stock_level
    
    def consume(self, amount: float) -> bool:
        """Consume some quantity of the item"""
        if amount <= self.quantity:
            self.quantity -= amount
            return True
        return False


@dataclass
class GroceryListItem:
    name: str
    category: FoodCategory
    quantity: float
    unit: str
    priority: str = "medium"  # low, medium, high, urgent
    estimated_cost: Optional[float] = None
    preferred_brand: Optional[str] = None
    organic_preferred: bool = False
    notes: Optional[str] = None
    store_section: Optional[str] = None
    recipe_needed_for: List[str] = None
    purchased: bool = False
    
    def __post_init__(self):
        if self.recipe_needed_for is None:
            self.recipe_needed_for = []


@dataclass
class Store:
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    affiliate_link: Optional[str] = None
    delivery_available: bool = False
    pickup_available: bool = False
    store_sections: Dict[str, List[str]] = None  # section -> categories
    average_prices: Dict[str, float] = None  # item -> average price
    
    def __post_init__(self):
        if self.store_sections is None:
            self.store_sections = {}
        if self.average_prices is None:
            self.average_prices = {}


class InventoryManager:
    """Manages food inventory and grocery lists"""
    
    def __init__(self, user_phone: str):
        self.user_phone = user_phone
        self.inventory: Dict[str, FoodItem] = {}
        self.grocery_list: List[GroceryListItem] = []
        self.preferred_stores: List[Store] = []
        self.shopping_history: List[Dict[str, Any]] = []
        self.last_updated = datetime.utcnow()
    
    def add_item(self, item: FoodItem) -> None:
        """Add item to inventory"""
        item_key = f"{item.name.lower()}_{item.brand or 'generic'}"
        
        if item_key in self.inventory:
            # If item exists, add to quantity
            existing_item = self.inventory[item_key]
            existing_item.quantity += item.quantity
            # Update expiration to earliest date
            if item.expiration_date and existing_item.expiration_date:
                existing_item.expiration_date = min(existing_item.expiration_date, item.expiration_date)
            elif item.expiration_date:
                existing_item.expiration_date = item.expiration_date
        else:
            self.inventory[item_key] = item
        
        self.last_updated = datetime.utcnow()
    
    def remove_item(self, name: str, brand: str = None) -> bool:
        """Remove item from inventory"""
        item_key = f"{name.lower()}_{brand or 'generic'}"
        if item_key in self.inventory:
            del self.inventory[item_key]
            self.last_updated = datetime.utcnow()
            return True
        return False
    
    def update_quantity(self, name: str, new_quantity: float, brand: str = None) -> bool:
        """Update item quantity"""
        item_key = f"{name.lower()}_{brand or 'generic'}"
        if item_key in self.inventory:
            self.inventory[item_key].quantity = new_quantity
            self.last_updated = datetime.utcnow()
            return True
        return False
    
    def consume_item(self, name: str, quantity: float, brand: str = None) -> bool:
        """Consume some quantity of an item"""
        item_key = f"{name.lower()}_{brand or 'generic'}"
        if item_key in self.inventory:
            success = self.inventory[item_key].consume(quantity)
            if success:
                self.last_updated = datetime.utcnow()
            return success
        return False
    
    def get_item(self, name: str, brand: str = None) -> Optional[FoodItem]:
        """Get item from inventory"""
        item_key = f"{name.lower()}_{brand or 'generic'}"
        return self.inventory.get(item_key)
    
    def get_items_by_category(self, category: FoodCategory) -> List[FoodItem]:
        """Get all items in a category"""
        return [item for item in self.inventory.values() if item.category == category]
    
    def get_items_by_location(self, location: StorageLocation) -> List[FoodItem]:
        """Get all items in a storage location"""
        return [item for item in self.inventory.values() if item.storage_location == location]
    
    def get_expiring_items(self, days: int = 3) -> List[FoodItem]:
        """Get items expiring within specified days"""
        expiring = []
        cutoff_date = date.today() + timedelta(days=days)
        
        for item in self.inventory.values():
            if item.expiration_date and item.expiration_date <= cutoff_date:
                expiring.append(item)
        
        return sorted(expiring, key=lambda x: x.expiration_date or date.max)
    
    def get_expired_items(self) -> List[FoodItem]:
        """Get expired items"""
        expired = []
        today = date.today()
        
        for item in self.inventory.values():
            if item.expiration_date and item.expiration_date < today:
                expired.append(item)
        
        return sorted(expired, key=lambda x: x.expiration_date or date.max)
    
    def get_low_stock_items(self) -> List[FoodItem]:
        """Get items that are low in stock"""
        return [item for item in self.inventory.values() if item.is_low_stock()]
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get inventory summary"""
        total_items = len(self.inventory)
        expiring_soon = len(self.get_expiring_items())
        expired = len(self.get_expired_items())
        low_stock = len(self.get_low_stock_items())
        
        categories = {}
        for item in self.inventory.values():
            category = item.category.value
            if category not in categories:
                categories[category] = {"count": 0, "total_value": 0}
            categories[category]["count"] += 1
            if item.cost:
                categories[category]["total_value"] += item.cost
        
        return {
            "total_items": total_items,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "low_stock": low_stock,
            "categories": categories,
            "last_updated": self.last_updated.isoformat()
        }
    
    def add_to_grocery_list(self, item: GroceryListItem) -> None:
        """Add item to grocery list"""
        # Check if item already exists and combine
        for existing_item in self.grocery_list:
            if (existing_item.name.lower() == item.name.lower() and 
                existing_item.unit == item.unit):
                existing_item.quantity += item.quantity
                existing_item.priority = max(existing_item.priority, item.priority, 
                                           key=lambda x: {"low": 1, "medium": 2, "high": 3, "urgent": 4}[x])
                return
        
        self.grocery_list.append(item)
    
    def remove_from_grocery_list(self, name: str) -> bool:
        """Remove item from grocery list"""
        for i, item in enumerate(self.grocery_list):
            if item.name.lower() == name.lower():
                del self.grocery_list[i]
                return True
        return False
    
    def mark_grocery_item_purchased(self, name: str) -> bool:
        """Mark grocery item as purchased"""
        for item in self.grocery_list:
            if item.name.lower() == name.lower():
                item.purchased = True
                return True
        return False
    
    def clear_purchased_items(self) -> List[GroceryListItem]:
        """Remove purchased items from grocery list and return them"""
        purchased_items = [item for item in self.grocery_list if item.purchased]
        self.grocery_list = [item for item in self.grocery_list if not item.purchased]
        return purchased_items
    
    def generate_grocery_list_from_meal_plan(self, meal_plan: List[Dict[str, Any]], 
                                           servings: int = 1) -> List[GroceryListItem]:
        """Generate grocery list from meal plan"""
        needed_items = []
        
        for meal in meal_plan:
            recipe_name = meal.get("name", "Unknown Recipe")
            ingredients = meal.get("ingredients", [])
            
            for ingredient in ingredients:
                # Parse ingredient (this would be more sophisticated in practice)
                if isinstance(ingredient, str):
                    # Simple parsing - would use NLP in production
                    parts = ingredient.split()
                    quantity = 1
                    unit = "item"
                    name = ingredient
                    
                    try:
                        quantity = float(parts[0]) * servings
                        unit = parts[1] if len(parts) > 1 else "item"
                        name = " ".join(parts[2:]) if len(parts) > 2 else ingredient
                    except (ValueError, IndexError):
                        pass
                    
                    # Check if we already have this item
                    existing_item = self.get_item(name)
                    if existing_item and existing_item.quantity >= quantity:
                        continue  # We have enough
                    
                    needed_quantity = quantity
                    if existing_item:
                        needed_quantity = max(0, quantity - existing_item.quantity)
                    
                    if needed_quantity > 0:
                        grocery_item = GroceryListItem(
                            name=name,
                            category=self._guess_category(name),
                            quantity=needed_quantity,
                            unit=unit,
                            recipe_needed_for=[recipe_name]
                        )
                        needed_items.append(grocery_item)
        
        # Add to grocery list
        for item in needed_items:
            self.add_to_grocery_list(item)
        
        return needed_items
    
    def _guess_category(self, item_name: str) -> FoodCategory:
        """Guess category based on item name"""
        item_lower = item_name.lower()
        
        # Simple categorization - would use ML in production
        if any(word in item_lower for word in ["chicken", "beef", "pork", "fish", "salmon", "tuna"]):
            return FoodCategory.MEAT_SEAFOOD
        elif any(word in item_lower for word in ["milk", "cheese", "yogurt", "butter", "cream"]):
            return FoodCategory.DAIRY
        elif any(word in item_lower for word in ["apple", "banana", "carrot", "lettuce", "tomato", "onion"]):
            return FoodCategory.PRODUCE
        elif any(word in item_lower for word in ["rice", "pasta", "bread", "flour", "oats"]):
            return FoodCategory.GRAINS
        elif any(word in item_lower for word in ["salt", "pepper", "oregano", "basil", "cinnamon"]):
            return FoodCategory.SPICES
        else:
            return FoodCategory.PANTRY
    
    def optimize_grocery_list_by_store(self, store: Store) -> Dict[str, List[GroceryListItem]]:
        """Organize grocery list by store sections"""
        organized = {}
        
        for item in self.grocery_list:
            if not item.purchased:
                section = self._get_store_section(item, store)
                if section not in organized:
                    organized[section] = []
                organized[section].append(item)
        
        return organized
    
    def _get_store_section(self, item: GroceryListItem, store: Store) -> str:
        """Get store section for an item"""
        # Check store's section mapping
        for section, categories in store.store_sections.items():
            if item.category.value in categories:
                return section
        
        # Default section mapping
        section_map = {
            FoodCategory.PRODUCE: "Produce",
            FoodCategory.MEAT_SEAFOOD: "Meat & Seafood",
            FoodCategory.DAIRY: "Dairy",
            FoodCategory.FROZEN: "Frozen",
            FoodCategory.GRAINS: "Bakery & Grains",
            FoodCategory.PANTRY: "Pantry",
            FoodCategory.CONDIMENTS: "Condiments",
            FoodCategory.SPICES: "Spices & Seasonings",
            FoodCategory.BEVERAGES: "Beverages",
            FoodCategory.SNACKS: "Snacks"
        }
        
        return section_map.get(item.category, "Other")
    
    def estimate_grocery_cost(self, store: Store = None) -> float:
        """Estimate total cost of grocery list"""
        total_cost = 0
        
        for item in self.grocery_list:
            if not item.purchased:
                if item.estimated_cost:
                    total_cost += item.estimated_cost
                elif store and item.name in store.average_prices:
                    total_cost += store.average_prices[item.name] * item.quantity
                else:
                    # Use default estimates
                    default_prices = {
                        FoodCategory.PRODUCE: 2.0,
                        FoodCategory.MEAT_SEAFOOD: 8.0,
                        FoodCategory.DAIRY: 3.0,
                        FoodCategory.GRAINS: 1.5,
                        FoodCategory.PANTRY: 2.5
                    }
                    price_per_unit = default_prices.get(item.category, 3.0)
                    total_cost += price_per_unit * item.quantity
        
        return round(total_cost, 2)
    
    def get_shopping_recommendations(self) -> Dict[str, Any]:
        """Get shopping recommendations"""
        low_stock = self.get_low_stock_items()
        expiring_soon = self.get_expiring_items()
        
        recommendations = {
            "urgent_items": [],
            "suggested_items": [],
            "money_saving_tips": [],
            "meal_prep_suggestions": []
        }
        
        # Add low stock items as urgent
        for item in low_stock:
            recommendations["urgent_items"].append({
                "name": item.name,
                "reason": "Running low",
                "current_quantity": item.quantity,
                "suggested_quantity": item.minimum_stock_level * 2
            })
        
        # Suggest replacing expiring items
        for item in expiring_soon:
            if item.quantity > 0:
                recommendations["suggested_items"].append({
                    "name": item.name,
                    "reason": f"Expires in {item.days_until_expiration()} days",
                    "suggested_quantity": item.quantity
                })
        
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "user_phone": self.user_phone,
            "inventory": {key: asdict(item) for key, item in self.inventory.items()},
            "grocery_list": [asdict(item) for item in self.grocery_list],
            "preferred_stores": [asdict(store) for store in self.preferred_stores],
            "shopping_history": self.shopping_history,
            "last_updated": self.last_updated.isoformat()
        }
