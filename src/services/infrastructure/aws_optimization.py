"""
AWS Connection Pool and Caching Service
Optimizes AWS service usage for cost reduction and performance improvement.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from functools import lru_cache
import boto3
from botocore.config import Config
import redis
import asyncio_redis

logger = logging.getLogger(__name__)


class AWSConnectionPool:
    """Manages reusable AWS service connections with optimized configuration."""
    
    def __init__(self):
        self._dynamodb = None
        self._ssm = None
        self._cloudwatch = None
        self._lambda_client = None
        self._s3 = None
        self._bedrock = None
        self._secretsmanager = None
        
        # Optimized boto3 configuration for cost reduction
        self._boto_config = Config(
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=10,  # Limit concurrent connections
            read_timeout=30,
            connect_timeout=10
        )
    
    @property
    def dynamodb(self):
        """Get cached DynamoDB resource."""
        if not self._dynamodb:
            self._dynamodb = boto3.resource('dynamodb', config=self._boto_config)
        return self._dynamodb
    
    @property
    def ssm(self):
        """Get cached SSM client."""
        if not self._ssm:
            self._ssm = boto3.client('ssm', config=self._boto_config)
        return self._ssm
    
    @property
    def cloudwatch(self):
        """Get cached CloudWatch client."""
        if not self._cloudwatch:
            self._cloudwatch = boto3.client('cloudwatch', config=self._boto_config)
        return self._cloudwatch
    
    @property
    def lambda_client(self):
        """Get cached Lambda client."""
        if not self._lambda_client:
            self._lambda_client = boto3.client('lambda', config=self._boto_config)
        return self._lambda_client
    
    @property
    def s3(self):
        """Get cached S3 client."""
        if not self._s3:
            self._s3 = boto3.client('s3', config=self._boto_config)
        return self._s3
    
    @property
    def bedrock(self):
        """Get cached Bedrock client."""
        if not self._bedrock:
            self._bedrock = boto3.client('bedrock-runtime', config=self._boto_config)
        return self._bedrock
    
    @property
    def secretsmanager(self):
        """Get cached Secrets Manager client."""
        if not self._secretsmanager:
            self._secretsmanager = boto3.client('secretsmanager', config=self._boto_config)
        return self._secretsmanager


class CostOptimizedCache:
    """Redis-based caching service for cost optimization."""
    
    def __init__(self):
        self._redis_client = None
        self._memory_cache = {}  # Fallback in-memory cache
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'cost_savings': 0.0
        }
    
    async def get_redis_client(self) -> Optional[asyncio_redis.Connection]:
        """Get Redis client with fallback handling."""
        if self._redis_client:
            return self._redis_client
            
        try:
            redis_host = os.getenv('REDIS_HOST')
            if redis_host:
                self._redis_client = await asyncio_redis.Connection.create(
                    host=redis_host,
                    port=int(os.getenv('REDIS_PORT', '6379')),
                    db=int(os.getenv('REDIS_DB', '0'))
                )
                return self._redis_client
        except Exception as e:
            logger.warning(f"Redis unavailable, using memory cache: {e}")
            
        return None
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get cached value with cost tracking."""
        cache_key = f"ai-nutritionist:{key}"
        
        # Try Redis first
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                value = await redis_client.get(cache_key)
                if value:
                    self._cache_stats['hits'] += 1
                    self._cache_stats['cost_savings'] += 0.02  # Estimated API call cost saved
                    return json.loads(value.decode())
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory cache
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry['expires'] > datetime.utcnow():
                self._cache_stats['hits'] += 1
                return entry['value']
            else:
                del self._memory_cache[key]
        
        self._cache_stats['misses'] += 1
        return default
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set cached value with TTL."""
        cache_key = f"ai-nutritionist:{key}"
        serialized_value = json.dumps(value, default=str)
        
        # Try Redis first
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                await redis_client.setex(cache_key, ttl, serialized_value)
                return
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Fallback to memory cache
        self._memory_cache[key] = {
            'value': value,
            'expires': datetime.utcnow() + timedelta(seconds=ttl)
        }
        
        # Clean up expired entries periodically
        if len(self._memory_cache) > 1000:
            self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry['expires'] <= now
        ]
        for key in expired_keys:
            del self._memory_cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = self._cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'estimated_cost_savings': self._cache_stats['cost_savings']
        }


class RequestThrottler:
    """Throttles API requests to prevent cost overruns."""
    
    def __init__(self):
        self._request_counts = {}
        self._cost_tracking = {
            'bedrock_requests': 0,
            'bedrock_cost': 0.0,
            'dynamodb_reads': 0,
            'dynamodb_writes': 0,
            'dynamodb_cost': 0.0
        }
        
        # Cost limits per hour
        self._hourly_limits = {
            'bedrock_cost': float(os.getenv('BEDROCK_HOURLY_LIMIT', '10.0')),
            'dynamodb_cost': float(os.getenv('DYNAMODB_HOURLY_LIMIT', '5.0')),
            'total_cost': float(os.getenv('TOTAL_HOURLY_LIMIT', '20.0'))
        }
    
    async def check_rate_limit(self, service: str, operation: str = 'default') -> bool:
        """Check if request is within rate limits."""
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        key = f"{service}:{operation}:{current_hour.isoformat()}"
        
        # Get current count
        current_count = self._request_counts.get(key, 0)
        
        # Service-specific limits
        limits = {
            'bedrock': 100,  # requests per hour
            'dynamodb': 1000,  # operations per hour
            'lambda': 500,  # invocations per hour
        }
        
        limit = limits.get(service, 100)
        
        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for {service}:{operation} ({current_count}/{limit})")
            return False
        
        # Increment counter
        self._request_counts[key] = current_count + 1
        return True
    
    def track_cost(self, service: str, operation: str, estimated_cost: float):
        """Track estimated costs for monitoring."""
        self._cost_tracking[f'{service}_cost'] = self._cost_tracking.get(f'{service}_cost', 0) + estimated_cost
        
        # Log if approaching limits
        total_cost = sum(v for k, v in self._cost_tracking.items() if k.endswith('_cost'))
        if total_cost > self._hourly_limits['total_cost'] * 0.8:
            logger.warning(f"Approaching cost limit: ${total_cost:.2f}/{self._hourly_limits['total_cost']}")
    
    def get_cost_stats(self) -> Dict[str, Any]:
        """Get current cost tracking statistics."""
        return dict(self._cost_tracking)


# Global instances for reuse
aws_pool = AWSConnectionPool()
cache_service = CostOptimizedCache()
throttler = RequestThrottler()


def get_aws_service(service_name: str):
    """Get AWS service client/resource from pool."""
    return getattr(aws_pool, service_name)


async def cached_aws_call(
    service: str,
    operation: str,
    cache_key: str,
    cache_ttl: int = 300,
    estimated_cost: float = 0.01,
    **kwargs
) -> Any:
    """Make cached AWS API call with cost optimization."""
    
    # Check cache first
    cached_result = await cache_service.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Check rate limits
    if not await throttler.check_rate_limit(service, operation):
        raise Exception(f"Rate limit exceeded for {service}:{operation}")
    
    # Make the API call
    aws_service = get_aws_service(service)
    method = getattr(aws_service, operation)
    result = method(**kwargs)
    
    # Cache the result
    await cache_service.set(cache_key, result, cache_ttl)
    
    # Track costs
    throttler.track_cost(service, operation, estimated_cost)
    
    return result


# Convenience functions for common patterns
async def get_parameter(parameter_name: str, cache_ttl: int = 3600) -> str:
    """Get SSM parameter with caching."""
    cache_key = f"ssm:parameter:{parameter_name}"
    return await cached_aws_call(
        service='ssm',
        operation='get_parameter',
        cache_key=cache_key,
        cache_ttl=cache_ttl,
        estimated_cost=0.005,
        Name=parameter_name,
        WithDecryption=True
    )


async def get_secret(secret_id: str, cache_ttl: int = 1800) -> str:
    """Get secret with caching."""
    cache_key = f"secrets:secret:{secret_id}"
    return await cached_aws_call(
        service='secretsmanager',
        operation='get_secret_value',
        cache_key=cache_key,
        cache_ttl=cache_ttl,
        estimated_cost=0.05,
        SecretId=secret_id
    )
