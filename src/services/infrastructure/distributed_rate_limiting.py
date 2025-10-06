"""
Distributed Rate Limiting Service
Implements rate limiting using Redis/DynamoDB for multi-instance compatibility.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import hashlib
import boto3
from botocore.exceptions import ClientError

# Optional Redis import
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

# Simplified config access functions
def get_table_name(base_name: str) -> str:
    """Get environment-specific table name."""
    env = os.getenv('ENVIRONMENT', 'dev')
    return f"ai-nutritionist-{base_name}-{env}"

def get_parameter(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get parameter from environment or AWS Parameter Store."""
    return os.getenv(name.upper(), default)

def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get secret from environment or AWS Secrets Manager."""
    return os.getenv(name.upper(), default)

class SimpleConfig:
    """Simplified config class."""
    aws_region = os.getenv('AWS_REGION', 'us-east-1')

config = SimpleConfig()

logger = logging.getLogger(__name__)


class DistributedRateLimiter:
    """Distributed rate limiter using Redis or DynamoDB as backend."""
    
    def __init__(self):
        self._redis_client = None
        self._dynamodb_table = None
        self._use_redis = False
        self._fallback_memory = {}  # Emergency fallback
        
        # Rate limiting configuration
        self.default_limits = {
            'api_requests': {'limit': 100, 'window': 3600},  # 100/hour
            'sms_messages': {'limit': 10, 'window': 3600},   # 10/hour
            'meal_plans': {'limit': 5, 'window': 86400},     # 5/day
            'ai_requests': {'limit': 50, 'window': 3600},    # 50/hour
            'login_attempts': {'limit': 5, 'window': 900},   # 5/15min
        }
        
        # Cost tracking limits
        self.cost_limits = {
            'bedrock_hourly': float(get_parameter('bedrock_hourly_limit', '10.0')),
            'dynamodb_hourly': float(get_parameter('dynamodb_hourly_limit', '5.0')),
            'total_hourly': float(get_parameter('total_hourly_limit', '20.0'))
        }
    
    async def initialize(self):
        """Initialize the distributed backend."""
        try:
            # Try Redis first (only if available)
            if REDIS_AVAILABLE:
                redis_host = get_parameter('redis_host', None)
                if redis_host:
                    redis_password = get_secret('redis_password', None)
                    redis_port = int(get_parameter('redis_port', '6379'))
                    
                    self._redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        decode_responses=True,
                        socket_timeout=5,
                        socket_connect_timeout=5
                    )
                    
                    # Test Redis connection
                    await self._redis_client.ping()
                    self._use_redis = True
                    logger.info("Initialized Redis-based rate limiting")
                    return
            else:
                logger.info("Redis not available, skipping Redis initialization")
                
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
        
        # Fallback to DynamoDB
        try:
            dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)
            self._dynamodb_table = dynamodb.Table(get_table_name('rate-limits'))
            
            # Test DynamoDB connection
            self._dynamodb_table.describe_table()
            logger.info("Initialized DynamoDB-based rate limiting")
            
        except Exception as e:
            logger.warning(f"DynamoDB initialization failed: {e}")
            logger.warning("Using in-memory fallback (not suitable for production)")
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        action: str = 'api_requests',
        custom_limit: Optional[int] = None,
        custom_window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if action is within rate limits.
        
        Returns:
            (allowed: bool, info: dict with remaining, reset_time, etc.)
        """
        
        # Get rate limit configuration
        limit_config = self.default_limits.get(action, self.default_limits['api_requests'])
        limit = custom_limit or limit_config['limit']
        window = custom_window or limit_config['window']
        
        # Create rate limit key
        current_window = int(time.time() // window)
        rate_key = f"rate_limit:{action}:{identifier}:{current_window}"
        
        try:
            if self._use_redis and self._redis_client:
                return await self._check_redis_rate_limit(rate_key, limit, window)
            elif self._dynamodb_table:
                return await self._check_dynamodb_rate_limit(rate_key, limit, window, identifier, action)
            else:
                return await self._check_memory_rate_limit(rate_key, limit, window)
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request on error but log the issue
            return True, {
                'remaining': limit - 1,
                'reset_time': int(time.time() + window),
                'error': str(e)
            }
    
    async def _check_redis_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, Dict]:
        """Check rate limit using Redis."""
        
        pipe = self._redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        
        current_count = results[0]
        allowed = current_count <= limit
        
        info = {
            'remaining': max(0, limit - current_count),
            'reset_time': int(time.time() + window),
            'current_count': current_count,
            'limit': limit
        }
        
        return allowed, info
    
    async def _check_dynamodb_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window: int, 
        identifier: str, 
        action: str
    ) -> Tuple[bool, Dict]:
        """Check rate limit using DynamoDB."""
        
        try:
            # Use atomic counter update
            response = self._dynamodb_table.update_item(
                Key={'rate_key': key},
                UpdateExpression='ADD request_count :inc SET expires_at = :expires, identifier = :id, action_type = :action',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':expires': int(time.time() + window),
                    ':id': identifier,
                    ':action': action
                },
                ReturnValues='ALL_NEW'
            )
            
            current_count = response['Attributes']['request_count']
            allowed = current_count <= limit
            
            info = {
                'remaining': max(0, limit - current_count),
                'reset_time': response['Attributes']['expires_at'],
                'current_count': current_count,
                'limit': limit
            }
            
            return allowed, info
            
        except ClientError as e:
            logger.error(f"DynamoDB rate limit error: {e}")
            # Fallback to allowing request
            return True, {'remaining': limit - 1, 'reset_time': int(time.time() + window)}
    
    async def _check_memory_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, Dict]:
        """Fallback in-memory rate limiting (not distributed)."""
        
        current_time = time.time()
        
        # Clean up expired entries
        expired_keys = [
            k for k, v in self._fallback_memory.items() 
            if v['expires_at'] < current_time
        ]
        for k in expired_keys:
            del self._fallback_memory[k]
        
        # Check current count
        if key in self._fallback_memory:
            self._fallback_memory[key]['count'] += 1
            current_count = self._fallback_memory[key]['count']
        else:
            self._fallback_memory[key] = {
                'count': 1,
                'expires_at': current_time + window
            }
            current_count = 1
        
        allowed = current_count <= limit
        
        info = {
            'remaining': max(0, limit - current_count),
            'reset_time': int(current_time + window),
            'current_count': current_count,
            'limit': limit,
            'warning': 'Using non-distributed memory cache'
        }
        
        return allowed, info
    
    async def track_cost(self, service: str, cost: float, user_id: str = None) -> Dict[str, Any]:
        """Track service costs for budget monitoring."""
        
        current_hour = int(time.time() // 3600)
        cost_key = f"cost:{service}:{current_hour}"
        user_cost_key = f"user_cost:{user_id}:{current_hour}" if user_id else None
        
        try:
            if self._use_redis and self._redis_client:
                pipe = self._redis_client.pipeline()
                pipe.incrbyfloat(cost_key, cost)
                pipe.expire(cost_key, 7200)  # Keep for 2 hours
                
                if user_cost_key:
                    pipe.incrbyfloat(user_cost_key, cost)
                    pipe.expire(user_cost_key, 7200)
                
                results = await pipe.execute()
                total_cost = results[0]
                user_cost = results[2] if user_cost_key else 0
                
            elif self._dynamodb_table:
                # Use DynamoDB for cost tracking
                response = self._dynamodb_table.update_item(
                    Key={'rate_key': cost_key},
                    UpdateExpression='ADD cost_amount :cost SET expires_at = :expires, service_name = :service',
                    ExpressionAttributeValues={
                        ':cost': cost,
                        ':expires': int(time.time() + 7200),
                        ':service': service
                    },
                    ReturnValues='ALL_NEW'
                )
                total_cost = response['Attributes']['cost_amount']
                user_cost = 0  # Could implement user cost tracking separately
                
            else:
                # Memory fallback
                if cost_key not in self._fallback_memory:
                    self._fallback_memory[cost_key] = {
                        'cost': 0,
                        'expires_at': time.time() + 7200
                    }
                self._fallback_memory[cost_key]['cost'] += cost
                total_cost = self._fallback_memory[cost_key]['cost']
                user_cost = 0
            
            # Check against limits
            service_limit = self.cost_limits.get(f'{service}_hourly', 10.0)
            total_limit = self.cost_limits['total_hourly']
            
            cost_info = {
                'service': service,
                'current_cost': total_cost,
                'service_limit': service_limit,
                'total_limit': total_limit,
                'user_cost': user_cost,
                'approaching_limit': total_cost > service_limit * 0.8,
                'over_limit': total_cost > service_limit
            }
            
            # Log warnings
            if cost_info['over_limit']:
                logger.warning(f"Cost limit exceeded for {service}: ${total_cost:.2f}/${service_limit}")
            elif cost_info['approaching_limit']:
                logger.warning(f"Approaching cost limit for {service}: ${total_cost:.2f}/${service_limit}")
            
            return cost_info
            
        except Exception as e:
            logger.error(f"Cost tracking failed: {e}")
            return {
                'service': service,
                'error': str(e),
                'current_cost': 0,
                'over_limit': False
            }
    
    async def get_rate_limit_stats(self, identifier: str) -> Dict[str, Any]:
        """Get current rate limit statistics for an identifier."""
        
        stats = {}
        current_time = int(time.time())
        
        for action, config in self.default_limits.items():
            window = config['window']
            current_window = current_time // window
            rate_key = f"rate_limit:{action}:{identifier}:{current_window}"
            
            try:
                if self._use_redis and self._redis_client:
                    count = await self._redis_client.get(rate_key) or 0
                    count = int(count)
                elif self._dynamodb_table:
                    response = self._dynamodb_table.get_item(Key={'rate_key': rate_key})
                    count = response.get('Item', {}).get('request_count', 0)
                else:
                    count = self._fallback_memory.get(rate_key, {}).get('count', 0)
                
                stats[action] = {
                    'current': count,
                    'limit': config['limit'],
                    'remaining': max(0, config['limit'] - count),
                    'reset_time': (current_window + 1) * window
                }
                
            except Exception as e:
                logger.error(f"Failed to get stats for {action}: {e}")
                stats[action] = {'error': str(e)}
        
        return stats
    
    async def reset_rate_limit(self, identifier: str, action: str) -> bool:
        """Reset rate limit for specific identifier and action (admin function)."""
        
        current_window = int(time.time() // self.default_limits[action]['window'])
        rate_key = f"rate_limit:{action}:{identifier}:{current_window}"
        
        try:
            if self._use_redis and self._redis_client:
                await self._redis_client.delete(rate_key)
            elif self._dynamodb_table:
                self._dynamodb_table.delete_item(Key={'rate_key': rate_key})
            else:
                self._fallback_memory.pop(rate_key, None)
            
            logger.info(f"Reset rate limit for {identifier}:{action}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


# Global rate limiter instance
rate_limiter = DistributedRateLimiter()


async def check_rate_limit(identifier: str, action: str = 'api_requests') -> Tuple[bool, Dict]:
    """Convenience function for rate limit checking."""
    if not hasattr(rate_limiter, '_initialized'):
        await rate_limiter.initialize()
        rate_limiter._initialized = True
    
    return await rate_limiter.check_rate_limit(identifier, action)


async def track_service_cost(service: str, cost: float, user_id: str = None) -> Dict:
    """Convenience function for cost tracking."""
    if not hasattr(rate_limiter, '_initialized'):
        await rate_limiter.initialize()
        rate_limiter._initialized = True
    
    return await rate_limiter.track_cost(service, cost, user_id)
