"""
Cache backend implementations for different storage systems.
"""

import asyncio
import json
import pickle
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import hashlib

# Optional imports with fallbacks
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    boto3 = None

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def get_size(self) -> int:
        """Get current cache size."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check expiration
                if entry['expires_at'] > time.time():
                    # Update access order
                    self._access_order.remove(key)
                    self._access_order.append(key)
                    return entry['value']
                else:
                    # Expired entry
                    await self._remove_entry(key)
            
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        async with self._lock:
            try:
                ttl = ttl or self.default_ttl
                expires_at = time.time() + ttl
                
                # Remove existing entry from access order
                if key in self._cache:
                    self._access_order.remove(key)
                
                # Evict if necessary
                while len(self._cache) >= self.max_size:
                    await self._evict_lru()
                
                # Add new entry
                self._cache[key] = {
                    'value': value,
                    'expires_at': expires_at,
                    'created_at': time.time()
                }
                self._access_order.append(key)
                
                return True
                
            except Exception as e:
                logger.error(f"Error setting memory cache entry {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        async with self._lock:
            return await self._remove_entry(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        value = await self.get(key)
        return value is not None
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            return True
    
    async def get_size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self._cache)
    
    async def _remove_entry(self, key: str) -> bool:
        """Remove entry from cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False
    
    async def _evict_lru(self):
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order[0]
            await self._remove_entry(lru_key)


class RedisCacheBackend(CacheBackend):
    """Redis cache backend with clustering support."""
    
    def __init__(
        self, 
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        cluster_mode: bool = False,
        connection_pool_size: int = 20,
        timeout: float = 1.0
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for Redis backend")
        
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.cluster_mode = cluster_mode
        self.timeout = timeout
        self._redis = None
        
        # Connection pool configuration
        self.pool_config = {
            'host': host,
            'port': port,
            'db': db,
            'password': password,
            'max_connections': connection_pool_size,
            'socket_timeout': timeout,
            'socket_connect_timeout': timeout
        }
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None:
            if self.cluster_mode:
                # Redis Cluster mode
                startup_nodes = [{"host": self.host, "port": self.port}]
                self._redis = redis.RedisCluster(
                    startup_nodes=startup_nodes,
                    password=self.password,
                    socket_timeout=self.timeout
                )
            else:
                # Single Redis instance
                connection_pool = redis.ConnectionPool(**self.pool_config)
                self._redis = redis.Redis(connection_pool=connection_pool)
        
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            redis_client = await self._get_redis()
            
            # Get serialized data
            data = await redis_client.get(key)
            if data is None:
                return None
            
            # Deserialize
            return self._deserialize(data)
            
        except Exception as e:
            logger.error(f"Error getting Redis cache entry {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            redis_client = await self._get_redis()
            
            # Serialize data
            serialized_data = self._serialize(value)
            
            # Set with TTL
            if ttl:
                result = await redis_client.setex(key, ttl, serialized_data)
            else:
                result = await redis_client.set(key, serialized_data)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error setting Redis cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting Redis cache entry {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Error checking Redis key existence {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries in Redis."""
        try:
            redis_client = await self._get_redis()
            await redis_client.flushdb()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")
            return False
    
    async def get_size(self) -> int:
        """Get current Redis database size."""
        try:
            redis_client = await self._get_redis()
            return await redis_client.dbsize()
            
        except Exception as e:
            logger.error(f"Error getting Redis cache size: {e}")
            return 0
    
    async def delete_by_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern."""
        try:
            redis_client = await self._get_redis()
            
            # Use SCAN for large datasets
            count = 0
            async for key in redis_client.scan_iter(match=pattern, count=100):
                await redis_client.delete(key)
                count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Error deleting Redis keys by pattern {pattern}: {e}")
            return 0
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get TTL for a key."""
        try:
            redis_client = await self._get_redis()
            ttl = await redis_client.ttl(key)
            return ttl if ttl > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return None
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis storage."""
        try:
            # Try JSON first for simple types
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                return json.dumps(value).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(value)
        except Exception:
            # Fallback to pickle
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from Redis storage."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to pickle
            return pickle.loads(data)
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


class DatabaseCacheBackend(CacheBackend):
    """Database cache backend using DynamoDB."""
    
    def __init__(
        self, 
        table_name: str = "ai_nutritionist_cache",
        region_name: str = "us-east-1"
    ):
        if not AWS_AVAILABLE:
            raise ImportError("boto3 package is required for Database backend")
        
        self.table_name = table_name
        self.region_name = region_name
        self._dynamodb = None
        self._table = None
    
    def _get_table(self):
        """Get DynamoDB table."""
        if self._table is None:
            if self._dynamodb is None:
                self._dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
            self._table = self._dynamodb.Table(self.table_name)
        return self._table
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from DynamoDB cache."""
        try:
            table = self._get_table()
            
            response = await asyncio.to_thread(
                table.get_item,
                Key={'cache_key': key}
            )
            
            if 'Item' in response:
                item = response['Item']
                
                # Check expiration
                expires_at = item.get('expires_at', 0)
                if expires_at > time.time():
                    return self._deserialize(item['value'])
                else:
                    # Expired - delete it
                    await self.delete(key)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting DynamoDB cache entry {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in DynamoDB cache."""
        try:
            table = self._get_table()
            
            expires_at = time.time() + (ttl or 3600)
            
            await asyncio.to_thread(
                table.put_item,
                Item={
                    'cache_key': key,
                    'value': self._serialize(value),
                    'expires_at': int(expires_at),
                    'created_at': int(time.time())
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting DynamoDB cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from DynamoDB cache."""
        try:
            table = self._get_table()
            
            await asyncio.to_thread(
                table.delete_item,
                Key={'cache_key': key}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting DynamoDB cache entry {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in DynamoDB cache."""
        value = await self.get(key)
        return value is not None
    
    async def clear(self) -> bool:
        """Clear all cache entries (scan and delete)."""
        try:
            table = self._get_table()
            
            # Scan all items
            response = await asyncio.to_thread(table.scan)
            
            # Delete in batches
            with table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(Key={'cache_key': item['cache_key']})
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing DynamoDB cache: {e}")
            return False
    
    async def get_size(self) -> int:
        """Get approximate cache size."""
        try:
            table = self._get_table()
            response = await asyncio.to_thread(table.describe_table)
            return response['Table']['ItemCount']
            
        except Exception as e:
            logger.error(f"Error getting DynamoDB cache size: {e}")
            return 0
    
    def _serialize(self, value: Any) -> str:
        """Serialize value for DynamoDB storage."""
        try:
            return json.dumps(value, default=str)
        except Exception:
            # Fallback to base64 encoded pickle
            import base64
            return base64.b64encode(pickle.dumps(value)).decode('utf-8')
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize value from DynamoDB storage."""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            # Try base64 decoded pickle
            import base64
            return pickle.loads(base64.b64decode(data.encode('utf-8')))


class CDNCacheBackend(CacheBackend):
    """CDN cache backend for static content caching."""
    
    def __init__(
        self, 
        base_url: str,
        cache_control: str = "public, max-age=3600",
        s3_bucket: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.cache_control = cache_control
        self.s3_bucket = s3_bucket
        self._s3_client = None
        
        if s3_bucket and AWS_AVAILABLE:
            self._s3_client = boto3.client('s3')
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from CDN (usually via HTTP)."""
        try:
            import aiohttp
            
            url = f"{self.base_url}/{key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        if 'application/json' in content_type:
                            return await response.json()
                        else:
                            return await response.text()
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting CDN cache entry {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in CDN (upload to S3 if configured)."""
        if not self._s3_client or not self.s3_bucket:
            return False
        
        try:
            # Serialize content
            if isinstance(value, (dict, list)):
                content = json.dumps(value)
                content_type = 'application/json'
            else:
                content = str(value)
                content_type = 'text/plain'
            
            # Set cache control based on TTL
            cache_control = self.cache_control
            if ttl:
                cache_control = f"public, max-age={ttl}"
            
            await asyncio.to_thread(
                self._s3_client.put_object,
                Bucket=self.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl=cache_control
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting CDN cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from CDN (S3)."""
        if not self._s3_client or not self.s3_bucket:
            return False
        
        try:
            await asyncio.to_thread(
                self._s3_client.delete_object,
                Bucket=self.s3_bucket,
                Key=key
            )
            return True
            
        except Exception as e:
            logger.error(f"Error deleting CDN cache entry {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in CDN."""
        if not self._s3_client or not self.s3_bucket:
            return False
        
        try:
            await asyncio.to_thread(
                self._s3_client.head_object,
                Bucket=self.s3_bucket,
                Key=key
            )
            return True
            
        except Exception:
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries (not recommended for CDN)."""
        logger.warning("Clear operation not recommended for CDN cache")
        return False
    
    async def get_size(self) -> int:
        """Get cache size (not easily available for CDN)."""
        return 0
