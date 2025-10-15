#!/usr/bin/env python3
"""
Database Seeding Script

Seeds the database with:
- Sample user profiles and preferences
- Test meal plans and recipes
- Nutrition data
- Sample messages and conversations
- Configuration data
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid
import random


class DatabaseSeeder:
    """Handles database seeding for development and testing"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / "data" / "sample"
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """Ensure sample data directory exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def seed_database(self, environment: str = "development") -> bool:
        """Seed database with sample data"""
        try:
            print(f"🌱 Seeding database for {environment} environment...")
            
            # Initialize database connection
            db_client = await self._get_database_client()
            
            # Create tables if they don't exist
            print("📋 Creating database tables...")
            await self._create_tables(db_client)
            
            # Seed data in order of dependencies
            print("👥 Seeding user data...")
            users = await self._seed_users(db_client)
            
            print("🍽️ Seeding meal plans and recipes...")
            await self._seed_meal_plans(db_client, users)
            
            print("📊 Seeding nutrition data...")
            await self._seed_nutrition_data(db_client)
            
            print("💬 Seeding messages and conversations...")
            await self._seed_messages(db_client, users)
            
            print("⚙️ Seeding configuration data...")
            await self._seed_configuration(db_client)
            
            print("📈 Seeding analytics data...")
            await self._seed_analytics_data(db_client, users)
            
            print("✅ Database seeding completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Database seeding failed: {e}")
            return False
    
    async def _get_database_client(self):
        """Get database client (mock for development)"""
        # In a real implementation, this would return a DynamoDB client
        return MockDatabaseClient()
    
    async def _create_tables(self, db_client):
        """Create database tables"""
        tables = [
            "user_profiles",
            "user_preferences", 
            "meal_plans",
            "recipes",
            "nutrition_data",
            "messages",
            "conversations",
            "analytics",
            "configuration"
        ]
        
        for table in tables:
            await db_client.create_table(table)
            print(f"  ✅ Created table: {table}")
    
    async def _seed_users(self, db_client) -> List[Dict[str, Any]]:
        """Seed user profiles and preferences"""
        users = []
        
        # Sample user profiles
        sample_users = [
            {
                "user_id": str(uuid.uuid4()),
                "phone_number": "+1234567890",
                "name": "Alice Johnson",
                "age": 28,
                "height": 165,
                "weight": 65,
                "activity_level": "moderate",
                "dietary_restrictions": ["vegetarian"],
                "health_goals": ["weight_loss", "muscle_gain"],
                "created_at": datetime.utcnow().isoformat(),
                "last_active": datetime.utcnow().isoformat(),
                "subscription_tier": "premium"
            },
            {
                "user_id": str(uuid.uuid4()),
                "phone_number": "+1234567891",
                "name": "Bob Smith", 
                "age": 35,
                "height": 180,
                "weight": 80,
                "activity_level": "high",
                "dietary_restrictions": ["gluten_free"],
                "health_goals": ["maintain_weight", "improve_performance"],
                "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "last_active": datetime.utcnow().isoformat(),
                "subscription_tier": "basic"
            },
            {
                "user_id": str(uuid.uuid4()),
                "phone_number": "+1234567892",
                "name": "Carol Davis",
                "age": 42,
                "height": 158,
                "weight": 70,
                "activity_level": "low",
                "dietary_restrictions": ["dairy_free", "nut_free"],
                "health_goals": ["weight_loss", "improve_energy"],
                "created_at": (datetime.utcnow() - timedelta(days=60)).isoformat(),
                "last_active": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "subscription_tier": "premium"
            }
        ]
        
        for user_data in sample_users:
            # Create user profile
            await db_client.put_item("user_profiles", user_data)
            
            # Create user preferences
            preferences = {
                "user_id": user_data["user_id"],
                "meal_frequency": random.choice([3, 4, 5, 6]),
                "preferred_cuisines": random.sample(
                    ["italian", "mexican", "asian", "mediterranean", "american", "indian"], 
                    k=random.randint(2, 4)
                ),
                "cooking_skill": random.choice(["beginner", "intermediate", "advanced"]),
                "meal_prep_time": random.choice(["15_min", "30_min", "60_min", "no_limit"]),
                "budget_preference": random.choice(["low", "medium", "high"]),
                "notification_preferences": {
                    "meal_reminders": True,
                    "grocery_reminders": True,
                    "progress_updates": True,
                    "tips_and_advice": True
                },
                "updated_at": datetime.utcnow().isoformat()
            }
            
            await db_client.put_item("user_preferences", preferences)
            users.append(user_data)
        
        return users
    
    async def _seed_meal_plans(self, db_client, users: List[Dict[str, Any]]):
        """Seed meal plans and recipes"""
        
        # Sample recipes
        recipes = [
            {
                "recipe_id": str(uuid.uuid4()),
                "name": "Quinoa Buddha Bowl",
                "description": "Nutritious bowl with quinoa, roasted vegetables, and tahini dressing",
                "cuisine_type": "mediterranean",
                "difficulty": "easy",
                "prep_time": 15,
                "cook_time": 25,
                "servings": 2,
                "ingredients": [
                    {"name": "quinoa", "amount": 1, "unit": "cup"},
                    {"name": "sweet potato", "amount": 1, "unit": "medium"},
                    {"name": "chickpeas", "amount": 1, "unit": "can"},
                    {"name": "spinach", "amount": 2, "unit": "cups"},
                    {"name": "tahini", "amount": 2, "unit": "tbsp"}
                ],
                "instructions": [
                    "Cook quinoa according to package directions",
                    "Roast sweet potato and chickpeas at 400°F for 20 minutes",
                    "Assemble bowl with quinoa, vegetables, and spinach",
                    "Drizzle with tahini dressing"
                ],
                "nutrition": {
                    "calories": 450,
                    "protein": 18,
                    "carbs": 65,
                    "fat": 12,
                    "fiber": 12
                },
                "tags": ["vegetarian", "gluten_free", "high_protein", "high_fiber"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "recipe_id": str(uuid.uuid4()),
                "name": "Grilled Salmon with Asparagus",
                "description": "Fresh salmon with roasted asparagus and lemon",
                "cuisine_type": "american",
                "difficulty": "medium",
                "prep_time": 10,
                "cook_time": 20,
                "servings": 2,
                "ingredients": [
                    {"name": "salmon fillet", "amount": 2, "unit": "pieces"},
                    {"name": "asparagus", "amount": 1, "unit": "bunch"},
                    {"name": "olive oil", "amount": 2, "unit": "tbsp"},
                    {"name": "lemon", "amount": 1, "unit": "whole"},
                    {"name": "garlic", "amount": 2, "unit": "cloves"}
                ],
                "instructions": [
                    "Season salmon with salt, pepper, and lemon",
                    "Heat grill or pan to medium-high heat",
                    "Grill salmon 4-5 minutes per side",
                    "Roast asparagus with olive oil and garlic",
                    "Serve with lemon wedges"
                ],
                "nutrition": {
                    "calories": 380,
                    "protein": 35,
                    "carbs": 8,
                    "fat": 22,
                    "fiber": 4
                },
                "tags": ["high_protein", "low_carb", "omega_3", "gluten_free"],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "recipe_id": str(uuid.uuid4()),
                "name": "Vegetable Stir Fry",
                "description": "Quick and healthy vegetable stir fry with brown rice",
                "cuisine_type": "asian",
                "difficulty": "easy",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 3,
                "ingredients": [
                    {"name": "brown rice", "amount": 1, "unit": "cup"},
                    {"name": "broccoli", "amount": 2, "unit": "cups"},
                    {"name": "bell peppers", "amount": 2, "unit": "whole"},
                    {"name": "carrots", "amount": 2, "unit": "medium"},
                    {"name": "soy sauce", "amount": 3, "unit": "tbsp"},
                    {"name": "sesame oil", "amount": 1, "unit": "tbsp"}
                ],
                "instructions": [
                    "Cook brown rice according to package directions",
                    "Heat sesame oil in large pan",
                    "Add vegetables in order of cooking time",
                    "Stir fry for 5-7 minutes until tender-crisp",
                    "Add soy sauce and serve over rice"
                ],
                "nutrition": {
                    "calories": 320,
                    "protein": 12,
                    "carbs": 58,
                    "fat": 8,
                    "fiber": 8
                },
                "tags": ["vegetarian", "vegan", "high_fiber", "low_fat"],
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
        # Save recipes
        for recipe in recipes:
            await db_client.put_item("recipes", recipe)
        
        # Generate meal plans for each user
        for user in users:
            # Create weekly meal plan
            meal_plan = {
                "plan_id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "plan_type": "weekly",
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "meals": [],
                "grocery_list": [],
                "total_nutrition": {
                    "calories": 0,
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0,
                    "fiber": 0
                },
                "created_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Add meals for 7 days
            for day in range(7):
                day_date = datetime.utcnow() + timedelta(days=day)
                daily_recipes = random.sample(recipes, k=3)  # 3 meals per day
                
                for i, recipe in enumerate(daily_recipes):
                    meal_type = ["breakfast", "lunch", "dinner"][i]
                    meal = {
                        "meal_id": str(uuid.uuid4()),
                        "date": day_date.date().isoformat(),
                        "meal_type": meal_type,
                        "recipe_id": recipe["recipe_id"],
                        "recipe_name": recipe["name"],
                        "servings": 1,
                        "nutrition": recipe["nutrition"],
                        "completed": random.choice([True, False]) if day < 3 else False
                    }
                    meal_plan["meals"].append(meal)
                    
                    # Add to total nutrition
                    for nutrient, amount in recipe["nutrition"].items():
                        meal_plan["total_nutrition"][nutrient] += amount
            
            # Generate grocery list
            grocery_items = set()
            for meal in meal_plan["meals"]:
                recipe = next(r for r in recipes if r["recipe_id"] == meal["recipe_id"])
                for ingredient in recipe["ingredients"]:
                    grocery_items.add(ingredient["name"])
            
            meal_plan["grocery_list"] = [
                {
                    "item_id": str(uuid.uuid4()),
                    "name": item,
                    "category": self._get_ingredient_category(item),
                    "purchased": random.choice([True, False])
                }
                for item in grocery_items
            ]
            
            await db_client.put_item("meal_plans", meal_plan)
    
    def _get_ingredient_category(self, ingredient_name: str) -> str:
        """Get category for grocery ingredient"""
        categories = {
            "produce": ["sweet potato", "spinach", "asparagus", "broccoli", "bell peppers", "carrots", "lemon", "garlic"],
            "proteins": ["salmon fillet", "chickpeas"],
            "grains": ["quinoa", "brown rice"],
            "pantry": ["tahini", "olive oil", "soy sauce", "sesame oil"],
            "other": []
        }
        
        for category, items in categories.items():
            if ingredient_name.lower() in items:
                return category
        return "other"
    
    async def _seed_nutrition_data(self, db_client):
        """Seed nutrition database with food items"""
        nutrition_items = [
            {
                "food_id": str(uuid.uuid4()),
                "name": "quinoa",
                "category": "grains",
                "nutrition_per_100g": {
                    "calories": 368,
                    "protein": 14.1,
                    "carbs": 64.2,
                    "fat": 6.1,
                    "fiber": 7.0,
                    "sugar": 4.9,
                    "sodium": 5
                },
                "vitamins": ["folate", "magnesium", "phosphorus"],
                "allergens": [],
                "verified": True,
                "source": "USDA",
                "last_updated": datetime.utcnow().isoformat()
            },
            {
                "food_id": str(uuid.uuid4()),
                "name": "salmon",
                "category": "proteins",
                "nutrition_per_100g": {
                    "calories": 208,
                    "protein": 25.4,
                    "carbs": 0,
                    "fat": 12.4,
                    "fiber": 0,
                    "sugar": 0,
                    "sodium": 59
                },
                "vitamins": ["omega_3", "vitamin_d", "vitamin_b12"],
                "allergens": ["fish"],
                "verified": True,
                "source": "USDA",
                "last_updated": datetime.utcnow().isoformat()
            },
            {
                "food_id": str(uuid.uuid4()),
                "name": "spinach",
                "category": "vegetables",
                "nutrition_per_100g": {
                    "calories": 23,
                    "protein": 2.9,
                    "carbs": 3.6,
                    "fat": 0.4,
                    "fiber": 2.2,
                    "sugar": 0.4,
                    "sodium": 79
                },
                "vitamins": ["vitamin_k", "vitamin_a", "folate", "iron"],
                "allergens": [],
                "verified": True,
                "source": "USDA",
                "last_updated": datetime.utcnow().isoformat()
            }
        ]
        
        for item in nutrition_items:
            await db_client.put_item("nutrition_data", item)
    
    async def _seed_messages(self, db_client, users: List[Dict[str, Any]]):
        """Seed messages and conversations"""
        
        for user in users:
            # Create conversation history
            conversation = {
                "conversation_id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "platform": "whatsapp",
                "created_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "last_message_at": datetime.utcnow().isoformat(),
                "message_count": 0,
                "status": "active"
            }
            
            # Generate sample messages
            messages = [
                {
                    "message_id": str(uuid.uuid4()),
                    "conversation_id": conversation["conversation_id"],
                    "user_id": user["user_id"],
                    "direction": "inbound",
                    "content": "Hi! I'd like to start tracking my nutrition",
                    "timestamp": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "message_type": "text",
                    "processed": True
                },
                {
                    "message_id": str(uuid.uuid4()),
                    "conversation_id": conversation["conversation_id"],
                    "user_id": user["user_id"],
                    "direction": "outbound",
                    "content": "Welcome! I'm here to help you with personalized nutrition advice. Let's start by learning about your goals and preferences.",
                    "timestamp": (datetime.utcnow() - timedelta(days=7, minutes=2)).isoformat(),
                    "message_type": "text",
                    "processed": True
                },
                {
                    "message_id": str(uuid.uuid4()),
                    "conversation_id": conversation["conversation_id"],
                    "user_id": user["user_id"],
                    "direction": "inbound",
                    "content": "Can you suggest a healthy lunch for today?",
                    "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "message_type": "text",
                    "processed": True
                },
                {
                    "message_id": str(uuid.uuid4()),
                    "conversation_id": conversation["conversation_id"],
                    "user_id": user["user_id"],
                    "direction": "outbound",
                    "content": "Based on your preferences, I recommend the Quinoa Buddha Bowl! It's vegetarian, high in protein, and fits your goals perfectly. Would you like the recipe?",
                    "timestamp": (datetime.utcnow() - timedelta(days=1, minutes=1)).isoformat(),
                    "message_type": "text",
                    "processed": True
                }
            ]
            
            conversation["message_count"] = len(messages)
            await db_client.put_item("conversations", conversation)
            
            for message in messages:
                await db_client.put_item("messages", message)
    
    async def _seed_configuration(self, db_client):
        """Seed system configuration data"""
        config_items = [
            {
                "config_id": "system_settings",
                "type": "system",
                "settings": {
                    "ai_model_version": "claude-3-haiku",
                    "max_daily_messages": 50,
                    "cache_ttl_seconds": 3600,
                    "rate_limit_per_minute": 10,
                    "feature_flags": {
                        "advanced_meal_planning": True,
                        "grocery_integration": True,
                        "nutrition_tracking": True,
                        "social_features": False
                    }
                },
                "last_updated": datetime.utcnow().isoformat()
            },
            {
                "config_id": "notification_templates",
                "type": "templates",
                "templates": {
                    "welcome_message": "Welcome to AI Nutritionist! I'm here to help you achieve your health goals with personalized nutrition advice.",
                    "meal_reminder": "🍽️ Don't forget about your planned {meal_type} today: {recipe_name}",
                    "grocery_reminder": "🛒 Remember to pick up items from your grocery list!",
                    "progress_update": "🎉 Great job staying on track! You've completed {completed_meals} out of {total_meals} planned meals this week."
                },
                "last_updated": datetime.utcnow().isoformat()
            }
        ]
        
        for config in config_items:
            await db_client.put_item("configuration", config)
    
    async def _seed_analytics_data(self, db_client, users: List[Dict[str, Any]]):
        """Seed analytics and usage data"""
        
        for user in users:
            # User analytics
            analytics = {
                "analytics_id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "period": "weekly",
                "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "metrics": {
                    "messages_sent": random.randint(5, 25),
                    "meals_planned": random.randint(10, 21),
                    "meals_completed": random.randint(7, 18),
                    "recipes_saved": random.randint(2, 8),
                    "grocery_items_purchased": random.randint(15, 40),
                    "engagement_score": random.randint(60, 95)
                },
                "nutrition_goals": {
                    "calories_target": random.randint(1800, 2500),
                    "calories_actual": random.randint(1600, 2600),
                    "protein_target": random.randint(80, 150),
                    "protein_actual": random.randint(70, 160),
                    "carbs_target": random.randint(180, 300),
                    "carbs_actual": random.randint(170, 320)
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            await db_client.put_item("analytics", analytics)
    
    def save_sample_data_files(self):
        """Save sample data to JSON files for reference"""
        try:
            print("💾 Saving sample data files...")
            
            # Sample user data file
            sample_users = {
                "users": [
                    {
                        "name": "Alice Johnson",
                        "profile": {
                            "age": 28,
                            "height": 165,
                            "weight": 65,
                            "activity_level": "moderate",
                            "dietary_restrictions": ["vegetarian"],
                            "health_goals": ["weight_loss", "muscle_gain"]
                        }
                    }
                ],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            sample_users_file = self.data_dir / "sample_users.json"
            with open(sample_users_file, 'w') as f:
                json.dump(sample_users, f, indent=2)
            
            # Sample recipes file
            sample_recipes = {
                "recipes": [
                    {
                        "name": "Quinoa Buddha Bowl",
                        "cuisine": "mediterranean",
                        "difficulty": "easy",
                        "nutrition": {
                            "calories": 450,
                            "protein": 18,
                            "carbs": 65,
                            "fat": 12
                        }
                    }
                ],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            sample_recipes_file = self.data_dir / "sample_recipes.json"
            with open(sample_recipes_file, 'w') as f:
                json.dump(sample_recipes, f, indent=2)
            
            print("✅ Sample data files saved")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save sample data files: {e}")


class MockDatabaseClient:
    """Mock database client for development"""
    
    def __init__(self):
        self.data = {}
    
    async def create_table(self, table_name: str):
        """Mock table creation"""
        if table_name not in self.data:
            self.data[table_name] = []
    
    async def put_item(self, table_name: str, item: Dict[str, Any]):
        """Mock item insertion"""
        if table_name not in self.data:
            self.data[table_name] = []
        self.data[table_name].append(item)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed database with sample data")
    parser.add_argument("--environment", default="development", 
                       choices=["development", "testing", "staging"],
                       help="Environment to seed")
    parser.add_argument("--save-files", action="store_true",
                       help="Save sample data to JSON files")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    seeder = DatabaseSeeder(project_root)
    
    if args.save_files:
        seeder.save_sample_data_files()
    
    success = await seeder.seed_database(args.environment)
    
    if success:
        print(f"\n✅ Database seeding completed for {args.environment} environment")
    else:
        print(f"\n❌ Database seeding failed for {args.environment} environment")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
