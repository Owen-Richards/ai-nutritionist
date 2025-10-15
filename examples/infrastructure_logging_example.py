"""
Example implementation of structured logging for infrastructure layer.

Demonstrates:
- Database operation logging
- External API call logging
- Caching operation logging
- Error recovery logging
- Performance monitoring
"""

import time
import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import aiohttp

from packages.shared.monitoring import (
    get_logger, get_tracer, get_business_metrics,
    LogLevel, EventType, performance_monitor
)


class DatabaseRepository:
    """Example database repository with comprehensive logging."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.logger = get_logger()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
    
    @performance_monitor("db_query")
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID with comprehensive logging."""
        operation_start = time.time()
        
        self.logger.info(
            "Starting database query: get_user_by_id",
            extra={
                "user_id": user_id,
                "operation": "select",
                "table": "users"
            }
        )
        
        with self.tracer.trace("db_query_user", tags={"table": "users", "operation": "select"}) as span:
            try:
                span.add_tag("user_id", user_id)
                span.add_log("Executing user lookup query")
                
                # Simulate database connection and query
                await asyncio.sleep(0.02)  # Simulate DB latency
                
                # Mock database result
                user_data = {
                    "id": user_id,
                    "email": "user@example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "preferences": {
                        "dietary_restrictions": ["vegetarian"],
                        "goal_calories": 2000
                    }
                }
                
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.info(
                    "Database query completed successfully",
                    extra={
                        "user_id": user_id,
                        "operation": "select",
                        "table": "users",
                        "duration_ms": duration_ms,
                        "rows_returned": 1
                    }
                )
                
                # Track metrics
                if self.business_metrics:
                    self.business_metrics.track_database_operation(
                        operation="select",
                        table="users",
                        duration_ms=duration_ms,
                        success=True
                    )
                
                span.add_tag("db.rows_returned", "1")
                span.add_tag("db.status", "success")
                
                return user_data
                
            except Exception as e:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "Database query failed",
                    error=e,
                    extra={
                        "user_id": user_id,
                        "operation": "select",
                        "table": "users",
                        "duration_ms": duration_ms
                    }
                )
                
                # Track failure metrics
                if self.business_metrics:
                    self.business_metrics.track_database_operation(
                        operation="select",
                        table="users",
                        duration_ms=duration_ms,
                        success=False
                    )
                
                span.add_tag("db.status", "failed")
                span.add_tag("error.type", type(e).__name__)
                
                # Log business event for database failures
                self.logger.business_event(
                    event_type=EventType.ERROR_EVENT,
                    entity_type="database",
                    action="query_failed",
                    metadata={
                        "table": "users",
                        "operation": "select",
                        "error": str(e),
                        "user_id": user_id
                    },
                    level=LogLevel.ERROR
                )
                
                return None
    
    @performance_monitor("db_insert")
    async def create_nutrition_log(self, user_id: str, log_data: Dict[str, Any]) -> str:
        """Create nutrition log entry."""
        operation_start = time.time()
        log_id = f"log_{int(time.time())}_{user_id}"
        
        self.logger.info(
            "Starting database insert: create_nutrition_log",
            extra={
                "user_id": user_id,
                "log_id": log_id,
                "operation": "insert",
                "table": "nutrition_logs",
                "data_size_bytes": len(json.dumps(log_data))
            }
        )
        
        with self.tracer.trace("db_insert_nutrition_log", tags={"table": "nutrition_logs", "operation": "insert"}) as span:
            try:
                span.add_tag("user_id", user_id)
                span.add_tag("log_id", log_id)
                span.add_log("Executing nutrition log insert")
                
                # Validate data before insert
                await self._validate_nutrition_log_data(log_data, span)
                
                # Simulate database insert
                await asyncio.sleep(0.015)
                
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.info(
                    "Database insert completed successfully",
                    extra={
                        "user_id": user_id,
                        "log_id": log_id,
                        "operation": "insert",
                        "table": "nutrition_logs",
                        "duration_ms": duration_ms
                    }
                )
                
                # Log business event for data creation
                self.logger.business_event(
                    event_type=EventType.BUSINESS_EVENT,
                    entity_type="nutrition_log",
                    entity_id=log_id,
                    action="created",
                    metadata={
                        "user_id": user_id,
                        "total_calories": log_data.get("total_calories"),
                        "meal_type": log_data.get("meal_type")
                    }
                )
                
                # Track metrics
                if self.business_metrics:
                    self.business_metrics.track_database_operation(
                        operation="insert",
                        table="nutrition_logs",
                        duration_ms=duration_ms,
                        success=True
                    )
                
                span.add_tag("db.status", "success")
                span.add_tag("db.rows_affected", "1")
                
                return log_id
                
            except Exception as e:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "Database insert failed",
                    error=e,
                    extra={
                        "user_id": user_id,
                        "log_id": log_id,
                        "operation": "insert",
                        "table": "nutrition_logs",
                        "duration_ms": duration_ms
                    }
                )
                
                # Track failure metrics
                if self.business_metrics:
                    self.business_metrics.track_database_operation(
                        operation="insert",
                        table="nutrition_logs",
                        duration_ms=duration_ms,
                        success=False
                    )
                
                span.add_tag("db.status", "failed")
                
                raise
    
    async def _validate_nutrition_log_data(self, log_data: Dict[str, Any], span) -> None:
        """Validate nutrition log data."""
        span.add_log("Validating nutrition log data")
        
        required_fields = ["total_calories", "meal_type", "timestamp"]
        missing_fields = [field for field in required_fields if field not in log_data]
        
        if missing_fields:
            self.logger.error(
                "Nutrition log data validation failed: missing required fields",
                extra={
                    "missing_fields": missing_fields,
                    "provided_fields": list(log_data.keys())
                }
            )
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        if log_data["total_calories"] < 0:
            self.logger.error(
                "Nutrition log data validation failed: invalid calories",
                extra={"total_calories": log_data["total_calories"]}
            )
            raise ValueError("Calories cannot be negative")
        
        span.add_log("Nutrition log data validation completed")


class ExternalAPIClient:
    """Example external API client with comprehensive logging."""
    
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.logger = get_logger()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
    
    @performance_monitor("external_api_call")
    async def get_food_nutrition_data(self, food_name: str) -> Optional[Dict[str, Any]]:
        """Get nutrition data from external API."""
        operation_start = time.time()
        url = f"{self.api_base_url}/nutrition/{food_name}"
        
        self.logger.info(
            "Starting external API call: get_food_nutrition_data",
            extra={
                "food_name": food_name,
                "url": url,
                "service": "nutrition_api"
            }
        )
        
        with self.tracer.trace("external_api_nutrition", tags={"service": "nutrition_api", "endpoint": "nutrition"}) as span:
            try:
                span.add_tag("food_name", food_name)
                span.add_tag("api.url", url)
                span.add_log("Making HTTP request to nutrition API")
                
                # Make HTTP request with timeout
                timeout = aiohttp.ClientTimeout(total=5.0)
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "AI-Nutritionist/1.0"
                }
                
                # Inject tracing headers
                headers = self.tracer.inject_context(headers)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        response_data = await response.json()
                        
                        duration_ms = (time.time() - operation_start) * 1000
                        
                        if response.status == 200:
                            self.logger.info(
                                "External API call completed successfully",
                                extra={
                                    "food_name": food_name,
                                    "service": "nutrition_api",
                                    "status_code": response.status,
                                    "duration_ms": duration_ms,
                                    "response_size_bytes": len(str(response_data))
                                }
                            )
                            
                            # Track success metrics
                            if self.business_metrics:
                                self.business_metrics.track_external_api_call(
                                    service="nutrition_api",
                                    endpoint="nutrition",
                                    duration_ms=duration_ms,
                                    success=True
                                )
                            
                            span.add_tag("http.status_code", str(response.status))
                            span.add_tag("api.status", "success")
                            
                            return response_data
                        else:
                            self.logger.warn(
                                "External API returned non-200 status",
                                extra={
                                    "food_name": food_name,
                                    "service": "nutrition_api",
                                    "status_code": response.status,
                                    "duration_ms": duration_ms,
                                    "response_body": str(response_data)
                                }
                            )
                            
                            # Track partial failure
                            if self.business_metrics:
                                self.business_metrics.track_external_api_call(
                                    service="nutrition_api",
                                    endpoint="nutrition",
                                    duration_ms=duration_ms,
                                    success=False
                                )
                            
                            span.add_tag("http.status_code", str(response.status))
                            span.add_tag("api.status", "failed")
                            
                            return None
                
            except asyncio.TimeoutError:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "External API call timed out",
                    extra={
                        "food_name": food_name,
                        "service": "nutrition_api",
                        "duration_ms": duration_ms,
                        "timeout_seconds": 5.0
                    }
                )
                
                # Track timeout
                if self.business_metrics:
                    self.business_metrics.track_external_api_call(
                        service="nutrition_api",
                        endpoint="nutrition",
                        duration_ms=duration_ms,
                        success=False
                    )
                
                span.add_tag("api.status", "timeout")
                
                # Log business event for service degradation
                self.logger.business_event(
                    event_type=EventType.SYSTEM_EVENT,
                    entity_type="external_service",
                    action="timeout",
                    metadata={
                        "service": "nutrition_api",
                        "endpoint": "nutrition",
                        "timeout_seconds": 5.0
                    },
                    level=LogLevel.WARN
                )
                
                return None
                
            except Exception as e:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "External API call failed",
                    error=e,
                    extra={
                        "food_name": food_name,
                        "service": "nutrition_api",
                        "duration_ms": duration_ms
                    }
                )
                
                # Track failure
                if self.business_metrics:
                    self.business_metrics.track_external_api_call(
                        service="nutrition_api",
                        endpoint="nutrition",
                        duration_ms=duration_ms,
                        success=False
                    )
                
                span.add_tag("api.status", "error")
                span.add_tag("error.type", type(e).__name__)
                
                return None


class CacheService:
    """Example cache service with logging."""
    
    def __init__(self):
        self.logger = get_logger()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
        self._cache: Dict[str, Any] = {}  # Simple in-memory cache for example
    
    @performance_monitor("cache_operation")
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        operation_start = time.time()
        
        self.logger.debug(
            "Cache get operation started",
            extra={
                "cache_key": key,
                "operation": "get"
            }
        )
        
        with self.tracer.trace("cache_get", tags={"operation": "get"}) as span:
            try:
                span.add_tag("cache.key", key)
                span.add_log("Looking up cache key")
                
                # Simulate cache lookup latency
                await asyncio.sleep(0.001)
                
                value = self._cache.get(key)
                hit = value is not None
                
                duration_ms = (time.time() - operation_start) * 1000
                
                if hit:
                    self.logger.debug(
                        "Cache hit",
                        extra={
                            "cache_key": key,
                            "operation": "get",
                            "duration_ms": duration_ms,
                            "hit": True
                        }
                    )
                    
                    # Track cache hit metrics
                    if self.business_metrics:
                        self.business_metrics.get_registry().counter("cache_hits_total").increment(
                            tags={"operation": "get"}
                        )
                else:
                    self.logger.debug(
                        "Cache miss",
                        extra={
                            "cache_key": key,
                            "operation": "get",
                            "duration_ms": duration_ms,
                            "hit": False
                        }
                    )
                    
                    # Track cache miss metrics
                    if self.business_metrics:
                        self.business_metrics.get_registry().counter("cache_misses_total").increment(
                            tags={"operation": "get"}
                        )
                
                span.add_tag("cache.hit", str(hit))
                span.add_tag("cache.status", "success")
                
                return value
                
            except Exception as e:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "Cache get operation failed",
                    error=e,
                    extra={
                        "cache_key": key,
                        "operation": "get",
                        "duration_ms": duration_ms
                    }
                )
                
                span.add_tag("cache.status", "error")
                
                return None
    
    @performance_monitor("cache_operation")
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache."""
        operation_start = time.time()
        
        self.logger.debug(
            "Cache set operation started",
            extra={
                "cache_key": key,
                "operation": "set",
                "ttl_seconds": ttl_seconds,
                "value_size_bytes": len(str(value))
            }
        )
        
        with self.tracer.trace("cache_set", tags={"operation": "set"}) as span:
            try:
                span.add_tag("cache.key", key)
                span.add_tag("cache.ttl", str(ttl_seconds) if ttl_seconds else "none")
                span.add_log("Setting cache value")
                
                # Simulate cache set latency
                await asyncio.sleep(0.002)
                
                # Store in cache (simplified - no TTL implementation)
                self._cache[key] = value
                
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.debug(
                    "Cache set operation completed",
                    extra={
                        "cache_key": key,
                        "operation": "set",
                        "duration_ms": duration_ms,
                        "success": True
                    }
                )
                
                # Track cache set metrics
                if self.business_metrics:
                    self.business_metrics.get_registry().counter("cache_sets_total").increment(
                        tags={"operation": "set"}
                    )
                
                span.add_tag("cache.status", "success")
                
                return True
                
            except Exception as e:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "Cache set operation failed",
                    error=e,
                    extra={
                        "cache_key": key,
                        "operation": "set",
                        "duration_ms": duration_ms
                    }
                )
                
                span.add_tag("cache.status", "error")
                
                return False


class AWSService:
    """Example AWS service integration with comprehensive logging."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.logger = get_logger()
        self.tracer = get_tracer()
        self.business_metrics = get_business_metrics()
    
    @performance_monitor("aws_s3_operation")
    async def upload_meal_image(self, user_id: str, image_data: bytes, filename: str) -> Optional[str]:
        """Upload meal image to S3."""
        operation_start = time.time()
        bucket_name = "ai-nutritionist-meal-images"
        s3_key = f"users/{user_id}/meals/{filename}"
        
        self.logger.info(
            "Starting S3 upload operation",
            extra={
                "user_id": user_id,
                "filename": filename,
                "bucket": bucket_name,
                "s3_key": s3_key,
                "file_size_bytes": len(image_data),
                "aws_service": "s3"
            }
        )
        
        with self.tracer.trace("aws_s3_upload", tags={"aws.service": "s3", "operation": "upload"}) as span:
            try:
                span.add_tag("aws.s3.bucket", bucket_name)
                span.add_tag("aws.s3.key", s3_key)
                span.add_tag("file.size_bytes", str(len(image_data)))
                span.add_log("Uploading file to S3")
                
                # Simulate S3 upload
                s3_client = boto3.client('s3', region_name=self.region)
                
                # This would be the actual upload in production
                # s3_client.put_object(
                #     Bucket=bucket_name,
                #     Key=s3_key,
                #     Body=image_data,
                #     ContentType='image/jpeg'
                # )
                
                # Simulate upload time
                await asyncio.sleep(0.1)
                
                duration_ms = (time.time() - operation_start) * 1000
                
                # Generate public URL (mock)
                public_url = f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
                
                self.logger.info(
                    "S3 upload completed successfully",
                    extra={
                        "user_id": user_id,
                        "filename": filename,
                        "bucket": bucket_name,
                        "s3_key": s3_key,
                        "public_url": public_url,
                        "duration_ms": duration_ms,
                        "aws_service": "s3"
                    }
                )
                
                # Log business event
                self.logger.business_event(
                    event_type=EventType.BUSINESS_EVENT,
                    entity_type="meal_image",
                    action="uploaded",
                    metadata={
                        "user_id": user_id,
                        "filename": filename,
                        "file_size_bytes": len(image_data),
                        "s3_url": public_url
                    }
                )
                
                # Track AWS operation metrics
                if self.business_metrics:
                    self.business_metrics.get_registry().counter("aws_operations_total").increment(
                        tags={"service": "s3", "operation": "upload", "status": "success"}
                    )
                    
                    self.business_metrics.get_registry().histogram("aws_operation_duration_ms").observe(
                        duration_ms, tags={"service": "s3", "operation": "upload"}
                    )
                
                span.add_tag("aws.status", "success")
                span.add_tag("aws.s3.url", public_url)
                
                return public_url
                
            except NoCredentialsError:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "S3 upload failed: AWS credentials not found",
                    extra={
                        "user_id": user_id,
                        "filename": filename,
                        "duration_ms": duration_ms,
                        "aws_service": "s3"
                    }
                )
                
                # Log security event for credential issues
                self.logger.business_event(
                    event_type=EventType.SECURITY_EVENT,
                    entity_type="aws_credentials",
                    action="missing",
                    metadata={
                        "service": "s3",
                        "operation": "upload"
                    },
                    level=LogLevel.ERROR
                )
                
                span.add_tag("aws.status", "credentials_error")
                
                return None
                
            except ClientError as e:
                duration_ms = (time.time() - operation_start) * 1000
                error_code = e.response['Error']['Code']
                
                self.logger.error(
                    "S3 upload failed: AWS client error",
                    error=e,
                    extra={
                        "user_id": user_id,
                        "filename": filename,
                        "duration_ms": duration_ms,
                        "aws_service": "s3",
                        "error_code": error_code
                    }
                )
                
                # Track AWS operation failure
                if self.business_metrics:
                    self.business_metrics.get_registry().counter("aws_operations_total").increment(
                        tags={"service": "s3", "operation": "upload", "status": "failed"}
                    )
                
                span.add_tag("aws.status", "client_error")
                span.add_tag("aws.error_code", error_code)
                
                return None
                
            except Exception as e:
                duration_ms = (time.time() - operation_start) * 1000
                
                self.logger.error(
                    "S3 upload failed: unexpected error",
                    error=e,
                    extra={
                        "user_id": user_id,
                        "filename": filename,
                        "duration_ms": duration_ms,
                        "aws_service": "s3"
                    }
                )
                
                span.add_tag("aws.status", "error")
                
                return None


# Example infrastructure service that combines multiple components
class NutritionDataService:
    """High-level service that demonstrates infrastructure layer logging."""
    
    def __init__(self):
        self.db_repo = DatabaseRepository("postgresql://localhost:5432/nutrition")
        self.api_client = ExternalAPIClient("https://api.nutrition.com/v1", "api_key_123")
        self.cache = CacheService()
        self.aws_service = AWSService()
        self.logger = get_logger()
        self.tracer = get_tracer()
    
    @performance_monitor("get_enhanced_nutrition_data")
    async def get_enhanced_nutrition_data(self, food_name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get nutrition data with caching and external API fallback."""
        cache_key = f"nutrition:{food_name.lower()}"
        
        self.logger.info(
            "Getting enhanced nutrition data",
            extra={
                "food_name": food_name,
                "user_id": user_id,
                "cache_key": cache_key
            }
        )
        
        with self.tracer.trace("get_enhanced_nutrition_data") as span:
            span.add_tag("food_name", food_name)
            span.add_tag("user_id", user_id)
            
            # Try cache first
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                self.logger.info("Nutrition data found in cache")
                span.add_tag("data_source", "cache")
                return cached_data
            
            # Fallback to external API
            api_data = await self.api_client.get_food_nutrition_data(food_name)
            if api_data:
                # Cache the result
                await self.cache.set(cache_key, api_data, ttl_seconds=3600)
                
                self.logger.info("Nutrition data retrieved from external API and cached")
                span.add_tag("data_source", "external_api")
                
                # Log user search event
                self.logger.business_event(
                    event_type=EventType.USER_ACTION,
                    entity_type="nutrition_search",
                    action="food_lookup",
                    metadata={
                        "food_name": food_name,
                        "user_id": user_id,
                        "data_source": "external_api"
                    }
                )
                
                return api_data
            
            self.logger.warn(
                "Nutrition data not available from any source",
                extra={
                    "food_name": food_name,
                    "user_id": user_id
                }
            )
            
            span.add_tag("data_source", "none")
            return None


# Example usage
async def example_usage():
    """Example of infrastructure layer logging."""
    logger = get_logger()
    
    logger.info("Starting infrastructure layer example")
    
    # Database operations
    db_repo = DatabaseRepository("postgresql://localhost:5432/nutrition")
    user_data = await db_repo.get_user_by_id("user_123")
    
    if user_data:
        log_id = await db_repo.create_nutrition_log("user_123", {
            "total_calories": 500,
            "meal_type": "breakfast",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Created nutrition log: {log_id}")
    
    # External API operations
    api_client = ExternalAPIClient("https://api.nutrition.com/v1", "api_key_123")
    nutrition_data = await api_client.get_food_nutrition_data("banana")
    
    # Cache operations
    cache = CacheService()
    await cache.set("test_key", {"data": "test"})
    cached_value = await cache.get("test_key")
    
    # AWS operations
    aws_service = AWSService()
    # url = await aws_service.upload_meal_image("user_123", b"fake_image_data", "meal.jpg")
    
    # Combined service
    nutrition_service = NutritionDataService()
    enhanced_data = await nutrition_service.get_enhanced_nutrition_data("apple", "user_123")
    
    logger.info("Infrastructure layer example completed")


if __name__ == "__main__":
    # Setup monitoring
    from packages.shared.monitoring.setup import setup_service_monitoring
    monitoring = setup_service_monitoring("infrastructure-service")
    
    # Add health checks for dependencies
    monitoring.add_external_api_health_check(
        "nutrition_api",
        "https://api.nutrition.com/v1/health",
        timeout=5.0
    )
    
    # Run example
    asyncio.run(example_usage())
