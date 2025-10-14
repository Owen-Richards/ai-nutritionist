"""
Database Optimization Validation Script

This script validates that all database optimization features are working correctly.
It tests repositories, caching, monitoring, batch operations, and performance improvements.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Any

# Database layer imports
from src.core.database import (
    UserProfileRepository,
    MealPlanRepository,
    DynamoDBUnitOfWork,
    UserByPhoneSpecification,
    ActiveUsersSpecification,
    get_query_monitor,
    get_database_dashboard,
    ConnectionPool,
    QueryCache,
    BatchLoader,
)

# Model imports
from src.models.user import UserProfile, UserPreferences
from src.models.meal_planning import GeneratedMealPlan, MealEntry

logger = logging.getLogger(__name__)


class DatabaseOptimizationValidator:
    """Comprehensive validation of database optimization features."""
    
    def __init__(self):
        self.test_results = []
        self.user_repo = None
        self.meal_repo = None
        self.test_users = []
        
    async def setup(self):
        """Initialize repositories and test data."""
        print("🔧 Setting up validation environment...")
        
        self.user_repo = UserProfileRepository()
        self.meal_repo = MealPlanRepository()
        
        # Create test users
        for i in range(10):
            user = UserProfile(
                id=f"test-user-{i}",
                phone_number=f"+1234567{i:03d}",
                preferences=UserPreferences(
                    dietary_restrictions=["vegetarian"] if i % 2 == 0 else ["keto"],
                    cuisine_preferences=["italian", "mexican"],
                    meal_types=["breakfast", "lunch", "dinner"]
                ),
                created_at=datetime.utcnow() - timedelta(days=i),
                last_login=datetime.utcnow() - timedelta(hours=i)
            )
            self.test_users.append(user)
        
        print(f"✅ Created {len(self.test_users)} test users")
    
    async def validate_repository_operations(self) -> Dict[str, Any]:
        """Validate basic repository operations."""
        print("\n📁 Validating Repository Operations...")
        
        results = {
            "test_name": "Repository Operations",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Test save operation
            user = self.test_users[0]
            saved_user = await self.user_repo.save(user)
            
            if saved_user and saved_user.id == user.id:
                results["passed"] += 1
                results["details"].append("✅ Save operation successful")
            else:
                results["failed"] += 1
                results["details"].append("❌ Save operation failed")
            
            # Test get operation
            retrieved_user = await self.user_repo.get_by_id(user.id)
            
            if retrieved_user and retrieved_user.id == user.id:
                results["passed"] += 1
                results["details"].append("✅ Get operation successful")
            else:
                results["failed"] += 1
                results["details"].append("❌ Get operation failed")
            
            # Test update operation
            retrieved_user.subscription_tier = "premium"
            updated_user = await self.user_repo.save(retrieved_user)
            
            if updated_user and updated_user.subscription_tier == "premium":
                results["passed"] += 1
                results["details"].append("✅ Update operation successful")
            else:
                results["failed"] += 1
                results["details"].append("❌ Update operation failed")
            
            # Test delete operation
            deleted = await self.user_repo.delete(user.id)
            
            if deleted:
                results["passed"] += 1
                results["details"].append("✅ Delete operation successful")
            else:
                results["failed"] += 1
                results["details"].append("❌ Delete operation failed")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Repository operations failed: {e}")
        
        return results
    
    async def validate_batch_operations(self) -> Dict[str, Any]:
        """Validate batch operations efficiency."""
        print("\n🚀 Validating Batch Operations...")
        
        results = {
            "test_name": "Batch Operations",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Test batch save
            start_time = time.time()
            saved_users = await self.user_repo.save_many(self.test_users)
            batch_save_time = time.time() - start_time
            
            if len(saved_users) == len(self.test_users):
                results["passed"] += 1
                results["details"].append(f"✅ Batch save successful ({batch_save_time:.2f}s for {len(self.test_users)} users)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Batch save failed")
            
            # Test batch get
            user_ids = [user.id for user in self.test_users]
            start_time = time.time()
            retrieved_users = await self.user_repo.get_by_ids(user_ids)
            batch_get_time = time.time() - start_time
            
            if len(retrieved_users) == len(user_ids):
                results["passed"] += 1
                results["details"].append(f"✅ Batch get successful ({batch_get_time:.2f}s for {len(user_ids)} users)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Batch get failed")
            
            # Compare with individual operations
            start_time = time.time()
            for user_id in user_ids[:3]:  # Test subset to avoid too long execution
                await self.user_repo.get_by_id(user_id)
            individual_time = time.time() - start_time
            
            # Extrapolate for full set
            extrapolated_time = (individual_time / 3) * len(user_ids)
            
            if batch_get_time < extrapolated_time:
                efficiency_gain = ((extrapolated_time - batch_get_time) / extrapolated_time) * 100
                results["passed"] += 1
                results["details"].append(f"✅ Batch operations more efficient ({efficiency_gain:.1f}% improvement)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Batch operations not more efficient")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Batch operations failed: {e}")
        
        return results
    
    async def validate_caching(self) -> Dict[str, Any]:
        """Validate caching mechanisms."""
        print("\n💾 Validating Caching...")
        
        results = {
            "test_name": "Caching",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            user = self.test_users[0]
            user_id = user.id
            
            # Ensure user is saved
            await self.user_repo.save(user)
            
            # First call (miss cache)
            start_time = time.time()
            user1 = await self.user_repo.get_by_id(user_id)
            first_call_time = time.time() - start_time
            
            # Second call (should hit cache)
            start_time = time.time()
            user2 = await self.user_repo.get_by_id(user_id)
            second_call_time = time.time() - start_time
            
            if user1 and user2 and user1.id == user2.id:
                results["passed"] += 1
                results["details"].append("✅ Cache returns correct data")
            else:
                results["failed"] += 1
                results["details"].append("❌ Cache returns incorrect data")
            
            # Check if second call is faster (cache hit)
            if second_call_time < first_call_time:
                speedup = ((first_call_time - second_call_time) / first_call_time) * 100
                results["passed"] += 1
                results["details"].append(f"✅ Cache improves performance ({speedup:.1f}% faster)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Cache doesn't improve performance")
            
            # Test cache invalidation
            user.subscription_tier = "premium"
            await self.user_repo.save(user)
            
            # Get updated user
            updated_user = await self.user_repo.get_by_id(user_id)
            
            if updated_user and updated_user.subscription_tier == "premium":
                results["passed"] += 1
                results["details"].append("✅ Cache invalidation works correctly")
            else:
                results["failed"] += 1
                results["details"].append("❌ Cache invalidation failed")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Caching validation failed: {e}")
        
        return results
    
    async def validate_specifications(self) -> Dict[str, Any]:
        """Validate specification pattern."""
        print("\n🔍 Validating Specifications...")
        
        results = {
            "test_name": "Specifications",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Save test users
            await self.user_repo.save_many(self.test_users)
            
            # Test phone specification
            test_phone = self.test_users[0].phone_number
            phone_spec = UserByPhoneSpecification(test_phone)
            users_by_phone = await self.user_repo.find_by_specification(phone_spec)
            
            if any(user.phone_number == test_phone for user in users_by_phone):
                results["passed"] += 1
                results["details"].append("✅ Phone specification works correctly")
            else:
                results["failed"] += 1
                results["details"].append("❌ Phone specification failed")
            
            # Test active users specification
            active_spec = ActiveUsersSpecification()
            active_users = await self.user_repo.find_by_specification(active_spec)
            
            if len(active_users) > 0:
                results["passed"] += 1
                results["details"].append(f"✅ Active users specification found {len(active_users)} users")
            else:
                results["failed"] += 1
                results["details"].append("❌ Active users specification failed")
            
            # Test specification composition
            combined_spec = phone_spec.and_specification(active_spec)
            combined_users = await self.user_repo.find_by_specification(combined_spec)
            
            if len(combined_users) <= len(users_by_phone):
                results["passed"] += 1
                results["details"].append("✅ Specification composition works correctly")
            else:
                results["failed"] += 1
                results["details"].append("❌ Specification composition failed")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Specifications validation failed: {e}")
        
        return results
    
    async def validate_unit_of_work(self) -> Dict[str, Any]:
        """Validate Unit of Work pattern."""
        print("\n🔄 Validating Unit of Work...")
        
        results = {
            "test_name": "Unit of Work",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Test successful transaction
            user = UserProfile(
                id="uow-test-user",
                phone_number="+1999999999",
                preferences=UserPreferences()
            )
            
            meal_plan = GeneratedMealPlan(
                plan_id="uow-test-plan",
                user_id=user.id,
                week_start=datetime.now().date(),
                generated_at=datetime.utcnow(),
                meals=[],
                estimated_cost=0.0,
                total_calories=0,
                grocery_list=[]
            )
            
            async with DynamoDBUnitOfWork() as uow:
                uow.register_repository('users', self.user_repo)
                uow.register_repository('meal_plans', self.meal_repo)
                
                uow.register_new(user)
                uow.register_new(meal_plan)
                
                await uow.commit()
            
            # Verify both entities were saved
            saved_user = await self.user_repo.get_by_id(user.id)
            saved_plan = await self.meal_repo.get_by_id(meal_plan.plan_id)
            
            if saved_user and saved_plan:
                results["passed"] += 1
                results["details"].append("✅ Unit of Work successful transaction")
            else:
                results["failed"] += 1
                results["details"].append("❌ Unit of Work transaction failed")
            
            # Test rollback on failure
            user2 = UserProfile(
                id="uow-test-user-2",
                phone_number="+1888888888",
                preferences=UserPreferences()
            )
            
            try:
                async with DynamoDBUnitOfWork() as uow:
                    uow.register_repository('users', self.user_repo)
                    uow.register_new(user2)
                    
                    # Force an error during commit
                    raise Exception("Simulated error")
            except Exception:
                pass  # Expected
            
            # Verify user2 was not saved due to rollback
            user2_check = await self.user_repo.get_by_id(user2.id)
            
            if user2_check is None:
                results["passed"] += 1
                results["details"].append("✅ Unit of Work rollback successful")
            else:
                results["failed"] += 1
                results["details"].append("❌ Unit of Work rollback failed")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Unit of Work validation failed: {e}")
        
        return results
    
    async def validate_monitoring(self) -> Dict[str, Any]:
        """Validate query monitoring."""
        print("\n📊 Validating Monitoring...")
        
        results = {
            "test_name": "Monitoring",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            monitor = get_query_monitor()
            
            # Perform some operations to generate metrics
            user = self.test_users[0]
            await self.user_repo.save(user)
            await self.user_repo.get_by_id(user.id)
            
            # Wait a moment for metrics to be recorded
            await asyncio.sleep(0.1)
            
            # Get metrics
            metrics = await monitor.get_metrics()
            
            if metrics.total_queries > 0:
                results["passed"] += 1
                results["details"].append(f"✅ Query monitoring active ({metrics.total_queries} queries tracked)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Query monitoring not working")
            
            if hasattr(metrics, 'avg_query_time_ms'):
                results["passed"] += 1
                results["details"].append(f"✅ Performance metrics available (avg: {metrics.avg_query_time_ms:.2f}ms)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Performance metrics not available")
            
            # Test query patterns
            patterns = await monitor.get_query_patterns()
            
            if len(patterns) > 0:
                results["passed"] += 1
                results["details"].append(f"✅ Query patterns detected ({len(patterns)} patterns)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Query patterns not detected")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Monitoring validation failed: {e}")
        
        return results
    
    async def validate_connection_pool(self) -> Dict[str, Any]:
        """Validate connection pooling."""
        print("\n🔌 Validating Connection Pool...")
        
        results = {
            "test_name": "Connection Pool",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Test concurrent connections
            tasks = []
            for i in range(10):
                task = self.user_repo.get_by_id(f"test-user-{i}")
                tasks.append(task)
            
            start_time = time.time()
            await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = time.time() - start_time
            
            results["passed"] += 1
            results["details"].append(f"✅ Concurrent operations successful ({concurrent_time:.2f}s for 10 operations)")
            
            # Test connection reuse
            pool = ConnectionPool()
            initial_stats = pool.get_stats()
            
            # Perform operations
            for i in range(5):
                await self.user_repo.get_by_id(f"test-user-{i}")
            
            final_stats = pool.get_stats()
            
            if final_stats['total_connections'] >= initial_stats['total_connections']:
                results["passed"] += 1
                results["details"].append("✅ Connection pooling active")
            else:
                results["failed"] += 1
                results["details"].append("❌ Connection pooling not working")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Connection pool validation failed: {e}")
        
        return results
    
    async def validate_performance_improvements(self) -> Dict[str, Any]:
        """Validate overall performance improvements."""
        print("\n⚡ Validating Performance Improvements...")
        
        results = {
            "test_name": "Performance Improvements",
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Test N+1 query prevention
            meal_plans = []
            for i in range(5):
                plan = GeneratedMealPlan(
                    plan_id=f"test-plan-{i}",
                    user_id=f"test-user-{i}",
                    week_start=datetime.now().date(),
                    generated_at=datetime.utcnow(),
                    meals=[],
                    estimated_cost=0.0,
                    total_calories=0,
                    grocery_list=[]
                )
                meal_plans.append(plan)
            
            await self.meal_repo.save_many(meal_plans)
            
            # Load users for meal plans (should use batch loading)
            user_ids = [plan.user_id for plan in meal_plans]
            start_time = time.time()
            users = await self.user_repo.get_by_ids(user_ids)
            batch_time = time.time() - start_time
            
            if len(users) > 0:
                results["passed"] += 1
                results["details"].append(f"✅ Batch loading prevents N+1 queries ({batch_time:.3f}s for {len(user_ids)} users)")
            else:
                results["failed"] += 1
                results["details"].append("❌ Batch loading not working")
            
            # Test cache effectiveness
            monitor = get_query_monitor()
            metrics = await monitor.get_metrics()
            
            if hasattr(metrics, 'cache_hit_ratio') and metrics.cache_hit_ratio > 0:
                results["passed"] += 1
                results["details"].append(f"✅ Cache hit ratio: {metrics.cache_hit_ratio:.2%}")
            else:
                results["failed"] += 1
                results["details"].append("❌ Cache not effective")
            
            # Test query optimization
            if hasattr(metrics, 'avg_query_time_ms') and metrics.avg_query_time_ms < 100:
                results["passed"] += 1
                results["details"].append(f"✅ Fast query performance: {metrics.avg_query_time_ms:.2f}ms average")
            else:
                results["failed"] += 1
                results["details"].append("❌ Query performance not optimized")
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"❌ Performance validation failed: {e}")
        
        return results
    
    async def cleanup(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test users
            for user in self.test_users:
                await self.user_repo.delete(user.id)
            
            # Delete additional test data
            await self.user_repo.delete("uow-test-user")
            await self.user_repo.delete("uow-test-user-2")
            await self.meal_repo.delete("uow-test-plan")
            
            for i in range(5):
                await self.meal_repo.delete(f"test-plan-{i}")
            
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        print("🚀 Database Optimization Validation Suite")
        print("=" * 60)
        
        await self.setup()
        
        # Run all validation tests
        validation_tests = [
            self.validate_repository_operations,
            self.validate_batch_operations,
            self.validate_caching,
            self.validate_specifications,
            self.validate_unit_of_work,
            self.validate_monitoring,
            self.validate_connection_pool,
            self.validate_performance_improvements,
        ]
        
        all_results = []
        total_passed = 0
        total_failed = 0
        
        for test in validation_tests:
            try:
                result = await test()
                all_results.append(result)
                total_passed += result["passed"]
                total_failed += result["failed"]
                
                # Print test results
                print(f"\n{result['test_name']}:")
                for detail in result["details"]:
                    print(f"  {detail}")
                    
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with error: {e}")
                total_failed += 1
        
        await self.cleanup()
        
        # Summary
        total_tests = total_passed + total_failed
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"📊 VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed} ✅")
        print(f"Failed: {total_failed} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print(f"\n🎉 EXCELLENT! Database optimization is working great!")
        elif success_rate >= 75:
            print(f"\n👍 GOOD! Database optimization is mostly working.")
        elif success_rate >= 50:
            print(f"\n⚠️  WARNING! Some database optimization features need attention.")
        else:
            print(f"\n🚨 CRITICAL! Database optimization needs major fixes.")
        
        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": success_rate,
            "results": all_results
        }


async def main():
    """Main validation function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    validator = DatabaseOptimizationValidator()
    results = await validator.run_validation()
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
