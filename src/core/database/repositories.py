"""
Optimized repository implementations for AI Nutritionist entities.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Type
from datetime import datetime, timedelta
from uuid import UUID
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from ..abstractions import Repository, Specification, UnitOfWork, QueryBuilder
from ..connection_pool import get_connection_pool, Connection
from ..monitoring import get_query_monitor
from ..cache import get_query_cache, CacheStrategy
from ..optimizations import BatchLoader, IndexManager

from ...models.user import UserProfile, UserGoal, UserPreferences, NutritionTargets
from ...models.meal_planning import GeneratedMealPlan, PlanFeedback, MealEntry

logger = logging.getLogger(__name__)


class DynamoDBQueryBuilder(QueryBuilder):
    """DynamoDB-specific query builder with optimization."""
    
    def __init__(self, table_name: str, connection: Connection):
        super().__init__(table_name)
        self.connection = connection
        self.table = connection.get_table(table_name)
        self._key_conditions: List[Dict[str, Any]] = []
        self._filter_expressions: List[Any] = []
        self._is_query = False  # vs scan
        
    def where_key(self, key_name: str, value: Any) -> 'DynamoDBQueryBuilder':
        """Add key condition for efficient query."""
        self._key_conditions.append({
            "key": key_name,
            "value": value
        })
        self._is_query = True
        return self
    
    def where_key_between(self, key_name: str, start: Any, end: Any) -> 'DynamoDBQueryBuilder':
        """Add range key condition."""
        self._key_conditions.append({
            "key": key_name,
            "condition": "between",
            "start": start,
            "end": end
        })
        self._is_query = True
        return self
    
    def where(self, field: str, operator: str, value: Any) -> 'DynamoDBQueryBuilder':
        """Add filter condition."""
        if operator == "eq":
            condition = Attr(field).eq(value)
        elif operator == "ne":
            condition = Attr(field).ne(value)
        elif operator == "lt":
            condition = Attr(field).lt(value)
        elif operator == "lte":
            condition = Attr(field).lte(value)
        elif operator == "gt":
            condition = Attr(field).gt(value)
        elif operator == "gte":
            condition = Attr(field).gte(value)
        elif operator == "in":
            condition = Attr(field).is_in(value)
        elif operator == "contains":
            condition = Attr(field).contains(value)
        elif operator == "exists":
            condition = Attr(field).exists()
        elif operator == "not_exists":
            condition = Attr(field).not_exists()
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        self._filter_expressions.append(condition)
        return self
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute the built query."""
        monitor = get_query_monitor()
        
        operation = "query" if self._is_query else "scan"
        async with monitor.monitor_query(operation, self.table_name) as query_id:
            
            if self._is_query:
                # Build key condition expression
                key_condition = None
                for key_cond in self._key_conditions:
                    if key_cond.get("condition") == "between":
                        condition = Key(key_cond["key"]).between(
                            key_cond["start"], key_cond["end"]
                        )
                    else:
                        condition = Key(key_cond["key"]).eq(key_cond["value"])
                    
                    if key_condition is None:
                        key_condition = condition
                    else:
                        key_condition = key_condition & condition
                
                # Execute query
                kwargs = {"KeyConditionExpression": key_condition}
                
                if self._filter_expressions:
                    filter_expr = self._filter_expressions[0]
                    for expr in self._filter_expressions[1:]:
                        filter_expr = filter_expr & expr
                    kwargs["FilterExpression"] = filter_expr
                
                if self._projections:
                    kwargs["ProjectionExpression"] = ",".join(self._projections)
                
                if self._limit:
                    kwargs["Limit"] = self._limit
                
                response = await asyncio.to_thread(self.table.query, **kwargs)
                
            else:
                # Execute scan
                kwargs = {}
                
                if self._filter_expressions:
                    filter_expr = self._filter_expressions[0]
                    for expr in self._filter_expressions[1:]:
                        filter_expr = filter_expr & expr
                    kwargs["FilterExpression"] = filter_expr
                
                if self._projections:
                    kwargs["ProjectionExpression"] = ",".join(self._projections)
                
                if self._limit:
                    kwargs["Limit"] = self._limit
                
                response = await asyncio.to_thread(self.table.scan, **kwargs)
            
            return response.get("Items", [])
    
    async def count(self) -> int:
        """Execute count query."""
        original_projections = self._projections
        self._projections = []  # Don't project for count
        
        if self._is_query:
            kwargs = {"Select": "COUNT"}
            
            # Build key condition
            key_condition = None
            for key_cond in self._key_conditions:
                if key_cond.get("condition") == "between":
                    condition = Key(key_cond["key"]).between(
                        key_cond["start"], key_cond["end"]
                    )
                else:
                    condition = Key(key_cond["key"]).eq(key_cond["value"])
                
                if key_condition is None:
                    key_condition = condition
                else:
                    key_condition = key_condition & condition
            
            kwargs["KeyConditionExpression"] = key_condition
            
            if self._filter_expressions:
                filter_expr = self._filter_expressions[0]
                for expr in self._filter_expressions[1:]:
                    filter_expr = filter_expr & expr
                kwargs["FilterExpression"] = filter_expr
            
            response = await asyncio.to_thread(self.table.query, **kwargs)
        else:
            kwargs = {"Select": "COUNT"}
            
            if self._filter_expressions:
                filter_expr = self._filter_expressions[0]
                for expr in self._filter_expressions[1:]:
                    filter_expr = filter_expr & expr
                kwargs["FilterExpression"] = filter_expr
            
            response = await asyncio.to_thread(self.table.scan, **kwargs)
        
        self._projections = original_projections
        return response.get("Count", 0)
    
    def to_query_string(self) -> str:
        """Convert to query string for logging."""
        parts = [f"Table: {self.table_name}"]
        
        if self._is_query:
            parts.append("Operation: Query")
            for key_cond in self._key_conditions:
                parts.append(f"Key: {key_cond['key']} = {key_cond['value']}")
        else:
            parts.append("Operation: Scan")
        
        if self._filter_expressions:
            parts.append(f"Filters: {len(self._filter_expressions)} conditions")
        
        if self._limit:
            parts.append(f"Limit: {self._limit}")
        
        return "; ".join(parts)


class UserProfileRepository(Repository[UserProfile]):
    """Optimized repository for user profiles with caching and batching."""
    
    def __init__(self, table_name: str = "ai-nutritionist-users"):
        super().__init__(UserProfile)
        self.table_name = table_name
        self.cache = get_query_cache()
        self.monitor = get_query_monitor()
        self.index_manager = IndexManager()
        
        # Batch loader for efficient bulk operations
        self.batch_loader = BatchLoader(
            fetch_fn=self._batch_fetch_users,
            batch_size=25,
            cache_results=True
        )
    
    async def get_by_id(self, user_id: Union[str, int, UUID]) -> Optional[UserProfile]:
        """Get user by ID with caching."""
        user_id_str = str(user_id)
        
        # Check cache first
        cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"user_id": user_id_str})
        cached_result, was_hit = await self.cache.get(cache_key)
        
        if was_hit:
            return cached_result
        
        # Use batch loader for efficiency
        result = self.batch_loader.load(user_id_str)
        
        # Cache result
        if result:
            await self.cache.set(cache_key, result, strategy=CacheStrategy.WRITE_THROUGH)
        
        return result
    
    async def get_by_ids(self, user_ids: List[Union[str, int, UUID]]) -> List[UserProfile]:
        """Batch get users by IDs."""
        user_id_strs = [str(uid) for uid in user_ids]
        
        # Use batch loader
        results_dict = self.batch_loader.load_many(user_id_strs)
        
        # Return as list in original order
        results = []
        for user_id in user_id_strs:
            user = results_dict.get(user_id)
            if user:
                results.append(user)
        
        return results
    
    async def save(self, user: UserProfile) -> UserProfile:
        """Save user with optimized caching."""
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            table = conn.get_table(self.table_name)
            
            # Prepare item for DynamoDB
            item = self._user_to_item(user)
            item["updated_at"] = datetime.utcnow().isoformat()
            
            # Monitor performance
            async with self.monitor.monitor_query("put_item", self.table_name, {"user_id": str(user.id)}) as query_id:
                await asyncio.to_thread(table.put_item, Item=item)
            
            # Update cache
            cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"user_id": str(user.id)})
            await self.cache.set(cache_key, user, strategy=CacheStrategy.WRITE_THROUGH)
            
            # Clear batch loader cache for this user
            if hasattr(self.batch_loader, '_cache') and str(user.id) in self.batch_loader._cache:
                del self.batch_loader._cache[str(user.id)]
        
        return user
    
    async def save_many(self, users: List[UserProfile]) -> List[UserProfile]:
        """Batch save multiple users."""
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            table = conn.get_table(self.table_name)
            
            # Process in batches of 25 (DynamoDB limit)
            batch_size = 25
            for i in range(0, len(users), batch_size):
                batch_users = users[i:i + batch_size]
                
                # Monitor performance
                async with self.monitor.monitor_query("batch_write", self.table_name, {"count": len(batch_users)}) as query_id:
                    with table.batch_writer() as batch:
                        for user in batch_users:
                            item = self._user_to_item(user)
                            item["updated_at"] = datetime.utcnow().isoformat()
                            batch.put_item(Item=item)
                
                # Update cache for all users in batch
                for user in batch_users:
                    cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"user_id": str(user.id)})
                    await self.cache.set(cache_key, user, strategy=CacheStrategy.WRITE_BEHIND)
        
        return users
    
    async def delete(self, user_id: Union[str, int, UUID]) -> bool:
        """Delete user with cache invalidation."""
        user_id_str = str(user_id)
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            table = conn.get_table(self.table_name)
            
            try:
                async with self.monitor.monitor_query("delete_item", self.table_name, {"user_id": user_id_str}) as query_id:
                    await asyncio.to_thread(
                        table.delete_item,
                        Key={"user_id": user_id_str}
                    )
                
                # Invalidate cache
                cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"user_id": user_id_str})
                await self.cache.delete(cache_key)
                
                # Clear from batch loader cache
                if hasattr(self.batch_loader, '_cache') and user_id_str in self.batch_loader._cache:
                    del self.batch_loader._cache[user_id_str]
                
                return True
                
            except ClientError as e:
                logger.error(f"Failed to delete user {user_id_str}: {e}")
                return False
    
    async def delete_many(self, user_ids: List[Union[str, int, UUID]]) -> int:
        """Batch delete multiple users."""
        deleted_count = 0
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            table = conn.get_table(self.table_name)
            
            # Process in batches of 25
            batch_size = 25
            for i in range(0, len(user_ids), batch_size):
                batch_ids = user_ids[i:i + batch_size]
                
                async with self.monitor.monitor_query("batch_delete", self.table_name, {"count": len(batch_ids)}) as query_id:
                    with table.batch_writer() as batch:
                        for user_id in batch_ids:
                            try:
                                batch.delete_item(Key={"user_id": str(user_id)})
                                deleted_count += 1
                                
                                # Invalidate cache
                                cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"user_id": str(user_id)})
                                await self.cache.delete(cache_key)
                                
                            except Exception as e:
                                logger.error(f"Failed to delete user {user_id}: {e}")
        
        return deleted_count
    
    async def find_by_specification(self, spec: Specification) -> List[UserProfile]:
        """Find users matching specification."""
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            builder = DynamoDBQueryBuilder(self.table_name, conn)
            
            # Convert specification to query conditions
            query_filter = spec.to_query_filter()
            
            # Apply filters based on specification
            for field, condition in query_filter.items():
                if isinstance(condition, dict):
                    for op, value in condition.items():
                        builder.where(field, op, value)
                else:
                    builder.where(field, "eq", condition)
            
            # Execute query
            items = await builder.execute()
            
            # Convert to user objects
            users = [self._item_to_user(item) for item in items]
            
            # Cache results
            for user in users:
                cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"user_id": str(user.id)})
                await self.cache.set(cache_key, user, strategy=CacheStrategy.WRITE_BEHIND)
            
            return users
    
    async def count_by_specification(self, spec: Specification) -> int:
        """Count users matching specification."""
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            builder = DynamoDBQueryBuilder(self.table_name, conn)
            
            # Convert specification to query conditions
            query_filter = spec.to_query_filter()
            
            for field, condition in query_filter.items():
                if isinstance(condition, dict):
                    for op, value in condition.items():
                        builder.where(field, op, value)
                else:
                    builder.where(field, "eq", condition)
            
            return await builder.count()
    
    async def exists(self, user_id: Union[str, int, UUID]) -> bool:
        """Check if user exists."""
        user = await self.get_by_id(user_id)
        return user is not None
    
    def _batch_fetch_users(self, user_ids: List[str]) -> Dict[str, UserProfile]:
        """Batch fetch function for batch loader."""
        # This would be called synchronously by the batch loader
        # For async, we need to use asyncio.to_thread or similar
        
        # Simplified implementation - in practice you'd use batch_get_item
        results = {}
        
        # Use DynamoDB batch_get_item for efficiency
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(self.table_name)
        
        # Process in chunks of 100 (DynamoDB limit)
        for i in range(0, len(user_ids), 100):
            chunk = user_ids[i:i + 100]
            
            request_items = {
                self.table_name: {
                    'Keys': [{'user_id': user_id} for user_id in chunk]
                }
            }
            
            try:
                response = dynamodb.batch_get_item(RequestItems=request_items)
                
                for item in response.get('Responses', {}).get(self.table_name, []):
                    user = self._item_to_user(item)
                    results[str(user.id)] = user
                    
            except Exception as e:
                logger.error(f"Batch fetch failed for chunk: {e}")
        
        return results
    
    def _user_to_item(self, user: UserProfile) -> Dict[str, Any]:
        """Convert user profile to DynamoDB item."""
        return {
            "user_id": str(user.id),
            "phone_number": user.phone_number,
            "preferences": user.preferences.to_dict() if user.preferences else {},
            "goals": [goal.to_dict() for goal in user.goals],
            "nutrition_targets": user.nutrition_targets.to_dict() if user.nutrition_targets else {},
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "is_active": user.is_active,
            "subscription_tier": user.subscription_tier,
            "metadata": user.metadata
        }
    
    def _item_to_user(self, item: Dict[str, Any]) -> UserProfile:
        """Convert DynamoDB item to user profile."""
        # Reconstruct preferences
        preferences = None
        if item.get("preferences"):
            preferences = UserPreferences.from_dict(item["preferences"])
        
        # Reconstruct goals
        goals = []
        for goal_data in item.get("goals", []):
            goals.append(UserGoal.from_dict(goal_data))
        
        # Reconstruct nutrition targets
        nutrition_targets = None
        if item.get("nutrition_targets"):
            nutrition_targets = NutritionTargets.from_dict(item["nutrition_targets"])
        
        return UserProfile(
            id=item["user_id"],
            phone_number=item["phone_number"],
            preferences=preferences,
            goals=goals,
            nutrition_targets=nutrition_targets,
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            is_active=item.get("is_active", True),
            subscription_tier=item.get("subscription_tier", "free"),
            metadata=item.get("metadata", {})
        )


class MealPlanRepository(Repository[GeneratedMealPlan]):
    """Optimized repository for meal plans with time-based indexing."""
    
    def __init__(self, table_name: str = "ai-nutritionist-meal-plans"):
        super().__init__(GeneratedMealPlan)
        self.table_name = table_name
        self.cache = get_query_cache()
        self.monitor = get_query_monitor()
    
    async def get_by_id(self, plan_id: Union[str, int, UUID]) -> Optional[GeneratedMealPlan]:
        """Get meal plan by ID."""
        plan_id_str = str(plan_id)
        
        # Check cache first
        cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"plan_id": plan_id_str})
        cached_result, was_hit = await self.cache.get(cache_key)
        
        if was_hit:
            return cached_result
        
        pool = await get_connection_pool()
        async with pool.get_connection() as conn:
            table = conn.get_table(self.table_name)
            
            async with self.monitor.monitor_query("get_item", self.table_name, {"plan_id": plan_id_str}) as query_id:
                response = await asyncio.to_thread(
                    table.get_item,
                    Key={"plan_id": plan_id_str}
                )
            
            if "Item" in response:
                plan = self._item_to_plan(response["Item"])
                
                # Cache result
                await self.cache.set(cache_key, plan, strategy=CacheStrategy.WRITE_THROUGH)
                
                return plan
        
        return None
    
    async def get_by_ids(self, plan_ids: List[Union[str, int, UUID]]) -> List[GeneratedMealPlan]:
        """Batch get meal plans by IDs."""
        plan_id_strs = [str(pid) for pid in plan_ids]
        results = []
        
        pool = await get_connection_pool()
        async with pool.get_connection() as conn:
            # Use batch_get_item for efficiency
            dynamodb = conn.dynamodb
            
            # Process in chunks of 100
            for i in range(0, len(plan_id_strs), 100):
                chunk = plan_id_strs[i:i + 100]
                
                request_items = {
                    self.table_name: {
                        'Keys': [{'plan_id': plan_id} for plan_id in chunk]
                    }
                }
                
                async with self.monitor.monitor_query("batch_get", self.table_name, {"count": len(chunk)}) as query_id:
                    response = await asyncio.to_thread(
                        dynamodb.batch_get_item,
                        RequestItems=request_items
                    )
                
                for item in response.get('Responses', {}).get(self.table_name, []):
                    plan = self._item_to_plan(item)
                    results.append(plan)
                    
                    # Cache result
                    cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"plan_id": str(plan.plan_id)})
                    await self.cache.set(cache_key, plan, strategy=CacheStrategy.WRITE_BEHIND)
        
        return results
    
    async def get_plans_for_user(self, user_id: str, limit: int = 10) -> List[GeneratedMealPlan]:
        """Get recent meal plans for a user using GSI."""
        pool = await get_connection_pool()
        
        async with pool.get_connection() as conn:
            builder = DynamoDBQueryBuilder(self.table_name, conn)
            
            # Use GSI for user_id queries
            builder.where_key("user_id", user_id)
            builder.order_by("generated_at", "desc")
            builder.limit(limit)
            
            items = await builder.execute()
            plans = [self._item_to_plan(item) for item in items]
            
            # Cache results
            for plan in plans:
                cache_key = self.cache.create_cache_key("get_by_id", self.table_name, {"plan_id": str(plan.plan_id)})
                await self.cache.set(cache_key, plan, strategy=CacheStrategy.WRITE_BEHIND)
            
            return plans
    
    def _item_to_plan(self, item: Dict[str, Any]) -> GeneratedMealPlan:
        """Convert DynamoDB item to meal plan."""
        meals = []
        for meal_data in item.get("meals", []):
            meals.append(MealEntry(**meal_data))
        
        return GeneratedMealPlan(
            plan_id=item["plan_id"],
            user_id=item["user_id"],
            week_start=datetime.fromisoformat(item["week_start"]).date(),
            generated_at=datetime.fromisoformat(item["generated_at"]),
            meals=meals,
            estimated_cost=item["estimated_cost"],
            total_calories=item["total_calories"],
            grocery_list=item.get("grocery_list", []),
            metadata=item.get("metadata", {})
        )
    
    # ... implement other required methods following similar patterns


# Specifications for common queries
class UserByPhoneSpecification(Specification):
    """Specification for finding user by phone number."""
    
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
    
    def is_satisfied_by(self, entity: Any) -> bool:
        return hasattr(entity, 'phone_number') and entity.phone_number == self.phone_number
    
    def to_query_filter(self) -> Dict[str, Any]:
        return {"phone_number": {"eq": self.phone_number}}


class ActiveUsersSpecification(Specification):
    """Specification for finding active users."""
    
    def is_satisfied_by(self, entity: Any) -> bool:
        return hasattr(entity, 'is_active') and entity.is_active
    
    def to_query_filter(self) -> Dict[str, Any]:
        return {"is_active": {"eq": True}}


class RecentMealPlansSpecification(Specification):
    """Specification for finding recent meal plans."""
    
    def __init__(self, user_id: str, days_back: int = 30):
        self.user_id = user_id
        self.days_back = days_back
    
    def is_satisfied_by(self, entity: Any) -> bool:
        if not hasattr(entity, 'user_id') or entity.user_id != self.user_id:
            return False
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.days_back)
        return hasattr(entity, 'generated_at') and entity.generated_at >= cutoff_date
    
    def to_query_filter(self) -> Dict[str, Any]:
        cutoff_date = datetime.utcnow() - timedelta(days=self.days_back)
        return {
            "user_id": {"eq": self.user_id},
            "generated_at": {"gte": cutoff_date.isoformat()}
        }
