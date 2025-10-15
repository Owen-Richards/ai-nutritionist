"""
Dependency Health Checks

Provides health check implementations for various external dependencies.
"""

import asyncio
import time
import socket
from datetime import datetime
from typing import Dict, Optional, Any, List
import logging

import httpx
import redis
import psycopg2
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .core import DependencyCheck, HealthCheckResult, HealthStatus

logger = logging.getLogger(__name__)


class DatabaseHealthCheck(DependencyCheck):
    """Health check for PostgreSQL database"""
    
    def __init__(
        self,
        name: str = "database",
        connection_string: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 5.0
    ):
        super().__init__(name, timeout)
        self.connection_string = connection_string
        self.host = host
        self.port = port or 5432
        self.database = database
        self.user = user
        self.password = password
    
    async def check_health(self) -> HealthCheckResult:
        """Check database connectivity and basic operations"""
        start_time = time.time()
        
        try:
            # Test connection
            if self.connection_string:
                conn = psycopg2.connect(self.connection_string)
            else:
                conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Test write capability (create temp table)
            cursor.execute("CREATE TEMP TABLE health_check (id INTEGER)")
            cursor.execute("INSERT INTO health_check VALUES (1)")
            cursor.execute("SELECT * FROM health_check")
            test_result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if result and test_result:
                return self._create_result(
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration_ms,
                    message="Database connection and operations successful",
                    details={
                        'host': self.host,
                        'port': self.port,
                        'database': self.database,
                        'read_test': 'passed',
                        'write_test': 'passed'
                    }
                )
            else:
                return self._create_result(
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                    message="Database query failed",
                    error="Query returned unexpected result"
                )
        
        except psycopg2.OperationalError as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="Database connection failed",
                error=str(e)
            )
        except Exception as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="Database health check failed",
                error=str(e)
            )


class RedisHealthCheck(DependencyCheck):
    """Health check for Redis cache"""
    
    def __init__(
        self,
        name: str = "redis",
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        timeout: float = 5.0
    ):
        super().__init__(name, timeout)
        self.host = host
        self.port = port
        self.password = password
        self.db = db
    
    async def check_health(self) -> HealthCheckResult:
        """Check Redis connectivity and basic operations"""
        start_time = time.time()
        
        try:
            # Create Redis connection
            r = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                socket_timeout=self.timeout,
                decode_responses=True
            )
            
            # Test ping
            ping_result = r.ping()
            
            # Test set/get
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_check_value"
            
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = r.get(test_key)
            
            # Clean up
            r.delete(test_key)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if ping_result and retrieved_value == test_value:
                # Get Redis info
                info = r.info()
                
                return self._create_result(
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration_ms,
                    message="Redis connection and operations successful",
                    details={
                        'host': self.host,
                        'port': self.port,
                        'db': self.db,
                        'ping_test': 'passed',
                        'read_write_test': 'passed',
                        'redis_version': info.get('redis_version'),
                        'connected_clients': info.get('connected_clients'),
                        'used_memory_human': info.get('used_memory_human')
                    }
                )
            else:
                return self._create_result(
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                    message="Redis operations failed",
                    error="Set/get operation failed"
                )
        
        except redis.ConnectionError as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="Redis connection failed",
                error=str(e)
            )
        except Exception as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="Redis health check failed",
                error=str(e)
            )


class HTTPServiceHealthCheck(DependencyCheck):
    """Health check for HTTP-based external services"""
    
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        expected_response: Optional[str] = None,
        timeout: float = 10.0
    ):
        super().__init__(name, timeout)
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.expected_status = expected_status
        self.expected_response = expected_response
    
    async def check_health(self) -> HealthCheckResult:
        """Check HTTP service availability"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Check status code
                if response.status_code != self.expected_status:
                    return self._create_result(
                        status=HealthStatus.UNHEALTHY,
                        duration_ms=duration_ms,
                        message=f"Unexpected status code: {response.status_code}",
                        details={
                            'url': self.url,
                            'expected_status': self.expected_status,
                            'actual_status': response.status_code,
                            'response_time_ms': duration_ms
                        }
                    )
                
                # Check response content if specified
                if self.expected_response:
                    response_text = response.text
                    if self.expected_response not in response_text:
                        return self._create_result(
                            status=HealthStatus.UNHEALTHY,
                            duration_ms=duration_ms,
                            message="Expected response content not found",
                            details={
                                'url': self.url,
                                'expected_content': self.expected_response,
                                'response_preview': response_text[:200]
                            }
                        )
                
                return self._create_result(
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration_ms,
                    message="HTTP service check successful",
                    details={
                        'url': self.url,
                        'status_code': response.status_code,
                        'response_time_ms': duration_ms,
                        'content_length': len(response.content)
                    }
                )
        
        except httpx.TimeoutException:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"HTTP request timed out after {self.timeout}s",
                error="Timeout",
                details={'url': self.url}
            )
        except Exception as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="HTTP service check failed",
                error=str(e),
                details={'url': self.url}
            )


class AWSServiceHealthCheck(DependencyCheck):
    """Health check for AWS services"""
    
    def __init__(
        self,
        name: str,
        service_name: str,
        region: str = "us-east-1",
        operation: str = "list",
        timeout: float = 10.0
    ):
        super().__init__(name, timeout)
        self.service_name = service_name
        self.region = region
        self.operation = operation
    
    async def check_health(self) -> HealthCheckResult:
        """Check AWS service connectivity"""
        start_time = time.time()
        
        try:
            # Create AWS client
            client = boto3.client(self.service_name, region_name=self.region)
            
            # Perform service-specific health check
            if self.service_name == 's3':
                # List buckets (lightweight operation)
                response = client.list_buckets()
                bucket_count = len(response.get('Buckets', []))
                details = {'bucket_count': bucket_count}
                
            elif self.service_name == 'pinpoint-sms-voice-v2':
                # Check account configuration
                response = client.describe_account_attributes()
                details = {'account_attributes': response.get('AccountAttributes', {})}
                
            elif self.service_name == 'dynamodb':
                # List tables
                response = client.list_tables()
                table_count = len(response.get('TableNames', []))
                details = {'table_count': table_count}
                
            elif self.service_name == 'lambda':
                # List functions (limited)
                response = client.list_functions(MaxItems=1)
                function_count = len(response.get('Functions', []))
                details = {'function_count': function_count}
                
            elif self.service_name == 'cloudwatch':
                # List metrics (limited)
                response = client.list_metrics(MaxRecords=1)
                metric_count = len(response.get('Metrics', []))
                details = {'metric_count': metric_count}
                
            else:
                # Generic check - try to get service description
                try:
                    response = client.describe_regions()
                    details = {'regions_available': len(response.get('Regions', []))}
                except:
                    # If describe_regions not available, just check credentials
                    sts_client = boto3.client('sts', region_name=self.region)
                    identity = sts_client.get_caller_identity()
                    details = {'account_id': identity.get('Account')}
            
            duration_ms = (time.time() - start_time) * 1000
            
            return self._create_result(
                status=HealthStatus.HEALTHY,
                duration_ms=duration_ms,
                message=f"AWS {self.service_name} service check successful",
                details={
                    'service': self.service_name,
                    'region': self.region,
                    'response_time_ms': duration_ms,
                    **details
                }
            )
        
        except NoCredentialsError:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="AWS credentials not found",
                error="No credentials configured"
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"AWS {self.service_name} service error",
                error=f"{error_code}: {str(e)}"
            )
        except Exception as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"AWS {self.service_name} health check failed",
                error=str(e)
            )


class ExternalAPIHealthCheck(DependencyCheck):
    """Health check for external APIs (OpenAI, etc.)"""
    
    def __init__(
        self,
        name: str,
        api_url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        test_endpoint: Optional[str] = None,
        timeout: float = 15.0
    ):
        super().__init__(name, timeout)
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = headers or {}
        self.test_endpoint = test_endpoint
        
        # Add API key to headers if provided
        if self.api_key:
            if 'openai' in self.api_url.lower():
                self.headers['Authorization'] = f'Bearer {self.api_key}'
            else:
                self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    async def check_health(self) -> HealthCheckResult:
        """Check external API availability"""
        start_time = time.time()
        
        try:
            # Determine test endpoint
            if self.test_endpoint:
                test_url = f"{self.api_url}/{self.test_endpoint}"
            elif 'openai' in self.api_url.lower():
                test_url = f"{self.api_url}/models"
            else:
                # Default to root endpoint
                test_url = self.api_url
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(test_url, headers=self.headers)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Check for successful response
                if response.status_code == 200:
                    status = HealthStatus.HEALTHY
                    message = "External API check successful"
                    
                    # Try to get additional info
                    try:
                        json_response = response.json()
                        if 'openai' in self.api_url.lower() and 'data' in json_response:
                            details = {
                                'api_type': 'openai',
                                'models_available': len(json_response['data']),
                                'response_time_ms': duration_ms
                            }
                        else:
                            details = {
                                'response_time_ms': duration_ms,
                                'content_length': len(response.content)
                            }
                    except:
                        details = {
                            'response_time_ms': duration_ms,
                            'content_length': len(response.content)
                        }
                
                elif response.status_code == 401:
                    status = HealthStatus.UNHEALTHY
                    message = "API authentication failed"
                    details = {'status_code': response.status_code}
                
                elif response.status_code == 429:
                    status = HealthStatus.DEGRADED
                    message = "API rate limited"
                    details = {'status_code': response.status_code}
                
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"API returned status {response.status_code}"
                    details = {'status_code': response.status_code}
                
                return self._create_result(
                    status=status,
                    duration_ms=duration_ms,
                    message=message,
                    details={
                        'api_url': self.api_url,
                        'test_endpoint': test_url,
                        **details
                    }
                )
        
        except httpx.TimeoutException:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"API request timed out after {self.timeout}s",
                error="Timeout",
                details={'api_url': self.api_url}
            )
        except Exception as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="External API check failed",
                error=str(e),
                details={'api_url': self.api_url}
            )


class TCPPortHealthCheck(DependencyCheck):
    """Health check for TCP port connectivity"""
    
    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        timeout: float = 5.0
    ):
        super().__init__(name, timeout)
        self.host = host
        self.port = port
    
    async def check_health(self) -> HealthCheckResult:
        """Check TCP port connectivity"""
        start_time = time.time()
        
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if result == 0:
                return self._create_result(
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration_ms,
                    message="TCP connection successful",
                    details={
                        'host': self.host,
                        'port': self.port,
                        'connection_time_ms': duration_ms
                    }
                )
            else:
                return self._create_result(
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                    message="TCP connection failed",
                    error=f"Connection refused or host unreachable",
                    details={
                        'host': self.host,
                        'port': self.port,
                        'error_code': result
                    }
                )
        
        except socket.timeout:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"TCP connection timed out after {self.timeout}s",
                error="Timeout",
                details={'host': self.host, 'port': self.port}
            )
        except Exception as e:
            return self._create_result(
                status=HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start_time) * 1000,
                message="TCP health check failed",
                error=str(e),
                details={'host': self.host, 'port': self.port}
            )
